# 🎯 Q25: Database Isolation Levels Explained

> **Interview Frequency:** 68% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Multiple concurrent transactions. How much can they see of each other's changes?

---

## 📌 Isolation Levels (Least to Most Strict)

### 1. **READ_UNCOMMITTED** (Dangerous)
- Can read uncommitted data from other transactions
- "Dirty reads" possible
- Almost never used

### 2. **READ_COMMITTED** (Default)
- Can only read committed data
- Still have "phantom reads"
- Good for most cases

### 3. **REPEATABLE_READ**
- Same query returns same results within transaction
- But new rows might appear (phantom reads)
- MySQL default

### 4. **SERIALIZABLE** (Slowest)
- Transactions execute as if sequential
- No dirty/phantom/lost-update reads
- Used only when data correctness critical

---

## 💬 Interview Tip (Say This Exactly)

"Default READ_COMMITTED is good for most cases. Use REPEATABLE_READ if transaction runs same query twice and expects same results. Use SERIALIZABLE only for critical transactions (payments). More strict = slower performance."

---

## ☑️ Examples

```java
@Transactional(isolation = Isolation.READ_COMMITTED)  // Default, fine
public void transfer(Account from, Account to, double amount) {
    // Safe in most cases
}

@Transactional(isolation = Isolation.SERIALIZABLE)  // Payment
public void chargeCard(String cardId, double amount) {
    // Ensures atomicity of payment
}
```

---

**Last Updated:** February 22, 2026  
**Next: [Q26_deadlock_handling.md](Q26_deadlock_handling.md)**
