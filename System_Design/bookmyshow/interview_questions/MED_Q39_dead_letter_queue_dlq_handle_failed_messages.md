# Q39: Dead Letter Queue (DLQ) - Handle failed messages

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution: DLQ with Retry Logic

```java
@Configuration
public class KafkaRetryConfig {
    
    @Bean
    public ConsumerFactory<String, BookingEvent> retryConsumerFactory() {
        Map<String, Object> config = new HashMap<>();
        // ... standard config
        config.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 10);
        return new DefaultKafkaConsumerFactory<>(config);
    }
    
    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, BookingEvent>
            retryKafkaListenerContainerFactory() {
        
        ConcurrentKafkaListenerContainerFactory<String, BookingEvent> factory =
            new ConcurrentKafkaListenerContainerFactory<>();
        
        factory.setConsumerFactory(retryConsumerFactory());
        
        // Configure retry
        factory.setCommonErrorHandler(
            new DefaultErrorHandler(
                new DeadLetterPublishingRecoverer(kafkaTemplate()),
                new FixedBackOff(1000L, 3)  // 3 retries, 1s interval
            )
        );
        
        return factory;
    }
}

@Component
public class EmailConsumerWithRetry {
    
    private final EmailService emailService;
    
    @KafkaListener(
        topics = "booking-events",
        groupId = "email-service",
        containerFactory = "retryKafkaListenerContainerFactory"
    )
    @RetryableTopic(
        attempts = "3",
        backoff = @Backoff(delay = 1000, multiplier = 2),
        include = {EmailDeliveryException.class},
        dltTopicSuffix = "-dlt"
    )
    public void consume(BookingEvent event) {
        
        try {
            emailService.send(event);
            log.info("Email sent for booking: {}", event.getBookingId());
            
        } catch (EmailDeliveryException e) {
            log.error("Failed to send email", e);
            throw e;  // Will be retried
        }
    }
    
    // Dead Letter Topic Consumer
    @KafkaListener(
        topics = "booking-events-dlt",
        groupId = "email-service-dlt"
    )
    public void consumeDLT(BookingEvent event) {
        
        log.error("Message moved to DLT: {}", event.getEventId());
        
        // Store in database for manual processing
        failedMessageRepository.save(
            FailedMessage.builder()
                .topic("booking-events")
                .message(JsonUtils.toJson(event))
                .reason("Max retries exceeded")
                .createdAt(LocalDateTime.now())
                .build()
        );
        
        // Alert ops team
        alertService.send(
            "DLT Message",
            "Failed to process event after 3 retries: " + event.getEventId()
        );
    }
}
```

**Retry Timeline:**

```
MESSAGE PROCESSING WITH RETRY
═══════════════════════════════════════════════════════════
10:00:00 - Attempt 1: FAILED (EmailDeliveryException)
10:00:01 - Attempt 2: FAILED (wait 1s)
10:00:03 - Attempt 3: FAILED (wait 2s, exponential backoff)
10:00:07 - Attempt 4: FAILED (wait 4s)
10:00:11 - Move to DLQ (max 3 retries exceeded)

DLQ Consumer:
10:00:12 - Store in failed_messages table
10:00:13 - Alert ops team
```

---
