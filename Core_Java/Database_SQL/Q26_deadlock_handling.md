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

## ⚠️ Common Pitfalls

**Pitfall 1: Inconsistent lock ordering**
```java
// ❌ Transaction A
@Transactional
public void transferAtoB() {
	accountRepo.lock(accountA);
	accountRepo.lock(accountB);  // A → B order
}

// ❌ Transaction B
@Transactional
public void transferBtoA() {
	accountRepo.lock(accountB);
	accountRepo.lock(accountA);  // B → A order - DEADLOCK!
}

// ✅ Always same order (sort by ID)
public void transfer(Account from, Account to) {
	Account first = from.getId() < to.getId() ? from : to;
	Account second = from.getId() < to.getId() ? to : from;
	accountRepo.lock(first);
	accountRepo.lock(second);
}
```

**Pitfall 2: Not handling deadlock with retry**
```java
// ❌ Deadlock causes failure, no retry
@Transactional
public void processOrder(Order order) {
	orderRepo.save(order);  // Deadlock → exception → fail
}

// ✅ Retry with backoff
@Retryable(value = DeadlockLoserDataAccessException.class, maxAttempts = 3, backoff = @Backoff(delay = 100))
@Transactional
public void processOrder(Order order) {
	orderRepo.save(order);
}
```

**Pitfall 3: Long transactions increase deadlock chance**
```java
// ❌ Transaction holds locks for 10 seconds
@Transactional
public void generateReport() {
	List<Order> orders = orderRepo.findAll();  // Locks rows
	// 10 seconds of processing
	// Other transactions waiting → deadlock risk
}

// ✅ Short transaction
public void generateReport() {
	List<Order> orders = readOrders();  // 100ms transaction
	processReport(orders);  // No locks held
}
```

---

## 🛑 When Deadlocks Are Hard to Avoid

- ❌ Complex multi-table updates with unpredictable order
- ❌ High concurrency + SERIALIZABLE isolation
- ❌ Application doesn't control lock order (third-party library)
- ✅ **Solution**: Lock ordering + timeout + retry with exponential backoff

---

---

**Last Updated:** February 22, 2026  
**Next: [Q27_optimistic_locking.md](Q27_optimistic_locking.md)**
