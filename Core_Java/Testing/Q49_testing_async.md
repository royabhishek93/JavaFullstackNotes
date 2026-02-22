# 🎯 Q49: Testing Async Code (CompletableFuture)?

> **Interview Frequency:** 48% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Test async method that returns CompletableFuture. How to wait for result?

---

## 📌 Approaches

### 1. **Using `.get()` (Blocking)**
```java
@Test
void testAsync() throws Exception {
    CompletableFuture<String> future = asyncService.fetchData();
    String result = future.get(5, TimeUnit.SECONDS);  // Wait 5 sec max
    assertEquals("expected", result);
}
```

### 2. **Using `.thenApply()` (Chaining)**
```java
@Test
void testAsyncChain() {
    asyncService.fetchData()
        .thenApply(result -> {
            assertEquals("expected", result);
            return null;
        })
        .join();  // Wait for completion
}
```

### 3. **Using Awaitility (Assertion Library)**
```java
@Test
void testAsyncAwaitility() {
    asyncService.fetchData();
    
    Awaitility.await()
        .atMost(Duration.ofSeconds(5))
        .until(() -> someCondition.isTrue());
}
```

---

## ✅ Best Practices

1. **Always set timeout** - Prevent hanging tests
2. **Use `.get(timeout)`** - Simple case
3. **Use Awaitility** - Complex polling
4. **Don't use `.sleep()`** - Unreliable, slow tests

---

## 💬 Interview Tip (Say This Exactly)

"Use `.get(timeout)` for simple async tests. Use Awaitility for polling. Always set timeout to prevent hanging. Mock async calls in unit tests, real calls in integration tests."

---

**Last Updated:** February 22, 2026  
**Next: [Q50_spring_test_slices.md](Q50_spring_test_slices.md)**
