# Q35: Bulkhead Pattern - Isolate thread pools for different operations

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Separate Thread Pools

**Problem:**

```
SINGLE THREAD POOL (Bad)
═══════════════════════════════════════════════════════════
100 threads handling all requests:
- 90 threads: Slow payment gateway calls (5s each)
- 10 threads: Fast booking queries (50ms each)

Result: Booking queries starved! ❌

Timeline:
10:00:00 - 100 payment requests arrive (hold threads for 5s)
10:00:01 - 1000 booking queries arrive (all blocked!)
10:00:05 - Payments complete, bookings can proceed
10:00:05 - Users see 5-second delay for simple query ❌
```

**Solution: Bulkhead Pattern**

```java
@Configuration
public class ThreadPoolConfig {
    
    @Bean(name = "paymentExecutor")
    public ThreadPoolTaskExecutor paymentExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(20);
        executor.setMaxPoolSize(50);
        executor.setQueueCapacity(500);
        executor.setThreadNamePrefix("payment-");
        executor.setRejectedExecutionHandler(
            new ThreadPoolExecutor.CallerRunsPolicy()
        );
        executor.initialize();
        return executor;
    }
    
    @Bean(name = "bookingExecutor")
    public ThreadPoolTaskExecutor bookingExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(50);
        executor.setMaxPoolSize(100);
        executor.setQueueCapacity(1000);
        executor.setThreadNamePrefix("booking-");
        executor.setRejectedExecutionHandler(
            new ThreadPoolExecutor.CallerRunsPolicy()
        );
        executor.initialize();
        return executor;
    }
    
    @Bean(name = "searchExecutor")
    public ThreadPoolTaskExecutor searchExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(100);
        executor.setMaxPoolSize(200);
        executor.setQueueCapacity(2000);
        executor.setThreadNamePrefix("search-");
        executor.setRejectedExecutionHandler(
            new ThreadPoolExecutor.AbortPolicy()  // Reject if full
        );
        executor.initialize();
        return executor;
    }
}
```

**Usage:**

```java
@RestController
@RequestMapping("/api")
public class BookingController {
    
    @Qualifier("bookingExecutor")
    private final Executor bookingExecutor;
    
    @Qualifier("paymentExecutor")
    private final Executor paymentExecutor;
    
    @PostMapping("/bookings")
    public CompletableFuture<BookingResponse> createBooking(
            @RequestBody BookingRequest request) {
        
        // Use dedicated booking thread pool
        return CompletableFuture.supplyAsync(
            () -> bookingService.createBooking(request),
            bookingExecutor
        );
    }
    
    @PostMapping("/payments")
    public CompletableFuture<PaymentResponse> processPayment(
            @RequestBody PaymentRequest request) {
        
        // Use dedicated payment thread pool
        return CompletableFuture.supplyAsync(
            () -> paymentService.processPayment(request),
            paymentExecutor
        );
    }
}
```

**Benefits:**

```
ISOLATED THREAD POOLS
═══════════════════════════════════════════════════════════
Payment Pool: 20-50 threads
Booking Pool: 50-100 threads
Search Pool: 100-200 threads

Timeline:
10:00:00 - 100 payment requests → Payment pool (20-50 threads)
10:00:01 - 1000 booking queries → Booking pool (50-100 threads)
10:00:01 - Bookings proceed immediately! ✅

Result: Isolation prevents cascading failures
```

**Resilience4j Bulkhead:**

```java
@Configuration
public class BulkheadConfig {
    
    @Bean
    public BulkheadRegistry bulkheadRegistry() {
        BulkheadConfig config = BulkheadConfig.custom()
            .maxConcurrentCalls(25)
            .maxWaitDuration(Duration.ofMillis(500))
            .build();
        
        return BulkheadRegistry.of(config);
    }
}

@Service
public class PaymentServiceWithBulkhead {
    
    private final Bulkhead bulkhead;
    
    public PaymentServiceWithBulkhead(BulkheadRegistry registry) {
        this.bulkhead = registry.bulkhead("payment");
    }
    
    public PaymentResponse processPayment(PaymentRequest request) {
        
        return bulkhead.executeSupplier(() -> {
            // Only 25 concurrent calls allowed
            return stripeClient.charge(request);
        });
    }
}
```

**Monitoring:**

```java
@Component
public class ThreadPoolMonitoring {
    
    @Scheduled(fixedRate = 10000)
    public void monitorThreadPools() {
        
        ThreadPoolTaskExecutor[] executors = {
            paymentExecutor,
            bookingExecutor,
            searchExecutor
        };
        
        for (ThreadPoolTaskExecutor executor : executors) {
            ThreadPoolExecutor pool = executor.getThreadPoolExecutor();
            
            int active = pool.getActiveCount();
            int max = pool.getMaximumPoolSize();
            int queueSize = pool.getQueue().size();
            
            double utilization = (double) active / max;
            
            meterRegistry.gauge(
                "threadpool.utilization",
                Tags.of("pool", executor.getThreadNamePrefix()),
                utilization
            );
            
            meterRegistry.gauge(
                "threadpool.queue.size",
                Tags.of("pool", executor.getThreadNamePrefix()),
                queueSize
            );
            
            // Alert if high utilization
            if (utilization > 0.9) {
                log.warn("High thread pool utilization: {} ({}%)",
                    executor.getThreadNamePrefix(),
                    (int) (utilization * 100)
                );
            }
        }
    }
}
```

---

## Key Takeaways:

```
Q32: Rate Limiting
✅ Token bucket algorithm (10 req/min)
✅ Sliding window for precision
✅ Different limits per endpoint
✅ Return 429 with Retry-After header

Q33: Load Balancer
✅ ALB with health checks (30s interval)
✅ Deregistration delay (30s drain)
✅ Sticky sessions (1 hour cookie)
✅ Health endpoint checks DB + Redis

Q34: Circuit Breaker
✅ Open at 50% failure rate
✅ 60s wait before retry
✅ Fallback to queue when open
✅ Alert ops on state change

Q35: Bulkhead Pattern
✅ Separate thread pools per operation
✅ Payment: 20-50 threads
✅ Booking: 50-100 threads
✅ Search: 100-200 threads
✅ Prevent cascading failures
```

This demonstrates production resilience patterns expertise! 🎯
