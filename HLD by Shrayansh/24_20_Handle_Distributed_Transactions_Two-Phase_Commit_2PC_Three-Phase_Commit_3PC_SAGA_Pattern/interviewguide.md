# Interview Guide: Distributed Transactions — Two-Phase Commit (2PC), Three-Phase Commit (3PC), SAGA Pattern

## 🗣️ The Interview Scenario

> "A customer places an order. Your `order-service` writes to the Order DB, and your `inventory-service` writes to the Inventory DB — two separate databases, possibly two separate microservices. If the order write succeeds but the inventory write fails, how do you avoid ending up in an inconsistent state? Walk me through Two-Phase Commit, tell me what happens if the coordinator crashes mid-protocol, then explain why you might use SAGA instead for a longer workflow spanning five services."

This is a senior-level staple because it's not really about "do you know the term 2PC" — it's about whether you can reason through the **specific failure windows** (message lost here, crash there) and know which pattern actually fits a given workflow shape (short atomic vs. long-running sequential).

## 🏗️ Architect's Explanation (For a New Developer)

A **transaction** is just a set of operations performed against a database that must behave as one indivisible unit. The classic example: debit ₹100 from account A, credit ₹100 to account B. The four guarantees a transaction gives you are the **ACID** properties:

- **Atomicity** — all operations in the transaction succeed, or all are rolled back. No partial completion.
- **Consistency** — the DB moves from one valid state to another valid state; it never gets stuck half-updated.
- **Isolation** — even when multiple transactions run concurrently, each one behaves as though it ran alone, in some serial order.
- **Durability** — once a transaction commits, the result survives even a subsequent crash.

Here's the catch, and it's the entire reason this topic exists: **a transaction is local to a single database.** If your `order-service` and `inventory-service` each have their *own* database with their *own* transaction manager, a rollback triggered in one database's transaction has **no way to reach into and roll back** a transaction in a completely different database. If the order update succeeds and commits, but the inventory update then fails, nothing automatically undoes the order update — you're left with an inconsistent state across two systems.

To coordinate a "transaction" that spans multiple independent databases/services, you need one of three patterns:
1. **Two-Phase Commit (2PC)** — a coordinator asks everyone "are you ready?" before telling everyone to actually commit.
2. **Three-Phase Commit (3PC)** — an improvement on 2PC that avoids certain blocking scenarios, at the cost of more complexity (rarely used in practice).
3. **SAGA Pattern** — for long-running, sequential, multi-step workflows where holding locks the whole time (as 2PC/3PC effectively require) isn't practical; instead, each step commits independently and failures trigger a chain of compensating rollbacks.

## 📊 Visualize It

**Two-Phase Commit — the happy path:**

```
                     ┌─────────────────────┐
                     │ Transaction          │
                     │ Coordinator           │
                     └──────────┬───────────┘
           PHASE 1: "prepared to commit?"      │
           ┌─────────────────────┼─────────────────────┐
           ▼                                            ▼
     Order Service                              Inventory Service
     (locks row, makes change,                  (locks row, makes change,
      NOT yet committed)                         NOT yet committed)
      responds: "YES, ready"                      responds: "YES, ready"
           │                                            │
           └─────────────────────┬─────────────────────┘
                     PHASE 2: coordinator decides → "COMMIT"
           ┌─────────────────────┼─────────────────────┐
           ▼                                            ▼
     Order Service COMMITS                     Inventory Service COMMITS
```

**2PC blocking failure — commit message lost after phase 1 succeeds:**

```
Coordinator: got YES from both participants → decided COMMIT → wrote decision to its log
Coordinator ──✖ CRASHES before sending "commit" to Order Service ──✖

Order Service: already said "YES, ready", now stuck waiting
              → CANNOT unilaterally decide commit or abort
              → BLOCKED until coordinator recovers and reads its log
```

## 🔧 Deep Dive: How It Actually Works

### Two-Phase Commit (2PC)

**Roles:** a **transaction coordinator** interacts with all **participants** (e.g., Order microservice, Inventory microservice). Every participant must be reachable/supported by the coordinator up front.

**Phase 1 — Prepare / Voting Phase:**
- Coordinator sends the update operation to every participant.
- Coordinator then asks each participant: *"are you prepared to commit?"*
- Each participant attempts the operation, **puts a lock on the affected row, makes the change in its DB, but does NOT commit yet.**
- Each participant replies **YES** (prepared) or **NO** (failed to prepare).

**Phase 2 — Decision / Commit Phase:**
- If **all** participants replied YES → coordinator decides **COMMIT**, and sends a commit message to everyone; each participant commits and releases its lock.
- If **any** participant replied NO → coordinator decides **ABORT**, and sends an abort message to everyone; each participant rolls back its uncommitted change.

**Persistent logging:** both the coordinator and every participant write to their **own log file** (durable storage) *before* sending each message — e.g., the coordinator logs "sent prepare," then later logs "decided commit" before actually sending the commit message. This log is what enables recovery after a crash.

**The three specific failure scenarios interviewers probe:**

1. **Prepare message lost** (coordinator crashes before/while sending it): the participant, having already locked its row, waits for a timeout, then **safely aborts** on its own — since it never told the coordinator "yes," it's always safe to unilaterally abort.
2. **"OK" (vote) message lost** (participant crashed or its response never arrived): the coordinator waits for a timeout, then **aborts the entire transaction** and instructs all participants to roll back. When the failed participant recovers, it can ask the coordinator what happened and follow that decision.
3. **Commit/decision message lost** (coordinator crashes after deciding, before informing everyone): **this is the dangerous, blocking case.** A participant that already said "YES" cannot unilaterally decide to commit or abort — it doesn't know what the other participants said, so it must **block and wait** for the coordinator to recover and consult its log to find out the actual decision. **This blocking behavior is the core weakness of 2PC.**

### Three-Phase Commit (3PC)
3PC exists specifically to remove the blocking problem from case #3 above. It splits 2PC's single commit/decision phase into **two** phases:

1. **Prepare / Voting Phase** — identical to 2PC.
2. **Pre-Commit Phase** (new) — the coordinator shares its decision (commit or abort) with all participants *as information only* — not yet an instruction to actually act. This means that if the coordinator crashes right after this phase, participants already know what the intended outcome was.
3. **Commit Phase** — the coordinator instructs everyone to actually commit (or abort), and they do so.

**Why this unblocks participants:** if the coordinator crashes *after* sending pre-commit messages, participants can check their own logs — if they received a "pre-commit: intend to commit," they can safely proceed to commit themselves rather than waiting indefinitely. Participants can also **query each other** ("did you get a pre-commit message?") — if none of them received one, they can safely conclude the coordinator failed before making any decision at all, and it's safe to abort collectively.

**Why 3PC isn't popular in practice:** despite solving the blocking problem, it is **significantly more complex to implement and reason about** — extra round trips, extra failure cases to handle (e.g., what if the pre-commit message itself is lost) — so most real systems either accept 2PC's blocking risk (mitigated by fast coordinator recovery/HA) or use SAGA instead.

### SAGA Pattern
2PC and 3PC are **synchronous** — the whole transaction happens in a single tightly-coordinated flow, and every participant holds locks until it completes. That's fine for short transactions, but becomes impractical for a **long-running, sequential, multi-participant workflow** (e.g., Participant 1 → Participant 2 → Participant 3 → Participant 4 → Participant 5, where each step only starts after the previous one succeeds) — you don't want to hold DB locks open across that entire chain.

SAGA is **asynchronous**: each participant commits its own local transaction independently and then triggers the next step (rather than everyone waiting under one shared lock). If a step downstream fails:
- The failing participant **publishes an event** (e.g., onto a queue) indicating failure.
- The **previous participant reads that event and rolls back its own change** (a "compensating transaction"), then publishes its own rollback event.
- This **cascades backward** through the chain — each prior participant rolls back in turn upon hearing from the one after it — until the very first participant has also rolled back.

This backward-cascading, event-driven rollback is exactly what makes SAGA suitable for long-running workflows: no global lock is held anywhere; instead, failure recovery is handled via a **chain of compensating actions** communicated asynchronously.

## 🔥 Real Production Incident & Fix

**What broke:** A ride-hailing platform used 2PC across a "booking" transaction coordinator and two participants: a `driver-assignment-service` and a `fare-calculation-service`. During a regional network partition event, the transaction coordinator pod crashed **after** deciding to COMMIT (and durably logging that decision) but **before** it could send the commit instruction to `fare-calculation-service`. That participant had already replied "prepared" in phase 1, holding a row-level lock on the fare record, and now had no way to know the outcome — it blocked, waiting.

**How it was detected:** An APM trace dashboard (e.g., New Relic) showed request latency for a specific fare-record row spiking to several minutes with no error, just an open, held lock — visible via the database's `pg_locks`/lock-wait diagnostics showing a long-held row lock with no corresponding active query progressing. On-call correlated the timestamp with a coordinator pod restart event in the orchestration platform's event log.

**Root cause:** Classic 2PC blocking scenario — the coordinator crashed in the exact window between deciding COMMIT and broadcasting that decision to all participants, and the affected participant had no mechanism to independently resolve its own state (it could only wait or query the coordinator, which was temporarily unreachable).

**The fix:** Short-term, the team added a **coordinator recovery protocol**: when the coordinator pod restarted, it immediately replayed its transaction log on startup and re-sent any decisions (commit/abort) that hadn't been fully acknowledged by all participants, unblocking the stuck `fare-calculation-service` within seconds of the coordinator coming back up. Medium-term, the team **re-architected the booking flow to use SAGA** instead of 2PC for this specific multi-step, cross-service flow, since holding a lock across a network-partition-prone coordinator was deemed too risky for a workflow that didn't strictly need atomic all-or-nothing semantics — compensating rollbacks (e.g., "release driver assignment" as a compensating action) were an acceptable trade-off for eliminating the blocking failure mode entirely.

```
BEFORE (2PC, coordinator crash after decision, before broadcast):
Coordinator: decided COMMIT, logged it ──✖ CRASH ──✖ never told fare-service
fare-calculation-service: BLOCKED, holding lock, for several minutes

AFTER (recovery protocol + SAGA migration):
Coordinator restart → replays log → re-sends decision → unblocks in seconds
(long-term: SAGA removes the lock-holding coordinator dependency altogether)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why can't a participant that already voted "YES" in 2PC just decide on its own to commit if it doesn't hear back from the coordinator?**
Because it has no visibility into what the *other* participants voted. If even one other participant voted "NO," the coordinator's decision would be ABORT — a participant unilaterally committing based on its own "YES" vote could violate atomicity if the group decision was actually to abort. This uncertainty is precisely why it must block and wait rather than guess.

**Q2: How does 3PC's pre-commit phase actually prevent blocking, mechanically?**
By separating "what the decision is" from "act on the decision now," 3PC ensures the decision is durably communicated to participants *before* asking them to act on it. If the coordinator dies after this pre-commit broadcast, participants already have the information needed to independently proceed (or, by querying each other, determine no decision was ever made and it's safe to abort) — removing the single point of uncertainty that caused 2PC's blocking.

**Q3: Why is SAGA described as asynchronous, and what's the concrete risk of that asynchrony?**
It's asynchronous because each participant commits its own step and moves on without holding a lock while waiting for downstream steps — coordination happens via published events rather than a live, synchronous handshake. The risk is a longer window of **temporary inconsistency**: between step 2 committing and step 5 potentially failing and triggering a rollback cascade, the system is in a state where step 2's effect is visible even though the overall business transaction hasn't fully succeeded yet — callers must be designed to tolerate that intermediate state.

**Q4: When would you explicitly choose SAGA over 2PC even for a short transaction?**
When the participants are owned by different teams/services that can't (or shouldn't) share a single transaction coordinator's locking semantics, or when the workflow's compensating actions are well-defined and acceptable — SAGA trades strict atomicity for looser coupling and no long-held locks, which is often preferred in microservice architectures specifically to avoid the kind of coordinator-crash blocking scenario described above.

**Q5: What's a "compensating transaction" in SAGA, and does it perfectly undo the original action?**
It's the explicit rollback logic each participant implements for its own step (e.g., "release the reserved inventory" to undo "reserve inventory"). It doesn't use a DB-level rollback like 2PC's abort — it's application-level logic, and it doesn't always perfectly restore the exact prior state (e.g., a "send email" step can't be undone, only followed by a "send cancellation email" compensating step) — this is a key nuance interviewers listen for.

**Q5b (bonus): How do coordinator and participant logs work together to resolve stuck transactions in 2PC?**
Both sides persist every action to a local durable log before sending or acting on a message. When a crashed party recovers, it consults its own log to reconstruct where it left off (e.g., "did I send prepare?", "did I decide commit?") and can either resume, query the other party, or safely conclude what's already known — this log is the entire mechanism enabling recovery in both 2PC and 3PC.

**Q6: Between 2PC, 3PC, and SAGA, which is used most in real distributed systems today, and why?**
2PC is still used where strict, short-lived cross-database atomicity is required and infrastructure support exists (e.g., some distributed SQL databases). SAGA is heavily used in microservice architectures for longer business workflows. 3PC, despite solving 2PC's blocking problem in theory, is rarely used in production because of its implementation complexity relative to the marginal benefit.

## 🔑 Key Takeaway
Say this out loud: **"2PC guarantees atomicity across databases via a prepare-then-commit handshake but can block participants if the coordinator crashes at the wrong moment; 3PC fixes that blocking at the cost of complexity; SAGA sidesteps the whole problem for long-running workflows by letting each step commit independently and using a chain of compensating rollbacks instead of holding locks across the entire flow."**
