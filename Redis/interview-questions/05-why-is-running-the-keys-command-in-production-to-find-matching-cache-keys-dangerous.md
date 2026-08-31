# Why is running the KEYS command in production to find matching cache keys dangerous?

**Type:** Trap Question
**Topic:** Redis Caching Patterns — Production Safety
**Level:** Senior Interview (8–12+ YOE) — common gotcha

## Direct Answer
Because `KEYS pattern` scans the **entire keyspace** in one blocking operation — on a large production dataset with millions of keys, this can freeze the Redis server for other clients for seconds, causing a cascading latency spike or even an outage. The safe alternative is `SCAN`, which iterates the keyspace incrementally in small batches without blocking.

## Easy Explanation
`KEYS` is like asking a librarian to stop everything and personally check every single book in a massive library, right now, before helping anyone else — while they're doing that, no other customer gets served. `SCAN` is like asking the librarian to check a handful of shelves at a time, between helping other customers, so the library never grinds to a halt just to answer your one search.

## Diagram
```
Redis with 10 million keys

KEYS user:*
        |
        v
  Redis is SINGLE-THREADED for command execution
  it must scan ALL 10 million keys before returning ANY answer
        |
        v
  every other client's command is BLOCKED and waits    <- production outage risk

SCAN 0 MATCH user:* COUNT 100
        |
        v
  returns a small batch + a cursor, e.g. cursor=848
  other clients' commands continue to be served in between calls
        |
        v
  repeat SCAN 848 MATCH user:* COUNT 100 ... until cursor returns to 0
  (fully non-blocking, safe on a live production instance)
```

## Production Example
An engineer, trying to debug a caching issue, ran `KEYS session:*` directly against a production Redis instance holding tens of millions of session keys. The entire application experienced a multi-second latency spike across every service using that Redis instance, because every other command queued up behind the single blocking `KEYS` scan.

```bash
# DANGEROUS in production
KEYS session:*

# SAFE — incremental, non-blocking
SCAN 0 MATCH session:* COUNT 100
```

## Why Interviewers Ask This
It's one of the most common "looks harmless, causes an outage" Redis mistakes. This question checks whether a candidate has hands-on production experience and instinctively reaches for `SCAN` over `KEYS` on any non-trivial dataset.
