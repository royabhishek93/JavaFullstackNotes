# Virtual Waiting Room: Redis Sorted Set Drip-Feed — LinkedIn Post

## Post Text (copy-paste ready)

500,000 people hit "Buy" in the same second. Your DB pool handles 2,000. Here's how to say yes to everyone anyway.

- Rate limiting rejects excess traffic unfairly — the 499,700th click is just as legitimate as the first, it just needs to wait its turn
- The fix: a Redis Sorted Set as a waiting room — `ZADD waiting_room <arrivalTimestamp> <queueId>` is O(log N), so even 500K simultaneous joins are trivial for Redis (would flatten a relational DB)
- A background admission worker pops the oldest N entries every few seconds (`ZRANGE` + `ZREM`, wrapped in Lua for atomicity), admitting exactly enough to top back up to your concurrency cap
- The trap: abandoned admitted slots. A user gets admitted, walks away, and their slot sits wasted for the full TTL while thousands behind them wait unnecessarily — fix with keyspace-notification reclaim or a periodic sweep job
- Users poll `ZRANK` to see their live position — same UX as watching your position in a phone hold queue

Swipe → to see the full join → wait → admit → book flow and the exact math for how fast a 500K queue drains.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
500K people hit "Buy" at once. Your DB handles 2K. Here's the Redis pattern that lets everyone in, fairly, without a meltdown 👇

### Variant B — Long (400–600 chars)
Rate limiting rejects excess traffic — unfair when a legitimate customer just happened to click a second later. A virtual waiting room instead admits everyone eventually, FIFO, using a Redis Sorted Set: joining is O(log N) so even 500K simultaneous requests are trivial, and a background worker drip-feeds admissions at whatever rate your backend can sustain. The trap: abandoned admitted slots sitting idle for their full TTL while thousands wait behind them — you need an active reclaim strategy, not just a passive expiry.

---

## Best Time to Post
Wednesday, 9:00–10:00 AM IST (flash-sale/high-traffic infrastructure content performs well mid-week)

## Engagement Hook
"Has your platform ever had to build admission control for a scheduled traffic spike — a ticket drop, a flash sale? What did you use?"
