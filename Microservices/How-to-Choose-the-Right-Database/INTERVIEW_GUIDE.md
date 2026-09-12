# INTERVIEW_GUIDE.md
## How to Choose the Right Database (15 YOE Interview Pack)

Print settings: landscape, monospace font (Consolas/Courier New 9-10pt), narrow margins.

Reference video:
- https://www.youtube.com/watch?v=JjhJ5-RBIG0

---

# PAGE 1 - BIG PICTURE + RAPID ANSWER (5 MIN SPOKEN SCRIPT)

DRAW THIS

```text
+------------------+        +------------------------+
| Client / Product |------->| API / Service Layer    |
+------------------+        +------------------------+
                                      |
                                      v
                        +------------------------------+
                        | Data Access / Query Patterns |
                        +------------------------------+
                                      |
          +---------------------------+---------------------------+
          |                           |                           |
          v                           v                           v
+------------------+       +--------------------+      +------------------+
| RDBMS            |       | NoSQL Family       |      | Specialized      |
| Postgres / MySQL |       | Doc/KV/Wide Column |      | Search/Graph/TS  |
+------------------+       +--------------------+      +------------------+
          |                           |                           |
          +---------------------------+---------------------------+
                                      |
                                      v
                        +------------------------------+
                        | Scale Path: Cache/Index/Part |
                        | then Shard/Polyglot if needed|
                        +------------------------------+
```

### Rapid Answer
"Let me answer database choice in a structured way. I do not start with a product name like Postgres or MongoDB. I start with four filters.

First, what is the data shape: relational, document, graph, key-value, or time-series.

Second, what consistency and transaction guarantees do we need. If this is money movement, order placement, inventory decrement, or payment settlement, I default to ACID-friendly relational design.

Third, what are the access patterns: point lookups, complex joins, full-text search, graph traversal, analytics, or high-ingest telemetry.

Fourth, what is scale and latency target now and in 12 months.

Then I choose category first and engine second.

For example:
- User onboarding and authentication -> PostgreSQL or MySQL. Example: a login/signup system where you store users, passwords, roles, and audit logs in tables.
- Flexible product attributes or rapidly evolving schema -> MongoDB or Couchbase. Example: an e-commerce catalog where electronics, clothes, and books all have different fields.
- Ultra-low latency counters, sessions, or leaderboard style operations -> Redis. Example: session tokens, OTP cache, rate limiting, or a game leaderboard.
- Full-text ranking and search -> Elasticsearch or OpenSearch. Example: product search with typo tolerance, filters, and relevance scoring.
- Deep relationship traversal like friends-of-friends -> Neo4j or Amazon Neptune. Example: social network recommendations or fraud-ring detection.

---

# PAGE 2 - GLOSSARY (SIMPLE DEFINITIONS)

- Structured data: Table-like data with fixed columns and strong schema. Example: `users`, `orders`, and `payments` tables in an e-commerce app.
- Semi-structured data: Flexible JSON-like data where fields can vary. Example: product catalog documents where electronics, books, and clothes have different fields.
- Unstructured data: Files, media, blobs, logs, and text that do not fit rows cleanly. Example: uploaded images, PDFs, application logs, and customer support attachments.
- ACID: Atomicity, Consistency, Isolation, Durability. Example: when a bank transfer happens, debit and credit must either both succeed or both fail.
- BASE: Basically Available, Soft state, Eventual consistency. Example: a social feed can show a post a few seconds late, but the system stays available.
- OLTP: High-volume transactional read/write operations. Example: checkout, login, booking tickets, placing orders.
- OLAP: Analytical, aggregation-heavy queries over large datasets. Example: monthly sales dashboard, cohort analysis, revenue trends.
- Idempotency: Repeating an operation produces same final result. Example: retrying `POST /orders` should not create two identical orders.
- Read-heavy: Workload dominated by reads. Example: product catalog or user profile service where pages are viewed much more often than updated.
- Write-heavy: Workload dominated by writes/ingestion. Example: clickstream events, IoT telemetry, or chat message ingestion.
- Sharding: Splitting data across nodes by shard key. Example: splitting customers by `customer_id` range across multiple database servers.
- Partitioning: Splitting a table/index into logical chunks. Example: monthly order partitions so old data is separated from current hot data.
- Indexing: Data structures that speed reads at write/storage cost. Example: index on `email` for fast login lookup, or `order_id` for quick order fetch.
- Replica: Read-only copy for scale and HA. Example: one primary DB writes orders, multiple replicas handle reporting and dashboards.
- p99 latency: 99th percentile response time. Example: if p99 search latency is 300 ms, 99 out of 100 searches finish within 300 ms.
- Hot partition: One shard gets disproportionate traffic. Example: all users hitting the same trending hashtag or the same celebrity profile.
- Eventual consistency: Replicas converge later, not instantly. Example: a newly uploaded profile photo appears in search results a few seconds later.
- Fan-out: One event expands to many writes/messages. Example: one invoice job creates millions of child email jobs.
- Backpressure: Controlled rejection/throttling when system is overloaded. Example: returning `429 Too Many Requests` when checkout traffic spikes and the DB is saturated.
- Polyglot persistence: Using multiple database types in one system. Example: Postgres for orders, Redis for sessions, Elasticsearch for search, and Neo4j for relationships.

---

# PAGE 3 - COMPONENT CHOICES (WHY / WHY NOT)

## 1) Relational (Postgres/MySQL)
Why picked:
- Scenario 1 (payment): user pays 499 INR, but the app crashes in the middle. In a relational DB, either all related updates happen together (payment row + order status), or none happen. You do not end up with "money debited but order not placed".
- Scenario 2 (e-commerce checkout): when an order is placed, inventory must reduce exactly once. Relational constraints and transactions help avoid overselling when many users buy the same item at the same time.
- Scenario 3 (login and account): user, role, session, and audit records are connected data. Relational tables with foreign keys make this safer and easier to maintain than storing everything as disconnected documents.

Why not always:
- Rigid schema can slow rapid shape changes.
- Horizontal scale is possible but operationally heavier.

## 2) Document DB (MongoDB/Document stores)
Why picked:
- Flexible schema for evolving product/profile metadata.
- Easy nested object modeling.

Why not always:
- Multi-record relational constraints are weaker compared to RDBMS.
- Complex joins are often harder.

## 3) Key-Value (Redis)
Why picked:
- Ultra-low latency for cache/session/counter/rate limiting.
- Excellent for transient or computed data.

Why not always:
- Usually not primary durable source of truth.
- Memory cost and persistence tradeoffs.

## 4) Search Engine (Elasticsearch/OpenSearch)
Why picked:
- Full-text ranking, fuzzy search, faceting, relevance scoring.

Why not always:
- Not a replacement for transactional source of truth.
- Index maintenance overhead.

## 5) Graph DB (Neo4j)
Why picked:
- Deep relationship traversal and graph algorithms.

Why not always:
- Overkill for simple CRUD systems.
- Additional operational complexity.

DRAW THIS

```text
Requirement -> Category -> Engine
---------------------------------
Payments/Orders        -> Relational   -> Postgres/MySQL
Profile metadata       -> Document     -> MongoDB
Session/cache/counters -> Key-Value    -> Redis
Text search            -> Search       -> Elasticsearch
Social graph traversal -> Graph        -> Neo4j
Telemetry metrics      -> Time-series  -> TSDB
```

## PAGE 3A - TOP 2 DATABASES PER CATEGORY (DIFFERENCE + WHY + WHEN)

DRAW THIS

```text
Category      Option A        Option B
------------- --------------- -----------------
Relational    PostgreSQL      MySQL
Document      MongoDB         Couchbase
Key-Value     Redis           DynamoDB
Wide-column   Cassandra       HBase
Search        Elasticsearch   OpenSearch
Graph         Neo4j           Amazon Neptune
Time-series   InfluxDB        TimescaleDB
Vector        Pinecone        pgvector (Postgres)
```

### 1) Relational: PostgreSQL vs MySQL
- Difference:
  - PostgreSQL: choose this when your app needs richer querying, JSON + table data together, or more complex reporting.
  - MySQL: can still run joins and filters, but PostgreSQL fits better once queries become more ad hoc, reporting-heavy, or mixed with JSON fields.
- Why choose PostgreSQL:
  - Scenario: an e-commerce app stores orders in tables, but coupon rules, shipping preferences, and extra metadata are in JSON. PostgreSQL is better because you can query both relational and JSON data together.
  - Scenario: a finance app needs payment history, reconciliation reports, and flexible filters by date, status, and region. PostgreSQL handles deeper SQL reporting more comfortably.
  - Why PostgreSQL is the better fit here: it gives you stronger support for advanced SQL patterns like JSON operators, CTEs, window functions, and complex reporting queries. MySQL can do basic SQL, but PostgreSQL is easier when the query becomes more analytical.
- Why choose MySQL:
  - Scenario: SaaS app with user signup, login, subscription status, basic reporting. Queries are simple and predictable.
- When:
  - Choose PostgreSQL if you expect complex SQL, JSON fields, or reporting-style queries.
  - Choose MySQL if you want a simpler relational setup for common business CRUD.
  - Example: payment ledger + reconciliation reports -> PostgreSQL.
  - Example: user signup + subscription management + basic admin reports -> MySQL.

### 2) Document: MongoDB vs Couchbase
- Difference:
  - MongoDB: choose when the document shape changes often and developers need to add/remove fields quickly.
  - Couchbase: choose when you want document storage plus very fast key-value-style reads.
- Why choose MongoDB:
  - Scenario: an e-commerce product catalog has different fields for different product types: phones have battery capacity, clothes have size, and books have ISBN. MongoDB handles this changing structure well.
  - Scenario: a content management system stores articles, tags, and author metadata in slightly different shapes as the product evolves.
- Why choose Couchbase:
  - Scenario: a travel app repeatedly reads user preference documents like seat preference, meal preference, and frequent flyer info. Couchbase is attractive because the reads must be extremely fast.
  - Scenario: a recommendation service needs document data with cache-like performance for millions of profile lookups.
- When:
  - Choose MongoDB if the schema changes often and the team wants easy document modeling.
  - Choose Couchbase if the main problem is hot document reads with very low latency.
  - Example: product catalog with changing attributes -> MongoDB.
  - Example: customer profile service with heavy read traffic -> Couchbase.

### 3) Key-Value: Redis vs DynamoDB
- Difference:
  - Redis: choose when speed matters most and the data is short-lived or cache-like.
  - DynamoDB: choose when you need a managed, durable key-value store that scales automatically.
- Why choose Redis:
  - Scenario: a login system stores OTPs in Redis with a 5-minute TTL. If the OTP is not used quickly, it disappears automatically.
  - Scenario: a payment API uses Redis for rate limiting, so one user cannot spam retries too fast.
- Why choose DynamoDB:
  - Scenario: an e-commerce cart must survive app restarts and still be available later. DynamoDB is better because it is durable and managed.
  - Scenario: a SaaS app stores user preferences or notification settings and wants cloud-managed scaling without running its own database servers.
- When:
  - Choose Redis for session cache, OTP, leaderboard, rate limiting, and distributed locks.
  - Choose DynamoDB for durable preferences, carts, or AWS-native apps that need automatic scale.
  - Example: leaderboard showing top 100 players -> Redis.
  - Example: shopping cart that must survive service restarts -> DynamoDB.

### 4) Wide-column: Cassandra vs HBase
- Difference:
  - Cassandra: choose when you have very high writes and you want the system to stay available across regions.
  - HBase: choose when your platform already uses Hadoop/Spark and you need very large sparse tables.
- Why choose Cassandra:
  - Scenario: a telemetry system collects millions of sensor events per second from devices around the world. Cassandra is useful because it is built for high write throughput.
  - Scenario: a chat or event stream service needs always-on writes and can tolerate eventual consistency.
- Why choose HBase:
  - Scenario: a data platform uses Hadoop and Spark to process massive sparse tables, and HBase fits naturally into that ecosystem.
  - Scenario: a big-data reporting system stores huge rows with many empty columns and needs random access at scale.
- When:
  - Choose Cassandra for global write-heavy workloads, telemetry, and multi-region availability.
  - Choose HBase when the company is already standardized on Hadoop/HDFS.
  - Example: IoT device metrics from multiple countries -> Cassandra.
  - Example: enterprise analytics platform built on HDFS -> HBase.

### 5) Search: Elasticsearch vs OpenSearch
- Difference:
  - Both are used for searching text, ranking results, and filtering data.
  - The main difference is ecosystem preference and managed service choice.
- Why choose Elasticsearch:
  - Scenario: an online store wants product search with typo tolerance, brand filters, and ranking based on popularity.
  - Scenario: a SaaS admin console needs search across logs, users, and tickets with rich query features.
- Why choose OpenSearch:
  - Scenario: an AWS-heavy company wants log analytics, search, and dashboards without depending on a specific proprietary ecosystem.
  - Scenario: a platform team wants an open-managed search stack for observability data.
- When:
  - Choose Elasticsearch for product search, typo tolerance, and mature search tooling.
  - Choose OpenSearch when the team wants an open distribution and strong AWS alignment.
  - Example: shopping site search -> Elasticsearch.
  - Example: log search for a monitoring stack on AWS -> OpenSearch.

### 6) Graph: Neo4j vs Amazon Neptune
- Difference:
  - Neo4j: choose when you want the easiest graph modeling and strongest developer experience.
  - Neptune: choose when you want graph capabilities as a managed AWS service.
- Why choose Neo4j:
  - Scenario: fraud detection asks questions like, "Does this card share a device with other suspicious users?" Neo4j is strong for multi-hop traversal.
  - Scenario: a recommendation engine wants to discover "friends of friends" or "users with similar paths".
- Why choose Neptune:
  - Scenario: a company already uses AWS and wants a managed graph service instead of operating graph servers itself.
  - Scenario: a supply-chain platform wants managed graph storage for relationships between suppliers, products, and shipments.
- When:
  - Choose Neo4j when graph traversal is core to the product and the team wants fast modeling and querying.
  - Choose Neptune when AWS-managed operations matter more than developer ergonomics.
  - Example: fraud ring detection -> Neo4j.
  - Example: AWS-managed relationship graph for enterprise apps -> Neptune.

### 7) Time-series: InfluxDB vs TimescaleDB
- Difference:
  - InfluxDB: choose when the app is mostly metrics, telemetry, and time-window queries.
  - TimescaleDB: choose when you want time-series features but still want PostgreSQL-style SQL and joins.
- Why choose InfluxDB:
  - Scenario: a monitoring system collects CPU, memory, and latency metrics every second from thousands of servers.
  - Scenario: an IoT dashboard stores temperature and pressure readings that are queried by time range and downsampled later.
- Why choose TimescaleDB:
  - Scenario: a fleet-management app stores vehicle telemetry but also needs joins with customer and vehicle tables in the same database.
  - Scenario: a business dashboard needs time-series analytics plus normal SQL reports on the same data.
- When:
  - Choose InfluxDB for pure telemetry, observability, and metrics pipelines.
  - Choose TimescaleDB when time-series is only one part of a larger relational system.
  - Example: server monitoring dashboard -> InfluxDB.
  - Example: IoT data plus customer reporting in one SQL system -> TimescaleDB.

### 8) Vector: Pinecone vs pgvector (Postgres)
- Difference:
  - Pinecone: choose when vector search is a major product feature and scale is large.
  - pgvector: choose when you already use Postgres and vector search is an added feature, not the whole system.
- Why choose Pinecone:
  - Scenario: a customer support chatbot searches millions of embedded documents to answer questions from PDFs, FAQs, and policies.
  - Scenario: a recommendation engine needs fast nearest-neighbor search over a very large embedding set.
- Why choose pgvector:
  - Scenario: an internal knowledge-search tool has a moderate number of documents and the team wants to keep everything inside Postgres.
  - Scenario: a startup adds semantic search as a small feature and does not want another database to operate.
- When:
  - Choose Pinecone for dedicated, large-scale vector retrieval systems.
  - Choose pgvector when vector search is modest and simplicity matters.
  - Example: AI chatbot over 100M documents -> Pinecone.
  - Example: small internal semantic search on top of Postgres -> pgvector.

Interview line to use:
"I choose category first, then engine based on consistency needs, access pattern, team operational maturity, and cloud constraints."

---

# PAGE 4+ - FULL CONVERSATIONAL INTERVIEW SCRIPT

## SECTION A - Requirement Clarification (Word-for-Word)
"Before I commit to a database, I want to clarify four things.

One, what is the business-critical entity and what correctness means for that entity.

Two, where can we tolerate eventual consistency and where we cannot.

Three, what are dominant query patterns: by primary key, by range, by text, or by relationship depth.

Four, what is expected scale now and one year out.

Once these are clear, database choice becomes straightforward and defensible."

Cross-question: Why not pick one DB for everything?
Strong answer: "Because each workload stresses different access paths and consistency constraints. One-size-fits-all increases risk and cost."

## SECTION B - Capacity Estimation Framework
"I estimate request mix first, then data growth, then peak amplification.

Example template:
- DAU: 5M
- Peak QPS: 8x average
- Read/write mix: 80/20
- Payload: 2 KB average record
- Annual growth: 2-4x

From this, I derive index budget, cache hit target, and shard key risk."

DRAW THIS

```text
Traffic Model
-------------
Daily Requests = DAU x Requests/User/Day
Avg QPS       = Daily Requests / 86400
Peak QPS      = Avg QPS x Burst Factor
Write QPS     = Peak QPS x Write Ratio
Read QPS      = Peak QPS x Read Ratio
```

## SECTION C - Core Entities and Data Shape
"I classify entities into transactional core and peripheral metadata.

Transactional core goes to relational.
Flexible metadata may go to document storage.
Derived/read-optimized copies can go to cache/search."

DRAW THIS

```text
Core vs Peripheral
------------------
Core (strict correctness): user_account, order, payment, inventory
Peripheral (flexible): profile_preferences, product_attributes, event_logs
Derived (read-optimized): cache views, search index docs
```

## SECTION D - API Design (with JSON)

### Endpoint examples
- POST /v1/users
- POST /v1/orders
- GET /v1/orders/{id}
- GET /v1/search?q=...&filters=...

### Example request/response

```json
POST /v1/orders
{
  "idempotency_key": "ord_2026_08_22_001",
  "user_id": "u_102",
  "items": [
    { "sku": "SKU123", "qty": 2, "price": 499 }
  ],
  "currency": "INR"
}
```

```json
201 Created
{
  "order_id": "o_9912",
  "status": "PLACED",
  "created_at": "2026-08-22T10:30:00Z"
}
```

Interview line:
"For write APIs I enforce idempotency keys to avoid duplicate side effects on retries."

## SECTION E - Architecture Diagram (Implementation View)

DRAW THIS

```text
+-------------+      +-------------------+      +------------------+
| API Gateway |----->| App Services      |----->| Primary RDBMS    |
+-------------+      +-------------------+      +------------------+
       |                      |                          |
       |                      +-------> +-----------+   |
       |                                | Redis KV  |<--+
       |                                +-----------+
       |
       +-------------------------------> +----------------------+
                                        | Search Index Cluster |
                                        +----------------------+

Write Path: API -> Service -> RDBMS -> Async index update
Read Path : API -> Redis (hit) else RDBMS/Search then cache fill
```

## SECTION F - ER Relationship Diagram

DRAW THIS

```text
+-----------+      1:N      +---------+      1:N      +------------+
| users     |--------------- | orders  |---------------| order_items|
+-----------+                +---------+               +------------+
| user_id PK|                | order_id PK             | item_id PK |
| email UQ  |                | user_id FK              | order_id FK|
+-----------+                | status                  | sku        |
                             +---------+               +------------+
                                   |
                                   | 1:1
                                   v
                             +-------------+
                             | payments    |
                             +-------------+
                             | payment_idPK|
                             | order_id FK |
                             | state       |
                             +-------------+
```

## SECTION G - Sequence Diagram (Order Placement)

DRAW THIS

```text
Client -> API        : POST /orders (idempotency_key)
API -> Redis         : Check idempotency key cache
Redis -> API         : miss
API -> RDBMS         : BEGIN
API -> RDBMS         : insert order
API -> RDBMS         : reserve inventory
API -> RDBMS         : insert payment_intent
API -> RDBMS         : COMMIT
API -> Redis         : set idempotency key -> order_id
API -> Queue         : publish order_created
Worker -> Search     : upsert search document
API -> Client        : 201 CREATED
```

## SECTION H - Trade-offs (Say This)
"I optimize correctness first on write path, then latency on read path.

If reads become expensive, I add cache and read replicas.
If search becomes critical, I add a dedicated search index.
If one table grows too fast, I partition before sharding.
I only shard after access pattern and shard key are stable."

## SECTION I - Beginner Visual Anchor (Choice -> Scale Path)

DRAW THIS

```text
Step 1: Choose base DB by correctness + query shape
  |
  v
Step 2: Optimize query + indexes
  |
  v
Step 3: Add cache + read replicas for read-heavy traffic
  |
  v
Step 4: Partition large hot tables
  |
  v
Step 5: Shard only when single-node limits are proven

Rule: Start simple, measure bottleneck, then add complexity.
```

---

# SENIOR TRAP QUESTIONS (15 YOE)

1) Why not NoSQL for everything if scale is high?
- Strong answer: "Scale is one axis. Consistency and transaction semantics are equally critical."

2) What if idempotency cache is lost?
- Strong answer: "Persist key-to-result in durable store for critical operations."

3) How do you handle hot shard?
- Strong answer: "Choose high-cardinality shard key, use bucketing/salting where needed."

4) Why eventual consistency is acceptable in search but not in payments?
- Strong answer: "Search is read convenience; payments are source-of-truth correctness domain."

5) How to migrate from single SQL to polyglot safely?
- Strong answer: "Use CDC/outbox, dual-write avoidance, phased read cutover, reconciliation."

---

# WHAT NOT TO SAY

- "NoSQL is always faster." -> Wrong. Access pattern decides performance.
- "MySQL cannot scale." -> Wrong. It scales with partitioning, indexing, replicas, and sharding.
- "I choose Mongo because schema is flexible." -> Incomplete. Must justify consistency and query behavior too.
- "We will shard from day one." -> Usually premature and costly.

---

# KEY NUMBERS TO MEMORIZE

```text
- p99 API latency target: < 200 ms (read), < 400 ms (write)
- Cache hit target: 80-95% for hot reads
- Read/write split triggers read replica consideration: >70/30
- Table growth trigger for partition planning: 50M+ rows hot table
- Retry policy: 3 attempts, exponential backoff + jitter
- Idempotency key TTL: 24-72 hours (business dependent)
```

---

# WHITEBOARD DRAW ORDER (INTERVIEW EXECUTION)

DRAW THIS

```text
1) Requirements box (functional + NFR)
2) Decision tree (data shape -> consistency -> access -> scale)
3) Big picture architecture
4) ER model
5) Sequence for write path
6) Scale path (index -> cache -> partition -> shard)
7) Risk + mitigation table
```

Script close:
"My final database choice is a responsibility split, not a technology preference. I keep source-of-truth transactional data in relational storage, add specialized stores only for validated workload pressure, and I always present a safe migration path from simple to scalable architecture."