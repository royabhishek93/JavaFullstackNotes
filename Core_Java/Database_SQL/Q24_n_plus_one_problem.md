# 🎯 Q24: Explain N+1 Query Problem and Solutions

> **Interview Frequency:** 73% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Get user with all their orders. Result: 1 query for user + N queries for N orders = N+1 queries!

---

## 📌 The Problem

```java
// WRONG: N+1 queries
User user = userRepository.findById(123);  // 1 query
for (Order order : user.getOrders()) {     // N queries! (one per order)
    process(order);
}
// Total: 1 + N queries = SLOW
```

---

## ✅ Solutions

### 1. **Eager Loading (JOIN)**
```java
@Query("SELECT u FROM User u LEFT JOIN FETCH u.orders WHERE u.id = ?1")
User findWithOrders(long id);  // 1 query with JOIN
```

### 2. **Batch Fetching**
```java
@Fetch(FetchMode.SUBSELECT)
List<Order> orders;  // Subquery fetches all at once
```

### 3. **Explicit Query**
```java
List<Order> orders = orderRepository.findByUserId(userId);  // 1 query
```

---

## 💬 Interview Tip (Say This Exactly)

"N+1: 1 query for parent + N queries for children. Fix: Use eager loading (JOIN), batch fetching, or explicit queries. Monitor with query logging (show_sql=true)."

---

**Last Updated:** February 22, 2026  
**Next: [Q25_isolation_levels.md](Q25_isolation_levels.md)**
