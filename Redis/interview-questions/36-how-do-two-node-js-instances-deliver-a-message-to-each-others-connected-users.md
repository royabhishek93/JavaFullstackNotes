# How do two Node.js instances deliver a message to each other's connected users?

**Type:** Scenario-Based
**Topic:** Redis Caching Patterns — Pub/Sub for Cross-Instance Messaging
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
Each Node.js instance subscribes to a shared Redis channel. When instance A's WebSocket receives a message meant for a user connected to instance B, instance A publishes it to that shared channel; Redis fans it out to every subscribed instance (including B), and instance B forwards it to its own locally connected WebSocket client.

## Easy Explanation
If two office branches each have their own phone system with no direct line between them, but both are connected to a shared radio channel, an employee in branch A can announce a message on the radio, and the employee in branch B — listening on the same channel — hears it and relays it to their own customer on their local phone line. Redis Pub/Sub is that shared radio channel bridging otherwise-isolated backend instances.

## Diagram
```
   User X                                              User Y
     | (WebSocket)                                        | (WebSocket)
     v                                                     v
+-----------+                                        +-----------+
| Instance A |                                       | Instance B |
+-----+-----+                                        +-----+-----+
      |  PUBLISH chat-events "to:Y hello!"                  |
      +---------------------> Redis <---------------------- + SUBSCRIBE chat-events
                               |
                  fans out message to ALL subscribers
                               |
                               v
                     Instance B receives it via subscription
                               |
                               v
                     Instance B forwards to User Y's WebSocket
```

## Production Example
```javascript
// Instance A: user X sends a message meant for user Y (connected elsewhere)
redisPublisher.publish("chat-events", JSON.stringify({ to: "userY", text: "hello!" }));

// Every instance (including B) subscribes and forwards locally-relevant messages
redisSubscriber.subscribe("chat-events", (message) => {
  const event = JSON.parse(message);
  const socket = localConnections.get(event.to);
  if (socket) socket.send(event.text);   // only delivers if that user is connected HERE
});
```

This pattern is the standard way to scale WebSocket-based chat/notification systems horizontally — Redis Pub/Sub becomes the "backbone" that lets any instance reach any connected user, regardless of which instance they're attached to.

## Why Interviewers Ask This
It tests whether a candidate can explain how real-time features work *across* horizontally scaled instances, not just within a single process — a very common real architecture question for chat, notifications, and live-update features.
