# Search Engine — Interview Script
## Design Google Search / Web Search Engine
### Speak This Word-for-Word to Your Interviewer

> **How to use this:**
> **Step 1 — Read Big Picture** (PAGE 1): burn the overview into your head.
> **Step 2 — Read Glossary** (PAGE 2): know every term before the deep-dive.
> **Step 3 — Read Component Choices** (PAGE 3): know WHY each tech was chosen.
> **Step 4 — Read the Interview Script** (PAGE 4 onward): speak each step aloud 2-3 times.

---

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> A search engine is TWO completely separate systems that share one artifact: the INDEX.
> System 1 — Offline pipeline: Crawler → Parser → Indexer → builds the inverted index.
> System 2 — Online serving: Query comes in → lookup inverted index → rank → return top-10 in < 200ms.
> Most candidates conflate these. State this separation early — it impresses interviewers immediately.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   SEARCH ENGINE — BIG PICTURE                        │
└─────────────────────────────────────────────────────────────────────┘

════════ OFFLINE PIPELINE (runs continuously) ════════

  ┌────────────┐    ┌──────────────┐    ┌─────────────────┐
  │  URL       │    │   Crawler    │    │   Parser /      │
  │ Frontier   │───▶│  (workers)   │───▶│   Processor     │
  │            │    │  fetch HTML  │    │                 │
  │ Redis ZSET │    │  robots.txt  │    │ • strip HTML    │
  │ priority=  │    │  politeness  │    │ • tokenize      │
  │ PageRank   │◀───│  extract URLs│    │ • remove stops  │
  │ + freshness│    └──────────────┘    │ • stem words    │
  └────────────┘                        │ • extract links │
                                        └────────┬────────┘
                                                 │
                                                 ▼
                                        ┌─────────────────┐
                                        │   Indexer       │
                                        │                 │
                                        │ Build inverted  │
                                        │ index segments  │
                                        │ → merge →       │
                                        │ shard by hash   │
                                        └────────┬────────┘
                                                 │
                                    ┌────────────▼────────────┐
                                    │   INDEX SHARDS          │
                                    │  (Lucene / custom)      │
                                    │                         │
                                    │ "java" → [(doc1, tf=3,  │
                                    │  pos=[5,18,42]),        │
                                    │  (doc2, tf=2, pos=[2])] │
                                    └─────────────────────────┘

════════ ONLINE SERVING (99K searches/sec) ════════

  User types "java developer"
         │
         ▼
  ┌──────────────┐   cache hit   ┌──────────────────────┐
  │ Query Cache  │──────────────▶│  Return cached result │
  │ (Redis)      │               └──────────────────────┘
  └──────┬───────┘
         │ cache miss
         ▼
  ┌──────────────┐
  │ Query Parser │  tokenize → stem → spell-correct → expand
  └──────┬───────┘
         │
         ▼  (scatter to all shards in parallel)
  ┌──────────────────────────────────────────┐
  │  Index Shards (parallel lookup)          │
  │  Each shard: lookup "java" AND "developer"│
  │  → posting list intersection             │
  │  → score each doc (BM25 × PageRank)      │
  │  → return local top-K                   │
  └──────────────┬───────────────────────────┘
                 │ gather top-K from each shard
                 ▼
  ┌──────────────────────────────────────────┐
  │  Ranker / Result Merger                  │
  │  Merge top-K results across shards       │
  │  Re-rank with: freshness, CTR, ML signals│
  │  Return top-10                           │
  └──────────────────────────────────────────┘
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design a search engine with five pieces:

1. CRAWLER (Offline):
   URL frontier as a Redis sorted set (score = priority: PageRank + freshness).
   Crawler workers pop highest-priority URLs, fetch HTML, respect robots.txt
   with per-domain crawl delay. Extract new URLs, add to frontier.
   Deduplicate via Bloom filter (URL seen?) + SimHash (near-duplicate content).

2. INDEXER (Offline):
   Parser strips HTML, tokenizes, removes stop words ('the', 'a'),
   stems words ('running' → 'run'). Builds inverted index segments in memory,
   flushes to disk. Lucene-style: sorted posting lists per term.
   Index partitioned by URL hash across N shards.

3. INVERTED INDEX (the core data structure):
   Maps: word → sorted list of (docId, TF, positions[]).
   'java' → [(doc1, tf=3, pos=[5,18]), (doc99, tf=1, pos=[44]), ...]
   Query 'java developer' = intersect posting lists for both terms.
   This is O(1) per term lookup, then merge. Never a full table scan.

4. QUERY SERVING (Online):
   Parse query → lookup each term in index shards (parallel scatter-gather)
   → BM25 score × PageRank × freshness → merge top-K from all shards
   → return top-10. Popular query cache in Redis (TTL 5min). Target: < 200ms.

5. RANKING:
   BM25 for text relevance (TF-IDF + document length normalization).
   PageRank for authority (iterative: page authority = sum of authority of linkers).
   CTR model: click-through rate on previous impressions of this result.
   ML re-ranker: BERT-based for query intent understanding (car vs animal for 'jaguar')."
```

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

## Terminology — Know These Before Reading Further

```
┌──────────────────────┬──────────────────────────────────────────────────┐
│ Term                 │ What It Means (Simply)                           │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Inverted Index       │ The core search data structure. Maps:            │
│                      │ word → list of documents containing that word.   │
│                      │ "inverted" because docs point to words normally; │
│                      │ here words point back to docs.                   │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Posting List         │ The list of (docId, TF, positions) for one term  │
│                      │ in the inverted index. "java" → its posting list.│
├──────────────────────┼──────────────────────────────────────────────────┤
│ TF (Term Frequency)  │ How many times a term appears in a document.     │
│                      │ doc with "java" 10 times = more relevant than    │
│                      │ doc with "java" once. But diminishing returns.   │
├──────────────────────┼──────────────────────────────────────────────────┤
│ IDF (Inverse Doc     │ How rare is this term across all documents?      │
│ Frequency)           │ "java" in 10M docs = common → lower weight.      │
│                      │ "heliocentric" in 100 docs = rare → higher weight│
├──────────────────────┼──────────────────────────────────────────────────┤
│ BM25                 │ Best Matching 25. The industry-standard text     │
│                      │ relevance scoring formula. Combines TF + IDF +   │
│                      │ document length normalization. Used by Elasticsearch│
│                      │ and most search engines as baseline ranking.     │
├──────────────────────┼──────────────────────────────────────────────────┤
│ PageRank             │ Iterative algorithm measuring a page's authority │
│                      │ based on who links to it. Page A's rank =        │
│                      │ sum(rank of all pages linking to A / their       │
│                      │ out-degree). More links from authoritative pages │
│                      │ = higher PageRank.                               │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Crawler              │ Bot that fetches web pages by following links.   │
│                      │ Starts with seed URLs, discovers new URLs        │
│                      │ from each fetched page's HTML links.             │
├──────────────────────┼──────────────────────────────────────────────────┤
│ URL Frontier         │ Queue of URLs to be crawled next. Priority-based:│
│                      │ high-PageRank pages crawled more often.          │
│                      │ Implemented as Redis sorted set.                 │
├──────────────────────┼──────────────────────────────────────────────────┤
│ robots.txt           │ File at domain root specifying which paths       │
│                      │ crawlers are allowed to access. Crawlers must    │
│                      │ respect this (legal/ethical requirement).        │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Stop Words           │ Common words excluded from the index:            │
│                      │ "the", "a", "is", "of", "and". Too common to be │
│                      │ useful for discriminating between documents.     │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Stemming             │ Reduce words to their root form:                 │
│                      │ "running" → "run", "developer" → "develop".     │
│                      │ Ensures "runs" matches "running" in search.     │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Scatter-Gather       │ Query sent to ALL index shards in parallel       │
│                      │ (scatter). Each shard returns its local top-K   │
│                      │ (gather). Merge results into global top-K.       │
├──────────────────────┼──────────────────────────────────────────────────┤
│ Index Shard          │ One partition of the inverted index. Full index  │
│                      │ is split across N shards by URL hash. Each shard │
│                      │ independently answers queries for its docs.      │
├──────────────────────┼──────────────────────────────────────────────────┤
│ SimHash              │ Locality-sensitive hash for near-duplicate       │
│                      │ content detection. Similar documents → similar   │
│                      │ hashes (Hamming distance < threshold = duplicate).│
├──────────────────────┼──────────────────────────────────────────────────┤
│ Positional Index     │ Enhanced inverted index that also stores word    │
│                      │ positions. Enables phrase queries: "new york"    │
│                      │ requires "york" immediately after "new".         │
├──────────────────────┼──────────────────────────────────────────────────┤
│ CTR (Click-Through   │ Fraction of times users click a result when      │
│ Rate)                │ shown it. High CTR = users find it relevant.     │
│                      │ Used as a ranking signal (past clicks guide      │
│                      │ future rankings).                                │
└──────────────────────┴──────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

## Component Choices — Why We Picked Each One

```
┌────────────────────────┬──────────────────────────────────────────────────┐
│ COMPONENT              │ WHY THIS? NOT SOMETHING ELSE?                    │
├────────────────────────┼──────────────────────────────────────────────────┤
│                        │                                                  │
│ Inverted Index         │ WHY: Lookup by keyword needs to be O(1) per term,│
│ (core data structure)  │ not a full scan. Inverted index pre-computes the  │
│                        │ mapping at index time. Query "java" → directly   │
│                        │ get list of 10M documents. Total query time:     │
│                        │ O(|posting list|) not O(N documents).            │
│                        │                                                  │
│                        │ WHY NOT SQL LIKE '%java%': Full table scan on    │
│                        │ 60 trillion documents = would take years per     │
│                        │ query. Completely infeasible. No search engine   │
│                        │ uses a relational DB for the index.              │
│                        │                                                  │
├────────────────────────┼──────────────────────────────────────────────────┤
│                        │                                                  │
│ Lucene / Segment-based │ WHY: Lucene writes index segments incrementally  │
│ Indexing               │ (each segment = sorted inverted index). New docs │
│                        │ go to new segment. Periodic background merge     │
│                        │ reduces segment count. Efficient for both write  │
│                        │ (append-only segments) and read (sorted, binary- │
│                        │ search posting lists). Elasticsearch is Lucene-  │
│                        │ based. Battle-tested for this exact problem.     │
│                        │                                                  │
│                        │ WHY NOT B-tree DB: B-trees optimize for exact-   │
│                        │ key lookup and range scans. For "give me all     │
│                        │ docs containing 'java'" → need inverted index    │
│                        │ posting list, not a B-tree row scan.             │
│                        │                                                  │
├────────────────────────┼──────────────────────────────────────────────────┤
│                        │                                                  │
│ Redis Sorted Set       │ WHY: URL frontier = priority queue. We need to   │
│ (URL Frontier)         │ ZPOPMIN (get highest-priority URL atomically)    │
│                        │ across 1000s of crawler workers. Redis ZPOPMIN  │
│                        │ is O(log N) and atomic. Multiple crawlers can    │
│                        │ call ZPOPMIN concurrently — each gets unique URL.│
│                        │                                                  │
│                        │ WHY NOT Kafka for frontier: Kafka is FIFO per   │
│                        │ partition. We need priority-based ordering       │
│                        │ (re-crawl popular pages more often). FIFO can't │
│                        │ model this. Redis sorted set is the right choice.│
│                        │                                                  │
├────────────────────────┼──────────────────────────────────────────────────┤
│                        │                                                  │
│ Scatter-Gather         │ WHY: Index is too large for one machine (100+PB).│
│ Query Serving          │ Sharding is mandatory. Each shard independently  │
│                        │ answers queries for its portion of the index.   │
│                        │ Scatter to all N shards in parallel → gather    │
│                        │ top-K from each → global merge. Parallelism     │
│                        │ is what achieves < 200ms at this scale.          │
│                        │                                                  │
│                        │ WHY NOT sequential shard search: Searching one   │
│                        │ shard at a time with 1000 shards × 10ms each =  │
│                        │ 10 seconds per query. Parallel scatter-gather   │
│                        │ = all shards simultaneously = 10ms regardless   │
│                        │ of shard count.                                 │
│                        │                                                  │
├────────────────────────┼──────────────────────────────────────────────────┤
│                        │                                                  │
│ Redis Query Cache      │ WHY: 1% of queries (e.g., "youtube", "weather") │
│                        │ represent 20-30% of all traffic (Zipf's law).   │
│                        │ Cache these at Redis: sub-ms, no index lookup.  │
│                        │ 5-minute TTL ensures freshness.                 │
│                        │                                                  │
│                        │ WHY NOT CDN for query results: Query results are │
│                        │ personalized (logged-in user), dynamic, and     │
│                        │ highly varied. CDN is for static content.       │
│                        │ Redis in-process cache is more flexible.        │
│                        │                                                  │
└────────────────────────┴──────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4+ — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design a Search Engine"

*"Great. A search engine is actually two separate systems that share one artifact — the index.
The offline pipeline crawls the web and builds an inverted index. The online serving layer uses
that index to answer queries in < 200ms. The defining challenges are: building the inverted index
at web scale (60 trillion pages), and query serving at 99,000 searches/second. Let me ask a
few scoping questions first."*

---

## STEP 1 — Requirements Gathering

```
YOU ASK:                                    INTERVIEWER SAYS:
─────────────────────────────────────────────────────────────────
"Web-scale search or domain-specific?"     → "Web-scale like Google"
"Full-text keyword search?"                → "Yes, multi-word queries"
"Phrase queries like 'new york times'?"    → "Yes"
"Ranked results — relevance-based?"        → "Yes, most relevant first"
"How fast?"                                → "< 200ms"
"How many searches per second?"            → "~100K searches/sec"
"How many pages to index?"                 → "50-100 billion pages"
─────────────────────────────────────────────────────────────────
```

```
┌──────────────────────────────────────────────────────────────────┐
│                   REQUIREMENTS SUMMARY                            │
├──────────────────────────────────────────────────────────────────┤
│  FUNCTIONAL:                                                      │
│  Crawl and index billions of web pages                           │
│  Full-text search with multi-word queries                        │
│  Phrase queries ("new york times")                               │
│  Ranked results (relevance + authority)                          │
│  [Extension]: Personalization, autocomplete, spell-correct       │
├──────────────────────────────────────────────────────────────────┤
│  NON-FUNCTIONAL:                                                  │
│  Scale:     50-100B pages indexed                                │
│  Freshness: Popular pages re-indexed within hours                │
│  Query:     < 200ms response time                                │
│  Throughput: 99,000 searches/sec (Google's actual number)        │
│  Availability: 99.99% — downtime = millions of failed searches   │
└──────────────────────────────────────────────────────────────────┘
```

*"Key insight: these two systems (indexing vs. query serving) have completely different
scaling characteristics and should be designed independently. I'll cover the offline
pipeline first, then the query serving layer."*

---

## STEP 2 — Capacity Estimation

```
SCALE:
─────────────────────────────────────────────────────────────────
Indexed pages:     60 trillion (Google's actual count)
Average page size: 20 KB text content (after stripping HTML)
Raw text storage:  60T × 20KB = 1.2 exabytes of content
Inverted index:    ~10-20% of raw text size = 100-200 PB

CRAWLER THROUGHPUT:
─────────────────────────────────────────────────────────────────
To re-crawl 60T pages in 6 months:
  60T ÷ (180 days × 86,400 sec) = 3.9M pages/sec
  Average page: 100KB HTML = 3.9M × 100KB = 390 GB/sec bandwidth
  Need: thousands of crawlers spread across multiple datacenters

QUERY SERVING:
─────────────────────────────────────────────────────────────────
Google: 8.5B searches/day = 99,000 searches/sec
Read:Write ≈ 10,000:1 (much more reading than indexing)
Each query touches multiple index shards in parallel
Target: < 200ms end-to-end

INDEX SHARDING:
─────────────────────────────────────────────────────────────────
100 PB index ÷ 1 TB per server = 100,000 servers
With 3× replication: 300,000 servers for index storage
(This is why Google has ~1M+ servers)
```

---

## STEP 3 — Core Entities

```
┌──────────────────────────────────────────────────────────────────┐
│                        CORE ENTITIES                              │
├──────────────────┬───────────────────────────────────────────────┤
│ WebPage          │ url, contentHash, title, bodyText,            │
│                  │ pageRank, crawledAt, lastModified             │
│ InvertedIndex    │ term → [(docId, TF, positions[])]             │
│                  │ (not a DB table — custom file format)         │
│ Crawl Record     │ url, lastCrawledAt, nextCrawlAt, status       │
│ QueryLog         │ query, userId, timestamp, clicked_docIds[]    │
│ Domain           │ domain, robotsTxtRules, crawlDelay, banned    │
└──────────────────┴───────────────────────────────────────────────┘

KEY: "The InvertedIndex is NOT a database table. It's a custom binary file format
(Lucene segment files) stored on disk — sorted by term, with compressed posting
lists. Querying it is binary search for the term, then sequential read of posting list."
```

---

> **► DRAW THIS on the whiteboard ◄**

## ER RELATIONSHIP DIAGRAM

```
┌────────────────────────────────────────────────────────────────────┐
│               SEARCH ENGINE — ENTITY RELATIONSHIP                   │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────┐      ┌───────────────────────────┐
│        web_pages            │      │     crawl_schedule         │
│    (MySQL/Cassandra)        │      │         (MySQL)            │
├────────────────────────────┤      ├───────────────────────────┤
│ PK doc_id      BIGINT      │      │ PK url VARCHAR (PK)       │
│    url         VARCHAR UNIQ│      │    last_crawled_at TS     │
│    title       TEXT        │      │    next_crawl_at TS       │
│    content_hash VARCHAR    │      │    crawl_frequency ENUM   │
│    page_rank   FLOAT       │      │    status ENUM            │
│    last_crawled_at TS      │      │    http_status INT        │
│    is_indexed  BOOL        │      └───────────────────────────┘
└─────────────────────────────┘
           │ 1                     ┌─────────────────────────────┐
           │ N                     │     domains                  │
┌──────────▼──────────────────┐    │       (MySQL)               │
│        outbound_links        │    ├─────────────────────────────┤
│          (MySQL)             │    │ PK domain VARCHAR          │
├─────────────────────────────┤    │    robots_txt TEXT         │
│ PK from_doc_id BIGINT       │    │    crawl_delay_sec INT     │
│ PK to_url VARCHAR           │    │    is_banned BOOL          │
│    anchor_text VARCHAR      │    │    last_robots_fetch TS    │
│    discovered_at TS         │    └─────────────────────────────┘
└─────────────────────────────┘

Inverted Index (Lucene segment files — NOT a DB table):
┌────────────────────────────────────────────────────────────┐
│  Term           → Compressed Posting List                  │
│  ─────────────────────────────────────────────────────────│
│  "java"         → [(doc1,tf=3,pos=[5,18,42]),              │
│                    (doc99,tf=1,pos=[2]), ...]              │
│  "developer"    → [(doc1,tf=2,pos=[7,33]),                 │
│                    (doc45,tf=5,pos=[1,3,8,12,44]), ...]    │
│  "spring"       → [(doc7,tf=4,pos=[2,9,18,31]), ...]      │
│                                                            │
│  Stored as: sorted binary file, one per shard              │
│  Total: ~100 PB across 100K+ shard servers                 │
└────────────────────────────────────────────────────────────┘

Redis:
┌──────────────────────────────────────────────────────────┐
│ url_frontier   ZSET score=priority(PageRank+freshness)   │
│ seen_urls      BLOOM FILTER (probabilistic dedup)        │
│ query_cache:{hash} → result list (TTL 5min)              │
└──────────────────────────────────────────────────────────┘
```

---

## STEP 4 — API Design

```
# Query API (Online — user-facing)
GET /search?q=java+developer&page=1&limit=10
  Response: {
    results: [
      { docId, url, title, snippet, pageRank, score },
      ...
    ],
    totalHits: 1500000,
    searchTimeMs: 45,
    nextPage: 2
  }

# Indexing API (Internal — for Indexer service)
POST /index
  Request: { url, title, bodyText, links[], crawledAt }
  Response: { indexed: true, docId }

# Crawl Status API (Internal — admin)
GET /crawl/status?domain=example.com
  Response: { domain, lastCrawled, nextCrawl, pageCount, blocked }

PAGINATION: Offset-based for search results (not cursor) because:
  Users skip pages (jump to page 5). offset=40, limit=10.
  Results don't change between page loads (index is stable at query time).
  Cursor-based not needed here (new results don't arrive mid-session).
```

---

> **► DRAW THIS on the whiteboard ◄**

## JSON REQUEST / RESPONSE EXAMPLES

```json
// GET /search?q=java+developer&page=1&limit=10
// Response 200 OK:
{
  "query": "java developer",
  "totalHits": 1580000,
  "searchTimeMs": 47,
  "results": [
    {
      "docId": 123456,
      "url": "https://docs.oracle.com/en/java/",
      "title": "Java SE Documentation - Oracle",
      "snippet": "...comprehensive guide for <b>Java developers</b>. Learn about collections, streams, concurrency...",
      "pageRank": 0.94,
      "score": 12.45,
      "lastCrawledAt": "2025-01-20T08:00:00Z"
    }
  ],
  "page": 1,
  "nextPage": 2,
  "spellSuggestion": null
}

// GET /search?q=jaav+developer  (misspelled)
// Response 200 OK:
{
  "query": "jaav developer",
  "spellSuggestion": "java developer",
  "results": [],
  "totalHits": 0
}
```

---

## STEP 5 — High-Level Architecture

> **► DRAW THIS on the whiteboard ◄**
> Draw TWO clearly separated boxes: "Offline Pipeline" (left) and "Online Serving" (right).
> Show the inverted index as the shared artifact between them. This separation is your key insight.

```
═══════════════ OFFLINE PIPELINE ════════════════════════════════

 ┌────────────────────────────────────────────────────────────┐
 │                   URL FRONTIER                              │
 │              Redis Sorted Set                               │
 │   score = PageRank_estimate × freshness_priority           │
 └────────────────────┬───────────────────────────────────────┘
                      │ ZPOPMIN (atomic, concurrent workers OK)
          ┌───────────┼───────────┐
          ▼           ▼           ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐
   │ Crawler  │ │ Crawler  │ │ Crawler  │  (1000s of workers)
   │ Worker 1 │ │ Worker 2 │ │ Worker N │
   └────┬─────┘ └────┬─────┘ └────┬─────┘
        │             │             │
        └─────────────┼─────────────┘
                      │ raw HTML pages
                      ▼
             ┌──────────────────┐
             │  DNS Resolver /  │
             │  HTTP Fetcher    │
             │  (respect robots │
             │   .txt, crawl    │
             │   delay)         │
             └────────┬─────────┘
                      │
                      ▼ Kafka: raw-pages topic
             ┌──────────────────┐
             │  Parser Worker   │
             │                  │
             │ • Strip HTML     │
             │ • Tokenize       │
             │ • Remove stops   │
             │ • Stem words     │
             │ • Extract links  │
             │   → add to       │
             │   URL frontier   │
             │ • Dedup:         │
             │   URL Bloom      │
             │   SimHash content│
             └────────┬─────────┘
                      │
                      ▼ Kafka: parsed-pages topic
             ┌──────────────────┐
             │  Indexer         │
             │                  │
             │ Build in-memory  │
             │ inverted index   │
             │ segment → flush  │
             │ to disk          │
             │ → background     │
             │   merge segments │
             └────────┬─────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │   INDEX SHARDS (N servers)  │
        │   each shard = Lucene index │
        │   of 1/N of all documents   │
        └─────────────────────────────┘

═══════════════ ONLINE SERVING ════════════════════════════════

  Client
    │ GET /search?q=java+developer
    ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Query Frontend (API Gateway)                            │
  │  • Auth, rate limiting                                   │
  │  • Check Redis query cache: query_cache:{hash} → HIT?   │
  └──────────────────────────┬──────────────────────────────┘
                             │ cache miss
                             ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Query Parser                                            │
  │  • Tokenize: ["java", "developer"]                       │
  │  • Stem: ["java", "develop"]                             │
  │  • Spell-correct: (if no results for original terms)     │
  │  • Expand: (synonyms, related terms — optional)          │
  └──────────────────────────┬──────────────────────────────┘
                             │
                             ▼  (SCATTER to all shards in parallel)
  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
  │ Shard 1│  │ Shard 2│  │ Shard 3│  │ Shard N│  ← All queried at once
  │        │  │        │  │        │  │        │
  │ Lookup │  │ Lookup │  │ Lookup │  │ Lookup │
  │ "java" │  │ "java" │  │ "java" │  │ "java" │
  │  AND   │  │  AND   │  │  AND   │  │  AND   │
  │"develop│  │"develop│  │"develop│  │"develop│
  │        │  │        │  │        │  │        │
  │ BM25 × │  │ BM25 × │  │ BM25 × │  │ BM25 × │
  │PageRank│  │PageRank│  │PageRank│  │PageRank│
  │→ top-K │  │→ top-K │  │→ top-K │  │→ top-K │
  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘
      └───────────┼───────────┴───────────┘
                  │ GATHER
                  ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Result Merger / Re-ranker                               │
  │  • Merge top-K from all shards → global top-K           │
  │  • Re-rank: + freshness signal + CTR signal + ML        │
  │  • Generate snippets (extract relevant sentences)        │
  │  • Cache result: SET query_cache:{hash} result EX 300   │
  │  • Return top-10 to client                              │
  └─────────────────────────────────────────────────────────┘
```

---

> **► DRAW THIS on the whiteboard ◄**

## SEQUENCE DIAGRAM — WEB CRAWL PIPELINE

```
  Scheduler    Crawler Worker    DNS/HTTP    Parser Worker    Indexer    Index Shard
      │               │              │               │            │            │
      │ ZPOPMIN       │              │               │            │            │
      │ job_frontier  │              │               │            │            │
      │──────────────▶│              │               │            │            │
      │               │ Fetch robots │               │            │            │
      │               │ .txt         │               │            │            │
      │               │─────────────▶│               │            │            │
      │               │◀─────────────│               │            │            │
      │               │  {allow/*}   │               │            │            │
      │               │              │               │            │            │
      │               │ GET url      │               │            │            │
      │               │─────────────▶│               │            │            │
      │               │◀─────────────│               │            │            │
      │               │  {HTML page} │               │            │            │
      │               │              │               │            │            │
      │               │ Check Bloom  │               │            │            │
      │               │ filter (seen?)               │            │            │
      │               │ Publish raw-pages to Kafka   │            │            │
      │               │──────────────────────────────▶            │            │
      │               │              │               │            │            │
      │               │ Extract links→ ZADD frontier │            │            │
      │               │──────────────────────────────▶            │            │
      │               │              │               │            │            │
      │               │              │ Parser consumes           │            │
      │               │              │               │ Strip HTML │            │
      │               │              │               │ Tokenize   │            │
      │               │              │               │ Stem/stops │            │
      │               │              │               │ SimHash    │            │
      │               │              │               │ dedup      │            │
      │               │              │               │───────────▶│            │
      │               │              │               │            │ ZADD to    │
      │               │              │               │            │ index seg  │
      │               │              │               │            │────────────▶
```

## SEQUENCE DIAGRAM — SEARCH QUERY SERVING

```
  Browser     API Gateway    Query Parser    Index Shard 1..N    Ranker    Redis Cache
     │               │             │                │               │           │
     │ GET /search   │             │                │               │           │
     │ ?q=java+dev   │             │                │               │           │
     │──────────────▶│             │                │               │           │
     │               │ Check cache │                │               │           │
     │               │ query_cache:{hash}           │               │           │
     │               │──────────────────────────────────────────────────────────▶
     │               │◀──────────────────────────────────────────────────────────
     │               │  CACHE HIT → return immediately              │           │
     │◀──────────────│             │                │               │           │
     │               │  OR CACHE MISS:              │               │           │
     │               │─────────────▶               │               │           │
     │               │             │ Tokenize       │               │           │
     │               │             │ Stem           │               │           │
     │               │             │ Spell-check    │               │           │
     │               │             │                │               │           │
     │               │             │ SCATTER to ALL shards (parallel)           │
     │               │             │────────────────▶               │           │
     │               │             │ (simultaneous) │               │           │
     │               │             │                │ Lookup "java" │           │
     │               │             │                │ AND "develop" │           │
     │               │             │                │ posting lists │           │
     │               │             │                │ BM25 × PageRnk           │
     │               │             │                │ → local top-K │           │
     │               │             │◀───────────────│               │           │
     │               │             │  GATHER top-K  │               │           │
     │               │             │  from all shards               │           │
     │               │             │ Merge + Re-rank│               │           │
     │               │             │────────────────────────────────▶          │
     │               │             │◀────────────────────────────────          │
     │               │             │  [global top-10]               │           │
     │               │ Cache result│                │               │           │
     │               │──────────────────────────────────────────────────────────▶
     │ {results,     │             │                │               │           │
     │  searchTimeMs │             │                │               │           │
     │  totalHits}   │             │                │               │           │
     │◀──────────────│             │                │               │           │
```

---

## STEP 6 — Deep Dive: Inverted Index Structure

> **► DRAW THIS on the whiteboard ◄**

```
┌──────────────────────────────────────────────────────────────────┐
│                    INVERTED INDEX DEEP DIVE                       │
└──────────────────────────────────────────────────────────────────┘

BASIC INVERTED INDEX:
  term       →  posting list
  ─────────────────────────────────────────────────────────────────
  "apple"    →  [doc1, doc5, doc8, doc23, doc99, ...]
  "banana"   →  [doc3, doc8, doc14, doc99, ...]
  "developer"→  [doc2, doc5, doc17, doc88, ...]
  "java"     →  [doc5, doc17, doc88, doc123, ...]

POSITIONAL INVERTED INDEX (for phrase queries):
  term       →  [(docId, TF, positions[]), ...]
  ─────────────────────────────────────────────────────────────────
  "new"      →  [(doc5, tf=2, pos=[3,14]), (doc8, tf=1, pos=[0])]
  "york"     →  [(doc5, tf=1, pos=[4]),    (doc8, tf=1, pos=[1])]
  "times"    →  [(doc5, tf=1, pos=[5])]

PHRASE QUERY "new york":
  Step 1: Intersect docIds for "new" AND "york" → {doc5, doc8}
  Step 2: For each doc, verify "york" appears at pos+1 after "new":
    doc5: "new" at 3, "york" at 4 → consecutive ✓ MATCH
    doc8: "new" at 0, "york" at 1 → consecutive ✓ MATCH
  Step 3: "new york times" → also verify "times" at pos+2 → doc5 only

BOOLEAN QUERY MERGING (AND of two terms):
  Algorithm: merge two sorted posting lists like merge-sort.
    Pointer on list A, pointer on list B.
    If A_docId == B_docId → add to results, advance both.
    If A_docId < B_docId → advance A.
    If A_docId > B_docId → advance B.
  Time: O(|A| + |B|) — linear in posting list sizes.

BM25 SCORING FORMULA:
  Score(q, d) = Σ_terms [ IDF(t) × TF_norm(t, d) ]

  IDF(t) = log((N - df + 0.5) / (df + 0.5))
    N = total documents, df = documents containing term t
    Rare terms → higher IDF (more discriminating)

  TF_norm(t, d) = (tf × (k1+1)) / (tf + k1 × (1 - b + b × dl/avgdl))
    tf = term freq in doc, dl = doc length, avgdl = avg doc length
    k1 = 1.5, b = 0.75 (standard params)
    Prevents long documents from dominating just for having more words

PAGE RANK (simplified):
  PR(A) = (1-d)/N + d × Σ_(pages B linking to A) PR(B) / OutLinks(B)
  d = damping factor (0.85) — models random surfer sometimes jumps to random page
  N = total pages
  Iterative: compute until convergence (~50-100 iterations)
  Modern Google: PageRank is one of 200+ ranking signals, not dominant alone
```

---

## STEP 7 — Crawler Deep Dive

```
URL DEDUPLICATION:
  Problem: same URL discovered from multiple pages → crawl once only.
  Solution: Redis Bloom filter (seen_urls bloom filter).
  Bloom filter: may have false positives (say "seen" when not).
  Consequence: occasionally skip a URL we haven't seen. Acceptable.
  Never false negatives: never say "not seen" when we have.
  Size: 100B URLs × 10 bits/URL = 125 GB (tiny vs. 100PB index).

POLITENESS (don't hammer one domain):
  Max 1 request / crawl_delay per domain.
  crawl_delay from robots.txt (e.g., "Crawl-delay: 10" = 10 sec between requests).
  Per-domain last-crawl timestamp in Redis.
  robots.txt fetched once on first visit to domain, cached for 24h.

CONTENT DEDUPLICATION (SimHash):
  Many pages have same content (mirrors, scrapers).
  SimHash: hash of document → 64-bit fingerprint.
  Similar documents → similar fingerprints (Hamming distance ≤ 3).
  Store all fingerprints in Redis/Cassandra → on new page, compare Hamming distance.
  If near-duplicate → skip indexing (or index as duplicate with lower priority).

FRESHNESS STRATEGY:
  Not all pages need to be re-crawled equally.
  News sites: re-crawl every 15 min (high churn).
  Wikipedia: re-crawl daily (moderate churn).
  Corporate static pages: re-crawl weekly.
  Frequency determined by: historical change rate + page popularity.
  URL frontier score = PageRank × freshness_need.
  High-PageRank + high-churn pages = highest priority.
```

---

## STEP 8 — Scalability

```
BOTTLENECK 1: INDEX SIZE (100+ PB)
─────────────────────────────────────────────────────────────────
No single machine holds the full index. Must shard.
Sharding strategy: hash(URL) mod N_shards → assign all docs for
that URL to that shard. OR: shard by URL domain (locality for
link-analysis). OR: random distribution (even load).
Each shard: 1 TB per server → 100,000 servers for 100 PB.
Replicate 3× for availability → 300,000 servers.
Query scatter-gather: all shards queried in parallel (not sequential).

BOTTLENECK 2: QUERY CACHE EFFECTIVENESS
─────────────────────────────────────────────────────────────────
99,000 queries/sec. But 99% of queries are unique (long tail).
Top 1% of queries: 1% × 99K = 990 queries/sec, repeated often.
Cache hit rate for popular queries: 25-30%.
Result: 25K queries/sec served from Redis cache (sub-ms).
Remaining 74K/sec hit index shards.
Cache eviction: LRU + TTL 5 min (results can be stale up to 5 min — fine).

BOTTLENECK 3: HOT SHARD (POPULAR TERMS)
─────────────────────────────────────────────────────────────────
"java" appears in millions of docs → its posting list is HUGE.
One shard handles all queries involving "java" (if sharded by term).
Solution: shard by DOCUMENT (not by term). Each query → all shards.
"java" posting list is distributed across all shards.
Each shard only stores docs in its partition → no hot posting lists.
This is why document-based sharding wins over term-based sharding.

BOTTLENECK 4: INDEXING LAG (FRESHNESS)
─────────────────────────────────────────────────────────────────
New page appears → how quickly does it show in search results?
Crawl → Parse → Index → Serve: full pipeline.
For news/breaking events: expedited crawl queue (RSS feeds, 
Pub/Sub from major publishers, sitemap pings → skip frontier wait).
Target: breaking news indexed within minutes.
Normal pages: hours to days.
Google Search Console allows publishers to request immediate index.
```

---

## WHAT NOT TO SAY ✗

```
✗ "Use SQL LIKE '%java%' to search the documents"
  → Full table scan on 60 trillion documents. Each query would take
    years. No search engine uses SQL full-text scan. Inverted index
    is the ONLY approach.

✗ "Put the entire index on one server"
  → 100+ PB of index. No server has this capacity. Sharding across
    hundreds of thousands of servers is mandatory. State this early.

✗ "Crawling and query serving are the same system"
  → Completely different scale characteristics, technologies, and
    team ownership. Conflating them shows lack of systems thinking.
    Separation of these two is your first credibility signal.

✗ "Use Kafka as the URL frontier queue"
  → Kafka is FIFO per partition. URL frontier needs priority-based
    ordering (high-PageRank pages first). Redis sorted set with
    ZPOPMIN is the correct data structure for a priority queue.

✗ "Search results are always real-time fresh"
  → Real-time indexing at web scale is impossible. Index has a lag
    (minutes for news, hours/days for regular pages). Say this
    explicitly and explain freshness tiers.

✗ "PageRank alone determines result ranking"
  → PageRank is one of 200+ signals in modern search. BM25 text
    relevance + PageRank + freshness + CTR + ML (BERT) = combined
    score. PageRank alone would return authoritative pages even when
    not relevant to the query.

✗ "Ignore robots.txt"
  → Legal and ethical requirement. Crawler must check robots.txt
    before crawling any path. Also: crawl delay per domain to avoid
    DDOS-ing target sites.
```

---

## SENIOR TRAP QUESTIONS (15 YOE Level)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 1 — QUERY UNDERSTANDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "User searches 'jaguar'. They could mean the animal, the car,
   or the NFL team. How do you return the right results?"

A: This is the query intent disambiguation problem.
   Short answer: return a blended result set, weighted by predicted intent.
   Signals for intent:
   1. Session context: what did they search before? "buy" + "car" → car intent.
   2. Location: near Jacksonville FL → NFL team more likely.
   3. Query co-occurrence: historically, "jaguar" with no context clicks on
      car pages 60%, animal pages 30%, NFL 10% → weighted blend.
   4. ML query classifier: BERT-based model trained on (query, click) pairs
      → predict intent distribution.
   Modern approach: return diverse top-10 (some car, some animal, some NFL)
   for ambiguous queries. User's click teaches the system their intent → 
   personalize future results for this user.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "An index shard goes down. How does the system behave?"

A: Graceful degradation with replica failover.
   Every shard has 2-3 replicas. Query goes to primary; if primary is down,
   query router automatically routes to replica (health check via heartbeat).
   If ALL replicas for a shard are down:
   - Queries that touch this shard return partial results (missing that
     shard's documents).
   - Result page: "Some results may be missing" or silently degrade.
   - Alerting: PagerDuty fires immediately.
   Key: never return a 500 error to users for partial shard failure.
   Partial results > no results. Users rarely notice if 1/1000 shards is down.
   SLA: 99.99% of queries return complete results (requires 3 replicas for
   P(all down) = (0.001)^3 = negligible).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 2 — INDEXING CHALLENGES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "A webpage updates its content. How do you update the index
   without re-crawling the entire web?"

A: Differential indexing. When a page is re-crawled (freshness scheduler
   triggers it), the new content replaces the old.
   In Lucene: documents are immutable once written to a segment. Update =
   tombstone old docId (mark deleted in a bloom filter) + insert new docId
   with new content. Merged segments eventually garbage-collect tombstoned docs.
   Triggering re-crawl: (1) freshness priority based on historical change rate,
   (2) publisher pushes via sitemap ping (POST to indexing API), (3) RSS/Atom
   feed subscriptions for news sites. HTTP If-Modified-Since header lets crawler
   skip re-parsing if page hasn't changed since last crawl (304 Not Modified).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CATEGORY 3 — RANKING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q: "A spammy site creates 10 million links pointing to their page
   to game PageRank. How do you handle this?"

A: Link quality vs. quantity. Several defenses:
   1. TrustRank: seed a set of trusted domains (Wikipedia, NYT, .gov, .edu).
      TrustRank propagates trust outward from seeds through links. Links from
      trusted pages are worth more. Links from newly-created pages with no trust
      score contribute near-zero PageRank.
   2. Link farm detection: if 10M pages all have the same content pattern and
      link to the same target → spam cluster. ML spam classifier trained on
      known spam link farms.
   3. Nofollow attribute: links with rel="nofollow" don't pass PageRank.
      Legitimate sites use this for paid/sponsored links.
   4. Domain authority decay: links from domains registered < 30 days ago
      contribute minimal PageRank until the domain establishes history.
   Real Google: has dedicated spam teams, ML spam classifiers, and manual
   penalties (Google Search Console manual actions) for egregious cases.
```

---

## KEY NUMBERS — Memorize These

```
┌──────────────────────────────────────┬────────────────────────────┐
│              METRIC                  │  VALUE                     │
├──────────────────────────────────────┼────────────────────────────┤
│ Google indexed pages                 │ 60 trillion                │
│ Google daily searches                │ 8.5 billion                │
│ Google searches per second           │ ~99,000                    │
│ Average page size (text content)     │ ~20 KB                     │
│ Raw text storage (60T pages)         │ ~1.2 exabytes              │
│ Inverted index size                  │ ~100-200 PB                │
│ Query response time target           │ < 200ms                    │
│ Crawler speed (Google estimate)      │ ~1M pages/sec              │
│ Freshness: breaking news             │ minutes                    │
│ Freshness: regular pages             │ hours to days              │
│ Query cache hit rate                 │ 25-30%                     │
│ BM25 params (standard)               │ k1=1.5, b=0.75             │
│ PageRank damping factor              │ 0.85                       │
│ PageRank convergence iterations      │ 50-100                     │
└──────────────────────────────────────┴────────────────────────────┘
```

---

*Study order: STEP 5 Architecture + Big Picture (20 min) → STEP 6 Inverted Index (15 min)
→ STEP 7 Crawler (10 min) → STEP 8 Scalability (10 min) → Rapid Answer (5 min)*
