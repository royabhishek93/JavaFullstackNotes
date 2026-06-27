# Transaction Flow Diagrams

## 1. P2P Money Transfer Flow (Person to Person)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    P2P TRANSFER - HAPPY PATH                                │
└─────────────────────────────────────────────────────────────────────────────┘

User A          App A           Payment         NPCI          Bank A        Bank B
(Sender)       (PSP A)          Service        Switch         (Sender)    (Receiver)
   │               │                │              │              │             │
   │ Initiate      │                │              │              │             │
   │ Transfer      │                │              │              │             │
   │ userB@ybl     │                │              │              │             │
   │ ₹500          │                │              │              │             │
   ├──────────────►│                │              │              │             │
   │               │                │              │              │             │
   │               │ Create Request │              │              │             │
   │               │ (idempotency)  │              │              │             │
   │               ├───────────────►│              │              │             │
   │               │                │              │              │             │
   │               │                │ Validate VPA │              │             │
   │               │                │ userB@ybl    │              │             │
   │               │                ├─────────────►│              │             │
   │               │                │              │              │             │
   │               │                │              │ Resolve VPA  │             │
   │               │                │              ├─────────────►│             │
   │               │                │              │              │             │
   │               │                │              │ A/c Details  │             │
   │               │                │              │◄─────────────┤             │
   │               │                │              │              │             │
   │               │                │◄─────────────┤              │             │
   │               │                │ VPA Valid    │              │             │
   │               │◄───────────────┤              │              │             │
   │               │                │              │              │             │
   │◄──────────────┤                │              │              │             │
   │ Enter MPIN    │                │              │              │             │
   │               │                │              │              │             │
   ├──────────────►│                │              │              │             │
   │ MPIN ****     │                │              │              │             │
   │               │                │              │              │             │
   │               │ Verify MPIN    │              │              │             │
   │               ├───────────────►│              │              │             │
   │               │                │              │              │             │
   │               │◄───────────────┤              │              │             │
   │               │ MPIN OK        │              │              │             │
   │               │                │              │              │             │
   │               │                │ Start Txn    │              │             │
   │               │                │ (2-Phase)    │              │             │
   │               │                ├─────────────►│              │             │
   │               │                │              │              │             │
   │               │                │              │ PHASE 1:     │             │
   │               │                │              │ Prepare      │             │
   │               │                │              │ (Lock Funds) │             │
   │               │                │              ├─────────────►│             │
   │               │                │              │              │             │
   │               │                │              │ Check Balance│             │
   │               │                │              │ Lock ₹500    │             │
   │               │                │              │              │             │
   │               │                │              │◄─────────────┤             │
   │               │                │              │ READY        │             │
   │               │                │              │              │             │
   │               │                │              │ PHASE 1:     │             │
   │               │                │              │ Prepare      │             │
   │               │                │              ├────────────────────────────►│
   │               │                │              │              │             │
   │               │                │              │              │   Validate  │
   │               │                │              │              │   Account   │
   │               │                │              │              │             │
   │               │                │              │◄────────────────────────────┤
   │               │                │              │              │   READY     │
   │               │                │              │              │             │
   │               │                │              │ PHASE 2:     │             │
   │               │                │              │ Commit       │             │
   │               │                │              ├─────────────►│             │
   │               │                │              │              │             │
   │               │                │              │ Debit ₹500   │             │
   │               │                │              │              │             │
   │               │                │              │◄─────────────┤             │
   │               │                │              │ DEBITED      │             │
   │               │                │              │              │             │
   │               │                │              │ PHASE 2:     │             │
   │               │                │              │ Commit       │             │
   │               │                │              ├────────────────────────────►│
   │               │                │              │              │             │
   │               │                │              │              │  Credit ₹500│
   │               │                │              │              │             │
   │               │                │              │◄────────────────────────────┤
   │               │                │              │              │  CREDITED   │
   │               │                │              │              │             │
   │               │                │◄─────────────┤              │             │
   │               │                │ SUCCESS      │              │             │
   │               │◄───────────────┤              │              │             │
   │               │                │              │              │             │
   │◄──────────────┤                │              │              │             │
   │ Success       │                │              │              │             │
   │ ₹500 sent     │                │              │             │              │
   │               │                │              │              │             │
   │               │ Trigger Events │              │              │             │
   │               │ (Kafka)        │              │              │             │
   │               ├───────────────►│              │              │             │
   │               │                │              │              │             │
   │               │                │─────► Notification Service  │             │
   │               │                │─────► Analytics Service     │             │
   │               │                │─────► Settlement Service    │             │
   │               │                │              │              │             │

Timeline: ~2-3 seconds
Status: INITIATED → PENDING → SUCCESS
```

## 2. Transaction State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRANSACTION STATE MACHINE                                │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌─────────────┐
                            │  INITIATED  │
                            └──────┬──────┘
                                   │
                                   │ VPA Validated
                                   │ MPIN Verified
                                   ▼
                            ┌─────────────┐
                            │  VALIDATING │
                            └──────┬──────┘
                                   │
                                   │ Validation Success
                                   ▼
                            ┌─────────────┐
                            │   PENDING   │◄───────────┐
                            └──────┬──────┘            │
                                   │                   │
                    ┌──────────────┼──────────────┐    │
                    │              │              │    │
                    │              │              │    │ Retry
              Network Fail    Prepare Phase  Timeout  │
                    │         Success          │      │
                    │              │           │      │
                    ▼              ▼           ▼      │
             ┌──────────┐   ┌──────────┐   ┌────────┴───┐
             │ PENDING_ │   │ PREPARED │   │  RETRYING  │
             │ TIMEOUT  │   └────┬─────┘   └────────────┘
             └─────┬────┘        │
                   │             │ Commit Phase
                   │             ▼
                   │      ┌─────────────┐
                   │      │   DEBITED   │
                   │      └──────┬──────┘
                   │             │
                   │             │ Credit Phase
                   │             ▼
                   │      ┌─────────────┐
                   │      │  CREDITED   │
                   │      └──────┬──────┘
                   │             │
                   │             ▼
                   │      ┌─────────────┐
                   └─────►│   SUCCESS   │
                          └─────────────┘
                                 ▲
                                 │
                          [Terminal State]


                    ┌──────────────┐
                    │   FAILED     │
                    └──────┬───────┘
                           │
                           │ Reversal Needed?
                           │
                    ┌──────┴───────┐
                    │              │
                    ▼              ▼
            ┌──────────────┐  ┌──────────────┐
            │  REVERSING   │  │  FAILED_     │
            │              │  │  NO_REVERSAL │
            └──────┬───────┘  └──────────────┘
                   │                 ▲
                   │                 │
                   ▼                 │
            ┌──────────────┐         │
            │  REVERSED    │─────────┘
            └──────────────┘
                   ▲
                   │
            [Terminal State]
```

## 3. Failure and Rollback Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│               FAILURE SCENARIO - DEBIT SUCCESS, CREDIT FAILED               │
└─────────────────────────────────────────────────────────────────────────────┘

User A          Payment         NPCI          Bank A        Bank B      Reversal
(Sender)        Service        Switch         (Sender)    (Receiver)    Service
   │               │              │              │             │            │
   │ Transfer      │              │              │             │            │
   │ ₹500          │              │              │             │            │
   ├──────────────►│              │              │             │            │
   │               │              │              │             │            │
   │               │ 2PC Phase 1  │              │             │            │
   │               ├─────────────►│              │             │            │
   │               │              │              │             │            │
   │               │              │ Prepare      │             │            │
   │               │              ├─────────────►│             │            │
   │               │              │              │             │            │
   │               │              │◄─────────────┤             │            │
   │               │              │ READY        │             │            │
   │               │              │              │             │            │
   │               │              │ 2PC Phase 2  │             │            │
   │               │              │ Commit Debit │             │            │
   │               │              ├─────────────►│             │            │
   │               │              │              │             │            │
   │               │              │ Debit ₹500   │             │            │
   │               │              │              │             │            │
   │               │              │◄─────────────┤             │            │
   │               │              │ DEBITED ✓    │             │            │
   │               │              │              │             │            │
   │               │              │ Commit Credit│             │            │
   │               │              ├────────────────────────────►│            │
   │               │              │              │             │            │
   │               │              │              │      TIMEOUT/ERROR       │
   │               │              │              │        (Network Issue)   │
   │               │              │              │             X            │
   │               │              │◄────────────────────────────┤            │
   │               │              │              │  NO RESPONSE │            │
   │               │              │              │             │            │
   │               │◄─────────────┤              │             │            │
   │               │ FAILED       │              │             │            │
   │               │ (Partial)    │              │             │            │
   │               │              │              │             │            │
   │               │ Trigger      │              │             │            │
   │               │ Reversal     │              │             │            │
   │               ├──────────────────────────────────────────────────────►│
   │               │              │              │             │            │
   │               │              │              │             │  Initiate  │
   │               │              │              │             │  Reversal  │
   │               │              │              │             │  Txn       │
   │               │              │              │             │            │
   │               │              │◄─────────────────────────────────────────┤
   │               │              │              │             │  Credit    │
   │               │              │              │             │  Back      │
   │               │              ├─────────────►│             │            │
   │               │              │              │             │            │
   │               │              │ Credit ₹500  │             │            │
   │               │              │ (Reversal)   │             │            │
   │               │              │              │             │            │
   │               │              │◄─────────────┤             │            │
   │               │              │ REVERSED ✓   │             │            │
   │               │              │              │             │            │
   │               │◄─────────────┤              │             │            │
   │               │ REVERSED     │              │             │            │
   │◄──────────────┤              │              │             │            │
   │ Transaction   │              │              │             │            │
   │ Failed        │              │              │             │            │
   │ Amount        │              │              │             │            │
   │ Refunded      │              │              │             │            │

Timeline: 3-5 seconds (including reversal)
Status: INITIATED → PENDING → DEBITED → FAILED → REVERSED

Reversal SLA: Within 1 hour (auto-retry every 5 minutes)
```

## 4. Merchant Payment (QR Code) Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MERCHANT QR CODE PAYMENT FLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘

Customer        Mobile          Payment        NPCI       Customer    Merchant
 User            App            Service       Switch        Bank        Bank
   │              │                │             │            │           │
   │ Scan QR      │                │             │            │           │
   │ Code         │                │             │            │           │
   ├─────────────►│                │             │            │           │
   │              │                │             │            │           │
   │              │ Parse QR       │             │            │           │
   │              │ (merchant VPA, │             │            │           │
   │              │  amount)       │             │            │           │
   │              │                │             │            │           │
   │◄─────────────┤                │             │            │           │
   │ Confirm      │                │             │            │           │
   │ ₹1,200       │                │             │            │           │
   │ to Shop XYZ  │                │             │            │           │
   │              │                │             │            │           │
   ├─────────────►│                │             │            │           │
   │ Confirm +    │                │             │            │           │
   │ MPIN         │                │             │            │           │
   │              │                │             │            │           │
   │              │ Initiate       │             │            │           │
   │              ├───────────────►│             │            │           │
   │              │                │             │            │           │
   │              │                │ Validate &  │            │           │
   │              │                │ Process     │            │           │
   │              │                ├────────────►│            │           │
   │              │                │             │            │           │
   │              │                │             │ Debit      │           │
   │              │                │             ├───────────►│           │
   │              │                │             │            │           │
   │              │                │             │◄───────────┤           │
   │              │                │             │ DEBITED    │           │
   │              │                │             │            │           │
   │              │                │             │ Credit     │           │
   │              │                │             ├──────────────────────►│
   │              │                │             │            │           │
   │              │                │             │            │  Credit   │
   │              │                │             │            │  (Merchant│
   │              │                │             │            │   MDR     │
   │              │                │             │            │  deducted)│
   │              │                │             │            │           │
   │              │                │             │◄──────────────────────┤
   │              │                │             │            │  SUCCESS  │
   │              │                │             │            │           │
   │              │                │◄────────────┤            │           │
   │              │                │ SUCCESS     │            │           │
   │              │◄───────────────┤             │            │           │
   │              │                │             │            │           │
   │◄─────────────┤                │             │            │           │
   │ Payment      │                │             │            │           │
   │ Successful   │                │             │            │           │
   │ (Receipt)    │                │             │            │           │
   │              │                │             │            │           │
   │              │                │─────► Webhook to Merchant Portal    │
   │              │                │       (Payment notification)        │

QR Code Format (UPI):
upi://pay?pa=merchant@bank&pn=Shop%20XYZ&am=1200&cu=INR&tn=Invoice123

MDR (Merchant Discount Rate): 0% for P2M (Govt. subsidized)
Timeline: ~3-4 seconds
```

## 5. Concurrent Transaction Handling

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              CONCURRENT TRANSACTIONS - RACE CONDITION HANDLING              │
└─────────────────────────────────────────────────────────────────────────────┘

Scenario: User initiates 2 transactions simultaneously with balance = ₹1000

Transaction 1            Database Lock         Transaction 2
(₹800)                   (Row-Level)           (₹500)
   │                          │                     │
   │ Check Balance            │                     │ Check Balance
   │ & Lock Row               │                     │ (Waiting...)
   ├─────────────────────────►│                     │
   │                          │                     │
   │ Balance: ₹1000           │                     │
   │ Lock Acquired ✓          │                     │
   │                          │                     │
   │ Deduct ₹800              │                     │
   ├─────────────────────────►│                     │
   │                          │                     │
   │ New Balance: ₹200        │                     │
   │ COMMIT                   │                     │
   ├─────────────────────────►│                     │
   │                          │                     │
   │◄─────────────────────────┤                     │
   │ SUCCESS                  │                     │
   │                          │                     │
   │ Release Lock             │                     │
   ├─────────────────────────►│◄────────────────────┤
   │                          │ Now Lock Acquired   │
   │                          │                     │
   │                          │ Balance: ₹200       │
   │                          │ Required: ₹500      │
   │                          │                     │
   │                          ├────────────────────►│
   │                          │ INSUFFICIENT        │
   │                          │ BALANCE             │
   │                          │                     │
   │                          │◄────────────────────┤
   │                          │ ROLLBACK            │
   │                          │                     │
   │                          │────────────────────►│
   │                          │ FAILED              │

SQL Implementation:
BEGIN TRANSACTION;
SELECT balance FROM accounts 
WHERE account_id = ? 
FOR UPDATE;  -- Row-level lock

IF balance >= amount THEN
    UPDATE accounts 
    SET balance = balance - amount 
    WHERE account_id = ?;
    COMMIT;
ELSE
    ROLLBACK;
END IF;
```

## 6. Retry and Idempotency Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IDEMPOTENCY & RETRY MECHANISM                            │
└─────────────────────────────────────────────────────────────────────────────┘

Client          API Gateway      Payment        Idempotency      Database
  App                           Service          Cache
   │                │               │                │               │
   │ Transfer       │               │                │               │
   │ Request        │               │                │               │
   │ (txn-uuid-123) │               │                │               │
   ├───────────────►│               │                │               │
   │                │               │                │               │
   │                │ Forward       │                │               │
   │                ├──────────────►│                │               │
   │                │               │                │               │
   │                │               │ Check Key      │               │
   │                │               ├───────────────►│               │
   │                │               │                │               │
   │                │               │◄───────────────┤               │
   │                │               │ NOT FOUND      │               │
   │                │               │                │               │
   │                │               │ Store Key      │               │
   │                │               │ (24hr TTL)     │               │
   │                │               ├───────────────►│               │
   │                │               │                │               │
   │                │               │ Process Txn    │               │
   │                │               ├────────────────────────────────►│
   │                │               │                │               │
   │                │               │                │   PROCESSING  │
   │                │               │                │               │
   │                │◄──────────────┤                │               │
   │◄───────────────┤ Processing    │                │               │
   │ (Connection    │               │                │               │
   │  Lost!)        X               │                │               │
   │                                │                │               │
   │ RETRY          │               │                │               │
   │ Same Request   │               │                │               │
   │ (txn-uuid-123) │               │                │               │
   ├───────────────►│               │                │               │
   │                │               │                │               │
   │                │ Forward       │                │               │
   │                ├──────────────►│                │               │
   │                │               │                │               │
   │                │               │ Check Key      │               │
   │                │               ├───────────────►│               │
   │                │               │                │               │
   │                │               │◄───────────────┤               │
   │                │               │ FOUND!         │               │
   │                │               │ (Processing)   │               │
   │                │               │                │               │
   │                │               │ Query Status   │               │
   │                │               ├────────────────────────────────►│
   │                │               │                │               │
   │                │               │◄────────────────────────────────┤
   │                │               │                │   SUCCESS     │
   │                │               │                │               │
   │                │◄──────────────┤                │               │
   │◄───────────────┤ SUCCESS       │                │               │
   │ (Same response │ (from cache)  │                │               │
   │  as before)    │               │                │               │

Idempotency Key Generation:
key = hash(user_id + receiver_vpa + amount + timestamp_hour)

Benefits:
- Prevents duplicate charges
- Safe retries on network failures
- Consistent response for same request
```
