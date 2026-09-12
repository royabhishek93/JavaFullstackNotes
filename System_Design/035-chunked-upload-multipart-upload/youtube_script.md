# Chunked Upload & Multipart Upload — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 35

## HOOK (0:00–0:30)

Picture this. You're on a train, uploading a 1GB vacation video to your cloud storage app. You're at 99%. Ninety-nine percent. And then — the connection drops for half a second as the train goes through a tunnel.

What happens? If that app was built naively — with a single HTTP request for the whole file — you lose everything. All 990 megabytes. Gone. You start again from zero.

And here's the number that should scare you: on a mobile connection, the probability of a stable, uninterrupted 160-second connection is LOW. So this isn't an edge case — it's the default experience.

[Screen cue: Progress bar animation stuck at 99%, then snapping back to 0% with a red "X"]

Today we're breaking down chunked upload and multipart upload — the pattern behind every large file upload system you've ever used, from Google Drive to Netflix's content pipeline.

## THE PROBLEM (0:30–2:00)

Let's think about what actually happens when you upload a 1 gigabyte file as ONE single HTTP request.

Problem one: reliability. If the network drops at byte 1,060,000,000 — basically 990MB in — the server just discards everything it received. There's no partial credit. The client has to start from byte zero. Full retry.

Problem two: mobile speed math. A typical 4G LTE connection tops out around 50 megabits per second, which is about 6.25 megabytes per second. Do the division: 1GB divided by 6.25 MB/s is 160 seconds. That's almost three minutes where absolutely nothing can go wrong on a mobile network. Realistically, you're looking at three to five retries before one of these uploads actually succeeds.

Problem three: server memory. Think about it this way — if your server naively buffers the entire file in RAM before writing it to disk, and you've got 10 people uploading simultaneously, that's 10 gigabytes of RAM eaten up by file buffers alone. On an 8GB server, that's an out-of-memory crash waiting to happen.

Problem four, and this one catches people off guard: load balancer timeouts. AWS's Application Load Balancer has a default timeout of 60 seconds. At 6 megabytes per second, a 1GB upload takes about 170 seconds. So the load balancer kills the connection at the 60-second mark — regardless of whether the client and server were behaving perfectly. The upload was doomed before it even started, because of infrastructure you don't even control directly.

[Screen cue: Diagram — single arrow "Client → Server" labeled "1GB single POST", with red X marks at network drop, OOM crash, and LB timeout points along the arrow]

## THE SOLUTION (2:00–5:00)

So here's the fix: stop sending the file as one blob. Break it into small pieces — chunks — and upload them one at a time, or better, in parallel.

Now watch what happens with S3 Multipart Upload, which is Amazon's implementation of this exact pattern, and honestly the industry reference design.

Step one: initiate. Your client tells your backend "I want to upload vacation.mp4, it's 1,073,741,824 bytes, it's an mp4." Your backend calls S3's CreateMultipartUpload API. S3 responds with an UploadId — think of it as a session token for this specific upload. Your backend hands that back to the client, along with a plan for how to split the file.

Step two: upload the parts. With a 1GB file and 10MB chunks, that's 1,073,741,824 divided by 10,485,760 — round up — and you get 103 parts. Now here's the key move: the client doesn't upload these one after another. It uploads them in parallel, say 5 at a time. Each part is a PUT request with a partNumber and the uploadId, and each successful part upload returns an ETag — basically a fingerprint of that chunk's content.

And here's the payoff: if part 7 fails — network blip, whatever — you retry ONLY part 7. Ten megabytes. Not the whole gigabyte.

Step three: complete. Once every part has succeeded, the client sends the full list of part numbers and ETags back to your backend. Your backend calls S3's CompleteMultipartUpload with that list, and S3 stitches all 103 parts together into the final object. Done. vacation.mp4 now exists as one file in S3.

Now let's talk resumability, because uploads don't just fail on the network — they fail because your phone falls asleep, or you close the app. Say a user is at 60% — parts 1 through 60 done — and the phone sleeps. Without resumability, that's a restart from zero. With it, the client had been tracking progress in localStorage: the uploadId, the list of completed parts, and their ETags. On resume, it checks localStorage, then calls S3's ListParts API to confirm the server-side state agrees, and then just continues from part 61. Only about 400MB gets re-uploaded, not the full gig.

[Screen cue: Live diagram — file split into 103 numbered blocks, 5 blocks highlighted green flowing in parallel into an S3 cylinder icon, one block (7) shown red with a retry loop arrow back onto it only]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Let's go through the traps, because this is where interviews — and production incidents — actually live.

Trap one: routing everything through your own server. This is the classic anti-pattern. Client uploads 1GB to YOUR server, then your server re-uploads that same 1GB to S3. Two problems stack up here. First, your server becomes the bandwidth bottleneck — its upload speed to S3 now gates every user's experience. Second, you're paying for egress TWICE: once client-to-server, once server-to-S3. And your server's RAM is now holding every in-flight upload's buffer.

The fix is presigned URLs. Your backend still initiates the multipart upload and asks S3 to generate signed URLs — one per part, each valid for an hour typically. Your backend hands those URLs to the client, and the client uploads DIRECTLY to S3. Your servers see zero video bytes — only metadata like the uploadId and ETags. S3 is built to handle massive bandwidth; your API fleet is not.

Trap two: forgetting to clean up abandoned uploads. Here's a sneaky one — S3 stores incomplete multipart uploads indefinitely by default. If a user starts a 1GB upload and abandons it at part 3, those 3 parts just sit there... forever... and you pay storage cost for them forever. The fix is a lifecycle policy: AbortIncompleteMultipartUpload after, say, 7 days. One JSON rule. Miss this and your storage bill quietly creeps up from thousands of abandoned partial uploads.

Trap three: not knowing AWS's actual size thresholds, which interviewers absolutely will probe. Under 5MB — just do a single PUT, multipart is overkill. Between 5MB and 5GB — multipart is recommended but not mandatory. Above 5GB — multipart is REQUIRED, because a single PUT request in S3 caps out at 5GB. If you say "single request" for a 50GB file in an interview, that's an instant red flag — it's not even possible with a single PUT.

Trap four: sequential instead of parallel part uploads. If you upload 103 parts one at a time, you get zero benefit over a single request except resumability. The real speed win comes from parallelism. Five parallel threads at 100 megabits per second each gives you 500 megabits per second of effective throughput. A 2GB file at 500 Mbps takes about 32 seconds — compare that to 160 seconds sequential. That's a 5x speedup just from doing chunks concurrently instead of one after another.

[Screen cue: Split-screen comparison table — "Sequential: 1 chunk at a time, 160s" vs "Parallel: 5 chunks at once, 32s", with a stopwatch animation on each side]

## REAL WORLD (8:00–9:30)

Let's ground this in scale. Think about an OTT platform like Hotstar during IPL season, or a platform like Netflix — content creators are uploading 50GB-plus raw 4K video files. At that size, S3 multipart isn't a nice-to-have, it's mandatory — you literally cannot do a single PUT past 5GB. And with 5 parallel threads at 100 Mbps each, that's 500 Mbps effective — versus 100 Mbps if you naively went sequential. If one chunk fails on a 50GB upload, you retry 10 megabytes, not 50 gigabytes.

Now zoom into the bandwidth math for a consumer app doing 1 million daily uploads of 2GB each — this is the exact number from the architect-level interview answer for this pattern. If you routed all of that through your own API servers, you'd need 23 terabytes of bandwidth PER DAY flowing through your fleet. Twenty-three terabytes. That's not a "provision more servers" problem, that's a "your architecture is fundamentally wrong" problem. With presigned URLs, that traffic goes straight to S3, and your API servers only ever see small JSON payloads — uploadIds and ETags.

And after the upload completes in a video pipeline, the pattern continues: a VideoUploaded event goes onto Kafka, a transcoding worker picks it up, runs FFmpeg to produce HLS segments at 480p, 720p, and 1080p, stores those back to S3, and CloudFront serves them globally. The multipart upload is just the front door — but getting that front door wrong at scale means paying for double egress and bottlenecking your entire fleet on file bytes it never needed to touch.

[Screen cue: Split-screen — left "OTT Platform" logo-style text with "50GB uploads, 500Mbps parallel", right "1M daily uploads × 2GB" with "23TB/day through servers" crossed out in red, replaced by "23TB/day direct to S3" in green]

## OUTRO + NEXT EPISODE (9:30–10:00)

So here's the one-liner to remember: for anything over 100MB, use multipart upload with presigned URLs — your servers never touch the bytes, chunks upload in parallel, and a dropped connection retries one chunk, not the whole file.

If this saved you from an awkward moment in a system design interview, hit subscribe — we're going through one system design concept every single episode.

Next up, Episode 36: we're going to talk about how databases survive a crash mid-write without losing your data — the Write-Ahead Log, and how it makes crash recovery possible. If multipart upload is about surviving a bad network, WAL is about surviving a bad power outage. See you there.

[Screen cue: End card — "Episode 36: Write-Ahead Log & Crash Recovery" with subscribe button animation]
