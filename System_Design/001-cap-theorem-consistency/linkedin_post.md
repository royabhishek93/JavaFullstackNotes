# CAP Theorem & Consistency Models — LinkedIn Post

## Post Text (copy-paste ready)

Your bank transfer and your shopping cart should NEVER use the same consistency model.

- CAP theorem says pick 2 of Consistency, Availability, Partition tolerance — but partitions aren't optional, so it's really CP vs AP
- Shopping cart → AP: a 5-second stale cart beats a 500 error and a lost sale
- Bank transfer → CP: refusing the transfer beats deducting ₹10,000 from savings and never crediting checking
- The #1 architect-interview mistake: "I'll use strong consistency everywhere" — it kills write latency, breaks on any replica outage, and is usually unnecessary
- Read-your-own-writes is the trap nobody sees coming: post a status, read your own profile from a lagging replica, and your own post looks deleted

Swipe → to see how CP vs AP maps to real systems (ZooKeeper, Cassandra, DynamoDB) and the PACELC model that matters more than CAP day-to-day.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
CAP theorem isn't a whiteboard toy — it's why your cart tolerates staleness but your bank transfer can't. Full breakdown 👇

### Variant B — Long (400–600 chars)
Every distributed system hits the same wall: the network will partition, and when it does, you must choose between staying available with possibly-stale data, or staying consistent and refusing requests. Amazon's cart picks availability — a missing item for 5 seconds beats a lost sale. A bank transfer picks consistency — an error beats losing ₹10,000 that vanishes between accounts. The mistake most engineers make: applying one consistency model everywhere instead of choosing it per feature based on what's actually worse — stale data, or no response at all.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (Indian tech audience checks LinkedIn pre-standup; Tuesday outperforms Monday backlog-catch-up scrolling)

## Engagement Hook
"What's a real production incident where your team picked the wrong side of CP vs AP? Drop it below — I'll feature the best one in a future post."
