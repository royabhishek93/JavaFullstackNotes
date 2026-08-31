# How do you subscribe to every channel ending in _chat without hardcoding each channel name?

**Type:** Scenario-Based
**Topic:** Redis Pub/Sub — Pattern Subscriptions
**Level:** Mid Interview (3–8+ YOE)

## Direct Answer
Use `PSUBSCRIBE` with a glob-style pattern, such as `*_chat`, instead of `SUBSCRIBE` to individual channel names. Redis matches any channel whose name fits the pattern, so new channels created later (like `room42_chat`) are automatically covered without any code changes.

## Easy Explanation
`SUBSCRIBE` is like memorizing the exact names of every radio station you want to listen to — if a new station launches, you have to manually add it to your list. `PSUBSCRIBE` is like saying "tune me into any station whose name ends in `_chat`," so any brand-new station matching that rule is automatically picked up, without you ever needing to update anything.

## Diagram
```
SUBSCRIBE room1_chat            <- only matches this exact channel
SUBSCRIBE room2_chat            <- need a separate call for every new room

vs.

PSUBSCRIBE *_chat               <- matches ANY channel ending in "_chat"

PUBLISH room1_chat "hi"     -> matched, delivered
PUBLISH room2_chat "hi"     -> matched, delivered
PUBLISH room999_chat "hi"   -> matched automatically, even though room999_chat
                                 didn't exist when PSUBSCRIBE was first run
PUBLISH room1_notifications "hi" -> NOT matched (doesn't end in "_chat")
```

## Production Example
```bash
# A monitoring/logging service that needs to observe every chat room, present and future
PSUBSCRIBE *_chat
```

```javascript
redisSubscriber.pSubscribe("*_chat", (message, channel) => {
  console.log(`[audit log] ${channel}: ${message}`);
});
```

This is commonly used for cross-cutting services like logging, moderation bots, or analytics collectors that need to observe an entire category of channels without maintaining a manually updated list of every individual channel name.

## Why Interviewers Ask This
It's a practical, low-friction question that checks whether a candidate knows Redis supports pattern-based subscriptions — useful for any system where the set of channels grows dynamically (per-room, per-user, per-tenant channels).
