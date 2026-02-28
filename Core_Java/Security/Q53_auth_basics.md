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

## ⚠️ Common Pitfalls

**Pitfall 1: Mixing authentication and authorization**
```java
// ❌ Assuming login = admin access
if (user.isAuthenticated()) {
    return adminPanel;  // Anyone logged in gets admin!
}

// ✅ Always enforce authorization
@PreAuthorize("hasRole('ADMIN')")
public AdminPanel getAdminPanel() { return adminPanel; }
```

**Pitfall 2: Relying on client-side checks**
```js
// ❌ Frontend hides admin button, but backend still allows access
if (user.role === "ADMIN") showAdminButton();

// ✅ Server must enforce authorization
// Backend: @PreAuthorize("hasRole('ADMIN')")
```

**Pitfall 3: Storing passwords in plain text**
```java
// ❌ Plain text password storage
user.setPassword("myPassword123");

// ✅ Hash passwords (bcrypt)
user.setPassword(passwordEncoder.encode("myPassword123"));
```

**Pitfall 4: Using roles for identity**
```java
// ❌ Using role to identify user
if (user.hasRole("USER")) { /* assume userId */ }

// ✅ Use userId for identity, roles for permissions
String userId = auth.getName();
```

---

## 🛑 When NOT to Use Only Authentication

- ❌ Public data access without authorization checks (data leaks)
- ❌ Assuming JWT auth implies all permissions
- ✅ DO use: Separate authn + authz layers with role/permission checks

---

**Last Updated:** February 22, 2026  
**Next: [Q54_jwt_tokens.md](Q54_jwt_tokens.md)**
