# Interview Guide: Two-Phase Locking (2PL) — Basic, Conservative, and Strong Strict (Rigorous) 2PL

## 🗣️ The Interview Scenario

> "You've told me pessimistic concurrency control can deadlock. Now specifically explain Two-Phase Locking: what are its two phases, what's the difference between 'basic,' 'conservative,' and 'strict/rigorous' 2PL, and why does the industry mostly use strict 2PL over the other two variants? Also — walk me through a concrete deadlock scenario and tell me how a scheduler would actually detect and resolve it."

This is the natural follow-up once a candidate has correctly identified pessimistic locking as deadlock-prone — the interviewer now wants to see if you know the **specific protocol** (2PL) that formalizes pessimistic locking, and whether you understand the **real tradeoffs** between its variants (deadlock vs. cascading aborts vs. concurrency loss).

## 🏗️ Architect's Explanation (For a New Developer)

Two-Phase Locking (2PL) is the formal rulebook behind "pessimistic" concurrency control. The name comes from exactly two phases every transaction must go through, **in order, without going back**:

1. **Growing Phase** — the transaction is only allowed to **acquire** locks (never release any). It keeps taking more and more locks as it needs to touch more rows.
2. **Shrinking Phase** — the transaction is only allowed to **release** locks (never acquire any new ones).

Think of it like a "ratchet": once you start releasing locks, you can never go back to acquiring more. This strict two-phase discipline is what gives 2PL its correctness guarantee (serializability) — but it doesn't automatically prevent every problem. Depending on **exactly when** locks are acquired and released within those two phases, you get three different flavors, each with a different tradeoff:

- **Basic 2PL** — simplest, most concurrency, but suffers from **both deadlock and cascading aborts**.
- **Conservative 2PL** — acquires *all* needed locks upfront before doing any work, eliminating deadlock entirely, but at the cost of much lower concurrency (and cascading aborts can still happen).
- **Strong Strict (Rigorous) 2PL** — holds *all* locks until the very end of the transaction (commit/abort), eliminating cascading aborts, but deadlock is still possible. **This is the variant most widely used in industry**, because cascading aborts are considered far more expensive/dangerous than deadlocks (which have well-known detection and resolution strategies).

## 📊 Visualize It

**The shape of a valid 2PL transaction — locks only ever go up, then only ever go down:**

```
Lock Count
   ▲
   │        ┌───┐
   │       ╱     ╲
   │      ╱       ╲
   │     ╱         ╲___
   │    ╱ GROWING    SHRINKING ╲
   │   ╱  (acquire    (release)  ╲
   │  ╱    only)                  ╲
   └──────────────────────────────────► Time
        Never: acquire → release → acquire again (that breaks 2PL)
```

**Deadlock via lock upgrade (a subtle case — even ONE shared row can deadlock):**

```
Row A:  T1 holds SHARED lock  |  T2 holds SHARED lock   (both can read simultaneously)

T1 wants to UPGRADE its shared lock → EXCLUSIVE (to write)
        → must wait for T2 to release its shared lock

T2 wants to UPGRADE its shared lock → EXCLUSIVE (to write)
        → must wait for T1 to release its shared lock

   T1 waits on T2, T2 waits on T1  →  DEADLOCK (even though it's just ONE row!)
```

## 🔧 Deep Dive: How It Actually Works

### The Two Phases, Formally
- **Growing Phase:** the transaction requests locks from the **lock manager**, which either **grants** or **denies** each request (denied if another transaction already holds a conflicting lock on that row). The transaction can only acquire more locks during this phase — never release.
- **Shrinking Phase:** the transaction can now only **release** previously-acquired locks — no new lock acquisition is permitted at all, for the rest of the transaction's life.

All three variants below obey this same two-phase shape; they differ only in **when exactly** the growing phase starts/ends and **when exactly** locks are actually released.

### Variant 1: Basic 2PL
- Locks can be acquired incrementally as needed (e.g., lock A, do some work, lock B, do more work) during the growing phase.
- Locks can then be released incrementally during the shrinking phase — **potentially even before the transaction commits** (e.g., unlock A, then later unlock B, then commit). Alternatively, all locks might simply be released automatically at the moment of commit.
- **This is the version used to illustrate the classic problems**, because it allows the shortest possible lock-holding window, which is efficient but exposes two serious issues:

**Problem 1: Deadlock**
- **Classic two-resource case:** T1 locks A, T2 locks B; then T1 wants to also lock B (must wait on T2) while T2 wants to also lock A (must wait on T1) — circular wait, deadlock.
- **Subtler single-resource case (lock upgrade deadlock):** T1 and T2 both hold a **shared** lock on the *same single row* A (both can read simultaneously — shared locks are compatible with each other). Now both T1 and T2 want to **upgrade** their shared lock to an **exclusive** lock (to write). Neither can upgrade until the *other* releases its shared lock — but neither will release, because each is waiting to acquire the exclusive lock first. This proves deadlock can happen **even with just one shared piece of data**, not only in multi-resource scenarios.

**Deadlock Prevention/Resolution Strategies (four approaches covered):**

1. **Timeout-based:** a scheduler tracks how long each transaction has been waiting for a lock; if it waits "too long," the scheduler **assumes** a deadlock and aborts it. **Disadvantage:** this can produce **false positives** — a transaction might just be legitimately slow (no actual deadlock), yet still get wrongly aborted because it happened to exceed the timeout threshold.
2. **Wait-For Graph (WFG):** a **directed graph** where an edge from T_i → T_j means "T_i is waiting for T_j to release a lock." The scheduler periodically checks this graph for **cycles** — a cycle means a deadlock exists among those transactions. When a lock is released, the corresponding edge is removed. This is considered a more principled/accurate approach than blind timeouts.
   - **Choosing the "victim" to abort from a detected cycle** — the scheduler considers multiple factors, not just picking arbitrarily: (a) **how much work/effort the transaction has already invested** (favor keeping transactions that have done more work), (b) **how much more time/work the transaction still needs to finish** (favor aborting ones that would take longer to complete anyway), (c) **the cost of aborting** — i.e., how many updates would need to be rolled back, and (d) **how many separate cycles a transaction participates in** — a transaction involved in multiple deadlock cycles is a stronger candidate for being the victim, since aborting it may resolve several cycles at once.
3. **Timestamp-based deadlock avoidance:** every transaction gets a timestamp when it starts; **older timestamp = higher priority.** Two competing schemes:
   - **Wait-Die:** an **older** transaction is allowed to **wait** for a lock held by a newer transaction. A **newer** transaction requesting a lock held by an older transaction must **die** (abort) immediately rather than wait.
   - **Wound-Wait:** an **older** transaction requesting a lock held by a newer transaction will **"wound"** it — forcibly aborting the newer transaction so the older one can proceed. A **newer** transaction requesting a lock held by an older transaction must simply **wait**.
   - Both schemes guarantee no deadlock by ensuring waits only ever flow in one consistent priority direction (never a cycle), but they differ in *who* gets aborted vs. who waits.

**Problem 2: Cascading Aborts**
- Scenario: T1 locks A, updates it (value 10 → 11), and **releases the lock on A before its own transaction fully completes**. T2 then acquires a lock on A, reads the updated value (11), and proceeds to use it in its own computation. **T1 then aborts** (rolls back to 10). Now T2's read of "11" was a **dirty read of data that no longer validly exists** — so T2 must **also be aborted**, even though T2 did nothing wrong itself. This chain reaction of forced aborts is called a **cascading abort**, and it happens specifically because basic 2PL allows releasing a lock **before** the transaction is actually finished/committed.

### Variant 2: Conservative 2PL (a.k.a. Static 2PL)
- **Avoids deadlock entirely** by requiring a transaction to **acquire ALL the locks it will ever need, upfront, before executing any of its actual read/write operations.**
- Mechanism: the scheduler tries to grant every needed lock (on A, B, C, etc.) at once at the start. **If even one of those locks can't be acquired (already held elsewhere), NONE of the locks are granted, and the transaction waits** until all of them become simultaneously available.
- **Why this eliminates deadlock:** since a transaction never starts partial work while holding only *some* of what it needs, it never ends up in a position of holding some locks while waiting on others that a different transaction is also waiting to acquire from it — the circular-wait precondition for deadlock simply can't form.
- **Disadvantages:**
  - **Significantly lower concurrency** — transactions must wait for the full set of locks to be simultaneously available, even if they'd only need some of them early on.
  - **Extra scheduler overhead** — the scheduler must know, in advance, exactly which rows a transaction will read/write, which requires additional upfront analysis/bookkeeping.
  - **This is why conservative 2PL is mostly NOT used in practice** — the concurrency loss is considered too costly relative to the deadlock-avoidance benefit.
  - Note: cascading aborts are **still possible** under conservative 2PL if locks are released gradually before commit (the transcript demonstrates a case releasing locks one at a time in the shrinking phase, which is legal under conservative 2PL as long as growing-phase acquisition happened all at once upfront).

### Variant 3: Strong Strict 2PL (a.k.a. Rigorous 2PL)
- **Growing phase:** locks can still be acquired **gradually**, exactly like basic 2PL (no need to grab everything upfront).
- **Shrinking phase:** the critical difference — **ALL locks (shared and exclusive) are held until the very end of the transaction** (only released together at commit or abort). No gradual release is permitted at all.
- **This directly eliminates cascading aborts:** since no other transaction can ever acquire a lock on data that a still-in-flight transaction has modified (the modifying transaction won't release that lock until it's fully committed or aborted), nobody can ever perform a "dirty read" of an uncommitted change in the first place.
- **Deadlock is still possible** under this variant — strict/rigorous 2PL does nothing to prevent the classic circular-wait scenario; you still need one of the deadlock detection/resolution strategies (typically **Wait-For Graph**) running alongside it.
- **Why this is the most widely used variant in industry:** cascading aborts are generally considered a **worse, more expensive** problem than deadlocks — a single upstream abort can force a chain of unrelated transactions to also abort, whereas deadlocks are a well-understood, detectable, and resolvable problem (via WFG + a principled victim-selection policy).

### Worked Example — Money Transfer Highlighting the Concurrency-Anomaly Difference
Scenario: T1 transfers ₹10 from A to B (A: 100→90, B: 100→110); T2 computes `A + B`. Starting balances: A=100, B=100 (correct final total after T1 completes should be 200: A=90, B=110).

- **Under Basic 2PL** (locks released gradually, mid-transaction): T2 can end up reading A **after** T1's update (90) but B **before** T1's update (100) — computing `90 + 100 = 190` instead of the correct `200`. This happens precisely because basic 2PL allows T1 to release its lock on A (letting T2 read the new value) while T1 hasn't yet finished updating B.
- **Under Conservative 2PL:** T1 acquires locks on **both** A and B upfront before doing any work; T2 must wait until T1 releases **both** locks (which happens only after both updates are complete) before it can acquire either — so T2 correctly reads `90 + 110 = 200`.
- **Under Strong Strict 2PL:** similarly, since T1 doesn't release **any** lock until full commit, T2 is blocked from reading either A or B until both updates are finalized, again correctly yielding `200`.

This worked example is the clearest illustration of *why* basic 2PL's early-release behavior is dangerous even without an outright abort — it can produce silently incorrect computed results from a concurrently-running reader.

## 🔥 Real Production Incident & Fix

**What broke:** A banking service used **Basic 2PL** semantics (releasing locks incrementally, before full transaction commit, to maximize concurrency) for a funds-transfer transaction that updated a source account and a destination account in two separate statements. A reporting job concurrently read the destination account's balance to compute a customer's total balance across multiple accounts. During a period of high transfer volume, customer-facing balance totals started intermittently showing values that didn't match the sum of individually-viewed account balances — a customer complained their "total balance" was ₹1,900 short of what their two account pages showed added together.

**How it was detected:** A daily balance-reconciliation batch job flagged discrepancies between the "total balance" cache and the sum of live account balances for a small percentage of accounts. Correlating discrepancy timestamps with the transaction audit log showed the reporting job's read consistently landed **between** the source account's debit commit and the destination account's credit commit — i.e., mid-transfer, reading a partially-updated state, exactly like the `90 + 100 = 190` scenario.

**Root cause:** The transfer transaction released its lock on the source account row as soon as that individual statement completed, **before** the destination account's credit statement had also committed — a direct consequence of using basic 2PL's early-release behavior instead of holding both locks until the full transaction finished.

**The fix:** The team migrated the transfer transaction to **Strong Strict (Rigorous) 2PL** semantics — configuring the ORM/transaction manager to hold all row locks acquired during the transfer until the entire transaction committed, rather than releasing them per-statement. They paired this with a standard **Wait-For Graph**-based deadlock detector (already provided by their RDBMS) to handle the residual deadlock risk that strict 2PL doesn't eliminate, accepting occasional transaction retries as a far cheaper cost than silently incorrect balance reads.

```
BEFORE (Basic 2PL, early lock release):             AFTER (Strong Strict 2PL, hold until commit):
T1: lock(A) → debit → UNLOCK(A) → lock(B) → credit  T1: lock(A) → debit → lock(B) → credit → COMMIT → unlock both
T2 reads A (new) + B (old) = WRONG total ✖          T2 blocked from reading either until T1 fully commits ✔
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Can a deadlock happen in 2PL even when there's only a single shared row involved?**
Yes — the lock-upgrade case: two transactions both hold a shared (read) lock on the same row and both then try to upgrade to an exclusive (write) lock. Neither can upgrade until the other releases its shared lock, but neither will release since each is waiting on the other to upgrade first — a genuine deadlock with just one resource.

**Q2: Why is Conservative 2PL rarely used in production despite fully eliminating deadlock?**
Because it requires acquiring every lock a transaction will ever need upfront, before any work begins — this can force transactions to wait far longer than necessary (waiting for locks on rows they won't actually touch until much later in their logic) and requires extra scheduler bookkeeping to know the full read/write set in advance, resulting in a significant concurrency penalty that most systems find not worth the deadlock-avoidance benefit.

**Q3: Does Strong Strict 2PL fully solve cascading aborts, or just reduce them?**
It fully eliminates them for the specific mechanism described — since no lock on modified data is ever released before the modifying transaction fully commits or aborts, no other transaction can ever read that (potentially-to-be-rolled-back) uncommitted data in the first place, removing the precondition needed for a cascading abort to occur.

**Q4: In a Wait-For Graph, what exactly triggers the scheduler to remove an edge?**
An edge from T_i to T_j (meaning "T_i is waiting for T_j") is removed once T_j actually **releases the lock** T_i was waiting for — at that point, T_i is no longer blocked on T_j, so the wait-dependency it represents no longer exists.

**Q5: What's the practical difference between the Wait-Die and Wound-Wait deadlock avoidance schemes?**
Both use transaction age (timestamp) to break potential cycles, but they differ in who takes the action: in Wait-Die, a *younger* transaction requesting a lock held by an older one aborts itself ("dies"); in Wound-Wait, an *older* transaction requesting a lock held by a younger one forcibly aborts ("wounds") that younger transaction. In both schemes, an older transaction is never forced to abort by a younger one — only the specific mechanic (self-abort vs. forced-abort, and who waits) differs.

**Q6: If deadlocks can still happen under Strong Strict 2PL, why is it still preferred industry-wide over Basic 2PL?**
Because deadlocks are a well-understood, detectable-and-resolvable failure mode (via WFG + victim selection, or timeout/timestamp-based avoidance) with bounded, contained impact — typically just the deadlocked transactions get aborted and retried. Cascading aborts, by contrast, can silently ripple outward to unrelated transactions that merely happened to read uncommitted data, making the failure blast radius unpredictable and much harder to reason about or bound.

## 🔑 Key Takeaway
Say this out loud: **"Two-Phase Locking's growing-then-shrinking phase discipline guarantees serializability, but the specific choice of variant matters — Basic 2PL maximizes concurrency but risks both deadlock and cascading aborts, Conservative 2PL eliminates deadlock at a steep concurrency cost, and Strong Strict (Rigorous) 2PL — by holding every lock until commit — eliminates cascading aborts while still requiring separate deadlock detection, which is exactly why it's the industry's default choice."**
