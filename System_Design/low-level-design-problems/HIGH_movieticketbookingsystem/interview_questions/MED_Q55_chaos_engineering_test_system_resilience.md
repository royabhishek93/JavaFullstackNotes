# Q55: Chaos Engineering - Test system resilience

### Difficulty: ⭐⭐⭐⭐⭐ (Principal)

### ✅ Solution: Controlled Failure Injection

```java
@Component
@ConditionalOnProperty(name = "chaos.enabled", havingValue = "true")
public class ChaosEngineer {
    
    private final Random random = new Random();
    
    // Chaos Experiment 1: Random latency injection
    public void injectLatency(String component) {
        
        if (!shouldInjectChaos()) {
            return;
        }
        
        int latencyMs = random.nextInt(1000) + 500;  // 500-1500ms
        
        log.warn("CHAOS: Injecting {}ms latency to {}", latencyMs, component);
        
        try {
            Thread.sleep(latencyMs);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
    
    // Chaos Experiment 2: Random exception injection
    public void throwRandomException(String component) {
        
        if (!shouldInjectChaos()) {
            return;
        }
        
        log.error("CHAOS: Throwing exception from {}", component);
        
        throw new ChaosException(
            "Simulated failure in " + component
        );
    }
    
    // Chaos Experiment 3: Database connection drop
    public void simulateDatabaseFailure() {
        
        if (!shouldInjectChaos()) {
            return;
        }
        
        log.error("CHAOS: Simulating database connection failure");
        
        // Close all database connections
        HikariDataSource dataSource = getDataSource();
        dataSource.getHikariPoolMXBean().softEvictConnections();
    }
    
    // Chaos Experiment 4: Redis cache unavailable
    public void simulateCacheFailure() {
        
        if (!shouldInjectChaos()) {
            return;
        }
        
        log.error("CHAOS: Simulating Redis unavailable");
        
        // Disconnect Redis
        redisConnectionFactory.getConnection().close();
    }
    
    private boolean shouldInjectChaos() {
        // 1% chance of chaos injection
        return random.nextDouble() < 0.01;
    }
}

@Aspect
@Component
public class ChaosAspect {
    
    @Autowired
    private ChaosEngineer chaosEngineer;
    
    @Around("@annotation(ChaosExperiment)")
    public Object injectChaos(ProceedingJoinPoint joinPoint) throws Throwable {
        
        // Inject latency before method execution
        chaosEngineer.injectLatency(
            joinPoint.getSignature().getName()
        );
        
        // Randomly throw exception (1% chance)
        chaosEngineer.throwRandomException(
            joinPoint.getSignature().getName()
        );
        
        // Execute method
        return joinPoint.proceed();
    }
}

@Service
public class BookingService {
    
    @ChaosExperiment
    public Booking createBooking(BookingRequest request) {
        // Method may experience chaos injection
        // Tests resilience: retries, circuit breaker, fallback
        
        return doCreateBooking(request);
    }
}
```

**Chaos Experiments Schedule:**

```
EXPERIMENT 1: Database Latency
═══════════════════════════════════════════════════════════
Goal: Test slow database response
Method: Add 2s delay to all DB queries
Duration: 10 minutes
Expected: Circuit breaker opens, app remains functional
Metrics: 
  - P99 latency should stay <5s
  - Error rate should stay <5%
  - No cascading failures


EXPERIMENT 2: Payment Gateway Failure
═══════════════════════════════════════════════════════════
Goal: Test payment gateway downtime
Method: Return 503 from Stripe mock
Duration: 5 minutes
Expected: 
  - Circuit breaker opens
  - Fallback to queue
  - Users see "payment processing" message
Metrics:
  - 0 lost bookings
  - Queue depth increases
  - Recovery within 1 minute after gateway restored


EXPERIMENT 3: Redis Cache Unavailable
═══════════════════════════════════════════════════════════
Goal: Test cache failure
Method: Stop Redis container
Duration: 15 minutes
Expected:
  - Graceful degradation (read from DB)
  - Latency increases but app functional
  - Cache automatically reconnects
Metrics:
  - P99 latency <1s (vs 100ms with cache)
  - Error rate <1%


EXPERIMENT 4: Pod Termination (Kubernetes)
═══════════════════════════════════════════════════════════
Goal: Test graceful shutdown
Method: kubectl delete pod (random)
Duration: Continuous (every 30 min)
Expected:
  - No dropped requests (load balancer drains)
  - New pod starts within 30s
  - Zero downtime
Metrics:
  - 0 failed requests during pod restart
```

---

## Key Takeaways:

```
Q51: Metrics & Monitoring
✅ Four Golden Signals (latency, traffic, errors, saturation)
✅ Business metrics (revenue, occupancy, conversion)
✅ System metrics (DB pool, thread pool, memory)
✅ Prometheus + Grafana

Q52: Distributed Tracing
✅ OpenTelemetry + Jaeger
✅ Trace request across services
✅ Identify bottlenecks (payment gateway 72% of latency)
✅ Parent/child span relationships

Q53: Centralized Logging
✅ ELK Stack (Elasticsearch, Logstash, Kibana)
✅ Structured logging (JSON)
✅ Correlation IDs for request tracking
✅ 30-day retention

Q54: Alerting
✅ Alert on symptoms, not causes
✅ Error rate >5% → Critical
✅ P99 latency >2s → Warning
✅ DB pool >95% → Critical
✅ Route critical → PagerDuty, warning → Slack

Q55: Chaos Engineering
✅ Inject latency (500-1500ms)
✅ Simulate failures (DB, Redis, payment gateway)
✅ Test circuit breaker, retries, fallback
✅ 1% chaos injection rate
✅ Scheduled experiments (DB latency, pod termination)
```

This demonstrates production observability expertise! 🎯
