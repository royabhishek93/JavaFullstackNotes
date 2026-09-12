# Chunked Upload & Multipart Upload — LinkedIn Post

## Post Text (copy-paste ready)

Your user is at 99% upload progress. Connection drops. They lose all 990MB and start over.

- Single HTTP request for a 1GB file = one dropped packet away from a full restart
- On mobile (4G ~6.25MB/s), a 1GB upload takes 160s — the odds of zero interruptions are low
- Naive server buffering: 10 concurrent uploads = 10GB RAM = OOM crash on an 8GB box
- AWS ALB's 60s default timeout kills your 170s upload before your code even gets a chance
- Fix: split into 10MB chunks, upload in parallel via presigned URLs — S3 handles bandwidth, your servers handle zero bytes

Swipe → to see the full multipart upload flow, the presigned-URL anti-pattern most teams still ship, and the exact AWS size thresholds interviewers ask about.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
1M uploads/day × 2GB through your servers = 23TB/day of bandwidth you don't need. Here's the multipart upload fix. 👇

### Variant B — Long (400–600 chars)
A 2GB video upload routed through your own API servers instead of directly to S3 means: double egress cost, your fleet's bandwidth as the bottleneck, and RAM eaten by upload buffers. At 1M uploads/day of 2GB each, that's 23TB/day through servers that should never touch a single video byte. The fix is S3 Multipart Upload with presigned URLs: your backend only hands out signed part URLs and ETags — the client uploads directly to S3, in parallel, resumable from any failed chunk. Files under 5MB skip this entirely; files over 5GB require it (S3's single-PUT cap). This is the exact pattern behind Drive, Dropbox, and every OTT platform's 50GB+ content ingestion.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (before the Indian tech workday starts, catches commute scrollers)

## Engagement Hook
What's the worst "restart the whole upload from 0%" bug you've personally hit or shipped — and what finally fixed it?
