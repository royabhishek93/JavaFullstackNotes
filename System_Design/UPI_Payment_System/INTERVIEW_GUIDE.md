# Interview Preparation Guide - UPI System Design

## Quick Reference Checklist

### For HLD Interview (45 minutes)

#### Phase 1: Requirements (5 minutes)
- [ ] Clarify functional requirements
  - P2P, P2M, QR payments
  - Transaction history, notifications
- [ ] Clarify non-functional requirements
  - 99.99% availability
  - <3s latency
  - 50K TPS
  - Strong consistency
- [ ] Estimate scale
  - 500M users
  - 10B transactions/month
  - 150TB storage/year

#### Phase 2: High-Level Architecture (15 minutes)
- [ ] Draw component diagram with:
  - Client apps layer
  - API Gateway + Load Balancer
  - Microservices (Payment, User, VPA, Auth)
  - NPCI Switch
  - Banks
- [ ] Explain data flow for P2P transfer
- [ ] Show how NPCI acts as central hub

#### Phase 3: Deep Dive (15 minutes)
- [ ] Database design
  - SQL for transactions (ACID)
  - NoSQL for logs
  - Redis for cache
  - Sharding strategy
- [ ] Transaction flow with 2-Phase Commit
- [ ] How to prevent double spending
- [ ] Idempotency handling

#### Phase 4: Edge Cases & Trade-offs (10 minutes)
- [ ] What if NPCI is down?
- [ ] What if debit succeeds but credit fails?
- [ ] How to handle network partitions?
- [ ] CAP theorem choice (CP over AP)
- [ ] Settlement process

---

## 🎯 Core Concepts Explained in Simple English

### 2-Phase Commit (2PC) - Like a Handshake Deal

**Real-World Analogy**: Trading your iPhone for a friend's PlayStation

**Phase 1 - "Are you ready?"**
```
You: "Do you have the PlayStation?"
Friend: "Yes!"
You: "I have the iPhone!"
Friend: "Let's trade!"
```
Both confirm they're ready. If either says "No", deal is cancelled.

**Phase 2 - "Let's do it!"**
```
You give iPhone → Friend gives PlayStation
BOTH happen at the same time!
```

**In UPI:**
```
Phase 1 (PREPARE):
NPCI → Sender Bank: "Ready to debit ₹500?"
Sender Bank: "Yes! ₹500 locked ✓"

NPCI → Receiver Bank: "Ready to credit ₹500?"  
Receiver Bank: "Yes! Account valid ✓"

Phase 2 (COMMIT):
NPCI: "Both ready? GO!"
→ Sender: Deduct ₹500 ✓
→ Receiver: Add ₹500 ✓
```

**Why it matters**: Either BOTH happen OR neither happens. No money disappears!

---

### Settlement (T+0/T+1) - Instant for Users, Bulk for Banks

**What You See (Instant)**:
```
10:00 AM - Send ₹500
10:00 AM - "Success! ✓" (2 seconds)
10:00 AM - Friend sees ₹500
```

**What Actually Happens (Behind the Scenes)**:
```
10:00 AM - Your balance: -₹500 (shown instantly)
10:00 AM - Friend's balance: +₹500 (shown instantly)

11:59 PM - Banks transfer REAL money in bulk
         - Your bank → NPCI: ₹500
         - NPCI → Friend's bank: ₹500
```

**Restaurant Analogy**:
- You order food → Instant ✓
- You eat food → Instant ✓  
- Restaurant pays suppliers → End of day (batch)

**Why separate?**
- **Fast**: Users see results in 2 seconds
- **Efficient**: Banks process millions in ONE batch
- **Cheap**: One bulk transfer vs millions of small transfers

---

### Idempotency - No Double Charging

**The Problem**:
```
You click "Pay ₹500"
Network is slow... 😰
You click again... and again...

Without Idempotency: Charged ₹500 × 3 = ₹1500! 💸
With Idempotency: Charged ₹500 × 1 only ✓
```

**How it works**:
```
Request 1: "Pay ₹500" [ID: abc123]
→ System: "New! Processing..." → Charges ₹500

Request 2: "Pay ₹500" [ID: abc123]  
→ System: "Seen abc123 before!"
→ Returns previous response, NO new charge
```

**Pizza Shop Analogy**:
```
You: "One pizza please" (call drops)
You call again: "One pizza please"
Shop: "Sir, you already ordered! Same number, same order.
      Sending ONE pizza only!"
```

---

## Common Interview Questions & Answers

### Q1: How does UPI ensure atomicity across two different banks?

**Technical Answer**: UPI uses **Two-Phase Commit (2PC) protocol** coordinated by NPCI:

**Phase 1 - Prepare**:
- NPCI asks sender bank: "Can you debit ₹500?"
- Sender bank locks funds and responds "READY"
- NPCI asks receiver bank: "Can you credit ₹500?"
- Receiver bank validates account and responds "READY"

**Phase 2 - Commit**:
- If both are ready, NPCI sends "COMMIT" to both
- Sender bank debits ₹500
- Receiver bank credits ₹500
- If any fails in Phase 1, NPCI sends "ABORT" to both

**Key Point**: NPCI acts as the transaction coordinator, ensuring both banks either commit or rollback together.

**Simple Interview Answer**: 
> "It's like a handshake deal. NPCI first asks both banks 'Are you ready?' (Phase 1). If both say yes, NPCI says 'Do it now!' (Phase 2). Both execute together - all or nothing. This ensures money doesn't disappear if one bank fails."

---

### Q2: How do you prevent double spending (race condition)?

**Answer**: Multiple layers of protection:

**1. Database-level locking**:
```sql
BEGIN TRANSACTION;
SELECT balance FROM accounts 
WHERE account_id = ? 
FOR UPDATE;  -- Acquires row-level lock

IF balance >= amount THEN
    UPDATE accounts 
    SET balance = balance - amount;
    COMMIT;
ELSE
    ROLLBACK;
END IF;
```

**2. Idempotency**:
- Each request has a unique idempotency key
- Duplicate requests return cached response
- TTL: 24 hours

**3. Transaction status checking**:
- Before debiting, check if transaction is already in PENDING/SUCCESS state

---

### Q3: What happens if a transaction fails after debit but before credit?

**Answer**: This is a **critical failure scenario**. Here's how we handle it:

**Immediate Actions**:
1. Transaction status updated to `REVERSING`
2. Reversal event published to Kafka
3. Reversal service picks up event

**Reversal Flow**:
1. Create a reversal transaction (type: REFUND)
2. Send credit request to sender's bank
3. Retry with exponential backoff if it fails
4. SLA: Reversal within 1 hour

**Monitoring**:
- Alert ops team for manual intervention if reversal fails after 3 retries
- Dashboard shows all transactions in REVERSING state

**Prevention**:
- Receiver bank health checks before initiating
- Circuit breaker pattern to avoid sending to unhealthy banks

---

### Q4: How do you handle NPCI being down?

**Answer**: Multi-layered approach:

**1. Graceful Degradation**:
- Show user: "UPI service temporarily unavailable"
- Suggest alternative payment methods (cards, net banking)
- Don't fail silently

**2. Retry with Circuit Breaker**:
```java
@CircuitBreaker(
    failureThreshold = 5,
    resetTimeout = 30000
)
public NPCIResponse callNPCI(Transaction txn) {
    // NPCI call
}
```
- After 5 failures, circuit opens (stops calling NPCI)
- Resets after 30 seconds
- Prevents cascading failures

**3. Fallback to Other Payment Rails**:
- IMPS (Immediate Payment Service)
- RTGS (Real-Time Gross Settlement) for large amounts
- NEFT for non-urgent transfers

**4. Transaction Reconciliation**:
- Batch job runs every hour to reconcile pending transactions
- Query NPCI for status of stuck transactions

---

### Q5: How do you scale the system to handle 100K TPS?

**Answer**:

**1. Horizontal Scaling**:
- Microservices deployed on Kubernetes
- Auto-scaling based on CPU/memory/request rate
- Payment service: 100+ pods during peak

**2. Database Sharding**:
- Shard by `user_id` hash
- Each shard handles subset of users
- 64 shards initially, expandable to 256

**3. Caching**:
- Redis cluster for:
  - VPA resolution (1 hour TTL)
  - User sessions (30 min TTL)
  - Rate limiting counters
- Cache hit ratio: >95%

**4. Asynchronous Processing**:
- Kafka for non-critical operations:
  - Notifications (SMS, push)
  - Analytics
  - Settlement
- Critical path stays synchronous (payment validation)

**5. Database Read Replicas**:
- 1 Master (writes) + 3 Read Replicas
- Transaction history queries go to replicas
- Reduces master load

**6. CDN for Static Assets**:
- App resources, images served via CloudFlare
- Reduces API server load

---

### Q6: How do you ensure data consistency in a distributed system?

**Answer**: UPI chooses **CP (Consistency + Partition Tolerance)** over AP:

**Strong Consistency Mechanisms**:

**1. Synchronous Replication**:
- PostgreSQL with synchronous replication
- Transaction not committed until replica ACKs
```sql
synchronous_commit = on
synchronous_standby_names = 'replica1'
```

**2. Distributed Transactions (2PC)**:
- NPCI coordinates between banks
- All-or-nothing semantics

**3. Idempotency**:
- Same request always produces same result
- Prevents duplicate charges

**4. Event Sourcing**:
- All state changes stored as immutable events
- Can rebuild state from event log
- Audit trail for compliance

**Trade-offs**:
- **Availability**: During network partition, reject writes rather than accept inconsistent data
- **Latency**: Synchronous replication adds ~50-100ms
- **Acceptable**: Financial correctness > speed

---

### Q7: Explain the database schema for transactions.

**Answer**: Key tables and relationships:

**transactions** (main table):
- `transaction_id` (PK, UUID)
- `sender_account_id` (FK to bank_accounts)
- `receiver_account_id` (FK to bank_accounts)
- `amount` (DECIMAL 18,2)
- `status` (ENUM: INITIATED, PENDING, SUCCESS, FAILED)
- `created_at`, `updated_at`

**Indexes**:
```sql
CREATE INDEX idx_sender ON transactions(sender_account_id, created_at);
CREATE INDEX idx_receiver ON transactions(receiver_account_id, created_at);
CREATE INDEX idx_status ON transactions(status, created_at);
CREATE UNIQUE INDEX idx_npci ON transactions(npci_transaction_id);
```

**Partitioning**:
- Partition by `created_at` (monthly partitions)
- Hot partition (current month): SSD
- Cold partitions: HDD, compressed

**Sharding**:
- Shard by `sender_account_id` (hash-based)
- User's sent transactions stay on one shard
- Received transactions may require cross-shard query (acceptable)

---

### Q8: How do you handle fraud detection?

**Answer**: Multi-layered approach:

**1. Rule-Based Detection**:
```java
// Velocity checks
if (countTransactionsLast1Hour(userId) > 20) {
    blockTransaction("Too many transactions");
}

// Amount checks
if (amount > userDailyLimit) {
    blockTransaction("Daily limit exceeded");
}

// Geographic checks
if (userLocation != expectedLocation) {
    requireAdditionalAuth();
}
```

**2. ML-Based Scoring**:
```java
FraudScore score = mlModel.predict(
    userBehavior,
    transactionPattern,
    deviceFingerprint,
    timeOfDay
);

if (score > HIGH_RISK_THRESHOLD) {
    blockTransaction();
} else if (score > MEDIUM_RISK_THRESHOLD) {
    requireOTP();
}
```

**Features used**:
- Transaction amount deviation from average
- Time since last transaction
- Device change
- Location change
- Beneficiary risk score

**3. Device Binding**:
- MPIN tied to specific device
- Device change requires OTP verification

**4. Real-time Monitoring**:
- Kafka stream processing
- Alerts for suspicious patterns
- Human review for edge cases

---

## Key Diagrams to Draw

### 1. System Architecture (5 minutes)
```
[Apps] → [API Gateway] → [Load Balancer] → [Services] → [NPCI] → [Banks]
                                          ↓
                              [Cache + DB + Kafka]
```

### 2. Transaction Flow (7 minutes)
- Sequence diagram showing 2PC flow
- Include all states: INITIATED → VALIDATED → PENDING → PREPARED → DEBITED → CREDITED → SUCCESS

### 3. Database Schema (5 minutes)
- ERD showing Users, Accounts, Transactions, UPI Handles

---

## Time Management Tips

**HLD Interview**:
- 0-5 min: Requirements
- 5-15 min: Architecture diagram
- 15-30 min: Deep dive (DB, 2PC, caching)
- 30-40 min: Edge cases
- 40-45 min: Q&A

**LLD Interview**:
- 0-5 min: Scope clarification
- 5-20 min: Class diagram
- 20-35 min: Code 2-3 key methods
- 35-45 min: Testing & edge cases

---

## Red Flags to Avoid

❌ **Don't**:
- Ignore edge cases (network failures, partial failures)
- Design for eventual consistency (UPI needs strong consistency)
- Forget about idempotency
- Neglect security (MPIN, encryption)
- Ignore compliance (PCI-DSS, RBI guidelines)

✅ **Do**:
- Ask clarifying questions
- Explain trade-offs
- Show awareness of CAP theorem
- Discuss monitoring and alerting
- Mention real-world constraints

---

## Practice Questions

**Easy**:
1. Design a VPA validation service
2. Implement idempotency checker
3. Design transaction history API with pagination

**Medium**:
4. Design 2-phase commit coordinator
5. Implement fraud detection rule engine
6. Design QR code payment flow

**Hard**:
7. Handle partial failure in distributed transaction
8. Design settlement reconciliation system
9. Implement circuit breaker for NPCI calls

---

## Resources to Review

**Before Interview**:
- [ ] NPCI UPI documentation
- [ ] 2-Phase Commit protocol
- [ ] CAP theorem
- [ ] Database sharding strategies
- [ ] Idempotency patterns
- [ ] Circuit breaker pattern
- [ ] Rate limiting algorithms

**Sample Answer Template**:
1. **Understand**: Restate the question
2. **Clarify**: Ask about scale, constraints
3. **High-Level**: Draw architecture
4. **Deep Dive**: Explain one component in detail
5. **Trade-offs**: Discuss alternatives
6. **Edge Cases**: Handle failures
7. **Scale**: How to scale 10x

Good luck! 🚀
# Cross-Questions from Component Diagram - UPI System

## 📚 Full Forms
- **PSP** = Payment Service Provider (Apps like PhonePe, Google Pay, Paytm)
- **NPCI** = National Payments Corporation of India (Central switch/hub)

---

## 🔥 MOST IMPORTANT QUESTIONS (Must Know)

### 1. **Why do we need NPCI as a central hub? Can't banks directly talk to each other?**

**Answer**: 
Without NPCI, you'd need **N × (N-1) / 2** connections for N banks:
- 100 banks = 4,950 connections
- Each bank maintains 99 integrations

With NPCI (Star topology):
- 100 banks = 100 connections (each talks to NPCI only)
- Banks maintain 1 integration each

**Real analogy**: Airport hub system vs direct flights between every city pair.

---

### 2. **What is the difference between PSP Server and Bank PSP?**

**Answer**:
```
PSP Server (Third-party apps):
- PhonePe, Google Pay, Paytm
- User-facing applications
- NOT a bank themselves
- Connected to multiple banks

Bank PSP (Bank's own system):
- ICICI Bank's UPI system
- HDFC Bank's UPI system  
- They are actual banks
- Handle their own accounts
```

**Example**:
- PhonePe (PSP Server) → Routes to → ICICI Bank (Bank PSP) → Core Banking System

---

### 3. **Why dedicated leased line between PSP and NPCI? Why not regular internet?**

**Answer**:
```
Security reasons:
✅ No public internet exposure
✅ Guaranteed bandwidth
✅ Lower latency (<10ms)
✅ SLA guarantees (99.99% uptime)
✅ No DDoS risk
✅ Encrypted channel (TLS + physical security)

Cost: ~₹5-10 lakhs/month but handles ₹1000 crores/day transactions
```

---

### 4. **How does rate limiting work at API Gateway layer?**

**Answer**:
```
Token Bucket Algorithm:

User gets 1000 tokens/minute
Each request consumes 1 token
Bucket refills at 1000 tokens/minute

Example:
10:00:00 - User has 1000 tokens
10:00:30 - Made 600 requests → 400 tokens left
10:00:45 - Made 500 requests → Blocked! (needs 500, has 400)
10:01:00 - Bucket refills → 1000 tokens again
```

Implementation:
```java
// Redis-based
String key = "rate:" + userId;
long count = redis.incr(key);
if (count == 1) {
    redis.expire(key, 60); // 60 seconds
}
if (count > 1000) {
    throw new RateLimitException();
}
```

---

### 5. **Why have both Master and Read Replicas for PostgreSQL? Why not just scale Master?**

**Answer**:
```
Read/Write Split:
- 80% queries are READS (transaction history, balance check)
- 20% queries are WRITES (new transactions)

Master (Writes only):
- 1 server handles 10K writes/sec
- Strong consistency needed

Read Replicas (Reads only):
- 3 replicas handle 30K reads/sec each = 90K reads/sec total
- Eventual consistency OK (few milliseconds lag)

Can't scale Master horizontally because:
❌ Master-Master conflicts (split brain)
❌ Complex distributed locking
✅ Master-Slave is simpler, battle-tested
```

---

## 🎯 VERY IMPORTANT QUESTIONS

### 6. **Why use both PostgreSQL AND MongoDB? Why not just one database?**

**Answer**:
```
PostgreSQL (ACID needed):
✅ Transactions (can't lose money!)
✅ Users, Accounts
✅ Strong consistency
✅ Complex joins
❌ Slow for high-write logs

MongoDB (High writes):
✅ Transaction logs (100K writes/sec)
✅ Audit trails (append-only)
✅ Schema flexibility
❌ No ACID guarantees (not for money!)
```

**Polyglot Persistence** = Right tool for right job

---

### 7. **What happens if NPCI Adapter service fails? Does the whole system go down?**

**Answer**:
```
Circuit Breaker Pattern:

Normal:
Request → NPCI Adapter → NPCI ✓

After 5 failures (threshold):
Circuit OPENS
Request → Fail Fast (don't call NPCI)
Return: "UPI service temporarily unavailable"

After 30 seconds:
Circuit HALF-OPEN
Try 1 request → If success, CLOSE circuit
              → If fail, stay OPEN

Prevents cascading failures!
```

---

### 8. **Why Kafka for notifications instead of direct HTTP calls?**

**Answer**:
```
Problem with Direct Calls:
Payment Service → (HTTP) → Notification Service
If Notification is down → Payment waits/fails

With Kafka (Event-Driven):
Payment Service → Publish event → Kafka
                                    ↓
                         Notification Service subscribes
                         
Benefits:
✅ Decoupling: Payment doesn't wait for notification
✅ Reliability: Kafka retains messages if subscriber down
✅ Scalability: Multiple consumers can process
✅ Ordering: Partition keys maintain order
```

---

### 9. **How does JWT validation work at API Gateway?**

**Answer**:
```
Login:
User → Auth Service
     ← JWT token (contains: userId, expiry, signature)

Later requests:
User sends: Authorization: Bearer <JWT>

API Gateway:
1. Extracts token from header
2. Verifies signature (using public key)
3. Checks expiry
4. Extracts userId
5. Forwards request with userId to backend

No database call needed! (Stateless)
```

---

### 10. **Why hash-based sharding on user_id? Why not range-based?**

**Answer**:
```
Hash-based (Chosen):
user_id % 64 = shard number
✅ Even distribution
✅ No hotspots
❌ Hard to add/remove shards

Range-based (NOT chosen):
user_id 1-1M → Shard 1
user_id 1M-2M → Shard 2
✅ Easy to add shards
❌ Hotspots (new users → last shard)
❌ Uneven load

For UPI: Even distribution > Easy resharding
```

---

## ⚡ IMPORTANT QUESTIONS

### 11. **What is Service Mesh (Istio)? Why need it?**

**Answer**:
```
Without Service Mesh:
Service A → (HTTP) → Service B
- No encryption between services
- Manual retry logic in each service
- No metrics/tracing out of box

With Service Mesh (Istio):
Service A → (Sidecar Proxy) → (Sidecar Proxy) → Service B
              ↑                      ↑
            Istio                  Istio

Benefits:
✅ Auto mTLS (mutual TLS) between services
✅ Auto retries, circuit breakers
✅ Centralized metrics, logs, tracing
✅ Traffic splitting (canary deployments)
```

---

### 12. **Why TTL of 1 hour for VPA cache but 30 seconds for balance cache?**

**Answer**:
```
VPA Cache (1 hour):
- VPAs rarely change (user@bank is fixed)
- Cache miss cost: Database query (100ms)
- Stale data risk: Low (VPA doesn't change often)

Balance Cache (30 seconds):
- Balance changes frequently (every transaction)
- Cache miss cost: Call to bank API (500ms)
- Stale data risk: High (show wrong balance)

Idempotency Keys (24 hours):
- Prevents duplicates for a day
- After 24h, safe to allow same request again
```

---

### 13. **Why 32 partitions for Kafka topics? Why not 100 or 10?**

**Answer**:
```
Partitions = Parallelism

32 partitions means:
- 32 consumer instances can process in parallel
- Higher throughput (32x vs 1x)

Why not 100?
- More partitions = more overhead
- Each partition has its own file/memory
- Diminishing returns after certain point

Why not 10?
- Can't scale beyond 10 consumers
- Lower throughput

Sweet spot: Number of consumer instances you'll run
UPI case: 32 payment services → 32 partitions
```

---

### 14. **What is HPA? How does it scale pods?**

**Answer**:
```
HPA = Horizontal Pod Autoscaler

Current state:
Payment Service: 20 pods
CPU usage: 80% (threshold: 70%)

HPA detects: CPU > 70%
HPA action: Scale up!
  
Calculation:
desiredReplicas = currentReplicas × (currentMetric / targetMetric)
                = 20 × (80 / 70)
                = 22.8 → 23 pods

Kubernetes spawns 3 new pods
CPU drops to 65%

Also scales DOWN if CPU < 70% for 5 minutes
```

---

### 15. **Why synchronous replication for PostgreSQL but asynchronous for MongoDB?**

**Answer**:
```
PostgreSQL (Financial data):
Master writes → WAIT → Replica ACKs → Commit
✅ Zero data loss (RPO = 0)
❌ Slower writes (100-200ms)

MongoDB (Logs):
Master writes → Commit immediately
Replica syncs later
✅ Fast writes (<10ms)
❌ Possible data loss (last few seconds)

Trade-off:
Money > Speed → Synchronous
Logs < Speed → Asynchronous
```

---

## 📊 MODERATE IMPORTANCE QUESTIONS

### 16. **What is WAF? Give examples of attacks it prevents.**

**Answer**:
```
WAF = Web Application Firewall (Layer 7 firewall)

Blocks:
1. SQL Injection:
   ' OR '1'='1' -- in input
   
2. XSS (Cross-Site Scripting):
   <script>alert('hacked')</script>
   
3. DDoS:
   10,000 requests/second from same IP
   
4. Path Traversal:
   ../../etc/passwd in URL
   
5. API Abuse:
   Scraping endpoints without rate limits
```

---

### 17. **Why both Auth Service (MPIN) and API Gateway (JWT)?**

**Answer**:
```
They serve different purposes:

API Gateway (JWT):
- Every request validation
- "Are you logged in?"
- Fast (no DB call)
- Stateless

Auth Service (MPIN):
- Only for payment transactions
- "Are you the real user?"
- Validates 4-digit PIN
- Checks device binding

Flow:
Login → Auth Service issues JWT
Later: Each request → API Gateway validates JWT
Payment: Payment Service calls Auth Service for MPIN
```

---

### 18. **What is the purpose of NPCI Adapter Service?**

**Answer**:
```
Adapter Pattern - Translates between formats

Payment Service (internal format):
{
  "from": "user@ybl",
  "to": "merchant@icici",
  "amount": 500
}

NPCI Adapter converts to NPCI format:
{
  "payerVPA": "user@ybl",
  "payeeVPA": "merchant@icici", 
  "txnAmount": "500.00",
  "currency": "INR",
  "merchantId": "...",
  "timestamp": "...",
  "signature": "..."
}

Also handles:
- Retry logic (3 attempts with backoff)
- Timeout handling
- Error code mapping
- Response parsing
```

---

### 19. **Why have separate Settlement Service? Can't Payment Service do it?**

**Answer**:
```
Single Responsibility Principle:

Payment Service:
- Real-time user transactions
- High throughput (50K TPS)
- Low latency (<3s)
- Synchronous

Settlement Service:
- Batch processing (end of day)
- Low throughput (1 batch/day)
- Can take hours
- Asynchronous

Separate because:
✅ Different performance characteristics
✅ Different scaling needs
✅ Failure isolation
❌ Settlement batch shouldn't block payments
```

---

### 20. **What are Liveness and Readiness probes in Kubernetes?**

**Answer**:
```
Liveness Probe:
"Is the app alive?"
If fails 3 times → Kubernetes RESTARTS pod
Example: HTTP GET /health/live → 200 OK

Readiness Probe:
"Is the app ready to serve traffic?"
If fails → Remove from load balancer (don't send requests)
Example: HTTP GET /health/ready → 200 OK

Difference:
Liveness: Crashed/deadlocked app
Readiness: Warm-up, dependencies not ready

Java example:
/health/live: return 200 (JVM running?)
/health/ready: return DB.ping() ? 200 : 503
```

---

## 💡 GOOD-TO-KNOW QUESTIONS

### 21. **Why Mutual TLS? What's different from regular TLS?**

**Answer**:
```
Regular TLS (HTTPS):
Client → Server
Client verifies: "Is server legitimate?"
(Certificate check)

Mutual TLS:
Client ← → Server
Both verify each other!
Server also checks: "Is client legitimate?"

Use case:
Service-to-service communication in Istio
Both Payment Service AND VPA Service prove identity
Prevents rogue services
```

---

### 22. **What is Round Robin load balancing? Is it always fair?**

**Answer**:
```
Round Robin:
Request 1 → Server A
Request 2 → Server B  
Request 3 → Server C
Request 4 → Server A (cycle repeats)

Problem:
If Server B is slower (old hardware), it gets overloaded!

Better alternatives:
- Least Connections: Send to server with fewest active connections
- Weighted Round Robin: Server A gets 50%, B gets 30%, C gets 20%
- Response Time: Send to fastest server

UPI uses: Least Connections (mentioned as alternative)
```

---

### 23. **Why 7-day retention for Kafka? Why not forever?**

**Answer**:
```
Storage cost:
100M events/day × 7 days = 700M events
At 1KB each = 700GB storage
Cost: ~$20/month

If forever:
100M × 365 = 36.5B events = 35TB
Cost: ~$700/month

After 7 days:
- Events already processed
- Written to MongoDB for audit
- No need in Kafka anymore

Exception: Regulatory logs (10 years) → S3 Glacier
```

---

### 24. **What is IP Whitelisting for merchants? Why only merchants?**

**Answer**:
```
IP Whitelisting:
Only allow requests from specific IP addresses

Merchant APIs:
merchant.com (fixed IP: 1.2.3.4)
Only this IP can call our API
Extra security layer

Why not for users?
Users have dynamic IPs:
- Home WiFi: 49.x.x.x
- Office WiFi: 103.x.x.x  
- Mobile data: Changes constantly

Can't whitelist dynamic IPs!
```

---

### 25. **How does Device Binding work?**

**Answer**:
```
First Login:
User enters MPIN on Phone A
Backend stores: (userId, deviceFingerprint, publicKey)

deviceFingerprint = hash(
  IMEI,
  Model,
  OS Version,
  MAC Address
)

Later login from Phone B:
Device fingerprint doesn't match!
→ Requires OTP verification
→ Adds Phone B as trusted device

Prevents:
Stolen credentials used on different device
```

---

## 🔧 **Hands-On Experience Questions** (Production Reality Check)

These questions separate theoretical knowledge from real production experience. Interviewers ask these to verify you've actually built/maintained payment systems.

---

### 1. **You deployed a new version and transaction success rate dropped from 99.5% to 97%. How do you debug?**

**What This Tests**: Production debugging, monitoring, incident response

**Answer**:
```
Step 1: Check Monitoring Dashboard (2 min)
- Grafana → Transaction success rate graph
- Which error codes increased? (400, 500, 503?)
- p95/p99 latency changed?
- Error logs spike at deployment time?

Step 2: Analyze Error Patterns (5 min)
- Group by error type:
  * MPIN_INVALID → Frontend issue?
  * NPCI_TIMEOUT → Integration issue?
  * BALANCE_INSUFFICIENT → Logic bug?
  * DATABASE_DEADLOCK → Concurrency issue?

Step 3: Check Recent Code Changes
git diff prod-v1.2.3 prod-v1.2.4
- Transaction validation logic changed?
- New retry mechanism added?
- Timeout values modified?

Step 4: Compare Logs Before/After
- Sample 100 failed transactions
- Check what's different in request flow
- Look for new exception stack traces

Step 5: Quick Fix Decision
Option A: Immediate rollback (if critical)
kubectl rollout undo deployment/payment-service

Option B: Hotfix + Deploy (if small bug)
Fix → Test → Blue-Green deploy

Real Example:
We once changed timeout from 3s → 2s
→ NPCI calls started timing out
→ Success rate dropped 2%
→ Rolled back, increased to 2.5s instead
```

**Follow-up**: "How do you prevent this next time?"
- **Answer**: Feature flags, canary deployment (5% traffic first), synthetic monitoring

---

### 2. **A merchant reports they received ₹10,000 but their dashboard shows ₹0. How do you reconcile?**

**What This Tests**: Data consistency, reconciliation, SQL skills

**Answer**:
```sql
-- Step 1: Find the transaction
SELECT * FROM transactions 
WHERE receiver_account_id = 'MERCHANT_ACCOUNT'
  AND amount = 10000
  AND created_at > NOW() - INTERVAL '7 days';

-- Step 2: Check transaction status
-- Possible states:
-- SUCCESS → Money transferred, dashboard bug
-- PENDING → 2PC didn't complete
-- DEBITED → Sender debited, credit failed
-- REVERSED → Money sent then reversed

-- Step 3: Check settlement table
SELECT * FROM settlement
WHERE transaction_id = 'TXN_12345';

-- Step 4: Check merchant balance cache
-- Redis might be stale
REDIS> GET merchant:balance:MERCHANT_ID

-- Step 5: Verify with NPCI logs
SELECT * FROM npci_callback_log
WHERE transaction_id = 'TXN_12345';

-- Real Issue Found:
Dashboard was reading from read-replica with 5-min lag!
Master had correct balance, replica was behind.

-- Solution:
1. Refresh dashboard from master (critical reads)
2. Add replication lag monitoring
3. Alert if lag > 10 seconds
```

**Follow-up**: "What if NPCI says success but our DB says failed?"
- **Answer**: Manual reconciliation, create reversal request, update DB, notify user

---

### 3. **Redis cache goes down. Your app crashes. Why did this happen and how to fix?**

**What This Tests**: Resilience, cache fallback, anti-patterns

**Answer**:
```java
// ❌ BAD CODE (Causes crash)
public String resolveVPA(String vpa) {
    String accountId = redis.get("vpa:" + vpa); // Throws exception!
    return accountId;
}

// ✅ GOOD CODE (Resilient)
public String resolveVPA(String vpa) {
    try {
        String accountId = redis.get("vpa:" + vpa);
        if (accountId != null) {
            return accountId;
        }
    } catch (RedisException e) {
        log.warn("Redis down, falling back to DB", e);
        metrics.increment("cache_miss_redis_down");
    }
    
    // Fallback to database
    String accountId = database.query(
        "SELECT account_id FROM upi_handles WHERE vpa = ?", vpa
    );
    return accountId;
}

// Even Better: Circuit Breaker
@CircuitBreaker(
    failureThreshold = 5,
    resetTimeout = 30000
)
public String getFromRedis(String key) {
    return redis.get(key);
}
```

**Why This Happens in Real Life**:
- Redis runs out of memory → Evicts keys → App assumes key exists
- Redis cluster split-brain → Inconsistent data
- Network partition → Can't reach Redis

**Fix**:
1. Always wrap cache calls in try-catch
2. Implement circuit breaker
3. Monitor cache hit rate (if drops → investigate)
4. Set Redis max memory policy: `allkeys-lru`

---

### 4. **You see 10,000 transactions stuck in "PENDING" state for 2 hours. What do you do?**

**What This Tests**: Incident handling, batch operations, transaction recovery

**Answer**:
```
Step 1: Stop the Bleeding
- Check if new transactions still getting stuck
- If yes: Stop accepting new payments (maintenance mode)
- If no: Old issue, safe to process backlog

Step 2: Analyze Why They're Stuck
SELECT status, COUNT(*) 
FROM transactions
WHERE status = 'PENDING'
  AND created_at < NOW() - INTERVAL '2 hours'
GROUP BY status;

Possible Reasons:
- NPCI callback didn't arrive
- Kafka consumer crashed (notifications not sent)
- Settlement service down

Step 3: Query NPCI Status API
for (Transaction txn : pendingTxns) {
    NPCIStatus status = npciClient.getStatus(txn.npciTxnId);
    
    if (status == SUCCESS) {
        // NPCI has it as success, our DB is stale
        txn.setStatus(SUCCESS);
        txn.update();
    } else if (status == FAILED) {
        txn.setStatus(FAILED);
        initiateReversal(txn);
    } else {
        // Still pending at NPCI, wait more
    }
}

Step 4: Batch Update
UPDATE transactions
SET status = 'SUCCESS',
    updated_at = NOW()
WHERE id IN (?, ?, ...); -- IDs confirmed with NPCI

Step 5: Replay Kafka Events
// For notifications that didn't go out
for (Transaction txn : recoveredTxns) {
    kafka.send("txn-success-topic", txn);
}

Step 6: Post-Mortem
- Why didn't our retry mechanism work?
- Was Kafka down?
- Was there a database lock?
```

---

### 5. **Database queries are slow. Transactions timing out. How do you optimize?**

**What This Tests**: SQL optimization, indexing, query analysis

**Answer**:
```sql
-- Step 1: Find Slow Queries
-- PostgreSQL
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Step 2: Analyze Query Plan
EXPLAIN ANALYZE
SELECT * FROM transactions
WHERE sender_account_id = 'ACC123'
  AND created_at > '2024-01-01';

-- If you see "Seq Scan" → BAD! (Full table scan)
-- If you see "Index Scan" → GOOD!

-- Step 3: Add Missing Index
CREATE INDEX CONCURRENTLY idx_sender_created
ON transactions(sender_account_id, created_at);

-- Step 4: Check for Table Bloat
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE tablename = 'transactions';

-- If table is huge → Partition it
CREATE TABLE transactions_2024_01 
PARTITION OF transactions
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Step 5: Check Lock Contention
SELECT blocked_locks.pid AS blocked_pid,
       blocking_locks.pid AS blocking_pid
FROM pg_locks blocked_locks
JOIN pg_locks blocking_locks 
  ON blocked_locks.locktype = blocking_locks.locktype
WHERE NOT blocked_locks.granted;

-- If many locks → Optimize transaction size

-- Step 6: Connection Pool Exhausted?
-- HikariCP settings
maximum-pool-size: 50
minimum-idle: 10
connection-timeout: 30000

-- If pool exhausted → Increase pool OR fix slow queries
```

**Real Production Story**:
```
We had a query:
SELECT * FROM transactions 
WHERE status = 'SUCCESS'
ORDER BY created_at DESC 
LIMIT 100;

10M rows → Took 5 seconds!

Added composite index:
CREATE INDEX idx_status_created 
ON transactions(status, created_at DESC);

Query now takes 20ms! 250x faster!
```

---

### 6. **You're processing 1M settlement records. Job takes 6 hours. How to optimize?**

**What This Tests**: Batch processing, parallel execution, optimization

**Answer**:
```java
// ❌ BAD: Sequential Processing (6 hours)
for (Transaction txn : allTransactions) {
    processSettlement(txn);
}

// ✅ GOOD: Parallel Processing (30 minutes)
ExecutorService executor = Executors.newFixedThreadPool(20);

List<Transaction> batch = fetchBatch(1000);
while (!batch.isEmpty()) {
    for (Transaction txn : batch) {
        executor.submit(() -> processSettlement(txn));
    }
    batch = fetchBatch(1000);
}

executor.shutdown();
executor.awaitTermination(1, TimeUnit.HOURS);

// ✅ BETTER: Kafka Streams (Real-time)
StreamsBuilder builder = new StreamsBuilder();
builder.stream("transactions-topic")
    .filter((key, txn) -> txn.status == SUCCESS)
    .mapValues(txn -> calculateSettlement(txn))
    .to("settlement-topic");

// ✅ BEST: Database-Level Aggregation
INSERT INTO daily_settlement (bank_id, total_amount, txn_count)
SELECT 
    bank_id,
    SUM(amount) as total_amount,
    COUNT(*) as txn_count
FROM transactions
WHERE created_at::date = CURRENT_DATE
  AND status = 'SUCCESS'
GROUP BY bank_id;

-- Processes 1M rows in 2 minutes!
```

**Optimization Checklist**:
- [ ] Use batch INSERT (1000 rows at once)
- [ ] Process in parallel (20 threads)
- [ ] Use database aggregation (not Java loops)
- [ ] Add indexes on filter columns
- [ ] Use prepared statements (not string concat)
- [ ] Disable auto-commit in batch mode

---

### 7. **How do you test 2-Phase Commit rollback without breaking production?**

**What This Tests**: Testing strategy, chaos engineering

**Answer**:
```
Testing Environments:

1. Unit Tests (Mock)
@Test
public void testRollbackWhenCreditFails() {
    // Mock NPCI
    when(npci.prepare(any())).thenReturn(PREPARED);
    when(npci.commit(any())).thenThrow(new NPCIException());
    
    // Execute
    Transaction result = paymentService.execute(txn);
    
    // Verify rollback happened
    assertEquals(FAILED, result.getStatus());
    verify(npci).rollback(txn.getId());
}

2. Integration Tests (Test NPCI)
// NPCI provides sandbox environment
@Test
public void testRealNPCIRollback() {
    // Use NPCI sandbox API
    npciClient.setEnvironment(SANDBOX);
    
    // Trigger failure scenario
    Transaction txn = new Transaction()
        .setAmount(-1); // Invalid amount
    
    Result result = paymentService.execute(txn);
    
    assertEquals(ROLLED_BACK, result.getStatus());
}

3. Staging Environment
// Dedicated leased line to NPCI test environment
// Full end-to-end test with:
- Real database
- Real Kafka
- Test NPCI endpoint

4. Production (Chaos Engineering)
// Gradually introduce failures

// Step 1: Shadow traffic (no real transactions)
if (txn.isTest()) {
    simulateNPCIFailure(txn);
}

// Step 2: Canary (1% traffic)
if (Math.random() < 0.01 && txn.amount < 10) {
    // Test rollback on tiny transactions
}

// Step 3: Monitor metrics
- Rollback success rate
- No money lost
- User notified correctly
```

**Real Testing Story**:
```
We found a bug in production:
- Debit succeeded
- Credit failed  
- Rollback API called
- But reversal entry was NOT created!

Users lost money for 2 hours until we noticed.

Now we have:
1. Synthetic transaction every 5 minutes
2. Monitors reversal table
3. Alerts if reversal missing after rollback
```

---

### 8. **Your Kubernetes pod keeps crashing with OOMKilled. How do you debug?**

**What This Tests**: Kubernetes, memory profiling, resource tuning

**Answer**:
```bash
# Step 1: Check Pod Status
kubectl get pods
# NAME                     STATUS      RESTARTS
# payment-service-abc123   OOMKilled   5

# Step 2: Check Resource Limits
kubectl describe pod payment-service-abc123
# Limits:
#   memory: 512Mi  ← Too low!
# Requests:
#   memory: 256Mi

# Step 3: Check Actual Memory Usage
kubectl top pod payment-service-abc123
# NAME                     CPU    MEMORY
# payment-service-abc123   200m   480Mi/512Mi  ← Using 94%!

# Step 4: Check Java Heap
kubectl logs payment-service-abc123 | grep -i "heap"
# OutOfMemoryError: Java heap space

# Step 5: Analyze Heap Dump
# Add to deployment:
env:
  - name: JAVA_OPTS
    value: "-Xmx400m -Xms400m -XX:+HeapDumpOnOutOfMemoryError"

# Download heap dump
kubectl cp payment-service-abc123:/app/heapdump.hprof ./heapdump.hprof

# Analyze with Eclipse MAT or VisualVM
# Found: Caching entire transaction history in memory!

# Step 6: Fix Code
// ❌ BAD
private Map<String, Transaction> cache = new HashMap<>();
// Grows unbounded!

// ✅ GOOD  
private LoadingCache<String, Transaction> cache = 
    Caffeine.newBuilder()
        .maximumSize(10_000)
        .expireAfterWrite(10, TimeUnit.MINUTES)
        .build(key -> loadFromDB(key));

# Step 7: Increase Resource Limits
resources:
  limits:
    memory: 1Gi  ← 2x previous
  requests:
    memory: 512Mi
```

---

### 9. **NPCI sent duplicate callback. User charged twice. How to prevent?**

**What This Tests**: Idempotency implementation, race conditions

**Answer**:
```java
// ❌ BAD (Allows duplicates)
@PostMapping("/npci/callback")
public void handleCallback(@RequestBody NPCICallback callback) {
    Transaction txn = findById(callback.getTxnId());
    txn.setStatus(SUCCESS);
    txn.save();
    
    // If called twice → User charged twice!
}

// ✅ GOOD (Idempotent)
@PostMapping("/npci/callback")
public void handleCallback(@RequestBody NPCICallback callback) {
    String idempotencyKey = callback.getNpciTxnId();
    
    // Atomic check-and-set
    Boolean isFirstTime = redis.setNX(
        "callback:" + idempotencyKey, 
        "PROCESSING",
        Duration.ofMinutes(5)
    );
    
    if (!isFirstTime) {
        log.warn("Duplicate callback ignored: {}", idempotencyKey);
        return; // Ignore duplicate
    }
    
    try {
        Transaction txn = findById(callback.getTxnId());
        
        // Check current status
        if (txn.getStatus() == SUCCESS) {
            log.warn("Transaction already successful");
            return;
        }
        
        // Update only if still pending
        int rowsUpdated = database.execute(
            "UPDATE transactions " +
            "SET status = 'SUCCESS' " +
            "WHERE id = ? AND status = 'PENDING'",
            txn.getId()
        );
        
        if (rowsUpdated == 0) {
            log.warn("Transaction already processed");
            return;
        }
        
        // Send notification
        kafka.send("txn-success", txn);
        
    } finally {
        redis.set("callback:" + idempotencyKey, "DONE");
    }
}

// Database-level constraint
ALTER TABLE transactions 
ADD CONSTRAINT unique_npci_txn 
UNIQUE (npci_transaction_id);

// If duplicate → constraint violation → rollback
```

**Real Production Bug**:
```
NPCI sent callback twice within 100ms
→ Both requests passed Redis check
→ Both updated database
→ User got 2 notifications
→ Balance deducted twice

Fix: Added database unique constraint + 
      Optimistic locking (version column)
```

---

### 10. **How do you handle a situation where 1000 transactions are stuck due to database deadlock?**

**What This Tests**: Deadlock understanding, resolution, prevention

**Answer**:
```sql
-- Step 1: Detect Deadlock
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.query AS blocked_query,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.query AS blocking_query
FROM pg_locks blocked_locks
JOIN pg_stat_activity blocked_activity ON blocked_locks.pid = blocked_activity.pid
JOIN pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
JOIN pg_stat_activity blocking_activity ON blocking_locks.pid = blocking_activity.pid
WHERE NOT blocked_locks.granted;

-- Step 2: Kill Blocking Query (Emergency)
SELECT pg_terminate_backend(blocking_pid);

-- Step 3: Analyze Why Deadlock Happened

-- Common Cause: Different Lock Order
-- Transaction A:
UPDATE accounts SET balance = balance - 100 WHERE id = 1;
UPDATE accounts SET balance = balance + 100 WHERE id = 2;

-- Transaction B (Reverse order):
UPDATE accounts SET balance = balance - 50 WHERE id = 2;
UPDATE accounts SET balance = balance + 50 WHERE id = 1;

-- DEADLOCK! A holds lock on 1, wants 2
--           B holds lock on 2, wants 1

-- Step 4: Fix Code (Consistent Lock Order)
public void transfer(String from, String to, BigDecimal amount) {
    // Always lock accounts in ascending ID order
    String first = from.compareTo(to) < 0 ? from : to;
    String second = from.compareTo(to) < 0 ? to : from;
    
    lockAccount(first);
    lockAccount(second);
    
    // Now do the transfer
    debit(from, amount);
    credit(to, amount);
}

-- Step 5: Retry Logic
@Retry(
    maxAttempts = 3,
    backoff = @Backoff(delay = 100),
    include = DeadlockLoserDataAccessException.class
)
public void executeTransaction(Transaction txn) {
    // If deadlock → Retry automatically
}

-- Step 6: Reduce Lock Duration
// ❌ BAD (Long lock)
BEGIN;
  SELECT * FROM accounts WHERE id = 1 FOR UPDATE;
  doExpensiveCalculation(); // Holds lock for 5 seconds!
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;
COMMIT;

// ✅ GOOD (Short lock)
BigDecimal newBalance = doExpensiveCalculation();
BEGIN;
  UPDATE accounts SET balance = newBalance WHERE id = 1;
COMMIT; // Lock held for 10ms only
```

**Prevention Checklist**:
- [ ] Always lock resources in same order (alphabetical ID)
- [ ] Keep transactions short (<100ms)
- [ ] Use optimistic locking (version column) where possible
- [ ] Set `lock_timeout = '5s'` in PostgreSQL
- [ ] Monitor deadlock rate: `pg_stat_database.deadlocks`

---

## 🎯 **Interview Priority Order:**

**Must explain (Top 5):**
1. Why NPCI as central hub?
2. PSP vs Bank PSP difference
3. Master-Replica database split
4. Kafka for async processing
5. Rate limiting mechanism

**Very likely (Next 5):**
6. PostgreSQL vs MongoDB choice
7. Circuit breaker pattern
8. Hash-based sharding
9. JWT validation
10. Service mesh purpose

**Moderate chance (Next 5):**
11. HPA autoscaling
12. Synchronous vs async replication
13. NPCI Adapter role
14. Settlement service separation
15. Liveness vs readiness probes

**Good to know (Remaining):**
16-25. All other questions

---

## 📝 **Interview Strategy:**

**If asked about architecture:**
1. Start with high-level diagram (5 layers)
2. Explain NPCI's role
3. Dive into one layer (say Microservices)
4. Explain trade-offs (SQL vs NoSQL)

**If asked about scalability:**
1. Database sharding
2. Read replicas
3. Kafka partitions
4. Kubernetes HPA

**If asked about reliability:**
1. Circuit breaker
2. Retry mechanisms
3. Multi-AZ deployment
4. Health checks

Good luck! 🚀
