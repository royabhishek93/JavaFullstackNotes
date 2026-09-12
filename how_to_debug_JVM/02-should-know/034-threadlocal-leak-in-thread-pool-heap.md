# #34 — ThreadLocal Leak in a Thread Pool

> **Category:** Heap Dump Analysis | **Type:** Advanced Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Explain a ThreadLocal leak pattern and how to find it in a heap dump."

## 😊 Explain It Simply (for anyone)
Picture a shared fleet of taxis (thread pool threads) that never get retired — the same physical cars just keep getting reused for different passengers (requests) all day, every day, forever. Now imagine each car has a small glovebox (`ThreadLocal` storage) where the current passenger can stash something private for the ride.

If the driver forgets to CLEAR the glovebox before picking up the next passenger, whatever the previous passenger stashed (a big folder of documents, say) just sits there — and if every future passenger keeps adding stuff without clearing, the glovebox slowly fills with junk left behind by dozens of past passengers, weighing down that one taxi forever, because taxis (unlike passengers) are never replaced.

## 📊 Visualize It
```
Thread Pool (threads live forever, reused per request):

Thread-7:  [ThreadLocalMap]
  Request A sets UserContext(A) → glovebox: {A}
  Request A done, NO remove()   → glovebox: {A}  ← leaked!
  Request B sets UserContext(B) → glovebox: {B}  (A now overwritten, but B may leak too)
  Request B done, NO remove()   → glovebox: {B}  ← leaked!
   ... same thread reused thousands of times, memory pinned per active thread

MAT diagnosis:
  search: java.lang.ThreadLocal$ThreadLocalMap$Entry
  OQL: SELECT t FROM java.lang.Thread t WHERE t.threadLocals != null

Fix: try { set(...); ...work... } finally { threadLocal.remove(); }
```

## 🏭 The Real Production Answer (15-YOE Level)

ThreadLocal values are stored in a `ThreadLocalMap` attached to each `Thread` object. In a thread pool (like Tomcat's request threads), threads are reused — they are never garbage collected for the lifetime of the JVM.

If code sets a `ThreadLocal` but never calls `remove()`, the value remains in the thread's map indefinitely. If that value holds a large object graph (e.g., a user session, a Hibernate entity), it accumulates per thread.

```java
// Leak pattern
private static final ThreadLocal<UserContext> userContext = new ThreadLocal<>();

// Servlet filter sets context at request start
userContext.set(new UserContext(request)); // Set on thread pool thread

// BUG: never cleaned up — UserContext stays in thread's ThreadLocalMap forever
// when the same thread handles the next request, old UserContext remains until overwritten
```

```java
// Correct pattern — always remove in finally
public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain) {
    try {
        userContext.set(new UserContext((HttpServletRequest) req));
        chain.doFilter(req, res);
    } finally {
        userContext.remove(); // Critical — cleans up before thread returns to pool
    }
}
```

Heap dump diagnosis:
- MAT: search for `java.lang.ThreadLocal$ThreadLocalMap$Entry` instances
- Check the referent value — is it a large object?
- Follow to parent: `ThreadLocalMap` → `Thread` → thread pool
- OQL query: `SELECT t FROM java.lang.Thread t WHERE t.threadLocals != null`

## 🔑 Key Takeaway
In a reused thread pool, `ThreadLocal.remove()` in a `finally` block is mandatory — otherwise stale values pin memory to threads that never die.
