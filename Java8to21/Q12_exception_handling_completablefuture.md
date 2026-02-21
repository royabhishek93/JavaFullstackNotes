# Q12: How to handle exceptions in CompletableFuture?

**Study Time:** 3-5 minutes

---

## Problem

With async operations, exceptions happen on other threads. Standard try-catch won't work.

```java
// ❌ WRONG: try-catch doesn't catch async exceptions
try {
    CompletableFuture<User> future = userService.fetchUser(1);
    // Exception might happen later, on another thread!
    handleUser(future.get());  // Only catches here
} catch (Exception e) {
    // Too late if error happens in the future
}
```

## Exception Handling Methods

### Method 1: exceptionally() - Recover with Default

```java
CompletableFuture<User> future = userService.fetchUser(1);

CompletableFuture<User> withFallback = future.exceptionally(throwable -> {
    System.out.println("Error: " + throwable.getMessage());
    return new User(0, "Unknown User");  // Fallback value
});

User user = withFallback.get();  // Gets fallback if error
System.out.println(user.getName());  // "Unknown User" if failed
```

### Method 2: handle() - Handle Success OR Failure

```java
CompletableFuture<String> future = userService.fetchUser(1)
    .handle((user, exception) -> {
        if (exception != null) {
            System.out.println("Error: " + exception.getMessage());
            return "Could not fetch user";
        } else {
            return "User: " + user.getName();
        }
    });

String result = future.get();
System.out.println(result);
```

### Method 3: whenComplete() - React to Result or Error

```java
CompletableFuture<User> future = userService.fetchUser(1);

future.whenComplete((user, exception) -> {
    if (exception != null) {
        log.error("Failed to fetch user", exception);
        metrics.incrementFailureCount();
    } else {
        log.info("Fetched user: " + user.getName());
        cache.put(user.getId(), user);
    }
});

// Future still completes with original value or exception
User user = future.get();
```

## Propagating Errors Down the Chain

```java
fetchUser(1)
    .thenCompose(user -> {
        if (user.getStatus().equals("BLOCKED")) {
            // Create failed future - error propagates down
            return CompletableFuture.failedFuture(
                new IllegalStateException("User blocked")
            );
        }
        return fetchPayments(user.getId());
    })
    .exceptionally(e -> {
        // Catches both service errors AND our IllegalStateException
        System.out.println("Error: " + e.getMessage());
        return List.of();  // Empty list fallback
    })
    .get();
```

## Complete Example: Fetch with Retry and Fallback

```java
public CompletableFuture<User> fetchUserWithFallback(int userId) {
    return userService.fetchUser(userId)
        .exceptionally(e -> {
            log.warn("Primary service failed, trying backup", e);
            return userService.fetchUserFromBackup(userId).get();  // Blocks!
        })
        .exceptionally(e -> {
            log.error("Backup failed too, using default", e);
            return new User(userId, "Unknown");  // Final fallback
        });
}
```

## ❌ Wrong Ways to Handle Errors

### Wrong 1: Ignoring the exception

```java
// ❌ WRONG: Exception is swallowed, future completes with null
CompletableFuture<User> future = fetchUser(1)
    .exceptionally(e -> null);  // Dangerous!

User user = future.get();  // Might be null later
String name = user.getName();  // NullPointerException!
```

### Wrong 2: Blocking in exception handler

```java
// ❌ WRONG: Blocks thread in exception handler
future.exceptionally(e -> {
    // This runs on same executor thread!
    return userService.fetchUserFromBackup(userId).get();  // Blocks!
});
```

## ✅ Better: Using completeExceptionally

```java
public CompletableFuture<User> fetchWithTimeout(int userId, 
                                                 Duration timeout) {
    CompletableFuture<User> future = userService.fetchUser(userId);
    
    // Add timeout - complete with exception if timeout
    ScheduledExecutorService scheduler = 
        Executors.newScheduledThreadPool(1);
    
    scheduler.schedule(() -> {
        if (!future.isDone()) {
            future.completeExceptionally(
                new TimeoutException("Fetch took too long")
            );
        }
    }, timeout.toMillis(), TimeUnit.MILLISECONDS);
    
    return future;
}

// Usage
fetchWithTimeout(1, Duration.ofSeconds(5))
    .exceptionally(e -> new User(0, "Timed out"))
    .get();
```

## Real World: API Call with Fallback and Logging

```java
public CompletableFuture<User> getUserForDisplay(int userId) {
    return userService.fetchUser(userId)
        // Log success
        .whenComplete((user, exception) -> {
            if (exception == null) {
                metrics.recordSuccess("user.fetch");
            } else {
                metrics.recordFailure("user.fetch", exception);
            }
        })
        // Handle specific errors
        .handle((user, exception) -> {
            if (exception instanceof TimeoutException) {
                log.warn("User fetch timed out for id: " + userId);
                return cacheService.getCachedUser(userId)
                    .orElse(new User(userId, "Unknown"));
            } else if (exception instanceof HttpClientException) {
                log.error("Network error fetching user", exception);
                return new User(userId, "Network Error");
            } else if (exception != null) {
                log.error("Unexpected error", exception);
                return new User(userId, "Error");
            }
            return user;
        });
}

// Usage
User displayUser = getUserForDisplay(123).get();
// Returns cached user if timeout, fallback if error, real user if success
```

## Chaining with Error Recovery

```java
fetchUser(1)
    .thenCompose(user -> 
        // This might fail
        expensiveOperation(user.getId())
    )
    .exceptionally(e -> {
        // Try simpler alternative
        System.out.println("Expensive op failed: " + e.getMessage());
        // Create a successful future with default result
        return CompletableFuture.completedFuture(defaultResult).get();
    })
    .get();
```

## Summary of Methods

```java
// exceptionally - transform exception to value
future.exceptionally(ex -> defaultValue)

// handle - transform either result or exception  
future.handle((result, ex) -> ...)

// whenComplete - react to completion (doesn't transform)
future.whenComplete((result, ex) -> { ... })

// completeExceptionally - manually fail a future
future.completeExceptionally(new Exception());

// failedFuture - create already-failed future
CompletableFuture.failedFuture(new Exception())
```

## Interview Tip

"Exception handling in CompletableFuture happens via `exceptionally()` (recover with default), `handle()` (handle both success and failure), or `whenComplete()` (react but don't transform). Use `exceptionally()` for fallback values, `handle()` for conditional recovery. Errors propagate down the chain unless caught. Use `whenComplete()` for logging/metrics as it doesn't swallow exceptions. Be careful with `null` in exceptionally - consider checked exceptions properly."

## Quick Checklist

- ✅ `exceptionally()` returns CompletableFuture, safe fallback
- ✅ `handle()` for both success and error handling
- ✅ `whenComplete()` for logging/metrics (no transform)
- ✅ Errors propagate down chain by default
- ✅ `failedFuture()` to create error future
- ✅ `completeExceptionally()` to manually fail
- ✅ Avoid `null` returns from exceptionally
- ✅ Use `metrics`/`logging` in `whenComplete()`

---

**Java8to21 Complete!** You've covered all 12 Modern Java interview questions. Next: Study Spring Bean Scopes (SpringBoot folder)
