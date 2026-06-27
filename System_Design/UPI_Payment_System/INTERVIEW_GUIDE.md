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

## Common Interview Questions & Answers

### Q1: How does UPI ensure atomicity across two different banks?

**Answer**: UPI uses **Two-Phase Commit (2PC) protocol** coordinated by NPCI:

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
