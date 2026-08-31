# How do you redesign a notification system so offline users do not lose messages?

**Type:** Advanced Scenario-Based
**Topic:** Redis Pub/Sub — Overcoming the Delivery Gap
**Level:** Staff Interview (10–15+ YOE)

## Direct Answer
Stop relying on Pub/Sub alone for anything that must not be lost. Either (a) replace it with a Redis Stream + consumer group, so a reconnecting client resumes from its last acknowledged position, or (b) keep Pub/Sub for instant "you're online, here it is now" delivery, but *also* persist every notification to a durable store, and have clients fetch "anything I missed since my last seen timestamp" on reconnect.

## Easy Explanation
Instead of relying only on a live radio broadcast (Pub/Sub), you add a voicemail inbox (a durable store or a Stream) that records every message as it happens. When someone comes back online, they don't just start listening to the live broadcast again — they first check their voicemail inbox for anything they missed, then resume listening live. Two systems, two jobs: live delivery for those already listening, durable catch-up for those who weren't.

## Diagram
```
Hybrid design:

Publisher --PUBLISH--> chat:room-9 --> [ online subscribers get it instantly ]
     |
     +--------------> ALSO written to a durable store, e.g.:
                          XADD chat-history:room-9 * from "userA" text "hello"
                       (or a database table)

Client reconnects after being offline:
     1. XRANGE chat-history:room-9 <lastSeenId> +     <- fetch everything missed
     2. SUBSCRIBE chat:room-9                          <- resume live delivery
```

## Production Example
```javascript
// On send: publish for instant delivery AND persist for catch-up
async function sendMessage(roomId, from, text) {
  const payload = JSON.stringify({ from, text, ts: Date.now() });
  await redisPublisher.publish(`chat:${roomId}`, payload);
  await redisClient.xAdd(`chat-history:${roomId}`, "*", { from, text });
}

// On reconnect: catch up on missed history, then resume live subscription
async function onReconnect(roomId, lastSeenId) {
  const missed = await redisClient.xRange(`chat-history:${roomId}`, lastSeenId, "+");
  deliverToClient(missed);
  redisSubscriber.subscribe(`chat:${roomId}`);
}
```

## Why Interviewers Ask This
It tests whether a candidate can design around a known limitation instead of pretending it doesn't exist — a hallmark of experienced engineers who've actually operated real-time systems where "occasionally drop a message" wasn't an acceptable outcome.
