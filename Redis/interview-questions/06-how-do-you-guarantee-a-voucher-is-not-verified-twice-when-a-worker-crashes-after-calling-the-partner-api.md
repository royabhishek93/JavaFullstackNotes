# How do you guarantee a voucher is not verified twice when a worker crashes after calling the partner API?

**Type:** Scenario-Based
**Topic:** Redis Streams — Reliable Delivery & Idempotency
**Level:** Senior/Staff Interview (10–15+ YOE)

## Direct Answer
You can't guarantee it with Redis alone — Redis Streams give you **at-least-once** delivery, never exactly-once. The guarantee has to come from your own application: give every voucher request a stable `requestId`, make the partner call and the database write idempotent on that ID, and only call `XACK` *after* the database write succeeds.

## Easy Explanation
Think of a Redis Stream like a shared to-do list pinned on a wall. A worker takes a sticky note (a message), does the work, and only removes the note (`XACK`) after the work is fully done and saved. If the worker dies with the note still in hand, someone else will eventually pick it up and do the work *again*. Redis has no idea whether "again" is safe or dangerous — that's on you. So the real fix isn't in Redis; it's making sure that doing the same task twice has the same end result as doing it once (that's what "idempotent" means).

## Diagram
```
Normal path:
Client -> XADD -> Stream -> XREADGROUP -> Worker -> Partner API -> DB write -> XACK
                                                                      (success)   (safe to remove)

Crash path (the risky one):
Client -> XADD -> Stream -> XREADGROUP -> Worker -> Partner API -> DB write
                                              |
                                         worker CRASHES here, before XACK
                                              v
                          message stays in the Pending Entries List (PEL)
                                              |
                                     XAUTOCLAIM (after idle timeout)
                                              v
                                    another worker re-reads SAME message
                                              |
                                 calls partner API AGAIN + writes to DB AGAIN
                                              |
                     ---> WITHOUT an idempotency key, this double-charges the voucher
                     ---> WITH an idempotency key, the DB write is a safe no-op
```

## Production Example
An e-commerce checkout uses Redis Streams to verify discount vouchers asynchronously:

```java
public void process(MapRecord<String, Object, Object> message) {
    VoucherEvent event = mapper.toEvent(message);

    // requestId is the same every time this event is redelivered
    boolean alreadyProcessed = voucherRepo.existsByRequestId(event.requestId());
    if (!alreadyProcessed) {
        partnerClient.verify(event);                 // safe even if retried
        voucherRepo.markVerified(event.requestId());  // unique DB constraint on requestId
    }

    redisTemplate.opsForStream().acknowledge("voucher-verifiers", message); // XACK LAST
}
```

The unique constraint on `requestId` in the database is what actually stops the double effect — Redis just makes sure the work is *not lost*, not that it's *not repeated*.

## Why Interviewers Ask This
It separates candidates who memorized commands from candidates who understand delivery guarantees. A senior engineer should immediately say "at-least-once, not exactly-once" and pivot straight to idempotency, instead of trying to find a Redis flag that "fixes" it.
