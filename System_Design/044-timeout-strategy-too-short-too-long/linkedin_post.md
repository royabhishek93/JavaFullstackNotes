# Timeout Strategy: Too Short, Too Long — LinkedIn Post

## Post Text (copy-paste ready)

A 60-second timeout let 200 threads pile up waiting on a hung service — and took down checkout entirely.

- Too short: a healthy 200ms service that occasionally hits 300ms gets treated as "dead" → unnecessary retries → doubled load
- Too long (60s timeout): every hung request holds a thread → 200 threads exhaust the pool → full cascade failure
- The fix: set timeout at P99 latency + 50% buffer, not a guess
- Timeout chain rule: parent timeout MUST be longer than child (API Gateway 29s → Order Service 25s → Payment Service 5s) — invert it and you get orphaned calls
- No deadline propagation = a payment can succeed downstream while the user sees a 504 and gets double-charged on retry

Swipe → to see: the timeout layers (connection/read/DB/gateway), the deadline propagation fix, and the exact timeout values used for payment, fraud scoring, and recommendation services.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Your 60s timeout is why 200 threads just froze your checkout. Here's the right way to set timeouts (P99 + buffer). 🎥👇

### Variant B — Long (400–600 chars)
Most engineers pick a timeout value by guessing. That's how a hung Payment Service ends up exhausting 200 threads and taking down your entire Order Service — even though Order Service itself was completely fine.

The right approach: set timeout at P99 latency + 50% buffer, configure connection/read/DB timeouts separately, enforce the parent-timeout-longer-than-child rule across your service chain, and propagate deadlines so a client that already gave up doesn't leave orphaned calls running downstream (which is how double-charges happen). Pair every timeout with a circuit breaker. This is the exact framework interviewers expect when they ask "what timeout would you set for this call?"

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (commute scroll time for Indian tech professionals before standups)

## Engagement Hook
What's the worst outage you've seen caused by a timeout that was either way too short or way too long? Drop the war story below.
