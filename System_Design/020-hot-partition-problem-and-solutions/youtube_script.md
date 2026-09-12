# Hot Partition Problem and Solutions — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 20 of 29

## HOOK (0:00–0:30)

[Screen cue: animated 10-lane highway, cars evenly spread]

Picture a highway with 10 lanes. Normal day. Traffic is spread evenly — each lane carries about 10% of the cars. Smooth, boring, nobody's complaining.

[Screen cue: celebrity convoy enters Lane 3, thousands of paparazzi cars pile in behind it]

Now a celebrity's convoy pulls onto that highway. Ten thousand journalists and fans follow. Suddenly, 99% of all traffic is jammed into Lane 3. Lane 3 is a parking lot. Lanes 1, 2, and 4 through 10? Basically empty.

[Screen cue: text overlay — "You can't fix this by adding more lanes"]

And here's the kicker — you can't fix this by adding more lanes to the highway. The problem was never total capacity. It's that 99% of traffic routes to ONE lane.

This is the hot partition problem, and it's exactly what happens when Cristiano Ronaldo — 500 million followers — posts something, and your Kafka topic keyed by `user_id` sends every single one of those fan-out events to the same partition. One partition eats 1000x more messages than everyone else. Let's talk about why this breaks systems, and the five ways to actually fix it.

## THE PROBLEM (0:30–2:00)

[Screen cue: title card — "Three Flavors of Hot Partition"]

Let's go through three real scenarios, with real numbers, because this bug hides in plain sight if you're not looking at the right dashboard.

**Scenario one: Kafka hot partition.** You've got a topic called `user-events` with 6 partitions, keyed by `user_id`. On a normal day, each partition handles about 2,000 events per second — nice and even, 12K events per second total across the topic.

[Screen cue: bar chart, P0 through P5 all at 2K, then P3 spikes]

Then Ronaldo posts. `hash("user_12345") % 6` maps him to partition 3. Partition 3 goes from 2,000 events per second to 50,000 events per second. That's a 25x jump on just that one partition. Consumer lag on P3 goes from zero to millions of messages, backlogged. And the consumer processing P3? It gets `OOMKilled` — heap exhausted, trying to buffer all those messages. Meanwhile P0, P1, P2, P4, P5 are sitting there completely idle, totally unaffected.

**Scenario two: hot shard by date.** Say you've sharded your `orders` table by `created_at` — shard-per-year. Sounds reasonable, right? Except Shard 5, which holds today's orders, gets 100% of writes and 35% of reads. Shard 5 CPU sits at 95%. Shards 1 through 4 — last year's, two years ago's orders — sit at 5% to 20% CPU. You have 5 shards, but only one of them is doing any real work.

[Screen cue: text overlay — "Time-based shard keys are almost always a bad idea"]

The lesson here: time-based shard keys are almost always a bad idea. Anything that concentrates "current" activity into one bucket is a hot shard waiting to happen.

**Scenario three: hot cache key.** A product goes viral on TikTok. Normally, each Redis node handles maybe 5,000 requests per second, spread across products. Redis can handle 500,000 ops per second per node — you're nowhere close to the limit. But this one viral product hashes to Redis node 2, and node 2 suddenly gets 200,000 requests per second — CPU pegged at 100%, network card saturated. Nodes 1 and 3? Completely normal.

[Screen cue: text overlay in bold — "Your monitoring dashboard says: All Systems Normal"]

And here's the trap that catches almost everyone: your monitoring dashboard is showing average throughput, and the average looks totally fine. Total cluster CPU, average request rate — nothing alarms. But one single node, one single partition, is on fire. If you're only watching averages, you will never see this coming. You have to look at per-partition, per-shard, per-node metrics.

## THE SOLUTION (2:00–5:00)

[Screen cue: title card — "5 Ways to Fix a Hot Partition"]

Okay, five solutions. Let's go in order of how commonly you'll reach for them.

**Solution 1: Salt the key with a random prefix.** Instead of routing all of Ronaldo's events to `user_12345`, append a random digit 0 through 9 before hashing: `user_12345_7`. Now his events spread across up to 10 different partitions instead of piling into one.

[Screen cue: code snippet — buildPartitionKey with ThreadLocalRandom]

```java
int salt = ThreadLocalRandom.current().nextInt(10);
return userId + "_" + salt;
```

But there's a trade-off — and interviewers love asking about this: you break ordering. Events for `user_12345_3` and `user_12345_7` can now arrive out of order relative to each other, because they're on different partitions. The fix: stamp a sequence number on each event and re-sort on the consumer side if strict ordering actually matters for that use case.

**Solution 2: Dedicated partitions for hot keys.** If you can predict who's going to be hot — verified celebrities, known large accounts — pull them out entirely. Route normal users to a `user-events` topic with 6 partitions, and route celebrities to a separate `celebrity-events` topic with 100 partitions. Completely different scaling tier, different consumer group, dedicated resources. No contention with normal traffic at all.

**Solution 3: Cell-based sharding**, mainly for databases. Say one account — Alice, an institutional trader — makes 10,000 transactions per second, all writing to one row. Instead of one row, split her balance across 10 "cells" — literally 10 rows, `cell_id` 0 through 9, and writes randomly pick a cell.

[Screen cue: SQL snippet — account_cells table with SUM aggregation]

```sql
SELECT account_id, SUM(balance) AS total_balance
FROM account_cells WHERE account_id = 'alice' GROUP BY account_id;
```

Reads aggregate across all 10 cells with a `SUM`. Ten rows instead of one, but no single hot row taking all the write pressure.

**Solution 4: Local in-process cache with Caffeine.** This is the fix for the viral-product Redis problem. Every app instance keeps a tiny local cache — Caffeine, max 1,000 entries, 1-second TTL. Check local cache first — that's roughly 100 nanoseconds, zero network. Only fall through to Redis on a miss.

At 200,000 requests per second for that viral product, spread across 100 app instances, each instance sees 2,000 requests per second — and with a 1-second local cache, Redis gets hit at most 100 times per second total. You just absorbed 200K req/sec down to 100 req/sec hitting Redis. That's the whole trick.

**Solution 5: Adaptive rate limiting and backpressure.** Tune your Kafka consumer so it doesn't try to gulp down millions of backlogged messages at once — `max.poll.records: 100` instead of pulling 10,000 at a time. Add a custom `pause.on.lag` behavior: if a partition's lag exceeds a million records, pause that consumer, resume once lag drops below 100K. This doesn't fix the hot partition, but it stops it from taking down your consumer with an OOM kill while you apply one of the other four fixes.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[Screen cue: title card — "How Do You Actually Detect This?"]

Let's get concrete about detection, because "my system feels slow" isn't a diagnosis.

For Kafka, run this:

```bash
kafka-consumer-groups.sh --bootstrap-server kafka:9092 \
  --describe --group my-consumer-group | sort -k5 -nr | head -20
```

That sorts partitions by lag, descending. If partition 3 shows 50 million lag and everyone else shows under 200K, that's not a capacity problem — that's a hot partition, full stop. Don't scale the whole cluster; find the one partition.

For a database, query `pg_stat_user_tables`:

```sql
SELECT schemaname, tablename, n_tup_ins + n_tup_upd + n_tup_del AS writes,
       seq_scan, idx_scan FROM pg_stat_user_tables ORDER BY writes DESC;
```

That tells you which table — and by extension, which shard — is absorbing all the write traffic.

For Redis, there's a built-in flag: `redis-cli --hotkeys`. It scans and reports keys that are getting disproportionate access, assuming you've got an LRU-based `maxmemory-policy` set.

[Screen cue: text overlay — thresholds table]

Now, the numbers engineers get wrong most often — the thresholds:

- A single Kafka partition tops out around 50 megabytes per second write throughput. If one partition is running 5x the average across the topic, that's your hot-partition signal.
- Redis can do about 500,000 simple ops per second on a single node. But per single key, once you're crossing 50,000 requests per second on ONE key, that's your trigger to add a local cache — don't wait for the node to actually saturate.
- PostgreSQL, a single shard with typical indexing tops out around 5,000 writes per second. Cross 3x the average across your shards, and it's time to re-shard or add read replicas.

The rule of thumb across all of these: **5x the average traffic on one partition, shard, or key means you have a hot partition** — not a "let's add more capacity" problem.

[Screen cue: decision tree diagram]

Now here's where engineers get the actual FIX wrong — they reach for the same solution every time. Use this decision tree instead:

Is the hot key **predictable**? Celebrity accounts, large merchants, known trending entities — yes, you can name them in advance. Then use a **dedicated partition or shard**. Don't salt it — just give it its own lane with more resources, like that 100-partition `celebrity-events` topic.

Is it **temporary and unpredictable**? A flash sale, a random viral product you couldn't have predicted? Then reach for a **local cache** — Caffeine with a short TTL absorbs the spike without you needing to know in advance which key would go hot.

Is **ordering required** for that entity's events? If yes, salting means you need a sequence number and re-sort logic — don't skip that step, or you'll ship subtle out-of-order bugs. If ordering doesn't matter, plain random salting is the simplest fix — just spread the key across N buckets and move on.

The mistake I see most: engineers jump straight to salting everything, forget the ordering trade-off exists, and three weeks later someone's debugging why events are processed out of sequence in production.

## REAL WORLD (8:00–9:30)

[Screen cue: split-screen — social media, payments, leaderboard icons]

Let's connect this to systems you've actually built or will be asked about in interviews.

**Social media, celebrity fan-out.** Think Instagram or Twitter-style platforms — when a celebrity account posts, it triggers a fan-out write to every follower's feed. Keying that Kafka topic by `user_id` means the celebrity's partition absorbs 1000x normal load. The fix in production: detect verified celebrity accounts via real-time event-rate monitoring, and route them to a dedicated high-throughput topic — separate scaling tier, separate consumer group, so a viral moment for one account doesn't degrade feed delivery for everyone else.

**Payments, large merchants.** Picture PhonePe or Paytm processing transactions where merchant_id is your Kafka partition key. A tiny local kirana store generates a handful of transactions a day. Amazon or a large merchant integrated with Apple Pay generates thousands per second. That merchant_id becomes a hot partition instantly. The production fix: sub-partition large merchants by payment type, or apply a salt, with compensating aggregation downstream to reconstruct a merchant-level view for reconciliation and reporting.

**Leaderboards.** Think an IPL fantasy league leaderboard during a live match — the top player, or a viral streamer's account, generates 100x more score-update events than an average player. Redis `ZINCRBY` itself handles concurrent updates fine — it's a single-threaded atomic command. But the Kafka topic feeding those score updates into Redis, if it's keyed by `player_id`, will show a hot partition for whoever's currently topping the leaderboard. The lesson: partition lag is your leading indicator — watch it before the leaderboard starts lagging behind the live match.

Across every one of these, the architect's answer in an interview is the same: you assumed uniform traffic per key, and reality gave you a power-law distribution instead. You fix it by either splitting the hot key across multiple partitions with a salt, or giving predictably hot entities their own dedicated, independently-scalable partition tier.

## OUTRO + NEXT EPISODE (9:30–10:00)

[Screen cue: recap bullet list — Kafka hot partition, hot shard, hot cache key, 5 solutions, 5x rule]

So to recap: hot partitions happen when your partitioning key isn't actually uniform — celebrity users, time-based shard keys, viral products. Detect it with per-partition metrics, not averages. Fix it with salting, dedicated partitions, cell-based sharding, local caching, or backpressure — pick based on whether the hot key is predictable, temporary, and whether ordering matters.

[Screen cue: end card — "Next Episode: Optimistic vs Pessimistic Locking"]

Next episode, we're tackling a question that comes up in almost every system design interview involving concurrent writes: optimistic versus pessimistic locking. When do you let two transactions race and check for conflicts after the fact, versus locking the row up front? That's episode 21. Subscribe so you don't miss it, and I'll see you there.
