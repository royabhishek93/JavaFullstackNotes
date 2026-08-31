# Which Redis data type should you use to count millions of unique daily visitors with very low memory?

**Type:** Scenario-Based
**Topic:** Redis Architecture — Choosing the Right Specialized Data Type
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
**HyperLogLog** (`PFADD`, `PFCOUNT`). It's a probabilistic data structure purpose-built for counting unique elements using a small, fixed amount of memory (about 12 KB regardless of whether you're tracking thousands or billions of items), trading a small, well-understood margin of error (~0.81%) for massive memory savings compared to a Set.

## Easy Explanation
If you used a Set to track "every unique visitor today," Redis would need to remember *every single visitor ID*, and memory usage grows with every new unique visitor — potentially huge at scale. HyperLogLog is more like a clever estimation trick: it doesn't remember who visited, it just keeps a compact mathematical fingerprint that lets it *estimate* "roughly how many different people were there" using barely any memory at all, no matter how many visitors you've counted.

## Diagram
```
Approach 1: Set (SADD visitor-ids userId)
  memory grows linearly with unique visitors
  10 million unique visitors -> tens/hundreds of MB, and growing

Approach 2: HyperLogLog (PFADD daily-visitors userId)
  memory stays ~12 KB, FLAT, regardless of scale
  10 million unique visitors -> still ~12 KB, estimate accurate to ~0.81% error

  PFADD daily-visitors "user:1" "user:2" "user:3" ...
  PFCOUNT daily-visitors    -> approx unique count, e.g. 9,918,204 (true value ~9,920,000)
```

## Production Example
A news website tracks daily unique readers per article without wanting to store every reader ID forever:

```bash
PFADD unique-readers:article-42 "user:1001"
PFADD unique-readers:article-42 "user:2002"
PFCOUNT unique-readers:article-42        # approximate unique reader count
```

This is ideal for dashboards and analytics widgets ("12.4M unique visitors today") where an approximate number is perfectly acceptable, but you can't justify the memory cost of storing every single visitor ID in a Set just to answer "how many were unique."

## Why Interviewers Ask This
It tests whether a candidate knows Redis offers purpose-built structures beyond the "big four" (String/List/Set/Hash) for specific trade-offs — here, trading exactness for a dramatic and predictable reduction in memory at scale.
