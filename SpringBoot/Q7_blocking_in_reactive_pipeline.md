# Q7: Blocking in Reactive Pipeline (Quick Companion)

**Study Time:** 5-10 minutes | **Use this for:** last-minute revision

This is the lightweight companion file.
Canonical full guide is: `SpringBoot/webflux-senior-interview-questions.md`.

## What to Remember First

1. Reactive and WebFlux are not the same.
2. Reactive is the model; WebFlux is Spring's reactive HTTP framework.
3. Event-loop threads must not block.
4. Blocking JDBC/RestTemplate/sleep in chain causes starvation.
5. `.block()` is boundary-only (tests/startup/CLI), not request path.
6. `publishOn` switches downstream context; it does not auto-parallelize work.
7. `subscribeOn` affects source/subscription side.
8. Prefer end-to-end non-blocking stack (R2DBC + WebClient).
9. Use `boundedElastic` only as migration bridge for legacy blocking calls.
10. Pick backpressure strategy by business semantics, not guesswork.

---

## 30-Second Interview Script

"In WebFlux, the biggest production bug is blocking inside the reactive request pipeline. Since event-loop threads are few, a blocking JDBC or `.block()` call can stall many concurrent requests. The right architecture is end-to-end non-blocking I/O (WebClient/R2DBC). If migration is gradual, isolate legacy blocking with `Mono.fromCallable(...).subscribeOn(Schedulers.boundedElastic())`, plus timeout and bounded concurrency."

---

## Where to Read Details in Canonical File

- Reactive vs WebFlux distinction: section 1
- Event loop and starvation mechanics: sections 2-3
- Migration fix strategy: section 4
- `subscribeOn` vs `publishOn`: section 5
- `.block()` trap: section 6
- Backpressure choices: section 7
- Resilience patterns: section 8
- Data layer and transactions: section 9
- Testing and real-time choices: sections 11-12
- Final architect answer: section 15

---

## Update Policy

When content differs, `SpringBoot/webflux-senior-interview-questions.md` is source of truth.
Keep this file short and revision-oriented; do not duplicate full explanations here.
