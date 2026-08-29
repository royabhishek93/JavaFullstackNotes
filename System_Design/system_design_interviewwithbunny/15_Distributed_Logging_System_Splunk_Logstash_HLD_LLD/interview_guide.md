# Distributed Logging Platform — Interview Guide
### (Like Splunk / OpenObserve / Logstash)

> **One-liner to open with:**  
> *"Multi-source ingestion → Kafka buffering → Apache Flink stream processing → Hot/Warm/Cold tiered storage with Elasticsearch for search"*

---

## 1. Functional Requirements

| # | Requirement |
|---|-------------|
| 1 | Ingest logs from multiple sources (FluentBit, OTEL, custom agents) — real-time and batch |
| 2 | Support both real-time streaming and batch/file-upload ingestion |
| 3 | Validate, parse, and normalize logs into a standard JSON structure |
| 4 | User sees logs on dashboard in near real-time (< 5 seconds) |
| 5 | Advanced search — full-text, regex, filters, time-range queries |
| 6 | Real-time log tailing (live tail via WebSocket) |
| 7 | Alerting based on log patterns, thresholds, and anomalies |

---

## 2. Non-Functional Requirements

| Dimension | Target |
|-----------|--------|
| **Scale** | Millions of events/hour, 100K–1M logs/sec sustained |
| **Latency** | < 5s end-to-end; search < 200ms for hot data |
| **Availability** | 99.9% uptime — always available for ingestion |
| **Consistency** | Eventual (AP in CAP) — logs don't need strong consistency |
| **Durability** | No data loss — Kafka RF=3, Cassandra RF=3, S3 cold backup |
| **Retention** | Hot: 14 days → Warm: 45 days → Cold: unlimited (S3) |

---

## 3. Core Entities

```
LogEvent      → The actual log (timestamp, message, level, metadata)
IngestionJob  → Tracks batch/streaming ingestion tasks
Source/Agent  → Log producers (servers, apps, containers) with unique IDs
Client/User   → Organizations with access-controlled log namespaces
AlertRule     → Configured patterns/thresholds that trigger notifications
SearchQuery   → User queries with filters, time ranges, pagination
```

---

## 4. API Design

### Agent Ingestion (FluentBit / OTEL / Custom Agent)
```
POST  /agents/register              → Register new log source/agent
PUT   /agents/{agentId}             → Update agent metadata
GET   /agents/{agentId}/config      → Pull agent configuration
POST  /agents/{agentId}/heartbeat   → Health check from agent
POST  /agents/{agentId}/logs        → Submit logs from agent
```

### File / Offline Ingestion
```
POST  /files/upload                 → Upload log file (batch)
GET   /files/{fileId}/status        → Check file processing status
```

### API-Based Ingestion (Microservices)
```
POST  /logs/ingest                  → Single log ingestion
POST  /logs/batch                   → Batch ingestion (up to 10K logs)
GET   /logs/status/{requestId}      → Get ingestion status
```

### Search & Dashboard
```
POST  /logs/search      (Pagination) → Full-text + regex + filters + time-range
GET   /logs/{logId}                  → Get specific log entry
GET   /logs/tail                     → Live tail (REST polling)
WS    /logs/tail/ws                  → WebSocket for real-time streaming
```

---

## 5. High-Level Design (HLD)

```
┌─────────────┐
│   Clients   │──────────────────────────────────────────────┐
│ (many srcs) │                                              │
└─────────────┘                                              ▼
                                               ┌─────────────────────────┐
                                               │    LB & API Gateway     │
                                               └─────────────────────────┘
                                                /            |            \
                                               ▼             ▼             ▼
                                  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
                                  │  Client      │  │  Ingestion   │  │   Search     │
                                  │  Onboarding  │  │   Service    │  │   Service    │
                                  │  Service     │  └──────┬───────┘  └──────┬───────┘
                                  └──────┬───────┘         │                  │
                                         │                  │                  │
                                         ▼                  ▼                  ▼
                                    ┌─────────┐         ┌───────────────────────┐
                                    │ Client  │         │       Log DB          │
                                    │   DB    │         │  (Cassandra / ES)     │
                                    └─────────┘         └───────────────────────┘
```

---

## 6. Deep Dive Design (LLD)

### Full Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          INGESTION LAYER                                        │
│                                                                                 │
│  Agent Forwarder        ┌─────────────────────────────────────────────┐        │
│  (FluentBit/OTEL/       │              LB & API Gateway               │        │
│   Custom Agent) ───────▶│  • Authentication & Authorization           │        │
│                         │  • Rate Limiting (10K logs/min per client)  │        │
│  FileUpload/Batch ─────▶│  • Routing (Round Robin)                    │        │
│  (Offline Ingest)       └────────────┬──────────────┬─────────────────┘        │
│                                      │              │                           │
└──────────────────────────────────────┼──────────────┼───────────────────────────┘
                                       │              │
                    ┌──────────────────┘              └──────────────────┐
                    ▼                                                     ▼
     ┌──────────────────────┐                             ┌──────────────────────┐
     │  File Ingestion Svc  │                             │  Agent Based Svc     │
     │  (HTTP/multipart)    │                             │  (agent protocols)   │
     └──────────┬───────────┘                             └──────────┬───────────┘
                │                                                     │
                └─────────────────────┐   ┌─────────────────────────┘
                                      ▼   ▼
                              ┌────────────────────┐
                              │       KAFKA         │
                              │  Topics:            │
                              │  • raw_logs         │
                              │  • alert_topic      │
                              └────────┬────────────┘
                                       │
                                       ▼
                              ┌────────────────────┐
                              │   Apache Flink      │
                              │  1. Validation      │
                              │  2. Parse/Normalize │
                              │  3. Enrich          │
                              │  4. Deduplicate     │
                              └───┬──────┬──────────┘
                                  │      │
              ┌───────────────────┘      └───────────────────┐
              ▼                                               ▼
  ┌───────────────────────┐                    ┌──────────────────────────┐
  │    CassandraDB         │                   │     Elasticsearch        │
  │    (Log DB)            │                   │     (14 days hot)        │
  │                        │                   │     Full-text search     │
  │  logs_by_service:      │                   │                          │
  │  • service_name (PK)   │                   │  logs_<date> index:      │
  │  • log_date (PK)       │                   │  • log_id (keyword)      │
  │  • timestamp (CK)      │                   │  • timestamp (date)      │
  │  • log_id (CK)         │                   │  • log_level (keyword)   │
  │  • log_level           │                   │  • message (text/FTS)    │
  │  • message             │                   │  • service_name          │
  │  • host                │                   │  • host, env, namespace  │
  │  • env, namespace      │                   │  • pod_name, trace_id    │
  │  • pod_name, trace_id  │                   └──────────────────────────┘
  │  • TTL: 14 days        │
  │                        │                   ┌──────────────────────────┐
  │  logs_by_traceId:      │──── Cron Svc ────▶│     S3 (Cold Storage)    │
  │  • trace_id (PK)       │    (>45 days)      │  Parquet + Snappy        │
  │  • timestamp (CK)      │                   │  Partitioned by          │
  │  • log_id, service     │                   │  year/month/day/service  │
  │  • log_level, message  │                   │  Query via Athena/Presto │
  └───────────────────────┘                    └──────────────────────────┘
              │
              ▼ (Flink also routes to alert_topic)
  ┌──────────────────────┐
  │     Alert Service    │◀──── AlertPref DB
  │  • Sliding window    │
  │  • Cooldown 10 min   │
  │  • Deduplication     │
  └──────────┬───────────┘
             ▼
  ┌──────────────────────┐
  │  Notification Svc    │──▶ xmatter / email / SMS / pager
  └──────────────────────┘
```

### Client Onboarding Flow (separate)
```
Client ──▶ POST /agents/register
               │
               ▼
  ┌─────────────────────────┐
  │  Client Onboarding Svc  │ ──▶ ClientDB (PostgreSQL)
  │  • Validate email        │     • client_id (uuid PK)
  │  • Check uniqueness      │     • client_name (unique)
  │  • Create namespace      │     • token (JWT)
  │  • Provision ES index    │     • token_ttl
  └─────────────────────────┘     • env (prod/staging/dev)
               │                  • pref (jsonb)
               ▼                  • metadata (jsonb)
  Returns: ClientId + tokenId
```

---

## 7. Storage Schema Details

### Cassandra — logs_by_service (Hot, 14-day TTL)
```
PRIMARY KEY: (service_name, log_date) ← partition key
CLUSTERING:  timestamp DESC, log_id   ← ordering
FIELDS:      log_level, message, host, env, namespace, pod_name, trace_id, metadata
TTL:         14 days (auto-deletes)
```

### Cassandra — logs_by_traceId (Trace correlation)
```
PRIMARY KEY: trace_id
CLUSTERING:  timestamp DESC
FIELDS:      log_id, service_name, log_level, message
```

### Elasticsearch — logs_<date>
```
log_id        → keyword  (unique ID)
timestamp     → date     (range queries, ILM)
log_level     → keyword  (aggregations, filter)
message       → text     (full-text search + analyzer)
service_name  → keyword  (aggregations)
host, env     → keyword
namespace     → keyword  (k8s namespace)
pod_name      → keyword
trace_id      → keyword  (distributed tracing)
```

### AlertRule (PostgreSQL)
```
alert_id             → uuid PRIMARY KEY
client_id            → uuid FK → ClientDB
rule_name            → varchar(255)
condition            → jsonb  ({field: 'log_level', operator: '=', value: 'ERROR', count: 100, window: '5m'})
notification_channels→ jsonb  (['email', 'slack', 'pagerduty'])
is_active            → boolean
cooldown_period      → interval (10 minutes — prevent alert spam)
last_triggered       → timestamp
```

### Hot-Warm-Cold Storage Costs
```
Hot   (0-14 days)  : Cassandra + ES  | SSD   | <200ms  | $0.10/GB/month
Warm  (14-45 days) : Cassandra only  | HDD   | 1-2s    | $0.05/GB/month
Cold  (>45 days)   : S3 Parquet      | Glacier| 10-30s  | $0.01/GB/month

Example: 1TB/day → $3,000/mo (hot only) vs $300/mo (tiered) = 90% savings
```

---

## 8. End-to-End Latency Breakdown

```
Agent → API Gateway          →  50ms  (network + TLS + auth)
API Gateway → Kafka publish  → 100ms  (validation + acks=all)
Kafka → Flink processing     → 500ms  (consumer lag + windowing + enrich)
Flink → Elasticsearch index  → 200ms  (bulk API, 5K batch)
                               ──────
Total p95 latency            → ~850ms  (well within 5s SLA)
```

---

## 9. Key Numbers to Remember

| Metric | Value |
|--------|-------|
| Ingestion rate (peak) | 100K–1M logs/sec |
| Agent batch | 100 logs OR 10 seconds, whichever first |
| Agent local buffer | 10MB disk, 24h retry window |
| Kafka partitions | 100 (keyed by client_id) |
| Flink parallelism | 32 tasks, 100K events/sec each |
| Cassandra writes | 10K/sec per node |
| Elasticsearch search | < 200ms (hot), 1-2s (warm) |
| Flink dedup window | 5-minute tumbling window |
| Flink checkpoints | Every 60s → S3 |
| Kafka replication | RF=3, min.insync.replicas=2, acks=all |
| Cassandra RF | RF=3, QUORUM writes |
| Watermark delay | 5 minutes (handles late-arriving logs) |
| Real-time tail latency | < 1 second log → WebSocket |
| Sampling (DEBUG) | 10% sent, 100% for ERROR/FATAL = 60% volume reduction |

---

## 10. Top Interview Q&A

### Q1: Why Kafka instead of writing directly to the database?

**Answer (4 points):**
1. **Back-pressure** — if DB is slow/down, Kafka buffers millions of logs without data loss
2. **Replay** — reprocess logs if processing logic changes or fails
3. **Multiple consumers** — same stream feeds Cassandra, Elasticsearch, and Alert service independently
4. **Peak smoothing** — 1M logs/sec burst → Kafka absorbs, Flink processes at steady 100K/sec

---

### Q2: Why Cassandra over other databases?

**Answer (4 points):**
1. **Write-optimized** — 10K writes/sec per node (WAL + memtable)
2. **Time-series model** — clustering by timestamp enables efficient range queries
3. **TTL support** — auto-deletes logs without manual cleanup jobs
4. **Linear scalability** — add nodes to scale horizontally

---

### Q3: How do you ensure no log data is lost?

**Answer (5 layers):**
```
1. Kafka        → RF=3, min.insync.replicas=2, acks=all
2. Agent buffer → FluentBit: 10MB local disk, retry 24h with exponential backoff
3. Flink        → Checkpoint every 60s to S3, exactly-once recovery
4. Cassandra    → RF=3, QUORUM writes, tolerates 1 node failure
5. S3           → Immutable cold storage, 11 nines durability
→ Result: At-least-once delivery, duplicates handled by Flink deduplication
```

---

### Q4: How does Flink deduplication work?

**Answer:**
```
1. Tumbling Window  → 5-minute windows
2. Hash Generation  → hash(timestamp_minute + service_name + message[0:100])
3. State Backend    → RocksDB maintains seen-hash set per window
4. Detection        → if hash exists → drop; else → emit downstream
5. State Expiration → window closes, state cleared (prevents unbounded growth)

Trade-off: Catches 99% of duplicates from agent retries.
Cross-window duplicates not detected (acceptable trade-off for state size).
```

---

### Q5: What if Elasticsearch goes down?

**Answer (graceful degradation):**
```
1. Fallback to Cassandra → Search routes to Cassandra, slower (1-2s vs 200ms) but functional
2. Replay queue        → Flink queues bulk index requests in 'es_retry' Kafka topic
3. Cache layer         → Redis caches frequent queries (60s TTL), serves during downtime
4. UI banner           → Show 'Limited search mode', manage user expectations
```

---

### Q6: How do you handle out-of-order logs?

**Answer:**
```
1. Flink Watermarks   → 5-minute watermark delay, late logs included in correct window
2. Cassandra ordering → Clustering by timestamp maintains chronological order per query
3. ES @timestamp      → Range-indexed, UI sorts correctly even if processed out-of-order
4. Grace period       → Accepts logs up to 10 min late; extremely late → DLQ

Trade-off: 5-min watermark delays alerting but ensures 99.9% correct window placement
```

---

### Q7: How do you handle log spikes during incidents?

**Answer:**
```
1. Kafka absorption  → Buffers 1M+ logs, absorbs burst without loss
2. Auto-sampling     → Spike detected → DEBUG drops to 1%, INFO to 10%, ERROR stays 100%
3. Rate limiting     → Token bucket, 10K logs/min per client (prevents one service choking system)
4. Alert dedup       → Top-K algorithm → "Top 10 error types" not individual alert per error
```

---

### Q8: How does real-time log tailing work?

**Answer:**
```
1. Client opens WebSocket → WS /logs/tail/ws with filters {service, level}
2. Backend creates Kafka Consumer Group → unique group per WebSocket connection
3. Consumer Interceptor → filters matching logs before sending over WebSocket
4. Backpressure → buffer last 100 messages in-memory, drop oldest if client slow
5. Heartbeat → ping/pong every 30s to detect disconnects
6. Reconnect → client stores last log timestamp, reconnects with 'since' param to resume
```

---

### Q9: How does query routing work across storage tiers?

**Answer:**
```
Query range          → Storage hit
─────────────────────────────────────────────
last 14 days         → Elasticsearch only  (<200ms)
14–45 days           → Cassandra only      (1-2s)
> 45 days            → S3 via Athena       (10-30s)
cross-tier (e.g. 60d)→ Fan-out ES + Cassandra + S3 in parallel, merge results

Cassandra optimization: Always include partition key (service_name, log_date) in WHERE
Athena optimization:    Parquet partitioned by year/month/day, scans only needed partitions
```

---

### Q10: How do you avoid alert fatigue?

**Answer (6 techniques):**
```
1. Aggregation    → Alert on 'ERROR count >100 in 5 min', not every ERROR (100x noise reduction)
2. Cooldown       → Don't re-alert same condition for 10 min (configurable)
3. Severity       → P0 (page now) / P1 (email+Slack) / P2 (Slack) / P3 (daily digest)
4. Deduplication  → Same fingerprint (service + error_type) → grouped summary, not flood
5. Escalation     → P1 unacknowledged in 15 min → auto-escalate to P0
6. Rate limiting  → Max 10 alerts per service per hour
```

---

### Q11: How do you handle schema evolution when log formats change?

**Answer (6-point backward-compatible strategy):**
```
1. Schema Registry     → maintain version history; agents send schema_version with each log
2. Multi-version Flink → parsers for v1/v2/v3, routes to correct parser by version field
3. ES dynamic mapping  → new fields auto-detected and indexed with default types
4. Default values      → missing fields → null (optional) or 'UNKNOWN' (required) during processing
5. Parallel validation → run old + new parsers in parallel for 7 days, validate outputs match
                         before deprecating old parser
6. Deprecation window  → old fields kept for 90 days with 'deprecated' flag; clients have
                         time to upgrade agents

Example: Add 'request_id' field → Flink auto-maps to ES, old logs show null,
         queries work seamlessly across old and new logs.
```

---

### Q12: What is your data retention and archival strategy?

**Answer:**
```
Three-tier lifecycle:
  Hot   (0-14 days)  → Cassandra + ES  | SSD   | <200ms  | $0.10/GB/month
  Warm  (14-45 days) → Cassandra only  | HDD   | 1-2s    | $0.05/GB/month
  Cold  (>45 days)   → S3 Parquet      | Glacier| 10-30s  | $0.01/GB/month

Cron job (daily at 2 AM UTC):
  → ILM moves ES indices to warm tier
  → Exports Cassandra rows to S3 as Parquet (Snappy compressed, 3:1 ratio)
  → Deletes archived rows from Cassandra

Retention enforcement:
  → Per-client policy stored in ClientDB.pref (e.g., retain_days=90)
  → Soft delete (marked deleted) for 7 days → then hard delete across all tiers
  → GDPR: purge specific user logs across all tiers on deletion request
  → Audit trail: deletion events logged for compliance verification

Example: 1TB/day → $3,000/mo (hot only) vs $300/mo (tiered) = 90% savings
```

---

## 11. Critical "Never Do" Rules  ⚠️

| Rule | Why |
|------|-----|
| NEVER write logs directly to Elasticsearch during ingestion | ES downtime = data loss; always buffer through Kafka first |
| NEVER return 200 after Kafka publish synchronously waiting for ES | Ingestion latency spikes from 200ms to 2s; return 202 Accepted immediately |
| NEVER do full table scan in Cassandra (SELECT * without partition key) | Query hits all nodes, takes minutes, can crash cluster under load |
| NEVER skip ILM in Elasticsearch | Indices grow unbounded, cluster runs out of disk |
| NEVER use strong consistency for logs | Unnecessary overhead; eventual consistency (AP) is the right trade-off |

---

## 12. Scaling Techniques Summary

| Technique | Detail |
|-----------|--------|
| Kafka partitioning | 100 partitions by client_id, each ~1K msg/sec |
| ES sharding | 10 primary + 1 replica per daily index, auto-scales |
| Cassandra clustering | Partition by (service_name, log_date), 10K writes/node |
| Flink parallelism | 32 parallel tasks, horizontal scaling |
| ILM (ES) | Daily rollover, auto-moves warm tier, deletes old |
| Batch aggregation | 100 logs / 10s window → 100x fewer API calls |
| Snappy compression | 3:1 ratio in Kafka and S3 |
| Query cache (ES) | 60s TTL → 80% faster dashboard load |
| Connection pooling | 1000 persistent connections at API Gateway |
| Rate limiting | Token bucket, 10K logs/min per client |
| Sampling | DEBUG→10%, ERROR→100% = 60% volume reduction |
| Dead Letter Queue | Malformed logs → Kafka DLQ for manual review |

---

## 13. Agent-Side Components

```
FluentBit / OTEL collector
├── Log Collector    → reads files, syslog, stdout/stderr
├── Parser           → converts syslog/JSON/custom → standard schema
├── Buffer           → 10MB disk buffer, retry with exponential backoff (24h)
├── Batch Aggregator → 100 logs or 10s window before HTTP POST
├── Auth Module      → JWT refresh, API key rotation
└── Sampler          → DEBUG=10%, INFO=50%, WARN/ERROR=100%
```

---

## 14. Quick Cheat Sheet

```
Why Kafka?          → Decouple ingestion from processing; buffer; replay; multi-consumer
Why Cassandra?      → Write-optimized; time-series TTL; linear scale
Why Elasticsearch?  → Full-text search; inverted index; aggregations; ILM
Why Flink?          → Event-time watermarks; stateful windowing; exactly-once; dedup
Why S3?             → Cheap cold storage; 11 9s durability; Athena for querying

CAP choice?         → AP (Availability > Consistency) — logs are append-only, eventual is fine
Consistency model?  → Eventual — 1s delay between Cassandra write and ES indexing is acceptable
Dedup strategy?     → 5-min tumbling window + hash(ts_minute + service + msg[0:100])
Late data?          → 5-min watermark; accept up to 10 min late; older → DLQ
No data loss?       → Kafka RF=3, agent disk buffer, Flink checkpoints, Cassandra RF=3, S3
```
