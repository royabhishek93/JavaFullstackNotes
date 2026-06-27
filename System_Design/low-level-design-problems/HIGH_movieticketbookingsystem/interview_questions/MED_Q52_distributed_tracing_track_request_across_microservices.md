# Q52: Distributed Tracing - Track request across microservices

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: OpenTelemetry + Jaeger

```java
@Configuration
public class TracingConfig {
    
    @Bean
    public OpenTelemetry openTelemetry() {
        
        Resource resource = Resource.getDefault()
            .merge(Resource.create(Attributes.of(
                ResourceAttributes.SERVICE_NAME, "bookmyshow-api",
                ResourceAttributes.SERVICE_VERSION, "1.0.0"
            )));
        
        JaegerGrpcSpanExporter jaegerExporter = 
            JaegerGrpcSpanExporter.builder()
                .setEndpoint("http://jaeger:14250")
                .build();
        
        SdkTracerProvider tracerProvider = SdkTracerProvider.builder()
            .addSpanProcessor(BatchSpanProcessor.builder(jaegerExporter).build())
            .setResource(resource)
            .build();
        
        return OpenTelemetrySdk.builder()
            .setTracerProvider(tracerProvider)
            .buildAndRegisterGlobal();
    }
}

@Service
public class TracedBookingService {
    
    private final Tracer tracer;
    
    public TracedBookingService(OpenTelemetry openTelemetry) {
        this.tracer = openTelemetry.getTracer("booking-service");
    }
    
    public Booking createBooking(BookingRequest request) {
        
        // Start parent span
        Span span = tracer.spanBuilder("createBooking")
            .setSpanKind(SpanKind.SERVER)
            .setAttribute("user.id", request.getUserId())
            .setAttribute("show.id", request.getShowId())
            .setAttribute("seat.count", request.getSeatIds().size())
            .startSpan();
        
        try (Scope scope = span.makeCurrent()) {
            
            // Child span: Validate seats
            Span validateSpan = tracer.spanBuilder("validateSeats")
                .startSpan();
            
            try (Scope validateScope = validateSpan.makeCurrent()) {
                validateSeats(request);
                validateSpan.setStatus(StatusCode.OK);
            } catch (Exception e) {
                validateSpan.recordException(e);
                validateSpan.setStatus(StatusCode.ERROR, e.getMessage());
                throw e;
            } finally {
                validateSpan.end();
            }
            
            // Child span: Reserve seats
            Span reserveSpan = tracer.spanBuilder("reserveSeats")
                .startSpan();
            
            try (Scope reserveScope = reserveSpan.makeCurrent()) {
                List<Seat> seats = reserveSeats(request);
                reserveSpan.setAttribute("seats.reserved", seats.size());
                reserveSpan.setStatus(StatusCode.OK);
            } finally {
                reserveSpan.end();
            }
            
            // Child span: Process payment
            Span paymentSpan = tracer.spanBuilder("processPayment")
                .setSpanKind(SpanKind.CLIENT)  // External call
                .setAttribute("payment.gateway", "stripe")
                .startSpan();
            
            try (Scope paymentScope = paymentSpan.makeCurrent()) {
                Payment payment = paymentService.processPayment(request);
                paymentSpan.setAttribute("payment.id", payment.getId());
                paymentSpan.setAttribute("payment.amount", 
                    payment.getAmount().doubleValue());
                paymentSpan.setStatus(StatusCode.OK);
            } finally {
                paymentSpan.end();
            }
            
            // Create booking
            Booking booking = doCreateBooking(request);
            
            span.setAttribute("booking.id", booking.getId());
            span.setStatus(StatusCode.OK);
            
            return booking;
            
        } catch (Exception e) {
            span.recordException(e);
            span.setStatus(StatusCode.ERROR, e.getMessage());
            throw e;
        } finally {
            span.end();
        }
    }
}
```

**Trace Example:**

```
TRACE ID: abc123def456
═══════════════════════════════════════════════════════════

createBooking [250ms]
├─ validateSeats [10ms]
│  └─ SQL: SELECT * FROM seat_availability [8ms]
├─ reserveSeats [50ms]
│  ├─ SQL: BEGIN TRANSACTION [1ms]
│  ├─ SQL: SELECT ... FOR UPDATE [30ms]
│  ├─ SQL: UPDATE seat_availability [15ms]
│  └─ SQL: COMMIT [4ms]
├─ processPayment [180ms] ← SLOW!
│  ├─ HTTP POST /stripe/charges [175ms] ← Culprit!
│  └─ Kafka: publish payment-event [5ms]
└─ SQL: INSERT INTO booking [10ms]

Analysis:
- Total: 250ms
- Payment gateway: 180ms (72% of total)
- Database: 60ms (24% of total)
- Other: 10ms (4% of total)

Action: Payment gateway timeout too high (reduce to 100ms)
```

---
