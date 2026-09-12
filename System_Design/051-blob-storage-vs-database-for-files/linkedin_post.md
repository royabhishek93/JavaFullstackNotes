# Blob Storage vs Database for Files — LinkedIn Post

## Post Text (copy-paste ready)

100K users × 2MB profile photos = 200GB of BLOBs in MySQL. Your backup just went from 5 minutes to 6 hours.

- Row size explosion: a normal 116-byte user row balloons to 2MB with one BLOB column — InnoDB's max row size (~65,535 bytes) can't hold it, so it overflows to off-page storage and adds extra I/O to even simple SELECTs
- Buffer pool contamination: `SELECT * FROM users LIMIT 1000` on BLOB columns loads 2GB into RAM, evicts your hot index pages, and spikes latency across your ENTIRE database from 1ms to 100ms
- Backup and replication nightmare: 200GB of BLOBs turns a 5-minute mysqldump into a 6-hour job, and every INSERT with a 2MB BLOB bloats the binary log, spiking replication lag
- No efficient HTTP serving: at 10,000 concurrent image requests, serving from MySQL burns 10,000 DB connections and 20GB of API server RAM — versus S3 + CDN, which serves images directly to the browser with zero API server involvement
- The only files that belong in a DB: guaranteed <1KB (icons, tiny thumbnails) or strictly compliance-encrypted docs under 1MB — everything else, especially anything that could exceed 100KB, goes to object storage
- Real-world scale: a Google Drive/Dropbox-style system with 10M users × 5MB average file = 50TB of BLOBs if stored in Postgres — pg_dump would take days, not minutes

Swipe → to see the update flow, the decision rule, and the exact interview answer.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
200GB of BLOBs turned a 5-min backup into 6 hours. Here's why files never belong in your database 👇

### Variant B — Long (400–600 chars)
Storing a 2MB profile photo as a BLOB in MySQL feels convenient — one table, ACID, done. In production it contaminates the buffer pool (latency spikes from 1ms to 100ms across ALL queries), bloats backups from 5 minutes to 6 hours at 200GB of BLOB data, and burns 20GB of API server RAM at just 10K concurrent image requests. The fix: store the S3 key (50 bytes) in the DB, the actual bytes in S3, and serve through a CDN — zero API server load, zero DB impact. Files under 1KB are the only real exception.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (technical deep-dives perform best early-to-mid week when engineers are actively scrolling before standups)

## Engagement Hook
"Have you ever inherited a database with file BLOBs in it? What broke first — backups, replication, or query latency?"
