# How do you implement feature flags for gradual rollout?

> **Interview priority:** GOOD TO KNOW

## Question

How do you implement feature flags for gradual rollout?

## Beginner Lens

Watch the deployment: instead of releasing a risky feature to 100% of users at once, you show it to 5%, measure metrics, then 25%, then 100%. If something breaks, you flip the flag off instantly without redeploying code. Feature flags let you separate deployment from release.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "Feature flags are essential for safe production releases. I've seen teams deploy broken features to all users, then scramble to hotfix and redeploy. With flags, you deploy the code hidden, test it in production with 1% of users, watch error rates and metrics, then gradually increase. If errors spike, you toggle the flag off in seconds. It separates 'code is deployed' from 'feature is live,' giving you a kill switch. Let me show the patterns..."

```
REAL APP: New Checkout Flow — Gradual Rollout
─────────────────────────────────────────────────────────────────

SCENARIO: Rewrite checkout with new payment provider (risky)

NAIVE APPROACH (no flags):
────────────────────────────────────────────────────────────────

1. Develop new checkout locally
2. Test in staging
3. Deploy to production (all users instantly see it)
4. Bug discovered: payment fails for 10% of users ❌
5. Frantically code a fix
6. Redeploy (20 min build + deploy)
7. Meanwhile: losing revenue, angry customers ❌

WITH FEATURE FLAGS:
────────────────────────────────────────────────────────────────

1. Develop new checkout with flag check
2. Deploy to production (flag OFF, nobody sees it) ✅
3. Enable for internal team (10 people) → test in prod
4. Enable for 1% of users → watch metrics
5. If metrics good: 5% → 25% → 50% → 100% ✅
6. If error spike at 5%: toggle flag OFF ✅ (instant rollback)
7. Fix bug in code
8. Redeploy with fix
9. Resume rollout: 5% → 25% → ...

Result: Controlled risk, instant rollback, no downtime ✅
```

> "The mental model: feature flags decouple deployment from release. Code goes to production dark (flag off), then you illuminate it gradually. Hash-based bucketing ensures consistency — user 123 sees the same experience across sessions. Real-time updates via SSE let you kill a feature instantly if metrics tank. Always measure both variants to make data-driven decisions."

**INTERVIEW FOLLOW-UP QUESTIONS:**

**Q: "How do you clean up old feature flags?"**

> "Track flag age and usage. After full rollout (100% for 2 weeks), remove the flag and dead code. Keep a registry of flags with creation date, owner, and status. Auto-notify teams when flags are >90 days old. Stale flags accumulate technical debt."

**Q: "What about flag dependencies?"**

> "If flag B depends on flag A, check both: `if (flagA && flagB)`. Or use hierarchical flags: `new_checkout` parent flag, `new_checkout_paypal` child flag. Document dependencies in flag config."
