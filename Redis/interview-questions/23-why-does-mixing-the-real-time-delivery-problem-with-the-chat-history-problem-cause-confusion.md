# Why does mixing the real-time delivery problem with the chat-history problem cause confusion?

**Type:** Trap Question
**Topic:** Redis vs Kafka — Problem Decomposition
**Level:** Senior Interview (8–12+ YOE) — common gotcha

## Direct Answer
Because the two problems have fundamentally different, sometimes conflicting requirements — real-time delivery cares about *speed* and can tolerate loss for offline users; chat history cares about *permanence* and must never lose anything. Trying to satisfy both with one mechanism forces awkward compromises (like treating a fire-and-forget Pub/Sub channel as if it were a durable log), and the resulting bugs are confusing precisely because they look like "sometimes it works, sometimes it doesn't," when really two unrelated requirements were bolted onto one tool.

## Easy Explanation
It's like trying to use a whiteboard as both "today's quick reminders" (fine, gets erased, no big deal) and "our permanent company history" (bad idea, it gets erased!). The whiteboard isn't broken — it's being asked to do two jobs that need different tools. Once you separate them — a whiteboard for quick notes, a filing cabinet for permanent records — both jobs get done properly, and the confusing "why did our history randomly disappear" question goes away entirely.

## Diagram
```
Mixed (confusing) design:
  Pub/Sub channel used for BOTH live delivery AND assumed history
        |
        v
  "why did user X's chat history have gaps?"
        |
        v
  because Pub/Sub never stored anything -- any message published while
  X was briefly offline was simply never in "history" to begin with
  (the bug LOOKS random, but it's a predictable consequence of misusing the tool)

Separated (clear) design:
  Pub/Sub  -> ONLY live delivery, no permanence expected, no confusion
  Database -> ONLY history, always complete, independent of who was online when
```

## Production Example
A team debugging "random" missing messages in chat history spent significant time suspecting network issues, client bugs, and race conditions — before realizing the actual root cause was architectural: history was being reconstructed purely from what Pub/Sub happened to deliver to a logging subscriber, which itself was subject to the exact same "must be connected to receive it" limitation as any other Pub/Sub subscriber. Once history was moved to its own dedicated, always-persisted store, the "randomness" disappeared completely — because it was never actually random.

## Why Interviewers Ask This
It tests systems-thinking: can the candidate recognize when a single confusing symptom is actually the predictable result of conflating two different problem statements, and fix it by separating concerns rather than patching symptoms?
