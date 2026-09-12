> **Sequence 12/19 (Tier 3 👍)** — See [README.md](README.md) for the full ranked index.

# Testing reactive pipelines deterministically with `StepVerifier`

**Interview framing:** "How do you unit-test asynchronous reactive code deterministically — without flaky `Thread.sleep()`-based tests?"

**Use `StepVerifier`** (from `reactor-test`) instead of manually calling `.subscribe()` and eyeballing console output.

```java
@Test
void testReactivePipeline() {
    Flux<String> result = fluxLearnService.getMapExampleFlux();

    StepVerifier.create(result)
        .expectNext("ANKIT", "DURGESH", "RAVI", "GAUTAM") // exact values, in order
        .verifyComplete();
}

// Or just assert a count when exact values aren't the point:
StepVerifier.create(result)
    .expectNextCount(4)
    .verifyComplete();
```

**Why this matters in production codebases:** manually subscribing and printing to console gives you **no automated pass/fail signal** and can't run reliably in CI — you'd need `Thread.sleep()` guesses to "wait for async work," which is exactly the kind of flaky test that erodes trust in a test suite. `StepVerifier` subscribes internally and **blocks the test thread until the expected signals occur (or a timeout fails the test)**, giving deterministic, CI-safe assertions on both **values** and **completion/error signals**.

> **One-line takeaway:** Never manually `subscribe()` + eyeball console output in a test. Use `StepVerifier` for deterministic, CI-safe assertions on reactive pipelines — it's the reactive-world equivalent of JUnit assertions.

---
**Next:** [13-doOn-side-effect-operators.md](13-doOn-side-effect-operators.md)
