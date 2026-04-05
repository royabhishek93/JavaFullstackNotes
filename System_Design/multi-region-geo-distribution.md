# Q23: Multi-Region / Geo-Distribution (Global Users)

**Study Time:** 12-15 minutes | **Frequency:** 70% in interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## Scenario

You run an e-commerce platform with users in the US, Europe, and Asia. Users in Asia report slow page loads (400-700 ms latency). You also have EU data residency requirements. The CTO asks: **"How do we design a multi-region system?"**

---

## Key Principle

Multi-region systems reduce latency and improve availability by deploying **compute + data** across regions. The tradeoff is **consistency, complexity, and cost**.

---

## Priority Map

| Priority | Topic | Why It Matters |
|---------|------|----------------|
| 🔥 MUST KNOW | Active-Active vs Active-Passive | Core architecture choice |
| 🔥 MUST KNOW | Data replication strategy | Consistency and correctness |
| ✅ SHOULD KNOW | Geo routing (DNS/Anycast) | How traffic reaches region |
| ✅ SHOULD KNOW | Conflict resolution | Required in active-active writes |
| 👍 GOOD TO KNOW | Data residency compliance | Legal requirement |
| ⚙️ NICHE | Multi-leader CRDTs | Advanced consistency model |

---

## Step-by-Step Design

### 1) Define Your Latency and Availability Goals

- Latency target (p95/p99)
- RTO/RPO for failures
- Which flows must be strongly consistent (payments, inventory)?

### 2) Choose a Deployment Model

**Option A: Active-Passive (Primary + DR)**
- Writes go to one region
- Other regions are read-only or warm standby
- Simple consistency, slower failover

**Option B: Active-Active (Multi-Primary)**
- Reads and writes in every region
- Lowest latency
- Requires conflict resolution

### 3) Pick Data Placement

- **Single primary DB** + read replicas in other regions
- **Multi-region DB** (e.g., Spanner, Cosmos DB, Aurora Global DB)
- **Sharding by geography** (EU data stays in EU)

### 4) Route Traffic

- **Geo DNS**: routes by user location
- **Anycast + Global Load Balancer**: lowest latency region
- **Edge caching**: static assets at CDN edge

### 5) Handle Consistency

- Strong consistency for money movement
- Eventual consistency for profile updates, analytics
- Use **idempotency** and **versioning** to resolve conflicts

---

## Active-Active Conflict Resolution Examples

### Example 1: Profile Updates (Last-Write-Wins)

```
Region US writes: displayName = "Abhi", version=12, ts=10:01:05
Region EU writes: displayName = "Abhishek", version=13, ts=10:01:07

Resolution: choose the write with the highest version or latest timestamp.
Result: displayName = "Abhishek"
```

### Example 2: Shopping Cart (Commutative Merge)

```
US: add item A, quantity +1
EU: add item A, quantity +1

Merge rule: sum quantities for same item
Result: item A quantity = 2
```

### Example 3: Likes/Counts (CRDT Counter)

```
US increments likes by 3
Asia increments likes by 2

CRDT G-Counter merge: sum per-region counters
Result: likes = 5
```

### Example 4: Inventory (Avoid Active-Active Writes)

```
Inventory must be strongly consistent.
Use single-writer or global strong DB.
Active-active with async replication can oversell stock.
```

---

## Example Architecture

```
Users (US/EU/Asia)
   ↓
Geo DNS / Global LB
   ↓
Closest Region
   ├─ App Layer
   ├─ Cache (regional)
   └─ DB
        ├─ Primary (US)
        └─ Read Replicas (EU, Asia)
```

### Active-Active Variant

```
Region US  ←→  Region EU  ←→  Region Asia
   App + DB      App + DB      App + DB
      ↕             ↕             ↕
   Async Replication + Conflict Resolution
```

---

## Consistency vs Latency Tradeoff

| Model | Latency | Consistency | Complexity |
|------|---------|-------------|------------|
| Active-Passive | Medium | Strong | Low |
| Active-Active (Async) | Low | Eventual | High |
| Global Strong DB | High | Strong | Medium |

---

## Common Strategies

### Strategy 1: Read Local, Write Primary
- Local reads for speed
- Writes to primary for consistency
- Use **async replication** to other regions

### Strategy 2: Geo-Sharding
- EU users stored only in EU
- US users stored in US
- Reduces cross-region writes

### Strategy 3: Edge + Regional Cache
- Cache data near users
- Reduce DB load
- Use TTL and cache invalidation carefully

---

## Failure Handling

- Region down → route traffic to nearest healthy region
- Degraded mode → read-only when cross-region consistency fails
- Health checks + auto failover

---

## Interview Q&A

### Q1: Active-Active vs Active-Passive?

**Answer:**
```
Active-Passive: single write region, simple, higher latency for far users.
Active-Active: multi-write, low latency, needs conflict resolution.
```

---

### Q2: How do you handle data conflicts in Active-Active?

**Answer:**
```
Use conflict resolution strategies:
- Last write wins (simple but risky)
- Version vectors
- Application-level merges
- CRDTs for specific data types
```

---

### Q3: How do you ensure data residency?

**Answer:**
```
Use geo-sharding so EU data only stays in EU.
Also enforce access policies at the DB layer.
```

---

### Q4: How do you route users to the nearest region?

**Answer:**
```
Use Geo DNS or Anycast with a global load balancer.
This routes traffic by location and latency.
```

---

### Q5: What should be strongly consistent?

**Answer:**
```
Payments, inventory, account balances.
Other domains like analytics can be eventual.
```

---

## Common Pitfalls

```java
❌ Pitfall 1: Multi-region without conflict strategy
// Active-active writes will diverge

❌ Pitfall 2: Single global cache
// Becomes a latency bottleneck

❌ Pitfall 3: Ignoring data residency
// Compliance violations

❌ Pitfall 4: Synchronous cross-region calls
// Increases p99 latency sharply
```

---

## Interview Answer (Concise)

**Q: "How do you design for global users?"**

**Answer:**

> "I start with latency and consistency goals, then pick active-passive or active-active. I route traffic with Geo DNS or a global load balancer. For data, I either use a global DB, read replicas with a single write region, or geo-sharding to meet residency rules. For strong consistency flows like payments, I keep writes centralized or use strongly consistent global DBs. For other flows, I allow eventual consistency and resolve conflicts with versioning or CRDTs."

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| Active-Active vs Active-Passive | Core tradeoff | ⭐⭐⭐⭐⭐ |
| Geo routing | Reduces latency | ⭐⭐⭐⭐ |
| Consistency model | Prevents data bugs | ⭐⭐⭐⭐⭐ |
| Data residency | Regulatory requirement | ⭐⭐⭐⭐ |
| Conflict resolution | Required for multi-write | ⭐⭐⭐⭐ |
