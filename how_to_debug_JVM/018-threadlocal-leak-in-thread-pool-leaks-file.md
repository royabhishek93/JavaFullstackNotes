# #18 — ThreadLocal Leak in Thread Pool

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Explain how ThreadLocal causes a memory leak in a thread pool and how to fix it."

## 😊 Explain It Simply (for anyone)
Think of a `ThreadLocal` (a per-thread storage box — each worker thread gets its own private variable that no other thread can see) like a locker assigned to a hotel room. In a normal hotel, a guest checks out and the room is cleaned before the next guest arrives. But a thread pool (a fixed set of reusable "worker" threads that handle many requests one after another) is like a hotel that NEVER cleans the locker between guests — it just hands the same locker to the next guest. If guest #1 leaves something heavy in the locker and nobody removes it, guest #2, #3, #4... all inherit that clutter, and it never gets cleaned because the "room" (thread) is reused forever, not destroyed after each guest. That's why data stored per-request in a ThreadLocal must be explicitly removed before the thread goes back into the pool.

## 📊 Visualize It
```
 Thread Pool (threads live forever, reused per request)

  Thread-1's ThreadLocalMap:
    [ThreadLocalKey] -> UserSession(req#1)   <- never removed!
                        ^
                        after req#1 ends, req#2 reuses Thread-1
                        but UserSession(req#1) is STILL referenced

  Fix: call session.remove() in a "finally" block
  before the thread returns to the pool.
```

## 🏭 The Real Production Answer (15-YOE Level)

Buggy code:
```java
public class RequestContext {
    // LEAK: ThreadLocal in a pooled-thread environment
    private static final ThreadLocal<UserSession> session = new ThreadLocal<>();

    public static void set(UserSession s) { session.set(s); }
    public static UserSession get() { return session.get(); }
    // No remove() called after request ends
}
```

Why it leaks: Thread pool threads are reused. ThreadLocal values survive request boundaries. After request 1, the `UserSession` object sits in the thread's `ThreadLocalMap` forever (until that thread is reused and the value overwritten, or the thread dies — which in a pool may be never). Each entry in `ThreadLocalMap` is keyed by a `WeakReference` to the ThreadLocal itself, but the value is a strong reference. So even if the `ThreadLocal` field is GC'd, the value `UserSession` remains reachable.

Fix:
```java
// In a Servlet Filter or Spring HandlerInterceptor:
try {
    RequestContext.set(buildSession(request));
    chain.doFilter(request, response);
} finally {
    RequestContext.remove(); // CRITICAL: always remove in finally
}
```

In Spring: use `HandlerInterceptorAdapter.afterCompletion` to call `ThreadLocal.remove()`.

## 🔑 Key Takeaway
Every `ThreadLocal.set()` in a pooled-thread environment needs a matching `remove()` in a `finally` block, or the value outlives the request that created it.
