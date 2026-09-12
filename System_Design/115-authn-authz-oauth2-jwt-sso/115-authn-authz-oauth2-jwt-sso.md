# Authentication & Authorization: OAuth2, JWT, SSO, and RBAC in System Design
### How systems answer "who are you" and "what can you do" without a database lookup on every request

---

## PART 1 — THE STUDENT CONVERSATION

Imagine a large office campus with a dozen separate buildings (your microservices), and every employee needs to badge into each one. The dumb way to run this: every door calls the front-desk security office by phone, on every single entry, and waits for someone to look up the employee's file and read back their clearance level. That works for one door with light foot traffic. It collapses the moment you have a thousand employees walking through fifty doors a minute — the front desk becomes a bottleneck and a single point of failure for the entire campus.

The fix real security systems use: the front desk (an **Identity Provider** — Okta, Auth0, your own auth service) verifies you ONCE, at the main gate, and hands you a **badge** that is itself cryptographically tamper-proof and lists your clearance directly on its face — "Engineering, Level 3, expires 6PM today." Every door on campus has a badge reader that can verify the badge's authenticity **on its own**, using a public verification key distributed to every door in advance, without calling the front desk again. This is exactly what a **JWT (JSON Web Token)** is: a self-contained, digitally signed claim ("this user is 12345, these are their roles, this token expires at time T") that any service can verify locally with a public key, with zero network round-trip back to the identity provider.

This immediately raises the question every junior engineer asks next: "if the badge is good until 6PM and I want to fire someone at 2PM, how do I get their badge back?" This is the **revocation problem**, and it's the single most important tradeoff in token-based auth: a self-contained token that nobody needs to look up is also a token nobody can instantly invalidate. The practical answer used everywhere in production is to make the badge short-lived (a JWT access token expiring in 5-15 minutes) and pair it with a separate, longer-lived **refresh token** that IS checked against a database/denylist on each use — so you get fast, stateless verification for the common case, and a bounded window (at most 15 minutes) of "damage" if you need to actually revoke someone.

**SSO (Single Sign-On)** is the generalization of this badge system across separate companies/domains: log into your identity provider once, and every trusted application (Slack, Gmail, your internal tools) accepts that same badge instead of asking you to prove who you are again. **OAuth2** is the protocol that describes how a third-party application gets a token on your behalf without ever seeing your password — "Login with Google" doesn't hand your Google password to the app you're logging into; it hands the app a scoped, limited token after you approve it at Google's own login page.

Finally, once a service knows WHO you are (authentication), it still needs to decide WHAT you can do (authorization). **RBAC (Role-Based Access Control)** checks "does this user's ROLE (admin, editor, viewer) permit this action" — simple, coarse-grained, easy to reason about. **ABAC (Attribute-Based Access Control)** checks a richer policy against many attributes at once ("is the user's department == the document's department AND is it business hours AND is the request from a corporate IP") — more flexible, but harder to audit because the "who can do what" answer isn't a simple lookup table anymore.

---

## PART 2 — THE AUTH ARCHITECTURE DIAGRAMS

### OAuth2 Authorization Code Flow ("Login with Google")

```
User            Your App (Client)         Google (Auth Server)      Google (Resource Server)
────            ──────────────────         ────────────────────      ─────────────────────────
 |  click "Login with Google"      |                                 |
 |─────────────────────────────────>                                 |
 |                                  |  redirect to Google login page  |
 |<─────────────────────────────────|                                |
 |  logs in + approves scopes       |                                 |
 |──────────────────────────────────────────────────────────────────>|
 |                                  |  redirect back with AUTH CODE   |
 |<──────────────────────────────────────────────────────────────────|
 |  browser hits your app callback  |                                 |
 |─────────────────────────────────>                                 |
 |                                  | exchange CODE for ACCESS TOKEN  |
 |                                  | (server-to-server, client_secret|
 |                                  |  never exposed to browser)      |
 |                                  |──────────────────────────────>  |
 |                                  |<── access_token + id_token ────|
 |  app now has a token to call     |                                 |
 |  Google APIs on user's behalf    |                                 |         call with
 |                                  |─────────────────────────────────────────> Bearer token
 |                                  |<──────────────────────────────────────── user profile data
```

### JWT Structure and Stateless Verification

```
JWT = base64url(header) . base64url(payload) . base64url(signature)

Header:   {"alg": "RS256", "typ": "JWT", "kid": "key-2024-08"}
Payload:  {"sub": "user-12345", "roles": ["editor"], "exp": 1719850500, "iss": "auth.company.com"}
Signature: RSA-SHA256(base64(header) + "." + base64(payload), PRIVATE_KEY)

Verification at ANY downstream service (no call back to auth server):
  1. Fetch auth server's PUBLIC key by "kid" (cached, rotates rarely — from a JWKS endpoint)
  2. Recompute signature over header+payload using the public key
  3. Compare to the signature in the token → tampering is mathematically detectable
  4. Check "exp" (expiry) and "iss" (issuer) claims locally
  → Zero network calls to the identity provider on the hot path.
```

### Session Cookie vs Stateless JWT: Where the "Source of Truth" Lives

```
SESSION COOKIE (stateful)                    JWT (stateless)
──────────────────────────                   ────────────────
Browser: Cookie: session_id=abc123            Browser: Authorization: Bearer eyJhbGci...
             |                                              |
             v                                              v
   App Server → Redis: GET session:abc123        App Server verifies signature LOCALLY
   (network round trip EVERY request)            (no round trip — unless a denylist
             |                                     check is added for revocation)
             v
   {userId: 12345, roles: [...]}

Revoke instantly?  DELETE session:abc123 → done   Revoke instantly? Not possible without
                                                    a denylist check (defeats statelessness)
                                                    or waiting out the short expiry (5-15 min)
```

### RBAC vs ABAC Policy Check

```
RBAC: "Can user delete this document?"
   user.roles.contains("admin") OR user.roles.contains("owner")   → simple table lookup

ABAC: "Can user delete this document?"
   user.department == document.department
   AND user.clearanceLevel >= document.classification
   AND request.time BETWEEN 09:00-18:00 (business hours policy)
   AND request.sourceIp IN corporate_ip_ranges
   → a POLICY ENGINE (e.g. Open Policy Agent / Rego) evaluates a rule set,
     not a static role-to-permission table — powerful, but each decision
     needs an audit trail because "why was this allowed" is no longer obvious
```

---

## PART 3 — INTERNALS AND REAL NUMBERS

### Access Token + Refresh Token Rotation

```
T+0min   : login → access_token (exp 10min) + refresh_token (exp 30 days, stored hashed in DB)
T+9min   : access_token about to expire → client silently calls /token/refresh with refresh_token
T+9min   : auth server issues a NEW access_token AND a NEW refresh_token,
           and marks the OLD refresh_token as used/rotated in the DB
           (refresh token REUSE detection: if the old, already-rotated
            refresh_token is presented again, that's a signal the token
            was STOLEN — auth server revokes the entire token family)
T+30days : refresh_token expires → user must fully re-authenticate

Damage window if an access_token is stolen: at most its own TTL (5-15 min).
Damage window if a refresh_token is stolen: mitigated by reuse detection,
not by TTL alone — this is why rotation, not just expiry, matters.
```

### JWKS Key Rotation (so verification never breaks mid-rotation)

```json
GET https://auth.company.com/.well-known/jwks.json
{
  "keys": [
    { "kid": "key-2024-08", "use": "sig", "alg": "RS256", "n": "...", "e": "AQAB" },
    { "kid": "key-2024-05", "use": "sig", "alg": "RS256", "n": "...", "e": "AQAB" }
  ]
}
```
Old signing keys stay published in the JWKS document for as long as the
longest-lived token signed with them could still be valid — otherwise a
token signed 2 minutes before a key rotation would suddenly fail
verification everywhere, a common production incident when teams rotate
keys without a grace-period overlap.

### RBAC Middleware (Java/Spring)

```java
@PreAuthorize("hasRole('EDITOR') or hasRole('ADMIN')")
@PutMapping("/documents/{id}")
public DocumentResponse update(@PathVariable String id, @RequestBody DocumentUpdate body) {
    // Roles were extracted from the verified JWT claims by a filter
    // upstream — no DB call happens inside this method for the auth check.
    return documentService.update(id, body);
}
```

### Real Numbers

```
JWT verification (RSA signature check): ~0.1-0.3ms CPU-bound, no I/O.
Session lookup in Redis: ~0.5-2ms, but requires network I/O + Redis
  availability — a session store outage becomes an auth outage.
Access token TTL in production systems: commonly 5-15 minutes.
Refresh token TTL: commonly 7-30 days, with reuse-detection revocation.
JWKS cache TTL on verifying services: commonly 10-60 minutes, so a key
  rotation propagates within that window, not instantly.
```

---

## PART 4 — THE INTERVIEW CONVERSATION

**Interviewer:** "Your microservices architecture has 20 services. How do you avoid every single one calling a central auth service on every request, while still being able to revoke a compromised user's access quickly?"

**You (architect answer):**

> "I'd issue short-lived, signed JWT access tokens from a central identity provider — signed with an asymmetric key, RS256, not a shared secret — so every downstream service can verify the token's authenticity locally using a cached public key from a JWKS endpoint, with zero network call back to the auth service on the request path. That solves the fan-out bottleneck.
>
> The tradeoff is revocation: a self-contained token can't be un-issued. I'd bound that risk by keeping the access token TTL short, 10 minutes or so, and pairing it with a refresh token that IS checked server-side on each use, with reuse-detection — if a refresh token that's already been rotated shows up again, that's a signal of theft, and I revoke the entire token family immediately. So the worst-case exposure window for a compromised access token is capped at its own short TTL, while the refresh flow gives me a real revocation point without making every request hit the database.
>
> For authorization, I'd keep roles in the JWT claims themselves for coarse RBAC checks — no extra lookup needed, since the role list travels with the token. If we need finer-grained, attribute-based decisions later, I'd push those into a dedicated policy engine rather than overload the token itself, since attribute-based rules change more often than a user's role does and I don't want to force a re-login every time a business rule changes."

---

## PART 5 — DECISION FRAMEWORK

| Approach | Verification Cost | Revocation Speed | Best For |
|---|---|---|---|
| **Session cookie + server-side store** | Network round trip every request | Instant (delete row) | Small-medium systems, single deployment, revocation-critical apps |
| **Stateless JWT (short TTL) + refresh rotation** | Local, in-memory, sub-millisecond | Bounded by access-token TTL (5-15 min) | Microservices, high fan-out, mobile clients |
| **Opaque token + introspection endpoint** | One network call per request to auth server | Instant | When you need JWT's format-agility tradeoffs but can't accept the revocation gap |
| **RBAC** | O(1) lookup, roles embedded in token | N/A | Simple permission models, most CRUD apps |
| **ABAC / policy engine (OPA)** | Policy evaluation per request, can be cached | N/A | Complex, context-dependent, multi-tenant, compliance-heavy permission models |
