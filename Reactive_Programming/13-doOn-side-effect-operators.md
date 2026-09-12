> **Sequence 13/19 (Tier 3 👍)** — See [README.md](README.md) for the full ranked index.

# Observability without mutation: `doOnNext`/`doOnSubscribe`/`doOnComplete`

**Interview framing:** "You need to log/audit/emit metrics for every element passing through a pipeline — without altering the actual data or mixing observability code into business logic. What operators?"

**Side-effect operators** (`doOn*` family) — hook into specific signals in the pipeline **without transforming the data itself**:

```java
public Flux<String> getObservableFlux() {
    return getFlux()
        .doOnSubscribe(sub -> log.info("Subscription started"))
        .doOnNext(data -> metricsCounter.increment())      // fires just before each onNext
        .doOnEach(signal -> log.debug("Signal: {}", signal)) // fires for onNext AND onComplete/onError
        .doOnComplete(() -> log.info("Stream completed"))
        .doOnCancel(() -> log.warn("Subscriber cancelled"));
}
```

**Why this matters in production:** this is how you add **cross-cutting observability** (Micrometer metrics, distributed tracing spans, audit logging) to a reactive pipeline **without polluting the actual business transformation logic** (`map`/`filter`/`flatMap`) with logging statements. It keeps a clean separation between "what the data becomes" (`map`/`filter`/`flatMap`) and "what we observe about the flow" (`doOn*`).

Related error-handling side-effect operators worth knowing exist (not deep-dived here): `onErrorResume()` (recover with a fallback publisher), `onErrorMap()` (translate one exception type to another, e.g., wrapping a low-level DB exception into a domain exception), `onErrorComplete()` (swallow the error and complete normally).

> **One-line takeaway:** `doOn*` operators are for **observing** the stream (logging, metrics, tracing) without changing it. Keep them separate from `map`/`filter`/`flatMap`, which are for **transforming** the data — mixing the two makes pipelines hard to read and test.

---
**Next:** [14-transform-reusable-pipelines.md](14-transform-reusable-pipelines.md)
