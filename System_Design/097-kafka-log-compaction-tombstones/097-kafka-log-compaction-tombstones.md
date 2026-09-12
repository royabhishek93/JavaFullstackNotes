# Kafka Log Compaction & Tombstones
### How Kafka keeps "latest state per key" topics small forever, without ever deleting a key

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a whiteboard in an office that tracks "current status of every employee" — one row per employee, showing their latest desk assignment. Every time someone moves desks, instead of erasing the old row, a new clerk just writes a fresh row at the bottom of the whiteboard: "Alice → Desk 12", then later "Alice → Desk 45", then later "Alice → Desk 9". The whiteboard is append-only — you're never allowed to erase, only append.

After a year, the whiteboard is covered edge-to-edge with rows, 90% of which are stale — nobody cares that Alice sat at Desk 12 eight months ago. All that matters is her *current* desk. But you still need the history *while it's recent*, in case someone's still catching up.

This is exactly the tension a normal Kafka topic has. A regular topic (`cleanup.policy=delete`) is that append-only whiteboard — it keeps every message for `retention.ms` (say 7 days) and then deletes the *whole segment* once its oldest message ages out, regardless of key.

Now imagine a smarter janitor walks the whiteboard periodically. For every employee name (the *key*), the janitor finds all the rows for that name and erases every row except the **most recent one**. Rows for *different* employees are untouched — nothing about Bob's rows changes just because Alice moved desks. The rows that survive keep their **original position on the whiteboard** (compaction doesn't reorder anything, it just deletes older duplicates in place).

That's log compaction (`cleanup.policy=compact`). The topic still behaves like a log — offsets keep increasing, order is preserved — but the janitor (background compaction thread) periodically removes all-but-the-latest record for each key. The topic converges toward "one row per key, forever," which is exactly what you want for something like a KTable changelog, a config topic, or a "current profile" cache: you don't care about Alice's desk history, you care what desk she's at *right now*, and you want that answer available even if you restart your consumer from scratch and replay the topic from offset 0.

But what if Alice *leaves the company*? You can't just stop writing about her — if you did, her last known desk assignment ("Desk 9") would sit on the whiteboard forever, and the janitor would keep preserving it because it's still "the latest row for that key." You need a special row that means "delete this person's row entirely": a row with the name but a blank/null status. That blank row is a **tombstone**. The janitor keeps the tombstone around for a while (so anyone reading the whiteboard recently still learns "Alice left"), and only after enough time has passed does the janitor erase the tombstone itself, at which point Alice's key vanishes from the whiteboard completely.

---

## PART 2 — THE COMPACTION ARCHITECTURE DIAGRAMS

### Before/After: A Compaction Pass Collapsing Duplicate Keys

```
BEFORE COMPACTION (log segment on disk, offsets in order, uncompacted)
Segment: 00000000000000000000.log   cleanup.policy=compact

Offset | Key        | Value                          | Notes
-------|------------|--------------------------------|------------------
  0    | user-42    | {"name":"Alice","desk":"D12"}  | stale (superseded)
  1    | user-77    | {"name":"Bob","desk":"D3"}     | stale (superseded)
  2    | user-42    | {"name":"Alice","desk":"D45"}  | stale (superseded)
  3    | user-91    | {"name":"Carol","desk":"D8"}   | LATEST for user-91
  4    | user-77    | {"name":"Bob","desk":"D19"}    | stale (superseded)
  5    | user-42    | {"name":"Alice","desk":"D9"}   | LATEST for user-42
  6    | user-77    | {"name":"Bob","desk":"D22"}    | LATEST for user-77

Total: 7 records, 3 unique keys → 4 records are "dirty" (superseded duplicates)
Dirty ratio = dirty_bytes / total_bytes  ≈ 0.57  (57% of the segment is waste)

                              |
                              |  min.cleanable.dirty.ratio = 0.5 exceeded
                              |  → compaction thread picks this segment
                              v

AFTER COMPACTION (new segment, SAME offsets preserved for surviving records)
Segment: 00000000000000000000.log   (rewritten in place)

Offset | Key        | Value                          | Notes
-------|------------|--------------------------------|------------------
  3    | user-91    | {"name":"Carol","desk":"D8"}   | untouched (only value for key)
  5    | user-42    | {"name":"Alice","desk":"D9"}   | survived (was latest)
  6    | user-77    | {"name":"Bob","desk":"D22"}    | survived (was latest)

Total: 3 records, 3 unique keys → 0% dirty
Note: offsets 0,1,2,4 are now GAPS — consumers must tolerate offset gaps!
       Order is preserved (3 < 5 < 6) — compaction never reorders records.
```

### Tombstone Lifecycle: Delete → Retained → Purged

```
STEP 1 — Application deletes a key
──────────────────────────────────
  producer.send(new ProducerRecord<>("user-profiles", "user-42", null));
                                                          ^^^^ null value = TOMBSTONE

  Topic: user-profiles   cleanup.policy=compact,delete.retention.ms=86400000 (24h)

  Offset 5  | key=user-42 | value={"name":"Alice","desk":"D9"} | ts=Day 1, 09:00
  Offset 9  | key=user-42 | value=NULL  (TOMBSTONE)            | ts=Day 1, 15:00
                                                                     ^ write time

STEP 2 — Within 24h of the tombstone: compaction runs, but tombstone is KEPT
──────────────────────────────────────────────────────────────────────────
  Compaction pass at Day 1, 20:00 (5h after tombstone written):
    - Offset 5 (old value for user-42) → REMOVED (superseded by tombstone)
    - Offset 9 (tombstone for user-42) → KEPT (< delete.retention.ms old)

  Segment now:
  Offset 9  | key=user-42 | value=NULL (TOMBSTONE) | ts=Day 1, 15:00
       ^ still visible — any consumer replaying from offset 0 will see
         "user-42 was deleted" and can react (e.g. evict from local cache)

STEP 3 — After delete.retention.ms elapses: tombstone itself is purged
────────────────────────────────────────────────────────────────────
  Compaction pass at Day 2, 16:00 (25h after tombstone written, > 24h threshold):
    - Offset 9 (tombstone) → REMOVED entirely

  Segment now:
  (no record for user-42 at all — key is completely gone from the topic)

  WARNING: if a consumer was offline for > delete.retention.ms and only
  resumes AFTER the tombstone is purged, it will NEVER see the delete —
  it will just see user-42's key silently disappear from future reads,
  and any stale local state (e.g. a KTable store) for user-42 will not
  be told to evict it. This is why delete.retention.ms must be set
  LONGER than your slowest consumer's expected max downtime.
```

### Where Compacted Topics Fit: KTable Changelogs & Config Topics

```
Kafka Streams KTable  ─────────────────────────────────────────────
  KTable<String, UserProfile> table = builder.table("user-profiles");

  Internally: Kafka Streams materializes this as a RocksDB local store
  AND backs it with a Kafka changelog topic:
       user-profiles-STORE-NAME-changelog   cleanup.policy=compact

  Why compacted: if the app crashes and restarts, Kafka Streams
  restores the RocksDB store by replaying the changelog topic from
  offset 0. If it were a normal delete-based topic with 7-day
  retention, any state older than 7 days would be LOST on restore.
  Compaction guarantees "current value per key" survives forever.

Config / Feature-flag topic  ────────────────────────────────────
  Topic: app-config   cleanup.policy=compact
  Key: "feature.new-checkout.enabled"   Value: "true"
  Key: "feature.dark-mode.enabled"      Value: "false"

  Every service instance on startup consumes this topic from offset 0
  to bootstrap its in-memory config, then keeps consuming live updates.
  Compaction keeps the topic small (one record per config key) even
  after years of config changes — no need for a separate DB.

Connect / Schema Registry internal topics  ──────────────────────
  connect-offsets, connect-configs, connect-status,
  _schemas (Confluent Schema Registry)
  → all cleanup.policy=compact for the exact same "latest state" reason
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Topic Configuration: Delete vs Compact vs Both

```bash
# Normal time-based retention (default):
kafka-topics.sh --create --topic order-events \
  --config cleanup.policy=delete \
  --config retention.ms=604800000       # 7 days, then whole segments dropped

# Pure compaction (KTable changelog style — no time-based deletion at all):
kafka-topics.sh --create --topic user-profiles \
  --config cleanup.policy=compact \
  --config min.cleanable.dirty.ratio=0.5 \
  --config delete.retention.ms=86400000 \      # 24h — tombstone survival window
  --config segment.ms=600000 \                 # roll a new segment every 10 min
  --config min.compaction.lag.ms=0             # allow compaction immediately

# Hybrid — compact AND delete (common for changelog topics you also want
# to time-bound, e.g. "keep at most latest value per key, but nothing
# older than 30 days regardless"):
kafka-topics.sh --create --topic session-state \
  --config cleanup.policy=compact,delete \
  --config retention.ms=2592000000
```

### The `min.cleanable.dirty.ratio` Trigger — Why Compaction Isn't Real-Time

```
Kafka does NOT compact on every write. That would be extremely expensive —
every produce would trigger a full segment rewrite. Instead, a background
"log cleaner" thread periodically scans each partition's segments and asks:

    dirty_ratio = dirty_bytes / (dirty_bytes + clean_bytes)

  dirty_bytes = bytes in segments NOT yet compacted (may contain duplicate keys)
  clean_bytes = bytes already known to be compacted (one value per key)

  If dirty_ratio > min.cleanable.dirty.ratio (default 0.5) → segment is
  eligible for compaction, log cleaner thread schedules a compaction pass.

  Key nuance: the ACTIVE segment (the one currently being written to) is
  NEVER compacted — Kafka only compacts closed/rolled segments. This means
  a key's latest value in the active segment can coexist with an older
  duplicate of the same key in an already-compacted older segment, until
  the active segment eventually rolls (segment.ms or segment.bytes) and
  becomes eligible itself.

  Practical implication: "log compaction keeps only the latest value per
  key" is an EVENTUAL guarantee, not an instantaneous one. A consumer
  reading a partition at any given moment MAY see multiple stale values
  for the same key that haven't been compacted away yet — the guarantee
  is about what survives long-term, not about zero duplicates ever.

# Tuning knobs (broker-level defaults, overridable per-topic):
log.cleaner.enable=true                  # must be true (default) for compaction to run
log.cleaner.threads=1                    # parallel compaction threads across all partitions
log.cleaner.min.cleanable.ratio=0.5      # broker-wide default for dirty ratio
log.cleaner.backoff.ms=15000             # how often cleaner checks for eligible segments
```

### Producing a Tombstone (Java) and Consuming It Correctly

```java
// Writing a tombstone — value must be explicitly null, key must be present
// (a null KEY cannot be compacted against anything and is simply dropped
//  by the log cleaner immediately if cleanup.policy=compact).
ProducerRecord<String, UserProfile> tombstone =
    new ProducerRecord<>("user-profiles", "user-42", null);
producer.send(tombstone);

// Consuming: a KTable / KStream sees a tombstone as (key, null)
KStream<String, UserProfile> stream = builder.stream("user-profiles");
stream.foreach((key, value) -> {
    if (value == null) {
        // This is a tombstone — the upstream producer deleted this key.
        localCache.evict(key);
    } else {
        localCache.put(key, value);
    }
});

// Deleting a key from a KTable materialized store (Streams DSL) —
// same mechanism under the hood: emitting null triggers a tombstone
// on the underlying changelog topic, which the RocksDB store then evicts.
KTable<String, UserProfile> table = builder.table("user-profiles");
table.toStream()
     .filter((key, value) -> value == null)   // isolate deletes for logging/audit
     .foreach((key, value) -> log.info("Profile deleted for key={}", key));
```

### Real Numbers: Compaction Cost & Timing

```
Compaction throughput (typical, on spinning/SSD mixed clusters):
  ~20-50 MB/sec per log cleaner thread (I/O bound: read old segment,
  write new compacted segment, fsync, swap file references atomically)

Dirty ratio 0.5 in practice:
  A 1 GB partition with 50% duplicate keys becomes eligible for compaction.
  After compaction: often drops to 200-400 MB depending on key cardinality
  (fewer unique keys = more aggressive shrinkage).

delete.retention.ms default = 86400000 (24 hours):
  Chosen to comfortably outlast typical consumer restart / redeploy windows.
  Bump to 7 days (604800000) for topics consumed by batch jobs that may
  only run once a week, otherwise a weekly batch job can silently miss
  deletes that happened between runs.

segment.ms / segment.bytes (defaults: 7 days / 1 GB):
  Smaller segments = compaction reclaims space faster but more file-handle
  and I/O churn. For high-churn KTable changelogs (e.g. session state
  updated every few seconds), operators commonly lower segment.ms to
  10-30 minutes so stale duplicates get cleaned up faster instead of
  sitting in a not-yet-rolled 7-day segment.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You're building a Kafka Streams application that maintains a `KTable` of current user session state, keyed by session ID, updated frequently. Users log out constantly, and old sessions need to disappear from the table — not just age out after some fixed time. How would you design the underlying topic, and what happens if a consumer instance is down for a few days and comes back?"

**You (architect answer):**

> "For a KTable like this, I'd back it with a topic set to `cleanup.policy=compact` rather than time-based deletion. The core property I need is 'exactly one record per session ID representing its current state' — I don't care about the history of a session, only its latest value, and I need that latest value to survive indefinitely, not expire after 7 days just because nobody touched it.
>
> For logout, I don't do a separate 'delete' API call against some external store — I just produce a record with that session key and a `null` value onto the same topic. That's a tombstone. Kafka's log compaction treats it as 'the latest value for this key is: delete it,' and any KTable materialization built on top of that topic sees the tombstone and evicts the key from its local RocksDB store automatically. The application code doesn't need special-case delete logic beyond 'send null.'
>
> The `delete.retention.ms` setting is the thing I'd pay closest attention to given your scenario of a consumer being down for days. Tombstones aren't purged immediately — they're kept around for `delete.retention.ms` (default 24 hours) specifically so that any consumer, even one that's a bit behind, has a chance to see the delete and react to it. If a consumer instance is down for, say, 3 days, and my `delete.retention.ms` is still the default 24 hours, that instance will come back online, replay the changelog from its last committed offset, and simply never see some of the tombstones that were written and already purged during its downtime. The practical effect: its local KTable state for those sessions never gets evicted — it thinks those sessions are still logged in, silently stale forever until overwritten by a new value for that key.
>
> The mitigation is straightforward: size `delete.retention.ms` around your worst-case consumer downtime, not the 24-hour default. If I expect deploys or incident recovery could take a consumer offline for up to 3 days, I'd set `delete.retention.ms` to something like 7 days, accepting the small extra disk cost of tombstones sticking around longer, in exchange for the correctness guarantee that no consumer misses a delete. I'd also add a periodic reconciliation job — a batch process that compares the KTable's materialized state against the source-of-truth session store — as a belt-and-suspenders check, because relying purely on tombstone timing for a system where 'sessions never wrongly appear active' matters for security is a bit too fragile on its own."

---

## PART 5 — DECISION FRAMEWORK

### Log Compaction vs Time-Based Retention vs Hybrid vs External Store

| Approach | How It Works | Consistency / Tradeoff | Storage Growth | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Time-based delete** (`cleanup.policy=delete`) | Whole segments dropped once oldest record ages past `retention.ms` | Simple; but loses ALL history including still-relevant "latest" values once retention passes | Bounded by time window, unbounded by key count | Low | Loses "current state" for a key if nobody wrote to it recently — bad fit for changelogs |
| **Log compaction** (`cleanup.policy=compact`) | Background cleaner rewrites segments keeping only the latest value per key | "Latest per key forever," but only eventually consistent (active segment never compacted) | Bounded by unique key count × value size, not time | Medium | Unbounded key cardinality (e.g. using a UUID-per-event as key) means compaction never shrinks the topic — no repeated keys to collapse |
| **Hybrid** (`cleanup.policy=compact,delete`) | Compaction reclaims duplicate-key space AND a hard `retention.ms` ceiling still applies | Best of both, but a key can be evicted by the time-based rule even if it's still "the latest value" | Bounded by both key count and hard time ceiling | Medium-High | Silently drops keys nobody re-wrote within `retention.ms`, even though compaction alone would have kept them — surprising if the two policies aren't both understood |
| **External store** (Postgres/Redis as the "latest state" table, Kafka just as the event log) | Kafka topic is `cleanup.policy=delete` for a bounded event log; a consumer materializes "current state" into a real DB/cache | Full query flexibility (indexes, joins), but requires operating and scaling a separate stateful store | Bounded by unique keys in the external store | High (extra infra) | Extra moving part to keep available/consistent; doesn't get "replay from offset 0 restores full state" for free like a compacted topic does |

### When Log Compaction Is the Right Choice

```
Use compaction when:
  ✓ You need "current value per key" semantics, not full history
  ✓ Key cardinality is bounded/reasonable (user IDs, session IDs, config
    keys) — NOT a random UUID or timestamp per event
  ✓ You want free crash recovery: replay topic from offset 0, rebuild
    full state (KTable / RocksDB store / in-memory cache)
  ✓ Deletes are a first-class need (tombstones) and time-based expiry
    alone isn't the semantic you want
  ✓ Building Kafka Streams KTables, config topics, Connect internal
    topics, "latest known state" caches

Skip pure compaction when:
  ✗ Every message is meaningfully unique — an audit log, an event
    stream where you want ALL history, not just "the latest" — use
    cleanup.policy=delete instead
  ✗ Key cardinality is effectively unbounded (compaction can never
    shrink a topic where every key appears exactly once)
  ✗ You need guaranteed hard deletion within a strict SLA — compaction
    timing is best-effort (dirty ratio + segment rolling), not instant

Consider hybrid (compact,delete) when:
  ✓ You want changelog-style "latest per key" behavior but ALSO want a
    hard ceiling on how long an unreferenced key can survive (e.g.
    GDPR-driven max retention regardless of compaction)
```

---

## QUICK REFERENCE CARD

```
TOPIC CONFIG:
  cleanup.policy=compact                 # keep only latest value per key
  cleanup.policy=compact,delete          # compaction + hard time ceiling
  min.cleanable.dirty.ratio=0.5          # (default) dirty% to trigger compaction pass
  delete.retention.ms=86400000           # (default 24h) how long tombstones survive
  segment.ms / segment.bytes             # (defaults 7d / 1GB) active segment never compacted

TOMBSTONE:
  producer.send(new ProducerRecord<>(topic, key, null));   // null VALUE = delete this key
  Requires non-null KEY (null key can't be matched/compacted, dropped immediately)

DIRTY RATIO FORMULA:
  dirty_ratio = dirty_bytes / (dirty_bytes + clean_bytes)
  compaction eligible when dirty_ratio > min.cleanable.dirty.ratio

GUARANTEES:
  ✓ Latest value per key survives indefinitely
  ✓ Offset ordering never changes (only removes older duplicates, in place)
  ✗ NOT instantaneous — active segment excluded, background thread runs on interval
  ✗ NOT a substitute for bounded key cardinality — unbounded keys never shrink

TYPICAL USE CASES:
  KTable changelog topics · config/feature-flag topics ·
  Kafka Connect internal topics (connect-offsets, connect-configs) ·
  Schema Registry _schemas topic
```

---
