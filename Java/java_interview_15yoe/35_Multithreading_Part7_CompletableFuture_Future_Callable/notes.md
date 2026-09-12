# Future, Callable & CompletableFuture — Non-Blocking Async Chaining in Java

## What is this? (Plain English)

When you submit a task to a thread pool with `execute()`, it's like handing a letter to the postal service and walking away — you have zero way to know if it was delivered, lost, or is still in transit. `Future` fixes this: `submit()` hands you back a **claim ticket**. You can check the ticket later ("is it done yet?"), cancel the request, or wait at the counter until the result is ready.

`CompletableFuture` is the same claim ticket, but upgraded: instead of you standing at the counter waiting (`get()`), you can say "as soon as this is ready, automatically hand the result to the next counter, and then the next" — a relay/assembly-line of dependent steps that run without you blocking and waiting at every stage.

## The Problem It Solves

**Plain `Runnable` submitted via a thread pool has no status handle.** The caller thread continues immediately and has no reference to ask "did it finish? did it fail? what did it return?" — unless the return type of `submit()` is captured.

**`Future` (returned by `ExecutorService.submit()`) solves the status problem but is still limited:**
- `future.cancel(true)` — attempts to interrupt/cancel the task. Returns `false` if the task already completed (can't cancel it).
- `future.isCancelled()` — was it cancelled before completing.
- `future.isDone()` — `true` for *any* completion (normal, exception, or cancellation).
- `future.get()` — **blocks the caller indefinitely** until the task finishes, then returns the result.
- `future.get(timeout, unit)` — blocks only up to the timeout, then throws `TimeoutException` if the task isn't done yet.

**`Runnable` vs `Callable`:** both represent a task to run; the only difference is `Runnable.run()` returns nothing, while `Callable.call()` returns a value. This gives `ExecutorService.submit()` three overloads:
- `submit(Runnable)` → `Future<?>` whose `get()` **always returns `null`** (there's nothing to return).
- `submit(Runnable, T result)` → a workaround: you pass in a shared mutable object (e.g. a `List`); the `Runnable` mutates it during `run()`; `future.get()` then returns that same object reference, now updated.
- `submit(Callable<T>)` → the cleanest option: the task itself returns the actual computed value.

Internally, `submit()` wraps whatever you give it into a **`FutureTask`** (which implements `RunnableFuture`, i.e. both `Runnable` and `Future`), bundling the task together with its internal execution state. The pool updates that state as the task runs, and the `FutureTask` reference is what you get back as the `Future`.

**The real limitation: `Future.get()` is a blocking dead end.** If you need to run several *dependent* async steps (step 2 needs step 1's result, step 3 needs step 2's, etc.), plain `Future` forces you to call `get()` (blocking) after every single step before you can even start the next one — you gain nothing over synchronous code except the first hop. There's also no built-in way to combine two independent `Future`s' results without blocking on both first.

**`CompletableFuture` (Java 8) is a `Future` implementation that adds non-blocking composition** — you can chain transformations (`thenApply`), chain dependent async stages (`thenCompose`), combine two independent async results (`thenCombine`), and consume a final result (`thenAccept`) — all without the calling thread blocking until you explicitly ask for the final result with `get()`/`join()`.

`supplyAsync(supplier)` is the entry point — like `submit()`, but if you don't pass your own `Executor`, it silently uses the shared **`ForkJoinPool.commonPool()`**, which sizes itself dynamically based on available processors and gives you **no control** over minimum/maximum thread counts. Pass your own executor when you need predictable resource limits.

## CompletableFuture Chaining — Sequence Diagram

```
Lanes: Main = Main Thread | Pool = Executor / ForkJoinPool | T1 = Worker Thread (supplyAsync) | T2 = Worker Thread (Async stage)

1)  Main ──────────> Pool : supplyAsync(supplier, executor)
2)  Pool ──────────> T1   : run supplier task
3)  Main ──(self-call)─>       : continue other work (non-blocking)
    note: T1 sleeps / does work (e.g. 5s)
4)  Pool <────────── T1   : returns result "concept"
5)  Pool ──────────> T1   : thenApply(fn) - SYNCHRONOUS, same thread reused
    note: runs fn on the SAME thread that finished supplyAsync
6)  Pool <────────── T1   : returns result "concept and coding"
7)  Pool ──────────> T2   : thenApplyAsync(fn) - submitted to executor/ForkJoinPool
    note: NEW thread picked from pool
8)  Pool <────────── T2   : returns result
9)  Pool ──────────> T2   : thenCompose(fn) - flattens nested CompletableFuture, preserves order
    note: waits for its own async stage before continuing
10) Pool <────────── T2   : returns final composed result
11) Pool ──────────> T2   : thenAccept(consumer) - end of chain, returns void
    note: consumes result, no further chaining possible
12) Main ──────────> Pool : cf.get() / cf.join()
    note: Main BLOCKS here until entire chain completes
13) Main <────────── Pool : final result delivered
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Key Code / Config

### 1. `Callable` + `Future` basics — status checks, blocking `get()`, timeout

```java
import java.util.concurrent.*;

public class FutureBasicsDemo {
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(1);

        // submit() returns a Future - the "claim ticket" for the async task
        Future<?> future = pool.submit(() -> {
            try {
                Thread.sleep(7000); // simulate a long-running task
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            System.out.println("Task finished on: " + Thread.currentThread().getName());
        });

        System.out.println("Is done right after submit? " + future.isDone()); // false, task takes 7s

        try {
            future.get(2, TimeUnit.SECONDS); // wait at most 2 seconds
        } catch (TimeoutException e) {
            System.out.println("Timed out waiting 2 seconds - task still running");
        }

        future.get(); // now block indefinitely until the task actually completes
        System.out.println("Is done now? " + future.isDone());       // true
        System.out.println("Is cancelled? " + future.isCancelled()); // false - completed normally

        pool.shutdown();
    }
}
```

### 2. `submit(Runnable)` vs `submit(Runnable, T)` vs `submit(Callable<T>)`

```java
import java.util.*;
import java.util.concurrent.*;

public class SubmitVariantsDemo {

    // Custom Runnable that mutates a shared list passed in via its constructor
    static class ListUpdatingTask implements Runnable {
        private final List<Integer> sharedOutput;
        ListUpdatingTask(List<Integer> sharedOutput) { this.sharedOutput = sharedOutput; }
        @Override public void run() {
            sharedOutput.add(300);
        }
    }

    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);

        // 1) submit(Runnable) -> Future<?> - get() always returns null (no return type)
        Future<?> f1 = pool.submit(() -> System.out.println("plain runnable, no result"));
        System.out.println("submit(Runnable) result: " + f1.get()); // always null

        // 2) submit(Runnable, T) -> workaround: mutate a shared object,
        //    future.get() returns that same reference, now updated
        List<Integer> output = new ArrayList<>();
        Future<List<Integer>> f2 = pool.submit(new ListUpdatingTask(output), output);
        List<Integer> result2 = f2.get(); // blocks until the task completes
        System.out.println("submit(Runnable, T) result: " + result2.get(0)); // 300

        // 3) submit(Callable<T>) -> cleanest option: the task itself returns the value
        Future<List<Integer>> f3 = pool.submit(() -> {
            List<Integer> callableOutput = new ArrayList<>();
            callableOutput.add(300);
            return callableOutput;
        });
        List<Integer> result3 = f3.get();
        System.out.println("submit(Callable) result: " + result3.get(0)); // 300

        pool.shutdown();
    }
}
```

### 3. `CompletableFuture.supplyAsync` + `thenApply` vs `thenApplyAsync`

```java
import java.util.concurrent.*;

public class CompletableFutureApplyDemo {
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);

        CompletableFuture<String> cf = CompletableFuture
            .supplyAsync(() -> {
                sleep(5000);
                System.out.println("supplyAsync running on: " + Thread.currentThread().getName());
                return "concept";
            }, pool)
            // thenApply -> SYNCHRONOUS: runs on the SAME thread that completed supplyAsync
            .thenApply(result -> {
                System.out.println("thenApply running on: " + Thread.currentThread().getName());
                return result + " and coding";
            })
            // thenApplyAsync -> runs on a NEW thread (ForkJoinPool.commonPool() if no executor passed)
            .thenApplyAsync(result -> {
                System.out.println("thenApplyAsync running on: " + Thread.currentThread().getName());
                return result + "!";
            });

        System.out.println("Final result: " + cf.get()); // blocks main thread until the whole chain finishes
        pool.shutdown();
    }

    static void sleep(long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
}
```

### 4. `thenCompose` vs `thenComposeAsync` — ordering guarantee for dependent stages

```java
import java.util.concurrent.*;

public class CompletableFutureComposeDemo {
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);

        CompletableFuture<String> chained = CompletableFuture
            .supplyAsync(() -> "Hello", pool)
            // thenCompose flattens a nested CompletableFuture and preserves ordering,
            // even across multiple *Async stages
            .thenCompose(prev -> CompletableFuture.supplyAsync(() -> prev + " World", pool))
            .thenCompose(prev -> CompletableFuture.supplyAsync(() -> prev + "!!"));

        // Guaranteed output order: "Hello" -> "Hello World" -> "Hello World!!"
        // (plain thenApply/thenApplyAsync chains do not guarantee this ordering)
        System.out.println(chained.get());
        pool.shutdown();
    }
}
```

### 5. `thenAccept` — end of the chain, no return value

```java
import java.util.concurrent.*;

public class CompletableFutureAcceptDemo {
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(1);

        CompletableFuture<Void> cf = CompletableFuture
            .supplyAsync(() -> "final value", pool)
            // thenAccept consumes the result but returns nothing (Void) -
            // nothing left to chain a further thenApply onto afterward
            .thenAccept(value -> System.out.println("Consumed: " + value));

        cf.get(); // block until the consumer has run
        pool.shutdown();
    }
}
```

### 6. `thenCombine` — merging two independent futures

```java
import java.util.concurrent.*;

public class CompletableFutureCombineDemo {
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);

        CompletableFuture<Integer> task1 = CompletableFuture.supplyAsync(() -> 10, pool);
        CompletableFuture<String> task2 = CompletableFuture.supplyAsync(() -> "K", pool);

        // thenCombine merges the results of two INDEPENDENT completable futures
        // (task2 does not depend on task1's result, unlike thenCompose)
        CompletableFuture<String> combined = task1.thenCombine(task2, (num, unit) -> num + unit);

        System.out.println(combined.get()); // "10K"
        pool.shutdown();
    }
}
```

## Interview Q&A

**Q1: What's the difference between `Runnable` and `Callable`, and how does that affect `ExecutorService.submit()`?**
A: `Runnable.run()` returns nothing; `Callable.call()` returns a value of type `T`. `submit(Runnable)` gives you a `Future<?>` whose `get()` always returns `null`, while `submit(Callable<T>)` gives you a `Future<T>` with the actual computed result.

**Q2: Why does `future.get()` sometimes block forever, and how do you avoid it?**
A: The no-argument `get()` blocks the caller indefinitely until the task completes, fails, or is cancelled. Use `get(timeout, unit)` to cap the wait — it throws `TimeoutException` if the task isn't done in time, so the caller can decide whether to retry, log, or move on instead of blocking indefinitely.

**Q3: What actually happens internally when you call `executorService.submit(task)`?**
A: `submit()` wraps the given `Runnable`/`Callable` in a `FutureTask` (which implements `RunnableFuture`, extending both `Runnable` and `Future`), bundling the task together with its internal execution state. The pool updates that state as it runs the task, and the `FutureTask` reference is what's returned to the caller as the `Future`.

**Q4: What's the difference between `thenApply` and `thenApplyAsync`?**
A: `thenApply` is synchronous — it runs on whichever thread completed the previous stage, no new thread is created. `thenApplyAsync` submits the continuation to an executor (the common `ForkJoinPool` by default, or a custom executor if supplied), so it may run on a different thread, freeing the previous thread to go back to its pool sooner.

**Q5: When would you use `thenCompose` instead of `thenApply`, and why does ordering matter here?**
A: Use `thenCompose` when the next async step's execution genuinely depends on the previous stage's result — it flattens a `CompletableFuture<CompletableFuture<T>>` down to `CompletableFuture<T>` and guarantees the stages run in the declared order internally, using a maintained sequence of dependent actions. Plain `thenApply`/`thenApplyAsync` chains don't give that ordering guarantee across async stages on their own.

**Q6: What does `supplyAsync` do if you don't pass an `Executor`, and what's the downside?**
A: It runs the supplier on a thread from the shared `ForkJoinPool.commonPool()`, which dynamically sizes itself based on available processors. The downside is you have no control over the pool's minimum/maximum thread count, and you're sharing that pool with any other code in the JVM relying on it — for production code that needs predictable resource limits, pass your own `Executor`.
