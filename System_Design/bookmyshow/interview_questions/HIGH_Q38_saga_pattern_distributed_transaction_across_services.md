# Q38: Saga Pattern - Distributed transaction across services

### Difficulty: ⭐⭐⭐⭐⭐ (Principal)

### ✅ Solution: Choreography-Based Saga

```java
// Step 1: Booking Service creates booking
@Service
public class BookingSagaService {
    
    @Transactional
    public void initiateBookingSaga(BookingRequest request) {
        
        // Create booking (PENDING)
        Booking booking = new Booking();
        booking.setStatus(BookingStatus.PENDING);
        bookingRepository.save(booking);
        
        // Publish event
        eventPublisher.publish(new BookingCreatedEvent(booking));
    }
}

// Step 2: Seat Service reserves seats
@Component
public class SeatReservationListener {
    
    @KafkaListener(topics = "booking-events")
    public void onBookingCreated(BookingCreatedEvent event) {
        
        try {
            // Reserve seats
            List<Seat> seats = seatService.reserve(
                event.getShowId(),
                event.getSeatIds()
            );
            
            // Success: Publish event
            eventPublisher.publish(
                new SeatsReservedEvent(event.getBookingId(), seats)
            );
            
        } catch (SeatUnavailableException e) {
            // Failure: Publish compensation event
            eventPublisher.publish(
                new SeatReservationFailedEvent(
                    event.getBookingId(),
                    e.getMessage()
                )
            );
        }
    }
}

// Step 3: Payment Service processes payment
@Component
public class PaymentListener {
    
    @KafkaListener(topics = "seat-events")
    public void onSeatsReserved(SeatsReservedEvent event) {
        
        try {
            // Process payment
            Payment payment = paymentService.charge(
                event.getBookingId(),
                event.getAmount()
            );
            
            // Success: Publish event
            eventPublisher.publish(
                new PaymentCompletedEvent(event.getBookingId(), payment)
            );
            
        } catch (PaymentFailedException e) {
            // Failure: Publish compensation event
            eventPublisher.publish(
                new PaymentFailedEvent(
                    event.getBookingId(),
                    e.getMessage()
                )
            );
        }
    }
}

// Step 4: Booking Service confirms or cancels
@Component
public class BookingConfirmationListener {
    
    @KafkaListener(topics = "payment-events")
    public void onPaymentCompleted(PaymentCompletedEvent event) {
        
        // Confirm booking
        Booking booking = bookingRepository
            .findById(event.getBookingId())
            .orElseThrow();
        
        booking.setStatus(BookingStatus.CONFIRMED);
        bookingRepository.save(booking);
        
        // Publish final event
        eventPublisher.publish(
            new BookingConfirmedEvent(event.getBookingId())
        );
    }
    
    @KafkaListener(topics = "payment-events")
    public void onPaymentFailed(PaymentFailedEvent event) {
        
        // Cancel booking
        Booking booking = bookingRepository
            .findById(event.getBookingId())
            .orElseThrow();
        
        booking.setStatus(BookingStatus.CANCELLED);
        bookingRepository.save(booking);
        
        // Trigger compensating transactions
        eventPublisher.publish(
            new BookingCancelledEvent(event.getBookingId())
        );
    }
}

// Compensating Transaction: Release seats
@Component
public class SeatReleaseListener {
    
    @KafkaListener(topics = "booking-events")
    public void onBookingCancelled(BookingCancelledEvent event) {
        
        // Release reserved seats
        seatService.release(event.getBookingId());
        
        log.info("Compensating transaction: Seats released for booking {}",
                 event.getBookingId());
    }
}
```

**Saga State Machine:**

```
HAPPY PATH
═══════════════════════════════════════════════════════════
1. BOOKING_CREATED        (Booking Service)
   ↓
2. SEATS_RESERVED         (Seat Service)
   ↓
3. PAYMENT_COMPLETED      (Payment Service)
   ↓
4. BOOKING_CONFIRMED      (Booking Service)


FAILURE PATH (Payment Fails)
═══════════════════════════════════════════════════════════
1. BOOKING_CREATED        (Booking Service)
   ↓
2. SEATS_RESERVED         (Seat Service)
   ↓
3. PAYMENT_FAILED         (Payment Service) ❌
   ↓
4. BOOKING_CANCELLED      (Booking Service)
   ↓
5. SEATS_RELEASED         (Seat Service) ← Compensation


FAILURE PATH (Seats Unavailable)
═══════════════════════════════════════════════════════════
1. BOOKING_CREATED        (Booking Service)
   ↓
2. SEAT_RESERVATION_FAILED (Seat Service) ❌
   ↓
3. BOOKING_CANCELLED      (Booking Service)
```

---
