> **Sequence 07/19 (Tier 2 ⭐)** — See [README.md](README.md) for the full ranked index.

# `Stream` vs `Flux`/`Mono` — single-use vs replayable

**Interview framing:** "Why can't I just use `java.util.stream.Stream` instead of learning `Flux`/`Mono`? Aren't they the same idea?"

**The production scenario:** A senior engineer on your team writes a `List<Order>` → `Stream<Order>` pipeline inside a Spring MVC controller, ships it, and later someone tries to reuse that same `Stream` object to serve two different clients (once for an audit log, once for the API response) — and it throws:

```
java.lang.IllegalStateException: stream has already been operated upon or closed
```

**Easy English explanation:** `Stream` is a **one-time, pull-based** processing pipeline over data that already exists (or that a terminal operation *pulls* into existence). Think of it like a **conveyor belt with one paying customer** — once that customer has taken all the items off the belt, the belt is empty and gone. You cannot rewind it.

A `Flux`/`Mono` (Reactor's reactive stream types) is a **push-based, replayable Publisher**. Think of it like a **YouTube video** — many different viewers (subscribers) can hit "play" independently, and each one gets their own fresh playback of the content, starting from the beginning, at their own pace.

**Why we need this distinction (production impact):**
- **Streams are lazy AND single-use** — nothing runs until a terminal operation (`forEach`, `collect`, etc.) is called, and once called, the pipeline is dead. Fine for a one-shot batch job; unusable if the same data source needs to feed multiple independent consumers (e.g., broadcasting the same price-update pipeline to a websocket handler **and** a metrics counter **and** an audit logger).
- **A `Flux`/`Mono` can be subscribed to multiple times**, and (for a "cold" publisher — the default) **each subscriber gets its own independent run of the whole pipeline**, in the order they subscribed.

```java
Flux<Integer> numbers = Flux.just(1, 2, 3, 4);

numbers.subscribe(n -> System.out.println("Subscriber A: " + n));
numbers.subscribe(n -> System.out.println("Subscriber B: " + n));
// Both print 1, 2, 3, 4 — completely independent runs.
// Try this with a Stream and the second subscribe() would throw IllegalStateException.
```

**How Reactor solves it:** every `Flux`/`Mono` is a **Publisher** (from the Reactive Streams spec). Each `.subscribe()` call creates a brand-new subscription and re-runs the declared pipeline from scratch — no shared, mutable, single-use cursor like `Stream` has.

> **One-line takeaway:** Reach for `Stream` for one-shot, single-consumer, synchronous batch processing. Reach for `Flux`/`Mono` the moment you need **replayable, async, multi-consumer, or I/O-bound** data pipelines.

---
**Next:** [08-multiple-subscribers-behavior.md](08-multiple-subscribers-behavior.md) — a deeper look at the "multiple subscribers" behavior introduced here.
