# Q16: Microservices & Distributed Systems — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 25-30 minutes | **Frequency:** Every architect/principal round 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "We updated the inventory and charged the card. Then the order service crashed. Inventory decremented, card charged, no order created. Customer was billed for nothing." — Distributed transaction gone wrong.

---

## Scenario 1: Distributed Transaction Problem (Why 2PC Fails)

### The Problem
```
Microservices: OrderService, InventoryService, PaymentService

"Place Order" flow:
  1. Create order record        (OrderService DB)
  2. Decrement inventory        (InventoryService DB)
  3. Charge payment card        (PaymentService / Stripe)

If step 3 fails → must rollback steps 1 and 2
But: these are 3 separate databases, 3 separate services
     → No single @Transactional can span them!

Two-Phase Commit (2PC) in microservices:
  → Blocks all participants during the commit phase
  → If coordinator crashes mid-commit → all services hang
  → Network partitions make this unreliable
  → Practically abandoned in modern microservices
```

### The Fix: Saga Pattern

---

## Saga Pattern — Two Flavours

### Choreography Saga (Event-Driven, No Central Coordinator)

```
OrderService          InventoryService        PaymentService
     │                      │                      │
  Creates Order              │                      │
  Publishes ──────────► OrderCreated ──────────►    │
  OrderCreated               │                      │
     │               Decrements inventory            │
     │               Publishes ─────────────► InventoryReserved
     │                      │                      │
     │                      │               Charges payment
     │                      │               Publishes ──────►
     │                      │                       OrderCompleted

Compensating transactions (rollback path):
  PaymentFailed event:
    InventoryService listens → releases reservation
    OrderService listens → cancels order
```

```java
// OrderService
@KafkaListener(topics = "payment-failed")
public void onPaymentFailed(PaymentFailedEvent event) {
    orderRepo.findByOrderId(event.getOrderId())
             .ifPresent(order -> {
                 order.setStatus(OrderStatus.CANCELLED);
                 orderRepo.save(order);
                 // Publish event so other services compensate
                 kafkaTemplate.send("order-cancelled", new OrderCancelledEvent(order));
             });
}

// InventoryService
@KafkaListener(topics = "order-cancelled")
public void onOrderCancelled(OrderCancelledEvent event) {
    inventoryRepo.releaseReservation(event.getOrderId());
}
```

### Orchestration Saga (Central Coordinator, Spring State Machine / Temporal)

```java
@Service
public class PlaceOrderSaga {

    public OrderResult execute(OrderRequest request) {

        OrderId orderId = null;
        boolean inventoryReserved = false;

        try {
            // Step 1: Create order
            orderId = orderService.createOrder(request);

            // Step 2: Reserve inventory
            inventoryService.reserve(orderId, request.getItems());
            inventoryReserved = true;

            // Step 3: Charge payment
            paymentService.charge(orderId, request.getPayment());

            // All steps succeeded
            orderService.confirm(orderId);
            return OrderResult.success(orderId);

        } catch (PaymentException ex) {
            // Compensate: release inventory
            if (inventoryReserved) inventoryService.release(orderId);
            if (orderId != null) orderService.cancel(orderId);
            return OrderResult.failed("Payment declined");

        } catch (InventoryException ex) {
            // Compensate: cancel order (no inventory reserved yet)
            if (orderId != null) orderService.cancel(orderId);
            return OrderResult.failed("Out of stock");
        }
    }
}
```

### Which to Use?
```
Choreography: simpler, looser coupling, harder to debug (events scattered)
Orchestration: easier to trace & debug, central point of failure, tight coupling
Rule of thumb: < 4 services in a saga → choreography; ≥ 4 or complex rollback → orchestration
```

---

## Scenario 2: API Idempotency (Retry Without Double-Charge)

### The Problem
```
Client sends POST /orders (place order)
Network timeout after 5s — client doesn't know if request succeeded
Client retries → order created AGAIN → double charge
```

### Fix: Idempotency Keys
```java
@RestController
public class OrderController {

    @PostMapping("/orders")
    public ResponseEntity<Order> placeOrder(
            @RequestBody OrderRequest request,
            @RequestHeader("Idempotency-Key") String idempotencyKey) {

        // Check if this key was already processed
        Optional<OrderResult> existing = idempotencyStore.get(idempotencyKey);
        if (existing.isPresent()) {
            // Return the SAME response as the first call
            log.info("Duplicate request with key: {}", idempotencyKey);
            return ResponseEntity.ok(existing.get().getOrder());
        }

        // Process the order
        Order order = orderService.placeOrder(request);

        // Store result against idempotency key (TTL = 24h)
        idempotencyStore.save(idempotencyKey, new OrderResult(order), Duration.ofHours(24));

        return ResponseEntity.status(201).body(order);
    }
}

@Service
public class IdempotencyStore {
    private final RedisTemplate<String, OrderResult> redis;

    public void save(String key, OrderResult result, Duration ttl) {
        redis.opsForValue().set("idempotency:" + key, result, ttl);
    }

    public Optional<OrderResult> get(String key) {
        return Optional.ofNullable(redis.opsForValue().get("idempotency:" + key));
    }
}
```

### Client-Side Pattern
```java
// Client generates UUID once per logical operation
// Retries use the SAME UUID
String idempotencyKey = UUID.randomUUID().toString();

for (int attempt = 0; attempt < 3; attempt++) {
    try {
        return orderClient.placeOrder(request, idempotencyKey);
    } catch (SocketTimeoutException e) {
        // Safe to retry — server handles deduplication
        Thread.sleep(exponentialBackoff(attempt));
    }
}
```

---

## Scenario 3: Distributed Tracing — Finding the Slow Service

### The Problem
```
/api/checkout takes 8 seconds. Which of the 6 microservices is slow?
Without tracing: tail -f logs on 6 services, correlate timestamps manually → 2 hours of hell
```

### Fix: Micrometer Tracing + Zipkin/Jaeger
```java
// Spring Boot 3.x (Micrometer Tracing replaces Spring Cloud Sleuth)
```

```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-brave</artifactId>
</dependency>
<dependency>
    <groupId>io.zipkin.reporter2</groupId>
    <artifactId>zipkin-reporter-brave</artifactId>
</dependency>
```

```yaml
management:
  tracing:
    sampling:
      probability: 0.1   # trace 10% of requests in production
      # 1.0 = trace everything (only for debugging!)
spring:
  zipkin:
    base-url: http://zipkin:9411
```

```java
// Trace IDs are automatically propagated via HTTP headers:
// traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01

// Accessing trace ID in logs:
@GetMapping("/checkout")
public ResponseEntity<Order> checkout(@RequestBody CartRequest cart) {
    log.info("Processing checkout"); // → log includes traceId, spanId automatically
    // In Zipkin: can see full journey: checkout → inventory → payment → notification
    // → See exactly which service added the 8s delay
}
```

---

## Trap 1: Split-Brain in Distributed Caching (Stale Reads After Write)

### The Problem
```
Service A (Pod 1): reads User from Redis → user.plan = "FREE"
Service B (Pod 2): user upgrades → updates DB, updates Redis
Service A (Pod 1): processes request with stale "FREE" data
→ Features not unlocked even though user paid

Write-Behind / Write-Through cache:
  Time to propagate → depends on Redis replication / cache eviction
```

### Fix: Cache-Aside with Versioning
```java
public User getUser(Long userId) {
    String key = "user:" + userId;
    CachedUser cached = redis.opsForValue().get(key);

    if (cached != null) return cached.getUser();

    User user = userRepo.findById(userId).orElseThrow();
    redis.opsForValue().set(key, new CachedUser(user), 5, TimeUnit.MINUTES);
    return user;
}

// On update: evict AND publish invalidation event
@Transactional
public User updateUser(User user) {
    User saved = userRepo.save(user);
    redis.delete("user:" + user.getId());

    // Publish to all pods to evict their local caches (Caffeine L1)
    eventBus.publish(new CacheInvalidationEvent("user", user.getId()));
    return saved;
}

// Each pod subscribes to invalidation events
@EventListener
public void onCacheInvalidation(CacheInvalidationEvent event) {
    localCaffeineCache.invalidate(event.getCacheType() + ":" + event.getId());
}
```

---

## Trap 2: Temporal Coupling — Synchronous Chain of Service Calls

### The Problem
```
CheckoutController calls:
  → InventoryService  (sync HTTP, 100ms)
  → PricingService    (sync HTTP, 80ms)
  → TaxService        (sync HTTP, 60ms)
  → PaymentService    (sync HTTP, 300ms)
  → NotificationService (sync HTTP, 200ms)

Total: 740ms sequential
Availability: 99% × 99% × 99% × 99% × 99% = 95% (5% downtime from chaining!)
```

### Fix 1: Parallelise Independent Calls
```java
@Service
public class CheckoutService {

    public CheckoutResult checkout(Cart cart) {
        // Inventory and Pricing are independent — run in parallel
        CompletableFuture<InventoryResult> inventoryFuture =
            CompletableFuture.supplyAsync(() -> inventoryClient.reserve(cart));

        CompletableFuture<PriceResult> priceFuture =
            CompletableFuture.supplyAsync(() -> pricingClient.calculatePrice(cart));

        // Wait for both (parallel, not sequential)
        InventoryResult inventory = inventoryFuture.join();  // ~100ms
        PriceResult price = priceFuture.join();              // ~80ms (overlapped)
        // Total so far: max(100, 80) = 100ms — not 180ms

        TaxResult tax = taxClient.calculate(price);          // 60ms — depends on price

        PaymentResult payment = paymentClient.charge(price.getTotal() + tax.getAmount());

        // Notification is fire-and-forget — don't block checkout on it!
        CompletableFuture.runAsync(() -> notificationClient.sendConfirmation(payment));

        return new CheckoutResult(inventory, payment);
        // Total: 100 + 60 + 300 = 460ms (vs 740ms sequential, 38% faster)
    }
}
```

### Fix 2: Event-Driven Decoupling
```
Synchronous: Checkout → Notification (blocks user response)
Event-driven: Checkout publishes "OrderPlaced" event
              NotificationService subscribes → sends email asynchronously
              → User gets response immediately
              → Email sent in background, independently retried if it fails
```

---

## Trap 3: Service Discovery and Stale Registry (Kubernetes)

### The Problem
```
Pod A crashes → Kubernetes terminates it
Service registry (Eureka/Consul) still has Pod A for up to 90s (default heartbeat eviction)
Load balancer sends 1/3 of requests to dead Pod A
→ 1 in 3 requests fail with connection refused
→ Circuit breaker opens → whole feature appears down
```

### Fix: Health Check + Graceful Deregistration
```yaml
# application.yml
eureka:
  instance:
    lease-renewal-interval-in-seconds: 5     # heartbeat every 5s (default: 30s)
    lease-expiration-duration-in-seconds: 15  # evict after 15s of no heartbeat (default: 90s)
  client:
    registry-fetch-interval-seconds: 5        # refresh registry every 5s (default: 30s)
```

```java
// Kubernetes: use readiness probe to control traffic
// Ready → receives traffic; Not Ready → removed from Service endpoints (no stale issue)
// Spring Boot Actuator exposes readiness probe automatically:

management:
  endpoint:
    health:
      probes:
        enabled: true   # /actuator/health/readiness + /actuator/health/liveness
```

```yaml
# kubernetes deployment.yaml
readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  failureThreshold: 3
# Pod removed from endpoints within 15s of going unhealthy
# Much faster than Eureka's 90s default
```

---

## Advanced Scenario: CQRS — Separate Read and Write Models

### The Problem
```
Single OrderService handles:
  - Write: placeOrder, updateOrder, cancelOrder (requires strong consistency)
  - Read: getOrderHistory, searchOrders, getOrderSummary (needs fast, flexible queries)

Same DB table: queries for reads (complex JOINs, filters) lock rows for writes
→ Write latency spikes during reporting queries
→ Schema optimised for writes = bad for reads and vice versa
```

### Fix: CQRS Pattern
```java
// Write side: normalised DB, strong consistency, JPA
@Service
public class OrderCommandService {
    @Transactional
    public Order placeOrder(PlaceOrderCommand cmd) {
        Order order = new Order(cmd);
        Order saved = orderRepo.save(order);  // write to MySQL

        // Publish event for read-side sync
        eventPublisher.publish(new OrderPlacedEvent(saved));
        return saved;
    }
}

// Read side: denormalised, optimised for queries, Elasticsearch/Read DB
@Service
public class OrderQueryService {
    public OrderSummaryPage searchOrders(OrderSearchQuery query) {
        // Query denormalised read model (Elasticsearch, read replica, etc.)
        return elasticsearchRepo.searchOrders(
            query.getUserId(), query.getStatus(),
            query.getDateRange(), query.getPageable()
        );
    }
}

// Sync write → read model
@KafkaListener(topics = "order-events")
public void syncReadModel(OrderPlacedEvent event) {
    OrderDocument doc = OrderDocument.from(event);
    elasticsearchRepo.save(doc);  // update read model asynchronously
}
```

```
Trade-off: eventual consistency between write and read models
           User places order → order in MySQL immediately
           Search results updated ~100-500ms later
           Acceptable for order history, NOT for payment confirmation
```

---

## Interview Cheat Sheet

> "Distributed transactions are solved with Saga pattern, not 2PC — 2PC creates blocking distributed locks that fail badly on network partitions. For choreography sagas, compensating events handle rollback; for orchestration, a coordinator explicitly calls compensation steps. Idempotency keys on all write endpoints make retries safe — client generates UUID once, retries use same key, server deduplicates via Redis. For temporal coupling: parallelise independent downstream calls with CompletableFuture and decouple fire-and-forget calls with events. In Kubernetes, use readiness probes instead of relying on Eureka TTLs — K8s removes pods from endpoints within seconds vs Eureka's 90s default. CQRS solves the read-write contention problem but introduces eventual consistency — the key is being explicit about which operations require strong consistency and which tolerate lag."
