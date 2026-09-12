# Cache-Aside vs Write-Through vs Write-Behind — LinkedIn Post

## Post Text (copy-paste ready)

Flipkart shows you ₹999. The real price just changed to ₹1499. That's the entire reason write-through caching exists.

- Cache-aside (lazy loading) is what most engineers write by default — but on write, always DELETE the cache key, never update it. Update-then-race-condition = permanently stale data that never self-heals
- Cache stampede is real: 10,000 concurrent requests miss the cache at the same second (cold start or TTL expiry) and all hammer the DB at once — fix with a mutex lock, pre-warming, or random jitter on your TTL
- Write-behind (write-back) gives you the fastest writes — perfect for a Zomato/Swiggy-style cart — but if Redis crashes before the batched flush hits the DB, that data is gone. Redis AOF with `appendfsync everysec` caps your worst-case loss at 1 second
- TTL is a tradeoff, not a free parameter: short TTL = fresh but hammers your DB, long TTL = safe for your DB but customers see stale prices/inventory for longer. Production pattern: long TTL as a safety net + explicit invalidation on every write
- Wallet balances (PhonePe/Paytm-style) never get write-behind — a lost or stale balance is a financial-correctness bug, not just a bad UX moment

Swipe to see: the read/write path diagrams for all three strategies, the decision tree, and the exact interview line to close with.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
₹999 vs the real ₹1499 price — why write-through caching exists, and the stampede trap that takes down your DB 👇

### Variant B — Long (400–600 chars)
Most engineers reach for "just add Redis" without picking a strategy. Cache-aside is simplest but can go stale — always invalidate on write, never update the cache directly, or you risk a race condition that never self-heals. Write-through guarantees freshness (use it for prices, inventory, wallet balances) at the cost of slower writes. Write-behind is the fastest (great for cart updates) but risks data loss on a crash — Redis AOF with appendfsync everysec caps that at 1 second. Add TTL jitter to dodge cache stampedes. Know all three cold for your next interview.

---

## Best Time to Post
Tuesday, 10:00–11:00 AM IST (technical deep-dives perform best early-to-mid week when engineers are actively scrolling before standup/sprint planning)

## Engagement Hook
"Have you ever shipped a cache bug where you updated instead of invalidated — and it silently served stale data for days? What caught it?"
