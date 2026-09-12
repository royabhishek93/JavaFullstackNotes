# Caching Deep Dive — LinkedIn Post

## Post Text (copy-paste ready)

50,000 users. One expired cache key. One database crash.

- A cache stampede happens when a popular key expires under load — every request misses at once and all of them hammer the DB simultaneously
- Fix: TTL jitter (270-330s instead of a flat 300s), a mutex lock so only 1 thread refreshes, or Caffeine's refreshAfterWrite for zero-miss hot data
- Cache penetration is the quiet killer: attackers spam non-existent IDs, every one is a guaranteed miss, every one hits your DB — fix with cached nulls or a Bloom filter
- 4 patterns, 4 jobs: cache-aside (catalogs), write-through (inventory, must be fresh), write-behind (counters, loss-tolerant), refresh-ahead (your hottest items)
- With good caching, your DB should handle just 1-5% of total traffic — if it's higher, something's wrong

Swipe → to see all 4 caching patterns and the exact fix for cache stampede + cache penetration.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
One expired cache key + 50,000 concurrent requests = database down. Here's how to prevent a cache stampede 👇

### Variant B — Long (400–600 chars)
Caching feels simple until the exact moment a popular key expires under heavy load — then every single request becomes a cache miss at once, and all of them hit your database simultaneously. That's a cache stampede, and it's taken down real production systems during flash sales. The fix isn't one trick — it's TTL jitter to spread expiry, a mutex lock so only one thread refreshes the DB, or Caffeine's refreshAfterWrite for zero-miss hot data. Add Bloom filters to stop attackers from cache-penetrating with fake IDs, and your DB should handle 1-5% of total traffic, not more.

---

## Best Time to Post
Wednesday, 8:30–9:30 AM IST (mid-week technical content performs best before standups)

## Engagement Hook
"Has a cache stampede ever taken down one of your production systems? What was the fix? Tell me below."
