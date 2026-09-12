# #146 — APM-First Triage (Datadog / New Relic / Dynatrace) Before Touching CLI Tools

> **Category:** Modern Observability (2026) | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know (2026 additions)

## 🗣️ The Interview Question
"3 AM page: p99 latency alert fires for `checkout-service`. Your company runs Datadog APM (or New Relic / Dynatrace). Walk me through your first 5 minutes — before you'd even consider SSHing in to run `jstack`."

## 😊 Explain It Simply (for anyone)
Imagine a patient is wheeled into the ER unconscious. A good doctor doesn't immediately grab a scalpel — they first check the vitals monitor that's already been recording heart rate, oxygen, and blood pressure for the last hour, because that chart already narrows down what's wrong before any invasive step. An APM tool is that vitals monitor for your service: it's already been recording every request's timing, every database call, every JVM metric, continuously, before the page ever fired. SSH-ing in and running `jstack` blind is like skipping the chart and going straight to exploratory surgery — sometimes necessary, but only after you've read what's already been recorded.

## 📊 Visualize It
```
Alert fires (p99 > 2s, checkout-service)
        │
        ▼
1. APM Service Page          → latency graph + deploy markers overlaid
        │  (correlate: did this start right after a deploy?)
        ▼
2. Trace Explorer             → filter: service:checkout status:error OR duration:>2s
        │  (which span dominates? DB? downstream HTTP? GC?)
        ▼
3. Runtime Metrics tab         → heap, GC pause %, thread count — zero SSH
        │  (JVM metrics shipped automatically via the APM agent's JMX hook)
        ▼
4. Continuous Profiler flame graph → for THAT pod, THAT 2-minute window
        │  (only if steps 1-3 didn't already explain it)
        ▼
5. SSH + jstack/jcmd            → only if APM data is inconclusive or needs live confirmation
```

## 🏭 The Real Production Answer (15-YOE Level)
"I don't reach for `jstack` first — that's a 2015 reflex. In 2026, the APM agent has already been recording continuously, so the first five minutes are entirely in the dashboard:

**1. Service page + Deployment Tracking:** Open the Datadog APM service page for `checkout-service`. The very first thing I check is whether the deploy markers line up with when the latency graph started climbing — a huge fraction of 'mystery' incidents are just an undetected bad deploy. `DD_VERSION`/`DD_ENV` tags let Datadog draw this correlation automatically.

**2. Trace Explorer, not logs:** I filter `service:checkout-service (status:error OR @duration:>2s)` in Trace Explorer and open one of the slow traces. The trace waterfall shows me exactly which span dominates the 2 seconds — a downstream HTTP call to `payment-service`? A specific SQL query? Time spent 'between spans' (a strong hint of GC pause or thread pool queueing, not application code). This one waterfall view often replaces what used to take a manual thread dump correlation.

**3. Runtime Metrics tab (zero SSH):** Datadog's `dd-trace-java` (or New Relic's Java agent, or Dynatrace OneAgent) auto-instruments JVM metrics via JMX under the hood and ships them continuously — heap usage per generation, GC pause time and frequency, live thread count, thread pool queue depth. I can already see 'GC pause time spiked to 40% of wall clock at 03:02' without touching a terminal — that alone often tells me it's file #040's p99-correlates-with-GC pattern, not a code bug.

**4. Continuous Profiler (if enabled):** if `DD_PROFILING_ENABLED=true` was set on the agent (or the New Relic/Dynatrace equivalent), I pull the flame graph for that exact pod during that exact window — this is the zero-touch equivalent of file #084's live Arthas trace, because these vendor profilers literally wrap async-profiler + JFR under the hood for Java.

**5. Only then, SSH:** I drop to `jcmd`/`jstack`/a fresh JFR recording only if the APM data is inconclusive, or if I need to confirm a hypothesis with a live heap histogram (`jcmd <pid> GC.class_histogram`) that the APM tool doesn't expose, or if I suspect the APM agent itself is adding overhead that's masking the real signal.

**Real gotchas I flag proactively in interviews:**
- APM agent overhead is real, typically 1–3% CPU for `dd-trace-java` with default settings — teams sometimes disable full request/response body capture to reduce it, which then limits what you can see later.
- Trace sampling matters: Datadog's default is **head-based sampling** (a small % of traces kept, decided at the start of the request) — if your slow outlier wasn't sampled, it doesn't show up in Trace Explorer, only in the aggregated latency metric. This is exactly why file #147 exists — a green dashboard doesn't always mean nothing's wrong."

## 🔑 Key Takeaway
In a modern stack, the first move on a paged incident is the APM dashboard (deploy correlation → trace waterfall → JVM runtime metrics → continuous profiler flame graph), not a blind SSH+`jstack` — CLI tools are for confirming a hypothesis or filling a gap the APM agent's sampling/overhead trade-offs left uncovered.
