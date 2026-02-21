# Q4: What's the difference between singleton and ThreadLocal?

**Study Time:** 3-4 minutes

---

## Problem

Both "singleton" and ThreadLocal create one instance, but in very different ways.

```java
// One instance per JVM (Singleton)
@Component
public class Service { }

// One instance per thread (ThreadLocal)
private static ThreadLocal<User> threadLocalUser = ThreadLocal.withInitial(() -> null);
```

They're often confused because both avoid creating multiple instances.

## Singleton: One Instance Per JVM

```java
@Component
public class UserService {
    // ONE instance shared across ALL threads
}

@RestController
public class Controller {
    @Autowired private UserService service;  // ALL requests get same instance
}

// Memory:
// JVM Memory
//   └─ UserService instance (shared by all threads)
//        ├─ Thread 1 uses it
//        ├─ Thread 2 uses it
//        └─ Thread 3 uses it
```

### Singleton State: Shared Across Threads

```java
@Component
public class Counter {
    private int count = 0;  // ⚠️ Shared!
    
    public void increment() {
        count++;  // All threads see same count
    }
    
    public int getCount() {
        return count;
    }
}

// If 3 threads call increment():
// Thread 1 reads count: 0, increments to 1
// Thread 2 reads count: 0 (race condition!), increments to 1
// Thread 3 reads count: 1, increments to 2
// Final count: 2 (wrong! Should be 3)
```

## ThreadLocal: One Instance Per Thread

```java
public class UserContext {
    // One instance per thread - completely isolated
    private static ThreadLocal<String> userIdLocal = 
        ThreadLocal.withInitial(() -> "anonymous");
    
    public static void setUserId(String userId) {
        userIdLocal.set(userId);
    }
    
    public static String getUserId() {
        return userIdLocal.get();
    }
}

// Memory:
// JVM Memory
//   ├─ Thread 1 memory
//   │    └─ userIdLocal value: "user1"
//   ├─ Thread 2 memory
//   │    └─ userIdLocal value: "user2"
//   └─ Thread 3 memory
//        └─ userIdLocal value: "anonymous"
```

### ThreadLocal State: Isolated Per Thread

```java
public class UserContext {
    private static ThreadLocal<String> userLocal = ThreadLocal.withInitial(() -> null);
    
    public static void setUser(String user) {
        userLocal.set(user);
    }
    
    public static String getUser() {
        return userLocal.get();
    }
}

// Thread 1:
UserContext.setUser("user1");
// Thread 2:
UserContext.setUser("user2");
// Meanwhile in Thread 1:
System.out.println(UserContext.getUser());  // "user1" ✅ Not affected by Thread 2!
```

## Side-by-Side Comparison

| Feature | Singleton | ThreadLocal |
|---------|-----------|------------|
| **Instances** | 1 per JVM | 1 per thread |
| **Access** | @Autowired | Static method |
| **Data Isolation** | ❌ Shared | ✅ Per-thread |
| **Thread Safety** | ⚠️ Need sync | ✅ Automatic |
| **Use Case** | Services (stateless) | Request context |
| **Spring Native** | ✅ YES | 🔶 Manual |
| **Memory** | Low | Higher (per thread) |

## Real Example 1: Request Context

### ❌ WRONG: Using singleton

```java
@Component
public class RequestContext {
    private String userId;    // ⚠️ Shared across all requests!
    
    public void setUserId(String id) {
        this.userId = id;     // Thread 1 and 2 overwrite each other
    }
    
    public String getUserId() {
        return userId;
    }
}

@RestController
public class OrderController {
    @Autowired private RequestContext context;
    
    @PostMapping("/order")
    public String createOrder(String userId, String itemId) {
        context.setUserId(userId);  // Request 1: sets "user1"
                                     // Request 2: sets "user2" (overwrites!)
        Thread.sleep(100);           // Simulate processing
        System.out.println(context.getUserId());  // Prints "user2"!
    }
}
```

### ✅ RIGHT: Using ThreadLocal

```java
public class RequestContext {
    private static ThreadLocal<String> userIdLocal = 
        ThreadLocal.withInitial(() -> null);
    
    public static void setUserId(String id) {
        userIdLocal.set(id);  // Per-thread storage
    }
    
    public static String getUserId() {
        return userIdLocal.get();
    }
}

@RestController
public class OrderController {
    @PostMapping("/order")
    public String createOrder(String userId, String itemId) {
        RequestContext.setUserId(userId);  // Each request has own storage
        Thread.sleep(100);
        System.out.println(RequestContext.getUserId());  // ✅ Correct!
    }
}
```

### ✅ BETTER: Using Spring Request Scope

```java
@Component
@Scope("request")  // One per HTTP request
public class RequestContext {
    private String userId;
    
    public void setUserId(String id) { this.userId = id; }
    public String getUserId() { return userId; }
}

@RestController
public class OrderController {
    @Autowired private RequestContext context;  // Injected per-request
    
    @PostMapping("/order")
    public String createOrder(String userId, String itemId) {
        context.setUserId(userId);  // Spring handles per-request isolation
        System.out.println(context.getUserId());  // ✅ Always correct
    }
}
```

## Real Example 2: Security Context (Spring Security Uses This!)

```java
// Spring Security internally uses ThreadLocal
public class SecurityContext {
    private static final ThreadLocal<Authentication> authLocal =
        new ThreadLocal<>();
    
    public static void setAuthentication(Authentication auth) {
        authLocal.set(auth);  // Each thread has its own auth
    }
    
    public static Authentication getAuthentication() {
        return authLocal.get();
    }
}

// In filter, for each request (each on own thread):
@Component
public class SecurityFilter extends OncePerRequestFilter {
    
    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain chain) {
        Authentication auth = authenticateRequest(request);
        SecurityContext.setAuthentication(auth);  // Per-thread isolation!
        
        chain.doFilter(request, response);
        
        SecurityContext.clearContext();  // Clean up
    }
}
```

## ThreadLocal Pitfall: Memory Leaks

```java
public class UserContext {
    private static ThreadLocal<User> userLocal = ThreadLocal.withInitial(() -> null);
    
    public static void setUser(User user) {
        userLocal.set(user);
    }
    
    public static User getUser() {
        return userLocal.get();
    }
    
    // ❌ MUST clean up when done!
    public static void clear() {
        userLocal.remove();  // Remove from ThreadLocal
    }
}

// In filter:
try {
    UserContext.setUser(loadUser());
    chain.doFilter(request, response);
} finally {
    UserContext.clear();  // ✅ Always clean up!
}
```

## When to Use Each

| Scenario | Use | Why |
|----------|-----|-----|
| Service bean with stateless logic | Singleton | What Spring does by default |
| Stateless repository access | Singleton | No shared state |
| Request-specific data | Request Scope or ThreadLocal | Per-request isolation |
| Security context | ThreadLocal | Each request's own context |
| User session data | Session Scope | Per-user isolation |
| Application configuration | Singleton | Immutable, shared safely |

## Interview Tip

"Singleton creates one instance for the entire JVM, shared by all threads - needs synchronization if mutable. ThreadLocal creates one instance per thread with automatic isolation - no synchronization needed. Spring beans are singletons by default and should be stateless. For request-scoped data, use @Scope('request') (Spring standard) or ThreadLocal (manual management). Spring Security uses ThreadLocal internally for authentication context. Always remove ThreadLocal values to prevent memory leaks."

## Quick Checklist

- ✅ Singleton = 1 per JVM, shared across all threads
- ✅ ThreadLocal = 1 per thread, isolated per thread
- ✅ Singleton with mutable state = must synchronize
- ✅ ThreadLocal is automatically thread-safe
- ✅ Use @Scope("request") instead of ThreadLocal if possible
- ✅ ThreadLocal requires manual cleanup (remove())
- ✅ Spring Security uses ThreadLocal for SecurityContext
- ✅ ThreadLocal causes memory leaks if not cleared

---

**Next:** Study Q5 on circular dependencies
