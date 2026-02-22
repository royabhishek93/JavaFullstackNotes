# 🎯 Q21: CAP Theorem Basics?

> **Interview Frequency:** 55% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Why can't a distributed system have all three: Consistency, Availability, Partition tolerance?

---

## 📌 CAP Theorem

**Consistency:** All nodes see same data at same time
**Availability:** System always responsive
**Partition Tolerance:** Works despite network failures

**You can pick 2 of 3:**

### 1. **CA (Consistency + Availability)** ❌
- No network partition tolerance
- Single database (no distribution)
- Example: Single PostgreSQL
- Good for: Non-distributed systems

### 2. **CP (Consistency + Partition Tolerance)** ✅
- System goes down if partition occurs
- Example: HBase, MongoDB
- Good for: Financial systems (no stale data)

### 3. **AP (Availability + Partition Tolerance)** ✅
- Accepts stale data during partition
- Example: DynamoDB, Cassandra
- Good for: Social media (consistency can be eventual)

---

## 💬 Interview Tip (Say This Exactly)

"Most distributed systems are AP by default (available during partitions but eventual consistency). Choose CP (HBase) only if data correctness critical. Most web systems tolerate eventual consistency."

---

**Last Updated:** February 22, 2026  
**Next: [Q22_message_queues.md](Q22_message_queues.md)**
