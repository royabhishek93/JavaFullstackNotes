# MED Q01 - How Adaptive Bitrate Streaming Works

## Scenario
User network speed changes during playback.

## Explanation
- Player first fetches manifest (HLS/DASH).
- Manifest lists multiple renditions.
- Player switches segment quality based on current bandwidth and buffer health.
- User keeps watching with minimal buffering.

## Interview One-Liner
Adaptive bitrate is a client playback strategy enabled by server-side transcoding into multiple renditions.
