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

## ⚠️ Common Pitfalls

**Pitfall 1: Forgetting retry logic with optimistic locking**
```java
// ❌ No retry, fails on conflict
@Version
long version;

public void updateProduct(Product product) {
	productRepo.save(product);  // OptimisticLockException if version changed!
}
// Result: User sees error, loses changes

// ✅ Retry logic
@Retryable(value = OptimisticLockingFailureException.class, maxAttempts = 3)
public void updateProduct(Product product) {
	Product current = productRepo.findById(product.getId());
	current.setName(product.getName());  // Apply changes
	productRepo.save(current);  // Retry if version mismatch
}
```

**Pitfall 2: Using optimistic locking for high contention**
```java
// ❌ Incrementing view counter with optimistic lock
@Version
long version;

public void incrementViews(long postId) {
	Post post = postRepo.findById(postId);
	post.setViews(post.getViews() + 1);
	postRepo.save(post);  // 100 concurrent requests = 99 retry failures!
}

// ✅ Use pessimistic lock or atomic update
@Modifying
@Query("UPDATE Post p SET p.views = p.views + 1 WHERE p.id = ?1")
void incrementViews(long postId);  // Atomic, no version check
```

**Pitfall 3: Not handling OptimisticLockException**
```java
// ❌ Exception not caught
public void updateUser(User user) {
	userRepo.save(user);  // OptimisticLockException propagates to user!
}

// ✅ Catch and handle
public void updateUser(User user) {
	try {
		userRepo.save(user);
	} catch (OptimisticLockingFailureException e) {
		throw new ConflictException("User data changed, please refresh");
	}
}
```

**Pitfall 4: Using pessimistic lock for everything**
```java
// ❌ Every read locks the row
@Lock(LockModeType.PESSIMISTIC_WRITE)
Product findById(long id);  // Blocks all other reads!

// ✅ Pessimistic only when needed
Product findById(long id);  // Normal read

@Lock(LockModeType.PESSIMISTIC_WRITE)
Product findByIdForUpdate(long id);  // Only for updates
```

---

## 🛑 When to Use Each

| Scenario | Use This |
|----------|----------|
| E-commerce product updates (low conflict) | **Optimistic** |
| Bank account transfers (high conflict) | **Pessimistic** |
| View/like counters (very high conflict) | **Atomic updates** (no locking) |
| Document editing (medium conflict) | **Optimistic** + retry |

---

---

**Last Updated:** February 22, 2026  
**Next: [Q28_connection_pooling.md](Q28_connection_pooling.md)**
