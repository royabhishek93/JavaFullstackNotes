# Reactive Programming — Interview Q&A Index (Ranked for 15+ YOE / Architect Interviews)

Each question lives in its own file, numbered by **interview priority** — start at `01` and work down. Higher numbers are more niche/basic and less likely to be the deciding question in a senior/architect round.

## 🔥 Tier 1 — Architecture & Scalability Decisions (most likely to gate a senior/architect round)

| # | File | Question |
|---|---|---|
| 01 | [01-why-webflux-over-mvc-netty-vs-tomcat.md](01-why-webflux-over-mvc-netty-vs-tomcat.md) | Why choose Spring WebFlux over Spring MVC? Netty vs Tomcat |
| 02 | [02-blocking-call-poisons-event-loop.md](02-blocking-call-poisons-event-loop.md) | The #1 production pitfall: one blocking call poisons the whole event loop |
| 03 | [03-publisher-subscriber-backpressure.md](03-publisher-subscriber-backpressure.md) | Publisher-Subscriber handshake & backpressure (`request(n)`, `onNext`, `onComplete`) |
| 04 | [04-mono-vs-flux-decision-rule.md](04-mono-vs-flux-decision-rule.md) | `Mono` vs `Flux` — which one should a service/API return? |
| 05 | [05-flatmap-vs-concatmap-vs-map.md](05-flatmap-vs-concatmap-vs-map.md) | Async fan-out per element: `map` vs `flatMap` vs `concatMap` |
| 06 | [06-webclient-vs-resttemplate-feign.md](06-webclient-vs-resttemplate-feign.md) | `WebClient` vs `RestTemplate`/Feign for inter-service calls |

## ⭐ Tier 2 — Core Reactive Semantics (expected working knowledge)

| # | File | Question |
|---|---|---|
| 07 | [07-stream-vs-flux-replayability.md](07-stream-vs-flux-replayability.md) | `Stream` vs `Flux`/`Mono` — single-use vs replayable |
| 08 | [08-multiple-subscribers-behavior.md](08-multiple-subscribers-behavior.md) | What happens when multiple subscribers attach to one publisher? |
| 09 | [09-concat-vs-merge-vs-zip.md](09-concat-vs-merge-vs-zip.md) | Combining two Flux sources: `concat` vs `merge` vs `zip` |
| 10 | [10-defaultifempty-vs-switchifempty.md](10-defaultifempty-vs-switchifempty.md) | Fallback on empty results: `defaultIfEmpty` vs `switchIfEmpty` (cache-aside) |

## 👍 Tier 3 — Good-to-Know Depth

| # | File | Question |
|---|---|---|
| 11 | [11-functional-endpoints-routerfunction.md](11-functional-endpoints-routerfunction.md) | Functional endpoints: `RouterFunction`/`HandlerFunction` vs `@RestController` |
| 12 | [12-stepverifier-testing.md](12-stepverifier-testing.md) | Testing reactive pipelines deterministically with `StepVerifier` |
| 13 | [13-doOn-side-effect-operators.md](13-doOn-side-effect-operators.md) | Observability without mutation: `doOnNext`/`doOnSubscribe`/`doOnComplete` |
| 14 | [14-transform-reusable-pipelines.md](14-transform-reusable-pipelines.md) | Reusable operator chains with `transform()` |

## ⚙️ Tier 4 — Foundational Basics (assumed knowledge, rarely the main question)

| # | File | Question |
|---|---|---|
| 15 | [15-map-operator.md](15-map-operator.md) | The `map()` operator and its blocking-call trap |
| 16 | [16-filter-operator.md](16-filter-operator.md) | The `filter()` operator |
| 17 | [17-flux-laziness-subscribe.md](17-flux-laziness-subscribe.md) | Why nothing happens until `.subscribe()` is called |
| 18 | [18-creating-flux-from-list.md](18-creating-flux-from-list.md) | Creating a `Flux`/`Mono` from a `List`/fixed values |
| 19 | [19-stream-pull-model-peek-limit-skip.md](19-stream-pull-model-peek-limit-skip.md) | `Stream` pull-model trivia: `peek()`/`limit()`/`skip()` ordering puzzle |

---

## How to use this for interview prep

- **1–2 days out:** Read Tier 1 (01–06) end-to-end — these are the questions that separate a senior engineer answer from an architect answer (trade-offs, production incidents, cost/scalability reasoning).
- **3–5 days out:** Add Tier 2 (07–10) — core semantics interviewers assume you already know.
- **1 week+ out:** Work through Tier 3–4 (11–19) for completeness and to handle follow-up/rapid-fire questions.
