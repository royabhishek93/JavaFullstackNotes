# 🎯 Q27: Optimistic vs Pessimistic Locking?

> **Interview Frequency:** 55% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

User A and User B both edit the same document. Who wins?

---

## 📌 Comparison

### **Pessimistic Locking** (Blocking)
- Lock immediately when reading
- Other transactions wait
- Prevents but costly
- Use for: High contention scenarios

```java
@Query("SELECT u FROM User u WHERE id = ?1 FOR UPDATE")
User findForUpdate(long id);  // Locks row
```

### **Optimistic Locking** (Version-based)
- No lock, check version on update
- Update fails if version changed
- Retry needed
- Use for: Low contention, high concurrency

```java
@Version
long version;  // Auto-incremented on update
```

---

## 💬 Interview Tip (Say This Exactly)

"Optimistic (version-based) for high concurrency, low conflicts. Pessimistic (locks) for high contention. Optimistic requires retry logic but no blocking. Most web systems use optimistic."

---

**Last Updated:** February 22, 2026  
**Next: [Q28_connection_pooling.md](Q28_connection_pooling.md)**
