# System Design — File-to-Sequence Quick Map

**For fast reference: which sequence # maps to which file/folder**

## Tier 1: MUST-KNOW (Seq #1–8)

```
001 CAP Theorem
    └─ System_Design/06_cap_theorem_consistency.md
    └─ System_Design/CAP_Theorem_Applied_What_Actually_Breaks.md

002 Caching Fundamentals  
    └─ System_Design/02_caching_deep_dive.md
    └─ System_Design/Cache_Aside_vs_Write_Through_vs_Write_Behind.md
    └─ System_Design/Cache_Eviction_LRU_LFU_TTL_Redis_Policies.md

003 Database Scaling & Sharding
    └─ System_Design/04_database_scaling_sharding.md
    └─ System_Design/Database_Sharding_Range_Hash_Consistent_Hashing.md

004 Load Balancing & Scalability
    └─ System_Design/01_scalability_load_balancing.md

005 Distributed Transactions & Saga
    └─ System_Design/05_distributed_transactions_saga.md
    └─ System_Design/Saga_Pattern_Choreography_vs_Orchestration.md
    └─ System_Design/Two_Phase_Commit_2PC_Distributed_Transactions.md

006 Consistency Models
    └─ System_Design/CAP_Theorem_Applied_What_Actually_Breaks.md
    └─ System_Design/MVCC_How_PostgreSQL_Reads_Never_Block_Writes.md

007 Replication & Read Replicas
    └─ System_Design/Read_Replica_Lag_Read_Your_Own_Writes.md

008 Messaging & Event-Driven Arch
    └─ System_Design/KAFKA/ (entire folder)
    └─ System_Design/CDC_Change_Data_Capture_Debezium.md
```

---

## Tier 2: SHOULD-KNOW (Seq #9–17)

```
009 Circuit Breaker & Resilience
    └─ System_Design/Circuit_Breaker_Pattern.md
    └─ System_Design/Bulkhead_Pattern_Isolate_Failures.md
    └─ System_Design/Graceful_Degradation.md

010 Idempotency & Deduplication
    └─ System_Design/Idempotency_Keys_Prevent_Double_Processing.md
    └─ System_Design/Content_Addressable_Storage_Deduplication.md

011 Rate Limiting
    └─ System_Design/system_design_interviewwithbunny/02_Distributed_Rate_Limiter_Token_Bucket_Leaky_Bucket_Sliding_Window_HLD_LLD/

012 Search & Indexing
    └─ System_Design/23_design_search_engine/
    └─ System_Design/Inverted_Index_How_Elasticsearch_Works.md
    └─ System_Design/Index_Types_BTree_Hash_Composite_Covering.md
    └─ System_Design/Elasticsearch_vs_PostgreSQL_Full_Text_Search.md

013 Monitoring, Logging, Tracing
    └─ System_Design/system_design_interviewwithbunny/15_Distributed_Logging_System_Splunk_Logstash_HLD_LLD/
    └─ System_Design/DIAGRAMS_INDEX.md

014 Pagination & Cursor-Based Navigation
    └─ System_Design/Cursor_Pagination_vs_Offset_Pagination.md
    └─ System_Design/N_Plus_1_Query_Problem.md

015 Data Partitioning Strategies
    └─ System_Design/Geohash_vs_QuadTree_Map_Partitioning.md
    └─ System_Design/Hot_Partition_Problem_And_Solutions.md

016 Locking & Concurrency
    └─ System_Design/Optimistic_vs_Pessimistic_Locking.md
    └─ System_Design/Redlock_Distributed_Lock.md

017 Notification & Push Systems
    └─ System_Design/Push_vs_Pull_Notification_APNs_FCM.md
    └─ System_Design/Scalable Notifications System | SMS | OTP | Email & Push | HLD | LLD/
```

---

## Tier 3: GOOD-TO-KNOW (Seq #18–30)

```
018 Tiny URL / URL Shortening
    └─ System_Design/system_design_interviewwithbunny/01_Tiny_URL_Design/

019 Ride-Sharing System (Uber/Ola)
    └─ System_Design/system_design_interviewwithbunny/06_UBER_OLA_Rapido_Lyft_HLD_LLD/

020 Social Media Feed System
    └─ System_Design/system_design_interviewwithbunny/05_Social_Media_like_Facebook_Instagram_Feeds_Generation_HLD_LLD/
    └─ System_Design/11_News_Feed_Instagram_SystemDesign/

021 E-Commerce Platform
    └─ System_Design/system_design_interviewwithbunny/09_E-Commerce_Platform_like_Amazon/

022 Payment System Design
    └─ System_Design/system_design_interviewwithbunny/07_Payment_System/
    └─ System_Design/system_design_interviewwithbunny/19_Stock_Broker_Trading/

023 Chat Application (WhatsApp)
    └─ System_Design/system_design_interviewwithbunny/04_Chat_Application_System_Design_like_Whatsapp/

024 Food Delivery System
    └─ System_Design/system_design_interviewwithbunny/08_Food_Delivery_Zomato_Swiggy_Uber_Eats_HLD_LLD/

025 Ticket Booking System
    └─ System_Design/system_design_interviewwithbunny/11_Ticket_Booking_System_like_BookMyShow/
    └─ System_Design/13_bookmyshow/
    └─ System_Design/25_Parking_Lot_System/

026 Cloud Storage (Google Drive)
    └─ System_Design/system_design_interviewwithbunny/10_Cloud_Storage_Google_Drive_Dropbox_HLD_LLD/
    └─ System_Design/14_Google_Drive_System_Design/
    └─ System_Design/Object_vs_Block_vs_File_Storage_S3_EBS_EFS.md

027 Hotel Booking
    └─ System_Design/system_design_interviewwithbunny/12_Hotel_Booking/

028 Collaborative Editing (Google Docs)
    └─ System_Design/system_design_interviewwithbunny/18_Text_Editor_Google_Docs_Notion_HLD_LLD/
    └─ System_Design/18_GoogleDocs_System_Design/

029 Leaderboard System
    └─ System_Design/system_design_interviewwithbunny/13_Top_K_Leaderboard_Ranking_System_Trending_HLD_LLD/
    └─ System_Design/21_Likes_Comment_System_Design/

030 Chat/Notification Server
    └─ System_Design/system_design_interviewwithbunny/03_Notification_System_Design/
```

---

## Tier 4: ADVANCED PATTERNS (Seq #31–45)

```
031 Geospatial Search
    └─ System_Design/system_design_interviewwithbunny/14_Proximity_Search_QuadTree_Geohash_PostGIS_Elasticsearch_HLD/

032 CQRS & Event Sourcing
    └─ System_Design/CQRS_Event_Sourcing.md

033 Vector Search & Semantic Similarity
    └─ System_Design/BM25_vs_Vector_Search_Semantic_Similarity.md

034 Bloom Filters & HyperLogLog
    └─ System_Design/Bloom_Filter_HyperLogLog_Approximate_Data_Structures.md

035 B-Tree vs LSM Tree
    └─ System_Design/BTree_vs_LSM_Tree_MySQL_vs_Cassandra_RocksDB.md

036 Backpressure & Reactive Streams
    └─ System_Design/Backpressure_Reactive_Streams.md

037 Cache Stampede & Thundering Herd
    └─ System_Design/Cache_Stampede_Thundering_Herd.md
    └─ System_Design/Negative_Caching_Cache_Miss_Storm.md

038 Distributed Locks (Redlock)
    └─ System_Design/Redlock_Distributed_Lock.md

039 Heartbeat & Failure Detection
    └─ System_Design/Heartbeat_Detection_Dead_vs_Slow_Node.md

040 Leader Election
    └─ System_Design/Leader_Election_Zookeeper_Raft.md

041 Gossip Protocol
    └─ System_Design/Gossip_Protocol_Node_Discovery.md

042 OTT Platform (Streaming)
    └─ System_Design/system_design_interviewwithbunny/17_OTT_Platform_System_Design/

043 Job Scheduler
    └─ System_Design/system_design_interviewwithbunny/16_Job_Scheduler_System_Design/

044 Email Delivery System
    └─ System_Design/system_design_interviewwithbunny/20_Email_Delivery_System_Gmail_Outlook_HLD_LLD/

045 Online Learning Platform
    └─ System_Design/system_design_interviewwithbunny/21_Online_Learning_Platform_Udemy_Coursera_HLD_LLD/
```

---

## Tier 5: NICHE / EMERGING (Seq #46–62)

```
046 Chunked & Multipart Upload
    └─ System_Design/Chunked_Upload_Multipart_Upload.md

047 Write-Ahead Logging (WAL)
    └─ System_Design/Write_Ahead_Log_WAL_Crash_Recovery.md

048 Vector Clocks & Conflict Detection
    └─ System_Design/Vector_Clocks_Write_Conflict_Detection.md

049 Quorum Reads/Writes
    └─ System_Design/Quorum_Reads_Writes_Cassandra_W_R_N.md

050 WebSocket vs SSE vs Long Polling
    └─ System_Design/WebSocket_vs_SSE_vs_Long_Polling.md

051 Split Brain Problem
    └─ System_Design/Split_Brain_Problem_Two_Primary_Nodes.md

052 UUID as Primary Key
    └─ System_Design/UUID_as_Primary_Key_Why_Its_Bad.md

053 Long-Tail Latency & P99
    └─ System_Design/Long_Tail_Latency_P99_Percentiles.md

054 Write Skew & Phantom Reads
    └─ System_Design/Write_Skew_Phantom_Reads_Isolation_Levels.md

055 Timeout Strategies
    └─ System_Design/Timeout_Strategy_Too_Short_Too_Long.md

056 Retry & Exponential Backoff
    └─ System_Design/Retry_Exponential_Backoff_Jitter.md

057 Elevator System
    └─ System_Design/26_Elevator_System/

058 Airline Management
    └─ System_Design/27_Airline_Management_System/

059 Multitenancy & SaaS Design
    └─ System_Design/Multitenancy_SAAS_System_Design/

060 Blob Storage vs DB for Files
    └─ System_Design/Blob_Storage_vs_Database_For_Files.md

061 CDN: Origin Pull vs Origin Push
    └─ System_Design/CDN_Origin_Pull_vs_Origin_Push.md

062 Fan-Out Write vs Fan-Out Read
    └─ System_Design/Fan_Out_Write_vs_Fan_Out_Read.md
```

---

## 🎯 Print This Quick Reference

**Tier 1 (Memorize First):** 001–008  
**Tier 2 (Interview Must-Haves):** 009–017  
**Tier 3 (Full System Practices):** 018–030  
**Tier 4 (Specialist Topics):** 031–045  
**Tier 5 (Context-Specific):** 046–062  

**Total:** 62 distinct topics/systems ranked by importance
