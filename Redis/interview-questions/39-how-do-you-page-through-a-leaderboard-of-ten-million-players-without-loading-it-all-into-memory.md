# How do you page through a leaderboard of ten million players without loading it all into memory?

**Type:** Advanced Scenario-Based
**Topic:** Redis Core Data Types — Sorted Sets at Scale
**Level:** Staff Interview (12–15+ YOE)

## Direct Answer
Use range-based queries with explicit offsets — `ZREVRANGE key start stop` or, for very large sets, cursor-based iteration with `ZSCAN` — instead of ever calling a "give me everything" command. Fetch only the slice you need (e.g., 50 players at a time), and combine with `ZRANK`/`ZREVRANK` to jump directly to "show me the 50 players around *this* user's rank" without scanning from the top.

## Easy Explanation
Never ask Redis "give me the entire ten-million-name leaderboard" — that's like asking a librarian to hand you every book in the building at once. Instead, ask for a *page*: "give me ranks 0 through 49," then later "give me ranks 50 through 99." Sorted Sets support this natively and efficiently because they're stored as an ordered structure internally — fetching a slice by rank or by score range doesn't require scanning everything before it.

## Diagram
```
10,000,000-member leaderboard

BAD:  ZRANGE leaderboard 0 -1          <- fetches ALL 10 million members, huge payload

GOOD: paginate in fixed-size windows
  Page 1: ZREVRANGE leaderboard 0   49   WITHSCORES   (ranks 1-50)
  Page 2: ZREVRANGE leaderboard 50  99   WITHSCORES   (ranks 51-100)
  Page 3: ZREVRANGE leaderboard 100 149  WITHSCORES   (ranks 101-150)

"Show me around player X":
  1. ZREVRANK leaderboard "player:X"        -> e.g. 3,482,910
  2. ZREVRANGE leaderboard 3482885 3482935  -> the 50 players surrounding X
     (jump straight to their neighborhood, no need to page from rank 0)
```

## Production Example
A season-long leaderboard with millions of players shows a "your rank + nearby competitors" widget instead of a full list:

```bash
ZREVRANK season-leaderboard "player:8842"          # e.g. returns 204993
ZREVRANGE season-leaderboard 204968 205018 WITHSCORES   # 25 players above and below
```

For bulk export/analytics jobs that genuinely need to walk the whole structure without blocking Redis, `ZSCAN` is used instead of `ZRANGE 0 -1`, because it iterates incrementally in small batches rather than returning everything in one giant response.

## Why Interviewers Ask This
It distinguishes engineers who've only used small demo datasets from those who've operated Sorted Sets at real scale, where "just fetch everything" becomes a memory and latency problem, and where rank-relative queries (not just top-N) are a common real feature request.
