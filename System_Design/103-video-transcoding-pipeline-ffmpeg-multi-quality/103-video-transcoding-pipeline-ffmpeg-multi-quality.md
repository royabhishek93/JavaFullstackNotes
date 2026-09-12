# Video Transcoding Pipeline: FFmpeg Multi-Quality Encoding Ladder
### How one uploaded video becomes the 6 bitrate rungs your player adaptively switches between

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you upload a 10-minute video to YouTube. Within a few minutes, that video is watchable at 240p on a subway connection, at 1080p on home Wi-Fi, and at 4K on a fiber connection — all from the SAME single file you uploaded. That doesn't happen by magic; it happens because YouTube's backend spent real compute time, right after your upload, creating *several completely separate encoded versions* of your video — one for each quality rung — and chopping each of them into small chunks that a video player can adaptively switch between mid-playback.

This file is about that production/encoding side — the offline pipeline that CREATES the encoding ladder. (For the delivery side — how the player picks which chunk to fetch next based on network conditions — see 096-hls-adaptive-bitrate-streaming.md.)

Here's the analogy: think of a print shop that receives one master photograph and needs to produce postcards, posters, and a giant banner from it, each requiring different processing (resizing, re-compressing, re-touching for that specific size). You wouldn't try to derive the giant banner from the tiny postcard — you'd always start from the master, and run each size as its own independent job, ideally in parallel on different printing presses so the whole batch finishes faster.

That's exactly what a transcoding pipeline does. The raw uploaded file goes into cold storage. A job is enqueued asking "please produce the 1080p, 720p, 480p, 360p, and 240p renditions of video X." Each rendition is a separate FFmpeg process — its own CPU-bound job — because encoding at 240p is a genuinely different computation from encoding at 1080p (different resolution, different bitrate target, different encoder settings). These jobs run on a fleet of autoscaling workers, often further parallelized by splitting a single video into time-chunks so a 2-hour video isn't a single 2-hour-long CPU-bound task blocking one worker — instead, ten workers each transcode a 12-minute chunk, and a final step concatenates them back together.

Once every rendition exists, each is segmented into small HLS chunks (typically 2-10 seconds each) with a manifest file describing them, thumbnails and a "scrubbing preview sprite" are generated, and everything is uploaded to object storage and pushed out to the CDN. Only then does the video become "ready to watch" — which is why there's always a visible processing delay between upload and availability.

---

## PART 2 — THE TRANSCODING PIPELINE ARCHITECTURE DIAGRAMS

### End-to-End Pipeline: Upload to Watchable

```
Creator uploads               Upload Service            Raw Storage           Job Queue              Transcode Workers
──────────────────           ────────────────           ────────────          ─────────              ──────────────────

video.mp4 (2.1 GB,                                                                                                     T+0:00
1080p source,                POST /videos/upload
10-min runtime)      ───►    Validates format,     ───►  S3/GCS bucket:
                              generates videoId       "raw/vid_8f3a2b1c/
                              = "vid_8f3a2b1c"          source.mp4"
                                                        (durable, never
                                                         deleted — re-transcode
                                                         source if ladder
                                                         needs regenerating)
                                                              |
                              Publishes job    ─────────────►|
                              to queue:                      v
                              {                        Kafka topic:
                                "videoId":              "video.transcode.jobs"
                                "vid_8f3a2b1c",               |
                                "sourcePath":                 |
                                "raw/.../source.mp4",         |
                                "renditions":                 |
                                  ["1080p","720p",             |
                                   "480p","360p","240p"]       |
                              }                                |
                                                                v
                                                        Worker pool (autoscaling,
                                                        e.g. 50-200 spot GPU/CPU
                                                        instances based on queue depth)
                                                        consumes job, fans out:
                                                                |
                              ┌─────────────────────────────────┼─────────────────────────────────┐
                              v                                 v                                 v
                        Worker A: 1080p                  Worker B: 720p                    Worker C: 480p/360p/240p
                        rung (highest CPU cost)           rung                              (lower-res rungs are cheap,
                        ffmpeg -i source.mp4              ffmpeg -i source.mp4              often batched on one worker)
                        -vf scale=1920:1080                -vf scale=1280:720
                        -b:v 5000k ...                     -b:v 2800k ...
                        Duration: ~4 min for               Duration: ~2.5 min
                        10-min source (0.4x realtime)      (0.25x realtime)
                              |                                 |                                 |
                              └─────────────────────────────────┼─────────────────────────────────┘
                                                                v
                                                        Segment each rendition into
                                                        HLS chunks (6-sec segments):
                                                          vid_8f3a2b1c_1080p_000.ts
                                                          vid_8f3a2b1c_1080p_001.ts
                                                          ... (100 segments for 10 min)
                                                        + master.m3u8 manifest
                                                                |
                                                                v
                                                        Thumbnail + sprite generation:
                                                          thumb_default.jpg (1 frame)
                                                          sprite_scrub.jpg (100 tiny
                                                            frames, 1 per 6-sec segment,
                                                            for scrubber preview)
                                                                |
                                                                v                              CDN / Origin
                                                        Upload all outputs to         ───►    Warm edge caches,
                                                        object storage:                        publish availability
                                                          "processed/vid_8f3a2b1c/              event
                                                           1080p/*.ts, master.m3u8,
                                                           thumb_default.jpg"
                                                                |
                                                                v
                                                        Webhook callback to
                                                        Upload Service:
                                                          POST /videos/vid_8f3a2b1c/ready
                                                                |
                                                                v
                                                        Video status: PROCESSING -> READY
                                                        (creator's dashboard updates,
                                                         video becomes publicly playable)

Total wall-clock T+0:00 to READY: ~6-8 minutes for a 10-min 1080p source
(dominated by the 1080p rung, since lower rungs finish faster and run
in parallel on separate workers)
```

### Parallelizing a Long Video by Time-Chunking

```
Problem: A 2-hour source video transcoded at 720p, single-threaded,
takes roughly 0.25x realtime per rung = ~30 minutes wall-clock for
JUST the 720p rung on one worker. Across 5 rungs sequentially on one
worker, that's 2.5+ hours — unacceptable for a platform promising
"video ready in minutes."

Solution: split the source into N time-chunks BEFORE transcoding,
send each chunk to a different worker in parallel, then concatenate.

  Source: 2-hour video (7200s)
  Split into 10 chunks of 12 minutes (720s) each, using keyframe-aligned
  cut points (ffprobe identifies nearest I-frame to avoid re-encoding
  artifacts at the splice boundary):

  ffmpeg -i source.mp4 -c copy -ss 0    -t 720 chunk_00.mp4   (0:00-12:00)
  ffmpeg -i source.mp4 -c copy -ss 720  -t 720 chunk_01.mp4   (12:00-24:00)
  ... (stream-copy, no re-encode, so splitting itself is near-instant)
  ffmpeg -i source.mp4 -c copy -ss 6480 -t 720 chunk_09.mp4   (108:00-120:00)

  Dispatch each chunk to a SEPARATE worker, each transcoding its
  12-min chunk to 720p independently:

    Worker 1: chunk_00 -> chunk_00_720p.ts   (~3 min wall-clock)
    Worker 2: chunk_01 -> chunk_01_720p.ts   (~3 min wall-clock, IN PARALLEL)
    ...
    Worker 10: chunk_09 -> chunk_09_720p.ts  (~3 min wall-clock, IN PARALLEL)

  All 10 workers run concurrently -> wall-clock for the 720p rung
  drops from ~30 min (single worker) to ~3-4 min (10 workers in parallel,
  plus small overhead for splitting/concatenation coordination).

  Concatenate outputs back into one continuous rendition:
    ffmpeg -f concat -safe 0 -i chunklist.txt -c copy final_720p.mp4
    (stream-copy concat, since all chunks share identical codec params —
     fast, no re-encode needed at this step)

  This same fan-out repeats independently for EACH rung (1080p, 480p,
  etc.), so the whole ladder for a 2-hour video can complete in
  well under 15 minutes total, instead of hours.
```

### Failure Mode: Worker Crash Mid-Job and Retry

```
T+0:00  Job dispatched: transcode vid_8f3a2b1c, chunk_04, rung=1080p,
        assigned to Worker 17 (spot instance).

T+2:15  Worker 17 is a spot/preemptible instance and receives a
        termination notice from the cloud provider (spot reclaim).
        FFmpeg process is killed mid-encode. Partial output file
        "chunk_04_1080p.ts" exists but is truncated/corrupt.

T+2:16  Job queue (SQS/Kafka) never received an ACK for this job
        (worker died before acking) -> message becomes visible
        again after visibility-timeout expires (e.g. 5 min for SQS).

T+7:16  A DIFFERENT healthy worker (Worker 33) picks up the same
        job from the queue (message redelivery).
        - Checks object storage: does a valid, complete
          "chunk_04_1080p.ts" already exist? (idempotency check
          via a manifest/checksum, not just file presence, since
          the truncated file from Worker 17 DOES exist but is invalid)
        - Truncated file fails checksum/duration validation ->
          treated as absent, job re-run from scratch.
        - Worker 33 re-transcodes chunk_04 successfully.

T+9:45  Job completes. Progress tracker (Redis hash or DB row per
        videoId) increments completed-chunks count.
        Once ALL chunks for ALL rungs report complete, the
        concatenation + packaging step triggers.

Operational safeguards in place:
  - Max retry count (e.g. 3) before routing to a dead-letter queue
    and alerting on-call (protects against a systematically bad
    input file causing infinite retry loops).
  - Idempotent job IDs (videoId + chunkIndex + rung) so redelivery
    never produces duplicate/conflicting output files.
  - Progress webhook to the upload service on EVERY state change
    (queued -> processing -> failed -> retrying -> ready) so the
    creator's UI can show real status instead of a silent spinner.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### FFmpeg Command for One Rung of the Encoding Ladder

```bash
# Produce the 720p rung, targeting ~2.8 Mbps video bitrate,
# H.264 (libx264) codec, AAC audio, segmented for HLS delivery.

ffmpeg -i source.mp4 \
  -vf "scale=1280:720" \
  -c:v libx264 -preset medium -profile:v main -level 4.0 \
  -b:v 2800k -maxrate 2996k -bufsize 4200k \
  -g 48 -keyint_min 48 -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 48000 -ac 2 \
  -hls_time 6 -hls_playlist_type vod \
  -hls_segment_filename "vid_8f3a2b1c_720p_%03d.ts" \
  vid_8f3a2b1c_720p.m3u8

# Flag notes:
#   -g 48 -keyint_min 48 -sc_threshold 0
#     Forces a keyframe (I-frame) every 48 frames (2s @ 24fps),
#     ALIGNED across every rung — critical so the player can
#     switch bitrates cleanly at segment boundaries (see
#     096-hls-adaptive-bitrate-streaming.md for why alignment matters).
#   -maxrate / -bufsize
#     VBV constraints so CDN/player buffering assumptions hold —
#     prevents transient bitrate spikes above the advertised rung rate.
#   -hls_time 6
#     6-second segments — a common middle ground: short enough for
#     fast quality switches, long enough to keep segment-count/manifest
#     overhead reasonable (10-min video -> ~100 segments per rung).
```

### The Full Encoding Ladder (Typical Rung Set)

```json
{
  "videoId": "vid_8f3a2b1c",
  "sourceResolution": "1920x1080",
  "renditions": [
    { "name": "1080p", "resolution": "1920x1080", "videoBitrateKbps": 5000, "audioBitrateKbps": 192 },
    { "name": "720p",  "resolution": "1280x720",  "videoBitrateKbps": 2800, "audioBitrateKbps": 128 },
    { "name": "480p",  "resolution": "854x480",   "videoBitrateKbps": 1400, "audioBitrateKbps": 128 },
    { "name": "360p",  "resolution": "640x360",   "videoBitrateKbps": 800,  "audioBitrateKbps": 96  },
    { "name": "240p",  "resolution": "426x240",   "videoBitrateKbps": 400,  "audioBitrateKbps": 64  }
  ],
  "segmentDurationSec": 6,
  "note": "Never upscale: only generate rungs <= source resolution. A 720p source never gets a synthetic 1080p rung."
}
```

### Job Queue + Worker Pool (Java / Spring, Kafka Consumer)

```java
@Component
public class TranscodeJobConsumer {

    @Autowired private FfmpegExecutor ffmpeg;
    @Autowired private ObjectStorageClient storage;
    @Autowired private ProgressTracker progress;

    @KafkaListener(topics = "video.transcode.jobs", concurrency = "20")
    public void handle(TranscodeJob job) {
        String outputKey = String.format("processed/%s/%s/chunk_%02d.ts",
            job.videoId(), job.rendition(), job.chunkIndex());

        // Idempotency: skip if a VALID output already exists (checksum, not just presence)
        if (storage.existsAndValid(outputKey, job.expectedDurationSec())) {
            progress.markComplete(job.videoId(), job.rendition(), job.chunkIndex());
            return;
        }

        try {
            Path localOutput = ffmpeg.transcode(job.sourceChunkPath(), job.rendition());
            storage.upload(localOutput, outputKey);
            progress.markComplete(job.videoId(), job.rendition(), job.chunkIndex());

            if (progress.isFullyComplete(job.videoId())) {
                triggerConcatenationAndPackaging(job.videoId());
            }
        } catch (FfmpegException e) {
            progress.markFailed(job.videoId(), job.rendition(), job.chunkIndex(), e.getMessage());
            throw e; // let Kafka redeliver up to configured max retries, then DLQ
        }
    }
}
```

### Real Numbers

```
Source: 10-minute 1080p video (1920x1080, ~24fps, H.264, ~2.1 GB)

Per-rung transcode time (single worker, no chunk-splitting), typical
cloud CPU-based encoding (e.g. c5.4xlarge equivalent, libx264 "medium" preset):
  1080p rung:  ~4.0 min   (~0.4x realtime — slowest, highest resolution)
  720p rung:   ~2.5 min   (~0.25x realtime)
  480p rung:   ~1.5 min   (~0.15x realtime)
  360p rung:   ~1.0 min   (~0.10x realtime)
  240p rung:   ~0.6 min   (~0.06x realtime)
  Sequential total (1 worker, all rungs): ~9.6 min
  Parallel total (5 workers, one per rung): ~4.0 min (bounded by slowest rung)

With time-chunk splitting (10 chunks, 10 workers per rung):
  1080p rung wall-clock: ~0.4-0.6 min per chunk, all parallel -> ~1 min total
  (Plus fixed overhead: splitting ~5-10s, concatenation ~10-20s per rung)

Cost estimate (cloud CPU transcoding, rough public pricing ballpark):
  ~$0.015-$0.030 per minute of SOURCE video per rung on general-purpose
  CPU instances; a full 5-rung ladder for a 10-min video:
  ~10 min * 5 rungs * ~$0.02/min ≈ $1.00 per video
  (GPU-accelerated encoding, e.g. NVENC, cuts wall-clock significantly
  but has different cost/quality tradeoffs — common for very high volume)

Storage footprint (all rungs + segments + thumbnails, 10-min video):
  1080p rendition: ~230 MB   720p: ~130 MB   480p: ~65 MB
  360p: ~37 MB   240p: ~19 MB   thumbnails+sprite: ~2 MB
  Total processed output: ~480 MB (vs 2.1 GB raw source retained separately)
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "A creator uploads a 2-hour 1080p video. We need it available for adaptive-bitrate streaming — five quality rungs — within about 15 minutes. Walk me through the pipeline you'd design, and how you'd hit that time budget for a video this long."

**You (architect answer):**

> "The naive approach — one worker running FFmpeg sequentially through all five rungs for the full 2-hour file — would take well over two hours just for the highest rung, which blows the 15-minute budget immediately. So the design has to parallelize on two axes: across rungs, and within a single rung across time.
>
> First, the raw upload lands in durable object storage — that source file is never deleted, because if I ever need to regenerate the ladder (say, we add an AV1 rung later, or fix an encoder bug), I re-derive from the source rather than from an already-lossy rendition. A job is published to a queue describing which rungs to produce.
>
> Second, for a video this long, I split the source into time-chunks — say ten 12-minute chunks — using a stream-copy cut at the nearest keyframe, so the split itself is nearly instant and doesn't re-encode anything. Each chunk, for each rung, becomes an independent unit of work dispatched to an autoscaling worker pool. That gives me two dimensions of parallelism: five rungs times ten chunks means up to fifty FFmpeg jobs running concurrently across the fleet, instead of five sequential multi-hour jobs.
>
> One detail I'd insist on: keyframes must be aligned identically across every rung — same GOP size, same forced keyframe interval — because the player needs to switch bitrates cleanly at segment boundaries, and misaligned keyframes across rungs break that. Once every chunk for every rung finishes, I concatenate the chunks back into a continuous rendition per rung using another fast stream-copy, then segment each into HLS `.ts` files with a manifest, generate thumbnails and a scrub-preview sprite, and push everything to object storage and the CDN.
>
> The operational concern I'd flag is worker failure mid-job — these are often spot/preemptible instances for cost reasons, so they get killed without warning. My mitigation is idempotent job IDs keyed on videoId, rung, and chunk index, plus a validity check on redelivery — not just 'does the output file exist' but 'does it pass a duration/checksum check' — because a truncated partial file from a killed worker DOES exist on disk and would silently corrupt the final concatenation if I only checked for file presence. Jobs that fail past a retry limit go to a dead-letter queue with an alert, and I push progress webhooks back to the upload service at every state transition so the creator sees real status instead of a stuck spinner."

---

## PART 5 — DECISION FRAMEWORK

### Transcoding Architecture Choices

| Approach | How It Works | Tradeoff | Latency (10-min 1080p video) | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Single worker, sequential rungs** | One FFmpeg process per rung, one after another | Simplest to build, ops-light | ~9-10 min | Low | Blows time budget badly for long videos (2hr+) |
| **Parallel-by-rung only** | One worker per rung, all rungs run concurrently | Good improvement, still bounded by slowest (highest) rung | ~4 min | Low-Medium | Long videos still bottleneck on the 1080p rung alone |
| **Parallel-by-rung + time-chunking (this file)** | Split source into N chunks, fan out N*rungs jobs, concatenate | Fastest, but adds splitting/concat/idempotency complexity | ~1-4 min even for 2-hr source | Medium-High | Keyframe-misaligned splits cause visible glitches at splice points if not handled carefully |
| **GPU-accelerated encoding (NVENC/QuickSync)** | Hardware encoder instead of CPU libx264 | Much faster wall-clock, but different rate-distortion tradeoffs, needs GPU fleet | Sub-minute per rung possible | Medium | Higher instance cost per hour; quality-per-bitrate slightly behind best CPU presets at very low bitrates |
| **On-demand/just-in-time transcoding** | Transcode only requested rung, only when first requested | Saves compute for rarely-watched videos/rungs | First viewer waits (seconds-minutes); later viewers instant | Medium | Bad for viral/spiky content — first requester eats a large latency penalty |

### When full-ladder pre-transcoding (this pipeline) is right

```
✓ Content is expected to be watched by many viewers across many networks/devices
✓ You control upload-to-publish latency expectations (few minutes is acceptable)
✓ Predictable, poolable compute demand (batch job queue, autoscaling workers)
✓ You need every rung ready before the FIRST viewer arrives (no per-request latency)
```

### Skip full pre-transcoding when

```
✗ Content is rarely watched (long-tail archive) -> transcode on-demand, cache result
✗ Live streaming (no "video file" exists yet to batch-process) -> needs real-time
  segment-by-segment encoding pipeline instead, not this offline batch model
✗ Extremely tight upload-to-publish SLA (sub-30-second) at very long video lengths
  -> may need to publish lower rungs first and backfill higher rungs progressively
✗ Single-resolution-only use case (e.g. fixed-format internal tool) -> a single
  transcode pass with no ladder is simpler and sufficient
```

---

## QUICK REFERENCE CARD

```
PIPELINE STAGES:
  upload -> raw storage -> job queue -> parallel FFmpeg workers
  -> HLS segment + manifest -> thumbnails/sprite -> CDN publish
  -> webhook: video status READY

TYPICAL ENCODING LADDER (5 rungs):
  1080p  5000 kbps video / 192 kbps audio
  720p   2800 kbps / 128 kbps
  480p   1400 kbps / 128 kbps
  360p    800 kbps /  96 kbps
  240p    400 kbps /  64 kbps
  Rule: never generate a rung ABOVE source resolution.

FFMPEG CORE FLAGS:
  -vf scale=W:H              resize
  -c:v libx264 -b:v Xk        video codec + bitrate
  -g 48 -keyint_min 48 -sc_threshold 0   aligned keyframes (critical for ABR)
  -hls_time 6 -hls_playlist_type vod     6s HLS segments

PARALLELIZE LONG VIDEOS:
  split source into N time-chunks (keyframe-aligned, stream-copy cut)
  -> fan out N * rungCount jobs across worker pool
  -> concatenate (stream-copy, no re-encode) per rung when all chunks done

RELIABILITY:
  idempotent job key = videoId + rendition + chunkIndex
  validity check on redelivery = checksum/duration, NOT just file existence
  max retries -> dead-letter queue -> alert on-call
  progress webhook on every state transition

SEE ALSO:
  096-hls-adaptive-bitrate-streaming.md  (delivery/player side)
```

---
