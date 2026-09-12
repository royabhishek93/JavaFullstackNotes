> **Sequence 10/19 (Tier 2 ⭐)** — See [README.md](README.md) for the full ranked index.

# Fallback on empty results: `defaultIfEmpty` vs `switchIfEmpty` (cache-aside pattern)

**Interview framing:** "Production scenario: an endpoint should return a sensible default instead of an empty response when there's no data (e.g., cache miss → fallback message, or empty search → fallback to a broader result set). What operators handle this?"

**`defaultIfEmpty(T)`** — emits a single fallback value if the upstream completes with **zero elements**.

```java
public Flux<String> getFilteredOrDefault(int minLength) {
    return getFlux()
        .filter(name -> name.length() > minLength)
        .defaultIfEmpty("NO_MATCHES_FOUND");
}
```

**`switchIfEmpty(Publisher)`** — same idea, but instead of one static fallback value, **switches to an entirely different Publisher** (e.g., a broader fallback query) when the upstream is empty.

```java
public Flux<String> getFilteredWithFallbackSearch(int minLength) {
    return getFlux()
        .filter(name -> name.length() > minLength)
        .switchIfEmpty(getBroaderFallbackFlux()); // e.g. relaxed search query
}
```

**Production analogy:** cache-aside pattern — `getFromCache(key).switchIfEmpty(getFromDatabaseAndCache(key))`. This is exactly how you implement cache-miss fallback logic reactively, without an imperative `if (result == null) { ... }` check.

> **One-line takeaway:** `defaultIfEmpty()` = static fallback value. `switchIfEmpty()` = fallback to a whole different reactive source (e.g., cache-miss → DB read). Both avoid manual null-checking in reactive code.

---
**Next:** [11-functional-endpoints-routerfunction.md](11-functional-endpoints-routerfunction.md) (Tier 3 — good-to-know depth)
