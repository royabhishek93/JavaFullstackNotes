# Why does fire-and-forget mean Redis never tells the publisher if anyone actually got the message?

**Type:** Trap Question
**Topic:** Redis Pub/Sub — Fire-and-Forget Semantics
**Level:** Mid–Senior Interview (5–10+ YOE) — common gotcha

## Direct Answer
Because Redis Pub/Sub was designed as a **fire-and-forget** messaging pattern: the publisher sends a message and moves on immediately, with no acknowledgment step confirming any subscriber received or processed it. Even the `PUBLISH` command's return value only tells you the *number of subscribers the message was delivered to* — not whether any of them successfully handled it.

## Easy Explanation
Announcing something over a loudspeaker doesn't tell you whether anyone in the crowd actually heard or understood you — you just know your voice went out. `PUBLISH` in Redis works the same way: it tells you "N people were listening when I said this," not "N people confirmed they got it and did something useful with it." If you need that confirmation, Pub/Sub is the wrong tool.

## Diagram
```
PUBLISH orders:new '{"orderId": 900}'
        |
        v
   returns: 3        <- "3 subscribers were listening at this instant"

This number does NOT mean:
  - 3 subscribers successfully processed the message
  - 0 subscribers crashed while handling it
  - the message was stored anywhere for retry

It ONLY means: 3 sockets were subscribed at the moment of publishing.
A subscriber could receive it and immediately crash before doing anything —
the publisher would never know.
```

## Production Example
A team used Pub/Sub to trigger "process this order" logic across worker instances, checking `PUBLISH`'s return value ("delivered to 2 subscribers") as if it meant "2 workers will definitely process this order." When one of those workers crashed immediately after receiving the message but before finishing the work, the order was silently never processed — and nothing in the system indicated a failure, because Pub/Sub was never designed to track processing outcomes.

```bash
PUBLISH orders:new '{"orderId": 900}'
# returns 2 — this is a subscriber COUNT, not a success/completion guarantee
```

## Why Interviewers Ask This
It checks whether a candidate correctly interprets `PUBLISH`'s return value and understands that Pub/Sub has zero built-in concept of "processing succeeded" — a subtlety that's easy to misread as a delivery guarantee if you haven't used it in a real failure scenario.
