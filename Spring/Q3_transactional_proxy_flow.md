# Q3: @Transactional Flow (Proxy → Interceptor → TransactionManager)

**Study Time:** 10-12 minutes | **Frequency:** 80% in interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## Scenario

**Given this service, what happens at runtime?**

```java
@Service
public class OrderService {

    @Transactional
    public void placeOrder() {
        // 1) Save order
        // 2) Save order items
        // 3) Update inventory
    }
}
```

You add `@Transactional`, but a teammate claims the private method inside the same class is also transactional. Is that true?

---

## Key Principle

`@Transactional` is applied via **Spring AOP proxies**.

**Only calls that pass through the proxy are transactional.**

Internal calls (self-invocation) and private method calls **bypass** the proxy.

---

## Core Flow

```
@Transactional
   ↓
Spring AOP Proxy
   ↓
TransactionInterceptor
   ↓
PlatformTransactionManager
   ↓
Database Transaction (commit/rollback)
```

---

## Step-by-Step Analysis

### 1) Spring Creates a Proxy

When Spring sees `@Transactional`, it creates a proxy for the bean.

- If the class implements an interface → JDK dynamic proxy
- Else → CGLIB proxy

### 2) Client Calls the Proxy

```java
Client → Proxy → public method ✅
```

The proxy intercepts the call and invokes `TransactionInterceptor`.

### 3) TransactionInterceptor Does the Work

It decides:

- Start a transaction
- Commit if successful
- Roll back on exception (by default: runtime exceptions)

### 4) PlatformTransactionManager Executes

The manager delegates to the underlying resource (JDBC, JPA, etc.).

---

## Why Private Methods Are NOT Transactional

```java
@Service
public class OrderService {

    @Transactional
    public void placeOrder() {
        saveOrderInternal(); // ❌ self-invocation
    }

    @Transactional
    private void saveOrderInternal() {
        // This will NOT be transactional
    }
}
```

**Reason:**
- `placeOrder()` calls `saveOrderInternal()` **inside the same class**
- This does **not** go through the proxy
- So `@Transactional` on `saveOrderInternal()` is ignored

---

## Correct Patterns

### ✅ Option 1: Move to Another Bean

```java
@Service
public class OrderService {
    private final OrderWriter writer;

    public OrderService(OrderWriter writer) {
        this.writer = writer;
    }

    public void placeOrder() {
        writer.saveOrderTransactional(); // goes through proxy
    }
}

@Service
public class OrderWriter {

    @Transactional
    public void saveOrderTransactional() {
        // Transactional work
    }
}
```

### ✅ Option 2: Self-Proxy (Advanced)

```java
@Service
public class OrderService {

    @Autowired
    private OrderService self;

    public void placeOrder() {
        self.saveOrderInternal(); // goes through proxy
    }

    @Transactional
    public void saveOrderInternal() {
        // Now transactional
    }
}
```

⚠ Use with caution; can be confusing and brittle.

---

## Common Interview Q&A

### Q1: What happens when I add `@Transactional`?

**Answer:**
```
Spring creates a proxy that routes method calls through
TransactionInterceptor, which uses PlatformTransactionManager
to start/commit/rollback a transaction.
```

---

### Q2: Why don't private methods become transactional?

**Answer:**
```
Because transactions are applied via proxies.
Private methods are called directly inside the class,
so the proxy is bypassed.
```

---

### Q3: What exceptions trigger rollback by default?

**Answer:**
```
By default, runtime exceptions (unchecked) cause rollback.
Checked exceptions do NOT, unless configured.
```

---

### Q4: How to force rollback for checked exceptions?

**Answer:**
```java
@Transactional(rollbackFor = Exception.class)
public void save() { ... }
```

---

### Q5: What if I call a @Transactional method from the same class?

**Answer:**
```
Self-invocation bypasses the proxy, so @Transactional
won't be applied. Move the method to another bean
or call via the proxy.
```

---

## Visual Summary

```
Client
  ↓
Spring Proxy
  ↓
TransactionInterceptor
  ↓
PlatformTransactionManager
  ↓
DB Transaction (commit / rollback)
```

---

## Common Pitfalls

```java
❌ Pitfall 1: @Transactional on private method
// Not intercepted

❌ Pitfall 2: Self-invocation
// Bypasses proxy

❌ Pitfall 3: Using @Transactional on final methods
// CGLIB cannot override final methods

❌ Pitfall 4: Forgetting rollbackFor for checked exceptions
// No rollback by default
```

---

## Interview Answer (Concise)

**Q: "Explain the @Transactional flow."**

**Answer:**

> "`@Transactional` works through Spring AOP proxies. The proxy intercepts external method calls and delegates to `TransactionInterceptor`, which uses a `PlatformTransactionManager` to begin, commit, or roll back a transaction. Internal calls inside the same class, including private methods, bypass the proxy, so they are not transactional unless invoked through another bean or the proxy itself."

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| Proxy-based transactions | Explains behavior | ⭐⭐⭐⭐⭐ |
| TransactionInterceptor | Core execution logic | ⭐⭐⭐⭐ |
| Self-invocation caveat | Common trick question | ⭐⭐⭐⭐⭐ |
| Rollback rules | Production impact | ⭐⭐⭐⭐ |
| TransactionManager | Real transaction boundary | ⭐⭐⭐⭐ |
