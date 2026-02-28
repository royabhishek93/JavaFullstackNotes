# 🎯 Q57: Password Hashing and Storage (bcrypt, scrypt, PBKDF2)?

> **Interview Frequency:** 72% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Store user password. Must be irreversible. Must resist brute force.

---

## 📌 Comparison

| Algorithm | Speed | Cost | Use |
|-----------|-------|------|-----|
| **bcrypt** | Adaptive | ✅ Medium | Use this |
| **scrypt** | Adaptive | ✅✅ Higher | Better |
| **PBKDF2** | Fixed | ❌ Low | Acceptable |
| **MD5** | Fast | ❌ None | NEVER |

---

## ✅ bcrypt (Spring Standard)

```java
BCryptPasswordEncoder encoder = new BCryptPasswordEncoder();

// Hash password
String hashed = encoder.encode("myPassword123");  
// Output: $2a$10$slYQmyNdGzin7olVfH2MkO... (different every time!)

// Verify password
boolean matches = encoder.matches("myPassword123", hashed);
```

---

## 📌 Why Not Simple Hash?

```java
// WRONG: MD5 is reversible via rainbow tables
String hash = DigestUtils.md5Hex("password");  // 5f4dcc3b5aa765d61d8327deb882cf99

// RIGHT: bcrypt has salt and work factor
$2a$10$...  // $2a$ = version, $10$ = work factor, ... = salt+hash
```

---

## ✅ Spring Security Config

```java
@Configuration
public class SecurityConfig {
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);  // Work factor 12 (slower = safer)
    }
}
```

---

## 💬 Interview Tip (Say This Exactly)

"Use bcrypt with work factor 10-12 (4 chars='cost'). Each hash unique due to salt. Never store plain, never use MD5. Verify with encoder.matches(). Takes 100ms per hash (good!)."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Using low work factor**
```java
// ❌ Too fast, easy to brute force
new BCryptPasswordEncoder(4);

// ✅ Use 10-12 for production
new BCryptPasswordEncoder(12);
```

**Pitfall 2: Re-hashing password on login**
```java
// ❌ Wrong - hashing input and comparing strings
String inputHash = encoder.encode(rawPassword);
if (inputHash.equals(storedHash)) { ... }  // Always false

// ✅ Use matches()
if (encoder.matches(rawPassword, storedHash)) { ... }
```

**Pitfall 3: Migrating from weak hashes without upgrade plan**
```text
// ❌ Users keep MD5 hashes forever

// ✅ Rehash on login
if (isLegacyHash(storedHash) && matchesLegacy(rawPassword)) {
    user.setPassword(encoder.encode(rawPassword));
}
```

**Pitfall 4: Using bcrypt for API tokens**
```text
// ❌ bcrypt for short-lived tokens (slow, unnecessary)

// ✅ Use HMAC or random tokens with expiration
```

---

## 🛑 When NOT to Use bcrypt

- ❌ Very high-throughput auth without caching (latency sensitive)
- ❌ Hardware-accelerated attackers and large budgets (consider Argon2)
- ✅ DO use: User passwords, admin credentials, long-lived secrets

---

## 🔗 Related Questions

- [Q53_auth_basics.md](Q53_auth_basics.md) - Authentication fundamentals
- [Q54_jwt_implementation.md](Q54_jwt_implementation.md) - JWT token security
- [Q56_spring_security.md](Q56_spring_security.md) - Spring Security configuration
- [Q58_injection_prevention.md](Q58_injection_prevention.md) - Preventing security vulnerabilities

---

**Last Updated:** February 22, 2026  
**Next: [Q58_injection_prevention.md](Q58_injection_prevention.md)**
