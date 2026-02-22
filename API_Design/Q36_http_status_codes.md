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

**Last Updated:** February 22, 2026  
**Next: [Q37_api_versioning.md](Q37_api_versioning.md)**
