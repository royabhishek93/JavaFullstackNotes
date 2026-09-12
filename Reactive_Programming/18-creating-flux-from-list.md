> **Sequence 18/19 (Tier 4 ⚙️)** — See [README.md](README.md) for the full ranked index.

# Creating a `Flux`/`Mono` from a `List`/fixed values

**Interview framing:** "You have a `List<T>` from a repository/service call — how do you turn it into a reactive pipeline?"

**Easy English + code:**

```java
// From fixed values
Flux<String> names = Flux.just("Ankit", "Durgesh", "Ravi", "Gautam");

// From any existing collection (List, Set, anything Iterable)
List<String> fruitNames = List.of("Mango", "Apple");
Flux<String> fruits = Flux.fromIterable(fruitNames);

// Empty publisher (e.g. "no results" case)
Flux<String> empty = Flux.empty();

// Exactly one value
Mono<String> single = Mono.just("Ankit");
```

**Why this matters in production:** most real Flux pipelines don't start from hardcoded values — they start from `Flux.fromIterable(repository.findAll())`-style calls, or (better) directly from a reactive repository (`R2dbcRepository`, `ReactiveMongoRepository`) that already returns `Flux`/`Mono` natively without ever materializing a `List`. Using `fromIterable` on a list you already loaded into memory doesn't save memory — real wins come when the *source itself* is reactive end-to-end (e.g., streaming rows straight from the DB driver).

> **One-line takeaway:** `Flux.just()` for fixed test data, `Flux.fromIterable()` to wrap an existing collection, `Flux.empty()` for the "nothing found" case — but for real scalability, prefer sources that are reactive natively (R2DBC, reactive Mongo, WebClient) over wrapping already-loaded `List`s.

---
**Next:** [19-stream-pull-model-peek-limit-skip.md](19-stream-pull-model-peek-limit-skip.md) — the final, most niche entry in this index.
