# Payment System - Scenario-Based Interview Questions

**Study Time:** 20-25 minutes  
**Interview Frequency:** 70-80% (Critical for payment system roles)

---

## Part 1: Sequence & Timing Questions

### Q1: When do Account Balances get updated vs Ledger Entries?

**Scenario:**
```
User pays $100 to merchant for order_123
```

**Answer: Two Design Approaches**

#### **Approach 1: Accounts Table EXISTS (Materialized View)**

```sql
-- Step 1: Insert ledger entries (source of truth)
BEGIN TRANSACTION;

INSERT INTO ledger_entries VALUES
  (uuid1, 'txn_001', 'customer_123', 'DEBIT',  100.00, 'PAYMENT', 'order_123', NOW()),
  (uuid2, 'txn_001', 'merchant_456', 'CREDIT', 100.00, 'PAYMENT', 'order_123', NOW());

-- Step 2: Update accounts table (derived/cached balance)
UPDATE accounts 
SET balance = balance - 100.00, updated_at = NOW() 
WHERE account_id = 'customer_123';

UPDATE accounts 
SET balance = balance + 100.00, updated_at = NOW() 
WHERE account_id = 'merchant_456';

COMMIT;
```

**Why this order?**
- ✅ Ledger entries are **source of truth** (immutable audit trail)
- ✅ Accounts table is **performance optimization** (avoid SUM queries)
- ✅ If UPDATE fails, ROLLBACK entire transaction → consistency maintained
- ✅ Can **rebuild accounts table** from ledger_entries if corrupted

**Database Design:**
```sql
CREATE TABLE accounts (
    account_id VARCHAR(100) PRIMARY KEY,
    account_type VARCHAR(50), -- CUSTOMER, MERCHANT, PLATFORM
    balance DECIMAL(19, 4) NOT NULL DEFAULT 0,
    currency VARCHAR(3),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

#### **Approach 2: No Accounts Table (Pure Ledger Design)**

```sql
-- Only insert ledger entries
INSERT INTO ledger_entries VALUES
  (uuid1, 'txn_001', 'customer_123', 'DEBIT',  100.00, 'PAYMENT', 'order_123', NOW()),
  (uuid2, 'txn_001', 'merchant_456', 'CREDIT', 100.00, 'PAYMENT', 'order_123', NOW());

-- Balance calculated on-demand
SELECT account_id,
       SUM(CASE WHEN side = 'CREDIT' THEN amount ELSE 0 END) -
       SUM(CASE WHEN side = 'DEBIT'  THEN amount ELSE 0 END) AS balance
FROM ledger_entries
WHERE account_id = 'merchant_456'
GROUP BY account_id;
```

**Pros:**
- ✅ Single source of truth (no sync issues)
- ✅ Simpler (no dual-write complexity)

**Cons:**
- ❌ Slower balance queries (requires SUM aggregation)
- ❌ Solution: Use **indexed view** or **periodic cache rebuild**

---

### Q2: When does WebhookEvent data get inserted?

**Scenario Timeline:**

```
10:00:00 - Client calls POST /payment-orders/123/confirm
10:00:01 - Payment service calls gateway API
10:00:30 - Gateway API times out (no response)
10:00:31 - Payment attempt marked as UNKNOWN
10:02:15 - Gateway sends webhook: payment.succeeded
           ⬇️ WebhookEvent inserted HERE
```

**Exact Flow:**

```java
@PostMapping("/webhooks/stripe")
public ResponseEntity<String> handleStripeWebhook(
    @RequestBody String payload,
    @RequestHeader("Stripe-Signature") String signature
) {
    // Step 1: Verify webhook signature
    if (!webhookService.verifySignature(payload, signature)) {
        return ResponseEntity.status(401).body("Invalid signature");
    }
    
    WebhookEvent event = parsePayload(payload);
    
    // Step 2: Check if already processed (idempotency)
    if (webhookEventRepo.existsByGatewayEventId(event.getGatewayEventId())) {
        return ResponseEntity.ok("Already processed");
    }
    
    // Step 3: INSERT webhook_events (BEFORE processing)
    WebhookEvent savedEvent = webhookEventRepo.save(new WebhookEvent(
        gateway = "STRIPE",
        gatewayEventId = event.getGatewayEventId(),
        eventType = event.getType(),
        payloadHash = sha256(payload),
        createdAt = NOW()
    ));
    
    // Step 4: Process the webhook
    try {
        processWebhook(event);
        
        // Step 5: Mark as processed
        savedEvent.setProcessedAt(NOW());
        webhookEventRepo.save(savedEvent);
        
    } catch (Exception e) {
        // Webhook remains unprocessed (processed_at = NULL)
        // Retry job will pick it up later
    }
    
    return ResponseEntity.ok("Success");
}
```

**Key Points:**
1. **Insert IMMEDIATELY** upon receiving webhook (even before processing)
2. **Why?** Prevents duplicate processing if webhook retried during processing
3. **processed_at NULL** means failed processing → retry later
4. **Unique constraint** on `gateway_event_id` prevents duplicates

---

## Part 2: Failure Scenario Questions

### Q3: Gateway timeout - How do you handle UNKNOWN payment status?

**Scenario:**
```
1. User clicks "Pay Now" ($100)
2. Call Stripe API: POST /charges → 30-second timeout
3. Payment status = ??? (did it go through?)
4. User sees error, might retry
```

**Bad Approach:**
```java
// ❌ Return error immediately
return new PaymentResponse(FAILED, "Try again");
// Problem: If payment succeeded at gateway, user will be double-charged on retry!
```

**Good Approach:**
```java
@Transactional
public PaymentResponse confirmPayment(String orderId) {
    PaymentOrder order = orderRepo.findById(orderId);
    
    // Create attempt record
    PaymentAttempt attempt = new PaymentAttempt(
        orderId = orderId,
        gateway = "STRIPE",
        status = INITIATED,
        attemptNo = order.getAttemptCount() + 1
    );
    attemptRepo.save(attempt);
    
    try {
        // Call gateway
        GatewayResponse response = stripeClient.charge(order.getAmount());
        
        attempt.setStatus(SUCCESS);
        attempt.setGatewayTxnId(response.getTxnId());
        order.setStatus(CAPTURED);
        
        // Create ledger entries
        createLedgerEntries(order);
        
        return new PaymentResponse(SUCCESS);
        
    } catch (TimeoutException e) {
        // ⚠️ UNKNOWN state - payment might have succeeded
        attempt.setStatus(UNKNOWN);
        order.setStatus(PENDING_CONFIRMATION);
        
        // Start reconciliation job
        reconciliationQueue.enqueue(attempt.getId());
        
        return new PaymentResponse(
            PENDING, 
            "Payment processing. Check status in 2 minutes."
        );
    }
}
```

**Reconciliation Job:**
```java
@Scheduled(fixedDelay = 30000) // Every 30 seconds
public void reconcileUnknownPayments() {
    List<PaymentAttempt> unknownAttempts = 
        attemptRepo.findByStatus(UNKNOWN);
    
    for (PaymentAttempt attempt : unknownAttempts) {
        try {
            // Poll gateway for status
            GatewayTransaction txn = stripeClient.getTransaction(
                attempt.getGatewayTxnId()
            );
            
            if (txn.getStatus() == SUCCEEDED) {
                attempt.setStatus(SUCCESS);
                order.setStatus(CAPTURED);
                createLedgerEntries(order);
            } else {
                attempt.setStatus(FAILED);
                order.setStatus(FAILED);
            }
            
        } catch (Exception e) {
            // Keep in UNKNOWN, retry later
        }
    }
}
```

**Wait for Webhook:**
```java
// When webhook arrives (could be 2 minutes later)
public void processPaymentSuccessWebhook(WebhookEvent event) {
    PaymentAttempt attempt = attemptRepo.findByGatewayTxnId(
        event.getGatewayTxnId()
    );
    
    if (attempt.getStatus() == UNKNOWN) {
        // Finally resolved!
        attempt.setStatus(SUCCESS);
        attempt.getOrder().setStatus(CAPTURED);
        createLedgerEntries(attempt.getOrder());
    }
}
```

---

### Q4: User clicks "Pay" twice rapidly - How to prevent double charge?

**Scenario:**
```
10:00:00.000 - User clicks "Pay" (Request 1)
10:00:00.100 - User clicks "Pay" again (Request 2) - Button not disabled yet!
```

**Solution 1: Frontend Idempotency Key**
```javascript
// Frontend generates idempotency key
const idempotencyKey = uuidv4(); // Generated ONCE per payment intent

async function handlePayment() {
    const response = await fetch('/payment-orders', {
        method: 'POST',
        headers: {
            'Idempotency-Key': idempotencyKey, // Same key for retries
        },
        body: JSON.stringify(paymentData)
    });
}
```

**Backend Implementation:**
```java
@PostMapping("/payment-orders")
public PaymentResponse createPaymentOrder(
    @RequestHeader("Idempotency-Key") String idempotencyKey,
    @RequestBody PaymentRequest request
) {
    String cacheKey = "payment:" + request.getMerchantId() + ":" + idempotencyKey;
    
    // Check Redis cache first (fast path)
    PaymentResponse cachedResponse = redisCache.get(cacheKey);
    if (cachedResponse != null) {
        return cachedResponse; // Return same response immediately
    }
    
    // Acquire distributed lock
    RLock lock = redisson.getLock("lock:" + cacheKey);
    
    try {
        lock.lock(10, TimeUnit.SECONDS);
        
        // Double-check cache after acquiring lock
        cachedResponse = redisCache.get(cacheKey);
        if (cachedResponse != null) {
            return cachedResponse;
        }
        
        // Check database (slow path)
        PaymentOrder existingOrder = orderRepo.findByMerchantIdAndIdempotencyKey(
            request.getMerchantId(), 
            idempotencyKey
        );
        
        if (existingOrder != null) {
            // Already processed
            PaymentResponse response = new PaymentResponse(existingOrder);
            redisCache.setex(cacheKey, 86400, response); // Cache 24 hours
            return response;
        }
        
        // Create new payment order
        PaymentOrder order = new PaymentOrder();
        order.setMerchantId(request.getMerchantId());
        order.setIdempotencyKey(idempotencyKey);
        order.setAmount(request.getAmount());
        order.setStatus(CREATED);
        
        orderRepo.save(order);
        
        PaymentResponse response = new PaymentResponse(order);
        redisCache.setex(cacheKey, 86400, response);
        
        return response;
        
    } finally {
        lock.unlock();
    }
}
```

**Database Constraint:**
```sql
CREATE UNIQUE INDEX idx_merchant_idempotency 
ON payment_orders(merchant_id, idempotency_key);

-- If duplicate INSERT attempted → throws exception
-- Catch and return existing order
```

---

### Q5: Webhook arrives BEFORE your API call completes - Race condition!

**Scenario:**
```
10:00:00 - Call gateway API: POST /charges
10:00:01 - Gateway processes instantly, sends webhook (fast network)
10:00:01.5 - Webhook hits your server: POST /webhooks/stripe
10:00:02 - Your API call finally returns success
```

**Problem:**
```
Webhook handler: "Where is payment_order with gateway_txn_id = 'ch_abc'?"
                 "Not found!" → Webhook processing fails
```

**Solution: Webhook Retry + Eventual Consistency**

```java
public void processWebhook(WebhookEvent event) {
    String gatewayTxnId = event.getGatewayTxnId();
    
    // Try to find payment attempt
    PaymentAttempt attempt = attemptRepo.findByGatewayTxnId(gatewayTxnId);
    
    if (attempt == null) {
        // Race condition: Our DB insert hasn't committed yet
        
        if (event.getRetryCount() < 3) {
            // Delay and retry
            Thread.sleep(2000); // Wait 2 seconds
            attempt = attemptRepo.findByGatewayTxnId(gatewayTxnId);
        }
        
        if (attempt == null) {
            // Still not found - store webhook for later reconciliation
            orphanedWebhookRepo.save(event);
            return;
        }
    }
    
    // Process normally
    updatePaymentStatus(attempt, event);
}
```

**Alternative: Webhook as Source of Truth**
```java
// Don't wait for API response
@Async
public CompletableFuture<PaymentResponse> confirmPayment(String orderId) {
    PaymentOrder order = orderRepo.findById(orderId);
    
    // Make async call to gateway
    stripeClient.chargeAsync(order.getAmount())
        .thenAccept(response -> {
            // Don't update status here
            // Let webhook do it (single source of truth)
        });
    
    // Return immediately
    return CompletableFuture.completedFuture(
        new PaymentResponse(PENDING, "Check webhook for final status")
    );
}
```

---

## Part 3: Concurrency & Race Conditions

### Q6: Two concurrent refunds on same payment - How to prevent over-refund?

**Scenario:**
```
Payment: $100
Customer service agent 1: Issues $60 refund
Customer service agent 2: Issues $50 refund (simultaneously)
Total refund: $110 > $100 ❌ Over-refunded!
```

**Solution: Optimistic Locking**

```java
@Entity
@Table(name = "payment_orders")
public class PaymentOrder {
    @Id
    private String id;
    
    private BigDecimal amount;
    private BigDecimal refundedAmount = BigDecimal.ZERO;
    
    @Version // Optimistic lock version
    private Long version;
}
```

```java
@Transactional
public RefundResponse processRefund(String orderId, BigDecimal refundAmount) {
    // SELECT ... FOR UPDATE (pessimistic lock)
    PaymentOrder order = orderRepo.findByIdWithLock(orderId);
    
    BigDecimal maxRefundable = order.getAmount().subtract(order.getRefundedAmount());
    
    if (refundAmount.compareTo(maxRefundable) > 0) {
        throw new InsufficientRefundAmountException(
            "Max refundable: " + maxRefundable
        );
    }
    
    // Call gateway
    GatewayRefundResponse gatewayResponse = stripeClient.refund(
        order.getGatewayTxnId(), 
        refundAmount
    );
    
    // Update refunded amount
    order.setRefundedAmount(order.getRefundedAmount().add(refundAmount));
    order.setVersion(order.getVersion() + 1); // Increment version
    
    // If another transaction modified this row, version mismatch → exception
    orderRepo.save(order);
    
    // Create refund record
    Refund refund = new Refund(orderId, refundAmount, gatewayResponse.getRefundId());
    refundRepo.save(refund);
    
    // Create ledger entries (reverse transaction)
    createRefundLedgerEntries(order, refund);
    
    return new RefundResponse(SUCCESS);
}
```

**What happens with concurrent refunds?**
```
Time    Agent 1 (Refund $60)           Agent 2 (Refund $50)
────────────────────────────────────────────────────────────
10:00   Read: version=1, refunded=0    
10:01                                  Read: version=1, refunded=0
10:02   Check: 60 <= 100 ✅
10:03                                  Check: 50 <= 100 ✅
10:04   Call gateway: refund $60
10:05                                  Call gateway: refund $50
10:06   UPDATE version=2, refunded=60
10:07                                  UPDATE version=2, refunded=50
                                       ❌ OptimisticLockException!
                                       (Expected version=1, found=2)
```

**Agent 2 retry:**
```java
catch (OptimisticLockException e) {
    // Retry with fresh data
    order = orderRepo.findById(orderId);
    // Now: version=2, refunded=60
    // Check: 50 <= (100-60) = 40 ❌ 
    throw new InsufficientRefundAmountException();
}
```

---

### Q7: Ledger entries don't balance - How to detect and fix?

**Scenario:**
```sql
-- Transaction txn_001: Should balance
INSERT INTO ledger_entries VALUES
  ('uuid1', 'txn_001', 'customer_123', 'DEBIT',  100.00),
  ('uuid2', 'txn_001', 'merchant_456', 'CREDIT',  98.00),
  ('uuid3', 'txn_001', 'platform_wallet', 'CREDIT', 2.00);
  
-- DEBIT = 100, CREDIT = 100 ✅ Balanced

-- Bug: Application crashes after inserting 2 entries
INSERT INTO ledger_entries VALUES
  ('uuid4', 'txn_002', 'customer_789', 'DEBIT', 50.00);
  -- CRASH! Missing CREDIT entry
  
-- DEBIT = 50, CREDIT = 0 ❌ UNBALANCED!
```

**Detection: Daily Reconciliation Job**

```sql
-- Find unbalanced transactions
WITH transaction_balance AS (
    SELECT 
        txn_group_id,
        SUM(CASE WHEN side = 'DEBIT' THEN amount ELSE 0 END) AS total_debit,
        SUM(CASE WHEN side = 'CREDIT' THEN amount ELSE 0 END) AS total_credit,
        COUNT(*) AS entry_count,
        MAX(created_at) AS last_entry_at
    FROM ledger_entries
    WHERE DATE(created_at) = CURRENT_DATE - INTERVAL 1 DAY
    GROUP BY txn_group_id
)
SELECT *
FROM transaction_balance
WHERE total_debit != total_credit
   OR entry_count = 1; -- Incomplete transaction

-- Alert if any found!
```

**Prevention: Database Transaction Wrapper**

```java
@Transactional
public void createLedgerEntries(PaymentOrder order) {
    String txnGroupId = UUID.randomUUID().toString();
    
    List<LedgerEntry> entries = new ArrayList<>();
    
    // Debit customer
    entries.add(new LedgerEntry(
        txnGroupId, 
        order.getCustomerId(), 
        DEBIT, 
        order.getAmount()
    ));
    
    // Credit merchant (after fees)
    BigDecimal merchantAmount = order.getAmount().subtract(order.getFee());
    entries.add(new LedgerEntry(
        txnGroupId, 
        order.getMerchantId(), 
        CREDIT, 
        merchantAmount
    ));
    
    // Credit platform
    entries.add(new LedgerEntry(
        txnGroupId, 
        "platform_wallet", 
        CREDIT, 
        order.getFee()
    ));
    
    // Verify balance BEFORE inserting
    BigDecimal totalDebit = entries.stream()
        .filter(e -> e.getSide() == DEBIT)
        .map(LedgerEntry::getAmount)
        .reduce(BigDecimal.ZERO, BigDecimal::add);
    
    BigDecimal totalCredit = entries.stream()
        .filter(e -> e.getSide() == CREDIT)
        .map(LedgerEntry::getAmount)
        .reduce(BigDecimal.ZERO, BigDecimal::add);
    
    if (!totalDebit.equals(totalCredit)) {
        throw new LedgerImbalanceException(
            "Debit: " + totalDebit + ", Credit: " + totalCredit
        );
    }
    
    // Insert all entries in single transaction
    ledgerRepo.saveAll(entries);
    
    // If ANY insert fails, ALL rollback → consistency maintained
}
```

---

## Part 4: Scale & Performance

### Q8: Payment service receives 10K requests/sec - How to scale?

**Architecture:**

```
                    Load Balancer
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   API Instance 1   API Instance 2   API Instance 3
        │                │                │
        └────────────────┼────────────────┘
                         │
                    Kafka Queue
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   Worker 1          Worker 2         Worker 3
        │                │                │
        └────────────────┼────────────────┘
                         │
                  Database (Sharded)
```

**Approach:**

1. **Separate Write API from Processing**
```java
// API Layer: Accept request, return immediately
@PostMapping("/payment-orders")
public PaymentResponse createOrder(@RequestBody PaymentRequest req) {
    // 1. Validate
    validate(req);
    
    // 2. Create order (CREATED state)
    PaymentOrder order = new PaymentOrder(CREATED);
    orderRepo.save(order);
    
    // 3. Publish to Kafka (async processing)
    kafkaProducer.send("payment-events", new PaymentEvent(order.getId()));
    
    // 4. Return immediately
    return new PaymentResponse(order.getId(), CREATED);
}

// Worker: Process from Kafka
@KafkaListener(topics = "payment-events")
public void processPayment(PaymentEvent event) {
    PaymentOrder order = orderRepo.findById(event.getOrderId());
    
    // Call gateway (can be slow)
    GatewayResponse response = gatewayClient.charge(order);
    
    order.setStatus(response.isSuccess() ? CAPTURED : FAILED);
    orderRepo.save(order);
    
    createLedgerEntries(order);
}
```

2. **Database Sharding by merchant_id**
```java
// Shard routing
public DataSource getShardForMerchant(String merchantId) {
    int shardId = Math.abs(merchantId.hashCode()) % NUM_SHARDS;
    return dataSources.get(shardId);
}

// Query routing
public PaymentOrder findOrder(String orderId) {
    // Extract merchant_id from order_id or lookup in routing table
    String merchantId = extractMerchantId(orderId);
    DataSource shard = getShardForMerchant(merchantId);
    return shard.query("SELECT * FROM payment_orders WHERE id = ?", orderId);
}
```

3. **Redis Cache for Idempotency**
```java
// Fast path: Check Redis
@Cacheable(key = "#merchantId + ':' + #idempotencyKey", ttl = 86400)
public PaymentResponse getOrCreateOrder(String merchantId, String idempotencyKey) {
    // Slow path: Check database
    return orderRepo.findByMerchantIdAndIdempotencyKey(merchantId, idempotencyKey);
}
```

4. **Rate Limiting per Merchant**
```java
@RateLimiter(
    key = "#request.merchantId",
    limit = 100,
    window = 60 // 100 requests per minute per merchant
)
public PaymentResponse createOrder(PaymentRequest request) {
    // ...
}
```

---

### Q9: Gateway reconciliation - 1M transactions/day, how to match?

**Problem:**
```
Your database: 1,000,000 transactions
Gateway settlement report: 999,998 transactions
Missing: 2 transactions ⚠️
```

**Solution: Daily Batch Reconciliation**

```java
@Scheduled(cron = "0 0 2 * * *") // 2 AM daily
public void reconcileSettlement() {
    LocalDate yesterday = LocalDate.now().minusDays(1);
    
    // 1. Download gateway settlement report
    List<GatewayTransaction> gatewayTxns = 
        stripeClient.getSettlementReport(yesterday);
    
    // 2. Fetch our transactions
    List<PaymentOrder> ourOrders = 
        orderRepo.findByCreatedDateAndStatus(yesterday, CAPTURED);
    
    // 3. Create lookup maps
    Map<String, GatewayTransaction> gatewayMap = 
        gatewayTxns.stream()
            .collect(Collectors.toMap(
                GatewayTransaction::getId, 
                Function.identity()
            ));
    
    Map<String, PaymentOrder> ourMap = 
        ourOrders.stream()
            .collect(Collectors.toMap(
                PaymentOrder::getGatewayTxnId, 
                Function.identity()
            ));
    
    // 4. Find discrepancies
    List<String> missingInGateway = ourMap.keySet().stream()
        .filter(id -> !gatewayMap.containsKey(id))
        .collect(Collectors.toList());
    
    List<String> missingInOurDb = gatewayMap.keySet().stream()
        .filter(id -> !ourMap.containsKey(id))
        .collect(Collectors.toList());
    
    // 5. Amount mismatch
    List<String> amountMismatch = new ArrayList<>();
    for (String gatewayTxnId : gatewayMap.keySet()) {
        if (ourMap.containsKey(gatewayTxnId)) {
            GatewayTransaction gTxn = gatewayMap.get(gatewayTxnId);
            PaymentOrder order = ourMap.get(gatewayTxnId);
            
            if (!gTxn.getAmount().equals(order.getAmount())) {
                amountMismatch.add(gatewayTxnId);
            }
        }
    }
    
    // 6. Alert if discrepancies found
    if (!missingInGateway.isEmpty() || 
        !missingInOurDb.isEmpty() || 
        !amountMismatch.isEmpty()) {
        
        alertService.sendCriticalAlert(
            "Settlement mismatch for " + yesterday +
            "\nMissing in gateway: " + missingInGateway.size() +
            "\nMissing in DB: " + missingInOurDb.size() +
            "\nAmount mismatch: " + amountMismatch.size()
        );
    }
}
```

**Optimization for Scale:**
```java
// Use batch processing with pagination
public void reconcileInBatches() {
    int batchSize = 10000;
    int offset = 0;
    
    while (true) {
        List<PaymentOrder> batch = orderRepo.findBatch(offset, batchSize);
        if (batch.isEmpty()) break;
        
        reconcileBatch(batch);
        offset += batchSize;
    }
}
```

---

## Summary: Key Takeaways

1. **Ledger entries BEFORE account updates** (if accounts table exists)
2. **WebhookEvent inserted IMMEDIATELY** upon receiving webhook
3. **UNKNOWN status** for gateway timeouts → reconciliation + webhook
4. **Idempotency keys** prevent double charges
5. **Optimistic locking** prevents over-refunds
6. **Daily reconciliation** detects ledger imbalances
7. **Async processing** (Kafka) for high throughput
8. **Sharding by merchant_id** for horizontal scaling

---

**Interview Tips:**
- Always mention **"transaction boundaries"** and **"ACID guarantees"**
- Draw sequence diagrams for timing questions
- Discuss tradeoffs: sync vs async, strong vs eventual consistency
- Know SQL constraints: UNIQUE, CHECK, FOREIGN KEY
- Understand distributed locks (Redis, ZooKeeper)

Study time: 20-25 minutes  
Interview frequency: 70-80%
