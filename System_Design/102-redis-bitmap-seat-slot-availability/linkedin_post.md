# Redis Bitmaps: Seat/Slot Availability — LinkedIn Post

## Post Text (copy-paste ready)

10,000 stadium seats as 10,000 Redis keys = ~900KB. As 1 bitmap = 1,250 bytes. A ~700x difference.

- A Redis Bitmap is just a String with individual bits addressable — `SETBIT seats:section-A 4821 1` books a seat with zero per-entry overhead
- `BITCOUNT` gives total booked seats across the whole section in one command; `BITPOS` finds the first available seat — both in microseconds via hardware popcount
- The real power: `BITOP AND` across 3 separate bitmaps (available, wheelchair-accessible, aisle) finds a seat matching ALL 3 conditions instantly — no composite DB index needed
- The trap: bitmaps only work for DENSE, BOUNDED ID spaces. Track a sparse 50M-user-ID space with raw IDs as bit offsets, and Redis allocates memory covering every unused gap up to your highest ID — 6.25MB for one key even if only 3 users ever log in
- For sparse/unbounded ID membership tracking, use a Bloom filter instead; for cardinality estimates only, use HyperLogLog

Swipe → to see the exact memory math (bitmap vs separate keys vs hash) and when to reach for a Bloom filter instead.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
10,000 seats as separate Redis keys: ~900KB. As one bitmap: 1.25KB. Here's the ~700x memory trick 👇

### Variant B — Long (400–600 chars)
A Redis Bitmap stores one bit per item with near-zero per-entry overhead — 10,000 seats fit in 1,250 bytes instead of ~900KB as separate keys. Aggregate operations like BITCOUNT and BITPOS run in microseconds via hardware-optimized popcount, and BITOP AND across multiple attribute bitmaps (available + wheelchair-accessible + aisle) finds a matching seat instantly. The trap: bitmaps only work for dense, bounded ID spaces — apply the same pattern to a sparse 50-million-user-ID space and Redis allocates memory covering every unused gap. Use a Bloom filter instead for that case.

---

## Best Time to Post
Thursday, 9:00–10:00 AM IST (Redis data-structure deep-dives perform well mid-week)

## Engagement Hook
"Have you used Redis bitmaps for anything beyond seat maps — attendance tracking, feature rollout flags, something else?"
