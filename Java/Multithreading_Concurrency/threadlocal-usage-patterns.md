# ThreadLocal: Thread-Scoped Storage

**Study Time:** 8-10 minutes | **Frequency:** 65% in interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Problem Scenario

How do you store data that's specific to each thread without passing parameters around?

```java
class RequestContext {
    private static String userId;  // ❌ WRONG - Shared across threads!

    public void setUserId(String id) {
        this.userId = id;
    }

    public String getUserId() {
        return userId;
    }
}

// In multi-threaded context:
public class ThreadProblem {
    public static void main(String[] args) {
        RequestContext context = new RequestContext();

        new Thread(() -> {
            context.setUserId("user1");
            System.out.println("T1: " + context.getUserId());  // user1
        }).start();

        new Thread(() -> {
            Thread.sleep(100);
            context.setUserId("user2");
            System.out.println("T2: " + context.getUserId());  // user2
            System.out.println("T1 now sees: " + context.getUserId());  // user2 (WRONG!)
        }).start();
    }
}
```

**Problem:** Both threads share the same `userId`. Thread-1's data is overwritten by Thread-2!

---

## 🧠 Key Principle: ThreadLocal Storage

**ThreadLocal:** Each thread gets its own **isolated copy** of the variable.

```
Without ThreadLocal:
  Thread-1: userId ─┐
                   ├→ [shared memory] ← conflict!
  Thread-2: userId ─┘

With ThreadLocal:
  Thread-1: userId → [T1's memory]
  Thread-2: userId → [T2's memory]  (isolated!)
```

---

## ✅ Solution: Using ThreadLocal

```java
class RequestContext {
    private static final ThreadLocal<String> userIdHolder = new ThreadLocal<>();

    public void setUserId(String id) {
        userIdHolder.set(id);  // Set for this thread only
    }

    public String getUserId() {
        return userIdHolder.get();  // Get for this thread only
    }

    public void clear() {
        userIdHolder.remove();  // Clean up
    }
}

// Usage
public class ThreadSafe {
    public static void main(String[] args) throws InterruptedException {
        RequestContext context = new RequestContext();

        Thread t1 = new Thread(() -> {
            context.setUserId("user1");
            System.out.println("T1: " + context.getUserId());  // user1
            try { Thread.sleep(500); } catch (InterruptedException e) {}
            System.out.println("T1 still sees: " + context.getUserId());  // user1
        });

        Thread t2 = new Thread(() -> {
            try { Thread.sleep(100); } catch (InterruptedException e) {}
            context.setUserId("user2");
            System.out.println("T2: " + context.getUserId());  // user2
            System.out.println("T1 still sees: " + context.getUserId());  // user2
        });

        t1.start();
        t2.start();
        t1.join();
        t2.join();
    }
}
```

**Output:**
```
T1: user1
T2: user2
T1 still sees: user1
T2 still sees: user2
```

---

## ✅ Scenario 2: ThreadLocal in RequestFilter

```java
// Web context (Spring example)
class RequestContextHolder {
    private static final ThreadLocal<String> userIdThreadLocal = new ThreadLocal<>();
    private static final ThreadLocal<Long> requestIdThreadLocal = new ThreadLocal<>();

    public static void setUserId(String userId) {
        userIdThreadLocal.set(userId);
    }

    public static String getUserId() {
        return userIdThreadLocal.get();
    }

    public static void setRequestId(Long requestId) {
        requestIdThreadLocal.set(requestId);
    }

    public static Long getRequestId() {
        return requestIdThreadLocal.get();
    }

    public static void clear() {
        userIdThreadLocal.remove();
        requestIdThreadLocal.remove();
    }
}

// In request filter
class RequestFilter {
    public void doFilter(Request request) {
        try {
            String userId = extractUserFromToken(request);
            long requestId = generateRequestId();

            RequestContextHolder.setUserId(userId);
            RequestContextHolder.setRequestId(requestId);

            processRequest(request);
        } finally {
            RequestContextHolder.clear();  // IMPORTANT!
        }
    }

    private void processRequest(Request request) {
        // Can access context from anywhere without passing as parameter
        String userId = RequestContextHolder.getUserId();
        Long requestId = RequestContextHolder.getRequestId();
        System.out.println("Processing request " + requestId + " for user " + userId);
    }
}
```

---

## ✅ Scenario 3: ThreadLocal.withInitial()

Default value for each thread:

```java
class Counter {
    private static final ThreadLocal<Integer> countThreadLocal = 
        ThreadLocal.withInitial(() -> 0);

    public void increment() {
        Integer count = countThreadLocal.get();  // 0 if first call
        countThreadLocal.set(count + 1);
    }

    public int getCount() {
        return countThreadLocal.get();
    }

    public void reset() {
        countThreadLocal.remove();
    }
}

// Usage
public class ThreadLocalInit {
    public static void main(String[] args) {
        Counter counter = new Counter();

        new Thread(() -> {
            counter.increment();
            counter.increment();
            System.out.println("T1 count: " + counter.getCount());  // 2
        }).start();

        new Thread(() -> {
            counter.increment();
            System.out.println("T2 count: " + counter.getCount());  // 1
        }).start();
    }
}
```

---

## ❌ Common Mistakes

### ❌ Mistake 1: Forgetting to Remove ThreadLocal

```java
// WRONG
class RequestProcessor {
    private static ThreadLocal<Connection> connHolder = new ThreadLocal<>();

    public void process(Request request) {
        Connection conn = getConnection();
        connHolder.set(conn);
        // ... process ...
        // Forgot to remove! Memory leak!
    }
}

// CORRECT - Always use try-finally
class RequestProcessor {
    private static ThreadLocal<Connection> connHolder = new ThreadLocal<>();

    public void process(Request request) {
        Connection conn = getConnection();
        connHolder.set(conn);
        try {
            // ... process ...
        } finally {
            connHolder.remove();  // Always remove!
        }
    }
}
```

**Why?** ThreadLocal values aren't cleaned up automatically. In thread pools, threads are reused, and leftover values cause data leaks.

---

### ❌ Mistake 2: Calling get() Without Initialization

```java
// WRONG - May return null
ThreadLocal<String> holder = new ThreadLocal<>();
String value = holder.get();  // null if never set
System.out.println(value.length());  // NullPointerException!

// CORRECT
ThreadLocal<String> holder = ThreadLocal.withInitial(() -> "default");
String value = holder.get();  // "default"
System.out.println(value.length());  // 7
```

---

### ❌ Mistake 3: Using ThreadLocal with Shared Object

```java
// WRONG - Object is still shared
ThreadLocal<List<String>> listHolder = new ThreadLocal<>();
List<String> sharedList = new ArrayList<>();

new Thread(() -> {
    listHolder.set(sharedList);
    sharedList.add("T1");  // Modifies shared list
}).start();

new Thread(() -> {
    listHolder.set(sharedList);
    sharedList.add("T2");  // Modifies same list!
    System.out.println(sharedList);  // [T1, T2]
}).start();

// CORRECT - Each thread gets its own list
ThreadLocal<List<String>> listHolder = ThreadLocal.withInitial(() -> new ArrayList<>());

new Thread(() -> {
    listHolder.get().add("T1");  // Own list
}).start();

new Thread(() -> {
    listHolder.get().add("T2");  // Own list (different from T1)
}).start();
```

---

### ❌ Mistake 4: ThreadLocal in Thread Pools

```java
// WRONG in thread pool
ExecutorService executor = Executors.newFixedThreadPool(2);

ThreadLocal<String> userIdHolder = new ThreadLocal<>();

executor.submit(() -> {
    userIdHolder.set("user1");
    doWork();
    // Forgot to remove!
});

executor.submit(() -> {
    String userId = userIdHolder.get();  // Gets "user1" from previous task!
    // WRONG DATA!
});

// CORRECT
executor.submit(() -> {
    try {
        userIdHolder.set("user1");
        doWork();
    } finally {
        userIdHolder.remove();  // Always cleanup
    }
});
```

---

## 🎯 Interview Q&A

### Q1: "What is ThreadLocal and why use it?"

**Answer (30 seconds):**
```
ThreadLocal stores thread-scoped data.
Each thread gets its own isolated copy.

Why:
- Avoid passing parameters through call stack
- Thread-safe without synchronization
- Each thread's data isolated

Example:
ThreadLocal<String> userHolder = new ThreadLocal<>();
T1.set("user1") → T1 sees "user1"
T2.set("user2") → T2 sees "user2"
(No conflict!)
```

---

### Q2: "ThreadLocal vs synchronized?"

**Answer:**
```
ThreadLocal:
✅ No synchronization needed
✅ Each thread has own copy
✅ Better performance
❌ Memory overhead per thread

synchronized:
✅ Single copy
❌ Requires synchronization
❌ Contention under load
✅ Less memory

Use ThreadLocal when:
- Many concurrent threads
- No coordination needed between threads
- Per-thread state (user context, connection, etc.)

Use synchronized when:
- Shared resource needs locking
- Threads need to coordinate
- Limited number of threads
```

---

### Q3: "Memory leak with ThreadLocal?"

**Answer:**
```
YES - If not removed properly!

Scenario:
1. Thread pool reuses threads
2. Set ThreadLocal value
3. Forget to remove()
4. Next task on same thread sees old value
5. If many tasks, values accumulate → memory leak

Solution:
try {
    threadLocal.set(value);
    doWork();
} finally {
    threadLocal.remove();  // Always!
}

Or use try-with-resources (Java 7+) with custom cleanup.
```

---

### Q4: "InheritableThreadLocal?"

**Answer:**
```
ThreadLocal: Child threads DON'T see parent's values

Thread parent = Thread.currentThread();
ThreadLocal<String> holder = new ThreadLocal<>();
holder.set("parent-value");

new Thread(() -> {
    System.out.println(holder.get());  // null
}).start();

InheritableThreadLocal: Child threads DO see parent's values

ThreadLocal<String> holder = new InheritableThreadLocal<>();
holder.set("parent-value");

new Thread(() -> {
    System.out.println(holder.get());  // parent-value
}).start();

Use when:
- Parent-child thread inheritance needed
- Context needs to be passed to spawned threads
- Logging/tracing contexts
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Thread isolation purpose | Design understanding | ⭐⭐⭐⭐⭐ |
| Memory leak prevention | Production safety | ⭐⭐⭐⭐⭐ |
| Proper remove() usage | Critical coding practice | ⭐⭐⭐⭐ |
| vs synchronized trade-offs | Performance awareness | ⭐⭐⭐⭐ |
| Real-world examples (filters) | Practical knowledge | ⭐⭐⭐⭐ |

---

## ✅ Best Practices

```java
// 1. Always remove in finally (or try-catch-finally)
try {
    threadLocal.set(value);
    // ...
} finally {
    threadLocal.remove();
}

// 2. Use withInitial() to provide defaults
ThreadLocal<SimpleDateFormat> dateFormat = 
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));

// 3. Make it final and static
private static final ThreadLocal<String> contextHolder = new ThreadLocal<>();

// 4. Document thread-safety carefully
/*
 * ThreadLocal storage for current user context.
 * IMPORTANT: Must call clear() after use to prevent memory leaks.
 */

// 5. In web frameworks, use built-in context holders
// Spring: SecurityContextHolder, RequestContextHolder (handle cleanup)
```

---

**Priority:** ✅ SHOULD KNOW (65% interview frequency)

**Related Topics:**
- [Deadlock Prevention](#)
- [Thread Pool Patterns](#)
- [Request Context Propagation](#)

---

**Last Updated:** March 5, 2026
