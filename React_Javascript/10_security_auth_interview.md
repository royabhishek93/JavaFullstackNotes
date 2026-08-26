# React Security & Authentication — 15-YOE Interview Prep

> Target: Staff / Principal / Senior II roles. Every answer here reflects production-hardened thinking,
> not just "I read the docs." Expect follow-up drilling — have a war story ready for each topic.

---

## 1. Big Picture — Auth & Security Architecture

### OAuth 2.0 + PKCE Flow (SPA)

```
Browser (SPA)                    Auth Server (AS)              Resource Server (API)
     |                                  |                              |
     |-- 1. Generate code_verifier  --->|                              |
     |   code_challenge = SHA256(cv)    |                              |
     |                                  |                              |
     |-- 2. GET /authorize ------------>|                              |
     |   ?response_type=code            |                              |
     |   &client_id=...                 |                              |
     |   &redirect_uri=...              |                              |
     |   &code_challenge=...            |                              |
     |   &code_challenge_method=S256    |                              |
     |                                  |                              |
     |<- 3. Redirect back with ?code=.. |                              |
     |                                  |                              |
     |-- 4. POST /token ---------------->|                              |
     |   grant_type=authorization_code  |                              |
     |   code=...                       |                              |
     |   code_verifier=...  (secret!)   |                              |
     |                                  |                              |
     |<- 5. { access_token,             |                              |
     |        refresh_token,            |                              |
     |        id_token } --------------|                              |
     |                                  |                              |
     |-- 6. GET /api/data  Bearer AT -->|----------------------------->|
     |                                  |                     validate |
     |<- 7. Protected resource <--------|<----------------------------|
```

### Security Layers Onion

```
┌─────────────────────────────────────────────────────────────┐
│  NETWORK LAYER                                              │
│  HTTPS / TLS everywhere   ·   HSTS preload                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  TRANSPORT LAYER                                    │   │
│  │  Secure + SameSite cookies   ·   No mixed content   │   │
│  │  ┌─────────────────────────────────────────────┐   │   │
│  │  │  APPLICATION LAYER                          │   │   │
│  │  │  CSP headers   ·   X-Frame-Options           │   │   │
│  │  │  CSRF tokens / SameSite=Strict               │   │   │
│  │  │  ┌─────────────────────────────────────┐   │   │   │
│  │  │  │  REACT LAYER                        │   │   │   │
│  │  │  │  JSX auto-escaping                  │   │   │   │
│  │  │  │  No dangerouslySetInnerHTML w/o      │   │   │   │
│  │  │  │  DOMPurify sanitization              │   │   │   │
│  │  │  │  ┌─────────────────────────────┐   │   │   │   │
│  │  │  │  │  DATA LAYER                 │   │   │   │   │
│  │  │  │  │  Parameterized queries      │   │   │   │   │
│  │  │  │  │  Input validation           │   │   │   │   │
│  │  │  │  │  Secrets NEVER in bundle    │   │   │   │   │
│  │  │  │  └─────────────────────────────┘   │   │   │   │
│  │  │  └─────────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### JWT Storage Decision Tree

```
Where to store tokens?

                    ┌─────────────────────────┐
                    │ What are you storing?   │
                    └────────────┬────────────┘
                                 │
               ┌─────────────────┴──────────────────┐
               ▼                                     ▼
        Access Token                          Refresh Token
     (short-lived, 5-15m)               (long-lived, days/weeks)
               │                                     │
     ┌─────────┴─────────┐                ┌──────────┴──────────┐
     ▼                   ▼                ▼                     ▼
  Memory             localStorage    httpOnly cookie         localStorage
  (React state)      ← AVOID:        ← BEST: JS can't        ← WORST:
  BEST: gone on       XSS reads it    read it, CSRF-safe       XSS can
  tab close                           with SameSite=Strict      steal it
```

---

## 2. Conversational Interview Script

### Opening Frame (how a 15-YOE engineer answers "tell me about React security")

> "Security in React isn't a single feature — it's defense in depth. React's JSX gives you automatic
> HTML escaping for free, which kills most reflected XSS. But that only covers one attack vector.
> The real work is in how you handle authentication tokens, configure your HTTP headers, structure
> OAuth flows, and make sure your engineers don't accidentally bypass the safety rails — like with
> dangerouslySetInnerHTML or putting secrets in .env files that ship to the browser.
>
> In my last few roles I've owned the full auth stack: token issuance, refresh rotation, CSP policy,
> and the RBAC middleware in Next.js. I've also done a couple of post-incident reviews where the root
> cause was one of those beginner-looking mistakes that sneak into production — like an implicit OAuth
> flow left over from 2018, or a refresh token sitting in localStorage."

### On Being Asked "How Does XSS Work?"

> "XSS is when an attacker gets their JavaScript to execute in another user's browser session.
> There are three flavors. Reflected: the payload is in the URL, the server echoes it back
> unsanitized, and the victim's browser executes it. Stored: the payload is persisted to the database
> and served to every user who loads that page. DOM-based: the vulnerability is entirely in client
> code — something like reading location.hash and writing it with innerHTML.
>
> React kills most of this by design. Every JSX expression goes through escaping before it hits
> the DOM. The exception is dangerouslySetInnerHTML, which is the escape hatch and lives up to its
> name. Whenever I see it in code review I ask: does this content come from user input? If so,
> we need DOMPurify before it gets anywhere near that prop."

### On Being Asked "JWT vs Sessions"

> "They solve the same problem differently. Sessions keep state server-side — the server holds a
> session store (Redis usually), issues an opaque ID in a cookie, and every request gets validated
> by a database lookup. JWTs are self-contained — everything the server needs to verify identity
> is in the token itself, signed with a secret or private key. No lookup needed.
>
> JWTs shine in distributed systems: microservices can all verify the token without calling a central
> auth service. The downside is revocation — you can't 'invalidate' a JWT before it expires unless
> you maintain a blocklist, which brings back the database lookup you were trying to avoid.
>
> For storage: I always push short-lived access tokens into memory (React state or a module-level
> variable), and if I need persistence I put refresh tokens in httpOnly, SameSite=Strict cookies.
> HttpOnly means JavaScript literally cannot read the cookie — XSS can't steal it. SameSite=Strict
> means it won't be sent on cross-site requests — CSRF doesn't apply."

---

## 3. Scenario-Based Q&As

### Q1: Your SPA needs to call a third-party API with a secret API key. How do you handle this?

**Trap in the question:** The word "secret" is the tell. In a pure SPA, you cannot keep anything secret
— the entire bundle ships to the user's browser.

**Answer:**
> "You don't. A secret API key in a frontend bundle is not a secret — anyone can open DevTools
> Network tab or deobfuscate your bundle and extract it. The correct architecture is a thin BFF
> (Backend For Frontend) — a server-side endpoint your SPA calls, and the server holds the API key
> in an environment variable or secrets manager (Vault, AWS Secrets Manager, GCP Secret Manager).
> The BFF authenticates your users, enforces rate limits, and proxies to the third-party API.
> Your frontend never sees the key."

**What REACT_APP_ vars actually do:**
```typescript
// .env
REACT_APP_API_KEY=super_secret_123

// After build, this is in your bundle as a plain string:
// "super_secret_123"
// Vite equivalent: VITE_API_KEY — same problem
// Anyone can `cat build/static/js/main.xxx.js | grep super_secret`
```

---

### Q2: A user reports they're being logged out randomly. You suspect refresh token issues. Walk through your diagnosis.

**Answer:**
> "First question: where are refresh tokens stored? If localStorage, an XSS attack could have stolen
> them and they've been used by the attacker — triggering server-side rotation invalidation of the
> old token. If httpOnly cookie, an expired or deleted cookie is more likely.
>
> Second: does the auth server implement refresh token rotation? With rotation, each use of a
> refresh token invalidates it and issues a new one. If two tabs call the refresh endpoint
> simultaneously — race condition — the second call will get a 401 because the first call already
> rotated the token. I've fixed this with a singleton promise: the first tab to need a refresh
> kicks off the call and every other caller awaits the same promise instead of firing their own."

**Production fix for race condition:**

```typescript
// tokenManager.ts
let refreshPromise: Promise<string> | null = null;

export async function getValidAccessToken(): Promise<string> {
  if (isAccessTokenValid()) return getAccessToken();

  if (!refreshPromise) {
    refreshPromise = refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
  }

  return refreshPromise;
}
```

---

### Q3: A pen tester finds a CSRF vulnerability on your logout endpoint. How do you respond?

**Answer:**
> "First, assess impact. Logout CSRF is annoying but usually low severity — the attacker logs the
> user out, not in. Compare that to a CSRF on a fund transfer endpoint — much worse.
>
> For the fix: if we're a pure SPA making JSON API calls with fetch, we likely don't need a CSRF
> token at all. Browsers send cookies automatically on form submissions and img src requests, but a
> cross-site page cannot set Content-Type: application/json and send a custom Authorization header
> — that requires CORS preflight, which the server can restrict by origin. The combination of
> SameSite=Strict cookies and custom headers (like X-Requested-With or Authorization: Bearer)
> eliminates CSRF without a token.
>
> However, if the endpoint accepts form-encoded data or the cookie is SameSite=None (required for
> embedded iframes), a CSRF token or double-submit cookie pattern is warranted."

---

### Q4: You're implementing a PrivateRoute in a Next.js app. How do you prevent flash of unauthenticated content?

**Answer:**
> "Client-side PrivateRoute has an inherent flash problem — the component renders before the auth
> check completes, and if you're not careful users see the protected page for one render cycle.
> Three layers of defense:
>
> 1. Server-side: Next.js middleware (runs on the edge, before the page is sent) redirects
>    unauthenticated requests. This is the cleanest — the browser never receives the protected HTML.
> 2. If using getServerSideProps: check session there and redirect server-side.
> 3. Client-side fallback: while auth state is loading, render a skeleton or null, not the protected
>    content. Only render children when auth is confirmed."

**Next.js middleware pattern:**

```typescript
// middleware.ts (runs on Edge Runtime — no flash possible)
import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

export async function middleware(req: NextRequest) {
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  const isAuth = !!token;
  const isAuthPage = req.nextUrl.pathname.startsWith('/login');

  if (!isAuth && !isAuthPage) {
    return NextResponse.redirect(new URL('/login', req.url));
  }
  return NextResponse.next();
}

export const config = { matcher: ['/dashboard/:path*', '/settings/:path*'] };
```

---

### Q5: How would you implement role-based access control in a React app?

**Answer:**
> "RBAC in React is always UI enforcement, not security enforcement. Real authorization happens
> server-side — the API must validate the user's role on every request. React RBAC just improves UX
> by hiding buttons or routes the user can't use anyway.
>
> For the pattern: decode the JWT or fetch user roles from the auth context, then use a hook or
> component gate. I usually store roles in the auth context from the OIDC id_token claims, and
> expose a usePermission hook. For routes, Next.js middleware reads the JWT claims and returns 403
> before the page loads."

**RBAC hook:**

```typescript
// usePermission.ts
import { useAuth } from './AuthContext';

type Permission = 'admin:write' | 'reports:read' | 'users:delete';

export function usePermission(permission: Permission): boolean {
  const { user } = useAuth();
  if (!user?.roles) return false;
  // Never trust client-only — this is UX gating, API still enforces
  return user.roles.includes(permission) || user.roles.includes('admin');
}

// Usage
const canDelete = usePermission('users:delete');
return canDelete ? <DeleteButton /> : null;
```

---

### Q6: Walk me through setting up Content Security Policy for a React app.

**Answer:**
> "CSP is an HTTP response header that tells the browser which sources of content are trusted.
> It's the last line of defense against XSS — even if an attacker injects a script, CSP can
> prevent it from executing.
>
> The hardest part with React is inline scripts. Create React App and Vite can inject inline
> script chunks that violate a strict CSP. Two solutions: use nonces (server generates a random
> value per request, injects it into the script tag and the CSP header), or use hash-based CSP
> (pre-compute SHA256 of each inline script).
>
> I usually start with report-only mode in staging: `Content-Security-Policy-Report-Only` with
> a report-uri pointing to a collector. This logs violations without breaking anything. Once I've
> iterated to zero violations, I switch to enforcement mode."

**Next.js CSP header config:**

```typescript
// next.config.ts
const nonce = Buffer.from(crypto.randomUUID()).toString('base64');

const cspHeader = `
  default-src 'self';
  script-src 'self' 'nonce-${nonce}' 'strict-dynamic';
  style-src 'self' 'nonce-${nonce}';
  img-src 'self' blob: data: https:;
  font-src 'self';
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none';
  upgrade-insecure-requests;
`.replace(/\s{2,}/g, ' ').trim();
```

---

### Q7: An npm audit shows a high-severity vulnerability in a transitive dependency. What's your process?

**Answer:**
> "First, determine if the vulnerability is actually exploitable in your context. Many audit hits are
> theoretical — a regex DoS in a package you only use at build time, for example, poses zero runtime
> risk. Read the CVE, understand the attack vector.
>
> If exploitable: check if there's a patched version. Try npm update or Dependabot. If the direct
> dependency hasn't updated to use the patched transitive dep, check if you can use npm overrides
> (package.json overrides field in npm 8.3+) to force the patched version.
>
> If no patch exists: weigh the risk. Can you replace the dependency? Is there a workaround?
> Do you need to take the feature offline temporarily?
>
> The supply chain attack angle is separate — for that I care about package integrity (lockfile
> committed, npm ci in CI, not npm install), Sigstore/provenance attestations, and internal
> artifact mirrors so a package can't be yanked or poisoned post-install."

---

### Q8: How do you protect against clickjacking in a React app?

**Answer:**
> "Clickjacking is when an attacker embeds your page in a transparent iframe and tricks users into
> clicking UI elements. Two defenses:
>
> 1. X-Frame-Options header (legacy): `DENY` or `SAMEORIGIN`. Simple, widely supported.
> 2. CSP frame-ancestors (modern, preferred): `Content-Security-Policy: frame-ancestors 'none'`
>    or `frame-ancestors 'self' https://trusted-embed.com`. More flexible — supports wildcards and
>    multiple origins. Overrides X-Frame-Options in browsers that support both.
>
> I set both in production for defense in depth. The React app itself doesn't need special code —
> this is purely a server/CDN header configuration."

---

## 4. Advanced Scenario Q&As

### AQ1: You're migrating from implicit OAuth flow to authorization code + PKCE. What breaks and how do you handle the migration?

**Answer:**
> "Implicit flow is deprecated in OAuth 2.1 because the access token is returned in the URL fragment,
> visible in browser history, referrer headers, and server logs. PKCE solves this — the token is
> returned via a back-channel POST exchange, not in the URL.
>
> Migration steps:
> 1. Register a new redirect URI on the auth server for the PKCE flow if needed.
> 2. Update the authorization request: add code_challenge and code_challenge_method=S256.
> 3. Handle the callback: extract the authorization code from the query string (not fragment),
>    generate the token exchange request with code_verifier.
> 4. If the auth server doesn't support PKCE yet — escalate that first. That's the blocker.
> 5. Session continuity: users in the middle of implicit flow sessions will need to re-authenticate.
>    Plan a maintenance window or accept one-time logouts.
>
> The hard part is usually the auth server, not the client. I've seen orgs running Okta/Auth0 where
> the PKCE flag was disabled by default on the application config — that was a 5-minute fix once
> we found it."

---

### AQ2: Explain refresh token rotation and how to handle the reuse detection edge case.

**Answer:**
> "Refresh token rotation means each refresh token use produces a new refresh token AND a new access
> token. The old refresh token is immediately invalidated. This limits the damage if a refresh token
> is stolen — the attacker gets one use before detection.
>
> Reuse detection: if the server sees a refresh token being used that's already been rotated
> (i.e., the token is in the 'used tokens' log), it treats this as a token theft signal and
> immediately invalidates the entire token family — all refresh tokens for that session.
>
> The edge case I've hit in production: user has two tabs open. Both detect the access token is
> expiring. Both fire the refresh endpoint simultaneously. One succeeds, one fails with 'token
> already used.' That triggers the server's reuse detection, logs out the user, and the team gets a
> 3am alert about 'suspicious activity' that was just a multi-tab user.
>
> Fix: the singleton refresh promise pattern I mentioned earlier. Only one refresh call in-flight
> per client at any time. The second tab awaits the first tab's promise result."

---

### AQ3: How would you design a secure logout that covers all attack vectors?

**Answer:**
> "Complete logout has multiple layers. Incomplete logout is one of the most common auth vulnerabilities.
>
> Client-side:
> - Clear in-memory token state (React context, Zustand store, etc.)
> - Clear any sessionStorage entries
> - If using service workers: send a message to clear cached auth state
>
> Server-side:
> - Revoke the refresh token (add to blocklist or delete from store)
> - If using session cookies: invalidate the session in the session store
> - Call the auth server's /logout endpoint if using OIDC (this clears the SSO session — without
>   this, the user can get a new token immediately via SSO without re-entering credentials)
>
> Cookie:
> - Server sets Set-Cookie with an expired date to clear the httpOnly cookie (client JS can't)
>
> The OIDC front-channel and back-channel logout specs handle propagating logout across multiple
> relying parties — important for SSO environments where one login covers multiple apps."

---

### AQ4: You discover that a third-party script (analytics, chat widget) on your site is loading over HTTP. What's the risk and how do you fix it?

**Answer:**
> "Mixed content — an HTTPS page loading HTTP subresources. Browsers block active mixed content
> (scripts, iframes, XHR) by default in modern browsers. Passive mixed content (images, audio)
> gets a warning but loads.
>
> If the script somehow loads (older browser, misconfigured browser policy), it can be
> man-in-the-middled — an attacker on the network path can replace the script content with anything,
> including a keylogger. This completely defeats HTTPS.
>
> Fixes in order of preference:
> 1. Tell the vendor to serve over HTTPS. Most have for years now.
> 2. If the vendor is still HTTP-only in 2024: replace the vendor.
> 3. Self-host the script — download it, serve it from your own origin over HTTPS.
> 4. Use `upgrade-insecure-requests` in CSP — this tells the browser to automatically upgrade
>    HTTP subresource requests to HTTPS. Won't work if the server doesn't support HTTPS at all.
>
> Add `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload` to prevent
> initial HTTP connections for returning users, and submit to the HSTS preload list for new users."

---

## 5. Senior Trap Questions

### Trap 1: "We store JWTs in localStorage — it's simpler and it works fine, right?"

**The trap:** localStorage is accessible by any JavaScript on the page. If there is ever an XSS
vulnerability — even in a third-party script you load — the attacker can read `localStorage.getItem('token')`
and exfiltrate the token silently. The user has no idea.

**Correct answer:**
> "localStorage is the wrong place for anything sensitive. All JavaScript on the page can read it —
> your code, analytics scripts, chat widgets, everything. One XSS vulnerability, anywhere in your
> dependency tree, and every token in localStorage is compromised for every user who loaded
> the infected page.
>
> The right approach depends on the token type. Access tokens should live in memory — a module-level
> variable or React state. They're short-lived (5-15 minutes) so loss on tab close is acceptable.
> Refresh tokens should be in httpOnly, SameSite=Strict cookies. HttpOnly means JavaScript literally
> cannot read it — not even your own code. XSS can't steal what it can't see. SameSite=Strict
> prevents it from being sent cross-site, killing CSRF."

---

### Trap 2: "React sanitizes all user input automatically, so we don't need to worry about XSS."

**The trap:** React sanitizes JSX expression values rendered into the virtual DOM, but this protection
has explicit escape hatches, and it says nothing about URL-based XSS or event handler injection.

**Correct answer:**
> "React escapes string values in JSX — that's true and it's a great baseline. But there are at
> least three ways around it:
>
> 1. `dangerouslySetInnerHTML={{ __html: userContent }}` — React literally tells you it's dangerous.
>    Any HTML in userContent, including `<script>` tags or onerror attributes, goes straight to the DOM.
> 2. `href={userUrl}` — React does NOT sanitize href values. A user can set href to
>    `javascript:maliciousCode()` and clicking the link executes it. Always validate that href starts
>    with http or https.
> 3. Server-side rendering: if you inject user data into the initial HTML string before React
>    hydrates, the protection hasn't kicked in yet.
>
> For dangerouslySetInnerHTML, DOMPurify is the standard solution:
> `{ __html: DOMPurify.sanitize(userContent) }`"

---

### Trap 3: "Our app is on HTTPS so we're secure from XSS and CSRF attacks."

**The trap:** HTTPS encrypts data in transit. It says nothing about what happens on the endpoints.
XSS and CSRF operate at the application layer, completely orthogonal to transport encryption.

**Correct answer:**
> "HTTPS solves transport-layer attacks: eavesdropping, man-in-the-middle, tampered responses.
> It does nothing for application-layer vulnerabilities.
>
> XSS happens after the content reaches the browser — HTTPS has delivered the payload, its job is
> done. Once the attacker's script is running in the browser, it's running in the same origin as your
> app, over the same HTTPS connection.
>
> CSRF happens because the browser automatically attaches cookies to requests — HTTPS cookies
> included. An attacker's site at http://evil.com can trigger a form submission to https://yourapp.com
> and the browser sends the victim's auth cookie along with it.
>
> HTTPS is table stakes. It's not a security posture."

---

### Trap 4: "We put our API keys in .env files with REACT_APP_ prefix — they're environment variables, not in source code."

**The trap:** Vite's VITE_ prefix and Create React App's REACT_APP_ prefix are both compile-time
replacements. The build process inlines the values directly into the JavaScript bundle. They are
not server environment variables — they are string literals in your shipped code.

**Correct answer:**
> "REACT_APP_ and VITE_ variables are build-time substitutions, not runtime server secrets.
> During `npm run build`, every reference to `process.env.REACT_APP_API_KEY` or `import.meta.env.VITE_API_KEY`
> is replaced with the literal string value. That string ships in your JavaScript bundle to every user.
>
> `cat dist/assets/index-abc123.js | grep -o '\"[A-Za-z0-9_\-]{20,}\"'` — you'd find it in minutes.
>
> What CAN go in these variables: public configuration that's safe to expose — your public API URL,
> feature flags, analytics property IDs (already in the JS anyway), your OAuth client_id (public by
> design in OAuth 2.0).
>
> What CANNOT: API secret keys, private OAuth client_secret, database credentials, signing secrets.
> Those live on the server, in a secrets manager, accessed only by your BFF/API layer."

---

### Trap 5: "We use OAuth implicit flow for our SPA — it's simpler since we don't need a backend."

**The trap:** Implicit flow is deprecated in OAuth 2.1 and considered insecure. The access token
appears directly in the URL fragment, leaking through browser history, referrer headers, and logs.

**Correct answer:**
> "Implicit flow was designed in 2012 when browsers couldn't do PKCE. It's been deprecated in
> RFC 9700 (OAuth 2.1) precisely because the access token is returned in the URL fragment — visible
> in browser history, in server access logs if the URL is shared, and extractable from window.location
> by any JavaScript on the page.
>
> Authorization code + PKCE is the correct flow for SPAs today, and it doesn't require a backend.
> PKCE (Proof Key for Code Exchange) replaces the client_secret with a per-request code_verifier/
> code_challenge pair. The SPA generates a random code_verifier, hashes it to make the code_challenge,
> sends the hash with the auth request, then proves ownership by sending the original code_verifier
> in the token exchange. No secret, no backend needed, no token in the URL.
>
> Auth0, Okta, Cognito, and every major provider have supported PKCE for years. There's no reason
> to use implicit flow in a new SPA."

---

### Trap 6: "We validate user roles on the frontend before showing admin pages — that's our authorization."

**The trap:** Client-side authorization is UI convenience, not security. Any user can open DevTools,
modify JavaScript, or call the API directly.

**Correct answer:**
> "Frontend RBAC is UX, not security. A determined user can open DevTools, set a breakpoint, modify
> the `isAdmin` variable to `true`, or just call the admin API endpoint directly with curl. Nothing
> in the browser is tamper-proof.
>
> Real authorization lives on the server, enforced on every single API request. The server validates
> the JWT, extracts the roles/claims from it, and checks that this specific operation is permitted
> for this specific role — before doing anything.
>
> Frontend RBAC serves one purpose: hide buttons and routes that the user isn't allowed to use anyway,
> improving UX. Think of it as progressive disclosure, not access control. The actual enforcement is
> in your API middleware. I always make this explicit in code reviews: 'This is UX gating, not
> authorization — server must enforce this too.'"

---

## 6. Production Code Examples

### Example 1: Secure OAuth PKCE Implementation

```typescript
// pkce.ts — PKCE helper utilities
function generateCodeVerifier(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

export async function initiateLogin(): Promise<void> {
  const verifier = generateCodeVerifier();
  const challenge = await generateCodeChallenge(verifier);
  sessionStorage.setItem('pkce_verifier', verifier); // OK: same tab only, short-lived

  const params = new URLSearchParams({
    response_type: 'code',
    client_id: import.meta.env.VITE_OAUTH_CLIENT_ID, // public — this is fine
    redirect_uri: `${window.location.origin}/callback`,
    scope: 'openid profile email',
    code_challenge: challenge,
    code_challenge_method: 'S256',
    state: crypto.randomUUID(), // CSRF protection for the OAuth flow itself
  });
  window.location.href = `${AUTH_SERVER}/authorize?${params}`;
}
```

---

### Example 2: Token Manager with Silent Refresh

```typescript
// tokenManager.ts
interface TokenState {
  accessToken: string | null;
  expiresAt: number | null;
}

let state: TokenState = { accessToken: null, expiresAt: null };
let refreshPromise: Promise<string> | null = null;

export function setAccessToken(token: string, expiresInSeconds: number): void {
  state = {
    accessToken: token,
    expiresAt: Date.now() + (expiresInSeconds - 30) * 1000, // 30s buffer
  };
}

async function doRefresh(): Promise<string> {
  const res = await fetch('/api/auth/refresh', {
    method: 'POST',
    credentials: 'include', // sends httpOnly refresh token cookie
  });
  if (!res.ok) {
    state = { accessToken: null, expiresAt: null };
    throw new Error('Session expired');
  }
  const { accessToken, expiresIn } = await res.json();
  setAccessToken(accessToken, expiresIn);
  return accessToken;
}

export async function getToken(): Promise<string> {
  if (state.accessToken && state.expiresAt && Date.now() < state.expiresAt) {
    return state.accessToken;
  }
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => { refreshPromise = null; });
  }
  return refreshPromise;
}
```

---

### Example 3: Secure AuthContext with Loading State (no flash)

```typescript
// AuthContext.tsx
interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true); // starts true — prevents flash

  useEffect(() => {
    // Try silent token refresh on mount
    getToken()
      .then(() => fetchCurrentUser().then(setUser))
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  const logout = async () => {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    state = { accessToken: null, expiresAt: null }; // clear in-memory token
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
```

---

### Example 4: PrivateRoute with Role Check

```typescript
// PrivateRoute.tsx
interface PrivateRouteProps {
  children: ReactNode;
  requiredRole?: string;
}

export function PrivateRoute({ children, requiredRole }: PrivateRouteProps) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) return <PageSkeleton />; // never flash protected content

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && !user.roles?.includes(requiredRole)) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
}

// Usage in router
<Route path="/admin/*" element={
  <PrivateRoute requiredRole="admin">
    <AdminLayout />
  </PrivateRoute>
} />
```

---

### Example 5: DOMPurify for Rich Text Rendering

```typescript
// SafeHtml.tsx — use only for content that truly needs HTML rendering
import DOMPurify from 'dompurify';

interface SafeHtmlProps {
  html: string;
  className?: string;
}

const PURIFY_CONFIG: DOMPurify.Config = {
  ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'a', 'code'],
  ALLOWED_ATTR: ['href', 'target', 'rel'],
  ALLOW_DATA_ATTR: false,
};

// Add hook: force noopener on all external links
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('rel', 'noopener noreferrer');
    if (!node.getAttribute('href')?.startsWith('/')) {
      node.setAttribute('target', '_blank');
    }
  }
});

export function SafeHtml({ html, className }: SafeHtmlProps) {
  const clean = DOMPurify.sanitize(html, PURIFY_CONFIG);
  return <div className={className} dangerouslySetInnerHTML={{ __html: clean }} />;
}
```

---

### Example 6: Href XSS Prevention

```typescript
// safeHref.ts — React doesn't sanitize href
const SAFE_PROTOCOLS = new Set(['http:', 'https:', 'mailto:', 'tel:']);

export function isSafeHref(href: string): boolean {
  try {
    const url = new URL(href, window.location.origin);
    return SAFE_PROTOCOLS.has(url.protocol);
  } catch {
    return href.startsWith('/'); // relative paths are safe
  }
}

// Component usage
export function SafeLink({ href, children, ...props }: AnchorHTMLAttributes<HTMLAnchorElement>) {
  if (!isSafeHref(href ?? '')) {
    console.warn('SafeLink: blocked unsafe href:', href);
    return <span {...props}>{children}</span>; // render as non-link
  }
  return <a href={href} rel="noopener noreferrer" {...props}>{children}</a>;
}
```

---

### Example 7: NextAuth.js Session with JWT Strategy

```typescript
// app/api/auth/[...nextauth]/route.ts
import NextAuth, { NextAuthOptions } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,     // server env — truly private
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!, // server env — truly private
    }),
  ],
  session: { strategy: 'jwt', maxAge: 30 * 24 * 60 * 60 }, // 30 days
  callbacks: {
    async jwt({ token, user, account }) {
      if (account && user) {
        token.accessToken = account.access_token;
        token.roles = await fetchUserRoles(user.email!); // enrich from your DB
      }
      return token;
    },
    async session({ session, token }) {
      session.user.roles = token.roles as string[];
      // Never leak accessToken to client session — keep server-side only
      return session;
    },
  },
  cookies: {
    sessionToken: {
      options: {
        httpOnly: true,
        sameSite: 'lax', // 'strict' breaks OAuth redirects — 'lax' is the right trade-off
        secure: process.env.NODE_ENV === 'production',
      },
    },
  },
};

export const { GET, POST } = NextAuth(authOptions);
```

---

## 7. Interview Cheat Sheet

### XSS Quick Reference

| Type | Source | Sink | React Protected? |
|------|--------|------|-----------------|
| Reflected | URL params | Server echoes into HTML | Yes (JSX escaping) |
| Stored | DB via user input | Page render | Yes (JSX escaping) |
| DOM-based | location.hash, URL | innerHTML, eval | NO — client code |
| dangerouslySetInnerHTML | Any | __html prop | NO — explicit bypass |
| javascript: URLs | user input | href attribute | NO — React allows any href |

### Token Storage Comparison

| Storage | XSS Accessible | CSRF Vulnerable | Persists Across Tabs | Verdict |
|---------|---------------|-----------------|---------------------|---------|
| localStorage | YES | No | Yes | Avoid for sensitive tokens |
| sessionStorage | YES | No | No | Avoid for sensitive tokens |
| Memory (JS var) | NO* | No | No | Best for access tokens |
| httpOnly Cookie | NO | Yes (mitigated by SameSite) | Yes | Best for refresh tokens |

*Only if there is NO XSS — in-memory is safe from direct theft but script execution still exploits the user's session.

### OAuth 2.0 Flow Selection

| Use Case | Recommended Flow | Why |
|----------|-----------------|-----|
| SPA (no backend) | Authorization Code + PKCE | No secret needed, no token in URL |
| Web app (server) | Authorization Code | Server holds client_secret securely |
| Machine-to-machine | Client Credentials | No user involved |
| Implicit | DEPRECATED | Token in URL fragment, history/logs exposure |
| Resource Owner Password | AVOID | App sees user's password, breaks OAuth trust model |

### CSP Directives Quick Reference

| Directive | What It Controls |
|-----------|-----------------|
| `default-src` | Fallback for all fetch directives |
| `script-src` | JavaScript sources (nonce or hash for inline) |
| `style-src` | CSS sources |
| `img-src` | Image sources |
| `connect-src` | fetch, XHR, WebSocket endpoints |
| `frame-ancestors` | Who can embed this page (replaces X-Frame-Options) |
| `object-src 'none'` | Block Flash, Java plugins — always set this |
| `base-uri 'self'` | Prevent base tag injection attacks |

### Critical Security Headers

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; object-src 'none'; base-uri 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

### When SPA Doesn't Need CSRF Tokens

A SPA that:
1. Sends all requests with `Authorization: Bearer <token>` header (custom header = CORS preflight) AND
2. Accepts only `Content-Type: application/json` AND
3. Uses CORS with `Access-Control-Allow-Origin` restricted to your origin

...is naturally CSRF-immune. Browsers require CORS preflight for custom headers and non-simple
content types, and cross-site requests cannot pass CORS preflight.

**Still need CSRF consideration when:** cookies are the auth mechanism AND endpoint accepts
form-encoded data OR SameSite=None.

### Dependency Security Checklist

- [ ] `package-lock.json` committed and `npm ci` in CI (not `npm install`)
- [ ] Dependabot or Renovate configured for automatic PRs
- [ ] `npm audit` in CI pipeline, fail on high+critical
- [ ] Review SBOM (Software Bill of Materials) for regulated industries
- [ ] Pin Docker base images to digests (`@sha256:...`)
- [ ] Internal artifact mirror (Artifactory/Nexus) for airgapped or high-security environments
- [ ] Verify published package provenance via Sigstore/npm attestations (npm 9.5+)

### Auth Library Quick Comparison

| Library | Good For | Token Storage | Trade-off |
|---------|----------|--------------|-----------|
| NextAuth / Auth.js | Next.js full-stack | httpOnly cookie (default) | Tied to Next.js ecosystem |
| Clerk | Quick SaaS auth | Managed (their infra) | Vendor dependency, cost |
| Auth0 SDK | Enterprise OAuth/OIDC | Configurable | Vendor dependency |
| Supabase Auth | Supabase projects | Configurable | Tied to Supabase |
| DIY + jose library | Full control | Your choice | You own the bugs |

### The Three Questions for Every Security Decision

1. **What's the threat model?** Who's the attacker? (Outsider, XSS, MITM, malicious employee?)
2. **What's the blast radius?** If this is exploited, what's the worst outcome?
3. **What's the trade-off?** Does this security measure hurt usability / DX in a way that will
   cause engineers to work around it?

### Secrets Scope — What Can Be Public

| Item | Public? | Why |
|------|---------|-----|
| VITE_/REACT_APP_ env vars | YES | Bundled into client JS |
| OAuth client_id | YES | Required by OAuth 2.0 spec for public clients |
| OAuth client_secret | NO | Server-side only |
| Public API URLs | YES | Visible in Network tab anyway |
| API signing secrets | NO | Server-side only |
| JWT secret (HS256) | NO | Server-side only |
| JWT public key (RS256 verify) | YES | That's the point |
| Database connection strings | NO | Server-side only, never in frontend |
| Third-party API secret keys | NO | BFF pattern — server proxies the call |

---

*Last updated: 2026-08-21 | Covers React 18/19, Next.js 14/15, OAuth 2.1, PKCE*
