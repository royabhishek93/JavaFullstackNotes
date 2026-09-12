# Hybrid Fan-Out: Push vs Pull and the Celebrity Problem
### What breaks when Taylor Swift posts to 100M followers, and how feeds survive it

---

## PART 1 — THE STUDENT CONVERSATION

You already know the basic fan-out tradeoff (see [053-fan-out-write-vs-fan-out-read.md](053-fan-out-write-vs-fan-out-read.md)): fan-out-on-write pushes a new post into every follower's precomputed feed the instant it's created, so reads are cheap; fan-out-on-read builds the feed live at read time by pulling from everyone you follow, so writes are cheap. Most systems pick fan-out-on-write because reads vastly outnumber writes for a normal user.

Now imagine that same fan-out-on-write strategy applied to a celebrity account with 100 million followers. The moment they hit "post," your system needs to insert that post into 100 million separate feed lists. Even at a very generous 500,000 writes/second across your whole fan-out fleet, that's 200 seconds just to finish fanning out ONE post — and in the meantime the celebrity might post again, or your write infrastructure gets swamped by every other normal user's posts competing for the same fan-out workers. This is "the celebrity problem," and it's not a hypothetical — it's why every major social platform (Twitter, Instagram, Facebook) has a special-cased path for high-follower accounts.

The fix is a hybrid: don't fan out celebrity posts at write time at all. Instead, treat celebrities specially — their posts stay in one place (their own post table/timeline), and every follower's feed read does a little extra work: pull their normal precomputed feed (built via fan-out-on-write, cheap), AND separately fetch the latest posts from the handful of celebrities they follow (there are only ever a few celebrities per user, even if there are millions of celebrity followers total), then merge the two lists by timestamp before returning the page. You've moved the expensive part of "the celebrity's fan-out" from "write once, multiplied by 100M" to "read once per follower page-load, but only touching a tiny number of celebrity accounts each time" — and reads were already going to happen regardless.

The threshold for "who counts as a celebrity" isn't magic — it's an engineering knob tuned against your write infrastructure's actual capacity, typically somewhere between 100K and 1M followers, because that's the point where fan-out-on-write's per-post cost starts to dominate write capacity budgets.

---

## PART 2 — THE HYBRID FAN-OUT ARCHITECTURE DIAGRAMS

### Happy Path: Normal User Post (Push / Fan-Out-on-Write)

```
Normal user "bob_the_baker" (12,000 followers) posts:

  POST /api/posts
  { "userId": "bob_the_baker", "content": "Fresh sourdough today!", "postedAt": "2026-08-31T07:00:00Z" }
        │
        v
  ┌───────────────────┐
  │  Post Service      │  1. Write post to posts table (source of truth)
  │                    │     INSERT INTO posts (post_id, author_id, content, posted_at)
  └────────┬───────────┘
           │
           v
  ┌───────────────────────────────┐
  │  Fan-Out Worker (async, Kafka  │  2. Look up bob's follower list (12,000 IDs)
  │  consumer on "post-created")   │  3. For EACH follower, push post_id into their
  └────────┬───────────────────────┘     precomputed feed (Redis sorted set / Cassandra)
           │
           v
   follower_feed:alice   → ZADD feed:alice  1724979600  post_9981
   follower_feed:erin    → ZADD feed:erin   1724979600  post_9981
   follower_feed:frank   → ZADD feed:frank  1724979600  post_9981
   ... (12,000 total writes, completes in ~50-100ms across fan-out workers)

  When Alice opens her feed:
  GET feed:alice  (ZREVRANGE, top 50 by score/timestamp)
  → single Redis read, <5ms, post already sitting there
```

### Failure Mode Avoided: What Would Happen WITHOUT the Celebrity Special-Case

```
Celebrity "taylor_swift" (100,000,000 followers) posts:

  Fan-out worker attempts the SAME strategy as bob_the_baker:

  ┌────────────────────────────────────────────────────┐
  │  Fan-Out Worker                                     │
  │  1. Look up taylor's follower list: 100,000,000 IDs │
  │  2. For EACH follower, ZADD feed:{followerId} ...   │
  └────────┬─────────────────────────────────────────────┘
           │
           v
   100,000,000 individual feed-writes queued
   At 500,000 writes/sec fan-out throughput (generous, whole fleet):
     100,000,000 / 500,000 = 200 seconds to fully propagate ONE post
   Meanwhile:
     - Every OTHER user's normal post is competing for the same
       fan-out worker pool → normal users' feeds start lagging too
     - If taylor posts again 60 seconds later, fan-out queue backs up
       further — a growing backlog, not a transient spike
     - Redis/Cassandra write throughput spikes 100M ops in a burst,
       risking hot-partition / throttling on the feed-storage cluster
   Result: fan-out-on-write, applied uniformly, does not scale past
   a follower-count threshold — this is the celebrity problem.
```

### Hybrid Solution: Celebrity Post Is PULLED at Read Time, Not Pushed

```
Celebrity "taylor_swift" (100,000,000 followers, flagged is_celebrity=true
because follower_count > 100,000 threshold) posts:

  ┌───────────────────┐
  │  Post Service      │  1. Write post to posts table (source of truth) — SAME as before
  └────────┬───────────┘
           │
           v
  ┌────────────────────────────┐
  │  Fan-Out Worker             │  2. Checks author.is_celebrity == true
  │                             │  3. SKIPS the 100M-follower fan-out entirely.
  └─────────────────────────────┘     Post just sits in taylor's own post timeline.
                                       Write cost: O(1), same as any single insert.

  When Alice (a normal follower of both bob AND taylor) opens her feed:

  ┌─────────────────────────────────────────────────────────────┐
  │  Feed Read Service                                            │
  │                                                                │
  │  Step 1: fetch precomputed feed (fan-out-on-write path)        │
  │    ZREVRANGE feed:alice 0 49  → [post_9981(bob), post_9955...] │
  │                                                                │
  │  Step 2: fetch celebrity_follow_list for alice (small: usually │
  │          0-20 celebrities per user, even for power users)      │
  │    celebrities_followed_by(alice) = [taylor_swift, elon_musk]  │
  │                                                                │
  │  Step 3: pull LATEST posts directly from each celebrity's own  │
  │          timeline (fan-out-on-read, but only 2 lookups!)       │
  │    SELECT * FROM posts WHERE author_id='taylor_swift'           │
  │      ORDER BY posted_at DESC LIMIT 20                          │
  │    SELECT * FROM posts WHERE author_id='elon_musk'              │
  │      ORDER BY posted_at DESC LIMIT 20                          │
  │                                                                │
  │  Step 4: MERGE-SORT all lists by posted_at DESC, take top 50   │
  │    [taylor_post(07:05), bob_post(07:00), elon_post(06:58), ...] │
  └────────────────────────────────────────────────────────────────┘
           │
           v
  Returned feed page, latency ~15-40ms total
  (precomputed-feed read ~5ms + 2 celebrity-timeline reads ~5-10ms each + merge ~1ms)

  Celebrity write cost: O(1) instead of O(100,000,000).
  Every follower's read cost: +2 small extra queries instead of 0 — a
  cost paid PER READ, but bounded by "how many celebrities you follow,"
  not by "how many followers the celebrity has."
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Celebrity Threshold Classification

```java
public class FanOutRouter {

    private static final int CELEBRITY_FOLLOWER_THRESHOLD = 100_000;

    public void handleNewPost(Post post) {
        User author = userService.get(post.getAuthorId());

        // Persist the post regardless — source of truth write is identical either way
        postRepository.save(post);

        if (author.getFollowerCount() < CELEBRITY_FOLLOWER_THRESHOLD) {
            // Normal user: fan-out-on-write, async via Kafka to avoid blocking the post API
            kafkaTemplate.send("fan-out-jobs", new FanOutJob(post.getId(), author.getId()));
        } else {
            // Celebrity: no fan-out job at all. Post is discoverable only via
            // (a) the author's own timeline table, and (b) read-time pull-merge below.
            metrics.increment("celebrity_post_skipped_fanout");
        }
    }
}
```

### Fan-Out Worker (Normal Users Only)

```java
@KafkaListener(topics = "fan-out-jobs")
public class FanOutWorker {

    public void process(FanOutJob job) {
        List<String> followerIds = followerService.getFollowerIds(job.getAuthorId());
        // Batched pipeline write to Redis sorted sets — NOT one round-trip per follower
        redisTemplate.executePipelined((RedisConnection conn) -> {
            for (String followerId : followerIds) {
                conn.zAdd(("feed:" + followerId).getBytes(),
                          job.getPostedAtEpochMillis(),
                          job.getPostId().getBytes());
            }
            return null;
        });
        // Real numbers: pipelined Redis ZADD throughput ~200K-400K ops/sec per shard.
        // A 12,000-follower fan-out completes in well under 100ms.
    }
}
```

### Feed Read Service — The Merge Step

```java
@Service
public class FeedReadService {

    private static final int PAGE_SIZE = 50;

    public List<FeedItem> getFeed(String userId) {
        // Part A: precomputed feed (fan-out-on-write results for normal follows)
        List<FeedItem> pushedFeed = redisTemplate.opsForZSet()
            .reverseRange("feed:" + userId, 0, PAGE_SIZE - 1)
            .stream().map(this::loadFeedItem).collect(Collectors.toList());

        // Part B: pull latest posts from celebrities this user follows (small list, 0-20 typical)
        List<String> celebrityIds = followerService.getCelebritiesFollowedBy(userId);
        List<FeedItem> pulledFeed = celebrityIds.stream()
            .flatMap(celebId -> postRepository
                .findTop20ByAuthorIdOrderByPostedAtDesc(celebId).stream())
            .map(this::toFeedItem)
            .collect(Collectors.toList());

        // Part C: merge-sort both lists by postedAt descending, cap at PAGE_SIZE
        return Stream.concat(pushedFeed.stream(), pulledFeed.stream())
            .sorted(Comparator.comparing(FeedItem::getPostedAt).reversed())
            .limit(PAGE_SIZE)
            .collect(Collectors.toList());
    }
}
```

### Real Cost Comparison at Different Follower Counts

```
Fan-out write cost estimate (pipelined Redis writes, ~300K ops/sec/shard,
assume 8 shards in parallel = ~2.4M ops/sec fleet-wide capacity):

  Follower count   | Fan-out writes | Time to complete (fleet-wide)
  -----------------|-----------------|-------------------------------
  1,000            | 1,000           | ~0.4ms  (negligible)
  100,000          | 100,000         | ~42ms   (borderline — threshold zone)
  1,000,000        | 1,000,000       | ~420ms  (starts to matter under load)
  10,000,000       | 10,000,000      | ~4.2s   (unacceptable write-path latency)
  100,000,000      | 100,000,000     | ~42s    (fleet saturated, other users' posts delayed)

  Why 100K-1M is the typical cutoff:
  - Below ~100K: fan-out completes fast enough (tens of ms) that it doesn't
    meaningfully compete with the rest of the write workload.
  - Above ~1M: a single post's fan-out can occupy a noticeable fraction of
    total fleet write capacity for whole seconds, degrading fan-out latency
    for every OTHER post being fanned out concurrently (multi-tenant noisy-
    neighbor effect on shared infrastructure), even before you reach true
    mega-celebrities with 50-100M+ followers.
  - The exact number is tuned per-platform against actual fan-out fleet size
    and the write SLA the product wants for normal users' post visibility
    (Twitter/X and Instagram have both publicly discussed variants of this
    exact push/pull hybrid for this reason).
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your news feed uses fan-out-on-write so reads are fast. What happens when a celebrity with 50 million followers makes a post — walk me through why that breaks, and how you'd fix it."

**You (architect answer):**

> "Fan-out-on-write works great for the 99.9% case because it converts an expensive read (merge posts from everyone you follow) into a cheap one (read your precomputed feed), by paying the cost once at write time, amortized across however many followers there are. The problem is that 'amortized across followers' assumption breaks down completely for a celebrity — the write cost scales linearly with follower count, so a post from someone with 50 million followers means 50 million feed-writes have to happen before that post is visible everywhere. Even at very generous pipelined write throughput, that's tens of seconds of fan-out work competing with every other user's posts for the same write infrastructure, and if the celebrity posts again before the first fan-out finishes, the backlog compounds.
>
> The fix is a hybrid push/pull model. I'd classify accounts by follower count — say, above 100K followers is flagged as a 'celebrity' account — and change the write path only for those accounts: their posts are NOT fanned out to followers' feeds at write time. They just get written once to their own post timeline, which is an O(1) write regardless of follower count.
>
> Then I move the cost to read time, but in a way that stays cheap: when any follower loads their feed, the read service does its normal precomputed-feed lookup for regular follows, and separately does a tiny number of extra lookups — one per celebrity that specific user follows, which in practice is almost always a single-digit or low double-digit number even for a power user — pulling each celebrity's latest posts directly, then merge-sorting everything by timestamp before returning the page. The key insight is that while there might be millions of celebrity FOLLOWERS in total, the number of celebrities any ONE follower follows is small and bounded, so the extra read-time cost per page-load stays flat regardless of how famous the celebrity is.
>
> The operational concern I'd flag is picking the right threshold and re-evaluating it as infrastructure scales — if I set it too low, normal 'semi-influencer' accounts pay unnecessary read-time complexity; too high, and I still get write-path pressure from upper-mid-tier accounts. I'd monitor fan-out job completion latency per post and set the threshold where p99 fan-out time crosses an acceptable bound — historically that's landed in the 100K-1M follower range for platforms I've studied, but I'd validate it against our own fan-out fleet's measured throughput rather than assume a fixed number."

---

## PART 5 — DECISION FRAMEWORK

### Fan-Out Strategy Comparison

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Pure fan-out-on-write** | Push every post to every follower's feed at write time | Reads are trivially cheap; writes scale with follower count | Read: <5ms / Write: O(followers) | Low | Celebrity accounts (millions of followers) saturate write path |
| **Pure fan-out-on-read** | Build feed live at read time by merging all followed authors' posts | Writes are O(1); reads scale with follow-count | Read: 50-300ms+ / Write: <5ms | Low-Medium | Users following thousands of accounts make every read expensive |
| **Hybrid (push normal, pull celebrity)** | Threshold-based split — push for normal accounts, pull-and-merge for celebrities | Small added read complexity for everyone; bounded write cost | Read: 15-40ms / Write: O(1) for celebrities, O(followers) for normal | Medium | Threshold misconfigured (too low/high) shifts pressure to the wrong path |
| **Fan-out with fixed feed cap** | Push to feeds, but only keep e.g. latest 1,000 posts per feed (trim old ones) | Bounds Redis memory growth; slightly complicates "infinite scroll" pagination past the cap | Read: <5ms | Medium | Deep pagination beyond the cap needs a fallback pull path anyway |

### When hybrid fan-out is right
```
✓ Your platform has a genuine long-tail follower distribution (a small
  number of accounts have orders-of-magnitude more followers than the median)
✓ Fan-out write infrastructure has a measurable throughput ceiling you can
  benchmark against
✓ You can tolerate slightly higher read-path complexity (extra merge step)
  in exchange for bounded, predictable write costs
```

### Skip hybrid fan-out when
```
✗ Your platform has no "celebrity" tail — all accounts have roughly similar
  follower counts (e.g. a small enterprise team collaboration tool)
✗ You're pre-scale and pure fan-out-on-write already meets latency SLAs —
  don't add the merge complexity before you've measured an actual fan-out
  bottleneck
✗ Follower counts are capped by design (e.g. a "close friends" list product)
```

---

## QUICK REFERENCE CARD

```
CLASSIFICATION:
  is_celebrity = follower_count > CELEBRITY_THRESHOLD   (typical: 100K-1M)

WRITE PATH:
  Normal user post  → async fan-out job → ZADD feed:{followerId} for each follower
  Celebrity post    → NO fan-out job → post written once to author's own timeline

READ PATH (every user, always):
  1. pushedFeed = ZREVRANGE feed:{userId} 0 49        (precomputed, fast)
  2. celebIds   = getCelebritiesFollowedBy(userId)     (small, bounded list)
  3. pulledFeed = for each celebId: latest N posts from their timeline
  4. result     = mergeSortByTimestamp(pushedFeed, pulledFeed)[:50]

WHY IT WORKS:
  Celebrity FOLLOWER count can be huge (unbounded write cost avoided).
  Celebrities FOLLOWED per user is small and bounded (read cost stays flat).

RELATED:
  see 053-fan-out-write-vs-fan-out-read.md for the base push/pull tradeoff
```
