# Read Replica Lag & Read-Your-Own-Writes — LinkedIn Post

## Post Text (copy-paste ready)

You post a photo. You check your own profile. It's not there. Here's why — and it's not a bug.

- Writes go to a primary, reads get spread across replicas — and replication is async by default, meaning replicas can lag 10ms to several seconds behind
- This is "read-your-own-writes": you write something, immediately read it back, and don't see it because your read hit a lagging replica
- 4 fixes, ranked by precision: read-from-primary window (simplest), sticky/monotonic routing, LSN-based routing (most precise), semi-sync replication (write-level guarantee)
- The real skill is picking the fix PER ENDPOINT: a hotel booking needs LSN routing (strictest), an order-history page is fine with a 5s primary window, a "continue watching" list needs no fix at all
- Alert thresholds that matter: >5s lag = investigate, >30s = pull the replica from the read pool entirely

Swipe → to see all 4 fixes compared, plus exactly which one fits which type of feature.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Your own post "disappearing" for 2 seconds after you publish it isn't a bug — it's replica lag. Here are the 4 real fixes 👇

### Variant B — Long (400–600 chars)
Read-your-own-writes is one of the most common stale-data bugs in production: you write something, immediately read it back, and see the OLD version because your read landed on a lagging replica. The fix isn't one-size-fits-all — a hotel booking needs LSN-based routing (strictest), an order-history page is fine with a simple 5-second read-from-primary window, and a "continue watching" list needs no fix at all, since 30 seconds of staleness there is genuinely invisible to users.

---

## Best Time to Post
Thursday, 9:00–10:00 AM IST (practical production-bug content resonates mid-week)

## Engagement Hook
"Which feature in your product actually needed the strictest read-your-own-writes fix — and which one did you deliberately leave lagging?"
