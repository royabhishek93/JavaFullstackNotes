# 🎯 Q38: Error Response Standardization?

> **Interview Frequency:** 55% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Different errors return different formats. Client doesn't know how to parse.

---

## 📌 Standard Error Format

```json
{
  "status": 400,
  "error": "ValidationError",
  "message": "Invalid order amount",
  "timestamp": "2026-02-22T10:30:00Z",
  "path": "/api/orders",
  "details": [
    {
      "field": "amount",
      "reason": "must be positive"
    }
  ]
}
```

---

## ✅ Good Practices

1. **Consistent structure** - Always include status, error, message
2. **Error codes** - `INVALID_INPUT`, `UNAUTHORIZED`, not generic
3. **Timestamp** - When error occurred
4. **Path** - Which endpoint failed
5. **Details** - Field-level errors for validation

---

## 💬 Interview Tip (Say This Exactly)

"Standardize error responses. Include: status, error type, message, timestamp, affected field. Clients parse error type, not message (messages are for logging). Use error codes for programmatic handling."

---

**Last Updated:** February 22, 2026  
**Next: [Q39_pagination_filtering.md](Q39_pagination_filtering.md)**
