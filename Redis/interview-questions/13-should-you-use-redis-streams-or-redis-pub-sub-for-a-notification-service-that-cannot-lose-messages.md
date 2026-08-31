# Should you use Redis Streams or Redis Pub/Sub for a notification service that cannot lose messages?

**Type:** Scenario-Based
**Topic:** Redis Streams vs Pub/Sub vs Kafka
**Level:** Senior Interview (10+ YOE)

## Direct Answer
Redis Streams. Pub/Sub only delivers to subscribers that are connected at the exact moment of publishing — anything published while a subscriber is offline or restarting is gone forever. Streams retain entries and track per-consumer-group progress, so a restarted consumer can resume exactly where it left off.

## Easy Explanation
Pub/Sub is like a live radio broadcast: if your radio was off, you missed the news, permanently. A Stream is more like a voicemail inbox: messages wait for you, in order, until you actually listen to them and mark them heard. If "cannot lose messages" is a requirement, you need the voicemail inbox, not the live radio.

## Diagram
```
Redis Pub/Sub (fire-and-forget):
Publisher --PUBLISH--> [ no subscriber connected right now ] --> message is GONE

Redis Streams (durable + resumable):
Publisher --XADD--> [ Stream: retains entries ] --XREADGROUP--> Consumer
                                                        |
                                     consumer restarts, reconnects,
                                     resumes from its last un-acked ID
                                     (nothing is lost)
```

## Production Example
A notification service sends "your report is ready" emails triggered by backend events. Under Pub/Sub, a rolling deployment that restarts the email worker for even 10 seconds silently drops every notification published during that window — with no error, no alert, just missing emails. Switching the event source to a Redis Stream with a consumer group means the worker resumes from its last acknowledged ID after restarting, and no notification is skipped.

```bash
XADD report-events * userId 42 reportId 900
XGROUP CREATE report-events email-workers $ MKSTREAM
XREADGROUP GROUP email-workers worker-1 COUNT 10 STREAMS report-events >
```

## Why Interviewers Ask This
It's the single most common Redis architecture mistake: reaching for Pub/Sub because it's simpler, without realizing "simple" comes with "messages during downtime are silently lost." This question filters for engineers who match the tool to the durability requirement instead of to familiarity.
