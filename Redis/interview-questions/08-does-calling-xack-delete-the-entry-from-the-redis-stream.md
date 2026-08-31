# Does calling XACK delete the entry from the Redis stream?

**Type:** Trap Question
**Topic:** Redis Streams — Reliable Delivery & Idempotency
**Level:** Senior Interview (10+ YOE) — common gotcha

## Direct Answer
**No.** `XACK` only removes the entry from that consumer group's **Pending Entries List (PEL)**. The entry itself stays in the stream until it is explicitly removed by `XDEL`, or aged out by trimming (`XTRIM`, `MAXLEN`, `MINID`).

## Easy Explanation
Picture the stream as a long receipt tape, and the PEL as a sticky-note board next to it that tracks "which lines on the tape is Worker A still holding?" When Worker A finishes a line and calls `XACK`, you're only removing *their sticky note* — the line is still printed on the tape. Other consumer groups reading the same tape can still see it. Only cutting the tape (`XTRIM`/`XDEL`) actually removes the line.

## Diagram
```
Stream "orders" (the tape):
  1001-0  1001-1  1001-2  1001-3  1001-4   <- entries live here permanently until trimmed

Consumer Group "billing" PEL:      Consumer Group "analytics" PEL:
  [1001-2 pending]                    [1001-1, 1001-2 pending]

billing worker calls XACK 1001-2
        |
        v
Consumer Group "billing" PEL:      Consumer Group "analytics" PEL:
  [ empty ]                           [1001-1, 1001-2 pending]   <-- UNCHANGED

Entry 1001-2 is STILL on the stream tape — "analytics" hasn't acked it yet.
```

## Production Example
This bites teams that run two consumer groups on one stream — say `billing` and `analytics` both reading `order-events`. If an engineer assumes `XACK` from `billing` cleans up the stream and adds a scheduled `XTRIM MAXLEN ~ 1000` right after acknowledging, the `analytics` group can lose entries it never got to process, silently breaking its reporting numbers.

```bash
XACK order-events billing 1001-2      # only clears billing's PEL entry
XLEN order-events                     # entry count is unchanged — still on the stream
XPENDING order-events analytics       # analytics still sees 1001-2 as unprocessed
```

Retention decisions (`XTRIM`/`MAXLEN`/`MINID`) must be based on the **slowest** consumer group's lag, never on one group's acknowledgements.

## Why Interviewers Ask This
It's a classic "sounds obvious but isn't" trap. Many engineers who've only used Kafka assume acknowledging = removing, because offset commits feel similar. This question quickly reveals whether someone has actually operated multi-consumer-group Redis Streams in production.
