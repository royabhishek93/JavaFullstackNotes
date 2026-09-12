# SimHash: Near-Duplicate Detection at Web Scale — LinkedIn Post

## Post Text (copy-paste ready)

Change ONE character in a document and SHA-256 gives you a hash with zero relationship to the original. That's why "just hash and compare" can't find near-duplicates.

- Cryptographic hashes (MD5/SHA-256) are built for the avalanche effect — 1 bit changes in, ~half the output bits flip. Perfect for integrity checks, useless for similarity.
- SimHash flips the goal: extract word shingles, hash each one, then take a weighted majority vote per bit across all features → one 64-bit fingerprint per document.
- Near-duplicates land at Hamming distance 0–3 out of 64 bits. Unrelated docs average ~32 (pure 50% chance). That gap is the entire signal.
- Trap #1: using single words (unigrams) as features makes "dog bites man" and "man bites dog" hash IDENTICAL — same feature set, Hamming distance 0, false "certain duplicate." Fix: use 3+ word shingles.
- Trap #2: comparing 1 new fingerprint against billions is O(n) — infeasible. Google's fix (WWW 2007, Manku et al.): split 64 bits into 6 blocks, exploit the pigeonhole principle, build ~20 sorted permutation tables. 8B-row lookup → single-digit milliseconds.

Swipe → to see the fingerprint construction, the Hamming distance math, the scaling architecture, and the technique comparison table.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
SHA-256 can't find near-duplicates. Here's how Google's SimHash finds them across 8 billion pages in milliseconds. 🎥👇

### Variant B — Long (400-600 chars)
Your MD5/SHA-256 dedup logic has a blind spot: change one character and the hash becomes completely unrelated — that's the avalanche effect working exactly as designed, and exactly against you.

SimHash solves this differently: hash each word-shingle separately, take a weighted bit-vote across all of them, and compare fingerprints by Hamming distance instead of equality. Near-dupes land at distance 0–3 out of 64 bits; unrelated docs average ~32.

Google runs this across 8 billion web pages using ~20 sorted permutation tables and the pigeonhole principle — turning an O(n) scan into a few binary searches, in single-digit milliseconds.

Two traps to know before your next interview: unigram features make "dog bites man" and "man bites dog" hash identically, and results right at the Hamming threshold can go either way — always treat SimHash as a candidate generator, never a final verdict.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (commute/coffee scroll window for Indian tech audience) or 7:30–8:30 PM IST (post-work wind-down scroll).

## Engagement Hook
Have you ever shipped an exact-hash dedup that quietly let near-duplicate content slip through? What broke first — spam, plagiarism, or catalog listings? Drop it below.
