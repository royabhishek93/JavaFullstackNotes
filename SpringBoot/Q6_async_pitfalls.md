# Q6: @Async Pitfalls — Self-Invocation, Thread Pool Config, Exception Handling (Architect Guide)

**Study Time:** 15-20 minutes | **Frequency:** 80% in architect interviews 🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

---

## Why This Matters in Production

`@Async` looks simple but has 4 silent failure modes that cause production incidents:
1. Self-invocation bypasses the proxy → runs synchronously, no one notices
2. Default thread pool is unbounded → OutOfMemoryError under load
3. Exceptions in async methods are swallowed silently
4. `@Async` + `@Transactional` combination is misunderstood

---

## How @Async Works (The Proxy Mechanism)

```
HTTP Thread
    ↓
Spring Proxy (wraps YourService)
    ↓ intercepts asyncMethod() call
TaskExecutor
    ↓ submits runnable to thread pool
Returns immediately to HTTP thread ✅

Thread pool thread → runs actual method body
```

**Enabling @Async:**

```java
@SpringBootApplication
@EnableAsync   // REQUIRED — without this, @Async is completely ignored (no error thrown!)
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

---

## Pitfall 1: Self-Invocation (Silent Synchronous Execution)

### The Bug

```java
@Service
public class EmailService {

    public void processOrder(Order order) {
        // Direct call — bypasses Spring proxy
        this.sendConfirmationEmail(order); // RUNS SYNCHRONOUSLY ❌
        // No error thrown, no warning — just silently not async
    }

    @Async
    public void sendConfirmationEmail(Order order) {
        // You think this runs in a new thread — it does NOT
        emailClient.send(order.getEmail(), buildTemplate(order));
    }
}
```

### Why It Breaks

```
HTTP Thread
    ↓
Spring Proxy (wraps EmailService)
    ↓ processOrder() called — proxy intercepts
Real EmailService.processOrder()
    ↓ this.sendConfirmationEmail() — direct call, skips proxy ❌
Real EmailService.sendConfirmationEmail() — runs in HTTP thread, BLOCKING
```

### Fix: Separate Bean or Self-Injection

```java
// Option 1 (preferred): Extract to separate @Service
@Service
public class EmailService {
    @Autowired
    private EmailSender emailSender; // separate bean

    public void processOrder(Order order) {
        emailSender.sendConfirmationEmail(order); // goes through proxy ✅
    }
}

@Service
public class EmailSender {
    @Async
    public void sendConfirmationEmail(Order order) {
        emailClient.send(order.getEmail(), buildTemplate(order));
    }
}

// Option 2: Self-injection
@Service
public class EmailService {
    @Autowired
    private EmailService self; // Spring injects the proxy

    public void processOrder(Order order) {
        self.sendConfirmationEmail(order); // goes through proxy ✅
    }

    @Async
    public void sendConfirmationEmail(Order order) {
        emailClient.send(order.getEmail(), buildTemplate(order));
    }
}
```

---

## Pitfall 2: Default Thread Pool is Unbounded (OOM Under Load)

### The Problem

Without configuration, Spring uses `SimpleAsyncTaskExecutor`:
- Creates a **new thread for every single @Async call**
- No queue, no pool, no limits
- Under load: thousands of threads → OutOfMemoryError

```java
// This looks fine but creates a new thread for EVERY order email
@Async
public void sendConfirmationEmail(Order order) { ... }

// Under Black Friday traffic: 50,000 orders/minute
// = 50,000 new threads/minute
// = JVM crash
```

### Fix: Configure a Proper ThreadPoolTaskExecutor

```java
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {

    @Override
    @Bean(name = "emailTaskExecutor")
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();

        executor.setCorePoolSize(5);          // Always-alive threads
        executor.setMaxPoolSize(20);          // Max threads under load
        executor.setQueueCapacity(100);       // Queue before creating new threads
        executor.setKeepAliveSeconds(60);     // Idle thread lifetime
        executor.setThreadNamePrefix("email-async-"); // For logs/monitoring
        executor.setRejectedExecutionHandler(
            new ThreadPoolExecutor.CallerRunsPolicy() // Fallback: run in caller thread
        );
        executor.initialize();
        return executor;
    }
}

// Use the named executor
@Async("emailTaskExecutor")
public void sendConfirmationEmail(Order order) {
    emailClient.send(order.getEmail(), buildTemplate(order));
}
```

### Thread Pool Sizing Formula

```
For I/O-bound tasks (HTTP calls, DB, email):
  corePoolSize  = number of CPU cores × 2
  maxPoolSize   = number of CPU cores × 4
  queueCapacity = max expected burst size

For CPU-bound tasks:
  corePoolSize  = number of CPU cores
  maxPoolSize   = number of CPU cores + 1
  queueCapacity = 0 (no queue — reject immediately if busy)
```

### Multiple Executors for Different Workloads

```java
@Configuration
@EnableAsync
public class AsyncConfig {

    @Bean(name = "emailExecutor")
    public Executor emailExecutor() {
        ThreadPoolTaskExecutor e = new ThreadPoolTaskExecutor();
        e.setCorePoolSize(10); e.setMaxPoolSize(50); e.setQueueCapacity(500);
        e.setThreadNamePrefix("email-");
        e.initialize(); return e;
    }

    @Bean(name = "reportExecutor")
    public Executor reportExecutor() {
        ThreadPoolTaskExecutor e = new ThreadPoolTaskExecutor();
        e.setCorePoolSize(2); e.setMaxPoolSize(5); e.setQueueCapacity(10);
        e.setThreadNamePrefix("report-");
        e.initialize(); return e;
    }
}

@Async("emailExecutor")
public void sendEmail(Order order) { ... }

@Async("reportExecutor")
public void generateReport(Long reportId) { ... }
```

---

## Pitfall 3: Exceptions Are Silently Swallowed

### The Problem

```java
@Async
public void sendConfirmationEmail(Order order) {
    // This exception disappears — no stack trace, no log, no alert
    throw new RuntimeException("SMTP server down");
}

// Caller sees nothing:
emailService.sendConfirmationEmail(order); // returns immediately, no exception
```

### Why: @Async returns void or Future — exceptions go nowhere

```
Thread pool thread throws RuntimeException
    ↓
No one is waiting for this thread
    ↓
Exception is handed to UncaughtExceptionHandler
    ↓
Default: prints to stderr — easy to miss in production logs
```

### Fix 1: Implement AsyncUncaughtExceptionHandler

```java
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {

    @Override
    public AsyncUncaughtExceptionHandler getAsyncUncaughtExceptionHandler() {
        return (throwable, method, params) -> {
            log.error("Async method {} threw exception: {}", method.getName(), throwable.getMessage(), throwable);
            // Send to alerting system, Sentry, PagerDuty, etc.
            alertingService.sendAlert("Async failure: " + method.getName(), throwable);
        };
    }
}
```

### Fix 2: Return CompletableFuture and Handle the Exception

```java
@Async("emailExecutor")
public CompletableFuture<Void> sendConfirmationEmail(Order order) {
    try {
        emailClient.send(order.getEmail(), buildTemplate(order));
        return CompletableFuture.completedFuture(null);
    } catch (Exception e) {
        log.error("Email failed for order {}", order.getId(), e);
        return CompletableFuture.failedFuture(e);
    }
}

// Caller can now handle the failure:
emailService.sendConfirmationEmail(order)
    .exceptionally(ex -> {
        log.warn("Email skipped, order {} still completes", order.getId());
        return null;
    });
```

### Fix 3: Try-catch inside @Async (simplest for fire-and-forget)

```java
@Async("emailExecutor")
public void sendConfirmationEmail(Order order) {
    try {
        emailClient.send(order.getEmail(), buildTemplate(order));
    } catch (Exception e) {
        log.error("Failed to send email for order {}: {}", order.getId(), e.getMessage(), e);
        // Store in failed_notifications table for retry
        failedNotificationRepo.save(new FailedNotification(order.getId(), e.getMessage()));
    }
}
```

---

## Pitfall 4: @Async + @Transactional Combination

### The Misunderstanding

```java
@Async
@Transactional
public void processAsync(Long orderId) {
    // This DOES work — each async invocation gets its own TX
    // BUT: the caller's TX is NOT propagated to this async thread
    Order order = orderRepo.findById(orderId).orElseThrow();
    order.setStatus("PROCESSED");
    orderRepo.save(order);
}
```

### What Happens

```
HTTP Thread (TX1 active)
    ↓
calls processAsync() — returns immediately
    ↓
Thread pool thread (NEW thread, NO TX from caller)
    ↓
@Transactional creates NEW TX (TX2) on this thread
    ↓
TX2 commits when method finishes
```

### The Bug: LazyInitializationException

```java
@Transactional  // TX1 on HTTP thread
public void placeOrder(Long orderId) {
    Order order = orderRepo.findById(orderId).orElseThrow();
    // order.getItems() is LAZY — works here because TX1 is open

    asyncService.processItems(order); // passes managed entity to async thread
}

@Async
@Transactional  // TX2 on new thread
public void processItems(Order order) {
    order.getItems(); // LazyInitializationException ❌
    // TX1 is closed. The entity is detached. No session open in this thread.
}
```

### Fix: Pass IDs not Entities

```java
// WRONG: pass entity
asyncService.processItems(order);

// RIGHT: pass ID, reload in async method
asyncService.processItems(order.getId());

@Async
@Transactional
public void processItems(Long orderId) {
    Order order = orderRepo.findById(orderId).orElseThrow(); // fresh load ✅
    order.getItems().forEach(this::processItem);
}
```

---

## Production Architecture Pattern: Reliable Async Processing

For critical async work (emails, notifications, reports), fire-and-forget @Async is risky. The production pattern:

```
HTTP Thread
    ↓
Save task to DB (in same @Transactional as business logic)
    ↓ commit

Background scheduler / Outbox processor
    ↓
Poll DB for pending tasks
    ↓
Execute via @Async with retry logic
    ↓
Mark complete / failed in DB
```

This ensures:
- Task is never lost if app crashes between submit and execution
- Failed tasks are retried
- Full audit trail

---

## Interview Cheat Sheet

```
@Async Pitfall 1 — Self-invocation:
  this.asyncMethod() bypasses proxy → runs synchronously, no error.
  Fix: separate @Service bean.

@Async Pitfall 2 — Default thread pool:
  SimpleAsyncTaskExecutor creates new thread per call → OOM under load.
  Fix: configure ThreadPoolTaskExecutor with core/max/queue settings.

@Async Pitfall 3 — Silent exceptions:
  void @Async methods swallow exceptions.
  Fix: implement AsyncUncaughtExceptionHandler OR return CompletableFuture.

@Async Pitfall 4 — @Transactional interaction:
  Caller's TX is never propagated to async thread.
  Never pass lazy JPA entities to @Async methods — pass IDs instead.

@EnableAsync is REQUIRED — without it @Async is completely ignored, no error.
```

---

## Key Architect Questions

**Q: What happens if you forget @EnableAsync?**
@Async annotations are silently ignored. Methods run synchronously. No error, no warning. Discovered only in production when performance doesn't improve.

**Q: How do you ensure an async task completes before the JVM shuts down?**
Configure `executor.setWaitForTasksToCompleteOnShutdown(true)` and `executor.setAwaitTerminationSeconds(30)`. Also tie to Spring's `SmartLifecycle` for graceful shutdown.

```java
executor.setWaitForTasksToCompleteOnShutdown(true);
executor.setAwaitTerminationSeconds(30);
```

**Q: Can @Async propagate SecurityContext (logged-in user) to the new thread?**
Not by default. Spring Security's `SecurityContext` is `ThreadLocal` — new thread gets empty context.
Fix: configure `DelegatingSecurityContextAsyncTaskExecutor`.

```java
@Bean
public Executor securityAwareExecutor() {
    return new DelegatingSecurityContextAsyncTaskExecutor(taskExecutor());
}
```

**Q: @Async vs @Scheduled — what's the difference?**
- `@Async`: triggered by a caller, runs in pool thread
- `@Scheduled`: triggered by time (cron/fixedRate), runs in single-threaded scheduler by default
- Both share the proxy problem (self-invocation breaks both)

**Q: How do you test @Async methods?**
Use `CompletableFuture` return type + `.get()` in tests, or configure a `SyncTaskExecutor` in test context to run async methods synchronously.
