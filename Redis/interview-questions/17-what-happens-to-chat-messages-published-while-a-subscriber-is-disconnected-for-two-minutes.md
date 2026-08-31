# What happens to chat messages published while a subscriber is disconnected for two minutes?

**Type:** Scenario-Based
**Topic:** Redis Pub/Sub — Synchronous Delivery
**Level:** Mid–Senior Interview (5–10+ YOE)

## Direct Answer
They are lost, permanently. Redis Pub/Sub is synchronous — it only delivers a message to subscribers that are connected at the exact instant it is published. There is no buffering, storage, or replay mechanism for a subscriber that reconnects later; those two minutes of messages simply never existed as far as that subscriber is concerned.

## Easy Explanation
Pub/Sub is exactly like a live radio broadcast. If your radio was switched off for two minutes, you don't get those two minutes replayed when you turn it back on — you just missed the news, forever. Redis doesn't record anything for latecomers; it only cares about who's tuned in *right now*.

## Diagram
```
t=0s     Subscriber connected, listening on "chat:room-9"
t=1s     Subscriber's network drops (disconnected)
t=1s-121s   PUBLISH chat:room-9 "message 1"   -> 0 subscribers -> LOST
            PUBLISH chat:room-9 "message 2"   -> 0 subscribers -> LOST
            PUBLISH chat:room-9 "message 3"   -> 0 subscribers -> LOST
t=121s   Subscriber reconnects, re-subscribes to "chat:room-9"
t=122s   PUBLISH chat:room-9 "message 4"   -> delivered normally

Result: subscriber only ever sees "message 4" — messages 1, 2, and 3 are gone forever,
with no error, no warning, and no way to know they were even sent.
```

## Production Example
A chat app relying purely on Pub/Sub for message delivery has a user who briefly loses their mobile network in a tunnel. Any messages sent to them during that gap never arrive, even after their connection is restored — there's no "catch-up" behavior built into Pub/Sub. This is exactly why production chat systems typically pair Pub/Sub (for instant delivery to online users) with a durable store or Redis Streams (so a reconnecting client can also fetch anything it missed).

## Why Interviewers Ask This
It's the single most important thing to understand about Redis Pub/Sub before using it in production — this question filters out candidates who assume Redis Pub/Sub "just works like a message queue," when it fundamentally does not guarantee delivery to anyone who wasn't listening at that exact moment.
