
# Spring WebFlux: Scenario-Based Guide for New Learners


This guide explains the most important WebFlux topics in simple English, with real-world examples. Each section starts with a summary of why the topic matters for beginners.

---

### WebFlux Request Flow (How a Request is Handled)

```
Client
  |
  | HTTP Request
  v
+-------------------+
| Router            |
+-------------------+
  |
  | Match Path
  v
+-------------------+
| Handler Function  |
+-------------------+
  |
  | Returns Mono/Flux
  v
+-------------------+
| Reactor Pipeline  |
+-------------------+
  |
  | Process Data
  v
+-------------------+
| Netty Event Loop  |
+-------------------+
  |
  | Send Response
  v
Client (Response)
```

This diagram shows how a request moves from the client, through your code, and back as a response.

---

## 🎯 Understanding Core Concepts (Explained Simply)

### What is Netty Event Loop? Why Do We Need It?

**Simple Explanation:**
Think of Netty Event Loop as a **single waiter in a restaurant** serving 1000 customers.

- **Traditional way (Spring MVC)**: One waiter per customer. 1000 customers = 1000 waiters. Very expensive!
- **WebFlux way (Netty Event Loop)**: One super-fast waiter handles all 1000 customers by doing things in parallel.

```
Traditional (Blocking):
Customer 1 → Waiter 1 (waits 5 minutes)
Customer 2 → Waiter 2 (waits 5 minutes)
Customer 3 → Waiter 3 (waits 5 minutes)
Result: 3 customers = needs 3 waiters. Slow and expensive.

WebFlux (Non-blocking):
Customer 1: Orders food → Waiter does other customers
Customer 2: Orders food → Waiter does other customers
Customer 3: Orders food → Waiter does other customers
(Food arrives for Customer 1 → Waiter serves it)
(Food arrives for Customer 2 → Waiter serves it)
Result: 1000 customers = 1 waiter! Fast and cheap.
```

**Why we need it:**
- Very fast for handling many concurrent requests
- Uses 10-20 threads instead of thousands
- Saves memory and CPU

---

### What is Backpressure? Why is It Important?

**Simple Explanation:**
Imagine a **garden hose filling a small cup**. (A firehose is a super-powerful water hose used by firefighters - shoots water very fast!)

```
Without Backpressure:
Garden Hose (1000 drops/sec) → Small Cup (holds 10 drops/sec)
Result: Water overflows, cup breaks, water wasted!

With Backpressure:
Garden Hose → Check cup capacity → Slow down the water flow
Small Cup tells hose: "Hey! I can only handle 10 drops/sec"
Garden Hose: "OK, I'll wait and send slowly"
Result: Cup stays safe, no overflow, no waste!
```

**Real example in code:**
```java
// WITHOUT backpressure (DANGEROUS - crashes your app)
@GetMapping("/videos")
public Flux<VideoFrame> streamVideo() {
    return Flux.range(1, 1_000_000)  // Sends 1 million frames instantly
        .map(i -> new VideoFrame(i));
}

// Client on slow internet can only receive 100 frames/sec
// But server sends 1,000,000 frames/sec
// Memory fills up → App crashes with OutOfMemoryError

// WITH backpressure (SAFE)
@GetMapping("/videos")
public Flux<VideoFrame> streamVideoSafe() {
    return Flux.range(1, 1_000_000)
        .map(i -> new VideoFrame(i))
        .onBackpressureBuffer(100)  // Only buffer 100 frames
        .delayElement(Duration.ofMillis(10));  // Wait a bit before sending next
}

// Client says: "I got 100 frames, please wait"
// Server stops sending until client is ready
// Result: No crash, smooth streaming!
```

**What happens if you don't have backpressure:**
- Server fills up memory with unsent data
- App crashes with OutOfMemoryError
- Users get frustrated

---

### What Does "Slowing Down Emission" Mean?

**Simple Explanation:**
Instead of throwing everything at once, you **wait and check if the receiver is ready**.

```
Fast (No slowdown):
Producer: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 (sends all at once)
Consumer: I can only handle 2 per second!
Result: 8 items pile up, memory overflows

Slow (With slowdown):
Producer: Waits... asks "Are you ready?"
Consumer: "I'm ready for 1 item"
Producer: Sends 1
Consumer: "I'm ready for 1 more"
Producer: Sends 1
Result: Perfect pace, no overflow
```

---

### Blocking JDBC Problem Explained

**The Scenario:**
You have **20 event loop threads handling 10,000 users**. One user asks for data from database.

```
BLOCKING JDBC (BAD):

Event Loop Thread 1: Calls userRepository.findById(id)
                     Waits... waiting... waiting... (100ms) ← BLOCKED!
                     
Meanwhile, 9,999 other users are waiting for this thread!
Only 19 threads left for everyone else!

Timeline:
Time 0ms: 10,000 requests come in
Time 1ms: Threads 1-20 are all BLOCKED waiting for database
Time 101ms: Thread 1 finally gets data back
Time 102ms: 10,000 users finally get responses

Real-world impact: 
- If each request blocks for 100ms
- And you have 20 event loop threads
- You can handle only 20 requests at a time = 200 requests/sec
- But you WANT to handle 10,000 requests/sec!
```

**Visual example:**
```
Event Loop Threads (like checkout lanes):

Lane 1: [User blocked waiting for DB] ⏳⏳⏳ 100ms
Lane 2: [User blocked waiting for DB] ⏳⏳⏳ 100ms
Lane 3: [User blocked waiting for DB] ⏳⏳⏳ 100ms
...
Lane 20: [User blocked waiting for DB] ⏳⏳⏳ 100ms

Meanwhile: 9,980 users stuck in queue waiting for a free lane!
```

---

### Schedulers.boundedElastic() - The Solution

**Simple Explanation:**
Instead of using the main waiter, **hire a temporary helper** for slow jobs.

```
SOLUTION 1: Without boundedElastic (still BAD):
@GetMapping("/user/{id}")
public Mono<User> getUser(@PathVariable String id) {
    User user = userRepository.findById(id);  // BLOCKING on event loop
    return Mono.just(user);
}

SOLUTION 2: With boundedElastic (GOOD):
@GetMapping("/user/{id}")
public Mono<User> getUser(@PathVariable String id) {
    return Mono.fromCallable(() -> userRepository.findById(id))
        .subscribeOn(Schedulers.boundedElastic());  // Use helper!
}
```

**How it works:**
```
Main Event Loop (20 threads): Handles fast, non-blocking work
     ↓
When you need blocking work (database call):
     ↓
boundedElastic() (helper thread pool): Takes the blocking task
     ↓
Helper thread: Happily waits for database (100ms) 
Main event loop: FREE to handle other requests!
     ↓
Helper finishes: Returns result back to main event loop

Timeline with boundedElastic:
Time 0ms: 10,000 requests come in
Time 1ms: Event loop assigns each request to a helper thread
Time 5ms: Event loop is free! Handling more requests
Time 101ms: First batch of database results come back
Result: Handles 10,000+ requests/sec! ✓
```

**Real-world analogy:**
```
Restaurant:
- Main waiter: Fast, handles everything
- One customer: "I need extra-crispy chicken" (slow cooking, 10 minutes)
- Main waiter: "Kitchen! You handle this slow job, I'll serve other customers"
- Kitchen: Takes 10 minutes, makes crispy chicken
- Main waiter: Keeps serving other customers, never stops
- Result: Everyone gets what they want without waiting!

WebFlux:
- Event Loop: Fast, handles everything
- One request: Database query (slow, 100ms)
- Event Loop: "boundedElastic! You handle this slow job, I'll handle other requests"
- boundedElastic: Takes 100ms, gets data from database
- Event Loop: Keeps processing other requests, never stops
- Result: All requests handled super fast!
```

---

### Code Example: Blocking vs Non-Blocking

```java
// ❌ BAD: Blocks event loop
@GetMapping("/user/{id}")
public Mono<User> badApproach(@PathVariable String id) {
    User user = jdbcRepository.findById(id);  // WAITS 100ms HERE
    return Mono.just(user);
}

// ✓ GOOD: Uses helper thread for blocking work
@GetMapping("/user/{id}")
public Mono<User> goodApproach(@PathVariable String id) {
    return Mono.fromCallable(() -> jdbcRepository.findById(id))
        .subscribeOn(Schedulers.boundedElastic());  // Do blocking work on helper
}

// ✓✓ BEST: Use R2DBC (non-blocking database driver)
@GetMapping("/user/{id}")
public Mono<User> bestApproach(@PathVariable String id) {
    return r2dbcRepository.findById(id);  // Non-blocking! No helper needed
}
```

**Performance comparison for 10,000 concurrent users:**

```
Approach 1 (BAD - Blocking):
- Throughput: ~200 requests/sec
- Response time: 5-10 seconds for many users
- CPU: High (context switching)
- Memory: High (many threads waiting)

Approach 2 (GOOD - With boundedElastic):
- Throughput: ~5,000 requests/sec
- Response time: 100-200ms for most users
- CPU: Low (no context switching on event loop)
- Memory: Low (only 20 event loop threads)

Approach 3 (BEST - R2DBC):
- Throughput: ~50,000 requests/sec
- Response time: 50-100ms for most users
- CPU: Very Low
- Memory: Very Low
```

---


### 1. Scenario: What if the client is slow? (Backpressure)

**Real-world example:**
You build a video streaming service with 100,000 users. Server streams data at 1000 items/sec, but a slow user can only consume 10 items/sec. Without backpressure, server memory fills up in seconds.

**Interview Q&A:**

**Q: How does WebFlux prevent overload when the client is slow?**
A: WebFlux uses the Reactive Streams backpressure protocol. When a subscriber can't keep up, it sends a demand signal back to the publisher, slowing down emission.

```java
// Without backpressure handling (BAD - can crash!)
@GetMapping("/stream")
public Flux<Data> streamData() {
    return Flux.range(1, 1_000_000)
        .map(i -> new Data(i));
}

// With backpressure handling (GOOD)
@GetMapping("/stream")
public Flux<Data> streamDataSafe() {
    return Flux.range(1, 1_000_000)
        .map(i -> new Data(i))
        .onBackpressureBuffer(100)  // Buffer up to 100 items
        .delayElement(Duration.ofMillis(10));  // Throttle emission
}
```

**Q: What are the three ways to handle backpressure?**
A:
1. **Buffer**: `.onBackpressureBuffer()` - store extra items in memory (risky if buffer fills)
2. **Drop**: `.onBackpressureDrop()` - skip items when can't keep up (loses data)
3. **Latest**: `.onBackpressureLatest()` - keep only the most recent item

**Detailed Examples:**

**1. onBackpressureBuffer() - Store items in a waiting room**
```java
// Producer sends: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 (very fast)
// Consumer can only process 1 item per second (very slow)

Flux.range(1, 10)
    .onBackpressureBuffer(5)  // Buffer holds max 5 items
    .delayElements(Duration.ofSeconds(1))  // Consumer is slow
    .subscribe(System.out::println);

// What happens:
// Time 0s: Items 1-5 go to buffer (waiting room), Item 6 processed
// Time 1s: Buffer has 1,2,3,4,5 → Consumer takes 1, processes it
// Time 2s: Buffer has 2,3,4,5 → Consumer takes 2, processes it
// If producer sends MORE than 5: ERROR! "Buffer overflow"

// Real-world: Like a waiting room with 5 chairs
// If 6th person arrives and no chairs → reject them
```

**2. onBackpressureDrop() - Skip items when busy**
```java
// Producer sends: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
// Consumer can only handle some items

Flux.range(1, 10)
    .onBackpressureDrop()  // Drop items if consumer is busy
    .delayElements(Duration.ofMillis(100))
    .subscribe(System.out::println);

// What happens:
// Consumer says: "I'm ready for 1 item"
// Producer sends: 1 → Consumer receives it
// Producer sends: 2, 3, 4, 5, 6 (while consumer is busy)
// Result: Consumer gets 1, then 7 (items 2-6 DROPPED!)

// Real-world: Video streaming
// If you miss some frames, skip them (don't freeze the video)
// Better to drop frames than lag behind
```

**3. onBackpressureLatest() - Keep only the newest**
```java
// Producer sends: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
// Consumer can only handle the latest value

Flux.range(1, 10)
    .onBackpressureLatest()  // Keep only the most recent item
    .delayElements(Duration.ofMillis(100))
    .subscribe(System.out::println);

// What happens:
// Producer sends: 1, 2, 3, 4, 5 (very fast)
// Consumer is busy processing 1
// Latest value = 5 (items 2, 3, 4 are REPLACED by 5)
// Consumer finishes 1 → Gets 5 next (skips 2, 3, 4)

// Real-world: Stock price ticker
// You only care about the LATEST price
// If stock was $100, $101, $102, $103
// Just show $103 (latest), skip the old prices
```

**When to use which?**
```
┌─────────────────────┬──────────────────────────────────┐
│ Strategy            │ Use When                         │
├─────────────────────┼──────────────────────────────────┤
│ Buffer              │ Can't lose data (banking)        │
│                     │ Have enough memory               │
├─────────────────────┼──────────────────────────────────┤
│ Drop                │ OK to lose some data (video)     │
│                     │ Speed matters more               │
├─────────────────────┼──────────────────────────────────┤
│ Latest              │ Only newest data matters         │
│                     │ (stock prices, temperature)      │
└─────────────────────┴──────────────────────────────────┘
```

**Q: What happens if you ignore backpressure?**
A: Memory grows indefinitely, app crashes with OutOfMemoryError. Producers emit faster than consumers can process.

---


### 2. Scenario: What if you use slow (blocking) code?

**Real-world example:**
You call `userRepository.findById(id)` (blocking JDBC) in a WebFlux handler. If DB takes 100ms per request, only 10 requests/sec fit in the event loop. Other users wait.

**Interview Q&A:**

**Q: Why is blocking code bad in WebFlux?**
A: WebFlux runs on Netty's event loop (10-20 threads for 1000s of users). Blocking one thread blocks all waiting requests on that thread.

```java
// BAD - blocks the event loop
@GetMapping("/user/{id}")
public Mono<User> getUser(@PathVariable String id) {
    User user = userRepository.findById(id);  // BLOCKING - 100ms wait
    return Mono.just(user);
}

// GOOD - runs blocking code on separate thread
@GetMapping("/user/{id}")
public Mono<User> getUserSafe(@PathVariable String id) {
    return Mono.fromCallable(() -> userRepository.findById(id))
        .subscribeOn(Schedulers.boundedElastic());
}

// BEST - use R2DBC (non-blocking database driver)
@GetMapping("/user/{id}")
public Mono<User> getUserBest(@PathVariable String id) {
    return userRepository.findById(id);  // Non-blocking!
}
```

**Q: What's the difference between `.subscribeOn()` and `.publishOn()`?**
A:
- `.subscribeOn()`: Changes the thread where subscription starts (upstream)
- `.publishOn()`: Changes the thread for downstream operations

**Q: How do you safely use blocking code?**
A: Use `Schedulers.boundedElastic()` - it creates a thread pool for blocking work, doesn't waste event loop threads.

---


### 3. Scenario: What if something goes wrong? (Error Handling)

**Real-world example:**
You call an external payment API that times out or returns 500. Without error handling, user sees a crash. With it, you show a friendly message.

**Interview Q&A:**

**Q: What's the difference between `.onErrorResume()` and `.onErrorReturn()`?**
A:

```java
// onErrorReturn - return a fixed value when error happens
@GetMapping("/payment/{id}")
public Mono<Payment> getPayment(@PathVariable String id) {
    return paymentService.fetch(id)
        .onErrorReturn(new Payment("FAILED"));  // Returns fixed object
}

// onErrorResume - switch to alternative flow when error happens
Mono<Payment> getPaymentWithFallback(String id) {
    return paymentService.fetch(id)
        .onErrorResume(e -> paymentService.fetchFromCache(id));  // Try backup
}

// doOnError - log/track error but re-throw it
Mono<Payment> getPaymentWithLogging(String id) {
    return paymentService.fetch(id)
        .doOnError(e -> logger.error("Payment fetch failed", e));  // Just log
}
```

**Q: How do you handle errors globally in WebFlux?**
A: Use `@ControllerAdvice` with exception handlers:

```java
@ControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(TimeoutException.class)
    public Mono<ResponseEntity<ErrorResponse>> handleTimeout(TimeoutException e) {
        return Mono.just(ResponseEntity.status(504)
            .body(new ErrorResponse("Request timeout")));
    }
}
```

**Q: What happens if an error occurs inside `.map()`?**
A: Error propagates downstream to the next `.onError*()` operator. If no handler, request fails.

---


## ✅ SHOULD KNOW (Good to Know for Building Real Apps)


### 4. Scenario: Who does the work? (Threading and Schedulers)

**Real-world example:**
You have: DB query (blocking) → JSON transformation (fast) → HTTP response (fast). Should each run on different threads?

**Interview Q&A:**

**Q: What are the available schedulers in Reactor?**
A:

```java
Schedulers.immediate()        // Current thread
Schedulers.single()           // Single reusable thread
Schedulers.boundedElastic()   // Elastic thread pool (blocking work)
Schedulers.parallel()         // Fixed-size thread pool (CPU-bound work)
```

**Q: How do you avoid thread starvation?**
A: Don't block the event loop. Use `boundedElastic()` for blocking I/O:

```java
// Good - event loop free, blocking on separate thread
blockingRepository.findAll()
    .subscribeOn(Schedulers.boundedElastic());

// Bad - blocks event loop
blockingRepository.findAll();  // Event loop becomes a waiting room
```

**Q: When do you use `.parallel()` scheduler?**
A: For CPU-intensive work that can run in parallel:

```java
Flux.range(1, 1000)
    .parallel()
    .runOn(Schedulers.parallel())
    .map(this::complexCalculation)
    .sequential()  // Re-order back to original sequence
    .subscribe();
```

---


### 5. Scenario: How do you test your code? (Testing WebFlux)
**Why it matters:**
Testing helps you catch bugs before users see them. WebFlux has special tools for testing reactive code.

**Real-world example:**
You want to check that your API returns the right data, in the right order, and handles errors.

**Interview Q&A:**

**Q: How do you test a Mono/Flux?**
A: Use `StepVerifier` to verify emissions step-by-step:

```java
// Test successful emission
@Test
void testMonoEmission() {
    Mono<String> mono = Mono.just("Hello");
    
    StepVerifier.create(mono)
        .expectNext("Hello")
        .expectComplete()
        .verify();
}

// Test Flux with multiple items
@Test
void testFluxEmission() {
    Flux<Integer> flux = Flux.just(1, 2, 3);
    
    StepVerifier.create(flux)
        .expectNext(1, 2, 3)
        .expectComplete()
        .verify();
}

// Test error scenario
@Test
void testMonoError() {
    Mono<String> mono = Mono.error(new RuntimeException("Failed"));
    
    StepVerifier.create(mono)
        .expectError(RuntimeException.class)
        .verify();
}
```

**Q: How do you test a WebFlux controller?**
A: Use `WebTestClient` to test HTTP endpoints:

```java
@WebFluxTest(controllers = UserController.class)
class UserControllerTest {
    @Autowired
    private WebTestClient webClient;
    
    @Test
    void testGetUser() {
        webClient.get()
            .uri("/users/1")
            .exchange()
            .expectStatus().isOk()
            .expectBody(User.class)
            .isEqualTo(new User(1, "Alice"));
    }
}
```

**Q: How do you test with time-dependent operations?**
A: Use `StepVerifier.withVirtualTime()`:

```java
@Test
void testWithDelay() {
    Mono<String> delayed = Mono.delay(Duration.ofSeconds(1))
        .map(l -> "done");
        
    StepVerifier.withVirtualTime(() -> delayed)
        .expectSubscription()
        .expectNoEvent(Duration.ofSeconds(1))
        .expectNext("done")
        .expectComplete()
        .verify();
}
```

---



### 6. Scenario: How do you connect to a database? (R2DBC vs JDBC)
**Why it matters:**
Most apps need to save or read data. Using the wrong database driver can make your app slow or block other users.

**Real-world example:**
You want to build a chat app that saves messages quickly, even if many users are online.

**What WebFlux helps you achieve:**
WebFlux works best with non-blocking databases like R2DBC. This keeps your app fast and responsive.

**How it works:**
- JDBC (classic) is blocking and slows down WebFlux
- R2DBC is non-blocking and fits WebFlux’s style
- Use R2DBC for best results

**Interview Q&A:**
- Q: What can’t R2DBC do yet?
- Q: Can you use JPA with WebFlux?

---


### 7. Scenario: How do you keep your app safe? (Security)
**Why it matters:**
You want to protect your app from hackers and make sure only the right people can access data.

**Real-world example:**
You build a banking app. Only the account owner should see their balance.

**What WebFlux helps you achieve:**
WebFlux works with Spring Security to protect your app, even in a reactive flow.

**How it works:**
- Use `@EnableWebFluxSecurity` to turn on security
- Set up rules with `SecurityWebFilterChain`
- Supports modern login methods like JWT and OAuth2

**Interview Q&A:**
- Q: How does security work in a reactive app?
- Q: What mistakes do people make with security in WebFlux?

---


### 8. Scenario: How do you combine results from many places? (zip, merge, concat, flatMap)

#### How WebFlux Handles Multiple Operations (ASCII Diagram)

Suppose you want to fetch user info, orders, and notifications at the same time and combine the results:

```
User Request
     |
     v
+-------------------+
|   Handler         |
+-------------------+
     |     |     |
     v     v     v
UserInfo Orders Notifications
 (Mono)   (Mono)    (Mono)
     |     |     |
     +--+--+--+--+
     v
   zip/merge/flatMap
     |
     v
   Combine Results
     |
     v
   Send Response
```

- With `zip`, you wait for all to finish, then combine.
- With `merge`, you process as soon as any is ready.
- With `flatMap`, you can run many in parallel and combine as they finish.

This lets WebFlux handle many operations efficiently, without blocking, and combine results for the client.
**Why it matters:**
Modern apps often need to get data from many sources at once. Doing this efficiently makes your app faster and more reliable.

**Real-world example:**
You want to show a dashboard that combines user info, recent orders, and notifications—all from different services.

**What WebFlux helps you achieve:**
You can combine results from many places, either in order or as soon as they’re ready.

**How it works:**
- `zip`: Waits for all sources, then combines results (good for related data)
- `merge`: Shows results as soon as any source is ready (good for speed)
- `concat`: Waits for one to finish before starting the next (good for order)
- `flatMap`: Runs many things at once (good for parallel work)
- Hot vs Cold: Hot publishers always emit; cold publishers emit per subscriber

**Interview Q&A:**
- Q: When do you use `flatMap` vs `concatMap`?
  - A: Use `flatMap` for speed (order not guaranteed), `concatMap` for order (one at a time).

---


### 9. Scenario: How do you save many things at once? (Transactions)
**Why it matters:**
Sometimes you need to save several things together, and if one fails, you want to undo them all. This is called a transaction.

**Real-world example:**
You transfer money between two accounts. If one update fails, you don’t want to lose money.

**Interview Q&A:**

**Q: How do you do transactions in WebFlux?**
A: Use `TransactionalOperator` to wrap the reactive chain:

```java
@Autowired
private TransactionalOperator rxtx;

public Mono<Void> transferMoney(String fromAccount, String toAccount, BigDecimal amount) {
    return rxtx.transactional(
        accountRepository.debit(fromAccount, amount)
            .then(accountRepository.credit(toAccount, amount))
    );
    // If either fails, BOTH are rolled back
}
```

**Q: What happens if one operation in the chain fails?**
A: All previous operations in the transaction are rolled back. The database returns to its initial state:

```java
rxtx.transactional(
    accountRepository.debit(fromAccount, 100)      // Success
        .then(accountRepository.credit(toAccount, 100))  // FAILS
)
// Result: Both operations are ROLLED BACK
// Money not debited, not credited
```

**Q: Can you use Spring @Transactional with WebFlux?**
A: Only if you use R2DBC (non-blocking). With blocking code, `@Transactional` defeats the purpose of WebFlux.

**Simple Explanation:**
Think of it like this:
- **R2DBC** = Electric car (fast, modern, non-blocking)
- **JDBC** = Old diesel truck (slow, blocks the road)

If you use an old diesel truck on a Formula 1 race track (WebFlux), you lose all the speed benefits!

```java
// GOOD - R2DBC is non-blocking (Electric car on race track)
@Transactional
public Mono<Void> transferMoney(String from, String to, BigDecimal amount) {
    return r2dbcRepository.save(...);  // Non-blocking! Fast!
}
// Event loop: FREE to handle other requests while database saves

// BAD - JDBC blocks (Diesel truck on race track)
@Transactional
public Mono<Void> transferMoney(String from, String to, BigDecimal amount) {
    return Mono.fromCallable(() -> jdbcRepository.save(...));  // BLOCKS!
}
// Event loop: STUCK waiting for database
// All other users must wait
// You lose all WebFlux speed benefits!
```

**Why it defeats the purpose:**
```
With R2DBC (GOOD):
User 1: Save to DB (non-blocking) ✓ Event loop free!
User 2: Save to DB (non-blocking) ✓ Event loop free!
User 3: Save to DB (non-blocking) ✓ Event loop free!
Result: All 3 running in parallel! Fast!

With JDBC (BAD):
User 1: Save to DB (blocks for 100ms) ⏳
User 2: Waits... ⏳
User 3: Waits... ⏳
Result: One at a time! Slow! Same as regular Spring MVC!
```

---


### 10. Scenario: How do you send updates instantly? (WebSockets)

#### Example: Real-Time Communication with WebSockets

```
Client                WebFlux               WebSocket
  |                     |                       |
  | Open WebSocket      |                       |
  |-------------------->|                       |
  |                     | Establish Session     |
  |                     |---------------------->|
  |                     |                       |
  | Message (Inbound)   |                       |
  |-------------------->|                       |
  |                     | Process & Send Back   |
  |     Real-time       |<----------------------|
  |     Updates         |                       |
  |<--------------------|                       |
  |                     |                       |
```
**Why it matters:**
Some apps need to send and receive messages in real time, like chat or live dashboards.

**Real-world example:**
You build a stock ticker that updates prices instantly for all users.

**What WebFlux helps you achieve:**
WebFlux supports WebSockets, so you can send and receive messages instantly, both ways.

**How it works:**
- Use `WebSocketHandler` to manage connections
- Use `WebSocketSession` to send and receive messages
- WebFlux helps you control message flow so you don’t overload users

**Interview Q&A:**
- Q: How does WebFlux handle real-time messages and backpressure?
  - A: It manages sessions and controls message speed so no one gets overloaded.

---


## ⚙️ NICHE (Specialized, Less Common)


### 11. Scenario: How do you stream updates to the browser? (SSE)
**Why it matters:**
Sometimes you want to send updates to the browser as they happen, but don’t need two-way chat.

**Real-world example:**
You show live sports scores that update automatically.

**What WebFlux helps you achieve:**
WebFlux supports Server-Sent Events (SSE) to push updates to browsers easily.

**How it works:**
- Return a `Flux<T>` from your controller
- Set the response type to `text/event-stream`
- Browser gets updates as soon as they happen

**Interview Q&A:**

**Q: When should you use SSE instead of WebSocket?**
A: Use SSE when you only need **one-way communication** (server → client). Use WebSocket when you need **two-way communication**.

**Simple Comparison:**
```
SSE (Server-Sent Events):
- Server → Client only (one direction)
- Like a NEWS CHANNEL on TV
  → TV broadcasts to you
  → You can't talk back to the TV
- Client just receives updates
- Simpler to set up
- Auto-reconnects if connection drops

WebSocket:
- Server ↔ Client (both directions)
- Like a PHONE CALL
  → You can talk
  → Other person can talk
  → Real conversation
- Both can send messages
- More complex setup
- Manual reconnection needed
```

**Real-World Examples:**

**Use SSE for:**
```java
// 1. Live sports scores (server pushes scores, you just watch)
@GetMapping(value = "/scores", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<Score> liveScores() {
    return scoreService.getScoreUpdates();  // Server sends, client receives
}

// 2. Stock price updates (server pushes prices)
@GetMapping(value = "/stocks", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<StockPrice> stockPrices() {
    return stockService.getLivePrices();  // One-way: Server → Client
}

// 3. News feed (server pushes articles)
@GetMapping(value = "/news", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<Article> newsUpdates() {
    return newsService.getLatestNews();  // Client just watches
}
```

**Use WebSocket for:**
```java
// 1. Chat application (both users send and receive)
@MessageMapping("/chat")
public Flux<ChatMessage> chat(Flux<ChatMessage> messages) {
    return messages;  // Two-way: User A ↔ User B
}

// 2. Online gaming (players send moves, receive updates)
@MessageMapping("/game")
public Flux<GameState> playGame(Flux<PlayerMove> moves) {
    return gameService.processMove(moves);  // Two-way communication
}

// 3. Collaborative editing (like Google Docs)
@MessageMapping("/edit")
public Flux<DocumentChange> editDocument(Flux<Edit> edits) {
    return documentService.applyEdits(edits);  // Both can edit
}
```

**Quick Decision Guide:**
```
┌─────────────────────────────┬──────────┬───────────┐
│ Use Case                    │ Solution │ Why       │
├─────────────────────────────┼──────────┼───────────┤
│ Server only sends updates   │ SSE      │ Simpler   │
│ Client only receives        │          │           │
├─────────────────────────────┼──────────┼───────────┤
│ Both send and receive       │ WebSocket│ Two-way   │
│ Real-time chat              │          │           │
├─────────────────────────────┼──────────┼───────────┤
│ Live dashboard (read-only)  │ SSE      │ Simpler   │
├─────────────────────────────┼──────────┼───────────┤
│ Gaming/collaboration        │ WebSocket│ Two-way   │
└─────────────────────────────┴──────────┴───────────┘
```

**Q: How do you handle users closing the browser?**
A: Use `.doOnCancel()` to clean up when the connection closes:

```java
@GetMapping(value = "/updates", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<Update> streamUpdates() {
    return updateService.getUpdates()
        .doOnCancel(() -> {
            // User closed browser
            logger.info("Client disconnected");
            // Clean up resources here
        });
}
```

---


### 12. Scenario: How do you add your own logic to data flows? (Custom Operators)
**Why it matters:**
Sometimes you need to do something special that isn’t built in.

**Real-world example:**
You want to log every item, or filter data in a custom way.

**What WebFlux helps you achieve:**
You can add your own steps to the data flow using custom operators.

**How it works:**
- Use `.transform()` or `.compose()` to add your logic
- You can even create your own publisher if needed

**Interview Q&A:**
- Q: When should you write a custom operator?
- Q: How do you test your custom logic?

---

## References
- [Project Reactor Reference](https://projectreactor.io/docs/core/release/reference/)
- [Spring WebFlux Documentation](https://docs.spring.io/spring-framework/docs/current/reference/html/web-reactive.html)
- [R2DBC Specification](https://r2dbc.io/spec/0.8.0.RELEASE/spec/html/)
