# Q4: AOP Internals — How Spring AOP Actually Works (15-Yr Architect Level)

**Study Time:** 25-30 minutes | **Frequency:** 85% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "You said @Around uses a proxy. Walk me through what AnnotationAwareAspectJAutoProxyCreator does, how the interceptor chain is built, and how multiple aspects are ordered at runtime." — Real architect question.

---

## NEW LEARNER FOUNDATION — Read This First

### What is AOP? (Plain English)
```
AOP = Aspect-Oriented Programming

Problem it solves: you have "cross-cutting concerns" — behaviour that
appears in many places but has nothing to do with business logic:
  - Logging execution time     → every service method
  - Checking authentication    → every controller
  - Opening a DB transaction   → every service method
  - Rate limiting              → every external call

Without AOP: you copy-paste the same logging/auth/TX code into 100 methods.
With AOP:    you write it ONCE in an Aspect. Spring adds it everywhere automatically.

```

### Key AOP Terms (Simple Definitions)
```
Aspect    = the class that holds your cross-cutting logic
            Example: ExecutionTimeAspect, SecurityAspect

Advice    = WHAT to do (the actual code)
            @Before, @After, @Around, @AfterReturning, @AfterThrowing

Pointcut  = WHERE to apply the advice (which methods)
            Example: "all methods annotated with @LogExecutionTime"
                     "all public methods in com.example.service.*"

JoinPoint = the specific method call being intercepted right now
            Gives you: method name, arguments, target object

Advisor   = Pointcut + Advice paired together (Spring's internal unit)
            "When THIS matches (Pointcut), do THAT (Advice)"

Weaving   = the process of applying aspects to target objects
            Spring does this at runtime using proxies
```

### What @Around Means (Plain English)
```
@Around = "I want to wrap around the method completely"
          Like a sandwich:

  [Your @Around code — BEFORE part]
     ↓ pjp.proceed() ← this calls the real method
  [Real method runs]
     ↓ returns result
  [Your @Around code — AFTER part]

You control:
  - Whether the real method runs at all (don't call pjp.proceed() to skip it)
  - What arguments it receives (pjp.proceed(newArgs))
  - What result the caller sees (return differentValue instead of result)
  - Whether exceptions propagate (catch and return default instead)
```

---

## BIG PICTURE — Where AOP Fits in Your App

```
 SPRING BOOT APPLICATION — STARTUP (runs once)
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  @SpringBootApplication → @EnableAspectJAutoProxy                │
 │       ↓                                                          │
 │  Registers: AnnotationAwareAspectJAutoProxyCreator               │
 │             (a BeanPostProcessor — runs after every bean created)│
 │                                                                  │
 │  For EVERY bean:                                                 │
 │    ┌──────────────────────────────────────────────────────────┐  │
 │    │ 1. Collect all @Aspect beans                             │  │
 │    │ 2. Parse pointcuts → build Advisor list                  │  │
 │    │ 3. Does any Advisor's Pointcut match this bean?          │  │
 │    │    YES → wrap bean in CGLIB proxy (has interceptor chain)│  │
 │    │    NO  → use real bean as-is                             │  │
 │    └──────────────────────────────────────────────────────────┘  │
 │                                                                  │
 └──────────────────────────────────────────────────────────────────┘

 RUNTIME — one HTTP request to placeOrder():
 ┌──────────────────────────────────────────────────────────────────┐
 │                                                                  │
 │  [HTTP Request]                                                  │
 │       │                                                          │
 │       ▼                                                          │
 │  [OrderService CGLIB Proxy]     ◄◄◄ THIS FILE                   │
 │       │                                                          │
 │       │  ReflectiveMethodInvocation.proceed() — CHAIN:          │
 │       │  ┌────────────────────────────────────────────────────┐ │
 │       │  │ [1] SecurityAspect @Before  @Order(1) ←outermost   │ │
 │       │  │      ↓ checkAuth() passes                          │ │
 │       │  │ [2] MetricsAspect @Around   @Order(2)              │ │
 │       │  │      ↓ timer.start()                               │ │
 │       │  │ [3] TransactionInterceptor  @Order(MAX-1)          │ │
 │       │  │      ↓ conn.setAutoCommit(false)                   │ │
 │       │  │ [4] Real OrderService.placeOrder() ← innermost     │ │
 │       │  │      ↑ returns result                              │ │
 │       │  │ [3] TransactionInterceptor commits TX              │ │
 │       │  │ [2] MetricsAspect logs duration                    │ │
 │       │  │ [1] SecurityAspect @Before (no after part)         │ │
 │       │  └────────────────────────────────────────────────────┘ │
 │       │                                                          │
 │       ▼                                                          │
 │  response returned to caller                                     │
 │                                                                  │
 │  SELF-INVOCATION TRAP:                                           │
 │  Inside real method: this.otherMethod() ──X──► bypasses proxy   │
 │  Proxy is in ApplicationContext, 'this' = real object (no chain)│
 └──────────────────────────────────────────────────────────────────┘

 @Order controls who wraps whom (lower = outermost):
 ┌────────────────────────────────────────────────────┐
 │  @Order(1) Security  [   wraps everything   ]      │
 │  @Order(2) Metrics    [  wraps TX + method  ]      │
 │  @Order(MAX) TX        [ wraps real method ] ]     │
 │                          [Real Method]             │
 └────────────────────────────────────────────────────┘
```

---

## What Spring AOP Actually Is (vs What People Think)

```
What people think:
  "AOP magic wraps methods with annotation processing"

What it actually is:
  Spring AOP = Proxy-based method interception
  ONLY works for Spring-managed beans
  ONLY intercepts method calls that go THROUGH the proxy
  Uses standard Java: runtime subclassing (CGLIB) or interface wrapping (JDK proxy)
  Has NOTHING to do with AspectJ at runtime (Spring uses AspectJ syntax/annotations
  but NOT AspectJ's weaving engine in the default proxy mode)

Three AOP modes in Spring:
  1. Proxy mode (DEFAULT) — runtime proxy, only public method calls via bean reference
  2. Load-Time Weaving (LTW) — AspectJ agent rewrites bytecode at classload time
                                → works on private methods, constructors, self-calls
  3. Compile-Time Weaving (CTW) — AspectJ compiler rewrites .class files at build time
                                   → fastest, but requires AspectJ compiler plugin

99% of Spring apps use mode 1 (proxy mode). This file covers that.
```

---

## Part 1: Startup — How Proxies Are Created

### AnnotationAwareAspectJAutoProxyCreator (The Key Class)

```
This is the BeanPostProcessor that powers ALL Spring AOP.
Registered by: @EnableAspectJAutoProxy (included in @SpringBootApplication)

It runs postProcessAfterInitialization() for EVERY bean created by Spring.

For each bean:
  1. Collect all @Aspect beans from the ApplicationContext
  2. For each @Aspect: parse @Pointcut / @Around / @Before / @After methods
     → each becomes an Advisor (Pointcut + Advice pair)
  3. Ask each Advisor: "does your Pointcut match this bean?"
  4. If ANY advisor matches → create a proxy for the bean
  5. Register the proxy as the bean in the ApplicationContext
     (the real object is wrapped inside; callers always get the proxy)
```

```java
// What happens when Spring processes your OrderService:

// You defined:
@Aspect
@Component
public class LoggingAspect {
    @Around("@annotation(LogExecutionTime)")
    public Object log(ProceedingJoinPoint pjp) throws Throwable { ... }
}

@Aspect
@Component
public class SecurityAspect {
    @Before("execution(* com.example.service.*.*(..))")
    public void checkAuth(JoinPoint jp) { ... }
}

// Spring startup:
// 1. Creates LoggingAspect bean
// 2. Creates SecurityAspect bean
// 3. Processes OrderService:
//      - LoggingAspect.pointcut matches placeOrder() (@LogExecutionTime present)? YES
//      - SecurityAspect.pointcut matches OrderService methods? YES (execution pattern)
//    → OrderService gets a CGLIB proxy wrapping both advisors
// 4. ApplicationContext.getBean(OrderService.class) returns the PROXY, not the real bean
```

### How ProxyFactory Builds the Proxy

```java
// Internally (simplified):
ProxyFactory proxyFactory = new ProxyFactory();
proxyFactory.setTarget(realOrderService);              // the real object
proxyFactory.setProxyTargetClass(true);               // use CGLIB (Spring Boot default)
proxyFactory.addAdvisor(loggingAdvisor);              // LoggingAspect
proxyFactory.addAdvisor(securityAdvisor);             // SecurityAspect
proxyFactory.addAdvisor(transactionAdvisor);          // @Transactional (if present)

Object proxy = proxyFactory.getProxy();
// Returns: OrderService$$SpringCGLIB$$0
// This proxy holds: [securityAdvisor, transactionAdvisor, loggingAdvisor] + realOrderService
```

---

## Part 2: Runtime — The Interceptor Chain

### ReflectiveMethodInvocation — How the Chain Executes

```
When the proxy's placeOrder() is called:

proxy.placeOrder(req)
     ↓
CGLIB override runs
     ↓
DynamicAdvisedInterceptor.intercept()
     ↓
Build ReflectiveMethodInvocation with list of interceptors
     ↓
ReflectiveMethodInvocation.proceed()
     ↓ (recursive chain — each interceptor calls proceed() to continue)
  [0] ExposeInvocationInterceptor (always first — stores invocation in ThreadLocal)
  [1] SecurityAspect.checkAuth()      → @Before (runs, then calls proceed())
  [2] TransactionInterceptor          → @Around (opens TX, calls proceed(), commits)
  [3] LoggingAspect.log()             → @Around (starts timer, calls proceed(), logs)
  [4] Method.invoke(realOrderService) → calls the REAL placeOrder() method
      ← returns result
  [3] LoggingAspect resumes           → stops timer, logs duration
  [2] TransactionInterceptor resumes  → commits transaction
  [1] (SecurityAspect @Before has no "after" part)
     ↓
proxy returns result to caller
```

```java
// ReflectiveMethodInvocation.proceed() — the actual recursion:
public Object proceed() throws Throwable {
    // If we've run all interceptors, invoke the real method
    if (this.currentInterceptorIndex == this.interceptorsAndDynamicMethodMatchers.size() - 1) {
        return invokeJoinpoint();  // method.invoke(target, args)
    }

    // Get next interceptor and invoke it
    Object interceptorOrInterceptionAdvice =
        this.interceptorsAndDynamicMethodMatchers.get(++this.currentInterceptorIndex);

    if (interceptorOrInterceptionAdvice instanceof MethodInterceptor) {
        return ((MethodInterceptor) interceptorOrInterceptionAdvice).invoke(this);
        // Each MethodInterceptor receives THIS (the MethodInvocation)
        // @Around advice calls pjp.proceed() which calls THIS.proceed()
        // → recursive chain
    }
    // ...
}
```

---

## Part 3: Advice Types — Internals of Each

```java
// @Before — runs, then ALWAYS calls proceed()
// Implemented as MethodBeforeAdviceInterceptor wrapping your @Before method
// If @Before throws: proceed() is NOT called → real method never runs

// @After — like finally: runs after proceed() regardless of exception
// Implemented as AspectJAfterAdvice
// Cannot affect return value, cannot suppress exceptions

// @AfterReturning — runs only if proceed() returned normally (no exception)
// Can read the return value, cannot change it (use @Around to change return)

// @AfterThrowing — runs only if proceed() threw an exception
// Can re-throw different exception, cannot suppress it (use @Around to suppress)

// @Around — full control: before AND after, can:
//   - Skip the real method (don't call pjp.proceed())
//   - Change return value (return different object)
//   - Suppress exception (catch and return default)
//   - Change arguments (pjp.proceed(newArgs))

// Example: @Around that changes arguments
@Around("execution(* com.example.*.*(String, ..))")
public Object sanitizeInput(ProceedingJoinPoint pjp) throws Throwable {
    Object[] args = pjp.getArgs();
    args[0] = ((String) args[0]).trim().toLowerCase();  // sanitize first arg
    return pjp.proceed(args);  // call with modified args
}
```

---

## Part 4: Aspect Ordering — Which Runs First?

```
When multiple aspects apply to the same method, ORDER MATTERS.
Especially: if you have both @Transactional and @Around logging:
  - Which wraps which?
  - Does logging see the committed data or the in-progress TX data?
  - Does SecurityAspect run before or after the TX opens?
```

```java
// Ordering mechanisms (highest priority = runs OUTERMOST = first before, last after):

// Option 1: @Order annotation
@Aspect @Component @Order(1)   // runs outermost
public class SecurityAspect { ... }

@Aspect @Component @Order(2)
public class TransactionAspect { ... }  // @Transactional uses this internally

@Aspect @Component @Order(3)   // runs innermost (closest to real method)
public class LoggingAspect { ... }

// Runtime chain (outermost first):
// Security(@Order=1) → Transaction(@Order=2) → Logging(@Order=3) → RealMethod
// ← Logging ← Transaction ← Security ← returns to caller

// Option 2: Implement Ordered interface
@Aspect @Component
public class SecurityAspect implements Ordered {
    @Override
    public int getOrder() { return 1; }
}

// Option 3: @Priority (Jakarta EE — same as @Order but different annotation)
```

```
CRITICAL ORDER DECISIONS in production:

Security BEFORE Transaction:
  ✅ Correct — authenticate/authorize before even opening a DB connection
  ✅ If auth fails, no TX opened, no DB load

Transaction BEFORE Logging:
  ✅ Correct — log the actual execution time including TX overhead
  ✅ If you log OUTSIDE the TX, you only see method time, not commit time

Retry BEFORE Transaction:
  ✅ Correct — retry must re-open a NEW transaction each attempt
  ❌ If retry is INSIDE transaction: retry within a single TX
     → DB might already be in bad state, retrying won't help

Default order when @Order not specified:
  → undefined (depends on classpath scan order)
  → always specify @Order for aspects that interact with each other
```

---

## Part 5: Pointcut Expressions — What They Match

```java
// execution() — matches method execution
@Pointcut("execution(* com.example.service.*.*(..))")
// Breakdown:
// *                  → any return type
// com.example.service.*  → any class in this package
// .*                 → any method name
// (..)               → any arguments (0 or more, any type)

// More precise:
@Pointcut("execution(public * com.example.service.OrderService.place*(Long, ..))")
// public             → only public methods
// OrderService       → only this class
// place*             → methods starting with "place"
// (Long, ..)         → first arg is Long, rest can be anything

// @annotation() — matches methods with a specific annotation
@Pointcut("@annotation(com.example.annotation.LogExecutionTime)")

// @within() — matches ALL methods in classes with the annotation
@Pointcut("@within(org.springframework.stereotype.Service)")
// vs execution(* (@Service *).*(..)) — same thing, cleaner

// within() — matches all methods in a class/package
@Pointcut("within(com.example.service..*)")  // note .. for sub-packages

// Composition — combine pointcuts
@Pointcut("within(com.example.service..*) && @annotation(LogExecutionTime)")
// Matches: methods annotated @LogExecutionTime AND inside service package

// args() — match AND bind arguments
@Around("execution(* *.*(..)) && args(userId, ..)")
public Object logUser(ProceedingJoinPoint pjp, Long userId) throws Throwable {
    log.info("Called with userId={}", userId);  // userId bound from the arg
    return pjp.proceed();
}
```

---

## Part 6: Complete Production Example — Multi-Aspect with Ordering

```java
// Three aspects on one service method — correct ordering for production

@Aspect @Component @Order(1)
public class AuthenticationAspect {
    @Before("within(com.example.service..*)")
    public void verifyAuthenticated(JoinPoint jp) {
        // Runs FIRST — before TX opens, before timing starts
        SecurityContext ctx = SecurityContextHolder.getContext();
        if (ctx.getAuthentication() == null) {
            throw new AccessDeniedException("Not authenticated");
        }
    }
}

@Aspect @Component @Order(2)
public class MetricsAspect {
    // Runs second — wraps TX + real method, measures total time including commit
    @Around("@annotation(LogExecutionTime)")
    public Object measure(ProceedingJoinPoint pjp) throws Throwable {
        Timer.Sample sample = Timer.start(registry);
        try {
            return pjp.proceed();
        } finally {
            sample.stop(registry.timer("method.duration",
                "method", pjp.getSignature().getName()));
        }
    }
}

// @Transactional (Spring's internal advisor): Order = Integer.MAX_VALUE - 1 (lowest priority = innermost)
// Or configure: @EnableTransactionManagement(order = 3)

// Runtime execution for placeOrder() with all three:
// Auth(1) → Metrics(2) → Transaction(MAX-1) → real placeOrder()
// ← Transaction commits ← Metrics records time (including commit) ← Auth (nothing after)
```

---

## Part 7: The Complete Self-Invocation Problem + All Fixes

```java
@Service
public class ProductService {

    // Called externally: proxy intercepts → @Around fires ✅
    @LogExecutionTime
    public void processProduct(Long id) {
        this.validateProduct(id);  // self-call → NOT through proxy
    }

    @LogExecutionTime  // NEVER fires for self-calls
    public void validateProduct(Long id) { ... }
}

// WHY:
// ProductService in ApplicationContext = CGLIB proxy
// Inside processProduct(), 'this' = the real ProductService
// The real object has no interceptors — it IS the target
// pjp.proceed() already "reached" the real object
// Calling this.x() inside is just a regular Java call inside the real object
```

```java
// FIX OPTION 1: Extract to separate service (always cleanest)
@Service public class ProductValidator {
    @LogExecutionTime
    public void validate(Long id) { ... }
}
@Service public class ProductService {
    @Autowired ProductValidator validator;

    @LogExecutionTime
    public void processProduct(Long id) {
        validator.validate(id);  // through proxy ✅
    }
}

// FIX OPTION 2: Inject self via ApplicationContext
@Service
public class ProductService {
    @Autowired private ApplicationContext ctx;

    @LogExecutionTime
    public void processProduct(Long id) {
        ctx.getBean(ProductService.class).validateProduct(id); // proxy ✅
    }
}

// FIX OPTION 3: Load-Time Weaving (AspectJ LTW)
// Add -javaagent:aspectjweaver.jar to JVM args
// @EnableLoadTimeWeaving in config
// → AOP works on self-calls, private methods, constructors
// → Full AspectJ power, not just proxy-based interception
// → Suitable when you absolutely need to intercept self-calls in same class
```

---

## Key Differences: Spring AOP vs AspectJ

| | Spring AOP (Proxy) | AspectJ (Weaving) |
|---|---|---|
| Mechanism | Runtime proxy (CGLIB/JDK) | Bytecode weaving |
| Works on | Spring beans only | Any Java class |
| Self-calls | No | Yes |
| Private methods | No | Yes |
| Constructors | No | Yes |
| Performance overhead | Tiny (~ns per call) | None (compiled in) |
| Setup | Auto (starter-aop) | Agent or compiler plugin |
| Use when | 99% of cases | Special cases (self-call, non-Spring) |

---

## Interview Cheat Sheet

> "Spring AOP works via AnnotationAwareAspectJAutoProxyCreator, a BeanPostProcessor that runs after every bean is instantiated. It collects all @Aspect beans, parses their pointcuts and advices into Advisors, and for any bean matched by at least one Advisor it creates a CGLIB subclass proxy. The proxy holds a list of MethodInterceptors (one per matching advisor) in a ReflectiveMethodInvocation chain. When a method is called on the proxy, the chain executes recursively — each @Around advice calls pjp.proceed() to pass control to the next interceptor, until the real method is finally invoked. Ordering is controlled by @Order — lower number = outermost = runs first before, runs last after. Self-invocation bypasses all this because 'this' inside the method is the unwrapped target object, not the CGLIB proxy held in the ApplicationContext. The only way to fix self-invocation in proxy mode is to route the call through another Spring bean or inject self via the ApplicationContext."
