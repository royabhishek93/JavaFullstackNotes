# High-Level Design (HLD) Interview Cheatsheet

## Quick Navigation
[HLD vs LLD](#hld-vs-lld) | [CAP Theorem](#cap-theorem) | [Scalability](#scalability-patterns) | [Databases](#database-scaling) | [Caching](#caching-strategies) | [Load Balancing](#load-balancing) | [Interview Framework](#interview-framework)

---

## HLD vs LLD

| Aspect | High-Level Design (HLD) | Low-Level Design (LLD) |
|--------|------------------------|------------------------|
| **Focus** | System architecture, components interaction | Class design, algorithms, data structures |
| **Scope** | Entire system (distributed) | Single component/module |
| **Concerns** | Scalability, availability, consistency | Code quality, design patterns, SOLID |
| **Tools** | Architecture diagrams, data flow | UML diagrams, sequence diagrams |
| **Questions** | "Design WhatsApp" | "Design parking lot classes" |
| **Skills Tested** | Distributed systems, trade-offs | OOP, algorithms, coding |
| **Example** | How to handle 1B users? | How to implement LRU cache? |

**Interview Tip**: Start HLD with requirements → capacity → architecture → deep dive → bottlenecks

---

## CAP Theorem

**Theorem**: In a distributed system, you can have at most 2 out of 3:

```
          Consistency
               /\
              /  \
             /    \
            /  CP  \
           /________\
          /    |     \
         / CA  |  AP  \
        /______|_______\
   Availability    Partition Tolerance
```

### The 3 Properties

| Property | Meaning | Example |
|----------|---------|---------|
| **Consistency** | All nodes see same data at same time | Bank balance must be consistent |
| **Availability** | Every request gets a response (success/failure) | System always responds |
| **Partition Tolerance** | System works despite network failures | Nodes can't talk, system still works |

### Real-World Choices

| System | Choice | Why |
|--------|--------|-----|
| **Traditional RDBMS** | CA | Sacrifice partition tolerance (single datacenter) |
| **MongoDB, HBase** | CP | Consistency over availability (strong reads) |
| **Cassandra, DynamoDB** | AP | Availability over consistency (eventual consistency) |
| **Redis** | CP/AP | Configurable (tunable consistency) |

**Reality Check**: Network partitions WILL happen, so really choosing between **CP vs AP**

### Trade-off Decision Tree
```
Need strong consistency (banking, booking)?
  ├─ YES → CP system (PostgreSQL, MongoDB)
  └─ NO  → AP system (Cassandra, DynamoDB)

Can tolerate stale reads?
  ├─ YES → AP (social media feeds, analytics)
  └─ NO  → CP (inventory, reservations)
```

---

## Scalability Patterns

### 1. Vertical Scaling (Scale Up)
**What**: Add more resources to existing machine (CPU, RAM, SSD)

**Pros**: Simple, no code changes
**Cons**: Hardware limits, expensive, single point of failure

**When to use**: Quick fix, predictable load, < 10K users

### 2. Horizontal Scaling (Scale Out)
**What**: Add more machines

**Pros**: No limits, cost-effective, fault-tolerant
**Cons**: Complex (distributed system challenges)

**When to use**: High scale (> 100K users), unpredictable traffic

### Comparison
```
Vertical:   [Small Server] → [BIG SERVER]
Horizontal: [Server 1] → [Server 1][Server 2][Server 3]...[Server N]
```

---

## Load Balancing

### Algorithms

| Algorithm | How It Works | Best For |
|-----------|-------------|----------|
| **Round Robin** | Distribute requests in circular order | Equal capacity servers |
| **Weighted Round Robin** | More requests to powerful servers | Different capacity servers |
| **Least Connections** | Send to server with fewest active connections | Long-lived connections |
| **Least Response Time** | Send to fastest responding server | Variable latency servers |
| **IP Hash** | Hash client IP → same server always | Session persistence needed |
| **Random** | Pick random server | Stateless, equal servers |

### Load Balancer Tiers

```
Internet → L4 (Network Layer) → L7 (Application Layer) → Servers

L4 (TCP/UDP):
  - Fast (no content inspection)
  - Routes based on IP, port
  - Example: AWS NLB

L7 (HTTP/HTTPS):
  - Slower (inspects content)
  - Routes based on URL, headers, cookies
  - Can terminate SSL
  - Example: AWS ALB, Nginx
```

### Health Checks
```python
Every 30 seconds:
  if server.respond_to_ping():
      mark_healthy()
  else:
      mark_unhealthy()  # Stop sending traffic
```

---

## Database Scaling

### 1. Read Replicas (Master-Slave)
```
        MASTER (Writes)
           |
     (Replication)
           |
    ┌──────┼──────┐
    ▼      ▼      ▼
 REPLICA REPLICA REPLICA
 (Reads) (Reads) (Reads)
```

**Pros**: Scale reads, fault tolerance
**Cons**: Replication lag, eventual consistency

**Use case**: Read-heavy workloads (90% reads, 10% writes)

### 2. Master-Master (Multi-Master)
```
 MASTER 1 ◀──── Bi-directional ────▶ MASTER 2
(Read/Write)    Replication       (Read/Write)
```

**Pros**: No single point of failure, low write latency
**Cons**: Conflict resolution needed, complex

**Use case**: Multi-region, high availability

### 3. Database Sharding (Horizontal Partitioning)
```
Users 1-1M   → Shard 1 (DB Server 1)
Users 1M-2M  → Shard 2 (DB Server 2)
Users 2M-3M  → Shard 3 (DB Server 3)
```

**Sharding Strategies**:

| Strategy | How | Pros | Cons |
|----------|-----|------|------|
| **Hash-based** | `hash(user_id) % num_shards` | Even distribution | Hard to add shards |
| **Range-based** | Users 1-1M, 1M-2M, etc. | Easy to add shards | Hotspots possible |
| **Geography** | US users → US DB, EU → EU DB | Low latency | Uneven distribution |
| **Entity-based** | All user data in one shard | No joins needed | Uneven distribution |

**Challenges**:
- Cross-shard queries are slow
- Transactions across shards are hard
- Resharding is expensive

### 4. Denormalization
**What**: Duplicate data to avoid joins

**Example**:
```sql
-- Normalized (requires join)
Orders: [order_id, user_id]
Users: [user_id, name, email]

-- Denormalized (no join needed)
Orders: [order_id, user_id, user_name, user_email]
```

**Trade-off**: Faster reads, slower writes, more storage

---

## Caching Strategies

### Cache-Aside (Lazy Loading)
```python
def get_user(user_id):
    # 1. Check cache
    user = cache.get(f"user:{user_id}")
    if user:
        return user  # Cache hit
    
    # 2. Cache miss → Query DB
    user = db.get_user(user_id)
    
    # 3. Update cache
    cache.set(f"user:{user_id}", user, ttl=3600)
    return user
```

**Pros**: Only cache what's needed
**Cons**: Cache miss penalty, stale data possible

### Write-Through
```python
def update_user(user):
    # 1. Write to DB
    db.update_user(user)
    
    # 2. Update cache
    cache.set(f"user:{user.id}", user)
```

**Pros**: Cache is always fresh
**Cons**: Write penalty, unused data in cache

### Write-Back (Write-Behind)
```python
def update_user(user):
    # 1. Update cache only
    cache.set(f"user:{user.id}", user)
    
    # 2. Async write to DB (later)
    queue.add_job(lambda: db.update_user(user))
```

**Pros**: Fastest writes
**Cons**: Risk of data loss if cache fails

### Comparison

| Strategy | Read | Write | Consistency | Use Case |
|----------|------|-------|-------------|----------|
| **Cache-Aside** | Fast after first | Normal | Eventual | General purpose |
| **Write-Through** | Fast | Slow | Strong | Read-heavy |
| **Write-Back** | Fast | Very fast | Eventual | Write-heavy |
| **Read-Through** | Fast | Normal | Eventual | Read-heavy |

---

## Message Queues & Event Streaming

### When to Use?

| Pattern | Use Case |
|---------|----------|
| **Request/Response** | Immediate result needed (REST API) |
| **Async Processing** | Background jobs (email, resize image) |
| **Event-Driven** | Multiple services need same event (order placed) |
| **Load Leveling** | Smooth traffic spikes (Black Friday) |

### Technology Comparison

| Feature | Kafka | RabbitMQ | AWS SQS |
|---------|-------|----------|---------|
| **Type** | Event streaming | Message broker | Managed queue |
| **Throughput** | Very high (1M+ msg/s) | Medium (10K msg/s) | High |
| **Ordering** | Per partition | Per queue | FIFO queues only |
| **Retention** | Days/weeks | Ack-based | Up to 14 days |
| **Use Case** | Event sourcing, logs | Task queues | AWS-native apps |
| **Complexity** | High | Medium | Low |

### Kafka Architecture
```
Producers → Kafka Cluster → Consumers
              (Topics)
         ┌─────┴─────┐
      Partition 0  Partition 1  Partition 2
      [m1][m2][m3] [m4][m5][m6] [m7][m8][m9]
           ▲            ▲            ▲
      Consumer 1   Consumer 2   Consumer 3
    (Consumer Group)
```

**Key Concepts**:
- **Topic**: Category of messages (e.g., "user-signups")
- **Partition**: Parallel processing unit
- **Consumer Group**: Multiple consumers share work

---

## API Design

### REST vs GraphQL vs gRPC

| Aspect | REST | GraphQL | gRPC |
|--------|------|---------|------|
| **Protocol** | HTTP | HTTP | HTTP/2 |
| **Data Format** | JSON | JSON | Protobuf (binary) |
| **Performance** | Medium | Medium | Very fast |
| **Flexibility** | Fixed endpoints | Flexible queries | Fixed schema |
| **Over-fetching** | Yes | No | No |
| **Use Case** | Public APIs | Mobile apps | Microservices |
| **Learning Curve** | Easy | Medium | Medium |

### When to Use Which?

```
Public-facing API (web/mobile)?
  └─ Complex nested data?
      ├─ YES → GraphQL (single endpoint, client-driven)
      └─ NO  → REST (simple, standard)

Internal microservices (high throughput)?
  └─ gRPC (fast, binary, strong typing)

Real-time updates (live data)?
  └─ WebSockets or Server-Sent Events (SSE)
```

---

## Consistency Models

### Strong Consistency
**Guarantee**: Read always returns most recent write

**Example**: Bank transfer (balance must be exact)

**Implementation**: 
- Read from master only
- Wait for all replicas to acknowledge write

**Trade-off**: Higher latency, lower availability

### Eventual Consistency
**Guarantee**: All replicas will converge eventually (seconds/minutes)

**Example**: Social media likes (OK if count is slightly off)

**Implementation**: 
- Write to master, async replicate
- Read from any replica

**Trade-off**: Lower latency, higher availability, stale reads possible

### Causal Consistency
**Guarantee**: Related events are seen in order

**Example**: Reply always appears after original post

**Trade-off**: Between strong and eventual

---

## Distributed Transactions

### Problem: Transfer $100 from Account A to Account B
```
Service 1 (Account A): Debit $100
Service 2 (Account B): Credit $100

What if Service 1 succeeds but Service 2 fails?
```

### Solution 1: Two-Phase Commit (2PC)
```
Phase 1 - Prepare:
  Coordinator: "Can you commit?"
  Service 1: "Yes, ready"
  Service 2: "Yes, ready"

Phase 2 - Commit:
  Coordinator: "Commit now!"
  Service 1: Commits
  Service 2: Commits
```

**Pros**: Strong consistency
**Cons**: Blocking (coordinator down = everyone blocked), slow

### Solution 2: Saga Pattern
```
Transaction = Sequence of local transactions + Compensations

Success path:
  1. Debit A ($100)
  2. Credit B ($100)
  3. Done

Failure path (compensation):
  1. Debit A ($100) ✓
  2. Credit B ($100) ✗ (fails)
  3. Compensate: Credit A ($100) (rollback)
```

**Pros**: No locking, scalable
**Cons**: Eventual consistency, complex rollback logic

**When to use**:
- 2PC: Small scale, strong consistency needed
- Saga: Large scale, eventual consistency acceptable

---

## Rate Limiting

### Why?
- Prevent abuse (DDoS)
- Fair resource allocation
- Cost control (API calls)

### Algorithms

#### 1. Token Bucket
```
Bucket capacity: 10 tokens
Refill rate: 1 token/second

Request arrives:
  if bucket.tokens > 0:
      bucket.tokens -= 1
      allow_request()
  else:
      reject_request()
```

**Pros**: Allows bursts
**Cons**: Can drain quickly

#### 2. Leaky Bucket
```
Process requests at fixed rate (1 req/sec)

Requests queue up:
  if queue.size < max:
      queue.add(request)
  else:
      reject_request()
```

**Pros**: Smooth traffic
**Cons**: No bursts allowed

#### 3. Fixed Window
```
Window: 1 minute
Limit: 100 requests

if count_requests_in_current_minute() < 100:
    allow()
else:
    reject()
```

**Pros**: Simple
**Cons**: Burst at window boundary (99 at 0:59, 101 at 1:00)

#### 4. Sliding Window Log
```
Store timestamp of each request
Remove requests older than 1 minute
if len(timestamps) < 100:
    allow()
```

**Pros**: Accurate, no boundary issues
**Cons**: Memory-intensive

### Comparison

| Algorithm | Memory | Accuracy | Burst | Complexity |
|-----------|--------|----------|-------|------------|
| Token Bucket | O(1) | Good | Yes | Medium |
| Leaky Bucket | O(n) | Good | No | Medium |
| Fixed Window | O(1) | Poor | Yes | Low |
| Sliding Window | O(n) | Excellent | Limited | High |

---

## Back-of-Envelope Calculations

### Powers of 2
```
2^10 = 1 KB   = 1,024 bytes
2^20 = 1 MB   = 1,048,576 bytes
2^30 = 1 GB   = ~1 billion bytes
2^40 = 1 TB   = ~1 trillion bytes
```

### Time Approximations
```
1 second  = 1,000 milliseconds
1 minute  = 60 seconds
1 hour    = 3,600 seconds
1 day     = 86,400 seconds
1 month   = 2.5M seconds (approx)
1 year    = 31.5M seconds (approx)
```

### Latency Numbers
```
L1 cache reference:           0.5 ns
Branch mispredict:            5 ns
L2 cache reference:           7 ns
Mutex lock/unlock:           25 ns
Main memory reference:      100 ns
Send 2K bytes over 1 Gbps:  20,000 ns = 20 μs
SSD random read:           150,000 ns = 150 μs
Read 1 MB sequentially:  250,000 ns = 250 μs
Round trip within datacenter: 500,000 ns = 500 μs
Disk seek:              10,000,000 ns = 10 ms
```

### Capacity Estimation Example: Twitter

**Given**:
- 200M DAU (Daily Active Users)
- Each user posts 2 tweets/day
- Each user reads 100 tweets/day

**Calculate**:

**Writes**:
- Posts/day: 200M × 2 = 400M tweets/day
- Posts/second: 400M / 86,400 = ~4,600 tweets/s
- Peak (3x): ~14,000 tweets/s

**Reads**:
- Reads/day: 200M × 100 = 20B tweets/day
- Reads/second: 20B / 86,400 = ~231,000 tweets/s

**Storage** (1 year):
- Size per tweet: 200 bytes (text + metadata)
- Daily storage: 400M × 200B = 80GB/day
- Yearly storage: 80GB × 365 = 29TB/year

**Bandwidth**:
- Write: 4,600 tweets/s × 200B = 920 KB/s = 7 Mbps
- Read: 231,000 tweets/s × 200B = 46 MB/s = 370 Mbps

---

## Monitoring & Observability

### Golden Signals (Google SRE)

1. **Latency**: How long requests take
   - p50, p95, p99 (percentiles)
   - Target: API < 200ms

2. **Traffic**: How many requests
   - Requests per second (RPS)
   - Queries per second (QPS)

3. **Errors**: Rate of failed requests
   - HTTP 5xx errors
   - Target: < 0.1% error rate

4. **Saturation**: How full is the system
   - CPU, Memory, Disk, Network
   - Target: < 70% utilization

### The 3 Pillars

```
┌─────────────────────────────────────────┐
│          Observability                  │
├─────────────┬────────────┬──────────────┤
│   Metrics   │   Logs     │   Traces     │
│ (Prometheus)│   (ELK)    │  (Jaeger)    │
└─────────────┴────────────┴──────────────┘
```

**Metrics**: Numbers over time (CPU %, request count)
**Logs**: Individual events (error messages)
**Traces**: Request flow across services

---

## Common Architecture Patterns

### 1. Microservices
```
Monolith:     [────────────]
Microservices: [Service A][Service B][Service C]

Pros: Independent deploy, scale independently
Cons: Complex (networking, monitoring)
```

### 2. Event-Driven
```
Service A → Event Bus (Kafka) → Service B, C, D
                                (all consume event)

Pros: Decoupled, scalable
Cons: Eventual consistency, hard to debug
```

### 3. CQRS (Command Query Responsibility Segregation)
```
Writes → Write Model (normalized DB)
              ↓ (event)
         Event Store
              ↓ (project)
Reads  ← Read Model (denormalized, fast queries)

Pros: Optimize read & write separately
Cons: Eventual consistency, complex
```

### 4. Circuit Breaker
```
State Machine:
  CLOSED → (failures) → OPEN → (timeout) → HALF_OPEN
    ↑                                           ↓
    └────────────── (success) ─────────────────┘

CLOSED: Normal operation
OPEN: Stop calling failing service
HALF_OPEN: Try one request to test
```

---

## SQL vs NoSQL

| Factor | SQL (PostgreSQL, MySQL) | NoSQL (MongoDB, Cassandra) |
|--------|------------------------|----------------------------|
| **Schema** | Fixed (predefined) | Flexible (schema-less) |
| **Scaling** | Vertical (harder to shard) | Horizontal (easy) |
| **Transactions** | ACID (strong) | BASE (eventual) |
| **Joins** | Yes (fast) | No (app-level) |
| **Use Case** | Financial, relational data | High write, flexible data |
| **Consistency** | Strong | Eventual (tunable) |

### Decision Tree
```
Need ACID transactions (banking, booking)?
  ├─ YES → SQL
  └─ NO  → Continue

Need complex queries with JOINs?
  ├─ YES → SQL
  └─ NO  → Continue

Need to scale writes massively (millions/sec)?
  ├─ YES → NoSQL (Cassandra, DynamoDB)
  └─ NO  → SQL is fine

Schema changes frequently?
  ├─ YES → NoSQL (MongoDB)
  └─ NO  → SQL
```

---

## Interview Framework (Step-by-Step)

### Step 1: Requirements (5 min)

**Functional**: What should the system do?
- Users can post tweets
- Users can follow others
- Users can see timeline

**Non-Functional**: How should it perform?
- 200M DAU
- 99.9% availability
- < 200ms latency

**Ask Clarifying Questions**:
- Read-heavy or write-heavy?
- Consistency requirements?
- Geographic distribution?

### Step 2: Capacity Estimation (5 min)

- QPS (queries per second)
- Storage needed
- Bandwidth needed

**Show your work!** Interviewers love seeing calculations.

### Step 3: High-Level Design (10 min)

Draw boxes and arrows:
```
[Client] → [Load Balancer] → [Web Servers] → [Database]
                                 ↓
                             [Cache]
```

Identify components:
- API Gateway
- Services (User, Tweet, Timeline)
- Databases (SQL, NoSQL)
- Cache (Redis)
- Message Queue (Kafka)

### Step 4: Deep Dive (15 min)

Interviewer will pick 1-2 areas to explore:
- "How do you generate timeline?"
- "How do you handle hot users (celebrities)?"

**Be ready to**:
- Draw detailed diagrams
- Discuss trade-offs
- Explain algorithms

### Step 5: Bottlenecks & Improvements (5 min)

- Single point of failure?
- What if database is slow?
- How to scale to 10x users?

**Proactively identify issues** and propose solutions.

---

## Top 20 HLD Interview Questions

1. **Design URL Shortener** (bit.ly)
2. **Design Twitter** (timeline, tweet, follow)
3. **Design WhatsApp/Messenger** (chat, read receipts)
4. **Design Instagram** (photo upload, feed, likes)
5. **Design YouTube** (video upload, streaming)
6. **Design Uber/Lyft** (matching, location tracking)
7. **Design Netflix** (streaming, recommendations)
8. **Design Amazon** (product catalog, cart, checkout)
9. **Design Google Docs** (collaborative editing)
10. **Design Dropbox** (file sync, sharing)
11. **Design Rate Limiter** (throttle requests)
12. **Design Web Crawler** (scrape websites)
13. **Design Notification Service** (push, email, SMS)
14. **Design News Feed** (Facebook, LinkedIn)
15. **Design Search Autocomplete** (Google suggest)
16. **Design Ticketmaster** (seat booking, concurrency)
17. **Design Zoom** (video calls, screen share)
18. **Design Airbnb** (search, booking, reviews)
19. **Design Slack** (channels, DMs, search)
20. **Design Distributed Cache** (Redis, Memcached)

---

## Technology Cheat Sheet

| Need | Technology | Why |
|------|-----------|-----|
| **Relational DB** | PostgreSQL, MySQL | Transactions, joins, structure |
| **NoSQL DB** | MongoDB, Cassandra, DynamoDB | Scale writes, flexible schema |
| **In-Memory Cache** | Redis, Memcached | Sub-ms latency |
| **Message Queue** | Kafka, RabbitMQ, SQS | Async processing, decouple |
| **Search Engine** | Elasticsearch, Solr | Full-text search |
| **CDN** | CloudFront, Akamai | Serve static content globally |
| **Load Balancer** | AWS ALB/NLB, Nginx | Distribute traffic |
| **Object Storage** | S3, GCS | Store images, videos |
| **Monitoring** | Prometheus, Grafana | Metrics, alerts |
| **Logging** | ELK Stack, Splunk | Centralized logs |
| **API Gateway** | Kong, AWS API Gateway | Auth, rate limit, routing |

---

## Final Tips for HLD Interviews

1. **Start with Requirements**: Clarify before designing
2. **Do Math**: Capacity estimation impresses
3. **Draw Diagrams**: Visual > Words
4. **Think Out Loud**: Show your thought process
5. **Discuss Trade-offs**: There's no perfect solution
6. **Scale Gradually**: Start simple, then scale
7. **Identify Bottlenecks**: Proactively find issues
8. **Know the Basics**: CAP, consistency, caching, sharding
9. **Use Real Tech**: Mention Kafka, Redis, PostgreSQL
10. **Practice**: Do 10-20 mock interviews

---

Good luck with your HLD interviews! 🚀
