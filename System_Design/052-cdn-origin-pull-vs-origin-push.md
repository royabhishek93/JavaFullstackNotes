# CDN Origin Pull vs Origin Push
### Does CDN Fetch Content on Demand or Does Your Server Push It?

---

## PART 1 — THE STUDENT CONVERSATION

**A CDN (Content Delivery Network) is a network of servers spread around the world that cache your content close to users.**

Instead of every user in Japan fetching your video from a server in New York (150ms round trip), a CDN node in Tokyo serves it (5ms round trip). 30x faster.

But how does the Tokyo CDN node get your content in the first place? Two strategies:

**Origin Pull (Lazy/On-demand):** The CDN node doesn't have the file until a user in Tokyo asks for it. On the first request: CDN node asks your origin server for the file, gets it, caches it, serves it. All subsequent users in Tokyo get it from cache — fast.

**Origin Push (Eager/Pre-warm):** You proactively push content to all CDN nodes before any user requests it. When the first user in Tokyo asks, the content is already there. Zero cache misses for any user anywhere.

---

## PART 2 — ORIGIN PULL DIAGRAM

```
Origin Pull — First Request (Cache Miss):
────────────────────────────────────────────────────────────────────

  User in Tokyo                CDN Node (Tokyo)        Your Origin Server (NYC)
  ─────────────                ────────────────        ──────────────────────────

  GET /videos/movie.mp4 ──────►
                               MISS: not in cache
                               ──────────────────────────────────────────────►
                                                        Serve movie.mp4 (150ms)
                               ◄──────────────────────────────────────────────
                               Cache movie.mp4 locally.
                               TTL = 7 days (from Cache-Control header)
  ◄────────────────────────── Serve from origin (150ms on this first request)

Origin Pull — Subsequent Requests (Cache Hit):
────────────────────────────────────────────────────────────────────

  User 2 in Tokyo              CDN Node (Tokyo)
  ───────────────              ────────────────

  GET /videos/movie.mp4 ──────►
                               HIT: cached locally
  ◄────────────────────────── Serve from CDN edge cache (5ms) ✓

  All 1M users in Tokyo after the first one: 5ms latency. ✓
  First user in Tokyo: 150ms (paid the cache miss once)
```

### The Cache Miss Storm Problem

```
You publish a viral video. 100,000 users worldwide all try to watch it simultaneously.
CDN has never cached it. All 100,000 CDN nodes worldwide see a cache miss.
All 100,000 nodes simultaneously fetch from your origin → origin gets slammed.

Solutions:
  1. Request coalescing: CDN node receives 1000 simultaneous requests for same URL
     → Makes ONE request to origin, holds other 999, serves all when origin replies
     → CloudFront calls this "origin shield"

  2. Pre-warming (Origin Push) for known viral content (see below)

  3. Origin Shield: designate one CDN region as the "shield" that talks to origin
     → All other CDN nodes fetch from shield, not origin directly
     → Reduces origin load from N CDN nodes to 1
```

---

## PART 3 — ORIGIN PUSH DIAGRAM

```
Origin Push — Pre-warming CDN before launch:
────────────────────────────────────────────────────────────────────

  Your Server                  CDN (all 200+ edge nodes worldwide)
  ───────────                  ────────────────────────────────────

  You upload new movie to S3.
  Immediately call CDN API:
  POST /invalidations { paths: ["/videos/new-movie.mp4"] }  ← pre-warm all edges

  CDN: fetches /videos/new-movie.mp4 from origin into all 200 edge nodes proactively.

  User 1 in Tokyo (first user worldwide):
  GET /videos/new-movie.mp4 ──► CDN Tokyo node → HIT (already pre-warmed)
  Response: 5ms ✓ (no cold start, no cache miss latency)

  User 1 in London:
  GET /videos/new-movie.mp4 ──► CDN London → HIT (pre-warmed)
  Response: 5ms ✓

  Every user worldwide gets cache hit from their first request. ✓
```

---

## PART 4 — CACHE INVALIDATION (THE HARD PROBLEM)

```
"There are only two hard things in Computer Science: cache invalidation and naming things."
— Phil Karlton

Problem: you cached /products/shoes-123.html with TTL=24h.
You change the price. Old price is still served for 24 hours from CDN.
Users see wrong prices. Support tickets flood in.

Solution 1: Short TTL (simple but inefficient)
  Cache-Control: max-age=60  (1 minute TTL)
  Stale window: max 1 minute. Acceptable for product pages.
  Cost: 60x more origin requests vs 1-hour TTL.

Solution 2: Purge/Invalidate on change (fast, precise)
  When price changes: call CDN API to invalidate specific URLs.
  CloudFront: CreateInvalidation({ Paths: ["/products/shoes-123.html"] })
  CloudFront propagates to all edge nodes within ~30 seconds.
  Cost: CloudFront charges $0.005 per 1000 invalidation paths.

Solution 3: Cache busting (best for static assets)
  Embed version/hash in URL: /assets/app.abc123.js
  When JS changes: new file with new hash → new URL → old URL still cached (fine)
  New URL is not in cache → fresh fetch.
  Set TTL to 1 year (it NEVER changes for a given hash).
  No invalidation needed. CDN naturally caches old and new versions.
  Old browsers with old HTML get old JS → consistent.
  New browsers with new HTML get new JS → consistent.
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your OTT platform serves video globally. 10 million users watch a new movie release simultaneously. How do you handle it?"

**You (architect answer):**

> "A new major release is a pre-warming use case — I know in advance that this content
> will be viral. I'd use origin push via CDN pre-warming.
>
> The flow: when the transcoding pipeline completes (video is in S3 in HLS format), I
> trigger a CDN pre-warming job. This calls the CloudFront API to warm the content at
> all 220+ edge locations. CloudFront fetches each HLS segment from S3 into every edge node.
> For a 2-hour movie at 720p: ~1,440 segments × 10MB each = 14.4 GB per edge node.
> 220 nodes × 14.4 GB = 3.17 TB of pre-warming traffic to S3.
>
> After pre-warming (takes 15–30 minutes): all users worldwide hit cache on their first
> request. 10 million simultaneous viewers each get their first segment from a nearby
> edge in 3–5ms. Zero requests hit our S3 origin during the movie launch.
>
> For content that I can't pre-warm (long-tail catalog, millions of movies): origin pull
> with origin shield. I designate one AWS region (us-east-1) as the shield. All 220 CDN
> edge nodes fetch from the shield, not directly from S3. The shield fetches from S3 only
> once per cache miss and serves all edges from its warm cache.
>
> For cache invalidation: static assets (HLS segments, thumbnails) use content-addressed
> URLs — the segment filename includes the content hash. TTL is 1 year. Metadata (thumbnails,
> show descriptions, price) uses short TTLs (5 minutes) plus API-level invalidation on update."

---

## PART 6 — CLOUDFRONT CACHE HEADERS

```
Controlling CDN behavior with HTTP headers:
────────────────────────────────────────────────────────────────────

  Your origin server sets these headers on every response:

  Cache-Control: public, max-age=31536000, immutable
    → Cache for 1 year. Never check for updates. (use with content-addressed URLs)

  Cache-Control: public, max-age=300, s-maxage=86400
    → Browsers cache 5 minutes. CDN caches 24 hours. (CDN ignores max-age if s-maxage set)

  Cache-Control: no-cache
    → CDN must revalidate with origin on every request (ETag/Last-Modified check)
    → Reduces origin load vs no-cache with 200 response every time

  Cache-Control: no-store
    → CDN does NOT cache. Every request goes to origin. (use for user-specific data)

  Vary: Accept-Encoding
    → CDN keeps separate cache entries for gzip vs br vs identity responses

  ETag: "abc123"
    → Conditional requests: If-None-Match: "abc123" → 304 Not Modified if unchanged
    → CDN uses ETag to avoid re-downloading unchanged content from origin

Common CDN cache strategy by content type:
  HTML pages:          Cache-Control: public, max-age=60 (1 min freshness)
  API JSON:            Cache-Control: no-store (user-specific, don't cache)
  CSS/JS (hashed URL): Cache-Control: public, max-age=31536000, immutable
  Images (versioned):  Cache-Control: public, max-age=31536000, immutable
  Video segments:      Cache-Control: public, max-age=31536000, immutable
  Video manifest (.m3u8): Cache-Control: public, max-age=5 (live streams: changes often)
```

---

## QUICK REFERENCE CARD

```
Origin Pull (default, lazy):
  CDN fetches from origin on first cache miss per edge node
  Best for: long-tail content, unpredictable traffic, most use cases
  Risk: cache miss storm on viral content → use origin shield

Origin Push (proactive):
  Pre-warm CDN before users arrive
  Best for: scheduled launches, known-viral content, live events
  How: call CDN invalidation/warm API or use CDN "prefetch" feature
  Cost: one large S3→CDN fetch vs many cache misses

Origin Shield:
  Designate one CDN region as the only one to talk to origin
  All other edges fetch from shield (often already cached there)
  Reduces origin request rate dramatically (N edges → 1 shield)

Cache invalidation:
  Short TTL:       simple, higher origin load
  Explicit purge:  fast, precise, costs per invalidation
  Cache busting:   best for static assets (hash in URL, 1-year TTL)

CloudFront numbers:
  Pre-warm propagation:  ~15-30 minutes
  Invalidation propagation: ~30 seconds
  Edge locations:         220+ worldwide
  Cache hit rate target:  >95% for static assets, >80% for media

Interview one-liner:
"Origin pull is lazy: CDN fetches from origin on first miss per edge.
Origin push is eager: you pre-warm content before users arrive.
For a viral movie launch, pre-warm all 220 edge nodes — zero cache misses
on launch day. For long-tail content, origin pull with origin shield
prevents stampede to your origin."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** CDN strategy is an expected discussion point in any media/content system — interviewers want to hear you distinguish between predictable popular content (push) and unpredictable long-tail content (pull).

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **10 — Cloud Storage (Google Drive/Dropbox)** | Origin pull for user-shared files — unpredictable which files go viral. First download from a region: CDN fetches from S3, caches. Subsequent downloads from same region: CDN cache hit. Origin shield prevents S3 stampede when a file is shared publicly. |
| **17 — OTT Platform (Netflix/Hotstar)** | New movie premiere → origin push (pre-warm all 220 CDN edges before premiere). First user in Tokyo hits cache, not S3. Long-tail catalog → origin pull with origin shield. Cache headers: HLS segments = Cache-Control: immutable, 1-year TTL (content-addressed URLs). |
| **21 — Online Learning (Udemy/Coursera)** | Course videos: origin pull (can't predict which courses are popular). Live class recordings: origin push immediately after recording completes — students log in to watch within minutes of class ending. |

**Architect's one-liner for the interview:**
*"Use origin push when you know content will be popular before users arrive; use origin pull with an origin shield for everything else."*
