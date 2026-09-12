> **Sequence 08/19 (Tier 2 ⭐)** — See [README.md](README.md) for the full ranked index. Builds on [07-stream-vs-flux-replayability.md](07-stream-vs-flux-replayability.md).

# What happens when multiple subscribers attach to one publisher?

**Interview framing:** "Can multiple subscribers attach to the same publisher? What actually happens when they do?"

**Easy English explanation:** Yes — a `Flux`/`Mono` (a "cold" publisher, which is the default for things like `Flux.just(...)`) can have **multiple independent subscribers**. Each subscription gets its **own full run** of the pipeline, executed **sequentially in subscription order** by default — subscriber A's full sequence runs to completion, then subscriber B's full sequence starts.

```java
Flux<Integer> flux = Flux.just(1, 2, 3);
flux.subscribe(n -> System.out.println("A: " + n)); // runs fully first
flux.subscribe(n -> System.out.println("B: " + n)); // runs fully second
```

**Production analogy:** think of a YouTube video (cold publisher) — 10 different viewers can watch the same video independently, each starting from 0:00 whenever *they* press play, with no interference between them. Compare this to a **live TV broadcast** (a "hot" publisher, e.g. `Sinks`/`ConnectableFlux` in Reactor) where late joiners miss whatever already aired — a different, more advanced topic worth knowing exists, but out of scope here.

**Why architects care:** this is fundamentally different from a `Stream`, which can only ever be consumed **once**. If your design needs the same computed pipeline consumed by multiple independent parts of the system (e.g., one subscriber persists to DB, another sends a Kafka event, a third updates a cache) — you get that "for free" with `Flux`/`Mono`, whereas with `Stream` you'd need to materialize a `List` first and iterate it multiple times manually.

> **One-line takeaway:** Cold publishers replay the entire sequence per subscriber, in the order they subscribed. This "multi-subscriber-friendly by design" behavior is a core reason reactive types replace collections in async architectures.

---
**Next:** [09-concat-vs-merge-vs-zip.md](09-concat-vs-merge-vs-zip.md)
