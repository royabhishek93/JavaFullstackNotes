# BM25 vs Vector Search — LinkedIn Post

## Post Text (copy-paste ready)

Our search returned ZERO results for "affordable wireless earbuds" — despite 1,000+ matching products in stock.

Why? The catalog said "Budget Bluetooth Headphones." BM25 needs exact word matches — zero overlapping words means a score of 0, no matter how relevant the product actually is.

- BM25 scores on IDF (rare terms score higher) × TF saturation (k1=1.2 stops "iPhone" mentioned 10x from being a 10x boost)
- Vector search embeds text into 768-dim space — cosine similarity of 0.94 for "affordable" vs "cheap," but only 0.12 for genuinely unrelated content
- Brute-force vector search over 10M docs takes 5-10 seconds; HNSW indexing gets that down to 1-10ms
- Hybrid search (BM25 + vector, merged via Reciprocal Rank Fusion, k=60) beats either one alone — exact matches rank first, semantic matches fill the gaps
- Vector search still fails on exact SKU lookups, error codes, and ID numbers — those need BM25 or a direct DB lookup, not embeddings

Real example: Gmail search finds "Q3 finance discussion" emails when you search "Q3 budget meeting" — that's vector search catching what pure keyword matching would miss.

Swipe → to see the BM25 formula, the HNSW architecture, and the RRF hybrid query that fixes this.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Zero search results for a term you have thousands of matches for? Your search engine doesn't understand meaning. Here's the fix. 👇

### Variant B — Long (400–600 chars)
"Affordable wireless earbuds" returned zero results — even though the catalog had 1,000+ matching products titled "Budget Bluetooth Headphones."

That's BM25 doing exactly what it's designed to do: match exact words, nothing more. Zero overlapping terms = zero score.

The fix isn't replacing BM25 — it's pairing it with vector search. Embeddings catch "budget" ≈ "affordable." HNSW makes that lookup take milliseconds instead of seconds at scale. Reciprocal Rank Fusion (k=60) merges both rankings so exact matches still win, semantics fill the rest.

Every e-commerce search, Gmail-style search, and RAG/LLM retrieval pipeline runs on this exact pattern. Full breakdown in the carousel.

---

## Best Time to Post
Tuesday, 8:30–9:30 AM IST (pre-work commute scroll for Indian tech audience)

## Engagement Hook
Have you ever debugged a "zero results" search bug that turned out to be a vocabulary mismatch, not a broken index? What was the fix?
