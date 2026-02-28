# 🎯 Q35: HTTP Methods and Idempotency?

> **Interview Frequency:** 65% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

When to use POST, PUT, PATCH, DELETE? What's idempotency?

---

## 📌 HTTP Methods

| Method | Idempotent | Use Case |
|--------|-----------|----------|
| **GET** | ✅ Yes | Retrieve data |
| **POST** | ❌ No | Create new resource (201 Created) |
| **PUT** | ✅ Yes | Replace entire resource |
| **PATCH** | ✅ Yes | Partial update |
| **DELETE** | ✅ Yes | Delete resource (204 No Content) |

---

## 📌 Idempotency

**Idempotent:** Calling N times = same result as once

```java
// IDEMPOTENT: Safe to retry
PUT /api/users/123 { name: "John" }  // 1x or 10x = same result
DELETE /api/users/123               // Deleting deleted = same state

// NOT IDEMPOTENT: Retry causes problems  
POST /api/orders { "amount": 100 }   // 1x = 1 order, 2x = 2 orders!
```

---

## ✅ Proper Endpoints

```
POST   /api/v1/orders                        (201 Created)
GET    /api/v1/orders/{id}                   (200 OK)
PUT    /api/v1/orders/{id} { entire obj }   (200 OK)
PATCH  /api/v1/orders/{id} { "status": "..." }  (200 OK)
DELETE /api/v1/orders/{id}                   (204 No Content)
```

---

## 💬 Interview Tip (Say This Exactly)

"POST creates (not idempotent, can create duplicates if retried), PUT replaces entire resource (idempotent), PATCH updates partially (idempotent), DELETE removes (idempotent). Use idempotent methods for client retries."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Using POST for updates**
```http
// ❌ POST used for update
POST /api/users/123 { "name": "John" }
// Hard to retry safely

// ✅ Use PUT/PATCH for updates
PATCH /api/users/123 { "name": "John" }
```

**Pitfall 2: PUT with partial payload**
```http
// ❌ PUT should replace entire resource
PUT /api/users/123 { "name": "John" }
// What about missing fields?

// ✅ Use PATCH for partial
PATCH /api/users/123 { "name": "John" }
```

**Pitfall 3: DELETE returning 200 with body**
```http
// ❌ Inconsistent response
DELETE /api/users/123 → 200 { "message": "deleted" }

// ✅ 204 No Content
DELETE /api/users/123 → 204 No Content
```

---

## 🛑 When NOT to Use PATCH

- ❌ Full replacement (use PUT)
- ❌ Complex partial updates without clear schema
- ✅ DO use: Small field updates, JSON Patch/merge patch

---

**Last Updated:** February 22, 2026  
**Next: [Q36_http_status_codes.md](Q36_http_status_codes.md)**
