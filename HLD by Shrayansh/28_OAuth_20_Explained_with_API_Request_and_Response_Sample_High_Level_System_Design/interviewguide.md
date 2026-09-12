# Interview Guide: OAuth 2.0

## 🗣️ The Interview Scenario

> "We're building a new consumer app and product wants a 'Sign in with Google' button on the login page instead of forcing users to create yet another password. Walk me through how you'd design this end-to-end — who talks to whom, what gets exchanged, and what could go wrong if you implement it carelessly?"

This is a classic staff-level question because it isn't really about "do you know what OAuth stands for" — it's about whether you understand the *actors*, the *token exchange*, and the *security pitfalls* (CSRF, token leakage) well enough to defend a design under follow-up pressure.

## 🏗️ Architect's Explanation (For a New Developer)

Think of OAuth 2.0 as a **valet key** system. When you hand a valet your car, you don't give them your house key too — you give them a limited key that can only start the engine and drive a few hundred meters, not open the trunk or the glovebox.

OAuth 2.0 is the same idea for your online identity. Instead of handing a third-party website your Gmail *password* (the master key to your entire account), you let Gmail hand that website a *limited, revocable token* that only proves "yes, this user is who they say they are" and only unlocks the specific pieces of data (profile, email) the user agreed to share.

OAuth is an **authorization framework** — it's about granting *access*, not about *proving identity* in the deepest sense (that nuance is why OpenID Connect exists on top of it, but let's stay focused on OAuth here).

There are always **four actors** in this play:

| Actor | Real-world example | What it means |
|---|---|---|
| **Resource Owner** | You (the human) | The person who owns the protected data |
| **Client** | The third-party app (e.g., Instagram) | The application that *wants* access to your data |
| **Authorization Server** | Gmail's auth service | Issues tokens after you consent |
| **Resource Server** | Gmail's API that holds your profile | Actually stores/serves the protected data |

In practice a big provider like Google often runs the Authorization Server and Resource Server as separate internal services, but conceptually they are two distinct responsibilities.

## 📊 Visualize It

**Authorization Code Grant — the "gold standard" flow:**

```
 Resource Owner        Client (Instagram)      Auth Server (Gmail)      Resource Server (Gmail)
      (You)                   |                        |                        |
        |--- 1. Click "Sign in with Gmail" ----------->|                        |
        |                     |--- 2. Redirect to /authorize (client_id, ------->|
        |                     |        redirect_uri, scope, state)              |
        |<---------------------------- 3. Login + Consent screen ---------------|
        |--- 4. Approve consent -------------------------------------------->   |
        |                     |<-- 5. Redirect back with (code, state) ---------|
        |                     |--- 6. POST /token (code, client_id, ----------->|
        |                     |        client_secret, grant_type=auth_code)     |
        |                     |<-- 7. access_token + refresh_token -------------|
        |                     |--- 8. GET /profile  (Authorization: Bearer AT)---------------------->|
        |                     |<--------------------------- 9. validate token, return profile data --|
        |<-- 10. "Welcome, User!" (logged in) --------|                        |
```

**The CSRF attack this flow must defend against (without `state`):**

```
Attacker                     You (victim)              Instagram              Gmail Auth Server
   |-- calls /authorize, gets its own auth_code -->|
   | (saves code, doesn't use it)                   |
   |                                                 |
   |------ tricks you into visiting the callback ---|
   |       URL with attacker's auth_code ----------->|--- exchanges attacker's code for a token ---->|
   |                                                 |<-- gets token bound to ATTACKER's account -----|
   |                                                 |--- Instagram now shows attacker's data --------|
   |                                                 |    logged in as if it were you (session mix-up)|
```
Fix: client generates a unique, unguessable `state` per request and rejects any callback where the returned `state` doesn't match.

## 🔧 Deep Dive: How It Actually Works

### Step 0 — Client Registration (one-time setup)
Before any user flow happens, the client (Instagram) registers with the authorization server:
- `POST /register` with `client_name` and up to **3 redirect URIs**.
- Response: `client_id` (public) and `client_secret` (confidential — known only to client + auth server).

### Step 1 — Authorization Request (`GET /authorize`)
When the user clicks "Sign in with Gmail," the client redirects the browser with these parameters:
- `response_type=code` → tells the auth server "I want an authorization code back."
- `client_id` → identifies the client from registration.
- `redirect_uri` → optional; if omitted, the auth server uses one of the pre-registered URIs. If provided, it **must match** one of the registered URIs.
- `scope` → space-separated list of what data the client wants (e.g., `email profile address`).
- `state` → a random, hard-to-guess value used purely for CSRF protection (see below).

### Step 2 — User Authentication + Consent
The user logs into Gmail (if not already) and sees a consent screen ("Instagram wants to access your email and profile — allow?"). Approval triggers a redirect back to `redirect_uri` with `code` and the same `state` that was sent.

### Step 3 — CSRF Protection via `state`
The client compares the `state` it receives against the one it originally sent:
- No `state` in response → discard the request.
- `state` mismatch → discard the request (possible CSRF/injected authorization code).
- `state` matches → accept the authorization code.

### Step 4 — Token Exchange (`POST /token`, grant_type=authorization_code)
The client calls the token endpoint with:
- `grant_type=authorization_code`
- `code` (from Step 2)
- `redirect_uri` (must match the one used earlier)
- `client_id` + `client_secret` → **this is where the client authenticates itself**, proving it's really Instagram and not an impersonator.

Response:
- `access_token` — short-lived (e.g., expires in `3600` seconds / 1 hour, sometimes even shorter like 15–30 min).
- `token_type=Bearer` — tells the client to send this token in the `Authorization` header on future calls.
- `refresh_token` — a long-lived token used to get a new access token without re-authenticating the user.

### Step 5 — Accessing Protected Resources
Client calls the resource server with `Authorization: Bearer <access_token>`. The resource server calls back to the authorization server to validate the token. If valid → data (profile, email, etc.) is returned. If invalid/expired → typically a `401 Unauthorized`.

### Step 6 — Refreshing an Expired Token
`POST /token` again with `grant_type=refresh_token` and the `refresh_token` value (no username/password needed). Response: a **new** access token (and often a new refresh token).

### The Other 3 Grant Types (know these for interviews)

| Grant Type | When used | Key characteristic |
|---|---|---|
| **Implicit Grant** | Legacy SPA-style flows (discouraged today) | Single step — `response_type=token` returns the access token directly in the redirect URI. **No refresh token** because there's no code-exchange step to bind to. |
| **Resource Owner Password Credentials** | Highly trusted first-party apps only | User gives username/password directly to the client, which posts them to `/token` with `grant_type=password`. No `/authorize` call needed. Returns access + refresh token. **Anti-pattern for third-party apps** since it defeats the purpose of never sharing your password. |
| **Client Credentials Grant** | Machine-to-machine (no human user) | Client is *itself* the resource owner. Calls `/token` with `grant_type=client_credentials`, `client_id`, `client_secret`. Returns access token only — **no refresh token** (just call again with the same credentials when it expires). |

## 🔥 Real Production Incident & Fix

**What broke:** A mid-size fintech startup added "Sign in with Google" using the Authorization Code Grant. To ship fast, an engineer implemented the `/authorize` redirect *without* generating or validating a `state` parameter, reasoning "we'll add it later, it's just a nice-to-have."

**How it was detected:** Within two weeks of launch, the fraud team noticed a spike in support tickets: users reported "I logged in and saw someone else's dashboard/orders for a few seconds before it corrected itself." The security team correlated this with unusual patterns in the auth callback logs — the same `redirect_uri` hits arriving with authorization codes that didn't map to the session that initiated the request (visible via mismatched session cookies vs. code-exchange timestamps in the access logs).

**Root cause:** Without `state`, the callback endpoint had no way to verify that the authorization code arriving at `/callback` belonged to the browser session that had just initiated the `/authorize` request. An attacker could pre-generate a valid authorization code for their *own* account, then trick a victim (via a crafted link or an open redirect elsewhere on the site) into hitting the app's callback URL with the attacker's code injected. The victim's browser would complete the token exchange using the attacker's authorization code, effectively logging the victim into the **attacker's** account — a classic **login CSRF**, which can be used to plant malicious data (e.g., attacker's payment details) into what the victim believes is their own session.

**The fix:**
1. Generate a cryptographically random `state` value per login attempt and store it tied to the user's browser session (signed cookie).
2. Reject any `/callback` request where the returned `state` doesn't exactly match the session's stored value.
3. Added `state` expiry (5 minutes) so stale/replayed states are also rejected.
4. Rotated all active refresh tokens as a precaution and added a WAF rule to detect the injection pattern.

```
BEFORE (vulnerable):                     AFTER (fixed):
/authorize?client_id=X                   /authorize?client_id=X&state=<random-per-session>
   (no state)                                  |
   |                                            v
   v                                    /callback?code=...&state=<same-random>
/callback?code=...                            |
   (blindly exchanges code)                    v
                                        compare state == stored session state?
                                        NO  -> reject, log security event
                                        YES -> proceed to token exchange
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why does the client need a `client_secret` if the `authorization_code` already proves the user consented?**
The `code` proves the *user* consented, but the token endpoint also needs to verify that the *caller* is genuinely the registered client and not an attacker who intercepted the code from a poorly protected redirect. The `client_secret` (known only to the client and authorization server) is what authenticates the client itself — it's a separate trust dimension from user consent.

**Q2: Why is Implicit Grant discouraged today?**
Because the access token is returned directly in the URL fragment of a redirect with no server-side exchange step, it's exposed to browser history, referrer headers, and any JavaScript on the page — there's no way to bind the token issuance to a client secret, and there's no refresh token. Modern guidance (RFC 8252/OAuth 2.1) recommends Authorization Code Grant + PKCE even for public clients like SPAs and mobile apps instead.

**Q3: What's the difference between an access token and a refresh token in terms of security handling?**
Access tokens are short-lived (minutes to an hour) and sent on every API call, so they're treated as "disposable" — if leaked, the blast radius is time-limited. Refresh tokens are long-lived and powerful (they can mint new access tokens indefinitely), so they should never be exposed to client-side JavaScript and should be stored server-side or in secure httpOnly cookies, and should be revocable.

**Q4: How would you revoke access if a user's OAuth-connected app is compromised?**
The authorization server maintains a token revocation list/registry tied to the `client_id` + user pairing. Revoking invalidates the refresh token (and ideally any live access tokens via a short TTL plus introspection endpoint), forcing the client to re-run the full authorization flow to get access again.

**Q5: When would you use Client Credentials Grant over Authorization Code Grant?**
Client Credentials is for machine-to-machine communication where there's no human resource owner in the loop — e.g., a backend cron job calling an internal API. Authorization Code Grant is for delegated *user* consent scenarios where a human is authorizing access to their own data.

**Q6: Is the access token itself always a JWT?**
No — the spec doesn't mandate a format. It can be an opaque random string that the resource server validates by calling back to the authorization server, or it can be a self-contained JWT that the resource server can validate locally using the authorization server's public key, trading off an extra network hop for local validation speed.

## 🔑 Key Takeaway

OAuth 2.0 is fundamentally about **delegated, scoped, revocable authorization** using short-lived tokens instead of sharing passwords — and the `state` parameter (plus the client secret at token-exchange time) is what stands between a clean login flow and a CSRF/token-injection vulnerability, so always call it out explicitly when describing the flow in an interview.
