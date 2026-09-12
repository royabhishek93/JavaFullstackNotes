# Index Types — B-Tree vs Hash vs Composite vs Covering Index — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 15 of 29

## HOOK (0:00–0:30)
So there's a query that's supposed to take 2 milliseconds. It's got an index on `user_id`. Everything looks fine. And in production, it's taking 4 seconds and locking up your connection pool. The index exists. It's just not being *used*. And the reason is something almost every engineer with an index on every table has gotten wrong at least once: not every index is the same, and picking the wrong one — or the wrong column order — silently turns your "fast" query into a full table scan.

[Screen cue: Terminal showing `EXPLAIN` output — a blank "Extra" column next to a red "rows: 480,000" highlighted]

## THE PROBLEM (0:30–2:00)
Think about it this way. A database index is exactly like the index at the back of a 500-page textbook. No index — you flip through every single page looking for "connection pooling." That's a full table scan. That's O(N). Slow, and it gets slower the bigger the book gets.

Now the book has an index: "connection pooling → page 247." You jump straight there. That's O(log N) or even better.

But here's the thing — a back-of-book index only works one way: alphabetical, sorted. What if you wanted to search by "which pages mention a number between 200 and 300"? Different index shape, different structure needed. What if you wanted an *exact* topic match, instant, no scanning at all? Different structure again.

That's the whole story of database indexes. There isn't one index type. There's B-Tree, there's Hash, there's Composite for multiple columns, there's Covering for skipping the table entirely. And engineers who default to "just add an index" without knowing which kind — that's how you get a table with ten indexes, each one slowing down every write, and queries that still don't go fast.

[Screen cue: Split screen — left side "500-page book, no index, O(N)"; right side "Book with index, O(log N)" with a magnifying glass jumping straight to a page]

## THE SOLUTION (2:00–5:00)
Let's go through every index type, one at a time, and I want you to notice: each one answers a *different kind of question*.

**First — B-Tree. This is your default. 95% of the indexes you will ever create are B-Trees.**

It's a balanced tree. Each node holds a sorted range of values, pointing down to child nodes, and the leaf nodes — the bottom level — are doubly linked to each other in sorted order.

Now watch what happens when you query it. `WHERE age = 25` — the tree walks down in O(log N) and finds it. `WHERE age BETWEEN 20 AND 35` — same thing, O(log N) to find 20, then it just walks the linked chain of leaf nodes until it passes 35. That's O(log N + K). Even `WHERE age > 30` works the same way. And if you say `ORDER BY age ASC` and your index is on age — free sort, zero extra work, because the leaf nodes are *already* sorted.

But — `WHERE name LIKE 'Abh%'`, starts-with, still works, O(log N). `WHERE name LIKE '%bhi'` — ends-with — that's a full scan. Can't use a sorted tree to find something in the *middle* or *end* of a string. And `WHERE age != 25` — full scan too, usually.

**Second — Hash Index.** Different data structure entirely. Instead of a tree, it's a hash map: `hash(key) → row pointer`. `hash('alice@x.com')` gives you a bucket number, you jump straight to that bucket. O(1). One computation, one lookup. Done.

But it only does equality. `WHERE email = 'alice@x.com'` — O(1), fastest possible. `WHERE age > 30`? Can't do it — a hash gives you zero ordering information. No ranges, no ORDER BY, nothing. And here's a fact most engineers don't know: MySQL's InnoDB engine — the one basically everyone uses — doesn't even let you *create* a hash index explicitly. It has something called an Adaptive Hash Index that it builds internally, automatically, for hot B-tree pages. You don't control it. PostgreSQL does support explicit hash indexes. But the practical rule almost everywhere: don't bother choosing hash explicitly — B-tree, and let the database's internal optimizations handle the rest.

**Third — Composite Index. Multi-column.** This is where most bugs live, so pay attention.

`CREATE INDEX idx_orders_status_date ON orders(status, created_at)`. Order of columns is not cosmetic — it changes what queries can even use the index. This is the Left-Prefix Rule: MySQL can only use *consecutive* columns starting from the left. If your index is `(status, created_at, user_id)` — a query filtering on `status` alone works. Status plus created_at — works. All three — works. But a query that only filters on `created_at`, skipping status? Doesn't use the index. Only on `user_id`, skipping the first two? Doesn't use it either. The index stops at the first column missing from your WHERE clause.

Then there's the Column Order Rule: equality columns go first, range columns go last. Why? Because MySQL stops using the index the moment it hits a range condition. So if your index is `(created_at, status)` — created_at first — and your query does `WHERE status = 'pending' AND created_at > '2024'`, MySQL uses created_at for the range, then has to manually filter status afterward. Flip it: `(status, created_at)` — status equality first — now MySQL narrows by status, *then* range-scans within that narrowed set on created_at. Same two columns, same query — completely different performance because of order.

**Fourth — Covering Index.** This one's a trick, not a structure. A covering index contains *every column your query needs* — so the database never has to go touch the actual table row at all.

[Screen cue: Live diagram — draw a B-Tree with 3 branches, then redraw it as a hash bucket map, then redraw as a 3-column composite index with arrows showing left-prefix, then finally draw a covering index leaf node containing extra payload columns]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)
Let's talk about the covering index mechanic properly, because this is the one that gets asked in every senior interview.

Normal index lookup: `SELECT name, email FROM users WHERE age = 25`. Index on `age` finds three row IDs — 4521, 8033, 9901. Then for *each one*, the database does a separate trip to the table heap — a "bookmark lookup" — three random disk reads. Now build `CREATE INDEX idx_covering ON users(age, name, email)`. Same query. The leaf node of the index *already contains* name and email alongside age. No trip to the table. Zero random reads. And you can literally see this in `EXPLAIN` — without the covering index, the Extra column is blank, meaning it went to the table. With it, Extra says "Using index" — that's the tell. If it says "Using index; Using where" with a table fetch, you're not covered.

Now — the anti-patterns. Every single one of these I've watched a real team hit in production.

**One — indexing every column.** "Let's just index everything, can't hurt, right?" It can. Every INSERT or UPDATE has to update *every* index on that table. Ten indexes means ten times the write amplification. And index storage can literally exceed your table's own data size. The rule: only index columns that show up in WHERE, JOIN ON, ORDER BY, or GROUP BY. Nothing else.

**Two — duplicate indexes.** `idx_a` on `(col1)`, and separately `idx_b` on `(col1, col2)`. `idx_a` is dead weight — `idx_b` already covers every query that only needs col1, because of the left-prefix rule. MySQL will *not* warn you or auto-drop it. You have to go find these yourself with `SHOW INDEX`.

**Three — a function wrapped around your indexed column.** `WHERE LOWER(email) = 'alice@x.com'` — the index on `email` is dead. The B-tree is sorted by the raw value, not by `LOWER(email)`. Same thing with `WHERE YEAR(created_at) = 2024` — completely ignores an index on `created_at`. The fix is either store the value pre-normalized, rewrite as a range — `created_at BETWEEN '2024-01-01' AND '2024-12-31'` — or in MySQL 5.7-plus, build a functional index directly: `CREATE INDEX idx_email_lower ON users((LOWER(email)))`.

**Four — indexing a low-cardinality boolean alone.** `WHERE is_deleted = false` when 95% of your rows match. The optimizer looks at that and says: an index here is *useless*, I'd rather just scan the table. And that ties into a number you need to remember for interviews: MySQL's optimizer has roughly a **30% threshold**. If it estimates a query is going to match more than about 30% of the table's rows, it will choose a full scan over random index lookups — because random reads at that volume are actually *more expensive* than a sequential scan. This is exactly why an index on `status` with only three possible values, where 'pending' is 40% of your orders, gets silently ignored. Fix: use the boolean as the *second* column in a composite index, like `(status, is_deleted)`, not alone.

**Five — too many covering indexes.** Covering indexes are wide by design — they carry extra payload columns beyond the key. That means bigger index size, more RAM needed to keep it cached. Only build covering indexes for your genuinely hot, high-traffic queries. Don't cover everything "just in case."

[Screen cue: Comparison table on screen — B-Tree, Hash, Composite, Covering — columns: "Supports", "Does NOT support", "Best for", pulled straight from the quick reference card]

## REAL WORLD (8:00–9:30)
Let's map this to systems you've actually used.

Think **Zomato or Swiggy** — proximity search, "restaurants within 5km." A plain B-tree only sorts on *one* dimension. It cannot efficiently answer a two-dimensional "near me" query. That's why geospatial systems use spatial indexes — R-Tree in MySQL, GiST in PostgreSQL — partitioning 2D space so a nearby-restaurant query resolves in O(log N + K) instead of scanning the whole restaurants table.

Think a **Flipkart or Meesho-style product listing page** — filtering by category, sorting by price. That's the textbook use case for a covering index: `(category_id, price, product_id)`. All three columns live directly in the index, so under load — thousands of concurrent listing-page requests — the query engine never touches the table heap. In `EXPLAIN`, you see "Using index," not "Using index; Using where" with a heap fetch per row.

Think a **PhonePe or Paytm-style URL shortener** or referral-code lookup — pure equality, `WHERE short_code = 'abc123'`. At a billion codes and 100,000 queries per second on redirects, a hash index's O(1) beats a B-tree's O(log N) — no range scans ever needed on that column, so there's zero reason to pay for tree traversal.

And the social feed pattern — think an **Instagram-style or a Facebook-style timeline** — composite B-tree on `(user_id, created_at DESC)`. Left-prefix rule means this *single* index serves both "all of user X's posts" and "user X's posts after date Y" — one index, two query shapes, instead of building and maintaining a separate index for each.

[Screen cue: Four logos in sequence — Zomato/Swiggy, Flipkart, PhonePe, Instagram-style feed icon — each with a one-line latency/scale stat overlay]

## OUTRO + NEXT EPISODE (9:30–10:00)
So next time someone tells you "just add an index," ask them *which kind*, and ask them what order the columns go in — because now you know that's the difference between a 2-millisecond query and a 4-second outage. If this helped you actually understand `EXPLAIN` output for the first time, hit subscribe — this is a full system design interview series, and we're only on episode 15 of 29.

Next episode: 016 — Elasticsearch vs PostgreSQL full-text search. If you've ever wondered why your `LIKE '%keyword%'` search is crawling and whether you actually need Elasticsearch or if Postgres can do it — that's next. See you there.

[Screen cue: End card — "Episode 16: Elasticsearch vs PostgreSQL Full-Text Search" with subscribe button animation]
