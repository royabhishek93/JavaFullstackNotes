# Why is creating a Kafka topic per conversation more expensive than using a Redis channel?

**Type:** Scenario-Based
**Topic:** Redis vs Kafka — Provisioning Cost
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
Because creating a Kafka topic is a real infrastructure operation — it allocates partitions and propagates that creation across the broker cluster, which takes real time and real resources. A Redis Pub/Sub channel requires no creation step at all; it simply starts existing the moment a publisher or subscriber references its name, with zero infrastructure allocation.

## Easy Explanation
Creating a Kafka topic is like opening a brand-new physical mailbox at a post office for every single conversation — the post office has to allocate space, register it, and make sure every branch knows about it before it's usable. A Redis channel is like just saying a name out loud — nothing needs to be built or registered first; if someone's listening, they hear you.

## Diagram
```
Kafka: creating a topic PER conversation
  kafka-topics --create --topic conversation-alice-bob --partitions 3 --replication-factor 2
       |
       v
  brokers allocate partition storage, replicate metadata across the cluster
  (measurable latency, real resource cost — multiplied by EVERY new conversation)

Redis: "creating" a channel PER conversation
  SUBSCRIBE conversation-alice-bob     <- no allocation, no cluster metadata change
  PUBLISH conversation-alice-bob "hi"  <- works immediately, zero setup cost
```

## Production Example
A chat platform that modeled "one Kafka topic per conversation" found that topic creation overhead became a real bottleneck as thousands of new conversations started every hour — each one triggering a non-trivial cluster operation. Switching the real-time delivery layer to Redis Pub/Sub channels (one per conversation) eliminated that overhead entirely, since channels require no provisioning step, while Kafka remained in place for durable message history stored separately.

## Why Interviewers Ask This
It tests whether a candidate understands that "topic" and "channel" are not interchangeable concepts with equivalent costs — Kafka topics are heavier infrastructure objects, which matters a lot when your system creates many short-lived communication channels.
