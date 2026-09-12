# Timeout Strategy: Too Short, Too Long — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 44

## HOOK (0:00–0:30)
[Shocking opening — a real outage, a real failure, a surprising number]

"Picture this: it's 2 AM. Your on-call phone goes off. Order Service is timing out. Checkout is down. The whole team scrambles, everyone assumes Order Service crashed. Thirty minutes of root-cause analysis later... Order Service was fine the entire time. The real villain? Payment Service quietly hung, and a sixty-second timeout let TWO HUNDRED THREADS pile up waiting for a response that was never coming. One bad timeout value took down your entire checkout flow. Today, we're fixing that — for good."

[Screen cue: Terminal-style dark screen with a fake PagerDuty alert: "🔴 Order Service — 504 Gateway Timeout" ticking up, then a red X over "Order Service" and a spotlight moving to "Payment Service — HUNG"]

## THE PROBLEM (0:30–2:00)
[Plain English — what breaks without understanding this concept]

"Every single network call in your system needs a timeout. The question nobody thinks hard enough about is: how long should it be?

Think about it this way — set it too short, and your caller gives up on a service that's actually fine. Say your service normally responds in 200 milliseconds, but every once in a while a garbage collection pause bumps that to 300 milliseconds. If your timeout is 250 milliseconds, the caller sees that as a failure. It retries. Now the service is doing the same work twice, for no reason. That's a false failure — a perfectly healthy service just got treated like it's dead.

Now flip it — set the timeout too long, and you get something much worse. Say your downstream Payment Service is overloaded or deadlocked, and you've got a 60-second timeout. Every single request that hits it just... waits. One thread stuck for 60 seconds. Then two. Then seventeen a second later. Within a few minutes, all 200 threads in your pool are stuck waiting on a service that's never going to answer. Your ENTIRE service — not just the payment part — grinds to a halt. That's a cascade failure, and it's one of the most common causes of 'mysterious' full outages in distributed systems.

So neither extreme works. We need to find the right number, and more importantly, understand that 'timeout' isn't even a single number — it's a whole system of layered decisions."

[Screen cue: Split-screen diagram — left side shows "TOO SHORT" with a clock icon flashing red at 250ms and a retry loop arrow; right side shows "TOO LONG" with a stack of thread icons piling up into a red overflow bar]

## THE SOLUTION (2:00–5:00)
[Step-by-step explanation. Cover ALL scenarios from the source file]

"Now watch what happens when we do this right. The golden rule: **your timeout should sit slightly above the 99th percentile latency of the downstream call, under normal operation.** If 99% of your Payment Service calls complete in 500 milliseconds, set your timeout at 750ms to 1000ms. That gives healthy variance enough room to breathe, while still failing fast the moment something is actually broken.

But here's the part most engineers miss — there isn't just ONE timeout per call. There are multiple layers, and you need to configure every single one of them.

Layer one: **Connection timeout** — the time it takes to establish the TCP connection itself. Typical value: 500ms to 2 seconds. If you can't even connect in that window, the server isn't reachable — no point waiting longer.

Layer two: **Read timeout** — the time to receive a response AFTER you're connected. Typical value: 1 to 5 seconds depending on the operation. This is your 'the server is hung' detector.

Layer three: **Total request timeout** — your overall end-to-end budget, covering retries and everything combined.

Then there's the database side. You've got **connection pool wait timeout** — typically 5 seconds with something like HikariCP — that's how long you wait just to grab a connection from the pool. Then **query timeout**, 5 to 30 seconds depending on the query. And **transaction timeout**, usually capped at 30 seconds, so a forgotten open transaction doesn't hold database locks forever.

And then, protecting yourself from the OTHER direction — upstream timeouts. Your API Gateway has its own timeout, typically 5 to 30 seconds for user-facing APIs, past which it just returns an HTTP 504. And don't forget your load balancer — AWS's Application Load Balancer defaults to a 60-second idle timeout.

Now here's the critical rule that ties it all together: these timeouts form a CHAIN, and parent timeouts must always be longer than child timeouts. If your API Gateway waits 29 seconds, and Order Service waits 25 seconds, and Payment Service waits 5 seconds — that's a sane chain. But get it backwards — say Payment gets 5 seconds but Order Service only waits 3 — and you get an orphaned call. Order Service gives up, but Payment Service is still chugging away in the background, completely unaware anyone stopped listening."

[Screen cue: Live-drawn diagram — nested boxes labeled "API Gateway (29s)" containing "Order Service (25s)" containing "Payment Service (5s)", with an arrow showing the timeout chain shrinking inward, then a broken-link icon showing what happens when the chain is inverted]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)
[Every trap, anti-pattern, edge case from the source file]

"Okay, let's go deep into the traps, because this is where the real interview questions live — and where real production incidents happen.

**Trap number one: Deadline propagation, or the lack of it.** Here's the scenario. Client gives your API Gateway a 10-second budget. Gateway calls Order Service — but doesn't tell it 'hey, you only have 10 seconds.' Order Service calls Payment Service — same problem, no budget passed along. Payment Service takes 7 seconds to actually process the payment. Order Service finally returns at the 9-second mark. But the API Gateway already gave up at 10 seconds and returned a 504 to the user. Here's the nightmare part — the payment WAS successfully processed. The user just got told it failed. So what do they do? They retry. And if you don't have an idempotency key on that payment call, congratulations, you just charged your customer twice.

The fix is deadline propagation — pass the actual deadline as a header, something like `X-Request-Deadline` with a Unix timestamp, all the way down the call chain. Before Order Service calls Payment, it checks: how much time is actually left? If it's less than 200 milliseconds, don't even bother calling — return an error immediately, because you know you won't get a useful answer in time. gRPC actually handles this natively through context deadlines. In plain HTTP, you either build this yourself or lean on a tracing library like Zipkin or Jaeger that propagates deadlines for you.

**Trap number two: treating timeout as an isolated decision.** A timeout by itself just tells you when to give up on ONE call. It does nothing to stop you from calling a broken service a thousand more times in the next minute. That's why timeout must always be paired with a circuit breaker. If, say, 50% of your last 10 calls to Payment Service timed out, the circuit opens. You stop calling Payment Service entirely and return a fallback — 'payment temporarily unavailable' — immediately, without even attempting the network call. That's what actually protects your thread pool from filling up.

**Trap number three: one-size-fits-all timeout values.** Engineers love picking one number and slapping it everywhere. But a fraud-scoring call that needs to happen in real time should time out at 500 milliseconds — if it's slow, just skip it. An S3 file upload might legitimately need 30 to 120 seconds because large files take time. A reporting query against your database might reasonably run for 30 to 300 seconds. Using the same timeout for all of these is either going to kill your slow-but-legitimate operations, or let your fast operations hang way too long.

**Trap number four: not distinguishing critical from non-critical calls at the API Gateway level.** Your `/checkout` endpoint — a critical write — deserves a generous 15-second timeout because it's worth retrying and getting right. Your `/recommendations` endpoint is optional — fail fast at 2 seconds, because showing an empty recommendations section is way better than making the whole page hang.

The rule of thumb to remember: for user-facing synchronous calls, use P99 latency plus 50% headroom. For background jobs, you can be more generous — P99 times 3, because they can tolerate the occasional slow run. And the one thing you should NEVER do — leave a call with no timeout at all. Unbounded wait always, eventually, becomes a cascade failure."

[Screen cue: Comparison table sliding in — columns: Service Call Type | Connection Timeout | Read Timeout | Notes — rows for Internal microservice, Payment gateway, Fraud scoring, Email service, S3 upload, DB OLTP query, DB reporting query, External geolocation API]

## REAL WORLD (8:00–9:30)
[2–3 Indian tech company examples with specific numbers]

"Let's ground this in real systems you've probably used this week.

Think about **Swiggy** or **Zomato** during a lunch-hour rush. The restaurant confirmation API has a strict total timeout — around 3 seconds. If the restaurant's system doesn't confirm the order in that window, the platform auto-accepts on the restaurant's behalf and fires off an SMS. And this is deadline propagation in action — if the overall order flow has a 5-second budget, 3 seconds go to the restaurant confirmation call, leaving exactly 2 seconds for driver assignment. No wasted time, no orphaned calls.

Now think about **Flipkart** or any large e-commerce platform during a big sale. The recommendation service — 'customers also bought' — gets a tight 200-millisecond timeout, because it's not critical. If it's slow, the section just doesn't render, and the user doesn't even notice. But the cart service? That's a 2-second timeout, because checkout absolutely must complete — that's revenue on the line.

And for **payment gateways** like the ones powering PhonePe or Paytm-style flows integrating with a bank — if the bank's SLA says P99 latency is 800 milliseconds, you don't set your timeout at 800ms flat. You add the buffer: 1200 milliseconds, that's P99 plus 50%. Set it at a tight 200ms instead, and you'll see false failures on totally legitimate slow payments during peak traffic. Set it at 10 seconds instead, and every failed payment now occupies a thread pool slot for 10 full seconds — and that's exactly how thread pool exhaustion cascades happen at scale, during the exact moment — a big sale, a payday — when you can least afford it."

[Screen cue: Company logo cards — Swiggy/Zomato with "3s restaurant confirmation, 5s total budget", Flipkart-style e-commerce with "200ms recommendations vs 2s cart", Payment gateway with "P99=800ms → timeout=1200ms"]

## OUTRO + NEXT EPISODE (9:30–10:00)
[Subscribe hook. Tease next episode]

"So here's your takeaway: timeout isn't a single guess, it's a system — connection timeout, read timeout, deadline propagation, and a circuit breaker working together. Get it right, and a hung downstream service becomes a graceful, contained failure instead of a 2 AM cascade.

If this saved you from a future outage, hit subscribe — we're going through the entire system design interview playbook, one pattern at a time. And speaking of patterns that pair PERFECTLY with today's episode — what do you do the moment a call times out? Do you just give up? Do you retry immediately and make things worse? That's exactly what we're covering next, in Episode 45: Retry, Exponential Backoff, and Jitter. See you there."

[Screen cue: Subscribe button animation + next episode card: "Episode 45 — Retry, Exponential Backoff & Jitter"]
