# Q22: Redis Pub/Sub vs Message Queue - When to use which?

### Comparison:

```
┌────────────────────┬──────────────────┬────────────────────┐
│    Feature         │   Redis Pub/Sub  │   Message Queue    │
├────────────────────┼──────────────────┼────────────────────┤
│ Delivery guarantee │ Fire-and-forget  │ At-least-once      │
│ Message persistence│ No               │ Yes                │
│ Subscriber offline │ Message lost     │ Queued until read  │
│ Throughput         │ 1M msgs/sec      │ 100k msgs/sec      │
│ Latency            │ <1ms             │ 5-10ms             │
│ Use case           │ Real-time events │ Background jobs    │
│ Ordering           │ No guarantee     │ FIFO (SQS/Kafka)   │
└────────────────────┴──────────────────┴────────────────────┘

Use Redis Pub/Sub when:
✅ Real-time updates (seat status)
✅ Low latency required (<10ms)
✅ OK to lose messages if subscriber offline
✅ Broadcast to multiple consumers

Use Message Queue when:
✅ Must not lose messages
✅ Background processing (email, notifications)
✅ Retry logic needed
✅ Order matters
```

**Example: Why Pub/Sub for Seat Updates:**

```java
// Pub/Sub: Fire-and-forget
redisTemplate.convertAndSend("seat:updates:123", event);
// ↑ Returns immediately, doesn't wait for subscribers
// If no subscribers online → message discarded (OK for real-time)

// Message Queue: Persistent
sqsClient.sendMessage("booking-confirmations", event);
// ↑ Message persisted, will retry if consumer fails
// Use for critical workflows (payment confirmation email)
```

---
