# Capacity Estimation: Back-of-the-Envelope Math — LinkedIn Post

## Post Text (copy-paste ready)

100M users posting twice a day = 14.7 PB/year of storage. Did you do that math before picking your database?

- Average QPS ≠ Peak QPS: apply a 2-3x peak factor for daytime traffic, or your "23K QPS" system falls over the moment it actually hits 70K
- Storage math forces the real decision: 200M posts/day × 201KB = 40TB/day → raw media has no business in your primary DB, object storage + CDN become mandatory, not optional
- Read:write ratio changes everything: a social feed (100:1 to 1000:1) should optimize for caching/CDN/replicas — a payment ledger (~1:1, write-heavy at settlement) should optimize for WAL/idempotency instead
- Sanity-check every estimate against known limits: a single Postgres does ~10K read QPS, a single Redis does 50-100K ops/sec — if your number is 500 QPS, you don't need to shard yet
- The interviewer isn't grading your arithmetic — they're grading whether "100 million DAU" instantly becomes "one database or two hundred" in your head

Swipe → to see the full DAU-to-QPS-to-storage funnel, the latency numbers every engineer should memorize, and the exact traps that sink otherwise-solid system design answers.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
100M users = 14.7 PB/year. Can you do this math in 60 seconds? Here's the back-of-envelope skill every system design interview quietly tests.

### Variant B — Long (400-600 chars)
Every system design interview starts the same way: "let's say 100 million daily active users." That's not a throwaway line — it's the test. Can you turn that into peak QPS, storage/year, and cache size before you draw a single box? Skip this step and you'll either over-engineer a system that needed one database, or under-provision one that needed two hundred. This post breaks down the exact funnel — DAU → actions/day → avg QPS → peak QPS → storage → bandwidth → cache sizing — plus the read:write ratio trap that flips your entire architecture (social feed vs. payment ledger), and the single-node reference numbers (~10K DB QPS, ~50-100K Redis ops/sec) that tell you whether you're over-engineering or under-provisioning. Save it before your next interview.

---

## Best Time to Post
Tuesday or Wednesday, 8:30-9:30 AM IST (Indian tech audience scrolling before standup, high engagement window for career/interview content)

## Engagement Hook
What's the estimation mistake you've actually seen ship to production — over-engineered for scale that never came, or under-provisioned for scale that hit overnight? Drop it below.
