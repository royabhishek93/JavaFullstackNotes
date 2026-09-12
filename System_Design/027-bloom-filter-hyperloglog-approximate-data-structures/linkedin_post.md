# Bloom Filter & HyperLogLog — LinkedIn Post

## Post Text (copy-paste ready)

Counting 1 billion distinct users with 12KB of memory instead of 8GB. Here's the trick most engineers never learn.

- A Bloom filter is a bouncer with a sticky note: it can say "definitely not on the list" with 100% certainty, but "probably on the list" is all it ever promises — no false negatives, false positives are the price you pay.
- False positive rate is a knob, not luck: p = (1 - e^(-kn/m))^k. For a URL shortener with 5 billion codes at 1% FPP, that's ~6GB instead of 40GB exact storage — still a 6-7x win.
- Cassandra checks an in-memory Bloom filter before every SSTable disk read — eliminating 70-90% of unnecessary disk I/O on keys that don't exist.
- HyperLogLog doesn't store values at all — it just tracks the max leading-zeros seen across hashed inputs and estimates cardinality from that: 2^(max_zeros) × correction constant.
- Redis makes both production-ready in two commands: PFADD to track, PFCOUNT to estimate DAU at 0.81% error — 12KB flat, whether you're counting 1K or 1B users.
- Never use a Bloom filter for security checks like "is this user admin?" — a false positive there means unauthorized access, not just an extra DB query.

Swipe → to see: the bit-array walkthrough, the FPP tuning math, and the Cassandra/Redis production code.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
1B distinct users, 12KB of memory, 0.81% error — no HashSet required. Bloom filters + HyperLogLog explained with real Cassandra/Redis code.

### Variant B — Long (400–600 chars)
Your URL shortener has 5 billion codes. Checking "does this code exist?" on every generation shouldn't cost a DB read. A Bloom filter answers "definitely not" with 100% certainty using ~6GB instead of 40GB — and Cassandra uses the exact same trick to skip 70-90% of SSTable disk reads. Need distinct counts instead? HyperLogLog estimates 1 billion unique users in 12KB flat, 0.81% error, via two Redis commands: PFADD and PFCOUNT. Swipe for the math, the bit arrays, and the production code.

---

## Best Time to Post
Tuesday or Wednesday, 8–10 AM local time (developer audience checking LinkedIn before standup) — avoid Monday morning and Friday afternoon slumps.

## Engagement Hook
Close the post by asking: "What's the largest set you've had to check membership against without blowing your memory budget? Drop the number below." Replies with real scale numbers (millions/billions) drive comments and reshares from other engineers comparing notes.
