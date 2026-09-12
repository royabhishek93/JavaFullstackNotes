# Deployment Strategies & Chaos Engineering: Shipping Safely at Scale
### How to change production code for millions of users without them noticing — until you want them to

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a restaurant that wants to switch its entire kitchen to a new recipe and a new head chef. The reckless approach: close the old kitchen at midnight, open the new one at 6AM, and hope nothing's wrong when the breakfast rush hits. If the new chef burns the eggs, every single customer that morning gets a bad meal before anyone notices. Real restaurants that can't afford this build a **second, identical kitchen** next door, get it fully staffed and tested with the new recipe while the OLD kitchen keeps serving every customer, and then — at the moment they're confident — flip a single switch so the front-of-house starts routing ALL new orders to the new kitchen instantly. If something's wrong, they flip the switch back just as instantly. This is **blue-green deployment**: two complete, independent environments, and the "switch" is just a load balancer's routing target, so rollback is a config change, not a redeploy.

An even more cautious restaurant doesn't trust the new kitchen fully even after testing — so instead of an all-or-nothing switch, they send the new recipe to just **one table out of fifty** first, watch that table's reaction closely (do they send it back? complain? get sick?), and only if that one table is happy do they widen it to five tables, then twenty, then all fifty. This is **canary deployment**: a small, real percentage of production traffic hits the new version while the vast majority still hits the known-good old version, and you watch error rates/latency on that canary slice before promoting further — often fully automated, where a monitoring system watches the canary's metrics and auto-rolls-back the instant something looks wrong, without a human needing to notice first.

**Rolling deployment** is the "replace one cook at a time, mid-shift" version — you swap out old-version instances for new-version ones a few at a time, so at any given moment both versions are running simultaneously and you never have zero capacity, but you also can't cleanly "switch back" all at once the way blue-green lets you — you have to roll the replacement back out gradually too.

Now the deepest, most counter-intuitive idea in this whole space: what if you don't wait for a real failure to test your recovery plan — what if you deliberately, safely, and on purpose UNPLUG something during off-peak hours to prove your backup plan actually works? A hospital that has a backup generator doesn't just assume it'll work during a real blackout — a disciplined one tests it under controlled conditions on a schedule. **Chaos Engineering** (Netflix's Chaos Monkey being the famous originator) applies exactly this discipline to software: deliberately kill a service instance, inject artificial network latency, or simulate an AWS availability zone outage, IN PRODUCTION, during a controlled window, specifically to discover that your circuit breaker ([009-circuit-breaker-pattern.md](009-circuit-breaker-pattern.md)) or your bulkhead isolation ([010-bulkhead-pattern-isolate-failures.md](010-bulkhead-pattern-isolate-failures.md)) actually behaves the way your architecture diagram claims it does — because an untested failure-recovery mechanism is really just a hopeful assumption, and the only way to know it works is to have actually watched it work.

---

## PART 2 — THE DEPLOYMENT & CHAOS DIAGRAMS

### Blue-Green: Instant Switch, Instant Rollback

```
                      Load Balancer
                     /              \
        (100% traffic)              (0% traffic — idle, but fully deployed
              |                       and warmed up, running new version)
              v                              v
      ┌───────────────┐            ┌───────────────┐
      │  BLUE (v1.0)    │            │  GREEN (v2.0)   │
      │  currently LIVE │            │  fully tested,  │
      │                 │            │  standing by     │
      └───────────────┘            └───────────────┘

  Cutover: flip LB target from BLUE to GREEN — 100% traffic moves
  instantly. If v2.0 misbehaves: flip LB target back to BLUE — instant
  rollback, no redeploy, no rebuild. Cost: you run DOUBLE the infra
  capacity during the transition window.
```

### Canary: Gradual, Metric-Gated Promotion

```
             Load Balancer (weighted routing)
             /                              \
     95% traffic                       5% traffic (CANARY)
          |                                  |
          v                                  v
  ┌────────────────┐               ┌────────────────┐
  │  v1.0 (stable)   │               │  v1.1 (canary)   │
  │  N instances      │               │  1-2 instances    │
  └────────────────┘               └────────────────┘
                                             |
                          Automated Canary Analysis (metrics agent)
                          watches: error rate, p99 latency, CPU
                                             |
              ┌──────────────────────────────┼──────────────────────┐
              v (metrics healthy)                          v (metrics degrade)
      promote: 5% → 25% → 50% → 100%              AUTO-ROLLBACK: canary weight
      (each step gated by a fixed                  → 0%, alert on-call, v1.1
       observation window, e.g. 10 min)            instances terminated
```

### Chaos Experiment: Controlled Failure Injection

```
Hypothesis: "If the payment-service's primary AZ fails, traffic fails
             over to the secondary AZ within 30 seconds with no
             customer-visible errors, because of our circuit breaker
             + multi-AZ load balancer config."

Chaos experiment (run during a scheduled, monitored window, often with
an "abort" button + a blast-radius limit like 1% of production traffic):
  1. Inject: terminate all payment-service pods in AZ-1 simultaneously
  2. Observe: does the LB detect unhealthy targets and reroute within
     the expected time? Does the circuit breaker trip cleanly instead
     of piling up timeouts? Does error rate spike, and if so, for how
     long and to what %?
  3. Compare actual behavior to the HYPOTHESIS — a chaos experiment
     that "passes" means reality matched the architecture diagram; a
     chaos experiment that "fails" is much more valuable, because it
     just found a real gap BEFORE a real, unplanned outage did.
```

### Expand-Contract: Zero-Downtime Schema Migration

```
Goal: rename column "user_name" → "username" with ZERO downtime and
      zero failed writes, while old and new application code both run
      simultaneously during a rolling deploy.

Step 1 (EXPAND):  ADD COLUMN username; keep user_name too.
                   Deploy app version that WRITES to BOTH columns,
                   reads from OLD column (user_name). No breaking change.

Step 2 (BACKFILL): Copy existing user_name values into username in a
                   background batch job, throttled to avoid replication
                   lag spikes (see 007-read-replica-lag-read-your-own-writes.md).

Step 3 (MIGRATE READS): Deploy app version that reads from NEW column
                   (username), still writes to both. Verify correctness.

Step 4 (CONTRACT): Once ALL instances run the new-read version, deploy
                   a final version that writes ONLY to username, then
                   DROP COLUMN user_name.

  At every single step, BOTH the old and new code versions running
  concurrently (during a rolling deploy) are actually valid against
  the CURRENT schema — this is the property that makes it zero-downtime.
```

---

## PART 3 — INTERNALS AND REAL NUMBERS

### Kubernetes Readiness vs Liveness Probes (What Actually Gates a Rollout)

```yaml
readinessProbe:      # "am I ready to RECEIVE traffic right now?"
  httpGet: { path: /health/ready, port: 8080 }
  periodSeconds: 5
  # A pod failing readiness is pulled OUT of the LB's target pool
  # immediately — used to gate canary/rolling promotion.

livenessProbe:       # "am I still ALIVE, or should I be restarted?"
  httpGet: { path: /health/live, port: 8080 }
  periodSeconds: 15
  failureThreshold: 3
  # A pod failing liveness gets KILLED and RESTARTED by the orchestrator
  # — this is a self-healing mechanism, distinct from traffic routing.
```

### Real Numbers

```
Blue-green infra cost: 2x steady-state capacity during the cutover
  window (often just minutes to a few hours), which is why teams often
  reserve blue-green for less frequent, higher-risk releases rather
  than every single deploy.
Canary promotion windows: commonly 10-30 minutes per step in mature
  pipelines (Spinnaker/Argo Rollouts), long enough to catch a latency
  or error-rate regression under real traffic before widening exposure.
Chaos experiment blast radius: mature practice caps a SINGLE experiment
  at a small, bounded % of production traffic/capacity (often <5%) with
  an automated abort condition if customer-facing error rate crosses a
  hard threshold mid-experiment.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You need to roll out a rewrite of your checkout service that touches the database schema. How do you do this with zero downtime and a fast rollback path if something goes wrong?"

**You (architect answer):**

> "I'd split this into two separate problems: the schema change and the code rollout, because coupling them is exactly what removes your rollback option.
>
> For the schema, I'd use an expand-contract migration: first add the new columns/tables alongside the old ones, deploy application code that writes to BOTH old and new schema, backfill historical data in a throttled background job, then — only once that's verified — deploy a version that reads from the new schema, and only in a FINAL step, once every instance is on the new code, drop the old columns. At every intermediate step, both old and new application code are valid against whatever the current schema looks like, which is what makes a rolling deploy safe here.
>
> For the code rollout itself, given this is checkout — high risk, revenue-critical — I'd use a canary strategy rather than blue-green: route a small percentage, say 5%, of real traffic to the new version, and gate promotion to 25%, 50%, 100% on automated checks of error rate and p99 latency staying within bounds, not just a human eyeballing a dashboard. If the canary's metrics degrade at any stage, the rollback is just setting that slice's weight back to 0% — no rebuild, no redeploy required.
>
> And before I fully trust the new checkout service's resilience claims — say, that it fails over cleanly if its database's primary AZ goes down — I'd want to have actually run a chaos experiment proving that, in a controlled window with a bounded blast radius, rather than relying on the architecture diagram's assumption that the failover 'should' work."

---

## PART 5 — DECISION FRAMEWORK

| Strategy | Rollback Speed | Infra Cost | Blast Radius on Bad Release | Best For |
|---|---|---|---|---|
| **Blue-green** | Instant (LB switch) | 2x during cutover | 100% if not caught before switch | Infrequent, high-risk releases; simple full-stack cutovers |
| **Canary** | Fast (reduce weight to 0%) | Small extra (1-2 canary instances) | Small % of traffic, bounded and observable | Frequent releases; revenue-critical paths; automated pipelines |
| **Rolling** | Slow (must roll back gradually too) | None extra | Grows as rollout proceeds | Default/simple case, low-risk, well-tested changes |
| **Chaos experiment** | N/A (validation, not a release strategy) | Small, controlled | Deliberately bounded (<5% typical) | Validating resilience claims BEFORE they're needed in a real incident |
| **Expand-contract schema migration** | Each step independently reversible | Temporary dual-write/dual-column overhead | None if steps are followed in order | Any schema change during a rolling/canary code deploy |
