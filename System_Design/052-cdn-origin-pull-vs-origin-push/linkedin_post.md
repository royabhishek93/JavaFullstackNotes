# CDN Origin Pull vs Origin Push — LinkedIn Post

## Post Text (copy-paste ready)

10 million users try to stream a movie premiere at the same second. Every one of them is a cache miss if you get this wrong — and your origin server falls over.

- Origin pull (lazy): CDN fetches from origin only on the first cache miss per edge node. Great default, but 100,000 simultaneous requests for a viral video = 100,000 edges hammering your origin at once — a cache miss storm.
- Origin push (eager): pre-warm all 220+ CDN edge nodes BEFORE launch. First user anywhere gets a cache hit — zero cold start. This is exactly how a Hotstar-style premiere survives 10M+ concurrent viewers.
- Origin shield fixes the stampede either way: designate one region as the only one that talks to your origin. Every other edge fetches from the shield, not the origin — N edges hammering you becomes 1 shield hammering you.
- Cache invalidation is the hard problem: short TTL is simple but costly, explicit purge (CloudFront: ~30s propagation) is precise but costs $0.005/1000 paths, and cache-busted hashed URLs (1-year TTL, zero invalidation ever) is the best answer for static assets.
- Cache-Control: no-cache does NOT mean "don't cache" — it means "revalidate every time." If you want zero caching, you need no-store. Mixing these up leaks cached responses or wastes origin round-trips.

Swipe to see: the pull vs push decision tree and the exact interview one-liner.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
10M users, one premiere, zero origin hits — the CDN pre-warming trick vs the cache-miss storm that takes your origin down 👇

### Variant B — Long (400–600 chars)
A CDN doesn't magically have your content — it either pulls it lazily on the first request (origin pull) or you push it proactively before anyone arrives (origin push). Get the choice backwards on a viral launch and 100,000+ simultaneous cache misses slam your origin server at once. The fix stack: origin push for predictable viral content, origin shield to absorb cache-miss storms for everything else, and content-hashed URLs so you almost never need to invalidate. This is the exact reasoning interviewers want to hear for any media or content-heavy system design question.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (technical deep-dives on CDN/infra topics land well early in the work week when engineers are planning sprints)

## Engagement Hook
"Has your origin ever gotten slammed by a cache-miss storm on a launch day? What finally fixed it — pre-warming, an origin shield, or something else?"
