# Should chat history be stored using the same mechanism that delivers real-time messages?

**Type:** Scenario-Based
**Topic:** Redis vs Kafka — Separating Delivery from Persistence
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
No. Real-time delivery ("get this message to an online user instantly") and durable history ("let a user see everything they missed, even from days ago") are two different problems with two different guarantees. Trying to solve both with the exact same mechanism (e.g., pure Redis Pub/Sub) leads to confusion and gaps — Pub/Sub simply isn't built to store anything for later retrieval.

## Easy Explanation
Delivering a message live is like handing someone a note the instant they're standing in front of you. Storing history is like keeping a permanent diary of every note ever sent, so anyone can flip back and read old entries anytime. These are genuinely different jobs — the live hand-off doesn't need permanence, and the diary doesn't need to be instant — so it makes sense to use two different tools, not force one tool to awkwardly do both.

## Diagram
```
Two separate concerns, two separate mechanisms:

Real-time delivery (needs speed, tolerates some loss for offline users):
  Publisher --PUBLISH--> chat:room-9 --> [ online subscribers get it instantly ]

Durable history (needs permanence, must never silently disappear):
  Publisher --INSERT/XADD--> chat-history:room-9 (database or Stream)
                                     |
                                     v
                       user opens the app later, queries history directly
                       (completely independent of whether Pub/Sub delivered it live)
```

## Production Example
```javascript
async function sendMessage(roomId, from, text) {
  const payload = { from, text, ts: Date.now() };
  // 1. deliver live, for anyone currently online
  await redisPublisher.publish(`chat:${roomId}`, JSON.stringify(payload));
  // 2. persist separately, for anyone who opens the app later
  await db.insertMessage(roomId, payload);
}

// Loading a chat screen always reads history from the DURABLE store,
// completely independent of whether Pub/Sub successfully delivered it live
async function loadHistory(roomId) {
  return db.getMessages(roomId, { limit: 50 });
}
```

## Why Interviewers Ask This
It tests whether a candidate can decompose a seemingly single feature ("chat") into its true underlying requirements, and avoid the common mistake of forcing one mechanism (usually the "live" one) to also serve as the system of record.
