> **Sequence 05/19 (Tier 1 🔥)** — See [README.md](README.md) for the full ranked index.

# Async fan-out per element: `map` vs `flatMap` vs `concatMap`

**Interview framing:** "Production scenario: for every order in a `Flux<Order>`, you need to call another **reactive/async** service (e.g., enrich each order with inventory data from another microservice). Why does `map()` break here, and what do you use instead?"

This is **the single most common real-world Flux interview scenario** — the "N async fan-out calls per element" problem.

**Why `map()` fails:** `map()` expects your lambda to return a **plain value**, synchronously. But calling another reactive service returns a `Mono<Inventory>` or `Flux<Inventory>` — a *publisher*, not a plain value. If you try `map(order -> inventoryClient.getInventory(order.getSkuId()))`, you end up with `Flux<Mono<Inventory>>` — a **nested publisher**, which is useless; nobody subscribed to the inner `Mono`, so it never actually executes.

**Use `flatMap()` instead** — it takes each element, lets you return a **brand-new Publisher** per element, and Reactor automatically **subscribes to and flattens** all those inner publishers into one single resulting `Flux`.

```java
public Flux<EnrichedOrder> getEnrichedOrders() {
    return orderRepository.findAll()
        .flatMap(order -> inventoryClient.getInventory(order.getSkuId())
            .map(inventory -> new EnrichedOrder(order, inventory)));
}
```

**The real architectural trade-off interviewers want to hear — ordering vs throughput:**
- `flatMap()` subscribes to all the inner publishers **concurrently** (by default, up to a concurrency limit) — **higher throughput**, but **output order is not guaranteed** to match input order, because whichever inner call finishes first emits first.
- `concatMap()` behaves like `flatMap()` but processes inner publishers **strictly one at a time, in order** — guarantees output order, at the cost of throughput (no parallelism).

**Production rule of thumb:** use `flatMap()` for independent, order-doesn't-matter fan-out calls (e.g., enriching each order from an inventory service — order of enrichment doesn't matter). Use `concatMap()` when downstream order matters (e.g., applying a sequence of ledger/audit entries that MUST be processed in the order they arrived, or writing to an append-only log).

```java
// Demonstrating async, out-of-order behavior with delays:
public Flux<String> getCharactersAsync() {
    return getFlux()
        .delayElements(Duration.ofSeconds(1))
        .flatMap(name -> Flux.fromArray(name.split("")));
}
```

**Bonus — `Mono` to `Flux`:** if your *source* is a `Mono` but the transformation returns a `Flux`, use `flatMapMany()`:

```java
Mono.just("csv,line,data")
    .flatMapMany(line -> Flux.fromArray(line.split(","))); // returns Flux<String>
```

> **One-line takeaway:** `map()` = sync 1-to-1. `flatMap()` = async 1-to-many-or-one, concurrent, order NOT guaranteed. `concatMap()` = same idea but strictly sequential/ordered, lower throughput. Picking the wrong one is either a silent ordering bug or a silent performance bottleneck — know which one your use case needs.

---
**Next:** [06-webclient-vs-resttemplate-feign.md](06-webclient-vs-resttemplate-feign.md)
