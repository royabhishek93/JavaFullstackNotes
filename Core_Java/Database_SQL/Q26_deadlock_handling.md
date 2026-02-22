# 🎯 Q26: Deadlock Detection and Prevention

> **Interview Frequency:** 58% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Transaction A locks Table 1, waits for Table 2. Transaction B locks Table 2, waits for Table 1. Deadlock!

---

## 📌 Prevention Strategies

### 1. **Lock Ordering**
- Always acquire locks in same order
- A: Lock 1 → Lock 2
- B: Lock 1 → Lock 2 (same order, no deadlock)

### 2. **Timeouts**
- Transaction waits 5 seconds, then rollback
- Retry with backoff
- Java: `@Transactional(timeout = 5)` or `Statement.setQueryTimeout()`

### 3. **Shorter Transactions**
- Release locks quickly
- Less time for lock conflicts
- Split large transaction into smaller ones

### 4. **Lower Isolation Level**
- READ_COMMITTED less likely to deadlock
- Trade-off: less consistency

---

## 💬 Interview Tip (Say This Exactly)

"Prevent deadlock: 1) Always acquire locks in same order, 2) Use short transactions, 3) Set timeout and retry with exponential backoff, 4) Use READ_COMMITTED isolation if possible."

---

**Last Updated:** February 22, 2026  
**Next: [Q27_optimistic_locking.md](Q27_optimistic_locking.md)**
