# Scoped Values (Java 25 — GA)

**Interview Priority:** Senior: 🔥 MUST KNOW | Mid: 👍 GOOD TO KNOW

---

## Scenario

**Given this ThreadLocal usage with virtual threads, what goes wrong?**

```java
static ThreadLocal<User> currentUser = new ThreadLocal<>();

void handleRequest(User user) {
    currentUser.set(user);
    processRequest(); // may spawn child virtual threads
    currentUser.remove(); // must manually clean up
}
```

**Problems:**
1. With millions of virtual threads, each `ThreadLocal` copy uses memory — heap explosion.
2. Child threads do NOT inherit the value (or do via `InheritableThreadLocal`, which copies it — still memory-heavy).
3. The value is mutable — any code can overwrite it accidentally.
4. Developers often forget `remove()`, causing leaks in thread pools.

---

## Key Principle

**`ScopedValue` is an immutable, per-scope binding that is automatically available to child threads within a bounded dynamic scope — no mutation, no cleanup, no inheritance copy.**

---

## Why It Happens (Simple English)

`ThreadLocal` was designed for platform threads. With virtual threads you can have millions of them, and each holding a copy of a `ThreadLocal` value multiplies memory usage by millions. `ScopedValue` binds a value for the duration of a scope (a lambda), makes it visible to all code called within that scope (including child virtual threads), and the value vanishes automatically when the scope exits.

---

## Basic Usage

```java
import java.lang.ScopedValue;

public class RequestHandler {

    static final ScopedValue<User> CURRENT_USER = ScopedValue.newInstance();

    void handleRequest(User user) throws Exception {
        ScopedValue.where(CURRENT_USER, user)
                   .run(() -> processRequest()); // value available inside
        // value is gone here — no cleanup needed
    }

    void processRequest() {
        User user = CURRENT_USER.get(); // safe to call anywhere in scope
        System.out.println("Processing for: " + user.name());
    }
}
```

---

## Returning a Value from the Scope

```java
String result = ScopedValue.where(CURRENT_USER, user)
                            .call(() -> computeResponse()); // call() returns a value
```

---

## Multiple Bindings

```java
ScopedValue.where(CURRENT_USER, user)
           .where(REQUEST_ID, requestId)
           .run(() -> handleRequest());
```

---

## Rebinding (Nested Scopes)

A child scope can shadow a parent's binding — the outer value is restored when the inner scope exits.

```java
ScopedValue.where(CURRENT_USER, adminUser)
           .run(() -> {
               CURRENT_USER.get(); // adminUser

               ScopedValue.where(CURRENT_USER, guestUser)
                          .run(() -> {
                              CURRENT_USER.get(); // guestUser (shadowed)
                          });

               CURRENT_USER.get(); // adminUser (restored)
           });
```

---

## With Structured Concurrency

`ScopedValue` propagates to child tasks forked inside a `StructuredTaskScope` — this is the primary use case.

```java
static final ScopedValue<String> TRACE_ID = ScopedValue.newInstance();

ScopedValue.where(TRACE_ID, "req-123").run(() -> {
    try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
        scope.fork(() -> {
            // TRACE_ID.get() == "req-123" — inherited by child virtual thread
            return callServiceA();
        });
        scope.fork(() -> {
            // TRACE_ID.get() == "req-123" — same
            return callServiceB();
        });
        scope.join().throwIfFailed();
    }
});
```

---

## ScopedValue vs ThreadLocal

| Feature | `ThreadLocal` | `ScopedValue` |
|---|---|---|
| Mutable | Yes | No (immutable per scope) |
| Memory per virtual thread | Full copy | Shared — no copy |
| Cleanup | Manual `remove()` | Automatic on scope exit |
| Child thread inheritance | InheritableThreadLocal only | Automatic in structured scope |
| Java version | Java 1 | **Java 25 (GA)** |
| Use case | Per-thread mutable state | Immutable per-request context |

---

## When to Keep ThreadLocal

- When you genuinely need mutable per-thread state (e.g., connection per thread in a pool).
- Framework code that pre-dates virtual threads and cannot be refactored.

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| `ThreadLocal` for request context in virtual threads | `ScopedValue` — no per-thread copy |
| Forgetting `ThreadLocal.remove()` | `ScopedValue` — auto-cleaned on scope exit |
| Mutable shared context via `ThreadLocal` | Immutable `ScopedValue` binding |

---

## Interview Tip (Exact Answer)

"`ScopedValue` replaces `ThreadLocal` for read-only per-request context in virtual thread applications. It binds a value for the duration of a lambda scope, requires no cleanup, uses no per-thread memory copies, and automatically propagates to child virtual threads in structured concurrency scopes."

---

## Quick Checklist

- Declare `ScopedValue` as `static final` (like constants).
- Use `ScopedValue.where(...).run(...)` to bind — value is available inside the lambda.
- Use `.call(...)` when the scope must return a value.
- `CURRENT_USER.get()` works anywhere inside the scope, including in child threads.
- Value is immutable — no `set()` method exists.

---

## Critical Pitfalls

- Calling `ScopedValue.get()` outside of any binding scope throws `NoSuchElementException` — use `isBound()` to guard.
- `ScopedValue` is NOT a replacement for all `ThreadLocal` uses — mutable per-thread state still needs `ThreadLocal`.
- Do not store `ScopedValue` bindings — the value is only valid within the `run()`/`call()` closure.

---

## Follow-up Questions & Answers

**Q:** Why does `ThreadLocal` cause memory problems with virtual threads?

**A:** Each virtual thread gets its own copy of every `ThreadLocal` value. With millions of virtual threads, this multiplies heap usage by millions. `ScopedValue` avoids copying — it stores one value and makes it accessible to all threads within the scope.

**Q:** Can you modify a `ScopedValue` binding?

**A:** No. `ScopedValue` is intentionally immutable. You can shadow it with a new binding in a nested scope, but the outer scope's value is always restored.

---

## How to Use for Interviews

- Lead with the `ThreadLocal` memory problem in virtual thread environments.
- Contrast: `ThreadLocal` = mutable per-thread copy; `ScopedValue` = immutable shared binding within a scope.
- Show the `where(...).run(...)` pattern and how it propagates to child tasks.
- Mention it pairs with `StructuredTaskScope` for trace IDs / request context.

---

**Last Updated:** August 18, 2026
