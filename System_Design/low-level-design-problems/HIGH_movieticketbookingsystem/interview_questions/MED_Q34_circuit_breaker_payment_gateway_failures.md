# Q34: Circuit Breaker - Payment gateway failures

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Resilience4j Circuit Breaker

```java
@Configuration
public class CircuitBreakerConfig {
    
    @Bean
    public CircuitBreakerRegistry circuitBreakerRegistry() {
        CircuitBreakerConfig config = CircuitBreakerConfig.custom()
            .failureRateThreshold(50)  // Open if 50% fail
            .waitDurationInOpenState(Duration.ofSeconds(60))
            .permittedNumberOfCallsInHalfOpenState(10)
            .slidingWindowSize(100)
            .minimumNumberOfCalls(10)
            .build();
        
        return CircuitBreakerRegistry.of(config);
    }
}

@Service
public class PaymentService {
    
    private final CircuitBreaker circuitBreaker;
    private final StripeClient stripeClient;
    
    public PaymentService(CircuitBreakerRegistry registry) {
        this.circuitBreaker = registry.circuitBreaker("stripe");
        
        // Listen to state transitions
        circuitBreaker.getEventPublisher()
            .onStateTransition(event -> {
                log.warn("Circuit breaker state: {} → {}",
                    event.getStateTransition().getFromState(),
                    event.getStateTransition().getToState()
                );
                
                if (event.getStateTransition().getToState() 
                        == CircuitBreaker.State.OPEN) {
                    // Alert ops team
                    alertService.send(
                        "Payment Gateway Down",
                        "Stripe circuit breaker opened"
                    );
                }
            });
    }
    
    public PaymentResponse processPayment(PaymentRequest request) {
        
        // Wrap call in circuit breaker
        return circuitBreaker.executeSupplier(() -> {
            try {
                return stripeClient.charge(request);
            } catch (StripeException e) {
                log.error("Stripe payment failed", e);
                throw new PaymentGatewayException(e);
            }
        });
    }
}
```

**Circuit Breaker States:**

```
CLOSED (Normal Operation)
═══════════════════════════════════════════════════════════
All requests go through
Success rate: 90%
Failure rate: 10%
Status: ✅ Healthy

↓ Failure rate > 50%

OPEN (Gateway Down)
═══════════════════════════════════════════════════════════
All requests rejected immediately
No calls to gateway
Fast-fail with fallback
Status: ❌ Circuit open

↓ Wait 60 seconds

HALF-OPEN (Testing)
═══════════════════════════════════════════════════════════
Allow 10 test requests
If 50% succeed → CLOSED
If 50% fail → OPEN
Status: ⚠️ Testing

Timeline:
═══════════════════════════════════════════════════════════
10:00:00 - CLOSED (healthy)
10:05:00 - 50 failures in 100 requests
10:05:01 - OPEN (circuit breaker trips)
10:05:01-10:06:00 - All requests fast-fail
10:06:00 - HALF-OPEN (try 10 requests)
10:06:05 - 8/10 succeed
10:06:05 - CLOSED (back to normal) ✅
```

**Fallback Strategy:**

```java
@Service
public class PaymentServiceWithFallback {
    
    public PaymentResponse processPayment(PaymentRequest request) {
        
        try {
            return circuitBreaker.executeSupplier(() -> 
                stripeClient.charge(request)
            );
            
        } catch (CallNotPermittedException e) {
            // Circuit is open, use fallback
            log.warn("Circuit open, using fallback payment queue");
            
            return fallbackToQueue(request);
        }
    }
    
    private PaymentResponse fallbackToQueue(PaymentRequest request) {
        
        // Queue payment for later processing
        paymentQueueService.enqueue(request);
        
        // Show user pending status
        return PaymentResponse.builder()
            .status(PaymentStatus.PENDING)
            .message("Payment processing delayed. You'll receive confirmation shortly.")
            .estimatedTime("5-10 minutes")
            .build();
    }
}
```

**Monitoring:**

```java
@Component
public class CircuitBreakerMetrics {
    
    private final MeterRegistry meterRegistry;
    private final CircuitBreaker circuitBreaker;
    
    @Scheduled(fixedRate = 10000)  // Every 10 seconds
    public void recordMetrics() {
        
        CircuitBreaker.Metrics metrics = circuitBreaker.getMetrics();
        
        // Failure rate
        meterRegistry.gauge(
            "circuit_breaker.failure_rate",
            metrics.getFailureRate()
        );
        
        // Number of calls
        meterRegistry.gauge(
            "circuit_breaker.buffered_calls",
            metrics.getNumberOfBufferedCalls()
        );
        
        // State (0=closed, 1=open, 2=half-open)
        int stateValue = switch (circuitBreaker.getState()) {
            case CLOSED -> 0;
            case OPEN -> 1;
            case HALF_OPEN -> 2;
            default -> -1;
        };
        
        meterRegistry.gauge("circuit_breaker.state", stateValue);
    }
}
```

---
