> **Sequence 03/19 (Tier 1 🔥)** — See [README.md](README.md) for the full ranked index.

# Publisher-Subscriber handshake & backpressure

**Interview framing:** "Explain the Publisher-Subscriber handshake — what are `onSubscribe`, `request(n)`, `onNext`, `onComplete`, `onError`, and why does this matter for a system handling real production load?"

**Easy English explanation:** Reactive Streams (the spec Reactor implements) define a strict protocol between a **Publisher** (the data source) and a **Subscriber** (the consumer):

1. `onSubscribe(Subscription)` — the moment you call `.subscribe()`, the publisher hands the subscriber a `Subscription` object — a remote control to ask for data.
2. `request(n)` — the subscriber uses that remote control to say "send me up to `n` items" (or `request(Long.MAX_VALUE)` for "send everything, unbounded").
3. `onNext(T)` — fired once per emitted element.
4. `onComplete()` — fired once, when the publisher has no more data.
5. `onError(Throwable)` — fired instead of `onComplete()` if something failed.

**Why the `request(n)` step exists at all — the real production problem it solves (backpressure):** Imagine a publisher reading rows from a database as fast as it can and pushing them to a subscriber that writes each row to a **slow external API** (rate-limited to 10 requests/sec). If the publisher just fires data at the subscriber with no throttle, the subscriber's internal buffer grows unbounded while it waits for the slow API — this is a classic **fast-producer, slow-consumer OutOfMemoryError** that has taken down real production systems (message queue consumers, Kafka streams, DB-to-API sync jobs).

**How Reactive Streams solves it:** because the subscriber explicitly `request(n)`s only as much as it can currently handle, the publisher is contractually forbidden from sending more than requested. This flow-control mechanism is called **backpressure**, and it's the single biggest reason reactive programming exists as a paradigm — it's not just "async for the sake of async," it's async **with a built-in safety valve** against memory blow-ups.

```java
Flux.range(1, 1_000_000)
    .log() // shows onSubscribe → request(unbounded) → onNext x N → onComplete
    .subscribe(data -> process(data));
```

> **One-line takeaway:** `request(n)` is not ceremony — it's the mechanism that stops a fast producer from drowning a slow consumer in memory. This is the #1 reason reactive > plain async callbacks for production data pipelines.

---
**Next:** [04-mono-vs-flux-decision-rule.md](04-mono-vs-flux-decision-rule.md)
