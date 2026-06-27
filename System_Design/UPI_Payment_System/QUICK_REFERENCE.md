# Quick Reference - UPI System Design Cheat Sheet

## 📋 30-Second Elevator Pitch

UPI is India's real-time payment system enabling instant money transfers between bank accounts using Virtual Payment Addresses (VPAs). It handles **50K TPS** with **<3s latency** and **99.99% availability** using a microservices architecture, 2-Phase Commit for distributed transactions, and strong consistency guarantees.

---

## 🎯 Key Numbers to Remember

| Metric | Value |
|--------|-------|
| Users | 500 million |
| Daily Transactions | 200 million |
| Peak TPS | 50,000 |
| Latency (p95) | <3 seconds |
| Availability | 99.99% |
| Storage/Year | 150 TB |
| Transaction Limit | ₹1,00,000 |
| MPIN Attempts | 3 |
| Rate Limit | 10 payments/min |
| Idempotency TTL | 24 hours |
| Cache TTL (VPA) | 1 hour |

---

## 🏗️ Architecture Layers (Top to Bottom)

```
1. CLIENT LAYER
   └─ Mobile Apps (PhonePe, GPay, Paytm)

2. EDGE LAYER
   └─ CDN → WAF → API Gateway

3. LOAD BALANCING
   └─ AWS ALB (Round Robin + Health Checks)

4. SERVICE LAYER (Microservices)
   ├─ Payment Service
   ├─ User Service
   ├─ VPA Resolution Service
   ├─ Auth Service
   ├─ Fraud Detection Service
   ├─ Notification Service
   └─ Settlement Service

5. DATA LAYER
   ├─ PostgreSQL (Master + Read Replicas)
   ├─ Redis Cluster (Cache)
   ├─ MongoDB (Logs)
   └─ Kafka (Events)

6. EXTERNAL INTEGRATION
   ├─ NPCI Switch
   └─ Bank Core Systems
```

---

## 💡 Core Concepts in One Line Each

| Concept | One-Liner |
|---------|-----------|
| **VPA** | Virtual address like `user@bank` that maps to account number |
| **NPCI** | Central switch that routes UPI transactions between banks |
| **2PC** | Protocol ensuring atomicity: both banks commit or both rollback |
| **Idempotency** | Same request repeated = same response, no duplicate charges |
| **Circuit Breaker** | Stop calling failing service, try again after cooldown |
| **Sharding** | Split data across servers by user_id hash |
| **CAP Theorem** | UPI chooses CP (Consistency + Partition tolerance) over Availability |
| **MDR** | Merchant Discount Rate (0% for P2M in India, govt subsidized) |

---

## 🔄 Transaction Flow (8 Steps)

```
1. INITIATE → User enters receiver VPA, amount, MPIN
2. VALIDATE → Check VPA exists, MPIN correct, fraud score
3. PREPARE → NPCI asks both banks "Ready?" (2PC Phase 1)
4. DEBIT → Sender bank locks ₹500
5. CREDIT → Receiver bank validates account
6. COMMIT → NPCI says "Go!" (2PC Phase 2)
7. SUCCESS → Money moved, status updated
8. NOTIFY → SMS/Push to both users
```

**Timeline**: 2-3 seconds  
**States**: INITIATED → VALIDATING → PENDING → PREPARED → DEBITED → CREDITED → SUCCESS

---

## 🗄️ Database Quick Reference

### Tables
- **users**: User profile, KYC status
- **upi_handles**: VPA to user mapping
- **bank_accounts**: Account details
- **transactions**: Payment records
- **transaction_log**: Audit trail
- **settlement**: Bank-to-bank reconciliation

### Key Indexes
```sql
-- Most important indexes
idx_sender: (sender_account_id, created_at)
idx_receiver: (receiver_account_id, created_at)
idx_npci: (npci_transaction_id) UNIQUE
idx_vpa: (vpa) UNIQUE
```

### Sharding Strategy
- **Shard by**: `user_id` (hash-based)
- **Shards**: 64 initially, expandable to 256
- **Why**: User's data stays together

### Partitioning
- **By**: `created_at` (monthly)
- **Hot data**: Current month on SSD
- **Cold data**: Older months on HDD, compressed

---

## 🔐 Security Checklist

✅ **Encryption**
- TLS 1.3 for all communication
- MPIN encrypted client-side (AES-256)
- Database TDE (Transparent Data Encryption)

✅ **Authentication**
- JWT tokens (30 min expiry)
- Device binding
- MPIN (4-6 digits, 3 attempts)
- OTP for sensitive operations

✅ **Authorization**
- RBAC (Role-Based Access Control)
- Transaction limits per user
- Daily/monthly caps

✅ **Compliance**
- PCI-DSS Level 1
- RBI guidelines
- Data localization (India)
- 10-year data retention

---

## 🎨 Design Patterns Used

| Pattern | Where | Why |
|---------|-------|-----|
| **Circuit Breaker** | NPCI adapter | Prevent cascading failures |
| **Retry with Exponential Backoff** | Transaction execution | Handle transient errors |
| **Idempotency** | Payment API | Safe retries |
| **Event Sourcing** | Transaction log | Audit trail, replay |
| **CQRS** | Transaction queries | Separate read/write paths |
| **Saga Pattern** | Reversal flow | Distributed rollback |
| **Rate Limiting** | API Gateway | Prevent abuse |
| **Cache-Aside** | VPA resolution | Reduce DB load |

---

## 🚨 Failure Scenarios & Solutions

| Failure | Impact | Solution |
|---------|--------|----------|
| **NPCI down** | All txns fail | Circuit breaker, show error, fallback to IMPS |
| **Debit success, credit fails** | Money stuck | Auto-reversal within 1 hour |
| **Network partition** | Split brain | Choose consistency, reject writes |
| **Database master down** | Write failures | Promote replica to master (30s) |
| **Redis down** | Slower queries | Fallback to DB, cache warm-up |
| **Kafka down** | No notifications | Retry queue, manual reconciliation |

---

## 📊 Monitoring Metrics

**Golden Signals**:
1. **Latency**: p50, p95, p99 transaction time
2. **Traffic**: Requests per second
3. **Errors**: Error rate, failed transactions
4. **Saturation**: CPU, memory, DB connections

**Business Metrics**:
- Transaction success rate (target: >99.5%)
- Reversal rate (target: <0.1%)
- Fraud detection rate
- Average transaction value
- User churn rate

**Alerts**:
- Transaction success rate < 98% → Page oncall
- p95 latency > 5s → Warning
- Circuit breaker open → Critical
- Reversal pending > 1 hour → Manual intervention

---

## 🔍 Interview Red Flags

### ❌ Don't Say This
- "We can use eventual consistency" (Financial data needs strong consistency)
- "NoSQL for everything" (ACID properties needed)
- "We'll handle failures later" (Failure handling is core requirement)
- "Ignore security" (PCI-DSS compliance mandatory)

### ✅ Say This Instead
- "Strong consistency using 2PC"
- "PostgreSQL for transactions, Redis for cache"
- "Reversal mechanism for partial failures"
- "Multi-layered security: TLS, MPIN, fraud detection"

---

## 📝 Code Snippets to Memorize

### Idempotency Check
```java
Optional<Transaction> existing = cache.get(idempotencyKey);
if (existing.isPresent()) {
    return existing.get(); // Return cached response
}
```

### Row-Level Locking (Double-Spend Prevention)
```sql
SELECT balance FROM accounts 
WHERE account_id = ? 
FOR UPDATE;  -- Locks row until transaction commits
```

### Circuit Breaker
```java
@CircuitBreaker(failureThreshold=5, resetTimeout=30000)
public Response callNPCI(Transaction txn) { ... }
```

### Rate Limiting
```java
String key = "rate:" + userId;
long count = redis.incr(key);
if (count == 1) redis.expire(key, 60); // 60 seconds
if (count > 10) throw new RateLimitException();
```

---

## 🎯 Interview Strategy

### First 5 Minutes (Requirements)
**Ask these questions**:
1. What's the expected scale? (Users, TPS)
2. Which features to prioritize? (P2P, P2M, QR)
3. Availability vs Consistency? (Choose CP)
4. Latency requirements? (<3s)
5. Geographic scope? (India only)

### Draw This Architecture (7 minutes)
```
┌────────┐
│  Apps  │
└───┬────┘
    ↓
┌────────────┐
│API Gateway │
└───┬────────┘
    ↓
┌────────────────────────────┐
│  Payment  │ Auth │ Fraud   │ (Microservices)
└─────┬──────┴──────┴─────┬──┘
      ↓                    ↓
┌──────────┐         ┌──────────┐
│PostgreSQL│         │  Redis   │
└──────────┘         └──────────┘
      ↓
┌──────────┐
│   NPCI   │
└──────────┘
```

### Deep Dive Topics (Choose 2-3)
1. **2-Phase Commit** (Always explain this)
2. **Database sharding** (Scalability focus)
3. **Idempotency** (Reliability focus)
4. **Fraud detection** (Security focus)

---

## 📚 Must-Know Terminology

- **VPA**: Virtual Payment Address (user@bank)
- **PSP**: Payment Service Provider (app like PhonePe)
- **NPCI**: National Payments Corporation of India
- **IMPS**: Immediate Payment Service (fallback)
- **MPIN**: Mobile PIN (4-6 digit password)
- **2PC**: Two-Phase Commit (distributed transaction)
- **MDR**: Merchant Discount Rate (transaction fee)
- **QR**: Quick Response code (for payments)
- **KYC**: Know Your Customer (identity verification)
- **AML**: Anti-Money Laundering

---

## ⏱️ Time Allocation

**45-minute HLD Interview**:
- 5 min: Requirements & scale
- 10 min: Architecture diagram
- 15 min: Deep dive (2PC + DB)
- 10 min: Edge cases & failures
- 5 min: Q&A

**45-minute LLD Interview**:
- 5 min: Scope clarification
- 15 min: Class diagram
- 20 min: Implement 2-3 methods
- 5 min: Testing & complexity

---

## 🚀 Pro Tips

1. **Start with the happy path**, then add failure handling
2. **Draw diagrams** - Visuals > Verbal explanations
3. **Think aloud** - Interviewer wants to see your process
4. **Ask clarifying questions** - Shows you're thorough
5. **Discuss trade-offs** - No perfect solution exists
6. **Use real numbers** - "50K TPS" beats "high traffic"
7. **Reference real systems** - "Similar to how Stripe handles..."
8. **Admit unknowns** - "I'd research X before deciding"

---

## 📖 Final Checklist Before Interview

- [ ] Can draw architecture in 5 minutes
- [ ] Can explain 2PC protocol
- [ ] Know CAP theorem choice (CP)
- [ ] Can design transaction schema
- [ ] Understand idempotency
- [ ] Can explain sharding strategy
- [ ] Know how to handle partial failures
- [ ] Can discuss fraud detection
- [ ] Understand rate limiting
- [ ] Know settlement process basics

**You're ready! 💪**
