# Cursor-Based Pagination vs Offset Pagination
### Why `page=10000` Kills Your Database

---

## PART 1 — THE STUDENT CONVERSATION

**Imagine a library with 1 million books, sorted by title.**

A customer walks in and says: "I want books 500,001 through 500,010."

**Librarian using offset pagination:**
Starts from book 1. Counts to 500,000. Throws those away. Picks up the next 10. Done.
Counted and discarded 500,000 books just to give you 10.

**Librarian using cursor pagination:**
Customer gives you a bookmark they got last time: "I left off at 'Harry Potter — Goblet of Fire'."
You walk directly to that shelf, pick up the next 10 books after it. Done.
Zero wasted work.

That's the entire difference.

---

## PART 2 — OFFSET PAGINATION INTERNALS

### How it works

```sql
-- Request: GET /products?page=3&limit=10
-- (page 3 = skip first 20 rows, return next 10)

SELECT * FROM products
ORDER BY created_at DESC
LIMIT 10 OFFSET 20;
```

### What MySQL ACTUALLY does

```
Table: products (1 million rows)

LIMIT 10 OFFSET 20:
─────────────────────────────────────────────────────
  Step 1: Scan rows 1 through 30 (using index or full scan)
  Step 2: DISCARD rows 1–20 (the OFFSET)
  Step 3: RETURN rows 21–30

  Rows scanned: 30
  Rows returned: 10
  Wasted work: 20 rows

LIMIT 10 OFFSET 500000:
─────────────────────────────────────────────────────
  Step 1: Scan rows 1 through 500,010
  Step 2: DISCARD rows 1–500,000
  Step 3: RETURN rows 500,001–500,010

  Rows scanned: 500,010
  Rows returned: 10
  Wasted work: 500,000 rows ← MySQL worked hard for nothing

At 100 users all requesting page=50000 simultaneously:
  Each query scans ~500,000 rows
  Total rows scanned: 50,000,000
  Total rows returned: 1,000
  0.002% of work was useful
  → Database CPU at 100%, query latency: 5–30 seconds
  → Everything else on the DB slows down
```

### The "shifting data" problem

```
Scenario: user is reading a feed, goes from page 1 → page 2.
Between their requests, 5 new items are inserted at the top.

Page 1 (first request):
  Row 1:  Post A  ← user sees this
  Row 2:  Post B
  ...
  Row 10: Post J

(5 new posts inserted)

Page 2 (second request, OFFSET=10):
  Row 1:  Post NEW1  ← inserted after user loaded page 1
  Row 2:  Post NEW2
  Row 3:  Post NEW3
  Row 4:  Post NEW4
  Row 5:  Post NEW5
  Row 6:  Post A      ← user already saw this!
  Row 7:  Post B      ← duplicate!
  ...
  Row 10: Post E      ← duplicate!
  Row 11: Post F  ← what user wanted
  ...

With OFFSET, new inserts shift everything down → duplicates on next page.
```

---

## PART 3 — CURSOR PAGINATION INTERNALS

### How it works

Instead of "skip N rows", use "give me rows after this specific value."

```sql
-- First request (no cursor):
SELECT id, title, created_at
FROM products
ORDER BY created_at DESC
LIMIT 10;

-- Returns 10 rows. Last row: id=4521, created_at='2024-01-15 10:30:00'
-- Server encodes this as cursor: base64("2024-01-15 10:30:00:4521")

-- Second request (with cursor):
SELECT id, title, created_at
FROM products
WHERE (created_at, id) < ('2024-01-15 10:30:00', 4521)
                      ↑ row tuple comparison
ORDER BY created_at DESC, id DESC
LIMIT 10;
```

### What MySQL ACTUALLY does

```
With index on (created_at DESC, id DESC):

  Step 1: Use B-tree index to find entry matching
          created_at='2024-01-15 10:30:00', id=4521
          → O(log N) — fast, direct lookup

  Step 2: From that position, read the next 10 entries in the index
          → O(K) where K=10 — just walk the linked list

  Total rows touched: ~10 (not 500,010!)
  Same performance whether you're on page 1 or page 50,000.
```

### No duplicate / missing data

```
User reads page 1 (cursor=null):
  Returns posts: A, B, C, D, E, F, G, H, I, J
  Last item cursor: cursor=J

(5 new posts inserted at top: NEW1, NEW2, NEW3, NEW4, NEW5)

User reads page 2 (cursor=J):
  WHERE (created_at, id) < (J.created_at, J.id)
  → Returns posts AFTER J: K, L, M, N, O, P, Q, R, S, T

  NEW1-NEW5 are all NEWER than J → never appear in page 2
  No duplicates, no gaps.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "How does your social feed API handle pagination for the infinite scroll?"

**You (architect answer):**

> "Offset pagination is what most people implement first — LIMIT N OFFSET M — but it has two
> critical problems at scale.
>
> First, performance: OFFSET N forces MySQL to scan and discard N rows to find its starting point.
> At page 500 with 20 items per page, that's 10,000 rows scanned for 20 returned. At 100K active
> users all scrolling deep feeds simultaneously, you're doing billions of wasted row scans per minute.
>
> Second, correctness: offset pagination is broken with live data. If 10 new posts arrive between
> page 1 and page 2, page 2 starts 10 rows later — the user sees items from page 1 again as
> duplicates. For a social feed that updates every second, offset pagination always shows duplicates.
>
> For infinite scroll I use cursor-based pagination. The server returns a cursor (an opaque token
> encoding the last seen row's sort key — typically base64 of `created_at:id`). The next request
> sends this cursor. The SQL becomes `WHERE (created_at, id) < (cursor_time, cursor_id)` with
> an index on `(created_at DESC, id DESC)`. This is a direct B-tree lookup — O(log N) regardless
> of how deep in the feed you are. Page 50,000 is as fast as page 1.
>
> The trade-off: you can't jump to 'page 42,000' — you can only go forward or backward from a cursor.
> For a social feed, that's fine. For an admin dashboard where users need to jump to a specific page,
> offset pagination is actually correct — just cap it at page 100 or so to prevent abuse."

---

## PART 5 — IMPLEMENTATION

### API Contract

```
Offset Pagination API:
  GET /products?page=3&limit=10
  Response: {
    "data": [...],
    "total": 1000000,
    "page": 3,
    "totalPages": 100000
  }

Cursor Pagination API:
  GET /products?limit=10              ← first request, no cursor
  GET /products?cursor=eyJp...&limit=10  ← subsequent requests

  Response: {
    "data": [...],
    "nextCursor": "eyJpZCI6NDUyMSwiY3JlYXRlZF9hdCI6IjIwMjQtMDEtMTUifQ==",
    "hasMore": true
  }

  When hasMore = false → no nextCursor → end of results
```

### Java / Spring Boot Implementation

```java
// Repository:
@Query("""
    SELECT p FROM Post p
    WHERE (:cursor IS NULL
           OR (p.createdAt, p.id) < (:cursorTime, :cursorId))
    ORDER BY p.createdAt DESC, p.id DESC
    """)
List<Post> findWithCursor(
    @Param("cursorTime") Instant cursorTime,
    @Param("cursorId") Long cursorId,
    Pageable pageable
);

// Service:
public PageResult<Post> getPosts(String cursor, int limit) {
    CursorData decoded = cursor != null ? decodeCursor(cursor) : null;

    List<Post> posts = decoded == null
        ? postRepo.findFirst(PageRequest.of(0, limit + 1))
        : postRepo.findWithCursor(decoded.time(), decoded.id(),
                                  PageRequest.of(0, limit + 1));
    // Fetch limit+1 to know if there's a next page

    boolean hasMore = posts.size() > limit;
    List<Post> data = hasMore ? posts.subList(0, limit) : posts;

    String nextCursor = hasMore
        ? encodeCursor(data.get(data.size() - 1))
        : null;

    return new PageResult<>(data, nextCursor, hasMore);
}

// Cursor encoding (opaque to client):
private String encodeCursor(Post last) {
    String raw = last.getCreatedAt().toEpochMilli() + ":" + last.getId();
    return Base64.getEncoder().encodeToString(raw.getBytes());
}

private CursorData decodeCursor(String cursor) {
    String raw = new String(Base64.getDecoder().decode(cursor));
    String[] parts = raw.split(":");
    return new CursorData(Instant.ofEpochMilli(Long.parseLong(parts[0])),
                          Long.parseLong(parts[1]));
}
```

---

## PART 6 — REQUIRED INDEX FOR CURSOR PAGINATION

```sql
-- Without this index: cursor pagination is still a full scan
CREATE INDEX idx_posts_cursor
ON posts(created_at DESC, id DESC);

-- Verify it's being used:
EXPLAIN SELECT * FROM posts
WHERE (created_at, id) < ('2024-01-15 10:30:00', 4521)
ORDER BY created_at DESC, id DESC
LIMIT 10;

-- Should see:
-- type: range (not ALL)
-- key: idx_posts_cursor
-- Extra: Using index condition (not Using filesort)
```

---

## PART 7 — WHEN TO USE WHICH

```
Use Cursor Pagination when:
  ✓ Infinite scroll / feed (social media, notifications)
  ✓ Real-time data (new items added frequently)
  ✓ Large datasets (millions of rows)
  ✓ Deep pagination is required (beyond page 100)
  ✓ Consistent result required (no duplicates/gaps)

Use Offset Pagination when:
  ✓ Admin dashboards with explicit page numbers ("Go to page 47")
  ✓ Static or rarely-changing data (product catalog)
  ✓ Small datasets (under 10,000 rows — offset cost is negligible)
  ✓ Client needs to know total count and total pages
  ✓ Random access needed (jump to any page)

Hybrid (use both):
  Most real products expose both:
  → Public feed API: cursor-based (infinite scroll)
  → Admin API: offset-based with hard cap (page <= 100)
```

---

## QUICK REFERENCE CARD

```
┌─────────────────────┬──────────────────────┬──────────────────────┐
│                     │  Offset Pagination   │  Cursor Pagination   │
├─────────────────────┼──────────────────────┼──────────────────────┤
│ SQL                 │ LIMIT N OFFSET M     │ WHERE (col, id) < X  │
│ DB scan cost        │ O(offset + limit)    │ O(log N + limit)     │
│ Page 50,000 perf    │ Scans 500,000 rows   │ Same as page 1       │
│ Handles new inserts │ Duplicates on pg 2   │ No duplicates        │
│ Jump to page N      │ Yes                  │ No (forward only)    │
│ Total count         │ Easy (SELECT COUNT)  │ Expensive / skip it  │
│ Implementation      │ Simple               │ More complex         │
│ Indexing needed     │ ORDER BY column      │ (sort_col, id) index │
│ Best for            │ Admin, static data   │ Feeds, infinite scroll│
└─────────────────────┴──────────────────────┴──────────────────────┘

Interview one-liner:
"Offset pagination forces the DB to scan and discard N rows on every page.
Cursor pagination uses the last-seen value as a WHERE clause — the index
jumps directly to it. Page 50,000 is as fast as page 1."
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every system with a list endpoint will be probed on pagination — "how do you handle page 500?" is the interviewer checking if you know offset scanning is O(N) not O(1).

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **05 — Social Media (Instagram/Facebook)** | Infinite scroll feed. OFFSET 9980 LIMIT 20 forces the DB to scan and discard 9,980 rows before returning 20. Cursor on (created_at, post_id) is a direct index seek — always scans exactly 20 rows regardless of scroll depth. At 1M concurrent users scrolling, this is the difference between O(N) and O(1) per page load. |
| **09 — E-Commerce** | Order history for business users with 5,000+ orders. Cursor on (order_date, order_id) makes every page equally fast — page 1 and page 250 both do a single index seek. Offset pagination degrades linearly: page 250 scans 5,000 rows. |
| **13 — Leaderboard** | "Show rank and the 10 players above and below me." ZREVRANGEBYSCORE with a score cursor is O(log N + K) and consistent under real-time score updates — OFFSET in a sorted set would drift as scores change between page loads. |
| **17 — OTT Platform** | Video catalog with 10 million videos. OFFSET 200,000 LIMIT 20 scans 200,000 index entries per page load. Cursor on (created_at, video_id) = 1 index seek, 20 rows returned, zero wasted scans regardless of page depth. |

**Architect's one-liner for the interview:**
*"Offset pagination is O(N) — the DB must count N rows from the start every time; cursor pagination is O(1) — the cursor IS the index position, so page 1 and page 10,000 cost exactly the same."*
