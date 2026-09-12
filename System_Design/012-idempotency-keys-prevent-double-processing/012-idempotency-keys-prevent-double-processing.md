# Idempotency Keys
### User Retries a Payment → Server Processes Twice — How Idempotency-Key: uuid Prevents Double Charge

---

## PART 1 — THE STUDENT CONVERSATION

**The problem: networks are unreliable. Retries are necessary. But retries can cause duplicate actions.**

User clicks "Pay $100." Request goes out. The server receives it, debits the account, creates the order — then the network drops before the response reaches the client. Client sees a timeout error. Client retries. Server receives the request again. Debits another $100. Creates another order.

User is charged twice. They are very unhappy.

**Idempotency means: no matter how many times you call an operation with the same input, the result is the same as calling it once.**

A mathematical example: `max(x, 5)` — calling it 1000 times with x=3 always gives 5. It's idempotent.

An API example: `DELETE /users/42` — calling it 3 times either deletes or finds user already deleted. Same end state. Idempotent.

A non-idempotent example: `POST /payments` without an idempotency key — each call creates a new charge. Calling it 3 times = 3 charges. Not idempotent.

**Idempotency keys fix this: the client generates a unique ID for the operation and sends it on every retry. The server uses it to deduplicate.**

---

## PART 2 — HOW IT WORKS

```
Without Idempotency Key:
────────────────────────────────────────────────────────────────────

  t=0: Client sends POST /payments { amount: 100, user: Alice }
  t=1: Server processes: debit $100, insert order #1001, return 200
  t=1: Network drops. Client never sees the 200.
  t=3: Client retries: POST /payments { amount: 100, user: Alice }
  t=4: Server processes: debit $100, insert order #1002, return 200
  t=4: Client sees 200. Thinks the first charge worked.
  Result: Alice charged $200, two orders created. ✗

With Idempotency Key:
────────────────────────────────────────────────────────────────────

  t=0: Client generates UUID: "idem-key-7f8a3b9c"
  t=0: Client sends POST /payments { amount: 100, user: Alice }
                          Header: Idempotency-Key: idem-key-7f8a3b9c
  t=1: Server:
    1. Check: have we seen key "idem-key-7f8a3b9c"? → NO
    2. Process: debit $100, insert order #1001
    3. Store in idempotency table: { key: "idem-key-7f8a3b9c", response: {...}, expires: +24h }
    4. Return 200 { order_id: 1001, charged: $100 }
  t=1: Network drops. Client never sees the 200.
  t=3: Client retries with SAME key: POST /payments
                                      Header: Idempotency-Key: idem-key-7f8a3b9c
  t=4: Server:
    1. Check: have we seen key "idem-key-7f8a3b9c"? → YES
    2. Return CACHED response: { order_id: 1001, charged: $100 }
    3. NO new debit, NO new order
  t=4: Client sees 200. Order #1001. Correct.
  Result: Alice charged $100, one order. ✓
```

---

## PART 3 — IMPLEMENTATION

```
Server-side idempotency table:
────────────────────────────────────────────────────────────────────

  CREATE TABLE idempotency_keys (
    key_value    VARCHAR(255) PRIMARY KEY,  -- the UUID from client
    user_id      BIGINT NOT NULL,           -- prevents key reuse across users
    endpoint     VARCHAR(100),             -- /api/v1/payments
    response     JSON,                     -- cached HTTP response
    status_code  INT,
    created_at   TIMESTAMP DEFAULT NOW(),
    expires_at   TIMESTAMP,                -- TTL: 24h or 7 days
    INDEX idx_expires (expires_at)         -- for cleanup job
  );

Server logic (Java/Spring):
────────────────────────────────────────────────────────────────────

  @PostMapping("/payments")
  public ResponseEntity<PaymentResponse> createPayment(
          @RequestHeader("Idempotency-Key") String idempotencyKey,
          @RequestBody PaymentRequest request,
          Authentication auth) {

      Long userId = auth.getUserId();

      // Check for existing result
      Optional<IdempotencyRecord> existing =
          idempotencyRepo.findByKeyAndUser(idempotencyKey, userId);

      if (existing.isPresent()) {
          // Return cached response — no processing
          return ResponseEntity
              .status(existing.get().getStatusCode())
              .body(existing.get().getResponse());
      }

      // Process the payment
      PaymentResponse result;
      int statusCode;
      try {
          result = paymentService.processPayment(request, userId);
          statusCode = 200;
      } catch (InsufficientFundsException e) {
          result = new PaymentResponse("FAILED", e.getMessage());
          statusCode = 422;  // also cache failures! (to return same error on retry)
      }

      // Store result for future retries (TTL: 24 hours)
      idempotencyRepo.save(new IdempotencyRecord(
          idempotencyKey, userId, "/payments",
          result, statusCode,
          Instant.now().plus(24, HOURS)
      ));

      return ResponseEntity.status(statusCode).body(result);
  }
```

### The Race Condition Problem

```
Two simultaneous retries of the same idempotency key:
────────────────────────────────────────────────────────────────────

  Request A: Check key → NOT found → begin processing...
  Request B: Check key → NOT found → begin processing...    ← race!
  Request A: Debit $100, insert order #1001
  Request B: Debit $100, insert order #1002               ← DUPLICATE!

Fix: database-level uniqueness constraint
  The PRIMARY KEY on key_value already prevents duplicate inserts.
  Use INSERT...ON DUPLICATE KEY as the lock:

  BEGIN;
  INSERT INTO idempotency_keys (key_value, user_id, status)
    VALUES ('idem-key-7f8a3b9c', 123, 'PROCESSING')
    ON DUPLICATE KEY UPDATE key_value=key_value;  ← no-op if exists
  -- If INSERT succeeded: this thread "owns" the key → proceed with payment
  -- If INSERT failed (duplicate): another thread is processing → wait/return cached
  COMMIT;
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your payment API is called by a mobile app. The user's connection drops after the charge. They reopen the app and retry. How do you prevent double charging?"

**You (architect answer):**

> "The client generates a UUID idempotency key when the user taps 'Pay.' It stores this key
> locally before sending the request. Every retry sends the same key in the Idempotency-Key
> header.
>
> On the server: before processing, I look up the key in an idempotency_keys table. If found,
> I return the cached response immediately — no processing. If not found, I INSERT the key
> with status=PROCESSING (using a unique constraint to handle concurrent retries), then
> process the payment, then update the record with the result.
>
> One important detail: I cache failed responses too. If the first attempt failed with
> 'insufficient funds,' the retry should get the same 'insufficient funds' error, not trigger
> another balance check that might now pass. The idempotency key ties the operation to
> a specific point in time.
>
> I set TTL to 24 hours — that's the window within which retries can occur. After 24 hours,
> the key expires and the client should treat this as a new operation (generate a new key).
>
> Stripe uses this exact pattern and is the reference implementation. Their idempotency
> keys have a 24-hour TTL too."

---

## PART 5 — WHEN OPERATIONS ARE NATURALLY IDEMPOTENT

```
Naturally idempotent (safe to retry without key):
  GET /users/42              → reads don't change state
  PUT /users/42 { name: X } → upsert semantics, same result each time
  DELETE /users/42           → deleting a deleted resource = same final state

NOT naturally idempotent (must use idempotency keys):
  POST /payments             → creates a new charge each time
  POST /orders               → creates a new order each time
  POST /emails/send          → sends another email each time

HTTP method semantics:
  GET, HEAD: safe (no side effects, idempotent by definition)
  PUT, DELETE: idempotent by HTTP spec (same effect repeated)
  POST: NOT idempotent by HTTP spec → must implement manually with idempotency key

Real-world usage:
  Stripe:    Idempotency-Key header for all POST requests
  PayPal:    PayPal-Request-Id header
  Braintree: same concept, different header name
  Twilio:    X-Twilio-Idempotency-Token
```

---

## QUICK REFERENCE CARD

```
Idempotency key flow:
  Client generates: UUID or ULID before sending request
  Client stores: key locally (in-memory or localStorage)
  Client sends: Idempotency-Key: <uuid> on every attempt
  Server checks: lookup key in idempotency_keys table
    Found: return cached response (no processing)
    Not found: INSERT key (race protection) → process → cache result

TTL: 24h (Stripe) to 7 days — beyond this, treat as new operation

Key scope:
  (key_value + user_id) should be unique — prevents one user using another's key
  (key_value + endpoint) optional — same key for different endpoints = separate ops

Failure caching:
  Cache both success AND failure responses
  Client retrying a 422 should get same 422, not trigger a new attempt

Race condition protection:
  Use INSERT with unique constraint on key_value
  Only one thread "wins" the INSERT → other threads return cached/wait

Interview one-liner:
"The client generates a UUID before the first attempt and sends it on every retry.
The server caches the result keyed by this UUID. Retries hit the cache,
not the business logic. Double-processing is impossible."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Idempotency keys come up any time you have a retry-capable client hitting a state-changing API — knowing when to reach for them is what separates junior designs from senior ones.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment** | User double-taps "Pay" button. Both requests reach payment service. Idempotency-Key: UUID per button click. Server stores result in idempotency_keys table. Second request: cache hit, returns same response. Charged exactly once. |
| **09 — E-Commerce** | Network timeout on POST /orders. Client retries. Without idempotency key: two orders, two charges. With key: server returns same order_id on retry. Idempotent operation = safe to retry. |
| **11 — Ticket Booking** | Client retries seat reservation on network timeout. Without key: two reservations for same seat attempted. With idempotency key: second request returns first reservation. No double-booking. |

**Architect's one-liner for the interview:**
*"The client generates a UUID once, before the first attempt, and sends it on every retry — the server caches the result by that UUID so retries are free and double-processing is impossible."*
