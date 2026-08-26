# 🎯 Q54: JWT Authentication and Token Management?

> **Interview Frequency:** 68% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

User logs in. Server needs to remember across requests without storing session. How?

---

## 📌 JWT Structure

`eyJhbGc...` (header) . `eyJzdWI...` (payload) . `SflKxw...` (signature)

```java
// Payload (JSON)
{
    "sub": "userId:123",
    "email": "user@example.com",
    "roles": ["USER"],
    "exp": 1708953600,  // 1 hour from now
    "iat": 1708950000
}
```

---

## ✅ Create JWT

```java
String token = Jwts.builder()
    .setSubject(userId)
    .claim("email", email)
    .claim("roles", roles)
    .setIssuedAt(new Date())
    .setExpiration(new Date(System.currentTimeMillis() + 3600000))
    .signWith(SECRET_KEY, SignatureAlgorithm.HS256)
    .compact();
```

---

## ✅ Validate JWT

```java
try {
    Jws<Claims> claims = Jwts.parserBuilder()
        .setSigningKey(SECRET_KEY)
        .build()
        .parseClaimsJws(token);
    
    String userId = claims.getBody().getSubject();
    Long expiration = claims.getBody().getExpiration().getTime();
    
    if (System.currentTimeMillis() > expiration) {
        throw new JwtException("Token expired");
    }
} catch (JwtException e) {
    throw new UnauthorizedException("Invalid token");
}
```

---

## 📌 Key Points

- **Stateless** - No session storage needed
- **Signed** - Can't be forged (unless secret compromised)
- **Expiring** - User forced to re-login after expiration
- **Refresh tokens** - Get new JWT without password

---

## 💬 Interview Tip (Say This Exactly)

"JWT is signed token with payload (userId, roles, expiration). Stateless, no session storage. Validate signature and expiration. Use refresh tokens for renewal. Store in httpOnly cookie or localStorage."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Not validating signature/algorithm**
```java
// ❌ Accepts tokens without checking signature
Claims claims = Jwts.parserBuilder().build().parseClaimsJws(token).getBody();

// ✅ Always validate signature with signing key
Jws<Claims> claims = Jwts.parserBuilder()
    .setSigningKey(SECRET_KEY)
    .build()
    .parseClaimsJws(token);
```

**Pitfall 2: Storing JWT in localStorage**
```text
// ❌ localStorage is accessible to JS → XSS steals token

// ✅ Store in httpOnly cookie
Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Strict
```

**Pitfall 3: No refresh token rotation**
```text
// ❌ Long-lived access token, never rotated
exp = 7 days

// ✅ Short-lived access token + rotating refresh token
access_token: 15 minutes
refresh_token: 7 days, rotate on every refresh
```

**Pitfall 4: Using JWT for logout without revocation**
```text
// ❌ User logs out, token still valid until expiry

// ✅ Maintain token blacklist or use short TTL + refresh
```

---

## 🛑 When NOT to Use JWT

- ❌ You need immediate token revocation (sessions easier)
- ❌ Very large payloads (JWT travels with every request)
- ❌ Simple monolith where server-side sessions are simpler
- ✅ DO use: Stateless APIs, mobile apps, multi-service auth

---

## 🔗 Related Questions

- [Q53_auth_basics.md](Q53_auth_basics.md) - Authentication vs authorization
- [Q55_oauth2.md](Q55_oauth2.md) - OAuth2 flows and JWT
- [Q57_bcrypt_hashing.md](Q57_bcrypt_hashing.md) - Password hashing before JWT
- [Q56_spring_security.md](Q56_spring_security.md) - Integrating JWT with Spring
- [../../API_Design/Q40_api_security.md](../../API_Design/Q40_api_security.md) - API authentication patterns

---

**Last Updated:** February 22, 2026  
**Next: [Q55_oauth2.md](Q55_oauth2.md)**
