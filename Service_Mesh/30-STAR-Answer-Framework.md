# How to Answer Scenario Questions in the Real Interview (STAR, Adapted)

**Mentor:** One final coaching note before you walk in. At the 15-year mark, interviewers aren't testing whether you know what `istiod` stands for — they're testing whether you've **actually operated** these systems under pressure, and whether you can **reason about trade-offs out loud**. Structure every scenario answer like this:

```
  Situation                    Trade-off                     Decision                        Result/Guardrail
  (1 sentence: what   -->      (What are the 2      -->      (What did you configure/  -->    (How did you verify
   was the system/              competing concerns?)          design and WHY)                   it worked, or what
   context)                                                                                      would you monitor
                                                                                                  going forward)
```

## Worked Example (applied to "blind retries=5 everywhere")

- **Situation:** "We had a junior engineer suggest blanket retries=5 across all services."
- **Trade-off:** "Retries improve resilience against transient blips, but blindly applied they can amplify load on an already-struggling service and risk duplicate side effects on non-idempotent calls."
- **Decision:** "I scoped retries only to safe/idempotent operations, added per-try timeouts and a retry budget, and paired it with outlier detection so a genuinely unhealthy instance stops receiving traffic instead of getting hammered by retries."
- **Result:** "We validated this with fault injection in staging before rolling to prod, and we alert on retry-amplification ratio in Grafana so we catch this pattern early if it recurs."

## Why This Structure Works

That four-beat structure — **say the constraint, not just the solution** — is what makes an answer sound like 15 years of production battle scars instead of a blog-post summary.

## Checklist Before You Answer Any Scenario Question

1. Restate the situation in one sentence — proves you understood the question correctly.
2. Name the **competing concern** explicitly (e.g., "resilience vs amplification risk," "latency vs consistency," "simplicity vs blast-radius control"). This is the single biggest signal of seniority — junior answers skip straight to the solution.
3. State your decision **and the reason**, not just the mechanism ("I set a timeout" is weak; "I set a 2s timeout because the caller's own SLA budget only allows 2.5s total, and I wanted headroom for its own downstream retry" is strong).
4. Close with how you'd **verify or monitor** it — shows you don't consider the job done at "configured," but at "proven to work and observable going forward."

Good luck.

---
Back to [`00-Index.md`](00-Index.md) · [`29-Cheat-Sheet.md`](29-Cheat-Sheet.md)
