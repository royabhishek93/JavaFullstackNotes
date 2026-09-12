# Content-Addressable Storage — LinkedIn Post

## Post Text (copy-paste ready)

You edit page 5 of a 1GB file. Dropbox uploads 4MB, not 1GB. Here's the trick.

- Content-addressable storage names files by the HASH of their content (SHA-256), not by filename — same content = same hash = stored exactly once
- 3 users upload the "same" photo under 3 different filenames → stored once, not three times — 66% storage saved in that example
- Chunked CAS goes further: split files into 4MB blocks, hash each independently. Edit one page of a 1GB file → only 1 chunk (4MB) needs re-uploading, the other 255 are untouched and already stored
- The trap engineers forget: garbage collection. You can't delete a blob just because one user deleted their file — reference counting tracks how many users still point at it, and only a count of zero triggers actual deletion
- This exact idea powers Google Drive/Dropbox dedup, every Git object, every Docker image layer, and IPFS

Swipe → to see the reference-counting schema and exactly how chunk-level hashing turns a full re-upload into a 4MB one.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Edit 1 page of a 1GB file, Dropbox uploads 4MB not 1GB. Here's how content-addressable storage makes dedup automatic 👇

### Variant B — Long (400–600 chars)
Content-addressable storage names files by the hash of their bytes instead of their filename — so identical content is stored exactly once, no matter how many users upload it under different names. Chunking takes it further: split files into small blocks, hash each independently, and a tiny edit only invalidates the one chunk that changed. The trap: you can't delete a blob just because one user deletes their file — reference counting tracks how many other users still need it, exactly like Git's own garbage collector.

---

## Best Time to Post
Thursday, 9:00–10:00 AM IST (storage/infrastructure deep-dives perform well mid-week)

## Engagement Hook
"Where have you seen deduplication save real storage costs in a system you've built?"
