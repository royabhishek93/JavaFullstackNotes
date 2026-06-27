# Notification System (LLD)

This folder follows the same structure and interview style as HIGH_movieticketbookingsystem.

## Files
- `notification-system.md` - End-to-end low-level design
- `DATABASE_SCHEMA_VISUAL.md` - Schema and entity relationships
- `INTERVIEW_APPROACH.md` - How to present the system in interviews
- `interview_questions/` - Scenario-based Q and A

## Scope
- Multi-channel notifications: email, SMS, push, in-app, webhook
- Template rendering and personalization
- User preferences and opt-out rules
- Retry, backoff, dead-letter queue, and deduplication
- Provider failover and delivery tracking

## One-line pitch
Design for reliability first: deduplication + retries + provider failover + delivery audit; then scale with queues, fan-out workers, and rate limiting.
