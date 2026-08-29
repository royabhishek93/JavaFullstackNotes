# Spring AOP — Visual Guide for New Learners

---

## The Problem: Repetitive Code Everywhere

Without AOP, every method needs the same boilerplate:

```
fetchEmployee()          updateEmployee()         deleteEmployee()
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│ log("start")    │      │ log("start")    │      │ log("start")    │
│ startTxn()      │      │ startTxn()      │      │ startTxn()      │
│                 │      │                 │      │                 │
│  BUSINESS LOGIC │      │  BUSINESS LOGIC │      │  BUSINESS LOGIC │
│                 │      │                 │      │                 │
│ commitTxn()     │      │ commitTxn()     │      │ commitTxn()     │
│ log("end")      │      │ log("end")      │      │ log("end")      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
     😩 copy-pasted           😩 copy-pasted           😩 copy-pasted
```

**With AOP:**

```
fetchEmployee()          updateEmployee()         deleteEmployee()
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│                 │      │                 │      │                 │
│  BUSINESS LOGIC │      │  BUSINESS LOGIC │      │  BUSINESS LOGIC │
│                 │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
         ↑                        ↑                        ↑
         └────────────────────────┴────────────────────────┘
                              LoggingAspect
                         ┌─────────────────────┐
                         │ log("start")        │
                         │ startTxn()          │
                         │ commitTxn()         │
                         │ log("end")          │
                         └─────────────────────┘
                    ✅ written ONCE, applied everywhere
```

---

## Key Terms as a Story

```
Your App                     AOP World
───────────────────────────────────────────────────────
                             ┌─────────────────────────┐
                             │        ASPECT           │
                             │  (the "where + what"    │
                             │   all in one place)     │
fetchEmployee() ──────────── │                         │
                             │  POINTCUT               │
"which methods               │  "match fetchEmployee   │
 to intercept?"              │   in EmployeeService"   │
                             │         +               │
"what to run?"               │  ADVICE                 │
                             │  "log before/after"     │
                             └─────────────────────────┘
                                         ↑
                             JOIN POINT = the exact moment
                             the real method is called
```

---

## Three Types of Advice

```
                    Your Method
                    fetchEmployee()
                         │
 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                         │
    @Before ────────►  [runs]
                         │
                    ┌────▼────┐
                    │  REAL   │
                    │ METHOD  │
                    └────┬────┘
                         │
    @After  ◄────────  [runs]
                         │
 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┼ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─

    @Around wraps BOTH sides — YOU must call proceed()
    ┌──────────────────────────────────────┐
    │  your code BEFORE                    │
    │       pjp.proceed() ← calls method  │
    │  your code AFTER                     │
    └──────────────────────────────────────┘
```

---

## Pointcut Cheat Sheet

```
POINTCUT TYPE      TARGETS                      EXAMPLE
────────────────────────────────────────────────────────────────────
execution        → a specific METHOD            execution(* com.example.*.*(..))
                                                         ↑  ↑         ↑
                                                  return  class  any args

within           → all methods in a CLASS       within(com.example.EmployeeUtil)

@annotation      → methods WITH an annotation   @annotation(GetMapping)

args             → methods by ARGUMENT TYPES    args(String, int)

target           → methods on a CLASS INSTANCE  target(com.example.EmployeeUtil)
                   (also works for interfaces)

@within          → all methods in classes       @within(Service)
                   WITH an annotation
```

### Wildcard Quick Reference

```
  *      matches any single item       → *(..))  any method name
  ..     matches zero or more items    → (..)    zero or more args
                                       → com.example..  any subpackage
```

---

## Combining Pointcuts

```
@Before("execution(* com.example..*(..))   &&   @within(RestController)")
         ────────────────────────────────        ──────────────────────
         any method in com.example package   AND  class has @RestController
```

```
@Before("within(com.example.A)   ||   within(com.example.B)")
         ─────────────────────         ─────────────────────
         all methods in class A    OR  all methods in class B
```

---

## How Spring AOP Works Internally

### Step 1 — App Startup

```
Spring starts
     │
     ├─► Scans for @Aspect classes
     │        └─► Parses & caches all pointcut expressions
     │
     ├─► Scans for @Component / @Service / @Controller beans
     │        └─► For each bean: does any pointcut match?
     │                   │
     │              YES  └─► Create a PROXY wrapping this bean
     │              NO       Keep the original bean as-is
     │
     └─► Spring container now holds PROXIES (not originals)
```

### Step 2 — Which Proxy Type?

```
Your class
     │
     ├── implements an Interface?
     │        YES ──► JDK Dynamic Proxy
     │                (Spring creates a class that implements the same interface)
     │
     └── NO interface?
              └──► CGLib Proxy
                   (Spring creates a SUBCLASS of your class)
```

```
CGLib example:

EmployeeUtil (your class)
     ↑
EmployeeUtil$$SpringCGLIB$$0  ← generated subclass (the proxy)
  overrides fetchEmployee() {
      // run advice chain
      super.fetchEmployee()   // calls your real method
      // run after advice
  }
```

### Step 3 — Method Call Flow

```
Your code calls:
  employeeUtil.fetchEmployee()
         │
         │  (Spring injected the PROXY, not the real object)
         ▼
  EmployeeUtil$$SpringCGLIB$$0.fetchEmployee()  ← proxy intercepts
         │
         ▼
  Advice Chain (list of matching advices)
  ┌─────────────────────────────────┐
  │  1. BeforeAdviceInterceptor     │──► runs @Before advice
  │         └── calls proceed()    │
  │  2. AfterAdviceInterceptor      │──► will run @After advice
  │         └── calls proceed()    │
  │  3. ACTUAL METHOD INVOKED  ◄───┘
  │         └── returns result     │
  │  (unwind) AfterAdvice runs     │
  └─────────────────────────────────┘
         │
         ▼
  Returns to your code
```

---

## Full Working Example

```java
// ─── 1. Your service (no AOP code here at all) ───────────────────
@Service
public class EmployeeService {
    public String fetchEmployee(int id) {
        System.out.println("Fetching employee " + id);
        return "John";
    }
}

// ─── 2. Your Aspect ──────────────────────────────────────────────
@Aspect
@Component
public class LoggingAspect {

    // Before: runs BEFORE the method
    @Before("execution(* com.example.EmployeeService.fetchEmployee(..))")
    public void logBefore() {
        System.out.println("[LOG] → entering fetchEmployee");
    }

    // After: runs AFTER the method (always, even if exception)
    @After("execution(* com.example.EmployeeService.fetchEmployee(..))")
    public void logAfter() {
        System.out.println("[LOG] → exiting fetchEmployee");
    }

    // Around: YOU control both sides
    @Around("execution(* com.example.EmployeeService.fetchEmployee(..))")
    public Object timeIt(ProceedingJoinPoint pjp) throws Throwable {
        long start = System.currentTimeMillis();
        Object result = pjp.proceed();           // ← calls real method
        long end = System.currentTimeMillis();
        System.out.println("[TIMER] took " + (end - start) + "ms");
        return result;
    }
}

// ─── Output when fetchEmployee(42) is called ─────────────────────
// [LOG] → entering fetchEmployee
// Fetching employee 42
// [LOG] → exiting fetchEmployee
// [TIMER] took 3ms
```

---

## Named Pointcut (Reuse an Expression)

```java
@Aspect
@Component
public class LoggingAspect {

    // Define once, reuse many times
    @Pointcut("execution(* com.example.EmployeeService.*(..))")
    public void employeeMethods() {}    // method body stays empty

    @Before("employeeMethods()")        // reuse by method name
    public void logBefore() { ... }

    @After("employeeMethods()")         // reuse again
    public void logAfter() { ... }
}
```

---

## Mental Model Summary

```
┌──────────────────────────────────────────────────────────────────┐
│                        YOUR APPLICATION                          │
│                                                                  │
│   Controller ──calls──► [PROXY] ──calls──► Real EmployeeService  │
│                            │                                     │
│                    Advice chain runs                             │
│                    (before/after/around)                         │
│                            │                                     │
│                     LoggingAspect                                │
│                     TransactionAspect                            │
│                     SecurityAspect                               │
│                            │                                     │
│              All defined ONCE, applied EVERYWHERE                │
└──────────────────────────────────────────────────────────────────┘
```

> **Golden rule:** If you see `@Transactional` or `@Cacheable` in Spring Boot — that's AOP working behind the scenes. Spring creates a proxy around your bean and weaves in transaction/cache logic automatically.
