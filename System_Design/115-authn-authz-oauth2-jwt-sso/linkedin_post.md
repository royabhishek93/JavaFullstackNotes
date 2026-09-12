# Authentication & Authorization: OAuth2, JWT, SSO, RBAC — LinkedIn Post

## Post Text (copy-paste ready)

Your 20-microservice architecture calling a central auth server on every request isn't "secure" — it's one outage away from taking everything down with it.

- A JWT is a badge, not a lookup ticket: sign it once at the identity provider, and every downstream service verifies it locally (~0.1-0.3ms, zero network calls) using a cached public key from a JWKS endpoint.
- Stateless tokens can't be revoked instantly — that's not a flaw, it's a tradeoff. Cap the damage by keeping access tokens short (5-15 min) and rotating refresh tokens (7-30 days) on every use.
- If a rotated refresh token gets reused, that's not a bug — it's a theft signal. Correct response: kill the entire token family instantly, not just that one request.
- Rotating a signing key without a grace period is a real production incident: tokens signed 2 minutes earlier suddenly fail everywhere. Keep old keys in JWKS until their tokens expire.
- RBAC is a fast O(1) role lookup baked into the token. ABAC checks a full policy (department, time, IP) — more powerful, harder to audit, and belongs in a policy engine (OPA), not stuffed into the JWT itself.

Swipe → to see: the OAuth2 "Login with Google" flow, JWT structure, session-vs-JWT tradeoffs, and refresh token rotation — visually.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
Your auth server isn't down. It's the single point of failure your whole architecture didn't know it had. Full breakdown 👇

### Variant B — Long (400-600 chars)
Every microservice calling a central auth server on every request doesn't scale — and it doesn't need to. A short-lived JWT lets any service verify identity locally in under 0.3ms, no network call back home. The real engineering problem isn't verification, it's revocation: how do you kill a badge you can't call back? Refresh token rotation with reuse-detection is the answer production systems actually use — and getting it wrong (or skipping key-rotation grace periods) is how real outages happen. RBAC vs ABAC, session cookies vs stateless JWTs, opaque tokens vs introspection — all tradeoffs, no silver bullet. Breakdown in the carousel.

---

## Best Time to Post
Tuesday or Wednesday, 8:30–9:30 AM IST (before the Indian tech workday standups, when engineers are scrolling LinkedIn with coffee)

## Engagement Hook
Session cookies or stateless JWTs — which one have you had to defend in an interview, and what tripped you up?
