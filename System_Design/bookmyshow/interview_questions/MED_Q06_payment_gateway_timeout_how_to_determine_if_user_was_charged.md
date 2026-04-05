# Q06: Payment Gateway Timeout - How to determine if user was charged?

### Difficulty: ⭐⭐⭐⭐ (Staff)

### The Problem:
```
User clicks "Pay" → Request sent to Stripe → 30 seconds... no response
Status: Unknown (charged? not charged?)
```

### ✅ Solution: Poll Gateway + Webhook + Idempotency

```java
@Service
public class PaymentRecoveryService {
    
    public PaymentResponse handlePaymentTimeout(
            String bookingId, 
            String idempotencyKey) {
        
        log.warn("Payment timeout for booking: {}", bookingId);
        
        // Poll Stripe with exponential backoff
        for (int attempt = 1; attempt <= 5; attempt++) {
            
            try {
                // Check payment status using idempotency key
                PaymentIntent intent = stripeClient
                    .retrieveByIdempotencyKey(idempotencyKey);
                
                if (intent.getStatus().equals("succeeded")) {
                    // Payment went through!
                    confirmBooking(bookingId, intent.getId());
                    return PaymentResponse.success(intent);
                    
                } else if (intent.getStatus().equals("failed")) {
                    // Payment failed
                    releaseSeats(bookingId);
                    return PaymentResponse.failure(intent);
                }
                
                // Still processing, continue polling
                
            } catch (NotFoundException e) {
                // Payment never reached Stripe
                // Safe to retry
                return PaymentResponse.retry();
            }
            
            // Exponential backoff: 1s, 2s, 4s, 8s, 16s
            Thread.sleep(Duration.ofSeconds(1L << attempt).toMillis());
        }
        
        // After 5 attempts, mark as PENDING_VERIFICATION
        // Webhook will eventually resolve
        return PaymentResponse.pendingVerification();
    }
}
```

**Timeline:**
```
10:00:00 - User pays
10:00:30 - Timeout (no response)
10:00:31 - Poll #1: Check Stripe status
10:00:33 - Poll #2: Still processing
10:00:37 - Poll #3: Success! Charge confirmed
10:00:37 - Confirm booking
10:00:38 - Send email

If all polls fail:
- Mark booking as PENDING_VERIFICATION
- Webhook will resolve within 1 hour
- User sees: "Payment processing, check email"
```

---
