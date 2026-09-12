> **Sequence 19/19 (Tier 4 ⚙️ — last, most niche)** — See [README.md](README.md) for the full ranked index.

# `Stream` pull-model trivia: `peek()`/`limit()`/`skip()` ordering puzzle

**Interview framing:** "My `Stream` returned surprising results when I chained `peek()`, `limit()`, and `skip()` — walk me through why."

This isn't really a "reactive" question, but architects occasionally get asked it because it proves you understand the **pull-based, upstream-request** execution model that reactive streams later flip on its head (see [07-stream-vs-flux-replayability.md](07-stream-vs-flux-replayability.md)).

**The scenario:**
```java
Stream.of(1,2,3,4,5,6,7,8,9)
    .peek(n -> System.out.println("peek: " + n))
    .limit(4)
    .forEach(n -> System.out.println("forEach: " + n));
```
Junior engineers expect all 9 numbers to be `peek`-ed first, then 4 printed. That's wrong.

**Easy English explanation:** A `Stream` pipeline works like a **relay race running backwards** — the terminal operation (`forEach`) *asks* (pulls) the operation right before it (`limit`) for one item at a time. `limit` in turn *asks* `peek` for one item, and `peek` asks the source. Data flows **downstream** one element at a time, only when asked. Nothing is pre-computed in bulk.

So the real output interleaves: `peek: 1`, `forEach: 1`, `peek: 2`, `forEach: 2`, `peek: 3`, `forEach: 3`, `peek: 4`, `forEach: 4` — then `limit` (a **short-circuiting, stateful** intermediate operation) tells the whole pipeline "I've emitted my 4, stop pulling" — elements 5–9 are **never touched**.

Contrast with `skip(5)` (a **stateful but non-short-circuiting** operation): it must silently consume and discard the first 5 elements (remembering a counter) before it starts forwarding data downstream — so you'll see `peek: 1` through `peek: 5` with **no corresponding `forEach`** output, then `peek: 6`/`forEach: 6` onward.

**Why this matters in production:** this pull-based, lazy, short-circuit behavior is *why* `Stream` pipelines are memory/CPU efficient for huge in-memory collections (`limit()` on a billion-row list doesn't process a billion rows) — but it's a **completely different execution model** from reactive streams, which are **push-based**. Mixing up the two mental models is the #1 cause of confusion when engineers move from Stream API to Reactor.

> **One-line takeaway:** `Stream` = downstream **pulls** data one element at a time (lazy, single-pass). Reactive `Flux`/`Mono` = upstream **pushes** data to you whenever it's ready (async, replayable). Same-looking `.map()`/`.filter()` syntax, opposite execution direction.

---
**This is the last file in the sequence.** Return to [README.md](README.md) for the full ranked index, or revisit [01-why-webflux-over-mvc-netty-vs-tomcat.md](01-why-webflux-over-mvc-netty-vs-tomcat.md) to restart from the top-priority question.
