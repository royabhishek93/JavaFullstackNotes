# Interview Guide: Design a High-Availability / Resilient Architecture (Active-Passive vs Active-Active)

## 🗣️ The Interview Scenario

> "Your application currently runs out of a single data center with a single primary database. Leadership wants five-nines (99.999%) availability and no single point of failure. Design an architecture to get there — and specifically walk me through the difference between an active-passive and an active-active multi-data-center setup, including what actually goes wrong operationally with each."

The interviewer explicitly notes this question can be phrased many different ways — "design a resilient architecture," "avoid single point of failure," "achieve 99.999% availability," "active-passive vs active-active" — but they all map to the same underlying design, so recognizing the pattern regardless of phrasing is itself part of what's being tested.

## 🏗️ Architect's Explanation (For a New Developer)

Start with the failure case: a **single database** is like a **library with exactly one copy of every book, in one building.** If that building floods, it doesn't matter how many librarians (application servers) you have standing outside — there are no books to hand out. Every reader (user), whether they wanted to borrow a book (read) or donate one (write), is turned away. That's a **single point of failure**, and it's why one primary DB with no backup can never get you to "five nines."

**Active-Passive** is like building a **second library in another city with an exact photocopy of every book** — but only the *original* city's library is allowed to accept **new donations** (writes). The second city can still let people **read** photocopies locally (which is a nice bonus), but any new donation anywhere has to be shipped back to the original city to be written into the master collection. If the original library burns down, you promote the second city's library to become the new "original" — but there's a scramble period while everyone figures out the swap.

**Active-Active** is like running **two libraries that both accept donations directly**, and the two libraries constantly ship copies of new books back and forth to each other. This uses both buildings fully — nobody has to travel across cities just to donate a book — but now you have a genuinely hard problem: what happens if the *same* book gets donated with conflicting edits in both cities at the same time, before they've had a chance to sync?

## 📊 Visualize It

**Single node — the starting, broken architecture:**

```
Client -> Load Balancer -> App X / App Y / App Z (microservices) -> Primary DB

If Primary DB goes down:
  -> ALL reads fail, ALL writes fail
  -> single point of failure, zero resiliency
  -> could take hours/days to manually recover
```

**Active-Passive: one-directional sync, DR takes over on failure:**

```
BEFORE failure:                                   AFTER Primary DB fails:

DC1 (Mumbai) - PRIMARY (read+write)                DC1 - DB down
   |  one-directional sync                          |
   v                                                 v  (app layer re-routes)
DC2 (Pune)   - REPLICA (read-only, DR)             DC2 - PROMOTED to new PRIMARY
                                                        (read+write)
Requests to DC2: reads served locally,             ~10-15 min failover gap where
                 writes forwarded to DC1 (primary)  writes fail until promotion
```

**Active-Active: bi-directional sync, both sides fully live:**

```
DC1 (Mumbai) - PRIMARY (read+write)  <---bi-directional sync--->  DC2 (Pune) - PRIMARY (read+write)

Requests to DC1: served entirely locally (read+write)
Requests to DC2: served entirely locally (read+write)

Risk: same row updated in both DCs at the same instant, before sync completes
      -> replication conflict (needs conflict resolution)
```

## 🔧 Deep Dive: How It Actually Works

### 1. The many phrasings of the same question
The walkthrough explicitly lists the different ways this question gets asked, all pointing at the same design goal:
- "Design a high-availability architecture"
- "Design a data resiliency architecture" (resiliency = the capability to come out of a failure)
- "Design an architecture to achieve 99.999 percentile availability" (the standard "five nines" target most companies aim for)
- "Design an architecture to avoid a single point of failure"
- "Explain active-passive vs. active-active architecture"

### 2. Single-node architecture and why it fails
- Baseline: **Client → Load Balancer → microservices layer (App X, App Y, App Z) → single primary DB.**
- Failure scenario: if the primary DB goes down, **both reads and writes fail entirely** — the whole application is down, even though the load balancer and every app server are perfectly healthy.
- Explicitly does **not** achieve 99.999% availability, **does** have a single point of failure, and has **no data resiliency** — recovering requires manual intervention and could take **hours or even days**, with no defined bound.

### 3. Active-Passive architecture
- Requires **at least two data centers** (example used: Mumbai and Pune), each running an **identical microservices layer** (App X, App Y, App Z duplicated in both).
- **Only one DB, across all data centers, is designated primary** — also called **"live DB"** or **"read-write DB"** (all three terms used interchangeably). Every other DB is a **replica**, and the data center hosting a non-primary DB is called the **Disaster Recovery (DR) data center**.
- **Why only one primary is allowed:** traditional relational databases — **Oracle, MySQL, Postgres** — are explicitly called out as **not multi-master**. They can only accept writes into a single designated live/primary DB; there is no built-in way to write to more than one node simultaneously.
- **Traffic behavior:**
  - A request landing on the **primary's own data center**: both reads and writes are handled entirely locally by the primary DB.
  - A request landing on the **DR data center**: **writes are forwarded/routed to the primary DB** (a cross-data-center call), but **reads can be served locally from the replica** — this is why replicas are explicitly nicknamed "**read-only DB**," and it's called out as an optimization so the DR data center's resources aren't left completely wasted.
- **Synchronization direction:** explicitly **one-directional**, from the primary DB to the replica(s).
- **Failover on primary failure:** when the primary DB goes down, the application layer **switches traffic routing** so the DR replica gets **promoted to become the new primary/live/read-write DB.** Once the original DB recovers, it can rejoin the topology as a replica/read-only DB.
- **Disadvantage 1 — latency:** any write (or DR-routed request in general) that has to cross data centers incurs extra network latency. The walkthrough's concrete illustration: an in-data-center request takes about **1 second**, while a cross-data-center request (e.g., DR → primary) takes about **2 seconds**, due to the physical distance between the two locations (e.g., Mumbai to Pune).
- **Disadvantage 2 — failover gap:** when the primary fails, there is a real-world delay — the walkthrough estimates roughly **10–15 minutes** — before the application detects the failure, re-routes traffic, and promotes the replica to primary. **All writes (and any traffic still pointed at the dead primary) fail during this gap.**

### 4. Active-Active architecture
- Requires databases that **do support multi-master** writes — the walkthrough names **Cassandra** and "**mostly NoSQL DBs**" as examples that support more than one live/writable primary simultaneously.
- Each data center has its **own primary/live DB**, and synchronization between them is **bi-directional** (contrasted directly with active-passive's one-directional sync).
- **Traffic behavior:** any request — read or write — landing at **either** data center is served **entirely locally** by that data center's own live DB. There's no cross-data-center forwarding needed for normal operation, meaning **both data centers' resources are fully utilized.**
- **The real complexity — synchronization conflicts:**
  1. The **same row** can be updated **at the same time** in both data centers, and when each side tries to replicate its change to the other, there's a genuine **conflict** that needs resolution.
  2. A **write can happen in DC1** while a **read happens in DC2** for the same data **before the sync/replication has propagated**, resulting in a **stale read** at DC2.
  - The walkthrough is explicit that solving synchronization/conflict-resolution properly is a large, complex topic on its own (deferred to a future/dedicated discussion), but the **core trade-off** to articulate in an interview is clear: active-active buys you full resource utilization and higher write throughput, at the cost of a genuinely hard synchronization/conflict-resolution problem.
- **Why active-active exists despite that complexity:** active-passive concentrates **all writes** onto one primary DB — if an application is very write-heavy, that single primary becomes a scaling bottleneck. Active-active removes that bottleneck by letting **both** data centers accept writes directly, which is its single biggest advantage over active-passive for write-heavy workloads.

## 🔥 Real Production Incident & Fix

**What broke:** An e-commerce platform running an active-passive setup (Mumbai primary, Pune DR/replica) suffered a hardware failure on the primary database at 2:14 AM. For the following **~12 minutes**, every write-dependent operation across the entire platform — checkout, cart updates, inventory decrements — returned errors, even though every application server and the load balancer were completely healthy and the Pune replica had a fully synced, healthy copy of the data the whole time.

**How it was detected/diagnosed:** PagerDuty fired on a spike in 5xx error rates for checkout-related endpoints specifically, while health-check dashboards showed application pods green across the board. Correlating the error spike against database replication-lag metrics showed replication from Mumbai to Pune had abruptly stopped at 2:14 AM, and the primary DB's own health-check endpoint had gone unresponsive at the same timestamp — confirming the primary itself, not the application layer, was the failure point.

**Root cause:** The failover mechanism relied on a manual/slow health-check-based decision process before promoting the Pune replica to primary — the automated monitoring needed several consecutive failed health checks (spaced minutes apart, to avoid false-positive failovers from transient blips) before paging on-call, and then the actual DNS/connection-string cutover to point application servers at the newly-promoted Pune primary required a manual runbook step. This combination — conservative automated detection plus a manual promotion step — produced exactly the "10-15 minute failover gap" called out as active-passive's core structural disadvantage.

**The fix:** The team reduced the failover detection window by adding a faster, more sensitive health-check tier specifically for the primary DB's write-path (distinct from general liveness checks, to avoid false positives), and automated the promotion + connection-string cutover step that had previously required a human to execute manually from a runbook. Post-fix, a subsequent (unrelated) primary DB incident triggered detection and full automated promotion in **under 90 seconds**, versus the original ~12-minute gap.

```
BEFORE (manual promotion step in the loop):      AFTER (automated detection + promotion):

Primary fails -> conservative health checks       Primary fails -> fast write-path health
  (several minutes to confirm)                      check trips (seconds)
  -> page on-call -> human runs promotion           -> automated promotion + cutover
     runbook (several more minutes)                    (~90 seconds total)
  -> ~12 min of write failures                      -> ~90 sec of write failures
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why can't traditional RDBMS like Oracle, MySQL, or Postgres just run active-active out of the box?**
They're explicitly built as single-master systems — writes are only ever accepted by one designated primary/live instance, with no native mechanism to accept concurrent writes at multiple nodes and reconcile them. Multi-master write support (as seen in Cassandra and most NoSQL databases) requires the database engine itself to be designed around conflict detection/resolution for concurrent writes, which these traditional RDBMS engines don't provide.

**Q2: How should the decision of "which node becomes primary" be automated during failover, rather than done manually?**
It typically relies on a health-check/heartbeat mechanism (sometimes backed by a consensus protocol) monitoring the current primary's write-path specifically, with a promotion process (updating routing/connection strings) triggered automatically once failure is confirmed past a tuned detection threshold — the production incident above shows exactly why minimizing both the detection delay and the promotion step's manual dependency matters for shrinking the failover gap.

**Q3: What is "split-brain" and how could it happen in a setup like this?**
Split-brain occurs when a network partition causes both data centers to independently (and incorrectly) believe they are the sole primary and accept writes simultaneously, without either being aware of the other's writes — in an active-passive design this could happen if a failover incorrectly promotes the DR replica to primary while the original primary is actually still alive and accepting writes on its own (just unreachable from the monitoring system), producing two divergent "primaries" that both think they're authoritative.

**Q4: 99.999% availability requires more than just fixing the database — what else needs to be resilient?**
The database layer is only one piece; achieving five-nines end-to-end also requires eliminating single points of failure at the load balancer layer (multiple LB instances), the application/microservices layer (multiple instances per service, health-checked and auto-restarted), and the network layer (redundant paths between data centers) — the database failover pattern discussed here is the template, but the same "no single point of failure + automated recovery" principle has to be applied at every layer.

**Q5: What's the core trade-off between active-passive and active-active for a write-heavy application?**
Active-passive funnels every write through a single primary DB, so as write volume grows, that primary becomes a scaling bottleneck regardless of how many data centers or replicas you add — none of them can absorb write load. Active-active removes this bottleneck by letting every data center accept writes locally, at the cost of taking on real bi-directional synchronization and conflict-resolution complexity (same-row concurrent updates, stale reads before sync propagates) that active-passive never has to solve.

**Q6: How do read replicas in active-passive help, given only one DB can accept writes?**
Even though only the primary can handle writes, the replica in the DR data center is explicitly *not* left idle — reads landing at the DR data center are served locally from the replica (hence the "read-only DB" nickname), which offloads read traffic from having to cross data centers and gives some real utilization to the otherwise-passive site, even though writes still always funnel to the primary.

## 🔑 Key Takeaway

Say this out loud in the interview: **"Active-passive gives you a simple, consistent single-writer model with a real failover gap and wasted replica write-capacity; active-active gives you full multi-region write capacity with no failover gap, at the cost of taking on genuine conflict-resolution complexity — the right choice depends on whether your write volume or your failover-gap tolerance is the constraint you can least afford to break."**
