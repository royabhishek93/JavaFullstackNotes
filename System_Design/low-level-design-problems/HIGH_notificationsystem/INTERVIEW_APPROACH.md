# Interview Approach - Notification System LLD

## 1. Start With Product Reality
"Notifications look simple, but production systems fail on retries, opt-outs, and provider reliability."

## 2. Define Core Guarantees
- No duplicate notification effect for same dedupe key.
- Respect user preferences before delivery.
- Delivery audit trail across retries and callbacks.
- Provider abstraction so business logic is not provider-coupled.

## 3. Walk Through Happy Path
1. Producer posts request.
2. Validate and dedupe.
3. Resolve preferences and template.
4. Create per-channel message.
5. Send via worker.
6. Track callback and final status.

## 4. Walk Through Failure Path
1. Provider timeout.
2. Mark attempt UNKNOWN or FAILED.
3. Retry with backoff or switch provider.
4. Send to DLQ after retry budget exhausted.

## 5. Mention Scale Levers
- Queue per channel/priority
- Rate limiting per user and per provider
- Batch sending for email/push where supported
- Partition messages by date/status

## 6. Trade-offs
- At-least-once delivery at infrastructure layer, deduplicated at business layer.
- Real-time sends for critical alerts; batched sends for low-priority marketing.

## 7. Close Strongly
"Correctness here means the right user gets the right message, once, at the right time, through an allowed channel."
