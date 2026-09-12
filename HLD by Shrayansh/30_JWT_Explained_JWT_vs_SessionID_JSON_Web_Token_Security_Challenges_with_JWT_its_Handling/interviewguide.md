# Interview Guide: JWT (JSON Web Token) — JWT vs Session ID, Structure, and Security Challenges

## 🗣️ The Interview Scenario

> "We're moving away from session-based auth to JWTs for our microservices platform because 'sessions don't scale.' Explain exactly what problem JWT solves, walk me through its structure, and then tell me — if a JWT is stateless, how do you *invalidate* one before it expires, say for a user we just banned for fraud?"

This is a favorite staff-level follow-up because most candidates can define JWT, but very few can cleanly answer the token invalidation problem — which is precisely where the "JWT is stateless" advantage becomes a real operational headache.

## 🏗️ Architect's Explanation (For a New Developer)

Think of a **JWT** like a **sealed, tamper-evident wristband** you get at a festival. The moment security scans your wristband, they don't need to call the front office and look you up in a database — the wristband itself already has your name, your access level (VIP/general), and an expiry date printed on it, and it has a special seal that proves nobody peeled it off and swapped in a fake one.

That's exactly what a JWT is: a **self-contained, digitally signed JSON object** that carries user information (identity, roles, expiry) and can be verified by anyone holding the right key — **without needing to look anything up in a database**. This is why JWT is called **stateless**.

This is fundamentally different from the older **Session ID** approach, where the wristband is just a random number, and security has to radio back to the front office *every single time* to check "what does this number mean again?" — that's a **stateful** approach (the server has to store and query session data).

JWT today is heavily used for three things:
1. **Authentication** — confirming *who* the user is.
2. **Authorization** — confirming *what* the user is allowed to do.
3. **Single Sign-On (SSO)** — logging into multiple applications using one token, without re-entering credentials each time.

## 📊 Visualize It

**JWT-based Authentication Flow:**

```
   Client              Authentication Server           Resource Server (Your App)
     |--- 1. username/password ------->|
     |<-- 2. JWT (signed token) -------|
     |                                                  |
     |--- 3. GET /resource                              |
     |     Authorization: Bearer <JWT> ----------------->|
     |                                  |<-- 4. verify token (server calls Auth Server's /verify API) --|
     |                                  |--- 5. valid/invalid --------------------------->|
     |<---------------------------------------------------- 6. data returned (if valid) --|
```

**JWT vs. Session ID — where the "state" lives:**

```
SESSION ID (stateful)                          JWT (stateless)
Client --login--> Server                        Client --login--> Auth Server
Server creates session_id, SAVES it in DB       Auth Server generates JWT (contains
   session_id -> {user, roles, expiry}            user info + expiry + signature)
Server <--session_id-- Client (cookie)          Auth Server --JWT--> Client
                                                 
Every subsequent request:                       Every subsequent request:
Client --session_id--> Server                   Client --JWT (in header)--> Resource Server
Server --QUERY DB-----> fetch session data      Resource Server verifies SIGNATURE only
   (extra latency, DB dependency,                  (no DB lookup needed — info is IN the token)
    tricky in distributed systems with
    multiple DB clusters to keep in sync)
```

## 🔧 Deep Dive: How It Actually Works

### JWT Structure: Three Dot-Separated Parts

`base64(header).base64(payload).base64(signature)`

**1. Header** — metadata about the token:
- `typ` — always `"JWT"`.
- `alg` — the signing algorithm used, e.g., `RSA` or `HMAC` (`HS256`).

**2. Payload** — contains **claims** (information), divided into three categories:
- **Registered claims** — reserved, standardized names with specific meaning:
  - `iss` (issuer) — who issued the token.
  - `sub` (subject) — unique identifier of the user.
  - `aud` (audience) — intended recipient of the token.
  - `exp` (expiry) — token invalid after this time.
  - `nbf` (not before) — token not valid *before* this time.
  - `iat` (issued at) — when the token was issued.
  - `jti` (JWT ID) — a unique ID for this specific token (important later for invalidation/blacklisting).
- **Public claims** — custom claims meant to be understood across multiple parties (e.g., `email`, `country`) — but **never put confidential data** (like passwords) here, since the payload is only base64-*encoded*, not encrypted, and is trivially decodable.
- **Private claims** — custom claims intended only for internal use by the issuing authentication server; other resource servers may not understand or use them.

**3. Signature** — proves the token wasn't tampered with:
1. Base64-encode the header.
2. Base64-encode the payload.
3. Concatenate: `encoded_header + "." + encoded_payload`.
4. Pass that concatenated string, plus a key, into a signing algorithm:
   - **HMAC** — same secret key used to sign and verify (symmetric).
   - **RSA** — sign with the **private key**, verify with the **public key** (asymmetric).
5. Base64-encode the resulting signature value.
6. Final JWT = `encoded_header.encoded_payload.encoded_signature`.

### Sending the Token: The `Authorization` Header

Requests carry the token as: `Authorization: Bearer <token>`.

- `Bearer` tells the server "this is a token, treat it as such" — as opposed to `Basic` (base64-encoded `username:password`), which requires entirely different server-side handling logic.

### JWT vs. Session ID — Head-to-Head

| Aspect | Session ID | JWT |
|---|---|---|
| State | Stateful — server stores session data in DB | Stateless — all info is in the token itself |
| Per-request cost | DB/cache lookup on every request | Just signature verification (no DB hit needed) |
| Distributed systems | Requires DB cluster sync across nodes — added complexity | No DB dependency for verification — easier to scale horizontally |
| Revocation | Trivial — just delete the session record | Hard — see Token Invalidation problem below |

### Advantages of JWT (Recap)
- **Compact** — small enough to fit in an HTTP header, fast to transmit.
- **Stateless / self-contained** — expiry, user ID, roles all embedded; no DB dependency for reads.
- **Digitally signed** (this specific signed variant is technically called **JWS** — JSON Web Signature; in practice "JWT" and "JWS" are used interchangeably because nobody uses an unsigned JWT in production).
- **Built-in expiry mechanism** via `exp`.
- **Custom claims** for extensibility (roles, permissions, etc.).

### Single Sign-On (SSO) via JWT

Once a user authenticates and receives a JWT, that **same token** can be presented to multiple applications (App1, App2, App3). Each app independently verifies the signature (and reads the payload for identity info) without requiring the user to log in again at each app — this is the mechanism behind SSO.

### The Big Production Problem: Token Invalidation

Because JWT is stateless, the resource server has **no built-in way to know** that a specific token should suddenly be considered invalid before its `exp` time — e.g., a user gets flagged as fraudulent mid-session but their token is still valid for hours.

**Solutions (each with trade-offs):**

1. **Blacklist lookup** — maintain a list of blacklisted `jti` values in a DB/cache; check every incoming token's `jti` against this list.
   - *Downside:* reintroduces the exact DB/cache lookup overhead that JWT was meant to avoid.
2. **Rotate the signing key** — change the private/public key pair used for signing; all tokens signed with the old key instantly fail verification.
   - *Downside:* this invalidates tokens for **all users**, not just the fraudulent one — genuine users get logged out too.
3. **Short-lived tokens** — make tokens expire quickly (e.g., 5 minutes) instead of hours/days.
   - *Downside:* doesn't eliminate the window of risk, just shrinks it.
4. **Single-use tokens + short TTL (combined)** — a token can only be used once, and expires quickly; commonly combined for higher-security flows. Still requires some lookup (cache) to track "have I seen this `jti` before?"

In practice, most production systems mix short-lived access tokens (5–15 minutes) with a longer-lived refresh token that *can* be revoked server-side, balancing statelessness with the ability to cut off access reasonably quickly.

### Encoded, Not Encrypted — and JWE

The payload is only **base64-encoded**, which is trivially reversible (not encryption) — meaning anyone who intercepts the token can read the payload's contents (though they cannot forge a valid signature without the key). This is why you should never put secrets/passwords in the payload.

If you need the payload contents themselves to be hidden, use **JWE (JSON Web Encryption)** — same overall approach, but the payload is *encrypted* (not just encoded), so only parties holding the correct decryption key can read it.

### "Unsecured JWT" — a Red Flag

If a token's header specifies `alg: none`, it means there is **no signature at all**. Such tokens (called **unsecured JWTs**) must **always be rejected** — accepting them means anyone could forge arbitrary claims with zero verification.

### The JWK Exploit (Important Interview Trap)

The header can optionally include a **JWK (JSON Web Key)** — the public key material itself (`n`/`e` = modulus/exponent forming an RSA public key), plus a **`kid`** (Key ID).

**The exploit:** if a resource/authorization server naively trusts the public key embedded *inside the incoming token's own header* to verify that token's signature, an attacker can:
1. Modify the payload (e.g., escalate their own role/claims).
2. Generate their **own** private/public key pair.
3. Sign the tampered token with their own private key.
4. Embed their own public key in the JWK header field.

The server would then "verify" the signature successfully — using the attacker's own public key — and wrongly accept the tampered payload as valid.

**The correct approach:** never trust a public key embedded in the token's own header. Instead, use the `kid` to look up the correct public key from the authorization server's own **pre-published, whitelisted `well-known/jwks.json`** endpoint — a trusted, server-controlled list of valid public keys, not anything supplied by the token itself.

## 🔥 Real Production Incident & Fix

**What broke:** A SaaS company's backend team migrated user roles/permissions checks to rely entirely on JWT claims for performance. Shortly after, a security researcher (via a bug bounty program) reported that a user who had their account **suspended for policy violations** could still perform privileged actions for nearly 45 minutes after suspension.

**How it was detected:** The security team correlated the bug bounty report with support/admin logs — the suspension action was recorded in the admin panel at time T, but API access logs showed successful authenticated requests from the same user's token up until roughly T+45 minutes, matching the JWT's `exp` window exactly.

**Root cause:** The team had implemented **pure stateless JWT verification** — resource servers only checked the token's signature and `exp`, with zero mechanism to check "has this specific user/token been revoked since issuance?" Suspending a user in the admin panel only flagged their account in the database; it never touched the already-issued, still-cryptographically-valid JWT.

**The fix:**
1. Introduced a lightweight **revocation cache** (Redis) keyed by `jti` (and separately by `sub`/user ID for "revoke all tokens for this user" scenarios), checked on every request — a small, fast lookup rather than a full DB query.
2. Reduced access token TTL from 24 hours to **15 minutes**, backed by a revocable refresh token, so even without the cache check, the maximum exposure window shrank drastically.
3. Admin "suspend user" action now also immediately writes an entry to the revocation cache, so already-issued tokens are rejected on the very next request.

```
BEFORE:                                       AFTER:
Admin suspends user in DB                     Admin suspends user in DB
        |                                              |
        v                                              v
JWT still cryptographically valid             Suspension ALSO writes jti/sub
until natural expiry (up to 24h)              to Redis revocation cache
        |                                              |
        v                                              v
Resource server only checks                   Resource server checks signature
signature + exp -> ACCEPTS request            + exp + revocation cache -> REJECTS
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: If JWT is meant to be stateless, isn't adding a revocation cache defeating the whole purpose?**
It's a deliberate trade-off, not a contradiction — you keep the stateless benefit for the vast majority of requests (fast signature-only verification, no full DB query), while accepting a small, fast cache lookup specifically to close the "can't invalidate before expiry" gap; this is far cheaper than the original session-ID approach's full DB round-trip per request.

**Q2: Why should you never put sensitive data like a password in the JWT payload?**
The payload is only base64-*encoded*, not encrypted — anyone who intercepts the token (or even just reads it from browser storage) can trivially decode it back into readable JSON, so any sensitive data placed there is effectively exposed in plaintext; use JWE if the payload itself must be confidential.

**Q3: What's the actual difference between JWT, JWS, and JWE?**
JWT is the general concept/format of a JSON-based token; JWS (JSON Web Signature) is a JWT that has been digitally signed (the vast majority of "JWTs" in practice are technically JWS); JWE (JSON Web Encryption) is a variant where the payload is encrypted rather than just base64-encoded, protecting confidentiality of the claims themselves, not just their integrity.

**Q4: Why is the JWK-in-header trust issue considered a serious vulnerability?**
Because it inverts the trust model — instead of the verifier deciding which public key to trust (from its own whitelisted key store), it lets the *token itself* dictate which key to verify it with, which means an attacker who can forge a token can also supply the "correct" key to make that forged token pass verification; the fix is to always resolve the key via a trusted `kid` lookup against the authorization server's own published JWKS, never from the incoming token's embedded key material.

**Q5: How would you implement Single Sign-On (SSO) using JWT across three different internal applications?**
Each application shares trust in a common authentication server; a user logs in once against that authentication server and receives a JWT, and each application independently verifies that JWT's signature (using the authentication server's public key or a shared secret) to confirm the user's identity and claims, without requiring the user to log in separately at each app.

**Q6: Why is a short-lived access token combined with a longer-lived refresh token a common pattern?**
It balances security and usability: the access token used on every API call is kept short-lived (minutes) to minimize the damage window if it leaks, while the refresh token (which is used far less often and can be stored more securely/revoked server-side) allows the user to get new access tokens without re-entering credentials repeatedly.

## 🔑 Key Takeaway

JWT trades the database-lookup overhead of session IDs for a self-contained, digitally-signed, statelessly-verifiable token — but that same statelessness is exactly why **token invalidation before expiry** (banning a user, rotating a compromised key) requires a deliberate additional mechanism, so always be ready to name at least one (blacklist cache, short TTL + refresh token, or key rotation) in an interview.
