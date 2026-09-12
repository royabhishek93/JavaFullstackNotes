# #75 — Full GC is always a production incident

> **Category:** GC Tuning & Debugging | **Type:** Senior Trap Question | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Full GC is always a production incident, right?"

## 😊 Explain It Simply (for anyone)
Imagine a restaurant that briefly closes its doors for 10 seconds to do a deep clean — if that happens during the busy dinner rush with customers waiting, it's a disaster and complaints pour in. But if that same 10-second closure happens at 3am when the restaurant is closed anyway for overnight prep work, literally nobody notices or cares. The "closure" itself (a Full GC, where the whole program pauses to do a big cleanup) isn't inherently good or bad — what matters entirely is *who's waiting on the other side* and *what they expect*. An interactive app serving live customer requests can't tolerate even a half-second pause without causing timeouts and errors. An overnight batch job that has hours to finish its work barely notices a 10-second pause once per hour.

## 📊 Visualize It
```
Same event: Full GC pause = 10 seconds

Interactive API (SLA: 200ms):     🚨 CRITICAL INCIDENT (many timeouts)
Nightly ETL job (runs 4 hours):   😐 rounding error, job still finishes on time
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG. The experienced answer:**

> Full GC is catastrophic for latency-sensitive services. For batch jobs, it's often completely acceptable — and sometimes desirable. A batch job that processes 10 million records and does one Full GC to compact the heap before shutting down is fine.
>
> The question to ask is: what is the pause SLA? For an interactive API, even a 500ms GC pause can violate SLAs and cascade into timeouts. For a nightly ETL that runs for 4 hours, a 10-second Full GC once per hour is a rounding error.
>
> When an architect says "we need to eliminate Full GC," the first question should be "what's the SLA?" — not "okay, let's switch to ZGC."

## 🔑 Key Takeaway
Whether a Full GC is an incident depends entirely on the workload's pause SLA — always ask "what's the SLA?" before reaching for a GC-switching fix.
