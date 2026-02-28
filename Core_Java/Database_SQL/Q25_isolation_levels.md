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

## ⚠️ Common Pitfalls

**Pitfall 1: Using SERIALIZABLE everywhere**
```java
// ❌ SERIALIZABLE for every transaction (slow!)
@Transactional(isolation = Isolation.SERIALIZABLE)
public User getUser(Long id) {  // Read-only, why SERIALIZABLE?
    return userRepo.findById(id);
}
// Result: 10x slower, locks, deadlocks

// ✅ Use appropriate level
@Transactional(isolation = Isolation.READ_COMMITTED)  // Default, fast
public User getUser(Long id) {
    return userRepo.findById(id);
}

@Transactional(isolation = Isolation.SERIALIZABLE)  // Only for critical
public void processPayment(Payment payment) {
    // Financial transaction
}
```

**Pitfall 2: Not understanding phantom reads**
```java
// ❌ Transaction 1 (READ_COMMITTED)
long count1 = orderRepo.count();  // 100 orders
// Transaction 2 inserts order
long count2 = orderRepo.count();  // 101 orders - DIFFERENT!
// Result: Same query, different results (phantom read)

// ✅ Use REPEATABLE_READ if this matters
@Transactional(isolation = Isolation.REPEATABLE_READ)
public void processReport() {
    long count1 = orderRepo.count();  // 100
    // Other transactions can't affect this
    long count2 = orderRepo.count();  // Still 100
}
```

**Pitfall 3: Lost updates with READ_COMMITTED**
```java
// ❌ Two threads increment counter
@Transactional(isolation = Isolation.READ_COMMITTED)
public void incrementViews(long postId) {
    Post post = postRepo.findById(postId);
    post.setViews(post.getViews() + 1);  // Both read 100, both set 101!
    postRepo.save(post);
}
// Result: 2 increments, but only +1 total (lost update)

// ✅ Use pessimistic locking or atomic update
@Query("UPDATE Post p SET p.views = p.views + 1 WHERE p.id = ?1")
void incrementViews(long postId);  // Atomic
```

**Pitfall 4: Long transaction with high isolation**
```java
// ❌ REPEATABLE_READ + long transaction = many locks
@Transactional(isolation = Isolation.REPEATABLE_READ)
public void generateReport() {
    List<Order> orders = orderRepo.findAll();  // Locks all rows!
    // Process for 10 seconds
    // Other transactions blocked
}

// ✅ Read data, then process outside transaction
public void generateReport() {
    List<Order> orders = readOrders();  // Short transaction
    processReport(orders);  // Outside transaction
}

@Transactional(readOnly = true)
private List<Order> readOrders() {
    return orderRepo.findAll();
}
```

---

## 🛑 When to Change Default (READ_COMMITTED)

- ❌ For every transaction (unnecessary overhead)
- ❌ When you don't understand what it does
- ✅ **REPEATABLE_READ**: Running same query twice, expect same results (reports)
- ✅ **SERIALIZABLE**: Critical financial transactions (payments, transfers)

---

## 🔗 Related Questions

- [Q23_acid_properties.md](Q23_acid_properties.md) - ACID fundamentals
- [Q26_deadlock_handling.md](Q26_deadlock_handling.md) - Deadlocks from isolation
- [Q27_optimistic_locking.md](Q27_optimistic_locking.md) - Alternative to high isolation

---

**Last Updated:** February 22, 2026  
**Next: [Q26_deadlock_handling.md](Q26_deadlock_handling.md)**
