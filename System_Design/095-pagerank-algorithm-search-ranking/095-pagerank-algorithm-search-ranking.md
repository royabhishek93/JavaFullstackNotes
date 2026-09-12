# PageRank: Ranking Nodes in a Link Graph
### How Google decided which page on the internet actually matters, and why the same math ranks influencers, papers, and fraud rings today

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a massive university where every professor writes a recommendation letter for other professors they respect. Some professors get recommended by hundreds of colleagues; some get recommended by nobody. Now imagine one professor is recommended by only ONE other person — but that one person is the university president, who is in turn recommended by everyone. Is that professor more or less "important" than someone with fifty recommendations from random adjunct instructors nobody's heard of?

Common sense says: importance isn't just about how many recommendations you get — it's about how important the people recommending you are. That's a circular, recursive definition — you need to know the importance of your recommenders to compute your own importance, but their importance depends on THEIR recommenders, and so on. PageRank is the algorithm that solves this circularity mathematically, using something called the "power iteration method" — start with a guess, repeatedly recompute everyone's score based on everyone else's current score, and after enough rounds, the scores stabilize (converge).

In the original web context: a hyperlink from page A to page B is a "vote" from A for B. But not all votes count equally — a link from a page with high PageRank is worth more than a link from an obscure page. And a page that links to 100 other pages "dilutes" its vote across all 100 — each of those pages gets only 1/100th of that page's vote.

There's one more ingredient: the "random surfer" model. Imagine a bored person clicking links on the web forever. Most of the time they follow a link on the current page. But occasionally (with probability 1-d, where d is the "damping factor," typically 0.85) they get bored and teleport to a totally random page instead of following any link. This models real user behavior — people don't click links forever, they sometimes type a new URL or use a bookmark. Mathematically, this damping factor is also what guarantees the algorithm converges and doesn't get "trapped" forever in a loop of pages that only link to each other.

The same exact math applies far beyond web search: ranking influence in a social graph (who does the algorithm think matters, based on who follows whom), ranking papers by citation importance, or detecting money-laundering rings in a transaction graph (a node repeatedly "recommended" by other suspicious nodes gets flagged).

---

## PART 2 — THE PAGERANK ARCHITECTURE DIAGRAMS

### The Link Graph and the Iterative Formula

```
Example web graph (4 pages, arrows = hyperlinks = "votes"):

        ┌─────┐         ┌─────┐
        │  A  │ ──────► │  B  │
        └─────┘         └─────┘
          ▲  ▲             │
          │  │             │
          │  └─────────────┘
          │                │
          │                ▼
        ┌─────┐         ┌─────┐
        │  D  │ ◄────── │  C  │
        └─────┘         └─────┘
          │                ▲
          └────────────────┘

Edges:  A → B         (A links to B)
        B → C         (B links to C)
        B → D         (B links to D)
        C → A         (C links to A)
        D → A         (D links to A)
        D → C         (D links to C)

Out-degree (C(T) = number of outbound links from page T):
        C(A) = 1   (A → B)
        C(B) = 2   (B → C, B → D)
        C(C) = 1   (C → A)
        C(D) = 2   (D → A, D → C)

Formula:
    PR(A) = (1 - d)/N  +  d * Σ [ PR(Ti) / C(Ti) ]   for each Ti linking TO A

    where:
      N = total number of pages (4 in this example)
      d = damping factor (0.85 — probability of following a link
          vs 0.15 probability of "teleporting" to a random page)

  For page A specifically (pages linking to A: C and D):
    PR(A) = (1-d)/N + d * [ PR(C)/C(C) + PR(D)/C(D) ]

  For page B (pages linking to B: A):
    PR(B) = (1-d)/N + d * [ PR(A)/C(A) ]

  For page C (pages linking to C: B and D):
    PR(C) = (1-d)/N + d * [ PR(B)/C(B) + PR(D)/C(D) ]

  For page D (pages linking to D: B):
    PR(D) = (1-d)/N + d * [ PR(B)/C(B) ]
```

### Worked Numeric Example: 3 Iterations Converging

```
N = 4 pages, d = 0.85, base term (1-d)/N = 0.15/4 = 0.0375

ITERATION 0 (initial guess — uniform, PR = 1/N for everyone):
  PR(A) = 0.25   PR(B) = 0.25   PR(C) = 0.25   PR(D) = 0.25

ITERATION 1 (plug iteration-0 values into the formula):
  PR(A) = 0.0375 + 0.85*(PR(C)/1 + PR(D)/2)
        = 0.0375 + 0.85*(0.25/1 + 0.25/2)
        = 0.0375 + 0.85*(0.25 + 0.125)
        = 0.0375 + 0.85*0.375 = 0.0375 + 0.31875 = 0.35625

  PR(B) = 0.0375 + 0.85*(PR(A)/1)
        = 0.0375 + 0.85*(0.25) = 0.0375 + 0.2125 = 0.25000

  PR(C) = 0.0375 + 0.85*(PR(B)/2 + PR(D)/2)
        = 0.0375 + 0.85*(0.125 + 0.125)
        = 0.0375 + 0.85*0.25 = 0.0375 + 0.2125 = 0.25000

  PR(D) = 0.0375 + 0.85*(PR(B)/2)
        = 0.0375 + 0.85*(0.125) = 0.0375 + 0.10625 = 0.14375

  After iteration 1: A=0.356  B=0.250  C=0.250  D=0.144
  (sum ≈ 1.000 — PageRank preserves total "mass" of 1.0 across all pages)

ITERATION 2 (plug iteration-1 values in):
  PR(A) = 0.0375 + 0.85*(PR(C)/1 + PR(D)/2)
        = 0.0375 + 0.85*(0.250 + 0.0719) = 0.0375 + 0.85*0.3219 = 0.3111

  PR(B) = 0.0375 + 0.85*(PR(A)/1)
        = 0.0375 + 0.85*(0.35625) = 0.0375 + 0.3028 = 0.3403

  PR(C) = 0.0375 + 0.85*(PR(B)/2 + PR(D)/2)
        = 0.0375 + 0.85*(0.125 + 0.0719) = 0.0375 + 0.85*0.1969 = 0.2049

  PR(D) = 0.0375 + 0.85*(PR(B)/2)
        = 0.0375 + 0.85*(0.125) = 0.0375 + 0.10625 = 0.14375

  After iteration 2: A=0.311  B=0.340  C=0.205  D=0.144

ITERATION 3:
  PR(A) = 0.0375 + 0.85*(0.2049 + 0.14375/2) = 0.0375 + 0.85*0.2768 = 0.2728
  PR(B) = 0.0375 + 0.85*(0.3111) = 0.0375 + 0.2644 = 0.3019
  PR(C) = 0.0375 + 0.85*(0.3403/2 + 0.14375/2) = 0.0375 + 0.85*0.2420 = 0.2432
  PR(D) = 0.0375 + 0.85*(0.3403/2) = 0.0375 + 0.1446 = 0.1821

  After iteration 3: A=0.273  B=0.302  C=0.243  D=0.182

  Values are oscillating and converging toward a fixed point.
  Real implementations run this 50-100 iterations, checking convergence
  by the L1 or L2 change between successive iterations dropping below
  a small epsilon (e.g. 1e-6), rather than a fixed iteration count.
```

### The Dangling Node Problem

```
A "dangling node" is a page with ZERO outbound links (C(T) = 0).
Example: page E has inbound links from A and B, but links to nothing.

        A ──► E          E has no outbound links.
        B ──► E          If we just skip E in the sum, its PageRank
                           "mass" (the vote it accumulated) VANISHES
                           from the system — total PageRank leaks below
                           1.0 across iterations, which breaks the math
                           (PageRank is supposed to be a probability
                           distribution over pages, summing to 1.0).

Standard fix — treat a dangling node as if it links to ALL pages equally:
  Effectively: PR(E) gets redistributed as (1-d)/N + d * (PR(E)/N) to
  EVERY page in the graph, as though E had one outbound link to each
  of the N pages (including itself, in most formulations).

  Implementation approach (matrix form):
    danglingMass = sum(PR(T) for all T where C(T) == 0)
    every page's PR += d * danglingMass / N

  This is computed once per iteration as a single scalar correction term
  added uniformly to every page, rather than tracked per-edge — O(1)
  extra work per iteration, not O(dangling_nodes × N).
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Matrix Representation (Sparse Adjacency)

```
PageRank at scale is expressed as matrix-vector multiplication, repeated
until convergence:

    PR_(k+1) = (1-d)/N * 1  +  d * M * PR_k

  where M is the N×N "transition matrix":
    M[i][j] = 1 / C(j)   if page j links to page i
    M[i][j] = 0          otherwise

  For our 4-page example (rows = destination, cols = source):
        A     B     C     D
    A [ 0     0     1    0.5 ]
    B [ 1     0     0     0  ]
    C [ 0    0.5    0    0.5 ]
    D [ 0    0.5    0     0  ]

  PR_k is a column vector [PR(A), PR(B), PR(C), PR(D)]^T.

  M is EXTREMELY sparse at web scale: a 50-billion-page web graph has an
  average out-degree of ~10-50 links per page, so M has on the order of
  10^11-10^12 non-zero entries out of a theoretical 50B × 50B = 2.5×10^21
  possible entries — sparsity on the order of 1 in 10^9. This is why
  PageRank is implemented with sparse matrix formats (compressed sparse
  row/column), never as a dense matrix.
```

### Distributed Computation (MapReduce-style)

```python
# Pseudocode: one MapReduce iteration of PageRank over a sharded link graph.
# Input: (page_id, [outbound_links], current_pr) triples, sharded across workers.

def map_phase(page_id, outbound_links, current_pr):
    out_degree = len(outbound_links)
    if out_degree == 0:
        # Dangling node: emit its mass to a special DANGLING key, redistributed
        # uniformly to all pages in the reduce phase.
        emit("__DANGLING__", current_pr)
    else:
        contribution = current_pr / out_degree
        for target_page in outbound_links:
            emit(target_page, contribution)
    # Re-emit graph structure so the next iteration still has the adjacency list
    emit_structure(page_id, outbound_links)

def reduce_phase(page_id, contributions, dangling_mass_total, N, d):
    incoming_sum = sum(contributions)
    new_pr = (1 - d) / N + d * (incoming_sum + dangling_mass_total / N)
    return (page_id, new_pr)

# Convergence check (driver/coordinator step, after each full pass):
def has_converged(pr_before, pr_after, epsilon=1e-6):
    delta = sum(abs(pr_after[p] - pr_before[p]) for p in pr_after)
    return delta < epsilon

# Typical loop:
#   for iteration in range(max_iterations=100):
#       pr_next = run_mapreduce_pass(graph, pr_current, d=0.85)
#       if has_converged(pr_current, pr_next):
#           break
#       pr_current = pr_next
```

### Convergence Numbers and Real-World Constants

```
Damping factor d = 0.85
  - This is the value from the original 1998 Brin/Page paper.
  - Interpretation: 85% of the time, the random surfer follows an
    outbound link; 15% of the time, they jump to a uniformly random page.
  - Lower d (e.g. 0.5) converges faster but makes link topology matter
    less (more "flattened" scores). Higher d (e.g. 0.95) makes the
    algorithm more sensitive to link structure but converges slower and
    is more exploitable by link-farms (see PART 5).

Convergence:
  - Typical real web graphs converge (L1 delta < 1e-6 or similar) in
    ~50-100 iterations of power iteration.
  - Convergence rate is governed by the ratio of the second-largest to
    largest eigenvalue of the transition matrix — theoretically bounded
    by d itself (since |λ2| <= d after damping), so d=0.85 guarantees
    geometric convergence with ratio ≤ 0.85 per iteration.

Google's original 1998-era numbers (from the Brin/Page paper):
  - Graph: ~322 million links over ~24 million pages, converged in
    ~52 iterations on a single (for the time) machine in a few hours.
  - Modern web-scale graphs (tens of billions of pages) run this as a
    distributed batch job (historically MapReduce, more recently Pregel/
    Spark GraphX-style bulk-synchronous-parallel graph processing),
    with each iteration being one full pass ("superstep") over the graph.

Practical numeric example convergence: for our 4-page toy graph above,
the PR vector settles (within 1e-4) to approximately:
  A ≈ 0.286   B ≈ 0.286   C ≈ 0.238   D ≈ 0.190
after roughly 15-20 iterations of hand/spreadsheet-level precision.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design a system that ranks influencer accounts by 'importance' in a social graph, where importance should reflect not just follower count but the influence of the followers themselves. How would you compute this, and how would you make it scale?"

**You (architect answer):**

> "This is structurally the same problem PageRank solved for the web — 'importance is recursive: you're important if important nodes point to you.' I'd model the social graph as a directed graph where an edge from user X to user Y means 'X follows Y,' and treat that follow as a vote for Y's importance, weighted by X's own importance and divided by how many people X follows in total — so someone who follows 10,000 accounts dilutes each 'vote' far more than someone who selectively follows 20 accounts.
>
> Concretely, I'd run the iterative formula: `PR(Y) = (1-d)/N + d * sum(PR(X)/outDegree(X))` for every X following Y, with d around 0.85 as the damping factor — modeling that most of a user's 'attention' flows through who they follow, but with some probability they discover an account through search or a totally unrelated channel, which is what keeps every node with a nonzero minimum score and guarantees the iteration converges instead of collapsing all mass into a tightly-linked clique.
>
> At scale, I would NOT compute this as a single-machine dense matrix multiply — the adjacency matrix for even a modest social graph is astronomically sparse, so I'd represent it as a sparse edge list sharded across a distributed graph-processing framework, running PageRank as a bulk-synchronous 'superstep' computation: each superstep, every node emits its current-score-divided-by-out-degree to each of its outbound edges, a shuffle/reduce step sums incoming contributions per node, and I check the L1 delta between the score vectors of consecutive supersteps — stopping once that delta drops below something like 1e-6, which for graphs of this size typically takes on the order of 50-100 iterations.
>
> One production concern I'd flag specifically for a social graph, versus a static web graph: dangling nodes are much more common and dynamic here — a brand-new account with zero follows, or a deactivated account, is a page with no outbound edges, and if you naively skip it, PageRank 'mass' leaks out of the system every iteration and your rankings silently drift. My mitigation is to explicitly track total dangling-node mass each pass and redistribute it uniformly back across all N nodes as a flat correction term — that keeps total PageRank conserved at exactly 1.0 and the algorithm numerically stable even as the graph churns with new and deleted accounts between batch runs."

---

## PART 5 — DECISION FRAMEWORK

### PageRank vs Alternative Graph-Ranking Approaches

| Approach | How It Works | Consistency/Tradeoff | Compute Cost | Complexity | When It Fails |
|---|---|---|---|---|---|
| **PageRank (power iteration)** | Recursive vote-weighting via iterative matrix-vector multiply | Converges to a stable, global, recursive importance score | O(iterations × edges), 50-100 passes typical | Medium | Slow to reflect real-time changes (batch); vulnerable to link farms without anti-spam heuristics |
| **Simple in-degree / follower count** | Count of incoming edges only | Cheap but naive — treats every voter equally | O(edges), single pass | Low | Easily gamed by bulk-creating low-quality accounts/links that all point at one target |
| **HITS (Hubs and Authorities)** | Two interdependent scores: "hub" (good linker) and "authority" (good target) | Query-dependent variant common; more nuanced for two-sided graphs | Similar iterative cost to PageRank | Medium | Less stable than PageRank on the full web graph; more common for query-time re-ranking of a subgraph |
| **Personalized PageRank** | Same formula, but "teleport" target is a fixed seed set instead of uniform-random | Captures "importance relative to a topic/user," not global importance | Same iterative cost, run per seed-set | Medium-High | Needs a fresh computation (or approximation) per personalization seed — expensive at per-user scale |
| **Eigenvector centrality (no damping)** | Pure recursive importance, no random-teleport term | Mathematically simpler, but ill-defined/non-convergent on graphs with dangling nodes or disconnected components | Similar to PageRank minus the damping correction | Low-Medium | Diverges or is undefined without strongly-connected, aperiodic graph structure — damping exists precisely to avoid this |

### When PageRank Is the Right Choice

```
Use PageRank when:
  ✓ Importance should be recursive (voters' own importance matters,
    not just raw vote count) — search ranking, citation importance,
    social-graph influence scoring
  ✓ You can tolerate a batch/offline recomputation cadence (hours,
    not milliseconds) — it is not a real-time per-request algorithm
  ✓ The graph is large enough that naive count-based ranking is
    trivially gameable (link farms, bot followers, citation rings)
  ✓ You need a single scalar "global importance" score usable as a
    ranking feature alongside other signals (freshness, relevance, etc.)

Skip PageRank when:
  ✗ You need real-time, per-query personalized ranking — use Personalized
    PageRank with precomputed seed vectors, or a learned ranking model
    that takes precomputed PageRank as one input feature instead
  ✗ Your graph is small enough that a simple weighted in-degree captures
    "importance" well enough and the added recursive computation isn't
    worth the operational complexity
  ✗ Your ranking need is inherently query-dependent within a small
    subgraph at request time (HITS-style hub/authority scoring on a
    query-specific result set is often a better fit than global PageRank)
  ✗ The graph changes so rapidly that a 50-100 iteration batch job is
    stale before it finishes — consider incremental/approximate PageRank
    update techniques instead of full recomputation
```

---

## QUICK REFERENCE CARD

```
CORE FORMULA:
  PR(A) = (1-d)/N + d * Σ [ PR(Ti) / C(Ti) ]   for all Ti linking to A

  d = damping factor, typically 0.85
  N = total number of nodes in the graph
  C(Ti) = out-degree of node Ti (number of outbound links)

INITIALIZATION:
  PR(page) = 1/N for all pages (iteration 0)

CONVERGENCE CHECK:
  stop when  Σ |PR_k+1(p) - PR_k(p)|  <  epsilon (e.g. 1e-6)
  typical: 50-100 iterations for real web-scale graphs

DANGLING NODE FIX:
  danglingMass = Σ PR(T) for all T with C(T) == 0
  PR(p) += d * danglingMass / N     for every page p, each iteration

MATRIX FORM:
  PR_(k+1) = (1-d)/N * 1  +  d * M * PR_k
  M[i][j] = 1/C(j) if j links to i, else 0   (sparse matrix at web scale)

DISTRIBUTED COMPUTE MODEL:
  Bulk-synchronous "superstep": each node emits PR/out-degree to
  neighbors → shuffle/reduce sums per node → check convergence →
  repeat (MapReduce / Pregel / Spark GraphX style)
```
