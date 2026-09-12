# Interview Guide: Design an Idempotent POST API

## 🗣️ The Interview Scenario

> "A customer's mobile app retries a `POST /payments/charge` request three times because of a flaky network connection. Design a mechanism so the customer is charged exactly once, no matter how many times that request is retried — including the case where two retries somehow arrive at your service at the exact same moment, on two different servers."

This is a favorite in fintech/e-commerce interviews (the walkthrough notes it was recently asked at a Singapore-based top product company) precisely because it forces you to reason about **both** a sequential-retry race and a true parallel race — most candidates only solve the easy one.

## 🏗️ Architect's Explanation (For a New Developer)

First, untangle two words that sound similar but mean different things. **Concurrency** is about *multiple different users* fighting over *one shared resource* — like a hundred people all trying to book the very last movie seat at the same instant. **Idempotency** is about *one client retrying the same operation* multiple times and making sure it only "counts" once — like a customer clicking "Pay" three times because the spinner froze, and making sure they're charged exactly once, not three times.

Here's the key insight that unlocks the whole design: **GET, PUT, and DELETE are already naturally idempotent, but POST is not.** A `GET` never changes anything, so calling it 1,000 times is harmless. A `PUT` that says "set my name to Shreyansh" gives the same end result whether you call it once or ten times — the record just ends up saying "Shreyansh" either way. But a `POST` that says "create a $10 payment from Shreyansh to Hardik" creates a **brand-new row every single time you call it** — retry it three times and you've just made three separate payments. Idempotency handling exists specifically to bolt POST-safety onto an operation that is, by its very nature, a "create a new thing" instruction.

The mental model for the fix: treat every POST request as carrying a **claim ticket** (an idempotency key). The very first time a ticket is presented, the server does the real work and stamps the ticket "used." Every subsequent time that *same* ticket shows up — whether five seconds later or in the same millisecond from a different server — the server's job is just to check the ticket's stamp and say "already handled," never to redo the work.

## 📊 Visualize It

**Sequential duplicate — the retry-after-timeout case:**

```
Client generates key K --POST--> Server (times out client-side, but
                                          server keeps processing)
Server: no key K in DB -> CREATE entry (status=created) -> do the work
                        -> SUCCESS -> update status=consumed -> return 201

Client retries with SAME key K --POST--> Server: key K found, status=consumed
                                        -> do NOT redo the work
                                        -> return 200 (already completed)
```

**Parallel duplicate — the race-condition case, before/after a mutex:**

```
BEFORE (no critical section):                 AFTER (mutex around check+create):

Req1 --\  both read DB at the SAME time        Req1 -> [enter mutex] -> check DB
Req2 --/  both see "key not found"                   -> not found -> create
        -> BOTH create a resource                    -> mark consumed -> [exit]
        -> DUPLICATE resource created!         Req2 -> [waits for mutex] -> check DB
                                                       -> found, consumed -> return 200
                                                       (no duplicate created)
```

## 🔧 Deep Dive: How It Actually Works

### 1. Concurrency vs. Idempotency — don't conflate them
- **Concurrency:** multiple *different* users trying to access/modify the **same resource** at once (the example given: many people trying to book the same movie seat on a ticketing app — a classic contention problem).
- **Idempotency:** enabling a **client** to safely **retry** the same operation any number of times without unwanted side effects. The explicit definition: a client can retry N times safely, without worrying about the side effects of the operation being repeated.

### 2. Why GET/PUT/DELETE are safe by default, and POST isn't
- **GET:** by nature has no side effect on the DB — a duplicate GET just returns whatever data already exists; nothing changes.
- **PUT:** described as idempotent by nature — the example given is updating a name field from "SJ" to "Shreyansh." Calling that same PUT any number of times converges to the same end state; it doesn't create additional side effects.
- **POST:** explicitly **not idempotent by nature** — the two motivating examples are (a) adding an item to a cart, and (b) making a payment (Shreyansh pays Hardik $10). A duplicate POST for either of these **creates a new resource/row each time** (a second cart item, a second payment) — this is the specific problem idempotency handling exists to solve. Only POST needs this special handling; GET/PUT/DELETE "already don't have to do anything" for idempotency.

### 3. Two distinct failure modes to design for
- **Sequential duplicates:** requests arrive one after another in time. The classic trigger scenario: client sends a POST, a **timeout** occurs on the client side (client believes the call failed), but the **server is actually still processing** it successfully — the client then retries, creating a second, duplicate request for what is logically the same operation.
- **Parallel duplicates:** two POST requests carrying the **same idempotency key** arrive at virtually the **same instant** — the example given is the same logical request being fired from two different browser tabs at once. This case is harder because a naive "check DB, then create if absent" flow has a race window between the check and the write.

### 4. The core mechanism: a universal unique idempotency key
- The **client** generates the key — typically a **UUID** (many libraries available for this), optionally with the **operation name and/or a timestamp appended** to strengthen uniqueness. The exact key-generation scheme is explicitly called an **agreement between client and server** — it can vary client-to-client, but a UUID is described as the generic, always-safe baseline because it's inherently unique.
- The client sets this key into the **request header** and calls the server's POST endpoint.

### 5. The server-side flow, step by step
1. **Validate the key is present.** If the idempotency key is missing from the header, return **HTTP 400** (validation error) immediately.
2. **Read the DB for this key.** Check whether an entry for this idempotency key already exists.
3. **If it does NOT exist (this is the original/first request):**
   - Create a new entry for the key with an initial status — described in the walkthrough as **"created"** (or equivalently, "claimed").
   - Perform the actual business operation (e.g., add the item to the cart, process the payment).
   - On success, **update the status to "consumed"** and mark the resource as created.
   - Return **HTTP 201** (resource successfully created).
4. **If it DOES already exist (a duplicate arriving sequentially, after the original):**
   - Check the existing entry's **status**:
     - If status is **"consumed"** (the original request already fully completed) → do **not** redo the operation or create anything new; simply return **HTTP 200** (already completed — idempotent no-op).
     - If status is still **"created"** (the original request is still in flight / hasn't finished) → return **HTTP 409 Conflict**, signaling "this same request is already being processed, please wait/retry later."

### 6. Solving the parallel-request race with a critical section
- The sequential flow above has a hole: if **two requests with the same key arrive at the same server at virtually the same instant**, both can read the DB **before either has written anything**, both see "key not found," and **both proceed to create the resource** — producing exactly the duplicate the whole mechanism was meant to prevent.
- The fix: wrap the **check-then-create** logic in a **critical section** using mutual exclusion — the walkthrough names **mutex**, **`Semaphore`**, or a **`synchronized`** block as concrete mechanisms — so only **one** request can execute that check-and-create logic at a time. The first request to acquire the lock creates the resource, marks it consumed, and returns; the second request (now serialized behind the lock) re-reads the DB, finds the key already consumed, and returns **200** without creating a duplicate.

### 7. Extending the fix across a distributed cluster
- A local in-process mutex only protects against races **within a single server process** — it does nothing if the two parallel duplicate requests happen to land on **different machines/pods** in a cluster.
- The proposed fix: use a **distributed cache (Redis)** instead of (or alongside) the primary DB for the idempotency-key check, because **cache synchronization is dramatically faster (milliseconds)** than trying to synchronize a check-and-write across a distributed database cluster. Redis is called out as making it easy to achieve this kind of cross-server atomicity/synchronization for the idempotency check — echoing the exact same "use Redis for atomic distributed counters" pattern used for rate limiting.

## 🔥 Real Production Incident & Fix

**What broke:** A payments POST endpoint (`POST /wallet/charge`) double-charged a customer during a mobile network "retry storm" — the customer's app retried the charge request after a flaky cellular handoff, and the customer ended up debited twice for a single $500 purchase within about 400 milliseconds of each other.

**How it was detected/diagnosed:** The customer filed a support ticket noticing two identical debit line items in their statement. Engineering pulled the payment service's access logs filtered by the customer's idempotency key and found **two** requests carrying the **exact same key**, timestamped 380ms apart, that had each been processed on **two different pods** behind the load balancer — each pod's application logic had independently checked its local view of "has this key been consumed?" and both concluded "no."

**Root cause:** The idempotency check-then-create logic was protected by an in-process `synchronized` block, which correctly prevented duplicate processing **within a single server instance** — but the payment service ran behind a load balancer distributing traffic across many pods, and each pod's synchronized block only serialized requests hitting *that* pod. The two near-simultaneous retries happened to be routed to two different pods, so the local mutex provided zero protection against the true, cross-machine race condition.

**The fix:** The team introduced a **Redis-backed distributed check** (using an atomic "set-if-not-exists" style operation) as the very first gate before any pod attempts the check-then-create DB flow — the first pod to successfully claim the key in Redis proceeds with the charge; any other pod that loses that atomic race immediately treats the request as a duplicate and returns the cached "already processed" response, without touching the payment logic at all. Post-fix, load testing with simulated concurrent retries across multiple pods showed zero duplicate charges, versus a measurable duplicate rate under the old in-process-mutex-only design.

```
BEFORE (mutex is per-pod, race survives across pods):   AFTER (Redis-backed distributed claim):

Pod A: mutex -> check "not found" -> charge -> $500      Pod A --\
Pod B: mutex -> check "not found" -> charge -> $500      Pod B ---> Redis SETNX(key)
   (each pod's mutex only sees its OWN process)             -> only ONE pod wins the
   -> customer charged TWICE                                   claim -> only ONE charge
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: What's the precise difference between idempotency and concurrency control?**
Concurrency control is about arbitrating multiple *different* clients/users competing over the *same* resource (e.g., two people booking the last seat). Idempotency is about making a *single logical operation from one client* safe to retry any number of times without unwanted side effects, regardless of whether other users are involved at all.

**Q2: Why are GET/PUT/DELETE naturally idempotent but POST isn't?**
GET has no side effects by definition, so repeats are harmless. PUT replaces/sets a resource's state to a specific target value, so repeating it converges to the same end state rather than compounding. POST's semantic is "create a new resource," so by definition, calling it again creates *another* new resource — that's the exact behavior idempotency handling needs to suppress for duplicate calls.

**Q3: Who should generate the idempotency key — the client or the server — and why?**
The client generates it (typically a UUID, optionally combined with operation name/timestamp), because only the client knows whether a given call is a genuine retry of a previous attempt versus a brand-new distinct request; if the server generated the key, it would have no way to distinguish "this is the same logical attempt as before" from "this is a new request."

**Q4: What HTTP status should you return for a duplicate that's still in-flight, versus one that already completed?**
If the original request already finished (status "consumed"), a duplicate returns **HTTP 200** — a successful, idempotent no-op that doesn't recreate anything. If the original request is still being processed (status still "created"), the duplicate returns **HTTP 409 Conflict**, signaling that the same request is already in progress and the client should wait/retry later rather than assuming failure.

**Q5: How do you handle the exact same idempotency key arriving at two different servers at nearly the same instant?**
A local mutex/synchronized block only protects a single process, so it does nothing across servers. The fix is to route the check-and-claim step through a shared, distributed store (Redis) using an atomic operation, so only one server instance can "win" the claim for a given key regardless of which physical machine each duplicate request landed on.

**Q6: What states should the idempotency-key record's status machine have?**
At minimum: a "created"/"claimed" state (set immediately when the original request is first seen, before the business operation completes) and a "consumed" state (set once the business operation succeeds). The "created but not yet consumed" state is exactly what lets a sequential duplicate arriving mid-processing be told "409, please wait" instead of either silently duplicating the operation or incorrectly returning success before the original work is actually done.

## 🔑 Key Takeaway

Say this out loud in the interview: **"Idempotency for POST is really a state machine on a client-generated key — created vs. consumed — plus a critical section (local mutex for single-server races, Redis-backed atomic claim for cross-server races) so that no matter how many times or how simultaneously a request is retried, the underlying operation only ever actually executes once."**
