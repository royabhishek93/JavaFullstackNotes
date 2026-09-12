> **Sequence 04/19 (Tier 1 🔥)** — See [README.md](README.md) for the full ranked index.

# `Mono` vs `Flux` — which one should a service/API return?

**Interview framing:** "What exactly is `Mono` vs `Flux`, and how do you decide which one to return from a service/API method?"

**Easy English explanation:**
- `Flux<T>` — a publisher that can emit **0, 1, or N elements** (any number, unbounded).
- `Mono<T>` — a publisher that can emit **0 or 1 element only**.

**Production decision rule (what interviewers actually want to hear):**

| Scenario | Return type | Why |
|---|---|---|
| `GET /orders/{id}` — fetch a single order | `Mono<Order>` | At most one row exists for a primary key lookup |
| `GET /orders` — fetch all orders for a user | `Flux<Order>` | Unbounded list of rows |
| `POST /orders` — create and return the created entity | `Mono<Order>` | One entity created, one entity returned |
| Streaming a live price ticker over SSE | `Flux<Price>` | Unbounded stream of future events |
| Calling another microservice that may return nothing (404) | `Mono<T>` (often combined with `switchIfEmpty`) | 0 or 1 result |

**Why the distinction matters for architects, not just types:** returning `Flux<Order>` from a single-row lookup **misleads API consumers** (and their auto-generated client code) into thinking multiple values might stream back, forces them to write unnecessary "collect to list" boilerplate, and can hide bugs where a query accidentally returns duplicate rows. Picking the tightest correct type (`Mono` vs `Flux`) is a code-review-level architectural signal, not a cosmetic choice.

> **One-line takeaway:** `Mono` = "give me at most one answer." `Flux` = "give me a stream of answers." Match your return type to your actual cardinality — don't default to `Flux` everywhere.

---
**Next:** [05-flatmap-vs-concatmap-vs-map.md](05-flatmap-vs-concatmap-vs-map.md)
