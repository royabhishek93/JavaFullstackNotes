# How do you design a chat backend that uses Redis for live delivery and a database for history?

**Type:** Advanced Scenario-Based
**Topic:** Redis vs Kafka — Hybrid Real-Time + Durable Architecture
**Level:** Staff Interview (12–15+ YOE)

## Direct Answer
Every message write does two things at once: publish it to a Redis Pub/Sub channel (or Stream) for instant delivery to anyone currently online, and persist it to a durable store (a database, or a long-retention Redis Stream/Kafka topic) as the permanent system of record. Reads for "live updates" come from the Pub/Sub subscription; reads for "chat history" always come from the durable store, never from Pub/Sub.

## Easy Explanation
Think of a newsroom: reporters announce breaking news live over the intercom (Pub/Sub) for whoever's in the building right now, *and* they simultaneously file the same story into the permanent newspaper archive (the database). Someone walking in late doesn't rely on having heard the intercom — they read the archive. Both systems carry the same information, but they serve different audiences with different needs (instant vs. anytime).

## Diagram
```
                        +---------------------------+
Client sends message -> |      Chat Backend           |
                        |  1. persist to DB (source   |----> Postgres / Mongo
                        |     of truth, permanent)     |        message table
                        |  2. PUBLISH to Redis channel |----> Redis Pub/Sub
                        |     (for anyone online now)  |        chat:room-9
                        +---------------------------+

Online user (subscribed):        Offline user who just opened the app:
  receives message instantly       queries DB directly: "give me last 50 messages"
  via Redis Pub/Sub                 (completely independent of Pub/Sub delivery)
```

## Production Example
```javascript
async function sendMessage(roomId, from, text) {
  const message = await db.messages.insertOne({ roomId, from, text, ts: Date.now() });
  await redisPublisher.publish(`chat:${roomId}`, JSON.stringify(message));
  return message;
}

// New client connecting to a room:
async function joinRoom(roomId, socket) {
  const history = await db.messages.find({ roomId }).sort({ ts: -1 }).limit(50);
  socket.send({ type: "history", messages: history });          // catch up first
  redisSubscriber.subscribe(`chat:${roomId}`, (msg) => socket.send(JSON.parse(msg))); // then go live
}
```

This "persist first, publish second" ordering (or persisting and publishing together in a transaction/outbox pattern) ensures the durable record is never missing a message that was successfully delivered live.

## Why Interviewers Ask This
It's the natural follow-up to "should delivery and history use the same mechanism" — it checks whether the candidate can actually implement the resulting two-mechanism design cleanly, including the correct order of operations and how a newly-joined or reconnecting client gets both history and live updates.
