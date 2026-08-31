# Index Types — B-Tree vs Hash vs Composite vs Covering Index
### What Each Is and When to Use Which

---

## PART 1 — THE STUDENT CONVERSATION

**Why do indexes exist at all?**

Imagine a 500-page book with no table of contents. To find "connection pooling", you read every single page. That's a full table scan — O(N).

Now imagine the book has an index at the back: "connection pooling → page 247." You jump straight there — O(log N) or better.

A database index is that back-of-book index. But there are different kinds depending on the type of search you're doing.

---

## PART 2 — B-TREE INDEX (THE DEFAULT — 95% OF INDEXES YOU'LL CREATE)

### What it is

A balanced tree where each node contains a sorted range of key values with pointers to child nodes or the actual row data.

```
B-Tree index on users.age:
──────────────────────────

                  ┌──────────────┐
                  │  ROOT: [30]  │
                  └──────┬───────┘
                         │
           ┌─────────────┴─────────────┐
           ▼                           ▼
    ┌─────────────┐             ┌─────────────┐
    │ [15] [22]   │             │ [38] [45]   │
    └──────┬──────┘             └──────┬──────┘
           │                           │
    ┌──────┼──────┐             ┌──────┼──────┐
    ▼      ▼      ▼             ▼      ▼      ▼
 [10,12] [18,20] [25,28]     [32,35] [40,42] [48,50]
 (data)  (data)  (data)      (data)  (data)  (data)
   ↕       ↕       ↕           ↕       ↕       ↕
 linked  linked  linked      linked  linked  linked

Leaf nodes are doubly linked → range scans: just follow the chain
```

### What queries it helps

```sql
-- Point lookup (equality):
WHERE age = 25              ← O(log N)  ✓

-- Range query:
WHERE age BETWEEN 20 AND 35 ← O(log N + K)  ✓
                               (find 20, then walk chain to 35)

-- Less than / greater than:
WHERE age > 30              ← O(log N + K)  ✓

-- Starts with (for strings):
WHERE name LIKE 'Abh%'      ← O(log N)  ✓
WHERE name LIKE '%bhi'      ← FULL SCAN ✗ (can't use B-tree for suffix)

-- ORDER BY (if index column matches sort):
ORDER BY age ASC            ← no extra sort needed  ✓

-- NOT supported efficiently:
WHERE age != 25             ← usually full scan ✗
WHERE YEAR(created_at) = 2024  ← function on column breaks index ✗
```

### Create

```sql
CREATE INDEX idx_users_age ON users(age);
```

---

## PART 3 — HASH INDEX

### What it is

Instead of a tree, build a hash map: `hash(key) → row pointer`.

```
Hash index on users.email:
───────────────────────────

  email value          hash        bucket    row pointer
  ──────────────       ────        ──────    ───────────
  "alice@x.com"   →  0xA3F1  →  bucket[5] → row id 1041
  "bob@y.com"     →  0x7C2B  →  bucket[2] → row id 2083
  "carol@z.com"   →  0xD4E9  →  bucket[8] → row id 3017

Lookup: hash("alice@x.com") → 0xA3F1 → bucket[5] → row 1041
O(1) — one hash computation, one bucket lookup
```

### What queries it helps (and doesn't)

```sql
-- Equality only:
WHERE email = 'alice@x.com'   ← O(1)  ✓ (fastest possible)

-- Does NOT support:
WHERE age > 30                ← ✗ (hash gives no ordering)
WHERE age BETWEEN 20 AND 35   ← ✗
WHERE name LIKE 'Abh%'        ← ✗
ORDER BY age                  ← ✗

-- Hash collisions:
If two different emails hash to same bucket → bucket stores a linked list
In worst case (all same hash): O(N). Usually O(1).
```

### Where you actually find hash indexes

```
MySQL InnoDB: does NOT support user-created hash indexes
              BUT has Adaptive Hash Index (AHI) — automatically created
              internally for frequently accessed B-tree pages

MySQL MEMORY engine: supports hash indexes
PostgreSQL: supports hash indexes explicitly
Redis: entire data model is a hash map

Practical rule: don't choose hash index explicitly.
                Use B-tree. MySQL/Postgres optimizes internally.
```

---

## PART 4 — COMPOSITE INDEX (MULTI-COLUMN INDEX)

### What it is

An index on multiple columns together. The order of columns matters enormously.

```sql
CREATE INDEX idx_orders_status_date ON orders(status, created_at);
--                                            ──────  ──────────
--                                            first   second
```

### The Left-Prefix Rule (the most important rule)

```
Index: (status, created_at, user_id)
                ↑ leftmost prefix

Queries that CAN use this index:
  WHERE status = 'pending'                          ← uses (status)
  WHERE status = 'pending' AND created_at > '2024' ← uses (status, created_at)
  WHERE status = 'pending' AND created_at > '2024'
        AND user_id = 42                            ← uses all 3 columns

Queries that CANNOT use this index:
  WHERE created_at > '2024'                         ← skips leftmost column ✗
  WHERE user_id = 42                                ← skips both left columns ✗
  WHERE created_at > '2024' AND user_id = 42        ← skips leftmost column ✗

The rule: MySQL can only use consecutive columns from the left.
          It stops at the first column not in the WHERE clause.
```

### The Column Order Rule

```
Scenario: queries are always:
  WHERE status = 'pending' AND created_at > '2024-01-01'
  WHERE status = 'shipped'
  WHERE status = 'pending' AND user_id = 42

Best index: (status, created_at)  ← high-cardinality filter first? No!
                                     equality first, range last

Rule: put equality columns BEFORE range columns
      (MySQL stops using the index at the first range column)

BAD:  (created_at, status)
  WHERE status='pending' AND created_at > '2024' 
  → uses only created_at, then filters status manually

GOOD: (status, created_at)
  WHERE status='pending' AND created_at > '2024'
  → uses status (equality), then narrows by created_at range
```

### Real Example: Index Design for Orders Table

```sql
-- Query pattern:
SELECT * FROM orders
WHERE user_id = 42
  AND status = 'pending'
  AND created_at > '2024-01-01'
ORDER BY created_at DESC;

-- Best index:
CREATE INDEX idx_orders_user_status_date
ON orders(user_id, status, created_at);
--         ───────  ──────  ──────────
--         equality equality  range (last)

-- Why this order?
-- 1. user_id: equality, high selectivity (narrows from millions to dozens)
-- 2. status: equality, further narrows (pending = ~10% of user's orders)
-- 3. created_at: range, applied last; also satisfies ORDER BY (no extra sort)
```

---

## PART 5 — COVERING INDEX

### What it is

An index that contains ALL the columns your query needs — so MySQL never has to touch the actual table row. The index IS the answer.

```
Normal index lookup:
──────────────────────────────────────────────────────

  Query: SELECT name, email FROM users WHERE age = 25

  Step 1: B-tree index on (age) → find entries where age=25
          Returns: row pointer → row id 4521
                              → row id 8033
                              → row id 9901

  Step 2: For each row id → go to the table page and fetch the row
          (this is called a "table heap fetch" or "bookmark lookup")
          Disk read: page containing row 4521
          Disk read: page containing row 8033
          Disk read: page containing row 9901

  Total: index traversal + 3 random disk reads to table

Covering index lookup:
──────────────────────────────────────────────────────

  Index: CREATE INDEX idx_covering ON users(age, name, email)
  --                                        ───  ────  ─────
  --                                        key  extra extra

  Query: SELECT name, email FROM users WHERE age = 25

  Step 1: B-tree index → find entries where age=25
          Each leaf node already contains: age + name + email
          No need to go to the table!

  Step 2: READ DONE — return name and email from index directly

  Total: index traversal only — no table reads
  MySQL says: "Using index" in EXPLAIN (not "Using index; Using where")
```

### EXPLAIN output — how to identify

```sql
EXPLAIN SELECT name, email FROM users WHERE age = 25;

-- Without covering index:
+------+------+------+----------+-------+
| type | key  | rows | filtered | Extra |
+------+------+------+----------+-------+
| ref  | idx  |  100 |   100.00 |       |  ← blank Extra = goes to table
+------+------+------+----------+-------+

-- With covering index:
+------+------+------+----------+-------------+
| type | key  | rows | filtered | Extra       |
+------+------+------+----------+-------------+
| ref  | idx  |  100 |   100.00 | Using index |  ← "Using index" = covered!
+------+------+------+----------+-------------+
```

---

## PART 6 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your `/orders` query is doing a full table scan even though there's an index on `user_id`. Why might that happen?"

**You (architect answer):**

> "A few reasons why MySQL might ignore the index.
>
> First, if the query has a function on the indexed column: `WHERE YEAR(created_at) = 2024`
> — MySQL can't use the B-tree index because the tree is sorted by the raw `created_at` value,
> not by `YEAR(created_at)`. Fix: rewrite as `WHERE created_at BETWEEN '2024-01-01' AND '2024-12-31'`.
>
> Second, if the optimizer estimates that the query matches more than ~30% of rows, it decides
> a full scan is faster than random index lookups. This happens when a column has low cardinality —
> like `status` with only 3 values. If 40% of orders have status='pending', the optimizer says
> 'just scan the table, it's cheaper than 40% of rows via random reads.'
>
> Third, a missing composite index where we have separate indexes. If I have `idx(user_id)` and
> `idx(status)` separately, a query `WHERE user_id = 42 AND status = 'pending'` may only use one
> of them, then filter the other in memory. A composite index `(user_id, status)` handles both
> in one traversal.
>
> I'd run `EXPLAIN` to see which index is being used and why, and `SHOW INDEX FROM orders` to
> see cardinality. If the query touches many columns, I'd consider a covering index so the entire
> query is served from the index without touching the table at all."

---

## PART 7 — INDEX ANTI-PATTERNS

```
1. Index on every column
   "Let's just index everything!"
   Problem:
   → Every INSERT requires updating all indexes
   → 10 indexes on a table = 10x write amplification
   → Index data can exceed table data in size
   → Rule: index columns that appear in WHERE, JOIN ON, ORDER BY, GROUP BY

2. Duplicate indexes
   CREATE INDEX idx_a ON t(col1);
   CREATE INDEX idx_b ON t(col1, col2);
   → idx_a is redundant — idx_b already covers single-col queries on col1
   → MySQL doesn't auto-deduplicate — you have to find and drop duplicates

3. Function in WHERE on indexed column
   WHERE LOWER(email) = 'alice@x.com'     ← index on email not used
   Fix: store email already lowercased, or use functional index:
   CREATE INDEX idx_email_lower ON users((LOWER(email)));  ← MySQL 5.7+

4. Index on boolean / low-cardinality column alone
   WHERE is_deleted = false               ← 95% of rows match → useless
   Fix: use as second column in composite: (status, is_deleted)

5. Too many covering indexes
   Covering indexes are wide (store extra columns) → larger index = more RAM needed
   → Add columns to covering index only for your most critical hot queries
```

---

## QUICK REFERENCE CARD

```
┌─────────────────┬─────────────────┬──────────────────────┬──────────────────┐
│ Index Type      │ Supports        │ Does NOT support     │ Best for         │
├─────────────────┼─────────────────┼──────────────────────┼──────────────────┤
│ B-Tree          │ =, >, <, BETWEEN│ Suffix LIKE ('%abc') │ General purpose  │
│ (default)       │ LIKE 'abc%'     │ Functions on column  │ 95% of cases     │
│                 │ ORDER BY        │                      │                  │
├─────────────────┼─────────────────┼──────────────────────┼──────────────────┤
│ Hash            │ = only          │ Ranges, ORDER BY     │ Exact match on   │
│                 │ O(1) lookup     │                      │ high-cardinality │
│                 │                 │                      │ (email, token)   │
├─────────────────┼─────────────────┼──────────────────────┼──────────────────┤
│ Composite       │ Left-prefix     │ Non-left columns     │ Multi-column     │
│ (multi-col)     │ combinations    │ alone                │ WHERE clauses    │
│                 │ ORDER BY cover  │                      │ Order matters!   │
├─────────────────┼─────────────────┼──────────────────────┼──────────────────┤
│ Covering        │ Entire query    │ N/A (it's a strategy)│ Hot read queries │
│ (includes all   │ from index only │                      │ no table fetch   │
│  SELECT cols)   │ no table read   │                      │                  │
└─────────────────┴─────────────────┴──────────────────────┴──────────────────┘

Order of columns in composite index:
  1. Equality columns first (=)
  2. Range columns last (>, <, BETWEEN, LIKE 'x%')
  3. Columns in ORDER BY last (to avoid filesort)
  4. Higher cardinality first within equality group (more selective = better)
```

---

## WHERE THIS PATTERN APPEARS IN YOUR SYSTEM DESIGN INTERVIEWS

> **For the 2-year developer:** Every system design has a database, and every database question eventually leads to "how do you make that query fast?" — index type selection is how you answer it precisely.

| System | Why This Pattern Is Needed Here |
|--------|----------------------------------|
| **01 — Tiny URL** | Hash index on the short_code column — pure equality lookup (WHERE short_code = 'abc123') runs in O(1). B-tree would be O(log N). At 1 billion URLs and 100K QPS redirects, hash index is the obvious choice since no range scans on short_code are ever needed. |
| **05 — Social Media (Instagram/Facebook)** | Composite B-tree index on (user_id, created_at DESC) for the user timeline. Left-prefix rule: this single index serves both "all posts by user X" and "posts by user X after date Y" — avoiding a separate index for each query shape. |
| **09 — E-Commerce** | Covering index on (category_id, price, product_id). All three columns live in the index — the query engine never touches the table heap. EXPLAIN output shows "Using index" instead of "Using index; Using where" with a heap fetch. |
| **14 — Proximity Search** | Spatial index (R-Tree in MySQL, GiST in PostgreSQL) for geospatial queries. B-tree only sorts on one dimension — it cannot efficiently answer "find all restaurants within 5km of latitude X, longitude Y." Spatial indexes partition 2D space and answer this in O(log N + K). |

**Architect's one-liner for the interview:**
*"Choose the index type by the shape of your query: hash for exact equality, B-tree for range and sort, composite for multi-column filters, spatial for 2D coordinates — never just add an index and hope."*
