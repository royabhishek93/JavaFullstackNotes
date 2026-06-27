# HIGH Q01 - Scale to 100M Notifications per Day

## Scenario
System must handle 100M notifications/day across email, SMS, and push.

## Design
- Partition queues by channel and priority.
- Batch low-priority email and push sends.
- Separate transactional vs marketing pipelines.
- Use DLQ and replay tools.
- Store rendered message snapshot, not just template reference.
- Archive old delivery attempts to cold storage.

## Bottlenecks
- Provider API rate limits
- Hot tenants/campaign spikes
- Callback ingestion burst from providers

## Interview One-Liner
The scaling unit is not just requests; it is messages times channels times retries.
