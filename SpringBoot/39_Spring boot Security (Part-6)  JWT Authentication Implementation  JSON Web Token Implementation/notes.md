# JWT Authentication — Visual Guide for New Learners

---

## The Big Picture: What Are We Building?

```
Without JWT (session-based):
  User logs in → Server creates session → Server REMEMBERS you forever
  Problem: 10M users = 10M sessions in memory 😩

With JWT (stateless):
  User logs in → Server gives you a TOKEN → YOU carry it everywhere
  Server never stores anything — it just checks your token each time ✅
```

---

## JWT Token Structure (3 Parts, Separated by Dots)

```
eyJhbGciOiJIUzI1NiJ9  .  eyJzdWIiOiJ1c2VyMSJ9  .  SflKxwRJSMeKKF2QT4fwp
─────────────────────    ──────────────────────    ──────────────────────
     HEADER                    PAYLOAD                   SIGNATURE
  (what algorithm?)         (who are you?)           (tamper-proof seal)
  { algo: "HS256" }     { user: "sj1", role: "USER",  HMAC(header+payload,
                           expiry: "15min" }            secretKey)
```

---

## How Part3 (Signature) Is Created

```
HMAC( base64(header) + "." + base64(payload),  secretKey )
      ─────────────────────────────────────    ──────────
              the actual content               your server's
              of the token                     private secret

       gives: "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
                        │
                        │  this result IS part3 — attached to the token
                        ▼
eyJhbGci...  .  eyJzdWIi...  .  SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
───────────     ───────────     ──────────────────────────────────────────────
  part1           part2                         part3
  (header)       (payload)               (the HMAC output, base64 encoded)
```

---

## What Is HMAC?

**Full form: Hash-based Message Authentication Code**

It answers one question: *"Was this message created by someone who knows the secret key, and was it unchanged?"*

### Why It's Useful for JWT

```
Property 1 — DETERMINISTIC
  Same message + same key → always the same output
  Server can re-run it anytime to verify

Property 2 — ONE-WAY
  Cannot reverse the hash to get the original message or key
  Attacker seeing the token cannot extract the secretKey

Property 3 — AVALANCHE EFFECT
  Change ONE character in payload → completely different hash
  "role:USER" vs "role:ADMIN" → totally different signature

Property 4 — KEYED
  Unlike plain SHA-256 (anyone can hash anything),
  HMAC requires knowing the secretKey to produce a valid hash
  → only your server can create valid signatures
```

### HMAC vs Plain Hash (SHA-256)

```
SHA-256(message)         → anyone can compute it, no secret needed
                            NOT safe for JWT — attacker can forge signatures

HMAC(message, secretKey) → only someone with secretKey can compute it
                            SAFE for JWT — attacker can't forge signatures
```

---

## Who Verifies the Token? (Spring Boot App vs Auth Server)

```
THIS TUTORIAL — Spring Boot app does everything:
┌─────────────────────────────────────────────────────┐
│              YOUR SPRING BOOT APP                    │
│                                                      │
│  ┌──────────────────┐    ┌──────────────────────┐   │
│  │  Token CREATION  │    │  Token VALIDATION    │   │
│  │  (login time)    │    │  (every request)     │   │
│  │                  │    │                      │   │
│  │  HMAC(p1+p2,key) │    │  HMAC(p1+p2,key)     │   │
│  │  → signs token   │    │  → verify match      │   │
│  └──────────────────┘    └──────────────────────┘   │
│                                                      │
│  secretKey lives here (application.properties)       │
└─────────────────────────────────────────────────────┘
Same app, same secretKey — used for both signing and verifying.

ENTERPRISE — dedicated auth server (Keycloak / Okta / Google):
┌──────────────────────┐        ┌──────────────────────┐
│   Auth Server        │        │  Your Spring Boot App │
│   (Keycloak/Okta)    │        │  (business logic)     │
│                      │        │                       │
│  Handles login       │        │  Verifies the token   │
│  Signs token         │        │  Rejects invalid ones │
│  (has secretKey)     │        │  Has no secretKey     │
│  Issues access +     │        │  (uses public key     │
│  refresh tokens      │        │   for RS256 instead)  │
└──────────────────────┘        └──────────────────────┘
  → Use this when multiple apps share one login (SSO)
```

---

## Token Verification: Every Single Request

```
TOKEN ARRIVES:
  eyJhbGci...  .  eyJzdWIi...  .  SflKxwRJSMeKKF2QT...
     part1           part2               part3
                                    (from the token)

SERVER RE-CALCULATES (ignores part3, computes fresh):
  HMAC( part1 + "." + part2,  secretKey )
       ─────────────────────  ──────────
       taken from token       server knows this
       exactly as-is

  result → "SflKxwRJSMeKKF2QT..."
                │
                ▼
  Does result == part3 ?
  ─────────────────────
  YES → token untampered → proceed ✅
  NO  → someone changed part1 or part2 → reject ❌
```

The server never "decodes" part3 — it recalculates fresh and only uses part3 as the thing to match against. Since HMAC is deterministic (same input + same key = always same output), a genuine token always matches.

---

**Why the signature matters:**
- Someone tries to change `role: "USER"` → `role: "ADMIN"`
- Server re-runs HMAC(modified_payload, secretKey) → different hash
- Doesn't match part3 → REJECTED ✅
- Nobody can fake a valid part3 without knowing the secretKey

---

## 4 Steps We're Implementing

```
STEP 1: User Registration
  POST /api/user-register
  { username: "sj1", password: "123", role: "user" }
  → Password gets HASHED → saved to DB
  → DB: { id: 1, username: "sj1", password: "$2a$...", role: "user" }

STEP 2: Token Generation (Login)
  POST /generate-token
  { username: "sj1", password: "123" }
  → Validate against DB → if match → return JWT token
  ← Header: Authorization: Bearer eyJhbGci...

STEP 3: Token Validation (Access Protected Resource)
  GET /api/users
  Header: Authorization: Bearer eyJhbGci...
  → Validate token → if valid → return data
  → If invalid/expired → 403 Forbidden

STEP 4: Refresh Token (Get New Token Without Re-Login)
  POST /refresh-token   (refresh token sent automatically via cookie)
  → Validate refresh token → generate new access token
  ← Header: Authorization: Bearer eyJhbGci... (new token)
```

---

## Spring Security Filter Chain (The Highway)

Think of the filter chain as a highway with toll booths. Every request passes through them in order.

```
HTTP Request
     │
     ▼
┌──────────────────────────────────────────────────────┐
│              FILTER CHAIN (highway)                   │
│                                                       │
│  [SecurityContextHolder Filter]                       │
│           ↓                                           │
│  [JWT Authentication Filter]  ← WE ADD THIS (login)  │
│           ↓                                           │
│  [Username/Password Filter]   (default Spring)        │
│           ↓                                           │
│  [JWT Validation Filter]      ← WE ADD THIS (access)  │
│           ↓                                           │
│  [Authorization Filter]       (default Spring)        │
│           ↓                                           │
└──────────────────────────────────────────────────────┘
     │
     ▼
  Controller (business logic)
```

**Key rule:** Each filter decides — handle this request OR pass it to the next filter.

---

## How Spring Security Routes Requests: The Provider System

```
Filter creates Authentication Object
         │
         ▼
  Authentication Manager (ProviderManager)
         │
         │  iterates over list of providers...
         │
         ├──► DAO Authentication Provider
         │         supports(UsernamePasswordToken)? → YES
         │         → validates username+password against DB
         │
         └──► JWT Authentication Provider  ← WE ADD THIS
                   supports(JwtAuthToken)? → YES
                   → validates JWT token signature + expiry
```

**Why this matters:** Spring never hardcodes which provider handles what. It asks each provider "can you handle this?" — only the matching one runs.

---

## STEP 2 Deep Dive: Token Generation Flow

```
User calls POST /generate-token  { username:"sj1", password:"123" }
                │
                ▼
  ┌─────────────────────────────┐
  │  JwtAuthenticationFilter    │  ← our custom filter
  │                             │
  │  1. Is path "/generate-token"? → YES, proceed
  │  2. Read LoginRequest (username, password)
  │  3. Create UsernamePasswordAuthToken(sj1, 123)
  │  4. Call authManager.authenticate(token)
  └──────────────┬──────────────┘
                 │
                 ▼
  ┌─────────────────────────────┐
  │  DAO Authentication Provider│
  │                             │
  │  1. Hash password "123"     │
  │  2. Load user from DB by    │
  │     username "sj1"          │
  │  3. Compare hashes → MATCH  │
  │  4. Return authenticated=true│
  └──────────────┬──────────────┘
                 │
                 ▼ (back to our filter)
  ┌─────────────────────────────┐
  │  JwtAuthenticationFilter    │
  │                             │
  │  5. Call jwtUtil.generateToken("sj1", 15min)
  │  6. Put in response header: │
  │     Authorization: Bearer <token>
  │  7. STOP — don't go to controller
  └─────────────────────────────┘
```

---

## STEP 3 Deep Dive: Token Validation Flow

```
User calls GET /api/users
Header: Authorization: Bearer eyJhbGci...
                │
                ▼
  ┌─────────────────────────────┐
  │  JwtValidationFilter        │  ← our custom filter
  │                             │
  │  1. Extract token from header
  │  2. Create JwtAuthToken(token)  ← CUSTOM auth object
  │  3. Call authManager.authenticate(jwtToken)
  └──────────────┬──────────────┘
                 │
                 ▼
  ┌─────────────────────────────┐
  │  JWT Authentication Provider│  ← our custom provider
  │                             │
  │  1. supports(JwtAuthToken)? → YES
  │  2. Parse token → extract username
  │  3. Check expiry → still valid?
  │  4. Load user from DB by username
  │  5. Return authenticated=true + user details
  └──────────────┬──────────────┘
                 │
                 ▼ (back to our filter)
  ┌─────────────────────────────┐
  │  JwtValidationFilter        │
  │                             │
  │  6. Store in SecurityContextHolder
  │  7. Call filterChain.doFilter() → CONTINUE to controller
  └─────────────────────────────┘
                 │
                 ▼
         Controller runs → returns data ✅
```

**If token is invalid:**
```
JWT Provider throws BadCredentialsException
→ filterChain.doFilter() never called
→ Controller never reached
→ 403 Forbidden returned
```

---

## What We Write vs What Spring Provides

```
┌──────────────────────────────────────────────────────┐
│  WE WRITE (pink boxes in the video)                   │
├──────────────────────────────────────────────────────┤
│  JwtAuthenticationFilter   — handles /generate-token │
│  JwtValidationFilter       — validates token on every │
│                               protected request       │
│  JwtAuthToken              — custom auth object       │
│  JwtAuthenticationProvider — validates JWT tokens     │
│  JwtUtil                   — generate + parse tokens  │
│  SecurityConfig            — wires everything together│
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  SPRING PROVIDES (we just configure)                  │
├──────────────────────────────────────────────────────┤
│  FilterChain               — the highway              │
│  ProviderManager           — iterates providers       │
│  DaoAuthenticationProvider — DB username/password check│
│  SecurityContextHolder     — stores current user      │
│  AuthorizationFilter       — role-based access check  │
└──────────────────────────────────────────────────────┘
```

---

## JwtUtil — The Token Kitchen

```java
// Generating a token
String token = jwtUtil.generateToken("sj1", 15);
//  └── creates:  header.payload.signature
//  payload = { sub: "sj1", iat: now, exp: now+15min }
//  signed with HMAC-SHA256 using your secretKey

// Validating + extracting username
String username = jwtUtil.validateAndExtractUsername(token);
//  └── parses token using same secretKey
//  └── if signature OK and not expired → returns "sj1"
//  └── if tampered/expired → throws exception
```

**Secret Key rule:** Same key signs and verifies (HMAC = symmetric). Never put it in code — store in `application.properties` or environment variable.

---

## Access Token vs Refresh Token

```
                    SHORT-LIVED           LONG-LIVED
                  (Access Token)        (Refresh Token)
                  ─────────────         ──────────────
  Expiry            15 minutes            7 days
  Stored in         Auth header           HTTP-only cookie
  Used for          API requests          Get new access token
  If leaked         Risk: 15 min only     Risk: higher — secured in cookie
  
  Why cookie for refresh?
  ─ HTTP-only: JavaScript can't read it (prevents XSS theft)
  ─ Secure: only sent over HTTPS
  ─ Path=/refresh-token: browser only sends it to refresh endpoint
```

---

## Refresh Token Flow

```
Access token expires (after 15 min)
        │
        ▼
User calls POST /refresh-token
Browser automatically includes refresh token cookie
        │
        ▼
  JwtRefreshFilter reads cookie → extracts refresh token
        │
        ▼
  Creates JwtAuthToken(refreshToken)
        │
        ▼
  JWT Authentication Provider validates it
        │
        ▼
  Generate NEW access token (15 min)
        │
        ▼
Response: Authorization: Bearer <new_access_token>
User continues without re-entering password ✅
```

---

## SecurityConfig: The Wiring

```
SecurityConfig does 5 things:
┌─────────────────────────────────────────────────────┐
│  1. Create DaoAuthenticationProvider                 │
│     └── give it: passwordEncoder + userDetailsService│
│                                                      │
│  2. Create ProviderManager (AuthenticationManager)   │
│     └── list: [DaoProvider, JwtProvider]             │
│                                                      │
│  3. Create JwtAuthenticationFilter                   │
│     └── give it: authManager + jwtUtil               │
│                                                      │
│  4. Create JwtValidationFilter                       │
│     └── give it: authManager                         │
│                                                      │
│  5. Register filters at exact positions in chain:    │
│     addFilterBefore(jwtAuthFilter, UsernamePasswordFilter)
│     addFilterAfter(jwtValidFilter, jwtAuthFilter)    │
│     addFilterAfter(jwtRefreshFilter, jwtValidFilter) │
└─────────────────────────────────────────────────────┘
```

---

## Authorization (Role-Based Access)

```java
// In SecurityConfig
.requestMatchers("/api/users").hasRole("USER")
.requestMatchers("/api/admin").hasRole("ADMIN")
```

```
User has role ADMIN tries to access /api/users (requires USER):
  Token is valid ✅
  AuthorizationFilter checks role → ADMIN ≠ USER → 403 Forbidden ❌
  Controller never reached
```

---

## Why Spring Doesn't Provide JWT Out of the Box

Spring provides form-based and basic auth because they're standardized — same for every app.

JWT is NOT standardized across apps because:
- **Payload content** varies — some apps put userId, some put email, some put custom claims
- **Refresh strategy** varies — some need it, some don't
- **Signing algorithm** varies — HS256, RS256, etc.
- **Token storage** varies — cookie, header, local storage

So Spring gives you the framework (filter chain + provider system) and says "you build on top of it." That's exactly what we did.

---

## Mental Model Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMPLETE JWT FLOW                            │
│                                                                  │
│  REGISTER: POST /api/user-register                               │
│  → Hash password → save to DB                                    │
│                                                                  │
│  LOGIN: POST /generate-token                                     │
│  → JwtAuthFilter → DAO validates → JwtUtil generates token       │
│  ← access token (header) + refresh token (cookie)               │
│                                                                  │
│  USE API: GET /api/users  + Authorization: Bearer <token>        │
│  → JwtValidFilter → JwtProvider validates → store in context     │
│  → Controller runs → 200 OK                                      │
│                                                                  │
│  REFRESH: POST /refresh-token  (cookie sent automatically)       │
│  → JwtRefreshFilter → JwtProvider validates → new access token   │
│  ← new access token (header)                                     │
│                                                                  │
│  WRONG ROLE: GET /api/users  (user has ADMIN, needs USER)        │
│  → Token valid but AuthorizationFilter blocks → 403              │
└─────────────────────────────────────────────────────────────────┘
```

> **Golden rule:** JWT is stateless — the server never stores sessions. It trusts the token's signature. If the signature is valid and not expired, the user is authenticated.
