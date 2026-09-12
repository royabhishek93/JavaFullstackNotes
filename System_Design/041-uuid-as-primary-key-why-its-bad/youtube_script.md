# UUID as Primary Key: Why It's Bad — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 41

## HOOK (0:00–0:30)

Picture this: your MySQL table has 40 to 50 percent wasted disk space. Not because of bad queries. Not because you forgot to run VACUUM. Because of one single decision you made on day one — the data type of your primary key.

If you've ever used `UUID()` or `gen_random_uuid()` as your primary key in a high-write table, you have — right now, today — a table that's roughly half empty on disk, doing thousands of extra random writes per second that it doesn't need to do. And most engineers don't find out until the table hits tens of millions of rows and inserts start mysteriously slowing down.

[Screen cue: Split screen — left side a clean, tightly-packed grid of blue squares labeled "AUTO_INCREMENT — 95% full", right side a messy, half-empty grid of red squares labeled "UUID — 48% full"]

Today we're going deep into why UUID primary keys quietly wreck your database performance, and exactly what to use instead.

## THE PROBLEM (0:30–2:00)

Let's start with a mental model, no jargon yet. Think about it this way: imagine a filing cabinet with 10 drawers. Each drawer holds papers sorted by number — drawer 1 has papers 1 through 100, drawer 2 has 101 through 200, and so on. Every drawer is packed full, nicely organized.

Now, I hand you a new paper numbered 47. Easy — you go to drawer 1, which already has 100 papers, you pull out 48 through 100, slide 47 into its correct spot, and push everything back in. A bit of work, but predictable.

Now here's the twist. I hand you papers numbered 7a3f-91bc, 2e4d-aa01, f901-3312 — random UUIDs. You have no idea which drawer these belong to. You open some random drawer, it's already full, so now you have to split that drawer into two drawers just to fit one new paper. And you're doing this a thousand times a second.

That — literally — is what happens inside MySQL when your primary key is a UUID.

[Screen cue: Animate the filing cabinet analogy — sequential numbers sliding neatly into the last drawer vs. random UUIDs forcing a drawer to split into two]

Here's why this matters mechanically. MySQL's InnoDB engine uses something called a clustered index for the primary key. That's a fancy way of saying: the primary key value determines the actual physical order rows are stored on disk. It's not just an index that points to data — the primary key *is* the layout of the data.

So if your primary key values arrive in order — 1, 2, 3, 4 — new rows just get appended to the end. Cheap. Predictable. One page write.

But if your primary key values are random 128-bit UUIDs, every single insert has to be slotted into wherever it alphabetically/numerically belongs across the *entire* B-tree — which could be anywhere. That page is probably already full from earlier inserts. So MySQL has to split it.

## THE SOLUTION (2:00–5:00)

Now watch what happens when we walk through both cases side by side, page by page.

**Case 1 — AUTO_INCREMENT (sequential):**

[Screen cue: Draw 3 boxes labeled Page 1, Page 2, Page 3. Page 1 has ids 1–1000, Page 2 has 1001–2000, Page 3 has 2001–3000 and still has room]

A new row comes in with `id = 3001`. MySQL doesn't need to think hard — it just appends to Page 3, which already has space. No reorganization. No cascading updates. O(1) page write, every time, forever, as long as inserts keep increasing.

**Case 2 — UUID (random):**

[Screen cue: Same 3 boxes, but filled with random-looking hex strings, all pages shown as FULL]

A new row comes in with UUID `2b3c4d5e-...`. MySQL looks at the UUID and realizes — based on lexicographic/numeric sort order — this value belongs *inside* Page 1, which is already full. So it does a page split: Page 1 gets cut into two half-full pages, the new value slots into the right one, and the parent B-tree node has to be updated to point at both new pages. If the parent node is also full, *that* splits too, and the split cascades upward.

At 10,000 inserts per second, that's not an occasional annoyance — that's thousands of page splits per second, each one a random disk write, each one holding a lock while it reorganizes.

Now let's cover every scenario from the source material, one at a time:

**Scenario — fragmentation over time.** After 6 months of UUID inserts, your pages settle at roughly 38–61% full — averaging around 48%. Compare that to AUTO_INCREMENT pages sitting at 90-95% full, with only the last page partially filled. That means: with UUIDs, you need roughly *twice* the disk space to store the same data, a full table scan reads twice as many pages, your buffer pool — the RAM cache for hot pages — wastes half its space on nearly-empty pages, and range queries get slow because logically related rows are physically scattered.

**Scenario — the interview answer.** If an interviewer asks "your schema uses UUID everywhere as primary key, is that a concern?" — here's the architect-level answer: yes. InnoDB clusters by primary key. Random UUIDs mean random insert positions. That causes page splits at high write volume, and it causes long-term fragmentation that hurts both storage and read performance. The fix depends on whether the ID needs to be exposed externally.

[Screen cue: Live-draw a B-tree, showing a page split cascading up to the parent node — animate one page turning into two, with an arrow up to a re-balanced parent]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Let's go through every trap, every anti-pattern, and every edge case engineers hit with this.

**Trap 1 — "I need globally unique IDs, so UUID is my only option."** Wrong. You have three good options here, and picking the wrong one is the single biggest mistake:

- **AUTO_INCREMENT BIGINT** — best when the ID is purely internal and never exposed to clients. Gives you 9.2 quintillion possible IDs. You never run out. Keep a separate `public_id` UUID column, unique-indexed, for anything user- or API-facing, like URLs.
- **ULID** — Universally Unique Lexicographically Sortable Identifier. Structurally, the first part is a timestamp, the rest is randomness. `01ARZ3NDEK` is time-sortable, `TSV4RRFFQ69G5FAV` gives you uniqueness. Because it's time-ordered, new inserts land near the end of the index almost every time — minimal page splits — while still being globally unique with no central counter needed. Great for distributed ID generation.
- **UUID v7** — the newer standard, where the first 48 bits are a millisecond timestamp. It's a drop-in replacement for UUID v4 that sorts almost the same way ULID does, avoiding the random-insert problem. Natively supported in PostgreSQL 17 and MySQL 9.0+.

**Trap 2 — assuming UUID is *always* bad.** It's not. UUID is actually fine when: you're on PostgreSQL using heap storage, which — unlike InnoDB — doesn't cluster by primary key by default, so the random-insert penalty barely applies. It's also fine on low-write tables under roughly 1,000 inserts per second. It's fine when it's a secondary, non-clustered key rather than the primary clustered key. And it's fine when you genuinely need distributed ID generation across multiple databases with no shared counter — think CockroachDB or Spanner, which are specifically engineered to handle UUID-style clustering internally.

**Trap 3 — the foreign key blind spot.** If your UUID primary key is referenced as a foreign key elsewhere, every one of those foreign key lookups becomes a random read too. This one's easy to miss because you're thinking about the primary table's write performance, not realizing the pain propagates to every child table's joins and lookups.

**Trap 4 — mixing up "unique" with "sortable."** UUID v4 gives you uniqueness but zero chronological order. Engineers assume "it's got a timestamp-like feel" — it doesn't. That's precisely why v4 fails at insert locality while ULID and v7 succeed: they deliberately put a timestamp component first.

[Screen cue: Comparison table — columns: AUTO_INCREMENT, ULID, UUID v4. Rows: Insert pattern, Page splits, Fragmentation, Global unique, Expose in URL, Sortable by time, DB support]

Here's the cheat-sheet comparison, straight from the numbers:

| | AUTO_INCREMENT | ULID | UUID v4 |
|---|---|---|---|
| Insert pattern | Sequential | Sequential | Random |
| Page splits | Almost never | Almost never | Constant |
| Fragmentation | Minimal | Minimal | High (40-50%) |
| Global unique | No (per DB) | Yes | Yes |
| Expose in URL | No (guessable) | Yes | Yes |
| Sortable by time | Yes | Yes | No |

Bottom line rule to memorize: internal-only IDs get AUTO_INCREMENT BIGINT. External IDs in a distributed system get ULID or UUID v7. Never use UUID v4 as your MySQL clustered primary key once you're at scale.

## REAL WORLD (8:00–9:30)

Let's ground this in real systems, the kind you'd see in Indian tech interviews.

Think about a **Swiggy or Zomato**-style order system. Millions of order rows get inserted daily, and during lunch and dinner rush, that's a serious sustained write load. If `order_id` were a raw UUID v4 primary key, you'd be looking at constant B-tree page splits during peak hours — exactly when you can least afford extra latency. The fix: BIGINT AUTO_INCREMENT as the clustered primary key for write locality, with a separate indexed `public_id` UUID column exposed through the API and app URLs.

Now think about a **flash-sale scenario**, like a Flipkart Big Billion Days or an e-commerce flash sale pushing 10,000-plus orders per second at peak. With sequential BIGINT primary keys, every single one of those inserts lands on the rightmost leaf page of the B-tree — zero fragmentation, zero page splits, even under that kind of load. Swap in UUID primary keys, and those same 10,000 inserts per second scatter randomly across the entire index tree, splitting pages constantly, right when your system is under the most pressure it will ever see.

And for something like a **PhonePe or UPI-style payment ledger**, or a stock-trading system processing trades at microsecond intervals — UUID primary keys don't just hurt writes, they thrash your buffer pool. Because "hot" recently-written pages get scattered across the whole index instead of staying clustered at the tail, your RAM cache hit rate drops, and reads that should be fast start hitting disk. A sequential trade ID, or ULID, keeps that working set clustered in the rightmost pages, keeping your buffer pool hit rate high.

[Screen cue: Show three company-style logos/mockups — an orders app, a flash-sale checkout screen, a payment ledger UI — each annotated with the relevant number: "10K+ orders/sec", "40–50% fragmentation avoided", "buffer pool hit rate"]

## OUTRO + NEXT EPISODE (9:30–10:00)

So here's your one-liner for the interview, memorize this: "UUID v4 as a clustered primary key trades write locality for global uniqueness — at 10,000 inserts per second that tradeoff costs you 40 percent index fragmentation. Use a sequential BIGINT primary key, and expose UUID only at the API boundary."

If this saved you from a production incident — or a rough interview moment — hit subscribe, because next episode we're tackling something every senior engineer gets asked about eventually: episode 42, long-tail latency and why your p99 is always worse than you think. See you there.
