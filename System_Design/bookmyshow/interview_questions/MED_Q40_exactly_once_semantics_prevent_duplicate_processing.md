# Q40: Exactly-Once Semantics - Prevent duplicate processing

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Idempotent Consumer

```java
@Component
public class IdempotentEmailConsumer {
    
    private final EmailService emailService;
    private final ProcessedMessageRepository processedRepository;
    
    @KafkaListener(topics = "booking-events", groupId = "email-service")
    @Transactional
    public void consume(BookingEvent event, Acknowledgment ack) {
        
        String messageId = event.getEventId();
        
        // Check if already processed (idempotency check)
        boolean alreadyProcessed = processedRepository
            .existsByMessageId(messageId);
        
        if (alreadyProcessed) {
            log.info("Message already processed: {}", messageId);
            ack.acknowledge();
            return;  // Skip duplicate
        }
        
        try {
            // Process message
            emailService.send(event);
            
            // Mark as processed (atomic with business logic)
            ProcessedMessage processed = new ProcessedMessage();
            processed.setMessageId(messageId);
            processed.setTopic("booking-events");
            processed.setProcessedAt(LocalDateTime.now());
            processedRepository.save(processed);
            
            // Commit offset
            ack.acknowledge();
            
            log.info("Message processed: {}", messageId);
            
        } catch (Exception e) {
            log.error("Failed to process message: {}", messageId, e);
            // Don't acknowledge, will be redelivered
            throw e;
        }
    }
}

@Entity
@Table(name = "processed_messages")
public class ProcessedMessage {
    
    @Id
    @Column(name = "message_id")
    private String messageId;
    
    @Column(name = "topic")
    private String topic;
    
    @Column(name = "processed_at")
    private LocalDateTime processedAt;
    
    @Column(name = "expires_at")
    private LocalDateTime expiresAt;  // Auto-cleanup after 7 days
}

// Cleanup job
@Scheduled(cron = "0 0 3 * * *")  // 3 AM daily
public void cleanupProcessedMessages() {
    int deleted = processedRepository
        .deleteByExpiresAtBefore(LocalDateTime.now());
    
    log.info("Cleaned up {} old processed messages", deleted);
}
```

**Kafka Exactly-Once (Transactional Producer):**

```java
@Configuration
public class KafkaTransactionalConfig {
    
    @Bean
    public ProducerFactory<String, BookingEvent> transactionalProducerFactory() {
        Map<String, Object> config = new HashMap<>();
        config.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "...");
        config.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "booking-producer-1");
        config.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        config.put(ProducerConfig.ACKS_CONFIG, "all");
        
        return new DefaultKafkaProducerFactory<>(config);
    }
}

@Service
public class TransactionalEventPublisher {
    
    @Autowired
    @Qualifier("transactionalKafkaTemplate")
    private KafkaTemplate<String, BookingEvent> kafkaTemplate;
    
    @Transactional
    public void publishWithTransaction(BookingEvent event) {
        
        // Begin Kafka transaction
        kafkaTemplate.executeInTransaction(ops -> {
            
            // Publish event
            ops.send("booking-events", event.getBookingId(), event);
            
            // Database changes and Kafka publish are atomic!
            // If DB fails, Kafka message won't be sent
            // If Kafka fails, DB transaction will rollback
            
            return null;
        });
    }
}
```

---

## Key Takeaways:

```
Q36: Kafka Architecture
✅ Partitioning by user_id (ordering)
✅ Replication factor 3 (durability)
✅ Manual commit (at-least-once)
✅ Multiple consumer groups

Q37: Event Sourcing
✅ Append-only event store
✅ Reconstruct state from events
✅ Snapshots every 100 events
✅ Audit trail for free

Q38: Saga Pattern
✅ Choreography (event-driven)
✅ Compensating transactions
✅ 4-step workflow (create → reserve → pay → confirm)
✅ Handle failures gracefully

Q39: Dead Letter Queue
✅ 3 retries with exponential backoff
✅ Move to DLT after max retries
✅ Alert ops team
✅ Store for manual processing

Q40: Exactly-Once Semantics
✅ Idempotent consumer (deduplication table)
✅ Transactional producer (Kafka transactions)
✅ Atomic: DB + Kafka
✅ Cleanup old records (7 days)
```

This demonstrates production message queue expertise! 🎯
