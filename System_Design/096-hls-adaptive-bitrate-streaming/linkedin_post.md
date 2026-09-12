# HLS & Adaptive Bitrate Streaming — LinkedIn Post

## Post Text (copy-paste ready)

WiFi drops from 50Mbps to 2Mbps mid-episode. Netflix doesn't freeze. Here's why.

- The trick: pre-encode the SAME video at multiple bitrates (240p to 4K), chop each into 2-6 second segments with keyframes aligned at IDENTICAL timestamps across every rendition
- Keyframe alignment is what makes switching possible — you can't jump from a keyframe in one bitrate to a mid-group frame in another, so switches only happen at segment boundaries
- ABR algorithms blend 2 signals: throughput (pick the highest bitrate that fits ~85% of recent download speed) and buffer occupancy (force a downgrade if buffer drops below ~10s, regardless of throughput)
- Real trap: a buffer can drain to rebuffer BEFORE a throughput-triggered downswitch takes effect — this is why buffer-based logic exists alongside throughput-based logic
- Segments get `Cache-Control: immutable` (95%+ CDN cache hit rate) — live manifests get a 1-2s TTL because they're actively being appended to with new segments

Swipe → to see the full manifest hierarchy (master → media playlists → segments) and the exact FFmpeg flags that force keyframe alignment.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
WiFi drops from 50Mbps to 2Mbps, Netflix doesn't freeze. Here's the encoding trick that makes seamless quality switching possible 👇

### Variant B — Long (400–600 chars)
Adaptive bitrate streaming works because every quality rendition of a video is encoded with keyframes at identical timestamps — the player can only switch quality at those aligned segment boundaries, never mid-segment. Production ABR algorithms blend throughput measurement with buffer occupancy: deep buffer means be aggressive, shallow buffer means force a downgrade immediately regardless of throughput. Get this wrong and you either rebuffer (buffer drains before the switch takes effect) or "flap" between qualities every few seconds.

---

## Best Time to Post
Wednesday, 9:00–10:00 AM IST (media/streaming infrastructure content performs well mid-week)

## Engagement Hook
"Have you ever debugged a video rebuffering issue in production? Was it a throughput problem or a buffer-logic problem?"
