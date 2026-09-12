# Capacity Estimation: Back-of-the-Envelope Math for System Design Interviews
### The rough-numbers-first skill that every case study in this folder quietly assumes you already have

---

## PART 1 — THE STUDENT CONVERSATION

Imagine an architect asked to design a new office building. Before a single blueprint is drawn, they need a rough number: how many elevators does this building need? They don't run a full simulation — they do quick, defensible arithmetic: "20 floors, 50 people per floor average, peak morning rush means most of them arrive within a 20-minute window, an elevator holds 12 people and takes roughly 90 seconds per round trip at this height... that's roughly 4 elevators needed, not 1 and not 20." That number is wrong in the third decimal place and right where it matters — it tells you whether you're building a modest lobby or need a bank of elevators, and it takes five minutes, not five weeks.

This is exactly the skill interviewers are testing when they open a system design round with "let's say 100 million daily active users" — they are NOT asking for a precise number; they're asking whether you can quickly turn a vague business scale into concrete engineering decisions: do I need one database server or a sharded cluster of 200? Does this fit in a single Redis instance's memory, or do I need a distributed cache? Is the bottleneck going to be storage, bandwidth, or compute? Skipping this step is why candidates who otherwise know all the right patterns (sharding, caching, CDNs) still design something either wildly over-engineered for the actual scale, or naively under-provisioned for it — because they never converted the word "100 million users" into an actual number of requests-per-second their design has to survive.

The estimation funnel almost always follows the same shape, regardless of which system you're designing: start from a human-scale number you were given or can reasonably assume (Daily Active Users), convert it to an AVERAGE request rate (divide by seconds in a day), then apply a **peak factor** because traffic is never evenly spread across 24 hours (a 2-3x multiplier for typical daytime-skewed traffic is a common, defensible assumption), and only THEN do you have a number — peak QPS — that tells you anything useful about how many servers, shards, or cache nodes you actually need. From there, storage and bandwidth estimates follow the same "start from a per-event size, multiply by event count, sanity-check the total" discipline.

The two failure modes interviewers actually watch for: doing NO estimation at all (jumping straight to "we'll use Kafka and Cassandra" without ever establishing whether this system needs to handle 100 QPS or 100,000 QPS — a huge, decision-changing difference), and getting LOST in false precision (spending ten minutes deriving a number to three significant figures when the interview only needed you to know whether you're in the thousands, millions, or billions range). The right level of rigor is "round numbers, clearly stated assumptions, sanity-checked against a known reference point" — not a spreadsheet.

---

## PART 2 — THE ESTIMATION FUNNEL DIAGRAMS

### The Standard Funnel: DAU → QPS → Storage → Bandwidth

```
Given (or assumed): 100 million Daily Active Users (DAU)

STEP 1 — Actions per user per day (state your assumption explicitly):
  Assume each user posts 2 times/day, reads feed 20 times/day
  → writes/day = 100M × 2 = 200M
  → reads/day  = 100M × 20 = 2B

STEP 2 — Average QPS (requests per second, spread over 86,400 sec/day):
  avg write QPS = 200,000,000 / 86,400 ≈ 2,315 QPS
  avg read QPS  = 2,000,000,000 / 86,400 ≈ 23,150 QPS

STEP 3 — Peak QPS (traffic is NOT uniform across 24 hours):
  Apply a peak factor of 2-3x for typical daytime-skewed consumer traffic
  peak write QPS ≈ 2,315 × 3 ≈ 7,000 QPS
  peak read QPS  ≈ 23,150 × 3 ≈ 70,000 QPS
  → THIS number (peak QPS), not the average, is what your architecture
    must survive without falling over.

STEP 4 — Storage estimate (per-event size × event count):
  Assume each post = 1 KB of metadata + 200 KB average media
  storage/day = 200M posts × 201 KB ≈ 40.2 TB/day
  storage/year = 40.2 TB × 365 ≈ 14.7 PB/year
  → THIS number tells you: do NOT put raw media in your primary
    database — object storage (S3-style, see 050) is mandatory at
    this scale, and even the 1 KB metadata alone
    (200M × 1KB × 365 ≈ 73 TB/year) means your metadata DB needs
    sharding well before year 3.

STEP 5 — Bandwidth estimate:
  peak read bandwidth ≈ 70,000 QPS × 201 KB average response ≈ 14 GB/s
  → THIS number tells you: a CDN (052-cdn-origin-pull-vs-origin-push.md)
    in front of media is not optional at this scale — serving 14 GB/s
    of media reads directly from origin servers is not realistic.
```

### Cache Sizing: Does the "Hot Set" Fit in Memory?

```
Question: can Redis hold the "hot" working set so most reads are
cache hits instead of hitting the database?

Assume: 20% of the 100M DAU are active in any given hour = 20M users
Each user's cached session/profile data ≈ 2 KB
  hot-set size ≈ 20,000,000 × 2 KB = 40 GB
  → fits comfortably in a modestly-sized Redis Cluster (a handful of
    nodes with 8-16 GB each) — a single machine wouldn't be enough,
    but you don't need hundreds of nodes either. This ONE calculation
    directly answers "how many Redis nodes do I provision," instead
    of guessing.
```

---

## PART 3 — INTERNALS AND REAL NUMBERS

### The Cheat Sheet: Powers of Two and Latency Numbers Every Engineer Should Know

```
POWERS OF TWO (for quick storage math):
  2^10 ≈ 1 thousand (KB)     2^40 ≈ 1 trillion (TB)
  2^20 ≈ 1 million  (MB)     2^50 ≈ 1 quadrillion (PB)
  2^30 ≈ 1 billion   (GB)

LATENCY NUMBERS (order-of-magnitude, not exact — but the RATIOS matter
most: know that memory is ~100,000x faster than a cross-region network
round trip, so you instinctively know where NOT to put a hot-path call):
  L1 cache reference                 ~1 ns
  Main memory reference              ~100 ns
  SSD random read                    ~100 μs (0.1 ms)
  Round trip within same datacenter  ~0.5 ms
  Redis GET (network + lookup)       ~1 ms
  Disk seek (spinning, rare now)     ~10 ms
  Round trip cross-region (US↔EU)    ~100-150 ms
  → this is WHY you never put a synchronous cross-region call on a
    request's hot path if you can avoid it (see also 042-long-tail-
    latency-p99-percentiles.md for how these add up under fan-out)
```

### Read:Write Ratio — Why Getting This Assumption Wrong Changes Everything

```
A social feed system: reads:writes commonly assumed 100:1 to 1000:1
  → architecture should optimize aggressively for READ path (caching,
    CDN, read replicas, precomputed feeds — see 053-fan-out-write-vs-
    fan-out-read.md)

A payment/ledger system: reads:writes often closer to 1:1 or even
  write-heavy during settlement batches
  → architecture instead optimizes for WRITE correctness/durability
    (WAL, idempotency keys, strong consistency) over raw read throughput

Getting this ratio backwards is a common interview mistake: proposing
heavy caching for a system that's actually write-dominated, or
proposing complex write-optimized sharding for a system that's
actually 1000:1 read-dominated and would be far better served by
simply adding read replicas and a cache layer.
```

### Real Numbers

```
A single modern DB server (well-provisioned Postgres/MySQL instance):
  commonly handles low thousands to ~10,000+ simple read QPS with
  proper indexing and connection pooling before needing read replicas
  or sharding — useful as a sanity-check reference point: if your peak
  QPS estimate comes out to 500, you probably don't need to shard yet.

A single Redis instance: commonly handles 50,000-100,000+ simple
  GET/SET ops/sec on modest hardware — another sanity-check reference:
  if your estimate says you need 2M ops/sec, you know you need a
  cluster of many nodes, not a config tweak on one box.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Design a URL shortener for 500 million new URLs created per month, with a 100:1 read:write ratio."

**You (walking through estimation out loud):**

> "Let me get rough numbers before I design anything, so I know what I'm actually building for.
>
> 500 million URLs/month → roughly 500,000,000 / (30 × 86,400) ≈ 193 writes/second average. With a typical 2-3x peak factor for daytime traffic, call it 500-600 peak writes/second. With a 100:1 read:write ratio, that's roughly 50,000-60,000 peak reads/second.
>
> That read number is the one that actually drives my architecture: 50,000+ QPS on simple key lookups is well beyond what I'd want hitting a single database directly, so this is a clear signal that a cache layer in front of the database — Redis, keyed by short-code — is not optional, it's load-bearing. The database itself, at only ~600 writes/second, is comfortably within what a single well-indexed instance handles, so I would NOT reach for sharding on the write path at this scale; that would be over-engineering for a problem I don't actually have yet.
>
> For storage: assume each URL record is roughly 500 bytes (short code, long URL, metadata). 500M/month × 500 bytes ≈ 250 GB/month, ≈ 3 TB/year. That's a small enough number that I wouldn't shard for storage volume reasons either — a single database with room to grow handles years of this comfortably. The bottleneck here is clearly READ THROUGHPUT, not storage or write volume, and that one estimation exercise just told me exactly where to spend my design effort: caching and read-path scaling, not database sharding."

---

## PART 5 — DECISION FRAMEWORK / CHECKLIST

| Always Estimate | Formula Shape | Tells You |
|---|---|---|
| **Average QPS** | DAU × actions/user/day ÷ 86,400 | Baseline load |
| **Peak QPS** | Average QPS × peak factor (2-3x typical) | The number your system must actually survive |
| **Storage/day and /year** | events/day × avg size/event | Whether you need object storage, sharding, archival tiers |
| **Bandwidth (peak)** | peak QPS × avg response size | Whether a CDN or streaming approach is mandatory |
| **Cache hot-set size** | active-fraction × users × per-user cache size | How many cache nodes, single instance vs cluster |
| **Read:Write ratio** | given or reasonably assumed | Whether to optimize for read scaling (cache/replica/CDN) or write durability/consistency |
| **Sanity-check against known single-node limits** | compare estimate to "~10K DB QPS, ~50-100K Redis ops/sec" reference points | Whether you actually need to shard/cluster, or whether that's premature over-engineering |
