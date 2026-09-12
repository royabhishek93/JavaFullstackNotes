> **Sequence 14/19 (Tier 3 👍)** — See [README.md](README.md) for the full ranked index.

# Reusable operator chains with `transform()`

**Interview framing:** "You want to apply a reusable, shared transformation pipeline (e.g., common logging + validation steps) across multiple different endpoints without copy-pasting operator chains. What operator helps, and why?"

**Use `transform()`** — takes a `Function<Flux<T>, Flux<R>>` and applies it to the *whole* Flux, letting you package a chain of operators into one reusable, named unit.

```java
Function<Flux<String>, Flux<String>> normalizeNames =
    flux -> flux.map(String::toUpperCase).filter(name -> !name.isBlank());

public Flux<String> getNormalizedNames() {
    return getFlux().transform(normalizeNames);
}
```

**Why this matters in production:** in a real codebase with dozens of endpoints, common cross-cutting operator chains (input sanitization, standard error mapping, standard logging) get duplicated across services if you don't extract them. `transform()` lets you define that chain **once**, as a `Function`, and reuse/chain it anywhere — a DRY principle applied to reactive pipelines, similar in spirit to a servlet filter chain but composable inline.

> **One-line takeaway:** `transform()` turns a reusable chain of operators into a single pluggable unit — use it to avoid copy-pasting the same `.map().filter().doOnNext()` sequence across every service method.

---
**Next:** [15-map-operator.md](15-map-operator.md) (Tier 4 — foundational basics)
