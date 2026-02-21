# Q11: How to chain CompletableFutures (thenCompose vs thenApply)?

**Study Time:** 3-5 minutes

---

## Problem

When you have multiple async operations that depend on each other, you need to chain them properly.

```java
User user = fetchUser(1);      // Async
Payments payments = fetchPayments(user.getId());  // Depends on user
sendNotification(user.getEmail());                // Depends on user
```

How do you express this with CompletableFutures?

## The Wrong Way: Blocking

```java
// ❌ WRONG: Blocks on each get()
CompletableFuture<User> userFuture = userService.fetchUser(1);
User user = userFuture.get();  // ← Blocks here!

CompletableFuture<Payment> paymentsFuture = 
    paymentService.fetchPayments(user.getId());
Payment payments = paymentsFuture.get();  // ← Blocks here!

System.out.println("Done!");
```

This defeats the purpose of async! You're waiting at each step.

## ✅ The Right Way: Chaining with thenCompose

```java
// ✅ RIGHT: No blocking, stays async
CompletableFuture<Payment> result = 
    userService.fetchUser(1)
        .thenCompose(user -> 
            paymentService.fetchPayments(user.getId())
        );

// Get result (optional blocking at the end)
Payment payments = result.get();
System.out.println("Done!");
```

## Key Difference: thenCompose vs thenApply

### ❌ WRONG: thenApply with Future-returning lambda

```java
// ❌ WRONG: thenApply returns CompletableFuture<CompletableFuture<Payment>>
CompletableFuture<CompletableFuture<Payment>> wrongChain = 
    userService.fetchUser(1)
        .thenApply(user -> 
            paymentService.fetchPayments(user.getId())  // Returns CompletableFuture!
        );

// Nasty nested futures!
Payment payment = wrongChain.get().get();  // ← Double get()!
```

### ✅ RIGHT: thenCompose flattens futures

```java
// ✅ RIGHT: thenCompose returns CompletableFuture<Payment>
CompletableFuture<Payment> rightChain = 
    userService.fetchUser(1)
        .thenCompose(user -> 
            paymentService.fetchPayments(user.getId())  // Returns CompletableFuture
        );

// Clean single get()
Payment payment = rightChain.get();  // ✅ Just one get()!
```

## Rule of Thumb

```java
// Use thenApply when lambda returns a PLAIN VALUE
future.thenApply(value -> processSync(value))  // returns String

// Use thenCompose when lambda returns a FUTURE/COMPLETABLEFUTURE
future.thenCompose(value -> fetchAsync(value))  // returns CompletableFuture<T>
```

## Real Example: Complete User Profile Fetch

```java
public CompletableFuture<UserProfile> getUserProfile(int userId) {
    return userService.fetchUser(userId)  // Returns CompletableFuture<User>
        .thenCompose(user ->              // user is the User object
            paymentService.fetchPayments(user.getId())  // Returns CompletableFuture<Payments>
        )
        .thenCompose(payments ->          // payments is the Payments object
            preferencesService.fetchPreferences(userId)  // Returns CompletableFuture<Preferences>
        )
        .thenApply(preferences -> {       // preferences is the Preferences object
            // Transform: combine all data into UserProfile
            return new UserProfile(
                user,      // Wait - we lost user! This is the problem
                payments,  // And payments!
                preferences
            );
        });
}
```

Wait - we lost the intermediate values! Let's fix this:

## ✅ Combining Multiple Futures

### Option 1: combineLatest (when you need all results)

```java
CompletableFuture<User> userFuture = userService.fetchUser(1);
CompletableFuture<Payments> paymentsFuture = userService.fetchPayments(1);
CompletableFuture<Preferences> prefFuture = prefsService.fetchPreferences(1);

// Wait for all
CompletableFuture<UserProfile> result = 
    userFuture.thenCombine(paymentsFuture, (user, payments) ->
        new UserProfile(user, payments)
    )
    .thenCombine(prefFuture, (profile, prefs) ->
        profile.withPreferences(prefs)
    );
```

### Option 2: allOf (when sequential, using method parameters)

```java
public CompletableFuture<UserProfile> getUserProfile(int userId) {
    CompletableFuture<User> userFuture = userService.fetchUser(userId);
    
    return userFuture.thenCompose(user ->
        paymentService.fetchPayments(user.getId())
            .thenApply(payments -> new Pair(user, payments))
    )
    .thenCompose(pair ->
        prefsService.fetchPreferences(userId)
            .thenApply(prefs ->
                new UserProfile(pair.user, pair.payments, prefs)
            )
    );
}

static class Pair {
    User user;
    Payments payments;
    Pair(User u, Payments p) { user = u; payments = p; }
}
```

### Option 3: Handle with Lambda (Cleanest)

```java
public CompletableFuture<UserProfile> getUserProfile(int userId) {
    return userService.fetchUser(userId)
        .thenCompose(user ->
            paymentService.fetchPayments(user.getId())
                .thenCompose(payments ->
                    prefsService.fetchPreferences(userId)
                        .thenApply(prefs ->
                            new UserProfile(user, payments, prefs)
                        )
                )
        );
}
```

## Chaining Multiple Independent Futures

```java
// Run in parallel, wait for all
CompletableFuture<Void> allDone = CompletableFuture.allOf(
    future1, future2, future3
);

// Then get results
allDone.thenRun(() -> {
    // All three are done here
    int result1 = future1.join();  // join() = get() but unchecked
    int result2 = future2.join();
    int result3 = future3.join();
    System.out.println(result1 + result2 + result3);
});

// Or blocking
CompletableFuture.allOf(future1, future2, future3).get();
```

## Common Chaining Patterns

```java
// Pattern 1: Chain with transformation (data flow)
fetchUser(1)
    .thenApply(user -> new UserDTO(user))           // Transform
    .thenAccept(dto -> sendResponse(dto));           // Consume

// Pattern 2: Chain with async (fetch then fetch)
fetchUser(1)
    .thenCompose(user -> fetchPayments(user.getId()))  // Chain async
    .thenAccept(payments -> saveToCache(payments));

// Pattern 3: Process all, combine results
CompletableFuture.allOf(fetch1, fetch2, fetch3)
    .thenRun(() -> System.out.println("All done!"));

// Pattern 4: Or completion (first one wins)
CompletableFuture.anyOf(fetch1, fetch2, fetch3)
    .thenAccept(first -> System.out.println("First: " + first));
```

## Interview Tip

"Use `thenCompose()` when chaining async operations (lambda returns CompletableFuture). Use `thenApply()` for sync transformations (lambda returns plain value). `thenCompose()` flattens nested CompletableFutures. Use `thenCombine()` to merge results from two futures, `allOf()` to wait for multiple, and `anyOf()` for first-to-complete. The key difference: `thenApply` would give you `CompletableFuture<CompletableFuture<T>>` (nested), while `thenCompose` flattens it to `CompletableFuture<T>`."

## Quick Checklist

- ✅ `thenCompose()` for async chains (returns CompletableFuture)
- ✅ `thenApply()` for sync transforms (returns value)
- ✅ `thenCombine()` to join two futures
- ✅ `allOf()` to wait for many futures
- ✅ `anyOf()` for first-to-complete race
- ✅ `join()` = `get()` but unchecked exceptions
- ✅ Lambdas capture variables from outer scope

---

**Next:** Study Q12 on exception handling in async operations
