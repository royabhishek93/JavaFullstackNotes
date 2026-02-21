# Q10: What is CompletableFuture (Java 8)?

**Study Time:** 3-5 minutes

---

## Problem

Before CompletableFuture, async code was messy with nested callbacks.

```java
// ❌ Callback Hell
userService.fetchUser(id, new Callback<User>() {
    @Override
    public void onSuccess(User user) {
        paymentService.fetchPayments(user.getId(), new Callback<List<Payment>>() {
            @Override
            public void onSuccess(List<Payment> payments) {
                notificationService.sendEmail(user.getEmail(), payments, 
                    new Callback<Void>() {
                        @Override
                        public void onSuccess(Void result) {
                            System.out.println("Email sent!");
                        }
                        @Override
                        public void onFailure(Exception e) {
                            System.out.println("Email failed!");
                        }
                    });
            }
            @Override
            public void onFailure(Exception e) { }
        });
    }
    @Override
    public void onFailure(Exception e) { }
});
```

This is hard to read and error-prone.

## ✅ CompletableFuture: Promise-Based Async

CompletableFuture is a **Promise** - a container that holds a value which becomes available in the future.

```java
// Simple async operation
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    // Runs asynchronously on ForkJoinPool
    return "Result from thread: " + Thread.currentThread().getName();
});

// Get result (blocking - wait for it)
String result = future.get();
System.out.println(result);
```

## Creating CompletableFutures

### Method 1: supplyAsync() - With Return Value

```java
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> {
    // Does work, returns a value
    return "Hello from async";
});

// Get the result
String result = future.get();  // Blocks until complete
System.out.println(result);    // Hello from async
```

### Method 2: runAsync() - No Return Value

```java
CompletableFuture<Void> future = CompletableFuture.runAsync(() -> {
    // Does work, no return value
    System.out.println("Running on thread: " + 
        Thread.currentThread().getName());
});

future.get();  // Wait for it to finish
System.out.println("Done!");
```

### Method 3: New CompletableFuture + Manual Completion

```java
CompletableFuture<String> future = new CompletableFuture<>();

new Thread(() -> {
    try {
        Thread.sleep(1000);  // Simulate work
        future.complete("Work finished!");  // Complete with value
    } catch (Exception e) {
        future.completeExceptionally(e);  // Complete with error
    }
}).start();

System.out.println(future.get());  // Waits 1 second, then: Work finished!
```

## Real Example: Fetch User + Payments

```java
// Simulate HTTP calls
public class UserService {
    public CompletableFuture<User> fetchUser(int id) {
        return CompletableFuture.supplyAsync(() -> {
            // Simulate API call
            return new User(id, "John Doe");
        });
    }
}

public class PaymentService {
    public CompletableFuture<List<Payment>> fetchPayments(int userId) {
        return CompletableFuture.supplyAsync(() -> {
            // Simulate API call
            return List.of(
                new Payment(100),
                new Payment(200)
            );
        });
    }
}

// Usage: Chain them together (Q11 will show this)
CompletableFuture<User> userFuture = userService.fetchUser(1);
CompletableFuture<List<Payment>> paymentsFuture = userFuture
    .thenCompose(user -> paymentService.fetchPayments(user.getId()));
// (This chains them - Q11 explains thenCompose)

List<Payment> payments = paymentsFuture.get();
```

## Key Concepts

### CompletableFuture State

```java
CompletableFuture<String> future = CompletableFuture.supplyAsync(() -> 
    "Hello"
);

// Query state
boolean isDone = future.isDone();                // true when complete
boolean isCompletedExceptionally = 
    future.isCompletedExceptionally();           // true if error

// Get result or default
String result = future.getNow("default");       // Returns value if done, else "default"

// Get result with timeout
String result = future.get(5, TimeUnit.SECONDS);  // Wait max 5 seconds
```

### Default Executor vs Custom

```java
// Uses ForkJoinPool.commonPool() by default
CompletableFuture<String> future1 = 
    CompletableFuture.supplyAsync(() -> "work");

// Use custom executor
ExecutorService executor = Executors.newFixedThreadPool(4);
CompletableFuture<String> future2 = 
    CompletableFuture.supplyAsync(() -> "work", executor);
```

## Blocking vs Non-Blocking

```java
// ❌ Blocking: Stops execution until result available
String result = future.get();  // Waits here!
System.out.println("Got: " + result);

// ✅ Non-blocking: Continues execution
future.thenAccept(result -> {
    System.out.println("Got: " + result);  // Runs when ready
});
System.out.println("Still running!");  // Runs immediately

// ✅ Non-blocking: With callback
future.whenComplete((result, exception) -> {
    if (exception != null) {
        System.out.println("Error: " + exception);
    } else {
        System.out.println("Got: " + result);
    }
});
```

## Common Patterns

```java
// Pattern 1: Do work, ignore result
CompletableFuture.runAsync(() -> sendNotification());

// Pattern 2: Do work, use result
CompletableFuture.supplyAsync(() -> fetchUser(1))
    .thenAccept(user -> System.out.println(user));

// Pattern 3: Chain operations (Q11 details this)
CompletableFuture.supplyAsync(() -> fetchUser(1))
    .thenCompose(user -> fetchPayments(user.getId()))
    .get();

// Pattern 4: Transform result
CompletableFuture.supplyAsync(() -> 100)
    .thenApply(amount -> amount * 2)      // 200
    .thenAccept(doubled -> System.out.println(doubled));
```

## Interview Tip

"CompletableFuture is a Promise-like container for async results. Use `supplyAsync()` for operations that return values, `runAsync()` for operations with no return. Get results with `.get()` (blocking) or use `.thenAccept()` (non-blocking callbacks). Key methods: `thenApply()` (transform), `thenCompose()` (chain futures), `thenAccept()` (consume result), `whenComplete()` (handle completion). Executor can be specified - defaults to ForkJoinPool."

## Quick Checklist

- ✅ `CompletableFuture<T>` is a Promise for async result
- ✅ `supplyAsync()` for returning operations
- ✅ `runAsync()` for void operations  
- ✅ `.get()` blocks until result available
- ✅ `.thenAccept()` for non-blocking callbacks
- ✅ `.thenApply()` to transform result
- ✅ Custom Executor can be specified
- ✅ `.complete()` and `.completeExceptionally()` for manual completion

---

**Next:** Study Q11 on chaining async operations with thenCompose and thenApply
