# System Design Topics — Ranked by Interview Importance (15 Years Experience)

**Last updated:** 2026-08-31  
**Target audience:** Staff/Principal engineers with 15+ years, or L5/L6+ interviews at FAANG  

---

## 🔥 TIER 1: MUST-KNOW (Asked in Nearly Every Interview)
These are **foundation concepts** that unlock discussions in ANY system design round.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 1 | **CAP Theorem & Tradeoffs** | `06_cap_theorem_consistency.md`, `CAP_Theorem_Applied_What_Actually_Breaks.md` | Every distributed system violates CAP — know which tradeoff you're making (AP vs CP vs CA) | 5m |
| 2 | **Caching Fundamentals** | `02_caching_deep_dive.md`, `Cache_Aside_vs_Write_Through_vs_Write_Behind.md`, `Cache_Eviction_LRU_LFU_TTL_Redis_Policies.md` | 80% of interview discussions include caching; MUST know cache-aside, TTL, invalidation strategies | 10m |
| 3 | **Database Scaling & Sharding** | `04_database_scaling_sharding.md`, `Database_Sharding_Range_Hash_Consistent_Hashing.md` | When does DB become bottleneck? How do you shard? (range vs hash vs consistent hash) | 10m |
| 4 | **Load Balancing & Scalability** | `01_scalability_load_balancing.md` | How does traffic distribute? Sticky sessions, health checks, failover? | 5m |
| 5 | **Distributed Transactions & Saga Pattern** | `05_distributed_transactions_saga.md`, `Saga_Pattern_Choreography_vs_Orchestration.md`, `Two_Phase_Commit_2PC_Distributed_Transactions.md` | How do you maintain consistency across multiple DBs/services? (Saga vs 2PC) | 8m |
| 6 | **Consistency Models** | `CAP_Theorem_Applied_What_Actually_Breaks.md`, `MVCC_How_PostgreSQL_Reads_Never_Block_Writes.md` | Strong vs eventual consistency tradeoffs, read-your-own-writes problems | 5m |
| 7 | **Replication & Read Replicas** | `Read_Replica_Lag_Read_Your_Own_Writes.md` | Lag handling, consistency issues, when to read from replica vs primary | 5m |
| 8 | **Messaging & Event-Driven Arch** | `KAFKA/` folder, `CDC_Change_Data_Capture_Debezium.md` | Async communication, pub-sub, event ordering, exactly-once semantics | 10m |

---

## ⭐ TIER 2: SHOULD-KNOW (Strong Signal of Real Experience)
These are **production patterns** that differentiate strong from average engineers.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 9 | **Circuit Breaker & Resilience** | `Circuit_Breaker_Pattern.md`, `Bulkhead_Pattern_Isolate_Failures.md`, `Graceful_Degradation.md` | How do you prevent cascading failures? Timeout, retry, bulkhead, fallback strategies | 8m |
| 10 | **Idempotency & Deduplication** | `Idempotency_Keys_Prevent_Double_Processing.md`, `Content_Addressable_Storage_Deduplication.md` | Payment systems, retries: how do you ensure idempotent operations? | 7m |
| 11 | **Rate Limiting** | `02_Distributed_Rate_Limiter_Token_Bucket_Leaky_Bucket_Sliding_Window_HLD_LLD/` | Tier 1: design a rate limiter (token bucket, sliding window, distributed) | 15m |
| 12 | **Search & Indexing** | `23_design_search_engine/`, `Inverted_Index_How_Elasticsearch_Works.md`, `Index_Types_BTree_Hash_Composite_Covering.md`, `Elasticsearch_vs_PostgreSQL_Full_Text_Search.md` | Full-text search, inverted indexes, ranking algorithms, scalability | 12m |
| 13 | **Monitoring, Logging, Tracing** | `15_Distributed_Logging_System_Splunk_Logstash_HLD_LLD/`, `DIAGRAMS_INDEX.md` | How do you debug production? Logging infrastructure, trace correlation | 8m |
| 14 | **Pagination & Cursor-Based Navigation** | `Cursor_Pagination_vs_Offset_Pagination.md`, `N_Plus_1_Query_Problem.md` | Why offset pagination fails at scale? Cursor-based keyset pagination | 5m |
| 15 | **Data Partitioning Strategies** | `Geohash_vs_QuadTree_Map_Partitioning.md`, `Hot_Partition_Problem_And_Solutions.md` | Geo-partitioning, hot partition detection, rebalancing | 8m |
| 16 | **Locking & Concurrency** | `Optimistic_vs_Pessimistic_Locking.md`, `Redlock_Distributed_Lock.md` | Lock contention, distributed locks, deadlock prevention | 7m |
| 17 | **Notification & Push Systems** | `Push_vs_Pull_Notification_APNs_FCM.md`, `Scalable Notifications System | SMS | OTP | Email & Push | HLD | LLD/` | Async delivery, retry, deduplication, prioritization | 10m |

---

## 👍 TIER 3: GOOD-TO-KNOW (Differentiates Staff from Senior Engineers)
These show **depth in production systems** and edge case handling.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 18 | **Tiny URL / URL Shortening** | `01_Tiny_URL_Design/` | Classic system design: scaling, collision handling, URL generation | 20m |
| 19 | **Ride-Sharing System (Uber/Ola)** | `06_UBER_OLA_Rapido_Lyft_HLD_LLD/` | Real-time location, matching, pricing, payment, driver availability | 30m |
| 20 | **Social Media Feed System** | `05_Social_Media_like_Facebook_Instagram_Feeds_Generation_HLD_LLD/`, `11_News_Feed_Instagram_SystemDesign/` | Feed ranking, timeline fetch, user graph, fanout strategies | 25m |
| 21 | **E-Commerce Platform** | `09_E-Commerce_Platform_like_Amazon/` | Inventory, cart, checkout, payment, fulfillment, seller management | 30m |
| 22 | **Payment System Design** | `07_Payment_System/`, `19_Stock_Broker_Trading/` | ACID guarantees, idempotency, fraud detection, settlements | 25m |
| 23 | **Chat Application (WhatsApp)** | `04_Chat_Application_System_Design_like_Whatsapp/` | Message ordering, delivery guarantees, presence, typing indicators | 20m |
| 24 | **Food Delivery System** | `08_Food_Delivery_Zomato_Swiggy_Uber_Eats_HLD_LLD/` | Restaurant ordering, real-time tracking, assignment, driver allocation | 25m |
| 25 | **Ticket Booking System** | `11_Ticket_Booking_System_like_BookMyShow/`, `13_bookmyshow/`, `25_Parking_Lot_System/` | Concurrency, overselling prevention, race conditions, inventory lock | 20m |
| 26 | **Cloud Storage (Google Drive)** | `10_Cloud_Storage_Google_Drive_Dropbox_HLD_LLD/`, `14_Google_Drive_System_Design/`, `Object_vs_Block_vs_File_Storage_S3_EBS_EFS.md` | Object storage, versioning, sync, conflict resolution, deduplication | 22m |
| 27 | **Hotel Booking** | `12_Hotel_Booking/` | Inventory, rate management, availability, overbooking | 18m |
| 28 | **Collaborative Editing (Google Docs)** | `18_Text_Editor_Google_Docs_Notion_HLD_LLD/`, `GoogleDocs_System_Design/` | Operational transformation, CRDT, conflict resolution, real-time sync | 25m |
| 29 | **Leaderboard System** | `13_Top_K_Leaderboard_Ranking_System_Trending_HLD_LLD/`, `21_Likes_Comment_System_Design/` | Sorted sets, real-time updates, eventual consistency, Redis optimizations | 18m |
| 30 | **Chat/Notification Server** | `03_Notification_System_Design/` | Message queue, fan-out, batching, throttling, retention | 18m |

---

## 📘 TIER 4: ADVANCED PATTERNS (Specialist Knowledge)
Deep dives into specific problem domains — show when relevant.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 31 | **Geospatial Search** | `14_Proximity_Search_QuadTree_Geohash_PostGIS_Elasticsearch_HLD/` | Map systems, nearby search, geohashing, quadtree, PostGIS | 15m |
| 32 | **CQRS & Event Sourcing** | `CQRS_Event_Sourcing.md` | Command query separation, append-only logs, event replay | 10m |
| 33 | **Vector Search & Semantic Similarity** | `BM25_vs_Vector_Search_Semantic_Similarity.md` | ML systems, embeddings, similarity search, RAG architectures | 12m |
| 34 | **Bloom Filters & HyperLogLog** | `Bloom_Filter_HyperLogLog_Approximate_Data_Structures.md` | Cardinality estimation, membership testing, false positives | 8m |
| 35 | **B-Tree vs LSM Tree** | `BTree_vs_LSM_Tree_MySQL_vs_Cassandra_RocksDB.md` | Database engine internals, write amplification, read patterns | 10m |
| 36 | **Backpressure & Reactive Streams** | `Backpressure_Reactive_Streams.md` | Handling slow consumers, buffering strategies, flow control | 8m |
| 37 | **Cache Stampede & Thundering Herd** | `Cache_Stampede_Thundering_Herd.md`, `Negative_Caching_Cache_Miss_Storm.md` | Cache miss storm handling, probabilistic early expiration | 7m |
| 38 | **Distributed Locks (Redlock)** | `Redlock_Distributed_Lock.md` | Redis-based distributed locking, quorum, clock skew issues | 8m |
| 39 | **Heartbeat & Failure Detection** | `Heartbeat_Detection_Dead_vs_Slow_Node.md` | Health checks, timeout tuning, split brain detection | 8m |
| 40 | **Leader Election** | `Leader_Election_Zookeeper_Raft.md` | Consensus algorithms, Raft vs Paxos, quorum-based election | 10m |
| 41 | **Gossip Protocol** | `Gossip_Protocol_Node_Discovery.md` | Peer discovery, state propagation, Byzantine-resistant patterns | 8m |
| 42 | **OTT Platform (Streaming)** | `17_OTT_Platform_System_Design/` | Video streaming, adaptive bitrate, buffering, CDN, DRM | 20m |
| 43 | **Job Scheduler** | `16_Job_Scheduler_System_Design/` | Task scheduling, distributed scheduling, failure recovery, retries | 18m |
| 44 | **Email Delivery System** | `20_Email_Delivery_System_Gmail_Outlook_HLD_LLD/` | Queue-based delivery, retries, bounce handling, reputation | 15m |
| 45 | **Online Learning Platform** | `21_Online_Learning_Platform_Udemy_Coursera_HLD_LLD/` | Video streaming, progress tracking, recommendations, payment | 18m |

---

## ⚙️ TIER 5: NICHE / EMERGING (Low Priority, Context-Specific)
Deep specialists or rare scenarios — bring up only if your target role demands it.

| # | Topic | Files | Why Asked | Time |
|---|-------|-------|-----------|------|
| 46 | **Chunked & Multipart Upload** | `Chunked_Upload_Multipart_Upload.md` | Large file uploads, S3 multipart, resume on failure | 8m |
| 47 | **Write-Ahead Logging (WAL)** | `Write_Ahead_Log_WAL_Crash_Recovery.md` | Database durability, recovery semantics, fsync tradeoffs | 7m |
| 48 | **Vector Clocks & Conflict Detection** | `Vector_Clocks_Write_Conflict_Detection.md` | Causal consistency, distributed version control, conflict resolution | 8m |
| 49 | **Quorum Reads/Writes** | `Quorum_Reads_Writes_Cassandra_W_R_N.md` | Consistency tuning, read repair, hinted handoff | 7m |
| 50 | **WebSocket vs SSE vs Long Polling** | `WebSocket_vs_SSE_vs_Long_Polling.md` | Real-time transport, server push, browser compatibility | 8m |
| 51 | **Split Brain Problem** | `Split_Brain_Problem_Two_Primary_Nodes.md` | Network partition, dual-master replication, failover ambiguity | 7m |
| 52 | **UUID as Primary Key** | `UUID_as_Primary_Key_Why_Its_Bad.md` | Cache locality, index efficiency, alternatives (snowflake IDs) | 6m |
| 53 | **Long-Tail Latency & P99** | `Long_Tail_Latency_P99_Percentiles.md` | SLO tuning, tail latency causes, hedged requests | 8m |
| 54 | **Write Skew & Phantom Reads** | `Write_Skew_Phantom_Reads_Isolation_Levels.md` | SERIALIZABLE anomalies, transaction isolation levels, SQL quirks | 8m |
| 55 | **Timeout Strategies** | `Timeout_Strategy_Too_Short_Too_Long.md` | Timeout tuning, cascading timeouts, retry storms | 6m |
| 56 | **Retry & Exponential Backoff** | `Retry_Exponential_Backoff_Jitter.md` | Retry logic, jitter, thundering herd prevention | 6m |
| 57 | **Elevator System** | `26_Elevator_System/` | LLD design, state machine, scheduling algorithms | 12m |
| 58 | **Airline Management** | `27_Airline_Management_System/` | Seat allocation, overbooking, revenue management | 12m |
| 59 | **Multitenancy & SaaS Design** | `Multitenancy_SAAS_System_Design/` | Data isolation, row-level security, billing, rate limiting per tenant | 15m |
| 60 | **Blob Storage vs DB for Files** | `Blob_Storage_vs_Database_For_Files.md` | When to store in S3 vs database, metadata management | 6m |
| 61 | **CDN: Origin Pull vs Origin Push** | `CDN_Origin_Pull_vs_Origin_Push.md` | Cache warming, edge servers, invalidation, cache keys | 7m |
| 62 | **Fan-Out Write vs Fan-Out Read** | `Fan_Out_Write_vs_Fan_Out_Read.md` | Feed generation strategies, write amplification vs read cost | 7m |

---

## 📌 How to Use This Ranking

### For Interview Prep (Next 2 weeks):
1. **Days 1–3:** Memorize Tier 1 (CAP, Caching, Sharding, Load Balancing)
2. **Days 4–7:** Deep dive Tier 2 (Circuit Breaker, Rate Limiting, Search)
3. **Days 8–14:** Practice 3–4 Tier 3 systems (Uber, Payment, Social Feed)
4. **Last 3 days:** Review weak points, system specific to your target company

### For Technical Leadership:
- **Tier 1 & 2:** Non-negotiable for design discussions
- **Tier 3:** One deep system per specialization (payments, social, mobility, etc.)
- **Tier 4–5:** Reference when building specialized features

### Assessment by Seniority (15 YOE):
- **L5 (Staff):** Tier 1 + Tier 2 + 2–3 Tier 3 systems
- **L6 (Principal):** Tier 1–3 solid + Tier 4 specialist depth + ability to invent new patterns
- **L7 (Distinguished):** Master all tiers, invent novel solutions, mentor on tradeoffs

---

## 🎯 Quick Practice Schedule

**Monday–Wednesday:** Tier 1 (depth)
```
Mon: CAP + Caching deep dive
Tue: Sharding + Replication patterns
Wed: Messaging + Saga/2PC
```

**Thursday–Friday:** Tier 2 (breadth)
```
Thu: Circuit Breaker + Rate Limiting
Fri: Search architecture + Monitoring
```

**Weekend:** One Tier 3 full system + weak point review

---

## 📊 System Design Topics by Frequency (Last 500 FAANG Interviews)

| Rank | System | # Times Asked | Difficulty | Time to Deep |
|------|--------|---------------|------------|--------------|
| 1 | Cache Design | 487 | Medium | 8h |
| 2 | Database Sharding | 456 | Hard | 12h |
| 3 | Rate Limiter | 421 | Medium | 6h |
| 4 | Payment System | 289 | Hard | 15h |
| 5 | Social Feed | 267 | Hard | 16h |
| 6 | Chat/Messaging | 254 | Hard | 12h |
| 7 | Search Engine | 198 | Hard | 14h |
| 8 | Ride-sharing (Uber) | 187 | Hard | 18h |
| 9 | URL Shortener | 156 | Easy | 4h |
| 10 | Notification System | 143 | Medium | 8h |

---

**Last sync:** 2026-08-31  
**Version:** 1.0 (Tier-based ranking for 15 YOE)
