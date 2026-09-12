# SimHash: Near-Duplicate Detection at Web Scale
### How to find "basically the same page" among billions, when a single changed character breaks every normal hash

---

## PART 1 — THE STUDENT CONVERSATION

Imagine you run a search engine crawler. You've just downloaded 8 billion web pages. A huge number of them are near-identical — the same news article syndicated across 40 mirror sites, the same product page with a different "Related Items" sidebar, the same blog post republished with a different ad banner. You don't want to index all 40 copies; you want to pick one canonical version and drop the rest.

Your first instinct: hash every page with MD5 or SHA-256, and drop any page whose hash you've already seen. This works great for *exact* duplicates — byte-for-byte identical pages. But it completely fails for *near*-duplicates. Why? Because cryptographic hashes are designed to have the **avalanche effect**: flip one bit of the input, and on average half the output bits flip. Change a single character in a 10,000-word article — fix a typo, update a timestamp in the footer, swap one ad slot — and the SHA-256 hash is a completely unrelated 256-bit string. There is zero similarity signal left. You can't ask "how close are these two hashes?" because closeness in hash-space has no relationship to closeness in content-space.

What you actually want is a hash function with the opposite property: **similar inputs should produce similar outputs**. That's called locality-sensitive hashing (LSH), and SimHash is the most famous instance of it, invented by Moses Charikar and famously deployed by Google for exactly this crawler-deduplication problem.

The trick is to stop hashing the *document as a single blob* and instead hash its *individual features* — words, or overlapping word-sequences called shingles ("the cat sat", "cat sat on", "sat on the") — each into its own small fixed-width hash (say 64 bits). Then, instead of picking one of those hashes to represent the document, you take a **weighted vote** across all of them, bit position by bit position. For bit position 5, look at every feature's hash: if bit 5 is a `1`, that feature votes +weight; if bit 5 is a `0`, it votes -weight (weight is usually the feature's frequency — how many times that shingle appears, i.e. its importance). Sum all the votes for bit 5 across every feature in the document. If the sum is positive, the document's final fingerprint has a `1` in bit 5; if negative (or zero), it has a `0`. Do this independently for all 64 bit positions, and you get one 64-bit fingerprint for the whole document.

Why does this produce similarity-preserving output? Because two documents that share most of their features will have nearly identical vote totals at nearly every bit position — only the few differing features can flip a handful of bits. Two completely unrelated documents share almost no features, so their vote totals at each bit position are essentially independent coin flips — on average, half the 64 bits will differ (Hamming distance ≈ 32). Near-duplicates, by contrast, typically land at Hamming distance 0–3. That's the entire signal SimHash gives you: **small Hamming distance between two 64-bit fingerprints ⇒ the source documents are probably near-duplicates**, and you never had to compare the actual text.

---

## PART 2 — THE SIMHASH ARCHITECTURE DIAGRAMS

### Fingerprint Construction: Feature Extraction → Weighted Bit Voting

```
Document: "the cat sat on the mat"

Step 1: FEATURE EXTRACTION (word shingles, here unigrams for simplicity)
  Features with frequency (weight):
    "the" → weight 2   (appears twice)
    "cat" → weight 1
    "sat" → weight 1
    "on"  → weight 1
    "mat" → weight 1

Step 2: HASH EACH FEATURE → fixed-width bit vector (production: 64-bit MurmurHash3;
         shown here as 8-bit toy hashes for a hand-traceable example)
    hash("the") = 01000001
    hash("cat") = 00111000
    hash("sat") = 01001000
    hash("on")  = 11011101
    hash("mat") = 01000010

Step 3: WEIGHTED BIT VOTE — for each of the 8 bit positions, sum weight if
         that feature's bit is 1, subtract weight if it's 0

  bit:        b7   b6   b5   b4   b3   b2   b1   b0
  "the" x2:   -2   +2   -2   -2   -2   -2   -2   +2
  "cat"  x1:  -1   -1   +1   +1   +1   -1   -1   -1
  "sat"  x1:  -1   +1   -1   -1   +1   -1   -1   -1
  "on"   x1:  +1   +1   -1   +1   +1   +1   -1   +1
  "mat"  x1:  -1   +1   -1   -1   -1   -1   +1   -1
  ─────────────────────────────────────────────────
  SUM:        -4   +4   -4   -2    0   -4   -4    0

Step 4: SIGN → BIT  (sum > 0 → 1, sum ≤ 0 → 0)
  fingerprint("the cat sat on the mat") = 0 1 0 0 0 0 0 0 = 0x40

  This single byte (64 bits in production) IS the document's identity for
  similarity purposes. The original text is gone; only the vote outcome survives.
```

### Near-Duplicate Detection at Scale: Table-Splitting (Google's Approach)

```
Problem: 8 billion pages → 8 billion 64-bit fingerprints.
Naively checking "is any existing fingerprint within Hamming distance ≤3
of this new one?" against all 8B is an O(n) scan PER new page = infeasible.
Comparing every pair is O(n²) — utterly impossible at this scale.

Google's fix (Manku, Jain, Das Sarma — "Detecting Near-Duplicates for Web
Crawling", WWW 2007): exploit the pigeonhole principle.

  64-bit fingerprint split into blocks, e.g. 6 blocks of ~11 bits:
    [ B1 ][ B2 ][ B3 ][ B4 ][ B5 ][ B6 ]

  Pigeonhole argument: if two 64-bit fingerprints differ in AT MOST 3 bits
  total, and you split into 6 blocks, then AT LEAST 3 of those 6 blocks
  must be bit-for-bit IDENTICAL between the two fingerprints (3 differing
  bits can "poison" at most 3 of the 6 blocks).

  So: build ~20 separate tables, each storing all 8B fingerprints SORTED
  by a different permutation of the 64 bits (rotating which blocks come
  first). Each table is designed so some specific combination of blocks
  sits at the front of the sort key.

  QUERY for new fingerprint F:
    For each of the ~20 tables:
      binary-search for entries sharing F's leading block-combination
      → returns a short candidate list (typically tens of entries, not billions)
    Take the union of all candidate lists (usually < 100 fingerprints)
    Compute EXACT Hamming distance only against this tiny candidate set
    Report matches with distance ≤ 3

  Result: a lookup that would be O(8 billion) becomes O(20 binary searches
  + a few hundred XOR+popcount ops) — each new page checked in low
  single-digit milliseconds against the entire historical repository.
```

### Edge Case: Bag-of-Words Blindness and Threshold Ambiguity

```
FAILURE MODE 1 — order-insensitivity (false positive risk):
  Doc X: "dog bites man" → unigram features {dog, bites, man}
  Doc Y: "man bites dog" → unigram features {dog, bites, man}   (same set!)

  Using unigram features, X and Y hash to the IDENTICAL fingerprint —
  SimHash reports Hamming distance 0 ("certain duplicate") even though
  the meaning is inverted.
  MITIGATION: use word-level SHINGLES (n-grams, e.g. n=3) instead of
  single words. "dog bites man" → {"dog bites man"} vs
  "man bites dog" → {"man bites dog"} — now the feature sets barely
  overlap, and the fingerprints diverge sharply.

FAILURE MODE 2 — threshold ambiguity near the cutoff:
  Two legitimately DIFFERENT articles that both quote the same 200-word
  press release verbatim can land at Hamming distance 2-3 (false positive
  → wrongly merged as duplicates).
  Two legitimately near-identical articles — same content, but one has
  200 extra words of unrelated boilerplate navigation/ads baked into the
  extracted text — can land at Hamming distance 6-8 (false negative →
  wrongly kept as distinct).
  MITIGATION: pre-filter boilerplate (nav bars, ads, footers) before
  feature extraction; treat SimHash as a CANDIDATE generator, not a final
  verdict — always confirm top candidates with a cheap exact-similarity
  check (e.g. shingle-set Jaccard overlap) before merging/discarding.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Worked Numeric Example: Two Similar Texts vs. One Dissimilar Text

Using the same toy 8-bit hash (`hash(word) = (sum of ASCII codes) mod 256`, shown as an 8-bit binary string — production systems use 64-bit MurmurHash3 or a 64-bit variant of SHA-1 per feature, this toy version exists purely so the arithmetic is hand-checkable):

```
Doc A: "the cat sat on the mat"   → fingerprint 01000000  (0x40)
Doc B: "the cat sat on the rug"   → fingerprint 01001000  (0x48)
       (only "mat" swapped for "rug" — one word out of six changed)

Doc C: "quantum entanglement defies classical intuition"
       → fingerprint 00100011  (0x23)
       (topically and lexically unrelated to A/B)

Hamming distance A ↔ B:
   01000000
 ⊕ 01001000
 ───────────
   00001000   → 1 bit set → Hamming distance = 1

Hamming distance A ↔ C:
   01000000
 ⊕ 00100011
 ───────────
   01100011   → 4 bits set → Hamming distance = 4

RESULT: near-duplicate pair (A,B) differs in 1/8 bits (12.5%).
        unrelated pair (A,C) differs in 4/8 bits (50%) — exactly what
        you'd expect from independent random bits.

At production 64-bit width, this ratio holds: near-duplicates cluster at
Hamming distance 0-3 (out of 64 bits, ~0-5%), while unrelated documents
average Hamming distance ~32 (50%, pure chance).
```

### Fingerprint Computation (Java)

```java
public final class SimHash {

    private static final int BITS = 64;

    public static long fingerprint(Map<String, Integer> featureWeights) {
        long[] vote = new long[BITS];

        for (Map.Entry<String, Integer> feature : featureWeights.entrySet()) {
            long featureHash = murmur3_64(feature.getKey());
            int weight = feature.getValue();
            for (int bit = 0; bit < BITS; bit++) {
                boolean isSet = ((featureHash >>> bit) & 1L) == 1L;
                vote[bit] += isSet ? weight : -weight;
            }
        }

        long fingerprint = 0L;
        for (int bit = 0; bit < BITS; bit++) {
            if (vote[bit] > 0) {
                fingerprint |= (1L << bit);
            }
        }
        return fingerprint;
    }

    public static int hammingDistance(long a, long b) {
        return Long.bitCount(a ^ b);
    }

    // Shingling: 3-word sliding window, avoids bag-of-words order blindness
    public static Map<String, Integer> shingleWeights(String text, int n) {
        String[] words = text.toLowerCase().split("\\s+");
        Map<String, Integer> weights = new HashMap<>();
        for (int i = 0; i + n <= words.length; i++) {
            String shingle = String.join(" ", Arrays.copyOfRange(words, i, i + n));
            weights.merge(shingle, 1, Integer::sum);
        }
        return weights;
    }
}
```

### Candidate Table Lookup (Pseudocode for the Permutation-Table Index)

```python
# Simplified version of Google's table-splitting scheme (k=3, 4 blocks of 16 bits)
NUM_BLOCKS = 4
BLOCK_BITS = 16          # 4 x 16 = 64
K = 3                    # max allowed Hamming distance for "near-duplicate"

# Build time: one sorted table per permutation (rotating which block leads)
tables = []
for perm in generate_permutations(NUM_BLOCKS):        # ~C(4, 2) = 6 useful perms for k=3
    permuted = [(permute_bits(fp, perm), doc_id) for fp, doc_id in all_fingerprints]
    permuted.sort()                                    # sort by leading block
    tables.append(permuted)

# Query time: new fingerprint F
def find_near_duplicates(F):
    candidates = set()
    for table, perm in zip(tables, perms):
        pf = permute_bits(F, perm)
        leading_block = pf >> (BLOCK_BITS * (NUM_BLOCKS - 1))
        # binary search for entries sharing the same leading block
        matches = binary_search_prefix(table, leading_block)
        candidates.update(doc_id for _, doc_id in matches)

    # verify: exact Hamming distance against the (small) candidate set only
    return [doc_id for doc_id in candidates
            if hamming_distance(F, fingerprint_of(doc_id)) <= K]
```

### Real-World Numbers (Google's Published Crawler Deduplication)

```
Corpus size (Manku et al., WWW 2007):     ~8 billion web page fingerprints
Fingerprint width:                         64 bits
Similarity threshold used in production:   Hamming distance ≤ 3
Table technique:                           64 bits split into 6 blocks,
                                            ~20-24 sorted permutation tables
                                            built to guarantee coverage of
                                            all "which blocks match exactly"
                                            combinations for k ≤ 3
Per-query cost:                            handful of binary searches +
                                            Hamming distance on a candidate
                                            set of ~tens to low-hundreds
                                            of fingerprints (not billions)
Memory footprint:                          64 bits x ~20 tables x 8B rows
                                            ≈ hundreds of GB, sharded across
                                            many machines, tables held in RAM
Typical shingle size in crawler dedup:      3-8 word n-grams
Typical near-duplicate threshold:           3-8% of bits differing (≈2-5
                                            bits out of 64)
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You're building a content platform where users submit blog posts, and you need to detect when someone submits a post that's a near-copy of an existing one — not identical, but heavily plagiarized with a few words changed. How would you design this at scale, say 50 million existing posts and 100K new submissions per day?"

**You (architect answer):**

> "The first thing I'd rule out is exact hashing — MD5 or SHA-256 on the raw text. Those are designed so that a single-character change produces a completely unrelated hash, which is exactly the avalanche property you want for integrity checks but exactly the wrong property for similarity detection. It would only catch byte-for-byte copies.
>
> Instead I'd compute a SimHash fingerprint for every post. I'd extract 4-5 word shingles from the normalized text — lowercased, boilerplate and markup stripped — rather than single words, specifically to avoid the bag-of-words blind spot where 'man bites dog' and 'dog bites man' would otherwise hash identically. Each shingle gets hashed to a 64-bit value with MurmurHash3, weighted by frequency, and I take the weighted majority vote per bit to get one 64-bit fingerprint per post.
>
> For the lookup problem — comparing a new submission's fingerprint against 50 million existing ones — I wouldn't do a linear scan. I'd use the table-splitting technique from Google's original crawler-dedup paper: split the 64 bits into blocks, build a handful of sorted permutation tables, and use the pigeonhole principle so that any pair within my target Hamming distance threshold (I'd start at ≤3, tune based on false-positive rate) is guaranteed to share at least one exact-matching block. That turns each query into a few binary searches plus Hamming distance checks on a small candidate set, instead of 50 million comparisons — this comfortably runs in single-digit milliseconds per submission even at 100K/day.
>
> One operational concern I'd flag up front: SimHash is a candidate generator, not a verdict. Two posts that both legitimately quote the same long press release, or one post with a lot of extra unrelated boilerplate, can land right at the threshold and produce false positives or false negatives. My mitigation is to never auto-reject on SimHash alone — any submission whose fingerprint lands within the threshold gets flagged and passed through a cheaper-than-full-text-diff but more precise second check, like Jaccard similarity over the actual shingle sets of just the small candidate list, before it's surfaced to a moderator or auto-blocked. That keeps the expensive precise comparison rare and cheap, while SimHash does the heavy lifting of shrinking 50 million candidates down to a handful."

---

## PART 5 — DECISION FRAMEWORK

### SimHash vs. Alternative Similarity Techniques

| Approach | How It Works | Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **MD5/SHA-256 (exact hash)** | Hash entire document, compare full hashes | Zero tolerance for any change | O(1) lookup | Very low | Any single-char change is invisible; no near-duplicate signal at all |
| **SimHash** | Weighted bit-vote over feature hashes → one fixed-width fingerprint; compare via Hamming distance | Fast, fixed-size, scales to billions with table-splitting | ~ms with indexing | Medium | Order-blind on unigrams; ambiguous near threshold; needs shingling to be reliable |
| **MinHash + LSH banding** | Multiple min-hash signatures estimate Jaccard similarity of shingle sets; bucket by bands for candidate generation | Directly estimates set-overlap %, tunable precision/recall via band count | ~ms with indexing | Medium-High | More signatures needed for high precision → higher storage; tuning bands/rows is fiddly |
| **Cosine similarity on TF-IDF/embedding vectors** | Represent doc as dense/sparse vector, compare via cosine or ANN index (e.g. HNSW) | Captures semantic similarity, not just lexical overlap | ms-tens of ms (ANN) | High | Needs ANN infra; expensive to compute for every doc; overkill for pure copy-detection |
| **Levenshtein / edit distance** | Character-by-character edit operations between two full texts | Exact, interpretable "how many edits" | O(n·m) per pair — too slow at scale | Low (per-pair) | Cannot be indexed; only usable as a final verification step on a tiny candidate set |

### When SimHash Is Right

```
Use SimHash when:
  ✓ You need to detect near-duplicates among millions/billions of documents
  ✓ Duplicates are lexical (near-identical wording), not just semantically similar
  ✓ You can tolerate a small false-positive/negative rate and add a verification pass
  ✓ You need a fixed-size, cheap-to-store, cheap-to-compare fingerprint (64 bits/doc)
  ✓ Classic use cases: web crawler dedup, plagiarism/duplicate-post detection,
    spam clustering, log-line dedup

Skip SimHash when:
  ✗ You need semantic similarity ("these mean the same thing" despite different
    wording) — use embeddings + ANN search instead
  ✗ Corpus is small (thousands of docs) — a direct Jaccard or edit-distance
    comparison is simpler and precise enough
  ✗ You need exact-match guarantees (e.g. content integrity checks) — use SHA-256
  ✗ Document order/structure changes materially alter meaning and unigram
    shingling would miss that — use larger n-gram shingles or a different technique

Related approximate data structures worth knowing alongside SimHash: see
027-bloom-filter-hyperloglog-approximate-data-structures.md for how Bloom filters
and HyperLogLog solve adjacent "approximate membership/cardinality" problems with
the same fixed-size-summary philosophy.
```

---

## QUICK REFERENCE CARD

```
SIMHASH ALGORITHM:
  1. Extract features (word shingles, n=3-8 recommended over unigrams)
  2. Hash each feature → fixed-width vector (64-bit MurmurHash3 in production)
  3. Per bit position: sum(+weight if bit=1, -weight if bit=0) across all features
  4. Output bit = 1 if sum > 0 else 0  →  one 64-bit fingerprint per document

SIMILARITY TEST:
  hamming_distance(fp_A, fp_B) = popcount(fp_A XOR fp_B)
  Near-duplicate heuristic: hamming_distance <= 3   (out of 64 bits)
  Unrelated documents average: hamming_distance ~= 32 (50%, random chance)

SCALING LOOKUP (avoid O(n) / O(n^2)):
  Split 64 bits into m blocks (pigeonhole: m > k guarantees >=1 exact-match
  block when true distance <= k)
  Build ~20 sorted permutation tables → binary search leading block →
  verify exact Hamming distance only on the small candidate union

JAVA:
  long fp = SimHash.fingerprint(shingleWeights(text, 4));
  int dist = SimHash.hammingDistance(fpA, fpB);
```
