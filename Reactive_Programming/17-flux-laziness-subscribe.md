> **Sequence 17/19 (Tier 4 ⚙️)** — See [README.md](README.md) for the full ranked index.

# Why nothing happens until `.subscribe()` is called

**Interview framing:** "Why does nothing happen when I just declare a `Flux`/`Mono` pipeline — do I need to call something extra?"

**The scenario:** an engineer writes:
```java
Flux<String> wordFlux = Flux.just("hello", "world");
System.out.println(wordFlux); // prints something like FluxArray, NOT the data
```
...and is confused that "hello"/"world" never printed.

**Easy English explanation:** Just like `Stream`, a `Flux`/`Mono` is **lazy** — declaring the pipeline only builds a *recipe*, it does not execute anything. Nothing runs until a **subscriber** attaches with `.subscribe(...)` and asks for data.

**Why this is a deliberate design, not a bug (production reasoning):** this lets you build complex, conditional reactive pipelines (e.g., a query builder that adds `.filter()`/`.map()` steps based on runtime feature flags) **without any cost** until the moment something actually needs the result. A pipeline built inside an `if` branch that's never taken costs nothing, because it's never subscribed to. This is analogous to a JPA/Criteria query builder that doesn't hit the DB until `.getResultList()` is called.

```java
wordFlux.subscribe(word -> System.out.println(word)); // NOW it runs: hello, world
```

> **One-line takeaway:** Declaring a `Flux`/`Mono` = writing a recipe. Calling `.subscribe()` = actually cooking it. No subscriber, no execution, no side effects — ever.

---
**Next:** [18-creating-flux-from-list.md](18-creating-flux-from-list.md)
