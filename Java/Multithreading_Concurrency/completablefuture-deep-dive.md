# CompletableFuture — Deep Dive (All Operators)

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: 🔥 MUST KNOW

---

## Scenario

**Given this code, what's wrong?**

```java
CompletableFuture<String> cf = CompletableFuture.supplyAsync(() -> fetchUser());
cf.thenApply(user -> transform(user));
System.out.println(cf.get()); // gets raw user, not transformed
```

**Problem:** `thenApply` returns a NEW `CompletableFuture`. The original `cf` is unchanged.

---

## Key Principle

**`CompletableFuture` chains are immutable pipelines — each stage returns a new future; always use the returned value.**

---

## Creation Methods

```java
// Already-completed value
CompletableFuture<String> done = CompletableFuture.completedFuture("hello");

// Async with result (uses ForkJoinPool.commonPool() by default)
CompletableFuture<String> cf = CompletableFuture.supplyAsync(() -> fetchData());

// Async with result + custom executor
ExecutorService pool = Executors.newFixedThreadPool(4);
CompletableFuture<String> cf2 = CompletableFuture.supplyAsync(() -> fetchData(), pool);

// Async, no result
CompletableFuture<Void> cf3 = CompletableFuture.runAsync(() -> doWork());
```

---

## Transformation Operators

```java
CompletableFuture<String> cf = CompletableFuture.supplyAsync(() -> "hello");

// thenApply — sync transform (runs in same thread that completed cf)
CompletableFuture<Integer> len = cf.thenApply(String::length);

// thenApplyAsync — async transform (runs in pool thread)
CompletableFuture<Integer> lenAsync = cf.thenApplyAsync(String::length);

// thenCompose — flatMap: when the function itself returns a CompletableFuture
CompletableFuture<String> orders = cf.thenCompose(user -> fetchOrders(user));
// (avoids CompletableFuture<CompletableFuture<String>>)

// thenAccept — consume result, return Void
CompletableFuture<Void> printed = cf.thenAccept(System.out::println);

// thenRun — run action, ignore result
CompletableFuture<Void> ran = cf.thenRun(() -> System.out.println("done"));
```

---

## Combining Two Futures

```java
CompletableFuture<String> user   = supplyAsync(() -> fetchUser());
CompletableFuture<String> orders = supplyAsync(() -> fetchOrders());

// thenCombine — combine two independent results
CompletableFuture<String> both = user.thenCombine(orders, (u, o) -> u + ":" + o);

// thenAcceptBoth — consume both, return Void
user.thenAcceptBoth(orders, (u, o) -> System.out.println(u + o));

// runAfterBoth — run action when both complete
user.runAfterBoth(orders, () -> System.out.println("both done"));

// applyToEither — take whichever completes first
CompletableFuture<String> first = user.applyToEither(orders, s -> s.toUpperCase());

// acceptEither — consume whichever arrives first
user.acceptEither(orders, System.out::println);
```

---

## Combining Many Futures

```java
CompletableFuture<String> a = supplyAsync(() -> "A");
CompletableFuture<String> b = supplyAsync(() -> "B");
CompletableFuture<String> c = supplyAsync(() -> "C");

// allOf — wait for ALL (result is Void; join each for values)
CompletableFuture<Void> all = CompletableFuture.allOf(a, b, c);
all.join(); // blocks until all done
String results = a.join() + b.join() + c.join();

// anyOf — complete as soon as ANY one completes
CompletableFuture<Object> any = CompletableFuture.anyOf(a, b, c);
System.out.println(any.join()); // first to finish
```

---

## Error Handling

```java
CompletableFuture<String> cf = supplyAsync(() -> {
    if (true) throw new RuntimeException("fail");
    return "ok";
});

// exceptionally — recover from error
CompletableFuture<String> recovered = cf.exceptionally(ex -> "default");

// handle — transform result OR exception (always runs)
CompletableFuture<String> handled = cf.handle((result, ex) -> {
    if (ex != null) return "error: " + ex.getMessage();
    return result.toUpperCase();
});

// whenComplete — side-effect only (does not transform)
cf.whenComplete((result, ex) -> {
    if (ex != null) log.error("failed", ex);
    else log.info("result: " + result);
});
```

---

## Timeout (Java 9+)

```java
CompletableFuture<String> cf = supplyAsync(() -> slowFetch());

// Complete exceptionally if not done in 2s
cf.orTimeout(2, TimeUnit.SECONDS);

// Complete with fallback value if not done in 2s
cf.completeOnTimeout("fallback", 2, TimeUnit.SECONDS);
```

---

## get() vs join()

| | `get()` | `join()` |
|---|---|---|
| Exception type | Checked (`ExecutionException`) | Unchecked (`CompletionException`) |
| Use in streams | No (checked throws) | Yes |
| Blocking | Yes | Yes |

```java
// In streams, join() is cleaner
List<String> results = futures.stream()
    .map(CompletableFuture::join)
    .collect(Collectors.toList());
```

---

## thenApply vs thenCompose

```java
// thenApply: function returns plain value
CompletableFuture<String> upper = cf.thenApply(s -> s.toUpperCase());

// thenCompose: function returns CompletableFuture (flatMap)
CompletableFuture<Order> order = cf.thenCompose(userId -> fetchOrderAsync(userId));
// NOT: cf.thenApply(userId -> fetchOrderAsync(userId))
//      ^ that gives CompletableFuture<CompletableFuture<Order>>
```

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| Discard returned stage | Chain from returned `CompletableFuture` |
| `thenApply` returning `CF<T>` | Use `thenCompose` for flatMap |
| Using common pool for blocking I/O | Pass custom `ExecutorService` |
| Ignoring exceptions silently | Use `exceptionally` or `handle` |

---

## Complete Pipeline Example

```java
ExecutorService pool = Executors.newFixedThreadPool(10);

CompletableFuture.supplyAsync(() -> fetchUserId(), pool)
    .thenComposeAsync(id -> fetchUser(id), pool)
    .thenCombineAsync(
        CompletableFuture.supplyAsync(() -> fetchConfig(), pool),
        (user, config) -> buildResponse(user, config),
        pool
    )
    .orTimeout(5, TimeUnit.SECONDS)
    .exceptionally(ex -> Response.error(ex.getMessage()))
    .thenAccept(response -> send(response));
```

---

## Interview Tip (Exact Answer)

"`thenApply` transforms a value synchronously, `thenCompose` is flatMap for when the function returns another `CompletableFuture`. Always use `handle` or `exceptionally` for error recovery, and always pass a custom executor to avoid blocking the common pool with I/O."

---

## Quick Checklist

- `supplyAsync` for tasks with results, `runAsync` for fire-and-forget.
- `thenApply` = map, `thenCompose` = flatMap.
- `thenCombine` for two independent futures, `allOf` for N futures.
- `handle` runs always (normal + exceptional); `exceptionally` runs only on error.
- `orTimeout` / `completeOnTimeout` for deadline control (Java 9+).
- Prefer `join()` over `get()` inside streams.

---

## Critical Pitfalls

- `allOf` result is `Void` — you must call `.join()` on each individual future for values.
- The common `ForkJoinPool` is shared with parallel streams — I/O in it starves CPU tasks.
- Exceptions in async stages are wrapped in `CompletionException`; unwrap with `getCause()`.
- `thenApply` vs `thenApplyAsync` — the Async variant always hops to a pool thread; the non-Async variant may run inline.

---

## Follow-up Questions & Answers

**Q:** What is the difference between `handle` and `exceptionally`?

**A:** `exceptionally` only runs when there is an exception. `handle` always runs and receives both the result and exception (one will be null).

**Q:** How do you run 10 async calls and collect all results?

**A:**
```java
List<CompletableFuture<String>> futures = ids.stream()
    .map(id -> supplyAsync(() -> fetch(id), pool))
    .collect(Collectors.toList());

CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
    .join();

List<String> results = futures.stream()
    .map(CompletableFuture::join)
    .collect(Collectors.toList());
```

---

## How to Use for Interviews

- Draw the pipeline: supply → compose → combine → handle → accept.
- Contrast `thenApply`/`thenCompose` with map/flatMap (interviewers love this).
- Show `allOf` + individual `.join()` for collecting N results.
- Always mention custom executor for production use.

---

**Last Updated:** August 18, 2026
