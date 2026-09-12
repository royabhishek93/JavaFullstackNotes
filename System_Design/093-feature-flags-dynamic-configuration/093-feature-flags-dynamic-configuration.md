# Feature Flags: Dynamic Configuration as a System Design Pattern
### How LaunchDarkly/Unleash-style flag systems let you change behavior in production without a deploy — and without adding latency to every request

---

## PART 1 — THE STUDENT CONVERSATION

Imagine your production system is a factory assembly line, and every worker on the line has to walk to a locked filing cabinet in another building to check "am I allowed to use the new packaging machine today?" before deciding how to package each item. That round trip would grind the entire line to a halt. Nobody does that. Instead, every worker gets a small laminated card at the start of their shift listing today's rules, and the factory posts a single announcement — over the loudspeaker — the instant a rule changes, so every worker updates their card without walking anywhere.

This is exactly the architecture of a real feature flag system, and it's the part junior engineers usually get wrong: they imagine a feature flag as "an if-statement that calls a remote config API on every request." That would add a network round-trip to every single request in your system — completely unacceptable at scale. Real flag systems separate **evaluation** (fast, local, in-process) from **distribution** (occasional, pushed from a central service).

Map the analogy to real terms:
- **Filing cabinet in another building** — the flag evaluation service (LaunchDarkly's servers, Unleash's server, or your homegrown flag API). This is the source of truth, but it is NOT consulted on every request.
- **Laminated card / local copy** — the SDK's in-memory cache of flag rules, refreshed in the background. Every flag check (`flags.isEnabled("new-checkout-flow", userId)`) is a pure in-memory computation, typically sub-microsecond, with zero network I/O.
- **Loudspeaker announcement** — a streaming connection (Server-Sent Events, or a WebSocket, or fallback polling) from the flag service to every running instance of your application, pushing rule CHANGES the instant an operator flips a flag in the dashboard, so the local cache updates within roughly a second, not on the next request's round-trip.
- **"Am I allowed to use the machine today" being the SAME answer every time you ask the same worker** — this is the consistent-hashing requirement for percentage rollouts: user 12345 must always land in the same 10% "on" bucket or the same 90% "off" bucket, on every request, on every server instance, or your UI will flicker between two experiences for the same person mid-session.
- **A rule that says "STOP using the machine immediately, safety issue"** — the kill-switch pattern: an operator can flip a flag to instantly disable a feature across your entire fleet, without a deploy, without a rollback PR, in the time it takes the streaming update to propagate (typically under a second, or up to a polling interval as a fallback).

The deeper system-design lesson: feature flags aren't a developer convenience for hiding half-built code (though they're that too) — they're a *decoupling mechanism between deployment and release*. Deploying code and releasing a feature become two independent operations, which is what lets you deploy on Friday afternoon with confidence, because "deployed" no longer means "live for users."

---

## PART 2 — THE FEATURE FLAG ARCHITECTURE DIAGRAMS

### Flag Evaluation Flow: Client SDK → Local Cache → Streaming → Fallback

```
                         ┌───────────────────────────────────┐
                         │   FLAG EVALUATION SERVICE (SaaS    │
                         │   or self-hosted, e.g. Unleash)    │
                         │                                     │
                         │   flag: "new-checkout-flow"         │
                         │   rules: [                          │
                         │     { rollout: 25%, salt: "v3" },    │
                         │     { segment: "internal-users",     │
                         │       always: true }                │
                         │   ]                                 │
                         └───────────┬─────────────────────────┘
                                     │
                    ┌────────────────┼─────────────────────┐
                    │ 1. STARTUP: SDK fetches full          │
                    │    rule set once via HTTPS GET         │
                    │ 2. STREAMING: SSE connection stays      │
                    │    open, pushes DIFFS on change         │
                    │ 3. FALLBACK: if SSE drops, poll every   │
                    │    30-60s for full refresh              │
                    v                                        v
        ┌──────────────────────┐                 ┌──────────────────────┐
        │  App Instance #1      │                 │  App Instance #2      │
        │  ┌─────────────────┐ │                 │  ┌─────────────────┐ │
        │  │ Flag SDK          │ │                 │  │ Flag SDK          │ │
        │  │ in-memory cache:  │ │                 │  │ in-memory cache:  │ │
        │  │ {new-checkout-    │ │                 │  │ {new-checkout-    │ │
        │  │  flow: {rules}}   │ │                 │  │  flow: {rules}}   │ │
        │  └────────┬──────────┘ │                 │  └────────┬──────────┘ │
        │           │            │                 │           │            │
        │  Request: userId=12345 │                 │  Request: userId=12345 │
        │           v            │                 │           v            │
        │  isEnabled(            │                 │  isEnabled(            │
        │   "new-checkout-flow", │                 │   "new-checkout-flow", │
        │   userId=12345)        │                 │   userId=12345)        │
        │  → hash(12345+"v3")    │                 │  → hash(12345+"v3")    │
        │    % 100 = 17          │                 │    % 100 = 17          │
        │  → 17 < 25 → TRUE       │                 │  → 17 < 25 → TRUE       │
        │  (in-process, <1μs,     │                 │  (SAME instance would   │
        │   zero network call)   │                 │   ALWAYS get 17 —       │
        └───────────────────────┘                 │   deterministic hash,   │
                                                    │   consistent across ALL │
                                                    │   app instances too)    │
                                                    └───────────────────────┘

If SSE connection drops (network blip, service restart):
  SDK keeps serving from LAST-KNOWN-GOOD cache — flags do NOT go blank or
  fail-open/closed unpredictably. This is the single most important
  resilience property: a flag SDK must NEVER make the flag service a
  hard dependency for request-serving. Worst case on a prolonged outage:
  flags are stale (a rollout percentage doesn't get the latest update)
  but the application keeps running exactly as it was.
```

### Percentage Rollout via Consistent Hashing

```
Goal: roll out "new-checkout-flow" to exactly 25% of users, and the SAME
25% every time (not a random coin flip per request, which would make a
single user bounce between old/new checkout mid-session — a serious bug).

  bucket(userId, flagKey) = hash(userId + flagKey + salt) % 100

  User 12345, flag "new-checkout-flow", salt "v3":
    hash("12345new-checkout-flowv3") = 8231971...
    8231971... % 100 = 17
    17 < 25 (rollout percentage)  →  ENABLED

  User 67890, same flag:
    hash("67890new-checkout-flowv3") = 9104432...
    9104432... % 100 = 84
    84 >= 25  →  DISABLED

  Same user, evaluated on a DIFFERENT server, a DIFFERENT day, after a
  deploy: hash(12345 + "new-checkout-flow" + "v3") is IDENTICAL every
  time — no state needs to be stored per user. The user's bucket is a
  pure function of their ID, not something looked up in a database.

Increasing rollout from 25% -> 50% later:
  Every user who was previously < 25 (already enabled) STAYS enabled,
  because the same hash function with the same salt is deterministic.
  New users are added: those landing in bucket 25-49 flip from
  DISABLED to ENABLED. Nobody who had the new feature loses it — this
  is the property that makes staged rollouts (1% -> 10% -> 50% -> 100%)
  safe and non-disruptive to users already in the experiment.

  Changing the SALT (e.g., "v3" -> "v4") reshuffles ALL users into new
  buckets — used deliberately when you want a fresh random sample for
  a new A/B test iteration, rather than always testing the same 25%.
```

### Kill Switch: Instant Rollback Without a Deploy

```
Normal operation:
  new-payment-provider flag: rollout 100%, all traffic → new provider

Incident detected (elevated payment failure rate, alert fires):
  On-call engineer opens flag dashboard, flips
    new-payment-provider: rollout 100% → rollout 0% (or targeting: OFF)

  Propagation timeline:
    T+0ms    : operator clicks "save" in dashboard
    T+50ms   : flag service persists change, pushes to SSE stream
    T+200ms  : most app instances (subscribed to stream) receive diff,
               update in-memory cache
    T+1000ms : ALL app instances across the fleet have the update
               (upper bound — accounts for instances with a
               reconnecting SSE client that fall back to polling)

  Compare to a code-revert-and-redeploy rollback:
    T+0        : incident detected
    T+2-10 min : revert commit, CI build + test suite
    T+5-20 min : rolling deploy across fleet (canary → full)
    Total: 10-30+ minutes of continued impact

  This 10-30x speed difference is the primary business justification
  for feature flags in production incident response — it converts a
  "redeploy under pressure" fire drill into a dashboard click.

  IMPORTANT: a kill switch is only as good as what the code path
  actually does when disabled. Best practice is the flag check wraps a
  fallback to the LAST KNOWN GOOD code path (old payment provider),
  not just "return an error" — otherwise the kill switch trades one
  outage for a different one.
```

---

## PART 3 — INTERNALS, IMPLEMENTATION, AND REAL NUMBERS

### Flag Definition and Targeting Rules (Unleash-Style JSON)

```json
{
  "name": "new-checkout-flow",
  "enabled": true,
  "strategies": [
    {
      "name": "flexibleRollout",
      "parameters": {
        "rollout": "25",
        "stickiness": "userId",
        "groupId": "new-checkout-flow-v3"
      }
    },
    {
      "name": "userWithId",
      "parameters": { "userIds": "internal-emp-001,internal-emp-002" }
    },
    {
      "name": "gradualRolloutSessionId",
      "constraints": [
        { "contextName": "country", "operator": "IN", "values": ["US", "CA"] }
      ],
      "parameters": { "rollout": "50", "stickiness": "sessionId" }
    }
  ],
  "variants": [
    { "name": "control", "weight": 500, "payload": { "type": "string", "value": "old-ui" } },
    { "name": "treatment", "weight": 500, "payload": { "type": "string", "value": "new-ui" } }
  ]
}
```

### SDK Usage in Application Code (Java/Spring)

```java
@Service
public class CheckoutService {

    private final FeatureFlagClient flags;   // wraps Unleash/LaunchDarkly SDK

    public CheckoutResponse checkout(CheckoutRequest req, String userId) {
        FlagContext ctx = FlagContext.builder()
            .userId(userId)
            .attribute("country", req.getShippingCountry())
            .attribute("plan", req.getUserPlanTier())
            .build();

        // Pure in-memory evaluation — no network call happens here.
        // The SDK evaluated this against its LOCAL cache of rules,
        // last refreshed via the streaming connection.
        if (flags.isEnabled("new-checkout-flow", ctx)) {
            return newCheckoutFlow.process(req);
        }
        return legacyCheckoutFlow.process(req);
    }

    public String getButtonVariant(String userId) {
        // Variants for A/B testing — returns "control" or "treatment"
        // deterministically for this user, plus fires an exposure event
        Variant variant = flags.getVariant("checkout-button-color-test",
            FlagContext.builder().userId(userId).build());

        // Exposure logging: fire-and-forget async event to the analytics
        // pipeline — critical for A/B test validity, see below
        analyticsClient.trackExposure(userId, "checkout-button-color-test",
            variant.getName());

        return variant.getPayload().orElse("control");
    }
}
```

```java
// SDK internals sketch: this is what "local cache + streaming" looks like
public class FlagSdkClient {

    private volatile Map<String, FlagRule> cache = Map.of();  // last-known-good, thread-safe read

    @PostConstruct
    void init() {
        cache = fetchFullRuleSetOverHttps();     // blocking startup fetch
        startSseListener();                       // background thread
    }

    private void startSseListener() {
        // Subscribes to Server-Sent Events; each event is a flag diff
        sseClient.subscribe("/flags/stream", event -> {
            Map<String, FlagRule> updated = new HashMap<>(cache);
            updated.put(event.getFlagKey(), event.getNewRule());
            cache = updated;   // atomic reference swap, readers never block
        }, onError -> {
            // SSE dropped: fall back to polling every 30s, KEEP serving
            // the existing cache in the meantime — never clear it
            startPollingFallback(Duration.ofSeconds(30));
        });
    }

    public boolean isEnabled(String flagKey, FlagContext ctx) {
        FlagRule rule = cache.get(flagKey);
        if (rule == null) return false;   // safe default: unknown flag = off
        long bucket = consistentHash(ctx.getUserId() + flagKey + rule.getSalt()) % 100;
        return bucket < rule.getRolloutPercentage();
    }
}
```

### A/B Testing Exposure Logging Pipeline

```
Client SDK evaluates variant                Analytics Pipeline
─────────────────────────────                ───────────────────
flags.getVariant(                             Kafka topic: "flag-exposures"
  "checkout-button-color-test",               {
  ctx)                                          "userId": "12345",
  → deterministic hash → "treatment"            "flagKey": "checkout-button-color-test",
                                                 "variant": "treatment",
Exposure event fired ASYNCHRONOUSLY              "timestamp": 1719849600000,
(never blocks the request):                      "context": {"country":"US","plan":"pro"}
  analyticsClient.trackExposure(...)             }
                                                        │
                                                        v
                                              Consumer aggregates into
                                              experiment results warehouse
                                              (e.g., joins exposure events
                                              with conversion events on
                                              userId to compute lift)

CRITICAL correctness requirement: "assignment consistency" — the SAME
user must see the SAME variant for the DURATION of the experiment, or
your statistical results are contaminated (a user bouncing between
control/treatment pollutes both cohorts). This is guaranteed by the
same consistent-hashing mechanism used for rollouts: hash(userId +
flagKey + salt) is deterministic and stable as long as the salt and
rollout percentages for that flag/experiment don't change mid-flight.

Exposure logging must be decoupled from evaluation: if you only log
exposure when a user actually SEES the UI element render (rather than
whenever the flag is evaluated internally, e.g. during a pre-fetch or
speculative render), you avoid "phantom exposures" that inflate sample
size without a corresponding user-visible impression — a common,
subtle A/B test bug in production analytics pipelines.
```

### Flag Lifecycle and Debt Cleanup

```bash
# Real operational discipline: flags accumulate. A team shipping weekly
# can accumulate 200-500+ flags per year if none are ever removed.
# Stale flags are a maintainability and SECURITY liability — an old
# "disable-auth-check-for-debugging" flag left in prod code is a
# textbook OWASP-relevant misconfiguration risk if it's ever
# accidentally flipped or defaults change.

# Lifecycle stages tracked by mature flag platforms (Unleash exposes this
# natively as flag "type" and staleness warnings):
#   1. RELEASE flag   — temporary, tied to a specific feature rollout
#                        should be deleted within days/weeks of 100% rollout
#   2. EXPERIMENT flag — temporary, tied to an A/B test
#                        deleted once the experiment concludes + is analyzed
#   3. OPS flag        — semi-permanent, kill-switches for operational safety
#                        (e.g., "disable-3rd-party-recommendation-calls")
#   4. PERMISSION flag — long-lived, gates functionality by plan/tier
#                        (e.g., "enterprise-sso-enabled") — NOT technical debt

# CI check some teams add: fail a build if a RELEASE-type flag has been
# at 100% rollout for > 30 days without its code branches being cleaned up.
grep -rn "flags.isEnabled(\"new-checkout-flow\"" src/ | wc -l
# If this flag has been at 100% for 45 days and still has 12 call sites
# with dead "else" branches serving the old code path, that's tech debt
# to schedule for removal — the flag itself becomes the reminder.
```

### Real Numbers

```
Flag evaluation latency: <1 microsecond (in-memory map lookup + hash
computation), compared to 20-100ms+ if you naively called a remote
config service per request — a 20,000x-100,000x difference, and the
entire reason SDKs are architected around local caching.

Streaming update propagation: SSE-based systems (LaunchDarkly, Unleash)
typically propagate a flag change to all connected SDK instances within
100-500ms under normal conditions; polling-only fallback clients see
updates within their configured interval, commonly 15-60 seconds.

Fleet size consideration: a fleet of 500 app instances all holding an
open SSE connection to the flag service is a moderate but manageable
connection load on the flag service (compare to 500 instances all
polling every request — that would be catastrophic). This asymmetry is
why the "cache + push" model, not "call on every check," is the only
architecture that scales.

Typical flag payload size: a single flag's rule definition is usually
under 1-2 KB (targeting rules, variants, constraints). A full ruleset
fetch for an application with 300 active flags: roughly 150-400 KB,
fetched once at startup and then only diffed thereafter.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "You need to roll out a risky new checkout flow to 5% of users first, be able to instantly kill it if error rates spike, and later run it as a proper A/B test against the old flow. How do you architect this so that a feature flag check doesn't become a bottleneck added to every checkout request?"

**You (architect answer):**

> "The bottleneck risk only exists if you architect flag evaluation as a network call on the request path — which is a mistake I've seen made when people think of a flag as 'call a remote config API.' Instead, I'd run the flag SDK's evaluation entirely in-process. On startup, each application instance fetches the full flag ruleset once and holds it in memory. From then on, the SDK maintains a persistent streaming connection — Server-Sent Events, typically — back to the flag service, and any change an operator makes in the dashboard gets pushed as a diff to every instance within roughly a second. The actual `isEnabled()` check inside `checkout()` is then a pure in-memory hash computation, sub-microsecond, with zero network I/O on the hot path.
>
> For the 5% rollout, I'd use consistent hashing: bucket = `hash(userId + flagKey + salt) % 100`, enabled if bucket falls under 5. That's deterministic — the same user always lands in the same bucket on every server, every request, without needing to persist a per-user assignment anywhere. When I later increase to 20% or 50%, everyone already enabled stays enabled; I'm only adding new buckets, which is what makes staged rollouts non-disruptive.
>
> For the kill switch, that's the same flag flipped to 0% rollout or targeting off — the propagation path is identical to the rollout mechanism, which means I get sub-second global disable with zero deploy, versus the 10-30 minutes a revert-and-redeploy would take under incident pressure. The one thing I'd insist on architecturally is that the code behind the flag check falls back to the last-known-good checkout flow, not an error state — a kill switch that just throws an exception when disabled just trades one outage for another.
>
> For the A/B test phase, I'd reuse the exact same consistent-hashing mechanism for variant assignment, which gives me assignment consistency for free — the same user sees the same variant for the life of the experiment. The part I'd be most careful about operationally is exposure logging: I fire an async, fire-and-forget event to our analytics pipeline only when the user actually renders the variant, not merely when the flag is internally evaluated, because logging on evaluation rather than on true impression is a common way experiment sample sizes get silently inflated with phantom exposures that never corresponded to a real user seeing anything."

---

## PART 5 — DECISION FRAMEWORK

### Feature Flags vs Alternative Release/Config Mechanisms

| Approach | How It Works | Consistency/Tradeoff | Latency | Complexity | When It Fails |
|---|---|---|---|---|---|
| **Feature flag platform (LaunchDarkly/Unleash)** | SDK local cache + streaming push from central service | Eventually consistent (sub-second lag on change), assignment-stable via consistent hashing | <1μs per evaluation, no request-path network call | Medium (SDK integration, salt/rollout discipline, flag lifecycle hygiene) | Stale flag debt if not cleaned up; a misconfigured default (fail-open vs fail-closed) can cause the wrong outage |
| **Environment variables / static config** | Baked in at deploy or container start | Fully consistent, but requires a deploy/restart to change | Zero runtime overhead | Very low | Any change needs a deploy — no fast kill switch, no gradual rollout |
| **Database-backed config table, polled** | App polls a `config` table every N seconds | Eventually consistent, lag = poll interval | Poll interval (often 30-60s), DB read overhead per poll cycle | Low-Medium | No streaming push means kill switch is only as fast as your poll interval; DB becomes a dependency for every instance |
| **Blue/green or canary deployment** | Route a % of traffic to a new deployed version at the infra/LB layer | Fully consistent per-instance, but coarse-grained (per-server, not per-user) | Instant traffic-level cutover | Medium (infra/LB routing rules) | Can't do per-user percentage rollout or A/B variant assignment cleanly — it's an infra-level toggle, not a user-level one |
| **Hardcoded if/else + manual code removal** | Just ship the new code path directly | Fully consistent, no rollout control at all | Zero overhead | Lowest | No ability to gradually roll out or instantly disable — every "flag flip" requires a full deploy cycle |

### When Feature Flags Are the Right Choice

```
Use feature flags when:
  ✓ You need to decouple "deployed" from "released" (deploy any day,
    release on your own schedule)
  ✓ You need instant kill-switch capability for risky changes
  ✓ You want gradual, percentage-based rollouts with stable per-user assignment
  ✓ You're running A/B tests and need consistent variant assignment +
    exposure logging tied to an analytics pipeline
  ✓ Different customer tiers/segments need different feature access
    (permission-style flags) without maintaining separate deployed builds

Skip feature flags (or minimize their footprint) when:
  ✗ The change is infrastructure-level (routing, scaling) — canary/blue-green
    at the load balancer is a better fit than an application-level flag
  ✗ You're using flags as a substitute for actually finishing a design decision
    — flags forever multiplying code paths without a cleanup plan is the
    #1 cause of flag debt and eventual production incidents from stale flags
  ✗ The setting genuinely never changes at runtime (that's just config,
    ship it as an environment variable, don't add a flag SDK dependency)
  ✗ Your team can't commit to lifecycle discipline (removing RELEASE/EXPERIMENT
    flags after rollout) — an ever-growing flag count becomes its own risk
```

---

## QUICK REFERENCE CARD

```
CORE EVALUATION MODEL:
  bucket(userId, flagKey, salt) = hash(userId + flagKey + salt) % 100
  enabled = bucket < rolloutPercentage
  → deterministic, stateless, stable across servers/requests/deploys

SDK ARCHITECTURE (never skip this):
  1. Startup: full rule fetch (HTTPS GET)
  2. Live updates: SSE/WebSocket stream pushes diffs (~100-500ms propagation)
  3. Fallback: poll every 15-60s if stream drops
  4. NEVER clear cache on stream failure — serve last-known-good always
  5. isEnabled() / getVariant() = pure in-memory op, no request-path network call

KILL SWITCH:
  flip rollout% -> 0 (or targeting OFF) = same mechanism as rollout,
  propagates in <1s vs 10-30min for revert-and-redeploy
  MUST fall back to last-known-good code path, not an error state

A/B TESTING REQUIREMENTS:
  Assignment consistency: same hash function/salt = same user always
    gets same variant for experiment duration
  Exposure logging: fire on ACTUAL render/impression, not on evaluation,
    to avoid phantom-exposure sample inflation
  Pipeline: SDK -> async event -> Kafka/analytics topic -> experiment warehouse

FLAG LIFECYCLE TYPES:
  RELEASE flag     -> delete within weeks of 100% rollout
  EXPERIMENT flag  -> delete after experiment analyzed
  OPS flag         -> semi-permanent kill switch, keep
  PERMISSION flag  -> long-lived tier/plan gate, keep

CROSS-REF: 090-operational-transformation-collaborative-editing.md (n/a, different domain)
           039-websocket-vs-sse-vs-long-polling.md (SSE transport mechanics)
           012-idempotency-keys-prevent-double-processing.md (exposure event dedup pattern)
```
