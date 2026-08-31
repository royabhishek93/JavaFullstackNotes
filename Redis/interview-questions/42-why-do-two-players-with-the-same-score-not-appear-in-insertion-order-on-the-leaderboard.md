# Why do two players with the same score not appear in insertion order on the leaderboard?

**Type:** Trap Question
**Topic:** Redis Core Data Types — Sorted Sets
**Level:** Mid–Senior Interview (5–10+ YOE) — common gotcha

## Direct Answer
Because Sorted Sets break score ties **lexicographically by member name**, not by insertion order. If two players have the exact same score, Redis orders them alphabetically by their member string, which can look surprising if you expected "whoever reached that score first" to rank higher.

## Easy Explanation
A Sorted Set's *only* promise is: order by score. It never remembers "who got there first." When two members tie on score, Redis needs *some* deterministic secondary rule to keep ordering consistent — it picks alphabetical order of the member name as that tiebreaker, which has nothing to do with when each member was added.

## Diagram
```
ZADD leaderboard 100 "zoe"
ZADD leaderboard 100 "alice"

You might expect "zoe" first (added first), but:

ZRANGE leaderboard 0 -1 WITHSCORES
  1) "alice"   -- 100
  2) "zoe"     -- 100

Tie broken alphabetically ("alice" < "zoe"), NOT by insertion order.
```

## Production Example
A trivia game shows "who answered fastest" using a Sorted Set scored by points. Two players who both scored exactly 500 points appeared in an order the product team assumed reflected "who got there first" — but it was actually just alphabetical. The real fix was encoding tie-breaking directly into the score itself, for example combining points with a timestamp so ties are naturally broken by time, not by name:

```bash
# score = points * 10,000,000,000 - timestamp_ms
# higher points always win; among equal points, earlier timestamp wins
ZADD leaderboard 5000000001695000000 "player:8842"
```

## Why Interviewers Ask This
It's a subtle but common real bug: teams assume Sorted Sets preserve "arrival order" as a tiebreaker, when in fact the only reliable tiebreaker is the member name itself. This question checks whether the candidate knows to encode any secondary ordering requirement directly into the score.
