# Payment Gateway System Design

**Interview frequency:** 65-70% (Very common for fintech, e-commerce roles)
**Study time:** 15-20 minutes

## Problem Statement

Design a payment gateway system that handles millions of transactions daily with high reliability, security, and consistency. The system should support multiple payment methods, handle failures gracefully, and ensure no duplicate charges or lost payments.

---

## 1. Requirements

### Functional Requirements
- **Process payments** from multiple payment methods (credit cards, debit cards, UPI, wallets)
- **Handle refunds and cancellations**
- **Transaction status tracking** (pending, success, failed)
- **Support multiple currencies**
- **Webhook notifications** to merchant systems
- **Payment reconciliation** with banks/payment processors
- **Retry mechanism** for failed transactions

### Non-Functional Requirements
- **High availability** (99.99% uptime)
- **Strong consistency** for money transfers (ACID properties)
- **Low latency** (<500ms for payment processing)
- **Security & Compliance** (PCI-DSS, encryption, fraud detection)
- **Idempotency** (no duplicate charges)
- **Audit trail** for all transactions
- **Scalability** to handle 10K+ TPS

---

## 2. High-Level Architecture

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │
       │ HTTPS
       ▼
┌─────────────────────────────────────────┐
│         API Gateway / Load Balancer      │
│     (Rate Limiting, SSL Termination)     │
└──────────────────┬──────────────────────┘
                   │
       ┌───────────┴───────────┐
       │                       │
       ▼                       ▼
┌─────────────┐         ┌─────────────┐
│  Payment    │         │  Webhook    │
│  Service    │         │  Service    │
└──────┬──────┘         └──────┬──────┘
       │                       │
       │                       │
       ▼                       ▼
┌─────────────────────────────────────────┐
│         Message Queue (Kafka)           │
│    (Transaction Events, Webhooks)       │
└──────────────────┬──────────────────────┘
                   │
       ┌───────────┼───────────┬─────────┐
       │           │           │         │
       ▼           ▼           ▼         ▼
┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
│ Payment  │ │  Fraud   │ │ Ledger  │ │ Notif.   │
│ Processor│ │ Detection│ │ Service │ │ Service  │
└────┬─────┘ └────┬─────┘ └────┬────┘ └────┬─────┘
     │            │            │           │
     │            │            │           │
     ▼            ▼            ▼           ▼
┌──────────────────────────────────────────────┐
│              Databases                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Payment  │  │  Ledger  │  │  Audit   │  │
│  │   DB     │  │    DB    │  │   Log    │  │
│  │(Postgres)│  │(Postgres)│  │(Cassandra)│  │
│  └──────────┘  └──────────┘  └──────────┘  │
└──────────────────────────────────────────────┘
     │
     │ External API Calls
     ▼
┌──────────────────────────────────────────────┐
│       External Payment Processors             │
│   (Stripe, Razorpay, PayPal, Bank APIs)      │
└──────────────────────────────────────────────┘
```

---

## 3. Core Components

### 3.1 Payment Service
**Responsibilities:**
- Payment request validation
- Idempotency key management
- Route to appropriate payment processor
- Handle retries with exponential backoff
- Transaction state management

**Key Design:**
```java
public class PaymentService {
    
    @Transactional
    public PaymentResponse processPayment(PaymentRequest request) {
        // 1. Validate idempotency key (prevent duplicate charges)
        if (isDuplicateRequest(request.getIdempotencyKey())) {
            return getCachedResponse(request.getIdempotencyKey());
        }
        
        // 2. Create transaction record (PENDING state)
        Transaction txn = createTransaction(request);
        
        // 3. Fraud detection check
        if (!fraudDetectionService.verify(request)) {
            txn.setStatus(REJECTED);
            return new PaymentResponse(REJECTED, "Fraud detected");
        }
        
        // 4. Call external payment processor
        try {
            ProcessorResponse response = paymentProcessor.charge(request);
            txn.setStatus(response.isSuccess() ? SUCCESS : FAILED);
            
            // 5. Update ledger (double-entry bookkeeping)
            ledgerService.recordTransaction(txn);
            
            // 6. Publish event to Kafka
            kafkaProducer.send(new PaymentEvent(txn));
            
            // 7. Cache response for idempotency
            cacheResponse(request.getIdempotencyKey(), response);
            
            return new PaymentResponse(txn.getStatus());
            
        } catch (TimeoutException | NetworkException e) {
            // Mark as PENDING for async retry
            txn.setStatus(PENDING);
            retryQueue.enqueue(txn.getId());
            return new PaymentResponse(PENDING, "Processing");
        }
    }
}
```

### 3.2 Idempotency Mechanism
**Problem:** Network failures can cause duplicate payment requests.

**Solution:**
```java
// Client generates idempotency key
String idempotencyKey = UUID.randomUUID().toString();

// Store in Redis with TTL (24 hours)
@Cacheable(key = "#idempotencyKey", ttl = 86400)
public PaymentResponse getCachedResponse(String idempotencyKey) {
    return redisCache.get(idempotencyKey);
}

// Database unique constraint
CREATE UNIQUE INDEX idx_idempotency 
ON payments(idempotency_key, merchant_id);
```

### 3.3 Ledger Service (Double-Entry Bookkeeping)
**Why:** Ensures money conservation (debits = credits).

**Schema:**
```sql
CREATE TABLE ledger_entries (
    id BIGSERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL,
    account_id VARCHAR(100) NOT NULL,
    entry_type ENUM('DEBIT', 'CREDIT') NOT NULL,
    amount DECIMAL(19, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    balance_after DECIMAL(19, 4) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- Audit fields
    created_by VARCHAR(100),
    metadata JSONB
);

-- Example: Customer pays $100 to Merchant
-- Entry 1: DEBIT customer account $100
-- Entry 2: CREDIT merchant account $100
```

**Reconciliation:**
```sql
-- Daily reconciliation query
SELECT DATE(created_at) as date,
       SUM(CASE WHEN entry_type = 'DEBIT' THEN amount ELSE 0 END) as total_debits,
       SUM(CASE WHEN entry_type = 'CREDIT' THEN amount ELSE 0 END) as total_credits
FROM ledger_entries
GROUP BY DATE(created_at)
HAVING total_debits != total_credits; -- Alert if mismatch
```

### 3.4 Fraud Detection Service
**Real-time checks:**
- **Velocity checks:** Max transactions per user per hour
- **Geolocation anomaly:** Payment from unusual location
- **Device fingerprinting:** Suspicious device patterns
- **ML models:** Anomaly detection based on historical patterns

**Implementation:**
```java
public class FraudDetectionService {
    
    public boolean verify(PaymentRequest request) {
        // 1. Velocity check (Redis counter)
        int recentTxnCount = redisCounter.increment(
            "txn_count:" + request.getUserId(), 
            3600 // 1 hour TTL
        );
        if (recentTxnCount > MAX_TXN_PER_HOUR) {
            return false;
        }
        
        // 2. Geolocation check
        if (isLocationAnomalous(request.getUserId(), request.getIpAddress())) {
            return false;
        }
        
        // 3. ML model prediction
        double fraudScore = mlModel.predict(request);
        return fraudScore < FRAUD_THRESHOLD;
    }
}
```

### 3.5 Retry Mechanism
**Pattern:** Exponential backoff with jitter

```java
public class PaymentRetryService {
    
    private static final int MAX_RETRIES = 3;
    private static final int BASE_DELAY_MS = 1000;
    
    @Scheduled(fixedDelay = 5000)
    public void retryPendingPayments() {
        List<Transaction> pending = transactionRepo.findPending();
        
        for (Transaction txn : pending) {
            if (txn.getRetryCount() >= MAX_RETRIES) {
                txn.setStatus(FAILED);
                notifyMerchant(txn);
                continue;
            }
            
            // Exponential backoff: 1s, 2s, 4s, 8s...
            long delayMs = BASE_DELAY_MS * (long) Math.pow(2, txn.getRetryCount());
            
            // Add jitter to prevent thundering herd
            delayMs += ThreadLocalRandom.current().nextLong(0, 1000);
            
            if (System.currentTimeMillis() - txn.getLastRetryAt() > delayMs) {
                retryPayment(txn);
                txn.incrementRetryCount();
            }
        }
    }
}
```

---

## 4. Database Design

### Payment Transaction Table
```sql
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id VARCHAR(100) NOT NULL,
    customer_id VARCHAR(100) NOT NULL,
    idempotency_key VARCHAR(100) NOT NULL,
    amount DECIMAL(19, 4) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL, -- PENDING, SUCCESS, FAILED, REFUNDED
    payment_method VARCHAR(50), -- CARD, UPI, WALLET
    processor VARCHAR(50), -- STRIPE, RAZORPAY
    processor_txn_id VARCHAR(200),
    
    -- Retry metadata
    retry_count INT DEFAULT 0,
    last_retry_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Indexes
    CONSTRAINT unique_idempotency UNIQUE (merchant_id, idempotency_key),
    INDEX idx_merchant_created (merchant_id, created_at),
    INDEX idx_status (status)
);
```

### Refund Table
```sql
CREATE TABLE refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL REFERENCES payments(id),
    amount DECIMAL(19, 4) NOT NULL,
    reason TEXT,
    status VARCHAR(20) NOT NULL,
    processor_refund_id VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_payment (payment_id)
);
```

---

## 5. Key Design Decisions

### 5.1 Consistency vs Availability

**Choice: Strong Consistency (CP in CAP theorem)**

**Why:**
- Financial transactions require ACID guarantees
- Better to be temporarily unavailable than to have inconsistent money
- Use distributed transactions (Saga pattern) for cross-service coordination

### 5.2 Saga Pattern for Distributed Transactions

**Scenario:** Payment involves multiple services (Payment → Ledger → Notification)

**Orchestration-based Saga:**
```java
public class PaymentOrchestrator {
    
    public void executePaymentSaga(PaymentRequest request) {
        Transaction txn = null;
        try {
            // Step 1: Create payment record
            txn = paymentService.createTransaction(request);
            
            // Step 2: Charge external processor
            ProcessorResponse response = paymentProcessor.charge(request);
            
            // Step 3: Update ledger
            ledgerService.recordTransaction(txn);
            
            // Step 4: Send notification
            notificationService.notify(txn);
            
            txn.setStatus(SUCCESS);
            
        } catch (Exception e) {
            // Compensating transactions (rollback)
            if (txn != null) {
                paymentProcessor.refund(txn.getProcessorTxnId());
                ledgerService.reverseTransaction(txn);
                txn.setStatus(FAILED);
            }
        }
    }
}
```

### 5.3 Database Sharding Strategy

**Sharding Key:** `merchant_id`

**Why:**
- Queries are mostly merchant-specific
- Avoids cross-shard joins
- Easy horizontal scaling

**Schema:**
```
Shard 1: merchant_id % 4 == 0
Shard 2: merchant_id % 4 == 1
Shard 3: merchant_id % 4 == 2
Shard 4: merchant_id % 4 == 3
```

### 5.4 Caching Strategy

**Redis Cache Layers:**
```java
// 1. Idempotency cache (TTL: 24 hours)
redis.setex("idempotency:" + key, 86400, response);

// 2. Merchant config cache (TTL: 1 hour)
redis.setex("merchant:" + merchantId, 3600, config);

// 3. Fraud velocity counters (TTL: 1 hour)
redis.incr("txn_count:" + userId, 3600);
```

---

## 6. Security & Compliance

### 6.1 PCI-DSS Compliance
- **Never store full card numbers** (use tokens from payment processors)
- **Encrypt sensitive data** at rest and in transit (TLS 1.3)
- **Tokenization:** Replace card data with tokens
- **PCI-SAQ validation** annually

### 6.2 Encryption
```java
// At rest: AES-256 encryption for sensitive fields
@Encrypted
@Column(name = "card_last_four")
private String cardLastFour;

// In transit: TLS 1.3 for all API calls
RestTemplate restTemplate = new RestTemplate(
    new HttpComponentsClientHttpRequestFactory(
        HttpClients.custom()
            .setSSLContext(SSLContexts.custom()
                .setProtocol("TLSv1.3")
                .build())
            .build()
    )
);
```

### 6.3 Rate Limiting
```java
// Per merchant: 1000 requests/minute
@RateLimiter(key = "#merchantId", limit = 1000, window = 60)
public PaymentResponse processPayment(String merchantId, PaymentRequest req) {
    // ...
}

// Implement using Redis or API Gateway (Kong, AWS API Gateway)
```

---

## 7. Monitoring & Observability

### Key Metrics
```java
// Prometheus metrics
@Timed(value = "payment.process.time")
@Counted(value = "payment.process.count")
public PaymentResponse processPayment(PaymentRequest request) {
    // ...
}

// Grafana dashboards
- Payment success rate (target: >99.5%)
- P99 latency (target: <500ms)
- Failed payment reasons (categorized)
- Fraud detection accuracy
- Retry queue depth
- Ledger reconciliation status
```

### Alerting
```yaml
# Alert rules
- name: payment_failure_rate
  condition: (failed_payments / total_payments) > 0.01
  for: 5m
  action: page_oncall

- name: ledger_mismatch
  condition: abs(total_debits - total_credits) > 0
  for: 1m
  action: critical_alert
```

---

## 8. Scalability Considerations

### Horizontal Scaling
```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-service
spec:
  replicas: 10 # Auto-scale based on CPU/Memory
  template:
    spec:
      containers:
      - name: payment-service
        image: payment-service:v1
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
```

### Database Connection Pooling
```java
// HikariCP configuration
hikari.maximumPoolSize=50
hikari.minimumIdle=10
hikari.connectionTimeout=30000
hikari.idleTimeout=600000
hikari.maxLifetime=1800000
```

### Kafka Partitioning
```java
// Partition by merchant_id for ordered processing
ProducerRecord<String, PaymentEvent> record = 
    new ProducerRecord<>(
        "payment-events", 
        event.getMerchantId(), // partition key
        event
    );
```

---

## 9. Failure Scenarios & Mitigation

| Failure | Impact | Mitigation |
|---------|--------|-----------|
| **External processor timeout** | Payment stuck in PENDING | Async retry with exponential backoff |
| **Database failure** | Cannot record transaction | Use master-slave replication, failover to replica |
| **Duplicate payment request** | Customer charged twice | Idempotency keys + unique DB constraint |
| **Ledger imbalance** | Money lost/gained | Daily reconciliation + alerts on mismatch |
| **Network split** | Cross-region inconsistency | Use distributed consensus (Raft/Paxos) or eventual consistency |
| **DDoS attack** | Service unavailable | Rate limiting, WAF, CDN (Cloudflare) |
| **Fraud attack** | Unauthorized payments | ML-based fraud detection, 3DS authentication |

---

## 10. Interview Discussion Points

### Tradeoffs
1. **Sync vs Async Processing:**
   - Sync: Lower latency, better UX
   - Async: Higher throughput, better resilience

2. **Strong vs Eventual Consistency:**
   - Strong: ACID guarantees (for money)
   - Eventual: Higher availability (for analytics)

3. **Database Choice:**
   - Relational (Postgres): ACID, complex queries
   - NoSQL (Cassandra): High write throughput, eventual consistency

### Follow-up Questions
- **"How do you handle refunds?"** → Reverse ledger entries, call processor refund API
- **"How do you prevent double-charging?"** → Idempotency keys
- **"How do you scale to 100K TPS?"** → Sharding, caching, async processing
- **"How do you ensure money is never lost?"** → Ledger reconciliation, audit logs
- **"How do you handle multi-currency?"** → Store amounts in smallest unit (cents), convert at display time

---

## 11. Code Example: End-to-End Payment Flow

```java
@RestController
@RequestMapping("/api/v1/payments")
public class PaymentController {
    
    @Autowired
    private PaymentService paymentService;
    
    @PostMapping
    public ResponseEntity<PaymentResponse> processPayment(
        @RequestHeader("Idempotency-Key") String idempotencyKey,
        @RequestBody PaymentRequest request
    ) {
        request.setIdempotencyKey(idempotencyKey);
        
        PaymentResponse response = paymentService.processPayment(request);
        
        HttpStatus status = response.getStatus() == SUCCESS 
            ? HttpStatus.OK 
            : HttpStatus.ACCEPTED; // For PENDING status
        
        return ResponseEntity.status(status).body(response);
    }
    
    @PostMapping("/{paymentId}/refund")
    public ResponseEntity<RefundResponse> refundPayment(
        @PathVariable String paymentId,
        @RequestBody RefundRequest request
    ) {
        RefundResponse response = paymentService.refundPayment(paymentId, request);
        return ResponseEntity.ok(response);
    }
    
    @GetMapping("/{paymentId}")
    public ResponseEntity<Payment> getPayment(@PathVariable String paymentId) {
        Payment payment = paymentService.getPayment(paymentId);
        return ResponseEntity.ok(payment);
    }
}
```

---

## Summary

**Key Takeaways:**
1. **Idempotency** prevents duplicate charges
2. **Double-entry bookkeeping** ensures money conservation
3. **Saga pattern** handles distributed transactions
4. **Strong consistency** over availability for financial data
5. **Fraud detection** is critical for security
6. **Retry with exponential backoff** handles transient failures
7. **Audit logs** for compliance and debugging

**Study time:** 15-20 minutes
**Interview frequency:** 65-70% (fintech/e-commerce roles)
