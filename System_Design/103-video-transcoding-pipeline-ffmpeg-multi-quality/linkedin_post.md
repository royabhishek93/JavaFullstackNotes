# Video Transcoding Pipeline: FFmpeg Multi-Quality Encoding — LinkedIn Post

## Post Text (copy-paste ready)

A 2-hour video, transcoded sequentially on one worker, would take over 2 hours for just the highest quality rung alone. Here's how it becomes watchable in under 15 minutes.

- Parallelize on 2 axes: across quality rungs (1080p/720p/480p/360p/240p each on their own worker) AND across time-chunks (split a 2-hour video into 10 keyframe-aligned 12-min chunks, fan out across the worker fleet)
- Up to 50 FFmpeg jobs running concurrently instead of 5 sequential multi-hour jobs — this is what turns 2+ hours into under 15 minutes
- Keyframes must align at IDENTICAL timestamps across every rendition (`-g 48 -keyint_min 48 -sc_threshold 0`) — this is what lets the player switch bitrates cleanly later
- The trap: spot-instance workers get killed mid-encode, leaving a corrupt truncated file that still "exists" on disk — validating output requires a checksum/duration check, not just file presence, or you silently bake a broken chunk into the final video
- Never synthesize a rendition ABOVE the source resolution — upscaling a 720p source to a fake 1080p rung wastes compute and looks worse than the honest source

Swipe → to see the full end-to-end pipeline and the exact FFmpeg flags that force keyframe alignment.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A 2-hour video transcoded sequentially: 2+ hours. Parallelized correctly: under 15 minutes. Here's the exact pipeline 👇

### Variant B — Long (400–600 chars)
Video transcoding pipelines parallelize on two axes to hit aggressive publish-time SLAs: across quality rungs (each rendition on its own worker) and across time-chunks (splitting long videos into keyframe-aligned pieces fanned out across a worker fleet). Every rendition needs identical keyframe timestamps for adaptive streaming to work later. The real production trap: spot-instance workers get killed mid-encode, leaving corrupt files that still "exist" on disk — you need a checksum/duration validation, not just a file-existence check, or a broken chunk silently ships.

---

## Best Time to Post
Friday, 9:00–10:00 AM IST (media infrastructure content closes out a technical week well)

## Engagement Hook
"Has a worker crash mid-transcode ever caused a corrupt video to silently ship in your pipeline? How did you catch it?"
