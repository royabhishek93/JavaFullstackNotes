# Q37: Event Sourcing - Reconstruct booking state from events

### Difficulty: ⭐⭐⭐⭐⭐ (Principal)

### ✅ Solution: Event Store + Projections

```java
@Entity
@Table(name = "event_store")
public class BookingEventStore {
    
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    @Column(name = "aggregate_id")
    private String aggregateId;  // booking_id
    
    @Column(name = "event_type")
    private String eventType;
    
    @Column(name = "event_data", columnDefinition = "JSONB")
    private String eventData;
    
    @Column(name = "sequence_number")
    private Long sequenceNumber;
    
    @Column(name = "timestamp")
    private LocalDateTime timestamp;
    
    @Column(name = "user_id")
    private Long userId;
}

@Service
public class BookingEventSourcingService {
    
    private final EventStoreRepository eventStore;
    
    // Append event (never update!)
    public void appendEvent(BookingEvent event) {
        
        // Get next sequence number
        Long nextSequence = eventStore
            .findMaxSequenceByAggregateId(event.getBookingId())
            .map(seq -> seq + 1)
            .orElse(1L);
        
        BookingEventStore storeEvent = new BookingEventStore();
        storeEvent.setAggregateId(event.getBookingId());
        storeEvent.setEventType(event.getEventType());
        storeEvent.setEventData(JsonUtils.toJson(event));
        storeEvent.setSequenceNumber(nextSequence);
        storeEvent.setTimestamp(LocalDateTime.now());
        storeEvent.setUserId(event.getUserId());
        
        eventStore.save(storeEvent);
    }
    
    // Reconstruct current state from events
    public Booking reconstructBooking(String bookingId) {
        
        List<BookingEventStore> events = eventStore
            .findByAggregateIdOrderBySequenceNumber(bookingId);
        
        if (events.isEmpty()) {
            throw new BookingNotFoundException(bookingId);
        }
        
        // Start with empty booking
        Booking booking = new Booking();
        booking.setId(bookingId);
        
        // Apply each event in order
        for (BookingEventStore eventStore : events) {
            BookingEvent event = JsonUtils.fromJson(
                eventStore.getEventData(),
                BookingEvent.class
            );
            
            applyEvent(booking, event);
        }
        
        return booking;
    }
    
    private void applyEvent(Booking booking, BookingEvent event) {
        switch (event.getEventType()) {
            case "BOOKING_CREATED":
                booking.setUserId(event.getUserId());
                booking.setShowId(event.getShowId());
                booking.setTotalPrice(event.getTotalPrice());
                booking.setStatus(BookingStatus.PENDING);
                booking.setCreatedAt(event.getTimestamp());
                break;
                
            case "SEATS_RESERVED":
                booking.setSeatIds(event.getSeatIds());
                break;
                
            case "PAYMENT_COMPLETED":
                booking.setPaymentId(event.getPaymentId());
                booking.setStatus(BookingStatus.CONFIRMED);
                booking.setConfirmedAt(event.getTimestamp());
                break;
                
            case "BOOKING_CANCELLED":
                booking.setStatus(BookingStatus.CANCELLED);
                booking.setCancelledAt(event.getTimestamp());
                booking.setCancellationReason(event.getReason());
                break;
                
            case "BOOKING_EXPIRED":
                booking.setStatus(BookingStatus.EXPIRED);
                break;
        }
    }
}
```

**Event Timeline:**

```
BOOKING LIFECYCLE (Event Stream)
═══════════════════════════════════════════════════════════
Seq 1: BOOKING_CREATED
       { booking_id: "abc123", user_id: 456, show_id: 789, 
         price: 500, timestamp: "2026-01-01T10:00:00" }

Seq 2: SEATS_RESERVED
       { booking_id: "abc123", seat_ids: [5, 6], 
         expires_at: "2026-01-01T10:15:00" }

Seq 3: PAYMENT_COMPLETED
       { booking_id: "abc123", payment_id: "py_xyz", 
         amount: 500, timestamp: "2026-01-01T10:05:00" }

Seq 4: TICKET_GENERATED
       { booking_id: "abc123", ticket_id: "tk_123" }

Current State = Sum of all events ✅
```

**Snapshot Optimization:**

```java
@Entity
@Table(name = "booking_snapshot")
public class BookingSnapshot {
    
    @Id
    private String bookingId;
    
    @Column(columnDefinition = "JSONB")
    private String snapshotData;
    
    @Column(name = "snapshot_sequence")
    private Long snapshotSequence;  // Last event included
    
    @Column(name = "created_at")
    private LocalDateTime createdAt;
}

public Booking reconstructBookingOptimized(String bookingId) {
    
    // Step 1: Load latest snapshot (if exists)
    Optional<BookingSnapshot> snapshot = 
        snapshotRepository.findById(bookingId);
    
    Booking booking;
    Long startSequence;
    
    if (snapshot.isPresent()) {
        // Start from snapshot
        booking = JsonUtils.fromJson(
            snapshot.get().getSnapshotData(),
            Booking.class
        );
        startSequence = snapshot.get().getSnapshotSequence() + 1;
    } else {
        // Start from scratch
        booking = new Booking();
        booking.setId(bookingId);
        startSequence = 1L;
    }
    
    // Step 2: Apply only new events after snapshot
    List<BookingEventStore> newEvents = eventStore
        .findByAggregateIdAndSequenceNumberGreaterThanEqual(
            bookingId,
            startSequence
        );
    
    for (BookingEventStore event : newEvents) {
        applyEvent(booking, event);
    }
    
    return booking;
}

// Create snapshot every 100 events
@Scheduled(fixedRate = 60000)  // Every minute
public void createSnapshots() {
    
    List<String> bookingIds = eventStore
        .findBookingsNeedingSnapshot(100);  // >100 events since last snapshot
    
    for (String bookingId : bookingIds) {
        Booking booking = reconstructBooking(bookingId);
        
        Long maxSequence = eventStore
            .findMaxSequenceByAggregateId(bookingId)
            .orElse(0L);
        
        BookingSnapshot snapshot = new BookingSnapshot();
        snapshot.setBookingId(bookingId);
        snapshot.setSnapshotData(JsonUtils.toJson(booking));
        snapshot.setSnapshotSequence(maxSequence);
        snapshot.setCreatedAt(LocalDateTime.now());
        
        snapshotRepository.save(snapshot);
    }
}
```

---
