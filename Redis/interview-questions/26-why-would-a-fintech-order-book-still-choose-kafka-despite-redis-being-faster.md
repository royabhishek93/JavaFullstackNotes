# Why would a fintech order book still choose Kafka despite Redis being faster?

**Type:** Advanced Scenario-Based
**Topic:** Redis vs Kafka — When Durability Outweighs Speed
**Level:** Staff/Principal Interview (12–15+ YOE)

## Direct Answer
Because raw speed isn't the only requirement for an order book — it needs long-term durability, exact replay for audits and regulatory compliance, and the ability for multiple independent consumers (settlement, risk, reporting, analytics) to read the *same* history at their own pace, potentially much later. Kafka's disk-backed, partitioned log is built exactly for that; Redis's in-memory, fire-and-forget-oriented design is not.

## Easy Explanation
Speed matters, but a financial order book also needs a permanent, trustworthy paper trail that regulators and auditors can review months later, and that several different departments can each read independently without stepping on each other. That's the filing cabinet (Kafka), not the whiteboard (Redis) — even though the whiteboard is faster to write on, it's the wrong tool when "provably permanent and independently replayable" matters more than shaving off a few milliseconds.

## Diagram
```
Requirement comparison for an order book:

                     Speed        Durability      Long replay    Many independent consumers
Redis (Streams)  -->  fast          short-term       limited        okay, but memory-costly
Kafka             -->  good enough   built-in         excellent      excellent, by design

Order events published once, consumed independently by:
  - Settlement engine   (needs it now)
  - Risk engine         (needs it now)
  - Regulatory audit    (needs it in 6 months, exactly as it happened)
  - Analytics warehouse (needs to replay all of last quarter)

Kafka lets all four read the same log independently, at their own pace, for as long as retention allows.
Redis Streams could serve the first two, but not comfortably the last two at scale.
```

## Production Example
A trading platform uses Kafka as the system of record for every order event, with retention measured in months, consumed independently by settlement, risk, and compliance teams. A Redis Stream might still be used *downstream* for a specific low-latency task (like real-time price-alert notifications), but the authoritative, replayable, auditable order history lives in Kafka — because "provably exact and replayable for months" is a harder requirement than "as fast as possible."

## Why Interviewers Ask This
It's the counter-example that proves a candidate isn't just memorizing "Redis is faster, therefore always better" — it checks whether they can identify when durability, audit, and multi-consumer replay requirements outweigh raw speed.
