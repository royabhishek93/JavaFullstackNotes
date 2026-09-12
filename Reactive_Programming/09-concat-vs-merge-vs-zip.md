> **Sequence 09/19 (Tier 2 ⭐)** — See [README.md](README.md) for the full ranked index.

# Combining two Flux sources: `concat` vs `merge` vs `zip`

**Interview framing:** "You need to combine two independent Flux sources (e.g., call two microservices and combine their responses). What are your options, and what's the real trade-off?"

Three families of combinators, each with a distinct production trade-off:

### `concat()` / `concatWith()` — strictly sequential, order guaranteed

```java
Flux.concat(getUserNamesFlux(), getFruitNamesFlux()); // static
getUserNamesFlux().concatWith(getFruitNamesFlux());    // instance, same result
```

The second source is **not even subscribed to** until the first one fully completes. Order is always preserved, **regardless of delays** on either source. **Production use case:** running two operations that MUST happen in strict order — e.g., "finish writing all audit-log entries for step 1, only then start step 2's writes."

### `merge()` / `mergeWith()` — concurrent, async, order NOT guaranteed

```java
getUserNamesFlux().mergeWith(getFruitNamesFlux());
```

Both sources are **subscribed to at the same time**; whichever emits first, wins — output interleaves unpredictably if either source has delays. **Production use case:** fanning out to two independent services in parallel to reduce total latency, when you don't care which one's data arrives first (e.g., merging two independent notification streams into one feed).

> There is also `mergeSequential()` — subscribes concurrently (for speed) but **buffers and re-orders output** to match input source order — a middle ground when you want concurrency's speed but still need deterministic output order.

### `zip()` / `zipWith()` — pairwise combination by index

```java
Flux.zip(getNamesFlux(), getScoresFlux(), (name, score) -> name + ": " + score);
```

Combines element *i* from source A with element *i* from source B into one combined value (a `Tuple2` by default, or a custom combiner function). **Stops at the shorter source's length** — extra unpaired elements are silently dropped. **Production use case:** combining a price stream with a quantity stream to compute line-item totals, or joining two parallel API calls' *i*-th results together (e.g., matching request IDs to response IDs by position — though pairing by an actual key/ID is usually safer than pairing by position).

**The trade-off table an architect should state out loud in an interview:**

| Combinator | Concurrency | Order guarantee | Best for |
|---|---|---|---|
| `concat`/`concatWith` | Sequential (one at a time) | Yes, always | Strict ordering requirements (e.g., migrations, ledgers) |
| `merge`/`mergeWith` | Concurrent | No | Max throughput, order doesn't matter |
| `mergeSequential` | Concurrent (internally) | Yes (buffered/reordered) | Need both speed AND order |
| `zip`/`zipWith` | Concurrent (paired by index) | Paired positionally | Combining two correlated streams element-by-element |

> **One-line takeaway:** `concat` = safe but slow (sequential). `merge` = fast but unordered. `mergeSequential` = fast AND ordered (buffers internally). `zip` = pairs elements positionally across two sources. Pick based on whether your business logic actually *needs* ordering — don't default to `concat` "just to be safe" if it's a needless serialization bottleneck.

---
**Next:** [10-defaultifempty-vs-switchifempty.md](10-defaultifempty-vs-switchifempty.md)
