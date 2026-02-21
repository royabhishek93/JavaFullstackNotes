# Q2: What's the problem with prototype bean in a singleton bean?

**Study Time:** 3-4 minutes

---

## Problem

You inject a prototype-scoped bean into a singleton bean. You expect a new instance each time, but you get the same instance every time.

```java
@Component
@Scope("prototype")
public class UserRequest {
    private String userId;
    
    public UserRequest() {
        System.out.println("New UserRequest created");
    }
    
    public void setUserId(String id) { this.userId = id; }
    public String getUserId() { return userId; }
}

@Component  // Singleton by default
public class RequestHandler {
    @Autowired
    private UserRequest userRequest;  // Injected ONCE
}

// Problem: RequestHandler is created ONCE (singleton)
// userRequest is injected ONCE during RequestHandler creation
// The SAME UserRequest instance is reused in every request!
```

## ❌ The Bug

```java
@Component
@Scope("prototype")
public class UserContext {
    private String userId;
    
    public UserContext() {
        System.out.println("New UserContext: " + this.hashCode());
    }
    
    public void setUserId(String id) { this.userId = id; }
    public String getUserId() { return userId; }
}

@Component  // Singleton
public class PaymentService {
    @Autowired
    private UserContext context;  // ONLY injected once!
    
    public void processPayment(String userId) {
        context.setUserId(userId);
        Thread.sleep(100);  // Simulate processing
        System.out.println("User: " + context.getUserId());
    }
}

// Scenario:
// Request 1: processPayment("user1")
//   context.hashCode() = 12345
//   Sets userId = "user1"
// Request 2 (while processing): processPayment("user2")
//   context.hashCode() = 12345  // SAME instance!
//   Sets userId = "user2"  // Overwrites!
// Request 1 resumes:
//   Prints "User: user2"  // WRONG! Should be user1
```

## Output Shows the Bug

```
New UserContext: 12345
Request for user1
Request for user2
User: user2  // ❌ Request 1 gets request 2's user!
User: user2  // ❌ Request 2 gets its own user
```

## ✅ Solution 1: ObjectProvider (BEST)

```java
@Component
public class PaymentService {
    @Autowired
    private ObjectProvider<UserContext> contextProvider;  // Don't inject the bean directly
    
    public void processPayment(String userId) {
        UserContext context = contextProvider.getObject();  // Get NEW instance each time!
        context.setUserId(userId);
        Thread.sleep(100);
        System.out.println("User: " + context.getUserId());
    }
}

// Output:
// New UserContext: 12345
// New UserContext: 67890  // ✅ Different instance!
// User: user1  // ✅ Correct
// User: user2  // ✅ Correct
```

### How ObjectProvider Works

```java
@Autowired
private ObjectProvider<UserContext> provider;

// Get a bean
UserContext context = provider.getObject();  // New instance

// Get optional
Optional<UserContext> optional = provider.getIfAvailable();

// Get with default
UserContext context = provider.getIfAvailable(() -> new UserContext());

// Lazy-get (only if needed)
UserContext context = provider.getIfPresent().orElse(new UserContext());
```

## ✅ Solution 2: Provider<T> (Less common)

```java
import javax.inject.Provider;

@Component
public class PaymentService {
    @Autowired
    private Provider<UserContext> contextProvider;  // JSR 330 Provider
    
    public void processPayment(String userId) {
        UserContext context = contextProvider.get();  // Get NEW instance
        context.setUserId(userId);
        System.out.println("User: " + context.getUserId());
    }
}
```

## ✅ Solution 3: Method-Level Injection

```java
@Component
public class PaymentService {
    
    public void processPayment(UserContext context, String userId) {
        // Spring injects per-method, bypassing singleton
        context.setUserId(userId);
        System.out.println("User: " + context.getUserId());
    }
}
```

## ✅ Solution 4: Use Request Scope Instead

```java
@Component
@Scope("request")  // Not prototype - request scope
public class UserContext {
    private String userId;
    
    public void setUserId(String id) { this.userId = id; }
    public String getUserId() { return userId; }
}

@Component
public class PaymentService {
    @Autowired
    private UserContext context;  // Injected per request, not per injection
    
    public void processPayment(String userId) {
        context.setUserId(userId);
        System.out.println("User: " + context.getUserId());
    }
}

// Works because context is request-scoped
// Each HTTP request gets its own context
```

## Complete Working Example

```java
@Component
@Scope("prototype")
public class UserRequest {
    private String userId;
    private long createdAt = System.currentTimeMillis();
    
    public UserRequest() {
        System.out.println("UserRequest created: " + this.hashCode());
    }
    
    public void setUserId(String id) { this.userId = id; }
    public String getUserId() { return userId; }
    public long getCreatedAt() { return createdAt; }
}

@Component
public class OrderService {
    @Autowired
    private ObjectProvider<UserRequest> requestProvider;  // ✅ Use ObjectProvider
    
    @Transactional
    public void createOrder(String userId, List<String> items) {
        UserRequest request = requestProvider.getObject();  // NEW instance
        request.setUserId(userId);
        
        System.out.println("Created at: " + request.getCreatedAt());
        System.out.println("For user: " + request.getUserId());
        
        // Save order with request context...
    }
}
```

## When This Happens in Real Code

```java
// ❌ BEFORE (Bug!)
@Component
public class RequestFilter {
    @Autowired
    private RequestContext context;  // Injected once
}

// ✅ AFTER (Fixed!)
@Component
public class RequestFilter {
    @Autowired
    private ObjectProvider<RequestContext> contextProvider;
}

// Reason: RequestContext is prototype, but injected into singleton filter
```

## Interview Tip

"Injecting a prototype bean into a singleton bean doesn't work as expected - the prototype is only created once during singleton construction. Use `ObjectProvider<T>` to get a new instance each time you call `.getObject()`. Alternatively, use `Provider<T>` (JSR 330), method-level injection, or switch the dependency to request scope. ObjectProvider is the Spring standard solution and preferred."

## Quick Checklist

- ✅ Prototype in singleton = ONLY created once (bug!)
- ✅ Solution 1 (BEST): `ObjectProvider<T>.getObject()`
- ✅ Solution 2: `Provider<T>.get()` (JSR 330)
- ✅ Solution 3: Method-level injection parameter
- ✅ Solution 4: Use request scope, not prototype
- ✅ ObjectProvider is Spring standard
- ✅ Common in filters, interceptors, handlers

---

**Next:** Study Q3 on singleton thread safety patterns
