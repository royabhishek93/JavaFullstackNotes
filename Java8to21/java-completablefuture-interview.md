# CompletableFuture - Interview Overview

**Use this file as a map. Full topic-wise guides are linked below.**

---

## Why This Exists

The repo contains three dedicated CompletableFuture notes. This file avoids repetition and gives a clean study path.

---

## Study Map (Topic-Wise)

1) Basics: what it is, supplyAsync/runAsync, blocking vs non-blocking
- [Java8to21/Q10_completablefuture_basics.md](Java8to21/Q10_completablefuture_basics.md)

2) Chaining: `thenCompose` vs `thenApply`, combining futures
- [Java8to21/Q11_chaining_completablefutures.md](Java8to21/Q11_chaining_completablefutures.md)

3) Exceptions: `exceptionally`, `handle`, `whenComplete`
- [Java8to21/Q12_exception_handling_completablefuture.md](Java8to21/Q12_exception_handling_completablefuture.md)

---

## Quick Recall

- `supplyAsync()` for values, `runAsync()` for void.
- Use `thenCompose()` for async chaining (avoid nested futures).
- Use `thenApply()` for sync transforms.
- Use `exceptionally()` or `handle()` for recovery.

---

## Interview Answer (One-Liner)

> "CompletableFuture lets me compose async work without blocking: `supplyAsync`, chain with `thenCompose`, combine with `allOf`, and handle failures with `exceptionally` or `handle`."

