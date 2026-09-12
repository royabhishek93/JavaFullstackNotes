# LRU vs LFU vs FIFO — When Flipkart Big Billion Day Needs LFU
> **Topic:** LRU Cache | **Level:** Senior Trap | **Frequency:** High

## The Setup

Flipkart runs a Big Billion Day sale. One specific product — a flagship phone — receives 10x the normal traffic for 6 hours, then returns to baseline. Redis is configured with `allkeys-lru`. Your cache hit rate drops to 60% during the sale window. The on-call engineer suggests switching to `allkeys-lfu`.

## The Question

Why is LRU underperforming here? Would switching to `allkeys-lfu` fix it? What are the trade-offs between LRU, LFU, and FIFO — and when does each win?

## Diagram

```
LRU FAILURE ON BIG BILLION DAY
================================
  Flagship phone entry: last accessed 8 seconds ago (constant hammering)
  Random stale key:     last accessed 6 seconds ago (single lookup by a bot)

  LRU eviction candidate = flagship phone  ← WRONG
  LRU only tracks WHEN, not HOW OFTEN

LFU PROTECTION
===============
  Flagship phone:  frequency score = 500,000 accesses
  Random stale key: frequency score = 1 access

  LFU eviction candidate = random stale key  ← CORRECT
  LFU protects the permanent hot item

FREQUENCY POLLUTION — LFU'S WEAKNESS
=======================================
  Viral news article from yesterday: frequency score = 300,000 (trend is OVER)
  Fresh trending article today:      frequency score = 200 (just went viral)

  LFU evicts fresh article  ← WRONG
  The stale high-frequency ghost blocks the new hot item

  Redis LFU fix: logarithmic frequency decay over time
  Counter decays when key is NOT accessed — old counts fade out
```

## Model Answer (15 YOE)

"During the sale, the flagship phone's cache entry is accessed constantly — it should never be evicted. But LRU only tracks *when* something was last accessed, not *how often*. If any other key is accessed once more recently than the phone (even a single stale lookup by a bot or a crawler), LRU may rank the phone as older and evict it under memory pressure.

LFU tracks access frequency. The flagship phone with 500,000 accesses has a frequency score that protects it from eviction even if it was not accessed in the last 10 seconds.

**When LFU beats LRU:** Stable hot-spot workloads — product catalog pages for popular SKUs, celebrity profile pages, global configuration keys. Items that are genuinely 'always hot' need frequency protection, not just recency protection.

**When LRU beats LFU:** Bursty, shifting workloads — news articles, trending tweets, live match commentary. A story trending for 20 minutes needs to enter the cache fast and get evicted once the trend fades. LFU under-evicts it because the high frequency count persists long after the burst ends. This is called **frequency pollution** — stale high-frequency items block fresh popular items from staying cached.

**Redis nuance:** Redis LFU (`allkeys-lfu`) uses a decay mechanism: frequency counters decay logarithmically over time. This mitigates frequency pollution but does not eliminate it.

**For Big Billion Day:** A hybrid approach often works best — switch to `allkeys-lfu` during the sale window (at deploy time), revert to `allkeys-lru` afterward. Or provision a dedicated Redis cluster for sale-time hot keys."

**Decision table:**

| | LRU | LFU | FIFO |
|---|---|---|---|
| **Evicts** | Least recently accessed | Least frequently accessed | Oldest inserted |
| **Best for** | Sessions, live feeds, trending content | Product catalog, config keys, DNS | Message queues, write buffers |
| **Weakness** | One-hit wonders evict warm items | Frequency pollution: old hot items block new ones | Ignores access pattern entirely |
| **Redis policy** | `allkeys-lru` | `allkeys-lfu` (added in Redis 4.0) | `noeviction` / TTL-based |
| **Real example** | Zomato session tokens, Twitter timeline | Flipkart bestseller pages, google.com DNS | Write-coalescing before DB flush |

## Why It's a Trap

Most candidates default to LRU for everything and cannot articulate when LFU is the better choice. The Big Billion Day scenario is specifically designed to expose this. The follow-up about frequency pollution tests whether you know LFU's failure mode — candidates who only advocate LFU without mentioning decay and frequency pollution are equally incomplete.

## What NOT to Say

- "Just use LFU, it's always better than LRU" — wrong; LFU has frequency pollution
- "LRU and LFU are basically the same" — they track fundamentally different things
- "Redis doesn't support LFU" — it has since version 4.0 (2017)
- "FIFO is never useful" — it is correct for queue semantics where insertion order matters

## Follow-up

**Q:** The flagship phone's Big Billion Day sale ends. Now its frequency count of 500,000 is stale. How does Redis LFU handle this so the phone does not permanently occupy a cache slot?

**A:** Redis LFU uses a logarithmic decay counter. The counter does not simply increment — it increments probabilistically (harder to increment as the count grows) and decays when the key is not accessed (controlled by the `lfu-decay-time` config, default 1 minute). After the sale ends, the phone key stops being accessed and its frequency counter decays over time. Eventually it falls below the frequency score of newly hot items and becomes an eviction candidate. This is why Redis LFU is practical for real workloads rather than a pure LFU that would never forget historical counts.
