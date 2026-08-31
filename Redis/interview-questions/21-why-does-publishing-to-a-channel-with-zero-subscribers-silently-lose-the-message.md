# Why does publishing to a channel with zero subscribers silently lose the message?

**Type:** Trap Question
**Topic:** Redis Pub/Sub — No Storage, No Replay
**Level:** Mid–Senior Interview (5–10+ YOE) — common gotcha

## Direct Answer
Because Redis Pub/Sub does not store messages anywhere — a channel is not a queue or a mailbox, it's just a live broadcast frequency. If nobody is tuned in (subscribed) at the exact moment `PUBLISH` runs, the message is delivered to zero recipients and then discarded completely, with no error and no persistence.

## Easy Explanation
A Pub/Sub channel doesn't physically "exist" as a stored thing — it's just a label Redis uses to match publishers with currently-listening subscribers. If you shout into a channel that nobody is listening to, there's no recording device catching it for later; the sound just fades into nothing.

## Diagram
```
PUBLISH order-updates:900 '{"status": "shipped"}'
        |
        v
   Redis checks: how many clients are currently SUBSCRIBEd to "order-updates:900"?
        |
        v
   answer: 0
        |
        v
   PUBLISH returns 0  (0 subscribers received it)
   the message itself is now GONE — nothing was stored, nothing can be replayed
```

## Production Example
A frontend page subscribes to `order-updates:900` only *after* the user opens the order-tracking screen. If the backend publishes a "shipped" status update a few seconds *before* the user opens that screen (a common race condition on page load), the update is missed entirely — the UI shows stale status until the *next* update happens to be published, which might be hours later.

```javascript
// Fragile: relies on the subscriber already being connected when the event fires
redisPublisher.publish(`order-updates:${orderId}`, JSON.stringify({ status: "shipped" }));

// More robust: also cache the LATEST status so a late subscriber can fetch current state on load
await redisClient.set(`order-status:${orderId}`, "shipped");
// UI on page load: 1) GET current status  2) SUBSCRIBE for future updates
```

## Why Interviewers Ask This
It reinforces the core Pub/Sub limitation from a different angle — the "zero subscriber" case — and checks whether a candidate proactively designs around it (e.g., always pairing a live channel with a "current state" cache) instead of discovering it in production.
