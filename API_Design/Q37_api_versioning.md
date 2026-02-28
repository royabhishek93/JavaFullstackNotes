# 🎯 Q37: API Versioning Strategies?

> **Interview Frequency:** 58% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

API v1 returns {name, price}. v2 needs {id, name, price, rating}. How to support both?

---

## 📌 Strategies

### 1. **URL Versioning** (Most Common)
```
GET /api/v1/products      # Returns {name, price}
GET /api/v2/products      # Returns {id, name, price, rating}
```
- **Pros:** Clear, easy to route
- **Cons:** Duplicate code, separate deployments

### 2. **Header Versioning**
```
GET /api/products
Accept-Version: v1        # Returns older format
Accept-Version: v2        # Returns new format
```
- **Pros:** Clean URLs
- **Cons:** Less visible, clients must know header

### 3. **Accept Header**
```
GET /api/products
Accept: application/vnd.company.v1+json
Accept: application/vnd.company.v2+json
```
- **Pros:** Standards-based
- **Cons:** Complex for clients

---

## 💬 Interview Tip (Say This Exactly)

"URL versioning most common (v1, v2 in path). Support 2-3 versions concurrently. Mark old versions deprecated. Use feature flags internally, not API versions, for agile development."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Versioning every tiny change**
```text
// ❌ v1.1, v1.2 for every response tweak

// ✅ Use compatible changes without version bump
Add optional fields, keep existing behavior
```

**Pitfall 2: Keeping old versions forever**
```text
// ❌ Supporting v1, v2, v3, v4 for years
// Tech debt grows

// ✅ Deprecate with timeline (e.g., 6-12 months)
```

**Pitfall 3: Breaking changes without version bump**
```text
// ❌ Removing field from v1 response

// ✅ New version for breaking changes
```

---

## 🛑 When NOT to Version

- ❌ Internal APIs with single client (coordinate changes)
- ❌ Minor non-breaking changes (additive changes)
- ✅ DO use: Public APIs, breaking changes, multi-client support

---

**Last Updated:** February 22, 2026  
**Next: [Q38_error_responses.md](Q38_error_responses.md)**
