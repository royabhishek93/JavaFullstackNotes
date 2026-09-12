# Backpressure — When Your Consumer Can't Keep Up with Your Producer
### Why Fast Producers Crash Slow Consumers and How Reactive Streams Solve It

---

## PART 1 — THE STUDENT CONVERSATION

**"Our service crashes every time there's a traffic spike. We're losing messages. What's going on?"**

Think of a fire hose and a garden watering can.

The fire hose (producer) blasts water at 500 liters/second. The watering can (consumer) can only accept 2 liters/second.

**Without backpressure:** water overflows the can and makes a mess everywhere. In software: the in-memory buffer fills up, you get an OutOfMemoryError, the consumer crashes, and you lose all the buffered messages.

**With backpressure:** the watering can signals "slow down — I can only take 2 liters/second." The hose throttles to 2 liters/second. Nobody drowns. The watering can isn't overwhelmed.

In distributed systems, the "signal" travels differently depending on the architecture:

- **Same process (reactive streams):** the subscriber literally calls `request(N)` — "give me N more items when I'm ready"
- **Across services (Kafka):** the consumer simply stops polling. Kafka holds the messages. The consumer resumes at its own pace. The "signal" is just the absence of polling.
- **HTTP services:** the downstream returns HTTP 429 (Too Many Requests) or the connection queue fills and returns 503

The producer-consumer speed mismatch is one of the most common causes of production outages. You'll be asked about it in every system design interview that involves any form of event processing.

---

## PART 2 — THE PRODUCER-CONSUMER MISMATCH VISUALIZED

### The Problem — Unbounded Buffer Overflow

```
Scenario: Order events during a flash sale

Producer (order events):  10,000 orders/second
Consumer (fraud checks):   1,000 checks/second
Net accumulation:          9,000 messages/second

Without backpressure (in-memory queue):
┌─────────────────────────────────────────────────────────────────┐
│ t=0s:    Buffer: [        ] (empty, 0 messages)                 │
│ t=10s:   Buffer: [■■■■■■■■] (90,000 messages, ~90MB)            │
│ t=60s:   Buffer: [■■■■■■■■] (540,000 messages, ~540MB)          │
│ t=120s:  Buffer: OVERFLOW → OOM → CRASH → ALL MESSAGES LOST    │
│                                                                 │
│ 9,000 msg/sec × 3600 sec (1 hour) = 32.4 MILLION messages      │
│ At 1KB avg: 32.4GB → OOM long before that                      │
└─────────────────────────────────────────────────────────────────┘

With Kafka as the buffer:
┌─────────────────────────────────────────────────────────────────┐
│ t=0s:    Kafka topic: [        ] (empty)                        │
│ t=60s:   Kafka topic: [■■■■■■■■] (540,000 messages on DISK)    │
│ t=120s:  Kafka topic: [■■■■■■■■■■■■■■■■] (1.08M messages)      │
│                                                                 │
│ Consumer reads at 1,000/sec regardless of production rate      │
│ Kafka retains messages for 7 days (configurable)               │
│ Messages NOT lost — just delayed                               │
│                                                                 │
│ Tradeoff: Consumer is 9,000/sec behind                         │
│           After 1 hour of spike: 32.4M messages in lag         │
│           Catch-up time at 1K/sec: 9 hours (need to autoscale!) │
└─────────────────────────────────────────────────────────────────┘
```

### Reactive Streams — The Pull Model

```
PUSH model (no backpressure) — producer controls the rate:
  Producer → [item1, item2, item3, item4, item5...] → Consumer
             ↑ Producer decides when to send
             ↑ Consumer has no say
             ↑ Result: overwhelmed consumer, OOM

PULL model (backpressure) — consumer controls the rate:
  Consumer → "request(3)" → Producer
  Producer → [item1, item2, item3] → Consumer
  Consumer processes items 1, 2, 3...
  Consumer → "request(3)" → Producer  (when ready for more)
  
  Key insight: Producer CANNOT send item4 until Consumer asks for it.
  The consumer paces the entire pipeline.

Reactive Streams specification (Java):
  interface Publisher<T>  { void subscribe(Subscriber<T> s); }
  interface Subscriber<T> {
    void onSubscribe(Subscription s);   // called once, gives you the handle
    void onNext(T item);                // called for each item
    void onError(Throwable t);
    void onComplete();
  }
  interface Subscription  {
    void request(long n);  // "I want n more items"
    void cancel();
  }
  
  Project Reactor, RxJava, Akka Streams all implement this spec.
```

### Project Reactor — Correct vs Incorrect Usage

```java
// ❌ WRONG: flatMap with no concurrency limit — OOM!
Flux.range(1, 1_000_000)
    .flatMap(i -> callSlowDownstreamService(i))
    // flatMap creates 1,000,000 concurrent subscriptions immediately
    // Each holds resources, pending HTTP connections, etc.
    // Result: OutOfMemoryError
    .subscribe();

// ✅ RIGHT: concatMap — processes one at a time (sequential, full backpressure)
Flux.range(1, 1_000_000)
    .concatMap(i -> callSlowDownstreamService(i))
    // Waits for each to complete before starting next
    // Throughput = 1 / downstream_latency per second
    // Use when order matters and throughput requirement is low
    .subscribe();

// ✅ RIGHT: flatMap with concurrency cap — bounded parallelism
Flux.range(1, 1_000_000)
    .flatMap(i -> callSlowDownstreamService(i), 10)
    //                                           ↑ max 10 concurrent!
    // When 10 in-flight, producer WAITS until one completes
    // Good balance: throughput × 10, memory bounded
    .subscribe();

// ✅ RIGHT: explicit request-based pull model
source.subscribe(new BaseSubscriber<Order>() {
    @Override
    protected void hookOnSubscribe(Subscription subscription) {
        request(10);  // "I'm ready for 10 items to start"
    }

    @Override
    protected void hookOnNext(Order order) {
        processOrder(order);
        // After processing each item, ask for one more
        // Producer cannot send more until we ask
        request(1);
    }
});
```

### Kafka Consumer — Natural Backpressure via Poll Loop

```java
// Kafka consumer implements backpressure intrinsically
KafkaConsumer<String, Order> consumer = new KafkaConsumer<>(props);
consumer.subscribe(List.of("orders"));

while (running) {
    // poll() blocks up to 100ms waiting for records
    // If processing loop is slow, we poll LESS FREQUENTLY
    // Kafka broker sees reduced poll frequency → knows consumer is busy
    ConsumerRecords<String, Order> records = consumer.poll(Duration.ofMillis(100));
    
    for (ConsumerRecord<String, Order> record : records) {
        // If this is slow (say 500ms per record):
        //   Next poll happens after 500ms × batch_size
        //   Consumer naturally slows its consumption rate
        processOrder(record.value());
    }
    
    consumer.commitSync();  // commit only after processing entire batch
}

// ─────────────────────────────────────────────────────────
// Key Kafka backpressure configs:
//   max.poll.records=500           // max items per poll (memory control)
//   max.poll.interval.ms=300000    // if no poll in 5min → rebalance
//   fetch.max.bytes=52428800       // max 50MB per fetch
// ─────────────────────────────────────────────────────────

// Consumer lag monitoring (Prometheus + kafka-exporter):
// kafka_consumer_group_lag{topic="orders", partition="0"} = 45000
//
// Alert: if lag > 100,000 → trigger autoscale
// HPA custom metric: kafka_consumer_lag_messages
```

### Backpressure Strategy Comparison

```
Strategy 1: DROP (lose messages)
  Producer → [■■■■■■■] → [BUFFER max=1000] → Consumer
  When buffer full: DROP new messages, return error to producer
  
  Use when: analytics events, logging, metrics (loss acceptable)
  Don't use when: financial transactions, order events

Strategy 2: BLOCK PRODUCER (slow producer down)
  Producer → [■■■■■■■] → [BUFFER max=1000] → Consumer
  When buffer full: producer.send() BLOCKS until space available
  
  Use when: internal same-datacenter service calls, batch jobs
  Don't use when: user-facing requests (blocking = timeout)

Strategy 3: EXTERNAL DURABLE QUEUE (Kafka/SQS)
  Producer → Kafka → Consumer (at its own pace)
  Buffer is disk-backed, virtually unlimited, replicated
  
  Use when: most production event-driven systems
  Cost: operational overhead of Kafka cluster

Strategy 4: AUTOSCALE CONSUMER
  Kafka lag > threshold → spin up more consumer pods
  10 consumers instead of 1 → 10x throughput
  
  Use when: burst traffic patterns (flash sales, events)
  Kubernetes HPA custom metric: kafka_consumer_lag_messages

Strategy 5: CIRCUIT BREAKER ON PRODUCER
  Downstream queue full → producer opens circuit → returns 503
  Client sees: HTTP 503 + Retry-After: 30
  
  Use when: want to surface pressure to callers (rate limiting intent)
```

---

## PART 3 — INTERNALS: REAL CONFIGS AND PRODUCTION NUMBERS

### Kafka Topic Partitioning for Throughput Scaling

```
Throughput scaling formula:
  max_throughput = partitions × (consumer_throughput_per_instance)
  
Example:
  Fraud check service: 1,000 checks/second per instance
  Target throughput:   10,000 checks/second
  Required consumers:  10
  Required partitions: ≥ 10 (one consumer per partition max in a group)

Kafka topic configuration:
  bin/kafka-topics.sh --create \
    --topic orders \
    --partitions 20 \           ← provision 20 (headroom for future growth)
    --replication-factor 3 \    ← 3 replicas for durability
    --config retention.ms=604800000  # 7 days retention

  Producer partition key: order_id (consistent hashing → same order 
  always goes to same partition → ordering guaranteed per order)

Consumer group:
  group.id = "fraud-check-service"
  Each instance gets a subset of partitions automatically
  Adding instances → Kafka rebalances partitions across group
```

### Kubernetes HPA on Custom Kafka Lag Metric

```yaml
# prometheus-adapter ConfigMap: expose kafka_consumer_lag as K8s metric
apiVersion: v1
kind: ConfigMap
metadata:
  name: custom-metrics-config
data:
  config.yaml: |
    rules:
    - seriesQuery: 'kafka_consumer_group_lag{topic="orders"}'
      resources:
        overrides:
          namespace: {resource: "namespace"}
      name:
        matches: "kafka_consumer_group_lag"
        as: "kafka_consumer_lag_messages"
      metricsQuery: 'sum(kafka_consumer_group_lag{topic="orders"}) by (namespace)'

---
# HPA targeting the custom metric
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: fraud-check-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: fraud-check-service
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: External
    external:
      metric:
        name: kafka_consumer_lag_messages
      target:
        type: AverageValue
        averageValue: "10000"   # Scale up when avg lag > 10K messages
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60    # Don't scale up more than once/min
      policies:
      - type: Pods
        value: 4                        # Add at most 4 pods at a time
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300   # Wait 5 min before scaling down
```

### Project Reactor — Practical Production Patterns

```java
@Service
public class OrderProcessingService {

    // Pattern: bounded flatMap for parallel processing with backpressure
    public Flux<ProcessedOrder> processOrders(Flux<Order> orders) {
        return orders
            .flatMap(
                order -> fraudCheckService.check(order)  // async, returns Mono<>
                    .timeout(Duration.ofMillis(500))       // don't wait forever
                    .onErrorReturn(FraudResult.UNKNOWN),  // fail open
                16  // max 16 concurrent fraud checks (bounded!)
            )
            .filter(result -> result.isApproved())
            .flatMap(
                order -> paymentService.charge(order),
                4   // payments: tighter concurrency (external API rate limits)
            );
    }

    // Pattern: rate limiting a Flux with delayElements
    public Flux<SmsNotification> sendSmsNotifications(Flux<Order> orders) {
        return orders
            .delayElements(Duration.ofMillis(10))  // max 100 SMS/second
            .flatMap(order -> smsGateway.send(order.getPhone(), "Order confirmed"),
                5);  // 5 concurrent × 100/sec rate = 500 SMS/sec total max
    }
}
```

### Bounded Queue with Block-on-Full (Java)

```java
// Use when: internal producer-consumer in same JVM (batch processing)
BlockingQueue<Order> queue = new LinkedBlockingQueue<>(10_000);  // max 10K

// Producer thread — blocks when queue is full
Thread producer = new Thread(() -> {
    for (Order order : orderSource) {
        queue.put(order);  // BLOCKS if queue is full — natural backpressure!
    }
});

// Consumer thread — processes at its own pace
Thread consumer = new Thread(() -> {
    while (!done || !queue.isEmpty()) {
        Order order = queue.poll(100, TimeUnit.MILLISECONDS);
        if (order != null) processOrder(order);
    }
});

// Result:
//   If consumer is slow: queue fills up → producer.put() blocks
//   Producer slows to match consumer speed automatically
//   Memory bounded to: 10,000 × avg_order_size = controllable
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your notification service consumes from a Kafka topic. During a large sports event, 1 million notifications are produced in 10 seconds. Your consumer can only process 10,000 per second. What happens and how do you handle it?"

**You:** "With Kafka as the buffer, those 1 million notifications are safely written to disk. The consumer sees normal Kafka consumer lag — it has 1 million messages to catch up on. Processing at 10K/sec, it takes 100 seconds to catch up — so notifications are delivered up to 100 seconds late. They're not lost, just delayed.

Whether that's acceptable depends on the notification type. If it's a 'your team just scored' notification, 100 seconds late is useless. If it's a promotional push, fine.

Here's how I'd handle this properly:

**Partition-based horizontal scaling:** First, ensure the topic has enough partitions. If I want to scale to 10 consumer instances, I need at least 10 partitions. With 10 instances at 10K/sec each, I get 100K/sec throughput — catch-up time drops to 10 seconds. With 20 partitions and 20 instances: 200K/sec, 5 seconds lag. This is the primary lever.

**Kafka consumer autoscaling:** I'd configure Kubernetes HPA on a custom metric: `kafka_consumer_lag_messages`. Threshold: scale up when lag > 100K messages. Scale from 2 to 20 consumer pods. This handles the burst automatically without manual intervention.

**Priority topics:** For time-sensitive notifications — live score updates, price alerts, order confirmations — I'd use a separate high-priority topic with dedicated consumers. Celebrity-post fan-out notifications go to a bulk topic. This way the time-critical notifications never wait behind millions of fan-out messages.

**Consumer backpressure to downstream:** If the downstream delivery (APNS/FCM) starts throttling — returns HTTP 429 — the consumer should slow its poll rate to match. Using Project Reactor's bounded `flatMap(n)` concurrency, the consumer naturally applies backpressure to the Kafka poll when all in-flight slots are occupied.

The monitoring setup: alert when lag > 500K messages for more than 5 minutes. That indicates autoscaling isn't keeping up and we need to investigate — possibly the consumer is CPU-bound or the downstream is rate-limiting."

**Interviewer:** "What if you can't use Kafka? Say you have a direct HTTP service-to-service call."

**You:** "Then backpressure surfaces as HTTP status codes. The downstream service returns 503 Service Unavailable or 429 Too Many Requests with a `Retry-After` header. The upstream client should implement a circuit breaker — after N consecutive 503s, open the circuit, stop sending, wait for the window to close, and retry.

The upstream also needs a bounded request queue. If the circuit is open and requests keep arriving, they queue up. Once the queue hits a limit — say 1,000 pending requests — start rejecting with 503 immediately, propagating backpressure up to the caller. This is the Bulkhead pattern: protect your own memory by bounding how many in-flight requests you'll hold.

The key principle is: pressure must propagate upstream, all the way back to the client, or you get the fire-hose-into-watering-can scenario."

---

## PART 5 — DECISION FRAMEWORK

### Strategy Selection Table

```
┌─────────────────────┬──────────┬──────────┬─────────────┬──────────────────────┐
│ Strategy            │ Data     │ Latency  │ Prod/Cons   │ Best Use Case        │
│                     │ Loss?    │ Impact?  │ Speed Ratio │                      │
├─────────────────────┼──────────┼──────────┼─────────────┼──────────────────────┤
│ Drop on overflow    │ YES      │ None     │ Any         │ Metrics, logs,       │
│ (bounded buffer)    │          │          │             │ analytics events     │
├─────────────────────┼──────────┼──────────┼─────────────┼──────────────────────┤
│ Block producer      │ No       │ High     │ < 10x       │ Internal batch jobs, │
│ (LinkedBlockingQ)   │          │          │             │ same-JVM processing  │
├─────────────────────┼──────────┼──────────┼─────────────┼──────────────────────┤
│ External queue      │ No       │ Delayed  │ Any         │ Most production      │
│ (Kafka/SQS)         │          │ delivery │             │ event-driven systems │
├─────────────────────┼──────────┼──────────┼─────────────┼──────────────────────┤
│ Autoscale consumer  │ No       │ Minimized│ Spiky       │ Flash sales, events, │
│ (K8s HPA on lag)    │          │          │             │ burst-heavy workloads│
├─────────────────────┼──────────┼──────────┼─────────────┼──────────────────────┤
│ Circuit breaker +   │ No       │ Error    │ Any         │ HTTP service chains, │
│ 503 propagation     │          │ (503)    │             │ no queue available   │
├─────────────────────┼──────────┼──────────┼─────────────┼──────────────────────┤
│ Reactive pull       │ No       │ Smooth   │ Any         │ Streaming pipelines, │
│ (request(N))        │          │          │             │ in-process reactive  │
└─────────────────────┴──────────┴──────────┴─────────────┴──────────────────────┘
```

### Decision Tree

```
Is data loss acceptable?
├── YES → Bounded drop-on-overflow buffer (analytics, logging)
└── NO
    ├── Is producer in the same JVM as consumer?
    │   ├── YES → LinkedBlockingQueue (bounded, block on full)
    │   └── NO
    │       ├── Is this HTTP service-to-service?
    │       │   └── YES → Circuit breaker + 503 propagation + bulkhead
    │       └── Is this async event processing?
    │           └── YES → Kafka/SQS
    │               ├── Is traffic bursty / unpredictable?
    │               │   └── YES → Kafka + HPA autoscale on lag metric
    │               └── Is traffic steady?
    │                   └── YES → Fixed consumer count, monitor lag
```

---

## QUICK REFERENCE CARD

```
BACKPRESSURE EQUATION:
  If production_rate > consumption_rate:
    buffer grows at: (production_rate - consumption_rate) × time
    catch-up time:   buffer_size / (consumption_rate - production_rate)

KAFKA LAG ALERT RULE:
  alert: HighConsumerLag
  expr: kafka_consumer_group_lag > 100000
  for: 5m
  action: scale consumer deployment

KAFKA PARTITION SIZING:
  partitions ≥ max_desired_consumer_instances
  throughput = partitions × throughput_per_consumer
  example: 20 partitions × 10K msg/sec = 200K msg/sec max

REACTOR BOUNDED FLATMAP (most common backpressure pattern):
  Flux.from(source)
      .flatMap(item -> processAsync(item), MAX_CONCURRENCY)
  //  MAX_CONCURRENCY = upstream_rate / downstream_latency_rate
  //  example: 1000 req/sec source, 100ms per item → 100 concurrency

BLOCKING QUEUE (in-JVM backpressure):
  BlockingQueue<T> q = new LinkedBlockingQueue<>(BOUND);
  producer: q.put(item);    // blocks when full
  consumer: q.poll(timeout) // pops when available

CIRCUIT BREAKER THRESHOLDS (Resilience4j):
  failureRateThreshold: 50%      // open when 50% of calls fail
  slowCallRateThreshold: 50%     // or when 50% are slow
  slowCallDurationThreshold: 2s  // "slow" defined as > 2s
  waitDurationInOpenState: 30s   // wait 30s before half-open
  permittedCallsInHalfOpenState: 10

REACTIVE STREAMS CONTRACT:
  subscriber.request(N) → publisher may emit 0..N items
  Publisher MUST NOT emit more than N items (backpressure guarantee)
  onNext() calls are sequential (no concurrent onNext)
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

```
┌──────┬─────────────────────┬────────────────────────────────────────────────────────────────┐
│  #   │ System              │ Backpressure Pattern                                           │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  03  │ Notification        │ Celebrity post → 10M fan-out events in seconds. Kafka absorbs  │
│      │ System              │ the burst. Notification consumers at fixed rate, autoscale on  │
│      │                     │ lag. Priority topic for time-sensitive (payment) notifications. │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  08  │ Food Delivery       │ Lunch/dinner rush: order events burst 10x normal volume. Food  │
│      │                     │ prep updates consumed by delivery tracking service. Acceptable  │
│      │                     │ lag for prep updates; driver GPS location is real-time (WebSocket│
│      │                     │ not Kafka — different path).                                   │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  13  │ Leaderboard         │ Tournament score events burst during peak play. Redis ZADD      │
│      │                     │ consumer updates scores. Consumer autoscales on lag; eventual   │
│      │                     │ consistency during burst is acceptable for leaderboard display. │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  09  │ E-Commerce          │ Flash sale: order placement spikes 50x. Cart service → order   │
│      │                     │ service via Kafka. Inventory reservation via Kafka outbox pattern│
│      │                     │ (not direct HTTP) prevents inventory service from being the    │
│      │                     │ bottleneck.                                                    │
├──────┼─────────────────────┼────────────────────────────────────────────────────────────────┤
│  All │ Any event-driven    │ Rule: if producer and consumer scale independently, use Kafka.  │
│      │ microservices       │ Monitor kafka_consumer_group_lag. Alert at 100K messages.      │
│      │                     │ Autoscale on lag, not CPU. Keep partition count ≥ max replicas. │
└──────┴─────────────────────┴────────────────────────────────────────────────────────────────┘
```

---

> **Architect's one-liner:** "Backpressure is the consumer's ability to signal 'slow down' to the producer — Kafka naturally handles it by decoupling production rate from consumption rate, with lag as the visible signal that triggers autoscaling."
