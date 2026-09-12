# YouTube View Count System Design
### Complete Interview Guide — 15 YOE Architect Level

> **Topic**: How YouTube shows "1.2M views" but doesn't update on every single play
> **Scale**: 500 million daily video plays
> **Core Problem**: Consistency vs Latency trade-off in a high-write distributed counter system
> **Level**: Senior / Staff / Architect Interview

---

## Table of Contents

1. [Big Picture Architecture Diagram](#1-big-picture-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Relationship Diagram](#3-er-relationship-diagram)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Technology Choices — Top 2 per Category](#5-technology-choices--top-2-per-category)
6. [Trade-offs](#6-trade-offs)
7. [Senior Trap Questions (15 YOE Level)](#7-senior-trap-questions-15-yoe-level)
8. [Conversational Interview-Speak](#8-conversational-interview-speak)

---

## 1. Big Picture Architecture Diagram

### Scenario First — Why Does This Architecture Exist?

> A user in Mumbai opens YouTube and clicks play on a video that is simultaneously being watched by 400,000 people.
> If every single click wrote directly to a database, that one video's row would get 400,000 writes per second.
> No relational database row survives that. PostgreSQL row-level locks, MySQL InnoDB, even Redis single-key INCRBY
> would create contention. The user's play must succeed in <200ms regardless of what the count system is doing.
>
> **The key insight**: The act of playing a video (user experience) and the act of counting that view (analytics) are
> two completely different SLA requirements. Decouple them entirely.

---

### ASCII Architecture — Big Picture

```
╔══════════════════════════════════════════════════════════════════════════════════════════════╗
║                        YOUTUBE VIEW COUNT SYSTEM — BIG PICTURE                              ║
╚══════════════════════════════════════════════════════════════════════════════════════════════╝

  ┌─────────────────────────────────────────────────────────────────────────────────────────┐
  │                              CLIENTS (Web / Mobile / Smart TV)                          │
  │   User clicks Play  →  Fire-and-forget POST /view  →  User gets 200 OK immediately      │
  └──────────────────────────────────┬──────────────────────────────────────────────────────┘
                                     │ view events (async)
                                     ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────┐
  │                           INGESTION LAYER                                            │
  │                                                                                      │
  │   ┌─────────────────┐    ┌──────────────────────────────────────────────────────┐   │
  │   │  API Gateway /  │    │              Apache Kafka                            │   │
  │   │  Load Balancer  │───►│  Topic: view-events  |  Partitioned by video_id      │   │
  │   │  (rate limit,   │    │  Retention: 7 days   |  Replication: 3               │   │
  │   │   auth token)   │    │  ~6,000 msg/sec avg  |  ~60,000 msg/sec peak         │   │
  │   └─────────────────┘    └─────────────────────┬────────────────────────────────┘   │
  └─────────────────────────────────────────────────│────────────────────────────────────┘
                                                    │ consume
                                                    ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────┐
  │                        STREAM PROCESSING LAYER                                       │
  │                                                                                      │
  │   ┌─────────────────────────────────────────────────────────────────────────────┐    │
  │   │                    Apache Flink (Stream Processor)                          │    │
  │   │                                                                             │    │
  │   │   ① Deduplicate ──► ② Fraud Fast-path ──► ③ 30s Tumbling Window ──► ④ Emit │    │
  │   │      (session)         (watch_time=0,         (GROUP BY video_id,            │    │
  │   │                         IP rate limit)          count delta)                │    │
  │   └─────────────┬───────────────────────────────────────────────────────────────┘    │
  │                 │                                                                     │
  │          ┌──────┴──────┐                                                              │
  │          │             │                                                              │
  │          ▼             ▼                                                              │
  │   [Fraud Queue]   [Delta Emitter] ────────────────────────────────────────────────   │
  └────────────────────────┬─────────────────────────────────────────────────────────────┘
                           │ write delta (e.g. video_abc: +847 in last 30s)
          ┌────────────────┼──────────────────────┐
          │                │                      │
          ▼                ▼                      ▼
  ┌───────────────┐  ┌──────────────────┐  ┌────────────────────┐
  │     Redis     │  │    Bigtable /    │  │   Fraud Review     │
  │  (Hot Tier)   │  │    Cassandra     │  │   Pipeline (ML)    │
  │               │  │  (Cold Tier /    │  │                    │
  │  INCRBY delta │  │   Authoritative) │  │  Async verdict     │
  │  per video_id │  │  Flush every 5m  │  │  → retroactive     │
  │  ~microsecs   │  │  Source of truth │  │    count adjust    │
  └───────┬───────┘  └──────────────────┘  └────────────────────┘
          │
          │ read (< 1ms)
          ▼
  ┌──────────────────────────────────────────────────────────────────────────────────────┐
  │                            READ / SERVING LAYER                                      │
  │                                                                                      │
  │   ┌──────────────────────────────────────────────────────────────────────────────┐   │
  │   │  CDN (Cloudflare / Akamai)                                                   │   │
  │   │  Cache view count per video_id                                               │   │
  │   │  TTL: 30s (viral)  /  2m (popular)  /  10m (normal)  /  1hr (archive)       │   │
  │   └──────────────────────────────────────────────────────────────────────────────┘   │
  │                    │ HIT: return cached                                               │
  │                    │ MISS: hit Redis → Bigtable → backfill cache                     │
  └──────────────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
  ┌─────────────────────────────────────────────┐
  │  User sees: "1.2M views"                    │
  │  (rounded display hides staleness)          │
  └─────────────────────────────────────────────┘
```

---

### Why This Architecture? — Decision by Decision

| Decision | Why |
|---|---|
| Kafka as ingestion buffer | Absorbs write spikes. Client gets 200 OK without waiting for counting. Replays on downstream failure. |
| Flink for stream processing | Stateful 30s windows with exactly-once semantics. Deduplication state stored in Flink checkpoints. |
| Redis as hot tier | Sub-millisecond INCRBY. Shared across all read servers. Counter sharding for viral videos. |
| Bigtable/Cassandra as cold tier | Persistent, horizontally scalable, append-optimised. Survives Redis restart. Source of truth for analytics. |
| CDN caching of counts | 600K reads/sec would crush Redis. CDN absorbs 95% of reads for popular videos. |
| Rounded display ("1.2M") | Buys cache TTL. Users accept approximation — the format communicates it. |

---

### Cross Questions — Architecture

1. *"Why not use a single Kafka topic partition per video?"* — Cardinality is ~800M videos. Kafka has practical limits of ~200K partitions per cluster. We use hash-based routing to a bounded partition set instead.
2. *"What happens if Kafka consumer lag grows during a spike?"* — Flink auto-scales consumers. Kafka retention (7 days) ensures no data loss during lag. Counts are delayed, not lost.
3. *"How do you handle multi-region?"* — Kafka MirrorMaker 2 replicates events cross-region. Each region has its own Flink + Redis + Bigtable. Global count is reconciled by a separate aggregation job.
4. *"What if Flink crashes mid-window?"* — Flink checkpoints every 10s to durable storage (S3/GCS). On restart, it replays from the last checkpoint offset in Kafka. At-least-once delivery + idempotent Redis INCRBY = correct counts.
5. *"What if Redis restarts?"* — Cold start: Bigtable read rehydrates Redis for the top N active videos. Archive videos stay on Bigtable until first access.

---

## 2. API Design

### Scenario First — Why These APIs?

> Three distinct actors need different things:
> - **The video player** fires a play event and needs instant acknowledgement (write API).
> - **The viewer's browser** needs to display a count and needs a fast, cacheable read (read API).
> - **The creator dashboard** needs accurate, historical, fraud-adjusted counts (analytics API).
>
> Each has a different SLA, different staleness tolerance, and different consistency requirement.
> Designing one "view count API" for all three is a mistake — it would force the slowest SLA on everyone.

---

### API 1 — Record View Event (Write Path)

```
POST /v1/views
Authorization: Bearer <session_token>

Request Body:
{
  "video_id":    "dQw4w9WgXcQ",
  "session_id":  "sess_a3f92b",
  "user_id":     "usr_xyz789",      // null for anonymous
  "client_ts":   1720000000000,      // client-side epoch ms
  "watch_pct":   0,                  // 0 at play start, updated via heartbeat
  "device_type": "mobile",           // mobile | desktop | tv | embed
  "referrer":    "search"            // search | homepage | external | direct
}

Response: 202 Accepted
{
  "event_id": "evt_9a8b7c",
  "status":   "queued"
}
```

**Why 202 Accepted, not 200 OK?**
202 signals "I received it, but processing is async." It's more semantically correct than 200 which implies completion.

**Why not 201 Created?**
We're not creating a resource the caller cares about. 202 = fire-and-forget acknowledgement.

---

### API 2 — Heartbeat / Watch-Time Update

```
PATCH /v1/views/{event_id}/progress
Authorization: Bearer <session_token>

Request Body:
{
  "watch_pct":    45,           // % of video watched so far
  "watch_time_s": 270           // seconds watched
}

Response: 204 No Content
```

**Why a separate heartbeat API?**
Watch time is the primary fraud signal. A view with 0s watch time is likely a bot.
Separating this allows the fraud pipeline to receive watch-time updates asynchronously
without holding up the initial view recording.

---

### API 3 — Get View Count (Public Read Path)

```
GET /v1/videos/{video_id}/view-count
Cache-Control: public, max-age=60       // CDN hint

Response: 200 OK
{
  "video_id":       "dQw4w9WgXcQ",
  "view_count":     1247832910,
  "display_count":  "1.2B",
  "as_of":          "2026-09-09T10:00:00Z",   // timestamp of last update
  "freshness":      "approximate"              // exact | approximate
}
```

**Why return `as_of` and `freshness`?**
Clients can show "updated 2 min ago" or know not to re-request within the TTL window.
Transparency about staleness is better than pretending it's real-time.

---

### API 4 — Creator Analytics (Authoritative Read)

```
GET /v1/creator/videos/{video_id}/analytics/views
Authorization: Bearer <creator_token>
X-SLA-Tier: authoritative                    // bypasses CDN, hits Bigtable directly

Query Params:
  from=2026-09-01T00:00:00Z
  to=2026-09-09T23:59:59Z
  granularity=hour                           // hour | day | week

Response: 200 OK
{
  "video_id": "dQw4w9WgXcQ",
  "period": {
    "from": "2026-09-01T00:00:00Z",
    "to":   "2026-09-09T23:59:59Z"
  },
  "total_views":           1247832910,
  "fraud_adjusted_views":  1244100000,
  "data_points": [
    { "ts": "2026-09-01T00:00:00Z", "views": 54200, "unique_viewers": 49100 },
    { "ts": "2026-09-01T01:00:00Z", "views": 63800, "unique_viewers": 57900 }
  ]
}
```

---

### API 5 — Trending / Batch View Counts (Internal)

```
POST /internal/v1/videos/view-counts/batch
Authorization: Internal-Service <service_token>

Request Body:
{
  "video_ids": ["id1", "id2", "id3", ... "id100"]    // max 100
}

Response: 200 OK
{
  "counts": {
    "id1": { "count": 4200000, "display": "4.2M" },
    "id2": { "count": 980000,  "display": "980K" }
  },
  "as_of": "2026-09-09T10:01:23Z"
}
```

**Why batch?** The home feed renders 20–50 video thumbnails. Individual GET per video = 50 round trips. One batch call = 1 round trip.

---

### API Design Cross Questions

1. *"Why not WebSocket for real-time count updates?"* — WebSocket requires a persistent connection per client. At 2B users, connection overhead is enormous. SSE is better if real-time is needed. But for counts, polling the CDN-cached endpoint is cheaper and simpler.
2. *"How do you handle the view event if the user's network drops after firing?"* — Client retries with the same `session_id`. Flink deduplicates on `session_id` within 60s window. Idempotent.
3. *"What rate limiting do you apply on the view event API?"* — Per-IP: 100 requests/min. Per-user: 10 events/min (heartbeats exempt). API Gateway enforces this before Kafka.
4. *"Why does the creator analytics API bypass CDN?"* — Creators are a small, non-anonymous set. They need fraud-adjusted accurate counts. CDN would serve stale counts — unacceptable for revenue reporting.
5. *"What if `video_id` doesn't exist?"* — The view event API accepts it without validation (validation would require a DB lookup on every play — too slow). Invalid `video_id` events are filtered in Flink using a bloom filter of valid IDs.

---

## 3. ER Relationship Diagram

### Scenario First — Why This Data Model?

> The data model must serve three very different use cases simultaneously:
> - **Real-time writes**: High-frequency, low-latency event ingestion — needs minimal schema, append-only
> - **Hot reads**: Sub-millisecond counter lookups — needs simple key-value structure
> - **Historical analytics**: Time-series aggregation over months — needs a time-bucketed, columnar-friendly schema
>
> A single relational table cannot serve all three. We use polyglot persistence — each store has
> the schema optimised for its access pattern.

---

### Entity Relationship Diagram (ASCII)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                    ER DIAGRAM — YOUTUBE VIEW COUNT SYSTEM                       ║
╚══════════════════════════════════════════════════════════════════════════════════╝

  ┌──────────────────────┐         ┌──────────────────────────────────────┐
  │       VIDEO          │         │           VIEW_EVENT                 │
  │──────────────────────│         │──────────────────────────────────────│
  │ PK  video_id  VARCHAR│ 1    M  │ PK  event_id       VARCHAR           │
  │     title     VARCHAR│◄────────│ FK  video_id       VARCHAR  NOT NULL │
  │     creator_id VARCHAR│         │ FK  user_id        VARCHAR  NULLABLE │
  │     duration_s INT   │         │     session_id     VARCHAR  NOT NULL │
  │     uploaded_at TIMESTAMP      │     client_ts      BIGINT            │
  │     status    ENUM   │         │     server_ts      TIMESTAMP         │
  └──────────────────────┘         │     watch_pct      SMALLINT          │
            │                      │     watch_time_s   INT               │
            │ 1                    │     device_type    ENUM              │
            │                      │     ip_hash        VARCHAR           │
            ▼                      │     referrer       VARCHAR           │
  ┌──────────────────────┐         │     fraud_status   ENUM             │
  │   VIDEO_VIEW_COUNT   │         │       (valid|suspect|rejected)       │
  │──────────────────────│         └──────────────────────────────────────┘
  │ PK  video_id  VARCHAR│                        │
  │     raw_count BIGINT │                        │ M
  │     adj_count BIGINT │                        │
  │     last_upd  TIMESTAMP                       ▼
  │     shard_id  TINYINT│         ┌──────────────────────────────────────┐
  └──────────────────────┘         │         FRAUD_SIGNAL                 │
            │                      │──────────────────────────────────────│
            │                      │ PK  signal_id   VARCHAR              │
            │                      │ FK  event_id    VARCHAR              │
            │                      │     signal_type ENUM                 │
            │                      │       (ip_burst|watch_time|          │
            │                      │        bot_pattern|geo_cluster)      │
            │                      │     confidence  FLOAT                │
            │                      │     created_at  TIMESTAMP            │
            │                      └──────────────────────────────────────┘
            │
            ▼
  ┌──────────────────────────────────────────────────────────┐
  │            VIEW_COUNT_TIMESERIES  (Bigtable/Cassandra)   │
  │──────────────────────────────────────────────────────────│
  │  Row Key:  video_id  +  date_bucket  (YYYYMMDDHH)        │
  │  Columns:                                                 │
  │    raw_delta          BIGINT                              │
  │    adj_delta          BIGINT                              │
  │    unique_viewers     BIGINT                              │
  │    flushed_at         TIMESTAMP                           │
  │  Partitioned by:  video_id  (hash)                        │
  │  Clustered by:    date_bucket  (ascending)                │
  └──────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────┐
  │            REDIS KEY SCHEMA  (In-Memory)                 │
  │──────────────────────────────────────────────────────────│
  │  Key:    video:{video_id}:count:{shard_id}               │
  │  Type:   String (integer)                                │
  │  Value:  cumulative count for this shard                 │
  │                                                          │
  │  Key:    video:{video_id}:count:total   (materialized)   │
  │  Type:   String                                          │
  │  Refreshed: every flush cycle from shard sum             │
  └──────────────────────────────────────────────────────────┘
```

---

### Entity Definitions

| Entity | Store | Purpose | Access Pattern |
|---|---|---|---|
| VIDEO | MySQL/PostgreSQL | Master metadata | Low write, high read |
| VIEW_EVENT | Kafka (raw) | Durable event log | Append-only, never queried directly |
| VIDEO_VIEW_COUNT | Redis | Hot counter, fast reads | High write (INCRBY), high read (GET) |
| VIEW_COUNT_TIMESERIES | Bigtable/Cassandra | Historical analytics | Append write, range scan by date |
| FRAUD_SIGNAL | Kafka + Cassandra | Fraud audit trail | Append write, lookup by event_id |

---

### ER Cross Questions

1. *"Why store VIDEO in MySQL and VIEW_EVENT in Kafka? Why not everything in one DB?"* — Write patterns are fundamentally different. MySQL is optimised for relational queries on video metadata. Kafka is a distributed log optimised for high-throughput append-only writes. Mixing them forces you to accept the worst of both.
2. *"Why have a `shard_id` column in VIDEO_VIEW_COUNT?"* — Redis shards the counter across N keys. The shard_id tracks which keys belong to a video, so the materialization job knows how many shards to sum.
3. *"How do you handle schema migrations on the timeseries table?"* — Bigtable/Cassandra are schema-flexible (wide column). New columns are additive — old rows just have null for new columns. No ALTER TABLE blocking.
4. *"Why not store VIEW_EVENT in a relational DB for fraud queries?"* — At 500M events/day, a relational DB with fraud query indexes would be 100TB+ in months. Kafka is the log; Cassandra is the indexed fraud store.

---

## 4. Sequence Diagrams

### Sequence 1 — User Plays a Video (Write Path)

**Scenario**: A user clicks play on a video. The view is recorded asynchronously without adding latency to the play experience.

```
Client          API Gateway      Kafka         Flink          Redis        Bigtable
  │                  │              │              │              │              │
  │──POST /view──►   │              │              │              │              │
  │   (video_id,     │              │              │              │              │
  │    session_id)   │              │              │              │              │
  │                  │──validate──► │              │              │              │
  │                  │  token       │              │              │              │
  │                  │◄─ ok ──────  │              │              │              │
  │                  │              │              │              │              │
  │                  │──produce ──► │              │              │              │
  │                  │  event msg   │              │              │              │
  │◄── 202 Accepted─ │              │              │              │              │
  │   (instant)      │              │              │              │              │
  │                  │              │              │              │              │
  │                  │              │──consume ──► │              │              │
  │                  │              │   (30s       │              │              │
  │                  │              │    window)   │              │              │
  │                  │              │              │──dedupe ──── │              │
  │                  │              │              │──fraud check │              │
  │                  │              │              │──aggregate   │              │
  │                  │              │              │  delta=847   │              │
  │                  │              │              │              │              │
  │                  │              │              │──INCRBY───►  │              │
  │                  │              │              │   847        │              │
  │                  │              │              │              │              │
  │                  │              │              │ (every 5min) │              │
  │                  │              │              │──────────────────────────►  │
  │                  │              │              │  flush delta │              │
  │                  │              │              │  to timeseries              │
```

**Key observation**: The user gets their 202 in `~20ms`. The count update happens `~30 seconds later`. These two timelines never block each other.

---

### Sequence 2 — User Reads View Count (Read Path)

**Scenario**: The browser renders a video page and needs to display the view count.

```
Browser         CDN             API Server      Redis         Bigtable
  │               │                  │              │              │
  │─GET /count──► │                  │              │              │
  │  video=abc    │                  │              │              │
  │               │                  │              │              │
  │  [CDN HIT]    │                  │              │              │
  │◄─ 200 ──────  │                  │              │              │
  │  "1.2M"       │                  │              │              │
  │  (cached)     │                  │              │              │
  │               │                  │              │              │
  │  [CDN MISS — first request or TTL expired]      │              │
  │               │──forward──────►  │              │              │
  │               │                  │──GET ──────► │              │
  │               │                  │  video:abc   │              │
  │               │                  │              │              │
  │               │  [Redis HIT]     │              │              │
  │               │                  │◄─ 1247832910 │              │
  │               │◄─ 200 ─────────  │              │              │
  │◄─ 200 ──────  │                  │              │              │
  │  "1.2B"       │  (CDN caches it) │              │              │
  │               │                  │              │              │
  │               │  [Redis MISS]    │              │              │
  │               │                  │──SELECT ─────────────────►  │
  │               │                  │  video_count │              │
  │               │                  │◄─────────────────────────── │
  │               │                  │  1247832910  │              │
  │               │                  │──SETEX ────► │              │
  │               │                  │  (warm Redis)│              │
  │               │◄─ 200 ─────────  │              │              │
  │◄─ 200 ──────  │  (CDN caches)    │              │              │
```

---

### Sequence 3 — Fraud Detection (Async Path)

**Scenario**: A suspected bot triggers fraud detection. The count gets retroactively adjusted.

```
Flink           Fraud Queue     ML Pipeline     Redis         Bigtable       Creator Dashboard
  │                  │               │              │              │                 │
  │──suspect ──────► │               │              │              │                 │
  │  event           │               │              │              │                 │
  │                  │──consume ───► │               │              │                 │
  │                  │               │              │              │                 │
  │                  │               │──analyse ─── │              │                 │
  │                  │               │  (bot model) │              │                 │
  │                  │               │              │              │                 │
  │                  │ [VERDICT: BOT]│              │              │                 │
  │                  │               │──DECRBY ───► │              │                 │
  │                  │               │  -1 count    │              │                 │
  │                  │               │              │              │                 │
  │                  │               │──UPDATE ─────────────────►  │                 │
  │                  │               │  adj_count   │              │                 │
  │                  │               │              │              │                 │
  │                  │               │              │              │──notify ───────► │
  │                  │               │              │              │ (event driven)   │
  │                  │               │              │              │ "count adjusted" │
```

---

### Sequence Cross Questions

1. *"What if the client fires the view event but Kafka is down?"* — API Gateway has a local write-ahead buffer (in-memory + local disk). Events are retried with exponential backoff. Max 30-second delay before client gets a 503, but in practice Kafka clusters have 99.99% uptime.
2. *"Can a user game the view count by replaying old session IDs?"* — Flink deduplication window is 60 seconds per session_id. After that window, a replay would count again. This is acceptable — a human re-watching a video is a legitimate view. Bots replaying the same session_id within 60s are filtered.
3. *"What if the fraud ML model is wrong and marks legitimate views as bots?"* — False positives are recoverable. The raw event is preserved in Kafka (7-day retention) and Bigtable audit log. Human review can trigger a recount job from raw events.

---

## 5. Technology Choices — Top 2 per Category

---

### Category A: Message Queue — Kafka vs AWS Kinesis

#### Apache Kafka

```
Open-source distributed log
Partitioned topics → ordered per partition
Consumer groups → parallelism
Retention: configurable (days/weeks)
Replay: any consumer can re-read from any offset
Throughput: millions of msgs/sec per cluster
Latency: ~5ms p99
```

#### AWS Kinesis Data Streams

```
Managed AWS service, serverless feel
Shards = fixed throughput units (1MB/s write, 2MB/s read per shard)
Retention: 1–365 days
Native integration with Lambda, Firehose, S3
Throughput: limited by shard count (manual or auto-scaling)
Latency: ~70ms p99 (higher than Kafka)
```

| Dimension | Kafka | Kinesis |
|---|---|---|
| Throughput | Very high — add brokers | Bounded by shards, resharding is painful |
| Latency | ~5ms | ~70ms |
| Replay | Yes, any consumer, any offset | Yes, but Kinesis iterator API is less flexible |
| Operational overhead | High (ZooKeeper/KRaft, cluster management) | Near zero (fully managed) |
| Cost model | Infrastructure cost | Per-shard-hour + PUT payload units |
| Ecosystem | Kafka Connect, Kafka Streams, Flink | AWS-native: Lambda, Glue, Firehose |
| Schema registry | Confluent Schema Registry | AWS Glue Schema Registry |

**Why Pick Kafka for YouTube View Count?**
- 60,000 msg/sec peak → Kinesis shards would need constant resharding under viral spikes
- Replay capability for fraud reprocessing is critical
- Flink has native Kafka connector with exactly-once semantics
- On-prem / multi-cloud flexibility

**Why Pick Kinesis?**
- Team is AWS-native and doesn't want Kafka operational overhead
- Scale is lower (e.g., 50K events/day, not 500M)
- Want Lambda to process events without managing Flink cluster

**Realistic Example — Kafka Wins**: YouTube, Netflix, Uber — all run Kafka at scale because resharding Kinesis under viral spikes is too slow (minutes) and Kafka scales by adding brokers in seconds.

**Realistic Example — Kinesis Wins**: A startup building analytics for a SaaS product with 10M daily events. No Kafka expertise in-house, all infra on AWS. Kinesis + Firehose + Athena gets them to analytics in a day.

**When to Choose Each**:
- Kafka: >1M msg/sec, multi-consumer replay, on-prem or multi-cloud, need exactly-once with Flink
- Kinesis: AWS-only, team wants managed service, sub-500K msg/sec, deep Lambda/Firehose integration

---

### Category B: Stream Processing — Apache Flink vs Apache Spark Streaming

#### Apache Flink

```
True streaming (event-at-a-time processing)
Stateful operators — state stored in RocksDB locally
Exactly-once guarantees via distributed snapshots (Chandy-Lamport)
Checkpointing to S3/GCS/HDFS
Low-latency: sub-second
Tumbling, Sliding, Session windows
Watermarks for out-of-order events
```

#### Apache Spark Structured Streaming

```
Micro-batch processing (batch intervals: 100ms–minutes)
Unified API: same code for batch and streaming
Strong SQL support via DataFrame API
Spark ecosystem: MLlib, GraphX, Delta Lake
Latency: 100ms–several seconds (micro-batch overhead)
Checkpointing to HDFS/S3
```

| Dimension | Flink | Spark Streaming |
|---|---|---|
| Processing model | True stream (event-at-a-time) | Micro-batch |
| Latency | Sub-second | 100ms to seconds |
| State management | Built-in, RocksDB backend | Limited, external store needed |
| Exactly-once | Native | Supported (more complex setup) |
| API | DataStream / Table API | DataFrame / SQL |
| Learning curve | Steeper | Easier (SQL-first) |
| Ecosystem | Kafka-native | Spark ecosystem (Delta Lake, MLlib) |

**Why Pick Flink for YouTube View Count?**
- 30-second tumbling windows with deduplication state need **stateful stream operators**
- Fraud deduplication within a 60s window is a stateful operation — Flink manages this natively in RocksDB
- Exactly-once is critical for count accuracy
- True streaming means the 30s window fires in exactly 30s, not 30s + batch overhead

**Why Pick Spark Streaming?**
- Team already uses Spark for ML and batch ETL — unified codebase
- Analytics pipeline needs to join streaming data with historical batch data — Delta Lake handles this
- Latency requirements are in the seconds range, not sub-second

**Realistic Example — Flink Wins**: LinkedIn's member activity stream processing uses Flink because it needs sub-second event processing with complex stateful operators (session windows per user across multiple event types).

**Realistic Example — Spark Wins**: An e-commerce company that already runs a Spark-based recommendation engine. Their view count latency requirement is "within 5 minutes" — Spark Structured Streaming with 1-minute micro-batches is simpler and reuses existing Spark infra.

---

### Category C: Hot Counter Storage — Redis vs Memcached

#### Redis

```
In-memory data structure store
Data types: String, Hash, List, Set, ZSet, Bitmap, HyperLogLog, Stream
INCRBY: atomic integer increment (O(1))
Persistence: RDB snapshots + AOF log
Cluster mode: sharding across nodes
Pub/Sub, Lua scripting, Transactions (MULTI/EXEC)
```

#### Memcached

```
Pure in-memory key-value cache
Only String type (byte array)
No persistence
Simple horizontal scaling (consistent hashing client-side)
Multi-threaded (vs Redis single-threaded event loop)
Slightly faster for pure get/set workloads at extreme scale
```

| Dimension | Redis | Memcached |
|---|---|---|
| Data types | Rich (String, Hash, ZSet, Bitmap) | String only |
| Atomic counter | INCRBY natively | CAS needed (not atomic) |
| Persistence | RDB + AOF | None |
| Clustering | Redis Cluster (server-side) | Client-side hashing |
| Pub/Sub | Yes | No |
| Lua scripting | Yes | No |
| Throughput | ~100K ops/sec single node | ~200K ops/sec (multi-threaded) |

**Why Pick Redis for YouTube View Count?**
- `INCRBY` is an atomic integer operation — no CAS loops needed
- Counter sharding pattern (16 keys per video) requires consistent key naming — Redis Cluster handles this
- Persistence (AOF) as secondary safety net if Bigtable rehydration is slow
- HyperLogLog for unique viewer counting without storing every user_id

**Why Pick Memcached?**
- Pure caching use case (no atomic counters needed)
- Team already uses Memcached for session cache
- Slightly better raw throughput for simple get/set

**Realistic Example — Redis Wins**: Twitter uses Redis for the "who's online" presence system and unread count badges. INCRBY + Pub/Sub in a single system.

**Realistic Example — Memcached Wins**: Facebook historically used Memcached at massive scale for purely caching DB query results (no atomic ops needed). TAO eventually replaced it, but Memcached was the right fit when the workload was pure cache, not counters.

---

### Category D: Cold / Authoritative Storage — Cassandra vs Google Bigtable

#### Apache Cassandra

```
Open-source wide-column store (inspired by Google Bigtable)
CQL (Cassandra Query Language) — SQL-like
Masterless architecture (all nodes equal — no SPOF)
Tunable consistency: ONE | QUORUM | ALL
Partition key + clustering key model
Time-series data: append-optimised with TTL support
Self-managed or DataStax managed
```

#### Google Bigtable

```
Google's proprietary wide-column store (the paper that inspired Cassandra)
Fully managed on GCP
Row key + column family + qualifier model
Scales to petabytes, millions of rows/sec
No secondary indexes (row key is the only index)
Integrated with GCP: Dataflow, BigQuery, Pub/Sub
HBase-compatible API
```

| Dimension | Cassandra | Bigtable |
|---|---|---|
| Deployment | Self-managed or DataStax | GCP managed only |
| Consistency | Tunable (eventual to strong) | Eventually consistent (single region) |
| Query model | CQL (flexible filtering) | Row key prefix scan only |
| Secondary indexes | Yes (limited, use with care) | No (row key design is critical) |
| Multi-cloud | Yes | GCP-only |
| Scalability | Petabyte-scale | Petabyte-scale |
| Operational overhead | High (tuning, compaction) | None (fully managed) |

**Why Pick Bigtable for YouTube?**
- YouTube is GCP-native — Bigtable integrates natively with Dataflow (Flink equivalent) and BigQuery
- Fully managed = zero operational overhead
- Row key design `video_id#YYYYMMDDHH` perfectly fits the time-series query pattern

**Why Pick Cassandra?**
- Multi-cloud or on-prem requirements — not locked to GCP
- Need CQL-based flexible queries (e.g., "find all videos with views > X in a time range")
- Team has Cassandra expertise
- Need tunable consistency (QUORUM writes for stronger durability guarantees)

**Realistic Example — Bigtable Wins**: YouTube, Google Analytics — both GCP-native. Bigtable's native Dataflow integration makes the Flink→Bigtable write path trivial.

**Realistic Example — Cassandra Wins**: Netflix uses Cassandra for their view history and playback state. Multi-region, multi-cloud, needs self-managed control over replication topology.

---

### Category E: CDN — Cloudflare vs AWS CloudFront

#### Cloudflare

```
200+ PoPs globally
DDoS protection built-in (up to 200 Tbps mitigation)
Workers: serverless compute at edge (V8 isolates, ~1ms cold start)
Cache-Control respect + custom cache rules
Cache TTL: flexible per URL pattern
Free tier available
Analytics: real-time edge analytics
```

#### AWS CloudFront

```
410+ PoPs globally (more locations)
Deep AWS ecosystem integration (S3, API Gateway, ALB, WAF)
Lambda@Edge: Node.js/Python at edge (heavier than CF Workers, 50ms cold start)
Signed URLs and signed cookies (media access control)
Origin Shield: second-tier cache to reduce origin hits
Tight integration with AWS WAF, Shield Advanced
```

| Dimension | Cloudflare | CloudFront |
|---|---|---|
| Edge locations | 200+ | 410+ |
| Edge compute | CF Workers (V8, fast) | Lambda@Edge (heavier) |
| Ecosystem | Any origin | AWS-native |
| DDoS protection | Best-in-class built-in | Requires Shield Advanced (paid) |
| Pricing model | Flat pricing, predictable | Per-GB transfer + request fees |
| Cache invalidation | Instant via API | ~5–10 seconds |

**Why Pick Cloudflare for YouTube?**
- Cloudflare Workers can run count-formatting logic (`1247832910 → "1.2B"`) at the edge — zero origin hits for count display
- DDoS protection on view events is critical — viral videos attract bot attacks
- Cache invalidation speed: instant (important when fraud correction reduces a count)

**Why Pick CloudFront?**
- Already on AWS: API Gateway + ALB origin, S3 for video segments, CloudFront is the natural fit
- Signed URLs for private video content (CloudFront has native signed URL support)
- Lambda@Edge for A/B testing the count display format

**Realistic Example — Cloudflare Wins**: A media company with origins on multiple clouds (AWS + GCP). Cloudflare is cloud-agnostic and provides a consistent edge layer.

**Realistic Example — CloudFront Wins**: A video platform fully on AWS with S3 for video storage and ALB for API. CloudFront + S3 Origins + Signed URLs = native integration, no extra vendor.

---

## 6. Trade-offs

### Trade-off Matrix

| Decision | Option A | Option B | We Chose | Why |
|---|---|---|---|---|
| Write consistency | Strong (sync DB) | Eventual (async queue) | Eventual | 60K writes/sec makes strong consistency impossible without horizontal sharding that adds complexity |
| Count freshness | Real-time (< 1s) | Approximate (1–2 min) | Approximate | Users accept "1.2M" — rounded display communicates approximation |
| Fraud detection timing | Synchronous (block count) | Asynchronous (retroactive) | Async | Blocking 60K/sec writes on ML inference is not feasible. Retroactive correction is accurate and acceptable |
| Counter storage | Single Redis key | Sharded keys | Sharded | Single key → write hotspot at viral scale. 16 shards reduce contention by 16x |
| Read latency | Fresh from DB | Cached (stale) | Cached | 600K reads/sec would saturate even a Redis cluster. CDN absorbs 95% |
| Creator analytics | Same cache as viewers | Direct DB (no cache) | No cache | Creators need fraud-adjusted accurate counts. Serving them stale data affects revenue trust |

---

### Detailed Trade-off Discussions

#### Trade-off 1: Eventual Consistency — What You Give Up

```
WHAT YOU GAIN:                     WHAT YOU LOSE:
✓ 202 OK in ~20ms                  ✗ Count may show 1.1M when true count is 1.15M
✓ No DB write on critical path     ✗ Brief inconsistency across datacenters
✓ Kafka absorbs viral spikes       ✗ Count can temporarily go backward (fraud removal)
✓ Flink reprocessing is possible   ✗ Creator dashboard requires separate authoritative path
```

**Is this acceptable for YouTube?** Yes. A viewer watching a video does not need exact counts. The creator dashboard is the only place where accuracy matters — and it gets its own direct-to-DB path.

---

#### Trade-off 2: CDN Caching vs Freshness

```
TTL 30 seconds:  99.9% cache hit rate, count up to 30s stale
TTL 5 minutes:   higher hit rate, count up to 5 min stale
TTL 0 (no cache): fresh every time, origin absorbs all traffic

At 600K reads/sec with no cache:
  Redis needs to handle 600K GET/sec → need 6+ Redis nodes just for reads
  Each node costs ~$500-$1000/month
  CDN with 60s TTL → 99% cache hit → Redis sees 6K reads/sec → 1 node

Cost impact of caching: ~85% cost reduction on read infrastructure
```

---

#### Trade-off 3: Counter Sharding Overhead

```
No sharding:
  PRO: Simple — one key per video, easy reads
  CON: Viral video with 100K concurrent viewers → single Redis key bottleneck

16 shards per video:
  PRO: 16x write throughput distribution
  CON: Read = SUM(16 keys) — 16 network round trips OR pipeline command
       Extra memory: 16 keys × 800M videos × 64 bytes = 800 GB (only for active videos)

Practical solution: Shard only videos above a threshold (e.g., >10K views/hour).
Regular videos use a single key. Promotion to sharded mode is triggered by the stream processor.
```

---

## 7. Senior Trap Questions (15 YOE Level)

> These are designed to reveal whether you've actually operated systems at scale,
> or just read about them. Model answers follow each question.

---

### Trap 1: "Your Flink job has been down for 6 hours due to a bug. How do you recover the counts?"

**The Trap**: Junior engineers say "we lost the data." Senior engineers know the data is in Kafka.

**Strong Model Answer**:
> "This is exactly why we chose Kafka with 7-day retention. The view events are in Kafka — they're not lost. Recovery steps:
> 1. Fix the Flink bug, deploy the patched job.
> 2. Reset the Flink consumer group offset back to the point before the failure (6 hours ago).
> 3. Flink replays 6 hours of events — this will run faster than real-time because it's not rate-limited by ingress.
> 4. During replay, Flink writes to a shadow Redis key (e.g., `video:abc:count:recovery`) to avoid double-counting live events.
> 5. Once replay catches up to current offset, we swap the recovery key to primary.
>
> The count will be slightly stale for 6 hours in the displayed UI — we accept this. What we won't do is serve incorrect counts permanently."

---

### Trap 2: "Redis memory usage is growing. The on-call team wants to evict old counters. What's the risk?"

**The Trap**: Redis eviction of a video counter means that counter returns 0 on next read, and the CDN caches "0 views."

**Strong Model Answer**:
> "Evicting a video counter is dangerous without care. If Redis evicts `video:abc:count` for a video with 5M views, the next read returns a Redis MISS, which falls through to Bigtable. But if there's a race condition where the CDN caches the Bigtable result before Flink has flushed the latest delta, the displayed count could be 4.9M instead of 5M — acceptable.
>
> The real risk is if we evict and Redis returns 0 (key not found treated as 0 by the application). That 0 gets cached in CDN for 30s–10 minutes and every user sees '0 views.'
>
> Fix: Never treat a Redis MISS as 0. Always fall through to Bigtable. Also, use a TTL-based eviction policy (LRU) targeted at archive videos, not active ones. A background job can keep counters for the top 1M active videos warm and set `PERSIST` on them — no TTL, no eviction risk."

---

### Trap 3: "The product team wants the count to never go backward — even after fraud removal. How do you handle it?"

**The Trap**: Fraud removal reduces the count, which means it goes backward. The product team is asking for a constraint that conflicts with accuracy.

**Strong Model Answer**:
> "This is a business decision masquerading as a technical one. Let me separate the two:
>
> If the requirement is 'never go backward,' there are two options:
> 1. **Display a high-water mark**: Never decrement the displayed count. Internal fraud-adjusted counts are accurate; the UI shows max(current, previous_max). This is dishonest but technically simple.
> 2. **Delayed display**: Don't show the count to viewers until fraud detection has run (2–5 min delay). This means a video going viral shows no count for the first few minutes — bad UX.
>
> My recommendation: allow decrements but add a 'view count stabilisation' window of 5 minutes for new videos. During this window, show 'loading' or a range ('hundreds of thousands'). After stabilisation, counts are fraud-adjusted and we guarantee they only increase by a small margin.
>
> I'd also push back on the product team — 'never go backward' is not a user trust feature; accurate counts are. If fraud inflates a count and we show it, creators and advertisers lose trust when the real number surfaces."

---

### Trap 4: "Explain how you'd guarantee exactly-once view counting end to end."

**The Trap**: Most candidates say "Flink's exactly-once." But exactly-once in Flink is within the Flink job — it doesn't cover Redis writes, which are outside Flink's transaction boundary.

**Strong Model Answer**:
> "Flink's exactly-once guarantee covers the Kafka-to-Flink-state boundary via distributed snapshots (Chandy-Lamport algorithm). When Flink checkpoints, it atomically records the Kafka offset and the accumulated state.
>
> But the Flink-to-Redis write is NOT covered by Flink's exactly-once. Redis doesn't participate in Flink's 2-phase commit. So in theory, Flink could write to Redis and then crash, then replay the same window and write again — double count.
>
> The solution: use **idempotent Redis writes**, not blind INCRBYs. Instead of:
> `INCRBY video:abc:count 847`
>
> Use a unique window ID in the key:
> `SET video:abc:count:window:1720000030 847 NX` (NX = only if not exists)
>
> If Flink replays window 1720000030, the SET NX is a no-op — window already written. Then a separate job materializes the sum of window keys into the main counter.
>
> This adds complexity, which is why most production systems accept at-least-once for counts and tolerate the ~0.001% double-count error. It's a conscious trade-off."

---

### Trap 5: "Hot partition problem — video_id as Kafka partition key means a viral video's partition gets all the load. How do you handle it?"

**The Trap**: Candidates who say "just add more partitions" miss the point — the problem is one specific partition is hot, not all of them.

**Strong Model Answer**:
> "You're right — if we partition by video_id, a viral video like a World Cup final might generate 500K events/sec, all going to a single Kafka partition. A single partition is limited to roughly 10MB/s or ~50K events/sec.
>
> Solutions:
> 1. **Salted partition key**: Instead of `video_id`, use `video_id + random_suffix(0..15)`. This spreads the viral video's events across 16 partitions. Flink consumers on all 16 partitions aggregate and emit per-video deltas — no ordering guarantee needed for counting.
>
> 2. **Virtual topic**: Detect hot videos via a separate signal (views/min threshold). When a video crosses the threshold, a routing service promotes it to a dedicated high-throughput topic. This is operationally complex but isolates hot videos.
>
> I'd go with option 1 (salted key) because it's simple, Flink handles the re-aggregation natively, and it requires no extra operational work. The downside is that per-partition ordering for a single video is lost — but we don't need ordering for counting; we need it for session deduplication, which Flink handles in state regardless of partition."

---

### Trap 6: "The interviewer asks: 'Your Redis cluster goes down for 10 minutes. Walk me through the blast radius.'"

**Strong Model Answer**:
> "Let me trace what fails:
>
> **Write path**: Flink's INCRBY calls fail. Flink buffers the delta in its own state and retries with exponential backoff. Kafka events are not lost. After Redis recovers, Flink flushes buffered deltas. View counts are stale for 10 minutes — not lost.
>
> **Read path**: CDN cache is still serving cached counts. Viral videos with 30s TTL start returning misses after 30s. The API server's Redis fallback hits Bigtable. Bigtable is ~5–10ms vs Redis's ~1ms, so read latency increases but doesn't fail.
>
> **Creator dashboard**: Uses Bigtable directly — unaffected.
>
> **User impact**: Viewers see counts that are 10–15 minutes stale. Not visible since counts are rounded ("1.2M" doesn't change visibly in 10 minutes for most videos).
>
> **Recovery**: Redis cold start. A background job reads top 1M active video counts from Bigtable and issues SETEX commands to warm Redis. Takes ~2–3 minutes at 10K writes/sec. Normal operation resumes.
>
> Summary: 10-minute Redis outage → degraded latency on reads (Bigtable fallback), stale counts by 10 extra minutes, zero data loss. This is a Tier 2 incident, not a Tier 1."

---

## 8. Conversational Interview-Speak

### How a Strong Candidate Narrates This Design Live

---

**Opening** (when given the problem):
> "Before I draw anything, let me make sure I understand the constraints. You said 500 million daily plays — is that average, or is that peak? And the key question for this system: does the count need to be exact in real-time, or is approximate acceptable — say, within a minute or two? Because that single answer completely changes the architecture."

---

**After getting "approximate is fine"**:
> "Perfect. Then this becomes an eventual consistency problem, not a strong consistency problem. That's a huge unlock. Let me do some quick math before I draw anything.
>
> 500 million divided by 86,400 seconds is roughly 6,000 writes per second average. Add a 10x spike for a viral video and we're at 60,000 writes per second. A single Postgres row with row-level locking handles maybe 2,000 to 5,000 writes per second before contention kills you. So synchronous DB writes are already ruled out just from the math. Redis INCRBY can do 100,000 ops per second, which is closer, but a single key is still a hotspot.
>
> So the core insight is: we separate the act of playing a video from the act of counting it. The user gets their 200 OK immediately. The counting happens asynchronously."

---

**Drawing the write path**:
> "So on the write side, the client fires a POST to record the view — fire and forget. It hits Kafka. Now the user has their response, they don't wait. Kafka gives us two things we really want here: it absorbs the burst — a viral spike doesn't take down the database — and it gives us replay. That replay is actually critical for fraud correction later.
>
> From Kafka, Flink consumes and processes the events. I'm using Flink here specifically because I need stateful stream processing — I need to deduplicate within a 60-second session window, and I need to aggregate counts in 30-second tumbling windows. That statefulness is where Flink wins over something like Spark Streaming, which is micro-batch and adds latency.
>
> Flink's output is not 'write one row per view.' It's 'video_abc had 847 views in the last 30 seconds.' One write to Redis that represents 847 events. That's a 847x write amplification reduction."

---

**When asked about consistency trade-offs**:
> "Yeah, so this is deliberately an AP system — available and partition-tolerant, not consistent. The user sees '1.2M views' which might actually be 1.18M right now. And I think that's the right call for three reasons.
>
> One, the rounded display format communicates approximation — the user doesn't expect '1.2M' to be exact. Two, the alternative — synchronous strong consistency — would require distributed transactions across Kafka, Flink, and Redis, which is a nightmare to operate and adds 200–500ms to every play event. Three, the only consumer who actually needs accuracy is the creator for revenue reporting, and we give them a separate authoritative path that bypasses the cache entirely."

---

**When challenged: "But what if a creator sees their count drop after fraud removal?"**:
> "That's a real tension. My honest take: accurate counts build more creator trust than artificially inflated ones. If we show 10M views, ad revenue is calculated, and then fraud detection says 2M were bots, the creator's revenue gets clawed back. That's worse than showing 8M from the start.
>
> That said, I'd propose a display policy: new videos get a 'stabilisation window' of 5 minutes where we show an approximate range rather than a specific number. After stabilisation, the fraud-adjusted count is final and we only increment going forward. The 'never goes backward' constraint is something I'd negotiate with the product team — it's a trust question, not just a technical one."

---

**Closing the design**:
> "So to summarise the trade-offs in one sentence: we chose high availability and low latency on writes, at the cost of approximately 1–2 minutes of staleness on counts, and we compensate with a rounded display format that makes the staleness invisible to users. The creator analytics path opts out of this trade-off and gets authoritative data. I think that's the right balance for a product like YouTube."

---

### Quick Reference — Interview Phrases to Use

| Situation | Phrase |
|---|---|
| Before starting | "Before I draw, let me clarify the consistency requirement — that one answer changes the entire architecture." |
| After getting requirements | "Let me do back-of-envelope math to validate the tech choices before committing to a design." |
| Justifying Kafka | "Kafka gives me two things I need: burst absorption and replay capability for fraud reprocessing." |
| Justifying eventual consistency | "This is deliberately an AP system. The trade-off is 1–2 minutes of staleness, which is invisible given the rounded display format." |
| On trade-offs | "I'm consciously making this trade-off: [X] for [Y]. The cost is [Z], which is acceptable because [reason]." |
| On weaknesses | "Let me pre-empt the obvious weakness of this design..." |
| On challenges | "That's a good challenge. Let me think through the blast radius..." |

---

## Quick Reference Card

```
╔══════════════════════════════════════════════════════════════════╗
║         YOUTUBE VIEW COUNT — ARCHITECT CHEAT SHEET              ║
╠══════════════════════════════════════════════════════════════════╣
║  Scale:    500M/day = 6K writes/sec avg, 60K peak               ║
║  Pattern:  AP system (Available + Partition-tolerant)            ║
║  Staleness: ~1–2 minutes (acceptable, rounded display hides it) ║
╠══════════════════════════════════════════════════════════════════╣
║  Write:  Client → Kafka → Flink (30s window) → Redis INCRBY     ║
║          + Bigtable flush every 5 min                           ║
║  Read:   CDN (TTL 30s–1hr) → Redis → Bigtable                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Tech Choices:                                                   ║
║    Queue:      Kafka (replay, exactly-once, high throughput)    ║
║    Streaming:  Flink (stateful windows, dedup, exactly-once)    ║
║    Hot store:  Redis (INCRBY, sharded, sub-ms)                  ║
║    Cold store: Bigtable/Cassandra (authoritative, time-series)  ║
║    CDN:        Cloudflare (edge workers, instant invalidation)  ║
╠══════════════════════════════════════════════════════════════════╣
║  Key Trade-offs:                                                 ║
║    Strong consistency → Eventual consistency                    ║
║    Real-time counts → ~1-2 min approximate counts              ║
║    Single Redis key → Sharded keys (viral videos)              ║
║    One API for all → Separate viewer + creator paths           ║
╠══════════════════════════════════════════════════════════════════╣
║  Senior Trap Answers:                                            ║
║    Flink down → replay from Kafka offset                        ║
║    Redis evicted → MISS → Bigtable fallback, never return 0    ║
║    Hot partition → salted key (video_id + shard suffix)        ║
║    Exactly-once → idempotent SET NX with window ID             ║
║    Count goes backward → stabilisation window + honest display ║
╚══════════════════════════════════════════════════════════════════╝

---

## 9. Database Design Decisions — Every Decision Explained

> This section answers the single most important architect interview question:
> **"Why did you choose that database, that schema, that field type — and what did you explicitly reject?"**
>
> Every decision below has a stated reason. If you can't justify it, you don't own the design.

---

### 9.1 The Big Decision — Why Polyglot Persistence?

**Scenario**: An interviewer asks — *"Why not use a single database for everything? Wouldn't that be simpler?"*

**The answer**: Each store in this system has a fundamentally different access pattern. Forcing one DB to serve all patterns means accepting the worst trade-offs of each.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║               WHY NOT ONE DATABASE — DECISION MATRIX                        ║
╠════════════════╦═══════════════════╦═══════════════════╦════════════════════╣
║ Store          ║ Access Pattern    ║ Best Tool         ║ Rejected Tools     ║
╠════════════════╬═══════════════════╬═══════════════════╬════════════════════╣
║ Video metadata ║ Relational reads, ║ MySQL/PostgreSQL  ║ MongoDB (no ACID   ║
║                ║ low write volume, ║                   ║ joins), DynamoDB   ║
║                ║ ACID needed       ║                   ║ (expensive joins)  ║
╠════════════════╬═══════════════════╬═══════════════════╬════════════════════╣
║ View events    ║ Append-only,      ║ Kafka             ║ MySQL (100TB+/yr), ║
║                ║ 6K writes/sec,    ║                   ║ MongoDB (scan      ║
║                ║ stream-consumed   ║                   ║ overhead), S3 only ║
║                ║                   ║                   ║ (no streaming)     ║
╠════════════════╬═══════════════════╬═══════════════════╬════════════════════╣
║ Hot counter    ║ Sub-ms INCRBY,    ║ Redis             ║ PostgreSQL (row    ║
║                ║ 60K writes/sec,   ║                   ║ lock), DynamoDB    ║
║                ║ single-key reads  ║                   ║ (expensive hot     ║
║                ║                   ║                   ║ key throttle)      ║
╠════════════════╬═══════════════════╬═══════════════════╬════════════════════╣
║ Timeseries     ║ Append by time    ║ Bigtable /        ║ PostgreSQL (no     ║
║ analytics      ║ bucket, range     ║ Cassandra         ║ horizontal scale), ║
║                ║ scan by date      ║                   ║ Elasticsearch      ║
║                ║                   ║                   ║ (wrong workload),  ║
║                ║                   ║                   ║ DynamoDB (cost)    ║
╠════════════════╬═══════════════════╬═══════════════════╬════════════════════╣
║ Fraud signals  ║ Append-only,      ║ Cassandra         ║ MySQL (write       ║
║                ║ lookup by event,  ║                   ║ bottleneck),       ║
║                ║ 5–10M writes/day  ║                   ║ Redis (no durable  ║
║                ║                   ║                   ║ audit trail)       ║
╚════════════════╩═══════════════════╩═══════════════════╩════════════════════╝
```

**Interview-speak**:
> *"I'm using polyglot persistence — each store has one job it's best at. The cost is operational complexity: multiple systems to monitor and maintain. I accept that trade-off because forcing one DB to serve all these patterns would mean accepting the worst bottleneck of each pattern simultaneously."*

---

### 9.2 VIDEO Table (MySQL / PostgreSQL) — Every Decision

```sql
CREATE TABLE video (
  video_id     VARCHAR(11)  PRIMARY KEY,   -- YouTube-style base64 ID
  creator_id   VARCHAR(36)  NOT NULL,      -- UUID of channel owner
  title        VARCHAR(100) NOT NULL,
  duration_s   INT          NOT NULL,      -- video length in seconds
  status       ENUM('uploading','processing','published','unlisted','deleted')
               NOT NULL DEFAULT 'uploading',
  uploaded_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_creator   (creator_id),
  INDEX idx_status_ts (status, uploaded_at)
);
```

#### Field-Level Decisions

| Field | Type Chosen | Why This Type | What Was Rejected & Why |
|---|---|---|---|
| `video_id` | `VARCHAR(11)` | YouTube-style base64 (dQw4w9WgXcQ). Opaque, doesn't leak video count, works across distributed systems | `INT AUTO_INCREMENT` — leaks business metrics (competitors count your videos), can't shard across systems |
| `creator_id` | `VARCHAR(36)` | UUID string (globally unique, no central coordinator) | `INT FK` — auto-increment FK requires a central sequence, breaks in multi-region writes |
| `duration_s` | `INT` | Seconds as integer, max ~2.1B sec (~68 years) | `TIME` type — doesn't support videos > 24h; `FLOAT` — floating point precision issues |
| `status` | `ENUM` | Fixed set of states, enforced at DB level, readable in queries | `VARCHAR` — allows typos and unmaintained values; `TINYINT` — opaque, requires lookup table |
| `uploaded_at` | `TIMESTAMP` | Normalized to UTC, supported by all ORMs, indexed for range queries | `BIGINT` epoch — epoch needs manual conversion, confusing in debug queries |

#### Index Decisions

```
idx_creator (creator_id)
  WHY: Creator dashboard queries — "show all my videos"
       SELECT * FROM video WHERE creator_id = 'abc' ORDER BY uploaded_at DESC
  WHY NOT index on title: Title search is delegated to Elasticsearch — a DB full-text
       index on 800M videos would be massive and slower than a search engine index.

idx_status_ts (status, uploaded_at)
  WHY: Content moderation queries — "show all videos in 'processing' status uploaded today"
       SELECT * FROM video WHERE status = 'processing' AND uploaded_at > NOW() - INTERVAL 1 DAY
  WHY composite: status alone has low cardinality (5 values) — covered range scan
       is more efficient than filtering post-index on uploaded_at.
  WHY NOT index on (uploaded_at, status): Cardinality order matters.
       High-cardinality column first = better selectivity per B-tree level.
```

#### Why MySQL/PostgreSQL Over MongoDB Here

```
MongoDB would give flexible schema (good for varying video metadata),
BUT:

  1. ACID transactions needed:
     Status transition (processing → published) must be atomic.
     MongoDB multi-document transactions exist but are slower and more complex.

  2. Relational joins:
     "Get all videos by creators who have > 1M subscribers" requires a join.
     MongoDB $lookup is slower than a SQL JOIN with proper indexes.

  3. YouTube's actual stack: MySQL (with Vitess for sharding).
     MySQL is proven at YouTube's scale with Vitess as the sharding layer.
```

---

### 9.3 VIEW_EVENT Schema (Kafka Message) — Every Decision

```json
{
  "event_id":    "evt_a3f9b2c1",
  "video_id":    "dQw4w9WgXcQ",
  "user_id":     null,
  "session_id":  "sess_782fab",
  "client_ts":   1725868800000,
  "server_ts":   1725868800042,
  "watch_pct":   0,
  "watch_time_s": 0,
  "device_type": "mobile",
  "ip_hash":     "a3f9b2c1d4e5f6...",
  "referrer":    "search",
  "fraud_status": "valid"
}
```

#### Field-Level Decisions

| Field | Decision | Reason |
|---|---|---|
| `event_id` | Application-generated UUID string | Kafka offset is not a stable dedup key across consumer group resets. An application-level event_id enables idempotent processing in Flink regardless of replay. |
| `user_id` | NULLABLE | Anonymous (logged-out) users represent ~30% of views. Forcing a user_id would require fake IDs or rejected events — both wrong. Fraud detection uses `session_id` for anonymous users. |
| `session_id` | NOT NULL | Always generated client-side before the view event fires. Used as the deduplication key in Flink: same session_id within 60s = duplicate. |
| `client_ts` vs `server_ts` | Both present | `client_ts` is the true event time (what happened when). `server_ts` is Kafka ingestion time. Flink uses `client_ts` for event-time windows; `server_ts` for detecting clock-skewed clients (fraud signal: client_ts 10 min ahead of server_ts). |
| `client_ts` type | `BIGINT` (epoch ms) | DB `TIMESTAMP` normalizes to server timezone. Epoch ms preserves the client's exact timestamp, including clock drift data used for fraud analysis. |
| `watch_pct` | `SMALLINT` (0–100) | Integer percentage is sufficient. `FLOAT` introduces comparison precision issues (0.99999 ≠ 1.0). `SMALLINT` is 2 bytes vs 8 bytes FLOAT — saves 6 bytes × 500M events = 3GB/day. |
| `ip_hash` | SHA-256 of (IP + daily salt) | Raw IP is PII under GDPR — cannot store. Hashed IP is still useful for burst detection (same hash = same IP) without reversibility. Daily salt prevents cross-day IP tracking (satisfies GDPR purpose limitation). |
| `device_type` | `ENUM` string | Categorical with < 10 values. `ENUM` in the message schema enforces valid values at event production time — invalid devices are rejected before Kafka. |
| `fraud_status` | `ENUM` (valid \| suspect \| rejected) | Boolean valid/invalid cannot model "under review" state. Three-state ENUM allows the Flink fast path to mark suspects and the slow ML pipeline to later confirm or clear. |

#### Why Kafka, Not a Database, for VIEW_EVENT

```
Scale math:
  500M events/day × 365 days = 182 BILLION rows/year
  At 200 bytes/event = 36 TB/year (raw)

PostgreSQL with 182B rows:
  - B-tree index on video_id would be multi-terabyte
  - VACUUM/autovacuum on append-only table is a known PostgreSQL bottleneck
  - Cannot replay events (no consumer offset model)
  - No native partitioning for stream consumption

Kafka:
  - Designed for exactly this: high-throughput append-only log
  - Consumer offset enables replay (Flink recovery)
  - 7-day retention = 7 × 100GB = 700GB — manageable
  - After Flink consumes, events are archived to cold storage (S3/GCS) for audit
```

---

### 9.4 VIDEO_VIEW_COUNT (Redis) — Every Decision

#### Why Redis INCRBY, Not a DB Counter

```
The write path for view counts:

  Option A — PostgreSQL:
    UPDATE video_view_count SET raw_count = raw_count + 1 WHERE video_id = 'abc';
    → Row-level lock acquired
    → Lock held during disk I/O
    → Next writer waits
    → At 60K writes/sec: queue depth → P99 latency explodes to seconds

  Option B — Redis INCRBY:
    INCRBY video:abc:count 847
    → Single-threaded event loop — no lock needed
    → In-memory — no disk I/O
    → O(1) operation
    → 100K+ ops/sec on a single core
```

#### Key Schema Decisions

```
Single key per video:
  Key:   video:{video_id}:count
  Value: BIGINT counter

  WHY BIGINT: INT max = 2.1B. "Gangnam Style" hit 4B+ views (broke the 32-bit INT YouTube
              counter in 2014). BIGINT max = 9.2 × 10^18. Never overflow.

  PROBLEM:    Viral video with 100K concurrent viewers → all 100K Flink windows
              INCRBY this single key → hot key bottleneck even in Redis.

Sharded keys for viral videos:
  Key:   video:{video_id}:count:shard_{0..15}
  Value: BIGINT partial counter

  Read:  MGET all 16 shard keys → SUM client-side

  WHY 16 shards: 60K peak writes/sec ÷ 16 = 3,750 writes/sec per shard.
                  Redis handles 100K ops/sec — 3,750 is comfortably under limit.

  WHY NOT 64 shards: Read = 64 MGET calls. Redis pipeline reduces this, but
                      16 is the sweet spot: enough distribution, small read overhead.

  WHY String, NOT Redis Hash for shards:
    Hash: HSET video:abc:count shard_0 847 shard_1 612 ...
    PROBLEM: All hash fields on same key = same Redis slot = no distribution benefit.
    String: Each shard is an independent key, distributed across Redis cluster nodes.
```

#### Materialized Total Key

```
Key:   video:{video_id}:count:total
Value: Pre-summed total (refreshed by background job every 30s)

WHY: Read path for the public API needs ONE key lookup, not 16.
     Without this: GET /view-count → MGET 16 keys → SUM → return
     With this:    GET /view-count → GET 1 key → return

     The background aggregation job runs MGET shard_0..15, sums, writes total key.
     Staleness: total key is at most 30s behind the shards — acceptable.
```

---

### 9.5 VIEW_COUNT_TIMESERIES (Bigtable / Cassandra) — Every Decision

#### Row Key Design (Bigtable): `{hash_prefix}#{video_id}#{YYYYMMDDHH}`

```
Why composite row key, not just video_id?
  → Bigtable stores rows sorted by row key (lexicographic).
  → All writes for video "abc" would go to the same tablet (server).
  → At 800M videos × 24 hours = hot tablet containing millions of writes → bottleneck.

Why hash prefix?
  → MD5(video_id)[0:4] prefix randomizes across tablets.
  → "abc" → prefix "f3a1" → tablet F region
  → "xyz" → prefix "2b7c" → tablet 2 region
  → Distributes writes evenly across the tablet fleet.

Why YYYYMMDDHH (hour bucket)?
  Rejected: YYYYMMDD (day)
    → 24h range query returns 1 row — no hourly trend resolution for creators.

  Rejected: YYYYMMDDHHMM (minute)
    → 60× more rows. Most minutes have <100 views for average videos.
    → Bigtable range scans are slower with more rows.
    → Pre-aggregate to hourly in Flink — 60 minutes → 1 row.

  Chosen: YYYYMMDDHH (hour)
    → 24 rows/day/video = 8,760 rows/year/video
    → Range scan "last 30 days" = 720 row reads → fast
    → Fine enough for creator analytics trends.
```

#### Cassandra Partition Key Design

```sql
CREATE TABLE view_count_timeseries (
  video_id      TEXT,
  year_month    TEXT,            -- '2026-09' — partition boundary
  hour_bucket   TIMESTAMP,       -- clustering key
  raw_delta     BIGINT,
  adj_delta     BIGINT,
  unique_viewers BIGINT,
  flushed_at    TIMESTAMP,
  PRIMARY KEY ((video_id, year_month), hour_bucket)
) WITH CLUSTERING ORDER BY (hour_bucket ASC)
  AND default_time_to_live = 7776000;  -- 90 days TTL
```

| Decision | Reason |
|---|---|
| Partition key: `(video_id, year_month)` | `video_id` alone = unbounded partition growth. A 10-year-old video would have 87,660 rows in one partition — Cassandra recommends <100MB per partition. Adding `year_month` caps each partition at 720 rows (30 days × 24 hours). |
| Clustering key: `hour_bucket ASC` | Determines physical sort order on disk. ASC = oldest first. New writes always append to the "end" of the partition — optimized for LSM-tree append writes (no rewrite). Range queries `WHERE hour_bucket BETWEEN X AND Y` leverage sorted order. |
| `CLUSTERING ORDER BY hour_bucket ASC` | Explicitly declared for documentation clarity and to force correct merge order during Cassandra compaction. |
| `default_time_to_live = 7776000` (90 days) | Raw hourly deltas are pre-aggregated to daily/monthly rollups by a background job at 90 days. Cassandra TTL automatically tombstones old data. No manual DELETE needed. Without TTL: partition grows forever. |
| `adj_delta` separate from `raw_delta` | Fraud-adjusted count is a separate column, not an update to raw. This preserves the audit trail: `raw_delta - adj_delta = fraud_views_removed`. Never overwrite raw data. |

#### Why TTL Over Manual Delete

```
Manual DELETE in Cassandra:
  → Creates tombstones (Cassandra marks deletes as special records)
  → Tombstones accumulate until compaction
  → Too many tombstones → ReadTimeout on range scans
  → Tombstone eviction requires full compaction — expensive

TTL:
  → Same tombstone mechanism BUT predictable — evenly distributed over 90 days
  → Cassandra's compaction strategies (TWCS — TimeWindowCompactionStrategy)
     are designed specifically for TTL-heavy timeseries workloads
  → Use TWCS with TTL for this table:
     COMPACTION = { 'class': 'TimeWindowCompactionStrategy',
                    'compaction_window_unit': 'HOURS',
                    'compaction_window_size': 24 }
```

---

### 9.6 FRAUD_SIGNAL Table (Cassandra) — Every Decision

```sql
CREATE TABLE fraud_signal (
  event_id     TEXT,
  signal_type  TEXT,
  confidence   FLOAT,
  created_at   TIMESTAMP,
  reviewed_by  TEXT,           -- null until human review
  resolution   TEXT,           -- null | 'confirmed_fraud' | 'cleared'
  PRIMARY KEY (event_id, signal_type)
);
```

| Decision | Reason |
|---|---|
| `confidence FLOAT` not BOOLEAN | Fraud detection is a probability score from an ML classifier (0.0–1.0). BOOLEAN "is_fraud" discards the confidence value needed for tuning thresholds without re-running classification. |
| `PRIMARY KEY (event_id, signal_type)` | One event can have multiple signal types (ip_burst + watch_time = two rows). Composite PK allows multiple signals per event without collision. |
| Cassandra over MySQL for this table | Fraud signals are purely append-only. Cassandra's LSM-tree write path handles 5–10M appends/day trivially. MySQL InnoDB would require index maintenance on every insert — slower for this access pattern. |
| `reviewed_by` nullable | Most signals are auto-resolved by the ML pipeline. `reviewed_by` is only populated if a human reviewer escalates. Nullable models the common case without a separate "human_review" table join. |

---

### 9.7 Index Strategy — What Was Indexed and Why

```
VIDEO table (MySQL):
  ✅ PRIMARY KEY (video_id)
     Auto-created. All lookups start here.

  ✅ INDEX idx_creator (creator_id)
     Query: "Show all videos for creator X"
     Without: Full table scan on 800M rows.
     With: O(log n) B-tree lookup → range scan on matching rows.

  ✅ INDEX idx_status_ts (status, uploaded_at)
     Query: "Show videos stuck in 'processing' status"
     Composite because: status alone has 5 values (low selectivity) —
     adding uploaded_at creates a covering index for the common query pattern.

  ❌ NO full-text INDEX on title
     Reason: Full-text search on 800M video titles belongs in Elasticsearch.
     A MySQL FULLTEXT index would be multi-GB and still slower than ES for
     fuzzy/ranked search. Single responsibility: MySQL for structured metadata,
     ES for search.

  ❌ NO INDEX on duration_s
     Reason: No production query filters by duration alone.
     "Videos between 5–10 minutes" is a UI filter — applied after creator/status
     filter has already reduced the result set. Low cardinality benefit doesn't
     justify the write overhead of maintaining the index.

VIEW_COUNT_TIMESERIES (Cassandra):
  ✅ PRIMARY KEY ((video_id, year_month), hour_bucket)
     This IS the index. The primary key in Cassandra determines data layout.
     Designed to answer: "Give me hourly views for video X in September 2026."

  ❌ NO secondary index on adj_delta or raw_delta
     Reason: Cassandra secondary indexes are local (per-node), not global.
     Query: "Find all videos with > 1M views in the last hour" would require
     scanning all nodes — effectively a full table scan. This query belongs in
     a separate analytical system (BigQuery / Druid), not Cassandra.

FRAUD_SIGNAL (Cassandra):
  ✅ PRIMARY KEY (event_id, signal_type)
     Designed for: "Get all signals for event_id X" — the only production query.

  ❌ NO index on confidence or signal_type globally
     Reason: "Find all high-confidence fraud signals" is an analytical query
     (fed into ML training pipelines). It runs on Spark/BigQuery against S3 exports,
     not against the operational Cassandra cluster.
```

---

### 9.8 Normalization vs Denormalization — Explicit Decisions

```
╔═══════════════════════════════════════════════════════════════════╗
║          NORMALIZE vs DENORMALIZE — DECISION TABLE                ║
╠═══════════════════════╦═══════════════╦═══════════════════════════╣
║ Entity                ║ Decision      ║ Reason                    ║
╠═══════════════════════╬═══════════════╬═══════════════════════════╣
║ VIDEO                 ║ Normalized    ║ Low write volume.         ║
║                       ║               ║ Data changes propagate    ║
║                       ║               ║ from one row.             ║
║                       ║               ║ JOIN cost is acceptable   ║
║                       ║               ║ at <1K reads/sec on       ║
║                       ║               ║ metadata queries.         ║
╠═══════════════════════╬═══════════════╬═══════════════════════════╣
║ VIDEO_VIEW_COUNT      ║ Denormalized  ║ Counter lifecycle is      ║
║ (Redis)               ║ from VIDEO    ║ independent of video      ║
║                       ║               ║ lifecycle. Joining        ║
║                       ║               ║ VIDEO + count at 600K     ║
║                       ║               ║ reads/sec is unacceptable.║
║                       ║               ║ Counter stands alone.     ║
╠═══════════════════════╬═══════════════╬═══════════════════════════╣
║ VIEW_COUNT_TIMESERIES ║ Denormalized  ║ Bigtable/Cassandra have   ║
║                       ║               ║ no JOIN. All data for a   ║
║                       ║               ║ query must be in one row. ║
║                       ║               ║ raw_delta + adj_delta     ║
║                       ║               ║ duplicates data but       ║
║                       ║               ║ enables single-row reads. ║
╠═══════════════════════╬═══════════════╬═══════════════════════════╣
║ FRAUD_SIGNAL          ║ Denormalized  ║ Append-only audit trail.  ║
║                       ║ from VIEW_EVENT║ Joining back to           ║
║                       ║               ║ VIEW_EVENT for fraud      ║
║                       ║               ║ context is done in        ║
║                       ║               ║ offline ML pipelines,     ║
║                       ║               ║ not online queries.       ║
╚═══════════════════════╩═══════════════╩═══════════════════════════╝
```

---

### 9.9 Replication Factor Decisions

```
Kafka — Replication Factor: 3
  WHY 3, not 2:
    RF=2: Leader + 1 replica. If leader fails during replica lag,
          replica may be behind → message loss.
    RF=3: Leader + 2 replicas. Can lose 1 broker with zero data loss.
    Min In-Sync Replicas (min.insync.replicas) = 2:
          Producer acks=all requires 2 replicas to confirm write.
          Prevents "ghost write" where leader acknowledges but both replicas fail.

Cassandra — Replication Factor: 3 per datacenter
  Write consistency: QUORUM (2/3 must acknowledge)
    WHY QUORUM, not ONE:
      ONE: Fastest write. Risk: if the single acknowledging node fails before
           replication, write is lost. Unacceptable for authoritative count data.
    WHY QUORUM, not ALL:
      ALL: All 3 nodes must acknowledge. If one node is slow/down, write blocks.
           Availability is sacrificed — unacceptable for a write-heavy path.
    QUORUM = (3/2) + 1 = 2 nodes acknowledge.
      Tolerates 1 node failure. Balances availability and durability.

  Read consistency: LOCAL_ONE for timeseries reads
    WHY LOCAL_ONE, not QUORUM:
      Timeseries reads are for creator analytics — slight staleness is acceptable.
      LOCAL_ONE reads from nearest replica = lowest latency.
      QUORUM read would require 2 replicas to agree = higher latency, no benefit
      for analytics use case.

Redis — No replication for counters? Wait, isn't that risky?
  Redis Sentinel / Cluster mode: Each master has 1 replica.
  WHY only 1 replica (not 2):
    Redis counter loss on crash is recoverable from Bigtable (rehydration).
    Over-replicating Redis adds network overhead on every INCRBY.
    The persistence SLA of Redis counters is: "best effort, Bigtable is authoritative."
    Losing 30 seconds of counts on a Redis failover is acceptable.
```

---

### 9.10 Why NOT These Databases (Explicit Rejections)

```
PostgreSQL for view counts:
  REJECTED. Reason:
  UPDATE video_view_count SET count = count + 1 WHERE video_id = 'abc'
  → Row-level write lock on 'abc' row
  → At 60K concurrent writers: every writer serializes through this lock
  → P99 latency = seconds at peak
  → Partitioning doesn't help: hot partition is still one row per video
  → Connection pool exhaustion: 60K writes/sec needs thousands of connections

DynamoDB for timeseries:
  REJECTED. Reason:
  → Write Capacity Units (WCU) pricing: 1 WCU = 1KB/sec
  → 500M events/day × 200 bytes = 100GB/day
  → ~1M WCU required during peak → $0.00065 × 1M = $650/hour = $15,600/day
  → Bigtable pricing: ~$0.17/GB/month → predictable and far cheaper at this scale
  → DynamoDB is excellent at <100K writes/sec for key-value; overkill cost for timeseries

MongoDB for events:
  REJECTED. Reason:
  → MongoDB is a document store — good for variable-schema documents
  → VIEW_EVENT has a fixed schema (no document flexibility needed)
  → MongoDB's WiredTiger engine is not optimised for pure append-only workloads
  → Kafka's log structure is purpose-built: sequential write, partitioned, replayable
  → No consumer offset model in MongoDB (polling needed = added latency)

Elasticsearch for timeseries:
  REJECTED. Reason:
  → ES is optimised for: full-text search, ad-hoc filtering, aggregations on small datasets
  → At 500M events/day, ES index segments grow rapidly
  → Merge operations (segment merging) cause GC pressure and write stalls
  → ES does not have a native compaction-friendly time-series storage model
  → ClickHouse or Druid is the right alternative to Bigtable for non-GCP stacks

ClickHouse / Druid (Honourable Mention — NOT rejected):
  → Strong candidates for the timeseries store if NOT on GCP
  → ClickHouse: Column-oriented, exceptional compression for timeseries,
                SQL-native, used by Cloudflare, Uber, ByteDance at this scale
  → Druid: Used by Lyft, Netflix for real-time analytics with sub-second query latency
  → If the stack is AWS/on-prem, ClickHouse over Bigtable is a legitimate choice
  → Interview answer: "If we weren't GCP-native, I'd evaluate ClickHouse for
                       the timeseries store — it has better query flexibility
                       than Cassandra and comparable write throughput."
```

---

### 9.11 Data Lifecycle — Where Data Lives Over Time

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    DATA LIFECYCLE — VIEW COUNT SYSTEM                    ║
╠══════════════╦══════════════╦══════════════════════════════════════════╣
║ Time         ║ Where        ║ What Happens                              ║
╠══════════════╬══════════════╬══════════════════════════════════════════╣
║ 0–30 seconds ║ Kafka        ║ Raw event sits in Kafka partition         ║
║              ║              ║ (durable, replicated, not yet counted)    ║
╠══════════════╬══════════════╬══════════════════════════════════════════╣
║ 30 seconds   ║ Redis        ║ Flink emits aggregated delta.             ║
║              ║              ║ INCRBY updates hot counter.               ║
║              ║              ║ Public view count is now ~30s stale.      ║
╠══════════════╬══════════════╬══════════════════════════════════════════╣
║ 5–10 minutes ║ Bigtable     ║ Flink flushes hourly bucket delta row.   ║
║              ║              ║ Authoritative count is now up to date.   ║
║              ║              ║ Creator analytics reflects this write.   ║
╠══════════════╬══════════════╬══════════════════════════════════════════╣
║ 7 days       ║ Kafka → S3   ║ Kafka retention expires. Events archived ║
║              ║              ║ to S3/GCS for compliance and ML training.║
╠══════════════╬══════════════╬══════════════════════════════════════════╣
║ 90 days      ║ Bigtable     ║ Hourly rows TTL-expires. Pre-aggregated  ║
║              ║              ║ daily/monthly rollup replaces them.       ║
╠══════════════╬══════════════╬══════════════════════════════════════════╣
║ 1 year+      ║ BigQuery/S3  ║ Monthly rollups offloaded to data        ║
║              ║              ║ warehouse for historical analysis.        ║
╚══════════════╩══════════════╩══════════════════════════════════════════╝
```

---

### 9.12 DB Design Interview-Speak

**When asked "Why did you choose Cassandra/Bigtable?"**:
> *"The timeseries access pattern has two non-negotiables: append-only writes at 500M events/day and range scans by video_id and date range. That rules out PostgreSQL — it can't scale writes horizontally. It rules out DynamoDB — cost at this volume is prohibitive. That leaves Cassandra or Bigtable. I chose Bigtable because we're GCP-native and it integrates natively with Dataflow. If we were multi-cloud, Cassandra would be my pick."*

**When asked "Why not just use one database?"**:
> *"I'd love to — operational simplicity is real value. But the access patterns are fundamentally incompatible. The hot counter needs microsecond atomic increments — that's Redis. The event log needs high-throughput sequential writes with replay — that's Kafka. The timeseries needs range scans by date — that's wide-column storage. Forcing all three into PostgreSQL means I accept the worst trade-off of each pattern simultaneously. Polyglot persistence is the right call here, and I'd accept the operational complexity because it's well-understood: these are all managed services."*

**When asked about index choices**:
> *"I only add an index when I have a specific query that needs it. Every index slows down writes a little — the database has to update the index on every insert. For video metadata, we have low writes and clear query patterns, so a few indexes make sense. But I didn't add a full-text search index on video titles. That kind of search belongs in Elasticsearch — it's much better at it. I try to give each tool one job and not ask a database to do something another system handles better."*

**When asked "Why Cassandra / Bigtable?"**:
> *"We needed two things: write a lot of data fast — 500 million events every day — and also be able to search it by video ID and date. PostgreSQL can't handle that many writes because it doesn't scale out easily. DynamoDB can, but it would cost a fortune at this volume. So we're down to Cassandra or Bigtable. We're already on Google Cloud, so Bigtable was the natural fit — it just plugs in. If we were on AWS or running our own servers, I'd go with Cassandra instead."*

**When asked "Why not just use one database?"**:
> *"I wish we could — fewer systems means less to manage. But each part of this system has a very different job. The counter needs to update in microseconds — Redis is built for that. The view events need to be written fast and replayed later if something breaks — that's exactly what Kafka does. The historical data needs to be queried by date — that's what wide-column stores like Bigtable are good at. If I put all of this into one PostgreSQL database, every part would be fighting the others. I'm adding complexity, yes, but all of these are managed cloud services — so the overhead is much smaller than it sounds."*

---

## 10. How Cassandra and Bigtable Work Internally — Plain English

> This section explains the internals using everyday analogies.
> No jargon without a plain-English explanation right next to it.

---

## CASSANDRA — How It Works Inside

### The Core Idea: No Boss

Most databases have one main server that controls everything.
If that server crashes, everything stops.

Cassandra works differently — **every server is equal**.
There is no "main" server. If one goes down, the rest keep running fine.

```
       Node A ──────── Node B
         │    \      /    │
         │      \  /      │
         │      / \       │
         │    /      \    │
       Node D ──────── Node C

  All nodes are equal.
  Each node talks to the others.
  No single point of failure.
```

---

### Writing Data — Step by Step

When your app saves something, Cassandra does **3 things in order**:

```
Your App sends data
        │
        ▼
┌───────────────────────────────────────────────────────┐
│  STEP 1 — Write to the Diary  (Commit Log)            │
│                                                       │
│  Think of this like a paper diary.                    │
│  Before doing anything else, Cassandra writes         │
│  your data here — straight to disk.                   │
│                                                       │
│  Why? If the server crashes RIGHT NOW,                │
│  the data is still safe on disk.                      │
│  It can be recovered from the diary on restart.       │
└───────────────────────┬───────────────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────┐
│  STEP 2 — Put it in Memory  (MemTable)                │
│                                                       │
│  Now Cassandra puts your data in RAM                  │
│  (the fast memory inside the computer).               │
│                                                       │
│  RAM is much faster than a hard disk.                 │
│  Your data is now readable right away.                │
│                                                       │
│  The MemTable fills up over time (~128 MB).           │
└───────────────────────┬───────────────────────────────┘
                        │
                        │  (when MemTable is full)
                        ▼
┌───────────────────────────────────────────────────────┐
│  STEP 3 — Save to Disk  (SSTable)                     │
│                                                       │
│  Cassandra takes everything in the MemTable           │
│  and writes it to a file on disk called an SSTable.   │
│                                                       │
│  Think of it like saving your Word document           │
│  after typing a lot.                                  │
│                                                       │
│  IMPORTANT: Once an SSTable is written,               │
│  it is NEVER changed.                                 │
│  If you update a record, Cassandra writes             │
│  a BRAND NEW SSTable with the update.                 │
│  The old file stays there until cleanup.              │
└───────────────────────────────────────────────────────┘
```

**Why is this approach fast?**
Cassandra never goes back to change old data.
Every write is just "add a new thing to the end."
No locks. No searching for old rows. Just keep adding.

---

### Reading Data — Step by Step

Reading is a little more complex. Your data might be sitting in memory
OR in any of dozens of files on disk. Cassandra checks them smartly.

```
Your App asks for data
        │
        ▼
┌──────────────────────────────────────────────────────┐
│  CHECK 1 — Look in Memory (MemTable)                 │
│  Newest data lives here. Fast.                       │
└──────────────────────┬───────────────────────────────┘
                       │  not found or need older data
                       ▼
┌──────────────────────────────────────────────────────┐
│  CHECK 2 — Look in Files on Disk (SSTables)          │
│                                                      │
│  PROBLEM: There could be 50 SSTable files.           │
│           Checking all 50 = very slow.               │
│                                                      │
│  SOLUTION 1 — Bloom Filter                           │
│  Each file has a tiny helper called a Bloom Filter.  │
│  It answers one question:                            │
│  "Is your data DEFINITELY NOT in this file?"         │
│                                                      │
│  If YES → skip this file completely                  │
│  If MAYBE → check this file                          │
│                                                      │
│  Result: Instead of checking 50 files,               │
│          you only check 2 or 3 that might have it.   │
│                                                      │
│  SOLUTION 2 — Key Cache                              │
│  Cassandra remembers: "Last time I looked for        │
│  video_abc, it was at position 48291 in SSTable_7."  │
│  Next time: jump straight there. No scanning.        │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
        Merge results from Memory + Files
        (newest write always wins)
                       │
                       ▼
               Return to your App
```

---

### The File Pile-Up Problem (Compaction)

Over time, lots of SSTable files pile up on disk.

```
Day 1:  File_1  File_2  File_3
Day 2:  File_4  File_5  File_6  File_7
Day 3:  File_8  File_9  File_10...

Problems:
  1. Reading gets slower — more files to check
  2. Same record exists in multiple files (old and new versions)
  3. Deleted records are still physically on disk
     (Cassandra marks deletes as "tombstones", not real deletes)
```

**Compaction** is a background job that fixes this:

```
Before compaction:
  File_1: video_abc | hour_00 | views: 1200   ← old version
  File_5: video_abc | hour_00 | views: 1350   ← newer version
  File_9: video_abc | hour_01 | views: 980

After compaction:
  File_merged: video_abc | hour_00 | views: 1350  ← kept newest
               video_abc | hour_01 | views: 980
               (old files deleted from disk)

Result: fewer files → faster reads.
```

**The downside**: Compaction uses CPU and disk while running.
It can slow things down temporarily — this is a real operational challenge.

---

### How Data Spreads Across Servers (The Ring)

Imagine a clock face. All servers sit around the edge of the clock.
Each server "owns" a section of the clock.

```
              Server A
            (owns 0–25%)
          ╱              ╲
   Server D              Server B
 (owns 75–100%)        (owns 25–50%)
          ╲              ╱
            Server C
           (owns 50–75%)
```

When you write `video_abc`:
- Cassandra converts `video_abc` to a number (e.g., 37%)
- 37% falls in Server B's section → sent to Server B

**Adding a new server?**
It just takes a small slice from each existing server.
Only that slice's data moves. Everything else stays where it is.
Much simpler than traditional database migration.

---

### How Servers Know About Each Other (Gossip)

Every second, each server picks 2–3 random neighbours and says:
*"Hey, here's what I know about myself and the servers I've recently talked to."*

Like office gossip — news spreads without a central announcer.

Within a few seconds, all servers know:
- Which servers are alive
- Which servers are down
- Which server owns which section of data

No central coordinator needed for any of this.

---

## BIGTABLE — How It Works Inside

### The Core Idea: One Giant Sorted Table, Cut Into Pieces

Imagine a massive spreadsheet with billions of rows.
Every row is sorted by a key (like an alphabetical dictionary).

That spreadsheet is too big for one computer, so it's cut into chunks.
Each chunk is called a **Tablet**.
Each Tablet is handled by a different server.

```
The whole table (sorted by row key):

  aa#video_123#2026090100  →  views: 1200
  aa#video_123#2026090101  →  views: 1350
  bb#video_456#2026090100  →  views: 450
  cc#video_789#2026090100  →  views: 9800
  ... billions more rows ...

Split into Tablets:

  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │    Tablet 1      │  │    Tablet 2      │  │    Tablet 3      │
  │  rows aa → am    │  │  rows am → bz    │  │  rows ca → zz    │
  │  (Tablet Server 1)│  │  (Tablet Server 2)│  │  (Tablet Server 3)│
  └──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

### Three Roles in Bigtable

```
┌──────────────────────────────────────────────────────┐
│                   MASTER SERVER                      │
│                                                      │
│  Like an air traffic controller.                     │
│  Knows which Tablet Server handles which Tablet.     │
│  Does NOT touch your data directly.                  │
│  Just manages assignments and load balancing.        │
└──────────────────────────────────────────────────────┘
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
  │Tablet Server │ │Tablet Server │ │Tablet Server │
  │      1       │ │      2       │ │      3       │
  │              │ │              │ │              │
  │ Handles reads│ │ Handles reads│ │ Handles reads│
  │ and writes   │ │ and writes   │ │ and writes   │
  │ for Tablet 1 │ │ for Tablet 2 │ │ for Tablet 3 │
  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
         │                │                │
         └────────────────┼────────────────┘
                          │
                          ▼
         ┌─────────────────────────────────┐
         │   Google Cloud Storage (GCS)    │
         │                                 │
         │   THE ACTUAL DATA FILES         │
         │   live here — NOT on the        │
         │   Tablet Server's local disk.   │
         │                                 │
         │   This is Bigtable's            │
         │   biggest design decision.      │
         └─────────────────────────────────┘
```

---

### Writing Data — Step by Step

```
Your App writes: video_abc | 2026-09-01 | views: 847

        │
        ▼
  Your app asks: "Which Tablet Server handles this row?"
  (The answer is cached locally from a metadata lookup)
        │
        ▼
  Tablet Server 2 receives the write
        │
        ├──► Write to Shared Log on GCS   ← crash safety (like the diary)
        │
        └──► Write to Memory (MemTable)   ← data readable immediately
        │
        ▼
  "Done" sent back to your App   ← FAST, before touching any more files
        │
        │  (later, when memory fills up)
        ▼
  MemTable is saved as an SSTable file on GCS
```

---

### The Clever Part: Why Data Lives in GCS, Not on the Server

This is what makes Bigtable really smart.

```
TRADITIONAL approach (data on server's local disk):

  Tablet Server 2 crashes
        │
        ▼
  Tablet 2's data is on its local disk
  STUCK — another server can't access it
  Need to copy data → takes MINUTES

BIGTABLE approach (data in GCS):

  Tablet Server 2 crashes
        │
        ▼
  Master notices immediately
        │
        ▼
  Master assigns Tablet 2 to Tablet Server 4
        │
        ▼
  Tablet Server 4 just reads from GCS
  Data was already there — nothing to copy
  Recovery in SECONDS
```

This is why Bigtable has near-instant recovery. The server is just a worker.
The data is separate. Swap the worker, keep the data.

---

### Reading Data — Step by Step

```
Your App asks for: video_abc, September 2026 data

        │
        ▼
  Tablet Server 2 receives the read
        │
        ├── Check Memory (MemTable)   ← newest data, fastest
        │
        └── Check SSTable files in GCS
              │
              │  Uses Bloom Filters (same idea as Cassandra)
              │  to skip files that definitely don't have the data
              │
              ▼
        Merge: Memory + Files  →  newest write wins
              │
              ▼
        Return to your App
```

---

### What Happens When a Tablet Gets Too Big?

```
Tablet 2 grows to 1 GB (the size limit):

  Before split:
  ┌──────────────────────────────┐
  │         Tablet 2             │
  │     rows am → bz (1 GB)      │
  └──────────────────────────────┘

  After split:
  ┌──────────────────┐  ┌──────────────────┐
  │    Tablet 2a     │  │    Tablet 2b     │
  │  rows am → bn    │  │  rows bn → bz    │
  │ (Tablet Server 2)│  │ (Tablet Server 5)│
  └──────────────────┘  └──────────────────┘

  No downtime. Happens automatically.
  This is how Bigtable scales — add more servers,
  split more tablets, spread the load.
```

---

### Cassandra vs Bigtable — Simple Side-by-Side

```
┌──────────────────────┬───────────────────────────┬──────────────────────────┐
│ Question             │ Cassandra                 │ Bigtable                 │
├──────────────────────┼───────────────────────────┼──────────────────────────┤
│ Is there a boss?     │ No — all servers equal    │ Yes — a Master server    │
│                      │ No single point of failure│ (but it doesn't          │
│                      │                           │  touch your data)        │
├──────────────────────┼───────────────────────────┼──────────────────────────┤
│ Where is data saved? │ On each server's own disk │ In Google Cloud Storage  │
│                      │                           │ (separate from servers)  │
├──────────────────────┼───────────────────────────┼──────────────────────────┤
│ What if a server     │ Other servers take over   │ Master reassigns tablets │
│ crashes?             │ (data was replicated)     │ to another server.       │
│                      │                           │ GCS data is already      │
│                      │                           │ accessible. Seconds.     │
├──────────────────────┼───────────────────────────┼──────────────────────────┤
│ How does it scale?   │ Add new server →          │ Tablet splits →          │
│                      │ ring rebalances            │ spread across servers    │
├──────────────────────┼───────────────────────────┼──────────────────────────┤
│ Do you manage it?    │ Yes (your team manages)   │ No — Google manages it   │
│                      │ or pay DataStax           │ fully                    │
├──────────────────────┼───────────────────────────┼──────────────────────────┤
│ Can you use it on    │ Yes — any cloud or        │ No — GCP only            │
│ any cloud?           │ your own servers           │                          │
├──────────────────────┼───────────────────────────┼──────────────────────────┤
│ Good for             │ Multi-cloud, need control │ GCP stack, zero ops      │
│                      │ over replication topology │ effort, petabyte scale   │
└──────────────────────┴───────────────────────────┴──────────────────────────┘
```

---

### One-Line Summary of Each

**Cassandra**:
Write fast by just adding to files (never changing old ones),
clean up in the background, spread data across equal servers
with no single point of failure.

**Bigtable**:
One huge sorted table cut into pieces, each piece handled by a server,
but the actual data files live separately in Google Cloud Storage —
so if any server dies, another picks up the pieces instantly.
