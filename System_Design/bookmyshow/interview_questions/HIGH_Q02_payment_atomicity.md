# Question 2: Design the payment flow ensuring atomicity - seat reserved OR payment fails, never both

## Difficulty Level: ⭐⭐⭐⭐ (Senior/Staff)

## Expected Answer Duration: 8-10 minutes

---

## The Problem:

```
User books seats → Payment succeeds → Server crashes before confirming booking
Result: User charged, but no ticket! 💸😡
```

This is a **distributed transaction** problem across two systems:
1. **Your database** (booking state)
2. **Payment gateway** (Stripe, Razorpay, etc.)

---

## ❌ Naive Approach (WRONG):

```java
public Booking bookAndPay(BookingRequest request) {
    // Step 1: Create booking
    Booking booking = createBooking(request);
    bookingRepo.save(booking);  // Status: CONFIRMED ❌
    
    // Step 2: Charge payment
    Payment payment = paymentGateway.charge(booking.getTotalAmount());
    
    if (payment.isSuccess()) {
        return booking;
    } else {
        // Too late! Booking already confirmed
        // Seats are locked, but payment failed
        throw new PaymentFailedException();
    }
}
```

**Issues:**
- Seats confirmed before payment
- If payment fails, seats stay locked
- If server crashes between steps, inconsistent state

---

## ✅ Correct Approach: 3-Phase Commit (Saga Pattern)

```
┌─────────────────────────────────────────────────────────┐
│                 3-PHASE COMMIT PATTERN                   │
└─────────────────────────────────────────────────────────┘

PHASE 1: RESERVE          PHASE 2: CHARGE          PHASE 3: CONFIRM
─────────────────         ───────────────          ─────────────────
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Booking    │         │   Payment    │         │   Ticket     │
│   PENDING    │────────>│   PENDING    │────────>│  CONFIRMED   │
└──────────────┘         └──────────────┘         └──────────────┘
     │                         │                        │
     │ DB Write:               │ External Call:         │ DB Update:
     │ - Create booking        │ - Stripe.charge()      │ - booking.status
     │ - Lock seats            │ - Idempotent key       │ - payment.status
     │ - Set expiry            │ - Webhook registered   │ - Send email
     │   (15 mins)             │                        │ - Generate QR
     │                         │                        │
     │ Rollback if:            │ Rollback if:           │ Async:
     │ - Seats taken           │ - Payment fails        │ - Kafka event
     │ - Show full             │ - Timeout (retry)      │ - Analytics
     │                         │ - Declined card        │ - Push notification
     │                         │                        │
     │                    ┌────▼─────┐                 │
     │                    │ WEBHOOK  │                 │
     │                    │ Confirm  │─────────────────┘
     │                    └──────────┘
     │
     └──[Timeout 15 mins]──> Auto-cancel, release seats
```

---

## 💻 Production Implementation:

### **Phase 1: Reserve Seats**

```java
@Service
public class BookingService {
    
    @Transactional(isolation = Isolation.READ_COMMITTED)
    public BookingResponse reserveSeats(BookingRequest request) {
        
        // Lock and validate seats (from Question 1)
        List<SeatAvailability> seats = lockAndValidateSeats(
            request.getShowId(), 
            request.getSeatIds()
        );
        
        // Create booking with PENDING status
        Booking booking = Booking.builder()
            .id(UUID.randomUUID().toString())  // Idempotent ID
            .userId(request.getUserId())
            .showId(request.getShowId())
            .status(BookingStatus.PENDING)  // ← Key: Not confirmed yet
            .totalAmount(calculateAmount(seats))
            .createdAt(LocalDateTime.now())
            .expiresAt(LocalDateTime.now().plusMinutes(15))  // 15-min hold
            .build();
        
        bookingRepository.save(booking);
        
        // Link seats to booking
        List<BookingSeat> bookingSeats = seats.stream()
            .map(seat -> new BookingSeat(booking.getId(), seat.getId()))
            .collect(Collectors.toList());
        
        bookingSeatRepository.saveAll(bookingSeats);
        
        // Mark seats as RESERVED (not BOOKED)
        seats.forEach(seat -> {
            seat.setStatus(SeatStatus.RESERVED);
            seat.setReservedUntil(booking.getExpiresAt());
            seat.setBookingId(booking.getId());
        });
        
        seatAvailabilityRepository.saveAll(seats);
        
        // Commit transaction - seats are held for 15 minutes
        
        return BookingResponse.builder()
            .bookingId(booking.getId())
            .status("PENDING")
            .expiresIn(Duration.ofMinutes(15))
            .totalAmount(booking.getTotalAmount())
            .message("Seats reserved. Please complete payment within 15 minutes.")
            .build();
    }
}
```

---

### **Phase 2: Charge Payment**

```java
@Service
public class PaymentService {
    
    public PaymentResponse initiatePayment(String bookingId, PaymentRequest request) {
        
        // Step 1: Validate booking exists and not expired
        Booking booking = bookingRepository.findById(bookingId)
            .orElseThrow(() -> new BookingNotFoundException(bookingId));
        
        if (booking.isExpired()) {
            // Release seats automatically
            releaseExpiredBooking(booking);
            throw new BookingExpiredException("Booking expired. Seats released.");
        }
        
        if (booking.getStatus() != BookingStatus.PENDING) {
            throw new InvalidBookingStateException(
                "Booking already " + booking.getStatus()
            );
        }
        
        // Step 2: Generate idempotency key (prevents double charging)
        String idempotencyKey = generateIdempotencyKey(bookingId);
        
        // Step 3: Call payment gateway
        PaymentGatewayResponse gatewayResponse;
        
        try {
            gatewayResponse = stripeClient.charge(
                PaymentGatewayRequest.builder()
                    .amount(booking.getTotalAmount())
                    .currency("INR")
                    .customerId(booking.getUserId())
                    .paymentMethod(request.getPaymentMethod())
                    .idempotencyKey(idempotencyKey)  // ← Prevents double charge
                    .metadata(Map.of(
                        "booking_id", bookingId,
                        "show_id", booking.getShowId().toString()
                    ))
                    .build()
            );
            
        } catch (PaymentGatewayTimeoutException e) {
            // Payment status unknown - need to poll
            return handlePaymentTimeout(bookingId, idempotencyKey);
            
        } catch (PaymentDeclinedException e) {
            // Payment failed - release seats
            releaseBookingSeats(booking);
            throw e;
        }
        
        // Step 4: Record payment in our system
        Payment payment = Payment.builder()
            .id(UUID.randomUUID().toString())
            .bookingId(bookingId)
            .userId(booking.getUserId())
            .amount(booking.getTotalAmount())
            .paymentMode(request.getPaymentMethod())
            .transactionId(gatewayResponse.getTransactionId())
            .gatewayName("Stripe")
            .status(mapStatus(gatewayResponse.getStatus()))
            .idempotencyKey(idempotencyKey)
            .createdAt(LocalDateTime.now())
            .build();
        
        paymentRepository.save(payment);
        
        // Step 5: If payment successful, proceed to Phase 3
        if (payment.getStatus() == PaymentStatus.SUCCESS) {
            confirmBooking(booking, payment);
            return PaymentResponse.success(payment);
        } else {
            releaseBookingSeats(booking);
            return PaymentResponse.failure(payment);
        }
    }
}
```

---

### **Phase 3: Confirm Booking**

```java
@Transactional
public void confirmBooking(Booking booking, Payment payment) {
    
    // Update booking status
    booking.setStatus(BookingStatus.CONFIRMED);
    booking.setPaymentId(payment.getId());
    booking.setConfirmedAt(LocalDateTime.now());
    bookingRepository.save(booking);
    
    // Update seat status from RESERVED to BOOKED
    List<SeatAvailability> seats = seatAvailabilityRepository
        .findByBookingId(booking.getId());
    
    seats.forEach(seat -> seat.setStatus(SeatStatus.BOOKED));
    seatAvailabilityRepository.saveAll(seats);
    
    // Update show available count
    showRepository.decrementAvailableSeats(
        booking.getShowId(), 
        seats.size()
    );
    
    // Commit transaction
    
    // Async operations (outside transaction)
    asyncOperations(booking, payment);
}

@Async
public void asyncOperations(Booking booking, Payment payment) {
    
    // 1. Generate QR ticket
    Ticket ticket = ticketGenerator.generate(booking);
    
    // 2. Send confirmation email
    emailService.sendBookingConfirmation(
        booking.getUserId(), 
        booking, 
        ticket
    );
    
    // 3. Send SMS
    smsService.sendConfirmation(booking.getUserId(), booking.getId());
    
    // 4. Publish Kafka event
    kafkaProducer.send("booking.confirmed", 
        new BookingConfirmedEvent(booking.getId(), booking.getShowId())
    );
    
    // 5. Invalidate cache
    redisCache.delete("show:" + booking.getShowId() + ":seats");
    
    // 6. Publish real-time update
    redisPublisher.publish("show:" + booking.getShowId() + ":update",
        new SeatUpdateEvent(booking.getShowId())
    );
}
```

---

## 🔥 Handling Failure Scenarios:

### **Scenario 1: Payment Success, Server Crashes Before Confirm**

```
Timeline:
10:00:00 - User pays $50
10:00:01 - Stripe charges card successfully
10:00:02 - 💥 Server crashes before updating booking status
10:00:03 - Server restarts

Result: User charged, booking status still PENDING

Solution: Stripe Webhook
```

**Implementation:**

```java
@RestController
@RequestMapping("/webhooks/stripe")
public class StripeWebhookController {
    
    @PostMapping
    public ResponseEntity<?> handleWebhook(
            @RequestBody String payload,
            @RequestHeader("Stripe-Signature") String signature) {
        
        // Verify webhook authenticity
        Event event = Webhook.constructEvent(
            payload, signature, webhookSecret
        );
        
        if (event.getType().equals("charge.succeeded")) {
            ChargeSucceededEvent chargeEvent = 
                (ChargeSucceededEvent) event.getDataObjectDeserializer()
                    .getObject().get();
            
            String bookingId = chargeEvent.getMetadata().get("booking_id");
            
            // Idempotent confirmation (safe to call multiple times)
            confirmBookingIfNeeded(bookingId, chargeEvent.getId());
        }
        
        return ResponseEntity.ok().build();
    }
    
    @Transactional
    public void confirmBookingIfNeeded(String bookingId, String transactionId) {
        
        Booking booking = bookingRepository.findById(bookingId)
            .orElseThrow();
        
        // Idempotency check
        if (booking.getStatus() == BookingStatus.CONFIRMED) {
            log.info("Booking {} already confirmed. Skipping.", bookingId);
            return;  // Already processed
        }
        
        // Find or create payment record
        Payment payment = paymentRepository
            .findByTransactionId(transactionId)
            .orElseGet(() -> createPaymentFromWebhook(booking, transactionId));
        
        // Confirm booking
        confirmBooking(booking, payment);
    }
}
```

**Stripe Retry Policy:**
- Retries webhook up to 10 times
- Exponential backoff (1h, 2h, 4h... up to 3 days)
- Eventually consistent

---

### **Scenario 2: Double Submission (User Clicks "Pay" Twice)**

```
Timeline:
10:00:00 - User clicks "Pay Now"
10:00:01 - Request 1 sent to Stripe
10:00:05 - User impatient, clicks "Pay Now" again
10:00:06 - Request 2 sent to Stripe

Without protection: Charged twice! 💸💸

With idempotency key: Stripe returns cached response from Request 1
```

**Idempotency Key Generation:**

```java
private String generateIdempotencyKey(String bookingId) {
    // Deterministic key per booking
    return "booking_" + bookingId + "_payment_attempt";
}

// Alternative: Include attempt number
private String generateIdempotencyKeyWithAttempt(String bookingId, int attempt) {
    return "booking_" + bookingId + "_attempt_" + attempt;
}
```

**Stripe Behavior:**
```
Request 1: idempotency_key = "booking_999_payment_attempt"
→ Stripe processes, returns: {charge_id: "ch_123", status: "succeeded"}

Request 2: idempotency_key = "booking_999_payment_attempt" (same!)
→ Stripe returns cached response: {charge_id: "ch_123", status: "succeeded"}
→ No double charge! ✅
```

---

### **Scenario 3: Payment Timeout (Network Issue)**

```
Timeline:
10:00:00 - Send payment request to Stripe
10:00:30 - No response (timeout after 30s)
10:00:31 - Status unknown: Did Stripe charge the card?

Solution: Poll Stripe API to check status
```

**Implementation:**

```java
private PaymentResponse handlePaymentTimeout(String bookingId, String idempotencyKey) {
    
    log.warn("Payment timeout for booking {}. Polling Stripe...", bookingId);
    
    // Poll Stripe with exponential backoff
    for (int attempt = 1; attempt <= 5; attempt++) {
        
        try {
            Thread.sleep(Duration.ofSeconds((long) Math.pow(2, attempt)).toMillis());
            
            // Check payment status
            PaymentIntent paymentIntent = stripeClient.retrievePaymentIntent(
                idempotencyKey
            );
            
            if (paymentIntent.getStatus().equals("succeeded")) {
                // Payment succeeded!
                Payment payment = recordSuccessfulPayment(bookingId, paymentIntent);
                confirmBooking(bookingRepository.findById(bookingId).get(), payment);
                return PaymentResponse.success(payment);
                
            } else if (paymentIntent.getStatus().equals("failed")) {
                // Payment failed
                releaseBookingSeats(bookingRepository.findById(bookingId).get());
                return PaymentResponse.failure(paymentIntent.getFailureReason());
            }
            
            // Still processing, continue polling
            
        } catch (Exception e) {
            log.error("Polling attempt {} failed", attempt, e);
        }
    }
    
    // After 5 attempts, mark as PENDING_VERIFICATION
    // Manual review or webhook will resolve later
    return PaymentResponse.pendingVerification(
        "Payment status unclear. You won't be charged if booking fails."
    );
}
```

---

### **Scenario 4: Seat Expiry (User Abandons Payment)**

```
Timeline:
10:00:00 - User reserves seats (15-min hold)
10:15:00 - Timer expires, user never paid
10:15:01 - Background job releases seats

Solution: Scheduled job
```

**Implementation:**

```java
@Component
public class SeatExpiryJob {
    
    @Scheduled(cron = "0 */5 * * * *")  // Every 5 minutes
    public void releaseExpiredSeats() {
        
        LocalDateTime now = LocalDateTime.now();
        
        // Find expired PENDING bookings
        List<Booking> expiredBookings = bookingRepository
            .findByStatusAndExpiresAtBefore(BookingStatus.PENDING, now);
        
        log.info("Found {} expired bookings", expiredBookings.size());
        
        for (Booking booking : expiredBookings) {
            try {
                releaseExpiredBooking(booking);
            } catch (Exception e) {
                log.error("Failed to release booking {}", booking.getId(), e);
            }
        }
    }
    
    @Transactional
    public void releaseExpiredBooking(Booking booking) {
        
        // Update booking status
        booking.setStatus(BookingStatus.EXPIRED);
        booking.setExpiredAt(LocalDateTime.now());
        bookingRepository.save(booking);
        
        // Release seats
        List<SeatAvailability> seats = seatAvailabilityRepository
            .findByBookingId(booking.getId());
        
        seats.forEach(seat -> {
            seat.setStatus(SeatStatus.AVAILABLE);
            seat.setReservedUntil(null);
            seat.setBookingId(null);
        });
        
        seatAvailabilityRepository.saveAll(seats);
        
        // Restore show available count
        showRepository.incrementAvailableSeats(
            booking.getShowId(), 
            seats.size()
        );
        
        // Notify user
        notificationService.sendBookingExpiredNotification(
            booking.getUserId(), 
            booking.getId()
        );
        
        // Invalidate cache
        redisCache.delete("show:" + booking.getShowId() + ":seats");
    }
}
```

---

## 🎯 Database Schema for Payment Atomicity:

```sql
CREATE TABLE booking (
    id VARCHAR(36) PRIMARY KEY,
    user_id BIGINT NOT NULL,
    show_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,  -- PENDING, CONFIRMED, EXPIRED, CANCELLED
    total_amount DECIMAL(10,2) NOT NULL,
    payment_id VARCHAR(36),  -- NULL until payment succeeds
    created_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    confirmed_at TIMESTAMP,
    
    INDEX idx_status_expires (status, expires_at),  -- For expiry job
    INDEX idx_user_created (user_id, created_at DESC)
);

CREATE TABLE payment (
    id VARCHAR(36) PRIMARY KEY,
    booking_id VARCHAR(36) NOT NULL UNIQUE,  -- 1:1 relationship
    user_id BIGINT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_mode VARCHAR(50) NOT NULL,
    transaction_id VARCHAR(255) UNIQUE,  -- From gateway
    gateway_name VARCHAR(50) NOT NULL,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,  -- Prevents duplicates
    status VARCHAR(20) NOT NULL,  -- PENDING, SUCCESS, FAILED, REFUNDED
    failure_reason TEXT,
    created_at TIMESTAMP NOT NULL,
    processed_at TIMESTAMP,
    refunded_at TIMESTAMP,
    
    FOREIGN KEY (booking_id) REFERENCES booking(id),
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_idempotency_key (idempotency_key)
);

CREATE TABLE seat_availability (
    show_id BIGINT NOT NULL,
    seat_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,  -- AVAILABLE, RESERVED, BOOKED
    reserved_until TIMESTAMP,  -- NULL if AVAILABLE or BOOKED
    booking_id VARCHAR(36),
    updated_at TIMESTAMP NOT NULL,
    
    PRIMARY KEY (show_id, seat_id),
    FOREIGN KEY (booking_id) REFERENCES booking(id),
    INDEX idx_booking_id (booking_id)
);
```

---

## 📊 State Transition Diagram:

```
                    BOOKING STATE MACHINE
                    
    ┌─────────────────────────────────────────────────────┐
    │                                                      │
    │  START                                               │
    │    │                                                 │
    │    │ User selects seats                              │
    │    ▼                                                 │
    │  ┌──────────┐                                        │
    │  │ PENDING  │ ◄────────┐                             │
    │  └────┬─────┘          │                             │
    │       │                │                             │
    │       │ Payment        │ Webhook retry               │
    │       │ initiated      │ (if server crashed)         │
    │       ▼                │                             │
    │  ┌──────────┐          │                             │
    │  │ PAYING   │──────────┘                             │
    │  └────┬─────┘                                        │
    │       │                                              │
    │       ├────── Success ─────────┐                     │
    │       │                        │                     │
    │       │                        ▼                     │
    │       │                   ┌──────────┐               │
    │       │                   │CONFIRMED │ (Final)       │
    │       │                   └──────────┘               │
    │       │                                              │
    │       ├────── Failure ─────────┐                     │
    │       │                        │                     │
    │       │                        ▼                     │
    │       │                   ┌──────────┐               │
    │       │                   │CANCELLED │ (Final)       │
    │       │                   └──────────┘               │
    │       │                                              │
    │       │                                              │
    │       └────── Timeout (15 min) ────┐                 │
    │                                    │                 │
    │                                    ▼                 │
    │                               ┌──────────┐           │
    │                               │ EXPIRED  │ (Final)   │
    │                               └──────────┘           │
    │                                                      │
    └─────────────────────────────────────────────────────┘
```

---

## 🔥 Advanced: Saga Pattern with Compensation

For complex flows with multiple services:

```java
@Service
public class BookingSaga {
    
    public BookingResponse executeBookingSaga(BookingRequest request) {
        
        SagaContext context = new SagaContext();
        
        try {
            // Step 1: Reserve seats
            ReservationResult reservation = reserveSeats(request);
            context.addCompensation(() -> releaseSeats(reservation.getBookingId()));
            
            // Step 2: Validate user credit
            creditCheck(request.getUserId(), reservation.getTotalAmount());
            // No compensation needed (read-only)
            
            // Step 3: Charge payment
            PaymentResult payment = chargePayment(reservation, request.getPaymentMethod());
            context.addCompensation(() -> refundPayment(payment.getPaymentId()));
            
            // Step 4: Confirm booking
            confirmBooking(reservation.getBookingId(), payment.getPaymentId());
            
            // Success - no compensation needed
            return BookingResponse.success(reservation);
            
        } catch (Exception e) {
            // Execute compensations in reverse order
            context.compensate();
            throw new BookingSagaException("Booking failed", e);
        }
    }
}
```

---

## 💡 Key Takeaways for Interview:

1. ✅ **3-Phase Commit**: Reserve → Charge → Confirm
2. ✅ **Idempotency**: Prevent double charges with unique keys
3. ✅ **Webhook**: Handle server crashes during payment
4. ✅ **Expiry Logic**: Release seats if user abandons
5. ✅ **Polling**: Handle payment gateway timeouts
6. ✅ **State Machine**: Clear booking status transitions

**Closing Statement:**
> "In production, payment atomicity requires a saga pattern: reserve seats (PENDING), charge payment gateway with idempotency keys, then confirm booking. Stripe webhooks handle server crashes, background jobs release expired bookings, and comprehensive logging enables audit trails. This ensures users are never charged without receiving tickets."

This demonstrates deep experience with distributed transactions! 🎯
