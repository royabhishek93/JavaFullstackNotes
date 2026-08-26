# Pub-Sub Event Bus — Complete LLD Interview Guide

**Interview Duration: 40 min | Difficulty: Hard | Must-Know: ⭐⭐⭐⭐ | 15-YOE Focus: At-Least-Once + Retry + Dead Letter + Async Dispatch**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                   PUB-SUB EVENT BUS                             │
 │                                                                  │
 │  PUBLISHERS                 EVENT BUS              SUBSCRIBERS  │
 │  ┌──────────┐              ┌──────────────────┐   ┌──────────┐ │
 │  │ OrderSvc │─publish()───►│  Topic: "orders" │──►│ InvSvc   │ │
 │  │ PaySvc   │              │  Topic: "payment"│──►│ EmailSvc │ │
 │  │ AuthSvc  │              │  Topic: "users"  │──►│ AuditSvc │ │
 │  └──────────┘              └────────┬─────────┘   └──────────┘ │
 │                                     │                            │
 │                            ┌────────▼─────────┐                 │
 │                            │ Dispatch Engine  │                 │
 │                            │ • ThreadPool     │                 │
 │                            │ • Retry+backoff  │                 │
 │                            │ • DLQ on failure │                 │
 │                            └──────────────────┘                 │
 │                                                                  │
 │  TOPIC SUBSCRIPTION MAP:                                        │
 │  ┌──────────────────────────────────────────────────────────┐  │
 │  │ "orders"  → [InventoryHandler, EmailHandler, Analytics]  │  │
 │  │ "payment" → [LedgerHandler, FraudDetector, Notifier]     │  │
 │  │ "users"   → [AuditHandler, RecommendationEngine]         │  │
 │  └──────────────────────────────────────────────────────────┘  │
 │                                                                  │
 │  DELIVERY SEMANTICS:                                            │
 │  ┌──────────────────────────────────────────────────────────┐  │
 │  │  At-most-once:  fire and forget. Fastest. May lose msgs  │  │
 │  │  At-least-once: retry on failure. May duplicate msgs     │  │
 │  │  Exactly-once:  idempotent consumer + dedup store        │  │
 │  └──────────────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────────────┘

 RETRY WITH EXPONENTIAL BACKOFF:
 ┌──────────────────────────────────────────────────────────────────┐
 │  Event published → Subscriber A fails                           │
 │                                                                  │
 │  Attempt 1: immediate        → FAIL                             │
 │  Attempt 2: wait 1s          → FAIL                             │
 │  Attempt 3: wait 2s          → FAIL                             │
 │  Attempt 4: wait 4s          → FAIL (maxRetries reached)        │
 │                         │                                        │
 │                         ▼                                        │
 │              [Dead Letter Queue]  ← parked for manual review    │
 │                                                                  │
 │  Other subscribers (B, C): unaffected by A's failure            │
 └──────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Let me clarify.

Functional:
- Publishers post events to named topics
- Subscribers register handlers for topics — multiple subscribers per topic
- Event delivery: call each subscriber's handler when event is published
- Retry: if a handler fails, retry with exponential backoff
- Dead Letter Queue: after maxRetries exhausted, park the event for inspection
- Unsubscribe: ability to remove a handler

Non-functional:
- Async delivery by default — publisher shouldn't block waiting for all subscribers
- Subscriber failure must not affect other subscribers for the same event
- Thread safety — multiple publishers and subscribers concurrently
- Ordered delivery within a topic? Nice to have but complex — let's discuss trade-offs

The key design question: do we deliver synchronously (simple, publisher blocks) or asynchronously (complex, but publisher doesn't block)? And what delivery guarantee do we provide?"

---

### Phase 3 — Implementation

```java
// ─── Event ───────────────────────────────────────────────────────
public class Event<T> {
    private final String eventId;
    private final String topic;
    private final T      payload;
    private final Instant publishedAt;
    private int          retryCount;

    public Event(String topic, T payload) {
        this.eventId     = UUID.randomUUID().toString();
        this.topic       = topic;
        this.payload     = payload;
        this.publishedAt = Instant.now();
        this.retryCount  = 0;
    }

    public Event<T> withIncrementedRetry() {
        Event<T> copy = new Event<>(topic, payload);
        copy.retryCount = this.retryCount + 1;
        return copy;
    }

    public String getEventId()    { return eventId; }
    public String getTopic()      { return topic; }
    public T      getPayload()    { return payload; }
    public int    getRetryCount() { return retryCount; }
}

// ─── Subscriber Handler ─────────────────────────────────────────
@FunctionalInterface
public interface EventHandler<T> {
    void handle(Event<T> event) throws Exception;
}

// ─── Subscription ───────────────────────────────────────────────
public class Subscription<T> {
    private final String          subscriptionId;
    private final String          topic;
    private final EventHandler<T> handler;
    private final String          subscriberName;

    public Subscription(String topic, EventHandler<T> handler, String subscriberName) {
        this.subscriptionId = UUID.randomUUID().toString();
        this.topic          = topic;
        this.handler        = handler;
        this.subscriberName = subscriberName;
    }

    public String getSubscriptionId()   { return subscriptionId; }
    public String getTopic()            { return topic; }
    public EventHandler<T> getHandler() { return handler; }
    public String getSubscriberName()   { return subscriberName; }
}

// ─── Dead Letter Queue ───────────────────────────────────────────
public class DeadLetterQueue {
    private final BlockingQueue<DeadLetterEntry> dlq = new LinkedBlockingQueue<>();

    public void enqueue(Event<?> event, String subscriber, Throwable cause) {
        dlq.offer(new DeadLetterEntry(event, subscriber, cause.getMessage(), Instant.now()));
    }

    public List<DeadLetterEntry> drain() {
        List<DeadLetterEntry> entries = new ArrayList<>();
        dlq.drainTo(entries);
        return entries;
    }

    public int size() { return dlq.size(); }
}

public record DeadLetterEntry(Event<?> event, String subscriber,
                               String errorMessage, Instant failedAt) {}

// ─── Event Bus (Core) ────────────────────────────────────────────
public class EventBus {
    // Topic → list of subscriptions
    private final ConcurrentHashMap<String, CopyOnWriteArrayList<Subscription<?>>>
        subscriptions = new ConcurrentHashMap<>();

    private final ExecutorService    dispatcher   = Executors.newFixedThreadPool(10);
    private final ScheduledExecutorService retryScheduler = Executors.newScheduledThreadPool(4);
    private final DeadLetterQueue    dlq;
    private final int                maxRetries   = 3;
    private final long               baseDelayMs  = 1000; // 1 second base for backoff

    // Deduplication store (for idempotent / exactly-once delivery)
    private final Set<String> processedEventIds = Collections.newSetFromMap(
        new ConcurrentHashMap<>());

    public EventBus(DeadLetterQueue dlq) {
        this.dlq = dlq;
    }

    // ─── Subscribe ───────────────────────────────────────────────
    @SuppressWarnings("unchecked")
    public <T> Subscription<T> subscribe(String topic, String subscriberName,
                                          EventHandler<T> handler) {
        subscriptions.computeIfAbsent(topic, k -> new CopyOnWriteArrayList<>());
        Subscription<T> sub = new Subscription<>(topic, handler, subscriberName);
        subscriptions.get(topic).add(sub);
        System.out.println("Subscribed: " + subscriberName + " → topic: " + topic);
        return sub;
    }

    // ─── Unsubscribe ─────────────────────────────────────────────
    public void unsubscribe(Subscription<?> subscription) {
        List<Subscription<?>> subs = subscriptions.get(subscription.getTopic());
        if (subs != null) subs.removeIf(s -> s.getSubscriptionId()
            .equals(subscription.getSubscriptionId()));
    }

    // ─── Publish ─────────────────────────────────────────────────
    public <T> void publish(String topic, T payload) {
        Event<T> event = new Event<>(topic, payload);
        List<Subscription<?>> subs = subscriptions.getOrDefault(topic,
            new CopyOnWriteArrayList<>());

        if (subs.isEmpty()) {
            System.out.println("No subscribers for topic: " + topic);
            return;
        }

        System.out.printf("Publishing event %s to topic '%s' (%d subscribers)%n",
            event.getEventId(), topic, subs.size());

        // Dispatch to each subscriber independently and asynchronously
        for (Subscription<?> sub : subs) {
            dispatcher.submit(() -> deliverWithRetry(event, sub, 0));
        }
    }

    // ─── Deliver with Retry ──────────────────────────────────────
    @SuppressWarnings("unchecked")
    private <T> void deliverWithRetry(Event<T> event, Subscription<?> sub, int attempt) {
        EventHandler<T> handler = (EventHandler<T>) sub.getHandler();
        try {
            handler.handle(event);
            System.out.printf("[%s] handled event %s successfully (attempt %d)%n",
                sub.getSubscriberName(), event.getEventId(), attempt + 1);
        } catch (Exception ex) {
            int nextAttempt = attempt + 1;
            System.err.printf("[%s] failed event %s (attempt %d): %s%n",
                sub.getSubscriberName(), event.getEventId(), nextAttempt, ex.getMessage());

            if (nextAttempt < maxRetries) {
                long delayMs = baseDelayMs * (1L << attempt); // exponential: 1s, 2s, 4s
                System.out.printf("[%s] retrying in %dms%n",
                    sub.getSubscriberName(), delayMs);
                retryScheduler.schedule(
                    () -> deliverWithRetry(event, sub, nextAttempt),
                    delayMs, TimeUnit.MILLISECONDS
                );
            } else {
                System.err.printf("[%s] max retries exhausted → DLQ%n",
                    sub.getSubscriberName());
                dlq.enqueue(event, sub.getSubscriberName(), ex);
            }
        }
    }

    // ─── Publish synchronously (blocking — for critical paths) ──
    public <T> Map<String, Boolean> publishSync(String topic, T payload) {
        Event<T> event = new Event<>(topic, payload);
        List<Subscription<?>> subs = subscriptions.getOrDefault(topic,
            new CopyOnWriteArrayList<>());

        Map<String, Boolean> results = new LinkedHashMap<>();
        for (Subscription<?> sub : subs) {
            try {
                ((EventHandler<T>) sub.getHandler()).handle(event);
                results.put(sub.getSubscriberName(), true);
            } catch (Exception ex) {
                results.put(sub.getSubscriberName(), false);
            }
        }
        return results;
    }

    public void shutdown() {
        dispatcher.shutdown();
        retryScheduler.shutdown();
    }
}

// ─── Usage Example ───────────────────────────────────────────────
class UsageDemo {
    public static void main(String[] args) throws InterruptedException {
        DeadLetterQueue dlq = new DeadLetterQueue();
        EventBus bus = new EventBus(dlq);

        // Subscribe
        bus.subscribe("orders", "InventoryService",
            (Event<Order> e) -> {
                System.out.println("Inventory: deducting stock for " + e.getPayload());
            });

        bus.subscribe("orders", "EmailService",
            (Event<Order> e) -> {
                if (e.getRetryCount() == 0) throw new RuntimeException("Email server down");
                System.out.println("Email: sending confirmation for " + e.getPayload());
            });

        bus.subscribe("orders", "AnalyticsService",
            (Event<Order> e) -> {
                System.out.println("Analytics: recording order " + e.getPayload());
            });

        // Publish
        bus.publish("orders", new Order("ORD-001", "userId-123", 599.0));
        // InventoryService: handles immediately
        // EmailService: fails attempt 1 → retries at 1s → succeeds at attempt 2
        // AnalyticsService: handles immediately
        // Both InventoryService and AnalyticsService are NOT affected by EmailService's failure

        Thread.sleep(5000); // wait for retries
        System.out.println("DLQ size: " + dlq.size()); // should be 0 after retry succeeds
    }
}
```

---

## Component Choices

```
COMPONENT             CHOICE                   WHY
──────────────────────────────────────────────────────────────────────
Subscriber storage    CopyOnWriteArrayList     Subscriptions mostly read
                                               (many dispatches, rare sub/unsub).
                                               Thread-safe for iteration.
                                               No ConcurrentModification
                                               during dispatch loop.

Async dispatch        Fixed ThreadPool(10)     Publisher returns instantly.
                                               10 threads handle all topics.
                                               Tune thread count to CPU cores
                                               and expected subscriber latency.

Retry scheduling      ScheduledExecutorService Exponential backoff without
                                               blocking the dispatch thread.
                                               Thread is freed between retries.

Subscriber isolation  Per-subscriber dispatch  Subscriber A's failure/retry
                                               does NOT block Subscriber B.
                                               Each gets its own Callable.

DLQ                   BlockingQueue            Bounded, thread-safe.
                                               drainTo() for batch processing.
                                               In production: a separate
                                               Kafka topic or DB table.

Sync vs Async publish Both modes available    Async: for high-throughput
                                               non-critical events.
                                               Sync: for critical events
                                               where publisher needs outcome.
```

---

## Senior Trap Questions

**Q1: "How do you guarantee at-least-once delivery if the app crashes mid-dispatch?"**
```
In-memory EventBus: events in the ThreadPool queue are LOST on crash.
No persistence = at-most-once at best.

For at-least-once:
  Option 1: Transactional outbox
    Publisher writes event to DB outbox table (same TX as business data).
    Outbox reader polls + dispatches.
    Even on crash: DB has the event, reader re-dispatches after restart.

  Option 2: Durable queue (Kafka/SQS)
    Replace in-memory bus with Kafka.
    Events on disk. Consumer offset tracks progress.
    Crash: consumer restarts from last committed offset.

  In-memory EventBus is fine for:
    - Within a single JVM, non-critical notifications
    - Spring @EventListener use case (same JVM, same TX)
    
  For cross-service, cross-JVM, crash-safe: use Kafka.
```

**Q2: "Multiple publishers fire the same event type. Subscriber processes twice. How do you prevent that?"**
```
This is the idempotency / exactly-once problem.

Deduplication via eventId:
  Each Event has a UUID eventId.
  Subscriber checks: have I seen this eventId before?
  If yes: skip (idempotent).
  If no: process + record eventId.

  // In subscriber:
  if (processedIds.contains(event.getEventId())) return; // skip duplicate
  process(event);
  processedIds.add(event.getEventId()); // mark as seen

Storage for processedIds:
  In-memory Set: fast but lost on restart.
  Redis SET with TTL: distributed, survives restart, auto-expires old IDs.
  DB table: durable but slower.

For payment events: always use Redis SET with TTL=24h.
For audit logs: duplicates are acceptable (idempotency less critical).
```

**Q3: "One subscriber is very slow (takes 5 seconds per event). Does this affect other subscribers?"**
```
With independent async dispatch:
  Each subscriber gets their own Runnable in the ThreadPool.
  Slow subscriber runs on thread T3. Other subscribers run on T1, T2.
  Slow subscriber does NOT block other subscribers. ✅

BUT: if there are 10 threads in the pool and 10+ slow subscribers all running,
     new events queue up waiting for a free thread.
     This is backpressure.

Fix: per-subscriber thread pool (dedicated threads for known-slow subscribers)
  SlowReportingService: dedicated pool of 2 threads.
  Fast services: shared pool of 10 threads.
  Slow service can't steal threads from fast services.

Or: circuit breaker on slow subscriber.
  If subscriber consistently takes >2s: mark it as degraded.
  Skip delivery (at-most-once) or queue to DLQ until it recovers.
```

---

## Failure Modes

```
SCENARIO              WHAT HAPPENS             FIX
────────────────────────────────────────────────────────────────────
Thread pool exhausted Events queue up          Bounded queue with rejection
due to slow subs      → publisher backs up     policy. Alert on queue depth.
                                               Per-subscriber thread pools.

Retry storm           Many events fail         Exponential backoff + jitter.
                      simultaneously           Spread retries over time.
                      → retry queue explodes   Max concurrent retries cap.

DLQ grows unbounded   Memory pressure /        Monitor DLQ size. Alert at
                      silent message loss      threshold. Bounded DLQ with
                                               overflow → external storage.

Event ordering        Async dispatch may       For ordered delivery: use
required but broken   deliver E2 before E1    single-threaded executor per
                                               topic (lose parallelism) or
                                               partition key + ordered queue.
```

---

## Interview Cheat Sheet

> "A Pub-Sub event bus decouples publishers from subscribers — the publisher doesn't know who's listening, and subscriber failures don't affect the publisher. The core design: ConcurrentHashMap of topic → CopyOnWriteArrayList of subscribers, async dispatch via a ThreadPool so the publisher returns immediately. Critical: each subscriber gets its own async Callable so one slow or failing subscriber doesn't block others. Retry uses exponential backoff via ScheduledExecutorService: 1s, 2s, 4s delays. After maxRetries, park to DLQ. The at-least-once guarantee trap: an in-memory bus loses events on crash. For crash-safe delivery you need persistence — transactional outbox (write event to DB in same TX as business data) or Kafka. Idempotency for exactly-once: check eventId against a Redis SET before processing; TTL=24h auto-expires old IDs."
