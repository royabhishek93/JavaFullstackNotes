> **Sequence 16/19 (Tier 4 ⚙️)** — See [README.md](README.md) for the full ranked index.

# The `filter()` operator

**Interview framing:** "You need to drop elements that don't match a condition mid-pipeline — without first collecting everything into a `List` to filter it. How?"

**Use `filter()`** — keeps only elements matching a predicate.

```java
public Flux<String> getActiveUserNames() {
    return getFlux().filter(name -> name.length() > 4); // toy example; real: user.isActive()
}
```

**Why this matters in production:** filtering *inside* the reactive pipeline (rather than materializing a list and using `stream().filter()`) means the filtering happens **as data arrives**, element by element, with no need to buffer the whole result set in memory first — important when the upstream source is a large or infinite stream (e.g., filtering a live Kafka event feed for only `ORDER_CREATED` events).

```java
@Test
void filterTest() {
    StepVerifier.create(userService.getActiveUserNames())
        .expectNextCount(3)
        .verifyComplete();
}
```

> **One-line takeaway:** `filter()` drops non-matching elements in-stream, without materializing the whole collection first — critical for large/unbounded sources.

---
**Next:** [17-flux-laziness-subscribe.md](17-flux-laziness-subscribe.md)
