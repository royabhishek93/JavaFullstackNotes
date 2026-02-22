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

**Last Updated:** February 22, 2026  
**Next: [Q55_oauth2.md](Q55_oauth2.md)**
