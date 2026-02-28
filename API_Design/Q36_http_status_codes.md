# 🎯 Q36: HTTP Status Codes Explained?

> **Interview Frequency:** 62% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

When to return 201, 204, 400, 401, 403, 404, 500?

---

## 📌 Status Codes

### **2xx: Success**
| Code | Meaning | Use |
|------|---------|-----|
| 200 | OK | GET, PUT, PATCH succeeded |
| 201 | Created | POST succeeded, resource created |
| 204 | No Content | DELETE succeeded, DELETE succeeded |

### **3xx: Redirect**
| Code | Meaning |
|------|---------|
| 301 | Moved Permanently (URL changed) |
| 302 | Found (Temporary redirect) |

### **4xx: Client Error**
| Code | Meaning | Cause |
|------|---------|-------|
| 400 | Bad Request | Invalid JSON, missing params |
| 401 | Unauthorized | Authentication failed (no token) |
| 403 | Forbidden | Authenticated but no permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource version conflict (optimistic lock) |

### **5xx: Server Error**
| Code | Meaning |
|------|---------|
| 500 | Internal Server Error |
| 502 | Bad Gateway (downstream service down) |
| 503 | Service Unavailable (maintenance) |

---

## 💬 Interview Tip (Say This Exactly)

"200 for success, 201 for create, 204 for delete. 400 for client mistake, 401 for missing auth, 403 for insufficient permission, 404 for not found. 500 for server errors. Clients use status to decide retry strategy."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Returning 200 for errors**
```json
// ❌ Always 200 with error payload
{ "success": false, "error": "Invalid input" }

// ✅ Use proper status code
HTTP 400 Bad Request
{ "error": "Invalid input" }
```

**Pitfall 2: Using 401 instead of 403**
```text
// ❌ 401 for authenticated user without permission
// ✅ 403 for authenticated but forbidden
```

**Pitfall 3: Using 500 for client mistakes**
```text
// ❌ 500 for invalid JSON
// ✅ 400 for client input errors
```

---

## 🛑 When NOT to Use 204

- ❌ When client needs response body (return 200)
- ❌ For async operations (return 202 Accepted)
- ✅ DO use: Successful deletes or updates with no body

---

**Last Updated:** February 22, 2026  
**Next: [Q37_api_versioning.md](Q37_api_versioning.md)**
