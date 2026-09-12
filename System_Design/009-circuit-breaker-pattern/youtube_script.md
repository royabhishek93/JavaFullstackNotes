# Circuit Breaker Pattern — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 10 of 20

## HOOK (0:00–0:30)
"Your Order Service has two hundred threads. Notification Service, which it calls to send confirmation emails, starts responding in thirty seconds instead of two hundred milliseconds. Twelve seconds later, every single one of those two hundred threads is blocked waiting on Notification Service — and new orders start timing out with 504 errors. Nothing is wrong with your order logic. A slow EMAIL service just took down checkout. Today I'm showing you the circuit breaker pattern that stops this exact cascade."

[Screen cue: A thread-pool counter climbing from 0 to 200 over 12 seconds, all going red, then a "504 GATEWAY TIMEOUT" banner.]

## THE PROBLEM (0:30–2:00)
"Think about it this way — this is cascade failure, and it's one of the most common causes of a total outage that started as a minor, unrelated slowdown. The circuit breaker pattern comes from electrical engineering: when a circuit gets overloaded, a physical breaker trips, opening the circuit to protect everything downstream from it. A software circuit breaker does the same thing — when a downstream service is failing, it stops even TRYING to call it, and instead returns an error or a fallback immediately. No thread waits thirty seconds for a timeout. No thread pool gets exhausted. And after a cooldown period, the circuit tries the service again to check if it's recovered."

[Screen cue: Draw a physical circuit breaker flipping open next to a software service diagram doing the same thing.]

## THE SOLUTION (2:00–5:00)
"Now watch the three states in action. CLOSED is normal operation — requests flow through to Notification Service, and the circuit breaker silently counts failures in the background. Say five failures happen within sixty seconds — the circuit trips to OPEN. In the OPEN state, every single request fails INSTANTLY, without even attempting to call Notification Service — no thread is blocked for thirty seconds, order processing continues completely normally, and email notifications are simply queued for retry later. After a wait timeout, say thirty seconds, the circuit moves to HALF-OPEN — a probe state where exactly one request is allowed through as a test. If that probe succeeds, the circuit closes and normal traffic resumes. If it fails, the circuit goes straight back to OPEN and waits another thirty seconds before trying again. In Resilience4j, this is configured with a failure rate threshold — say fifty percent of the last ten calls — a slow-call duration threshold marking anything over two seconds as effectively a failure, and a wait duration in the open state before the next probe."

[Screen cue: Draw the three-state machine — CLOSED → OPEN → HALF-OPEN → CLOSED — with the exact trigger condition labeled on each arrow.]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)
"Here's the trap: engineers add a circuit breaker and think they're done — but a circuit breaker without a fallback is useless, because you've just replaced 'slow error' with 'fast error,' and the user experience is still broken. Every circuit breaker needs a paired fallback: return cached data, return a sensible default, enqueue the request for later retry via Kafka or SQS, or fail-open by allowing the request through with reduced functionality. The deeper architectural fix, though, is realizing that email confirmation should never have been in the critical path of order placement in the first place — saving the order to the database is what makes an order 'placed,' not sending an email about it. The real fix: Order Service saves the order, publishes an OrderPlaced event to Kafka, and returns success to the user immediately. A separate Notification Consumer reads that event and calls Notification Service asynchronously — even if Notification Service is down for an entire hour, the Kafka consumer just keeps retrying, and order placement is never blocked at all. Circuit breakers are for the cases where a synchronous call genuinely can't be avoided — like calling a fraud-scoring service before approving a payment — where the correct fallback in the OPEN state might be 'allow with monitoring' rather than blocking every payment because fraud-scoring happens to be slow right now."

[Screen cue: Side-by-side — synchronous call with circuit breaker + fallback vs the async Kafka event pattern that avoids needing a circuit breaker at all.]

## REAL WORLD (8:00–9:30)
"Think about a notification system behind a platform like Swiggy or Zomato — when FCM push notifications slow down, a circuit breaker prevents that slowness from degrading in-app and SMS notification channels too, keeping them isolated and healthy. Think about a payment system like PhonePe calling a fraud-detection service — if fraud-detection is overloaded, the circuit opens and falls back to a cached ML risk score instead of blocking every payment on a slow synchronous call. And think about a food-delivery order flow, similar to Zomato or Swiggy, where the order service calls a restaurant's confirmation API — if that restaurant's system is down for maintenance, the circuit opens, the order gets auto-accepted, and the restaurant is notified separately via SMS, so the customer never even sees that outage."

[Screen cue: Three logo-style cards — "Swiggy/Zomato: notification channel isolation", "PhonePe: fraud-check fallback to cached score", "Zomato/Swiggy: restaurant API outage invisible to customer".]

## OUTRO + NEXT EPISODE (9:30–10:00)
"So remember: circuit breakers stop cascade failure by failing fast instead of failing slow, but they only work when paired with a real fallback — and the best fix is often making the call async in the first place so you never needed a circuit breaker at all. That wraps our first ten episodes covering the must-know and should-know system design foundations — subscribe so you don't miss the next batch covering messaging, search, and real production incident stories."

[Screen cue: "10 EPISODES DOWN — MORE COMING" title card with subscribe button animation.]
