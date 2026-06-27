# Q53: Centralized Logging - ELK Stack for log aggregation

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: Logback + Elasticsearch + Kibana

```xml
<!-- logback-spring.xml -->
<configuration>
    
    <!-- Console appender for local dev -->
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>
    
    <!-- Logstash appender for production -->
    <appender name="LOGSTASH" class="net.logstash.logback.appender.LogstashTcpSocketAppender">
        <destination>logstash:5000</destination>
        
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <customFields>{"app":"bookmyshow","env":"production"}</customFields>
        </encoder>
    </appender>
    
    <!-- File appender (backup) -->
    <appender name="FILE" class="ch.qos.logback.core.rolling.RollingFileAppender">
        <file>/var/log/bookmyshow/application.log</file>
        
        <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
            <fileNamePattern>/var/log/bookmyshow/application-%d{yyyy-MM-dd}.log</fileNamePattern>
            <maxHistory>30</maxHistory>
            <totalSizeCap>10GB</totalSizeCap>
        </rollingPolicy>
        
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>
    
    <root level="INFO">
        <appender-ref ref="CONSOLE" />
        <appender-ref ref="LOGSTASH" />
        <appender-ref ref="FILE" />
    </root>
    
</configuration>
```

**Structured Logging:**

```java
@Service
public class StructuredLoggingService {
    
    private static final Logger log = LoggerFactory.getLogger(
        StructuredLoggingService.class
    );
    
    public void logBookingCreated(Booking booking) {
        
        // Structured log (JSON)
        log.info("Booking created",
            kv("event", "booking_created"),
            kv("booking_id", booking.getId()),
            kv("user_id", booking.getUserId()),
            kv("show_id", booking.getShowId()),
            kv("seats", booking.getTotalSeats()),
            kv("price", booking.getTotalPrice()),
            kv("timestamp", LocalDateTime.now())
        );
        
        // Elasticsearch output:
        // {
        //   "event": "booking_created",
        //   "booking_id": "abc123",
        //   "user_id": 456,
        //   "show_id": 789,
        //   "seats": 2,
        //   "price": 500,
        //   "timestamp": "2026-01-01T10:00:00",
        //   "app": "bookmyshow",
        //   "env": "production",
        //   "level": "INFO"
        // }
    }
    
    public void logPaymentFailed(Payment payment, Exception e) {
        
        log.error("Payment failed",
            kv("event", "payment_failed"),
            kv("payment_id", payment.getId()),
            kv("booking_id", payment.getBookingId()),
            kv("amount", payment.getAmount()),
            kv("gateway", payment.getPaymentGateway()),
            kv("error_type", e.getClass().getSimpleName()),
            kv("error_message", e.getMessage()),
            kv("trace_id", MDC.get("trace_id"))
        );
    }
}
```

**Kibana Queries:**

```
# Find all booking errors in last 1 hour
event:booking_* AND level:ERROR AND @timestamp:[now-1h TO now]

# Payment failures by gateway
event:payment_failed | stats count by gateway

# Slow bookings (>1 second)
event:booking_created AND duration:>1000 | sort duration desc

# Top users by booking count
event:booking_created | stats count by user_id | sort count desc | head 10
```

---
