# Cache Eviction — LRU, LFU, TTL & Redis Policies — LinkedIn Post

## Post Text (copy-paste ready)

Redis at 80% memory. Evictions spiking every peak hour. Your hit rate falls off a cliff — because you picked the wrong one of Redis's 8 eviction policies.

- The default policy, noeviction, doesn't evict anything — it REJECTS every write once memory is full and your clients start getting OOM errors
- LRU gets skewed traffic wrong: a celebrity profile idle for 2 minutes (10,000 accesses/hr) gets evicted before a one-time report accessed 1 minute ago — LRU only sees the timestamp, not the value
- LFU fixes this with an 8-bit logarithmic counter (0-255) that decays over time — celebrity stays near 255, one-time report sits at 1, so the report gets evicted first, correctly
- TTL = 0 doesn't mean "expire now" — it means no expiry at all; keys you truly never want evicted need volatile-lru + deliberately NO TTL set, not allkeys-lru
- Any nonzero evicted_keys in production (outside a deliberate volatile-ttl + leaderboard-safety setup) means your cache is undersized for peak load — it's a signal, not a steady state

Swipe to see: the celebrity vs one-time-key trap diagrammed, all 8 Redis maxmemory-policy options compared, and the exact decision tree for picking LRU vs LFU vs TTL vs noeviction.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Redis gives you 8 eviction policies. Pick wrong and it evicts your celebrity-profile cache before a key nobody's touched twice 👇

### Variant B — Long (400–600 chars)
Redis at 80% memory, evictions spiking — most teams stay on allkeys-lru and never question it. But LRU only looks at recency: a celebrity profile idle for 2 minutes can get evicted before a one-time key accessed 1 minute ago, even though the celebrity gets 10,000 hits/hour. LFU fixes this with a decaying frequency counter. Add volatile-ttl for expiring rate-limit counters and volatile-lru + no TTL for source-of-truth data, and you've got all 8 Redis maxmemory policies mapped to real access patterns — exactly what a system design interviewer is listening for.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (technical deep-dives on caching internals perform best early-to-mid week when engineers are actively debugging or planning sprints)

## Engagement Hook
"Have you ever seen your cache evict the WRONG key during a traffic spike? What policy were you running — and what did you switch to?"
