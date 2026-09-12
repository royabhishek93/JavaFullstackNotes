# Posting-List Intersection & Scatter-Gather Query Execution — LinkedIn Post

## Post Text (copy-paste ready)

49 of your 50 search shards respond in <15ms. 1 is having a bad moment. Your query is now 340ms, not 15.

- Posting-list intersection: each term has a sorted list of doc IDs. "system AND design" needs the intersection — a two-pointer sorted-merge does it in O(n+m), not O(n×m)
- Skip pointers let you jump ahead in a long list (like "the," with billions of entries) instead of walking every entry — turns a 10M-entry scan into ~3,000 jumps
- At scale, the index is sharded — a coordinator SCATTERS the query to all shards, each does its own local intersection, and the coordinator GATHERS + merges the results
- The trap: response time = MAX(all shard latencies), not average. At 50-way fan-out, p99 can hit 340ms+ while p50 barely moves — some shard is ALWAYS having a bad moment
- Fix: hedged requests + replica shards — if a primary exceeds its own p95 threshold, fire the same request to a replica concurrently and take whichever responds first

Swipe → to see the exact two-pointer intersection algorithm and the p50-vs-p99 latency table across shard counts.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
49 of 50 search shards respond fast. 1 is slow. Your ENTIRE query is now as slow as the slowest shard. Here's the fix 👇

### Variant B — Long (400–600 chars)
Search engines resolve multi-term queries by intersecting sorted posting lists with a two-pointer merge — O(n+m) instead of a naive O(n×m) nested loop, with skip pointers accelerating very long lists. At scale, the index is sharded and a coordinator scatters the query to every shard, gathering local results back into a global ranking. The trap: response time is bounded by the SLOWEST shard, not the average — at wide fan-out, p99 latency diverges sharply from p50 because some shard is always mid-GC-pause or hitting a hot partition. Hedged requests to replica shards fix this.

---

## Best Time to Post
Friday, 9:00–10:00 AM IST (closes the bonus deep-dive series with strong technical save-worthy content)

## Engagement Hook
"Has tail latency from a single slow shard ever caused a search or query outage on your platform?"
