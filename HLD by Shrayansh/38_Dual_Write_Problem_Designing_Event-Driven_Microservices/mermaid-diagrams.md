# Mermaid Diagrams — Extracted

Diagrams extracted from `interviewguide.md` and replaced in-place with ASCII-art equivalents. Kept here verbatim for anyone who wants the interactive/renderable Mermaid version.

## From `interviewguide.md` — "Transactional Outbox (Sequence Diagram)"

```mermaid
sequenceDiagram
    participant Svc as Service (e.g. OrderService)
    participant DB as Local Database
    participant Poller as Poller/Publisher
    participant MQ as Kafka/Message Broker
    participant Down as Downstream Consumer

    Svc->>DB: BEGIN TXN
    Svc->>DB: INSERT business row (e.g. order)
    Svc->>DB: INSERT outbox_event (status=pending)
    Svc->>DB: COMMIT
    Note over DB: both writes succeed or fail together (ACID)

    loop poll
        Poller->>DB: SELECT unpublished outbox events
        DB-->>Poller: pending rows
        Poller->>MQ: publish event
        MQ-->>Poller: ack
        Poller->>DB: mark event published (or delete)
    end
    MQ->>Down: deliver event
    Down->>Down: idempotency check (business event ID) before acting
```
