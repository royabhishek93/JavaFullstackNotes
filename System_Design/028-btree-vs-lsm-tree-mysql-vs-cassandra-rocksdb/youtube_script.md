# B-Tree vs LSM Tree — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 28 of 29

## HOOK (0:00–0:30)

[SCREEN: Bold title card — "Why does MySQL crawl at 50K writes/sec while Cassandra does 500K? It's not the hardware."]

Quick question. If I hand you MySQL and Cassandra, both on identical servers, and I ask you to write half a million rows a second into each one — MySQL is going to choke. Cassandra will barely break a sweat.

[SCREEN: Split screen — "MySQL: ~10K-50K writes/sec" vs "Cassandra: ~100K-500K writes/sec"]

Same CPU. Same disk. Same RAM. So what's actually different? It's not the database — it's the data structure underneath it. One uses a B-Tree. The other uses something called an LSM Tree. And by the end of this video, you'll know exactly which one to reach for in your next system design interview — and why the wrong answer here is one of the fastest ways to lose credibility with a senior interviewer.

---

## THE PROBLEM (0:30–2:00)

[SCREEN: Librarian illustration — bookshelf vs a table by the door]

Let me explain this with a librarian analogy, because this is the one that sticks.

Imagine you're a librarian. Your job: store books, and help people find them fast. You've got two completely different ways to run your library.

[SCREEN: "Option A — B-Tree style" with a tree-of-shelves diagram]

**Option A** — you organize books into a tree of shelves. Everything's sorted. Top shelf is your index — A through Z. Each section has sub-shelves. Someone asks for "Harry Potter"? You go to the index, find "H", go to the H-section, find "Ha", pick up the book. Three steps. Fast.

But here's the catch — when a **new book arrives**, you have to walk to the exact right shelf, and if that shelf is full... you split it. Two shelves now. And you've got to update the parent shelf to point to both. Sometimes that update cascades — three, four, five shelves get reshuffled just to add one book.

[SCREEN: "Option B — LSM Tree style" with a table-by-the-door diagram]

**Option B** — completely different philosophy. New book arrives? You don't reorganize anything. You just drop it on a table by the door. That's your **MemTable**. Once a hundred books pile up, you bundle them into a small sorted package and toss it in the back room — that's your **SSTable**. More books come in, another package goes to the back room. Periodically, you merge small packages into bigger ones in the background — that's **compaction**.

Writing a book here is one step: drop it on the table. Always fast. Finding a book is a bit harder — you might have to check several packages — but you speed that up with a quick "definitely not in here" checker on each package.

[SCREEN: "MySQL = Option A (B-Tree) | Cassandra = Option B (LSM Tree)"]

MySQL is Option A. Cassandra, RocksDB, and LevelDB are Option B. And this one architectural decision ripples through everything — your write throughput, your read latency, your operational headaches, all of it.

---

## THE SOLUTION (2:00–5:00)

[SCREEN: B-Tree diagram — root node, internal nodes, leaf nodes with arrows between leaves]

Let's get concrete. Here's MySQL's InnoDB B-Tree. You've got a root node at the top holding a handful of keys — say 30, 60, 90. Below that, internal nodes that narrow the range further. And at the bottom, leaf nodes that actually hold the data — the rows.

Here's the important detail: those leaf nodes are **doubly linked** to each other. That's what makes range scans fast — "give me everything between id 20 and id 60" — you just find the starting leaf and walk the chain forward. You're not jumping around the tree.

[SCREEN: "O(log N) = 3-4 disk reads for 100 million rows" with page icon "16KB page size"]

And because the tree is always kept balanced, a read is O(log N). For a table with a hundred million rows, that's roughly **4 disk reads** — root, internal, leaf, done. Pages are typically **16KB** each. Predictable, fast, no surprises.

[SCREEN: Page split animation — full leaf splits into two]

Now the write side. Insert a new row, and InnoDB has to find the correct leaf page. If it's full — and it will be, eventually — the page **splits**. One full leaf becomes two half-full leaves. The parent node gets a new pointer. And if the parent is also full... it splits too. That's a **cascading split**, and it means one single insert can trigger multiple random disk writes.

[SCREEN: LSM write path diagram — WAL → MemTable → SSTable L0 → L1 → L2]

Now flip to the LSM Tree. Every write follows the same path: first it's appended to the **WAL** — the write-ahead log — sequentially, for crash durability. Then it's inserted into the **MemTable**, an in-memory sorted structure, usually a red-black tree. That's it. Write acknowledged. Sub-millisecond.

When the MemTable hits a size limit — commonly 64MB — it gets flushed to disk as an **SSTable**: immutable, sorted, never modified again. These pile up at **Level 0**. In the background, a compaction process merges L0 SSTables into L1, then L1 into L2 — bigger, cleaner, fewer files as you go up.

[SCREEN: SSTable with a Bloom Filter icon — "does key X exist? NO → skip. MAYBE → read."]

Here's the trick that makes LSM reads viable: every SSTable carries a **Bloom Filter**. Before touching disk, you ask the Bloom Filter "is this key possibly in here?" If it says no, you skip that file entirely — zero disk reads. If it says maybe, you go read the file. This is how LSM Trees avoid checking every single SSTable on every read.

[SCREEN: Side-by-side — "B-Tree read: 2-4 disk reads" vs "LSM read: 2-5 disk reads, Bloom filters skip most"]

So on reads: B-Tree does 2 to 4 disk reads, always predictable. LSM does 2 to 5 disk reads, but Bloom filters knock out most of the misses so it stays competitive — though range scans still favor B-Tree since LSM data is scattered across levels.

[SCREEN: Side-by-side — "B-Tree write: random I/O + splits" vs "LSM write: sequential append, O(1)"]

On writes, there's no contest. B-Tree write is a random disk read to find the leaf, then a random disk write, plus possible cascading splits. LSM write is a sequential append to a log and an in-memory insert — O(1), constant time, regardless of how much data you already have. Sequential writes are roughly **10x faster** than random writes on both SSD and spinning disk. That's the entire reason Cassandra can do 100K to 500K writes per second while MySQL tops out around 10K to 50K.

---

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[SCREEN: Bold red text — "Compaction is NOT free. It's a hidden cost."]

Here's where most engineers — even senior ones — get burned. They see LSM Trees and think "wow, writes are basically free." They are not free. They're **deferred**.

[SCREEN: Diagram — "WRITE: 1ms (looks free)" → arrow → "COMPACTION: background I/O storm"]

That MemTable flush and the fast write you just saw? The real cost shows up later, in compaction. Compaction has to read all those L0 SSTables, sort-merge them, write a brand new merged SSTable, and delete the old ones. And this isn't a background nicety — in production Cassandra clusters, compaction can consume **30 to 50 percent of your total disk I/O bandwidth**. While it's running, your reads slow down, because disk bandwidth is shared.

[SCREEN: "You need 2x your data size in FREE disk space for compaction"]

And here's the number that catches teams off guard during capacity planning: you need roughly **2x your data size in free disk space** just to run compaction safely — because you're writing the merged file before you delete the old ones. Run your disks near full, and compaction either stalls or fails, and your compaction queue starts growing. If you ever see compaction queue depth climbing in your monitoring, that's a red flag — you're writing faster than you can compact.

[SCREEN: "Size-tiered compaction vs Leveled compaction"]

There are two common compaction strategies, and this is a great thing to drop in an interview. **Size-tiered compaction** merges SSTables of similar size together — it's good for write-heavy workloads but can leave you with large read amplification. **Leveled compaction** keeps SSTables smaller and more organized across levels — better read performance, which is why it's the default in RocksDB.

[SCREEN: "Interviewer trap: secondary index on Cassandra"]

Now, the classic interview trap. You've picked Cassandra for an activity feed. The interviewer says: "What if I need to query all activities where type equals 'comment', across every single user?" The tempting wrong answer is "I'll just add a secondary index on type."

[SCREEN: Red X over "secondary index" / Green check over "push to data warehouse"]

That's wrong, and here's why — say it exactly like this in an interview. Cassandra partitions data by a key across the cluster. A secondary index there is a **distributed index** — every write has to update every node's index, and a query on it still has to scatter to every node in the cluster. It does not behave like a MySQL secondary index at all. The right answer: for cross-partition analytical queries, you push those events through Kafka into a data warehouse — BigQuery, Redshift, Snowflake. Cassandra stays focused on the operational write path; the warehouse handles the aggregations. Two systems, each doing what it's built for.

[SCREEN: B-Tree page split animation repeating — "fragmentation over time"]

One more trap, on the B-Tree side this time. Because pages constantly split under heavy write load, your table fragments over time — pages get scattered across disk, half-empty, and your read performance quietly degrades. The fix is `OPTIMIZE TABLE` or a full index rebuild — and that's an **expensive, often offline operation** on large tables. If your write-heavy MySQL table is degrading over months, this is usually why.

---

## REAL WORLD (8:00–9:30)

[SCREEN: Logos — "RocksDB @ Facebook & TikTok" / "LevelDB inside Chrome's IndexedDB"]

This isn't academic. **RocksDB**, an LSM Tree engine, runs inside Facebook's and TikTok's storage infrastructure at massive scale. **LevelDB**, also LSM-based, is what powers IndexedDB inside every Chrome browser on the planet. Every time a web app caches data locally in your browser, there's a good chance an LSM Tree is under the hood.

[SCREEN: Mapping table — WhatsApp Chat / Payment / Social Feed]

Now map this back to real systems you'd design in an interview. **WhatsApp-style chat** — Cassandra, because you're ingesting around **500,000 messages per second**, append-only, partitioned by chat ID — a textbook LSM workload. **Payment systems** — MySQL, every time, because **ACID is non-negotiable**; you cannot have an eventually-consistent balance. Write volume there is moderate anyway, so B-Tree's read predictability wins. **Social feed** — Cassandra plus Redis: Cassandra absorbs the high-write feed storage, Redis serves the hot, frequently-read feeds out of memory.

[SCREEN: "The pattern: high write throughput + simple model = LSM. ACID + complex queries = B-Tree."]

Notice the pattern across every one of these: when write throughput is the bottleneck and the access pattern is simple — LSM Tree wins. When you need transactions, joins, or complex queries — B-Tree wins. That's the entire decision framework, and you can defend it in one breath in an interview.

---

## OUTRO + NEXT EPISODE (9:30–10:00)

[SCREEN: Bold quote card — the interview one-liner]

If you remember exactly one line from this video, make it this one, because it's the line that separates people who've memorized buzzwords from people who actually get it:

> "LSM Tree moves the write cost from the hot path into background compaction. You're not eliminating I/O — you're deferring it and making it sequential instead of random."

[SCREEN: "Episode 28 of 29 — B-Tree vs LSM Tree ✔"]

That's B-Tree versus LSM Tree — episode 28 of this series.

[SCREEN: "NEXT: Episode 29 — Backpressure & Reactive Streams (Series Finale)"]

Next up is the **final episode** — episode 29, **Backpressure and Reactive Streams**. If storage engines are about how data gets written and read, backpressure is about what happens when your system gets data faster than it can process it, and why blindly buffering everything will eventually take your service down. See you there.

[SCREEN: Subscribe + series playlist link]
