# Distributed Transactions: Saga vs 2PC (Two-Phase Commit)

**Study Time:** 12-15 minutes | **Frequency:** 90% in senior interviews | **Difficulty:** ⭐⭐⭐⭐⭐

---

## 🤔 Problem Scenario

How do you maintain consistency across multiple services when one fails?

```
Order Service → Payment Service → Inventory Service

User places order:
1. Order Service: Create order
2. Payment Service: Charge card
3. Inventory Service: Deduct stock

What if Payment fails after Order is created?
→ Inconsistent state! (Order exists, payment failed)
```

**Challenge:** Atomicity across distributed systems (no ACID guarantee).

---

## 🧠 Key Principle: Two Approaches

| Approach | Mechanism | Consistency Model | Recovery |
|----------|-----------|-------------------|----------|
| **2PC (Two-Phase Commit)** | Synchronous, coordinator | Strong consistency | Automatic rollback |
| **Saga** | Asynchronous, events/choreography | Eventual consistency | Manual compensating transactions |

---

## ✅ Solution 1: Two-Phase Commit (2PC)

**How it works:**

```
Coordinator decides if all participants can commit.

Phase 1 (Prepare):
┌─────────────────────────────────────────┐
│ Coordinator: "Can you commit?"          │
├──────────────┬──────────────┬──────────┤
│ Order Service│ Payment Svc  │ Inventory│
│ "YES, ready" │ "YES, locked"│ "YES, ok"│
└──────────────┴──────────────┴──────────┘

Phase 2 (Commit or Rollback):
If ALL said YES → COMMIT
If ANY said NO → ROLLBACK ALL
```

### Implementation:

```java
public class TwoPhaseCommitExample {
    
    private final OrderService orderService;
    private final PaymentService paymentService;
    private final InventoryService inventoryService;

    public void processOrder(Order order) throws Exception {
        String transactionId = UUID.randomUUID().toString();
        
        // Phase 1: Prepare - Ask all services if they can proceed
        try {
            boolean orderReady = orderService.prepare(transactionId, order);
            boolean paymentReady = paymentService.prepare(transactionId, order.getAmount());
            boolean inventoryReady = inventoryService.prepare(transactionId, order.getItems());
            
            if (!orderReady || !paymentReady || !inventoryReady) {
                // Phase 2: ABORT - Rollback all
                orderService.abort(transactionId);
                paymentService.abort(transactionId);
                inventoryService.abort(transactionId);
                throw new TransactionAbortedException("One service not ready");
            }
            
            // Phase 2: COMMIT - All agreed, execute
            orderService.commit(transactionId);
            paymentService.commit(transactionId);
            inventoryService.commit(transactionId);
            
        } catch (Exception e) {
            // Any error → Rollback all
            orderService.abort(transactionId);
            paymentService.abort(transactionId);
            inventoryService.abort(transactionId);
            throw e;
        }
    }
}
```

### Timeline:

```
T=0:   All services LOCK resources (pessimistic)
T=1:   Coordinator asks "Ready?"
T=2:   All respond "YES"
T=3:   Coordinator: "COMMIT!"
T=4:   All commit, UNLOCK resources
T=5:   Transaction complete

PROBLEM: If one service fails at T=2.5?
→ Long locks, blocking, performance degradation
```

---

## ✅ Solution 2: Saga Pattern (Choreography-based)

**How it works:**

```
Services publish events, each service reacts.
No coordinator - choreographed through events.

Step 1: Order Service creates order
        Publishes: OrderCreated event
            ↓
Step 2: Payment Service listens
        Charges payment
        Publishes: PaymentProcessed event
            ↓
Step 3: Inventory Service listens
        Deducts stock
        Publishes: StockDeducted event
            ↓
Step 4: SUCCESS!

If any step FAILS:
Payment fails → Publishes PaymentFailed
Order Service listens → Compensates (cancelOrder())
Creates: OrderCanceled event

No locks, asynchronous, resilient
```

### Implementation:

```java
// Event-driven Saga (Choreography)
public class OrderService {
    private final EventPublisher eventPublisher;

    public void createOrder(Order order) {
        // Create order in DB
        Order saved = orderRepository.save(order);
        
        // Publish event - Payment Service will hear this
        eventPublisher.publish(new OrderCreatedEvent(
            saved.getId(),
            saved.getAmount(),
            saved.getItems()
        ));
    }

    @EventListener(PaymentFailedEvent.class)
    public void handlePaymentFailed(PaymentFailedEvent event) {
        // Compensating transaction - Undo order creation
        orderRepository.cancel(event.getOrderId());
        eventPublisher.publish(new OrderCanceledEvent(event.getOrderId()));
    }
}

public class PaymentService {
    private final EventPublisher eventPublisher;

    @EventListener(OrderCreatedEvent.class)
    public void handleOrderCreated(OrderCreatedEvent event) {
        try {
            // Charge payment
            Payment payment = chargeCard(event.getAmount());
            
            // Success - publish event
            eventPublisher.publish(new PaymentProcessedEvent(
                event.getOrderId(),
                payment.getId()
            ));
        } catch (PaymentException e) {
            // Failure - publish failure event
            eventPublisher.publish(new PaymentFailedEvent(
                event.getOrderId(),
                e.getMessage()
            ));
            // Order Service will compensate
        }
    }
}

public class InventoryService {
    private final EventPublisher eventPublisher;


---

## ✅ Saga Styles: Choreography vs Orchestration

### Style 1: Choreography (Event-Driven, No Coordinator)

```
Order Service  →  Payment Service  →  Inventory Service
    (event)          (event)            (event)
```

**Pros:**
- Loosely coupled services
- No central bottleneck

**Cons:**
- Harder to trace end-to-end state
- Complex testing and debugging

### Style 2: Orchestration (Central Saga Coordinator)

```
             Saga Orchestrator
                      │
    ┌─────────────┼─────────────┐
    │             │             │
Order         Payment       Inventory
Service       Service       Service
```

**Pros:**
- Clear control flow and state tracking
- Easier to add compensation logic

**Cons:**
- Orchestrator can become a bottleneck
- Extra component to operate
    @EventListener(PaymentProcessedEvent.class)
    public void handlePaymentProcessed(PaymentProcessedEvent event) {
        try {
            // Deduct stock
            inventoryRepository.deduct(event.getOrderId());
            
            // Success
            eventPublisher.publish(new StockDeductedEvent(event.getOrderId()));
        } catch (Exception e) {
            // Failure - publish event
            eventPublisher.publish(new StockDeductionFailedEvent(event.getOrderId()));
            // Payment Service will compensate (refund)
            eventPublisher.publish(new PaymentRefundEvent(event.getPaymentId()));
        }
    }
}
```

### Timeline:

```
T=0:   Order Service creates order, publishes OrderCreatedEvent
T=1:   Payment Service hears it, charges card
T=2:   Payment Service publishes PaymentProcessedEvent
T=3:   Inventory Service hears it, deducts stock
T=4:   Inventory Service publishes StockDeductedEvent
T=5:   SUCCESS!

If Payment fails at T=1.5:
T=1.5: Payment fails
T=2:   Payment Service publishes PaymentFailedEvent
T=3:   Order Service hears it, cancels order
T=4:   Order Service publishes OrderCanceledEvent

No blocking locks, asynchronous, eventual consistency
```

---

## 📊 2PC vs Saga Comparison

| Aspect | 2PC | Saga |
|--------|-----|------|
| **Consistency** | Strong (ACID-like) | Eventual |
| **Latency** | Slower (locks wait) | Faster (async) |
| **Blocking** | YES (pessimistic locks) | NO |
| **Scalability** | Poor (locks) | Excellent (async) |
| **Failure Recovery** | Automatic | Manual compensation needed |
| **Complexity** | Simple logic | Needs event handlers |
| **Best for** | <100ms transactions | >100ms, distributed |
| **Examples** | DB transactions | Microservices |

---

## 🎯 Interview Q&A

### Q1: "When to use 2PC vs Saga?"

**Answer (30 seconds):**
```
2PC: Single datacenter, tight consistency needed
- Reason: Low latency, automatic rollback
- Example: Bank transfer, financial systems

Saga: Microservices, distributed systems
- Reason: No blocking, resilient, scalable
- Example: E-commerce (order + payment + inventory)

Rule: If services in SAME datacenter → 2PC
      If services ACROSS datacenters → Saga
```

---

### Q2: "What's the problem with 2PC?"

**Answer:**
```
BLOCKING: Locks held until Phase 2 completes
- If one service slow → All wait
- If one service down → All deadlocked

Performance issue:
- Network latency: Each message takes 20ms
- Phase 1: 3 services = 60ms locked
- Phase 2: Another 60ms locked
- Total: 120ms per transaction
- At scale: Only 8-9 transactions/second max

Better: Saga (async, parallel processing)
```

---

### Q3: "How does Saga handle failure?"

**Answer:**
```
COMPENSATING TRANSACTIONS:

Normal flow:
Order → Payment → Inventory → SUCCESS

If Inventory fails:
Inventory fails
  ↓ publishes StockDeductionFailedEvent
Payment Service hears it
  ↓ executes refund (compensating transaction)
Order Service hears it
  ↓ cancels order (compensating transaction)

Requirements:
1. Each transaction must have a "undo" operation
2. Undo must be idempotent (safe to retry)
3. Order of compensations matters

Idempotent example:
refund(paymentId):
  If already refunded → return (safe)
  Else → refund (execute once)
```

---

### Q4: "Code - Saga compensation issue?"

```java
@EventListener(PaymentFailedEvent.class)
public void compensate(PaymentFailedEvent event) {
    // This runs 3 times (retried by fault tolerance)
    refundAccount(event.getPaymentId());  // Refund 3x?
}
```

**Answer:**
```
PROBLEM: Not idempotent
- Refund called 3 times = Refund 3 times!
- User gets 3x refund

SOLUTION: Make idempotent
@EventListener(PaymentFailedEvent.class)
public void compensate(PaymentFailedEvent event) {
    Refund refund = refundRepository.find(event.getPaymentId());
    
    if (refund.isCompleted()) return;  // Already done
    
    refund.setStatus(PROCESSING);
    executeRefund(event.getPaymentId());
    refund.setStatus(COMPLETED);
}

Safe to call multiple times!
```

---

## ❌ Common Mistakes

### ❌ Mistake 1: Not Having Compensating Transactions

```java
// WRONG - No way to undo
Payment payment = chargeCard(amount);
if (someServiceFails("stock")) {
    // Stuck! Payment charged but no transaction
}

// CORRECT - Always have compensation
try {
    Payment payment = chargeCard(amount);
    inventoryService.deduct(items);
} catch (Exception e) {
    refundCard(payment.getId());  // Compensate
    throw e;
}
```

---

### ❌ Mistake 2: Using 2PC for Microservices

```java
// WRONG - 2PC across services = disaster
OrderService.create(order);  // Service 1
PaymentService.charge(amount);  // Service 2 (network latency!)
InventoryService.deduct(items);  // Service 3

// 3 network calls locked = ~120ms blocked per transaction
// At scale: Only 8-9 tx/sec (bottleneck!)

// CORRECT - Use Saga (async events)
OrderService.create(order);
publishEvent(OrderCreatedEvent);
// Other services react asynchronously
```

---

### ❌ Mistake 3: Not Handling Partial Failures

```java
// WRONG - Assumes all-or-nothing
publishEvent(event);
// What if EventBus fails after payment but before inventory?
// Inventory never deducted!

// CORRECT - Idempotent, retryable events
publishEvent(event);  // Retried if fails
// Each service checks: "Did I process this event?"
// Handles duplicates gracefully
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| 2PC synchronous nature | Understands blocking problem | ⭐⭐⭐⭐⭐ |
| Saga compensations | Core complexity | ⭐⭐⭐⭐⭐ |
| When to use each | Right tool selection | ⭐⭐⭐⭐⭐ |
| Idempotency requirement | Prevents duplicate work | ⭐⭐⭐⭐ |
| Trade-offs | Systems thinking | ⭐⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (90% senior interviews)

**Related:**
- Event Sourcing
- Eventual Consistency
- Circuit Breaker Pattern

---

**Last Updated:** March 5, 2026
