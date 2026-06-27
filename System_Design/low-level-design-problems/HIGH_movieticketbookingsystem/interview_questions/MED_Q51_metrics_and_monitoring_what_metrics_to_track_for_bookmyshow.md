# Q51: Metrics & Monitoring - What metrics to track for BookMyShow?

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Four Golden Signals + Business Metrics

```java
@Configuration
public class MetricsConfig {
    
    @Bean
    public MeterRegistry meterRegistry() {
        return new PrometheusMeterRegistry(PrometheusConfig.DEFAULT);
    }
}

@Component
public class BookingMetrics {
    
    private final MeterRegistry meterRegistry;
    
    // 1. LATENCY (Golden Signal #1)
    public void recordBookingLatency(long durationMs, String outcome) {
        meterRegistry.timer("booking.duration",
            Tags.of("outcome", outcome)  // success, failure
        ).record(durationMs, TimeUnit.MILLISECONDS);
    }
    
    // 2. TRAFFIC (Golden Signal #2)
    public void recordBookingRequest() {
        meterRegistry.counter("booking.requests.total",
            Tags.of("endpoint", "/api/bookings")
        ).increment();
    }
    
    // 3. ERRORS (Golden Signal #3)
    public void recordBookingError(String errorType) {
        meterRegistry.counter("booking.errors.total",
            Tags.of("error_type", errorType)  // seat_unavailable, payment_failed
        ).increment();
    }
    
    // 4. SATURATION (Golden Signal #4)
    @Scheduled(fixedRate = 10000)  // Every 10 seconds
    public void recordSystemSaturation() {
        
        // Database connection pool
        HikariDataSource dataSource = getDataSource();
        int activeConnections = dataSource.getHikariPoolMXBean()
            .getActiveConnections();
        int maxConnections = dataSource.getMaximumPoolSize();
        
        meterRegistry.gauge("db.connection_pool.active", activeConnections);
        meterRegistry.gauge("db.connection_pool.utilization",
            (double) activeConnections / maxConnections);
        
        // Thread pool
        ThreadPoolExecutor executor = getExecutor();
        meterRegistry.gauge("threadpool.active", executor.getActiveCount());
        meterRegistry.gauge("threadpool.queue_size", executor.getQueue().size());
        
        // Heap memory
        MemoryMXBean memoryBean = ManagementFactory.getMemoryMXBean();
        MemoryUsage heapUsage = memoryBean.getHeapMemoryUsage();
        meterRegistry.gauge("jvm.memory.used", heapUsage.getUsed());
        meterRegistry.gauge("jvm.memory.utilization",
            (double) heapUsage.getUsed() / heapUsage.getMax());
    }
    
    // BUSINESS METRICS
    public void recordBookingCompleted(BigDecimal amount) {
        meterRegistry.counter("bookings.completed.total").increment();
        meterRegistry.summary("bookings.revenue").record(amount.doubleValue());
    }
    
    public void recordBookingCancelled(String reason) {
        meterRegistry.counter("bookings.cancelled.total",
            Tags.of("reason", reason)
        ).increment();
    }
    
    @Scheduled(fixedRate = 60000)  // Every minute
    public void recordOccupancyRate() {
        
        List<Show> upcomingShows = showRepository
            .findByShowDateAfter(LocalDate.now());
        
        for (Show show : upcomingShows) {
            double occupancy = 1.0 - 
                ((double) show.getAvailableSeats() / show.getTotalSeats());
            
            meterRegistry.gauge("show.occupancy",
                Tags.of("show_id", String.valueOf(show.getId())),
                occupancy
            );
        }
    }
}
```

**Prometheus Queries:**

```promql
# Booking request rate (per second)
rate(booking_requests_total[5m])

# Booking success rate
sum(rate(booking_requests_total{outcome="success"}[5m])) 
/ 
sum(rate(booking_requests_total[5m]))

# P99 booking latency
histogram_quantile(0.99, rate(booking_duration_bucket[5m]))

# Error rate
rate(booking_errors_total[5m])

# Database connection pool utilization
db_connection_pool_utilization > 0.8

# Revenue per minute
rate(bookings_revenue_sum[1m])
```

**Grafana Dashboard:**

```yaml
Dashboard: BookMyShow Production
═══════════════════════════════════════════════════════════

Row 1: Golden Signals
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Latency     │ Traffic     │ Errors      │ Saturation  │
│ P50: 250ms  │ 3.5k QPS    │ 0.5% rate   │ CPU: 65%    │
│ P99: 800ms  │             │             │ Mem: 70%    │
└─────────────┴─────────────┴─────────────┴─────────────┘

Row 2: Business Metrics
┌──────────────────────┬──────────────────────┐
│ Bookings/min         │ Revenue/min          │
│ 58 bookings          │ ₹29,000              │
└──────────────────────┴──────────────────────┘

Row 3: System Health
┌─────────────┬─────────────┬─────────────┐
│ DB Pool     │ Thread Pool │ Cache Hit   │
│ 45/100      │ 78/200      │ 85%         │
└─────────────┴─────────────┴─────────────┘
```

---
