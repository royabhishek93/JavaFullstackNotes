# Chunked Upload and Multipart Upload
### Why You Don't Upload a 1GB Video in One HTTP Request

---

## PART 1 — THE STUDENT CONVERSATION

**What happens if you upload a 1GB file in one HTTP request and your connection drops at 99%?**

You start over. From zero. The 990MB you already uploaded is gone. On a mobile connection in an elevator, this happens constantly.

**Chunked upload breaks the file into small pieces** (e.g., 10MB chunks) and uploads them one by one. If the connection drops at 99%, you only re-upload the last chunk (10MB), not the whole 1GB.

This is also necessary for parallel uploads: instead of uploading 1GB sequentially (which saturates one connection and is slow), you can upload 10 chunks simultaneously over 10 connections — potentially 10x faster.

**S3 Multipart Upload** is Amazon's implementation of this pattern. AWS requires it for files over 5GB, and recommends it for files over 100MB.

---

## PART 2 — THE SINGLE REQUEST FAILURE MODES

```
Single HTTP request for 1GB upload:
────────────────────────────────────────────────────────────────────

  Client → Server: POST /upload  (body: 1,073,741,824 bytes)

  Problems:
  1. Network drops at byte 1,060,000,000 (990MB sent):
     Server: connection reset → discards ALL received bytes
     Client: starts from byte 0 again. Full retry.

  2. Mobile network (4G LTE max: ~50 Mbps = 6.25 MB/s):
     1GB ÷ 6.25 MB/s = 160 seconds
     Probability of 160-second mobile connection staying stable: LOW
     → Expected retries before success: 3–5x

  3. Server memory:
     Naive server buffers entire 1GB in memory before writing to disk
     10 concurrent uploads = 10GB RAM consumed by file buffers
     → OOM crash on servers with 8GB RAM

  4. Proxy/Load balancer timeout:
     AWS ALB default: 60 seconds
     1GB at 6MB/s = 170 seconds → load balancer closes connection at 60s
     → Upload never completes regardless of client/server behavior
```

---

## PART 3 — MULTIPART UPLOAD FLOW

### S3 Multipart Upload

```
Step 1: Initiate multipart upload
────────────────────────────────────────────────────────────────────

  Client → Your Backend:
  POST /files/upload/initiate
  { filename: "vacation.mp4", size: 1073741824, content_type: "video/mp4" }

  Your Backend → S3:
  POST https://s3.amazonaws.com/bucket/vacation.mp4?uploads
  Response: { UploadId: "VXBsb2FkIElEIGZvciA2aWWpbmcncyBteS1tb3ZpZS5t..." }

  Your Backend → Client:
  { uploadId: "VXBsb2FkIElEI...", presigned_urls: [...] }

Step 2: Upload parts (in parallel)
────────────────────────────────────────────────────────────────────

  File size: 1GB = 1,073,741,824 bytes
  Chunk size: 10MB = 10,485,760 bytes
  Number of parts: ⌈1073741824 ÷ 10485760⌉ = 103 parts

  Client uploads parts 1–103 in parallel (e.g., 5 at a time):

  PUT https://s3.amazonaws.com/bucket/vacation.mp4?partNumber=1&uploadId=VXBsb2Fk...
  Body: bytes 0 – 10,485,759  (10MB)
  Response: ETag: "b54357faf0632cce46e942fa68356b38"

  PUT https://s3.amazonaws.com/bucket/vacation.mp4?partNumber=2&uploadId=VXBsb2Fk...
  Body: bytes 10,485,760 – 20,971,519  (10MB)
  Response: ETag: "a3f75f..."

  (parts 3–103 upload in parallel)

  If part 7 fails:
  Retry ONLY part 7 (10MB), not the whole file.

Step 3: Complete multipart upload
────────────────────────────────────────────────────────────────────

  Client → Your Backend: "all parts uploaded, here are the ETags"
  {
    uploadId: "VXBsb2Fk...",
    parts: [
      { partNumber: 1, ETag: "b54357..." },
      { partNumber: 2, ETag: "a3f75f..." },
      ...
      { partNumber: 103, ETag: "c8d4e2..." }
    ]
  }

  Your Backend → S3:
  POST https://s3.amazonaws.com/bucket/vacation.mp4?uploadId=VXBsb2Fk...
  Body: <CompleteMultipartUpload> XML with all parts + ETags

  S3: assembles all 103 parts into the final object.
  vacation.mp4 is now available in S3. ✓
```

---

## PART 4 — RESUMABLE UPLOADS

```
User uploads 1GB video. At 60% (600MB), phone goes to sleep.
────────────────────────────────────────────────────────────────────

  Without resumable upload: restart from 0%.
  With resumable upload: restart from part 61 (600MB mark).

  Implementation — client tracks progress:
  localStorage.setItem("upload:vacation.mp4", JSON.stringify({
    uploadId: "VXBsb2Fk...",
    completedParts: [1,2,...,60],     // parts 1-60 already uploaded
    partETags: { 1: "b54...", 2: "a3f..." ... 60: "..." }
  }));

  On resume:
  1. Check localStorage: uploadId exists, parts 1-60 done.
  2. Call S3 ListParts API: verify parts 1-60 are still valid on S3 side.
  3. Continue from part 61.
  Only re-uploads ~400MB (parts 61-103). ✓

  Abandoned upload cleanup:
  S3 stores incomplete multipart uploads indefinitely — you pay for storage!
  Set S3 Lifecycle policy to abort incomplete multipart uploads after 7 days:
  {
    "Rules": [{
      "AbortIncompleteMultipartUpload": { "DaysAfterInitiation": 7 }
    }]
  }
```

---

## PART 5 — DIRECT CLIENT UPLOAD (PRESIGNED URLS)

```
Anti-pattern (your server as proxy):
────────────────────────────────────────────────────────────────────

  Client ──1GB──► Your Server ──1GB──► S3
                     ↑
                 Your server becomes bandwidth bottleneck.
                 You pay for egress twice (client→server, server→S3).
                 Your server RAM handles all upload buffers.

Correct pattern (presigned URLs):
────────────────────────────────────────────────────────────────────

  Client → Your Server:
  "I want to upload vacation.mp4, 1GB"

  Your Server → S3:
  "Generate presigned URLs for 103 parts of uploadId VXBsb2Fk"

  S3 returns: 103 signed URLs, each valid for 1 hour

  Your Server → Client: { uploadId: ..., presigned_urls: [...103 URLs...] }

  Client ──10MB──► S3 directly (URL 1)    ← no traffic through your servers!
  Client ──10MB──► S3 directly (URL 2)
  ...
  Client ──10MB──► S3 directly (URL 103)

  Client → Your Server: "completed, ETags: [...]"
  Your Server → S3: CompleteMultipartUpload

Benefits:
  Your servers handle NO upload bytes (only metadata)
  S3 handles bandwidth directly (designed for it, much cheaper)
  Client upload speed limited only by S3 and client's ISP
```

---

## PART 6 — THE INTERVIEW CONVERSATION

**Interviewer:** "Users upload videos up to 2GB to your OTT platform. Walk me through the upload architecture."

**You (architect answer):**

> "A 2GB single HTTP upload would be terrible — any network hiccup means a full restart,
> and mobile users would rarely succeed. I'd use S3 Multipart Upload with presigned URLs.
>
> The flow: client asks our backend to initiate an upload. Our backend calls S3's
> CreateMultipartUpload API, gets an uploadId, then generates presigned URLs for each
> 10MB chunk — about 200 parts for a 2GB file. We return these to the client.
>
> The client uploads directly to S3 in parallel — 5 chunks simultaneously. This maximizes
> available bandwidth and if any chunk fails, only that chunk retries. Progress is saved
> to localStorage so the upload is resumable if the app closes.
>
> Once the client confirms all parts are uploaded (sends ETags to our backend), we call
> S3's CompleteMultipartUpload. S3 assembles the chunks into one object.
>
> Post-upload: we publish a VideoUploaded event to Kafka. A transcoding worker (FFmpeg-based)
> consumes the event, downloads the raw video from S3, produces HLS segments at 480p/720p/1080p,
> and stores them back to S3. A CloudFront distribution serves the segments to players worldwide.
>
> The presigned URL design is critical — our API servers handle zero video bytes. At 1M daily
> uploads of 2GB each, routing through our servers would require 23TB of bandwidth per day
> through our fleet. With presigned URLs, that traffic goes directly to S3."

---

## QUICK REFERENCE CARD

```
Multipart upload:
  Split file into chunks (S3 minimum: 5MB per part, max 10,000 parts)
  Upload parts in parallel
  On failure: retry only the failed part
  On completion: call CompleteMultipartUpload with all ETags

AWS requirements:
  <5MB:     single PUT (no multipart needed)
  5MB–5GB:  multipart recommended
  >5GB:     multipart REQUIRED (single PUT max is 5GB)

Presigned URL flow:
  1. Client asks backend for upload session
  2. Backend calls S3 CreateMultipartUpload → gets UploadId
  3. Backend generates N presigned PUT URLs (one per part)
  4. Client uploads parts directly to S3 (no traffic through backend)
  5. Client sends ETags to backend
  6. Backend calls S3 CompleteMultipartUpload

Resumability:
  Store { uploadId, completedParts, ETags } in localStorage/IndexedDB
  On resume: call S3 ListParts to verify already-uploaded parts
  Continue from first incomplete part

Cleanup:
  Set S3 Lifecycle policy: AbortIncompleteMultipartUpload after 7 days
  Without this: partial uploads accumulate and you pay for them indefinitely

Parallel upload speed example:
  5 parallel threads × 100 Mbps = 500 Mbps effective upload
  2GB at 500 Mbps = ~32 seconds (vs 160 seconds sequential)

Interview one-liner:
"Multipart upload splits a large file into 10MB chunks, uploads them in
parallel, and reassembles server-side. Failed chunks retry individually.
With presigned URLs, chunks go directly to S3 — your servers handle
zero video bytes. Resumable from any chunk on connection loss."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Any system with large file uploads (drive, video platform) will probe this — saying "the client uploads the file to the server" for a 50GB video is an instant red flag.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **10 — Cloud Storage (Google Drive/Dropbox)** | Users upload 5GB+ files. S3 multipart: split into 5MB chunks, upload 5 in parallel, resumable on network drop. Presigned URLs: client uploads directly to S3 — your servers handle zero file bytes. Progress bar possible by tracking which parts completed. |
| **17 — OTT Platform (Netflix/Hotstar)** | Content creators upload 50GB+ 4K raw videos. S3 multipart is mandatory for >5GB. 5 parallel threads × 100 Mbps = 500 Mbps effective upload vs 100 Mbps sequential. Failed chunk retries 10MB instead of 50GB restart. |

**Architect's one-liner for the interview:**
*"For anything over 100MB, use S3 multipart with presigned URLs — your servers never touch the bytes, chunks upload in parallel, and a dropped connection retries one chunk not the whole file."*
