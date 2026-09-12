# HLS and Adaptive Bitrate Streaming
### How Netflix and YouTube keep your video playing smoothly when your WiFi drops from 50 Mbps to 2 Mbps mid-episode

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you're watching a movie on a road trip, and the car has a screen showing a live speedometer of your internet connection. When the signal is strong, you'd want the highest quality picture. When you drive through a tunnel and the signal drops, you'd rather the video get a little blurry for a few seconds than freeze completely and make you wait. That's exactly the trade-off adaptive bitrate streaming is built to solve — never stop playback, quietly trade picture quality for continuity when bandwidth gets scarce.

Here's the trick: instead of storing ONE video file, the platform pre-encodes the SAME video multiple times at different quality levels — think of it like printing the same book in paperback (small, cheap, lower quality) and hardcover (large, expensive, best quality), and several editions in between. Then, it chops each of those versions into small, few-second pieces, like tearing each edition of the book into individual pages. Your video player downloads pages one at a time, and CRUCIALLY, it's allowed to switch editions between pages — read page 5 from the paperback, then page 6 from the hardcover, as long as it never mixes pages of DIFFERENT editions mid-page (mid-segment).

Why chop it into pieces at all, instead of just switching bitrate live like changing a TV channel? Because video compression works by encoding groups of frames relative to a "keyframe" (a fully self-contained frame), and you can't cleanly jump from a keyframe in a 500kbps stream to a mid-group frame in a 3Mbps stream — the decoder needs an aligned keyframe boundary to switch cleanly. So all bitrate versions are encoded with keyframes at the exact same timestamps (e.g., every 2 or 6 seconds), and video is only ever allowed to switch quality level at those aligned boundaries — hence segments.

Your video player is constantly playing detective: it watches how fast the last few segments downloaded (are we getting 10Mbps or 1Mbps right now?) and how full its internal buffer is (do I have 30 seconds of video queued up, or am I about to run dry in 2 seconds?). Based on those two signals, it decides: "download the next segment from the 720p track" or "drop down to 480p, bandwidth is getting scarce." This is the Adaptive Bitrate (ABR) algorithm, and it runs entirely on the client — the server doesn't make this decision, it just exposes a menu (the manifest) of what quality tracks are available and lets the player pick.

---

## PART 2 — THE HLS/ABR ARCHITECTURE DIAGRAMS

### Manifest Hierarchy: Master Playlist → Media Playlists → Segments

```
                         master.m3u8  (the "menu" — lists all quality variants)
                              │
    ┌──────────┬──────────┬──────────┬──────────┬─────────────┐
    │          │          │          │          │             │
    ▼          ▼          ▼          ▼          ▼             ▼
 240p.m3u8  480p.m3u8  720p.m3u8  1080p.m3u8  2160p.m3u8   audio.m3u8
 500 kbps   1.5 Mbps   3 Mbps     6 Mbps      25 Mbps      128 kbps
    │          │          │          │             │
    ▼          ▼          ▼          ▼             ▼
  seg-001.ts  seg-001.ts seg-001.ts seg-001.ts  seg-001.ts   (all timestamp-aligned:
  seg-002.ts  seg-002.ts seg-002.ts seg-002.ts  seg-002.ts    seg-047 in EVERY track
  seg-003.ts  seg-003.ts seg-003.ts seg-003.ts  seg-003.ts    covers the exact same
    ...         ...        ...        ...          ...        6.0-second window)
  seg-047.ts  seg-047.ts seg-047.ts seg-047.ts  seg-047.ts
  (6.0s each) (6.0s each)(6.0s each)(6.0s each) (6.0s each)

# master.m3u8 contents (what the client fetches FIRST):
#EXTM3U
#EXT-X-VERSION:7
#EXT-X-STREAM-INF:BANDWIDTH=500000,RESOLUTION=426x240,CODECS="avc1.42e00a,mp4a.40.2"
240p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1500000,RESOLUTION=854x480,CODECS="avc1.4d401e,mp4a.40.2"
480p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=3000000,RESOLUTION=1280x720,CODECS="avc1.4d401f,mp4a.40.2"
720p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=6000000,RESOLUTION=1920x1080,CODECS="avc1.640028,mp4a.40.2"
1080p.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=25000000,RESOLUTION=3840x2160,CODECS="hvc1.2.4.L153.90"
2160p.m3u8

# 720p.m3u8 contents (the "media playlist" for ONE quality track):
#EXTM3U
#EXT-X-VERSION:7
#EXT-X-TARGETDURATION:6
#EXT-X-PLAYLIST-TYPE:VOD
#EXT-X-MEDIA-SEQUENCE:0
#EXTINF:6.000,
seg-001.ts
#EXTINF:6.000,
seg-002.ts
#EXTINF:6.000,
seg-003.ts
...
#EXT-X-ENDLIST
```

### Encoding Ladder: Real Bitrate/Resolution Tiers

```
┌────────────┬────────────┬─────────────┬──────────────────┬───────────────────┐
│ Rendition  │ Resolution │ Video Bitrate│ Segment Size(6s) │ Typical Use Case  │
├────────────┼────────────┼─────────────┼──────────────────┼───────────────────┤
│ 240p       │ 426×240    │ 500 kbps    │ ~375 KB          │ 2G/weak 3G, EDGE  │
│ 360p       │ 640×360    │ 800 kbps    │ ~600 KB          │ Mobile data-saver │
│ 480p       │ 854×480    │ 1.5 Mbps    │ ~1.1 MB          │ Standard 4G       │
│ 720p       │ 1280×720   │ 3 Mbps      │ ~2.25 MB         │ Good WiFi/4G+     │
│ 1080p      │ 1920×1080  │ 6 Mbps      │ ~4.5 MB          │ Home broadband    │
│ 2160p (4K) │ 3840×2160  │ 25 Mbps     │ ~18.75 MB        │ Fiber/high-speed  │
└────────────┴────────────┴─────────────┴──────────────────┴───────────────────┘

Each rendition is a SEPARATE full transcode of the source master (usually a
high-bitrate ProRes or lightly-compressed mezzanine file), not a re-compression
of a lower-quality rendition — re-encoding from an already-lossy rendition
would compound artifacts. A typical VOD encoding pipeline fans one source out
to all 6 renditions in parallel using a farm of transcoding workers (e.g.
AWS MediaConvert, or self-hosted FFmpeg workers).

General rule of thumb (encoders target ~2x bitrate headroom for peak/motion
complexity above the "average" bitrate quoted): actual encoded file bitrate
fluctuates per-segment based on scene complexity (VBR — variable bitrate) even
though the "ladder" advertises one nominal number per rendition.
```

### Client ABR Decision Timeline Under a Bandwidth Drop

```
Time →   0s        6s        12s       18s       24s       30s       36s
         │         │         │         │         │         │         │
Buffer:  [████████████] 24s   [██████] 12s  [██] 4s   [░] 0.5s [██] 6s  [████] 18s
         (healthy)           (draining)   (CRITICAL) (rebuffer!)  (recovering)

Throughput samples (measured per-segment download):
  seg@0s:  downloaded 4.5MB in 0.9s  → ~40 Mbps  → plenty of headroom, on 1080p
  seg@6s:  downloaded 4.5MB in 1.4s  → ~26 Mbps  → still fine, stay on 1080p
  seg@12s: downloaded 4.5MB in 4.8s  → ~7.5 Mbps → WARNING: throughput dropping
           fast, buffer only refilling slowly (segment took almost as long
           as its own playback duration)
  seg@18s: ABR algorithm decides: SWITCH DOWN to 480p (1.5 Mbps track) at
           the next segment boundary — this is the earliest point a switch
           is legal, because 480p's keyframe at t=18s aligns with 1080p's
  seg@18s: downloaded 480p segment: 1.1MB in 1.6s → ~5.5 Mbps → buffer
           starts refilling instead of draining (segment took less time
           than its 6s playback duration)
  seg@24s: buffer hit critically low point (0.5s) BEFORE the down-switch
           had time to take effect → REBUFFER EVENT: playback pauses,
           spinner shown, buffer must refill past a minimum threshold
           (commonly 2-3 seconds) before resuming
  seg@30s: buffer refilling on 480p segments, throughput stabilizing ~6 Mbps
  seg@36s: ABR conservatively probes back up — some algorithms wait for
           SUSTAINED higher throughput across 2-3 segments before stepping
           back up to 720p, to avoid oscillating ("flapping") between
           bitrates every few seconds, which is itself a bad user experience

Two dominant ABR algorithm families:
  1. THROUGHPUT-BASED: pick the highest bitrate rendition whose bitrate is
     <= (measured recent throughput * safety margin, e.g. 0.8-0.9x).
     Simple, reacts fast to network changes, but can be noisy/oscillate on
     bursty networks (a single fast segment triggers an upswitch, then a
     slow one immediately triggers a downswitch).
  2. BUFFER-BASED (e.g. BOLA, used in some dash.js/ExoPlayer configs):
     Bitrate choice is a function of buffer OCCUPANCY, not throughput
     directly — if buffer is deep (say >20s), be aggressive and pick a
     higher bitrate even if recent throughput samples are borderline;
     if buffer is shallow (<10s), be conservative regardless of measured
     throughput. This tends to produce fewer bitrate switches and fewer
     rebuffer events on variable/bursty networks, at the cost of being
     slower to react to a genuine sustained bandwidth drop.
  Production players (e.g. ExoPlayer, hls.js, Shaka Player) commonly blend
  both signals rather than using either in isolation.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### FFmpeg: Producing the Encoding Ladder + HLS Segments

```bash
# Transcode a source video into ONE rendition (720p/3Mbps) with 6-second
# segments and keyframes forced at exact segment boundaries.
ffmpeg -i source_master.mov \
  -vf "scale=1280:720" \
  -c:v h264 -profile:v main -b:v 3000k -maxrate 3000k -bufsize 6000k \
  -g 180 -keyint_min 180 -sc_threshold 0 \
  -c:a aac -b:a 128k -ar 48000 \
  -f hls \
  -hls_time 6 \
  -hls_playlist_type vod \
  -hls_segment_filename "720p_seg-%03d.ts" \
  720p.m3u8

# Key flags explained:
#   -g 180            GOP size = 180 frames. At 30fps, 180 frames = 6.0s,
#                      matching -hls_time 6 exactly — this is what forces
#                      a keyframe every 6 seconds, aligned with segment
#                      boundaries, so the player can switch tracks here.
#   -sc_threshold 0    Disables scene-change-triggered extra keyframes,
#                      which would otherwise break exact keyframe alignment
#                      across renditions (different renditions might insert
#                      scene-change keyframes at different points otherwise).
#   -hls_time 6        Target segment duration in seconds (2-10s is typical;
#                      Netflix/YouTube commonly use 2-6s; shorter segments
#                      = faster ABR reaction but more HTTP request overhead).

# In a real pipeline, this command is repeated per rendition (240p, 480p,
# 720p, 1080p, 2160p) — often parallelized across a transcoding farm, then
# a master.m3u8 is generated referencing all the resulting media playlists.
```

### Client-Side ABR Pseudocode (Throughput + Buffer Hybrid)

```java
public class AbrDecisionEngine {

    private static final double SAFETY_MARGIN = 0.85; // don't fully commit bandwidth
    private static final double BUFFER_LOW_WATERMARK_SEC = 10.0;
    private static final double BUFFER_HIGH_WATERMARK_SEC = 20.0;

    private final List<Rendition> renditions; // sorted ascending by bitrate
    private final ThroughputEstimator throughputEstimator; // EWMA over last N segments

    public Rendition selectNextRendition(double bufferOccupancySec) {
        double estimatedThroughputBps = throughputEstimator.getEstimate();
        double safeThroughput = estimatedThroughputBps * SAFETY_MARGIN;

        // Throughput-based candidate: highest rendition we can sustain.
        Rendition throughputCandidate = renditions.stream()
            .filter(r -> r.getBitrateBps() <= safeThroughput)
            .max(Comparator.comparingLong(Rendition::getBitrateBps))
            .orElse(renditions.get(0)); // fall back to lowest quality

        // Buffer-based override: if buffer is critically low, force a
        // downgrade regardless of throughput reading (protect against
        // rebuffering even if the throughput estimate is stale/optimistic).
        if (bufferOccupancySec < BUFFER_LOW_WATERMARK_SEC) {
            int currentIndex = renditions.indexOf(throughputCandidate);
            int saferIndex = Math.max(0, currentIndex - 1);
            return renditions.get(saferIndex);
        }

        // If buffer is deep, allow stepping UP even on a borderline
        // throughput reading (buffer gives us a safety cushion).
        if (bufferOccupancySec > BUFFER_HIGH_WATERMARK_SEC) {
            int currentIndex = renditions.indexOf(throughputCandidate);
            int aggressiveIndex = Math.min(renditions.size() - 1, currentIndex + 1);
            if (renditions.get(aggressiveIndex).getBitrateBps() <= estimatedThroughputBps) {
                return renditions.get(aggressiveIndex);
            }
        }

        return throughputCandidate;
    }
}
```

### CDN Caching Behavior: Segments vs Manifest

```
HTTP response headers (illustrative) for a VOD segment vs the live manifest:

# Segment (immutable once written — content never changes after publish):
GET /720p_seg-047.ts HTTP/1.1
  → Cache-Control: public, max-age=31536000, immutable
  → CDN edge cache HIT ratio for VOD segments: typically >95% for popular
    content, since the same bytes serve every viewer of that title/quality
  → This is why segments dominate total egress bytes but are CHEAP to
    serve — one origin fetch can satisfy millions of edge cache hits.

# Master/media manifest for a LIVE stream (mutable — new segments append):
GET /live/720p.m3u8 HTTP/1.1
  → Cache-Control: max-age=2, must-revalidate
  → Must be revalidated frequently because a live media playlist is
    actively being appended to (#EXT-X-MEDIA-SEQUENCE increases, new
    #EXTINF lines added) as new segments are encoded in near-real-time.
  → For VOD (#EXT-X-PLAYLIST-TYPE:VOD), the manifest is static/complete
    once written (has #EXT-X-ENDLIST) and can be cached aggressively too.

Real-world numbers:
  - A 2-hour 1080p movie at 6 Mbps average: ~5.4 GB total egress per
    full-quality view. At CDN edge, this is served almost entirely from
    cache after the first viewer in a region "warms" the cache.
  - Origin-to-CDN egress cost dominates for LONG-TAIL content (rarely
    watched titles that don't stay warm in edge cache) — this is a key
    reason platforms invest in predictive cache pre-warming for new
    releases and popular titles ahead of expected demand spikes.
  - Segment duration trade-off: 2-second segments give ABR ~3x faster
    reaction time vs 6-second segments, but for a 2-hour movie that's
    ~3600 HTTP requests instead of ~1200 — more request overhead, more
    manifest lines, marginally worse CDN cache efficiency (smaller,
    more numerous cache objects) in exchange for smoother quality
    adaptation under volatile network conditions.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design the video delivery pipeline for a streaming platform like YouTube — specifically, how does a viewer's app decide what quality to play, and how does the system handle someone's WiFi suddenly getting worse mid-video without the video just freezing?"

**You (architect answer):**

> "The core design decision is to precompute multiple quality renditions of every video ahead of time — an encoding ladder, say 240p at 500kbps up through 4K at 25Mbps — and chop each rendition into short, independently-decodable segments, typically 2 to 6 seconds each, with keyframes forced at exactly the same timestamps across every rendition. That keyframe alignment is what makes mid-stream quality switching possible at all: the player can only switch bitrate at a segment boundary, because video compression encodes frames relative to a keyframe, so you can't cleanly splice a mid-GOP frame from one bitrate into a stream that was playing a different bitrate.
>
> The server side just needs to publish two levels of manifest — a master playlist listing the available renditions with their bitrates and resolutions, and per-rendition media playlists listing the actual segment URLs. All the smart decision-making happens client-side. The player continuously measures two signals: recent segment download throughput, and current buffer occupancy — how many seconds of already-downloaded video it has queued before playback. A pure throughput-based approach picks the highest rendition whose bitrate fits within, say, 85% of measured throughput as a safety margin, but that alone can oscillate badly on bursty networks. So in practice I'd combine it with buffer occupancy: if the buffer is deep, tolerate a more aggressive quality choice even on a borderline throughput reading, but if the buffer drops below some low watermark — say 10 seconds — force a downgrade immediately regardless of what the throughput estimate says, because protecting against a hard rebuffer is more important than maximizing resolution.
>
> On the CDN side, the segments themselves are the overwhelming majority of bytes served, and they're perfectly cacheable — once encoded, a segment's bytes never change, so `Cache-Control: immutable` lets the CDN edge serve nearly every request from cache after the first viewer in a region. The manifest is the only piece that needs freshness — trivial for VOD content since it's static once fully encoded, but for a live stream, the media playlist is actively being appended to, so it needs a short cache TTL, maybe 1-2 seconds, and clients poll it to discover new segments.
>
> One operational concern I'd flag: the transcoding step is the expensive, latency-sensitive part of the pipeline, not the delivery — fanning one uploaded video out to 5-6 renditions in parallel on a transcoding farm can take longer than the video's own runtime for high resolutions, so for user-generated content platforms specifically, I'd prioritize getting a lower rendition (say 480p) available fast so the video is watchable almost immediately, then backfill higher renditions asynchronously and update the master manifest once they're ready — rather than blocking initial availability on the full ladder finishing."

---

## PART 5 — DECISION FRAMEWORK

### HLS/ABR vs Alternative Video Delivery Approaches

| Approach | How It Works | Consistency/Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **HLS/DASH Adaptive Bitrate** | Pre-encoded ladder, segmented, client picks bitrate per segment | Eventually "smooth" — quality varies but playback rarely stalls | Segment duration (2-10s) sets minimum ABR reaction granularity | Medium-High (encoding pipeline + CDN + player logic) | Sudden severe bandwidth cliffs still cause rebuffers if buffer depletes faster than ABR reacts |
| **Single fixed-bitrate progressive download** | One file, one quality, plain HTTP range requests | Simple, but no adaptation — buffers hard on slow networks | N/A (no switching) | Low | Any sustained bandwidth below the fixed bitrate causes stalls with no recovery option |
| **WebRTC / low-latency live streaming** | Peer-to-peer or SFU-relayed real-time media, sub-second latency | Prioritizes latency over buffering headroom | <1s typical | High (real-time infra, NAT traversal, congestion control) | Not designed for VOD/CDN caching; harder to scale to millions of simultaneous viewers cheaply |
| **CMAF (Common Media Application Format)** | Single segment format usable by both HLS and DASH manifests | Same ABR mechanics, but avoids duplicate encoding/storage for two manifest formats | Same as HLS/DASH | Medium (encoder/packager complexity, less client complexity) | Requires modern player/encoder support; older HLS-only or DASH-only clients need format-specific segments |

### When HLS/ABR Is the Right Choice

```
Use HLS/Adaptive Bitrate streaming when:
  ✓ You're serving VOD or live video to a broad audience with highly
    variable network conditions (mobile, home WiFi, varying ISPs)
  ✓ Smooth, stall-free playback matters more than guaranteeing the
    absolute highest fixed quality at all times
  ✓ You want to leverage CDN edge caching heavily — segments are
    static, cacheable, and reusable across all viewers of that title
  ✓ You need broad device/browser compatibility (native HLS support on
    iOS/Safari; DASH/hls.js polyfills elsewhere)

Skip HLS/ABR when:
  ✗ You need true sub-second interactive latency (video calls, live
    auctions, interactive gaming streams) — use WebRTC instead
  ✗ The content library is tiny and quality requirements are fixed
    (e.g. an internal tool serving one known-bandwidth environment) —
    a single progressive-download file may be simpler to operate
  ✗ You're building a live low-latency broadcast (sports betting, live
    trading data overlays) where even a 6-second segment-based delay
    is unacceptable — consider low-latency HLS/DASH extensions (LL-HLS,
    chunked CMAF) or WebRTC-based delivery instead
```

---

## QUICK REFERENCE CARD

```
MANIFEST HIERARCHY:
  master.m3u8  → lists variant streams (#EXT-X-STREAM-INF: BANDWIDTH, RESOLUTION)
  {variant}.m3u8 → lists segments (#EXTINF: duration, segment URL)
  #EXT-X-ENDLIST → marks a VOD playlist as complete (no live appends)

ENCODING LADDER (typical):
  240p / 500kbps    480p / 1.5Mbps   720p / 3Mbps
  1080p / 6Mbps     2160p(4K) / 25Mbps

KEYFRAME ALIGNMENT (FFmpeg):
  -g <GOP_frames> -keyint_min <same> -sc_threshold 0
  GOP size (frames) / fps == segment duration (seconds) — must match
  -hls_time <segment_duration_seconds>

ABR DECISION SIGNALS:
  throughput-based: pick highest bitrate <= (measured_throughput * 0.85)
  buffer-based: bitrate choice as function of buffer occupancy (secs)
  hybrid: buffer low watermark → force downgrade; buffer high watermark
          → allow aggressive upgrade

SWITCH RULE:
  Bitrate can only change AT a segment boundary (keyframe-aligned)

CDN CACHING:
  Segments: Cache-Control: immutable, long max-age (static bytes)
  Live manifest: short max-age (2s), must-revalidate (actively appended)
  VOD manifest: cacheable once #EXT-X-ENDLIST is present
```
