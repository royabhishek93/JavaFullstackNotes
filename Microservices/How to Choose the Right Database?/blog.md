
Database Fundamentals · Architecture Decision Guide
Choose the database
from the problem.
A practical field guide for system design: understand the data model, identify access patterns and guarantees, choose the correct database category, and then select a specific engine with explicit trade-offs.

app
api
sensors
query results
2
Big families
9+
Database types
35+
Engines compared
2
Decision levels
01 — First Principles
What is a database, and why do we need one?
A database is an organized collection of data, stored so it can be queried, updated, and managed efficiently — run by software called a DBMS (Database Management System) that sits between your application and the raw bytes on disk.

Without a database
Just files on disk
No fast way to search or filter millions of records
Two users writing at once corrupt each other's data
A crash mid-write leaves half-saved, broken records
No rules — nothing stops bad or duplicate data
Every app re-invents storage, backup, and access logic
With a database
A managed, queryable store
Persistence — data survives restarts and crashes
Querying — ask complex questions, get answers in ms
Concurrency — thousands of users, safely, at once
Integrity — constraints & transactions keep data valid
Security & scale — access control, backups, replication
The one-line mental model  →  App asks a question or makes a change  ·  the DBMS finds, locks, and updates the exact data  ·  guarantees it stays correct even under failure and heavy load.
02 — Before choosing a database, know your data
The three shapes of data
The single biggest driver of database choice is how structured your data is. Data sits on a spectrum from rigid tables to raw, shapeless blobs.

Structured
Fits neatly into rows & columns with a fixed, predefined schema. Every record looks the same.

Examples: bank transactions, orders, inventory, user records
Lives well in: Relational / SQL
Semi-structured
Has tags or keys that give it shape, but the shape can vary record to record. Flexible, self-describing.

Examples: JSON, XML, log events, product catalogs, API payloads
Lives well in: Document / NoSQL
Unstructured
No predefined model at all — raw content you can't slot into fields without processing it first.

Examples: images, video, audio, PDFs, free-text, emails
Lives well in: Blob / object storage (S3, GCS, Azure Blob)
How unstructured data is really stored  →  You don't shove a 2 GB video into a database. The raw file goes into blob / object storage — Amazon S3, Google Cloud Storage, Azure Blob Storage, or self-hosted MinIO — which is built for cheap, durable, massive-scale binary files. The database then only holds a small pointer (the object URL/key) plus metadata (filename, size, owner, tags) so you can query and find it fast.
Rule of thumb  →  The more predictable and relational your data, the more a table-based SQL database pays off. The more variable, nested, or content-heavy it is, the more a specialized NoSQL engine earns its place.
03 — The great divide
SQL vs NoSQL
Not "old vs new" — two philosophies about structure, consistency, and scale. Most real systems use both, each for what it's best at.

Relational · SQL
Schema first, correctness first
Data lives in tables with rows & columns and a fixed schema
Schema-on-write — structure enforced before data goes in
ACID transactions — strong consistency, no half-done writes
Joins connect related tables; no duplicated data
Scales vertically (bigger box); harder to shard
Best for: money, orders, anything needing relationships & guarantees
Non-relational · NoSQL
Flexible shape, built to scale
Data lives as documents, key-values, wide-columns, or graphs
Model-specific schema — often flexible, but many NoSQL systems still enforce keys, types, or table definitions
Consistency is configurable — some favor eventual consistency; others support strong or transactional guarantees
Data is denormalized — stored the way it's read
Many products are designed for horizontal scale, but behavior depends on the engine and data model
Best for: huge scale, evolving schemas, high write throughput
Side by side
Dimension	SQL (Relational)	NoSQL (Non-relational)
Data model	Tables, rows, columns	Documents / KV / columns / graph
Schema	Explicit and strongly enforced	Ranges from flexible documents to strictly defined keys/tables
Consistency	Usually strong transactional guarantees	Engine-specific: eventual, tunable, strong, or transactional
Scaling	Vertical, replicas, partitioning, or distributed SQL	Often horizontal and access-pattern driven
Relationships	Joins across tables	Embedded / denormalized
Query language	SQL (standardized)	Engine-specific APIs
Sweet spot	Structured, transactional data	Big, varied, fast-changing data
CAP theorem, stated correctly  →  During a network partition, a distributed system must choose between returning only consistent results or remaining available for every request. Partition tolerance is not an optional “third choice” once the network has split. This applies to distributed SQL and NoSQL systems alike.
04 — The catalog
Every database type, and who plays there
NoSQL isn't one thing — it's a family of specialized engines. Here's the full landscape. Tap a category to expand it.































05 — The selection framework
Do not start with a database name
The durable skill is converting requirements into a database category, then selecting an engine whose operational model fits your constraints.

The best database does not exist. The right database depends on the problem, access patterns, guarantees you cannot compromise, and the operational cost your team can support.
Step 1
Data shape
Tables, documents, key-value entries, relationships, events, vectors, or timestamped measurements?

Step 2
Access patterns
Key lookup, range query, joins, traversal, full-text search, or aggregation?

Step 3
Guarantees
Transactions, uniqueness, ordering, read-after-write, or eventual convergence?

Step 4
Scale & latency
Volume, requests per second, read/write ratio, regions, hot keys and latency budget.

Step 5
Category
Relational, document, key-value, wide-column, graph, time-series, search, vector, or analytical?

Step 6
Engine
Choose by features, hosting, replication, ecosystem, cost, lock-in and team capability.

Questions to answer before naming a product
What must never be wrong?
Balances, inventory and order state usually demand stronger guarantees than feeds or analytics.
What are the dominant queries?
Select for the queries the system must answer, not merely for the incoming payload format.
What fails during a partition?
Decide whether stale data, rejected writes or temporary unavailability is acceptable.
Where will it run?
Self-hosted, managed cloud, serverless, edge, private data centres or multiple regions?
What is the operational budget?
A powerful engine is a bad choice if your team cannot back up, recover and upgrade it reliably.
Can one database remain the source of truth?
Specialized stores often work best as derived views or indexes beside a transactional source.
06 — The decision map
Choose your database by use case
This is the bible. Pick what you're building on the left — get the database type, the specific engines to reach for, the reasoning, and what to avoid.


🏦
Banking / payments / orders

⚡
Caching / sessions / leaderboards

🛍️
Product catalog / CMS / user profiles

📈
Metrics / monitoring / IoT sensors

🔥
Massive write throughput / event logs

🕸️
Social graph / recommendations / fraud

🔎
Full-text search / log analytics

🤖
AI semantic search / RAG / embeddings

🌍
Global app needing scale + transactions

📊
BI dashboards / analytics / reporting
Recommended · Relational (SQL)
Banking / payments / orders
Money demands ACID transactions and strong consistency — a transfer must fully succeed or fully fail, never halfway. Clear relationships between accounts, orders and users map perfectly to joined tables.
PostgreSQL
MySQL
Oracle
Avoid: Eventually-consistent NoSQL, where a balance could be read stale mid-transaction.
The whole map on one page
If you're building…	Reach for	Engines
🏦 Banking / payments / orders	Relational (SQL)	PostgreSQL, MySQL, Oracle
⚡ Caching / sessions / leaderboards	Key-Value	Redis, Memcached, DynamoDB
🛍️ Product catalog / CMS / user profiles	Document	MongoDB, Firestore, Couchbase
📈 Metrics / monitoring / IoT sensors	Time-Series	InfluxDB, TimescaleDB, Prometheus
🔥 Massive write throughput / event logs	Wide-Column	Cassandra, ScyllaDB, Bigtable
🕸️ Social graph / recommendations / fraud	Graph	Neo4j, Neptune, ArangoDB
🔎 Full-text search / log analytics	Search Engine	Elasticsearch, OpenSearch, Solr
🤖 AI semantic search / RAG / embeddings	Vector	Pinecone, Weaviate, pgvector, Qdrant
🌍 Global app needing scale + transactions	NewSQL	Google Spanner, CockroachDB, YugabyteDB
📊 BI dashboards / analytics / reporting	Warehouse (OLAP)	Snowflake, BigQuery, ClickHouse, Redshift
07 — Second-level decision
Choose an engine within the category
Once the category is correct, product choice becomes a trade-off among query features, deployment model, consistency, replication, cloud ecosystem, cost, operational complexity and team experience. Each comparison includes a simple real-world scenario so the choice is easier to remember.

Interview-quality answer  →  “I need a document database because the aggregate is naturally JSON-shaped and the schema evolves frequently. MongoDB is a reasonable implementation because we also need rich indexes and aggregation.” Category first; product second.
Relational
MySQL vs PostgreSQL
›


Document
MongoDB vs CouchDB
›


Key-value
Redis vs DynamoDB
›


Wide-column
Cassandra vs HBase
›


Graph
Neo4j vs ArangoDB
›


Time-series
InfluxDB vs TimescaleDB
›


Search
Elasticsearch vs OpenSearch
›


Vector
pgvector vs dedicated vector database
›


Analytics
BigQuery / Snowflake vs ClickHouse
›


Avoid universal “faster” claims. Performance depends on schema design, indexes, partition keys, workload distribution, durability settings, hardware and network. Validate the final choice with representative benchmarks and failure-recovery tests.
08 — Video 10 teaching module
Making databases faster and scalable
Choosing the correct database is only the first decision. As data and traffic grow, the same database may become slow, overloaded, too large for one machine, or difficult to keep available. This lesson connects each scaling problem to the technique designed to solve it.

Opening story
The database was correct. The scale changed.
Imagine an e-commerce system using PostgreSQL for products, customers, orders and payments. At launch, ten thousand products and a few hundred requests per second work perfectly. A year later, the system holds one hundred million products, receives heavy read traffic, and the same product pages are requested repeatedly.

The wrong conclusion is: “PostgreSQL has failed; replace it.”

The correct conclusion is: “Our non-functional requirements changed. We need to change how the database is accessed and scaled.”

10,000 → 100M
Records grew dramatically
500 → 50,000
Requests per second increased
40 ms → 4 sec
Latency became unacceptable
1 server → bottleneck
One machine now handles everything
Core teaching line  →  Functional requirements describe what the system does. Non-functional requirements describe how well it must do it under load, failure and growth.
Non-functional requirements affected by the database
Latency
How quickly must a read or write complete? A product page may need tens of milliseconds, not several seconds.

Throughput
How many operations must the system process per second? Reads and writes often scale differently.

Scalability
Can capacity increase as users, traffic and stored data grow?

Availability
Can the service continue when a database node, zone or network link fails?

Durability
Once a write is acknowledged, can it survive process, machine or infrastructure failure?

Cost
Can the system meet its target without endlessly buying larger machines or overloading the team operationally?

Diagnose the problem before selecting the technique
Finding matching rows is slow
→
Indexing
The same result is requested repeatedly
→
Caching
One node cannot handle read traffic
→
Read replicas
A huge table is hard to manage or scan
→
Partitioning
One machine cannot hold or serve the dataset
→
Sharding
Connections and tiny repeated writes overwhelm the DB
→
Pooling & batching
0
First: measure and remove obvious waste
Scaling architecture cannot rescue a badly shaped query or an application opening thousands of unnecessary connections.

Check before adding infrastructure
Which queries consume the most time or database CPU?
Are applications requesting unnecessary columns or rows?
Is one endpoint issuing hundreds of database calls—the N+1 pattern?
Are writes sent one at a time when they could be batched?
Are connections reused through a connection pool?
Vertical scaling
The simplest first step may be a larger machine: more CPU, memory, faster storage or higher I/O limits. It requires little architectural change.

Database server
CPU: 4  →  16 cores
RAM: 16 → 128 GB
Disk: standard → high IOPS
Trade-off: Vertical scaling is easy but has a ceiling, may create a larger single point of failure, and can become expensive. Use it deliberately—not as the entire long-term strategy.
Teaching line: “Before distributing the database, make sure the application is not wasting the database it already has.”
1
Indexing — reduce the amount of data searched
An index is an additional data structure that helps the database locate matching records without scanning every row.

Without an index
To find one email among one hundred million users, the database may inspect row after row—a full table scan.

users table
row 1  → not it
row 2  → not it
...
row 78,422,901 → match
With an index
The index maintains an organized lookup from the searched value to the relevant row location.

email index
"a..." ─┐
"b..."  ├─ organized search
"bunny@example.com" → row 78,422,901
Good candidates
Columns frequently used in WHERE, joins, sorting or uniqueness checks
Queries that return a small portion of a large table
Composite access patterns such as (customer_id, created_at)
Why not index everything?
Every index consumes storage
Inserts and updates must also update the indexes
Unused or badly ordered indexes add cost without helping queries
Trade-off: Indexing exchanges extra storage and slower writes for faster targeted reads. It does not solve unlimited data growth or an overloaded server by itself.
Book analogy: A book index helps you jump to the relevant page. It does not reduce the total number of books in the library.
2
Caching — avoid repeating expensive reads
A cache stores frequently requested or expensive-to-compute results in a faster layer, often memory.

Cache-aside flow
1. App asks cache for product:42
2. Cache miss
3. App reads database
4. App stores result in cache
5. Next requests read cache
Useful for
Popular product details, configuration and reference data
Expensive aggregations or generated responses
Sessions, rate-limit counters and short-lived state
Read-heavy workloads where some staleness is acceptable
The hard part: invalidation
When the source changes, the cached value can become stale. Common controls include expiration time, explicit invalidation and versioned keys.

Failure patterns
Cache stampede when many requests miss simultaneously
Hot keys concentrating traffic on one cache node
Treating cache data as the only durable source of truth
Trade-off: Caching improves latency and reduces database load, but introduces stale-data risk and another distributed component to operate.
Layman analogy: Keep frequently used items on your desk instead of walking to the storeroom every time.
3
Replication — copy data to improve availability and read capacity
Replication maintains copies of the database on additional nodes.

Primary–replica model
                 ┌─ Replica 1 → reads
Writes → Primary ───┼─ Replica 2 → reads
                 └─ Replica 3 → reads
Writes normally go to the primary. Read-only traffic can be distributed across replicas.

What it solves
More read capacity
Failover when a node becomes unavailable
Copies in different zones or regions
Backup, analytics or reporting traffic isolation
Replication lag
With asynchronous replication, a replica may briefly return older data. A user who just changed their profile could read the old version from a lagging replica.

It does not split the dataset
Every replica commonly stores the same data. Replication increases copies and read capacity; it does not reduce the total dataset per copy.

Trade-off: More replicas improve read scale and resilience, but add infrastructure cost, replication delay and failover complexity. Replication does not automatically scale writes.
Layman analogy: Several branches keep copies of the same catalogue. Customers can read from any branch, but updates still need controlled synchronization.
4
Partitioning — divide a large logical table into manageable pieces
Partitioning breaks one logical dataset into smaller partitions based on a rule such as time, range, list or hash.

Example: orders by month
ORDERS (one logical table)
├── orders_2026_01
├── orders_2026_02
├── orders_2026_03
└── orders_2026_04
A query for March can scan only the March partition—called partition pruning.

Why partition?
Reduce the portion scanned by time- or range-based queries
Archive or delete old data partition by partition
Make maintenance and index management more manageable
Separate hot recent data from cold historical data
Common partitioning strategies
Range: date, ID or price intervals
List: region or category
Hash: distribute keys more evenly
Key point
Partitioning is a logical data-layout concept. The partitions may remain inside one database instance or may later be placed across multiple nodes, depending on the system.

Trade-off: A poor partition key creates skew, hot partitions or queries that touch every partition. Partitioning helps only when queries can use the partition rule.
Layman analogy: Instead of keeping ten years of files in one giant cabinet, use one drawer per year so you open only the drawer you need.
5
Sharding — distribute different subsets across different database servers
Sharding is horizontal partitioning across independent database nodes. Each shard owns only part of the total data.

Example: users by hash
hash(user_id) % 3

Shard 1 → subset of users
Shard 2 → subset of users
Shard 3 → subset of users
A routing layer or application logic determines which shard owns a user.

What it solves
Dataset no longer fits comfortably on one machine
Write throughput must be distributed
Storage and compute need to grow by adding nodes
Tenant or regional isolation is required
Choosing a shard key
It should spread traffic and data evenly
It should match frequent query routing
It should avoid hot customers, regions or time ranges
Changing it later can require expensive resharding
What becomes harder
Cross-shard joins and transactions
Global uniqueness and ordering
Rebalancing when adding or removing shards
Operational debugging, backups and migrations
Trade-off: Sharding increases write and storage capacity, but introduces the largest complexity jump in this lesson. Do it because measured limits require it—not because the system might become large someday.
Layman analogy: One warehouse is full, so inventory is divided among several warehouses. You now need a reliable rule to know which warehouse holds each item.
Partitioning vs sharding vs replication
Technique	What is divided or copied?	Main goal	Typical difficulty
Partitioning	One logical table is divided into smaller pieces	Manage and query a large dataset efficiently	Choosing a useful partition key
Sharding	Different data subsets are placed on different servers	Scale storage and writes horizontally	Routing, rebalancing and cross-shard operations
Replication	The same data is copied to additional servers	Availability and read scalability	Lag, failover and consistency
A realistic evolution path
This is not a rigid recipe. It is a useful order of thought: apply the least complex technique that solves the measured bottleneck.

1. Good schema & queries
Stop unnecessary scans, calls and connections.
2. Index
Make targeted lookups efficient.
3. Scale vertically
Use more CPU, memory and faster storage where economical.
4. Cache
Remove repeated reads from the database.
5. Replicate
Distribute reads and improve availability.
6. Partition
Manage very large tables and data lifecycles.
7. Shard
Distribute data and writes when one node is no longer enough.
Common mistakes to warn students about
Adding every technique at day one
Complexity is not scalability. Build for known requirements and leave clear paths for future growth.
Calling partitioning and sharding identical
Sharding is distributed horizontal partitioning; partitioning does not necessarily mean multiple servers.
Assuming replicas solve write load
Traditional read replicas help reads and availability. Writes may still bottleneck on the primary.
Indexing every column
More indexes can slow writes, consume space and confuse maintenance without improving real queries.
Caching without a staleness policy
Define expiry, invalidation and the source of truth before adding a cache.
Choosing a shard key only for even data size
The key must also route common queries and distribute traffic—not merely stored bytes.
How to answer this in a system design interview
“I would first identify the actual bottleneck using query latency, database CPU, I/O, connection count and read/write throughput. For slow selective queries, I would add appropriate indexes. For repeated read-heavy traffic, I would introduce cache and potentially read replicas, while accounting for invalidation and replica lag. If individual tables become very large, I would partition them around dominant access patterns such as time. I would move to sharding only when one node can no longer meet storage or write-throughput requirements, because sharding introduces routing, rebalancing and cross-shard complexity.”

Final takeaway  →  Indexing reduces searched data. Caching avoids repeated work. Replication creates copies. Partitioning divides a logical dataset. Sharding distributes different subsets across servers. The correct technique depends on the bottleneck—not on popularity.
Database Choice & Scaling Bible · built for the System Design Fundamentals series

Final implementation decisions should be checked against current official product documentation and validated with representative benchmarks, operational tests, backup restores and failure simulations.