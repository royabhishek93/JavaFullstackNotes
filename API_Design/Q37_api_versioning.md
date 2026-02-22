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

**Last Updated:** February 22, 2026  
**Next: [Q38_error_responses.md](Q38_error_responses.md)**
