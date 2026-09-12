# OAuth 2.0 — Explained with API Request and Response Samples

## What is this? (Plain English)

OAuth 2.0 ("Open Authorization") is a framework that lets you grant a third-party app limited access to your data on another service, **without ever handing over your password**.

Think of it like a hotel valet key: when you check into a hotel, you don't give the valet your house keys — you give them a special valet key that only starts the car and opens the driver's door, nothing else (not the trunk, not the glovebox). OAuth works the same way: when you click "Sign in with Google" on some third-party website, you're not giving that website your Gmail password. Instead, Google hands the website a limited "valet key" (an access token) that only unlocks the specific pieces of your profile you agreed to share (like your name, email, or profile picture) — nothing more.

## The Problem It Solves

Before OAuth, the only way for a third-party site to act on your behalf on another service was for you to directly type your username and password into that third-party site. That approach has serious problems:

- The third-party site now **permanently stores or at least sees your real password**, so a breach on their end compromises your main account too.
- There's no way to grant **limited/scoped access** — it's all or nothing. You can't say "only let this app see my email, not my whole Drive."
- There's no easy way to **revoke access** to just one app without changing your master password everywhere.

OAuth 2.0 solves this by introducing a **token-based, scoped, revocable** delegation mechanism: the third party gets a short-lived access token limited to specific permissions (scopes), issued by an authorization server that you trust, and you never expose your real credentials to the third party.

## The Four Roles (Actors)

Every OAuth 2.0 flow involves four actors:

1. **Resource Owner** — the end user. In the running example, this is "Shan," who already has a Gmail account and is signed in there.
2. **Client** — the third-party application requesting access (e.g., Instagram), which initiates the request to use the resource owner's data.
3. **Authorization Server** — the component that authenticates the resource owner, collects their consent, and issues authorization codes/tokens (e.g., Gmail's authorization server).
4. **Resource Server** — the component that actually hosts the protected data (e.g., Gmail's resource server, which holds the user's profile — name, age, email, address).

In practice, the Authorization Server and Resource Server are often the same company/service (both "Gmail" in this example), but they are conceptually two distinct components — one handles auth/consent, the other hosts and serves the actual protected data.

## The Grant Types (Five Mechanisms to Obtain a Token)

OAuth 2.0 defines several "grant types" — different mechanisms a client can use to obtain an access token, depending on the trust level and use case:

1. **Authorization Code Grant** — the most common and most secure flow; used when the client is a server-side app that can safely keep a client secret.
2. **Implicit Grant** — a simplified, legacy flow for browser-only apps; no longer recommended.
3. **Resource Owner Password Credentials Grant** — the user gives their username/password directly to the client, which forwards them to the authorization server; only for highly trusted first-party clients.
4. **Client Credentials Grant** — used when the client itself is the resource owner (machine-to-machine access, no end user involved).
5. **Refresh Token Grant** — not a way to log in, but a way to get a new access token once the old one expires, without repeating the whole flow.

## Authorization Code Grant — Full Flow

This is the primary, most widely used flow. Walkthrough using the example: Shan (resource owner) wants to log into Instagram (client) using his Gmail account, where Gmail acts as both the authorization server and resource server.

### Step 0 — Client Registration (one-time setup)

Before any user ever logs in, Instagram must register itself with Gmail's authorization server. Instagram provides an app name and up to three redirect URIs (callback URLs Gmail is allowed to redirect back to). In return, the authorization server issues:
- A **client ID** — identifies the client publicly.
- A **client secret** — confidential, known only to the client and the authorization server; used to authenticate the client later.

### Step 1 — Redirect to Authorization Server

When Shan clicks "Sign in with Gmail" on Instagram, Instagram redirects his browser to Gmail's `/authorize` endpoint with:
- `response_type=code` — tells the authorization server "I want an authorization code back."
- `client_id` — from registration.
- `redirect_uri` — optional; if omitted, one of the URIs given at registration is used; if provided, it must match one of the registered URIs.
- `scope` — space-separated list of what data the client wants access to (e.g., email, profile, address).
- `state` — a random, hard-to-guess value generated by the client, used to prevent CSRF attacks (explained below).

### Step 2 — User Authenticates and Consents

Gmail authenticates Shan (login if not already signed in) and shows a consent screen: "Instagram wants to access your email, profile, and address — do you allow this?" If Shan approves, Gmail redirects back to the client's `redirect_uri` with an **authorization code** and the same `state` value that was sent in the request.

### Step 3 — Exchange Authorization Code for Tokens

Instagram calls Gmail's `/token` endpoint (a POST API) with:
- `grant_type=authorization_code`
- `code` — the authorization code just received.
- `redirect_uri` — optional, same rule as before.
- `client_id` and `client_secret` — this is where the client proves its own identity to the authorization server.

The authorization server responds with:
- `access_token` — a short-lived token (e.g., expires in 3600 seconds / 1 hour) used to access protected data.
- `token_type=Bearer` — tells the client to send this token in the `Authorization` header on subsequent requests.
- `expires_in` — lifetime of the access token, in seconds.
- `refresh_token` — a long-lived token used to obtain a new access token once the current one expires.
- The access token itself may be a plain opaque string or a JWT, depending on the implementation.

### Step 4 — Access Protected Resource

Instagram calls the Gmail **resource server** with the access token, requesting the user's profile data. Internally, the resource server validates the token by asking the authorization server whether it's valid. If valid, the resource server returns the requested profile fields (whatever was granted in `scope`); if invalid, the request is rejected, typically with a `401 Unauthorized`.

### Sequence Diagram (ASCII)

```
Lanes: User = Resource Owner (Shan) | Client = Client (Instagram) | AuthServer = Authorization Server (Gmail) | ResServer = Resource Server (Gmail)

-- One-time setup --
1)  Client ─────────> AuthServer : POST /register (client_name, redirect_uris)
2)  AuthServer ─────────> Client     : client_id, client_secret

-- Authorization Code Grant flow --
3)  User   ──────> Client     : Click "Sign in with Gmail"
4)  Client ──────> User       : Redirect to /authorize?response_type=code&client_id=...&redirect_uri=...&scope=...&state=sj1
5)  User   ──────> AuthServer : Authenticate (login) + view consent screen
6)  AuthServer ──> User       : Show consent ("Instagram wants email, profile, address")
7)  User   ──────> AuthServer : Approve consent
8)  AuthServer ──> Client     : Redirect to redirect_uri?code=AUTH_CODE&state=sj1
9)  Client (self)             : Verify returned state == sj1 (CSRF check)
10) Client ──────> AuthServer : POST /token (grant_type=authorization_code, code, redirect_uri, client_id, client_secret)
11) AuthServer ──> Client     : access_token, refresh_token, expires_in=3600, token_type=Bearer
12) Client ──────> ResServer  : GET /profile (Authorization: Bearer access_token)
13) ResServer ───> AuthServer : Validate access_token
14) AuthServer ──> ResServer  : valid / invalid
    alt token valid:
15)   ResServer ─> Client : 200 OK { name, email, address }
16)   Client    ─> User   : Signed in successfully
    else token invalid:
15)   ResServer ─> Client : 401 Unauthorized
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

### ASCII Fallback Diagram

```text
 Resource Owner        Client               Authorization Server        Resource Server
    (Shan)            (Instagram)                  (Gmail)                   (Gmail)
      |                    |                            |                        |
      |                    |--- POST /register -------->|                        |
      |                    |<-- client_id, secret -------|                        |
      |                    |                            |                        |
      |-- click "Sign in --|                            |                        |
      |    with Gmail" --->|                            |                        |
      |                    |--- redirect: /authorize --->|                        |
      |                    |    (response_type=code,     |                        |
      |                    |     client_id, redirect_uri,|                        |
      |                    |     scope, state=sj1)        |                        |
      |<----------------------- login + consent screen --|                        |
      |--- approve consent ------------------------------>|                        |
      |                    |<-- redirect: code + state=sj1|                        |
      |                    | (verify state == sj1)        |                        |
      |                    |--- POST /token ------------->|                        |
      |                    |  (grant_type=authorization_  |                        |
      |                    |   code, code, redirect_uri,  |                        |
      |                    |   client_id, client_secret)  |                        |
      |                    |<-- access_token, refresh_    |                        |
      |                    |    token, expires_in,        |                        |
      |                    |    token_type=Bearer          |                        |
      |                    |                            |                        |
      |                    |--- GET /profile (Bearer access_token) --------------->|
      |                    |                            |<--- validate token ------|
      |                    |                            |---- valid/invalid ------>|
      |                    |<---------------------------------- 200 OK / 401 ------|
      |<-- signed in ------|                            |                        |
```

## CSRF Protection via the `state` Parameter

The `state` value is not mandatory but strongly recommended. It exists specifically to defend against a **cross-site request forgery (CSRF)** attack on the redirect step. Attack scenario, without `state`:

1. An attacker calls `/authorize` against Gmail's authorization server for their *own* account and receives an authorization code — but instead of using it, the attacker saves it.
2. The legitimate user (Shan) initiates his own login on Instagram, hitting `/authorize` and waiting for Gmail to redirect back with his authorization code.
3. The attacker intercepts this in-flight request and injects **their own** authorization code into the redirect back to Instagram, instead of Shan's.
4. Instagram, having no way to tell the codes apart, accepts the attacker's code and exchanges it for an access token.
5. Instagram then calls Gmail's resource server with that token — but since the token belongs to the attacker's authorization code, Gmail returns the **attacker's** profile data.
6. The end result: Shan is now signed into Instagram as the attacker. Anything Shan does afterward (e.g., uploading files that get associated with a connected Google account) happens against the attacker's account instead of his own.

**Defense:** the client generates a random, hard-to-guess `state` value and sends it with the initial `/authorize` request. When the authorization server redirects back with the authorization code, it must echo the same `state` value. The client then compares the returned `state` against what it originally sent:
- If `state` is missing from the response → discard the request.
- If `state` doesn't match what was sent → discard the request (this is the injected/forged response).
- Only if `state` matches exactly does the client accept the authorization code as legitimate.

## Other Grant Types

### Implicit Grant (legacy, not recommended)

A simplified, single-step version of the Authorization Code Grant, historically used for browser-only apps with no backend to safely store a client secret.

- Client redirects to `/authorize` with `response_type=token` (not `code`), plus `client_id`, `redirect_uri` (optional), `scope`, and `state`.
- The authorization server directly returns the **access token** in the redirect URI itself — there is no separate authorization code and no separate `/token` call.
- There is **no refresh token** in this grant, since there's no two-step exchange to piggyback a refresh token onto.
- This flow is now considered legacy/discouraged because the access token is exposed directly in the browser's URL/redirect.

### Resource Owner Password Credentials Grant

Used only by highly trusted, first-party clients. There is no `/authorize` call and no authorization code at all — the client collects the user's username and password directly and sends them straight to the `/token` endpoint:
- `grant_type=password`
- `username`, `password` — the resource owner's own Gmail credentials.
- `client_id`, `client_secret`
- `scope`

Response: `access_token` and `refresh_token`, same shape as the Authorization Code Grant. To renew via refresh token later, the client does **not** need to resend the username/password — only the refresh token, client ID, and client secret.

### Client Credentials Grant

Used when there is no separate end user — **the client itself is the resource owner** (machine-to-machine communication). The client calls `/token` directly with:
- `grant_type=client_credentials`
- `client_id`, `client_secret`
- `scope`

Response: only an `access_token` — **no refresh token is issued**, because to get a new token the client can simply call `/token` again with the same `client_id`/`client_secret`; there's no need for a separate renewal mechanism. There is also no authorization call involved at all.

### Refresh Token Grant

Not a login mechanism — it's how any of the above flows renews an expired access token without repeating the full flow. The client calls `/token` with:
- `grant_type=refresh_token`
- `refresh_token` — the refresh token obtained from a previous token response.
- `client_id`, `client_secret`
- `redirect_uri` — optional, same rule as before.

Response: a **new** `access_token` and a **new** `refresh_token`.

## Key Code / Config

### Client Registration

```http
POST /register HTTP/1.1
Host: gmail-auth-server.com
Content-Type: application/x-www-form-urlencoded

client_name=Instagram&redirect_uris=https://instagram.com/callback1,https://instagram.com/callback2,https://instagram.com/callback3
```

```json
{
  "client_id": "instagram-client-12345",
  "client_secret": "s3cr3t-only-known-to-client-and-auth-server"
}
```

### Authorization Code Grant — Step 1: Redirect to `/authorize`

```
GET /authorize
    ?response_type=code
    &client_id=instagram-client-12345
    &redirect_uri=https://instagram.com/callback1
    &scope=email profile address
    &state=sj1
Host: gmail-auth-server.com
```

Redirect back after consent:

```
HTTP/1.1 302 Found
Location: https://instagram.com/callback1?code=AUTH_CODE_XYZ&state=sj1
```

### Authorization Code Grant — Step 2: Exchange code for tokens

```http
POST /token HTTP/1.1
Host: gmail-auth-server.com
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code=AUTH_CODE_XYZ
&redirect_uri=https://instagram.com/callback1
&client_id=instagram-client-12345
&client_secret=s3cr3t-only-known-to-client-and-auth-server
```

```json
{
  "access_token": "ya29.a0AfH6...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "1//0gLp...longLivedToken"
}
```

### Accessing Protected Data with the Access Token

```http
GET /userinfo HTTP/1.1
Host: gmail-resource-server.com
Authorization: Bearer ya29.a0AfH6...
```

```json
{
  "name": "Shan",
  "email": "shan@gmail.com",
  "address": "..."
}
```

Invalid/expired token response:

```http
HTTP/1.1 401 Unauthorized
```

### Refresh Token Grant — Getting a New Access Token

```http
POST /token HTTP/1.1
Host: gmail-auth-server.com
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token=1//0gLp...longLivedToken
&client_id=instagram-client-12345
&client_secret=s3cr3t-only-known-to-client-and-auth-server
```

```json
{
  "access_token": "ya29.newAccessToken...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "1//0gNew...refreshToken"
}
```

### Implicit Grant — Direct Token in Redirect

```
GET /authorize
    ?response_type=token
    &client_id=instagram-client-12345
    &redirect_uri=https://instagram.com/callback1
    &scope=email profile
    &state=sj2
Host: gmail-auth-server.com
```

```
HTTP/1.1 302 Found
Location: https://instagram.com/callback1#access_token=ya29.a0AfH6...&token_type=Bearer&expires_in=3600&state=sj2
```

(No `refresh_token` is returned — implicit grant is single-step.)

### Resource Owner Password Credentials Grant

```http
POST /token HTTP/1.1
Host: gmail-auth-server.com
Content-Type: application/x-www-form-urlencoded

grant_type=password
&username=shan@gmail.com
&password=user_password
&client_id=instagram-client-12345
&client_secret=s3cr3t-only-known-to-client-and-auth-server
&scope=email profile
```

```json
{
  "access_token": "ya29.a0AfH6...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "1//0gLp...longLivedToken"
}
```

### Client Credentials Grant (machine-to-machine, no refresh token)

```http
POST /token HTTP/1.1
Host: gmail-auth-server.com
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=instagram-client-12345
&client_secret=s3cr3t-only-known-to-client-and-auth-server
&scope=internal-api-access
```

```json
{
  "access_token": "ya29.a0AfH6...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

## Important Concepts

- **Resource Owner**: The end user who owns the protected data and grants (or denies) consent for a client to access it.
- **Client**: The third-party application requesting access to the resource owner's data (e.g., Instagram wanting Gmail profile data).
- **Authorization Server**: Authenticates the resource owner, obtains consent, and issues authorization codes and tokens.
- **Resource Server**: Hosts the actual protected data and serves it once a valid access token is presented; validates tokens against the authorization server.
- **Client ID / Client Secret**: Issued during one-time client registration. The client ID is public; the client secret is confidential and used to authenticate the client itself (not the user) when exchanging codes/tokens.
- **Authorization Code**: A short-lived, single-use code returned after user consent, exchanged by the client (with its client secret) for an access token — this indirection keeps the access token off the browser/redirect URL.
- **Access Token**: A short-lived credential (e.g., expires in ~1 hour) used to call the resource server; sent as a `Bearer` token in the `Authorization` header. May be a plain opaque string or a JWT.
- **Refresh Token**: A long-lived credential used to obtain a new access token once the current one expires, without repeating the full authorization flow. Not issued by the Implicit Grant or Client Credentials Grant.
- **Scope**: A space-separated list defining exactly which pieces of data/permissions the client is requesting (e.g., `email profile address`) — enables least-privilege, granular access instead of all-or-nothing.
- **`state` Parameter**: A random, client-generated value echoed back by the authorization server with the authorization code; used to detect and reject CSRF attacks where an attacker tries to inject their own authorization code into a victim's redirect flow.
- **Grant Types**: Five mechanisms to obtain a token — Authorization Code Grant (standard, most secure), Implicit Grant (legacy, no refresh token), Resource Owner Password Credentials Grant (trusted first-party apps only), Client Credentials Grant (machine-to-machine, no refresh token), and Refresh Token Grant (renewal, not a login mechanism).

## Interview Q&A

**Q1: Why does OAuth 2.0 use a separate "authorization code" step instead of just returning the access token directly at `/authorize`?**
A: Returning the code first (instead of the token) keeps the access token out of the browser's redirect URL/history, and forces the client to prove its identity with the client secret at the `/token` exchange step. This is more secure than the Implicit Grant, which returns the token directly in the redirect and is now discouraged.

**Q2: What problem does the `state` parameter solve, and what happens if a client skips it?**
A: It prevents a CSRF attack where an attacker's own authorization code is injected into a victim's redirect flow, causing the victim to get signed in under the attacker's account. Skipping `state` means the client cannot verify that the authorization code it receives actually corresponds to the request it originally sent, leaving it vulnerable to this attack.

**Q3: Why doesn't the Client Credentials Grant return a refresh token?**
A: Because there's no separate user session to preserve — the client itself is the resource owner, so if the access token expires, the client can simply call `/token` again with its own `client_id`/`client_secret` and get a fresh token immediately. There's no extra step a refresh token would simplify.

**Q4: What's the difference between the Resource Owner Password Credentials Grant and the Authorization Code Grant?**
A: In the Authorization Code Grant, the user authenticates directly with the authorization server and the client never sees the user's password — only an authorization code, then a token. In the Password Credentials Grant, the user hands their actual username/password to the client, which forwards them to the authorization server; this is only acceptable for highly trusted first-party clients since it defeats OAuth's core goal of never exposing credentials to third parties.

**Q5: How does the resource server know whether an access token presented to it is still valid?**
A: The resource server calls back to the authorization server to validate the token. If valid, the authorization server confirms it (and the resource server returns the requested scoped data); if invalid or expired, the resource server rejects the request, typically with a `401 Unauthorized`.

**Q6: If an access token expires while a user is mid-session, does the user have to log in again?**
A: No — the client uses the `refresh_token` grant, calling `/token` with `grant_type=refresh_token` plus the refresh token, client ID, and client secret, to silently obtain a new access token (and a new refresh token) without requiring the user to re-authenticate. This is not available for the Implicit Grant or Client Credentials Grant, since neither issues a refresh token.
