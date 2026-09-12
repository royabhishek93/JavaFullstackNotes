# Interview Guide: Database Indexing (How DBMS Indexing Actually Works Under the Hood)

## 🗣️ The Interview Scenario

> "You have a table with a million rows and no index on a column you frequently filter by. You add an index. Explain, at the storage-engine level, what actually changes — how the data is physically stored before and after, what data structure the index uses, why that data structure specifically, and what happens internally when you insert a new row that doesn't fit in its 'natural' page anymore."

This question separates candidates who've only memorized "indexes make queries faster" from those who understand **why** — via data pages, B+ trees, and the clustered/non-clustered distinction — which is exactly what senior DB-heavy interviews probe for.

## 🏗️ Architect's Explanation (For a New Developer)

Forget indexes for a second. First understand: **the table you see in a query result is a logical illusion.** A DBMS doesn't store your table as a literal grid of rows and columns on disk — it stores rows inside fixed-size **data pages**, and those pages are further mapped onto physical **data blocks** on disk.

Think of it like a library:
- Your **table** is the catalog view you browse.
- A **data page** is a single shelf that can hold a fixed number of books (rows) — commonly **8 KB** in size.
- A **data block** is the actual physical floor space the shelf sits on, managed by the building (the storage system/disk), not by the librarian (the DBMS).

Now, **indexing** solves one problem: *without an index, finding a specific row means scanning every page, every row, until you find it* — that's **O(n)** in the worst case. An index uses a clever, self-balancing tree structure (**B+ Tree**) to bring that down to **O(log n)** for search, insert, and delete.

There are exactly **two categories** of indexing in an RDBMS:
- **Clustered index** — determines the actual physical/logical *order* rows are stored in. There can be only **one** per table (a table can only be sorted one way at a time).
- **Non-clustered index** — a separate lookup structure (also a B+ Tree) that points back to where the actual row lives, without dictating physical row order. You can have **many** of these per table.

Everything else in this topic — page splitting, offset arrays, primary keys as default clustered keys — is really just mechanics supporting these two ideas.

## 📊 Visualize It

**Anatomy of a single 8 KB data page:**

```
┌─────────────────────── Data Page (8192 bytes total) ───────────────────────┐
│ HEADER (96 bytes)        │   DATA RECORDS (8060 bytes)   │  OFFSET ARRAY (36 bytes) │
│ page#, free space,       │   Row1 | Row2 | Row3 | Row4   │  [0]→Row2 [1]→Row4       │
│ checksum, etc.           │   (actual row bytes live here) │  [2]→Row5 [3]→Row3 ...   │
└──────────────────────────┴───────────────────────────────┴──────────────────────────┘
   (offset array = pointers giving a LOGICAL/SORTED order, independent of physical
    insertion order of rows inside the data-records area)
```

**Page splitting when a data page is full (three-order B+ Tree example, page capacity = 3 rows):**

```
BEFORE inserting row "17" (Page-1 already has 19, 25, 30 — FULL):
  Page-1: [19][25][30]

AFTER page split (new Page-2 created, data divided, pointers updated):
  Page-1: [17][19]  ──points to──►  Block-1
  Page-2: [25][30]  ──points to──►  Block-1 (or a different block)

  Index tree updated: leaf pointer for "30" now points to Page-2 instead of Page-1
```

## 🔧 Deep Dive: How It Actually Works

### 1. How Table Data Is Physically Stored
- The DBMS creates and manages **data pages** — commonly **8 KB (8192 bytes)** each.
- Layout of one page: **96 bytes header** (page number, free space, checksum) + **8060 bytes for actual row data** + **36 bytes offset array** (pointers to rows within this page).
- **Worked capacity example from the transcript:** if one row is 64 bytes, then `8060 / 64 ≈ 125` rows fit in a single data page.
- A table with more rows than fit in one page simply gets **more pages** — Page 1, Page 2, ... Page 100, etc. — all managed by the DBMS.
- These data pages are ultimately persisted onto **data blocks**, which are physical storage units on disk — **the minimum amount of data one I/O operation can read or write**, ranging typically from **4 KB to 32 KB** (most commonly also 8 KB).
- **Critical distinction:** the DBMS controls data *pages* (deciding what rows go where), but has **no control over data blocks** — those are managed by the underlying storage system (disk/SSD). The DBMS maintains a **mapping table** of "Page N → Block M" so it always knows where to physically fetch a given page from. Depending on block size relative to page size, one block can hold multiple pages (e.g., a 32 KB block can hold four 8 KB pages).

### 2. What Indexing Actually Is
Without an index, finding a row means the DBMS may have to **iterate every data page and every row within it** — worst case **O(n)**. Indexing exists purely to make search faster than that, and the data structure used is the **B+ Tree**, which provides **O(log n)** time complexity for **search, insertion, and deletion**. ("B" stands for **balanced**.)

### 3. How a B-Tree / B+ Tree Actually Builds Up (worked example)
Key rules for an **M-order B-Tree**: each node can have **at most M children**, and **at most M−1 keys** per node. The transcript walks through a concrete **3-order B-Tree** (each node: max 2 keys, max 3 child pointers):

- Insert `9` → stored alone in the root node.
- Insert `33` → root node now holds `[9, 33]` (still within the 2-key limit).
- Insert `75` → node would need a 3rd key, which breaks the 3-order rule. The **middle value is promoted** to a new parent node: parent becomes `[33]`, with left child `[9]` and right child `[75]`.
- Insert `41` → goes right of 33 (since 41 > 33), landing in the `[75]` node → becomes `[41, 75]` (sorted, still fits).
- Insert `98` → would make the right node `[41, 75, 98]`, breaking the limit → middle value (75) promoted to parent → parent becomes `[33, 75]`, with children `[9] / [41] / [98]`.
- This pattern (**insert in sorted position → if a node overflows past M−1 keys, promote the middle key to the parent, splitting the node**) continues recursively as more values (`214`, `126`, `55`, `72`...) are inserted, occasionally causing the tree to grow a new root when the top-level node itself overflows.

**B+ Tree** is described as essentially identical to a B-Tree, with **one added feature: all leaf nodes are linked to each other** (enabling fast sequential/range scans across leaves).

### 4. How the DBMS Uses B+ Trees for Indexing (connecting the dots)
- The **leaf nodes of the B+ Tree hold the actual indexed column values** — these are the real, current data values.
- The **root and intermediate nodes hold values used only for faster navigation/searching** — these values might not even exist as live data anymore (e.g., if that row was later deleted, the intermediate "routing" value can remain for tree navigation purposes even though the actual leaf-level row is gone).
- Crucially, **each leaf-level key also carries a pointer to the data page** where that row's full record actually lives.

**Worked example (index on `employee_id`):** as rows are inserted with IDs `19, 25, 30, 17, 6, 1, 5`, the B+ Tree is built exactly per the B-Tree insertion rules above, and once fully constructed, the **leaf level ends up perfectly sorted**: `1, 5, 6, 17, 19, 25, 30` — even though rows may have been inserted in a completely different physical order.

### 5. Connecting the Index to the Actual Data Page (the "how does insert decide which page" question)
When a new row is inserted:
1. The DBMS determines the row's correct **logical position** in the B+ Tree (based on the indexed column's value).
2. It looks at the **nearest existing neighbor's page pointer** in the tree — e.g., if inserting `30` and the tree shows `25`'s pointer says "Data Page 1," the DBMS will try to insert `30` into **Data Page 1** as well.
3. It loads that target page (via the page → block mapping) into memory.
4. **If the page has free space** (recall: a page holds a fixed max number of rows, e.g., 3 in the worked example), the new row is inserted directly, and the pointer for the new key is set accordingly.
5. **If the page is full → "page splitting" occurs:** a **new page is created**, the existing page's rows are divided between the old and new page, and **every affected key's pointer in the B+ Tree is updated** to reflect which page now actually holds its data (e.g., after splitting, key `30`'s pointer might change from Page 1 to the newly-created Page 2).
6. Any newly created page also gets registered in the **page → block mapping**.

This page-splitting + pointer-updating process is exactly why indexing has **write overhead**: every insert potentially triggers tree rebalancing, page splits, and pointer updates across multiple structures.

### 6. Clustered vs. Non-Clustered Indexing

**Clustered Index:**
- Defined as: **the order of rows inside the data pages matches the order of the index.**
- Mechanically achieved via the **offset array**: even if rows are physically inserted into a page in arbitrary order (e.g., row order `1, 4, 5, 2` as users inserted them), the **offset array's pointer sequence** is arranged to reflect the sorted index order (e.g., offset slot 0 → row "1", slot 1 → row "2", slot 2 → row "4", slot 3 → row "5") — so traversing via the offset array yields sorted order without physically moving the row bytes.
- **There can be only ONE clustered index per table**, because physical/logical row order can only be organized around one column's ordering at a time.
- **Priority for which column becomes the clustered key:**
  1. If a **primary key** is explicitly defined, the DBMS uses it as the clustered key by default.
  2. If **no primary key exists**, the DBMS **internally creates a hidden, sequentially auto-incrementing column** (guaranteed unique and not null) and uses *that* as the clustered key instead.
  3. If you **later add a primary key** to a table that previously had none, the DBMS must **regenerate the entire B+ Tree structure**, reload and reshuffle rows across data pages, and update all pointers — a potentially expensive operation, since the whole physical ordering basis has changed.

**Non-Clustered Index (a.k.a. secondary index):**
- Built the same way (a separate B+ Tree), but **does not dictate physical row/page ordering** — it's purely a lookup structure that points to wherever the actual row lives (which is governed by the clustered index).
- You can have **many non-clustered indexes per table** (e.g., on `name`, `address`, or any other frequently-queried column, including composite indexes across multiple columns).

### 7. The Overhead of Indexing (why you shouldn't index every column)
Every additional secondary index means:
- An **entirely separate B+ Tree** must be built and maintained for that column — for a table with a million rows, that's a million-node tree *per indexed column*, with real memory cost.
- These trees are themselves stored in **index pages**, which are separately mapped to disk blocks — so you now have index-page-to-block mapping overhead **in addition to** data-page-to-block mapping.
- **Every insert, update, or delete must update the clustered index AND every non-clustered index** — including potential page splits and pointer updates in each of those trees, not just one.

### 8. Putting It All Together — the Full Search Path
When searching for a value using an index, the sequence is:
1. Load the relevant **index page(s)** from their mapped data block(s) into memory.
2. **Traverse the B+ Tree** within those index pages to locate which **data page** holds the target row.
3. Look up that data page's **block mapping** to find its physical block.
4. Load that specific **data block** into memory.
5. Read the actual row data from within that block.

This is exactly why indexing turns an O(n) full-table scan into an O(log n) tree traversal followed by a single direct page/block lookup.

## 🔥 Real Production Incident & Fix

**What broke:** An analytics team added non-clustered indexes on **five** separate columns of a heavily-written `events` table (each meant to speed up a different dashboard filter) without reviewing write-path impact. Within a week, ingestion throughput on the `events` table dropped by roughly 60%, and the ingestion pipeline started falling behind real-time by tens of minutes.

**How it was detected:** Database performance metrics (via `pg_stat_user_tables` / slow query logs) showed insert latency on `events` climbing steadily, while read query latency on the dashboards had improved as expected. The DBA team correlated the regression's start date with the deployment that added the five new indexes.

**Root cause:** Every single insert into `events` now had to update **six B+ Trees** total (one clustered/primary index + five new non-clustered indexes) instead of just one. Each of those five additional trees could independently trigger page splits and pointer updates on every write, multiplying the per-row insert cost roughly six-fold — exactly the overhead problem the "why not index everything" discussion warns about.

**The fix:** The team profiled actual dashboard query patterns and found only **two** of the five new indexes were being used meaningfully; the other three were dropped entirely. For the two that mattered, they converted them into a single **composite (multi-column) non-clustered index** instead of two separate single-column ones, since the dashboard queries always filtered on both columns together — cutting the total number of maintained trees from six back down to two (clustered + one composite non-clustered) and restoring ingestion throughput to its prior baseline.

```
BEFORE (1 clustered + 5 non-clustered indexes):     AFTER (1 clustered + 1 composite non-clustered):
Every INSERT updates 6 B+ Trees ✖ (slow writes)     Every INSERT updates 2 B+ Trees (fast writes)
Ingestion lag: tens of minutes                       Ingestion lag: back to near real-time
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why does the DBMS create a hidden auto-increment column when a table has no primary key, instead of just leaving rows unordered?**
Because a clustered index requires *some* deterministic ordering basis to organize data pages around — without a primary key, there's no natural unique, non-null column to use, so the DBMS manufactures one (a sequential, guaranteed-unique, non-null internal column) purely so the clustered-index mechanism has something concrete to sort and split pages by.

**Q2: What's the real cost of adding a primary key to a table that already has millions of rows and no primary key?**
It's expensive — the DBMS must regenerate the entire B+ Tree structure around the new clustered key, which can mean reloading and reshuffling rows across many data pages and updating every affected pointer, essentially rebuilding the clustered index from scratch rather than just adding a small new structure.

**Q3: Why can a table have only one clustered index but many non-clustered indexes?**
Because a clustered index defines the actual physical/logical storage order of rows via the offset array — rows can only be arranged in one order at a time. Non-clustered indexes don't touch row storage order at all; they're independent lookup trees pointing back to wherever the clustered order has placed the row, so you can layer as many of these pointer-only structures as you need.

**Q4: What triggers a page split, and what's the downstream cost of one?**
A page split is triggered when a data page has no free space left for a new row that needs to be inserted into it (based on the row's position in the sorted index). The cost is a new page being created, existing rows divided between old and new pages, and **every B+ Tree pointer referencing the affected rows/pages being updated** to reflect the new location — plus a new page-to-block mapping entry.

**Q5: Why is the offset array necessary at all — why not just physically re-sort the row bytes in the data page every time?**
Physically re-sorting bytes on every insert would be extremely expensive (shifting large blocks of row data around). Instead, the offset array provides a layer of indirection: a small array of pointers can be reordered cheaply to represent the logical/sorted sequence, while the actual row bytes stay wherever they were physically written, avoiding costly in-place data movement.

**Q6: How does having a non-clustered index on a rarely-updated but frequently-queried column change the read/write tradeoff calculation?**
For a rarely-updated column, the per-insert overhead of maintaining that extra B+ Tree is paid infrequently, while the query speedup (O(log n) instead of O(n) scan) is realized on every read — making it a strongly favorable tradeoff, unlike indexing a column on a high-write-volume table where every insert pays the index-maintenance cost.

## 🔑 Key Takeaway
Say this out loud: **"An index isn't magic — it's a B+ Tree layered on top of your data pages that turns an O(n) scan into an O(log n) tree traversal, and the clustered index (at most one per table, tied to the primary key) physically orders your rows via the page's offset array, while every additional non-clustered index is a separate tree that adds real write-side maintenance cost in exchange for read-side speed."**
