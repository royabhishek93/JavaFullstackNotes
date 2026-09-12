# Two-Phase Commit (2PC)
### Distributed Transactions Across Two DBs — Why It's Slow and What Can Fail

---

## PART 1 — THE STUDENT CONVERSATION

**The problem: you need to update two separate databases and both must succeed or both must fail.**

Payment system: when a user buys something:
1. Debit $100 from the user's account (Database A — accounts DB)
2. Create an order record (Database B — orders DB)

If step 1 succeeds but step 2 fails — user paid but has no order. Money gone.
If step 2 succeeds but step 1 fails — user has an order but wasn't charged. Free stuff.

Within a single database, this is trivial: BEGIN; UPDATE; INSERT; COMMIT. Either both happen or neither does.

Across two separate databases: you can't use one database's transaction mechanism. You need a protocol that coordinates both databases to commit or rollback together. That's Two-Phase Commit.

---

## PART 2 — HOW 2PC WORKS

```
Participants:
  Coordinator: the service orchestrating the transaction (your Order Service)
  Participant 1: Accounts DB
  Participant 2: Orders DB

Phase 1 — PREPARE (Vote Phase):
────────────────────────────────────────────────────────────────────

  Coordinator                  Accounts DB        Orders DB
  ──────────                   ───────────        ─────────
  "Can you commit?"──────────► Validate, lock row, write to WAL
                               "YES, I can commit"◄───────────
  "Can you commit?"──────────────────────────────► Validate, lock row, write to WAL
                                                   "YES, I can commit"◄──────────

  After Phase 1: both DBs have written to their WAL and locked resources.
  They are PREPARED — they can commit but haven't yet.
  They will hold locks until told to commit or abort.

Phase 2 — COMMIT (Decision Phase):
────────────────────────────────────────────────────────────────────

  Coordinator: both said YES → send COMMIT to both
  Coordinator────────────────► "COMMIT"
  Accounts DB: commits transaction, releases lock ✓
  Coordinator──────────────────────────────────────► "COMMIT"
  Orders DB: commits transaction, releases lock ✓

  Transaction complete. Both DBs updated. ✓
```

### What Happens When Something Fails

```
Failure in Phase 1 (before commit):
────────────────────────────────────────────────────────────────────

  Orders DB says: "NO, I can't commit" (disk full, constraint violation)
  Coordinator: sends ABORT to both
  Accounts DB: rolls back its prepared transaction, releases lock
  Orders DB: rolls back its prepared transaction, releases lock
  → Clean. Neither DB changed. ✓

Failure of Coordinator AFTER Phase 1, BEFORE Phase 2:
────────────────────────────────────────────────────────────────────

  ┌─────────────┐
  │ Coordinator │  ← CRASHES HERE after receiving both YES votes
  └─────────────┘

  Accounts DB: prepared, holding locks, waiting for COMMIT or ABORT
  Orders DB: prepared, holding locks, waiting for COMMIT or ABORT

  Nobody tells them what to do.
  Both are stuck in PREPARED state, holding locks.
  Other transactions wanting to access those rows → BLOCKED

  This is the "blocking problem" of 2PC:
  If the coordinator dies between Phase 1 and Phase 2,
  participants are stuck holding locks until coordinator recovers.
  If coordinator doesn't recover for 10 minutes → 10 minutes of lock contention.
```

---

## PART 3 — THE BLOCKING PROBLEM DIAGRAM

```
Timeline showing why 2PC is dangerous:
────────────────────────────────────────────────────────────────────

t=0ms   Coordinator sends PREPARE to both DBs
t=5ms   Accounts DB: "YES" (row locked, WAL written)
t=6ms   Orders DB: "YES" (row locked, WAL written)
t=7ms   Coordinator: received both YES, about to send COMMIT
t=7ms   COORDINATOR CRASHES ← power failure, OOM, network partition

  Accounts DB: locked, waiting...   (can't commit, can't rollback — coordinator decides)
  Orders DB:   locked, waiting...

  Other user tries to read Alice's account balance → BLOCKED by lock
  Another order for the same item tries → BLOCKED by lock

  5 minutes later: coordinator restarts, reads WAL, sends COMMIT
  Both DBs finally commit. Locks released.
  Total blocked time: 5 minutes.

  Worst case: coordinator disk failure, WAL lost, coordinator can't recover.
  → Manual intervention required to decide commit or rollback.
  → This has happened at real companies. It's not theoretical.
```

---

## PART 4 — 2PC IN PRACTICE (XA TRANSACTIONS)

```
Java / Spring XA transaction example:
────────────────────────────────────────────────────────────────────

  @Configuration
  public class XAConfig {
      @Bean
      @Primary
      public DataSource accountsDataSource() {
          return new XADataSource("jdbc:mysql://accounts-db:3306/accounts");
      }

      @Bean
      public DataSource ordersDataSource() {
          return new XADataSource("jdbc:mysql://orders-db:3306/orders");
      }
  }

  @Service
  public class OrderService {
      @Transactional  // Spring uses JTA/XA coordinator (e.g., Atomikos, Bitronix)
      public void placeOrder(Order order) {
          accountsRepo.debit(order.getUserId(), order.getAmount());  // Accounts DB
          ordersRepo.save(order);                                      // Orders DB
          // If either fails → Spring rolls back both via XA
      }
  }

Performance cost:
  Single DB transaction: 2ms
  XA 2PC transaction:    10-50ms (2 round trips to each participant + coordinator overhead)
  At 1000 TPS → 2PC is feasible
  At 100,000 TPS → 2PC becomes a bottleneck

Real-world use: 2PC is used in:
  Banking (core banking systems tolerate high latency for correctness)
  Enterprise ERP (SAP, Oracle) for cross-module transactions
  NOT used in: high-throughput web systems (use Saga instead)
```

---

## PART 5 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your payment system needs to debit a user's wallet and create an order. Both must succeed or fail together. How do you implement this?"

**You (architect answer):**

> "The naive answer is 2PC — Two-Phase Commit. The coordinator sends PREPARE to both the
> wallet service and order service. Both lock their rows and say 'ready.' Coordinator sends
> COMMIT. Both commit. If either fails PREPARE, coordinator sends ABORT to both.
>
> The problem I'd flag immediately: 2PC has a blocking failure mode. If the coordinator dies
> after receiving all PREPARE votes but before sending COMMIT, all participants are stuck holding
> locks indefinitely. This is the 3PC problem — and it's why 2PC is avoided in microservices.
>
> For this use case, I'd prefer the Outbox Pattern with Saga. Here's the approach:
>
> Step 1: In a single local MySQL transaction on the Orders DB: INSERT order (status=PENDING),
> INSERT into outbox table (event: DebitUserWallet, amount=$100, order_id=X).
> This single-DB transaction cannot have the coordinator-crash problem.
>
> Step 2: A CDC process (Debezium) reads the outbox and publishes to Kafka.
>
> Step 3: Wallet Service consumes the event, debits the wallet, publishes a WalletDebited event.
>
> Step 4: Order Service listens for WalletDebited, updates order status to CONFIRMED.
>
> If the wallet debit fails (insufficient funds), Order Service listens for WalletDebitFailed
> and marks the order as CANCELLED. This is the Saga compensating transaction.
>
> No 2PC needed. No distributed locks. Eventual consistency across services."

---

## PART 6 — 2PC FAILURE MODES

```
Failure mode            │ When it happens          │ Result
────────────────────────┼──────────────────────────┼───────────────────────────
Participant fails        │ Before sending YES        │ Clean abort (coord gets NO)
in Phase 1              │                           │
                        │                           │
Participant fails        │ After sending YES         │ BLOCKED: participant holds
in Phase 2              │ before receiving COMMIT   │ locks, waits for coord
                        │                           │
Coordinator fails        │ Before sending PREPARE   │ Clean abort (nothing started)
                        │                           │
Coordinator fails        │ After all YES, before    │ BLOCKED: all participants
                        │ sending COMMIT            │ hold locks, unknown state
                        │                           │
Coordinator fails        │ During COMMIT phase      │ PARTIAL COMMIT: some DBs
                        │ (sent to A not B)         │ committed, some didn't
                        │                           │
Network partition        │ Any time                 │ Similar to coordinator fail

Solutions to blocking:
  3PC (3-phase commit): adds a pre-commit phase, reduces (not eliminates) blocking
  Paxos/Raft-based coordinator: coordinator state replicated → survives single crash
  Saga pattern: avoid 2PC entirely with compensating transactions
```

---

## QUICK REFERENCE CARD

```
2PC flow:
  Phase 1 (PREPARE): Coordinator asks all participants "can you commit?"
    → Participants: validate, write to WAL, acquire locks, reply YES/NO
  Phase 2 (COMMIT/ABORT):
    → If all YES: send COMMIT to all
    → If any NO:  send ABORT to all

Properties:
  Atomicity:  all commit or all abort ✓
  Durability: WAL writes before YES vote ✓
  Blocking:   coordinator failure leaves participants holding locks ✗
  Latency:    2 round trips minimum (PREPARE + COMMIT) ✗

When to use 2PC:
  ✓ You have 2-3 databases that must stay in sync
  ✓ Latency acceptable (enterprise, banking internals)
  ✓ All participants support XA protocol
  ✓ Coordinator is highly available (clustered)

When NOT to use 2PC:
  ✗ Microservices (each service owns its DB — use Saga instead)
  ✗ High throughput (>10K TPS — latency unacceptable)
  ✗ Databases don't support XA (DynamoDB, Cassandra don't)
  ✗ Participants span multiple cloud providers / regions

Alternative: Saga Pattern (see Saga_Pattern_Choreography_vs_Orchestration.md)

Interview one-liner:
"2PC guarantees atomicity across multiple databases but has a blocking failure
mode: if the coordinator crashes between PREPARE and COMMIT, all participants
hold locks indefinitely. For microservices, I use Saga with compensating
transactions instead — eventual consistency, but no distributed locks."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** You need to understand 2PC to explain why your design uses Saga instead — "I chose Saga because 2PC has a blocking failure mode" is a much stronger answer than just "I chose Saga."

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **07 — Payment** | Debit sender (DB shard 1) + credit receiver (DB shard 2) must be atomic. 2PC ensures both happen or neither. The blocking failure (coordinator crash between PREPARE and COMMIT) is why most payment systems use Saga instead. |
| **08 — Food Delivery** | Place order + reserve driver + charge customer across 3 services. 2PC would work but too slow for real-time UX. Saga is the real answer — 2PC is the theoretical foundation for understanding why Saga exists. |
| **09 — E-Commerce** | Reserve inventory + process payment + confirm order. 2PC across microservices is impractical — Saga is the answer, but knowing 2PC helps you explain what Saga is compensating for. |

**Architect's one-liner for the interview:**
*"2PC is theoretically correct but practically dangerous in microservices — the coordinator crash between PREPARE and COMMIT leaves all participants holding locks forever, which is why we use Saga with compensating transactions instead."*
