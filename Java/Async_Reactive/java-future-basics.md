# Java Future — Beginner Deep Dive

**Interview Priority:** Mid: 🔥 MUST KNOW | Senior: ✅ SHOULD KNOW (know limitations cold)

---

## Real-World Analogy First

Imagine you walk into a **pizza shop**:

```
WITHOUT Future (blocking):
  You: "One pizza please."
  You stand at the counter. Staring. Waiting. Doing nothing.
  [10 minutes pass]
  Pizza ready. You leave.

WITH Future (async):
  You: "One pizza please." → Cashier gives you a TOKEN (receipt number)
  You go sit, read your phone, drink water (do other work)
  [10 minutes pass, pizza is being made in the background]
  You check: "Is my pizza ready?" → YES → You pick it up and leave.
```

**The TOKEN is a `Future<Pizza>`.** It's a promise: *"I don't have the result now, but I will. Come back later."*

---

## What is `Future`?

`Future<T>` is an interface in `java.util.concurrent`. It represents the **result of an async computation** that hasn't finished yet.

```
Future<T>
├── get()               → block and wait for result
├── get(timeout, unit)  → block but give up after X time
├── isDone()            → check without blocking
├── isCancelled()       → was it cancelled?
└── cancel(boolean)     → try to stop it
```

A `Future` object is created when you **submit a task to an `ExecutorService`**.

---

## WITHOUT Future — What Actually Happens

### Code
```java
public class WithoutFuture {
    public static void main(String[] args) throws InterruptedException {
        System.out.println("Start");

        String user   = fetchUser();    // pretend this calls a DB — takes 2 seconds
        String orders = fetchOrders();  // pretend this calls an API — takes 3 seconds

        System.out.println("User: " + user + ", Orders: " + orders);
        System.out.println("Done");
    }

    static String fetchUser() throws InterruptedException {
        Thread.sleep(2000);             // simulates a DB call
        return "Alice";
    }

    static String fetchOrders() throws InterruptedException {
        Thread.sleep(3000);             // simulates an API call
        return "3 orders";
    }
}
```

### What happens step-by-step

```
Time    Main Thread
  0ms   main() starts
  0ms   fetchUser() called  ──── MAIN THREAD BLOCKED ──────────────────────┐
                                 (doing nothing, just waiting)              │
2000ms  fetchUser() returns "Alice"  ◄────────────────────────────────────┘
2000ms  fetchOrders() called  ──── MAIN THREAD BLOCKED ───────────────────┐
                                   (doing nothing again)                   │
5000ms  fetchOrders() returns "3 orders"  ◄──────────────────────────────┘
5000ms  print result
5000ms  Done
```

**Total time: 5 seconds (2 + 3). Both tasks ran one after the other.**

### ASCII Timeline

```
Thread: MAIN
|=====fetchUser=====|==========fetchOrders==========|--print--|
0s                  2s                               5s
                                              Total = 5 seconds
```

---

## WITH Future — The Fix

### Code (annotated line by line)

```java
import java.util.concurrent.*;

public class WithFuture {
    public static void main(String[] args) throws Exception {

        // Step 1: Create a thread pool with 2 threads
        ExecutorService pool = Executors.newFixedThreadPool(2);

        // Step 2: Submit task 1 — does NOT block. Returns a Future immediately.
        //         The actual work runs on a background thread.
        Future<String> userFuture = pool.submit(() -> fetchUser());

        // Step 3: Submit task 2 — also does NOT block. Another background thread picks it up.
        Future<String> ordersFuture = pool.submit(() -> fetchOrders());

        // Step 4: At this point, BOTH tasks are running in parallel.
        //         main thread is free to do other things here if needed.
        System.out.println("Both tasks submitted. Main thread is free!");

        // Step 5: .get() BLOCKS the main thread until the result is ready.
        //         userFuture.get() will wait ~2 seconds
        String user = userFuture.get();

        // Step 6: By the time userFuture.get() returns, ordersFuture is likely already done
        //         (it was running in parallel). So this returns almost instantly.
        String orders = ordersFuture.get();

        System.out.println("User: " + user + ", Orders: " + orders);

        // Step 7: Always shut down the pool or your program won't exit cleanly
        pool.shutdown();
    }

    static String fetchUser() throws InterruptedException {
        Thread.sleep(2000);
        return "Alice";
    }

    static String fetchOrders() throws InterruptedException {
        Thread.sleep(3000);
        return "3 orders";
    }
}
```

### What happens step-by-step

```
Time    Main Thread                 Thread-1 (pool)       Thread-2 (pool)
  0ms   pool created
  0ms   pool.submit(fetchUser)  →  fetchUser() starts
  0ms   pool.submit(fetchOrders)→                         fetchOrders() starts
  0ms   "Both tasks submitted"
  0ms   userFuture.get() BLOCKS
                                   [running...]           [running...]
2000ms  userFuture returns "Alice"  fetchUser done
2000ms  ordersFuture.get() →
        [already done! returns]                           fetchOrders done @ 3000ms
        Wait... actually:
```

> **Important detail:** `fetchOrders` takes 3s and started at 0ms. By the time `userFuture.get()` returns at 2000ms, `fetchOrders` still needs 1 more second. So `ordersFuture.get()` blocks for 1 more second.

### Corrected ASCII Timeline

```
Thread: MAIN      |--submit--|--submit--|---free---|--get()blocks--|--get()--|--print--|
Thread: pool-1    |=======fetchUser(2s)=======|
Thread: pool-2    |===============fetchOrders(3s)===============|

Time:   0s                              2s        3s
                                              Total = 3 seconds  (saved 2 seconds!)
```

**Total time: 3 seconds (longest task), not 5 seconds (sum of tasks).**

---

## The Future Object — What It Actually Is

```
pool.submit(callable)
      │
      │  creates on HEAP
      ▼
  ┌──────────────────────────────┐
  │   FutureTask<String>         │  ← this is what gets returned as Future<T>
  │                              │
  │   state: PENDING             │  ← changes as task progresses
  │   result: null               │
  │   exception: null            │
  │   runner: Thread-1           │
  └──────────────────────────────┘
```

### State Lifecycle

```
                submit()
                   │
                   ▼
              [ PENDING ]
                   │
        thread picks up the task
                   │
                   ▼
              [ RUNNING ]
               /       \
     completes            throws exception
          │                      │
          ▼                      ▼
       [ DONE ]           [ DONE (exceptional) ]
                                 │
                         get() throws ExecutionException
                         (wraps your original exception)

     OR if cancel() called before completion:
          ▼
      [ CANCELLED ]
```

---

## Each API Method — What it Does

### `future.get()` — block until done

```java
String result = future.get();
// Main thread STOPS here.
// Resumes only when background task finishes.
// If task threw an exception → throws ExecutionException
// If thread was interrupted  → throws InterruptedException
```

### `future.get(3, TimeUnit.SECONDS)` — block with timeout

```java
try {
    String result = future.get(3, TimeUnit.SECONDS);
} catch (TimeoutException e) {
    // task didn't finish in 3 seconds
    // Future is still running in background!
    future.cancel(true);  // optionally stop it
}
```

### `future.isDone()` — non-blocking check

```java
if (future.isDone()) {
    String result = future.get(); // safe — won't block
} else {
    System.out.println("Still working...");
}
```

### `future.cancel(boolean mayInterruptIfRunning)`

```java
future.cancel(true);
// true  → interrupt the thread if it's currently running
// false → only cancel if it hasn't started yet
// Returns: true if cancel succeeded, false if already done
```

---

## What Happens When the Task Throws an Exception

```java
Future<String> future = pool.submit(() -> {
    throw new RuntimeException("DB is down!");
});

try {
    String result = future.get();           // this line throws
} catch (ExecutionException e) {
    Throwable cause = e.getCause();         // unwrap to get original exception
    System.out.println(cause.getMessage()); // "DB is down!"
}
```

**The original exception is WRAPPED in `ExecutionException`.**  
Always call `e.getCause()` to get the real error.

---

## What If You Forget `.get()`?

```java
Future<String> future = pool.submit(() -> {
    processImportantData();   // DB write, file operation, etc.
    return "done";
});

// ... you never call future.get()
pool.shutdown();
// Problem: processImportantData() may still be running or may have silently failed.
// You'll never know.
```

**Rule:** If you submit a task that has side effects, always call `.get()` or at least `isDone()` to ensure it completed.

---

## The Big Problems With `Future` (Why CompletableFuture Exists)

| Problem | Example |
|---------|---------|
| `.get()` always blocks the calling thread | Can't use result without blocking |
| Can't chain tasks (`doA then doB with A's result`) | Need manual nesting and callback code |
| Can't combine multiple futures easily | `future1 + future2 → combined result` requires manual logic |
| No way to push a value in from outside | Can't complete it manually |
| Exception handling is clunky | Must catch `ExecutionException`, unwrap manually |

These are exactly the problems `CompletableFuture` (Java 8+) was designed to solve. See [Q10_completablefuture_basics.md](../../Java8to21/Q10_completablefuture_basics.md).

---

## Full Working Example — Everything Together

```java
import java.util.concurrent.*;

public class FutureFullExample {

    static ExecutorService pool = Executors.newFixedThreadPool(3);

    public static void main(String[] args) {

        System.out.println("[main] Submitting 3 tasks...");

        Future<String> f1 = pool.submit(() -> fetchFromDB());      // 2s
        Future<String> f2 = pool.submit(() -> fetchFromAPI());     // 1s
        Future<Integer> f3 = pool.submit(() -> computeScore());    // 3s

        System.out.println("[main] All 3 running in parallel. I'm free to do other work.");

        try {
            // isDone check — non-blocking poll
            System.out.println("[main] f2 done already? " + f2.isDone());

            String dbResult  = f1.get();               // blocks up to ~2s
            String apiResult = f2.get();               // already done by now, instant
            Integer score    = f3.get(5, TimeUnit.SECONDS); // wait max 5s

            System.out.println("DB: "    + dbResult);
            System.out.println("API: "   + apiResult);
            System.out.println("Score: " + score);

        } catch (TimeoutException e) {
            System.out.println("Score took too long, skipping.");
            f3.cancel(true);
        } catch (ExecutionException e) {
            System.out.println("Task failed: " + e.getCause().getMessage());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt(); // restore interrupt flag
        } finally {
            pool.shutdown();
        }
    }

    static String fetchFromDB()  throws InterruptedException { Thread.sleep(2000); return "DB data"; }
    static String fetchFromAPI() throws InterruptedException { Thread.sleep(1000); return "API data"; }
    static Integer computeScore()throws InterruptedException { Thread.sleep(3000); return 42; }
}
```

### Output

```
[main] Submitting 3 tasks...
[main] All 3 running in parallel. I'm free to do other work.
[main] f2 done already? false   ← checked immediately, f2 needs 1s
DB: DB data                     ← printed at ~2s
API: API data                   ← printed at ~2s (f2 finished at 1s, .get() instant)
Score: 42                       ← printed at ~3s
```

**Total time: ~3 seconds** (longest task), not 6 seconds (sum).

---

## Summary — When to Use What

| Scenario | Solution |
|----------|----------|
| Run one task in background, wait for result | `Future` |
| Run multiple independent tasks in parallel | `Future` + `ExecutorService` |
| Chain tasks (`A → B → C`) | `CompletableFuture` |
| Combine results of multiple futures | `CompletableFuture.allOf()` |
| React to result without blocking (`callback`) | `CompletableFuture` |

---

## Interview Q&A

**Q: What is `Future` in Java?**  
A: An interface representing the result of an async computation. You get a `Future` when you `submit()` a task to an `ExecutorService`. You can later call `.get()` to retrieve the result, blocking if it's not ready yet.

**Q: Does `submit()` block?**  
A: No. `submit()` returns immediately with a `Future`. The task runs on a background thread.

**Q: Does `get()` block?**  
A: Yes. `.get()` blocks the calling thread until the task finishes. Use `.get(timeout, unit)` to avoid blocking forever.

**Q: Task threw a `RuntimeException`. What does `get()` throw?**  
A: `ExecutionException`. The original exception is accessible via `e.getCause()`.

**Q: What's the difference between `isDone()` and `get()`?**  
A: `isDone()` is non-blocking — it just checks. `get()` blocks until done. Use `isDone()` for polling; use `get()` when you need the actual result.

**Q: What are the limitations of `Future`?**  
A: Cannot chain callbacks, cannot combine multiple futures elegantly, `.get()` always blocks, no manual completion, exception handling is verbose. `CompletableFuture` addresses all of these.

**Q: What happens if you never call `get()`?**  
A: The task still runs (and finishes or fails) in the background. You simply never receive the result or any exception. Silent failures are a real risk.

---

## Related Notes

- [asynchronous-programming-futures.md](../Multithreading_Concurrency/asynchronous-programming-futures.md) — Sequential vs parallel comparison overview
- [Q10_completablefuture_basics.md](../../Java8to21/Q10_completablefuture_basics.md) — Next step: chaining, callbacks, no-blocking patterns
- [Q11_chaining_completablefutures.md](../../Java8to21/Q11_chaining_completablefutures.md) — thenApply, thenCompose, allOf
