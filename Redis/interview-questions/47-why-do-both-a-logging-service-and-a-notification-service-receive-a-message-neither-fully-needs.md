# Why do both a logging service and a notification service receive a message neither fully needs?

**Type:** Advanced Scenario-Based
**Topic:** Redis Pub/Sub — Fan-Out-Only Delivery
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
Because Redis Pub/Sub is **fan-out only** — every subscriber on a channel receives an identical copy of every message published to it, with no server-side filtering based on subscriber-side interest. If two very different services both subscribe to the same channel, they both get everything, and each is responsible for deciding what to do with (or ignore in) every message.

## Easy Explanation
Publishing to a channel is like posting on a shared notice board that everyone subscribed to that board can read — the board doesn't know or care that one reader only cares about "urgent" notices while another only cares about "birthday" notices. Everyone gets the whole board; it's up to each reader to skim past what they don't need.

## Diagram
```
PUBLISH order-events '{"type": "created", "orderId": 900}'
        |
        v
   Redis fans this out identically to BOTH subscribers:

+---------------------+                     +---------------------------+
| Logging Service      |  <--- same msg --->| Notification Service       |
| (subscribed to       |                     | (subscribed to same       |
|  order-events)       |                     |  channel, only cares      |
|                       |                     |  about "type: shipped")   |
| logs everything,      |                     |                            |
| including this one    |                     | receives it too, checks   |
|                       |                     | type != "shipped", ignores |
+---------------------+                     +---------------------------+

Both received the SAME message; Redis did no filtering — each service filtered locally.
```

## Production Example
```javascript
redisSubscriber.subscribe("order-events", (raw) => {
  const event = JSON.parse(raw);
  if (event.type !== "shipped") return;  // ignore anything not relevant to this service
  sendShippingNotification(event);
});
```

If the two services need genuinely different event types, a cleaner design publishes to separate channels (`order-events:created`, `order-events:shipped`) so each service only subscribes to what it actually needs — reducing wasted deserialization and filtering work, especially at high message volumes.

## Why Interviewers Ask This
It tests whether a candidate understands Pub/Sub's fan-out-only nature well enough to design channel granularity deliberately, instead of dumping every event type onto one broad channel and filtering client-side at scale.
