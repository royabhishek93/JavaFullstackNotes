# Interview Guide: LLD of a Payment Gateway (Peer-to-Peer)

## 🗣️ The Interview Scenario

> "Design a payment gateway. Users can add/update/delete themselves and their funding instruments (bank accounts, cards), search for other users, and make a payment to another user, selecting which instrument to fund from. Walk me through your requirement clarification, the core entities, a sequence diagram for a happy-path payment, and then the class design — including how you'd handle the fact that the actual bank/network settlement might take several days rather than completing in real time."

This is a **large-scope system-design-flavored LLD** question. The interviewer is evaluating whether you can (1) proactively **narrow scope** rather than trying to boil the ocean, (2) systematically move from requirements → entities → sequence diagram → class diagram, and (3) reason about a realistic **async settlement** follow-up, which is a favorite way interviewers probe production maturity.

## 🏗️ Architect's Explanation (For a New Developer)

At its simplest, **a payment gateway acts as a mediator between a user and financial institutions**, moving money from one place to another. But "payment gateway" as a phrase covers an enormous space — peer-to-peer transfers (paying a friend), peer-to-merchant checkout (with refunds, multi-tenancy for many merchants), recurring payments, and more. The single most important move in this interview, made explicit up front, is to **define the scope before designing anything**: this guide (matching the source material) scopes to **peer-to-peer only**, explicitly excluding merchant checkout, refund processing, and multi-tenancy, because those alone could each be a separate 45-minute interview.

Once scoped, the approach is a repeatable four-step funnel that works for *any* large LLD problem:
1. **Clarify requirements** — what can a user actually do in the app?
2. **Identify main entities** — what are the nouns in this domain?
3. **Draw a sequence diagram for one happy-path flow** — this exposes which entities depend on which.
4. **Turn the sequence diagram into a class diagram** — now the dependencies are already known, so the class design falls out naturally.

## 📊 Visualize It

**Core class/service structure:**

```
   App (client)
     │
     ├──▶ UserController ──▶ UserService ──▶ [User entity] (static in-memory list)
     │
     ├──▶ InstrumentController ──▶ InstrumentServiceFactory
     │         │                        │
     │         │                        ├──▶ BankService   (Bank-specific add/get logic)
     │         │                        └──▶ CardService   (Card-specific add/get logic)
     │         │                                   │
     │         │                          [abstract Instrument] ◀── BankInstrument, CardInstrument
     │
     └──▶ TransactionController ──▶ TransactionService ──▶ (depends on) InstrumentController
                                          │                 (to fetch sender/receiver instrument details)
                                          ▼
                                     Processor ──▶ Card Network ──▶ Bank / Financial Institution
                                          │
                                          ▼
                                   NotificationService
```

**Sequence diagram — one happy-path payment (User1 → User2, ₹10):**

```
App          UserService      InstrumentSvc         TransactionSvc        InstrumentSvc(again)   Processor  Notif
 │──addUser──────▶│                                                                                          
 │◀───userId1─────│                                                                                          
 │──addUser──────▶│                                                                                          
 │◀───userId2─────│                                                                                          
 │──addBank(u1)───────────────▶│                                                                             
 │◀───bankInstrumentId─────────│                                                                             
 │──addCard(u2)───────────────▶│                                                                             
 │◀───cardInstrumentId─────────│                                                                             
 │──getUserDetails(email)─▶│  (search receiver by email/phone)                                              
 │──getInstruments(u1)────────▶│  (show which instrument to fund from)                                      
 │──makePayment(debitU1,creditU2,amt,debitInstrId)────────────────▶│                                         
 │                                                                  │──getInstrumentDetails(creditInstrId)──▶│
 │                                                                  │◀── ifsc/accNo/cardNo ───────────────────│
 │                                                                  │──validate & send to processor─────────────────────▶│
 │                                                                  │◀── success/pending ───────────────────────────────│
 │                                                                  │──store transaction (both sender & receiver)──────│
 │                                                                  │──send notification──────────────────────────────────────▶│
```

## 🔧 Deep Dive: How It Actually Works

### 1. Requirement clarification (the actual checklist used)
- User CRUD: add/update/delete a user.
- Instrument CRUD: a user can add/update/remove an **instrument** — defined precisely as "either your bank or card balance, through which you can fund a transaction or in which you receive a payment." A user can hold **multiple instruments** (e.g., two banks and a card).
- Make a payment, which itself decomposes into: **search** the receiving user (by email/phone), **select amount + funding instrument**, and **submit to a processor** (since the gateway is a mediator to the financial institution via a processor, which further talks to the card network, which talks to the bank).
- **Notifications** on add/update/delete of user or instrument.
- **Transaction history** — a user should be able to view their past transactions.

### 2. Core entities identified from the requirements
`User`, `Instrument` (Bank/Card), `Transaction` (a payment = one transaction, plus transaction history), `Notification`, `Processor`.

### 3. Entity design — `User`
```java
class User {
    String userId; String name; String email;
    // getters/setters
}
```
`UserService` maintains a **static in-memory list** of users (no DB in this LLD scope) and exposes `addUser(UserDto)` / `getUser(userId)`. `UserController` is the thin API-facing layer that just delegates to `UserService`.

**Key architectural detail: the DTO boundary.** Requests/responses use a `UserDto` (mirroring `User` but decoupled), so that internal entity/column changes never leak to or break external clients — described explicitly as "your DB column names ... very specific to you ... but only tell the client what it wants to know."

### 4. Entity design — `Instrument` (the most structurally interesting part)
```java
abstract class Instrument {
    String instrumentId;
    String userId;          // which user this instrument belongs to (not a full User object)
    InstrumentType type;    // enum: BANK, CARD, (future: BALANCE, ...)
}

class BankInstrument extends Instrument {
    String bankAccountNumber;
    String ifscCode;
}

class CardInstrument extends Instrument {
    String cardNumber;
    String cvv;
    // e.g., expiryDate
}
```
**Why split `InstrumentService` into `BankService` and `CardService`?** Because bank-specific and card-specific *validation logic* differs substantially (e.g., IFSC format checks vs. CVV/expiry checks), cramming both into one `addInstrument()` method would violate the **Single Responsibility Principle** — explicitly flagged as a place "where things get complicated" and where "the interviewer will catch you" if you don't separate concerns:
```java
abstract class InstrumentService {
    static Map<String, List<Instrument>> userInstruments;   // in-memory store
    abstract InstrumentDto addInstrument(InstrumentDto dto);
    abstract List<InstrumentDto> getInstrumentsByUser(String userId);
}
class BankService extends InstrumentService { /* bank-specific validation + storage */ }
class CardService extends InstrumentService { /* card-specific validation + storage */ }
```
An **`InstrumentServiceFactory`** selects `BankService` or `CardService` based on `instrumentType` from the incoming DTO, and `InstrumentController` stays generic — it just asks the factory for the right service and delegates:
```java
class InstrumentController {
    InstrumentDto addInstrument(InstrumentDto dto) {
        InstrumentService svc = instrumentServiceFactory.get(dto.getType());
        return svc.addInstrument(dto);
    }
}
```

### 5. Entity design — `Transaction` and `TransactionService`
```java
class Transaction {
    String transactionId;
    double amount;
    String senderUserId;
    String receiverUserId;
    String debitInstrumentId;
    String creditInstrumentId;
    TransactionStatus status;   // SUCCESS, PENDING, DENIED
}
```
`TransactionService.makePayment(TransactionDto)`:
1. Validates required fields are present.
2. Calls `InstrumentController`/`InstrumentService` to **fetch the debit instrument's details** (e.g., IFSC + account number) — needed because the processor requires full instrument details, not just an ID.
3. Also (in a fuller design) resolves the **receiver's preferred/default instrument** if not explicitly specified — "sometimes in the payment gateway you can set a preferred instrument ... if preferred is not set, check default ... or pick the latest added instrument."
4. Forwards the resolved details to the `Processor`.
5. Creates the `Transaction` record with a status, and — importantly — **stores the same transaction against both the sender's and receiver's history** so either party can retrieve it later.
6. Triggers a `Notification`.

`TransactionService` maintains a `Map<userId, List<Transaction>>` in memory, so transaction history lookups by user are direct.

### 6. The async settlement follow-up (a very likely interviewer probe)
The straightforward design calls the processor **synchronously and in real time**. A sharp interviewer will point out: *"real bank settlement can take 3–5 days — money can be debited without being credited for a while."* The mature answer:
- Call the processor **synchronously only for real-time validation**: does the sender have sufficient balance (and can it be reserved), is the receiver's account valid/not blocked/not closed.
- If validation passes, make the actual debit/credit call to the processor **asynchronously**, and immediately mark the transaction as **`PENDING`**.
- When the processor eventually calls back (hours/days later) with the final outcome, `TransactionService` updates the stored transaction's status to `SUCCESS` or `DENIED`.

This shows the interviewer you understand that **payment gateways are inherently eventually-consistent systems**, not naive synchronous request/response services.

## 🔥 Real Production Incident & Fix

**What broke:** A peer-to-peer payments feature initially treated `makePayment()` as a fully synchronous call all the way through to the bank processor — the API request blocked until the processor returned a final success/failure, and the transaction record was only created *after* that full round trip completed.

**How the team noticed:** During a partner bank's maintenance window, processor response times spiked from ~200ms to 25+ seconds. The API gateway's request timeout (10s) started firing mid-flight, so the client received a timeout/error — **but the debit had already been sent to and accepted by the processor** before the timeout fired. Users retried the "failed" payment from their app, resulting in **duplicate debits** for the same intended transfer. Customer support tickets ("I was charged twice for one ₹10 transfer to my friend") and a sudden spike in refund requests were the first signals; on-call engineers correlated it with processor latency graphs from the same window.

**Root cause:** The system conflated **"processor is slow to respond"** with **"the debit didn't happen."** Because there was no `PENDING` transaction state created *before* the processor call, a client-side timeout gave no visibility into whether the debit had actually succeeded on the processor's side, and naive client-side retry logic re-submitted a brand-new payment rather than checking on the status of the original one.

**The fix:** The team restructured the flow exactly along the lines described above: perform quick, synchronous **validation-only** calls to the processor (balance check, receiver-account-valid check) with a strict tight timeout; on success, **immediately persist a `PENDING` transaction record** with a unique idempotency key *before* asynchronously dispatching the actual debit/credit instruction; the processor's later callback updates that same record to `SUCCESS`/`DENIED`. Client retries were changed to check the status of the existing `PENDING` transaction by idempotency key rather than blindly creating a new one.

```
BEFORE: fully synchronous call; client timeout leaves        AFTER: sync validation-only + PENDING record
no record of in-flight debit; client retry double-charges     persisted before async dispatch; processor
                                                                 callback resolves final status; retries are
  makePayment() {                                               idempotent lookups, not new debits
     result = processor.debitAndCredit()  // blocks 25s+
     // client times out here, no record ever created
  }                                                            makePayment() {
                                                                   processor.validateOnly()       // fast, sync
                                                                   tx = createTransaction(PENDING)  // BEFORE dispatch
                                                                   processor.dispatchAsync(tx.id)
                                                                   return tx.id  // client can poll/retry-safe
                                                                }
                                                                // later: processor callback -> update tx status
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why is defining scope the very first thing you should do on this question?**
A: "Payment gateway" spans peer-to-peer transfers, merchant checkout (with refunds and multi-tenancy), recurring billing, and more — each of which could independently consume the entire interview. Explicitly narrowing to one flow (peer-to-peer, in this case) up front signals to the interviewer that you can manage scope under time pressure, rather than either freezing or superficially skimming an unbounded problem.

**Q2: Why is `Instrument` modeled as an abstract class with `BankInstrument`/`CardInstrument` subclasses instead of one flat class with optional fields for both?**
A: A flat class with optional bank fields *and* optional card fields (many of which would be null depending on instrument type) doesn't scale — every new instrument type (e.g., a future "wallet balance" type) would keep bloating that one class with more nullable fields. Subclassing keeps each instrument type's fields cohesive and makes it trivial to add a new instrument type as a new subclass without touching existing ones.

**Q3: Why split `InstrumentService` into `BankService` and `CardService` rather than one service handling both?**
A: Bank-specific validation (e.g., IFSC code format, account number checks) and card-specific validation (e.g., CVV, expiry) are different enough that cramming both into a single `addInstrument()` method creates a method that keeps growing conditionals per instrument type — a direct violation of the Single Responsibility Principle, and exactly the kind of design smell an interviewer is trained to catch.

**Q4: How does the `TransactionService` figure out which instrument to *credit* into, since the payer only selects which instrument to debit from?**
A: The payer explicitly picks their own debit instrument, but never picks the receiver's credit instrument directly (you don't get to choose someone else's bank account). Instead, `TransactionService` calls `InstrumentService`/`InstrumentController` to look up the receiver's instruments and resolve one via a priority order: an explicitly-set **preferred** instrument, else a **default** instrument, else potentially the **most recently added** instrument.

**Q5: Why store the same `Transaction` record against both the sender's and the receiver's history rather than just once with a foreign key?**
A: Storing it in both `Map<userId, List<Transaction>>` entries lets `TransactionService.getTransactionHistory(userId)` for **either party** return the same transaction directly without needing a join/lookup across sender and receiver — a pragmatic simplification for an in-memory, no-DB LLD implementation. In a real DB-backed system you'd more likely use indexed queries on sender/receiver columns instead of true duplication.

**Q6: What's the biggest structural weakness of doing the processor call synchronously in the main request path, and how would you defend against it?**
A: The biggest weakness is exactly what caused the production incident above — a slow or timing-out processor leaves the caller with no reliable signal about whether money actually moved, inviting unsafe retries and duplicate debits. The defense is to separate a **fast synchronous validation** step from an **asynchronous settlement dispatch**, persist a `PENDING` transaction (with an idempotency key) before dispatching, and let the processor's callback be the single source of truth for final status — never infer success/failure purely from client-side timeout behavior.

## 🔑 Key Takeaway

For any large-scope LLD prompt like a payment gateway, explicitly narrow the scope first, then work the funnel — requirements → entities → sequence diagram → class diagram — and always be ready to defend a synchronous design against the realistic follow-up that external systems (banks, processors) are slow and eventually consistent, which is exactly why real payment flows separate fast synchronous validation from asynchronous settlement with a `PENDING` state in between.
