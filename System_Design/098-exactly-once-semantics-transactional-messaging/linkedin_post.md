# Exactly-Once Semantics & Transactional Messaging — LinkedIn Post

## Post Text (copy-paste ready)

"We have exactly-once semantics configured, so we're safe from double-charging customers." This sentence is dangerously wrong.

- The Two Generals Problem proves exactly-once delivery over a network is mathematically impossible — a producer can never distinguish "the broker never got it" from "it got it, the ack just got lost"
- Kafka's actual guarantee is two narrower things stacked: idempotent producer (PID + sequence number dedupes retries at the broker) and transactions (atomically ties a produce + an offset commit together)
- The trap: EOS only covers Kafka-to-Kafka. The moment a consumer calls an EXTERNAL system (a payment gateway, an SMS API) as a side effect, that call is completely unprotected by Kafka's transaction
- Real failure: service charges a card, crashes BEFORE committing its Kafka offset, redelivers the message on restart, charges the card AGAIN — Kafka did exactly what it promised, the double-charge is on the external side
- Fix: a SEPARATE idempotency key at the external boundary (tied to order ID), independent of Kafka's own guarantees

Swipe → to see exactly where Kafka's exactly-once guarantee ends and why you need two independent idempotency mechanisms, not one.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
"We have EOS configured, so we're safe from double-charging" is a dangerous sentence. Here's exactly where Kafka's guarantee ends 👇

### Variant B — Long (400–600 chars)
Kafka's exactly-once semantics is real, but it only covers Kafka's own bookkeeping — topics, partitions, and consumer offsets. The moment a consumer calls an external system as a side effect of processing a message (a payment gateway, an SMS API), that call is completely unprotected. A crash right before committing the Kafka offset means the message gets redelivered and the external call happens again. The fix is a separate idempotency key at that external boundary — Kafka's EOS and external idempotency keys solve two different halves of the same problem.

---

## Best Time to Post
Friday, 9:00–10:00 AM IST (closes the full 20-episode series with a high-stakes, save-worthy correction to a common misconception)

## Engagement Hook
"Has your team ever assumed Kafka's EOS covered an external side effect, only to find out the hard way that it didn't?"
