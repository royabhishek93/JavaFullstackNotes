# 🎯 Q53: Authentication vs Authorization?

> **Interview Frequency:** 50% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

User logs in with username/password. How to ensure they can only see their own data?

---

## 📌 Difference

| Aspect | Authentication | Authorization |
|--------|----------------|---------------|
| **What** | WHO are you? | WHAT can you do? |
| **Method** | Login, password, token | Roles, permissions |
| **Example** | Login succeeds | Can view /admin? NO |

---

## ✅ Example

```java
// Authentication: verify identity
@PostMapping("/login")
public TokenResponse login(@RequestParam String username, String password) {
    if (passwordValid(username, password)) {
        return new Token(username);  // Auth success
    }
    throw new LoginException();
}

// Authorization: check permission
@GetMapping("/admin")
@PreAuthorize("hasRole('ADMIN')")  // Check permission
public AdminPanel getAdminPanel() {
    return adminPanel;
}

// User gets token (authenticated) but can't access /admin (not authorized)
```

---

## 💬 Interview Tip (Say This Exactly)

"Authentication: verify who you are (login). Authorization: verify what you can do (permissions). Use JWT tokens for auth. Use roles/permissions for authorization with Spring Security."

---

**Last Updated:** February 22, 2026  
**Next: [Q54_jwt_tokens.md](Q54_jwt_tokens.md)**
