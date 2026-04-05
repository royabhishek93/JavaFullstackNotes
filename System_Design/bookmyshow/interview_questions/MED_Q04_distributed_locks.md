# Question 4: How would you handle seat booking across multiple data centers (Distributed Locks)?

## Difficulty Level: ⭐⭐⭐⭐ (Staff/Principal)

## Expected Answer Duration: 12-15 minutes

---

## The Problem:

```
Scenario: BookMyShow operates in US, EU, and APAC regions
- US data center: Virginia
- EU data center: Frankfurt  
- APAC data center: Singapore

User in India books a seat → writes to Singapore DC
User in UK views same seat → reads from Frankfurt DC
Replication lag: 100-500ms

Question: How do you prevent double-booking across data centers?
```

---

## ❌ Poor Answer (Mid-Level):

> "I'll use database row-level locks with FOR UPDATE."

**Why this fails:**
- FOR UPDATE only works within a single database instance
- Doesn't work across data centers (different databases)
- Shows lack of distributed systems knowledge

---

## ✅ Good Answer (Architect Level):

### **Approach 1: Single Master Write (Recommended for BookMyShow)**

```
┌─────────────────────────────────────────────────────────┐
│         SINGLE MASTER ARCHITECTURE                       │
└─────────────────────────────────────────────────────────┘

    US (Virginia)           EU (Frankfurt)        APAC (Singapore)
    ┌──────────────┐       ┌──────────────┐      ┌──────────────┐
    │   Read       │       │   Read       │      │   MASTER     │
    │   Replica    │       │   Replica    │      │   (Write)    │
    └──────────────┘       └──────────────┘      └──────┬───────┘
           │                      │                      │
           │                      │                      │
           └──────── All writes go to master ───────────┘
                    (bookings written to Singapore)

Booking Flow:
──────────────────────────────────────────────────────────
1. User in UK searches movies → Read from Frankfurt (fast)
2. User clicks "Book Seat 5" → Write to Singapore (master)
3. Replication: Singapore → Frankfurt, Virginia (500ms lag)
4. Other users see updated status after replication

Pros:
✓ No distributed locks needed (single source of truth)
✓ Consistent (all writes serialize through master)
✓ Simple to implement
✓ No split-brain scenarios

Cons:
✗ Higher latency for writes from US/EU (100-200ms extra)
✗ Single point of failure (mitigated by automatic failover)

Latency Analysis:
──────────────────────────────────────────────────────────
UK user books seat:
├─ Network: London → Singapore = 180ms
├─ Processing: 50ms
├─ Network: Singapore → London = 180ms
└─ Total: 410ms (acceptable for booking)

US user books seat:
├─ Network: New York → Singapore = 220ms
├─ Processing: 50ms
├─ Network: Singapore → New York = 220ms
└─ Total: 490ms (still acceptable)
```

---

### **Approach 2: Distributed Locks with Redis/Redlock**

```java
/**
 * For truly distributed writes (if needed)
 * Example: Flash sale where writes happen globally
 */
@Service
public class DistributedBookingService {
    
    private final RedissonClient redissonClient;
    
    public Booking bookSeatsWithDistributedLock(BookingRequest request) {
        
        // Generate lock key (same across all DCs)
        String lockKey = "seat_lock:show:" + request.getShowId() + 
                        ":seats:" + String.join(",", request.getSeatIds());
        
        RLock lock = redissonClient.getLock(lockKey);
        
        try {
            // Try to acquire lock with timeout
            boolean acquired = lock.tryLock(
                5,      // Wait up to 5 seconds
                15,     // Lock held for max 15 seconds
                TimeUnit.SECONDS
            );
            
            if (!acquired) {
                throw new LockAcquisitionException(
                    "Could not acquire lock for seats. Another user is booking."
                );
            }
            
            // Critical section: Check and book seats
            List<SeatAvailability> seats = seatRepository.findByIds(
                request.getShowId(), 
                request.getSeatIds()
            );
            
            // Validate all seats available
            List<SeatAvailability> unavailable = seats.stream()
                .filter(s -> s.getStatus() != SeatStatus.AVAILABLE)
                .collect(Collectors.toList());
            
            if (!unavailable.isEmpty()) {
                throw new SeatNotAvailableException(
                    "Seats not available: " + unavailable
                );
            }
            
            // Book seats
            Booking booking = createBooking(request, seats);
            
            return booking;
            
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new BookingException("Interrupted while acquiring lock", e);
            
        } finally {
            // Always release lock
            if (lock.isHeldByCurrentThread()) {
                lock.unlock();
            }
        }
    }
}
```

**Redlock Algorithm Configuration:**

```yaml
# Redis Cluster Configuration (Multi-DC)
spring:
  redis:
    cluster:
      nodes:
        - redis-us-1.bookmyshow.com:6379
        - redis-us-2.bookmyshow.com:6379
        - redis-eu-1.bookmyshow.com:6379
        - redis-eu-2.bookmyshow.com:6379
        - redis-apac-1.bookmyshow.com:6379
        - redis-apac-2.bookmyshow.com:6379
      
      # Redlock requires majority consensus
      # 6 nodes → need 4 nodes to agree (quorum)
      min-locks-for-quorum: 4

redisson:
  config:
    multiLock:
      enabled: true
      quorum: 4  # Must acquire lock on 4/6 Redis instances
```

**How Redlock Works:**

```
┌─────────────────────────────────────────────────────────┐
│              REDLOCK ALGORITHM                           │
└─────────────────────────────────────────────────────────┘

User A tries to book Seat 5:

Step 1: Try to acquire lock on all 6 Redis instances
────────────────────────────────────────────────────────
SET seat_lock:show:123:seat:5 "user_A_request_id" NX PX 15000

Redis US-1:  ✅ Acquired
Redis US-2:  ✅ Acquired
Redis EU-1:  ✅ Acquired
Redis EU-2:  ✅ Acquired
Redis APAC-1: ✅ Acquired
Redis APAC-2: ✅ Acquired

Acquired: 6/6 ✅ (exceeds quorum of 4)
Lock held: 15 seconds
Total time: 50ms

Step 2: User B tries same seat (concurrent)
────────────────────────────────────────────────────────
SET seat_lock:show:123:seat:5 "user_B_request_id" NX PX 15000

Redis US-1:  ❌ Already locked by User A
Redis US-2:  ❌ Already locked by User A
Redis EU-1:  ❌ Already locked by User A
Redis EU-2:  ❌ Already locked by User A
Redis APAC-1: ❌ Already locked by User A
Redis APAC-2: ❌ Already locked by User A

Acquired: 0/6 ❌ (below quorum)
User B fails → retry or return error

Step 3: User A completes booking
────────────────────────────────────────────────────────
- Book seats in database
- Commit transaction
- Release locks on all 6 Redis instances
- DEL seat_lock:show:123:seat:5 on all nodes

Step 4: User B retries
────────────────────────────────────────────────────────
- Locks now released
- User B acquires locks
- Checks seat status → BOOKED
- Returns "Seat taken" error
```

---

### **Approach 3: Partition by Geography (Avoid Cross-DC Writes)**

```
┌─────────────────────────────────────────────────────────┐
│         GEOGRAPHIC PARTITIONING                          │
└─────────────────────────────────────────────────────────┘

Concept: Shows belong to specific regions

US Shows:
├─ Show IDs: 1-1,000,000
├─ Master: Virginia DC
└─ Users in US book US shows only

EU Shows:
├─ Show IDs: 1,000,001-2,000,000
├─ Master: Frankfurt DC
└─ Users in EU book EU shows only

APAC Shows:
├─ Show IDs: 2,000,001-3,000,000
├─ Master: Singapore DC
└─ Users in APAC book APAC shows only

Routing Logic:
──────────────────────────────────────────────────────────
public DataCenter getDataCenterForShow(Long showId) {
    if (showId <= 1_000_000) {
        return DataCenter.US;
    } else if (showId <= 2_000_000) {
        return DataCenter.EU;
    } else {
        return DataCenter.APAC;
    }
}

Pros:
✓ No cross-DC coordination needed
✓ Low latency (always write to local DC)
✓ High availability (DC failure only affects that region)

Cons:
✗ Users can't book shows in other regions
✗ Less flexibility
✗ Requires geographic show database
```

---

### **Approach 4: Consensus Protocol (Raft/Paxos) - Advanced**

```
┌─────────────────────────────────────────────────────────┐
│              RAFT CONSENSUS PROTOCOL                     │
└─────────────────────────────────────────────────────────┘

Use Case: Critical bookings requiring strong consistency

Architecture:
──────────────────────────────────────────────────────────
    US Node          EU Node         APAC Node
    ┌──────┐        ┌──────┐        ┌──────┐
    │Follower│      │Leader│        │Follower│
    └──────┘        └──────┘        └──────┘
                        │
                        │ Majority consensus required
                        │ (2/3 nodes must agree)
                        │
    User books seat → EU Leader
                        │
                        ├──> Replicate to US: ✅
                        ├──> Replicate to APAC: ✅
                        │
                        └──> Commit (majority achieved)

Booking Flow:
──────────────────────────────────────────────────────────
1. Write request sent to Leader (EU)
2. Leader proposes: "Book seat 5 for show 123"
3. Followers vote: US (yes), APAC (yes)
4. Majority achieved (3/3)
5. Leader commits
6. Followers commit
7. User gets confirmation

If Leader fails:
├─ Election timeout (150-300ms)
├─ New leader elected (US or APAC)
└─ System continues

Libraries:
- etcd (Raft implementation)
- Consul (Raft implementation)
- Apache Zookeeper (ZAB protocol, similar to Paxos)

Cons:
✗ Higher latency (consensus requires 2+ nodes)
✗ Complex to implement
✗ Overkill for BookMyShow (single master sufficient)
```

---

## 📊 Comparison Table:

```
┌──────────────────────┬───────────────┬────────────┬──────────────┬─────────────┐
│     Approach         │   Consistency │  Latency   │  Complexity  │    Cost     │
├──────────────────────┼───────────────┼────────────┼──────────────┼─────────────┤
│ Single Master        │ Strong        │ 100-500ms  │ Low ⭐       │ Low         │
│ (Recommended)        │ ✅            │            │              │             │
├──────────────────────┼───────────────┼────────────┼──────────────┼─────────────┤
│ Distributed Locks    │ Strong        │ 50-200ms   │ Medium ⭐⭐  │ Medium      │
│ (Redlock)            │ ✅            │            │              │             │
├──────────────────────┼───────────────┼────────────┼──────────────┼─────────────┤
│ Geographic           │ Strong        │ <50ms      │ Low ⭐       │ Low         │
│ Partitioning         │ ✅            │ (local)    │              │             │
├──────────────────────┼───────────────┼────────────┼──────────────┼─────────────┤
│ Consensus Protocol   │ Strong        │ 200-500ms  │ High ⭐⭐⭐⭐│ High        │
│ (Raft/Paxos)         │ ✅            │            │              │             │
├──────────────────────┼───────────────┼────────────┼──────────────┼─────────────┤
│ Eventual Consistency │ Weak ⚠️      │ <50ms      │ Low ⭐       │ Low         │
│ (Anti-pattern)       │ ❌            │            │              │             │
└──────────────────────┴───────────────┴────────────┴──────────────┴─────────────┘
```

---

## 🔥 Interview Follow-Ups:

### **Q: "What if master data center goes down?"**

**A:** 
```
Automatic Failover Strategy:
──────────────────────────────────────────────────────────
1. Health Check: Every 1 second, replicas ping master
2. Failure Detection: 3 consecutive failures = master down
3. Election: Replicas vote for new master (lowest latency wins)
4. Promotion: Replica promoted to master (30 seconds)
5. DNS Update: Route53 points to new master
6. Resume: Bookings continue with new master

During Failover (30 seconds):
├─ Writes: Queued in SQS (processed after failover)
├─ Reads: Continue from replicas (slightly stale data OK)
└─ Users: See "System under maintenance" for 30s

Data Loss:
├─ Synchronous replication: 0 data loss
├─ Asynchronous replication: Max 5 seconds of data loss
└─ Mitigation: Use synchronous for critical regions
```

---

### **Q: "How do you handle split-brain scenario?"**

**A:**
```
Split-Brain: Two data centers both think they're master

Prevention:
──────────────────────────────────────────────────────────
1. Fencing Token: Each master has incrementing token
   - Master 1 (Singapore): Token 42
   - Master 2 (Frankfurt): Token 43 (newer)
   - Database rejects writes from token 42

2. Quorum Requirement: Need majority of nodes
   - 3 DCs → need 2 to agree
   - US and EU say Frankfurt is master
   - Singapore isolated → demotes itself

3. Witness Node: Tie-breaker in neutral location
   - 2 DCs + 1 witness = 3 votes
   - Prevents split-brain

Example:
──────────────────────────────────────────────────────────
Network Partition:
US + EU (connected)     |    APAC (isolated)
──────────────────      |    ──────────────
Votes: 2/3 (majority)   |    Votes: 1/3
Result: US/EU continue  |    APAC stops accepting writes
                        |    (to prevent inconsistency)
```

---

### **Q: "Distributed locks sound complex. Why not optimistic locking?"**

**A:**
```
Optimistic Locking Across DCs:

┌─────────────────────────────────────────────────────────┐
│         DOES NOT WORK ACROSS DATA CENTERS                │
└─────────────────────────────────────────────────────────┘

Problem:
────────────────────────────────────────────────────────
User A (US DC):
├─ Read: seat_availability (version=10)
├─ Decide to book
└─ Write: UPDATE ... WHERE version=10

User B (EU DC):
├─ Read: seat_availability (version=10) ← Same!
├─ Decide to book
└─ Write: UPDATE ... WHERE version=10 ← Same!

Result: Both writes succeed if they hit different DCs!
💥 Double-booking across DCs

Why?
────────────────────────────────────────────────────────
- Optimistic locking only works within single database
- Replication lag (100-500ms) means both see version=10
- No coordination between DCs during write

Solution:
────────────────────────────────────────────────────────
1. Use single master (all writes go to one DB)
2. OR use distributed locks (coordinate across DCs)
3. Never rely on optimistic locking across DCs
```

---

## 💡 Key Takeaway for Interview:

**Perfect Answer:**

> "For BookMyShow's multi-DC deployment, I'd use **single master architecture** with master in Singapore (largest market). Here's why:
> 
> **Architecture:**
> - All bookings write to Singapore master
> - US/EU have read replicas (low latency reads)
> - Replication lag: 100-500ms (acceptable for bookings)
> - Automatic failover if master fails (30s downtime)
> 
> **Why not distributed locks:**
> - Adds complexity (Redlock requires 6 Redis instances)
> - Higher latency (must acquire locks across DCs)
> - More failure modes (what if 3/6 Redis nodes fail?)
> - Not needed if writes go to single master
> 
> **Handling cross-DC writes:**
> - 100-500ms latency is acceptable for booking (user expects delay)
> - UI can show "Confirming your booking..." spinner
> - Much simpler than distributed coordination
> 
> **When I'd use distributed locks:**
> - Flash sales where writes must be fast globally
> - Multi-master write scenarios (we don't have this)
> - Financial systems requiring consensus (overkill here)
> 
> **Alternative (geographic partitioning):**
> - US shows → US DC (writes local)
> - EU shows → EU DC (writes local)
> - APAC shows → APAC DC (writes local)
> - No cross-DC coordination needed
> - Trade-off: Users can't book shows in other regions"

---

## 🎯 Architecture Decision Record (ADR):

```
Title: Multi-DC Booking Architecture
Status: Accepted
Context: BookMyShow expanding to US, EU, APAC
Decision: Single master write architecture
──────────────────────────────────────────────────────────

Considered Alternatives:
1. Multi-master with distributed locks (Redlock)
2. Geographic partitioning (shows by region)
3. Consensus protocol (Raft)
4. Eventual consistency (REJECTED - double-booking risk)

Chosen: Single Master (Singapore)
──────────────────────────────────────────────────────────
Pros:
✓ Simple implementation (existing code mostly works)
✓ Strong consistency (single source of truth)
✓ No distributed lock complexity
✓ Acceptable latency (100-500ms for booking)
✓ Easy to reason about (all writes serialize)

Cons:
✗ Higher write latency from US/EU
✗ Single point of failure (mitigated by auto-failover)

Mitigation:
- Cache seat availability in each region (reads fast)
- Queue writes during failover (no data loss)
- Monitor replication lag (alert if >1 second)
- Pre-warm replicas for instant promotion

Cost:
- No additional Redis cluster for locks (saves $10k/year)
- Simple operational model (saves engineering time)

Review Date: 2027-01-01 (reassess if US/EU traffic > 50%)
```

This demonstrates Staff/Principal level distributed systems expertise! 🎯
