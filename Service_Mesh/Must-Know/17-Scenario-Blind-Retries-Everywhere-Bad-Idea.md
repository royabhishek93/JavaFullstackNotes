# Scenario 3: A Junior Engineer Wants retries=5 on Every Service "For Safety"

**Interviewer:** "A new engineer says 'let's just add retries=5 to every service to make things more resilient.' What do you say?"

**You (15-yr Architect):**

I'd push back, and this is a case where mesh power needs architectural judgment. Blind retries on every service create two dangers:

1. **Retry storms** — if `payment-service` is overloaded (not crashed, just slow), and five upstream callers each retry 5 times, you just **5x'd the load** on an already struggling service — you made the outage worse, not better.
2. **Non-idempotent operations** — retrying a POST that creates an order or charges a card can create duplicates if the original request actually succeeded, but the response got lost in transit.

## Retry Storm Amplification (ASCII)

```
  payment-service overloaded, p99 = 4s
              |
              v
  5 callers each retry x5
              |
              v
  Load multiplies ~5x - 25x
              |
              v
  Service fully collapses --
  retries caused the outage, not prevented it
```

## The Correct Rule

My rule: retries only on **idempotent, safe** calls (GET, or POST with idempotency keys), with a **budget** (limiting total retry attempts and per-try-timeout), combined with circuit breaking so retries stop entirely once the callee is clearly unhealthy.

```
   Safe to retry blindly:        Requires idempotency key
   ---------------------         or must NOT retry:
   GET /product/123               ------------------------
   GET /cart                      POST /payment/charge
   HEAD /health                   POST /order/create
                                   PATCH /inventory/decrement
```

## Why This Matters for the Interview

> "Mesh-level retries must only be applied to idempotent operations, or safe HTTP methods like GET. For POST/payment operations, I explicitly disable retries at the mesh layer or ensure idempotency keys are used, because retrying a network timeout on a payment call could double-charge a customer if the original request actually succeeded server-side but the response was lost."

That's a trap disguised as a feature question — junior engineers say "retries = more resilience," architects say "retries need idempotency guarantees and a budget."

---
See also: [06-Trap-More-Retries-Always-Better.md](06-Trap-More-Retries-Always-Better.md)
