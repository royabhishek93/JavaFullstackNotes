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

**Last Updated:** February 22, 2026  
**Next: [Q24_n_plus_one_problem.md](Q24_n_plus_one_problem.md)**
