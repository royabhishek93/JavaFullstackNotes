# CAP Theorem Applied — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 7 of 20

## HOOK (0:00–0:30)
"Your social feed is built AP, and during a network partition, someone's family sees their 'at the beach' post instead of their 'heading to the hospital' post — thirty seconds late. Meanwhile your payment system is built CP, and during that exact same partition, it just returns a 503 error instead of processing a transaction. Same failure, two completely different outcomes, both correct. Today I'm showing you what CAP theorem actually breaks in production — not the whiteboard theory, the real user-facing consequence."

[Screen cue: Split screen — a stale "at the beach" notification vs a clean "503 Service Unavailable" payment error.]

## THE PROBLEM (0:30–2:00)
"Think about it this way — everyone teaches CAP as theory: pick two of Consistency, Availability, Partition tolerance. But partitions always happen — cables get cut, servers hang — so partition tolerance isn't really a choice, it's mandatory. The real decision engineers make every day is: when the network partitions, do you stay available with possibly stale data, or do you refuse and stay consistent? Consistency means every read sees the latest write. Availability means every request gets SOME response, even if it's stale. And the interviewer isn't testing whether you know the definitions — they're testing whether you know which one your specific system needs."

[Screen cue: Draw the classic CP/AP axis with real systems plotted — ZooKeeper/MySQL on the CP side, Cassandra/DynamoDB on the AP side.]

## THE SOLUTION (2:00–5:00)
"Now watch what happens in two real scenarios. First, a social feed built on Cassandra, an AP system. During normal operation, User A posts, it replicates to a US replica and an EU replica. A partition isolates the EU replica. User A then posts something more urgent — the EU replica never gets it during the partition. A user in the EU reads the feed, hits the isolated replica, and sees the OLD post, not the new one. That's a stale read. For a social feed, this is completely fine — a few seconds or even minutes of staleness barely registers to a user scrolling their timeline. Second scenario: a payment system built as CP. Same partition. A user tries to pay for an order, the request hits an isolated replica that can't confirm it has the latest account balance. Instead of guessing, the CP system returns an HTTP 503 — 'I refuse to answer rather than risk giving you the wrong balance.' That's availability breaking, on purpose, because a wrong balance is far worse than a temporary error."

[Screen cue: Draw the two timelines side by side — feed staleness (green, acceptable) vs payment 503 (also green, but for the opposite reason).]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)
"Here's what most engineers get wrong: they think CAP is a single choice you make once for your whole system. It's not. Different subsystems in the SAME product make different CAP choices. Product catalog: AP, because a stale price for thirty seconds is annoying but tolerable. Inventory decrement at checkout: CP, because overselling — showing 'in stock' when there are zero units left — creates a real customer service disaster. And there's a subtler trap around conflict resolution in AP systems: if two replicas both accept writes during a partition, how do you merge them when the network heals? Cassandra's default is last-write-wins based on timestamp — fine for most fields, but for something like a 'like count', last-write-wins can silently lose increments. The fix is Cassandra's counter columns, which use CRDTs — conflict-free replicated data types — that merge by SUMMING instead of overwriting, so no increment is ever lost. And the model most senior engineers actually use instead of plain CAP is PACELC: during a Partition, you choose Availability or Consistency — but Else, during completely normal operation with no partition at all, you're choosing between Latency and Consistency. That second choice is the one you're making constantly, because partitions are actually rare. If you turn on QUORUM consistency in Cassandra to get stronger guarantees, every read now waits for two out of three nodes to reply instead of just one — and that shows up immediately as a latency spike, which is a very common real interview follow-up: 'your Cassandra read latency spiked, why?' — the answer is almost always a consistency-level change."

[Screen cue: Side-by-side table — Product Catalog: AP vs Inventory: CP; then a PACELC diagram showing the Partition branch (A/C) and the Else branch (Latency/Consistency).]

## REAL WORLD (8:00–9:30)
"Think about a rate limiter protecting checkout at a Flipkart-scale platform — that's a CP choice, fail-closed during a Redis partition, because a wrong rate-limit decision that lets fraud traffic through costs real money. Think about a chat system like the one behind Swiggy's delivery-partner messaging — that's AP, messages might arrive a little late during a partition, but the app must still let you send. And think about a payment gateway like PhonePe or Paytm — during a partition, it would rather return 'transaction failed, please retry' than risk executing a payment against a stale account balance and causing a double-charge or an incorrect deduction."

[Screen cue: Three logo-style cards — "Flipkart rate limiter: CP, fail-closed", "Swiggy chat: AP, availability first", "PhonePe/Paytm: CP, correctness over uptime".]

## OUTRO + NEXT EPISODE (9:30–10:00)
"So remember: CAP isn't a design-time choice you make once — it's a description of what breaks under failure, and the skill is knowing which subsystem needs which behavior before you start drawing boxes in an interview. Subscribe for Episode 8, where we go deep on Change Data Capture with Debezium — including how to stream every single database change to Kafka without touching a single line of your application code."

[Screen cue: "NEXT: Episode 8 — Change Data Capture with Debezium" title card with subscribe animation.]
