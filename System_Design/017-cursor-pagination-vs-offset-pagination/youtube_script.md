# Cursor-Based Pagination vs Offset Pagination — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 17 of 29

## HOOK (0:00–0:30)

[Screen cue: title card — "page=10000 — why does this simple request take 8 seconds?"]

Picture a library with 1 million books, all sorted by title. A customer walks up and says, "I want books number 500,001 through 500,010."

The offset librarian starts at book one, counts every single book — 1, 2, 3... all the way to 500,000 — throws all of them aside, and hands you the next 10. That librarian just did 500,000 units of pointless work to give you 10 books.

The cursor librarian does something smarter. You hand them a bookmark from last time — "I left off right after 'Goblet of Fire.'" They walk directly to that shelf and hand you the next 10 books. Zero wasted work.

[Screen cue: stat overlay — "100 users request page=50000 → 50,000,000 rows scanned → 1,000 rows returned → DB CPU at 100% → 5–30 second latency"]

That's not a hypothetical. That's `LIMIT 10 OFFSET 500000` running for 100 concurrent users. And if your API uses `page` and `offset` instead of a cursor, you already have this bug in production — you just haven't hit page 50,000 yet. Let's fix that.

## THE PROBLEM (0:30–2:00)

[Screen cue: SQL snippet — `SELECT * FROM products ORDER BY created_at DESC LIMIT 10 OFFSET 20;`]

Here's how almost everyone builds pagination first: `page=3&limit=10` translates to "skip the first 20 rows, give me the next 10" — `LIMIT 10 OFFSET 20`. Simple to write, simple to reason about. The problem is what the database has to physically do to satisfy that OFFSET.

[Screen cue: diagram — "OFFSET 20 → scan 30 rows → discard 20 → return 10"]

For `OFFSET 20`, MySQL scans rows 1 through 30, throws away the first 20, and returns the last 10. That's 30 rows scanned for 10 returned — 20 rows of pure waste. Annoying, but survivable.

[Screen cue: diagram — "OFFSET 500000 → scan 500,010 rows → discard 500,000 → return 10"]

Now watch what happens at `OFFSET 500000`. MySQL scans rows 1 through 500,010, discards the first 500,000, and returns the last 10. That's 500,010 rows scanned to return 10 rows. The database worked half a million rows for essentially nothing.

Multiply that by traffic. A hundred users all hitting `page=50000` at the same time — the numbers from the source doc — means roughly 50 million rows scanned in total, to return just 1,000 rows of actual content. Your database CPU pins at 100%, and every one of those queries takes 5 to 30 seconds. And it doesn't stop there — every other query hitting that same database slows down too, because you've saturated the CPU with wasted scan work.

[Screen cue: diagram — feed timeline with 5 new posts inserted between page 1 and page 2]

There's a second problem, and it's worse than slowness — it's *wrong data*. Say a user loads page 1 of a feed and sees posts A through J. While they're reading, 5 new posts get inserted at the top. They tap "next page," which is `OFFSET 10`. But offset counts from the *current* top of the table — so now position 10 lands somewhere completely different. The result: the 5 new posts shift everything down, and the user sees posts A through E *again* — duplicates — before finally reaching the content they actually hadn't seen yet. Offset pagination doesn't just get slow with scale, it gets *incorrect* the moment your data is live and changing.

## THE SOLUTION (2:00–5:00)

[Screen cue: text overlay — "Stop asking 'skip N rows.' Start asking 'give me rows after THIS row.'"]

Cursor pagination flips the question. Instead of "skip N rows from the start," you ask "give me the rows that come after this specific row I already saw." That's the entire mental shift.

[Screen cue: SQL snippet — first request without cursor]

```sql
SELECT id, title, created_at
FROM products
ORDER BY created_at DESC
LIMIT 10;
```

First request has no cursor — you just get the first page. Say the last row returned has `id=4521` and `created_at='2024-01-15 10:30:00'`. The server packages that up — typically as a Base64-encoded string like `created_at:id` — and sends it back to the client as `nextCursor`.

[Screen cue: SQL snippet — second request with cursor and tuple comparison]

```sql
SELECT id, title, created_at
FROM products
WHERE (created_at, id) < ('2024-01-15 10:30:00', 4521)
ORDER BY created_at DESC, id DESC
LIMIT 10;
```

The client sends that cursor back. The query becomes a *tuple comparison*: `WHERE (created_at, id) < (cursor_time, cursor_id)`. Read that as one condition: "give me every row that sorts after this exact point." The `id` tiebreaker matters — `created_at` alone can have duplicate timestamps, so pairing it with a unique, monotonic `id` guarantees a stable, unambiguous ordering.

[Screen cue: diagram — B-tree index, direct seek arrow to position, then walk 10 entries]

Here's why this is fast. With an index on `(created_at DESC, id DESC)`, the database doesn't scan from row 1. It uses the B-tree index to jump *directly* to the entry matching your cursor — that's an O(log N) lookup, the same cost whether N is 10,000 or 10 million. Then it just walks forward 10 entries in the index — O(K) where K is your page size. Total rows touched: about 10. Not 500,010. And this cost is *identical* whether you're on page 1 or page 50,000, because there's no "page number" concept at all — just "start here, walk K steps."

This also kills the duplicate-data bug completely. Go back to the feed example: user's cursor points at post J. Five new posts get inserted at the top — but they all have *newer* timestamps than J. The query `WHERE (created_at, id) < (J's values)` only returns rows *older* than J — so those 5 new posts structurally cannot appear in the next page. No duplicates, no gaps, by construction — not by luck.

[Screen cue: side-by-side API contract comparison]

The API contract changes shape too. Offset pagination returns `page`, `totalPages`, `total` — because "jump to page 47" is a real feature offset supports. Cursor pagination returns `nextCursor` and `hasMore` instead — there's no page number, just "here's your bookmark for the next call, and here's whether there's more."

[Screen cue: brief Java snippet — encode/decode via Base64]

On the Spring Boot side, this is genuinely simple to implement: fetch `limit + 1` rows so you know if there's a next page without a separate count query, encode the last row's `createdAt` and `id` as a Base64 string for `nextCursor`, and decode that same string back into a timestamp and ID on the next request to feed into your `WHERE` clause. The cursor itself is opaque to the client — they just pass it back verbatim.

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

[Screen cue: SQL — `CREATE INDEX idx_posts_cursor ON posts(created_at DESC, id DESC);`]

Mistake number one: shipping cursor pagination *without* the composite index. If you don't have `(created_at DESC, id DESC)` as an actual index, that tuple comparison in your `WHERE` clause falls back to a full table scan — you get all the API complexity of cursors with none of the performance benefit. Always verify with `EXPLAIN` — you want to see `type: range` and `key: idx_posts_cursor` in the output, and you explicitly do *not* want to see `Using filesort`. If you see a full scan, the index is missing or the column order doesn't match your `ORDER BY`.

[Screen cue: text overlay — "Cursor pagination cannot jump to page 42,000"]

Mistake number two: engineers reach for cursor pagination everywhere and then get surprised when product wants "jump to page 47" on an admin screen. Cursor pagination is fundamentally forward-and-backward only — there's no concept of "skip to an arbitrary page" because there's no page number, just a bookmark. If your UI genuinely needs random access to page numbers, cursor pagination is the wrong tool, full stop.

[Screen cue: checklist — "When offset is still correct"]

Which brings us to the trade-off engineers under-appreciate: offset pagination isn't obsolete, it's *situational*. It's still the right call when:
- You're building an admin dashboard where someone genuinely needs to type "page 47" and jump there.
- You cap pagination depth — say, page 100 max — which bounds the worst-case scan and makes the O(N) cost a non-issue in practice.
- Your table is small — under maybe 10,000 rows — where even a full scan is a few milliseconds, so the "waste" is invisible.

[Screen cue: split diagram — "Public feed = cursor | Admin panel = offset with cap"]

The pattern that shows up in almost every real production system is a hybrid: the public-facing, high-traffic, infinite-scroll surface — the feed, the catalog, the order list a customer scrolls through — uses cursor pagination. The internal, low-traffic, "give ops a page number to jump to" admin tool uses offset pagination, capped at a sane maximum page. You're not choosing one pattern for your whole system — you're choosing per endpoint, based on who's calling it and how deep they'll go.

One more subtlety worth calling out: cursor pagination effectively gives up "total count" and "total pages" as cheap operations. `SELECT COUNT(*)` on a huge table is its own expensive query — so most cursor-based APIs simply don't expose a total. If your frontend absolutely needs "showing 1,000,000 results," that's a signal you might want offset — or a separate, cached, approximate count computed out-of-band.

## REAL WORLD (8:00–9:30)

[Screen cue: phone mockup — infinite-scroll social feed]

Think about any infinite-scroll feed — Instagram, or closer to home, a Swiggy or Zomato home feed that keeps loading more restaurants and posts as you scroll. Users are scrolling *while* new content streams in constantly. If that used offset pagination, every insert during your scroll session would shift rows and hand you duplicate cards you already swiped past. Cursor pagination is the only correct choice here — the feed API has no idea what "page 12" even means, it only knows "give me what's older than the last card I sent you."

[Screen cue: e-commerce order history screen]

Now think about order history — Flipkart, or Amazon, showing a business account with 5,000-plus historical orders. A cursor on `(order_date, order_id)` means page 1 and page 250 of that order history both cost a single index seek — identical performance. With offset pagination, digging into page 250 means scanning roughly 5,000 rows just to get there — it degrades linearly the deeper a user digs into their history.

[Screen cue: leaderboard UI — "you + 10 above + 10 below"]

Leaderboards are a great edge case: "show my rank plus the 10 players above and below me." That's a score-based cursor — something like `ZREVRANGEBYSCORE` in Redis — which is O(log N + K) and stays *consistent* even as scores update in real time. An offset-based approach here would visibly drift, because ranks are shifting under your feet between requests — the exact "shifting data" bug from earlier, just in a different data structure.

[Screen cue: OTT app scrolling through video catalog]

And for scale, picture an OTT platform — think Hotstar — with a catalog of 10 million videos. `OFFSET 200000 LIMIT 20` on that catalog scans 200,000 index entries just to get to your page. A cursor on `(created_at, video_id)` does one index seek and returns 20 rows — regardless of whether you're browsing the newest releases or scrolling deep into the archive. Same cost, every time. That's the whole pitch of cursor pagination in one example: performance that doesn't degrade with depth.

## OUTRO + NEXT EPISODE (9:30–10:00)

[Screen cue: quick-reference card recap — offset vs cursor table]

So — the one-liner for your next interview: offset pagination is O(N), because the database has to count N rows from the start every single time. Cursor pagination is O(1) relative to depth, because the cursor *is* the index position — page 1 and page 50,000 cost exactly the same.

Default to cursor pagination for anything public-facing, high-traffic, or backed by live-changing data. Keep offset pagination for capped, low-traffic, jump-to-page admin tools. And always, always back your cursor query with the matching composite index — without it, you've built a slower version of the problem you were trying to solve.

[Screen cue: end card — "Episode 18: The N+1 Query Problem"]

Next episode, we're tackling a bug that hides in almost every ORM-based codebase — one clean-looking line of code that quietly fires a thousand queries instead of one. That's the N+1 query problem, episode 18. Subscribe so you don't miss it, and I'll see you there.
