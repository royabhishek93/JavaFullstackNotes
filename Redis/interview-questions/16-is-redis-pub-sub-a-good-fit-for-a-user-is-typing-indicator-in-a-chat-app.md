# Is Redis Pub/Sub a good fit for a "user is typing…" indicator in a chat app?

**Type:** Scenario-Based
**Topic:** Redis Pub/Sub — Fit-for-Purpose Decisions
**Level:** Mid–Senior Interview (5–10+ YOE)

## Direct Answer
**Yes.** A typing indicator is exactly the kind of feature where Pub/Sub's trade-offs (fire-and-forget, no delivery guarantee, no storage) are perfectly acceptable — if an occasional typing event is missed, nothing breaks; the UI simply updates on the *next* event a moment later, and nobody notices.

## Easy Explanation
Losing one "Alice is typing…" blip out of dozens sent per conversation is harmless — the next keystroke sends another one almost immediately. This is the opposite of a payment or order event, where losing even one message matters a lot. Matching Pub/Sub to low-stakes, high-frequency, "latest value wins" style features is exactly where it shines.

## Diagram
```
User types...
  PUBLISH typing:room-9 '{"user": "alice", "typing": true}'   (sent every ~2s while typing)

If ONE of these is lost due to a brief subscriber hiccup:
  - the UI just doesn't flicker "typing" for one brief instant
  - the NEXT publish (2 seconds later) corrects it
  - no data was "lost" in any meaningful business sense

Compare to an order event:
  PUBLISH orders:new '{"orderId": 900}'   (sent exactly ONCE, ever)
  if THIS one is lost -> the order is never processed -> real business impact
```

## Production Example
```javascript
// Perfectly fine use of Pub/Sub — low stakes, frequent, self-correcting
socket.on("typing", () => {
  redisPublisher.publish(`typing:${roomId}`, JSON.stringify({ user, typing: true }));
});
```

Contrast this with order confirmation, payment processing, or account verification events — those require guaranteed delivery and belong on Redis Streams (or another durable queue), not Pub/Sub.

## Why Interviewers Ask This
It checks whether a candidate can correctly classify features by their tolerance for occasional message loss, rather than reflexively avoiding Pub/Sub everywhere "just to be safe," or reflexively using it everywhere because it's simple.
