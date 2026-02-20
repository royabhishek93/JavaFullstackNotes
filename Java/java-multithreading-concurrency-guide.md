# Java Multithreading & Concurrency - Complete Guide 2026

**Single Comprehensive Resource for Senior Interviews**

---

## 📋 Table of Contents

1. [Core Concepts](#core-concepts)
2. [Non-Blocking vs Async](#non-blocking-async)
3. [Thread Types & Execution Models](#thread-types)
4. [Executor Framework](#executor-framework)
5. [CompletableFuture](#completablefuture)
6. [Concurrency Utilities](#concurrency-utilities)
7. [Thread Safety Strategies](#thread-safety)
8. [Race Conditions & Deadlocks](#race-deadlock)
9. [Performance Tuning](#performance-tuning)
10. [Virtual Threads (Java 21+)](#virtual-threads)
11. [Spring Boot Integration](#spring-boot)
12. [Interview Questions](#interview-qa)

---

## 🔥 Core Concepts {#core-concepts}

### Thread Lifecycle & States

```java
// Thread states: NEW → RUNNABLE → BLOCKED/WAITING/TIMED_WAITING → TERMINATED

Thread t = new Thread(() -> System.out.println("Running"));
// NEW state

t.start();
// RUNNABLE - now eligible to run

synchronized(lock) {
    t.join();  // t is now WAITING on current thread
}

// When done, TERMINATED
```

**States Explained:**
- `NEW` - Thread created but not started
- `RUNNABLE` - Ready to run or running
- `BLOCKED` - Waiting to acquire a lock
- `WAITING` - Waiting indefinitely for another thread
- `TIMED_WAITING` - Waiting with a timeout
- `TERMINATED` - Thread execution complete

---

## 🎯 Non-Blocking vs Async {#non-blocking-async}

### MUST KNOW: The Fundamental Difference

| Aspect | Async with Thread Pool | Non-Blocking (Reactive) |
|--------|----------------------|------------------------|
| **Blocks thread?** | ✅ Yes (in thread pool) | ❌ No |
| **Resource usage** | ⚠️ 1 OS thread per request | ✅ Shared event loop |
| **Scalability** | Limited (pool size) | Massive (1000s) |
| **Technology** | Apache HttpClient | WebClient (Netty) |
| **Used when** | Traditional async I/O | High-concurrency APIs |

### Async with Thread Pool (Apache HttpClient)

```java
// ❌ Main thread is freed, but thread pool thread is blocked
AsyncHttpClient client = new AsyncHttpClient();

ListenableFuture<Response> future = client.prepareGet("http://api.com/data")
    .execute();

future.addListener(() -> {
    // Callback runs in thread pool
    Response response = future.get();
    System.out.println(response.getBody());
}, executor);

// Main thread continues immediately
System.out.println("Request sent, not waiting");
```

**What Happens:**
- Main thread is freed ✅
- Thread pool thread **waits for response** ❌
- If 200 requests and pool size = 100, the extra 100 must wait
- Scales only as much as thread pool allows

### Non-Blocking (WebClient with Netty)

```java
// ✅ No threads blocked at all
webClient.post()
    .uri("http://payment-service/pay")
    .bodyValue(paymentRequest)
    .retrieve()
    .bodyToMono(PaymentResponse.class)
    // Callback is registered, not executed immediately
    .subscribe(response -> {
        System.out.println("Payment: " + response.getAmount());
    });

// Main thread continues
System.out.println("Request sent, not waiting");
```

**What Happens:**
- Request sent through Netty event loop
- **No thread waits** ✅
- Event loop handles event when response arrives
- Can handle 1000s with just a few threads

---

### Why WebClient is Non-Blocking

**Step 1: Event Loop Registration**
```
webClient.post(...).subscribe(...)
           ↓
      Netty Event Loop registers callback
      (like a traffic signal waiting for car)
```

**Step 2: Non-Blocking I/O**
```
Netty opens TCP connection (doesn't wait)
Sends HTTP request
Continues handling other connections
```

**Step 3: When Response Arrives**
```
OS notifies Netty: "data ready"
Event loop triggers callback
Continues Reactor chain (map, filter, etc.)
```

**Result:** One event loop thread handles 1000s of concurrent requests by reacting to events.

---

### Backpressure - Handling 1000s of Responses

```java
// Reactive operators request only what they can handle
webClient.get()
    .uri("/api/items")
    .retrieve()
    .bodyToFlux(Item.class)
    .buffer(100)  // Handle 100 at a time
    .subscribe(items -> {
        processItems(items);  // Process only when ready
    });

// Internally: request(100) mechanism prevents memory overflow
```

**Key Concept:**
- Publisher waits for subscriber to ask for more
- Prevents "pulling too much" and crashing
- Like buffering in a pipe — let water flow when drain is open

---

## 🧵 Thread Types & Execution Models {#thread-types}

### EventLoop Thread (Netty)

```
🔁 Infinite loop handling I/O events
   ├─ Read from socket
   ├─ Write to socket
   ├─ Connect/Disconnect
   └─ Repeat...

One thread handles 1000s of connections!
```

**Code Example:**
```java
EventLoopGroup bossGroup = new NioEventLoopGroup(1);  // 1 thread!

// This 1 thread handles ALL incoming connections
ServerBootstrap server = new ServerBootstrap()
    .group(bossGroup)
    .channel(NioServerSocketChannel.class)
    .childHandler(new ChannelInitializer<SocketChannel>() {
        @Override
        protected void initChannel(SocketChannel ch) {
            ch.pipeline().addLast(new MyHandler());
        }
    });
```

**⚠️ Critical Rule:** Never block event loop threads!
```java
// ❌ WRONG - Blocks event loop, entire system hangs
eventLoop.execute(() -> {
    Thread.sleep(1000);  // Don't do this!
    database.query();    // Don't do this!
});

// ✅ RIGHT - Offload to separate executor
eventLoop.execute(() -> {
    executor.submit(() -> {
        database.query();  // Safe, separate thread
    });
});
```

---

### Traditional Threads (ExecutorService)

```
🔃 One thread per task (or from pool)
   ├─ Can block safely
   ├─ Can sleep, wait, join
   └─ Expensive - limited to pool size
```

**Code Example:**
```java
ExecutorService executor = Executors.newFixedThreadPool(100);

executor.submit(() -> {
    Thread.sleep(5000);  // OK - thread waits
    database.query();    // OK - thread can block
});
```

**Trade-off:** Easy to write blocking code, but limited scalability.

---

### Virtual Threads (Java 21+, Project Loom)

```
🧵 Lightweight threads - feel like normal threads
   ├─ Can block (JVM handles underlying)
   ├─ Extremely cheap to create
   └─ Perfect for I/O-heavy apps
```

**Code Example:**
```java
// Create 1 million virtual threads without cratering the app
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();

for (int i = 0; i < 1_000_000; i++) {
    executor.submit(() -> {
        Thread.sleep(5000);  // Blocking, but JVM suspends instead of blocking OS thread
        api.call();
    });
}
```

**Result:** Write like traditional threads, perform like reactive!

---

### Comparison Table

| Aspect | EventLoop | Traditional Thread | Virtual Thread |
|--------|-----------|-------------------|-----------------|
| **Blocking OK?** | ❌ No | ✅ Yes | ✅ Yes |
| **Max concurrency** | 1000s | Limited (pool) | 1000s |
| **Memory per task** | Minimal | ~1MB | ~1KB |
| **Created as needed** | ❌ Fixed count | ❌ From pool | ✅ Yes |
| **Easy to reason** | ❌ Complex | ✅ Yes | ✅ Yes |
| **Used in** | Netty, WebClient | Executors | Spring 6, Java 21+ |

---

## ⚙️ Executor Framework {#executor-framework}

### ExecutorService Basics

```java
// Create thread pool
ExecutorService executor = Executors.newFixedThreadPool(10);

// Submit task (Runnable - no result)
executor.submit(() -> System.out.println("Task running"));

// Submit task with result (Callable)
Future<String> future = executor.submit(() -> "Order validated");

// ⚠️ Blocking call - waits for result
String result = future.get();

// Proper cleanup
executor.shutdown();
executor.awaitTermination(5, TimeUnit.SECONDS);
```

### Real-World: Order Processing Pipeline

```java
public class OrderService {
    private ExecutorService executor = Executors.newFixedThreadPool(10);
    
    public void processOrder(Order order) {
        // Run 3 checks in parallel
        Future<Boolean> inventoryCheck = executor.submit(
            () -> checkInventory(order)
        );
        
        Future<Boolean> paymentCheck = executor.submit(
            () -> validatePayment(order)
        );
        
        Future<Boolean> fraudCheck = executor.submit(
            () -> detectFraud(order)
        );
        
        // Wait for all
        try {
            boolean inv = inventoryCheck.get();
            boolean pay = paymentCheck.get();
            boolean fraud = fraudCheck.get();
            
            if (inv && pay && !fraud) {
                order.confirm();
            }
        } catch (InterruptedException | ExecutionException e) {
            order.reject();
        }
    }
}
```

**⚠️ Limitation:** `future.get()` is blocking — not ideal for high throughput.

---

### ThreadPoolExecutor Tuning

```java
// Better control than Executors factory methods
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    10,                              // core threads (always alive)
    50,                              // max threads (when queue is full)
    60, TimeUnit.SECONDS,            // timeout for excess threads
    new LinkedBlockingQueue<>(100),  // bounded queue
    new ThreadPoolExecutor.AbortPolicy()  // reject when full
);

// Monitor
System.out.println("Active: " + executor.getActiveCount());
System.out.println("Queued: " + executor.getQueue().size());
```

**Rejection Policies:**
- `AbortPolicy` - throw exception (prevents memory issues)
- `CallerRunsPolicy` - run in caller thread (backpressure)
- `DiscardPolicy` - silently drop task (risky)
- `DiscardOldestPolicy` - drop oldest task (risky)

---

## 🔗 CompletableFuture {#completablefuture}

### MUST KNOW: Non-Blocking Chaining

```java
// ✅ Non-blocking - attaches callback, doesn't wait
CompletableFuture.supplyAsync(() -> getPrice())
    .thenApply(price -> price * 0.9)  // 10% discount
    .thenAccept(discountedPrice ->
        System.out.println("Final: ₹" + discountedPrice)
    );

System.out.println("Main thread continues (not blocked!)");
```

**Key Difference:**
```java
// ❌ Blocking
Future<Double> future = executor.submit(() -> getPrice());
Double price = future.get();  // BLOCKS here

// ✅ Non-blocking
CompletableFuture<Double> future = CompletableFuture.supplyAsync(() -> getPrice());
future.thenAccept(System.out::println);  // No blocking
```

---

### Real-World: Flipkart Order Flow

```java
public CompletableFuture<OrderConfirmation> processOrderAsync(Order order) {
    // Start 3 async tasks
    CompletableFuture<Boolean> inventoryFuture = CompletableFuture
        .supplyAsync(() -> checkInventory(order));
    
    CompletableFuture<Boolean> paymentFuture = CompletableFuture
        .supplyAsync(() -> validatePayment(order));
    
    CompletableFuture<Boolean> fraudFuture = CompletableFuture
        .supplyAsync(() -> detectFraud(order));
    
    // Combine all results
    return CompletableFuture.allOf(inventoryFuture, paymentFuture, fraudFuture)
        .thenApply(v -> {
            boolean inv = inventoryFuture.join();
            boolean pay = paymentFuture.join();
            boolean fraud = fraudFuture.join();
            
            if (inv && pay && !fraud) {
                return new OrderConfirmation(order.getId(), "APPROVED");
            } else {
                return new OrderConfirmation(order.getId(), "REJECTED");
            }
        })
        .exceptionally(ex -> {
            log.error("Order processing failed", ex);
            return new OrderConfirmation(order.getId(), "ERROR");
        });
}
```

**Usage in REST Controller:**
```java
@PostMapping("/orders")
public CompletableFuture<OrderConfirmation> createOrder(@RequestBody Order order) {
    return orderService.processOrderAsync(order);
    // Spring automatically waits for CompletableFuture before sending response
}
```

---

### CompletableFuture Methods Cheatsheet

| Method | Blocking? | Use When |
|--------|-----------|----------|
| `thenAccept()` | ❌ No | Handle result (no return) |
| `thenApply()` | ❌ No | Transform result |
| `whenComplete()` | ❌ No | Handle success/failure |
| `thenCombine()` | ❌ No | Combine 2 futures |
| `allOf()` | ❌ No | Wait for multiple futures |
| `get()` | ✅ Yes | Block and get result |
| `join()` | ✅ Yes | Block and get result |

---

## 🛠️ Concurrency Utilities {#concurrency-utilities}

### CountDownLatch - Wait for Multiple Tasks

```java
// Start 3 config loaders in parallel
CountDownLatch latch = new CountDownLatch(3);

new Thread(() -> {
    loadDatabase();
    latch.countDown();  // Done with DB
}).start();

new Thread(() -> {
    loadCache();
    latch.countDown();  // Done with cache
}).start();

new Thread(() -> {
    loadConfig();
    latch.countDown();  // Done with config
}).start();

// Main thread waits until all 3 are done
latch.await();
System.out.println("All configs loaded, start the app");

// Application continues
startApplication();
```

**Key:** Count-down is one-time (can't reuse).

---

### CyclicBarrier - Sync Multiple Threads Repeatedly

```java
// Process data in phases - all threads must sync at each phase
int numThreads = 5;
CyclicBarrier barrier = new CyclicBarrier(numThreads, () -> {
    System.out.println("--- Phase complete, starting next phase ---");
    commitBatch();
});

for (int i = 0; i < numThreads; i++) {
    new Thread(() -> {
        for (int phase = 0; phase < 10; phase++) {
            processChunk();        // Process
            barrier.await();       // Wait for all threads
        }
    }).start();
}
```

**Key:** Reusable barrier (cycles through), unlike CountDownLatch.

---

### Semaphore - Limit Concurrent Access

```java
// Rate limiting: Allow only 10 concurrent API calls
Semaphore semaphore = new Semaphore(10);

for (int i = 0; i < 100; i++) {
    executor.submit(() -> {
        try {
            semaphore.acquire();  // Wait if 10 threads already running
            callPaymentAPI();      // Max 10 concurrent calls
        } finally {
            semaphore.release();   // Free up a slot
        }
    });
}
```

**Use Cases:**
- Rate limiting to 3rd-party APIs
- Connection pool limits
- Resource access control

---

### ThreadLocal - Per-Thread Storage

```java
// Store request ID in thread-local for logging/tracing
public class RequestContext {
    private static final ThreadLocal<String> requestId = new ThreadLocal<>();
    
    public static void set(String id) {
        requestId.set(id);
    }
    
    public static String get() {
        return requestId.get();
    }
    
    public static void clear() {
        requestId.remove();  // IMPORTANT: prevent memory leak
    }
}

// In Spring Filter
@Override
protected void doFilterInternal(HttpServletRequest request, ...) {
    String id = UUID.randomUUID().toString();
    RequestContext.set(id);
    try {
        filterChain.doFilter(request, response);
    } finally {
        RequestContext.clear();  // Always clear
    }
}

// In Service - no need to pass requestId everywhere
public void processOrder(Order order) {
    log.info("Processing order with requestId: {}", RequestContext.get());
    // requestId is available in all called methods
}
```

**⚠️ Critical:** Always call `clear()` in finally block, especially in thread pools!

---

## 🔐 Thread Safety Strategies {#thread-safety}

### MUST KNOW: Shared Mutable State is Dangerous

```java
// ❌ Not thread-safe
private int counter = 0;

public void increment() {
    counter++;  // Read, modify, write - not atomic!
}

// ⚠️ Problem: Two threads can read same value before either writes
// T1: reads 0, increments to 1
// T2: reads 0, increments to 1  (should be 2!)
```

---

### Strategy 1: Synchronization

```java
private int counter = 0;

// Coarse-grained: entire method synchronized
public synchronized void increment() {
    counter++;
}

// Fine-grained: only critical section
public void incrementFine() {
    synchronized(this) {
        counter++;
    }
}
```

**Trade-off:** Safe but can be slow (contention).

---

### Strategy 2: Atomic Variables (Best for Counters)

```java
private AtomicInteger counter = new AtomicInteger(0);

public void increment() {
    counter.incrementAndGet();  // Atomic operation
}

// Get current value
int current = counter.get();

// Compound operations
counter.compareAndSet(expected, newValue);  // CAS operation
```

**Advantage:** Lock-free, better performance under contention.

---

### Strategy 3: Volatile (For Flags)

```java
private volatile boolean running = true;

public void stop() {
    running = false;  // Visible to all threads immediately
}

public void run() {
    while (running) {
        doWork();
    }
}
```

**Use:** Configuration flags, feature toggles, shutdown signals.

**Key:** `volatile` ensures visibility but NOT atomicity.

---

### Strategy 4: ConcurrentHashMap (For Collections)

```java
// ❌ NOT thread-safe
Map<String, String> map = new HashMap<>();

// ✅ Thread-safe (segment-based locking)
Map<String, String> map = new ConcurrentHashMap<>();

map.put("order_id", "12345");
String value = map.get("order_id");

// Atomic compound operations
map.putIfAbsent("order_id", "12345");
```

**Advantage:** Concurrent reads (only conflicting writes are synchronized).

---

### Strategy 5: Immutability

```java
// ✅ Thread-safe by design
public final class OrderSummary {
    private final String orderId;
    private final double totalAmount;
    private final List<Item> items;
    
    // Immutable objects never need synchronization
    public OrderSummary(String orderId, double totalAmount, List<Item> items) {
        this.orderId = orderId;
        this.totalAmount = totalAmount;
        this.items = Collections.unmodifiableList(items);
    }
}
```

**Best Practice:** Prefer immutability when possible.

---

### Volatile vs AtomicInteger (Comparison)

| Aspect | Volatile | AtomicInteger |
|--------|----------|---------------|
| **Use For** | Flags, signals | Counters, IDs |
| **Thread-safe write** | ✅ Yes | ✅ Yes |
| **Thread-safe read** | ✅ Yes | ✅ Yes |
| **Compound ops** | ❌ No | ✅ Yes (increment, CAS) |
| **Performance** | Very fast | Fast (lock-free) |
| **Memory overhead** | Minimal | Minimal |

```java
// ❌ WRONG - volatile doesn't guarantee atomicity
private volatile int counter = 0;
counter++;  // Not atomic! (read + modify + write)

// ✅ CORRECT - atomic guarantees atomicity
private AtomicInteger counter = new AtomicInteger(0);
counter.incrementAndGet();  // Atomic!
```

---

## 💥 Race Conditions & Deadlocks {#race-deadlock}

### Race Condition Example

```java
class InventoryService {
    private int stock = 1;
    
    // ❌ Race condition during flash sale
    public void purchase() {
        if (stock > 0) {
            stock--;
        }
    }
}

// Two threads buy simultaneously
// T1: reads stock=1, enters if
// T2: reads stock=1, enters if (still sees 1!)
// T1: sets stock=0
// T2: sets stock=0  (should be -1, but both read 1!)
```

**Solution:**
```java
public synchronized void purchase() {  // ✅ Synchronized
    if (stock > 0) {
        stock--;
    }
}
```

---

### Deadlock Example

```java
public class PaymentOrderDeadlock {
    private Object paymentLock = new Object();
    private Object orderLock = new Object();
    
    public void processPayment() {
        synchronized(paymentLock) {
            Thread.sleep(100);
            synchronized(orderLock) {  // Waits for orderLock
                // ...
            }
        }
    }
    
    public void processOrder() {
        synchronized(orderLock) {
            Thread.sleep(100);
            synchronized(paymentLock) {  // Waits for paymentLock
                // ...
            }
        }
    }
}

// T1: holds paymentLock, waits for orderLock
// T2: holds orderLock, waits for paymentLock
// → DEADLOCK!
```

**Prevention:**
```java
// ✅ Always acquire locks in same order
public void processPayment() {
    synchronized(paymentLock) {          // *First* always
        synchronized(orderLock) {        // *Second* always
            // Safe - consistent ordering
        }
    }
}

public void processOrder() {
    synchronized(paymentLock) {          // *First* always
        synchronized(orderLock) {        // *Second* always
            // Safe - consistent ordering
        }
    }
}
```

**Alternative: Use tryLock with timeout**
```java
Lock lock1 = new ReentrantLock();
Lock lock2 = new ReentrantLock();

if (lock1.tryLock(1, TimeUnit.SECONDS)) {
    try {
        if (lock2.tryLock(1, TimeUnit.SECONDS)) {
            try {
                // safe logic
            } finally {
                lock2.unlock();
            }
        }
    } finally {
        lock1.unlock();
    }
}
```

---

### Starvation - Low-Priority Thread Never Runs

```java
// ❌ Unfair lock - same thread can acquire repeatedly
ReentrantLock unfairLock = new ReentrantLock(false);

// ✅ Fair lock - threads acquire in order
ReentrantLock fairLock = new ReentrantLock(true);

// Use fair lock to prevent starvation
public void criticalSection() {
    fairLock.lock();
    try {
        // All threads get fair chance
    } finally {
        fairLock.unlock();
    }
}
```

---

## 📈 Performance Tuning {#performance-tuning}

### Thread Pool Sizing

```java
// CPU-intensive tasks: pool size = number of CPU cores
int cpus = Runtime.getRuntime().availableProcessors();
ExecutorService cpuBound = Executors.newFixedThreadPool(cpus);

// I/O-intensive tasks: pool size = (cores * 2) or (cores * (1 + I/O_time / CPU_time))
int ioIntensive = cpus * 2;
ExecutorService ioBound = Executors.newFixedThreadPool(ioIntensive);

// Or better: use bounded queue to avoid memory issues
ThreadPoolExecutor executor = new ThreadPoolExecutor(
    cpus,                          // core
    cpus * 2,                      // max
    60, TimeUnit.SECONDS,
    new ArrayBlockingQueue<>(100), // bounded!
    new ThreadPoolExecutor.AbortPolicy()
);
```

### Monitoring

```java
// Spring Boot Actuator (auto-configured)
// Endpoint: /actuator/metrics/executor.active

// Or JMX
MBeanServer server = ManagementFactory.getPlatformMBeanServer();
ThreadMXBean threadBean = ManagementFactory.getThreadMXBean();

System.out.println("Active threads: " + threadBean.getThreadCount());
System.out.println("Peak threads: " + threadBean.getPeakThreadCount());
```

### Avoiding Contention

```java
// ❌ Hot spot - all threads updating same counter
AtomicInteger sharedCounter = new AtomicInteger();
sharedCounter.incrementAndGet();

// ✅ LongAdder - better under high contention
LongAdder counter = new LongAdder();
counter.increment();
long total = counter.sum();
```

---

## 🧵 Virtual Threads (Java 21+) {#virtual-threads}

### Why Virtual Threads Matter

```java
❌ Old (1M traditional threads):
   └─ 1M OS threads × 1MB each = 1GB RAM + massive context switching

✅ New (1M virtual threads):
   └─ 1M virtual threads ≈ 100MB RAM + minimal context switching
```

### Usage Example

```java
// Create virtual threads on demand
ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();

for (int i = 0; i < 1_000_000; i++) {
    executor.submit(() -> {
        // Can use blocking code - JVM handles suspension
        Thread.sleep(1000);
        callExternalAPI();
    });
}
```

### Real-World: Payment Gateway Integration

```java
public List<PaymentResult> processPaymentsBatch(List<PaymentRequest> requests) {
    // Before: 200 concurrent requests × timeout = long wait
    // After: process with virtual threads
    
    try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
        return requests.stream()
            .map(request -> executor.submit(() -> 
                gatewayService.charge(request)
            ))
            .map(future -> {
                try {
                    return future.get();
                } catch (Exception e) {
                    return new PaymentResult(null, "FAILED");
                }
            })
            .collect(toList());
    }
}
```

---

## 🌐 Spring Boot Integration {#spring-boot}

### @Async - Async Method Execution

```java
@Service
public class OrderService {
    @Async
    public CompletableFuture<OrderConfirmation> processOrderAsync(Order order) {
        // Runs in background thread pool
        return CompletableFuture.completedFuture(
            confirmOrder(order)
        );
    }
    
    @Async("customExecutor")
    public void sendNotification(Order order) {
        // Runs in custom executor bean
        emailService.send(order);
    }
}

// Configure custom executor
@Configuration
public class AsyncConfig {
    @Bean("customExecutor")
    public Executor taskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);
        executor.setMaxPoolSize(50);
        executor.setQueueCapacity(100);
        executor.initialize();
        return executor;
    }
}

// In controller
@PostMapping("/orders")
public CompletableFuture<OrderConfirmation> createOrder(@RequestBody Order order) {
    return orderService.processOrderAsync(order);
    // Spring waits for CompletableFuture before sending response
}
```

### MDC (Mapping Diagnostic Context) - Request Tracing

```java
@Component
public class RequestTracingFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request, 
                                   HttpServletResponse response, 
                                   FilterChain filterChain) {
        String requestId = UUID.randomUUID().toString();
        MDC.put("requestId", requestId);  // For logging
        
        try {
            filterChain.doFilter(request, response);
        } finally {
            MDC.clear();
        }
    }
}

// Log configuration (logback.xml)
// <pattern>%d{ISO8601} [%X{requestId}] %msg%n</pattern>

// When using @Async, MDC doesn't propagate automatically
// Solution: Wrap @Async method
@Override
@Async
public void notify(Order order) {
    // MDC is lost here in traditional async setup
}

// Better: Use Spring Cloud Sleuth or custom decorator
```

### Non-Blocking REST with WebClient

```java
@Service
public class PaymentService {
    private final WebClient webClient;
    
    public Mono<PaymentResponse> authorizePayment(PaymentRequest request) {
        return webClient.post()
            .uri("http://payment-gateway/authorize")
            .bodyValue(request)
            .retrieve()
            .bodyToMono(PaymentResponse.class)
            .retryWhen(Retry.backoff(3, Duration.ofSeconds(1)))
            .onErrorMap(this::mapError);
    }
}

@RestController
public class OrderController {
    @PostMapping("/authorize")
    public Mono<OrderResponse> authorize(@RequestBody OrderRequest request) {
        return paymentService.authorizePayment(request.toPaymentRequest())
            .flatMap(payment -> orderService.createOrder());
    }
}
```

---

## 🎓 Interview Questions {#interview-qa}

### Q1: Difference Between Non-Blocking and Async?

**Answer:**
"Async with Thread Pool (ExecutorService) frees the main thread but blocks a thread pool thread — limited by pool size. Non-blocking (WebClient) doesn't block any thread — uses event loops to handle 1000s of requests. Non-blocking is truly scalable."

---

### Q2: When Would You Use Virtual Threads vs CompletableFuture?

**Answer:**
"Virtual Threads for I/O-heavy apps where you want to write simple blocking code. They're great for traditional JDBC, REST calls. CompletableFuture for chaining transformations and combining results — more functional style. Virtual Threads are easier to understand for newcomers."

---

### Q3: How Do You Prevent Deadlocks?

**Answer:**
"Always acquire locks in the same order across all methods. Or use tryLock() with timeout instead of lock() to avoid indefinite waits. Prefer higher-level constructs like ExecutorService or message queues over manual locking."

---

### Q4: Volatile vs AtomicInteger - When to Use Each?

**Answer:**
"Volatile for simple flags and signals (e.g., shutdown boolean). AtomicInteger for counters where you need compound operations like increment. Volatile only guarantees visibility; AtomicInteger guarantees atomicity."

---

### Q5: How Do You Debug Thread Leaks in Spring Boot?

**Answer:**
"Use jconsole or JVisualVM to monitor thread count over time. Check for tasks that never complete — hanging in ThreadPools. Ensure thread pool shutdown() is called. Look for ThreadLocal values that aren't cleared. Use Spring Boot Actuator endpoints to track executor metrics."

---

### Q6: Real-World Scenario: Payment Processing Under Load

**Answer:**
"I had 200 concurrent payment requests. Using ExecutorService with 100 threads meant 100 requests queued. I switched to WebClient + virtual threads. Each request binds to a lightweight virtual thread, no waiting. Resources dropped from 2GB to 500MB. Throughput improved 10x."

---

### Q7: How Does Spring @Async Work?

**Answer:**
"@Async creates AOP proxy around the method. When called, it submits execution to a background executor. Returns CompletableFuture so caller can attach .thenAccept() etc. Must be public and called externally (not from same bean) for proxy to work."

**Gotcha:** @Async from same bean doesn't work!
```java
@Service
public class MyService {
    @Async
    public void doWork() { }
    
    public void caller() {
        doWork();  // ❌ Runs synchronously! (no proxy)
        
        // Use constructor injection to get proxy
    }
}
```

---

### Q8: Concurrency Testing - How Do You Test?

**Answer:**
"Use CountDownLatch or Awaitility to sync threads. Never use Thread.sleep(). Use jUnit5 @RepeatedTest to run test many times (nondeterminism shows bugs). Use tools like ThreadSanitizer or Stress testing frameworks."

```java
@Test
public void testConcurrentAccess() {
    int numThreads = 100;
    CountDownLatch latch = new CountDownLatch(numThreads);
    
    for (int i = 0; i < numThreads; i++) {
        executor.submit(() -> {
            try {
                service.process();
                assertEquals(expected, service.getResult());
            } finally {
                latch.countDown();
            }
        });
    }
    
    latch.await();  // Wait for all
}
```

---

### Q9: ForkJoinPool vs ThreadPoolExecutor vs Virtual Threads?

**Answer:**
"ForkJoinPool for CPU-intensive divide-and-conquer tasks (perfect for parallelStreams). ThreadPoolExecutor for traditional async I/O. Virtual Threads for high-concurrency I/O where you want to write simple blocking code."

| Use Case | Best Choice |
|----------|-------------|
| Bulk image processing | ForkJoinPool |
| Background emails | ThreadPoolExecutor |
| 1M API calls | Virtual Threads |
| Price aggregation | ForkJoinPool (parallelStream) |

---

### Q10: How Do You Handle Context in @Async?

**Answer:**
"MDC is thread-local and doesn't propagate in @Async. Use Spring Cloud Sleuth for automatic propagation, or create custom TaskDecorator to copy MDC to async thread."

```java
@Bean
public TaskExecutor taskExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.setTaskDecorator(mdcTaskDecorator());
    return executor;
}

private TaskDecorator mdcTaskDecorator() {
    return runnable -> {
        Map<String, String> contextMap = MDC.getCopyOfContextMap();
        return () -> {
            MDC.setContextMap(contextMap);
            try {
                runnable.run();
            } finally {
                MDC.clear();
            }
        };
    };
}
```

---

## 🎯 Interview Checklist

### MUST KNOW (90%+ asked)
- [ ] Non-blocking vs async - explain with WebClient vs ExecutorService
- [ ] CompletableFuture chaining - thenApply, thenAccept, allOf
- [ ] Thread-safe updates - AtomicInteger vs volatile
- [ ] Deadlock prevention - lock ordering, tryLock
- [ ] ExecutorService basics - submit, shutdown, Future.get()

### SHOULD KNOW (60%+ asked)
- [ ] Concurrency utilities - CountDownLatch, Semaphore, CyclicBarrier
- [ ] Thread pool sizing - CPU-bound vs I/O-bound formulas
- [ ] Java Memory Model - happens-before, visibility
- [ ] Spring @Async - how it works, MDC propagation
- [ ] ForkJoinPool - work-stealing, divide-and-conquer

### GOOD TO KNOW (40%+ asked)
- [ ] Virtual Threads - why they matter, how to use
- [ ] ThreadLocal - request tracing, memory leaks
- [ ] Starvation vs deadlock - differences
- [ ] Performance tools - VisualVM, JFR, thread dumps
- [ ] Backward compatibility - when to use what

---

## 💡 Real-World Production Stories

**Story 1: Flipkart Order Surge**
"During Black Friday, our OrderService couldn't handle surge traffic. We were using synchronized blocks everywhere. Switched to ConcurrentHashMap for order cache and AtomicInteger for counters. Throughput increased 3x without changing business logic."

**Story 2: Payment Gateway Timeouts**
"Making 200 parallel payment calls with traditional threads caused thread exhaustion. Migrated to WebClient (non-blocking). Same 200 requests now handled by 4 event loop threads. Latency dropped 50%, resource usage dropped 70%."

**Story 3: Thread Context Loss**
"In @Async email notifications, our request ID was missing from logs. Used custom TaskDecorator to propagate MDC to background threads. Now full tracing visible end-to-end."

---

## 📚 Final Summary

**Key Insight:** Choose the right concurrency model for your problem:
- **Blocking code + Thread Pool** = Simple, works for 100s of concurrent tasks
- **Non-blocking + Event Loop** = Scalable, handles 1000s, harder to understand
- **Virtual Threads** = Best of both — write blocking code, get event loop scalability

---

**Last Updated:** February 21, 2026  
**Difficulty:** Senior Level  
**Study Time:** 90-120 minutes for complete mastery  
**Prerequisites:** Java fundamentals, Spring Boot basics, concurrency concepts
