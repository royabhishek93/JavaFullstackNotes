# Why does a notification published while a service instance is restarting never arrive?

**Type:** Trap Question
**Topic:** Redis Caching Patterns — Pub/Sub Reliability Gap
**Level:** Senior Interview (8–12+ YOE) — common gotcha

## Direct Answer
Because Redis Pub/Sub only delivers messages to subscribers that are **connected at the exact moment of publishing** — if an instance is mid-restart (briefly disconnected), any message published during that gap is simply dropped, with no buffering, no retry, and no error raised anywhere. This is easy to miss in testing because restarts are usually brief, and the failure is silent.

## Easy Explanation
Pub/Sub is a live broadcast, not a mailbox. If your radio was switched off for even ten seconds during a restart, you don't get those ten seconds replayed to you later — they're just gone, as if they were never sent. Nothing in the system will ever tell you a message was lost; it simply never shows up.

## Diagram
```
t=0s     Instance B is subscribed and healthy
t=1s     Deploy triggers rolling restart -> Instance B disconnects briefly
t=1.2s   PUBLISH notifications '{"userId": "42", "text": "Report ready"}'
                       |
                       v
              Instance B is NOT currently subscribed (mid-restart)
                       |
                       v
              message is delivered to 0 subscribers -> GONE, no retry, no error
t=1.5s   Instance B finishes restarting, re-subscribes
                       |
                       v
              User 42 NEVER receives their "Report ready" notification
```

## Production Example
A team relied purely on Redis Pub/Sub for "your export is ready" email triggers. During routine rolling deployments (each pod restarting for ~5–8 seconds), any export that finished during that exact window silently never triggered an email — with zero errors in any log, since nothing failed; the message simply had no subscriber to deliver to. The fix was migrating that specific event to a Redis Stream with a consumer group, so a restarting worker resumes from its last acknowledged position instead of missing anything published while it was offline.

```bash
# Pub/Sub (loses messages during restarts)
PUBLISH report-ready '{"userId": "42"}'

# Streams (survives restarts — consumer resumes where it left off)
XADD report-events * userId 42
XREADGROUP GROUP email-workers worker-1 STREAMS report-events >
```

## Why Interviewers Ask This
It's a very realistic, easy-to-miss production bug that only shows up in a rolling-deployment environment — exactly the kind of subtle reliability gap a 15-YOE engineer is expected to anticipate before it causes a customer-facing incident.
