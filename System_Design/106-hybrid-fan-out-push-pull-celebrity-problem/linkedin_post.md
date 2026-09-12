# Hybrid Fan-Out: Push vs Pull & the Celebrity Problem — LinkedIn Post

## Post Text (copy-paste ready)

A celebrity with 100M followers posts. Fanning that out the normal way takes 200 seconds — and delays everyone else's feed too.

- Fan-out-on-write's cost scales LINEARLY with follower count — fine at 12,000 followers (~50ms), catastrophic at 100M (~42+ seconds, saturating shared write infrastructure)
- The fix: classify accounts by follower count (typically 100K-1M threshold). Above it, skip fan-out entirely — the post just sits in the celebrity's own timeline, an O(1) write
- The cost moves to READ time instead, but stays cheap: a user might follow millions of OTHER people's celebrities in aggregate, but any ONE user follows only a handful of celebrities themselves — pull their latest posts directly and merge-sort with the precomputed feed
- Real numbers: 100K followers = ~42ms fan-out (borderline), 1M = ~420ms (starting to matter), 10M = ~4.2s (unacceptable) — this is why the threshold sits where it does
- Never set the threshold from someone else's blog post — validate it against your own fan-out fleet's measured p99 completion latency

Swipe → to see the exact read-time merge architecture and the real cost table across follower-count tiers.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A celebrity's post can take 200+ seconds to fan out normally — and delay everyone else's feed too. Here's the hybrid fix 👇

### Variant B — Long (400–600 chars)
Fan-out-on-write makes reads cheap by pushing every post into followers' feeds at write time — but the cost scales linearly with follower count, which breaks completely for celebrity accounts with tens of millions of followers. The fix is a hybrid: skip fan-out above a follower threshold, and instead pull the celebrity's latest posts at read time, merging them with the precomputed feed. It works because while celebrities have huge follower counts, any single user only follows a handful of celebrities — so the read-time cost stays flat and small.

---

## Best Time to Post
Wednesday, 9:00–10:00 AM IST (feed architecture deep-dives perform well mid-week)

## Engagement Hook
"Has your platform had to special-case high-follower accounts to protect feed delivery for everyone else?"
