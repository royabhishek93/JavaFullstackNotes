# Two-Level Ranking: Candidate Retrieval + Re-Ranking — LinkedIn Post

## Post Text (copy-paste ready)

Your best ranking model scores 1ms per item. Run it over 2M candidates and a feed takes 33 minutes to load. Here's the fix.

- Two-stage funnel: Stage 1 (candidate retrieval) is cheap and optimizes for RECALL — shrink millions down to ~300-500 using recency filters + ANN embedding search (HNSW), in 20-50ms
- Stage 2 (re-ranking) is expensive and optimizes for PRECISION — only scores the shortlist with a rich feature vector (recency, predicted engagement, precomputed author-affinity, diversity), in 50-100ms
- Total budget: ~100-180ms end-to-end, because the expensive model NEVER sees the full candidate pool
- The invisible trap: stage-1 recall silently degrading. A system can respond in 100ms while quietly serving worse recommendations if the retrieval stage drops good candidates before the precise model ever sees them
- The fix: continuously measure recall@K OFFLINE — what fraction of true top-20 items actually made it into the stage-1 shortlist — this is invisible on a normal latency dashboard

Swipe → to see the full funnel architecture and the exact latency budget breakdown per stage.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A precise ranking model over 2M candidates = 33 minutes. The 2-stage funnel that gets it under 150ms 👇

### Variant B — Long (400–600 chars)
Running your best ranking model over millions of candidates is pure arithmetic failure — even a fast model takes seconds to minutes at that scale. The fix is a two-stage funnel: a cheap, high-recall retrieval stage (recency + ANN embedding search) shrinks millions down to a few hundred candidates, then an expensive, high-precision model re-ranks just that shortlist. The trap nobody watches: stage-1 recall silently degrading is invisible on a normal latency dashboard — you need a dedicated offline recall@K metric to catch it.

---

## Best Time to Post
Thursday, 9:00–10:00 AM IST (ranking/recommendation architecture content performs well mid-week)

## Engagement Hook
"Does your ranking pipeline track recall@K separately from latency? How did you catch a silent recall regression?"
