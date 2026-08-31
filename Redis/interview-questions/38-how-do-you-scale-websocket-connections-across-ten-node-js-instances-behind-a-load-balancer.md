# How do you scale WebSocket connections across ten Node.js instances behind a load balancer?

**Type:** Advanced Scenario-Based
**Topic:** Redis Caching Patterns — Scaling Real-Time Systems
**Level:** Staff Interview (12–15+ YOE)

## Direct Answer
Keep each instance responsible only for the WebSocket connections physically attached to it, and use Redis Pub/Sub as the shared messaging backbone between all ten instances. Every instance subscribes to relevant channels; when any instance needs to deliver a message, it publishes once, and Redis broadcasts it to all ten, each of which checks whether it has a locally connected socket for the intended recipient.

## Easy Explanation
Imagine ten separate call centers, each handling a slice of your customers, with no way to transfer a call between centers directly. If Center 3 needs to reach a customer being handled by Center 7, it can't call them directly — but if all ten centers are also listening to a shared internal broadcast system, Center 3 can announce "message for customer X" on that system, and whichever center is actually holding customer X's line picks it up and delivers it.

## Diagram
```
Load Balancer
     |
     +----------> Instance 1  (200 sockets)  --\
     +----------> Instance 2  (200 sockets)    \
     +----------> Instance 3  (200 sockets)     \___ all subscribe to Redis channels:
     +----------> ...                            /       "chat-events", "notifications"
     +----------> Instance 10 (200 sockets)  --/

Any instance publishes once:
  PUBLISH notifications '{"userId": "8842", "text": "New message"}'
        |
        v
  Redis fans out to ALL 10 subscribed instances
        |
        v
  Only the ONE instance holding userId 8842's live socket actually delivers it;
  the other 9 instances receive it too but find no matching local connection and ignore it
```

## Production Example
```javascript
redisSubscriber.subscribe("notifications", (raw) => {
  const { userId, text } = JSON.parse(raw);
  const socket = localSockets.get(userId);
  if (socket) socket.send(text);
  // if not found here, some OTHER instance will find and deliver it — no coordination needed
});
```

At larger scale, teams often also maintain a lightweight "which instance holds which user" lookup in Redis (e.g., a Hash: `socket-location:userId -> instanceId`) to publish *only* to the relevant instance instead of broadcasting to all ten — trading a bit of extra bookkeeping for reduced fan-out overhead.

## Why Interviewers Ask This
It probes whether a candidate can reason about horizontal scaling for stateful, connection-based features (unlike stateless HTTP APIs) — a genuinely harder problem that many engineers haven't had to solve directly.
