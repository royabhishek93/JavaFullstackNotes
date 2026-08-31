# 💳 Payment Gateway - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## **Design Patterns Used**: Strategy (payment methods) + Adapter (payment provider integration) + State (transaction lifecycle)

**Interviewer**: "Design a Payment Gateway system (like Razorpay/Stripe)."

**You**: "This is one of the highest-stakes systems in software - **money must NEVER be lost, duplicated, or double-charged**. Core challenges:
1. Multiple payment methods (card, UPI, wallet, netbanking) - different integration per method
2. Idempotency - network retries must NOT cause double charging
3. Transaction state machine - PENDING → PROCESSING → SUCCESS/FAILED
4. Reconciliation with external payment providers

Let me design with **Adapter Pattern** for provider integration and **State Pattern** for transaction lifecycle."

### 🎯 Scope Clarification: Merchant Gateway vs Peer-to-Peer Transfer

**Interviewer**: "Just to be clear - are we building a merchant checkout gateway (like Stripe/Razorpay, where a customer pays a business) or a peer-to-peer transfer system (like a wallet app, where User A pays User B)?"

**You**: "Great catch - these are genuinely different systems that both get called 'Payment Gateway' in interviews, and they lead to different designs:

| Aspect | Merchant Gateway (this guide's focus) | Peer-to-Peer Transfer |
|---|---|---|
| **Who pays whom** | Customer → Merchant (business account) | User → User (personal wallet/bank) |
| **Core entity** | `Transaction` against a `merchantId` | `Transaction` with `senderUserId` + `receiverUserId` |
| **Instrument model** | Tokenized card/UPI handle, single-use per checkout | `User` owns multiple `Instrument`s (bank accounts, cards) reused across transfers - Factory Pattern per instrument type fits well here |
| **Critical failure mode** | Double-charging a customer on retry → **Idempotency Key + DB UNIQUE constraint is THE must-have pattern** | Debit succeeds, credit fails (partial transfer) → needs Saga/compensating-transaction pattern |
| **External dependency** | Card networks/UPI switch respond in seconds; still need webhook reconciliation for ambiguous timeouts | Bank/NPCI settlement can take 3-5 days - **synchronous validation + asynchronous processing** is the key pattern, not idempotency |
| **Best-fit patterns** | Adapter (per-provider), State Machine (transaction lifecycle), Idempotency key | Factory (per-instrument-type service), DTO (mask account/card details from client), async processing |

**My approach**: Since 'Design a Payment Gateway' most commonly means the **merchant checkout flow** (this is what Stripe/Razorpay actually are), that's what this guide covers in depth below. But if the interviewer says 'no, it's a wallet-to-wallet transfer' - the object model shifts to `User` → `Instrument` (via Factory) → `Transaction(senderId, receiverId)`, and the hardest problem becomes **handling a slow, async external processor** (3-5 day bank settlement) rather than idempotent retries. I'd ask this clarifying question in the first 2 minutes of any real interview - it changes the entire design."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                 PAYMENT GATEWAY ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  MERCHANT APP     │
                    └────────┬─────────┘
                             │ POST /payments (idempotency key!)
                             ▼
                    ┌──────────────────┐
                    │ PAYMENT SERVICE   │
                    │                  │
                    │  Transaction     │
                    │  StateMachine    │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ PaymentMethod │ │  PROVIDER    │ │ RECONCILIATION│
    │  Strategy     │ │  ADAPTER     │ │   SERVICE     │
    │              │ │              │ │              │
    │ - CardPayment │ │ VisaAdapter  │ │ Match internal│
    │ - UPIPayment  │ │ UPIAdapter   │ │ vs bank       │
    │ - WalletPay   │ │ BankAdapter  │ │ statements    │
    └──────────────┘ └──────────────┘ └──────────────┘

    TRANSACTION STATE MACHINE:
    ┌────────────────────────────────────────────┐
    │  INITIATED → PROCESSING → SUCCESS           │
    │       │            │                       │
    │       │            └──────→ FAILED          │
    │       │                                     │
    │       └──────→ TIMEOUT → (reconcile with bank)
    └────────────────────────────────────────────┘

    IDEMPOTENCY (Critical!):
    ┌────────────────────────────────────────────┐
    │  Client sends: Idempotency-Key: abc-123     │
    │  Server: If key seen before, return CACHED  │
    │          response, don't reprocess payment! │
    └────────────────────────────────────────────┘
```

---

## 2. API Design

```http
POST /api/v1/payments
Headers: {"Idempotency-Key": "idem-key-abc123"}
Request:
{
  "amount": 5000,
  "currency": "INR",
  "paymentMethod": "CARD",
  "cardDetails": {"token": "tok_visa_xxxx"},  // Tokenized, NEVER raw card number
  "merchantId": "merchant-1234",
  "orderId": "order-5678"
}

Response: 201 CREATED
{
  "paymentId": "pay-9999",
  "status": "PROCESSING",
  "amount": 5000
}

// Same idempotency key retried:
Response: 200 OK  // Returns CACHED result, doesn't reprocess!
{
  "paymentId": "pay-9999",  // Same ID as before
  "status": "SUCCESS",  // Reflects actual final state
  "amount": 5000,
  "note": "Duplicate request detected via idempotency key"
}

---

GET /api/v1/payments/{paymentId}
Response: 200 OK
{"paymentId": "pay-9999", "status": "SUCCESS", "amount": 5000, "completedAt": "..."}

---

POST /api/v1/payments/{paymentId}/refund
Request: {"amount": 5000, "reason": "Customer requested"}
Response: 200 OK
{"refundId": "refund-1111", "status": "PROCESSING"}

---

POST /api/v1/webhooks/provider-callback  (Called BY payment provider)
Request: {"providerTransactionId": "visa-txn-999", "status": "SUCCESS", "signature": "..."}
Response: 200 OK
```

---

## 3. ER Diagram & Database Design

```sql
CREATE TABLE payments (
    payment_id VARCHAR(50) PRIMARY KEY,
    idempotency_key VARCHAR(100) UNIQUE NOT NULL,  -- CRITICAL for dedup!
    merchant_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    payment_method VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'INITIATED',
    provider_transaction_id VARCHAR(100),  -- External reference
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    
    CHECK (status IN ('INITIATED', 'PROCESSING', 'SUCCESS', 'FAILED', 'TIMEOUT', 'REFUNDED')),
    UNIQUE (idempotency_key),  -- Enforces idempotency at DB level!
    INDEX idx_merchant_created (merchant_id, created_at),
    INDEX idx_provider_txn (provider_transaction_id)
);

CREATE TABLE payment_events (
    event_id VARCHAR(50) PRIMARY KEY,
    payment_id VARCHAR(50) NOT NULL,
    event_type VARCHAR(30) NOT NULL,  -- STATE_CHANGE, PROVIDER_CALLBACK, RETRY
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    INDEX idx_payment_id (payment_id)
);

-- NEVER store raw card numbers! Only tokens.
CREATE TABLE payment_tokens (
    token VARCHAR(100) PRIMARY KEY,
    card_last_4 VARCHAR(4),  -- Only last 4 digits for display
    card_network VARCHAR(20),  -- VISA, MASTERCARD
    customer_id VARCHAR(50)
);
```

### **Why This Schema?**

**You**: "The `UNIQUE (idempotency_key)` constraint is THE critical line. It enforces idempotency at the database level - if the application layer somehow tries to insert a duplicate payment with the same idempotency key (due to a race condition on retry), the DATABASE itself rejects it with a unique constraint violation, which the application catches and returns the EXISTING payment record instead."

---

## 4. Sequence Diagrams

### **4.1 Idempotent Payment Processing**

```
Client   PaymentService   DB              ProviderAdapter   PaymentProvider
  │            │              │                    │                │
  │─POST(idem-key-abc)▶│              │                    │                │
  │            ├─SELECT WHERE idempotency_key=?──▶│                    │                │
  │            │◀no existing row──────│                    │                │
  │            ├─INSERT (status=INITIATED)────────▶│                    │                │
  │            ├─charge()──────────────────────────────────▶│                │
  │            │              │                    ├─processPayment()──────▶│
  │            │              │                    │◀SUCCESS────────────────│
  │            ├─UPDATE status=SUCCESS─────────────▶│                    │                │
  │◀201 payment-id-999─│              │                    │                │
  │            │              │                    │                │
  │  ... Client's network times out, doesn't see response, RETRIES with SAME idempotency key
  │            │              │                    │                │
  │─POST(idem-key-abc) [RETRY]▶│              │                    │                │
  │            ├─SELECT WHERE idempotency_key=?──▶│                    │                │
  │            │◀EXISTING row found (status=SUCCESS)                  │                │
  │◀200 payment-id-999 (CACHED, no reprocessing!)  │                    │                │
```

**You**: "This is THE most important sequence to nail in a payment system interview. Client retries (due to network timeout, NOT knowing if the first request succeeded) MUST NOT cause double-charging. The idempotency key + DB unique constraint pattern is industry-standard (Stripe, Razorpay both document this exact pattern)."

---

## 5. Scenario-First Explanations

### **5.1 Why Adapter Pattern for Payment Providers?**

**You**: "Different payment providers (Visa, UPI/NPCI, PayPal) have WILDLY different APIs. Adapter Pattern provides a unified interface:

```java
interface PaymentProviderAdapter {
    ProviderResponse charge(ChargeRequest request);
    ProviderResponse refund(RefundRequest request);
}

class VisaProviderAdapter implements PaymentProviderAdapter {
    private VisaSDK visaClient;  // Third-party SDK with its own API shape
    
    public ProviderResponse charge(ChargeRequest request) {
        // Translate OUR generic request into VISA-SPECIFIC API call
        VisaChargeRequest visaRequest = VisaChargeRequest.builder()
            .cardToken(request.getCardToken())
            .amountInCents(request.getAmount().multiply(BigDecimal.valueOf(100)).intValue())
            .merchantAccount(request.getMerchantId())
            .build();
        
        VisaChargeResponse visaResponse = visaClient.processCharge(visaRequest);
        
        // Translate VISA's response back into OUR generic response
        return ProviderResponse.builder()
            .success(visaResponse.getResponseCode().equals("00"))
            .providerTransactionId(visaResponse.getTransactionRef())
            .build();
    }
}

class UPIProviderAdapter implements PaymentProviderAdapter {
    private NPCIClient npciClient;  // Completely different SDK shape!
    
    public ProviderResponse charge(ChargeRequest request) {
        // UPI uses VPA (Virtual Payment Address), collect request flow - very different!
        NPCICollectRequest npciRequest = new NPCICollectRequest(
            request.getVpa(), request.getAmount(), request.getMerchantId()
        );
        NPCIResponse response = npciClient.initiateCollect(npciRequest);
        
        return ProviderResponse.builder()
            .success(response.getStatus() == NPCIStatus.SUCCESS)
            .providerTransactionId(response.getRrn())  // Different field name entirely!
            .build();
    }
}

// PaymentService only talks to the COMMON interface:
class PaymentService {
    private Map<PaymentMethod, PaymentProviderAdapter> adapters;
    
    ProviderResponse processCharge(ChargeRequest request) {
        PaymentProviderAdapter adapter = adapters.get(request.getPaymentMethod());
        return adapter.charge(request);  // Doesn't care if it's Visa or UPI internally!
    }
}
```

**Why this matters**: Adding a new payment provider (e.g., adding PayPal support) means writing ONE new Adapter class - zero changes to PaymentService or any existing adapters."

### **5.2 Why State Pattern for Transaction Lifecycle?**

**You**: "Payment transactions have strict allowed state transitions:

```java
enum PaymentStatus {
    INITIATED, PROCESSING, SUCCESS, FAILED, TIMEOUT, REFUNDED
}

class PaymentStateMachine {
    private static final Map<PaymentStatus, Set<PaymentStatus>> ALLOWED_TRANSITIONS = Map.of(
        PaymentStatus.INITIATED, Set.of(PaymentStatus.PROCESSING, PaymentStatus.FAILED),
        PaymentStatus.PROCESSING, Set.of(PaymentStatus.SUCCESS, PaymentStatus.FAILED, PaymentStatus.TIMEOUT),
        PaymentStatus.SUCCESS, Set.of(PaymentStatus.REFUNDED),
        PaymentStatus.FAILED, Set.of(),  // Terminal state
        PaymentStatus.TIMEOUT, Set.of(PaymentStatus.SUCCESS, PaymentStatus.FAILED)  // Reconciliation can resolve
    );
    
    void transition(Payment payment, PaymentStatus newStatus) {
        Set<PaymentStatus> allowed = ALLOWED_TRANSITIONS.get(payment.getStatus());
        if (!allowed.contains(newStatus)) {
            throw new IllegalStateTransitionException(
                "Cannot transition from " + payment.getStatus() + " to " + newStatus
            );
        }
        payment.setStatus(newStatus);
        eventLog.record(payment, newStatus);
    }
}
```

**Why this validation matters**: Prevents bugs like accidentally marking a REFUNDED payment back to PROCESSING (which could trigger duplicate provider calls). Explicit state machine catches these at development time via tests, and at runtime via exceptions."

---

## 6. Cross Questions

**Interviewer**: "What happens if the payment provider times out - did the charge succeed or not?"

**You**: "This is THE hardest problem in payments - the **ambiguous timeout**. Solution: reconciliation via provider status check API:

```java
@Scheduled(fixedRate = 60000)  // Every minute
class ReconciliationJob {
    void reconcileTimeoutPayments() {
        List<Payment> timedOutPayments = paymentRepo.findByStatusAndOlderThan(
            PaymentStatus.PROCESSING, Duration.ofMinutes(2)
        );
        
        for (Payment payment : timedOutPayments) {
            // Actively query the PROVIDER for the actual status (not just wait for their callback)
            PaymentProviderAdapter adapter = adapterFactory.get(payment.getPaymentMethod());
            ProviderStatusResponse actualStatus = adapter.checkStatus(payment.getProviderTransactionId());
            
            if (actualStatus.isSuccess()) {
                stateMachine.transition(payment, PaymentStatus.SUCCESS);
            } else if (actualStatus.isFailed()) {
                stateMachine.transition(payment, PaymentStatus.FAILED);
            } else {
                // Still processing on provider side - check again next cycle
                if (payment.getCreatedAt().isBefore(LocalDateTime.now().minusMinutes(30))) {
                    // Give up after 30 min, mark for manual investigation
                    stateMachine.transition(payment, PaymentStatus.TIMEOUT);
                    alertOpsTeam(payment);
                }
            }
        }
    }
}
```

**Key principle**: NEVER assume timeout = failure. ALWAYS actively reconcile with the source of truth (the payment provider/bank) before declaring final status. This is why payment systems have dedicated reconciliation teams and jobs."

---

## 7. Trade-offs

### **Synchronous vs Asynchronous Payment Processing**

| Aspect | Synchronous (wait for provider) | Asynchronous (webhook-based) |
|--------|------------------------------------|----------------------------------|
| **User Experience** | Immediate feedback | Requires polling/webhook UI updates |
| **Reliability** | Timeout = ambiguous state | More resilient to network issues |
| **Complexity** | Simpler | Requires webhook handling + reconciliation |

**You**: "Production payment gateways use HYBRID: attempt synchronous response for common fast paths (card payments usually respond in 2-3 sec), but ALWAYS also register a webhook listener for the definitive final status, since synchronous responses can be lost even if the actual charge succeeded on the provider's end."

---

## 8. Senior Trap Questions

### **Trap: "Just retry the payment if it fails, users will understand!"**

**❌ Junior**: "Simple retry logic on failure."

**✅ Senior**: "NEVER blindly retry payment charges without idempotency keys! If the FIRST attempt actually succeeded on the provider's side but your response got lost (network blip), a naive retry creates a SECOND charge - the customer is charged TWICE. This is one of the most common and costly bugs in payment systems.

**Correct approach**: Always use the SAME idempotency key for retries of the same logical payment attempt. The provider (and your own system, via the UNIQUE constraint) will recognize the duplicate and return the ORIGINAL result instead of processing a new charge."

---

## 9. Technology Choices

### **Database: PostgreSQL for Financial Data**

**You**: "PostgreSQL with `SERIALIZABLE` isolation is non-negotiable for payment data - ACID guarantees are essential. NoSQL databases (MongoDB, Cassandra) that trade consistency for availability are INAPPROPRIATE for the core ledger, though they might be fine for auxiliary data like payment provider webhooks logs or analytics."

### **Message Queue: Kafka for Payment Events**

**You**: "Every state transition published to Kafka (`payment-events` topic) - enables: fraud detection service consuming events in real-time, analytics/reporting, and audit compliance (financial regulations often require immutable event logs)."

---

## 🎓 **Final Tips**

1. **Idempotency Key + DB UNIQUE constraint**: THE most critical pattern - prevents double-charging
2. **Adapter Pattern**: Unified interface across wildly different provider APIs
3. **State Machine**: Explicit allowed transitions prevent invalid state bugs
4. **Reconciliation**: Never trust ambiguous timeouts - actively verify with provider
5. **PCI-DSS awareness**: Never store raw card numbers, only tokens

Good luck! Payment Gateway is one of the highest-stakes LLD questions - shows you understand **financial system correctness guarantees**. 🚀
