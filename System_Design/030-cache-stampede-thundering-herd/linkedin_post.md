# Cache Stampede & Thundering Herd — LinkedIn Post

## Post Text (copy-paste ready)

Your cache expired at midnight. 100,000 users refreshed. Your DB got 100,000 identical queries in 1 second.

- A cache miss at 2 AM with 10 users? Harmless.
- A cache miss at peak traffic with 50K concurrent users? Fatal — DB CPU hits 100%, connection pool exhausts, everyone times out.
- Mutex lock: 1 DB query, but 49,999 requests eat +100ms latency.
- Stale-while-revalidate: 1 DB query per cycle, zero added latency, data up to 5 min stale.
- Probabilistic early expiry: refreshes before expiry using randomness — no stampede moment ever arrives.

Reddit went down from a trending-post cache expiry storm. Facebook wrote a whole paper on thundering herd at Memcached scale.

Swipe → to see all 3 prevention strategies, the exact traps engineers hit (unowned lock release, synced TTLs across keys, picking the wrong strategy for your staleness tolerance), and the decision tree to pick the right one.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Your cache protection just killed your DB. 100K identical queries, 1 second. Here's how mutex locks, SWR & PER actually stop it. 🎥👇

### Variant B — Long (400–600 chars)
Cache stampede: the failure mode where your OWN caching layer takes down your database. TTL hits zero, thousands of concurrent requests all miss at once, all fire the same expensive query at the DB simultaneously. Reddit's been hit by it. Facebook published a paper on it at Memcached scale. In this breakdown: mutex locks (SET NX EX + Lua-script release), stale-while-revalidate (two-TTL, zero added latency), probabilistic early expiry (spreads recomputes before expiry), pre-warming for scheduled sales, and TTL jitter to stop synchronized key expiry. Plus the exact traps: lock TTL omission, releasing a lock you don't own, and matching the wrong strategy to your staleness tolerance.

---

## Best Time to Post
Tuesday or Wednesday, 9:00–10:30 AM IST (Indian tech audience scrolling before standups/first meetings)

## Engagement Hook
Which one have you actually used in production — mutex lock, stale-while-revalidate, or probabilistic early expiry? Or did you find out about cache stampedes the hard way (an outage)?
