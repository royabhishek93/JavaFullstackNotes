# Q23: Saga Pattern - Distributed Transactions in Microservices

**Study Time:** 8-10 minutes | **Frequency:** 72% in system design interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

---

## The Problem

In a **monolithic application**, you have **true ACID transactions**:

```java
@Transactional
public void placeOrder(Order order, Payment payment) {
    orderDAO.save(order);
    paymentDAO.save(payment);
    // If either fails → ROLLBACK both
}
```

But in **microservices**, each service has its own database:

```
Order Service (DB: orders)
Payment Service (DB: payments)
Portfolio Service (DB: inventory)
```

**Problem:** One transaction cannot span three databases at once.

**Traditional Solution:** Two-Phase Commit (2PC) - **Slow, not suitable for distributed systems**

**Modern Solution:** **Saga Pattern** with event-driven choreography or orchestration

---

## 🔥 The Core Principle

Instead of **ROLLBACK**, use **COMPENSATION**:

```
Step 1: Order Service → Creates order → Publishes ORDER_CREATED ✅
Step 2: Payment Service → Processes payment → Publishes PAYMENT_SUCCESS ✅
Step 3: Portfolio Service → Updates inventory → Publishes PORTFOLIO_UPDATED ✅

❌ If Step 2 fails:
   Payment Service → Publishes PAYMENT_FAILED
   Order Service → Listens and CANCELS order (compensation)
   No rollback needed - event-driven reversal
```

**Key:** Use **idempotent consumers** + **transactional messaging** to ensure consistency.

---

## Architecture Styles

### Style 1: Choreography (Events, No Central Coordinator)

```
Order Service                  Payment Service                  Portfolio Service
     │                              │                                │
     └─── ORDER_CREATED ──────────> │                                │
                                    │                                │
                              Processes payment                      │
                                    │                                │
                                    └─── PAYMENT_SUCCESS ──────────> │
                                                                     │
                                                            Updates inventory
                                                                     │
```

**Pros:**
- Simple, no central coordinator needed
- Services are loosely coupled
- Failure handling is event-based

**Cons:**
- Hard to track overall state
- Circular event dependencies possible
- Testing is complex

---

### Style 2: Orchestration (Central Saga Orchestrator)

```
                        Saga Orchestrator (Coordinator)
                                  │
                     ┌────────────┼────────────┐
                     │            │            │
                Order Service  Payment       Portfolio
                     │          Service       Service
                     │            │            │
```

Orchestrator sends commands:

```
Orchestrator → Order Service: CREATE_ORDER
Order Service → Orchestrator: ORDER_CREATED ✅

Orchestrator → Payment Service: PROCESS_PAYMENT
Payment Service → Orchestrator: PAYMENT_FAILED ❌

Orchestrator → Order Service: CANCEL_ORDER (compensation)
```

**Pros:**
- Centralized control, easier to understand
- Clear state transitions
- Easy to add compensations

**Cons:**
- Single point of failure
- Orchestrator becomes a bottleneck

---

## Real Example: Order → Payment → Inventory

### Step 1: Order Service Creates Order

```java
@Service
public class OrderService {
    @Transactional
    public void createOrder(Order order) {
        // 1. Save order to DB (atomic)
        orderRepository.save(order);
        
        // 2. Publish event (within transaction)
        kafkaTemplate.send("order-events", "ORDER_CREATED", 
            new OrderCreatedEvent(order.getId(), order.getAmount()));
    }
}
```

**Event Published:**
```json
{
    "orderId": "ORD123",
    "amount": 100.0,
    "timestamp": "2026-02-28T10:00:00Z"
}
```

---

### Step 2: Payment Service Consumes and Processes

```java
@Service
public class PaymentService {
    @KafkaListener(topics = "order-events")
    @Transactional
    public void handleOrderCreated(OrderCreatedEvent event) {
        try {
            // Process payment
            processPayment(event.getOrderId(), event.getAmount());
            
            // Publish success
            kafkaTemplate.send("payment-events", "PAYMENT_SUCCESS",
                new PaymentSuccessEvent(event.getOrderId()));
                
        } catch (PaymentException e) {
            // Publish failure → triggers compensation
            kafkaTemplate.send("payment-events", "PAYMENT_FAILED",
                new PaymentFailedEvent(event.getOrderId(), e.getMessage()));
        }
    }
}
```

---

### Step 3: Portfolio Service Updates Inventory

```java
@Service
public class PortfolioService {
    @KafkaListener(topics = "payment-events")
    @Transactional
    public void handlePaymentSuccess(PaymentSuccessEvent event) {
        // Update inventory
        updateInventory(event.getOrderId());
        
        // Publish completion
        kafkaTemplate.send("saga-events", "SAGA_COMPLETED", 
            new SagaCompletedEvent(event.getOrderId()));
    }
}
```

---

### Step 4: Compensation (If Payment Fails)

```java
@Service
public class OrderService {
    @KafkaListener(topics = "payment-events")
    @Transactional
    public void handlePaymentFailed(PaymentFailedEvent event) {
        // Compensation: Cancel the order
        cancelOrder(event.getOrderId());
        
        // Publish compensation event
        kafkaTemplate.send("saga-events", "ORDER_CANCELLED",
            new OrderCancelledEvent(event.getOrderId()));
        
        // Notify customer
        notificationService.sendEmail("Payment failed, order cancelled");
    }
}
```

---

## Ensuring Reliability (Idempotency + Transactional Messaging)

### Problem: Message Redelivery

Kafka might deliver the same message twice:

```
Payment Service receives: PAYMENT_SUCCESS
→ Updates portfolio
→ Crashes before acknowledging

Message redelivered
→ Portfolio updated TWICE! (Duplicate charge)
```

### Solution: Idempotent Processing

```java
@Service
public class PortfolioService {
    @KafkaListener(topics = "payment-events")
    @Transactional
    public void handlePaymentSuccess(PaymentSuccessEvent event) {
        // Check: Is this event already processed?
        if (processedEvents.contains(event.getEventId())) {
            return;  // Idempotent - skip duplicate
        }
        
        // Process only once
        updateInventory(event.getOrderId());
        
        // Mark as processed
        processedEvents.add(event.getEventId());
    }
}
```

### Solution: Transactional Messaging (Outbox Pattern)

```java
@Service
public class OrderService {
    @Transactional
    public void createOrder(Order order) {
        // 1. Save order and event in SAME transaction
        orderRepository.save(order);
        eventRepository.save(
            new Event(EventType.ORDER_CREATED, order.getId())
        );
        // If this transaction commits, BOTH are saved
        // If it rolls back, neither is saved
    }
}

// Separate thread: polls eventRepository and publishes to Kafka
@Scheduled(fixedDelay = 1000)
public void publishEvents() {
    List<Event> unpublished = eventRepository.findUnpublished();
    for (Event event : unpublished) {
        kafkaTemplate.send("order-events", event.getEventId(), 
            event.getPayload());
        event.markPublished();
        eventRepository.save(event);
    }
}
```

---

## Flow Diagram: Complete Saga

```
┌─────────────────────────────────────────────────────────┐
│ SUCCESS PATH: Order → Payment → Inventory               │
└─────────────────────────────────────────────────────────┘

Order Service
    └─ createOrder() → save DB ───────────────────┐
                                                   │
                                              ORDER_CREATED
                                                   │
Payment Service ◄──────────────────────────────────┘
    └─ handleOrderCreated() → processPayment()
       (if success)
              │
         PAYMENT_SUCCESS
              │
Portfolio Service ◄────────────────────────────────┐
    └─ handlePaymentSuccess() → updateInventory()   │
                                                    │
                      ┌──────────────────────────────┘
                      │
                 SAGA_COMPLETED
                      │
                  ✅ SUCCESS

┌─────────────────────────────────────────────────────────┐
│ FAILURE PATH: Order → Payment ❌ → Compensation        │
└─────────────────────────────────────────────────────────┘

Order Service
    └─ createOrder() → save DB ──────────────────┐
                                                  │
                                             ORDER_CREATED
                                                  │
Payment Service ◄───────────────────────────────┘
    └─ handleOrderCreated() → processPayment() ❌
              │
         PAYMENT_FAILED
              │
Order Service ◄───────────────────────────────┐
    └─ handlePaymentFailed() → cancelOrder() ◄─┘
       (compensation)
              │
         ORDER_CANCELLED
              │
          ✅ COMPENSATED (Consistent state)
```

---

## Interview Tip

"A **Saga Pattern** is a way to maintain data consistency across microservices without traditional distributed transactions. Instead of using rollback, we use **compensation logic** - when a step fails, the saga triggers compensating transactions in reverse order to undo previous steps. We ensure reliability using **idempotent consumers** and **transactional messaging** (outbox pattern) so each step executes exactly once, achieving eventual consistency."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Not making consumers idempotent**

❌ **Wrong approach:**
```java
@KafkaListener(topics = "payment-events")
public void handlePaymentSuccess(PaymentSuccessEvent event) {
    // No idempotency check
    updateInventory(event.getOrderId());  // Might run twice!
}

// Result: Inventory updated twice for same payment
```
**Why it fails:** Kafka can redeliver messages. Without idempotency, duplicate processing corrupts state.

✅ **Right approach:**
```java
@KafkaListener(topics = "payment-events")
public void handlePaymentSuccess(PaymentSuccessEvent event) {
    // Check if already processed
    if (isProcessed(event.getEventId())) return;
    
    // Process
    updateInventory(event.getOrderId());
    
    // Mark processed
    markAsProcessed(event.getEventId());
}
```

---

**Pitfall 2: Publishing events outside of transaction**

❌ **Wrong approach:**
```java
@Transactional
public void createOrder(Order order) {
    orderRepository.save(order);
}  // Transaction commits

// Outside transaction - might fail!
kafkaTemplate.send("order-events", new OrderCreatedEvent(order.getId()));
// If Kafka is down, event is lost!
```
**Why it fails:** Database commits but Kafka send fails. Other services never know about the order.

✅ **Right approach (Outbox Pattern):**
```java
@Transactional
public void createOrder(Order order) {
    // BOTH in same transaction
    orderRepository.save(order);
    eventRepository.save(new Event(...));  // Saved in DB
}

// Separate poller publishes FROM database TO Kafka
// If Kafka fails, can retry - event is persisted in DB
```

---

**Pitfall 3: Circular event dependencies**

❌ **Wrong approach:**
```
Order Service → publishes PAYMENT_FAILED
    ↑
    │
Payment Service → listens PAYMENT_FAILED, publishes ORDER_CANCELLED
    ↑
    │
Order Service → listens ORDER_CANCELLED, publishes ... (CIRCULAR!)
```
**Why it fails:** Infinite loop of events. Saga never completes.

✅ **Right approach:**
```java
// Use explicit compensation direction
// Forward flow: Order → Payment → Inventory
// Compensation: Inventory ← Payment ← Order (reverse)

// Not a full circle, clear termination
```

---

## 🛑 When NOT to Use Saga Pattern

1. **When you need strong ACID guarantees** → Use monolith or saga won't work
2. **For simple operations** → Overhead not worth it, use synchronous calls
3. **When compensation is very costly** → Saga adds overhead
4. **In synchronous systems** → Saga is async-first pattern

---

## Quick Checklist

- ✅ **Problem:** Distributed transactions across microservices
- ✅ **Solution:** Saga pattern with compensation logic
- ✅ **Two styles:** Choreography (events) vs Orchestration (coordinator)
- ✅ **Reliability:** Idempotent consumers + Transactional messaging (Outbox)
- ✅ **Consistency:** Eventual consistency, not immediate
- ✅ **Failure handling:** Compensation (reverse) steps on failure
- ✅ **Key insight:** Event-driven reversal replaces ROLLBACK

---

**Last Updated:** February 28, 2026
