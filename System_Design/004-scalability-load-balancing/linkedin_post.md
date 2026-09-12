# Scalability & Load Balancing — LinkedIn Post

## Post Text (copy-paste ready)

Sticky sessions are the #1 reason your auto-scaling doesn't actually scale.

- Sticky sessions pin a user to one server; auto-scaling adds 10 new servers, but that one server still holds every session — 80% CPU while the new servers idle at 10%
- Fix: sessions in Redis, not server memory — any pod can serve any request, and auto-scaling actually works
- Flash sale prep (10x traffic in 2 hours): pre-scale before traffic hits (HPA reacts in minutes, spikes happen in seconds), pre-warm caches, queue-based order acceptance via SQS instead of direct DB writes
- Consistent hashing prevents "cache avalanche" — adding a 5th Redis node with plain modulo hashing remaps 100% of keys at once; consistent hashing remaps only ~1/N
- Rolling deploys without connection draining = real 502 errors for real users — a 30s deregistration delay + readiness probe fixes it

Swipe → to see the full flash-sale architecture (Route53 → CDN → ALB → stateless pods → Redis/Aurora) and the sticky-session fix.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Sticky sessions quietly break auto-scaling — all your load pins to 1 server while the rest idle. Here's the fix 👇

### Variant B — Long (400–600 chars)
Auto-scaling only works if every pod is stateless. Sticky sessions break that promise — a user pinned to one server means that server carries 80% of the load while nine freshly-scaled servers sit at 10%, and if it crashes, every pinned user loses their session mid-checkout. For flash sales (10x traffic in 2 hours), the real prep is pre-scaling before traffic hits, pre-warming caches, and accepting orders through a queue instead of writing directly to the DB. Rolling deploys need connection draining too, or you'll see real 502s during routine releases.

---

## Best Time to Post
Monday, 10:00–11:00 AM IST (infrastructure/scaling content performs well at the start of the work week)

## Engagement Hook
"Has a sticky-session bug ever bitten your team during a high-traffic event? What tipped you off?"
