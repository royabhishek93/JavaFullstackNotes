# Feature Flags: Dynamic Configuration — LinkedIn Post

## Post Text (copy-paste ready)

A payment kill switch that takes 1 second beats a code revert that takes 30 minutes. Here's why most engineers still build feature flags wrong.

- The #1 mistake: treating a flag check as a remote API call per request — that's 20-100ms added to every request, vs <1 microsecond for the correct architecture (in-memory cache + streaming push)
- Percentage rollouts need consistent hashing: bucket = hash(userId + flagKey + salt) % 100 — deterministic, so the same user always lands in the same bucket, on every server, every request
- A kill switch is only as good as its fallback: flipping a flag to 0% but having the code just throw an error trades one outage for another — it must fall back to the last-known-good code path
- A/B tests get silently corrupted by "phantom exposures" — logging when a flag is evaluated (e.g. during a pre-fetch) instead of when the user actually sees the variant inflates your sample size with impressions that never happened
- Flag debt is real: a team shipping weekly can rack up 200-500 flags a year — an old "disable-auth-check-for-debugging" flag left in prod is a textbook misconfiguration risk if it's ever flipped by accident

Swipe to see: the propagation timeline (1s kill switch vs 30-min redeploy), the rollout math, and the flag lifecycle table every team needs.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
A flag flip propagates in <1s. A revert-and-redeploy takes 10-30 min. Here's the architecture behind that gap 👇

### Variant B — Long (400–600 chars)
Feature flags aren't "an if-statement that calls a config API." Real systems like LaunchDarkly and Unleash separate evaluation (in-memory, <1 microsecond, zero network I/O) from distribution (a streaming push, ~100-500ms propagation). That split is what turns an incident response from a 10-30 minute redeploy into a 1-second dashboard click — and what makes percentage rollouts safe via consistent hashing. Miss the fallback-on-kill-switch pattern or ignore flag lifecycle cleanup, and you trade one outage for another, or drown your codebase in 200+ dead flags a year.

---

## Best Time to Post
Wednesday, 9:00–10:00 AM IST (technical incident-response content performs best mid-week, before the pre-weekend drop-off)

## Engagement Hook
"Has a feature flag ever saved you during a production incident — or made one worse because the fallback path was missing?"
