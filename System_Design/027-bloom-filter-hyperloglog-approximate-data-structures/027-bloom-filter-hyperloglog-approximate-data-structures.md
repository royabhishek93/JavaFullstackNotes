# Bloom Filter & HyperLogLog: Approximate Data Structures
### Trading a tiny probability of being wrong for massive savings in memory and speed

---

## PART 1 — THE STUDENT CONVERSATION

### Bloom Filter — The Bouncer With a Sticky Note

Imagine you're a bouncer at an exclusive club. You have a blacklist — 10 million names of people who aren't allowed in. The problem: carrying a 10-million-name list is impossible. You can't hold the whole thing in your head, and looking up each name takes too long.

So you carry a small sticky note with 100 checkboxes instead.

When someone is added to the blacklist, your manager texts you three "codes" based on their name (three different hash functions). You check three specific boxes — say, box 14, box 37, and box 82 — for "Alice Troublemaker."

When Alice shows up at the door:
1. You calculate box 14, 37, 82 from her name.
2. You check: is box 14 checked? Yes. Box 37? Yes. Box 82? Yes.
3. You say: "Probably on the blacklist — denied."

When Bob Innocent shows up:
1. You calculate box 14, 91, 5 from his name.
2. You check: box 14? Checked. Box 91? Not checked. STOP.
3. You say: "Definitely NOT on the blacklist — come in."

**The key insight:**
- If ANY of the required boxes is unchecked → the person is **definitely not** on the blacklist. (No false negatives — you never let through someone who IS on the list.)
- If ALL required boxes are checked → the person is **probably** on the blacklist, but those boxes might have been checked for other reasons. (False positives exist — you might occasionally deny an innocent person.)

The blacklist could have 10 million names. Your sticky note has 100 boxes. You've compressed 10 million records into 100 bits. That's the power of a Bloom filter.

**The only question is: how often do you wrongly deny innocent people (false positive rate)?** That's a parameter you tune based on how many boxes you use.

---

### HyperLogLog — The Election Exit Poll

It's election day. 100 million people voted. You want to know how many distinct voters turned out (not double-counting people who voted twice, not counting no-shows).

Option A: Collect every single voter ID. Compare them all. Count unique ones.
Memory needed: 100M voter IDs × 8 bytes = 800MB. Takes hours.

Option B: Interview 10,000 random voters. Extrapolate to the full population.
Memory needed: 10,000 records. Takes minutes. Error margin: ±0.5%.

HyperLogLog is Option B, automated, for counting distinct values in a data stream.

You're streaming 1 billion user events. You want: "how many distinct users visited today?"

HyperLogLog hashes each user ID to a binary number. It tracks one statistic: the maximum number of leading zeros seen in any hash. The more distinct values you've seen, the higher this maximum tends to be (because rarer bit patterns start appearing). The formula: `2^(max_leading_zeros) × correction_constant` gives you the count estimate.

**Result:** Estimate distinct users across 1 billion events with:
- **Error rate: 0.81%** (off by at most 1 in 123)
- **Memory: 12KB** — always, whether tracking 1K or 1 trillion distinct values
- **Exact HashSet for comparison:** 1 billion users × 8 bytes = 8GB

You trade 0.81% accuracy for a 700,000x reduction in memory. For "how many distinct users?" that tradeoff is almost always worth it.

---

## PART 2 — DIAGRAMS

### Bloom Filter Mechanics

```
Bit array size: 16 bits (real implementations use millions)
Hash functions: h1, h2, h3 (deterministic, fast)

INSERTING "alice@email.com":
  h1("alice@email.com") → 3   →  set bit 3
  h2("alice@email.com") → 7   →  set bit 7
  h3("alice@email.com") → 12  →  set bit 12

Bit array:
  Index:  0  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15
  Value: [0, 0, 0, 1, 0, 0, 0, 1, 0, 0,  0,  0,  1,  0,  0,  0]

INSERTING "bob@email.com":
  h1("bob@email.com") → 1   → set bit 1
  h2("bob@email.com") → 5   → set bit 5
  h3("bob@email.com") → 12  → set bit 12 (already set)

Bit array:
  Index:  0  1  2  3  4  5  6  7  8  9  10  11  12  13  14  15
  Value: [0, 1, 0, 1, 0, 1, 0, 1, 0, 0,  0,  0,  1,  0,  0,  0]

QUERY "carol@email.com":
  h1("carol@email.com") → 3   → bit 3 SET? YES
  h2("carol@email.com") → 7   → bit 7 SET? YES
  h3("carol@email.com") → 12  → bit 12 SET? YES
  → Result: PROBABLY IN SET (false positive — carol was never inserted!)

QUERY "dave@email.com":
  h1("dave@email.com") → 2   → bit 2 SET? NO  ← STOP immediately
  → Result: DEFINITELY NOT IN SET ✓ (100% certain)

KEY PROPERTIES:
  NO FALSE NEGATIVES:   If item was inserted, query ALWAYS returns "probably yes"
  FALSE POSITIVES EXIST: Items never inserted may return "probably yes"
  NO DELETIONS:         Setting a bit is permanent (use Counting Bloom Filter to delete)
```

---

### Bloom Filter: False Positive Rate

```
False positive probability (FPP) formula:
  p = (1 - e^(-k*n/m))^k

Where:
  k = number of hash functions
  n = number of elements inserted
  m = number of bits in the array

Optimal k (minimizes FPP for given m and n):
  k_optimal = (m/n) × ln(2) ≈ 0.693 × (m/n)

Practical guide:
  n=1M elements, target FPP=1%:
    m = n × log2(1/p) / ln(2) ≈ 1M × 9.6 bits ≈ 1.2MB
    k = 7 hash functions

  n=1M elements, target FPP=0.1%:
    m ≈ 1M × 14.4 bits ≈ 1.8MB
    k = 10 hash functions

  n=5B elements (5 billion URL shortener codes), FPP=1%:
    m ≈ 5B × 9.6 bits ≈ 6GB  (vs exact set: 5B × 8 bytes = 40GB)
    Still 6-7x smaller than exact storage.
```

---

### HyperLogLog: How Counting Leading Zeros Estimates Cardinality

```
Counting distinct users in stream: [u1, u7, u3, u1, u2, u7, u4, u1, u3, u5]

For each user ID, compute hash → binary representation:

  hash(u1) = 0b10110100...  → leading zeros: 0
  hash(u7) = 0b01001010...  → leading zeros: 1
  hash(u3) = 0b00101101...  → leading zeros: 2
  hash(u2) = 0b11001001...  → leading zeros: 0
  hash(u4) = 0b00011010...  → leading zeros: 3
  hash(u5) = 0b01101001...  → leading zeros: 1

  max_leading_zeros = 3 (seen in hash(u4))

Estimate = 2^3 × correction_constant ≈ 8 × 0.72 ≈ 5.76 ≈ 6

Actual distinct count: 5 (u1, u2, u3, u4, u5, u7 = 6 distinct)
→ Estimate: 6 ✓ (exact in this tiny example)

Real HyperLogLog uses 2^14 = 16,384 "registers" (sub-streams)
and a harmonic mean across all registers to reduce variance.

MEMORY COMPARISON for 1 billion distinct user IDs:
  HashSet (exact):      1B × 8 bytes = 8 GB
  HyperLogLog:          12 KB  (regardless of cardinality)
  Error rate:           0.81%

REDIS COMMANDS:
  PFADD   daily_users "user:123"    # O(1) — add to HyperLogLog
  PFCOUNT daily_users               # O(1) — get estimated distinct count
  PFMERGE weekly_users day1 day2 day3  # merge multiple HLLs
```

---

### When to Use Which

```
EXACT COUNT needed?
  → HashSet / Redis SET (memory grows linearly with cardinality)

APPROXIMATE COUNT acceptable?
  Large cardinality (millions+) → HyperLogLog (12KB, 0.81% error)

MEMBERSHIP TEST needed?
  "Is X in this set?" with exact answer?
  → HashSet / Redis SET

  "Is X DEFINITELY NOT in this set?" (never need delete?)
  → Bloom Filter (false positives OK, false negatives not OK)
  Space: 10 bits per element at 1% FPP (vs 64 bits exact)
```

---

## PART 3 — PRODUCTION INTERNALS

### Bloom Filter in Apache Cassandra

Cassandra's storage engine (SSTables) lives on disk. Without a Bloom filter, every read for a key that doesn't exist requires scanning multiple SSTable files on disk — expensive I/O.

**How Cassandra uses Bloom filters:**
```
Each SSTable has an in-memory Bloom filter populated at compaction time.

Read request: "Get user_id = 12345"

For each SSTable on disk:
  1. Check in-memory Bloom filter for user_id 12345
  2. If DEFINITELY NOT PRESENT → skip this SSTable entirely (no disk I/O)
  3. If PROBABLY PRESENT → read from disk, check if key actually exists

Effect: 70-90% of unnecessary SSTable reads are eliminated.
False positives (BF says "maybe" but key not there) → 1 wasted disk read.
False negatives: IMPOSSIBLE — Bloom filter never skips a key that exists.
```

This is why Cassandra's Bloom filter false positive rate is configurable per table:
```
# Cassandra table option
bloom_filter_fp_chance = 0.01   # 1% FPP → larger BF, fewer false disk reads
bloom_filter_fp_chance = 0.1    # 10% FPP → smaller BF, more false disk reads
```

---

### Bloom Filter: Username / Short Code Availability Check

```java
// Redis BloomFilter (requires RedisBloom module or Redis Stack)
@Service
public class UsernameService {
    private final JedisPool jedisPool;

    // Initialize bloom filter: capacity 10M, error rate 0.001 (0.1%)
    public void initBloomFilter() {
        try (Jedis jedis = jedisPool.getResource()) {
            // BF.RESERVE key error_rate capacity
            jedis.sendCommand(Protocol.Command.valueOf("BF.RESERVE"),
                "usernames_bloom", "0.001", "10000000");
        }
    }

    // When a username is created
    public void addUsername(String username) {
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.sendCommand(Protocol.Command.valueOf("BF.ADD"),
                "usernames_bloom", username);
            // Also write to actual DB
            userRepository.save(username);
        }
    }

    // When checking availability
    public boolean isDefinitelyAvailable(String username) {
        try (Jedis jedis = jedisPool.getResource()) {
            Object result = jedis.sendCommand(
                Protocol.Command.valueOf("BF.EXISTS"),
                "usernames_bloom", username);
            long exists = (Long) result;
            // If 0: DEFINITELY not taken → offer it without DB query
            // If 1: PROBABLY taken → must verify against DB (may be false positive)
            return exists == 0;
        }
    }
}

// Decision flow:
// BF says "not exists" (0) → username is available → skip DB query → fast path
// BF says "exists" (1)    → do DB lookup → verify (may be false positive at 0.1%)
// Net result: ~99.9% of "definitely new" usernames skip the DB check entirely
```

---

### HyperLogLog: Daily Active Users in Redis

```java
@Service
public class AnalyticsService {
    private final JedisPool jedisPool;

    // Called on every user event
    public void trackUserActivity(String userId, LocalDate date) {
        String key = "dau:" + date.toString();  // e.g., "dau:2024-01-15"
        try (Jedis jedis = jedisPool.getResource()) {
            jedis.pfadd(key, userId);   // O(1), ~12KB total regardless of users
            jedis.expire(key, 90 * 24 * 3600);  // keep 90 days
        }
    }

    // Get DAU estimate
    public long getDailyActiveUsers(LocalDate date) {
        String key = "dau:" + date.toString();
        try (Jedis jedis = jedisPool.getResource()) {
            return jedis.pfcount(key);  // returns estimated distinct count, 0.81% error
        }
    }

    // Get WAU (Weekly Active Users) — merge 7 daily HLLs
    public long getWeeklyActiveUsers(LocalDate weekEnd) {
        String[] keys = new String[7];
        for (int i = 0; i < 7; i++) {
            keys[i] = "dau:" + weekEnd.minusDays(i).toString();
        }
        try (Jedis jedis = jedisPool.getResource()) {
            String destKey = "wau:" + weekEnd.toString();
            jedis.pfmerge(destKey, keys);   // merge HLLs (union, deduplicates)
            return jedis.pfcount(destKey);
        }
    }
}

// Memory comparison for 1M daily users:
//   HashSet<String>:  1M × ~50 bytes (avg user ID length) = 50MB per day
//   HyperLogLog:      12KB per day regardless
//   90-day window:    HLL = 1.1MB total vs HashSet = 4.5GB total
```

---

### False Positive Rate Tuning

```
For a URL shortener with 5 billion existing codes:

Target FPP = 1%:
  m = 5B × 9.6 bits ≈ 6GB  (bit array)
  k = 7 hash functions
  Each BF.EXISTS: 7 hash lookups, all in memory

Target FPP = 0.1%:
  m = 5B × 14.4 bits ≈ 9GB  (bit array)
  k = 10 hash functions

Tradeoff:
  Lower FPP → larger memory → fewer wasted DB lookups
  Higher FPP → smaller memory → more wasted DB lookups

For URL shortener: FPP=1% is fine.
  If BF says "code exists" (false positive): generate another code → retry.
  This happens 1% of the time → negligible overhead.
  The 99% case (BF says "definitely doesn't exist") skips DB entirely.

For spam filter: FPP must be extremely low.
  False positive = legitimate email not delivered.
  FPP = 0.001% (1 in 100,000) or lower is appropriate.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your URL shortener needs to check if a generated short code already exists before assigning it. You have 5 billion existing codes. How do you avoid a DB lookup on every generation?"

**You (architect answer):**

> "The naive approach is obvious: generate a candidate short code, query the DB to see if it exists, if it does try again. With 5 billion existing codes and millions of generations per day, that's millions of DB reads just to check existence — not for actual data retrieval.

> I'd introduce a Bloom filter in front of the existence check. A Bloom filter is a probabilistic data structure that answers 'is this element definitely not in the set?' with 100% certainty. The interesting property is the asymmetry: a Bloom filter can tell you definitively that a code doesn't exist, but it can only say 'probably exists' — not 'definitely exists.'

> For 5 billion codes at 1% false positive rate, the Bloom filter needs about 9.6 bits per element — so roughly 6GB as a bit array, held entirely in memory. At startup or warm-up, we populate the Bloom filter from the DB. For every code generation, we check the Bloom filter first. If it says 'definitely not present,' we assign the code immediately with zero DB reads. If it says 'probably present,' we do a DB lookup to verify — this happens at most 1% of the time.

> The net effect: 99% of code assignments skip the DB entirely. The remaining 1% (false positives) do a DB check, find nothing, and assign the code anyway. This is safe — false positives just cost one wasted DB query, not a correctness error. False negatives are impossible — if a code truly exists in the Bloom filter, it will always return 'probably present,' so we never accidentally double-assign a code.

> In practice I'd use the Redis BloomFilter commands — BF.ADD when a new code is created, BF.EXISTS on every generation attempt. Redis keeps the filter in memory, so each lookup is a sub-millisecond network call. I'd set the initial capacity to 10 billion (2x current, with room to grow) and error rate to 0.1% to keep false positives negligible."

---

## PART 5 — DECISION FRAMEWORK

### Bloom Filter vs HyperLogLog vs Exact Count

| Question | Answer | Structure | Memory |
|----------|--------|-----------|--------|
| "Is X in this set?" (exact) | YES/NO guaranteed | HashSet / Redis SET | O(n) — grows linearly |
| "Is X DEFINITELY NOT in this set?" | YES guaranteed, NO is probabilistic | **Bloom Filter** | O(m) — fixed at design time |
| "How many distinct values?" (exact) | Exact integer | HashSet | O(n) — grows linearly |
| "How many distinct values?" (~0.81% error OK) | Estimate | **HyperLogLog** | Always 12KB |
| "Have I seen X before?" (idempotency, dedup) | Tolerate rare false positives | **Bloom Filter** | O(m) — fixed |
| "What is the frequency of X?" | Exact or approximate | Counter Map / Count-Min Sketch | Varies |

### When Bloom Filters Are Appropriate

```
USE Bloom Filter when:
  ✓ Set is too large to hold in memory exactly
  ✓ False positives are tolerable (just cause extra work, not correctness errors)
  ✓ False negatives are NEVER acceptable (must never miss a true member)
  ✓ No deletions needed (or use Counting Bloom Filter)

Examples:
  ✓ "Has this email been delivered?" (FP: retry delivers again — annoying but OK)
  ✓ "Does this username exist?" (FP: do DB lookup — extra work, not wrong)
  ✓ "Has this URL been crawled?" (FP: re-crawl — wasted work but acceptable)
  ✓ Cassandra SSTable existence (FP: wasted disk read — acceptable)
  ✗ "What is the user's balance?" (wrong data structure — need exact answer)
  ✗ "Is this user admin?" (FP could grant unauthorized access — never use BF)

DO NOT USE Bloom Filter when:
  ✗ False positives cause security or correctness violations
  ✗ Deletions are frequent (Bloom filters can't delete — bit can't be "unset")
  ✗ You need the actual stored value, not just existence
```

### When HyperLogLog Is Appropriate

```
USE HyperLogLog when:
  ✓ You need distinct count (cardinality), not membership
  ✓ Dataset is too large to hold in exact form (millions+ distinct values)
  ✓ 0.81% error is acceptable for your use case
  ✓ You need real-time streaming count (can't pre-aggregate)

Examples:
  ✓ Daily active users, monthly active users
  ✓ Unique page views per article
  ✓ Distinct search queries per day
  ✓ Unique IPs accessing an API endpoint (rate limiting metrics)
  ✗ "How many items in shopping cart?" (small exact number — just use integer)
  ✗ "Total revenue today?" (need exact number — use sum not HLL)
  ✗ "Which specific users visited?" (HLL only counts, doesn't store identities)
```

---

## QUICK REFERENCE CARD

```java
// BLOOM FILTER — Redis BloomFilter (RedisBloom / Redis Stack)
// Initialize: BF.RESERVE key error_rate initial_capacity
jedis.sendCommand("BF.RESERVE", "short_codes", "0.001", "10000000000");

// Add element (O(1))
jedis.sendCommand("BF.ADD", "short_codes", "abc123");

// Check existence (O(1)) — returns 0=definitely absent, 1=probably present
long exists = (Long) jedis.sendCommand("BF.EXISTS", "short_codes", "abc123");
if (exists == 0) {
    // DEFINITELY not in set — fast path, no DB needed
} else {
    // Probably in set (may be false positive) — verify with DB
}

// HYPERLOGLOG — native Redis commands
jedis.pfadd("dau:2024-01-15", "user:123");     // add user to today's HLL
long dau = jedis.pfcount("dau:2024-01-15");    // get estimated distinct count
jedis.pfmerge("wau:week1", "dau:mon", "dau:tue", "dau:wed");  // merge HLLs

// FALSE POSITIVE RATE formula (Bloom Filter)
// p = (1 - e^(-k*n/m))^k
// k = optimal hash functions = (m/n) × ln(2)
// Memory for n=1M, p=1%: m = n × log2(1/p) / ln(2) ≈ 1.2 MB

// MEMORY COMPARISON
// n=1B distinct values:
//   HashSet:       ~8 GB
//   HyperLogLog:   12 KB (0.81% error)
//   Bloom filter:  ~1.2 GB for 1% FPP (vs exact: ~8 GB)
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Bloom filters and HyperLogLog let you answer "does this exist?" and "how many distinct?" at scale without exploding memory — every large-scale system encounters at least one problem that maps cleanly to one of these two structures.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **01 — Tiny URL** | Short code existence check: 5B codes × 10 bytes = 50GB as exact set. Bloom filter at 1% FPP needs ~6GB and eliminates 99% of DB lookups on generation. If BF says "absent," assign immediately. If BF says "present" (1% false positive rate), verify in DB and retry with a new code. |
| **05 — Social Media** | "Has user X already seen post Y?" for feed deduplication. With 1B users each potentially seeing thousands of posts, storing exact "seen" sets is petabytes. Bloom filter per user (sized for 10K posts, 1% FPP ≈ 12KB each) reduces feed re-query cost. False positive means a post is occasionally hidden from a user — tolerable. False negative (showing a seen post) does not occur. |
| **20 — Email System** | Two uses: (1) Spam deduplication — "Has this message-ID been processed before?" Bloom filter prevents re-delivering duplicate messages. A false positive (legitimate email treated as duplicate) means the email is not delivered — low tolerance needed, so use 0.01% FPP. (2) Daily active senders / recipients: HyperLogLog tracks distinct email addresses seen per day for analytics dashboards without storing billions of addresses. |

**Architect's one-liner for the interview:**
*"Bloom filters tell you what definitely isn't there — eliminating unnecessary lookups at scale — and HyperLogLog tells you approximately how many distinct things are there — both trading a tunable sliver of accuracy for orders-of-magnitude savings in memory."*
