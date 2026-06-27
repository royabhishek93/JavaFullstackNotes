# Designing a Notification System (LLD)

## Requirements
1. Support multiple channels: EMAIL, SMS, PUSH, IN_APP, WEBHOOK.
2. Accept notification requests from multiple producer services.
3. Personalize content using templates and variables.
4. Respect user preferences, quiet hours, and opt-outs.
5. Guarantee deduplication for retries.
6. Support retry with exponential backoff and DLQ.
7. Track delivery lifecycle: queued, sent, delivered, failed, opened.
8. Support provider fallback when primary provider fails.

## Core Components
1. Notification API
- Accepts request and validates payload.
- Applies idempotency and deduplication.

2. Preference Service
- Checks if user has opted in for a channel/topic.
- Enforces quiet hours and rate limits.

3. Template Service
- Loads template by channel + event type.
- Renders variables into final content.

4. Orchestrator
- Creates notification job.
- Fans out to channel-specific delivery tasks.

5. Delivery Workers
- Channel-specific workers for EMAIL, SMS, PUSH, WEBHOOK.
- Handle retries and provider failover.

6. Provider Adapters
- SES, SendGrid, Twilio, FCM, APNS, custom webhook.
- Normalizes provider response into common status model.

7. Delivery Tracking
- Processes webhook callbacks from providers.
- Updates final delivery status.

## Core Entities
1. NotificationRequest
- id, producer_service, user_id, topic, dedupe_key, priority, status

2. NotificationMessage
- id, request_id, channel, rendered_subject, rendered_body, status, scheduled_at

3. Template
- id, event_type, channel, subject_template, body_template, version, is_active

4. UserPreference
- user_id, topic, channel, enabled, quiet_hours_start, quiet_hours_end

5. DeliveryAttempt
- id, message_id, provider, attempt_no, status, provider_message_id, error_code

6. ProviderCallbackEvent
- id, provider, provider_message_id, event_type, payload_hash, processed_at

## APIs
- POST /v1/notifications
- GET /v1/notifications/{id}
- POST /v1/templates
- PUT /v1/templates/{id}
- GET /v1/users/{userId}/preferences
- PUT /v1/users/{userId}/preferences
- POST /v1/provider-callbacks/{provider}

## Delivery Flow
1. Producer sends notification request with `dedupe_key`.
2. API validates and creates request record.
3. Preference service filters unsupported/disabled channels.
4. Template service renders per-channel content.
5. Orchestrator creates notification messages.
6. Workers send via provider adapters.
7. Callback/webhook updates final status.

## State Transitions
- Request: RECEIVED -> PROCESSING -> COMPLETED or PARTIAL_FAILED or FAILED
- Message: QUEUED -> SENT -> DELIVERED or FAILED
- Attempt: INITIATED -> SUCCESS or FAILED or UNKNOWN

## Concurrency Strategy
- Unique constraint on `(producer_service, dedupe_key)`.
- Workers claim messages using status transition `QUEUED -> PROCESSING`.
- Use retry schedule with `next_attempt_at` and capped backoff.

## Failure Scenarios
1. Provider timeout
- Mark attempt UNKNOWN.
- Retry or wait for callback depending on provider semantics.

2. Duplicate producer retry
- Return same request ID using dedupe key.

3. User opted out after request creation
- Re-check preference before final send if message is delayed.

4. Template changed during queued processing
- Store rendered content snapshot in message.

## Interview One-Liner
A notification system is a reliability pipeline: validate, dedupe, personalize, queue, deliver, retry, and reconcile.
