# Q21: Spring Events & @TransactionalEventListener — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 15-20 minutes | **Frequency:** 75% in architect rounds 🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "We published a 'UserRegistered' event. The event listener sent a welcome email. In 5% of cases, the DB rolled back AFTER the email was sent. Users received welcome emails for accounts that didn't exist." — The @EventListener without AFTER_COMMIT trap.

---

## How Spring Events Work (Plain English)

```
Think of it like a newspaper:
  Publisher: writes an article (publishes event), doesn't know who reads it
  Listener:  subscribes to topics it cares about, gets notified

WHY USE EVENTS?
  Without events: OrderService calls NotificationService directly
    → OrderService depends on NotificationService
    → If Notification is slow, Order is slow
    → Tight coupling — hard to add more listeners

  With events: OrderService publishes "OrderPlaced" event
    → NotificationService listens → sends email
    → AnalyticsService listens → records event
    → LoyaltyService listens → updates points
    OrderService knows NOTHING about any of these → loose coupling
```

---

## Scenario 1: Basic @EventListener — Internal Decoupling

```java
// Step 1: Define an event (any POJO — no need to extend ApplicationEvent in Spring 4+)
public record OrderPlacedEvent(Long orderId, Long userId, BigDecimal amount) {}

// Step 2: Publisher — use ApplicationEventPublisher
@Service
@Transactional
public class OrderService {

    @Autowired
    private ApplicationEventPublisher eventPublisher;

    public Order placeOrder(OrderRequest request) {
        Order order = orderRepo.save(new Order(request));

        // Publish event — at this point, TX is still open (not committed yet!)
        eventPublisher.publishEvent(new OrderPlacedEvent(
            order.getId(), request.getUserId(), order.getTotalAmount()
        ));

        return order;
    }
}

// Step 3: Listener — @EventListener (synchronous by default)
@Component
public class OrderAnalyticsListener {

    @EventListener
    public void onOrderPlaced(OrderPlacedEvent event) {
        // Runs synchronously in the SAME thread as the publisher
        // Still inside the publisher's transaction if publisher is @Transactional
        analyticsRepo.save(new AnalyticsRecord(event.orderId(), event.amount()));
        log.info("Analytics recorded for order {}", event.orderId());
    }
}
```

---

## Scenario 2: @TransactionalEventListener — Fire AFTER Commit

### The Critical Problem
```
PlaceOrder flow:
  1. Save Order to DB (TX open)
  2. Publish OrderPlacedEvent (TX still open)
  3. @EventListener fires NOW (TX open, not yet committed!)
  4. Listener sends email ✅
  5. TX commits ✅

Failure scenario:
  3. Listener sends email ✅ — welcome email SENT
  4. TX fails to commit (constraint violation, timeout, etc.)
  5. Order is ROLLED BACK — order doesn't exist in DB!
  → Customer received email for order that doesn't exist
  → Inventory decremented for order that was rolled back
```

### Fix: @TransactionalEventListener
```java
@Component
public class OrderNotificationListener {

    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onOrderPlaced(OrderPlacedEvent event) {
        // Fires ONLY after the transaction that published the event COMMITS
        // If TX rolls back → this method is NEVER called
        emailService.sendOrderConfirmation(event.userId(), event.orderId());
    }

    @TransactionalEventListener(phase = TransactionPhase.AFTER_ROLLBACK)
    public void onOrderFailed(OrderPlacedEvent event) {
        // Fires only if transaction ROLLS BACK
        // Use for: alerting, cleanup, compensating actions
        alertingService.notify("Order " + event.orderId() + " rolled back");
    }
}
```

### The AFTER_COMMIT Transaction Trap
```java
// WRONG ❌ — trying to do DB work in AFTER_COMMIT listener
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
@Transactional   // ← TRAP: the original TX is already committed/closed!
public void onOrderPlaced(OrderPlacedEvent event) {
    // By default: no transaction active here
    // @Transactional tries to JOIN the existing TX
    // But the TX is already done → joins nothing → writes not persisted!
    auditRepo.save(new AuditLog(event.orderId()));  // NOT saved!
}

// FIX: Use REQUIRES_NEW to open a fresh transaction
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
@Transactional(propagation = Propagation.REQUIRES_NEW)
public void onOrderPlaced(OrderPlacedEvent event) {
    // Opens a NEW transaction — independent of the completed publisher TX
    auditRepo.save(new AuditLog(event.orderId()));  // Saved correctly ✅
}
```

---

## Scenario 3: Async Event Listener

### The Problem with Synchronous Listeners
```
OrderService.placeOrder() → publishEvent()
  → sync call to EmailService.sendEmail() → Mailgun API call (300ms)
  → sync call to AnalyticsService.record() → Elasticsearch write (100ms)
  → sync call to LoyaltyService.addPoints() → DB write (50ms)

Total delay added to placeOrder: 450ms
User waits 450ms extra for things that don't affect their order confirmation
```

### Fix: @Async + @EventListener
```java
@SpringBootApplication
@EnableAsync
public class Application { }

@Component
public class OrderEmailListener {

    @Async("eventExecutor")  // use named thread pool
    @EventListener
    public void onOrderPlaced(OrderPlacedEvent event) {
        // Runs in a separate thread — placeOrder returns immediately
        emailService.sendOrderConfirmation(event.userId(), event.orderId());
    }
}

// BUT: @Async + @EventListener has a problem with transactions!
// The async thread starts BEFORE the main TX commits.
// If you read the Order from DB in the async thread, it may not exist yet.
```

### Correct Pattern: @Async + @TransactionalEventListener
```java
@Component
public class OrderEmailListener {

    // CORRECT ✅ — fires after commit, runs async
    @Async("eventExecutor")
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void onOrderPlaced(OrderPlacedEvent event) {
        // Fires only after TX commits (data is in DB)
        // Runs in async thread (non-blocking for caller)
        // Safe to read the Order from DB here — it's committed
        Order order = orderRepo.findById(event.orderId()).orElseThrow();
        emailService.sendConfirmation(order);
    }
}

@Configuration
public class AsyncConfig implements AsyncConfigurer {

    @Bean("eventExecutor")
    public Executor eventExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(5);
        executor.setMaxPoolSize(20);
        executor.setQueueCapacity(1000);
        executor.setThreadNamePrefix("event-");
        executor.setRejectedExecutionHandler(new CallerRunsPolicy()); // fallback
        executor.initialize();
        return executor;
    }

    // Exception handler for @Async — otherwise exceptions are swallowed!
    @Override
    public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() {
        return (ex, method, params) ->
            log.error("Async event listener error in {}: {}", method.getName(), ex.getMessage(), ex);
    }
}
```

---

## Trap 1: Exceptions in @EventListener Propagate to Publisher

### The Bug
```java
@Component
public class OrderAuditListener {

    @EventListener
    public void onOrderPlaced(OrderPlacedEvent event) {
        auditService.log(event.orderId());  // throws RuntimeException
    }
}

@Service
@Transactional
public class OrderService {
    public Order placeOrder(OrderRequest request) {
        Order order = orderRepo.save(new Order(request));
        eventPublisher.publishEvent(new OrderPlacedEvent(order.getId())); // ← exception propagates HERE
        // ^ RuntimeException from listener propagates up
        // → TX rolls back!
        // → Order NOT saved
        // → User gets 500 error
    }
}
```

### Fix: Isolate listener failures from publisher
```java
// Option 1: Catch in listener
@EventListener
public void onOrderPlaced(OrderPlacedEvent event) {
    try {
        auditService.log(event.orderId());
    } catch (Exception ex) {
        log.error("Audit failed for order {}: {}", event.orderId(), ex.getMessage());
        // Don't re-throw — listener failure must not affect the main flow
    }
}

// Option 2: Use @Async — async listener exceptions don't propagate to publisher
@Async
@EventListener
public void onOrderPlaced(OrderPlacedEvent event) {
    auditService.log(event.orderId()); // exception in async thread, not in publisher
}
// Note: configure AsyncUncaughtExceptionHandler to log these exceptions!
```

---

## Trap 2: No Ordering Guarantee for Multiple Listeners

### The Problem
```java
// Two listeners for the same event
@EventListener
public void onOrderPlaced_sendEmail(OrderPlacedEvent event) { ... }

@EventListener
public void onOrderPlaced_deductLoyalty(OrderPlacedEvent event) { ... }

// Order of execution: NOT GUARANTEED
// LoyaltyService might run before EmailService or after
// If they depend on each other: race condition
```

### Fix: @Order annotation
```java
@Component
public class OrderEmailListener {
    @EventListener
    @Order(1)  // runs first
    public void onOrderPlaced(OrderPlacedEvent event) { ... }
}

@Component
public class OrderLoyaltyListener {
    @EventListener
    @Order(2)  // runs after email
    public void onOrderPlaced(OrderPlacedEvent event) { ... }
}

// But: if listeners must depend on each other's outcome,
// reconsider whether they should be separate events or a saga.
```

---

## Advanced: Domain Events with Spring Data

```java
// Spring Data entities can publish events automatically on save
@Entity
public class Order extends AbstractAggregateRoot<Order> {

    @Enumerated(STRING)
    private OrderStatus status;

    public Order confirm() {
        this.status = OrderStatus.CONFIRMED;
        // Registers event on THIS entity — published by Spring Data on repo.save()
        registerDomainEvent(new OrderConfirmedEvent(this.id, this.userId));
        return this;
    }
}

@Service
@Transactional
public class OrderService {
    public Order confirmOrder(Long orderId) {
        Order order = orderRepo.findById(orderId).orElseThrow();
        order.confirm();
        return orderRepo.save(order);
        // save() → entity saved AND OrderConfirmedEvent published
        // → @TransactionalEventListener fires after commit
    }
}
// Domain event lives with the aggregate — cleaner DDD design
// No need to inject ApplicationEventPublisher in the service
```

---

## Quick Reference: Event Listener Types

| Annotation | When Fires | Transactional | Use For |
|---|---|---|---|
| `@EventListener` | When published (sync) | Joins publisher's TX | Audit, secondary writes in same TX |
| `@EventListener` + `@Async` | When published (async) | No TX | Fire-and-forget (email, push notifications) |
| `@TransactionalEventListener(AFTER_COMMIT)` | After TX commits (sync) | No TX (use REQUIRES_NEW) | Safe side effects (email, cache invalidation) |
| `@TransactionalEventListener` + `@Async` | After TX commits (async) | No TX | Non-blocking safe side effects |
| `@TransactionalEventListener(AFTER_ROLLBACK)` | After TX rollback | No TX | Compensating actions, alerts |

---

## Interview Cheat Sheet

> "@EventListener is synchronous and joins the publisher's transaction — perfect for secondary writes that must be in the same TX. @TransactionalEventListener with AFTER_COMMIT fires only after the DB transaction commits — this prevents the 'email sent but order rolled back' problem. When doing DB work in AFTER_COMMIT phase, use REQUIRES_NEW propagation — the original TX is gone. Combine @Async + @TransactionalEventListener for non-blocking side effects that are safe only after commit (email, push notifications). Exception in a synchronous @EventListener propagates to the publisher and can roll back the whole transaction — always catch in the listener or use @Async to isolate. Domain events via AbstractAggregateRoot keep event publishing co-located with the aggregate — cleaner than injecting ApplicationEventPublisher everywhere."
