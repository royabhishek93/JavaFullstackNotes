# High-Level Design: Distributed Cache System (LRU-based)

## System Overview
Design a distributed, scalable caching system similar to Redis/Memcached with LRU eviction policy, serving millions of requests per second with sub-millisecond latency.

---

## Requirements

### Functional Requirements
1. **Put(key, value)**: Store key-value pair
2. **Get(key)**: Retrieve value by key
3. **Delete(key)**: Remove key-value pair
4. **LRU Eviction**: Automatically evict least recently used items when cache is full
5. **TTL Support**: Keys expire after specified time
6. **Distributed**: Data partitioned across multiple nodes
7. **Persistence**: Optional disk backup for durability

### Non-Functional Requirements
1. **Latency**: < 1ms for get/put operations (p99)
2. **Throughput**: 100K+ requests/second per node
3. **Availability**: 99.99% uptime (52 minutes downtime/year)
4. **Scalability**: Horizontal scaling to 100+ nodes
5. **Consistency**: Eventual consistency acceptable
6. **Durability**: Optional (can trade for performance)

---

## Capacity Estimation

### Traffic
- **Total Keys**: 1 billion keys
- **Requests per second**: 1M reads/sec, 100K writes/sec
- **Cache Hit Ratio**: 80% (target)
- **Average key size**: 50 bytes
- **Average value size**: 1KB

### Storage
- **Total data**: 1B keys × (50B + 1KB) ≈ 1TB
- **Per node (100 nodes)**: 10GB
- **With replication (3x)**: 30GB per node
- **Memory needed**: 32GB RAM per node

### Network Bandwidth
- **Read**: 1M req/s × 1KB = 1GB/s = 8 Gbps
- **Write**: 100K req/s × 1KB = 100MB/s = 800 Mbps

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        Clients                               │
│  (Web servers, Mobile apps, Microservices)                   │
└─────────────┬────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Load Balancer / Proxy Layer                 │
│         (Consistent Hashing for key distribution)            │
└─────────────┬───────────────────────────────────────────────┘
              │
      ┌───────┼───────┬───────────┬───────────┐
      │       │       │           │           │
      ▼       ▼       ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Cache   │ │ Cache   │ │ Cache   │ │ Cache   │ │ Cache   │
│ Node 1  │ │ Node 2  │ │ Node 3  │ │ Node N  │ │ Node    │
│         │ │         │ │         │ │  ...    │ │ 100     │
│ Master  │ │ Master  │ │ Master  │ │         │ │         │
└────┬────┘ └────┬────┘ └────┬────┘ └─────────┘ └─────────┘
     │           │           │
     ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐
│ Replica │ │ Replica │ │ Replica │
│  Node   │ │  Node   │ │  Node   │
└─────────┘ └─────────┘ └─────────┘
```

---

## Core Components

### 1. Client Library (Smart Client)
**Responsibilities**:
- **Consistent hashing**: Route requests to correct cache node
- **Connection pooling**: Reuse TCP connections
- **Retry logic**: Handle transient failures
- **Circuit breaker**: Fail fast when node is down
- **Compression**: Optionally compress large values

**Consistent Hashing**:
```
hash(key) % num_nodes = target_node

Example:
hash("user:123") = 42
42 % 100 nodes = Node 42
```

**Virtual Nodes**: Each physical node has 100-200 virtual nodes to ensure even distribution

```python
class CacheClient:
    def __init__(self, nodes):
        self.hash_ring = ConsistentHashRing(nodes, virtual_nodes=150)
        self.connection_pool = ConnectionPool(max_connections=100)
    
    def get(self, key):
        node = self.hash_ring.get_node(key)
        conn = self.connection_pool.get_connection(node)
        return conn.execute("GET", key)
    
    def put(self, key, value, ttl=None):
        node = self.hash_ring.get_node(key)
        conn = self.connection_pool.get_connection(node)
        return conn.execute("SET", key, value, ttl)
```

---

### 2. Cache Node (Single Instance)

#### In-Memory Data Structure
```
┌──────────────────────────────────────────────────────┐
│              HashMap (Key → Node*)                   │
│  ┌────────┬────────┬────────┬────────┬────────┐     │
│  │ Bucket │ Bucket │ Bucket │ Bucket │ Bucket │ ... │
│  │   0    │   1    │   2    │   3    │   4    │     │
│  └───┬────┴────────┴────────┴────────┴────────┘     │
│      │                                               │
│      ▼                                               │
│  ┌────────┐    ┌────────┐    ┌────────┐            │
│  │ Entry  │───▶│ Entry  │───▶│ Entry  │            │
│  └────────┘    └────────┘    └────────┘            │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│        Doubly Linked List (LRU Order)                │
│                                                       │
│   HEAD                                        TAIL   │
│   (MRU)                                       (LRU)  │
│     │                                           │    │
│     ▼                                           ▼    │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐      │
│  │Node │◀─┤Node │◀─┤Node │◀─┤Node │◀─┤Node │      │
│  │  1  │─▶│  2  │─▶│  3  │─▶│  4  │─▶│  5  │      │
│  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘      │
│                                                      │
└──────────────────────────────────────────────────────┘
```

#### Node Structure
```c++
struct CacheEntry {
    string key;
    string value;
    uint64_t expiry_time;  // TTL
    CacheEntry* prev;
    CacheEntry* next;
};

class CacheNode {
    unordered_map<string, CacheEntry*> cache;
    CacheEntry* head;  // Most recently used
    CacheEntry* tail;  // Least recently used
    size_t capacity;
    size_t current_size;
    mutex cache_mutex;  // Thread safety
    
public:
    string get(const string& key) {
        lock_guard<mutex> lock(cache_mutex);
        
        auto it = cache.find(key);
        if (it == cache.end() || isExpired(it->second)) {
            return "";  // Cache miss
        }
        
        // Move to front (most recently used)
        moveToFront(it->second);
        return it->second->value;
    }
    
    void put(const string& key, const string& value, int ttl) {
        lock_guard<mutex> lock(cache_mutex);
        
        auto it = cache.find(key);
        if (it != cache.end()) {
            // Update existing
            it->second->value = value;
            it->second->expiry_time = now() + ttl;
            moveToFront(it->second);
        } else {
            // Add new
            if (current_size >= capacity) {
                evictLRU();  // Remove tail
            }
            CacheEntry* entry = new CacheEntry{key, value, now() + ttl};
            cache[key] = entry;
            addToFront(entry);
            current_size++;
        }
    }
    
    void evictLRU() {
        if (tail) {
            cache.erase(tail->key);
            removeNode(tail);
            delete tail;
            current_size--;
        }
    }
};
```

---

### 3. Replication

#### Master-Slave Replication
```
┌──────────┐
│  Master  │ ◀── Writes go here
│  Node    │
└────┬─────┘
     │ (Async replication)
     ├─────────────┬─────────────┐
     ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Replica  │ │ Replica  │ │ Replica  │
│  Node 1  │ │  Node 2  │ │  Node 3  │
└──────────┘ └──────────┘ └──────────┘
     ▲             ▲             ▲
     └─────────────┴─────────────┘
         Reads can go to any
```

**Write Path**:
1. Client writes to Master
2. Master acknowledges immediately (async)
3. Master replicates to Replicas in background
4. Replicas apply changes

**Read Path**:
1. Client can read from Master OR any Replica
2. Eventual consistency (may read stale data briefly)

**Failover**:
- If Master dies → Promote Replica to Master
- Detection: Heartbeat + Zookeeper/etcd for consensus
- Automatic failover in < 10 seconds

---

### 4. Consistent Hashing

#### Why Consistent Hashing?
**Problem**: Simple modulo hashing (`hash(key) % N`) causes massive data movement when nodes are added/removed.

**Solution**: Consistent hashing with virtual nodes.

#### Implementation
```
┌────────────────────────────────────────────┐
│          Hash Ring (0 to 2^32)             │
│                                            │
│    0                                       │
│    │                                       │
│    ├── VNode 1-1 (Physical Node 1)        │
│    ├── VNode 2-3 (Physical Node 2)        │
│    ├── VNode 3-1 (Physical Node 3)        │
│    ├── VNode 1-2 (Physical Node 1)        │
│    ├── Key "user:123" (hash = 500)        │
│    ├── VNode 2-1 (Physical Node 2)        │
│    │    Routes to VNode 2-1               │
│    ├── VNode 3-2 (Physical Node 3)        │
│    ...                                     │
│    └── 2^32                                │
└────────────────────────────────────────────┘
```

**Algorithm**:
1. Hash each physical node 150 times (virtual nodes) → Place on ring
2. Hash the key → Find next virtual node clockwise
3. Map virtual node → Physical node

**Benefits**:
- Adding/removing node affects only neighboring nodes (~1/N keys move)
- Even distribution with virtual nodes
- Minimal data reshuffling

---

### 5. Persistence (Optional)

#### Append-Only Log (AOF)
Write every mutation to disk log:
```
SET user:123 "John Doe" TTL:3600
SET session:abc "xyz123" TTL:1800
DEL user:456
```

**Recovery**: Replay log on startup

**Compaction**: Periodically compact log (remove deletes, merge updates)

#### Snapshot (RDB)
Periodically save entire memory state to disk:
```
Every 5 minutes: Save snapshot
On startup: Load latest snapshot + replay AOF since snapshot
```

**Trade-off**:
- AOF: Durable but slower writes
- RDB: Faster but may lose recent data
- **Hybrid**: Use both (RDB for bulk, AOF for recent changes)

---

## Handling Failures

### 1. Node Failure
**Detection**: Heartbeat every 1 second
**Action**: Mark node as down, route requests to replicas
**Recovery**: Promote replica to master (via Zookeeper/etcd election)

### 2. Network Partition (Split Brain)
**Problem**: Two masters think they're the leader

**Solution**: Quorum-based consensus (Raft/Paxos)
- Requires majority of nodes to agree
- If < 50% nodes, become read-only

### 3. Cascading Failures
**Problem**: One slow node causes timeout → Clients retry → Overload other nodes

**Solution**:
- **Circuit breaker**: Stop sending requests to slow node
- **Request timeout**: Fail fast (e.g., 5ms timeout)
- **Rate limiting**: Limit requests per client

---

## Optimization Techniques

### 1. Memory Optimization
**Problem**: 1TB data doesn't fit in RAM

**Solution**:
- **Compression**: Compress values (Snappy/LZ4)
  - Trade-off: CPU time vs memory
  - Typical: 3x compression ratio
- **Tiered storage**:
  - Hot data (frequently accessed): RAM
  - Cold data (rarely accessed): SSD
  - Use LFU (Least Frequently Used) to identify cold data

### 2. Thundering Herd Problem
**Problem**: Cache expires → 1000 requests hit database simultaneously

**Solution**: **Probabilistic early expiration**
```python
def get_with_early_expiration(key, ttl):
    value, expiry = cache.get(key)
    if value is None:
        return fetch_from_db(key)
    
    # Probabilistically refresh before expiry
    time_to_expiry = expiry - now()
    delta = random.uniform(0, ttl * 0.1)  # 10% jitter
    if time_to_expiry < delta:
        # Refresh in background
        async_refresh(key)
    
    return value
```

### 3. Hot Key Problem
**Problem**: One key (e.g., celebrity profile) gets 10K req/s → Bottleneck on single node

**Solution**:
- **Local caching**: Client-side cache for hot keys
- **Replication**: Replicate hot keys to multiple nodes
- **Detection**: Monitor key access frequency

---

## Monitoring & Observability

### Key Metrics

#### Performance Metrics
- **Latency**: p50, p95, p99, p999
- **Throughput**: Requests per second
- **Cache hit ratio**: Hits / (Hits + Misses)
  - Target: > 80%
- **Eviction rate**: LRU evictions per second

#### Resource Metrics
- **Memory usage**: Current / Max capacity
- **CPU usage**: % utilization
- **Network bandwidth**: MB/s in/out
- **Disk I/O**: For persistence

#### Availability Metrics
- **Uptime**: % availability
- **Error rate**: Failed requests / Total requests
- **Failover time**: Time to recover from node failure

### Dashboards (Grafana)
```
┌──────────────────────────────────────────────────┐
│  Cache Hit Ratio: 82% ↑                          │
│  [████████████████░░░░] (Target: 80%)            │
├──────────────────────────────────────────────────┤
│  Latency (p99): 0.8ms                            │
│  [Graph showing latency over time]               │
├──────────────────────────────────────────────────┤
│  Throughput: 120K req/s                          │
│  [Graph showing RPS over time]                   │
├──────────────────────────────────────────────────┤
│  Memory Usage: 24GB / 32GB (75%)                 │
│  [████████████████████████████░░░░░░░░░░]       │
└──────────────────────────────────────────────────┘
```

---

## API Design

### REST API (HTTP)
```http
GET    /cache/{key}              # Get value
PUT    /cache/{key}              # Set value
DELETE /cache/{key}              # Delete value
GET    /cache/stats              # Get stats
POST   /cache/flush              # Clear all
```

### Binary Protocol (Faster)
```
Request:
[Command (1 byte)][Key Length (2 bytes)][Key][Value Length (4 bytes)][Value][TTL (4 bytes)]

Response:
[Status (1 byte)][Value Length (4 bytes)][Value]

Commands:
0x01 = GET
0x02 = SET
0x03 = DELETE
0x04 = EXISTS
```

**Why binary?**
- Faster parsing (no JSON overhead)
- Smaller packet size
- Used by Redis, Memcached

---

## Comparison with Existing Systems

| Feature | This Design | Redis | Memcached |
|---------|-------------|-------|-----------|
| **Data Structure** | HashMap + LRU List | Multiple (List, Set, Hash) | HashMap only |
| **Persistence** | Optional (AOF+RDB) | Yes (AOF+RDB) | No |
| **Replication** | Master-Slave | Master-Slave + Sentinel | No (app-level) |
| **Clustering** | Consistent Hashing | Redis Cluster | Consistent Hashing |
| **Eviction** | LRU | LRU, LFU, TTL | LRU |
| **Multi-threading** | Yes | Single-threaded (I/O multi) | Multi-threaded |
| **Max Value Size** | 1MB (configurable) | 512MB | 1MB |

---

## Scalability Path

### Phase 1: Single Node (0-10K RPS)
- One cache instance
- Simple LRU implementation
- In-memory only

### Phase 2: Replicated (10K-100K RPS)
- Add 2 replicas
- Read from replicas, write to master
- Basic failover

### Phase 3: Partitioned (100K-1M RPS)
- Shard data across 10 nodes
- Consistent hashing for distribution
- 3 replicas per shard

### Phase 4: Multi-Datacenter (> 1M RPS)
- Deploy in multiple regions
- Cross-DC replication
- Read from local DC, write to all DCs

---

## Interview Discussion Points

### Q1: LRU vs LFU - Which is better?
**Answer**:
- **LRU** (Least Recently Used): Evict oldest access
  - Pro: Simple, works for time-sensitive data
  - Con: One-time access can evict frequent items
- **LFU** (Least Frequently Used): Evict least accessed
  - Pro: Keeps frequently accessed items
  - Con: New popular items take time to gain frequency
- **Best**: Hybrid (W-TinyLFU) - Combine both with window

### Q2: How do you handle cache stampede?
**Answer**:
- **Problem**: Cache expires → 1000 requests hit DB
- **Solution 1**: Lock - First request refreshes, others wait
- **Solution 2**: Stale-while-revalidate - Serve stale data while refreshing
- **Solution 3**: Probabilistic early expiration - Refresh before expiry

### Q3: Consistency vs Availability trade-off?
**Answer** (CAP Theorem):
- **Consistency**: All nodes see same data
- **Availability**: Every request gets response
- **Partition Tolerance**: Works despite network issues
- **Cache choice**: AP system (favor availability)
  - Eventual consistency is OK for cache
  - If master fails, read from slightly stale replica

### Q4: How do you ensure data integrity?
**Answer**:
- **Checksums**: Detect corruption (CRC32)
- **Write-ahead log**: Replay on crash
- **Replication**: Multiple copies
- **Backups**: Periodic snapshots to S3

### Q5: How would you implement distributed transactions?
**Answer**:
- **Two-phase commit** (2PC): Prepare → Commit
  - Slow, blocking
- **Saga pattern**: Chain of compensating transactions
- **Eventual consistency**: Accept stale reads
- **Cache best practice**: Don't use cache for transactions!

---

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **Language** | C++ / Rust / Go | Low-level memory control, performance |
| **Networking** | epoll/io_uring (Linux) | Async I/O, high concurrency |
| **Serialization** | Protocol Buffers / MessagePack | Fast, compact binary format |
| **Coordination** | Zookeeper / etcd | Distributed consensus, leader election |
| **Monitoring** | Prometheus + Grafana | Metrics & dashboards |
| **Load Testing** | Locust / JMeter | Simulate high load |

---

## Deployment

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: cache-cluster
spec:
  replicas: 10
  template:
    spec:
      containers:
      - name: cache-node
        image: our-cache:v1.0
        resources:
          requests:
            memory: "32Gi"
            cpu: "4"
          limits:
            memory: "32Gi"
            cpu: "4"
        env:
        - name: CACHE_SIZE
          value: "30GB"
        - name: REPLICATION_FACTOR
          value: "3"
```

---

## Cost Estimation (AWS)

| Component | Specification | Monthly Cost |
|-----------|--------------|--------------|
| **EC2** | 100 × r5.xlarge (32GB RAM, 4 vCPU) | $13,000 |
| **Network** | 1TB data transfer | $90 |
| **S3** | 100GB snapshots | $3 |
| **CloudWatch** | Monitoring | $100 |
| **Total** | | **~$13,200/month** |

**Optimization**:
- Use Reserved Instances: Save 40% → ~$8,000/month
- Use Graviton (ARM): Additional 20% savings → ~$6,500/month

---

## Real-World Examples

### 1. **Redis**
- In-memory data structure store
- Supports 30+ data types (String, List, Set, Hash, Sorted Set)
- Used by: Twitter, GitHub, StackOverflow

### 2. **Memcached**
- Simple key-value cache
- Multi-threaded (uses all CPU cores)
- Used by: Facebook, Wikipedia, YouTube

### 3. **Amazon ElastiCache**
- Managed Redis/Memcached
- Automatic failover, backups, scaling

---

**This HLD covers a production-grade distributed cache system!** 🚀
