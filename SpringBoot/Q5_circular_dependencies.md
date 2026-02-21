# Q5: What are circular dependencies? How do you resolve them?

**Study Time:** 3-5 minutes

---

## Problem

Two or more beans depend on each other, creating a cycle that Spring can't resolve.

```java
@Component
public class ServiceA {
    @Autowired private ServiceB serviceB;  // Depends on B
}

@Component
public class ServiceB {
    @Autowired private ServiceA serviceA;  // Depends on A
}

// At startup:
// Spring tries to create ServiceA
//   → ServiceA needs ServiceB
//   → Spring tries to create ServiceB
//   → ServiceB needs ServiceA
//   → But ServiceA isn't fully created yet
//   → ❌ UnsatisfiedDependencyException
```

## The Error

```
Error creating bean with name 'serviceA':
Unsatisfied dependency expressed through field 'serviceB';
nested exception is org.springframework.beans.factory.BeanCurrentlyInCreationException:
Error creating bean with name 'serviceB':
Requested bean is currently in creation: Is there an unresolved circular dependency?
```

## Why It Happens

```
Timeline:
1. Spring starts creating ServiceA
2. ServiceA needs ServiceB → Spring starts creating ServiceB
3. ServiceB needs ServiceA → But ServiceA not ready yet
4. DEADLOCK → Circular dependency error
```

## ✅ Solution 1: Setter Injection (BEST)

```java
@Component
public class ServiceA {
    private ServiceB serviceB;
    
    @Autowired  // Setter injection
    public void setServiceB(ServiceB serviceB) {
        this.serviceB = serviceB;
    }
}

@Component
public class ServiceB {
    private ServiceA serviceA;
    
    @Autowired  // Setter injection
    public void setServiceA(ServiceA serviceA) {
        this.serviceA = serviceA;
    }
}

// Why this works:
// 1. Spring creates ServiceA without dependencies
// 2. Spring creates ServiceB without dependencies
// 3. Then it calls setServiceB() and setServiceA()
// ✅ No circular dependency!
```

## ✅ Solution 2: Constructor Injection + @Lazy

```java
@Component
public class ServiceA {
    private final ServiceB serviceB;
    
    @Autowired
    public ServiceA(@Lazy ServiceB serviceB) {  // Lazy initialization
        this.serviceB = serviceB;
    }
}

@Component
public class ServiceB {
    private final ServiceA serviceA;
    
    @Autowired
    public ServiceB(@Lazy ServiceA serviceA) {  // Lazy initialization
        this.serviceA = serviceA;
    }
}

// Why this works:
// 1. Spring passes a Proxy for serviceB (not the real bean)
// 2. Real bean created later when first accessed
// ✅ No circular dependency!
```

## ✅ Solution 3: ObjectProvider (Most Spring-ish)

```java
@Component
public class ServiceA {
    private final ObjectProvider<ServiceB> serviceBProvider;  // Provider, not B directly
    
    @Autowired
    public ServiceA(ObjectProvider<ServiceB> serviceBProvider) {
        this.serviceBProvider = serviceBProvider;
    }
    
    public void doSomething() {
        ServiceB serviceB = serviceBProvider.getObject();  // Get when needed
        serviceB.help();
    }
}

@Component
public class ServiceB {
    private final ObjectProvider<ServiceA> serviceAProvider;  // Provider, not A directly
    
    @Autowired
    public ServiceB(ObjectProvider<ServiceA> serviceAProvider) {
        this.serviceAProvider = serviceAProvider;
    }
}

// Why this works:
// ObjectProvider is created immediately
// Actual beans created when accessed via getObject()
// ✅ No circular dependency!
```

## ✅ Solution 4: Extract Common Dependency

Often the real issue is poor design. Extract the shared concern:

### ❌ BEFORE: Circular Design

```java
@Component
public class OrderService {
    @Autowired private PaymentService paymentService;
    
    public void createOrder() {
        paymentService.processPayment();  // Calls payment
    }
}

@Component
public class PaymentService {
    @Autowired private OrderService orderService;
    
    public void processPayment() {
        orderService.updateStatus();  // Calls order (circular!)
    }
}
```

### ✅ AFTER: Better Design

```java
@Component
public class OrderService {
    @Autowired private PaymentService paymentService;
    @Autowired private EventPublisher events;  // New: events instead of direct call
    
    public void createOrder() {
        paymentService.processPayment();
        events.publish(new OrderCreatedEvent());  // Publish event
    }
}

@Component
public class PaymentService {
    @Autowired private EventPublisher events;  // No dependency on OrderService!
    
    public void processPayment() {
        // Process payment
        events.publish(new PaymentProcessedEvent());  // Publish event
    }
}

@Component
public class OrderEventHandler {
    @Autowired private OrderService orderService;
    
    @EventListener
    public void onPaymentProcessed(PaymentProcessedEvent event) {
        orderService.updateStatus();  // Handle through event
    }
}

// Now: No circular dependency! Events decouple them.
```

## Real Example 1: User and Post Service

### ❌ Circular (Bad Design)

```java
@Component
public class UserService {
    @Autowired private PostService postService;
    
    public void getUserWithPosts(int userId) {
        User user = findUser(userId);
        List<Post> posts = postService.getPostsByUser(userId);  // Call post service
        return new UserDTO(user, posts);
    }
}

@Component
public class PostService {
    @Autowired private UserService userService;
    
    public Post createPost(Post post) {
        User author = userService.getUser(post.getAuthorId());  // Call user service (circular!)
        return save(post);
    }
}
```

### ✅ Solution: Proper Abstractions

```java
@Component
public class UserService {
    @Autowired private PostService postService;
    
    public UserDTO getUserWithPosts(int userId) {
        User user = findUser(userId);
        List<Post> posts = postService.getPostsByUser(userId);
        return new UserDTO(user, posts);
    }
}

@Component
public class PostService {
    @Autowired private UserRepository userRepo;  // Direct access, not UserService
    
    public Post createPost(Post post) {
        User author = userRepo.findById(post.getAuthorId());  // Repository, no service
        return save(post);
    }
}

// Or use @Lazy in constructor:
@Component
public class PostService {
    @Autowired
    public PostService(@Lazy UserService userService) {
        this.userService = userService;
    }
}
```

## Real Example 2: Filter and Service

### ❌ Circular

```java
@Component
public class AuthFilter {
    @Autowired private SecurityService securityService;
    
    public void checkAuth() {
        securityService.verify();
    }
}

@Component
public class SecurityService {
    @Autowired private AuthFilter authFilter;
    
    public void verify() {
        // Circular!
    }
}
```

### ✅ Fixed: Setter Injection

```java
@Component
public class AuthFilter {
    private SecurityService securityService;
    
    @Autowired
    public void setSecurityService(SecurityService securityService) {
        this.securityService = securityService;
    }
}

@Component
public class SecurityService {
    private AuthFilter authFilter;
    
    @Autowired
    public void setAuthFilter(AuthFilter authFilter) {
        this.authFilter = authFilter;
    }
}

// ✅ Works because beans created first, then setters called
```

## Comparison of Solutions

| Solution | Pros | Cons | When Use |
|----------|------|------|----------|
| Setter Injection | Simple, works well | Less clear dependencies | Quick fix |
| @Lazy | Clean, constructor-safe | Might hide issues | Modern Spring |
| ObjectProvider | Explicit, flexible | More verbose | Production code |
| Extract Service | Best design | Requires refactoring | New code |
| Event Bus | Decouples completely | More complex | Large systems |
| Repository | Direct data access | More queries | Common pattern |

## Interview Tip

"Circular dependencies occur when beans depend on each other. Solutions: 1) Use setter injection instead of constructor, 2) Use @Lazy to delay initialization, 3) Use ObjectProvider to defer resolution, 4) Extract shared dependencies to a third service, or 5) Use event-based communication instead of direct calls. The best approach depends on design - often circular dependencies indicate poor architecture. First try setter injection or @Lazy, then consider refactoring if it's a symptom of deeper design issues."

## Quick Checklist

- ✅ Circular dependency = beans depending on each other
- ✅ Constructor injection is vulnerable (creates cycles)
- ✅ Solution 1: Setter injection (defer dependency setup)
- ✅ Solution 2: @Lazy (deferred initialization)
- ✅ Solution 3: ObjectProvider (explicit provider access)
- ✅ Solution 4: Extract services (better design)
- ✅ Solution 5: Events (decouple completely)
- ✅ Usually indicates design that needs improvement

---

**SpringBoot Complete!** You've covered all 5 Spring Bean interview questions. Review INDIVIDUAL_QUESTIONS_GUIDE.md for navigation!
