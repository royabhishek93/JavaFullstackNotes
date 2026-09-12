# Trap 6: "More Retries Always Means More Resilience, So Let's Set Retries High Everywhere"

**Interviewer:** "More retries always means more resilience, so let's set retries to a high number everywhere for safety."

**Correct Answer: No.**

```
  A service that's SLOW/overloaded (not crashed) --
  gets hit with high retry counts from every caller
                |
                v
  Each caller retries multiple times per failed request
                |
                v
  Load on the already-struggling service MULTIPLIES
  (5 callers x 5 retries = up to 25x the original load)
                |
                v
  Service fully collapses --
  retries caused the outage, not prevented it
  ("retry storm")
```

High retry counts on a struggling service cause **retry storms** that amplify load and can turn a partial degradation into a full outage. Retries must be paired with **circuit breaking**, sane **timeouts**, and **idempotency guarantees** — retrying a non-idempotent operation (like a payment charge) can also cause duplicate side effects if the original request actually succeeded but the response was lost.

## The Correct Framing

```
  Safe to retry aggressively:      Requires idempotency key
  ----------------------------      or should NOT be retried:
  GET requests                      POST /payment/charge
  Idempotent PUT                    POST /order/create
  Health checks                     Any non-idempotent write
```

## Why This Trap Exists

It sounds like a purely positive, low-risk resilience improvement — "more retries = more robust" is intuitive but wrong once you consider system-wide load dynamics under partial degradation, not just single-request success rates.

---
See also: [17-Scenario-Blind-Retries-Everywhere-Bad-Idea.md](17-Scenario-Blind-Retries-Everywhere-Bad-Idea.md)
