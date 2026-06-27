# Q09: Payment Webhook Handling - Stripe/Razorpay callbacks

### Difficulty: ⭐⭐⭐ (Senior)

### ✅ Solution:

```java
@RestController
@RequestMapping("/webhooks")
public class PaymentWebhookController {
    
    private final String webhookSecret = "whsec_...";
    
    @PostMapping("/stripe")
    public ResponseEntity<?> handleStripeWebhook(
            @RequestBody String payload,
            @RequestHeader("Stripe-Signature") String signature) {
        
        // Step 1: Verify webhook signature
        Event event;
        try {
            event = Webhook.constructEvent(
                payload, 
                signature, 
                webhookSecret
            );
        } catch (SignatureVerificationException e) {
            log.error("Invalid webhook signature");
            return ResponseEntity.status(400).build();
        }
        
        // Step 2: Handle event type
        switch (event.getType()) {
            case "payment_intent.succeeded":
                handlePaymentSuccess(event);
                break;
                
            case "payment_intent.payment_failed":
                handlePaymentFailure(event);
                break;
                
            case "charge.refunded":
                handleRefund(event);
                break;
                
            default:
                log.info("Unhandled event type: {}", event.getType());
        }
        
        return ResponseEntity.ok().build();
    }
    
    @Transactional
    private void handlePaymentSuccess(Event event) {
        PaymentIntent intent = (PaymentIntent) event
            .getDataObjectDeserializer()
            .getObject()
            .orElseThrow();
        
        String bookingId = intent.getMetadata().get("booking_id");
        
        // Idempotent confirmation
        Booking booking = bookingRepository.findById(bookingId)
            .orElseThrow();
        
        if (booking.getStatus() == BookingStatus.CONFIRMED) {
            log.info("Booking {} already confirmed", bookingId);
            return;  // Already processed
        }
        
        // Confirm booking
        booking.setStatus(BookingStatus.CONFIRMED);
        booking.setConfirmedAt(LocalDateTime.now());
        bookingRepository.save(booking);
        
        // Update seats
        seatRepository.updateStatusByBookingId(
            bookingId, 
            SeatStatus.BOOKED
        );
        
        // Generate ticket and notify
        ticketService.generate(bookingId);
        notificationService.sendConfirmation(booking.getUserId());
    }
}
```

---
