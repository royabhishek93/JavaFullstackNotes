# URL Shortener: Database Block ASCII Diagram (Interview)

## Scenario
You are asked in an interview:

"Design the data layer for a URL shortener that supports low-latency redirects, URL lifecycle management, and click analytics at scale."

This note gives a production-style database block diagram plus the exact talking points to explain trade-offs.

## High-Level Data Layer

```text
                   +----------------------------------+
                   |         URL Shortener API        |
                   |  (Create / Redirect / Analytics) |
                   +----------------+-----------------+
                                    |
             +----------------------+----------------------+
             |                                             |
             v                                             v
 +---------------------------+                 +-----------------------------+
 | Redis (L1/L2 hot storage) |                 | PostgreSQL (Source of Truth)|
 |---------------------------|                 |-----------------------------|
 | short_code -> long_url    |                 | Table: url_mappings         |
 | long_url -> short_code    |                 | URL metadata + lifecycle    |
 | click counters (optional) |                 | unique short_code           |
 +-------------+-------------+                 +---------------+-------------+
               |                                                 |
               | cache miss / write-through                      | events / batch sync
               v                                                 v
                                            +--------------------------------------+
                                            | Cassandra (Analytics event store)    |
                                            |--------------------------------------|
                                            | Table: click_events                  |
                                            | high-write append-only click stream  |
                                            +--------------------------------------+
```

## Primary Table (PostgreSQL)

```text
+=======================================================================================================+
|                                         TABLE: url_mappings                                           |
+=======================================================================================================+
| Column Name        | Type             | Null | Key/Constraint         | Purpose                       |
|--------------------+------------------+------+------------------------+-------------------------------|
| id                 | BIGSERIAL        | NO   | PK                     | internal surrogate key        |
| short_code         | VARCHAR(10)      | NO   | UNIQUE, indexed        | token used in short URL       |
| long_url           | TEXT             | NO   |                        | destination URL               |
| user_id            | BIGINT           | YES  | indexed                | owner (if authenticated user) |
| created_at         | TIMESTAMP        | NO   | indexed                | creation timestamp            |
| expires_at         | TIMESTAMP        | YES  | indexed                | optional expiry               |
| is_custom_alias    | BOOLEAN          | YES  |                        | true when user chose alias    |
| status             | VARCHAR(20)/ENUM | NO   |                        | ACTIVE / EXPIRED / DELETED   |
| click_count        | BIGINT           | YES  |                        | fallback aggregate count      |
+=======================================================================================================+
```

Indexes:
- UNIQUE idx_short_code on short_code
- idx_user_id on user_id
- idx_created_at on created_at
- idx_expires_at on expires_at

## Analytics Table (Cassandra)

```text
+=======================================================================================================+
|                                         TABLE: click_events                                           |
+=======================================================================================================+
| Column Name   | Type      | Role in Key                     | Purpose                                |
|---------------+-----------+---------------------------------+----------------------------------------|
| short_code    | TEXT      | Partition Key (part 1)          | URL identity                           |
| click_date    | DATE      | Partition Key (part 2)          | keeps partition bounded per day        |
| click_hour    | INT       | Clustering Key (desc)           | hour-level ordering                    |
| click_id      | TIMEUUID  | Clustering Key (desc)           | unique + time ordered event id         |
| ip_address    | TEXT      | non-key                         | client IP                              |
| country       | TEXT      | non-key                         | geo analytics                           |
| device_type   | TEXT      | non-key                         | mobile/desktop/tablet                  |
| browser       | TEXT      | non-key                         | browser analytics                       |
+=======================================================================================================+

Primary Key: PRIMARY KEY ((short_code, click_date), click_hour, click_id)
Clustering Order: (click_hour DESC, click_id DESC)
```

## Read/Write Data Flows

### A) Create Short URL (Write Path)

```text
Client
  |
  v
[Validate URL + security checks + rate limit]
  |
  v
[Check duplicate by long_url]
  |-- found --> return existing mapping
  |
  |-- not found -->
  v
[Generate short_code]
  |
  v
[INSERT into PostgreSQL url_mappings]
  |
  +--> [Warm Redis cache for premium/hot path]
  |
  +--> [Publish creation event for analytics pipeline]
```

### B) Redirect (Read Path)

```text
Client hits /{short_code}
  |
  v
[L1 local cache]
  |-- hit --> return long_url
  |
  |-- miss -->
  v
[L2 Redis]
  |-- hit --> fill L1 and return long_url
  |
  |-- miss -->
  v
[PostgreSQL lookup by short_code + status=ACTIVE]
  |-- not found --> 404
  |-- expired   --> URL expired response
  |
  v
[Fill Redis + L1]
  |
  v
[302/301 redirect to long_url]
  |
  +--> [async click event -> Cassandra]
  +--> [counter updates -> Redis / periodic DB sync]
```

### C) Update/Delete

```text
[Find row by short_code]
  |
  v
[Authorization check]
  |
  +--> update long_url / expires_at
  |      -> save PostgreSQL
  |      -> evict Redis and local cache
  |
  +--> soft delete
         -> status = DELETED
         -> save PostgreSQL
         -> evict caches
```

## Interview-First Talking Points

### Why three data stores?
- PostgreSQL gives strong consistency for critical mapping data.
- Redis reduces redirect latency and shields the primary DB.
- Cassandra absorbs high-volume analytics writes with append-friendly partitions.

### Why do we need click events in a separate DB?
- Redirect requests are read-heavy, but analytics ingestion is write-heavy. Every click can produce an event, so this path grows much faster than URL metadata.
- Click data is naturally time-series-like: each event has a timestamp, and interview queries are usually time-window based (per hour, per day, per campaign).
- Event volume is unbounded. URL mappings are bounded by created short links, but click events keep growing as traffic increases.
- Keeping raw events separate protects the primary transactional table from write amplification, index bloat, and expensive analytics scans.
- A horizontally scalable event store gives predictable performance under spikes and supports high availability through replication.

### Interview way to explain this quickly
- URL mapping is correctness-critical and transactional, so it belongs in PostgreSQL.
- Click events are append-only, high-throughput, and time-oriented, so they belong in a write-optimized distributed store.
- This separation keeps redirects fast, keeps core data clean, and still allows rich analytics and retention policies.

### Why click events are needed (interview-ready)
- A single `click_count` only tells "how many"; click events tell "when, where, how, and by whom".
- Product analytics needs raw events for hourly/day-wise trends, geo breakdown, device/browser split, and campaign attribution.
- Fraud detection needs event-level signals (IP bursts, bot-like patterns, unusual spikes) that aggregate counters cannot provide.
- Billing and premium analytics features depend on accurate, replayable raw event history.
- If aggregate counters are lost or delayed, raw events allow recomputation and backfill.

### 20-second answer you can say in interview
"We store click events because aggregate counts are not enough for real analytics. Event-level data gives time-series insights, fraud detection signals, and replayability for recomputation. Keeping events separate from transactional URL mappings protects redirect latency and lets the analytics pipeline scale independently." 

### Why soft delete with status?
- Prevents accidental hard-loss of mapping records.
- Supports audit/debug and historical investigation.
- Keeps redirect logic simple: allow only status=ACTIVE.

### Collision safety in short code generation?
- Generator aims for uniqueness.
- Database UNIQUE constraint on short_code is the final guardrail.
- On collision, retry code generation and re-insert.

### Expiry handling?
- Keep expires_at nullable for permanent links.
- On read path, enforce expiry check before redirect.
- Optionally run async cleanup jobs to mark EXPIRED.

## Quick Answer Template (60-second interview)

"I keep URL mappings in PostgreSQL as the source of truth with a unique short_code and lifecycle fields like status and expires_at. I place Redis in front for low-latency redirects using short_code to long_url caching, with cache-aside on misses. For analytics, I write click events to Cassandra using a partition key of short_code plus date so write throughput scales and read patterns stay efficient. Redirect flow is cache-first, DB fallback, then cache fill; update/delete invalidates cache; delete is soft via status to preserve auditability."