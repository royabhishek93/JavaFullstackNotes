# Q4: AOP Execution Time Logging (Custom Annotation + @Around)

**Study Time:** 10-12 minutes | **Frequency:** 75% in interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## Scenario

You want to log execution time for selected methods **without** polluting business logic. You decide to use a custom annotation + Spring AOP.

---

## Key Principle

- A **custom annotation** marks methods to be timed.
- An **@Aspect** with **@Around** advice intercepts only those methods.
- `ProceedingJoinPoint.proceed()` runs the original method.
- The aspect logs duration before returning.

---

## Dependency

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>
```

---

## Class 1: Custom Annotation

```java
package com.example.annotation;

import java.lang.annotation.Documented;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface LogExecutionTime {
}
```

**Why:**
- `RUNTIME` retention so the aspect can read it
- `METHOD` target for method-level interception

---

## Class 2: Aspect

```java
package com.example.aspect;

import com.example.annotation.LogExecutionTime;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;

@Aspect
@Component
@Slf4j
public class ExecutionTimeAspect {

    @Around("@annotation(com.example.annotation.LogExecutionTime)")
    public Object logExecutionTime(ProceedingJoinPoint joinPoint) throws Throwable {
        long start = System.currentTimeMillis();

        Object result = joinPoint.proceed();

        long end = System.currentTimeMillis();

        log.info("Method {} executed in {} ms",
                joinPoint.getSignature(),
                (end - start));

        return result;
    }
}
```

**What happens:**
- `@Around` runs **before and after** the method
- `proceed()` executes the real method
- Time is logged after completion

---

## Class 3: Service Using the Annotation

```java
package com.example.service;

import com.example.annotation.LogExecutionTime;
import org.springframework.stereotype.Service;

@Service
public class UserService {

    @LogExecutionTime
    public void processUser() throws InterruptedException {
        Thread.sleep(2000);
        System.out.println("Processing user...");
    }
}
```

---

## Execution Flow

```
Method Call
   ↓
Spring AOP Proxy
   ↓
ExecutionTimeAspect (@Around)
   ↓
Start timer
   ↓
ProceedingJoinPoint.proceed()
   ↓
Stop timer
   ↓
Log execution time
```

---

## Variant 1: Using Spring StopWatch

```java
import org.springframework.util.StopWatch;

@Around("@annotation(com.example.annotation.LogExecutionTime)")
public Object logExecutionTime(ProceedingJoinPoint joinPoint) throws Throwable {
   StopWatch stopWatch = new StopWatch();
   stopWatch.start();

   Object result = joinPoint.proceed();

   stopWatch.stop();
   log.info("Method {} executed in {} ms",
         joinPoint.getSignature(),
         stopWatch.getTotalTimeMillis());

   return result;
}
```

**Why StopWatch:**
- Cleaner timing API
- Avoids manual start/end math

---

## Variant 2: Log Arguments and Return Value (Safely)

**Goal:** Avoid leaking secrets or logging huge payloads.

```java
@Around("@annotation(com.example.annotation.LogExecutionTime)")
public Object logExecutionTime(ProceedingJoinPoint joinPoint) throws Throwable {
   long start = System.currentTimeMillis();

   Object result = joinPoint.proceed();

   long end = System.currentTimeMillis();

   String args = safeArgs(joinPoint.getArgs());
   String ret = safeReturn(result);

   log.info("Method {} executed in {} ms | args={} | return={} ",
         joinPoint.getSignature(),
         (end - start), args, ret);

   return result;
}

private String safeArgs(Object[] args) {
   if (args == null || args.length == 0) {
      return "[]";
   }
   return Arrays.stream(args)
         .map(this::safeValue)
         .collect(Collectors.joining(", ", "[", "]"));
}

private String safeReturn(Object result) {
   return safeValue(result);
}

private String safeValue(Object value) {
   if (value == null) {
      return "null";
   }
   if (value instanceof CharSequence) {
      String s = value.toString();
      return s.length() > 200 ? s.substring(0, 200) + "..." : s;
   }
   return String.valueOf(value);
}
```

**Safe logging rules:**
- Redact secrets (passwords, tokens, PII)
- Truncate long strings
- Avoid logging large objects (DTOs, binary)

---

## Interview Q&A

### Q1: Why use @Around instead of @Before and @After?

**Answer:**
```
@Around gives full control and access to the return value.
It lets us run code before and after the method and measure time accurately.
```

---

### Q2: What does ProceedingJoinPoint do?

**Answer:**
```
It represents the intercepted method call.
Calling proceed() actually executes the target method.
```

---

### Q3: Why does the annotation need RUNTIME retention?

**Answer:**
```
The aspect reads annotations at runtime to decide which methods to intercept.
Without RUNTIME retention, the annotation is not visible to AOP.
```

---

### Q4: Will private methods be intercepted?

**Answer:**
```
No. Spring AOP uses proxies, so only public/protected methods
invoked through the proxy are intercepted. Private methods are not.
```

---

## Common Pitfalls

```java
❌ Pitfall 1: Missing spring-boot-starter-aop
// Aspect not activated

❌ Pitfall 2: Annotation retention not RUNTIME
// Aspect never sees the annotation

❌ Pitfall 3: Calling method inside same class
// Self-invocation bypasses proxy
```

---

## Interview Answer (Concise)

**Q: "How do you log method execution time using AOP?"**

**Answer:**

> "I create a custom annotation with runtime retention, build an `@Aspect` with `@Around` advice that targets methods annotated with that annotation, and measure time before and after `ProceedingJoinPoint.proceed()`. The aspect logs execution time and keeps performance logging separate from business logic."

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| Custom annotation | Clean, selective interception | ⭐⭐⭐⭐⭐ |
| @Around advice | Precise timing | ⭐⭐⭐⭐⭐ |
| ProceedingJoinPoint | Executes target method | ⭐⭐⭐⭐ |
| Proxy behavior | Explains interception limits | ⭐⭐⭐⭐ |
| Separation of concerns | Cleaner business logic | ⭐⭐⭐⭐ |
