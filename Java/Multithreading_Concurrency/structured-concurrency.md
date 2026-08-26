# Structured Concurrency (Java 25 — GA)

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: 👍 GOOD TO KNOW

---

## Scenario

**Given this code, what are the three problems when one of the subtasks fails?**

```java
Future<User>   userFuture   = pool.submit(() -> fetchUser(id));
Future<Orders> ordersFuture = pool.submit(() -> fetchOrders(id));

User   user   = userFuture.get();
Orders orders = ordersFuture.get();
```

**Problems:**
1. If `fetchUser` throws, `fetchOrders` keeps running (wasted work / resource leak).
2. If the calling thread is interrupted, futures are not cancelled.
3. If `fetchOrders` throws while waiting on `userFuture.get()`, the exception is lost.

---

## Key Principle

**Structured concurrency treats a group of concurrent tasks as a single unit of work: if the scope exits, all subtasks are cancelled. Tasks never outlive their scope.**

---

## Why It Happens (Simple English)

Unstructured concurrency (`ExecutorService` + `Future`) has no relationship between the lifetime of subtasks and the calling code. Structured concurrency enforces that child tasks are always bound to their parent scope — just like structured control flow (`if`, `try`) bounds code blocks.

---

## Basic Usage — ShutdownOnFailure

```java
import java.util.concurrent.StructuredTaskScope;

try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {

    StructuredTaskScope.Subtask<User>   userTask   = scope.fork(() -> fetchUser(id));
    StructuredTaskScope.Subtask<Orders> ordersTask = scope.fork(() -> fetchOrders(id));

    scope.join();           // wait for both
    scope.throwIfFailed();  // propagate exception if any subtask failed

    // BOTH succeeded — safe to use results
    return new Response(userTask.get(), ordersTask.get());

} // scope closes here — any still-running subtasks are cancelled
```

**If `fetchUser` fails:**
- `ShutdownOnFailure` cancels `fetchOrders` immediately.
- `throwIfFailed()` re-throws the cause.
- No resource leaks.

---

## ShutdownOnSuccess — First Result Wins

```java
try (var scope = new StructuredTaskScope.ShutdownOnSuccess<String>()) {

    scope.fork(() -> fetchFromPrimaryDB());
    scope.fork(() -> fetchFromCache());

    scope.join();

    return scope.result(); // first successful result
}
// As soon as one succeeds, the other is cancelled
```

---

## Subtask States

```java
StructuredTaskScope.Subtask<String> task = scope.fork(() -> work());

// After scope.join():
task.state()  // UNAVAILABLE, SUCCESS, or FAILED

task.get()    // result — only valid if state == SUCCESS
task.exception() // exception — only valid if state == FAILED
```

---

## Nested Scopes

```java
// Parent scope can contain child scopes — lifetime is always nested
try (var outer = new StructuredTaskScope.ShutdownOnFailure()) {
    outer.fork(() -> {
        try (var inner = new StructuredTaskScope.ShutdownOnFailure()) {
            inner.fork(() -> step1());
            inner.fork(() -> step2());
            inner.join().throwIfFailed();
            return "inner done";
        }
    });
    outer.join().throwIfFailed();
}
```

---

## Unstructured vs Structured

| | `ExecutorService` + `Future` | Structured Concurrency |
|---|---|---|
| Lifetime of subtasks | Unbounded — can outlive caller | Bounded to scope |
| Cancellation on failure | Manual | Automatic |
| Error propagation | Manual (check each future) | `throwIfFailed()` |
| Observability / debugging | Hard (tasks float freely) | Tree matches call tree |
| Java version | Java 5 | **Java 25 (GA)** |

---

## With Virtual Threads (Natural Fit)

```java
// Combine structured concurrency with virtual threads for scalable I/O
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    // Each fork() creates a virtual thread — very cheap
    scope.fork(() -> callServiceA());
    scope.fork(() -> callServiceB());
    scope.fork(() -> callServiceC());

    scope.join().throwIfFailed();
}
```

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| `Future` left running after caller fails | `StructuredTaskScope` — auto-cancelled on scope exit |
| Manual `future.cancel()` in catch blocks | Scope handles cancellation automatically |
| `ExecutorService.invokeAll()` for fan-out | `scope.fork()` — lifetime guaranteed |

---

## Interview Tip (Exact Answer)

"Structured concurrency, GA in Java 25, ensures that subtasks never outlive the scope that spawned them. `ShutdownOnFailure` cancels all siblings on the first failure, and `throwIfFailed()` propagates the error. This eliminates the resource leak and error-swallowing problems of unstructured `Future`-based code."

---

## Quick Checklist

- Use `StructuredTaskScope` in a try-with-resources block — scope always closes.
- `scope.fork()` creates a subtask (runs on a virtual thread by default).
- `scope.join()` waits for all subtasks to complete or the scope to shut down.
- `throwIfFailed()` after `join()` — always call this for `ShutdownOnFailure`.
- `scope.result()` for `ShutdownOnSuccess` — returns the first winner.

---

## Critical Pitfalls

- Do NOT call `subtask.get()` before `scope.join()` — it will throw.
- `StructuredTaskScope` is NOT a general-purpose executor — do not store and reuse it.
- Subtasks that are CPU-bound still benefit from scoping even without virtual threads.
- Exceptions thrown in `fork()` callbacks must not be swallowed — use `throwIfFailed()`.

---

## Follow-up Questions & Answers

**Q:** How is `StructuredTaskScope` different from `CompletableFuture.allOf()`?

**A:** `allOf` has no enforced lifetime — futures can outlive the calling context. `StructuredTaskScope` guarantees tasks are cancelled when the scope closes, and links their lifecycle to the call stack, making failure handling and observability much cleaner.

**Q:** Can I create a custom scope policy?

**A:** Yes — extend `StructuredTaskScope<T>` and override `handleComplete(Subtask<? extends T>)` to implement your own shutdown strategy.

---

## How to Use for Interviews

- Lead with the three problems of unstructured `Future` code (leak, swallowed errors, no cancellation).
- Show `ShutdownOnFailure` + `join().throwIfFailed()` — the most common pattern.
- Contrast with `CompletableFuture.allOf()` — lifetime and cancellation are the key differences.
- Mention it pairs naturally with virtual threads (Project Loom).

---

**Last Updated:** August 18, 2026
