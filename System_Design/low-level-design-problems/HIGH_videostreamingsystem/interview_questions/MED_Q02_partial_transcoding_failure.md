# MED Q02 - Partial Transcoding Failure

## Scenario
1080p rendition fails, but 480p and 720p are ready.

## Options
1. Publish video with available renditions if minimum playback quality is met.
2. Retry failed rendition asynchronously.
3. Keep metadata showing limited quality support.

## Interview One-Liner
A single rendition failure does not have to block publish if the product allows degraded availability.
