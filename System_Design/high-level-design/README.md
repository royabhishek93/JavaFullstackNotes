# High-Level Design (HLD) - System Architecture & Scalability

## 🎯 What is This Folder?

This folder contains **High-Level Design (HLD)** documents for 33+ distributed systems - the architectural counterpart to your Low-Level Design (LLD) problems.

**LLD** = Classes, design patterns, algorithms (single machine)  
**HLD** = Distributed systems, scalability, infrastructure (multiple machines)

---

## 🚀 Quick Start

1. **📖 START HERE**: Read [`HLD_INTERVIEW_CHEATSHEET.md`](HLD_INTERVIEW_CHEATSHEET.md)
2. **🔥 Study Top Systems**: Parking Lot, Distributed Cache, URL Shortener, Twitter, WhatsApp
3. **💡 Learn Concepts**: CAP Theorem, Caching, Load Balancing, Database Sharding
4. **🎯 Practice**: Use the interview framework to tackle new problems

---

## 📚 Available HLD Documents

### ⭐ Fully Detailed (Production-Ready Architecture)

1. **Parking Lot System** ([parking-lot-system-hld.md](parking-lot-system-hld.md))
   - Multi-location parking management
   - Real-time availability tracking
   - Payment processing, mobile apps
   - 100K+ transactions/day architecture

2. **Distributed Cache System** ([distributed-cache-system-hld.md](distributed-cache-system-hld.md))
   - Redis/Memcached-like system
   - LRU eviction at scale
   - 1M+ requests/second
   - Consistent hashing, replication

### 🎓 Interview Essentials

**Status**: Documents for these systems will be created based on your interview prep priorities.

#### Top Priority (Practice First)
- [ ] URL Shortener (bit.ly)
- [ ] Twitter/Social Network
- [ ] WhatsApp/Messenger
- [ ] Instagram/Photo Sharing
- [ ] YouTube/Video Streaming

#### High Demand
- [ ] Uber/Ride Sharing
- [ ] Netflix/Streaming
- [ ] Amazon E-commerce
- [ ] Google Docs/Collaborative Editing
- [ ] Dropbox/File Storage

#### System Components
- [ ] Rate Limiter
- [ ] Web Crawler
- [ ] Notification Service
- [ ] News Feed
- [ ] Search Autocomplete

#### Booking & Reservation
- [ ] Ticketmaster/Movie Booking
- [ ] Hotel Management
- [ ] Airline Reservation
- [ ] Restaurant Booking

#### Real-Time Systems
- [ ] Zoom/Video Conferencing
- [ ] Slack/Chat Application
- [ ] Stock Trading Platform
- [ ] Live Sports Updates

#### Others
- [ ] Airbnb
- [ ] LinkedIn
- [ ] Stack Overflow
- [ ] Food Delivery (Uber Eats)
- [ ] E-wallet (PayPal)

---

## 🎨 HLD vs LLD Comparison

| Aspect | Low-Level Design (LLD) | High-Level Design (HLD) |
|--------|------------------------|-------------------------|
| **Scope** | Single application/module | Entire distributed system |
| **Focus** | Classes, methods, algorithms | Services, databases, infrastructure |
| **Scale** | 1 machine | Multiple machines/datacenters |
| **Example Question** | "Design a parking lot class" | "Design a parking system for 100 locations" |
| **Tools** | UML diagrams, class diagrams | Architecture diagrams, data flow |
| **Key Topics** | OOP, SOLID, design patterns | Scalability, CAP theorem, sharding |
| **Interview Time** | 30-45 minutes | 45-60 minutes |

**Example**:
- **LLD**: How to implement an LRU cache with HashMap + Doubly Linked List
- **HLD**: How to build a distributed cache serving 1M requests/second across 100 nodes

---

## 🧠 Core HLD Concepts to Master

### 1. Scalability
- Horizontal vs Vertical Scaling
- Load Balancing (Round Robin, Least Connections, etc.)
- Database Sharding & Replication
- CDN for static content

### 2. Consistency & Availability
- CAP Theorem (Choose 2: Consistency, Availability, Partition Tolerance)
- Strong vs Eventual Consistency
- ACID vs BASE properties

### 3. Caching
- Cache-Aside, Write-Through, Write-Back
- Cache Eviction (LRU, LFU, TTL)
- Distributed Caching (Redis Cluster)

### 4. Database Scaling
- Read Replicas (Master-Slave)
- Sharding Strategies (Hash, Range, Geography)
- SQL vs NoSQL trade-offs

### 5. Message Queues
- Kafka, RabbitMQ, SQS
- Event-Driven Architecture
- Pub/Sub Pattern

### 6. System Design Patterns
- Microservices vs Monolith
- Event Sourcing & CQRS
- Circuit Breaker
- Saga Pattern (Distributed Transactions)

### 7. API Design
- REST vs GraphQL vs gRPC
- Versioning strategies
- Rate Limiting

---

## 📖 Interview Preparation Path

### Week 1: Fundamentals
- [ ] Read HLD_INTERVIEW_CHEATSHEET.md completely
- [ ] Understand CAP Theorem with examples
- [ ] Learn caching strategies
- [ ] Study load balancing algorithms
- [ ] Master database scaling techniques

### Week 2: Practice Core Systems
- [ ] URL Shortener (simple, great for learning)
- [ ] Twitter (classic, covers many concepts)
- [ ] Distributed Cache (technical depth)
- [ ] Rate Limiter (algorithmic component)

### Week 3: Real-World Systems
- [ ] WhatsApp (real-time, WebSockets)
- [ ] YouTube (streaming, CDN)
- [ ] Uber (location services, matching)
- [ ] Instagram (feed generation, media storage)

### Week 4: Mock Interviews
- [ ] Practice 2-3 full interviews (45 min each)
- [ ] Time yourself
- [ ] Record and review
- [ ] Focus on communication, not just design

---

## 🎯 Interview Framework (Use This Every Time!)

### Step 1: Requirements (5 minutes)
**Ask Clarifying Questions**:
- Functional requirements (what features?)
- Non-functional requirements (scale, latency, availability?)
- Read-heavy or write-heavy?
- Consistency requirements?

### Step 2: Capacity Estimation (5 minutes)
**Calculate**:
- DAU (Daily Active Users)
- QPS (Queries Per Second)
- Storage needed (GB/TB)
- Bandwidth needed (Mbps/Gbps)

**Example**:
```
100M DAU, each user posts 2 tweets/day
= 200M tweets/day
= 200M / 86,400 seconds
≈ 2,300 tweets/second
Peak (3x): ≈ 7,000 tweets/second
```

### Step 3: High-Level Architecture (10 minutes)
**Draw Components**:
```
[Clients] → [Load Balancer] → [API Gateway] → [Services] → [Databases]
                                                    ↓
                                              [Cache] [Queue]
```

**Identify**:
- Client (web, mobile)
- Load balancer
- API Gateway
- Microservices
- Databases (SQL, NoSQL)
- Cache (Redis)
- Message Queue (Kafka)
- Storage (S3)

### Step 4: Deep Dive (15 minutes)
**Interviewer picks 1-2 areas**:
- Database schema design
- API design
- Caching strategy
- Scaling approach
- Handling edge cases

**Be ready to**:
- Draw detailed diagrams
- Discuss trade-offs (time vs space, consistency vs availability)
- Explain algorithms
- Mention specific technologies

### Step 5: Identify Bottlenecks (5 minutes)
**Proactively discuss**:
- Single points of failure
- Scaling limitations
- Performance bottlenecks
- How to scale 10x

---

## 🔧 Technology Stack Reference

### Databases
- **SQL**: PostgreSQL, MySQL (ACID, transactions)
- **NoSQL Document**: MongoDB (flexible schema)
- **NoSQL Wide-Column**: Cassandra, HBase (high writes)
- **NoSQL Key-Value**: Redis, DynamoDB (fast reads)
- **Search**: Elasticsearch, Solr (full-text search)

### Caching
- **In-Memory**: Redis, Memcached
- **CDN**: CloudFront, Akamai, Cloudflare

### Message Queues
- **High Throughput**: Kafka (event streaming)
- **General Purpose**: RabbitMQ (task queues)
- **Cloud Native**: AWS SQS, Google Pub/Sub

### Load Balancing
- **Layer 4**: AWS NLB, HAProxy (TCP/UDP)
- **Layer 7**: AWS ALB, Nginx (HTTP/HTTPS)

### Storage
- **Object Storage**: AWS S3, Google Cloud Storage
- **Block Storage**: EBS, Persistent Disks
- **File Storage**: EFS, NFS

### Monitoring & Logging
- **Metrics**: Prometheus + Grafana
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Tracing**: Jaeger, Zipkin
- **APM**: Datadog, New Relic

---

## 📊 Back-of-Envelope Calculations

### Powers of 2
```
2^10 = 1 KB   ≈ 1 thousand bytes
2^20 = 1 MB   ≈ 1 million bytes
2^30 = 1 GB   ≈ 1 billion bytes
2^40 = 1 TB   ≈ 1 trillion bytes
```

### Time
```
1 second  = 1,000 milliseconds (ms)
1 minute  = 60 seconds
1 hour    = 3,600 seconds
1 day     = 86,400 seconds (≈ 100K)
1 month   = 2.5M seconds
1 year    = 31.5M seconds (≈ 30M)
```

### Latency
```
Memory:         100 ns
SSD:            150 μs
Disk:           10 ms
Network (same DC): 500 μs
Network (cross continent): 150 ms
```

### Throughput Estimation
```
1 MB/s = 8 Mbps
1 GB/s = 8 Gbps
```

---

## 🎓 Common Interview Questions & Quick Answers

### 1. **How do you scale a database?**
**Answer**:
- **Vertical**: Add more RAM/CPU (limited)
- **Horizontal**: 
  - Read replicas (for reads)
  - Sharding (for writes)
  - Denormalization (avoid joins)

### 2. **SQL vs NoSQL - When to use which?**
**Answer**:
- **SQL**: Structured data, ACID needed, complex queries with joins
- **NoSQL**: Unstructured data, high writes, eventual consistency OK

### 3. **How do you prevent single point of failure?**
**Answer**:
- Replication (multiple copies)
- Load balancing (multiple servers)
- Multi-region deployment
- Health checks + auto-failover

### 4. **How do you handle 1M requests/second?**
**Answer**:
- Horizontal scaling (100+ servers)
- Caching (reduce DB load)
- CDN (serve static content)
- Async processing (message queues)
- Database sharding

### 5. **Explain CAP Theorem**
**Answer**:
- **C**onsistency: All nodes see same data
- **A**vailability: Every request gets response
- **P**artition Tolerance: Works despite network failures
- Can only have 2 out of 3
- In practice: Choose CP (banks) or AP (social media)

---

## 🏆 Success Checklist

### Before Interview
- [ ] Read HLD_INTERVIEW_CHEATSHEET.md
- [ ] Practice 5+ system designs
- [ ] Know capacity estimation formulas
- [ ] Understand CAP theorem cold
- [ ] Can explain caching strategies
- [ ] Know when to shard databases

### During Interview
- [ ] Ask clarifying questions (don't assume!)
- [ ] Do capacity estimation (show math)
- [ ] Start simple, then scale
- [ ] Draw clear diagrams
- [ ] Think out loud
- [ ] Discuss trade-offs
- [ ] Identify bottlenecks
- [ ] Mention specific technologies

### After Interview
- [ ] Review what went well
- [ ] Note areas to improve
- [ ] Practice weak areas
- [ ] Do mock interviews

---

## 📁 Folder Structure

```
high-level-design/
├── HLD_INTERVIEW_CHEATSHEET.md          # 📚 Your main study guide
├── README.md                             # This file
│
├── parking-lot-system-hld.md             # ✅ Complete HLD
├── distributed-cache-system-hld.md       # ✅ Complete HLD
│
└── (More HLD documents to be added based on your priorities)
```

---

## 🎯 Next Steps

1. **Read the Cheatsheet**: Start with `HLD_INTERVIEW_CHEATSHEET.md`
2. **Study Examples**: Read the 2 complete HLD documents
3. **Practice**: Pick a system (e.g., Twitter) and design it yourself
4. **Time Yourself**: 45 minutes per system
5. **Compare**: Look up real architectures (Engineering blogs)
6. **Iterate**: Do 10-20 designs before interviews

---

## 🌟 Pro Tips

### For Communication
- ✅ "Let me clarify the requirements first..."
- ✅ "Given 100M users, let's estimate the load..."
- ✅ "I'll start with a simple design and then scale it..."
- ✅ "The trade-off here is X vs Y..."
- ❌ Don't jump straight to complex architecture
- ❌ Don't assume requirements
- ❌ Don't forget to do math

### For Scaling
- Start with 1 server
- Then add load balancer + multiple servers
- Then add database replicas
- Then add caching
- Then add sharding
- Then add message queues
- Then add CDN
- Show incremental thinking!

### For Answering Follow-ups
- "That's a great question. Let me think..."
- "There are several approaches here..."
- "The trade-off is... so I'd choose X because..."
- "In practice, companies like Netflix use..."

---

## 📖 Additional Resources

### System Design Blogs
- **Engineering Blogs**: Netflix Tech Blog, Uber Engineering, Airbnb Engineering
- **Books**: "Designing Data-Intensive Applications" (Martin Kleppmann)
- **Courses**: Grokking the System Design Interview

### Practice Platforms
- **Mock Interviews**: Pramp, interviewing.io
- **Visualize**: Draw.io, Excalidraw for diagrams

---

**Location**: `/Users/I771246/Abhi Personal/JavaFullstackNotes/System_Design/high-level-design/`

**Start Here**: `HLD_INTERVIEW_CHEATSHEET.md`

---

Good luck with your HLD interviews! 🚀

**Remember**: 
- There's no single "correct" design
- Communication matters more than perfection
- Show your thinking process
- Discuss trade-offs
- You've got this! 💪
