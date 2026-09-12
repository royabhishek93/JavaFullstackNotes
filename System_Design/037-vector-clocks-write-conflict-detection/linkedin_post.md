# Vector Clocks & Write Conflict Detection — LinkedIn Post

## Post Text (copy-paste ready)

Your database might be silently deleting items from customers' shopping carts — because it trusts clocks that lie.

- Two nodes write concurrently: laptop adds "jacket" → clock {A:2}, phone adds "gloves" → clock {A:1,B:1}. Neither timestamp is "more correct" — they're just concurrent.
- Cassandra's default (Last Write Wins) picks a winner by timestamp and silently discards the other write. No error. No warning. Just a lost item.
- Amazon Dynamo's fix: attach a vector clock `{node: counter}` to every write, compare component-by-component, and if neither dominates → flag it as a real conflict.
- The correct resolution isn't "pick one" — it's return BOTH versions to the app and let it merge (union the cart = never lose an item).
- CRDTs (G-Counter, PN-Counter, OR-Set) go further: data structures that merge correctly with zero app-level conflict logic — used in Redis counters and Riak.

Swipe → to see: the exact vector clock math, the conflict-detection rule, and the LWW vs return-all-versions vs CRDT comparison table.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Cassandra's LWW can silently delete your cart items. Here's the vector clock math Amazon Dynamo uses to actually catch write conflicts. 🎥

### Variant B — Long (400–600 chars)
Wall clocks drift by milliseconds between datacenters — and if your system uses timestamp-based Last-Write-Wins (Cassandra's default), that drift can silently discard a legitimate write with zero errors logged. Amazon's Dynamo paper solved this with vector clocks: one counter per node, merged by taking the max on every message. If neither version's clock fully dominates the other, it's a real concurrent conflict — not a "pick the bigger timestamp" situation. The fix: return both versions to the app and merge (union your shopping cart, never drop items), or use CRDTs for auto-merging counters and sets. This is the exact mechanism behind Riak, DynamoDB version vectors, and even Git's branch-ancestry model. Full breakdown — with the shopping cart walkthrough and interview-ready one-liner — in the video.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (commute-scroll window for Indian tech professionals)

## Engagement Hook
Has your team ever hit a silent lost-write bug from LWW or clock skew in production? What was the fix — LWW, vector clocks, or CRDTs? Drop it below 👇
