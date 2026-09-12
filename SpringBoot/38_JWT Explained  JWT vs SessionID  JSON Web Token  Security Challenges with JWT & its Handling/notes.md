# JWT — JSON Web Token, JWT vs Session ID, and Security Challenges

## What is this? (Plain English)

Think of a **signed, tamper-evident wristband** at a concert or theme park. Once the gate staff checks your ID and clips the wristband on, it already encodes everything a gate needs to know — your name, which zones you're allowed into, and when it expires. Any other gate in the venue can glance at the wristband, confirm it hasn't been forged or altered, and let you through *without radioing back to a central desk* to look you up. If you cut the wristband off and put it on someone else, or try to scribble a new expiry date on it, it's immediately obvious it's been tampered with.

A JWT (JSON Web Token) is that wristband for API requests. It's a way of transmitting information between parties as a JSON object, digitally signed so it can't be silently modified, and self-contained so any server can verify it without needing to look anything up in a database.

Today JWT is used in three overlapping areas:
- **Authentication** — confirming *who* the user is (e.g., "yes, this is Shan").
- **Authorization** — confirming *what* the user is allowed to do (e.g., "does Shan have permission to fetch this resource").
- **Single Sign-On (SSO)** — logging in once and reusing the same token to access multiple applications without re-entering credentials each time.

## The Problem It Solves

Before JWT became popular, the standard approach was **session ID** (often called `JSESSIONID`):

1. Client logs in with username/password.
2. The server generates a random session ID, and stores it **in a database** along with the user it belongs to, its expiry time, and the user's roles/permissions.
3. The session ID is handed back to the client, which sends it along with every subsequent request (typically in a cookie).
4. On every request, the server has to **query the database** using that session ID to fetch the expiry, roles, and other details, and only then decide whether to allow the request.

This makes session ID **stateful** — the server (and its database) must remember every issued session. In a distributed system this becomes painful: sessions are written to one DB cluster, but a later request might land on a different server, so all DB clusters/replicas need to stay in sync. On top of that, every single request now pays the extra latency of a DB (or cache) lookup just to validate who's calling.

JWT flips this: the token itself carries all the necessary information (user identity, roles, expiry) and is digitally signed. The server can verify the signature and read the claims **without touching a database at all** — that's what makes JWT **stateless**. This is the core tradeoff to remember:

- **Session ID**: stateful, requires server-side storage and DB/cache lookups on every request, but a token can be revoked instantly by deleting its DB record.
- **JWT**: stateless, no DB lookup needed to validate a request, faster and easier to scale across services — but *because* nothing is stored server-side, there's no built-in way to revoke a single token before it naturally expires.

That last point becomes one of the biggest real-world security challenges with JWT (covered below).

### Typical Authentication Flow

```text
Client                Authentication Server              Resource Server (your app)
  | 1. username/password        |                                |
  |----------------------------->|                                |
  |     2. generate JWT          |                                |
  |<-----------------------------|                                |
  |                                                                |
  | 3. GET /resource                                               |
  |    Authorization: Bearer <JWT>                                 |
  |----------------------------------------------------------------->|
  |                                | 4. verify token (internal call)|
  |                                |<--------------------------------|
  |                                | 5. valid / roles / claims       |
  |                                |-------------------------------->|
  |                       6. response with requested data            |
  |<-------------------------------------------------------------------|
```

With **SSO**, the same JWT issued once by the authentication server is reused across App 1, App 2, App 3 — each app independently verifies the token (and reads the user's name/email straight out of the payload) instead of asking the user to log in again.

## JWT Structure

A JWT is three base64url-encoded parts joined by dots: `header.payload.signature`.

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

```text
+----------------------------+   +--------------------------------+   +---------------------------------+
|  HEADER                    |   |  PAYLOAD (claims)               |   |  SIGNATURE                       |
|  { "typ": "JWT",           |   |  Registered: iss, sub, aud,     |   |  HMAC(secret) or RSA(privateKey) |
|    "alg": "HS256" }        |   |  exp, nbf, iat, jti             |   |  applied over:                   |
|                            |   |  Public: email, country ...     |   |  base64url(header) + "." +       |
|                            |   |  Private: internal-only fields  |   |  base64url(payload)              |
+-------------+--------------+   +---------------+------------------+   +---------------+-------------------+
              | base64url encode                | base64url encode                    | base64url encode
              v                                  v                                      v
      base64url(header)                  base64url(payload)                    base64url(signature)

Final JWT =  base64url(header)  +  "."  +  base64url(payload)  +  "."  +  base64url(signature)
             \______ Header ______/       \______ Payload _______/       \______ Signature _______/
```

**Header** — metadata: `typ` (always `JWT`) and `alg` (signing algorithm: `HS256` for HMAC, or `RS256` for RSA).

**Payload (claims)** — split into three categories:
- **Registered claims**: reserved names with predefined meaning — `iss` (issuer), `sub` (subject/user identifier), `aud` (audience/intended recipient), `exp` (expiry time — token invalid after this), `nbf` (not-before — token invalid before this), `iat` (issued-at time), `jti` (unique token ID, used for blacklisting/single-use).
- **Public claims**: custom fields with meaning shared and understood across multiple parties, e.g. `email`, `country`. Never put confidential data (like passwords) here — it's only encoded, not encrypted.
- **Private claims**: custom fields meant only for internal use by the issuer (e.g., an internal flag); other resource servers receiving the token don't need to and don't understand them.

**Signature** — computed by base64url-encoding the header and payload, joining them with a `.`, then signing that string with either an HMAC secret (same key used to sign and verify) or an RSA private key (verified later using the corresponding public key). The signature is then base64url-encoded and appended.

## JWT Validation Flow (ASCII)

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

```text
Client                     Resource Server                    Auth Server / Key Store
  |  GET /resource                 |                                    |
  |  Authorization: Bearer <JWT>   |                                    |
  |------------------------------->|                                    |
  |                                | split token into                   |
  |                                | header.payload.signature           |
  |                                |----------------------------------->|
  |                                |  verify signature using             |
  |                                |  HMAC secret or RSA public key      |
  |                                |<-----------------------------------|
  |                                |        valid / invalid              |
  |                                |
  |                       [signature invalid] --> 401 Unauthorized -------|
  |                                |
  |                       decode payload, check exp/nbf,                 |
  |                       check jti against blacklist                    |
  |                                |
  |                [expired / blacklisted] --> 401 / 403 Rejected         |
  |                                |
  |                 [all checks pass] --> read roles/claims               |
  |<-------------------------------|          200 OK + data                |
```

## Key Code / Config

```xml
<!-- pom.xml -->
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-api</artifactId>
    <version>0.11.5</version>
</dependency>
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-impl</artifactId>
    <version>0.11.5</version>
    <scope>runtime</scope>
</dependency>
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-jackson</artifactId>
    <version>0.11.5</version>
    <scope>runtime</scope>
</dependency>
```

```properties
# application.properties
jwt.secret=replace-with-a-long-random-base64-encoded-secret
jwt.access-token-expiry-ms=300000
jwt.refresh-token-expiry-ms=604800000
```

### Token generation (Header + Payload + Signature)

```java
@Component
public class JwtUtil {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.access-token-expiry-ms}")
    private long accessTokenExpiryMs;

    private Key signingKey() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    // Short-lived access token: registered claims (sub, iat, exp, jti) + public claim (email) + role.
    public String generateAccessToken(String userId, String email, List<String> roles) {
        Instant now = Instant.now();
        return Jwts.builder()
                .setHeaderParam("typ", "JWT")
                .setSubject(userId)                                  // registered claim: sub
                .claim("email", email)                                // public claim
                .claim("roles", roles)                                // custom claim used for authorization
                .setId(UUID.randomUUID().toString())                  // registered claim: jti (used for blacklist/single-use)
                .setIssuedAt(Date.from(now))                           // registered claim: iat
                .setExpiration(Date.from(now.plusMillis(accessTokenExpiryMs))) // registered claim: exp
                .signWith(signingKey(), SignatureAlgorithm.HS256)
                .compact();
    }

    public Jws<Claims> parseAndValidate(String token) {
        return Jwts.parserBuilder()
                .setSigningKey(signingKey())
                .build()
                .parseClaimsJws(token); // throws if signature invalid or token expired
    }
}
```

### Validation filter (checks Bearer token + blacklist on every request)

```java
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private TokenBlacklistService blacklistService;

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                     FilterChain chain) throws ServletException, IOException {

        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || !header.startsWith("Bearer ")) {
            chain.doFilter(request, response); // no token: let downstream security rules decide
            return;
        }

        String token = header.substring("Bearer ".length());
        try {
            Jws<Claims> jws = jwtUtil.parseAndValidate(token); // verifies signature + checks exp
            Claims claims = jws.getBody();

            if (blacklistService.isRevoked(claims.getId())) { // jti-based revocation check
                response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Token has been revoked");
                return;
            }

            List<String> roles = claims.get("roles", List.class);
            var authorities = roles.stream().map(SimpleGrantedAuthority::new).toList();
            var authentication = new UsernamePasswordAuthenticationToken(claims.getSubject(), null, authorities);
            SecurityContextHolder.getContext().setAuthentication(authentication);

        } catch (ExpiredJwtException | SignatureException | MalformedJwtException e) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Invalid or expired token");
            return;
        }

        chain.doFilter(request, response);
    }
}
```

### Token invalidation before expiry (blacklist by `jti`)

```java
@Service
public class TokenBlacklistService {

    // In production back this with Redis/cache, keyed by jti, with a TTL matching the token's remaining expiry.
    private final Set<String> revokedTokenIds = ConcurrentHashMap.newKeySet();

    public void revoke(String jti) {
        revokedTokenIds.add(jti);
    }

    public boolean isRevoked(String jti) {
        return revokedTokenIds.contains(jti);
    }
}
```

### Refresh tokens (mitigates short-lived-access-token inconvenience)

```java
@RestController
@RequestMapping("/auth")
public class AuthController {

    @Autowired
    private JwtUtil jwtUtil;

    @Autowired
    private RefreshTokenService refreshTokenService;

    // Called when the short-lived access token expires, without forcing a full re-login.
    @PostMapping("/refresh")
    public ResponseEntity<TokenResponse> refresh(@RequestBody RefreshRequest request) {
        RefreshTokenService.Session session = refreshTokenService.validateAndConsume(request.getRefreshToken());
        String newAccessToken = jwtUtil.generateAccessToken(session.userId(), session.email(), session.roles());
        return ResponseEntity.ok(new TokenResponse(newAccessToken));
    }
}
```

## Important Concepts

- **JWT vs JWS**: A JWT with no signature (`alg: none`) is called an **unsecured JWT** and must always be rejected. In practice nobody issues tokens without a signature, so "JWT" and "JWS" (JSON Web Signature — the signed variant) are used interchangeably.
- **JWE (JSON Web Encryption)**: JWT payloads are only base64-encoded, not encrypted — anyone can base64-decode and read them, so confidential data should never go in the payload. JWE encrypts the payload itself (encrypt with the recipient's public key, decrypt with their private key) when confidentiality of the claims is required.
- **Registered / Public / Private claims**: registered claims (`iss`, `sub`, `aud`, `exp`, `nbf`, `iat`, `jti`) have standardized meaning; public claims are custom but understood across services (e.g. `email`); private claims are custom and meaningful only to the issuer internally.
- **Bearer vs Basic auth header**: credentials always travel in the `Authorization` header. `Basic <base64(username:password)>` is for raw credentials; `Bearer <token>` tells the server "a token is being presented, not a username/password" so it applies token-validation logic instead.
- **Token invalidation problem**: because JWT is stateless, the server has no built-in memory of issued tokens, so a compromised/fraudulent user's token stays valid until it naturally expires. Three common mitigations, each with a tradeoff:
  1. **Blacklist by `jti`** in a DB/cache — works, but reintroduces the DB/cache lookup that JWT was meant to avoid.
  2. **Rotate the signing key** — invalidates the attacker's token, but also invalidates every genuine user's still-valid token signed with the old key, forcing everyone to log in again.
  3. **Short-lived + single-use tokens** (e.g. 5-minute expiry, used once) — shrinks the exposure window; enforcing "single use" still requires tracking used `jti` values somewhere, so it's usually combined with short expiry rather than replacing tracking entirely.
- **JWK spoofing exploit**: an attacker can tamper with a token's payload, re-sign it with their own key, and embed their own public key directly in the JWT header's `jwk` field. If the resource server naively verifies the signature using that embedded public key, the forged token passes validation. **Mitigation**: never trust a public key embedded inside the token itself. Instead, use the header's `kid` (Key ID) to look up the correct verification key from the issuer's own trusted, well-known JWKS endpoint (a whitelisted set of public keys), and only work with reputable identity providers that properly secure their key material.

## Interview Q&A

**Q1: Why is JWT considered stateless compared to session ID (`JSESSIONID`), and what's the tradeoff?**
A: With session ID, the server generates a random ID and stores the user's identity, roles, and expiry in a database; every request needs a DB/cache lookup by that ID. JWT instead packs identity, roles, and expiry directly into a signed token, so the server can verify it with just a signature check — no DB call. The tradeoff is that the server no longer has a record of issued tokens, making it hard to revoke a single token before its natural expiry.

**Q2: How would you invalidate one compromised JWT before it expires, given the server doesn't store tokens?**
A: Maintain a blacklist of revoked token IDs (`jti`) in a DB or cache, checked on every request — at the cost of a lookup. Alternatively, rotate the signing key (invalidates all tokens, including genuine ones) or keep tokens short-lived and single-use so the exposure window is small even without full revocation support.

**Q3: What's the difference between JWS and JWE, and when would you use JWE?**
A: JWS (what most people just call "JWT") signs the header and payload so tampering is detectable, but the payload itself is only base64-encoded and readable by anyone. JWE encrypts the payload so its contents are hidden, not just tamper-evident. Use JWE when the claims themselves contain sensitive data that must not be readable by anyone holding the token.

**Q4: Why should a resource server never trust the public key embedded in a JWT's own `jwk` header field?**
A: An attacker can tamper with the payload, sign it with their own private key, and simply attach their matching public key inside the token's `jwk` field. If the server blindly verifies against that embedded key, the forged signature checks out. Verification keys must instead be resolved via the token's `kid` against the issuer's own trusted, well-known JWKS endpoint — never from data supplied inside the token being verified.

**Q5: What's the difference between `Authorization: Basic` and `Authorization: Bearer`?**
A: `Basic` carries `base64(username:password)` — raw credentials. `Bearer` carries a token (like a JWT) and tells the server "authenticate me using this pre-issued token" rather than a username/password pair, so the server applies token-validation logic (signature check, expiry, claims) instead of a credentials check.

**Q6: How does signing with HMAC differ from signing with RSA for JWTs?**
A: HMAC is symmetric — the exact same secret key is used both to sign the token and to verify it, so every service that needs to verify tokens must hold that shared secret. RSA is asymmetric — the private key signs the token, and the public key (which can be distributed more freely) verifies it, so services can verify signatures without ever having access to the signing key itself.
