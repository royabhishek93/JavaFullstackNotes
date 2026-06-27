# Q46: PCI Compliance - Handle credit card data securely

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: Never Store Card Data - Use Payment Gateway Tokens

```java
@Service
public class PCICompliantPaymentService {
    
    private final StripeClient stripeClient;
    
    // NEVER do this! ❌
    // private String cardNumber;
    // private String cvv;
    // private String expiryDate;
    
    public PaymentResponse processPayment(PaymentRequest request) {
        
        // Step 1: Frontend collects card data via Stripe.js
        // Card data NEVER touches our servers! ✅
        
        // Step 2: Stripe.js creates token on client-side
        // Token returned to our server
        String paymentMethodId = request.getPaymentMethodId();  // "pm_..."
        
        // Step 3: Charge using token (no card data!)
        PaymentIntent intent = stripeClient.createPaymentIntent(
            CreatePaymentIntentRequest.builder()
                .amount(request.getAmount())
                .currency("INR")
                .paymentMethod(paymentMethodId)
                .customer(request.getCustomerId())
                .confirm(true)
                .metadata(Map.of(
                    "booking_id", request.getBookingId(),
                    "user_id", String.valueOf(request.getUserId())
                ))
                .build()
        );
        
        // Step 4: Store only safe references
        Payment payment = Payment.builder()
            .id(UUID.randomUUID().toString())
            .bookingId(request.getBookingId())
            .transactionId(intent.getId())  // Stripe payment intent ID
            .paymentMethodId(paymentMethodId)  // Token, not card number!
            .last4Digits(intent.getPaymentMethod().getCard().getLast4())  // Safe
            .cardBrand(intent.getPaymentMethod().getCard().getBrand())  // Safe
            .amount(request.getAmount())
            .status(PaymentStatus.SUCCESS)
            .build();
        
        paymentRepository.save(payment);
        
        return PaymentResponse.success(payment);
    }
}
```

**Frontend Integration (Stripe.js):**

```javascript
// PCI-compliant frontend flow
const stripe = Stripe('pk_live_...');

// Step 1: Create payment method on client-side
async function handlePayment() {
    
    // Stripe.js collects card data (NEVER sent to our server)
    const {paymentMethod, error} = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,  // Stripe-hosted iframe
        billing_details: {
            name: userName,
            email: userEmail
        }
    });
    
    if (error) {
        console.error(error);
        return;
    }
    
    // Step 2: Send only token to our backend
    const response = await fetch('/api/payments', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            bookingId: bookingId,
            paymentMethodId: paymentMethod.id,  // Token, not card!
            amount: 50000  // ₹500
        })
    });
    
    const result = await response.json();
    
    if (result.status === 'SUCCESS') {
        window.location.href = '/booking/confirmation';
    }
}
```

**PCI DSS Compliance Checklist:**

```
PCI DSS REQUIREMENTS (Level 4 Merchant)
═══════════════════════════════════════════════════════════
✅ Never store full card numbers (use tokens)
✅ Never store CVV/CVV2 codes
✅ Never log card data
✅ Use TLS 1.2+ for all card data transmission
✅ Encrypt stored payment tokens
✅ Implement access controls (who can see payment data)
✅ Regular security audits
✅ Network segmentation (payment services isolated)
✅ Strong password policies
✅ Two-factor authentication for admin access

WHAT WE STORE (Safe)
═══════════════════════════════════════════════════════════
✅ Payment method ID (token): "pm_1Abc2Def3Ghi"
✅ Transaction ID: "pi_1Xyz2Abc3Def"
✅ Last 4 digits: "4242"
✅ Card brand: "Visa"
✅ Expiry month/year: "12/2025" (optional)

WHAT WE NEVER STORE (Prohibited)
═══════════════════════════════════════════════════════════
❌ Full card number: "4242 4242 4242 4242"
❌ CVV: "123"
❌ Track data from magnetic stripe
```

---
