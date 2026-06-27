# Interview Approach - Video Streaming System LLD

## 1. Start With Core Separation
"Do not mix upload processing concerns with playback latency concerns."

## 2. Define Main Paths
- Upload path: heavy, async, CPU-intensive
- Metadata path: transactional and queryable
- Playback path: read-heavy, globally distributed

## 3. Walk Through Happy Path
1. Upload raw video.
2. Transcode to multiple renditions.
3. Store metadata and publish READY state.
4. Stream through CDN with adaptive bitrate.

## 4. Walk Through Failure Path
1. One rendition fails.
2. Retry processing or publish limited set.
3. Keep video PROCESSING/FAILED until minimum set is ready.

## 5. Mention Scale Levers
- Object storage for media
- CDN for segments/manifests
- Separate metadata DB from analytics/event store
- Async counters for views and engagement

## 6. Trade-offs
- Exact counters vs cheap eventually consistent counters
- Fast publish vs full moderation workflow
- Personalized ranking vs serving latency

## 7. Close Strongly
"Streaming quality depends on pipeline correctness before it depends on player performance."
