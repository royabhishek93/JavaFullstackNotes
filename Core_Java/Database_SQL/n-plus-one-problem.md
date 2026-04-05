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

## 🔗 Related Questions

- [isolation-levels.md](isolation-levels.md) - Transaction isolation levels

## ⚠️ Common Pitfalls

**Pitfall 1: Not detecting N+1 in development**
```java
// ❌ Looks fine in code
User user = userRepository.findById(123);
for (Order order : user.getOrders()) {  // N+1 happens here!
    process(order);
}
// Only 1 order in dev DB → seems fast
// Production: 1000 orders → 1001 queries!

// ✅ Enable query logging in application.properties
spring.jpa.show-sql=true
spring.jpa.properties.hibernate.format_sql=true
```

**Pitfall 2: Using FetchType.EAGER everywhere**
```java
// ❌ Always fetches orders, even when not needed
@OneToMany(fetch = FetchType.EAGER)
private List<Order> orders;

User user = userRepository.findById(123);  // Fetches orders too!
// 99% of time orders not needed → wasted query

// ✅ Use LAZY + explicit JOIN FETCH when needed
@OneToMany(fetch = FetchType.LAZY)
private List<Order> orders;

@Query("SELECT u FROM User u LEFT JOIN FETCH u.orders WHERE u.id = ?1")
User findWithOrders(Long id);  // Only when orders needed
```

**Pitfall 3: JOIN FETCH with pagination**
```java
// ❌ In-memory pagination after JOIN (slow!)
@Query("SELECT u FROM User u LEFT JOIN FETCH u.orders")
Page<User> findAll(Pageable pageable);  // WARNING: Hibernate loads ALL users into memory!

// ✅ Use separate query + batch fetch
@Query("SELECT u FROM User u")
Page<User> findAll(Pageable pageable);

@BatchSize(size = 25)
@OneToMany
private List<Order> orders;  // Fetches in batches when accessed
```

**Pitfall 4: N+1 in Streams**
```java
// ❌ N+1 hidden in stream
users.stream()
    .map(user -> user.getOrders().size())  // N queries!
    .collect(Collectors.toList());

// ✅ Fetch all data first
List<User> usersWithOrders = userRepository.findAllWithOrders();
usersWithOrders.stream()
    .map(user -> user.getOrders().size())
    .collect(Collectors.toList());
```

---

## 🛑 When NOT to Use JOIN FETCH

- ❌ Pagination (causes in-memory pagination)
- ❌ Multiple collections (cartesian product explosion)
- ❌ When child data not always needed (use LAZY)
- ✅ DO use: Single collection, data always needed together

---

## 🔗 Related Questions
- [connection-pooling.md](connection-pooling.md) - Connection pool tuning
- [../../System_Design/database-scaling.md](../../System_Design/database-scaling.md) - Database read replicas
- [../Stream_API/Q14_employee_stream_operations.md](../Stream_API/Q14_employee_stream_operations.md) - In-memory data processing alternative

---

**Last Updated:** February 22, 2026  
**Next: [isolation-levels.md](isolation-levels.md)**
