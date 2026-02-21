# Q1: What are Spring bean scopes?

**Study Time:** 3-4 minutes

---

## Problem

Spring beans can have different lifetimes. Sometimes you want one instance for the entire app, sometimes you want a new one per request.

```java
@Component
public class UserService {
    // How many instances of UserService will exist?
    // One per app? One per request? One per thread?
    // Default: ONE for entire app (Singleton)
}
```

Understanding scope is critical for:
- Thread safety issues
- Memory leaks
- Shared state correctness

## 5 Main Scopes

### Scope 1: Singleton (DEFAULT) 🔥

**One instance for entire app lifetime.**

```java
@Component
@Scope("singleton")  // Or just omit - it's default
public class UserService {
    // UserService instance is created once
    // Same instance shared across entire app
}

// Usage
@RestController
public class UserController {
    @Autowired UserService service1;  // Same instance
    
    @Autowired UserService service2;  // SAME instance as service1!
}
```

**Singleton State Sharing:**

```java
@Component
public class PaymentService {
    private int requestCount = 0;  // Shared across ALL requests!!
    
    public void processPayment() {
        requestCount++;  // ⚠️ Thread safety issue!
        System.out.println("Request: " + requestCount);
    }
}

// If 1000 requests come in parallel, requestCount is unsafe!
```

### Scope 2: Prototype 

**New instance every time you request it.**

```java
@Component
@Scope("prototype")
public class UserContext {
    // New UserContext created each time it's injected
}

@RestController
public class UserController {
    @Autowired UserContext context1;  // New instance
    
    @Autowired UserContext context2;  // DIFFERENT instance!
}
```

**When to use:**
- Per-request state (user ID, etc)
- Request-scoped objects
- NOT for service classes (usually)

### Scope 3: Request (Web Apps Only)

**New instance for each HTTP request.**

```java
@Component
@Scope("request")
public class RequestContext implements Serializable {
    private String userId;
    private LocalDateTime createdAt;
    
    public RequestContext() {
        this.createdAt = LocalDateTime.now();
        System.out.println("New RequestContext for request");
    }
}

@RestController
public class HomeController {
    @Autowired private RequestContext context;  // Injected per request
    
    @GetMapping("/home")
    public String home() {
        System.out.println("Request started at: " + context.createdAt);
        return "OK";
    }
}
```

**Real example:**
- Request 1 comes: RequestContext created
- Request 2 comes: DIFFERENT RequestContext created
- Request 1 finishes: Context garbage collected
- Request 2 finishes: Its context garbage collected

### Scope 4: Session (Web Apps Only)

**One instance per HTTP session (same user across multiple requests).**

```java
@Component
@Scope("session")
public class UserSession {
    private String userId;
    private List<String> shoppingCart;
    
    public UserSession() {
        System.out.println("New session");
    }
}

@RestController
public class CartController {
    @Autowired private UserSession session;  // Same for all requests from same user
    
    @PostMapping("/add-item")
    public String addItem(@RequestParam String item) {
        session.shoppingCart.add(item);  // Persists across requests
        return "Added";
    }
    
    @GetMapping("/cart")
    public List<String> getCart() {
        return session.shoppingCart;  // Same cart as before
    }
}
```

**Lifecycle:**
- User logs in: Session created
- User browses: SAME session
- User adds items: Persists in session
- User logs out/times out: Session destroyed

### Scope 5: Application 

**One instance for entire app lifetime (like Singleton but accessed differently).**

```java
@Component
@Scope("application")
public class AppConfig {
    private Properties settings;
    
    public AppConfig() {
        System.out.println("App starting - config loaded");
    }
}
```

**Difference from Singleton:**
- Usually no difference in practice
- Singleton = Spring-managed singleton
- Application = ServletContext-managed (less common)

## Scope Comparison Table

| Scope | Instances | When | Thread-Safe? |
|-------|-----------|------|-------------|
| Singleton | 1 per app | Entire app lifetime | ⚠️ NO - shared state |
| Prototype | New per inject | Every injection | ✅ YES - per instance |
| Request | New per HTTP | Each HTTP request | ✅ YES - per request |
| Session | Per user | User's session | ✅ YES - per user |
| Application | 1 per app | Entire app lifetime | ❌ NO - shared |

## Common Example: The Problem

```java
// ❌ NOT Thread-Safe Singleton
@Component
public class MessageService {
    private String lastMessage;  // ⚠️ Shared state!
    
    public void saveMessage(String msg) {
        lastMessage = msg;
        Thread.sleep(100);  // Simulate processing
        System.out.println("Saved: " + lastMessage);
    }
}

// If 2 threads call simultaneously:
// Thread 1: lastMessage = "Thread1 message"
// Thread 2: lastMessage = "Thread2 message"  [overwrites!]
// Thread 1: prints "Thread2 message"  [wrong!]
```

```java
// ✅ Thread-Safe Singleton (Stateless)
@Component
public class MessageService {
    // NO shared state - each method call is independent
    
    public void saveMessage(String msg) {
        // msg is local variable, not shared
        processMessage(msg);
        System.out.println("Saved: " + msg);
    }
}
```

## Interview Tip

"Spring has 5 scopes: Singleton (default, one instance per app - watch thread safety), Prototype (new per injection), Request (new per HTTP request), Session (per user session), and Application (whole app). Singleton is the default and most common for services - they should be stateless. Use Request scope for request-specific data, Session for user data across requests. The key issue: Singleton beans with mutable state are NOT thread-safe."

## Quick Checklist

- ✅ Singleton = DEFAULT, one instance per app
- ✅ Singleton beans must be STATELESS (immutable state)
- ✅ Prototype = new instance per injection  
- ✅ Request = new per HTTP request
- ✅ Session = one per user session
- ✅ Application = rare, usually use Singleton
- ✅ @Scope("scope-name") to set scope
- ✅ Singleton with shared state = BUG

---

**Next:** Study Q2 on the prototype-in-singleton problem
