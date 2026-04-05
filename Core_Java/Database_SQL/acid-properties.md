# 🎯 Q23: What Are ACID Properties (Deep Dive)?

> **Interview Frequency:** 75% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Bank transfer: $100 from Account A to Account B. If system crashes after debit but before credit, what happens?

---

## 📌 ACID Properties

### **A: Atomicity**
- Transaction all-or-nothing
- Transfer: debit AND credit both happen, or neither
- If crash mid-transaction, rollback happens
- No partial updates

### **C: Consistency**
- Data stays valid before and after transaction
- Total account balance never changes (only moves)
- Constraints always satisfied (no negative balance)

### **I: Isolation**
- Concurrent transactions don't interfere
- Transaction A can't see partial changes from B
- Prevents dirty reads, race conditions

### **D: Durability**
- Once committed, survives any failure
- Data persisted to disk, not just memory
- System crash won't lose committed data

---

## 💬 Interview Tip (Say This Exactly)

"ACID: Atomic (all-or-nothing), Consistent (data valid), Isolated (concurrent transactions don't see each other), Durable (commits survive crashes). Example: Money transfer gets all 4 or fails."

---

## ☑️ Checklist

- ✅ Atomicity: Transaction is atomic unit
- ✅ Consistency: Valid state before and after
- ✅ Isolation: Transactions don't interfere
- ✅ Durability: Survives crashes

---

## 🔗 Related Questions

- [isolation-levels.md](isolation-levels.md) - Isolation implementation details

## ⚠️ Common Pitfalls

**Pitfall 1: Not using transactions at all**
```java
// ❌ Without transaction
public void transfer(long fromId, long toId, double amount) {
	accountRepo.debit(fromId, amount);  // Executes immediately!
	accountRepo.credit(toId, amount);   // If this fails, first already committed!
}
// Result: Money lost from sender, never credited to receiver

// ✅ Use @Transactional
@Transactional
public void transfer(long fromId, long toId, double amount) {
	accountRepo.debit(fromId, amount);
	accountRepo.credit(toId, amount);
}  // Both commit together or rollback together
```

**Pitfall 2: Catching exceptions inside @Transactional**
```java
@Transactional
public void processOrder(Order order) {
	try {
		orderRepo.save(order);
		inventoryRepo.reserve(order);  // Throws exception
	} catch (Exception e) {
		log.error("Error", e);  // ❌ Swallowed! Transaction still commits!
	}
}

// ✅ Let exception propagate or mark for rollback
@Transactional
public void processOrder(Order order) {
	try {
		orderRepo.save(order);
		inventoryRepo.reserve(order);
	} catch (Exception e) {
		throw new OrderException("Failed", e);  // Transaction rolls back
	}
}
```

**Pitfall 3: Long-running transactions**
```java
// ❌ Transaction holds locks for seconds
@Transactional
public void processOrders(List<Order> orders) {
	for (Order order : orders) {
		orderRepo.save(order);
		emailService.send(order.getEmail());  // 500ms per email!
	}
}  // Locks held for seconds!

// ✅ Keep transactions short
public void processOrders(List<Order> orders) {
	for (Order order : orders) {
		saveOrder(order);  // Short transaction
		emailService.send(order.getEmail());  // Outside transaction
	}
}

@Transactional
private void saveOrder(Order order) {
	orderRepo.save(order);
}
```

**Pitfall 4: Assuming isolation = perfect consistency**
```java
// ❌ Two concurrent transfers from same account
Thread 1: transfer(accountA, accountB, 100);
Thread 2: transfer(accountA, accountC, 100);
// Both check balance (100), both proceed → -100 balance!

// ✅ Use pessimistic locking
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT a FROM Account a WHERE a.id = ?1")
Account findByIdForUpdate(Long id);
```

---

## 🛑 When ACID Might Be Too Much

- ❌ Logging, analytics (eventual consistency OK)
- ❌ High-throughput systems (NoSQL might be better)
- ❌ Distributed microservices (CAP theorem trade-offs)
- ✅ DO use: Financial transactions, inventory, user data

---

## 🔗 Related Questions
- [n-plus-one-problem.md](n-plus-one-problem.md) - Query optimization
- [optimistic-locking.md](optimistic-locking.md) - Handling concurrent updates
- [../../Spring/Q3_transactional_proxy_flow.md](../../Spring/Q3_transactional_proxy_flow.md) - Spring @Transactional

---

**Last Updated:** February 22, 2026  
**Next: [n-plus-one-problem.md](n-plus-one-problem.md)**
