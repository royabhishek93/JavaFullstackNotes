# Backpressure & Reactive Streams — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 29 of 29 (SERIES FINALE)

## HOOK (0:00–0:30)

[SCREEN: Black background, text types out — "Your service crashes every traffic spike. You're losing messages. Why?"]

Picture a fire hose blasting 500 liters of water per second... into a garden watering can that can only hold 2 liters per second.

[SCREEN: Split animation — fire hose on left labeled "500 L/sec", watering can on right labeled "2 L/sec", water overflowing everywhere]

You already know what happens. Overflow. Mess everywhere.

Now replace "water" with "messages," and "watering can" with "your consumer service." Same overflow. Except in software, it's not a puddle on the floor — it's an OutOfMemoryError, a crashed pod, and every buffered message gone forever.

[TEXT ON SCREEN: "Backpressure: the fix nobody teaches until production breaks"]

This is backpressure. And today — episode 29, the final episode of this entire system design series — we're breaking down exactly how fast producers and slow consumers coexist without anything catching fire.

## THE PROBLEM (0:30–2:00)

[SCREEN: Title card — "The Producer-Consumer Mismatch"]

Let's make this concrete. Say you're running a flash sale.

[SCREEN: Diagram — "Producer: Order events → 10,000/sec" arrow into a box "Buffer" arrow into "Consumer: Fraud checks → 1,000/sec"]

Orders are coming in at 10,000 per second. Your fraud-check service can only process 1,000 per second. That's a net accumulation of 9,000 messages every single second, piling up in whatever buffer sits between them.

[SCREEN: Counter animation ticking up — "t=0s: 0 messages" → "t=10s: 90,000 messages (~90MB)" → "t=60s: 540,000 messages (~540MB)"]

Do the math for a full hour of this: 9,000 messages a second times 3,600 seconds is 32.4 million messages. At just 1 kilobyte each, that's over 32 gigabytes trying to sit in memory. You will hit OutOfMemoryError long, long before you get there. The consumer crashes. And with an in-memory queue, when it crashes, every single buffered message is gone. Not delayed — gone.

[SCREEN: Big red text — "32.4 MILLION messages/hour → OOM → CRASH → DATA LOSS"]

Here's the twist most engineers miss: this isn't a rare edge case. Any time a producer and a consumer scale independently — and in microservices, they almost always do — this mismatch is lurking. Flash sales, viral posts, sporting events, cron jobs that suddenly wake up ten downstream services at once. It's one of the single most common causes of production outages, and it shows up in nearly every system design interview that touches event processing.

So how do we fix a fire hose pointed at a watering can? We teach the watering can how to say "slow down."

## THE SOLUTION (2:00–5:00)

[SCREEN: Title card — "Backpressure: The Consumer Talks Back"]

Backpressure is simply this: instead of the producer blindly pushing at full speed, the consumer signals its actual capacity, and the producer respects it.

[SCREEN: Side-by-side — "PUSH model (no backpressure)" vs "PULL model (backpressure)"]

That signal travels differently depending on where you are in the stack. There are three main ways.

[SCREEN: Numbered list appearing one at a time]

Number one — inside a single process, using Reactive Streams. The subscriber literally calls a method: `request(N)` — "give me N more items, and not one more until I ask again." The producer is physically incapable of sending more than what was requested.

Number two — across services with Kafka. There's no explicit "stop" message. The consumer just... stops polling as often. Kafka holds every message durably on disk, and the consumer resumes at whatever pace it can handle. The absence of polling IS the signal.

Number three — plain HTTP service-to-service calls. The downstream returns an HTTP 429, Too Many Requests, or a 503, Service Unavailable, often with a `Retry-After` header telling the caller exactly how long to back off.

[SCREEN: Code block — the Reactive Streams interfaces]
```
interface Publisher<T>  { void subscribe(Subscriber<T> s); }
interface Subscriber<T> {
  void onSubscribe(Subscription s);
  void onNext(T item);
  void onError(Throwable t);
  void onComplete();
}
interface Subscription {
  void request(long n);   // "I want n more items"
  void cancel();
}
```

This is the actual Java Reactive Streams specification — the contract that Project Reactor, RxJava, and Akka Streams all implement. The consumer calls `request(n)`, and the publisher is contractually forbidden from sending more than `n` items until asked again. That's the pull model in one interface.

[SCREEN: Diagram — Kafka topic as a durable buffer, disk icon, "messages NOT lost, just delayed"]

Now here's why Kafka changes the entire equation compared to an in-memory buffer. With Kafka sitting between producer and consumer, that same 9,000-messages-per-second overflow doesn't crash anything. It just accumulates — on disk, replicated, retained for 7 days by default. The consumer reads at its own pace, say 1,000 per second, completely decoupled from how fast orders are arriving.

The tradeoff isn't gone, though — it just changes shape. After one hour of that spike, you'd have 32.4 million messages sitting in lag. At 1,000 per second, catching up on that takes about 9 hours. So Kafka doesn't make the problem disappear — it turns "instant catastrophic data loss" into "a visible, measurable, fixable lag number." That's a massive upgrade.

[SCREEN: Code snippet — Project Reactor bounded flatMap]
```java
Flux.range(1, 1_000_000)
    .flatMap(i -> callSlowDownstreamService(i), 10)
    //                                           ↑ max 10 concurrent
    .subscribe();
```

And in Project Reactor specifically, the way you apply backpressure to async pipelines is concurrency bounding. Cap how many operations can be in-flight at once, and the producer naturally waits when that cap is hit.

Even Kafka's own consumer poll loop gives you backpressure for free — if your processing loop is slow, you simply call `poll()` less often, and Kafka broker sees that reduced polling frequency as a signal that you're busy. No special code required. It's baked into the client.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[SCREEN: Title card — "The Mistakes That Get You Paged at 2 AM"]

Let's get into where this actually breaks in production, because this is where interviews separate senior from mid-level candidates.

[SCREEN: Code block, red X over the top]
```java
// ❌ flatMap with NO concurrency limit
Flux.range(1, 1_000_000)
    .flatMap(i -> callSlowDownstreamService(i))
    .subscribe();
```

Mistake number one: unbounded `flatMap`. This looks totally innocent. But without a concurrency argument, Reactor tries to subscribe to all one million inner publishers essentially at once. Each one holds a pending HTTP connection, a chunk of memory, a subscription. Result: OutOfMemoryError. This is the single most common Reactor production bug I've seen.

[SCREEN: Three-way comparison table — flatMap (unbounded) / concatMap / flatMap(n)]

The fix is knowing your three tools. `concatMap` processes strictly one item at a time — full backpressure, but your throughput is capped at one divided by your downstream latency. Use it when order matters and throughput needs are low. Plain `flatMap` with a concurrency number — say `flatMap(fn, 10)` — gives you the real answer for most production systems: bounded parallelism. Ten concurrent operations, memory stays bounded, and throughput scales roughly ten times over `concatMap`. That number, 10, isn't arbitrary — you size it as upstream rate divided by downstream latency.

[SCREEN: Title card — "5 Backpressure Strategies — When to Use Each"]

Now, the five actual strategies, because interviewers will ask you to pick the right one for a scenario.

Strategy one: **Drop**. When the buffer's full, you just discard new messages and maybe return an error. Use this for analytics events, logs, metrics — anything where losing a data point occasionally doesn't matter. Never use it for financial transactions or order events.

Strategy two: **Block the producer**. A bounded `LinkedBlockingQueue` where `put()` blocks until there's space. Perfect for internal, same-JVM batch processing. Terrible for user-facing requests, because blocking there just means the user's request times out.

Strategy three: **External durable queue** — Kafka or SQS. This is the default answer for most production event-driven systems. Disk-backed, replicated, effectively unlimited capacity. The cost is operational overhead of running that queue infrastructure.

Strategy four: **Autoscale the consumer**. Kafka lag crosses a threshold, you spin up more consumer pods. Ten consumers instead of one gives you roughly ten times the throughput. This is your answer for bursty, unpredictable traffic — flash sales, viral events.

Strategy five: **Circuit breaker on the producer side**, surfacing pressure as an HTTP 503 back to the caller. Use this when there's no queue in the middle at all — direct service-to-service HTTP calls.

[SCREEN: Formula on screen — "throughput = partitions × throughput_per_consumer"]

Now let's talk numbers, because Kafka partitioning is a formula you need memorized: max throughput equals partition count times per-consumer throughput. If your fraud-check consumer handles 10,000 checks per second per instance, and you provision 20 partitions with 20 consumer instances, you get 20 times 10,000 — 200,000 messages per second of total throughput. Partition count is your hard ceiling on parallelism — you cannot have more active consumers in a group than partitions.

[SCREEN: YAML snippet — HPA with kafka_consumer_lag_messages metric, "averageValue: 10000"]

And for autoscaling in Kubernetes, you don't scale on CPU — you scale on a custom metric: `kafka_consumer_lag_messages`. A typical threshold is scaling up when average lag crosses 10,000 to 100,000 messages, depending on how tight your latency budget is. That's the metric prometheus-adapter exposes, and it's what your HPA spec targets directly.

[SCREEN: Resilience4j config block]
```
failureRateThreshold: 50%
waitDurationInOpenState: 30s
```

For circuit breakers specifically, Resilience4j's defaults are a great mental anchor: open the circuit at a 50% failure rate, wait 30 seconds in the open state before testing again with a half-open trial. Memorize those two numbers — 50% and 30 seconds — they come up constantly.

[SCREEN: Interview scenario card — "1,000,000 notifications in 10 seconds, consumer at 10,000/sec"]

Here's the classic interview trap: "1 million notifications produced in 10 seconds, your consumer processes 10,000 per second — what happens?" The naive answer is "it crashes." The correct answer: Kafka absorbs it, the consumer now has 100 seconds of catch-up lag, notifications arrive late but aren't lost. Then you fix the lateness — more partitions, more consumer instances via HPA, and a separate high-priority topic so time-critical notifications never queue behind bulk fan-out traffic.

## REAL WORLD (8:00–9:30)

[SCREEN: Title card — "Where This Shows Up in Real Systems"]

You've seen this pattern across this entire series, whether you noticed it or not.

[SCREEN: Notification bell icon, "10M fan-out"]

In the **Notification System** episode — a celebrity posts, and you get a 10 million-message fan-out in seconds. Kafka absorbs the burst, consumers run at a fixed rate and autoscale on lag, and time-sensitive notifications get routed through a separate priority topic so they don't wait behind the flood.

[SCREEN: Food delivery bag icon, "10x lunch rush"]

In **Food Delivery**, the lunch and dinner rush produces order events at 10 times normal volume. Prep-status updates can tolerate lag — a few seconds late is fine. But driver GPS location takes a completely different path, over WebSocket, because that one truly can't be delayed.

[SCREEN: Trophy icon, "tournament score burst"]

In **Leaderboard**, tournament play creates score-update bursts. A Redis `ZADD` consumer processes them, autoscaling on lag, and brief eventual consistency in the displayed rankings during a burst is a completely acceptable tradeoff.

[SCREEN: Shopping cart icon, "50x flash sale spike"]

And in **E-Commerce**, a flash sale spikes order placement 50 times over baseline. Cart and order services communicate through Kafka, and inventory reservation goes through the outbox pattern rather than direct synchronous calls — so the inventory service never becomes the bottleneck that topples the whole checkout flow.

[SCREEN: Text overlay — "Rule: if producer and consumer scale independently → use Kafka. Monitor lag. Autoscale on lag, not CPU."]

Notice the common thread across every single one of these: whenever a producer and a consumer can scale independently of each other, Kafka becomes the buffer, consumer lag becomes the metric you watch, and autoscaling triggers off lag — not CPU.

## OUTRO + SERIES WRAP-UP (9:30–10:00)

[SCREEN: Text — "Episode 29 of 29 — Series Complete"]

And that's backpressure — and that's also episode 29, the final episode of this entire system design interview series.

[SCREEN: Scrolling montage of episode titles/numbers, 1 through 29, fading in and out]

Think back to where we started. Episode 1, the transactional outbox pattern. We went through Kafka streams, service mesh, bulkhead and load shedding, strangler fig migrations, leader election, sharding, CAP theorem, CQRS, event sourcing, rate limiting, consensus algorithms, chaos engineering — twenty-nine patterns that, together, form the actual mental toolkit real distributed systems are built on. And today we closed the loop with the pattern that ties nearly all of them together: how fast producers and slow consumers coexist without anything catching fire.

[SCREEN: Text — "Thank you for 29 episodes"]

If you've made it through this whole series, genuinely — thank you. That's a real investment of time, and it shows in how you'll walk into your next system design interview.

[SCREEN: Comment prompt on screen — "Which pattern helped you most in an interview?"]

So here's my ask for this final episode: drop a comment and tell me which pattern from this series actually came up in one of your interviews, or the one that changed how you think about system design the most. I read every one, and it genuinely shapes what comes next.

[SCREEN: Subscribe button animation + "See you in the next series"]

Thanks for watching all the way through. Subscribe if this series helped, and I'll see you in whatever we build next.

[END]
