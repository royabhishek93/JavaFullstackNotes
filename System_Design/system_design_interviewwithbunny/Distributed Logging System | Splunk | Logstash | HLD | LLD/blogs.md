Distributed Logging Platform (Splunk/OpenObserve)

"Multi-source ingestion → Kafka buffering → Apache Flink processing → Hot/Warm/Cold storage tiering with Elasticsearch"

1. Functional Requirements

Feature 1: Ingest logs from multiple sources (FluentBit, OTEL, custom agents) in real-time and batch
Feature 2: Support both real-time streaming and batch log ingestion with different protocols
Feature 3: Validate, parse, and normalize logs into a standard structure (JSON/structured format)
Feature 4: User should be able to see logs in the dashboard in almost near real-time (<5 seconds)
Feature 5: Advanced search with filters, regex, time-range queries on indexed logs
Feature 6: Tail logs in real-time with live streaming capabilities
Feature 7: Generate alerts based on log patterns, thresholds, and anomalies
2. Non-Functional Requirements

Scale
Log Volume — Millions of events per hour, petabytes of log data annually
Ingestion Rate — 100K-1M logs/second sustained throughput
Sources — Thousands of distributed services/servers
Retention — Hot: 14 days, Warm: 45 days, Cold: unlimited (S3)
Performance
Latency — Near real-time ingestion (<5 seconds end-to-end), search <200ms for hot data
Query Performance — Sub-second for recent logs (14 days), seconds for historical queries
Throughput — High concurrent writes and reads without degradation
Reliability
Availability — System should be always available for ingestion - 99.9% uptime
Consistency — Eventual consistency acceptable (AP in CAP theorem)
Durability — No data loss - replicated storage with S3 cold backup
Data Lifecycle — Automated tiering: Hot → Warm → Cold with retention policies
3. Core Entity

Entity 1: LogEvent - The actual log entry with timestamp, message, severity, metadata
Entity 2: IngestionJob - Tracks batch/streaming ingestion tasks from sources
Entity 3: Source/Agent - Log producers (servers, apps, containers) with unique IDs
Entity 4: Client/User - Organizations/teams with access control to their log namespaces
Entity 5: AlertRule - Configured patterns/thresholds that trigger notifications
Entity 6: SearchQuery - User queries with filters, time ranges, and pagination
4. API Designing

Ingestion APIs (Splunk Universal Forwarder/FluentBit)
POST /v1/logs/ingest — Single log ingestion with JSON payload {timestamp, level, message, metadata}
POST /v1/logs/batch — Batch ingestion for offline/bulk uploads (up to 10K logs per request)
POST /agents/register — Register new log source/agent with credentials and metadata
POST /agents/{agentId}/config — Update agent configuration (sampling rate, filters, buffer size)
POST /agents/login/logs — Agent authentication and log submission endpoint
Search APIs (microservices)
POST /logs/search (Pagination) — Search logs with query={text search + regex + filters + time-range}, returns paginated results
POST /logs/tail — Real-time log tailing with WebSocket/SSE for live streaming
GET /logs/{logId}/status — Get processing status of specific log entry
WS /logs/tail/* — WebSocket endpoint for real-time log streaming with filters
Alert & Management APIs
POST /alerts/create — Create alert rule with conditions and notification channels
GET /alerts/{alertId} — Retrieve alert configuration and trigger history
POST /agents/{agentId}/status/{requestId} — Health check and status reporting from agents
5. High Level Design

Clients/Agents (FluentBit/OTEL/Custom) → LB & API Gateway: Entry point with authentication, rate limiting
Client Onboarding Service → Client DB: Manages client registration, tokens, namespaces
File Ingestion Service → Kafka: Accepts logs via HTTP/gRPC, publishes to Kafka topics (raw_logs)
Agent Based Service → Kafka: Handles agent-specific protocols and batching
Search Service → Elasticsearch: Queries indexed logs with filtering and aggregation
Kafka (Buffer) → Apache Flink: Stream processing for validation, enrichment, deduplication
Apache Flink → Log DB (Cassandra/CockroachDB): Writes processed logs to hot storage with clustering by timestamp
Apache Flink → Elasticsearch: Real-time indexing for fast search (14 days retention)
Cron Service → S3: Archives logs older than 45 days to cold storage, deletes from hot DB
6. Deep Dive Design (Low Level)

Step 1: Client Onboarding
Client sends: POST /agents/register with {client_name, email, metadata}
Client Onboarding Service validates: Email format, uniqueness, rate limits
Service creates: Client record in PostgreSQL with {client_id, token (JWT), token_ttl, env, metadata}
Service provisions: Dedicated namespace/index in Elasticsearch (client_<id>_logs)
Service returns: {client_id, token, namespace} for agent configuration
Step 2: Log Ingestion (Real-time)
Agent sends: POST /v1/logs/ingest with headers {Authorization: Bearer <token>} and body {timestamp, level: 'ERROR', message, service_name, host, trace_id}
LB & API Gateway validates: Token (JWT signature), rate limit (10K logs/min per client), payload size (<1MB)
File Ingestion Service performs: Schema validation (required fields present), timestamp normalization (ISO 8601)
Service enriches: Adds {ingestion_time, client_id, pod_name, namespace} metadata
Service publishes: To Kafka topic 'raw_logs' with key=client_id for partitioning, returns 202 Accepted immediately
Step 3: Stream Processing (Apache Flink)
Flink consumes: From Kafka topic 'raw_logs' with consumer group 'log_processor'
Flink performs validation: Checks required fields {timestamp, message}, drops malformed logs to DLQ (dead letter queue)
Flink enriches: Adds geo-location from IP, service tags from registry lookup
Flink deduplicates: Using 5-minute tumbling window + message hash to detect duplicates
Flink routes: To multiple sinks - (1) Cassandra for durable storage, (2) Elasticsearch for indexing, (3) Alert topic if matches alert rules
Step 4: Storage in Log DB (Cassandra)
Flink writes: Batch of 1000 logs to Cassandra with clustering key (timestamp DESC)
Cassandra stores: In table logs_by_service with partition key=(service_name, log_date), clustering=(timestamp, log_id)
Cassandra replication: RF=3 (replication factor) across multiple datacenters for durability
TTL policy: Automatically deletes logs older than 14 days (hot storage retention)
Write optimization: Uses write-ahead log (WAL) + memtable for fast writes (10K writes/sec per node)
Step 5: Indexing in Elasticsearch
Flink bulk indexes: Batches of 5000 logs to Elasticsearch using _bulk API
Elasticsearch creates: Documents in index 'logs_<date>' with fields {log_id, timestamp, log_level, message, service_name, host, env, trace_id}
Elasticsearch indexes: Full-text on 'message', keyword on 'service_name', 'log_level', range on 'timestamp'
Index lifecycle: ILM (Index Lifecycle Management) rolls over daily, keeps 14 days in hot tier
Search optimization: Uses inverted index for text search, doc values for aggregations
Step 6: Log Search (Real-time)
User sends: POST /logs/search with {query: 'error AND service:payment', time_range: {start: '2025-01-19T00:00:00Z', end: '2025-01-20T00:00:00Z'}, filters: {log_level: ['ERROR', 'FATAL']}, page: 1, size: 100}
Search Service builds: Elasticsearch DSL query with bool query (must: text match, filter: term + range)
Elasticsearch executes: Query on hot indices (last 14 days), uses query cache for repeated queries
Service fetches: Results with highlighting on matched terms, total count for pagination
Service returns: {logs: [{log_id, timestamp, message, ...}], total: 15234, page: 1, size: 100} in <200ms
Step 7: Real-time Log Tailing
User opens: WebSocket connection to WS /logs/tail/* with query parameters {service: 'payment', level: 'ERROR'}
Search Service subscribes: To Kafka topic 'alert_topic' with filter matching user's criteria
Kafka streams: New matching logs to WebSocket connection in real-time
Service sends: Each log event as JSON message over WebSocket with <1s latency
Connection handling: Auto-reconnect on disconnect, buffer last 100 messages for reconnect recovery
Step 8: Alerting (Alert Service)
Alert Service polls: AlertRule DB for active rules every 10 seconds
Service subscribes: To Kafka 'alert_topic' which receives logs matching alert patterns from Flink
Service evaluates: Conditions like 'ERROR count > 100 in 5 minutes' using sliding window aggregation
Service triggers: Notification to configured channels - Kafka → Notification Service → Email/SMS/Pager
Service deduplicates: Alerts using cooldown period (don't re-alert for same condition within 10 min)
Step 9: Cold Storage Archival (Cron Service)
Cron Service runs: Daily job at 2 AM UTC to archive logs older than 45 days
Service queries: Cassandra for logs_by_traceid WHERE timestamp < (now - 45 days)
Service exports: Logs to S3 in Parquet format with compression (Snappy) for efficient storage
S3 organization: Partitioned by s3://logs-archive/{year}/{month}/{day}/{service_name}/logs.parquet
Service deletes: Archived logs from Cassandra to free up disk space, keeps S3 copy indefinitely
Recovery: Historical queries (>45 days) route to S3 using Athena/Presto for querying
7. Agent/Client-Side Components

Component 1: Log Collector (FluentBit/OTEL) - Installed on servers/containers to collect logs from files, syslog, stdout
Component 2: Parser - Transforms logs from various formats (JSON, syslog, custom) to standard schema
Component 3: Buffer - Local disk/memory buffer to handle network failures, retry with exponential backoff
Component 4: Batch Aggregator - Batches logs (100 logs or 10 seconds window) to reduce API calls
Component 5: Authentication Module - Manages JWT token refresh, API key rotation
Component 6: Sampling - Reduces log volume by sampling (e.g., send 10% of DEBUG logs, 100% of ERROR logs)
8. Database Schema Details

ClientDB (PostgreSQL)
client_id — uuid PRIMARY KEY
client_name — varchar(255) UNIQUE
token — text (JWT token for authentication)
token_ttl — timestamp (token expiration time)
env — varchar(50) (production, staging, dev)
pref — jsonb (preferences: retention, sampling rate)
metadata — jsonb (custom client metadata)
created_at — timestamp
logs_by_service (Cassandra - Hot Storage 14 days)
service_name — text (partition key - distributes data)
log_date — date (partition key - enables time-based partitioning)
timestamp — timestamp (clustering key DESC - sorts logs newest first)
log_id — uuid (clustering key - uniqueness)
log_level — text (DEBUG, INFO, WARN, ERROR, FATAL)
message — text (actual log message)
host — text (hostname or pod name)
trace_id — text (distributed tracing correlation)
metadata — map<text, text> (additional fields)
TTL — 14 days (automatic expiration)
logs_by_traceid (Cassandra - For trace correlation)
trace_id — text PRIMARY KEY
timestamp — timestamp (clustering DESC)
log_id — uuid
service_name — text
log_level — text
message — text
Elasticsearch Index (logs_<date>)
log_id — keyword (unique identifier)
timestamp — date (indexed for range queries)
log_level — keyword (exact match filtering)
message — text (full-text search with analyzer)
service_name — keyword (aggregations, filtering)
host — keyword
env — keyword (production, staging)
namespace — keyword (Kubernetes namespace)
pod_name — keyword
trace_id — keyword (distributed tracing)
AlertRule (PostgreSQL)
alert_id — uuid PRIMARY KEY
client_id — uuid FK → ClientDB
rule_name — varchar(255)
condition — jsonb ({field: 'log_level', operator: '=', value: 'ERROR', count: 100, window: '5m'})
notification_channels — jsonb (['email', 'slack', 'pagerduty'])
is_active — boolean
cooldown_period — interval (10 minutes - prevent alert spam)
last_triggered — timestamp
9. Data Lifecycle & Tiering Mechanism

Hot-Warm-Cold Storage Tiering
Hot Tier (0-14 days): Logs stored in Cassandra + Elasticsearch for fast reads/writes. SSD storage, high IOPS. Used for real-time search and dashboards.
Warm Tier (14-45 days): Logs remain in Cassandra but removed from Elasticsearch. Slower queries via direct DB access. HDD storage for cost optimization.
Cold Tier (>45 days): Logs archived to S3 in Parquet format. Queried via Athena/Presto for historical analysis. Glacier storage for ultra-low-cost retention.
Transition Logic: Cron job runs daily, checks log age, moves data between tiers automatically based on timestamp.
Cost Optimization: Hot=$0.10/GB/month, Warm=$0.05/GB/month, Cold=$0.01/GB/month - saves 90% on storage for old logs
Retention Policy Enforcement
Trigger: Configured per client in ClientDB preferences (e.g., retain_days=90)
Processing: Cron service queries logs older than retention period
Deletion: Soft delete (mark as deleted) for 7 days, then hard delete from all tiers
Compliance: Supports GDPR/data deletion requests by purging specific user logs across all tiers
Audit: Logs deletion events to audit trail for compliance verification
10. Scaling & Optimization

Technique 1: Kafka Partitioning - Topic 'raw_logs' partitioned by client_id (100 partitions) for parallel processing, each partition handles ~1K msg/sec
Technique 2: Elasticsearch Sharding - Daily indices with 10 primary shards + 1 replica, auto-scales based on data volume
Technique 3: Cassandra Clustering - Partition by (service_name, log_date) enables distributed queries, each node handles 10K writes/sec
Technique 4: Apache Flink Parallelism - Runs with parallelism=32, each task processes subset of Kafka partitions for horizontal scaling
Technique 5: Index Lifecycle Management (ILM) - Automatically rolls over Elasticsearch indices daily, moves to warm nodes after 7 days
Technique 6: Batch Processing - Agents batch 100 logs or 10 seconds worth before sending, reduces API calls by 100x
Technique 7: Compression - Logs compressed with Snappy (3:1 ratio) in Kafka and S3, saves storage and network bandwidth
Technique 8: Query Cache - Elasticsearch caches frequent queries (60s TTL), improves dashboard load time by 80%
Technique 9: Connection Pooling - API Gateway maintains 1000 persistent connections to backend services, reduces handshake overhead
Technique 10: Rate Limiting - Token bucket algorithm limits to 10K logs/min per client, prevents single client from overwhelming system
Technique 11: Sampling - Agents configured to sample DEBUG logs (10%) but send all ERROR/FATAL (100%), reduces volume by 60%
Technique 12: Dead Letter Queue (DLQ) - Malformed logs sent to Kafka DLQ topic for manual review, prevents processing pipeline blockage
11. Common Interview Questions

Q
Why use Kafka as a buffer instead of writing directly to the database?
A
Kafka provides critical decoupling and resilience:

(1) Back-pressure handling - if DB is slow/down, Kafka buffers millions of logs without data loss,

(2) Replay capability - can reprocess logs if processing logic changes or fails,

(3) Multiple consumers - same log stream feeds Elasticsearch, Cassandra, and Alert service independently,

(4) Peak load smoothing - ingestion spikes (10x normal) absorbed by Kafka, downstream processes at steady rate. Example: Black Friday traffic spike - Kafka handles 1M logs/sec burst, Flink processes at 100K/sec, no data loss.

Q
How do you handle out-of-order logs with different timestamps?
A
Multi-layer approach:

(1) Flink Watermarks - uses event time processing with 5-minute watermark delay, allows late-arriving logs to be included in correct time window,

(2) Cassandra Clustering - sorts by timestamp within partition, maintains chronological order for queries,

(3) Elasticsearch @timestamp - indexed for range queries, UI shows logs in order even if processed out-of-order,

(4) Grace Period - Flink accepts logs up to 10 minutes late, drops extremely late logs to DLQ. Trade-off: 5-min watermark delays alerting but ensures 99.9% logs in correct window.

Q
What happens if Elasticsearch goes down? Can users still search logs?
A
Graceful degradation strategy:

(1) Fallback to Cassandra - Search service automatically routes queries to Cassandra, slower (1-2s vs 200ms) but functional,

(2) Elasticsearch recovery - Flink queues bulk index requests in Kafka topic 'es_retry', replays when ES recovers,

(3) Cache layer - Redis caches recent common queries for 60s, serves during ES downtime,

(4) Status notification - UI shows 'Limited search mode' banner, sets user expectations. Cassandra can handle point queries (by service+time) but lacks full-text search capability. Typical ES downtime: <5 minutes with auto-restart.

Q
How do you ensure no log data is lost during ingestion?
A
Multiple durability guarantees:

(1) Kafka persistence - replication factor=3, min.insync.replicas=2, acks=all ensures log written to 2+ brokers before acknowledging,

(2) Agent buffering - FluentBit buffers 10MB locally on disk, retries failed sends with exponential backoff (max 24 hours),

(3) Flink checkpointing - every 60s, saves processing state to durable storage (S3), can recover exactly-once on failure,

(4) Cassandra replication - RF=3 with QUORUM writes, tolerates 1 node failure,

(5) S3 archival - immutable cold storage with 11 9's durability. End-to-end guarantee: At-least-once delivery (may have duplicates, handled by deduplication), zero data loss.

Q
How does the deduplication mechanism work in Flink?
A
Window-based deduplication:

(1) Tumbling Window - 5-minute windows, groups logs by time slice,

(2) Hash Generation - creates hash from (timestamp_minute, service_name, message_substring[0:100]),

(3) State Backend - Flink maintains RocksDB state with hash set of seen hashes within window,

(4) Duplicate Detection - if hash exists in state, drop log, else add to state and emit downstream,

(5) State Expiration - window closes after 5 min, state cleared to prevent unbounded growth. Handles: duplicate sends from agent retries, load balancer routing same log to multiple endpoints. Trade-off: only deduplicates within 5-min window, cross-window duplicates not detected.

Q
What's your data retention and archival strategy?
A
Three-tier lifecycle:

(1) Hot (0-14 days) - Cassandra + Elasticsearch, SSD storage, <200ms queries, costs $0.10/GB/month,

(2) Warm (14-45 days) - Cassandra only (ES deleted), HDD storage, 1-2s queries, costs $0.05/GB/month,

(3) Cold (>45 days) - S3 Parquet files, Glacier storage, 10-30s queries via Athena, costs $0.01/GB/month. Cron job runs daily: moves ES indices to warm tier (ILM policy), exports Cassandra to S3, deletes old Cassandra data. Example: 1TB logs/day = $3000/month hot storage vs $300/month blended with tiering. Compression: Snappy compression 3:1, Parquet columnar format enables efficient queries on cold data.

Q
How do you handle log search across multiple time ranges efficiently?
A
Query routing strategy:

(1) Time-based routing - if query range within last 14 days, query Elasticsearch (fast), if 14-45 days, query Cassandra (medium), if >45 days, query S3 via Athena (slow),

(2) Parallel execution - for cross-tier queries (e.g., last 60 days), fan out to ES + Cassandra + S3 in parallel, merge results,

(3) Elasticsearch query optimization - use date histogram aggregations for time-series, filter context instead of query context for non-scoring filters,

(4) Cassandra partition pruning - WHERE clause includes partition key (service_name, log_date) to read minimal partitions,

(5) S3 partitioning - Parquet files partitioned by year/month/day, Athena only scans relevant partitions. Example: Query 'last 30 days' = ES (14 days) + Cassandra (16 days) in <500ms vs single tier would be 2-3s.

Q
How do you implement real-time log tailing efficiently?
A
WebSocket + Kafka Consumer approach:

(1) Connection - client opens WebSocket to /logs/tail with filters (service, level),

(2) Consumer Group - backend creates dedicated Kafka consumer in unique group (per WebSocket connection), subscribes to 'alert_topic',

(3) Filtering - Kafka consumer uses Consumer Interceptor to filter messages matching client's criteria before sending over WebSocket,

(4) Backpressure - if client slow to consume, buffer last 100 messages in-memory, drop oldest if buffer full,

(5) Heartbeat - ping/pong every 30s to detect disconnects,

(6) Reconnect - on disconnect, client stores last received log timestamp, reconnects with 'since' parameter to resume. Scalability: Kafka supports 10K+ consumer groups, each WebSocket is independent, no shared state. Alternative: SSE (Server-Sent Events) for one-way streaming, simpler but no bidirectional communication.

Q
What's your alerting strategy to avoid alert fatigue?
A
Multi-level alert suppression:

(1) Aggregation - alert on 'ERROR count >100 in 5 min' not 'every ERROR', reduces noise by 100x,

(2) Cooldown Period - once alert fires, don't re-alert for same condition for 10 minutes (configurable),

(3) Severity Levels - P0 (critical, page immediately), P1 (high, email+Slack), P2 (medium, Slack only), P3 (low, daily digest),

(4) Deduplication - alerts with same fingerprint (service+error_type) grouped, send summary not individual alerts,

(5) Escalation - if P1 alert not acknowledged in 15 min, escalate to P0 and page on-call,

(6) Rate Limiting - max 10 alerts per service per hour, prevent alert storms. Example: Payment service 1000 errors → single alert 'Payment ERROR spike: 1000 in 5 min' with link to dashboard, not 1000 individual alerts.

Q
How do you handle schema evolution when log formats change?
A
Backward-compatible schema design:

(1) Schema Registry - maintain version history in registry, agents send schema_version with logs,

(2) Multi-version Support - Flink has parsers for v1, v2, v3 schemas, routes to appropriate parser based on version,

(3) Elasticsearch Mapping - dynamic mapping enabled, new fields auto-detected and indexed with default types,

(4) Default Values - missing fields populated with defaults during processing (null for optional, 'UNKNOWN' for required),

(5) Migration Path - during schema change, run both old and new parsers in parallel for 7 days, validate outputs match before deprecating old version,

(6) Deprecated Field Handling - old fields kept for 90 days with 'deprecated' flag, gives clients time to upgrade agents. Example: Add 'request_id' field → Flink auto-maps to ES, old logs without field show null, queries work across old+new logs.

12. Key Numbers to Remember

Ingestion & Throughput
Ingestion Rate — 100K-1M logs/second (peak), 10K-100K/sec (average)
Batch Size — 100 logs per batch OR 10 seconds, whichever first
Agent Buffer — 10MB local disk buffer per agent, 24 hour retry window
Kafka Throughput — 100K messages/sec per partition, 100 partitions = 10M/sec
Flink Parallelism — 32 parallel tasks, processes 100K events/sec per task
Storage & Retention
Hot Storage — 14 days in Cassandra + Elasticsearch (SSD, <200ms queries)
Warm Storage — 14-45 days in Cassandra only (HDD, 1-2s queries)
Cold Storage — >45 days in S3 Parquet (Glacier, 10-30s queries via Athena)
Compression Ratio — 3:1 with Snappy (e.g., 1TB raw → 330GB compressed)
Cassandra Write Speed — 10K writes/sec per node, 100 nodes = 1M writes/sec
Search & Query Performance
Elasticsearch Query — <200ms for recent logs (14 days), uses query cache
Cassandra Query — 1-2 seconds for warm tier (14-45 days)
S3/Athena Query — 10-30 seconds for cold tier historical analysis
Real-time Tail Latency — <1 second from log generation to WebSocket delivery
Index Size — 50GB per daily index, 10 shards, 1 replica
Reliability & Availability
Kafka Replication — RF=3, min.insync.replicas=2, acks=all
Cassandra Replication — RF=3, QUORUM writes/reads, tolerates 1 node failure
Flink Checkpoints — Every 60 seconds, state saved to S3 for recovery
System Availability — 99.9% SLA (8.7 hours downtime/year max)
Watermark Delay — 5 minutes (handles late-arriving logs, 99.9% coverage)
Example Calculation - End-to-End Latency
Agent → API Gateway — 50ms (network + TLS handshake + auth)
API → Kafka Publish — 100ms (validation + Kafka acks=all)
Kafka → Flink Processing — 500ms (consumer lag + windowing + enrichment)
Flink → Elasticsearch Index — 200ms (bulk API with 5K batch)
Total Latency (p95) — 850ms (typically <5 seconds SLA met)
Cost Optimization
Hot Storage Cost — $0.10/GB/month (SSD, Cassandra + ES)
Warm Storage Cost — $0.05/GB/month (HDD, Cassandra only)
Cold Storage Cost — $0.01/GB/month (S3 Glacier)
Example Savings — 1TB/day = $3000/mo hot vs $300/mo blended (90% savings)
Sampling Impact — Sample DEBUG 10%, send ERROR 100% = 60% volume reduction
Key Interview Tips

⚠️
NEVER write logs directly to Elasticsearch during ingestion. Always use Kafka as buffer first. This is critical for: (1) preventing data loss during ES downtime, (2) enabling replay on processing errors, (3) supporting multiple downstream consumers.

⭐
Interviewers ALWAYS ask: 'Why Cassandra over other databases?'. Answer: (1) Write-optimized - 10K writes/sec per node, perfect for log ingestion, (2) Time-series model - clustering by timestamp enables efficient range queries, (3) TTL support - auto-deletes old logs without manual cleanup, (4) Linear scalability - add nodes to scale horizontally.

💡
Key optimization: Hot-Warm-Cold tiering saves 90% on storage costs. Recent logs (14 days) need fast access (SSD), old logs (>45 days) rarely queried (S3 Glacier). Users don't notice 10s delay on historical queries but save thousands in monthly costs.

⭐
Must mention: Apache Flink for stream processing shows understanding of event-time processing, watermarks, and exactly-once semantics. Don't just say 'Kafka consumer' - Flink provides windowing, stateful operations, and fault tolerance that plain consumers lack.

⚠️
NEVER synchronously wait for Elasticsearch indexing during ingestion. Return 202 Accepted immediately after Kafka publish. This prevents ingestion slowdown when ES is under load and improves p95 latency from 2s to 200ms.

💡
Deduplication window trade-off: 5-minute window catches 99% duplicates from agent retries while keeping Flink state size manageable (<1GB per task). Longer windows (1 hour) catch more duplicates but increase state size 12x and checkpoint time from 5s to 60s.

⭐
Interviewers love asking: 'How do you handle log spikes during incidents?'. Answer: (1) Kafka absorbs burst (buffer 1M logs), (2) Sampling increases automatically (DEBUG→1%, INFO→10%), (3) Rate limiting per client prevents one service overwhelming system, (4) Alert service uses top-K to show 'top 10 error types' not all errors.

💡
Elasticsearch ILM (Index Lifecycle Management) is NOT optional for production. Without it, indices grow unbounded, queries slow down, and cluster runs out of disk. ILM auto-rolls over daily, moves to warm tier, and deletes old indices - completely automated.

⚠️
NEVER use SELECT * or full table scans in Cassandra. Always include partition key (service_name, log_date) in WHERE clause. Without it, query hits all nodes, takes minutes instead of milliseconds, and can crash the cluster under load.

⭐
Must explain: Why eventual consistency is acceptable for logs. Unlike payments (need strong consistency), logs don't require immediate global consistency. It's fine if log appears in Elasticsearch 1 second after Cassandra - users care about near real-time (<5s), not strict ordering.