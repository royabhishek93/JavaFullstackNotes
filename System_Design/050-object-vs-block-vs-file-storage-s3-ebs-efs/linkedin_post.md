# Object vs Block vs File Storage — LinkedIn Post

## Post Text (copy-paste ready)

EFS costs 13x more than S3 for the exact same gigabyte — and most engineers only find out after the AWS bill lands.

- Object storage (S3) is a postal warehouse — ship a package, get a tracking number, retrieve it whole. $0.023/GB/month, 11 nines durability, unlimited scale. Perfect for user uploads, videos, backups.
- Block storage (EBS) is the hard drive inside your laptop — attached to ONE machine, sub-millisecond random I/O, POSIX filesystem. Built for database data files, not for serving files to the internet.
- File storage (EFS/NFS) is a shared office network drive — multiple servers mount the SAME directory at the SAME time. Powerful, but $0.30/GB/month — reach for it only when you truly need a shared filesystem.
- The #1 junior mistake: storing binary files (photos, PDFs, attachments) directly in a relational database column. Backups balloon, replication crawls. Fix: S3 holds the bytes, the database holds the address.
- Real cost math: Zomato/Swiggy-style restaurant photo pipelines run tens of millions of images — serving them from S3 instead of EBS is a 4x cost difference on identical bytes, and a CDN can hit S3 directly without touching your app servers.

Swipe → to see the S3 vs EBS vs EFS comparison table and the exact decision tree for your next system design interview.

Save this. You'll need it the next time someone asks "where do you store the video files?"

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
EFS costs 13x more than S3 for the same GB. Here's when to use S3 vs EBS vs EFS — and the junior mistake that kills backups 👇

### Variant B — Long (400–600 chars)
Storage is not one thing. S3 (object) is a postal warehouse — cheap, HTTP-accessible, $0.023/GB, built for user uploads and videos. EBS (block) is your laptop's hard drive — attached to one machine, sub-millisecond I/O, built for database data files. EFS (file) is a shared network drive — multiple servers, same directory, but $0.30/GB, roughly 13x S3's price. The most common mistake: storing binary files in a relational database, which balloons backups and replication. The fix — S3 holds the bytes, the database holds the address — is the single line that separates a junior architecture from a senior one.

---

## Best Time to Post
Tuesday, 10:00–11:00 AM IST (mid-morning technical deep-dives get strong engagement before lunch scroll)

## Engagement Hook
"Have you ever seen a team store files directly in the database, only to get bitten by backup or replication pain later? What was the fix?"
