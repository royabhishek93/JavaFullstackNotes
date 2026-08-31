# Why does a manual get-then-increment-then-set lose page view counts under load?

**Type:** Trap Question
**Topic:** Redis Core Data Types — Locking & Atomicity
**Level:** Mid–Senior Interview (5–10+ YOE) — common gotcha

## Direct Answer
Because `GET`, "add one in application code," and `SET` are **three separate steps**, not one atomic operation. Two concurrent requests can both `GET` the same value, both compute the same "+1" in their own memory, and both `SET` the same result — silently losing one of the increments. The fix is Redis's built-in `INCR`, which performs the read-and-write as a single atomic server-side operation.

## Easy Explanation
Imagine two people looking at the same tally counter that reads "10," and each decides to write "11" back on it — because they both read "10" before either one wrote anything. The counter should be "12" (two increments happened), but it ends up at "11" (one increment was lost). `INCR` avoids this entirely because Redis does the read-and-write as one indivisible step, so there's no gap where two requests can both see the same starting number.

## Diagram
```
UNSAFE (GET + application add + SET):
Request 1                    Redis                     Request 2
  GET views  ------------->  "10"
                                                    GET views ------------> "10"
  (app computes 10+1=11)
  SET views 11 ----------->  views = 11
                                                (app computes 10+1=11)
                                            SET views 11 ------------->  views = 11

Result: TWO requests happened, but views only went from 10 -> 11.  One increment LOST.

SAFE (INCR):
Request 1                    Redis                     Request 2
  INCR views --------------> views: 10 -> 11 (atomic)
                                                   INCR views -------------> views: 11 -> 12

Result: views correctly ends at 12.
```

## Production Example
```java
// WRONG — race condition under concurrent traffic
String current = redisTemplate.opsForValue().get("views:article:42");
int next = Integer.parseInt(current) + 1;
redisTemplate.opsForValue().set("views:article:42", String.valueOf(next));

// RIGHT — atomic on the Redis server, safe under any concurrency
redisTemplate.opsForValue().increment("views:article:42");
```

This exact bug is a classic cause of "our analytics dashboard undercounts traffic" tickets — it usually only shows up under real concurrent load, which is why it slips past casual testing.

## Why Interviewers Ask This
It's a fast way to check whether a candidate reflexively reaches for Redis's atomic primitives (`INCR`, `INCRBY`, `HINCRBY`) instead of re-implementing read-modify-write logic in application code, where race conditions are easy to introduce and hard to notice in a code review.
