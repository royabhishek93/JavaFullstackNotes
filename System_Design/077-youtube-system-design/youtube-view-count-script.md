# YouTube Video Script
# Title: "How YouTube Counts 500 Million Views a Day — System Design Deep Dive"
# Target Length: ~25–30 minutes
# Level: Intermediate to Senior Engineers / System Design Interview Prep
# Style: Conversational, whiteboard-style explanation

---

## VIDEO METADATA

**Thumbnail idea**: Split screen — left side shows "1.2M views" frozen, right side shows
a firehose of events flooding in. Bold text: "WHY DOESN'T IT UPDATE?"

**Tags**: system design, youtube architecture, cassandra internals, bigtable internals,
kafka, flink, redis, distributed systems, system design interview, 15 YOE

**Description**:
Ever noticed YouTube shows "1.2M views" but the number doesn't change every second
even though millions of people are watching? In this video I'll explain exactly why —
and walk you through the full system design behind it. We'll cover the architecture,
API design, database decisions, Cassandra vs Bigtable internals, trade-offs, and the
senior-level interview questions this topic generates. Let's go.

---

## CHAPTERS (Timestamps)

00:00 — Hook: Why doesn't the view count update in real time?
01:30 — The scale problem: 500M views a day
03:00 — Why every naive solution fails
06:00 — The big picture architecture
10:00 — API design and why we return 202 not 200
13:00 — ER diagram and database choices
17:00 — How Cassandra works internally (plain English)
21:00 — How Bigtable works internally (plain English)
24:30 — Cassandra vs Bigtable — which do you pick?
26:00 — Trade-offs and consistency vs latency
28:00 — Senior trap questions and how to answer them
31:00 — How to explain this in an interview like an architect
33:00 — Summary and what to study next

---
---

## SCRIPT

---

### INTRO / HOOK
### [00:00 — 01:30]
### [SCREEN: Show YouTube page, view count frozen at "1.2M views"]

---

**[PRESENTER — talking to camera, casual tone]**

Open YouTube right now. Pick any video with a million views.
Watch the number.

It doesn't move, does it?

Now think about this — if that video has a million people watching it right now,
that's a million play events happening every few minutes.
But the counter just... sits there.

How is that possible?

Is YouTube broken?

No. It's one of the most deliberate design decisions in the entire system.
And once you understand why — you'll understand a core principle of
how every large-scale distributed system works.

Today we're going to pull this apart completely.

We'll cover the full architecture, the API design, the database design,
how Cassandra and Bigtable actually work under the hood,
the trade-offs involved, and the senior-level questions this topic
generates in system design interviews.

If you're preparing for a staff engineer or architect interview,
this is exactly the kind of question they ask.

Let's go.

---

### SECTION 1: THE SCALE PROBLEM
### [01:30 — 03:00]
### [SCREEN: Draw numbers on whiteboard]

---

**[PRESENTER — whiteboard mode]**

Let's start with the numbers. Because in system design, math drives decisions.

YouTube gets 500 million video plays every single day.

Let's break that down.

500 million divided by 86,400 seconds in a day —
that's about 6,000 view events every second. Average.

But "average" is not the real problem.

Think about what happens when a big music video drops.
Or a breaking news moment.
Or a viral clip.

You can get 10x, 20x, sometimes 50x the average traffic
in a short window.

That's 60,000 to 100,000 view events per second.

### [SCREEN: Write on board]
```
500M views/day
÷ 86,400 seconds
= ~6,000 writes/second (average)

Peak viral event:
= ~60,000 – 100,000 writes/second
```

Now here's the question.
What if every single one of those events needed to
immediately update a counter in a database?

That's 60,000 writes per second on a single row.
A single row, for a single video.

Can a database handle that?

Spoiler: No. And we're about to see exactly why.

---

### SECTION 2: WHY NAIVE SOLUTIONS FAIL
### [03:00 — 06:00]
### [SCREEN: Whiteboard — draw three failed approaches]

---

**[PRESENTER]**

Let's look at the three obvious solutions that every engineer tries first.
And why each one breaks at this scale.

---

#### Naive Approach 1: Just update the database directly

**[SCREEN: Write SQL]**
```sql
UPDATE videos
SET view_count = view_count + 1
WHERE video_id = 'abc123';
```

Simple. Clean. Obvious.

But here's what actually happens at 60,000 writes per second.

When you run this SQL, the database puts a **lock** on that row.
It says — "no one else can touch this row until I'm done."

While that lock is held, all the other writers are waiting in a queue.

60,000 writers. One queue. One row.

Your wait time explodes. The request that used to take 5 milliseconds
now takes seconds. Users notice lag. Players buffer. Errors spike.

The database has become the bottleneck for your entire video player.

Not because of storage. Not because of disk space.
Because of one counter.

That's a design failure.

---

#### Naive Approach 2: Add a distributed lock

**[SCREEN: Draw lock → increment → release pattern]**

OK, so what if we use a smarter lock?
Something like Redis or Zookeeper managing a distributed lock.

```
acquire_lock(video_id)
  → increment counter
  → release_lock
```

Better? A little. But same fundamental problem.

At 60,000 requests per second, most requests are waiting for the lock.
If the server holding the lock crashes, everyone else is stuck.

And this approach still serialises everything.
You've just moved the bottleneck from the database to the lock manager.

---

#### Naive Approach 3: Each server keeps its own counter

**[SCREEN: Draw multiple servers each with their own count]**

What if each web server just keeps its own count in memory?
Server 1 says "I've seen 500 views." Server 2 says "I've seen 300 views."
Every few minutes, they all flush to the database.

This actually works better. But it has two big problems.

**Problem one**: If a server crashes, you lose whatever it had in memory.
That's missing view counts. Lost data.

**Problem two**: How do you deduplicate?
If the same user refreshes the page and hits server 1 once and server 2 once —
that's two counts for one person.

You need coordination between servers to deduplicate. And coordination brings
us right back to the lock problem.

---

**[PRESENTER — turns to camera]**

So all three obvious approaches either break under load,
lose data, or create the same bottleneck they were trying to avoid.

The real answer requires a completely different way of thinking.

Instead of asking "how do I update the count faster" —
you ask "what if I DON'T update the count immediately at all?"

That's the insight. Let's build on it.

---

### SECTION 3: THE BIG PICTURE ARCHITECTURE
### [06:00 — 10:00]
### [SCREEN: Draw the full architecture diagram]

---

**[PRESENTER — whiteboard]**

Here is the architecture. Let me walk through it left to right.

**[SCREEN: Draw each piece as you explain it]**

```
CLIENT → API GATEWAY → KAFKA → FLINK → REDIS → BIGTABLE → CDN → CLIENT
```

---

**Step 1: The user clicks play.**

Their device fires a small event — video ID, session ID, timestamp, device type.
That's it. The client does NOT wait for any counting to happen.
The server receives it, puts it in a queue, and immediately replies:
"Got it. You're good."

The video starts playing in under 200 milliseconds.
The counting hasn't happened yet. That's fine.
The user's experience is not blocked by the counting pipeline.

---

**Step 2: The event goes into Kafka.**

Kafka is a message queue — think of it like a very durable, very fast inbox.

Events pile up in Kafka. Millions of them per minute.
Kafka holds them safely, even if the processing systems downstream are slow or crashed.
And it can replay them — if something goes wrong, you can re-process the events later.

This is crucial. We'll come back to it.

---

**Step 3: Flink reads from Kafka and processes events.**

Flink is a stream processing engine. It reads the events from Kafka in real time.

But instead of processing each event one by one — it groups them into
**30-second windows**.

Every 30 seconds, Flink counts up all the view events for each video
and produces a single number: "video ABC had 847 views in the last 30 seconds."

That single number gets written to Redis.

Instead of 847 individual writes, you have 1 write every 30 seconds.
That's the write amplification reduction that makes this whole thing work.

---

**Step 4: Redis holds the hot counter.**

Redis is an in-memory database — extremely fast.
It has an atomic operation called INCRBY.
"Increase this counter by 847." Done in microseconds.

This is the live counter. When you request the view count for a video,
it comes from here most of the time.

---

**Step 5: Bigtable / Cassandra holds the authoritative historical data.**

Every 5–10 minutes, the counts are flushed from Redis to a persistent database.
This is your source of truth — what creator analytics, revenue systems,
and legal audits rely on.

Redis can lose data on restart. That's OK. Bigtable has it.

---

**Step 6: CDN caches the read response.**

When a viewer requests "how many views does this video have" —
that request doesn't even reach the servers most of the time.
A CDN (content delivery network) — like Cloudflare — cached the answer.

For viral videos, the cache is valid for 30 seconds.
For older videos, it might be valid for an hour.

This means 600,000 read requests per second are absorbed by the CDN
before a single one reaches Redis.

---

**[PRESENTER — steps back]**

The key insight from this whole diagram is this:

The user's play request and the counting pipeline are completely separate.
They run independently, on different tracks.
One is real-time. One is approximate and asynchronous.

That decoupling is what makes this work at 500 million events a day.

---

### SECTION 4: API DESIGN
### [10:00 — 13:00]
### [SCREEN: Show API contracts]

---

**[PRESENTER]**

Let's talk about the APIs. There are 5 key APIs in this system.

---

**API 1 — Record the view event**

```
POST /v1/views

Body:
{
  "video_id":    "dQw4w9WgXcQ",
  "session_id":  "sess_a3f92b",
  "user_id":     "usr_xyz789",
  "client_ts":   1720000000000,
  "watch_pct":   0,
  "device_type": "mobile"
}

Response: 202 Accepted
{
  "event_id": "evt_9a8b7c",
  "status":   "queued"
}
```

Notice the response code: **202 Accepted**, not **200 OK**.

Why?

200 means "I did the thing."
202 means "I received it. I'll do the thing asynchronously."

This is semantically correct because we're telling the client:
"Your view event is queued. We haven't counted it yet. But we will."

Honest, accurate, and it sets the right expectations.

---

**API 2 — Heartbeat (watch time update)**

```
PATCH /v1/views/{event_id}/progress

Body:
{
  "watch_pct":    45,
  "watch_time_s": 270
}

Response: 204 No Content
```

This one is interesting. Why a separate API for watch time?

Because watch time is our **primary fraud signal**.

A view event arrives. Watch time is zero. Is it a real view?
Could be a bot that never actually watched.

As the user watches, the client sends heartbeats every 30–60 seconds.
If after 5 minutes there are no heartbeats — the fraud pipeline flags it.

By separating this API, the fraud system gets a steady stream of
evidence about each view in real time — without needing to
hold the initial view event open.

---

**API 3 — Get view count (public)**

```
GET /v1/videos/{video_id}/view-count

Response:
{
  "view_count":    1247832910,
  "display_count": "1.2B",
  "as_of":         "2026-09-09T10:00:00Z",
  "freshness":     "approximate"
}
```

Two things worth noticing here.

**First**: We return both the raw number AND the display string.
"1.2B" is pre-formatted server side.
This ensures every client — web, mobile, TV — displays it consistently.

**Second**: We return "as_of" — when the count was last updated.
And "freshness" — is this exact or approximate.

This is transparency. The client knows this data is not real-time.
It can show "updated 2 minutes ago" if it wants to.
That's better UX than pretending it's live.

---

**API 4 — Creator analytics (authoritative)**

```
GET /v1/creator/videos/{video_id}/analytics/views
Header: X-SLA-Tier: authoritative

Query: from=..., to=..., granularity=hour
```

This API is different. It bypasses the CDN and Redis entirely.
It goes straight to Bigtable.

Why? Creators are not regular viewers.
They need fraud-adjusted, accurate counts.
Revenue is calculated from this data.

Different users have different requirements.
That's two separate read paths with two separate SLAs.
Design your API to reflect that.

---

**API 5 — Batch view counts (internal)**

```
POST /internal/v1/videos/view-counts/batch

Body: { "video_ids": ["id1", "id2", ..., "id100"] }
```

When your home feed loads, it shows 30 video thumbnails.
Each thumbnail needs a view count.

Without a batch API: 30 separate GET requests. 30 round trips.
With a batch API: 1 request. 1 round trip.

This is a 30x reduction in network overhead for the home feed.
Always design batch APIs for any resource that appears in lists.

---

### SECTION 5: DATABASE DESIGN AND DECISIONS
### [13:00 — 17:00]
### [SCREEN: Draw ER diagram, then table of decisions]

---

**[PRESENTER]**

Now the database design. This is where a lot of interviews go deep.

The question you'll always get is: "Why didn't you just use one database?"

The honest answer is: different parts of this system have
completely different requirements. One database can't serve all of them well.

Let me show you.

---

**[SCREEN: Draw entities]**

We have five main data stores in this system.

**VIDEO table — in MySQL or PostgreSQL**

This is simple relational metadata. Video title, creator, duration, status.
Low write volume — videos are uploaded, not updated constantly.
Needs ACID — when you change a video's status from "processing" to "published,"
that has to be correct.
PostgreSQL is perfect for this.

**VIEW_EVENT — in Kafka (not a database at all)**

500 million events per day. 182 billion per year.
You never query these directly — they're processed by Flink.
They need to be durable, replayable, and high-throughput.
That's Kafka. Not a database.

**VIDEO_VIEW_COUNT — in Redis**

This is the live counter. One counter per video.
Needs microsecond atomic increments.
Redis INCRBY is an atomic operation — no locks, no waiting, just increment.
PostgreSQL's "UPDATE SET count + 1" requires a row lock. Doesn't survive 60K writes/sec.

**VIEW_COUNT_TIMESERIES — in Bigtable or Cassandra**

Historical counts by hour. This is for analytics and creator dashboards.
Needs fast range queries: "give me all hourly data for video ABC in September."
Wide-column stores are built for exactly this access pattern.

**FRAUD_SIGNAL — in Cassandra**

Fraud events are append-only. High write volume. Lookup by event ID.
Cassandra's append-optimised write path is a perfect fit.

---

**[PRESENTER — turns to camera]**

Notice what I just did there.

I didn't say "let's use Cassandra for everything" or "let's use PostgreSQL."
I looked at each data entity, understood its access pattern,
and chose the tool that fits that pattern best.

**That's polyglot persistence.**
Multiple databases, each doing one job well.

The operational cost is real — more systems to manage.
But all of these are managed cloud services now.
The cost is much lower than it used to be.

---

**[SCREEN: Field-level decisions table]**

Let me also go through some specific field-level decisions
because these come up in interviews.

**Why BIGINT not INT for view counts?**

INT has a maximum value of about 2.1 billion.
In 2014, Gangnam Style broke YouTube's view counter.
It crossed 2.1 billion views and the counter overflowed.
YouTube had to patch the counter live.

BIGINT maximum is 9.2 × 10 to the 18th power.
That's 9.2 quintillion. You're not going to overflow BIGINT.

Always use BIGINT for counters.

---

**Why ip_hash instead of ip_address?**

Raw IP addresses are personal data under GDPR.
If you store them, you need to handle consent, deletion requests,
data retention limits.

Instead, we store SHA-256(ip_address + daily_salt).
A hash. You can't reverse it to get the original IP.
But you CAN still detect if the same IP appears 1,000 times in an hour.
Fraud detection still works. GDPR is satisfied.

---

**Why client_ts AND server_ts both exist?**

The client timestamp is when the event happened according to the user's device.
The server timestamp is when the server received it.

These can differ — devices have wrong clocks, events arrive late.

The difference between client_ts and server_ts is a fraud signal.
If an event arrives with a client timestamp 2 hours in the past,
it might be a replayed event from a bot.

We keep both to detect these patterns.

---

### SECTION 6: HOW CASSANDRA WORKS INTERNALLY
### [17:00 — 21:00]
### [SCREEN: Draw Cassandra write path step by step]

---

**[PRESENTER]**

OK let's go deep on Cassandra.

I'm going to explain how it actually works inside — with no jargon,
just plain analogies.

---

**The first thing you need to know: Cassandra has no boss.**

Most databases have a "primary" server that's in charge.
If that server goes down, you have a problem.

Cassandra doesn't work that way.
Every single server — every "node" — is equal.
There is no primary. There is no boss.

```
[SCREEN: Draw nodes in a ring, all connected to each other]

    Node A ──── Node B
       │   ╲  ╱   │
       │    ╲╱    │
       │    ╱╲    │
       │  ╱    ╲  │
    Node D ──── Node C
```

If Node B dies, Node A, C, and D keep running.
No downtime. No leader election. Just keep working.

---

**Now let's talk about what happens when you write data.**

There are three steps. I'll use an everyday analogy.

**[SCREEN: Draw the three-step write path]**

**Step 1 — The Diary (Commit Log)**

Before doing anything else, Cassandra writes your data to a file on disk.
Think of it like writing in a diary before you do anything with the information.

Why? If the power cuts out right now — the data is on disk.
Cassandra can recover it from the diary when it restarts.

This makes writes crash-safe.

**Step 2 — Memory (MemTable)**

Now Cassandra puts your data in RAM — the computer's fast memory.
Your data is now instantly readable.
RAM is maybe 100 times faster than disk.

The MemTable fills up over time. About 128 megabytes.

**Step 3 — File on disk (SSTable)**

When the MemTable fills up, Cassandra saves everything to a file on disk
called an SSTable — Sorted String Table.

Think of it like saving your Word document after typing a lot.

Here is the most important thing about SSTables:
**Once written, they are NEVER changed.**

If you update a record, Cassandra doesn't go back and edit the old file.
It writes a BRAND NEW file with the update.
The old file stays on disk until a cleanup job runs.

This is why Cassandra writes are so fast —
it never needs to find old data, never locks a row, never updates in place.
Just: write new file. Done.

---

**Reading data: the smart skip**

When you read data, it might be in memory OR in any of dozens of files on disk.

Checking 50 files is slow. So Cassandra uses a trick called a **Bloom Filter**.

Every SSTable file has a tiny Bloom Filter attached to it.
The Bloom Filter can answer one question:
"Is this data DEFINITELY NOT in me?"

If yes → skip this file completely, don't even open it.
If maybe → check this file.

Instead of checking 50 files, you check maybe 3.
That's a massive speed improvement.

---

**The cleanup job: Compaction**

Over days, SSTable files pile up.
Same record exists in multiple files — old version in file 1, new version in file 7.

A background job called Compaction runs and:
- Merges all those files into one
- Keeps only the newest version of each record
- Removes deleted records

Result: fewer files, faster reads.

Downside: Compaction uses CPU and disk while running.
This is a real operational challenge with Cassandra.

---

**How data spreads across servers: the Ring**

Imagine the servers arranged in a circle like a clock face.
Each server owns a section of the circle.

When you write a record, Cassandra converts the key to a number.
That number maps to a section of the circle.
The write goes to the server owning that section.

Adding a new server? It just takes a slice from existing servers.
Only that slice's data moves.
Everything else stays put.

---

**How servers know about each other: Gossip**

Every second, each server picks 2–3 random neighbours and says:
"Here's what I know about myself and the servers I've talked to recently."

Like office gossip. Information spreads through the whole cluster
without any central announcement system.

Within seconds, every server knows who's alive and who's down.

---

### SECTION 7: HOW BIGTABLE WORKS INTERNALLY
### [21:00 — 24:30]
### [SCREEN: Draw Bigtable architecture]

---

**[PRESENTER]**

Now Bigtable. Same goal — different architecture.

---

**The core idea: one giant sorted table, cut into pieces.**

Imagine a spreadsheet with billions of rows, sorted alphabetically.
That's Bigtable conceptually.

It's too big for one machine, so it's cut into chunks called **Tablets**.
Each Tablet is handled by a server called a **Tablet Server**.

```
[SCREEN: Draw the sorted table being cut into Tablets]

  Tablet 1          Tablet 2          Tablet 3
 (rows A–G)        (rows G–M)        (rows M–Z)
    │                   │                   │
Tablet Server 1   Tablet Server 2   Tablet Server 3
```

---

**Three roles in Bigtable:**

**The Master** — like a traffic controller.
Knows which Tablet Server handles which Tablet.
Manages load balancing — if one server has too much data, it moves Tablets.
Does NOT handle your data directly.

**Tablet Servers** — the workers.
Each one handles reads and writes for its assigned Tablets.

**Google Cloud Storage** — where the actual data files live.
NOT on the Tablet Server's local disk.

That last point is everything. Let me explain why.

---

**The clever part: data lives in GCS, not on the server**

In a traditional database, the data is on the server's local disk.
If the server crashes, the data is trapped there.
You need to copy it to another server. That can take minutes.

Bigtable does it differently.

The data files live in Google Cloud Storage — completely separately
from the Tablet Servers.

So when a Tablet Server crashes:
1. The Master notices immediately
2. Assigns those Tablets to another Tablet Server
3. That server just starts reading from GCS — data was already there
4. Recovery happens in seconds, not minutes

```
[SCREEN: Draw the comparison side by side]

Traditional:              Bigtable:
Server crashes            Server crashes
     ↓                         ↓
Data stuck on disk        Master reassigns Tablet
     ↓                         ↓
Need to copy data         New server reads from GCS
     ↓                         ↓
Minutes to recover        Seconds to recover
```

The server is just a worker. The data is the important thing,
and it lives separately. Swap the worker, keep the data.

---

**Writing data in Bigtable:**

1. Your app asks: which server handles this row?
2. Tablet Server 2 receives your write
3. Writes to a shared log on GCS — crash safety
4. Writes to its MemTable — immediately readable
5. Sends "done" back to your app
6. Later: MemTable flushes to an SSTable file in GCS

Same fundamental pattern as Cassandra — commit log, MemTable, SSTable.

---

**Scaling: tablet splitting**

When a Tablet grows too big — around 1 gigabyte —
Bigtable automatically splits it into two smaller Tablets
and moves one to another server.

No downtime. Completely automatic.
Add more servers, split more Tablets, handle more data.
That's the scaling model.

---

### SECTION 8: CASSANDRA VS BIGTABLE — WHICH DO YOU PICK?
### [24:30 — 26:00]
### [SCREEN: Comparison table]

---

**[PRESENTER]**

So you understand how both work. Now when do you pick which one?

```
[SCREEN: Show comparison table]

                    CASSANDRA           BIGTABLE
Is there a boss?    No — all equal      Yes — Master (but
                                        doesn't touch data)

Where is data?      On server's disk    In Google Cloud Storage

Server crashes?     Other nodes take    Master reassigns to
                    over (replicated)   another server — seconds

Scales how?         Add servers to ring Split tablets across
                                        more servers

You manage it?      Yes (or DataStax)   No — Google manages it

Works on?           Any cloud or        GCP only
                    on-prem
```

**Pick Bigtable when:**
- You're on GCP — it integrates natively with Dataflow, BigQuery, Pub/Sub
- You want zero operational overhead
- YouTube is GCP native, so Bigtable is the natural fit

**Pick Cassandra when:**
- You're multi-cloud or on-prem — not locked to GCP
- You need flexible CQL queries
- Your team already knows Cassandra
- You need tunable consistency per write operation

Both can handle petabyte scale. The decision is mostly about
your cloud strategy and operational preference.

---

### SECTION 9: TRADE-OFFS
### [26:00 — 28:00]
### [SCREEN: Draw trade-off table]

---

**[PRESENTER]**

Every design decision in this system is a trade-off.
Let me make them explicit.

---

**Trade-off 1: Consistency vs Latency**

We chose eventual consistency.
The view count is approximately 1–2 minutes behind real-time.

Why is this acceptable?
Because we display "1.2M" — not "1,247,832."
Rounded numbers look like approximations.
Nobody notices 2 minutes of lag when the number is already rounded.

If we wanted strong consistency, we'd need synchronous DB writes on every play.
That brings us back to the row lock problem.
The trade-off is clear: approximate counts for low latency. We take it.

---

**Trade-off 2: Write simplicity vs Read complexity**

Writes are simple and fast — just append to Kafka.
But reads have 3 layers: CDN, Redis, Bigtable.

We made reads more complex so writes could be simpler.
Writes happen 500 million times a day.
Reads happen even more.

But CDN absorbs most reads before they even reach the backend.
So the complexity is hidden from the client.

---

**Trade-off 3: Single Redis key vs Sharded keys**

For regular videos, one Redis key per video is simple and fast.
For viral videos, one key means one hotspot — all writes pile up there.

We shard viral video counters across 16 keys.
Writes spread across 16 Redis slots.
Read = sum 16 keys — slightly more work.

We only shard videos above a threshold.
Regular videos stay simple.

---

**Trade-off 4: Operational complexity**

We use 5 different systems: Kafka, Flink, Redis, Bigtable, CDN.
Each one needs monitoring, alerting, capacity planning.

The payoff: each system has one job, does it extremely well,
and can scale independently.

If view count reads spike, scale the CDN.
If view events spike, scale the Kafka partitions and Flink workers.
The two things don't affect each other.

Monoliths couple these concerns. This architecture separates them.

---

### SECTION 10: SENIOR TRAP QUESTIONS
### [28:00 — 31:00]
### [SCREEN: Q&A format]

---

**[PRESENTER]**

These are the questions designed to separate people who've read about
distributed systems from people who've actually operated them.

---

**Trap Question 1: "Your Flink job has been down for 6 hours due to a bug.
How do you recover the view counts?"**

Junior answer: "We lost those counts."

Senior answer:

The data is not lost. It's in Kafka.
Kafka keeps events for 7 days by default.

Here's what you do:
1. Fix the Flink bug, deploy the patched job.
2. Reset the consumer offset back to 6 hours ago.
3. Flink replays 6 hours of events — faster than real-time because
   it's not rate-limited by live ingress.
4. During replay, write to a shadow Redis key so you don't
   double-count live events coming in simultaneously.
5. Once replay catches up, swap the shadow key to primary.

The count was stale for 6 hours in the UI.
That's acceptable. What's not acceptable is permanent data loss.
Kafka prevents that.

---

**Trap Question 2: "Redis memory is getting full. Someone wants to
evict old counters. What's the risk?"**

The trap: Redis evicts a video counter. Application reads it, gets zero.
That zero gets cached in CDN. Every user sees "0 views" for 30 seconds to an hour.

The fix:
Never treat a Redis MISS as zero.
Always fall through to Bigtable.
The application must distinguish "key not found" from "counter is zero."

Also: use LRU eviction targeted at archive videos — not active ones.
Keep the top 1 million active video counters warm. Never evict them.

---

**Trap Question 3: "The product team wants counts to never go backward,
even after fraud removal. How do you handle it?"**

This is a business decision disguised as a technical question.

Option 1: Show a high-water mark. Never decrement.
Internal fraud-adjusted count is accurate.
UI shows the maximum the count has ever been.
Honest about being approximate. Dishonest about fraud removal.

Option 2: Stabilisation window.
New videos show approximate counts for 5 minutes.
After that, the fraud-adjusted count is final and only goes up from there.

My recommendation: Option 2.
It's honest. Creators eventually see accurate data.
And you negotiate with the product team — this is a trust decision,
not just a technical one.

---

**Trap Question 4: "How do you guarantee exactly-once counting?"**

The answer is: you can't — not truly. But you can get close enough.

Exactly-once in distributed systems is extremely expensive.
You need distributed transactions or idempotency keys everywhere.

What you actually do:
- Use `session_id` as an idempotency key in Flink windows
- Deduplicate: same session within 30 seconds = same view
- Accept that 0.1% of events might be double-counted or missed
- This is fine. "Approximately correct" is the design goal.

The display format "1.2M" means a few thousand double-counts
are invisible anyway.

---

### SECTION 11: HOW TO EXPLAIN THIS IN AN INTERVIEW
### [31:00 — 33:00]
### [SCREEN: 5-phase framework]

---

**[PRESENTER — talking directly to camera]**

If you're using this for interview prep, here's the exact framework to use.

---

**Phase 1: Clarify first — never draw first**

Before touching the whiteboard, ask:

"Does the view count need to be exact, or is approximate OK?"

If they say exact — your whole architecture changes.
You need strong consistency. Much harder, much more expensive.

If they say approximate — you've just unlocked eventual consistency.
That single answer shapes everything else.

Also ask: "What's the staleness tolerance? Seconds? Minutes?"

---

**Phase 2: Do the math before picking tech**

500 million divided by 86,400 = 6,000 writes per second.
Peak: 60,000.

A single PostgreSQL row handles maybe 5,000 writes per second.
Math already rules out direct DB writes.

Do the math. Let the math justify your tech choices.
Don't just say "I'd use Kafka." Say "I'd use Kafka because
direct DB writes fail at 60K writes per second — here's the math."

---

**Phase 3: Design top-down — data flow first**

Don't start with databases.
Start with: "What happens when a user clicks play?"

Walk through the data flow.
Identify what must be fast and what can be async.

Playing the video = must be fast.
Counting the view = can be async.

That distinction drives the entire architecture.

---

**Phase 4: Name your trade-offs before they ask**

After presenting your design, say:
"Let me walk through the weaknesses of this design."

Then name them yourself.
The interviewer can't ambush you with "but what if Redis crashes"
if you already answered it.

---

**Phase 5: Use the 3-part decision statement**

Every tech choice: "I'm choosing X, because Y, and the trade-off is Z,
which is acceptable because W."

"I'm choosing eventual consistency, because synchronous DB writes fail
at 60K writes per second, and the trade-off is 1–2 minutes of staleness,
which is acceptable because we display rounded numbers anyway."

Never say just "I'd use Kafka here."
Always finish the sentence.

---

### OUTRO
### [33:00 — 34:00]

---

**[PRESENTER — talking to camera, relaxed]**

Let's recap what we covered today.

We started with a simple observation: YouTube's view count doesn't update
in real time. And we traced that single design decision all the way through
to a full distributed system.

The core insight: decouple the user experience from the analytics pipeline.
Playing a video and counting a view are two different SLAs.
Design them separately.

We saw how Cassandra writes to an append-only log and never modifies data in place.
We saw how Bigtable separates compute from storage by keeping data in GCS.
We looked at why polyglot persistence is the right call when access patterns differ.
And we walked through the senior trap questions this topic generates.

If you're preparing for a system design interview at staff or architect level —
practice walking through this out loud.
Not reading it. Saying it.
The interviewer is watching how you think, not what you've memorised.

If this was useful, subscribe — I'll be covering more system designs at this level.
Drop a comment if you want me to go deeper on any specific part.

Links to all the written notes are in the description.

See you in the next one.

---
---

## VISUAL PRODUCTION NOTES

### Diagrams to prepare (animations or whiteboard)

1. Scale math on screen: 500M ÷ 86400 = 6K/sec, then 10x = 60K/sec
2. Three failing approaches (animated one by one)
3. Full architecture flow left to right (build it piece by piece as you talk)
4. Cassandra write path: 3 steps animated
5. Cassandra ring: nodes around a circle
6. SSTable pile-up → compaction animation
7. Bigtable: sorted table → tablets → servers
8. Bigtable vs traditional: server crash comparison side by side
9. Trade-off table (builds row by row)
10. Interview 5-phase framework (text on screen as points are made)

### Tone guidance

- Conversational, not lecture-y
- Pause after each concept before moving on
- Use "think of it like..." analogies often
- When showing code/SQL: read it out loud, don't just show it
- Senior trap questions: pause before giving the answer, let the question land first

### B-roll / overlay ideas

- YouTube page with frozen view count (opening)
- Terminal showing Redis INCRBY
- Kafka partition diagram
- Google Cloud Console showing Bigtable
- Whiteboard with ring diagram
