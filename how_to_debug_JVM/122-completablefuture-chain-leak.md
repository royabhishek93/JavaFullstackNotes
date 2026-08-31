# #122 — CompletableFuture Chain Leak

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"How can CompletableFuture chains cause memory leaks?"

## 😊 Explain It Simply (for anyone)
A `CompletableFuture` (a placeholder representing "a result that will arrive later, asynchronously") is like a claim ticket for dry cleaning — once you pick up your clothes, you're supposed to throw the ticket away. If you keep every single ticket you've ever received in a big drawer "just in case," that drawer keeps growing forever, even for orders you already picked up long ago. Worse — if a ticket represents an order that NEVER gets finished (nobody ever tells the shop "it's done"), then everything connected to that unfinished order (all the promised follow-up steps) sits frozen in limbo forever, taking up space and never getting cleaned up.

## 📊 Visualize It
```
 activeFutures: [CF1(done), CF2(done), CF3(done), ... CF50000(done)]
                 ^ never removed even after completion — grows forever

 Unfinished future chain:
  upstream (never completed)
     |
     +-- .thenApply(expensiveObject)   <-- held forever, waiting
     +-- .thenAccept(...)              <-- held forever, waiting
```

## 🏭 The Real Production Answer (15-YOE Level)

Buggy code:
```java
public class DataPipeline {
    private final List<CompletableFuture<?>> activeFutures = new ArrayList<>();

    public void process(String input) {
        CompletableFuture<String> future = CompletableFuture
            .supplyAsync(() -> fetch(input))
            .thenApply(this::transform)
            .thenAccept(this::store);
        activeFutures.add(future); // LEAK: never removed, even after completion
    }
}
```

Why it leaks: `activeFutures` holds strong references to every CompletableFuture ever created. Even completed futures retain their result value and the chain of dependent stages until GC'd. With high throughput, thousands of completed futures accumulate.

Second form: futures that are never completed:
```java
// If a future in the chain is never completed (e.g., timeout not handled),
// all downstream stages and their captured lambdas remain reachable indefinitely
CompletableFuture<String> upstream = new CompletableFuture<>();
upstream.thenApply(s -> expensiveObject); // expensiveObject never released
// If nobody calls upstream.complete() or upstream.cancel(), this leaks
```

Fix:
```java
public void process(String input) {
    CompletableFuture
        .supplyAsync(() -> fetch(input))
        .thenApply(this::transform)
        .thenAccept(this::store)
        .orTimeout(30, TimeUnit.SECONDS)      // always set timeout
        .exceptionally(ex -> { log.error("Pipeline failed", ex); return null; });
    // Don't retain reference unless you need to cancel it
}
```

If you need to track active work for cancellation, use a `Set` with a removal callback:
```java
future.whenComplete((r, ex) -> activeFutures.remove(future));
```

## 🔑 Key Takeaway
Always set a timeout on `CompletableFuture` chains and remove futures from tracking collections in a `whenComplete` callback — never retain "just to track" without cleanup.
