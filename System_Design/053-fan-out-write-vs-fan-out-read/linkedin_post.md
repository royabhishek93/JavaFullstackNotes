# Fan-Out on Write vs Fan-Out on Read — LinkedIn Post

## Post Text (copy-paste ready)

Cristiano Ronaldo posts a photo. 50 million followers. Push it to every feed right now, and that single post queues 50 million Redis writes that take 10–30 minutes to drain.

- Fan-out on write (push): instant reads (ZRANGE, <1ms) but celebrities blow up the write queue — 50 celebrities posting together = 2.5 billion Redis writes fighting for the same pipeline
- Fan-out on read (pull): writing is nearly free (1 DB insert) but every feed load fans out to 200–500 queries per user — at 1M concurrent feed opens that's 500M DB queries/sec, impossible for any DB
- The celebrity threshold is real: Instagram's production hybrid fans out on write below ~10K followers, and switches to fan-out on read above that
- On read in the hybrid: pull the pre-built Redis feed, then run just 3–10 direct queries for the celebrities you follow (not 500), merge by timestamp, cache the merged result for 60 seconds
- Miss the celebrity threshold entirely and you get an inconsistency window — followers open the app right after a celebrity post and the feed isn't updated yet, because the fan-out queue hasn't drained

Swipe to see: the exact hybrid architecture, the data model (Redis ZSET + Cassandra partitioning), and the interview one-liner.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
CR7 posts → 50M feeds to update. Push now or pull later? Here's the hybrid Instagram actually runs 👇

### Variant B — Long (400–600 chars)
When a celebrity with 50M followers posts, do you push the update to every follower's feed immediately, or let each follower pull it when they open the app? Pure push (fan-out on write) makes reads instant but queues 50M writes per celebrity post — 10 to 30 minutes to drain. Pure pull (fan-out on read) makes writes free but costs 200–500 DB queries per feed load. Production systems like Instagram run a hybrid: fan out small accounts (<10K followers) on write, pull celebrity posts on read, merge and cache. Below: the full architecture, data model, and interview answer.

---

## Best Time to Post
Wednesday, 10:00–11:00 AM IST (feed/architecture deep-dives perform best mid-week when engineers are actively problem-solving)

## Engagement Hook
"If you were designing Instagram's feed, what follower-count threshold would you pick for switching from fan-out-on-write to fan-out-on-read — and why?"
