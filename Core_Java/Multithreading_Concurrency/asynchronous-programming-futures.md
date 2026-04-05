# Asynchronous Programming (Future and CompletableFuture)

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: 🔥 MUST KNOW

---

## Scenario

**Given this code, why is it slow?**

```java
public class BlockingCalls {
    public static void main(String[] args) throws Exception {
        String user = getUser();      // 1s
        String orders = getOrders();  // 1s
        System.out.println(user + orders);
    }

    private static String getUser() throws InterruptedException {
        Thread.sleep(1000);
        return "User";
    }

    private static String getOrders() throws InterruptedException {
        Thread.sleep(1000);
        return "Orders";
    }
}
```

**Problem:** Calls are sequential. Total time = 2 seconds.

---

## Key Principle

**Async programming runs independent tasks in parallel and combines results.**

---

## Why It Happens (Simple English)

Blocking calls wait one after another. Futures let you run tasks in the background and get results later. `CompletableFuture` adds chaining and combination.

---

## Future (Basic Async)

```java
import java.util.concurrent.*;

public class FutureExample {
    public static void main(String[] args) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(2);

        Future<String> userFuture = pool.submit(() -> getUser());
        Future<String> ordersFuture = pool.submit(() -> getOrders());

        String result = userFuture.get() + ordersFuture.get();
        System.out.println(result); // UserOrders

        pool.shutdown();
    }

    private static String getUser() throws InterruptedException {
        Thread.sleep(1000);
        return "User";
    }

    private static String getOrders() throws InterruptedException {
        Thread.sleep(1000);
        return "Orders";
    }
}
```

---

## CompletableFuture (Non-Blocking + Chaining)

```java
import java.util.concurrent.*;

public class CompletableFutureExample {
    public static void main(String[] args) throws Exception {
        CompletableFuture<String> userFuture =
            CompletableFuture.supplyAsync(() -> getUser());

        CompletableFuture<String> ordersFuture =
            CompletableFuture.supplyAsync(() -> getOrders());

        CompletableFuture<String> combined = userFuture.thenCombine(
            ordersFuture,
            (user, orders) -> user + orders
        );

        System.out.println(combined.get()); // UserOrders
    }

    private static String getUser() {
        sleep(1000); return "User";
    }

    private static String getOrders() {
        sleep(1000); return "Orders";
    }

    private static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| Sequential blocking calls | Parallel futures + combine |
| `Future` + manual waiting | `CompletableFuture` chaining |

**Wrong:**
```java
String a = callA();
String b = callB();
```

**Right:**
```java
CompletableFuture<String> a = supplyAsync(this::callA);
CompletableFuture<String> b = supplyAsync(this::callB);
CompletableFuture<String> c = a.thenCombine(b, (x, y) -> x + y);
```

---

## Interview Tip (Exact Answer)

"`Future` gives me async execution but I still block on `get()`. `CompletableFuture` lets me chain, combine, and handle errors without blocking, which is better for parallel I/O calls."

---

## Quick Checklist

- Use `Future` for simple async tasks.
- Use `CompletableFuture` for chaining and combining.
- Always handle exceptions (`exceptionally`, `handle`).
- Provide a custom executor for control.

---

## Critical Pitfalls

- `CompletableFuture.supplyAsync` uses the common pool by default.
- Forgetting to handle exceptions causes silent failures.
- Blocking inside async callbacks can defeat parallelism.

---

## Follow-up Questions & Answers

**Q:** Future vs CompletableFuture?

**A:** `Future` is basic and blocking on `get()`. `CompletableFuture` supports non-blocking callbacks and composition.

**Q:** Should I always use the common pool?

**A:** No. Use a dedicated executor for isolation and predictable performance.

---

## How to Use for Interviews

- Say "parallelize independent I/O with `CompletableFuture`".
- Contrast `Future` vs `CompletableFuture` in one sentence.
- Mention custom executor usage.

---

**Last Updated:** March 5, 2026
