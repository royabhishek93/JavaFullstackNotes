# Q36: Kafka Architecture - Event streaming for bookings

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Kafka Event Streaming

```java
@Configuration
public class KafkaConfig {
    
    @Bean
    public ProducerFactory<String, BookingEvent> producerFactory() {
        Map<String, Object> config = new HashMap<>();
        config.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, 
                  "kafka-1:9092,kafka-2:9092,kafka-3:9092");
        config.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, 
                  StringSerializer.class);
        config.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, 
                  JsonSerializer.class);
        config.put(ProducerConfig.ACKS_CONFIG, "all");  // Wait for all replicas
        config.put(ProducerConfig.RETRIES_CONFIG, 3);
        config.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        
        return new DefaultKafkaProducerFactory<>(config);
    }
    
    @Bean
    public KafkaTemplate<String, BookingEvent> kafkaTemplate() {
        return new KafkaTemplate<>(producerFactory());
    }
}

@Service
public class BookingEventProducer {
    
    private final KafkaTemplate<String, BookingEvent> kafkaTemplate;
    
    private static final String TOPIC = "booking-events";
    
    public void publishBookingCreated(Booking booking) {
        
        BookingEvent event = BookingEvent.builder()
            .eventId(UUID.randomUUID().toString())
            .eventType("BOOKING_CREATED")
            .bookingId(booking.getId())
            .userId(booking.getUserId())
            .showId(booking.getShowId())
            .totalPrice(booking.getTotalPrice())
            .timestamp(LocalDateTime.now())
            .build();
        
        // Partition by user_id for ordering
        kafkaTemplate.send(
            TOPIC,
            booking.getUserId().toString(),  // Key for partitioning
            event
        );
        
        log.info("Published booking event: {}", event.getEventId());
    }
}
```

**Consumer (Email Service):**

```java
@Configuration
public class KafkaConsumerConfig {
    
    @Bean
    public ConsumerFactory<String, BookingEvent> consumerFactory() {
        Map<String, Object> config = new HashMap<>();
        config.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, 
                  "kafka-1:9092,kafka-2:9092,kafka-3:9092");
        config.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, 
                  StringDeserializer.class);
        config.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, 
                  JsonDeserializer.class);
        config.put(ConsumerConfig.GROUP_ID_CONFIG, "email-service");
        config.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        config.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);  // Manual commit
        config.put(ConsumerConfig.MAX_POLL_RECORDS_CONFIG, 100);
        
        return new DefaultKafkaConsumerFactory<>(config);
    }
    
    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, BookingEvent> 
            kafkaListenerContainerFactory() {
        
        ConcurrentKafkaListenerContainerFactory<String, BookingEvent> factory =
            new ConcurrentKafkaListenerContainerFactory<>();
        
        factory.setConsumerFactory(consumerFactory());
        factory.setConcurrency(3);  // 3 consumer threads
        factory.getContainerProperties()
            .setAckMode(ContainerProperties.AckMode.MANUAL_IMMEDIATE);
        
        return factory;
    }
}

@Component
public class BookingEventConsumer {
    
    private final EmailService emailService;
    
    @KafkaListener(
        topics = "booking-events",
        groupId = "email-service",
        containerFactory = "kafkaListenerContainerFactory"
    )
    public void consume(
            ConsumerRecord<String, BookingEvent> record,
            Acknowledgment acknowledgment) {
        
        BookingEvent event = record.value();
        
        try {
            if (event.getEventType().equals("BOOKING_CREATED")) {
                emailService.sendBookingConfirmation(
                    event.getUserId(),
                    event.getBookingId()
                );
            } else if (event.getEventType().equals("BOOKING_CANCELLED")) {
                emailService.sendCancellationEmail(
                    event.getUserId(),
                    event.getBookingId()
                );
            }
            
            // Manual commit after successful processing
            acknowledgment.acknowledge();
            
            log.info("Processed event: {}", event.getEventId());
            
        } catch (Exception e) {
            log.error("Failed to process event: {}", event.getEventId(), e);
            // Don't acknowledge, will retry
        }
    }
}
```

**Topic Configuration:**

```yaml
topics:
  booking-events:
    partitions: 10
    replication-factor: 3
    retention-ms: 604800000  # 7 days
    
  payment-events:
    partitions: 5
    replication-factor: 3
    retention-ms: 2592000000  # 30 days (compliance)
    
  notification-events:
    partitions: 20
    replication-factor: 3
    retention-ms: 86400000  # 1 day
```

**Kafka Architecture:**

```
PRODUCER (Booking Service)
═══════════════════════════════════════════════════════════
BookingService
    ↓ publish event
KafkaTemplate
    ↓ partition by user_id
Partition 0: user_id % 10 == 0
Partition 1: user_id % 10 == 1
...
Partition 9: user_id % 10 == 9


KAFKA CLUSTER
═══════════════════════════════════════════════════════════
Broker 1: Leader for partitions 0, 3, 6
Broker 2: Leader for partitions 1, 4, 7
Broker 3: Leader for partitions 2, 5, 8

Each partition: 3 replicas
Replication factor: 3
Min in-sync replicas: 2


CONSUMERS (Multiple Services)
═══════════════════════════════════════════════════════════
Group: email-service
├─ Consumer 1: Partitions 0, 1, 2
├─ Consumer 2: Partitions 3, 4, 5
└─ Consumer 3: Partitions 6, 7, 8, 9

Group: analytics-service
├─ Consumer 1: Partitions 0-4
└─ Consumer 2: Partitions 5-9

Group: notification-service
└─ Consumer 1: All partitions (10)
```

---
