# Observability: Metrics, Logs, Traces & SLI/SLO/SLA — LinkedIn Post

## Post Text (copy-paste ready)

One fraud-check call ate 190ms of a 280ms checkout — and log-grepping 15 services never would've found it.

- Metrics tell you something's wrong RIGHT NOW (cheap, fast, coarse) — but never WHY.
- Logs give rich detail on ONE event — but only if you already know where to look.
- Distributed traces carry one trace ID across every service hop, so a single waterfall view shows exactly which nested span (e.g. fraud-score, 190ms inside a 210ms payment call) is the real bottleneck.
- Head-based sampling can silently throw away the 1-in-10,000 request that actually errored; tail-based sampling buffers everything and keeps only errors/slow traces — better signal, real infra cost.
- A `userId` label on a metric isn't harmless — one team saw a single metric's time-series count jump from 500 to 2M and their bill spike ~8x. High-cardinality data belongs in logs/traces, never metric labels.
- SLO 99.9% = 43.2 minutes of error budget per 30 days. Burn 81% of it in one bad day, and "budget < 20% → freeze non-critical deploys" turns "let's be careful" into an actual number.

Swipe → to see the trace waterfall, the sampling comparison, and the exact error-budget math.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Metrics say something's wrong. Traces say where. Logs say why. Here's the exact order engineers actually use them. 🎥👇

### Variant B — Long (400-600 chars)
"Checkout is sometimes slow" across 15 microservices is unsolvable by grepping logs alone. The fix: metrics confirm it's real (p99 > 500ms, 5 min → page), tracing narrows it to ONE service via a shared trace ID (fraud-score span = 190ms inside a 210ms payment call), then logs give the exact error once you know where to look. Add SLO-based error budgets (99.9% = 43.2 min/month) and burn-rate alerts, and "be careful" becomes a number you can page on. Full breakdown + real cardinality-cost disaster in the carousel.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (commute scroll window for Indian tech audience, before standups)

## Engagement Hook
Which one do you reach for first when a customer says "it's slow" — metrics, logs, or traces? And has a `userId` label ever blown up your metrics bill?
