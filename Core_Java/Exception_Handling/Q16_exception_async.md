# 🎯 Q16: Exception Handling in Async/Multithreaded Code?

> **Interview Frequency:** 65% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Understanding how exceptions propagate in async code, CompletableFuture, and threads.

### Code Scenario
```java
// Where do exceptions go in async code?
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    if (someCondition) {
        throw new RuntimeException("Async error!");
    }
    return "success";
});

// Exception doesn't propagate to caller!
// Must be handled explicitly:
future.get();  // Throws ExecutionException wrapping the exception
```

---

## 📌 Why It Happens

In async code:
1. **No call stack** - exception can't propagate to caller
2. **Different thread** - exception occurs in executor thread
3. **Async nature** - caller continues before exception happens
4. **Must handle explicitly** - use callbacks or `.get()`

---

## ❌ Wrong (Ignoring Async Exceptions)

```java
// WRONG: Exception silently swallowed
ExecutorService executor = Executors.newSingleThreadExecutor();
executor.submit(() -> {
    throw new RuntimeException("Error!");  // Where does it go?
    // Caller never sees it!
});

// WRONG: Only catching at .get()
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    // ...
});
// If caller forgets .get(), exception is NEVER caught!
future.thenApply(result -> process(result));  // Exception lost!

// WRONG: Not handling CompletableFuture exception
CompletableFuture.supplyAsync(() -> database.query())
    .thenApply(data -> data.transform())
    .thenAccept(System.out::println);
    // Exception in any step silently ignored!
```

---

## ✅ Right (Explicit Exception Handling)

```java
// RIGHT: Use .whenComplete() or .exceptionally()
CompletableFuture.supplyAsync(() -> {
    return database.query();
})
.exceptionally(throwable -> {
    logger.error("Database query failed", throwable);
    return "default-value";  // Fallback value
})
.thenApply(data -> data.transform())
.thenAccept(System.out::println);

// RIGHT: Use .handle() for both success and failure
CompletableFuture.supplyAsync(() -> database.query())
.handle((data, throwable) -> {
    if (throwable != null) {
        logger.error("Query failed", throwable);
        return "default-value";
    }
    return data.transform();
})
.thenAccept(System.out::println);

// RIGHT: Use .whenComplete() for side effects
CompletableFuture.supplyAsync(() -> database.query())
.whenComplete((data, throwable) -> {
    if (throwable != null) {
        logger.error("Query failed", throwable);
        alertOps();  // Side effect
    }
    // Continue processing regardless
})
.thenApply(data -> data != null ? data.transform() : null);

// RIGHT: Composite async with exception handling
CompletableFuture<String> async1 = CompletableFuture.supplyAsync(() -> service1());
CompletableFuture<String> async2 = CompletableFuture.supplyAsync(() -> service2());

CompletableFuture.allOf(async1, async2)
    .exceptionally(throwable -> {
        logger.error("Any service failed", throwable);
        return null;
    })
    .join();  // Wait for completion
```

---

## 💬 Interview Tip (Say This Exactly)

"Async exceptions don't propagate - they're trapped in the CompletableFuture. Use `.exceptionally()` for recovery, `.handle()` for both cases, or `.whenComplete()` for side effects. Always handle exceptions explicitly in async chains."

---

## ☑️ Quick Checklist

- ✅ Regular try-catch doesn't work for async (different thread)
- ✅ Use `.exceptionally()` to catch and recover with fallback value
- ✅ Use `.handle()` to handle both success and exception
- ✅ Use `.whenComplete()` for side effects (logging, cleanup)
- ✅ Use `.thenApply()` only when no exception expected
- ✅ Chain `.exceptionally()` at END for final fallback
- ✅ Use `.join()` to wait and get exceptions
- ✅ Use `.get()` with timeout to prevent hanging
- ✅ ExecutorService requires explicit submit() handling

---

## 📚 Real Flipkart Scenario

```java
// Order processing with multiple async operations

public OrderConfirmation processOrder(Order order) {
    CompletableFuture<InventoryCheck> checkInventory = 
        CompletableFuture.supplyAsync(() -> 
            inventoryService.check(order)
        )
        .exceptionally(ex -> {
            logger.warn("Inventory check failed, assuming available", ex);
            return new InventoryCheck(true);  // Fallback: assume available
        });

    CompletableFuture<PaymentResult> processPayment =
        CompletableFuture.supplyAsync(() ->
            paymentService.charge(order)
        )
        .exceptionally(ex -> {
            logger.error("Payment failed, needs manual review", ex);
            alertPaymentTeam(order.getId(), ex);
            throw new PaymentException("Cannot charge", ex);  // Don't continue
        });

    // Wait for both with exception handling
    CompletableFuture<OrderConfirmation> confirmation =
        CompletableFuture.allOf(checkInventory, processPayment)
            .thenApply(v -> {
                InventoryCheck inv = checkInventory.join();
                PaymentResult payment = processPayment.join();
                
                if (inv.available && payment.successful) {
                    return new OrderConfirmation(order.getId(), "CONFIRMED");
                } else {
                    return new OrderConfirmation(order.getId(), "FAILED");
                }
            })
            .whenComplete((result, throwable) -> {
                if (throwable != null) {
                    logger.error("Order processing failed", throwable);
                    sendFailureNotification(order.getId());
                } else if (result != null) {
                    logger.info("Order confirmed: " + result.orderId);
                    sendConfirmationEmail(order.getId());
                }
            })
            .handle((result, throwable) -> {
                // Final fallback if everything fails
                if (throwable != null) {
                    logger.error("CRITICAL: Order failed at all levels", throwable);
                    return new OrderConfirmation(order.getId(), "ERROR_UNKNOWN");
                }
                return result;
            });

    return confirmation.join();  // Block and get result with exceptions
}
```

---

## ➡️ Bonus Follow-ups

1. **"What's difference between .exceptionally() and .handle()?"** → `.exceptionally()` only on exception, `.handle()` always
2. **"Why use .whenComplete() vs .handle()?"** → `.whenComplete()` for side effects only, `.handle()` when you transform result
3. **"What happens if exception in chained .then...()?"** → Propagates to next `.exceptionally()` or `.handle()`

---

## 🔗 Related Questions

- **Q12:** Parallel Streams (similar async exception handling issues)
- **Q49:** Testing async code (test exception scenarios)
- **Q56:** Spring Security (async authentication)

---

**Last Updated:** February 22, 2026  
**Previous: [Q15_try_with_resources.md](Q15_try_with_resources.md) | Next: [../../System_Design/Q17_database_scaling.md](../../System_Design/Q17_database_scaling.md)**
