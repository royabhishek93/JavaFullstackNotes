# Observability: Metrics, Logs, Traces & SLI/SLO/SLA — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE

## HOOK (0:00–0:30)

"Customers report checkout is 'sometimes slow.' You've got 15 microservices. Where do you even start?"

That's a real interview question, and it's also a real 2 A.M. page. Here's the number that should scare you: one single fraud-scoring dependency, buried three services deep, can eat 190 milliseconds out of a 280 millisecond checkout request — and if you're just grepping logs across 15 services with no shared ID, you will NOT find it in time. You'll be guessing at timestamps while your error budget burns.

By the end of this video, you'll know exactly which of the three observability pillars to reach for, in what order, and how to turn "let's be more careful" into an actual number you can page on.

**Screen cue:** Title card — "METRICS vs LOGS vs TRACES" with a giant "280ms" ticking down, then freezing on a red "190ms — root cause" callout.

---

## THE PROBLEM (0:30–2:00)

Here's the thing — most engineers think observability is "add some logging and maybe a dashboard." That's not observability, that's a security blanket. It falls apart the second something goes wrong across service boundaries, which — in a microservices world — is basically every incident.

Think about a hospital patient hooked up to a monitor. The bedside screen shows one number updating every second: heart rate, 72 BPM. That's cheap, it's real-time, and it tells you WHAT is happening — is it climbing, dropping, flatlining. But it never tells you WHY. That number alone can't tell you the patient reported chest pain at 2:14 PM.

For that, you need the nurse's handwritten chart notes — timestamped, detailed, specific. Rich context, but expensive, and useless if you don't already know roughly when and where to look.

Now the hard part: this ONE patient's heart rate spiked at 2:14 PM. Walk me through everything that happened to THIS SPECIFIC PATIENT — across the ER, radiology, and the pharmacy — in the exact causal order it happened. Neither the heart monitor nor the chart notes alone can do that. You need to stitch together every department's notes, tied to the same patient ID, in order.

That's the entire observability problem in one sentence: metrics tell you something's wrong right now, logs tell you the details of one specific thing, and neither one tells you WHERE in a chain of a dozen services the problem actually started. And log-grepping across twelve services manually? That simply does not scale.

**Screen cue:** Split-screen diagram — a heart monitor (single number, "72 BPM") on the left, a stack of handwritten chart notes in the middle, and a tangled line connecting five hospital department icons on the right, all converging on one red "?" — showing no single view connects them.

---

## THE SOLUTION (2:00–5:00)

So here's how the three pillars actually work together, step by step, using a real checkout request.

**Step 1 — Metrics fire the alert.** A metric is a numeric time series — cheap to store, cheap to alert on. Something like `payment_service_p99_latency_ms > 500` for 5 consecutive minutes trips a PagerDuty alert, and an on-call engineer gets paged. Fast, coarse, real-time. This is always where you start, because it's the cheapest signal that confirms something is actually wrong.

**Step 2 — Distributed tracing tells you WHERE.** Every request carries a trace ID from the very first hop. Picture a `GET /checkout` request. It hits the Gateway — 12ms. The Gateway calls Order Service — 45ms — which calls Inventory Service — 8ms. In parallel, it calls Payment Service — 210ms, the slow one — which itself calls Fraud Service — 190ms. And it fires off Notification Service — 5ms, fire-and-forget. Total request latency: 280ms.

Without tracing, that's logs from five separate services, no shared correlation ID, and manual timestamp-guessing across services that don't even agree on the clock. WITH tracing, you run one query — "show me trace 4bf92f..." — and the waterfall view immediately shows the fraud-score span, 190ms, nested inside the charge-card span, 210ms. The bottleneck is obvious in seconds, not hours.

**Step 3 — Logs give you the exact detail, once you know where to look.** Now that tracing narrowed it down to fraud-service, you pull its logs for that exact time range and trace ID: "Fraud service call timed out after 200ms, falling back to synchronous manual review queue." That tells you WHAT happened at that exact timestamp — but notice, you only got here because tracing told you WHERE to look first.

**Step 4 — Confirm the root cause with pattern, not a single data point.** Query 50 more traces from the same window. If EVERY fraud-score span in that period is running 150 to 200ms, up from a normal baseline of 20ms, that's not a fluke — that points straight at fraud-service's OWN dependency, maybe its database, maybe a downstream ML model endpoint, as the true root cause.

**Step 5 — Frame it against your SLO, not just "slow."** An SLI is your actual measured number — say, 99.95% of requests in the last 28 days completed under 200ms. An SLO is the internal target you hold yourself to. An SLA is the external, contractual promise to customers — deliberately looser than your SLO, so your own alarm fires before you've actually broken your promise to a paying customer. And the gap between perfect and your SLO target? That's your error budget — a deliberately allowed amount of imperfection.

**Screen cue:** Live-draw the trace waterfall — Gateway 12ms, Order Service 45ms with a nested Inventory Service 8ms bar, Payment Service 210ms bar with a nested Fraud Service 190ms bar highlighted in red, Notification Service 5ms bar off to the side. Then draw the SLI/SLO/SLA nested-circle diagram with the error budget as the gap between the outer and middle rings.

---

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Alright, let's talk about the traps, because this is where interviews — and production — separate people who've actually operated this stuff from people who read one blog post.

**Trap #1 — Head-based sampling misses the exact request you need.** Head-based sampling decides "trace this or not" at the very START of the request — say, a random 1%, or 100% of requests carrying a debug header. It's simple and cheap. But you might sample OUT the exact 1-in-10,000 request that later turns out to have errored. You threw away the one trace you actually needed.

**Trap #2 — Tail-based sampling fixes that, but it's not free.** Tail-based sampling buffers ALL the spans for a request temporarily, and only decides whether to KEEP the full trace AFTER the request completes. Always keep traces that errored or blew past a latency threshold, and randomly sample just 1% of the boring, everything-was-fine traces. Much better signal for debugging real problems — but it requires buffering every request's spans and adds a whole collector-side complexity and cost layer you have to run and pay for.

**Trap #3 — High-cardinality metric labels blow up your bill.** This is a genuinely common real production mistake: someone adds a `userId` label onto a metric. Now that metric has millions of unique label values. That can blow up your metrics backend's storage and query cost by orders of magnitude. High-cardinality data belongs in logs and traces — NOT in metric labels. Metrics want low-cardinality dimensions: service name, status code, region. Not user IDs.

**Trap #4 — You can't afford to keep logs forever, and you shouldn't try.** Raw logs at high volume are typically retained only 7 to 30 days hot and searchable, then archived to cold, cheap storage after that — because keeping full-fidelity logs at metric-like durations, months or years, is cost-prohibitive at scale. If your retention policy assumes logs behave like metrics, your storage bill will teach you otherwise.

**Trap #5 — Flat threshold alerts miss slow-burning disasters.** A flat alert like "latency over 500ms for 5 minutes" is fine for a sudden spike. But burn-rate alerting is smarter: "alert if we're consuming error budget fast enough that we'd exhaust the ENTIRE month's budget in under 6 hours at the current rate." That single rule catches both a sudden severe outage AND a slow, creeping degradation — at different severities. Fast burn pages someone right now. Slow burn just files a ticket for tomorrow.

**Trap #6 — Treating the error budget as a vague feeling instead of a number.** Let's do the actual math, because this is where it gets real. SLO: 99.9% of requests succeed over a rolling 30-day window. That means your allowed error budget is 0.1% of requests — which works out to 43.2 minutes of full-downtime-equivalent per 30 days. Now imagine day 1 through 20 are steady state, minor blips, 10 minutes consumed — that's 23% of budget gone. Then on day 21, a major incident burns 25 more minutes. You're now at 35 minutes consumed — 81% of the ENTIRE month's budget — with 9 days still left to go. Only 8.2 minutes of budget remain for the rest of the month. Some teams adopt a hard rule right here: budget remaining under 20% means you freeze non-critical deploys and prioritize reliability work until the 30-day window rolls forward and the budget resets. That's a data-driven version of "let's be careful," not a vague policy nobody actually follows.

**Screen cue:** Comparison table — Head-based sampling vs Tail-based sampling (cost, accuracy, complexity). Then a burn-down bar chart: 43.2-minute budget draining from 100% to 19% by day 21, with a red "FREEZE DEPLOYS" line drawn at the 20% mark.

---

## REAL WORLD (8:00–9:30)

Let's ground this in scale you'd actually see at an Indian tech company.

Picture a Swiggy-scale food delivery platform during a Friday night dinner rush — call it 40,000 requests per second across order placement, restaurant matching, and payment. Their payment service alone spans a chain of 6 microservices. With head-based sampling at just 2%, they were missing the exact failed-payment traces support tickets referenced. Switching to tail-based sampling — always keep errors and anything over 400ms, sample only 1% of the rest — meant 100% of actual incidents had a full trace, at roughly a 15% increase in collector infra cost. That trade was an easy yes.

Now picture a Paytm-style payments platform running an SLO of 99.95% success on UPI transaction processing, with an SLA of 99.9% to merchant partners. That 0.05% gap is deliberate — it's roughly 20 minutes of monthly error budget that exists purely so their own PagerDuty fires before they owe a merchant a service-credit conversation. When a partner bank integration degraded for 40 minutes one month, that single incident consumed the ENTIRE month's error budget in one shot — and it triggered an automatic freeze on non-critical deploys for the remaining 11 days of that billing cycle.

And picture a Zomato-scale team that got burned by cardinality: an engineer added a `userId` label to a request-latency metric to debug one customer's complaint. Within days, that single metric's unique time-series count went from about 500 to over 2 million, and their metrics backend bill for that one namespace jumped roughly 8x in a month before anyone caught it. The fix: userId moved to log and trace context, never a metric label, ever again.

**Screen cue:** Three company-style cards side by side — "40K req/s, tail-sampling, 100% incident trace capture" / "99.95% SLO vs 99.9% SLA, 20 min/month budget" / "500 → 2M time series, 8x cost spike" — each with a small logo-style badge and the number highlighted in red.

---

## OUTRO + NEXT EPISODE (9:30–10:00)

So next time someone says "it's slow," you now know the order of operations: metrics to confirm it's real and see the trend, tracing to find WHICH of your services is actually the bottleneck, logs to get the exact detail once you know where to look, and your SLO and error budget to decide whether this is a "fix it eventually" ticket or a "page right now" incident.

If this helped you connect metrics, logs, and traces into one mental model instead of three separate tools, hit subscribe — next episode, we're going deep on chaos engineering: how companies deliberately break their own production systems to find the failures before their customers do.

I'll see you in the next one.

**Screen cue:** End card — subscribe button animation, thumbnail preview of "Chaos Engineering" episode with a cracked-server icon.
