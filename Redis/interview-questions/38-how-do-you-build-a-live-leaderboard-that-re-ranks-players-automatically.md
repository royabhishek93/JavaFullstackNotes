# How do you build a live leaderboard that re-ranks players automatically?

**Type:** Scenario-Based
**Topic:** Redis Core Data Types — Sorted Sets
**Level:** Mid–Senior Interview (5–10+ YOE)

## Direct Answer
Use a **Sorted Set** (`ZADD`). Every player is a member with a numeric score (their game score); Redis automatically keeps all members ordered by score, so updating a score with `ZADD` (or `ZINCRBY`) instantly repositions that player — no manual sorting required.

## Easy Explanation
A Sorted Set is like a leaderboard on a wall where each name tag has a pin showing its score, and the tags are always physically arranged in score order. When someone's score changes, you just move their pin — you never have to re-sort the entire wall yourself; Redis does that automatically every time a score changes.

## Diagram
```
ZADD leaderboard 1500 "alice"
ZADD leaderboard 2200 "bob"
ZADD leaderboard 900  "carol"

leaderboard (auto-sorted ascending by score):
  carol:900 -> alice:1500 -> bob:2200

Player alice scores more points:
ZINCRBY leaderboard 800 "alice"     (alice: 1500 -> 2300)

leaderboard (automatically re-sorted):
  carol:900 -> bob:2200 -> alice:2300     <- alice moved up, no manual re-sort needed

Get bob's rank:                 ZRANK leaderboard "bob"        -> 1  (0-indexed)
Get top 3 players:              ZREVRANGE leaderboard 0 2 WITHSCORES
Get everyone between 1000-2500: ZRANGEBYSCORE leaderboard 1000 2500
```

## Production Example
A mobile game shows a "Top 10 this week" screen and each player's personal rank:

```bash
ZADD weekly-leaderboard 4300 "player:8842"
ZREVRANGE weekly-leaderboard 0 9 WITHSCORES     # top 10 players, highest first
ZRANK weekly-leaderboard "player:8842"           # this player's current rank
ZSCORE weekly-leaderboard "player:8842"          # this player's current score
```

Because Sorted Sets maintain order automatically, no cron job or background "re-rank everyone" batch process is ever needed — every `ZADD`/`ZINCRBY` keeps the structure correctly ordered in real time.

## Why Interviewers Ask This
It checks whether a candidate reaches for the data structure that matches the requirement ("always ranked, always queryable by score range") instead of building leaderboard logic on top of a plain List or a relational table with a manual `ORDER BY` and re-sort step on every update.
