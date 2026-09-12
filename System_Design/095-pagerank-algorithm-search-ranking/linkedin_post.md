# PageRank Algorithm: Ranking Nodes in a Link Graph — LinkedIn Post

## Post Text (copy-paste ready)

1 vote from an important node can outrank 50 votes from unimportant ones. Here's the recursive math behind it.

- PageRank's core insight: importance is recursive — you're important if important nodes point to you, not just if MANY nodes point to you
- Formula: PR(A) = (1-d)/N + d × Σ[PR(Ti)/outDegree(Ti)] for every page linking to A — solved by power iteration, starting from an equal guess and converging over 50-100 rounds
- Damping factor d=0.85 models a "random surfer" who follows links 85% of the time, teleports randomly 15% of the time — this teleport probability is what GUARANTEES convergence instead of an infinite loop
- The dangling-node trap: pages with zero outbound links leak PageRank "mass" out of the system if skipped — fix by redistributing that mass uniformly across all nodes each iteration
- At web scale, the adjacency matrix is sparse (~1 non-zero entry per billion possible), so real implementations run this as a distributed MapReduce/Pregel-style computation, not a dense matrix multiply

Swipe → to see a worked 4-page example converging over 3 iterations, and the exact dangling-node fix.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
1 vote from an important node beats 50 votes from unimportant ones. Here's the recursive algorithm behind PageRank 👇

### Variant B — Long (400–600 chars)
PageRank's insight isn't "count the votes" — it's "importance is recursive." A page is important if important pages link to it, which is circular until you solve it with power iteration: guess equal scores, recompute everyone based on everyone else's current score, repeat until it converges. The damping factor (0.85) models a random surfer occasionally teleporting instead of following links — this is what guarantees convergence. The trap: dangling nodes with zero outbound links leak PageRank mass unless you explicitly redistribute it.

---

## Best Time to Post
Tuesday, 9:00–10:00 AM IST (algorithm deep-dives perform well early in the work week)

## Engagement Hook
"Where else have you seen recursive importance scoring used — fraud detection, recommendation ranking, something else?"
