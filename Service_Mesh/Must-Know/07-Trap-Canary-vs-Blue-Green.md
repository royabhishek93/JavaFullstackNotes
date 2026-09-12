# Trap 11: "Canary Deployment and Blue-Green Deployment Are Basically the Same Thing, Right?"

**Interviewer:** "A canary deployment and a blue-green deployment are basically the same thing, just different names, right?"

**Correct Answer: No.**

```
  CANARY DEPLOYMENT                       BLUE-GREEN DEPLOYMENT
  ------------------------                 ------------------------
  Both versions run                        BOTH full environments exist
  SIMULTANEOUSLY, receiving                (blue = old, green = new)
  LIVE traffic CONCURRENTLY

  Traffic shifted GRADUALLY,               Traffic switched ALL-AT-ONCE
  by PERCENTAGE                            (atomic cutover)
  (e.g. 90% v2 / 10% v3)                    typically at load balancer/DNS level

  Enabled by: mesh-based                   Enabled by: swapping which
  weighted traffic-splitting               full environment receives
  (VirtualService / service resolver)      100% of traffic

  Benefit: fine-grained blast-radius       Benefit: instant, atomic
  control + real production signal         rollback (just switch back)
  at low risk

  Downside: takes longer to fully          Downside: no gradual validation
  roll out; requires monitoring            window before 100% of users
  during the gradual ramp                  hit the new version
```

**Canary** = gradual **percentage-based traffic shifting** to a new version while both versions run simultaneously and receive live traffic concurrently. **Blue-Green** = **both full environments exist**, but traffic is switched **all-at-once** from old (blue) to new (green).

Mesh-based traffic splitting is specifically what makes canary practical **without needing two full parallel environments** — you just need enough replicas of the new version to handle whatever percentage you're routing to it.

## Why This Trap Exists

Both patterns are "safe deployment strategies," and people who've only read summaries conflate them. The distinguishing detail — **gradual percentage-based** vs **all-at-once atomic switch** — is exactly what an architect should articulate precisely, along with when you'd choose one over the other (canary for validating behavior with real traffic gradually; blue-green when you need instant, guaranteed rollback and don't need gradual validation).

---
See also: [18-Scenario-Canary-Rollout-Undetected-Error-Spike.md](18-Scenario-Canary-Rollout-Undetected-Error-Spike.md), [`Diagram-05-Canary-Traffic-Split.drawio`](../Diagram-05-Canary-Traffic-Split.drawio)
