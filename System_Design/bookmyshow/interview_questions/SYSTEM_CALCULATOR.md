# BookMyShow - System Design Calculator & Capacity Planning

## For 15+ Years Experienced Architect

---

## 📊 Part 1: Capacity Planning Calculator

### **Input Parameters**

```yaml
Business Metrics:
  Daily Active Users (DAU): 10,000,000
  Monthly Active Users (MAU): 50,000,000
  Peak Concurrent Users: 1,000,000
  Average Session Duration: 15 minutes
  
Booking Metrics:
  Conversion Rate: 5%              # 5% of users complete booking
  Daily Bookings: 500,000
  Peak Hour Bookings: 100,000
  Average Seats per Booking: 2.5
  
Traffic Distribution:
  Peak Hours: 6 PM - 11 PM (40% of daily traffic)
  Normal Hours: 9 AM - 6 PM (40% of daily traffic)
  Off-Peak: 11 PM - 9 AM (20% of daily traffic)
```

---

### **1. Request Rate Calculations**

```
TOTAL REQUESTS PER DAY
═══════════════════════════════════════════════════════════

User Actions per Session:
├─ Search movies: 3 requests
├─ View shows: 2 requests
├─ View seats: 1 request
├─ API calls for seat status updates: 10 requests (real-time)
├─ Complete booking: 4 requests (select → reserve → pay → confirm)
└─ Total: 20 requests per session (average)

Daily Request Rate:
├─ Total sessions: 10M DAU × 1.5 sessions/user = 15M sessions
├─ Total requests: 15M sessions × 20 requests = 300M requests/day
└─ Requests per second (average): 300M ÷ 86,400 = 3,472 req/sec

Peak Hour (6 PM - 11 PM):
├─ Peak traffic: 40% of daily = 120M requests in 5 hours
├─ Peak req/sec: 120M ÷ 18,000 = 6,667 req/sec
└─ Peak booking rate: 100k bookings ÷ 3600 = 27.8 bookings/sec

Movie Premiere (100x spike):
├─ Peak concurrent users: 1M (vs normal 10k)
├─ Peak req/sec: 6,667 × 100 = 666,700 req/sec
└─ Peak booking rate: 27.8 × 100 = 2,780 bookings/sec
```

---

### **2. Server Capacity Calculations**

```
APPLICATION SERVERS
═══════════════════════════════════════════════════════════

Server Specs (AWS c5.2xlarge):
├─ vCPUs: 8
├─ RAM: 16 GB
├─ Network: 10 Gbps
├─ Cost: $0.34/hour = $248/month
└─ Capacity: 200 req/sec (with proper optimization)

Normal Load Calculation:
├─ Required capacity: 6,667 req/sec (peak hour)
├─ Servers needed: 6,667 ÷ 200 = 33.3 servers
├─ Safety buffer: 1.5x = 50 servers
├─ Monthly cost: 50 × $248 = $12,400
└─ Annual cost: $148,800

Movie Premiere Load:
├─ Required capacity: 666,700 req/sec
├─ Servers needed: 666,700 ÷ 200 = 3,334 servers
├─ Safety buffer: 1.5x = 5,000 servers
├─ Duration: 30 minutes = 0.5 hours
├─ Cost per event: 5,000 × $0.34 × 0.5 = $850
└─ Annual cost (12 premieres): $10,200

Total Annual Server Cost:
├─ Base (always running): $148,800
├─ Peak events (12 per year): $10,200
└─ TOTAL: $159,000/year
```

---

### **3. Database Capacity Calculations**

```
POSTGRESQL (TRANSACTIONAL DATA)
═══════════════════════════════════════════════════════════

Write Operations (Bookings):
├─ Daily bookings: 500,000
├─ Write ops per booking: 5 (booking, booking_seat×2.5, payment, seat_availability)
├─ Total writes/day: 500k × 5 = 2.5M writes
├─ Writes/sec (average): 2.5M ÷ 86,400 = 28.9 writes/sec
└─ Writes/sec (peak): 28.9 × 10 = 289 writes/sec

Database Instance (db.r5.2xlarge):
├─ vCPUs: 8
├─ RAM: 64 GB
├─ Storage: 1 TB SSD
├─ IOPS: 10,000
├─ Cost: $730/month
└─ Capacity: 500 writes/sec

Sharding Strategy:
├─ Shard by: city_id
├─ Number of shards: 10 (top 10 cities handle 80% of bookings)
├─ Master instances: 10 × $730 = $7,300/month
├─ Read replicas: 3 per shard × 10 × $730 = $21,900/month
└─ TOTAL: $29,200/month = $350,400/year

Storage Calculation:
├─ Average booking size: 2 KB
├─ Daily storage: 500k bookings × 2 KB = 1 GB/day
├─ Annual storage: 365 GB/year
├─ 3-year retention: 1,095 GB ≈ 1.1 TB
├─ Storage cost: 1.1 TB × $0.12/GB = $132/month
└─ Backup storage: 1.1 TB × $0.05/GB = $55/month


MYSQL (CATALOG DATA)
═══════════════════════════════════════════════════════════

Read Operations:
├─ Movie searches: 15M sessions × 3 = 45M reads/day
├─ Show listings: 15M sessions × 2 = 30M reads/day
├─ Total reads/day: 75M reads
├─ Reads/sec (average): 75M ÷ 86,400 = 868 reads/sec
└─ Reads/sec (peak): 868 × 10 = 8,680 reads/sec

Database Instance (db.r5.xlarge):
├─ vCPUs: 4
├─ RAM: 32 GB
├─ Cost: $380/month
└─ Capacity: 2,000 reads/sec

Read Replica Strategy:
├─ Master: 1 × $380 = $380/month
├─ Read replicas: 5 × $380 = $1,900/month
└─ TOTAL: $2,280/month = $27,360/year


ELASTICSEARCH (SEARCH INDEX)
═══════════════════════════════════════════════════════════

Index Size:
├─ Movies: 10,000 × 10 KB = 100 MB
├─ Theaters: 5,000 × 5 KB = 25 MB
├─ Shows: 500,000 × 2 KB = 1 GB
├─ Total index size: 1.2 GB
└─ With replication (3x): 3.6 GB

Cluster Configuration:
├─ Node type: r5.large.elasticsearch
├─ vCPUs: 2
├─ RAM: 16 GB
├─ Storage: 100 GB
├─ Cost: $150/month per node
├─ Nodes: 3 (1 master, 2 data nodes)
└─ TOTAL: 3 × $150 = $450/month = $5,400/year

Query Rate:
├─ Search queries: 45M/day
├─ Queries/sec (average): 520 queries/sec
├─ Queries/sec (peak): 5,200 queries/sec
└─ Capacity per node: 2,000 queries/sec → 3 nodes sufficient
```

---

### **4. Cache (Redis) Capacity Calculations**

```
REDIS CLUSTER
═══════════════════════════════════════════════════════════

Cache Data:
├─ Seat availability per show: 500 seats × 50 bytes = 25 KB per show
├─ Active shows: 50,000 (next 7 days)
├─ Seat data: 50k × 25 KB = 1.25 GB
├─ Search results: 10k cached queries × 100 KB = 1 GB
├─ Session data: 1M sessions × 5 KB = 5 GB
├─ Miscellaneous: 2 GB
└─ TOTAL: 9.25 GB

Redis Node (cache.r5.large):
├─ vCPUs: 2
├─ RAM: 13.07 GB (usable: ~10 GB after overhead)
├─ Network: 10 Gbps
├─ Cost: $120/month
└─ Capacity: 100,000 ops/sec

Cluster Configuration:
├─ Primary nodes: 3 (sharded)
├─ Replica nodes: 3 (1 per primary)
├─ Total nodes: 6
├─ Total capacity: 600,000 ops/sec
├─ Total memory: 60 GB (sufficient for 9.25 GB + headroom)
└─ TOTAL: 6 × $120 = $720/month = $8,640/year

Cache Request Rate:
├─ Cache hit rate target: 90%
├─ Total requests: 300M/day
├─ Cache requests: 270M/day (90% hit)
├─ Cache ops/sec (average): 3,125 ops/sec
├─ Cache ops/sec (peak): 31,250 ops/sec
└─ Cluster capacity: 600k ops/sec ✅ Sufficient

Peak Load (Movie Premiere):
├─ Peak requests: 666,700 req/sec
├─ Cache requests: 600k req/sec (90% hit)
├─ Cluster capacity: 600k ops/sec ✅ Just sufficient
└─ Action: Pre-warm cache before premiere
```

---

### **5. Network & Bandwidth Calculations**

```
BANDWIDTH REQUIREMENTS
═══════════════════════════════════════════════════════════

Average Request/Response Sizes:
├─ Search API: Request 2 KB, Response 50 KB = 52 KB
├─ Seat map API: Request 1 KB, Response 100 KB = 101 KB
├─ Booking API: Request 5 KB, Response 10 KB = 15 KB
├─ Average: 50 KB per request/response

Daily Bandwidth:
├─ Total requests: 300M/day
├─ Bandwidth: 300M × 50 KB = 15 TB/day
├─ Monthly: 15 TB × 30 = 450 TB/month
└─ Cost (AWS data transfer): 450 TB × $0.09/GB = $40,500/month

CDN Offloading (CloudFlare):
├─ Static assets: 30% of traffic (movie posters, images)
├─ CDN savings: 450 TB × 30% = 135 TB/month
├─ Remaining: 315 TB/month
├─ AWS cost: 315 TB × $0.09/GB = $28,350/month
├─ CDN cost: 135 TB × $0.02/GB = $2,700/month
└─ TOTAL: $31,050/month (vs $40,500 without CDN)

Peak Bandwidth (Movie Premiere):
├─ Peak requests: 666,700 req/sec
├─ Bandwidth: 666,700 × 50 KB = 33.3 GB/sec = 266 Gbps
├─ Duration: 30 minutes
└─ Total data: 33.3 GB/sec × 1800 sec = 60 TB
```

---

### **6. Load Balancer Calculations**

```
APPLICATION LOAD BALANCER (AWS ALB)
═══════════════════════════════════════════════════════════

ALB Capacity:
├─ Max connections: 50,000 per ALB
├─ New connections/sec: 25,000 per ALB
├─ Request rate: Unlimited (distributed)
└─ Cost: $22.50/month + $0.008 per LCU-hour

Normal Load:
├─ Concurrent connections: 100,000
├─ ALBs needed: 100k ÷ 50k = 2 ALBs
├─ LCU usage: ~50 LCUs (based on request rate)
├─ LCU cost: 50 × $0.008 × 730 = $292/month
├─ Fixed cost: 2 × $22.50 = $45/month
└─ TOTAL: $337/month = $4,044/year

Peak Load (Movie Premiere):
├─ Concurrent connections: 1,000,000
├─ ALBs needed: 1M ÷ 50k = 20 ALBs
├─ Duration: 30 minutes = 0.5 hours
├─ LCU usage: 500 LCUs
├─ Cost: (20 × $22.50 ÷ 730 × 0.5) + (500 × $0.008 × 0.5)
└─ Cost per event: $0.31 + $2.00 = $2.31
```

---

### **7. Message Queue (Kafka/SQS) Calculations**

```
KAFKA CLUSTER (FOR EVENT STREAMING)
═══════════════════════════════════════════════════════════

Topics:
├─ booking.confirmed: 500k messages/day
├─ booking.cancelled: 50k messages/day
├─ payment.success: 500k messages/day
├─ seat.updated: 2M messages/day (4 updates per booking)
└─ TOTAL: 3.05M messages/day

Message Size:
├─ Average: 2 KB per message
└─ Daily volume: 3.05M × 2 KB = 6.1 GB/day

Kafka Broker (m5.large):
├─ vCPUs: 2
├─ RAM: 8 GB
├─ Storage: 500 GB EBS
├─ Cost: $100/month
└─ Capacity: 100 MB/sec throughput

Cluster Configuration:
├─ Brokers: 3 (replication factor 3)
├─ Retention: 7 days
├─ Storage needed: 6.1 GB × 7 = 42.7 GB per partition
├─ Partitions: 10 (by city_id)
├─ Total storage: 42.7 GB × 10 × 3 (replication) = 1.28 TB
└─ TOTAL: 3 × $100 = $300/month = $3,600/year


AMAZON SQS (FOR QUEUING)
═══════════════════════════════════════════════════════════

Queue Usage:
├─ Booking queue (peak load handling)
├─ Email notification queue
├─ SMS notification queue
└─ Analytics processing queue

Message Volume:
├─ Peak bookings: 450k messages (queued during premiere)
├─ Notifications: 1M messages/day (email + SMS)
├─ Total messages/month: 30M messages
├─ Cost: 30M × $0.40 per million = $12/month
└─ TOTAL: $144/year
```

---

### **8. Storage (S3) Calculations**

```
AMAZON S3
═══════════════════════════════════════════════════════════

Storage Breakdown:
├─ Movie posters: 10k movies × 500 KB = 5 GB
├─ Theater images: 5k theaters × 1 MB = 5 GB
├─ Booking tickets (PDF): 500k/day × 100 KB × 30 days = 1.5 TB/month
├─ Application logs: 100 GB/day × 30 days = 3 TB/month
├─ Database backups: 1.1 TB
└─ TOTAL: 4.6 TB/month

Cost Calculation:
├─ Standard storage: 4.6 TB × $0.023/GB = $106/month
├─ Infrequent Access (logs >90 days): 1 TB × $0.0125/GB = $12.50/month
├─ Glacier (backups >1 year): 500 GB × $0.004/GB = $2/month
└─ TOTAL: $120.50/month = $1,446/year

Data Transfer:
├─ CloudFront downloads: 135 TB/month (covered by CDN)
├─ S3 to EC2: Free (same region)
└─ No additional cost
```

---

## 💰 Part 2: Total Cost Breakdown

```
MONTHLY INFRASTRUCTURE COST SUMMARY
═══════════════════════════════════════════════════════════

Application Tier:
├─ Application servers: $12,400
├─ Load balancers: $337
└─ Subtotal: $12,737

Database Tier:
├─ PostgreSQL (sharded): $29,200
├─ MySQL (replicated): $2,280
├─ Elasticsearch: $450
└─ Subtotal: $31,930

Cache Tier:
├─ Redis cluster: $720
└─ Subtotal: $720

Message Queue:
├─ Kafka cluster: $300
├─ SQS: $12
└─ Subtotal: $312

Storage:
├─ S3: $120.50
├─ EBS (attached to servers): $500
└─ Subtotal: $620.50

Network:
├─ Data transfer: $28,350
├─ CDN (CloudFlare): $2,700
└─ Subtotal: $31,050

Monitoring & Logging:
├─ CloudWatch: $200
├─ DataDog: $500
└─ Subtotal: $700

═══════════════════════════════════════════════════════════
TOTAL MONTHLY COST: $78,069.50
TOTAL ANNUAL COST: $936,834
═══════════════════════════════════════════════════════════

Cost per DAU: $936,834 ÷ (10M × 365) = $0.000257 per user per day
Cost per Booking: $936,834 ÷ (500k × 365) = $0.00513 per booking
```

---

## 📈 Part 3: Scaling Calculator

### **Formula: Determine Servers Needed for Target QPS**

```python
def calculate_servers_needed(
    target_qps: int,
    requests_per_server: int = 200,
    safety_factor: float = 1.5
) -> dict:
    """
    Calculate number of servers needed for target QPS
    
    Args:
        target_qps: Target queries per second
        requests_per_server: Capacity of each server
        safety_factor: Safety buffer (1.5 = 50% buffer)
    
    Returns:
        Dictionary with server count and cost
    """
    
    # Calculate base servers needed
    base_servers = math.ceil(target_qps / requests_per_server)
    
    # Apply safety factor
    total_servers = math.ceil(base_servers * safety_factor)
    
    # Calculate cost (c5.2xlarge = $0.34/hour)
    hourly_cost = total_servers * 0.34
    monthly_cost = hourly_cost * 730  # hours per month
    annual_cost = monthly_cost * 12
    
    return {
        "target_qps": target_qps,
        "base_servers": base_servers,
        "total_servers": total_servers,
        "hourly_cost": hourly_cost,
        "monthly_cost": monthly_cost,
        "annual_cost": annual_cost,
        "cost_per_request": monthly_cost / (target_qps * 2_592_000)  # per request
    }

# Example usage
print(calculate_servers_needed(target_qps=10_000))
# Output:
# {
#   "target_qps": 10000,
#   "base_servers": 50,
#   "total_servers": 75,
#   "hourly_cost": 25.5,
#   "monthly_cost": 18615.0,
#   "annual_cost": 223380.0,
#   "cost_per_request": 0.00000072
# }
```

---

### **Formula: Database Shard Calculation**

```python
def calculate_shards_needed(
    daily_writes: int,
    writes_per_second_per_shard: int = 500,
    peak_multiplier: int = 10,
    safety_factor: float = 1.5
) -> dict:
    """
    Calculate number of database shards needed
    
    Args:
        daily_writes: Total writes per day
        writes_per_second_per_shard: Capacity of each shard
        peak_multiplier: Peak vs average multiplier
        safety_factor: Safety buffer
    
    Returns:
        Dictionary with shard count and cost
    """
    
    # Calculate average writes per second
    avg_writes_per_sec = daily_writes / 86400
    
    # Calculate peak writes per second
    peak_writes_per_sec = avg_writes_per_sec * peak_multiplier
    
    # Calculate shards needed
    base_shards = math.ceil(peak_writes_per_sec / writes_per_second_per_shard)
    total_shards = math.ceil(base_shards * safety_factor)
    
    # Calculate cost (db.r5.2xlarge = $730/month per shard)
    cost_per_shard = 730  # master only
    cost_with_replicas = cost_per_shard * 4  # 1 master + 3 replicas
    monthly_cost = total_shards * cost_with_replicas
    annual_cost = monthly_cost * 12
    
    return {
        "daily_writes": daily_writes,
        "avg_writes_per_sec": avg_writes_per_sec,
        "peak_writes_per_sec": peak_writes_per_sec,
        "total_shards": total_shards,
        "monthly_cost": monthly_cost,
        "annual_cost": annual_cost
    }

# Example usage
print(calculate_shards_needed(daily_writes=500_000))
# Output:
# {
#   "daily_writes": 500000,
#   "avg_writes_per_sec": 5.79,
#   "peak_writes_per_sec": 57.9,
#   "total_shards": 1,
#   "monthly_cost": 2920,
#   "annual_cost": 35040
# }
```

---

### **Formula: Cache Size Calculation**

```python
def calculate_cache_size(
    cache_entries: dict,
    eviction_policy: str = "LRU",
    ttl_seconds: int = 300,
    safety_factor: float = 1.5
) -> dict:
    """
    Calculate Redis cache size needed
    
    Args:
        cache_entries: Dict of {entry_type: (count, size_bytes)}
        eviction_policy: Cache eviction policy
        ttl_seconds: Time to live for entries
        safety_factor: Memory overhead factor
    
    Returns:
        Dictionary with cache size and cost
    """
    
    # Calculate total size
    total_size_bytes = 0
    breakdown = {}
    
    for entry_type, (count, size_bytes) in cache_entries.items():
        entry_total = count * size_bytes
        total_size_bytes += entry_total
        breakdown[entry_type] = {
            "count": count,
            "size_per_entry": size_bytes,
            "total_size": entry_total
        }
    
    # Apply safety factor for overhead
    total_size_with_overhead = total_size_bytes * safety_factor
    total_size_gb = total_size_with_overhead / (1024 ** 3)
    
    # Calculate nodes needed (cache.r5.large = 13 GB usable)
    usable_per_node = 10  # GB (after Redis overhead)
    nodes_needed = math.ceil(total_size_gb / usable_per_node)
    
    # With replication (1 replica per primary)
    total_nodes = nodes_needed * 2
    
    # Calculate cost (cache.r5.large = $120/month)
    monthly_cost = total_nodes * 120
    annual_cost = monthly_cost * 12
    
    return {
        "total_size_bytes": total_size_bytes,
        "total_size_gb": total_size_gb,
        "nodes_needed": nodes_needed,
        "total_nodes": total_nodes,
        "monthly_cost": monthly_cost,
        "annual_cost": annual_cost,
        "breakdown": breakdown
    }

# Example usage
cache_data = {
    "seat_availability": (50_000, 25_000),  # 50k shows × 25KB
    "search_results": (10_000, 100_000),    # 10k queries × 100KB
    "session_data": (1_000_000, 5_000),     # 1M sessions × 5KB
    "movie_details": (10_000, 50_000)       # 10k movies × 50KB
}

print(calculate_cache_size(cache_data))
# Output will show total nodes needed and cost
```

---

## 🎯 Part 4: Interview Cheat Sheet

### **Quick Estimation Formula**

```
BACK-OF-THE-ENVELOPE CALCULATION
═══════════════════════════════════════════════════════════

Given:
- DAU: 10M users
- Sessions per user: 1.5
- Requests per session: 20

Calculate:
1. Total daily requests = 10M × 1.5 × 20 = 300M requests/day
2. Average QPS = 300M ÷ 86,400 = 3,472 QPS
3. Peak QPS = 3,472 × 10 (peak multiplier) = 34,720 QPS
4. Servers needed = 34,720 ÷ 200 (per server) × 1.5 (safety) = 260 servers
5. Monthly cost = 260 × $248 = $64,480

Quick Checks:
✓ Does it fit in memory? (9 GB cache vs 10 GB Redis node) ✅
✓ Can database handle writes? (289 writes/sec vs 500 capacity) ✅
✓ Network bandwidth sufficient? (266 Gbps peak vs 10 Gbps per server × 260) ✅
```

---

## 💡 Interview Tips

**When interviewer asks "How many servers?":**

1. **Clarify requirements** (DAU, QPS, latency targets)
2. **Calculate QPS** (average and peak)
3. **Estimate server capacity** (200 req/sec is reasonable)
4. **Add safety buffer** (1.5x to 2x)
5. **Consider cost** (show you think about business)

**Red Flags to Avoid:**
❌ "I'll just add more servers" (without calculations)
❌ Ignoring peak vs average load
❌ Not mentioning cost
❌ Forgetting database is often the bottleneck

**What impresses interviewers:**
✅ Quick mental math
✅ Considering trade-offs
✅ Knowing real-world metrics
✅ Thinking about cost optimization

This demonstrates architect-level capacity planning! 🎯
