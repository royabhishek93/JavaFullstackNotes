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

## ⚠️ Common Pitfalls

**Pitfall 1: Inconsistent error shapes**
```json
// ❌ Different endpoints return different formats
{ "error": "Invalid input" }
{ "message": "Bad request" }

// ✅ Standard structure everywhere
{ "status": 400, "error": "ValidationError", "message": "..." }
```

**Pitfall 2: Using message for logic**
```text
// ❌ Client checks message text
if (error.message.contains("expired")) ...

// ✅ Use error codes
error.code == "TOKEN_EXPIRED"
```

**Pitfall 3: Leaking internal errors**
```text
// ❌ Stack traces in response
"NullPointerException at UserService.java:42"

// ✅ Generic message for client, detailed logs server-side
```

---

## 🛑 When NOT to Expose Details

- ❌ Security-sensitive failures (auth, database)
- ❌ Internal exceptions and stack traces
- ✅ DO expose: Field validation errors with safe details

---

**Last Updated:** February 22, 2026  
**Next: [Q39_pagination_filtering.md](Q39_pagination_filtering.md)**
