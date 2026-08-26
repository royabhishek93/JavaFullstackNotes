# Search Engine System Design — Master Interview Guide
Complete guide: crawling, indexing, inverted index, ranking, query processing, freshness, scale, failure handling, and 15-year interview answers.

Print settings: Landscape mode, monospace font (Courier New/Consolas 9-10pt), narrow margins.

---

## BEGINNER PRIMER — READ THIS FIRST (NEW LEARNERS START HERE)

### What is a Search Engine?

A search engine lets you type words and get a ranked list of relevant results in milliseconds.
Behind that simple box is a pipeline that has already visited billions of web pages,
extracted text, built a massive index, and can answer any query against that index instantly.

### The Three Big Jobs

```text
1. CRAWLING    : Visit every webpage on the internet. Download and store the content.
2. INDEXING    : Process downloaded pages. Build a data structure that lets you find
                 "which pages contain this word" in milliseconds.
3. SERVING     : Accept a user's query, look it up in the index, rank the results,
                 and return the top 10 in under 200ms.
```

### Key Players and Components

```text
Web Crawler (Spider)  : A bot that follows links from page to page, downloading HTML.
                        Like a librarian reading every book to catalogue them.
URL Frontier          : The queue of URLs waiting to be crawled. Millions deep at any time.
HTML Parser           : Extracts clean text, links, and metadata from raw HTML.
Inverted Index        : The core data structure of a search engine.
                        Maps: word -> list of documents that contain that word.
                        Example: "java" -> [doc_1, doc_5, doc_23, ...]
                        Opposite of a book's index — instead of doc->words, it is word->docs.
Forward Index         : Maps: document -> list of words in that document.
                        Used during indexing, not query serving.
TF-IDF               : Term Frequency - Inverse Document Frequency. A score that measures
                        how important a word is in a document relative to all documents.
                        "the" appears everywhere -> low IDF -> low score.
                        "elasticsearch" is rare -> high IDF -> high score.
BM25                 : An improved ranking formula over TF-IDF. Used by Elasticsearch,
                        Solr, and most modern search engines as baseline ranking.
PageRank             : Google's original algorithm. A page is important if many important
                        pages link to it. Computed across the entire web graph.
Stemming             : Reducing a word to its root. "running" -> "run", "searches" -> "search".
                        Ensures a query for "run" also matches "running".
Stop Words           : Common words with little meaning: "the", "is", "a", "and".
                        Often removed from index to save space and reduce noise.
Query Expansion      : Automatically adding synonyms or related terms to a query.
                        Search for "automobile" -> also search for "car", "vehicle".
SimHash / MinHash    : Algorithms to detect near-duplicate pages (same content, different URL).
                        Prevents storing the same article 100 times from 100 mirror sites.
Shard                : A partition of the index. At web scale, one machine cannot hold
                        the full index. It is split across thousands of machines.
Replica              : A copy of a shard on a different machine for fault tolerance.
Re-crawl             : Visiting a previously crawled page again to pick up changes.
Delta Index          : A small, frequently-updated index of recently crawled pages.
                        Merged periodically into the large base index.
robots.txt           : A file websites publish to tell crawlers which pages NOT to crawl.
                        Crawlers must respect this to be well-behaved.
Crawl Politeness     : Not hammering a website too fast. Rate-limit requests per domain.
Spider Trap          : A website that generates infinite URLs (e.g. calendar pages going
                        back forever). Can trap a naive crawler in an infinite loop.
```

### How to Read This Guide as a New Learner

```text
1. Read this Primer fully. Know every term before moving on.
2. Section 0-1: Scope and scale targets.
3. Section 2: Architecture diagram — map every box to the glossary.
4. Section 4: Crawling deep dive — understand how pages are collected.
5. Section 5: Inverted index — the heart of search. Spend time here.
6. Section 6: Ranking — TF-IDF, BM25, PageRank explained with examples.
7. Section 7: Query flow — how your search becomes results.
8. Section 8: Schema — how data is stored.
9. Sections 9-12: Failures, tradeoffs, security, observability.
10. Sections 14-16: Interview closing answers and whiteboard summary.
```

---

## SECTION 0: HOW I START THE INTERVIEW

Interviewer: "Design a search engine like Google."

You:
"I will clarify scope first — 'search engine' can mean web search, product search, or internal document search. I will assume web-scale search unless you tell me otherwise."

"I will structure this in five steps:"
"Step 1: Lock scope and non-functional targets."
"Step 2: Draw the end-to-end architecture — crawler, indexer, query processor."
"Step 3: Deep dive the inverted index, ranking, and query understanding."
"Step 4: Cover failure handling, freshness, and scale."
"Step 5: Close with tradeoffs, observability, and 15-year answers."

---

## SECTION 1: REQUIREMENTS AND CAPACITY

### 1.1 Functional Scope

```text
[OK] Crawl the web and store page content
[OK] Parse HTML, extract text and links
[OK] Build and maintain an inverted index
[OK] Accept user queries and return ranked results
[OK] Handle spelling corrections and query expansion
[OK] Support Boolean queries (AND, OR, NOT)
[OK] Fresh results — re-crawl changed pages
[OK] Near-duplicate detection
[X]  Image/video search (descoped)
[X]  Real-time social media indexing (descoped)
[X]  Personalized search ranking (descoped for this round)
```

### 1.2 Non-Functional Targets

You:
"For a search engine, latency and freshness are the two tensions I design around."

```text
Query latency    : p99 < 200ms (end-to-end, user sees results)
Index freshness  : top pages re-crawled within 24 hours
Availability     : 99.99% for query serving
Scale            : 8 billion web pages indexed
                   50,000 queries per second (Google-scale)
Crawl throughput : 1 billion pages per day
Storage          : ~500 bytes avg compressed per page
                   -> 500 bytes x 8B pages = ~4 PB raw
Consistency      : eventual for index updates (freshness lag acceptable)
                   strong for query serving (read from replica is fine)
```

### 1.3 Capacity Estimation

You:
"Let me estimate crawl storage and query throughput separately."

```text
CRAWL STORAGE:
  8 billion pages x 500 bytes avg compressed = 4 TB per 1M pages = ~4 PB total
  Forward index (doc->words): ~200 bytes per page = ~1.6 PB
  Inverted index (word->docs): ~20% of forward index size = ~320 TB
  With replicas (3x): ~1 PB for inverted index cluster

QUERY THROUGHPUT:
  50,000 QPS
  Each query touches ~100 index shards in parallel
  Each shard must respond in < 10ms to meet 200ms p99 budget
  Result cache hit rate ~30% -> effective index load ~35,000 QPS

CRAWL THROUGHPUT:
  1 billion pages/day = 11,574 pages/second
  Each page ~50KB raw HTML
  Bandwidth: 11,574 x 50KB = ~580 MB/s inbound
```

---

## SECTION 2: HIGH-LEVEL ARCHITECTURE (WHAT I DRAW)

### 2.1 End-to-End Architecture Diagram (ASCII)

```text
+------------------------------------------------------------------+
|                        CRAWL PIPELINE                            |
+------------------------------------------------------------------+

   [Seed URLs]
        |
        v
+----------------+     +------------------+     +------------------+
| URL Frontier   |---->| Crawler Workers  |---->| Raw Page Store   |
| - priority Q   |     | - fetch HTML     |     | (HDFS / S3)      |
| - politeness   |     | - DNS resolve    |     | compressed HTML  |
| - dedup filter |     | - robots.txt     |     +--------+---------+
+----------------+     | - rate limit     |              |
        ^              +--------+---------+              v
        |                       |               +------------------+
        |               new links               | HTML Parser      |
        +----------------------------<----------|  - extract text  |
                                                |  - extract links |
                                                |  - extract meta  |
                                                +--------+---------+
                                                         |
                              +--------------------------+
                              |                          |
                              v                          v
                   +------------------+      +------------------+
                   | Duplicate Det.   |      | Link Extractor   |
                   | SimHash/MinHash  |      | -> URL Frontier  |
                   | drop near-dupes  |      +------------------+
                   +--------+---------+
                            |
                            v
+------------------------------------------------------------------+
|                        INDEX PIPELINE                            |
+------------------------------------------------------------------+

                   +------------------+
                   | Doc Processor    |
                   | - tokenize       |
                   | - stem           |
                   | - remove stops   |
                   | - score signals  |
                   +--------+---------+
                            |
               +------------+------------+
               |                         |
               v                         v
   +------------------+       +------------------+
   | Forward Index    |       | Inverted Index   |
   | doc_id -> words  |       | word -> [doc_ids |
   | (build phase)    |       |  + positions     |
   +------------------+       |  + tf scores]    |
                              +--------+---------+
                                       |
                            +----------+----------+
                            | Index Shards (N)    |
                            | replicated 3x each  |
                            +----------+----------+

+------------------------------------------------------------------+
|                        QUERY PIPELINE                            |
+------------------------------------------------------------------+

   [User Query]
        |
        v
+----------------+
| Query API GW   |
| rate limit     |
| auth (if any)  |
+-------+--------+
        |
        v
+----------------+     +------------------+
| Query Parser   |---->| Spell Corrector  |
| - tokenize     |     | - edit distance  |
| - stem         |     | - n-gram model   |
| - stopwords    |     +------------------+
| - expand syns  |
+-------+--------+
        |
        v
+----------------+
| Query Planner  |
| - build index  |
|   lookup plan  |
| - choose shards|
+-------+--------+
        |
        v (fan out to all relevant shards)
+------------------------------------------+
| Index Shard 1 | Shard 2 | ... | Shard N  |
| top-K local   | top-K   |     | top-K    |
| results       | results |     | results  |
+-------+----------------------------------+
        |
        v (merge + global rank)
+----------------+
| Result Merger  |
| - merge top-K  |
| - apply rerank |
| - PageRank     |
| - freshness    |
+-------+--------+
        |
        v
+----------------+
| Result Cache   |  (Redis / Memcached)
| TTL by query   |
+-------+--------+
        |
        v
+----------------+
| Snippet Gen.   |
| - highlight    |
| - extract desc |
+-------+--------+
        |
        v
   [User Results]
```

### 2.2 How I Explain This Diagram

You:
"I split the system into three independent pipelines: crawl, index, and query."

"The crawl pipeline is a continuous background job. It discovers URLs, fetches pages, parses them, and feeds cleaned content into the index pipeline."

"The index pipeline processes documents, builds the inverted index, and distributes shards across machines. Index updates are asynchronous — latency is acceptable here."

"The query pipeline is fully synchronous and latency-critical. A query fans out to all index shards in parallel, each shard returns local top-K results, a merger combines them and applies global ranking, and the result is cached for hot queries."

### 2.3 Plain English Walkthrough (For New Learners)

```text
1. URL FRONTIER
   Think of it as a giant to-do list of URLs to visit.
   It is a priority queue — important sites (high PageRank) are crawled more often.
   It also tracks politeness: don't visit the same domain more than once per second.

2. CRAWLER WORKERS
   Each worker picks a URL from the frontier, downloads the HTML, and stores it raw.
   Before fetching, it checks robots.txt: "Is this site allowing crawlers?"
   Many crawler workers run in parallel — thousands at once.

3. RAW PAGE STORE
   Every downloaded HTML page is stored as-is in a distributed file system (like S3).
   This is the "source of truth" for the crawl. The index is derived from this.

4. HTML PARSER
   Reads raw HTML and extracts:
   - Visible text (what users read)
   - Links (new URLs to add to the frontier)
   - Metadata (title, description, language)

5. DUPLICATE DETECTOR
   The web has millions of mirror sites with identical content.
   SimHash converts a document into a short fingerprint.
   Two documents with the same fingerprint are near-duplicates — only one is indexed.

6. DOC PROCESSOR
   Cleans the text: lowercase, remove punctuation, split into tokens (words),
   stem words (running -> run), remove stop words (the, is, a).
   Result: a clean list of meaningful terms with their positions in the document.

7. INVERTED INDEX
   The core of search. For every term, stores a "posting list":
   - Which documents contain this term
   - How many times (term frequency)
   - At what positions (for phrase matching)
   When you search "java tutorial", the engine looks up both words in the inverted index,
   finds documents that contain both, and ranks them by relevance.

8. INDEX SHARDS
   The inverted index is too large for one machine.
   It is split by document ID range across N shards.
   Each shard holds the full inverted index for its slice of documents.
   All shards are queried in parallel for every search.

9. QUERY PARSER
   Your search "runing java" is:
   - Spell-corrected to "running java"
   - Stemmed: "running" -> "run", "java" stays
   - Stop words removed: none here
   - Expanded: "java" may expand to include "jvm", "jdk"

10. RESULT MERGER + RANKER
    Each shard returns its local top-K results with scores.
    The merger combines all shard results, re-applies global signals (PageRank, freshness),
    and produces the final ranked top-10.

11. RESULT CACHE
    Popular queries like "weather today" are cached.
    Cache hit avoids a full index fan-out. Big latency win for hot queries.

12. SNIPPET GENERATOR
    Produces the two-line description you see under each result.
    Finds the sentence in the document that best matches the query terms.
```

---

## SECTION 3: CLASS DIAGRAM (LLD VIEW)

### 3.1 Full Class Diagram (ASCII)

```text
+------------------------------+
| CrawlerController            |
| +start()                     |
| +pause()                     |
| +getStats()                  |
+--------------+---------------+
               |
               v
+------------------------------+     +------------------------------+
| CrawlerService               |---->| URLFrontier                  |
| +crawlNext()                 |     | +enqueue(url, priority)      |
| +processFetched(page)        |     | +dequeue(): URL              |
+------+-----------------------+     | +isDuplicate(url): bool      |
       |                             | +markVisited(url)            |
       v                             +------------------------------+
+------------------------------+
| HTTPFetcher                  |     +------------------------------+
| +fetch(url): RawPage         |     | RobotsCache                  |
| +checkRobots(domain)         |---->| +isAllowed(domain, path)     |
| +respectCrawlDelay(domain)   |     | +getCrawlDelay(domain)       |
+------------------------------+     +------------------------------+

+------------------------------+
| HTMLParser                   |
| +parse(rawHtml): ParsedDoc   |
| +extractLinks(): List<URL>   |
| +extractText(): String       |
| +extractMeta(): Metadata     |
+------------------------------+

+------------------------------+     +------------------------------+
| DuplicateDetector            |     | DocProcessor                 |
| +computeSimHash(doc): long   |     | +tokenize(text): List<Token> |
| +isNearDuplicate(hash): bool |     | +stem(token): String         |
| +store(docId, hash)          |     | +removeStopWords(tokens)     |
+------------------------------+     | +buildTermFreqMap()          |
                                     +-------------+----------------+
                                                   |
                                                   v
+------------------------------+     +------------------------------+
| InvertedIndexWriter          |     | ForwardIndexWriter           |
| +addPosting(term, docId, tf, |     | +addDoc(docId, terms)        |
|            positions)        |     +------------------------------+
| +flush()                     |
| +merge(deltaIdx, baseIdx)    |
+------------------------------+

+------------------------------+
| QueryController              |
| +search(query): Results      |
+--------------+---------------+
               |
               v
+------------------------------+     +------------------------------+
| QueryParser                  |     | SpellCorrector               |
| +parse(rawQuery): Query      |---->| +correct(term): String       |
| +tokenize()                  |     | +suggest(prefix): List       |
| +stem()                      |     +------------------------------+
| +expand()                    |
+------+-----------------------+
       |
       v
+------------------------------+
| QueryPlanner                 |
| +plan(query): ShardPlan      |
| +selectShards(terms): List   |
+--------------+---------------+
               |
               v
+------------------------------+     +------------------------------+
| ShardQueryExecutor           |---->| InvertedIndexReader          |
| +queryAllShards(plan)        |     | +lookup(term): PostingList   |
| +mergeResults(shardResults)  |     | +intersect(lists): DocList   |
+--------------+---------------+     +------------------------------+
               |
               v
+------------------------------+
| Ranker                       |
| +score(doc, query): float    |
| +bm25(tf, idf, dl): float    |
| +applyPageRank(docId): float |
| +applyFreshness(crawledAt)   |
+--------------+---------------+
               |
               v
+------------------------------+
| SnippetGenerator             |
| +generate(doc, query): Snip  |
| +highlight(text, terms)      |
+------------------------------+
```

---

## SECTION 4: CRAWLING DEEP DIVE

### 4.1 URL Frontier Design (ASCII)

```text
+--------------------------------------------+
| URL Frontier                               |
|--------------------------------------------|
| Back Queue (per domain, politeness buffer) |
|  domain-A: [url1, url2, url3]              |
|  domain-B: [url4, url5]                    |
|  domain-C: [url6]                          |
|                                            |
| Front Queue (priority-based)               |
|  HIGH priority:   news sites, .gov, .edu   |
|  MEDIUM priority: known good domains       |
|  LOW priority:    newly discovered URLs    |
+--------------------------------------------+

Priority = f(PageRank, freshness_need, domain_trust)
```

You:
"The front queue manages priority. The back queue enforces politeness — one queue per domain ensures we never send two requests to the same domain within the crawl delay window."

### 4.2 Crawl Flow (ASCII)

```text
URL Frontier
    |
    | dequeue (highest priority, politeness OK)
    v
DNS Resolver (cached, TTL-aware)
    |
    v
robots.txt Cache
    | allowed? -> proceed
    | disallowed? -> skip, mark URL
    v
HTTP Fetcher
    | 200 OK -> store raw HTML in page store
    | 301/302 -> follow redirect (max 5 hops)
    | 404/410 -> mark URL dead, stop re-crawl
    | 429/503 -> back off, re-enqueue with delay
    v
Checksum / SimHash
    | duplicate? -> discard
    | new/changed? -> send to parse queue
    v
Parse Queue -> HTML Parser -> Link Extractor -> URL Frontier
                           -> Doc Processor -> Index Pipeline
```

### 4.3 Spider Trap Prevention

```text
Problem: Infinite URL generation
  Example: calendar.example.com/2024/01/01, /2024/01/02, ... forever

Controls:
- URL depth limit (do not crawl beyond depth 6 from seed)
- Max URLs per domain per crawl cycle
- Detect repeating URL patterns with regex blacklist
- URL normalisation (remove session IDs, tracking params before dedup)
```

### 4.4 Re-Crawl Freshness Strategy

```text
High freshness (crawl every few hours):
  - news sites, weather, stock tickers
  - pages with <meta http-equiv="refresh">
  - pages that changed on every prior crawl

Medium freshness (crawl daily):
  - blog posts, product pages
  - pages with Sitemap changefreq=daily

Low freshness (crawl weekly/monthly):
  - Wikipedia articles, static docs
  - pages that never changed across 5 crawls

Signal: if last_crawl_hash == current_hash -> content unchanged -> extend re-crawl interval
```

---

## SECTION 5: INVERTED INDEX (THE HEART OF SEARCH)

### 5.1 What the Inverted Index Looks Like

```text
TERM          DOC_IDS + TF + POSITIONS
---------     -------------------------------------------------
"java"     -> [(doc_1, tf=5, pos=[10,45,67]), (doc_3, tf=2, pos=[5,89]), ...]
"tutorial" -> [(doc_1, tf=3, pos=[11,46]),    (doc_7, tf=1, pos=[3]),    ...]
"python"   -> [(doc_2, tf=8, pos=[1,2,3]),    (doc_5, tf=4, pos=[22]),   ...]

When user searches "java tutorial":
  1. Look up posting list for "java"    -> {doc_1, doc_3, ...}
  2. Look up posting list for "tutorial"-> {doc_1, doc_7, ...}
  3. Intersect: docs containing BOTH    -> {doc_1}
  4. Rank doc_1 by BM25 score
  5. Return doc_1 as top result
```

### 5.2 Posting List Structure (ASCII)

```text
+----------+-----+----------+--------+
| term_id  | df  | ptr      | ...    |
+----------+-----+----------+--------+
    |
    v (pointer to posting list on disk)
+--------+----+----+--------+--------+--------+
| doc_id | tf | dl | pos[0] | pos[1] | pos[2] |
+--------+----+----+--------+--------+--------+
| doc_id | tf | dl | pos[0] | ...                (next entry)
+--------+----+----+--------+

df  = document frequency (how many docs contain this term)
tf  = term frequency in this doc (how many times term appears)
dl  = document length (total words in doc, used in BM25 normalisation)
pos = positions of term in document (enables phrase matching)
```

### 5.3 Building the Index (ASCII)

```text
Phase 1: MAP (per document)
  doc_1 text: "java is a programming language"
  After processing: {java:1, programming:1, language:1}
  Emit: (java, doc_1, tf=1), (programming, doc_1, tf=1), ...

Phase 2: SORT (by term)
  All (term, docId, tf) pairs sorted by term globally

Phase 3: REDUCE (merge into posting list per term)
  java -> [(doc_1,1), (doc_3,5), (doc_7,2)]
  Sort by docId within each posting list (enables fast intersection)

Phase 4: WRITE to index shards
  Distribute terms to shards by hash(term) % num_shards
```

### 5.4 Delta Index + Base Index Merge

```text
BASE INDEX   : full inverted index built from all crawled pages
               updated weekly or monthly via full rebuild
DELTA INDEX  : small index of pages crawled in the last 24 hours
               updated every hour

Query serving:
  query both BASE and DELTA in parallel
  merge results, prefer DELTA version if same docId appears in both
  (DELTA has fresher data for that document)

Merge job (periodic):
  merge DELTA into BASE, reset DELTA
  done during low-traffic window
```

---

## SECTION 6: RANKING ALGORITHMS

### 6.1 TF-IDF

You:
"TF-IDF answers: how important is this word to this document, relative to all documents?"

```text
TF  (Term Frequency)  = count of term t in doc d / total words in doc d
IDF (Inverse Doc Freq)= log(total docs / docs containing term t)

TF-IDF(t, d) = TF(t, d) * IDF(t)

Example:
  "the"     : TF=0.1, IDF=log(8B/8B)=0   -> score=0   (useless word)
  "java"    : TF=0.05, IDF=log(8B/10M)=3 -> score=0.15 (somewhat relevant)
  "graalvm" : TF=0.02, IDF=log(8B/100K)=5-> score=0.10 (very specific)
```

### 6.2 BM25 (Better Than TF-IDF)

You:
"BM25 is TF-IDF with two improvements: it caps term frequency saturation, and normalises for document length."

```text
BM25(t, d) = IDF(t) * [ tf * (k1 + 1) ] / [ tf + k1 * (1 - b + b * dl/avgdl) ]

k1 = 1.5  (term freq saturation: seeing a word 100x vs 10x is not 10x better)
b  = 0.75 (doc length normalisation: a long doc mentioning "java" once is less
            relevant than a short doc mentioning it once)
dl    = document length
avgdl = average document length across all docs

BM25 is the default ranking model in Elasticsearch, Solr, and Lucene.
```

### 6.3 PageRank

You:
"PageRank models the web as a graph. A page is important if many important pages link to it."

```text
PR(A) = (1 - d) + d * SUM( PR(B) / OutLinks(B) ) for all B that link to A

d = damping factor = 0.85
  (probability that a random web surfer follows a link rather than jumping to a random page)

Computed iteratively until convergence (typically 30-50 iterations over full web graph).

Intuition:
  - Wikipedia has millions of links pointing to it -> very high PageRank
  - A new blog with no inbound links -> near-zero PageRank
  - A page linked by many high-PR pages gets boosted even with fewer total links
```

### 6.4 Final Ranking Formula

```text
score(doc, query) =
    alpha * BM25(doc, query)       (text relevance)
  + beta  * PageRank(doc)          (link authority)
  + gamma * FreshnessScore(doc)    (recency bonus)
  + delta * AnchorTextScore(doc)   (what other pages call this page)

alpha, beta, gamma, delta = learned weights (machine learning / manual tuning)

FreshnessScore = 1 / (1 + days_since_crawl)  -- newer pages score higher
AnchorText     = text of hyperlinks pointing to this page (often more descriptive than page text)
```

---

## SECTION 7: QUERY PROCESSING FLOW

### 7.1 Full Query Flow (Sequence, ASCII)

```text
User      QueryGW    QueryParser  SpellCheck  Planner   Shards(N)  Merger   Cache  Snippet
 |           |            |           |          |          |         |        |       |
 | search    |            |           |          |          |         |        |       |
 |---------->|            |           |          |          |         |        |       |
 |           | check cache|           |          |          |         |        |       |
 |           |------------------------------------------------->      |        |       |
 |           |<-miss------|           |          |          |         |        |       |
 |           | parse query|           |          |          |         |        |       |
 |           |----------->|           |          |          |         |        |       |
 |           |            | spell chk |          |          |         |        |       |
 |           |            |---------->|          |          |         |        |       |
 |           |            |<-corrected|          |          |         |        |       |
 |           |            | plan shards          |          |         |        |       |
 |           |            |---------->|--------->|          |         |        |       |
 |           |            |           |          | fan-out  |         |        |       |
 |           |            |           |          |--------->|         |        |       |
 |           |            |           |          |<-top-K---|         |        |       |
 |           |            |           |          | merge+rank         |        |       |
 |           |            |           |          |--------->|         |        |       |
 |           |            |           |          |          |<-ranked-|        |       |
 |           | cache result                                            |------->|       |
 |           | gen snippets                                                     |------>|
 |<----------|<-results---|           |          |          |         |        |       |
```

### 7.2 Plain English Walkthrough (For New Learners)

```text
Step 1 — Cache Check
  Is this an exact query we've answered recently?
  "weather today" is searched millions of times per hour.
  Cache hit -> return immediately, skip all index work.

Step 2 — Query Parsing
  Raw query "runing java tutorail" is:
  - Spell corrected: "running java tutorial"
  - Tokenised: ["running", "java", "tutorial"]
  - Stemmed: ["run", "java", "tutori"]
  - Stop words removed: none here (all meaningful)
  - Expanded: "java" may add "jvm" as synonym

Step 3 — Shard Planning
  The inverted index is split across N shards.
  The planner determines: which shards could contain documents matching these terms?
  Answer: all shards (since doc-based sharding means any shard can have any term).
  So ALL shards are queried in parallel.

Step 4 — Parallel Shard Query
  Each shard independently:
  - Looks up posting lists for "run", "java", "tutorial"
  - Intersects them: find docs that contain all three
  - Scores each doc with BM25
  - Returns its local top-10 results

Step 5 — Merge and Global Rank
  The merger collects top-10 from each shard (could be 10 * N results).
  Applies global signals: PageRank, freshness score, anchor text.
  Re-ranks everything and picks the global top-10.

Step 6 — Cache Store
  Result is stored in cache with a TTL.
  Hot queries benefit all future users for that TTL window.

Step 7 — Snippet Generation
  For each result, find the sentence that best matches the query.
  Highlight matching terms in bold.
```

---

## SECTION 8: SCHEMA DIAGRAM

### 8.1 Schema (ASCII)

```text
+---------------------------+       +---------------------------+
| documents                 |       | url_frontier              |
|---------------------------|       |---------------------------|
| doc_id (PK)               |       | url_id (PK)               |
| url_id (FK)               |       | url (UNIQUE)              |
| content_hash (INDEX)      |       | domain                    |
| sim_hash                  |       | priority                  |
| title                     |       | status  (PENDING/CRAWLED/ |
| language                  |       |          FAILED/EXCLUDED) |
| crawled_at                |       | last_crawled_at           |
| page_rank_score           |       | next_crawl_at             |
| doc_length                |       | crawl_delay_ms            |
+---------------------------+       +---------------------------+

+---------------------------+       +---------------------------+
| terms                     |       | postings                  |
|---------------------------|       |---------------------------|
| term_id (PK)              |       | term_id (FK, PK1)         |
| term_text (UNIQUE INDEX)  |       | doc_id  (FK, PK2)         |
| doc_frequency             |       | term_frequency            |
| idf_score                 |       | doc_length                |
+---------------------------+       | positions (array/blob)    |
                                    | bm25_score                |
                                    +---------------------------+
                                    (stored on disk per shard)

+---------------------------+       +---------------------------+
| web_graph                 |       | domain_metadata           |
|---------------------------|       |---------------------------|
| src_doc_id (FK, INDEX)    |       | domain (PK)               |
| dst_doc_id (FK, INDEX)    |       | robots_txt_cache          |
| anchor_text               |       | crawl_delay_ms            |
+---------------------------+       | last_robots_check         |
(used for PageRank compute)         | trust_score               |
                                    +---------------------------+

+---------------------------+
| search_cache              |
|---------------------------|
| query_hash (PK)           |
| results_blob              |
| cached_at                 |
| ttl_seconds               |
+---------------------------+
```

### 8.2 Indexing Strategy

```text
documents:
- UNIQUE (url_id)
- INDEX  (content_hash)     -- fast duplicate detection
- INDEX  (crawled_at DESC)  -- freshness-ordered re-crawl scheduling

url_frontier:
- UNIQUE (url)
- INDEX  (priority DESC, next_crawl_at ASC)  -- crawler dequeue order
- INDEX  (domain, status)                    -- politeness grouping

postings:
- PRIMARY KEY (term_id, doc_id) -- covers all posting list lookups
- Stored sharded by doc_id range across index shard cluster

web_graph:
- INDEX (src_doc_id)  -- outbound links of a page
- INDEX (dst_doc_id)  -- inbound links (for PageRank)
```

### 8.3 Plain English Walkthrough (For New Learners)

```text
documents
  One row per crawled page. Stores the page's hash (to detect if it changed
  since last crawl), its SimHash (to detect near-duplicates), and its PageRank score.

url_frontier
  The crawler's work queue. next_crawl_at controls when to re-visit.
  domain column + crawl_delay_ms enforce politeness per domain.

terms
  Dictionary of all unique words in the index.
  idf_score is pre-computed and cached here to avoid recalculating per query.

postings
  The inverted index itself. For every (term, document) pair, stores
  how many times the term appears and at what positions.
  This is the most read table at query time — must be on fast SSDs.

web_graph
  Stores all hyperlinks between pages. Used offline to compute PageRank.
  anchor_text (the visible text of the link) is a strong relevance signal.

domain_metadata
  Per-domain crawler configuration. robots.txt rules cached here so we do
  not re-fetch robots.txt on every page visit to the same domain.

search_cache
  Results for recent queries. Key = hash of normalised query string.
  Avoids hitting the index for repeat popular queries.
```

---

## SECTION 9: FAILURE SCENARIOS

### 9.1 Crawler Worker Crash

```text
Risk: URLs in-flight are lost
Controls:
- URL leasing: when a worker picks a URL, it gets a lease (TTL=5min)
- If worker crashes, lease expires -> URL re-queued automatically
- Idempotent crawl: re-fetching a URL just overwrites the stored HTML
Outcome: no URL is permanently lost
```

### 9.2 Index Shard Down

```text
Risk: queries to that shard fail -> missing results
Controls:
- Each shard has 2 replicas (3 copies total)
- Query planner routes to replica if primary is down
- Replica lag: async replication means replica may be slightly stale
  (acceptable - eventual consistency for index updates)
Outcome: degraded freshness, not missing results
```

### 9.3 Index Shard Overloaded

```text
Risk: shard latency spikes -> p99 query latency blows up
Controls:
- Result cache absorbs 30%+ of read load for hot queries
- Query timeout per shard: 50ms hard limit
  (if shard exceeds timeout, return partial results rather than wait)
- Load shedding: drop lowest-priority queries if queue depth spikes
Outcome: slightly lower result quality (partial shard results), not full outage
```

### 9.4 Crawler Triggers Spider Trap

```text
Risk: infinite URL generation exhausts frontier queue and storage
Controls:
- URL depth limit (max depth 6 from seed)
- Per-domain URL cap per crawl cycle
- Detect cyclic URL patterns (regex blacklist for session IDs, infinite calendars)
- URL normalisation before de-duplication
Outcome: trap domain is flagged, crawler moves on
```

### 9.5 Duplicate Content Flood

```text
Risk: one piece of content from 1000 mirror sites fills index, crowding out original
Controls:
- SimHash deduplication: near-duplicate pages are dropped before indexing
- Canonical URL detection: <link rel="canonical"> tells crawler the original
- Domain trust score: low-trust domains indexed with lower priority
Outcome: original content ranks higher, mirrors excluded or ranked low
```

### 9.6 Query Latency Spike

```text
Risk: slow shard fan-out causes p99 to breach 200ms SLO
Controls:
- Hedged requests: send query to both primary and replica, use first response
- Result cache hit rate increase during incident (warm cache)
- Scatter-gather timeout: do not wait for stragglers beyond 50ms
- Reduce top-K per shard during load (return top-5 instead of top-20)
Outcome: marginally fewer results, latency SLO preserved
```

---

## SECTION 10: TRADEOFFS (SAY THIS CLEARLY)

```text
Choice                              Advantage                         Tradeoff
------------------------------------------------------------------------------------------
Document-based sharding              simple routing, balanced load      cross-shard merge needed
Term-based sharding                  no fan-out for single-term queries  hot terms overload one shard
Delta + Base index split             fresh results without full rebuild  query must hit both indexes
BM25 over TF-IDF                     better length normalisation         slightly more compute
Result caching by query hash         major latency win for hot queries   stale results for TTL window
Eventual consistency on index        crawl pipeline decoupled from query strict consistency is impractical
Timeout + partial results            latency SLO preserved              occasional missing shard results
SimHash deduplication                prevents mirror site flooding      near-duplicate threshold is tunable
Async PageRank (offline batch)       cheap, accurate over full graph    PageRank is hours/days stale
Hosted crawl infrastructure          full control of crawl rate/policy  very expensive to operate at scale
```

You:
"I accept eventual consistency for index updates — a page indexed 30 seconds late is fine. I never accept it for query serving — users expect consistent top results."

---

## SECTION 11: ANTI-SPAM AND SECURITY

### 11.1 Search Spam Controls

```text
Content spam:
- keyword stuffing detection (abnormally high TF for low-value terms)
- hidden text detection (white text on white background -> penalise)
- thin content filter (pages with < 100 meaningful words -> low priority)

Link spam:
- link farm detection: domain with 1000s of outbound links to same target
- paid link detection: nofollow attribute on sponsored links
- trust rank: propagate trust from known-good seed domains (Wikipedia, .gov, .edu)

Cloaking:
- serve different content to crawler vs human users -> permanent ban from index
- detect by comparing crawled HTML vs rendered HTML (headless browser check)
```

### 11.2 Query Abuse Controls

```text
- rate limit per IP / per user (Query API Gateway)
- detect scraping patterns (sequential queries, no human dwell time)
- CAPTCHA challenge after threshold
- query length limit (max 64 tokens)
- block queries that are purely API credential probes
```

---

## SECTION 12: OBSERVABILITY AND SLO RUNBOOK

### 12.1 Key Metrics

```text
Crawl pipeline:
- pages_crawled_per_second
- crawl_error_rate (4xx, 5xx, DNS failure)
- frontier_queue_depth (growing = crawlers can't keep up)
- duplicate_detection_rate
- fresh_page_ratio (% of pages re-crawled within SLA window)

Index pipeline:
- indexing_lag (time from crawl to available in index)
- delta_index_size (growing unboundedly = merge job failing)
- shard_replication_lag

Query pipeline:
- query_p95_latency (by shard, by merger, end-to-end)
- cache_hit_rate
- shard_timeout_rate (partial results indicator)
- result_count_per_query (dropping = index coverage shrinking)
```

### 12.2 Alerts

```text
- frontier queue depth growing for 30 min (crawler throughput degraded)
- any index shard returning 0 results (shard outage)
- query p99 > 500ms for 5 min
- cache hit rate drops below 20%
- delta index merge job not completed in 2 hours
- crawl error rate > 5% for a domain (site change or block)
```

### 12.3 Incident Runbook Snippet

```text
If query p99 latency spikes:
1) Check cache hit rate — if dropped, warm cache by replaying recent popular queries
2) Check shard latency metrics — which shard is slow?
3) If one shard slow: route to replica, investigate primary
4) If all shards slow: delta index merge job competing for I/O -> pause merge
5) Enable scatter-gather early timeout (reduce top-K per shard)
6) If still slow: enable result cache bypass for fresh results, serve from cache only
```

---

## SECTION 13: JAVA/SPRING IMPLEMENTATION NOTES

```text
- Crawler workers as Spring Batch jobs with configurable thread pool
- URL Frontier backed by Redis sorted set (score = priority, deadline = next_crawl_at)
- HTML parsing via JSoup library (handles malformed HTML gracefully)
- SimHash computed as 64-bit fingerprint — store as long in DB
- Inverted index stored on disk using RocksDB (LSM-tree, fast write, compaction)
- BM25 scoring computed at index time per (term, doc) pair — store in postings table
- Query fan-out via CompletableFuture.allOf() with per-shard timeout (50ms)
- Scatter-gather merger sorts by composite score using PriorityQueue
- Result cache: Redis with TTL per query category (news=30s, static=1h)
- PageRank computed as offline Spark job on web_graph table, results pushed to doc store
- Snippet generation: sliding window over document sentences, score by query term coverage
```

---

## SECTION 14: 15-YEAR CLOSING ANSWER

You:
"I design search systems with one rule: the index is a derived artifact — source of truth is the crawled page store."

"The crawl pipeline is a continuous background job with politeness, freshness scheduling, and spam controls. It feeds a processing pipeline that tokenises, stems, deduplicates, and builds posting lists."

"The inverted index is the query-time data structure. I shard it by document range, replicate 3x, and query all shards in parallel with a hard timeout to protect latency SLOs."

"BM25 gives text relevance, PageRank gives link authority, freshness gives recency. The merger combines all three signals into a global ranking."

"For freshness, I use a delta index for recent crawls and a base index for historical data. Queries hit both and merge results. Periodic merges keep the delta small."

"Result caching is the highest-leverage latency optimization — a 30% cache hit rate removes 30% of shard fan-out entirely."

One-line close:
"Crawl everything, index the important parts, rank by relevance and authority, serve under 200ms."

---

## SECTION 15: CROSS-QUESTIONS AND STRONG ANSWERS

Q1: What is an inverted index and why is it used?
A: "An inverted index maps each word to the list of documents that contain it. Without it, answering 'which pages mention java?' would require scanning every document. With it, that lookup is O(1) — just read the posting list for 'java'."

Q2: How do you handle a query for a phrase like "machine learning"?
A: "Phrase queries require position data in the posting list. I find docs that contain both 'machine' and 'learning', then check that their positions are adjacent (pos of 'learning' == pos of 'machine' + 1). Position storage is the key."

Q3: How do you keep the index fresh?
A: "Two-tier approach. Delta index for pages crawled in the last 24 hours, re-indexed hourly. Base index rebuilt weekly from the full page store. Queries hit both. For breaking news, I prioritise high-PageRank and news-domain URLs in the frontier."

Q4: Why not just use Elasticsearch for this?
A: "Elasticsearch uses Lucene internally — the same BM25 + inverted index. For a small-scale search (millions of docs), Elasticsearch is the right answer. At web scale (billions of docs), you need custom sharding, a dedicated crawl pipeline, offline PageRank computation, and a result cache tier that Elasticsearch does not provide out of the box."

Q5: How does PageRank handle new pages with no inbound links?
A: "New pages start with minimal PageRank — near zero. They are served for direct URL lookups and long-tail exact matches where text relevance dominates. As they earn inbound links over time, their PageRank grows. For brand-new domains with no history, we rely entirely on BM25 text relevance."

Q6: How do you prevent a crawler from being blocked by websites?
A: "Respect robots.txt, honour crawl-delay, rotate User-Agent strings to identify as a known crawler (not disguise it), limit requests per domain per second, back off on 429/503 responses, and distribute crawl traffic across multiple IP ranges."

Q7: How do you handle multilingual content?
A: "Language detection at parse time (using n-gram models or libraries like langdetect). Language-specific stemming and stop word lists. Separate index partitions per language, or a language tag on each posting so query routing can filter by detected query language."

Q8: What is the difference between precision and recall in search?
A: "Precision: of the results returned, how many are actually relevant? Recall: of all relevant documents, how many did we return? BM25 optimises precision — top results are highly relevant. Recall is improved by query expansion (adding synonyms). A good search engine trades off: high recall for broad queries, high precision for specific ones."

---

## SECTION 16: QUICK WHITEBOARD VERSION (2 MIN)

```text
1) Crawl      : URL Frontier -> Crawler Workers -> Raw Page Store
2) Parse      : HTML Parser -> text + links + metadata
3) Dedup      : SimHash -> drop near-duplicates
4) Index      : Doc Processor -> tokenize/stem -> Inverted Index (sharded)
5) Rank prep  : BM25 scores at index time + PageRank (offline batch)
6) Query in   : Query API -> spell correct -> stem -> expand
7) Fan-out    : Query Planner -> all index shards in parallel (50ms timeout)
8) Merge      : top-K from each shard -> global rank (BM25 + PageRank + freshness)
9) Cache      : result cache (Redis, TTL by query type)
10) Serve     : Snippet Generator -> highlight -> return results
11) Freshness : Delta index (hourly) + Base index (weekly rebuild)
12) Ops       : frontier depth + indexing lag + shard p99 + cache hit rate
```

Closing line:
"This design assumes the web is always changing, duplicate content is the norm, and every query must complete under 200ms regardless of how many shards we fan out to."
