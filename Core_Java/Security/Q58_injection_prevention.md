# 🎯 Q58: SQL Injection, XSS, CSRF Prevention?

> **Interview Frequency:** 50% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

User enters: `" OR "1"="1`. Finds all users! How to prevent?

---

## 📌 Attacks & Prevention

### **SQL Injection (WRONG)**
```java
// WRONG: Concatenate user input
String query = "SELECT * FROM users WHERE id = " + userId;
// User enters: "1 OR 1=1" → Returns all users!

// RIGHT: Prepared statements
String query = "SELECT * FROM users WHERE id = ?";
stmt.setInt(1, userId);  // Parameterized
```

### **XSS (Cross-Site Scripting)**
```java
// WRONG: Echo user input
<h1><%= userComment %></h1>  // User enters: <script>alert('hacked')</script>

// RIGHT: Escape HTML
<h1><spring:escapeBody><%= userComment %></spring:escapeBody></h1>
```

### **CSRF (Cross-Site Request Forgery)**
```java
// Spring Security auto-protects with CSRF tokens
<form method="POST">
    <input name="_csrf" type="hidden" value="<%= token %>"/>
    ...
</form>
```

---

## ✅ Best Practices

1. **SQL:** Always use PreparedStatements, never concatenate
2. **XSS:** Escape output, use template engines (Thymeleaf auto-escapes)
3. **CSRF:** Enable CSRF tokens in Spring Security
4. **Validation:** Validate all inputs server-side
5. **Headers:** Add CSP, X-Frame-Options

---

## 💬 Interview Tip (Say This Exactly)

"SQL injection: use prepared statements. XSS: escape output. CSRF: use tokens. Modern frameworks (Spring) handle CSRF automatically. Always validate/escape on server, never trust client input."

---

**Last Updated:** February 22, 2026  
**Previous: [Q57_password_hashing.md](Q57_password_hashing.md) | Next: [../Observability/Q59_logging_frameworks.md](../Observability/Q59_logging_frameworks.md)**
