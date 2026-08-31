# Can XTRIM delete a stream entry that a consumer group has not processed yet?

**Type:** Trap Question
**Topic:** Redis Streams — Retention & Data Safety
**Level:** Senior/Staff Interview (12+ YOE) — common gotcha

## Direct Answer
**Yes — and Redis will not stop you.** `XTRIM` (and `MAXLEN`/`MINID` trimming on `XADD`) removes entries purely based on count or ID, with no awareness of whether any consumer group still has that entry pending. If you trim before every group has processed an entry, that entry can vanish from underneath a pending claim.

## Easy Explanation
`XTRIM` is like someone shredding old pages from a shared logbook based only on "keep the last 1000 pages," without checking whether every team that reads the logbook has actually reviewed those pages yet. If the slow team is still three pages behind when the shredding happens, their remaining work disappears — and Redis won't warn you.

## Diagram
```
Stream "orders": [ ...998 older entries... ] [999] [1000] [1001]

Consumer group "billing"   -> already processed everything up to 1001 (fast)
Consumer group "analytics" -> still has 999, 1000 PENDING (slow, hasn't caught up)

Someone runs: XTRIM orders MAXLEN ~ 2
        |
        v
Stream "orders": [1000] [1001]     <- entry 999 is now GONE

Consumer group "analytics" PEL still references 999
        |
        v
XCLAIM / XAUTOCLAIM on 999 returns an empty/deleted entry
        |
        v
"analytics" worker must handle a missing payload defensively
(log + alert + ack, don't crash, don't silently skip real orders)
```

## Production Example
A team added a cron job that runs `XTRIM order-events MAXLEN ~ 5000` every hour to control memory, sized around the fast `billing` consumer group's throughput. They didn't notice the `analytics` consumer group sometimes fell behind during traffic spikes. Result: `analytics` periodically received "claimed" entries with missing data and had gaps in its reporting with no obvious error — until someone added monitoring on `XPENDING`/`XINFO GROUPS` lag per group.

```bash
# safer approach: size retention off the SLOWEST group's lag, not the fastest
XINFO GROUPS order-events   # check each group's lag before trimming
XTRIM order-events MINID ~ <oldest-still-pending-id-across-all-groups>
```

## Why Interviewers Ask This
It's a subtle production landmine that only shows up once multiple consumer groups exist on the same stream. This question separates people who've only used a single consumer group from people who've operated Streams with multiple independent readers.
