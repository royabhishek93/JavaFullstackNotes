# YouTube Script — 10 to 15 Minute Version
# Title: "How YouTube Counts 500 Million Views a Day"
# Reading pace: ~130 words/minute → ~1,800 words for 14 mins
# Style: Simple, conversational, no filler

---

## CHAPTERS

00:00 — Introduction + Hook
01:30 — The scale problem
03:00 — Why the obvious solution fails
04:30 — The real architecture (6 steps)
07:00 — Cassandra and Bigtable internals
10:30 — Which one do you pick?
11:30 — What Flink actually does inside the 30-second window
13:00 — The day YouTube's counter actually broke
14:00 — Outro

---
---

## SCRIPT

---

### INTRODUCTION + HOOK
### [00:00 — 01:30]

---

Hey everyone — I'm Abhishek.

I'm a Java full-stack developer,
and on this channel I break down how real systems work —
not the textbook version, the actual version.
The version that explains why engineers made the choices they made,
and what happens when things go wrong at scale.

Today we're looking at something that's in front of you every time
you open YouTube — the view counter.

---

Open YouTube right now.
Find any video with a million views.
Watch the number.

It doesn't move.

Thousands of people could be watching that video right now.
The number still doesn't move.

Is YouTube broken?

No.
That frozen counter is one of the most deliberate engineering decisions
in the entire platform.

And today I'm going to explain exactly why it works that way —
how 500 million video plays every single day get counted,
why the number you see is always a little behind,
why that's completely intentional,
and what actually happens inside the system when you click play.

By the end of this video you'll understand
Kafka, Flink, Redis, Cassandra, Bigtable —
not as buzzwords, but as pieces of a puzzle
that fit together for a very specific reason.

Let's get into it.

---

### THE SCALE PROBLEM
### [01:30 — 03:00]

---

YouTube gets 500 million video plays every single day.

Divide that by 86,400 seconds in a day —
that's 6,000 view events every second. Just on average.

When something goes viral? You can hit 60,000 to 100,000 events
per second on a single video.

Now ask yourself — what if every one of those events
had to immediately update a counter in a database?

60,000 writes. Per second. On one row.

That's the problem we're solving.

---

### WHY THE OBVIOUS SOLUTION FAILS
### [03:00 — 04:30]

---

The first thing every engineer tries is this:

```sql
UPDATE videos
SET view_count = view_count + 1
WHERE video_id = 'abc';
```

Simple. Clean. Obvious.

Here's what actually happens at 60,000 writes per second.

When this SQL runs, the database puts a lock on that row.
It says — no one else touches this row until I'm done.

While that lock is held, every other writer is waiting in a queue.

60,000 writers. One queue. One row.

Your response time goes from 5 milliseconds to seconds.
Users notice lag. The video player stutters.
The database becomes the bottleneck for your entire platform.

Not because of storage. Not because of network.
Because of one counter.

So the question isn't "how do I update the counter faster."
The real question is: what if I don't update it immediately at all?

That's the shift that unlocks the whole design.

---

### THE REAL ARCHITECTURE
### [04:30 — 07:00]

---

Here's how YouTube actually handles this.

The key insight: playing a video and counting that view
are two completely different jobs.
They don't need to happen at the same time.

So we separate them entirely.

> 🖥️ **[PRESENTATION — Slide 1: Architecture]** Open `presentation/youtube-view-count-slides.html` in Chrome · F11 full screen

Let me walk through each step.

---

**Step 1 — User clicks play. Gets an instant response.**  `[🖱️ CLICK → Client appears]`

The client fires a small event — video ID, session ID, timestamp.
The server receives it, drops it into a queue, and immediately replies with a `202 Accepted`.

The video starts playing in under 200 milliseconds.
The counter hasn't been updated yet. That's fine.
The user's experience is not blocked by counting.

---

**Step 2 — Events go into Kafka.**  `[🖱️ CLICK → Kafka appears]`

Kafka is a durable message queue.
Think of it like a very fast, very safe inbox that never loses messages.

Events are partitioned by video ID — that means all events for the same video go to the same partition,
preserving order. This matters for deduplication and replay.
Events pile up here. Millions per minute.
Even if the processing systems crash, the events stay safe in Kafka.
You can replay them later. That matters — we'll come back to it.

---

**Step 3 — Flink processes in 30-second windows.**  `[🖱️ CLICK → Flink appears]`

Every 30 seconds, Flink reads all the events from Kafka,
groups them by video, and produces one number per video:
"Video ABC had 847 views in the last 30 seconds."

That single number goes to Redis.

Instead of 847 individual database writes —
you do ONE write every 30 seconds.
That's the core optimisation that makes this whole system work.

`[🖱️ CLICK → Slide 2: Flink vs Kafka Streams]`

Now you might ask — why Flink and not Kafka Streams?
Kafka Streams is lighter weight, just a library.
But Flink gives you multi-stream joins — so you can join view events
with user-session data and bot-detection streams simultaneously.
That's how YouTube does fraud filtering.
Simple counting? Kafka Streams is enough.
Fraud detection at YouTube scale? You need Flink.

---

**Step 4 — Redis holds the live counter.**  `[🖱️ CLICK → Redis + Bigtable row appears]`

Redis is an in-memory database — extremely fast.
It has one operation we care about: INCRBY.
"Increase this counter by 847." Done in microseconds.

But here's something worth pausing on —
I said "no locks." Why does Redis not need locks?

Every other database you've used locks a row when updating it.
Two writers arrive at the same time — one waits for the other.
At 60,000 writes per second that queue becomes enormous.

Redis doesn't do that. Here's why.

`[🖱️ CLICK → Slide 3: Redis Single Thread]`

Redis is **single-threaded**.
One thread. One command at a time. In order. Always.

When INCRBY runs — Redis reads the current value, adds the delta,
writes it back. All in one step. No other command runs in between.
There's no second thread that could sneak in and cause a conflict.

In a normal multi-threaded database:
Thread A reads 1000. Thread B reads 1000.
Thread A writes 1001. Thread B writes 1001.
Final count: 1001. But it should be 1002. One write was lost.

In Redis:
Command 1 runs. Completes. Command 2 runs. Completes.
No overlap. No lost writes. No locks needed.

It sounds like a limitation — one thread.
But because Redis is entirely in memory,
that one thread handles over 100,000 operations per second.
Memory is just that fast.

The bank analogy: a multi-threaded database is ten cashiers
sharing one cash drawer — they need a lock on the drawer.
Redis is one cashier with a very long queue —
no lock needed because only one person is ever at the counter.

When someone requests the view count, it comes from Redis.
Sub-millisecond. Every time.

---

**Step 5 — Bigtable stores permanent history.**

Every 5–10 minutes, Redis flushes counts to Bigtable —
a persistent database that stores historical view data by hour.

This is what creator analytics, revenue systems, and legal audits use.
Redis can lose data on restart. Bigtable holds the truth permanently.

---

**Step 6 — CDN caches the read response.**  `[🖱️ CLICK → CDN appears]`  `[🖱️ CLICK → Viewer "1.2M views" appears]`

When a viewer asks "how many views does this video have" —
most of the time that answer comes from a CDN like Cloudflare.
Cached. No database hit at all.

For viral videos: cache valid 30 seconds.
For older videos: cache valid up to an hour.

The result: hundreds of thousands of read requests per second
are absorbed before a single one reaches your backend.

---

### HOW CASSANDRA AND BIGTABLE WORK INTERNALLY
### [07:00 — 10:30]

---

Now let's understand the two main databases in this system.
Bigtable is what YouTube actually uses.
Cassandra is the open-source alternative that many companies use instead.

Both are wide-column stores — built for exactly this kind of
high-write, time-series workload.

Let me explain how each one works inside.

---

#### CASSANDRA

`[🖱️ CLICK → Slide 4: Cassandra Write Path]`

**No boss.**

Most databases have one main server in control.
Cassandra doesn't. Every server is equal. If one goes down, the rest keep working.

**Writing data — 3 steps:**

Step 1 — Write to a diary on disk.  `[🖱️ CLICK → Commit Log appears]`
Before anything else, Cassandra writes your data to a log file.
Even if the server crashes right after this, the data is safe.

Step 2 — Write to memory.  `[🖱️ CLICK → MemTable appears]`
Now it puts the data in RAM — fast and immediately readable.

Step 3 — When memory fills up, save to a file on disk called an SSTable.  `[🖱️ CLICK → SSTable appears]`

**The most important rule**: once an SSTable is written, it is NEVER changed.
If you update a record, Cassandra writes a brand new file.
The old file stays until a cleanup job runs.

This is why writes are so fast — no locking, no finding old rows.
Just: append a new file. Done.

---

**Reading data — the smart skip:**

Over time, dozens of SSTable files pile up.
Checking all of them for every read would be slow.

So each file has a tiny helper called a **Bloom Filter**.
It answers one question: "Is your data definitely NOT in me?"
If yes — skip this file. Don't even open it.

Instead of checking 50 files, you check 2 or 3. Much faster.

---

**Cleanup — Compaction:**  `[🖱️ CLICK → Rule + Compaction + Bloom Filter reveals]`

Old and new versions of the same record end up in different files.
A background job called Compaction merges all the files,
keeps only the newest version, removes deleted data.

Fewer files → faster reads.
Downside: uses CPU while running. Real operational cost.


---

#### BIGTABLE

`[🖱️ CLICK → Slide 5: Bigtable Architecture]`

**One giant sorted table, cut into pieces.**

Imagine a spreadsheet with billions of rows sorted by key.
That's Bigtable.

Too big for one machine — so it's cut into chunks called Tablets.
Each Tablet is handled by a Tablet Server.

**The clever part: the data doesn't live on the Tablet Server.**  `[🖱️ CLICK → GCS box highlights]`
It lives in Google Cloud Storage — completely separately.

Why does this matter?


`[🖱️ CLICK → Crash scenario reveals]`

Traditional database — server crashes, data is stuck on its disk.
You have to copy data to another server. Takes minutes.

Bigtable — server crashes, another server immediately picks up
the Tablets and reads the data from GCS. Already there. Nothing to copy.
Recovery in seconds, not minutes.

The server is just a worker. The data is the important thing.
Swap the worker, keep the data.

---

**Writing data:**

1. Tablet Server receives your write
2. Writes to a shared log in GCS — crash safety
3. Writes to its memory — immediately readable
4. Later: flushes to a file in GCS

Same pattern as Cassandra — log, memory, file.
The difference: those files live in GCS, not on the server's disk.

---

**Scaling:**

When a Tablet grows too big, Bigtable automatically splits it in two
and moves one half to another server.
No downtime. Completely automatic.
That's how Bigtable scales — add servers, split Tablets, spread load.

---

### WHICH ONE DO YOU PICK?
### [10:30 — 11:30]


`[🖱️ CLICK → Slide 6: Pick One]`

Simple answer:

**Pick Bigtable**  `[🖱️ CLICK → Bigtable card appears]` if you're on Google Cloud.
It's fully managed — Google runs it for you.
It integrates natively with the rest of the GCP stack.
YouTube is GCP native — Bigtable is the obvious fit.

**Pick Cassandra** if you're multi-cloud  `[🖱️ CLICK → Cassandra card appears]` or on your own servers.
You're not locked to GCP.
You manage it yourself or pay DataStax to manage it.
Netflix uses Cassandra exactly this way.

Both handle petabyte-scale. Both work for this problem.
The decision comes down to your cloud strategy and your team's expertise.

---

### WHAT FLINK ACTUALLY DOES INSIDE THAT 30-SECOND WINDOW
### [11:30 — 13:00]

---

We keep saying "Flink processes events every 30 seconds."
But what does that actually mean?

Let me show you what's happening inside that window.

`[🖱️ CLICK → Slide 7: Flink Window Internals]`

Imagine 30 seconds of events coming in for one video.
Could be 50 events. Could be 50,000 if it's going viral.

---

**Problem 1 — The same person counted twice.**  `[🖱️ CLICK → Dedup step appears]`

Someone opens the video on their phone. The player fires a view event.
They minimise the app, come back, the player fires again.
Same person. Same video. 10 seconds apart.

Flink deduplicates using the session ID.
Same session ID within 60 seconds — second event is dropped.
The person is counted once.

---

**Problem 2 — Bots sending hundreds of fake events.**  `[🖱️ CLICK → Fraud check appears]`

Flink checks the watch time on every event.
If someone "watched" a 10-minute video but the watch time is zero seconds —
that event is flagged and held for review.

It doesn't block processing. It just doesn't count yet.
The pipeline keeps moving.

---

**Problem 3 — 50,000 events all needing to hit Redis.**  `[🖱️ CLICK → Count + INCRBY appears]`

After deduplication and fraud checks,
Flink doesn't send 50,000 individual writes to Redis.

It groups all valid events by video ID,
counts them up,
and sends ONE number.

"Video ABC. 847 valid views this window."
Redis gets one INCRBY. Not 847.

That single step is why this whole system can handle YouTube's scale.
You take 847 database writes and collapse them into 1.
Do that every 30 seconds for every video.
Suddenly the database isn't sweating at all.

---

**What happens if Flink crashes mid-window?**  `[🖱️ CLICK → Kafka safety net appears]`

This is the clever part.

Those events are still sitting in Kafka.
Kafka keeps everything for 7 days by default.

When Flink comes back up, it just rewinds Kafka
to the last point it successfully processed
and replays from there.

The events were never lost. They were just waiting.
This is why Kafka exists in the system — not just for speed,
but as a safety net for exactly this situation.

---

### THE DAY YOUTUBE'S COUNTER ACTUALLY BROKE
### [13:00 — 14:00]

---

`[🖱️ CLICK → Slide 8: The Day the Counter Broke]`

In December 2012, a song called Gangnam Style by PSY
was breaking every record on the internet.

It became the first video in YouTube history
to hit one billion views.

Then two billion.

And somewhere around 2.1 billion —
YouTube's view counter broke.

It stopped at exactly 2,147,483,647.

That number might look familiar if you've worked with databases.
It's the maximum value of a 32-bit integer.

YouTube had stored the view count as an INT.
An INT can hold up to about 2.1 billion.
Nobody had planned for a single video to ever reach that.

The counter just... stopped.
It couldn't go higher.
The number was too big for the box it was stored in.

YouTube had to stop the counter, fix the data type,
and change the storage from INT to a 64-bit integer — a BIGINT.

A BIGINT can hold up to about 9.2 quintillion.
That number will outlast the internet.

---

This is why in every view count system you build —
you use BIGINT for the counter from day one.
Not because you expect a billion views.
But because you never know.

The system should never be the thing that breaks.
Only the content should go viral. Not your database.

---

### OUTRO
### [14:00 — 14:30]

---

Let's bring it together.

500 million plays a day.
6,000 events every second on average.
100,000 at peak for a viral video.

You can't count that in real time with a simple database write.
So you don't.

Events go into Kafka — safe, durable, replayable.
Flink reads them every 30 seconds, deduplicates,
checks for bots, collapses thousands of events into one number.
Redis holds that number in memory — sub-millisecond reads.
Bigtable holds the permanent truth.
CDN serves 95% of reads without touching the backend at all.

And Cassandra or Bigtable under the hood —
both write fast because they never go back and change old data.
Just append. Always append. Clean up in the background.

The number you see on screen — "1.2M views" —
is approximately 1 to 2 minutes behind real time.
But because it's rounded, you never notice.

That's not a bug. That's the design.

See you in the next one.

---
---

## PRODUCTION NOTES

**Slides in the deck** (all 8 are ready):
1. Architecture flow — Client → Kafka → Flink → Redis → Bigtable → CDN
2. Flink vs Kafka Streams — comparison with code example and trade-offs
3. Redis single-threaded model — multi-thread race condition vs Redis correctness
4. Cassandra 3-step write — diary → memory → file, with Bloom Filter
5. Bigtable architecture — tablets + GCS separation + crash recovery
6. Bigtable or Cassandra — pick one based on cloud strategy
7. Inside the 30-second window — dedup, fraud checks, aggregation steps
8. Gangnam Style overflow — the day the counter broke (32-bit integer limit)

**Tone**: Confident and clear. Speak slightly slower during the architecture section.
Pause after each concept before moving to the next.

**What was cut from the long version**:
- API design details (202 vs 200, heartbeat API, batch API)
- ER diagram and field-level decisions
- Counter sharding for viral videos
- Full fraud detection pipeline
- Senior trap questions (Flink recovery, Redis eviction)
- All 5 tech-choice comparisons (Kafka vs Kinesis, etc.)

**If you want a follow-up video**: The long version covers all of those topics.
This short version is the entry point.
 the next.

**What was cut from the long version**:
- API design details (202 vs 200, heartbeat API, batch API)
- ER diagram and field-level decisions
- Counter sharding for viral videos
- Full fraud detection pipeline
- Senior trap questions (Flink recovery, Redis eviction)
- All 5 tech-choice comparisons (Kafka vs Kinesis, etc.)

**If you want a follow-up video**: The long version covers all of those topics.
This short version is the entry point.
