# Negative Caching & Cache Miss Storm — LinkedIn Post

## Post Text (copy-paste ready)

A bot sent 1,000,000 requests for a URL code that never existed — and took the DB down. Here's the 90-byte fix.

- Your cache only stores things that EXIST. A "not found" answer is never cached by default — every repeat miss on the same fake key goes straight to the DB, every time.
- 1M requests for a random short code = 1M DB queries at 100% CPU, while your real users start timing out.
- Fix: cache the "not found" answer itself. `redis.setex(key, 60, "__NULL__")` — next request for that key returns in <1ms, DB sees zero more queries.
- Stack 3 layers for real protection: Bloom filter (99% of fake keys blocked before cache/DB) → negative cache (catches the 1% false positives) → API gateway rate limit (per-key cap).
- The #1 bug teams ship: forgetting to invalidate the negative cache on write. User registers "user123" → cache still says NULL → user thinks signup failed → support ticket.

Swipe → to see: the 3-layer defense architecture, the TTL rules by use case, and the exact interview answer for "DB is at 100% CPU from a bot attack, how do you fix it?"

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A bot sent 1M requests for a fake URL code and took the DB down. The 90-byte fix every backend engineer should know 👇

### Variant B — Long (400–600 chars)
Your cache has a blind spot: it only remembers things that exist. So when a bot (or a bug) hammers your API with IDs that DON'T exist — random short codes, deleted product IDs, fake usernames — every single request bypasses the cache and hits your DB. At 1M requests, that's 1M DB queries for nothing, and real users start timing out.

The fix is negative caching: store the "not found" answer with a short TTL. Add a Bloom filter in front and rate limiting behind, and DB load from non-existent keys drops to near zero. One line of code, one architectural gap closed.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (commute scroll time for Indian tech audience) or 7:30–8:30 PM IST (post-work wind-down)

## Engagement Hook
Have you ever shipped a cache that forgot to invalidate on write — and had a user think their signup failed? Drop your incident story below.
