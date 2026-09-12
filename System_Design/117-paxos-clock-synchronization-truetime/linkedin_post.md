# Paxos, Clock Synchronization, and TrueTime — LinkedIn Post

## Post Text (copy-paste ready)

Google puts atomic clocks and GPS receivers in every data center just to know what time it is. Here's why.

- Naive local timestamps break global ordering: a transaction that happens LATER can get a SMALLER timestamp than one that happened EARLIER, purely from clock drift between servers.
- TrueTime doesn't pretend clocks are perfect — it returns an uncertainty INTERVAL (earliest/latest), kept to just 1-7ms in Google data centers using GPS + atomic clocks.
- Spanner's trick: "commit-wait" — deliberately pause after committing until real time has definitely passed the commit timestamp everywhere on Earth, guaranteeing external consistency.
- Paxos (the algorithm behind Raft) has no single-leader requirement — powerful, but "dueling proposers" can livelock it forever, which is exactly why Raft forces one leader per term instead.
- No GPS budget? CockroachDB and YugabyteDB use a Hybrid Logical Clock instead — physical time + logical counter, O(1) comparison, no special hardware, looser guarantee than TrueTime.

Swipe → to see the two-phase Paxos protocol, the commit-wait timeline, and the full decision table for Raft vs Paxos vs TrueTime vs HLC.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Google runs atomic clocks in its data centers just to order database transactions correctly. Here's the algorithm behind it. 🎥👇

### Variant B — Long (400-600 chars)
No two clocks are ever perfectly in sync — so how does Google Spanner guarantee that a transaction committed in Europe is correctly ordered before one committed in the US milliseconds later? Answer: TrueTime represents time as an uncertainty interval (not a false-precision point), then "commit-wait" pauses just long enough for real time to catch up everywhere on Earth. Pair that with Paxos — the harder, leader-less ancestor of Raft — and you've got the two building blocks behind planet-scale consistency. Can't afford GPS hardware? Hybrid Logical Clocks (used by CockroachDB) get you 90% of the benefit for free. Full breakdown in the video + carousel.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (catches the pre-standup scroll for Indian tech audiences) or 8:00–9:00 PM IST (post-dinner LinkedIn browsing window).

## Engagement Hook
Would you rather pay Google's price — GPS/atomic-clock hardware and per-transaction commit-wait latency — for airtight global ordering, or accept a Hybrid Logical Clock's looser guarantee for near-zero cost? Drop your answer below.
