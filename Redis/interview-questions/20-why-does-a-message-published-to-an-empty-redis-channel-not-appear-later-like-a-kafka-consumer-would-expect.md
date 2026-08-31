# Why does a message published to an empty Redis channel not appear later like a Kafka consumer would expect?

**Type:** Trap Question
**Topic:** Redis vs Kafka — Delivery Model Mismatch
**Level:** Mid–Senior Interview (5–10+ YOE) — common gotcha

## Direct Answer
Because Redis Pub/Sub channels and Kafka topics behave completely differently by design. A Kafka consumer can start reading a topic from an earlier offset and "catch up" on messages published before it connected, because Kafka persists everything to disk. A Redis Pub/Sub channel stores nothing — if no subscriber was connected the instant a message was published, that message is gone, and no amount of subscribing afterward will ever retrieve it.

## Easy Explanation
Kafka is like a filing cabinet: you can walk in anytime and read files filed weeks ago. Redis Pub/Sub is like a live announcement over a loudspeaker: if you weren't in the room when it played, there's no recording to go back and listen to. An engineer used to Kafka's "I can always catch up" mental model will be surprised the first time they realize Redis Pub/Sub offers no such thing.

## Diagram
```
Kafka mental model (catch-up IS possible):
  Producer writes "msg1" to topic at t=0s (persisted to disk)
  Consumer connects at t=10s, requests from offset 0
        |
        v
  Consumer successfully reads "msg1" -- it was never lost, it was on disk

Redis Pub/Sub reality (NO catch-up):
  PUBLISH channel "msg1" at t=0s -- zero subscribers connected -- msg1 is GONE, nothing stored
  Client SUBSCRIBEs at t=10s
        |
        v
  Client will NEVER see "msg1" -- there is nothing to "catch up" to
```

## Production Example
An engineer migrating a Kafka-based event pipeline to Redis Pub/Sub for cost reasons assumed a newly-deployed consumer service would "catch up" on events published while it was being deployed, just like it did with Kafka. In production, every event published during the few seconds of deployment downtime was silently and permanently lost — a direct consequence of not recognizing that Redis Pub/Sub has no equivalent to Kafka's offset-based replay.

## Why Interviewers Ask This
It specifically targets engineers with a Kafka background, checking whether they carry over an incorrect mental model into Redis Pub/Sub — a genuinely common and costly migration mistake.
