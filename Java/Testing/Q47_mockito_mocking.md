# 🎯 Q47: Mocking with Mockito - Best Practices?

> **Interview Frequency:** 50% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Database class is external. How to test without real database?

---

## 📌 Mocking

```java
@Test
void testOrderPlacement() {
    // Mock the database
    UserRepository mockRepo = Mockito.mock(UserRepository.class);
    Mockito.when(mockRepo.findById(123))
        .thenReturn(new User("John"));
    
    // Use mock in your service
    OrderService service = new OrderService(mockRepo);
    Order order = service.placeOrder(123);
    
    // Verify behavior
    Mockito.verify(mockRepo).findById(123);
}
```

---

## ✅ When to Mock

| When | Why |
|------|-----|
| **External APIs** | Can't control, unpredictable |
| **Databases** | Too slow, requires setup |
| **Randomness** | Control behavior |
| **Time** | Speed up tests |

---

## ❌ When NOT to Mock

- Simple getters/setters
- Core business logic (use real objects)
- Spring beans (use `@SpringBootTest`)

---

## 💬 Interview Tip (Say This Exactly)

"Mock external dependencies (DB, API). Don't mock core logic. Mock to control behavior and verify calls. Use `@Mock` and `@InjectMocks` for cleaner tests. Prefer ` verify()` over `assertEquals()` for mocks."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Mocking the class under test**
```java
// ❌ Mocking OrderService itself
OrderService service = Mockito.mock(OrderService.class);
// Test does nothing meaningful

// ✅ Mock dependencies, not the class under test
OrderService service = new OrderService(mockRepo);
```

**Pitfall 2: Overusing verify()**
```java
// ❌ Verifying every internal call
verify(repo).findById(1);
verify(repo).findById(1);  // Too strict, brittle tests

// ✅ Verify critical interactions only
```

**Pitfall 3: Stubbing too much**
```java
// ❌ Complex stubbing for simple behavior
when(repo.findById(1)).thenReturn(user);
when(repo.findById(2)).thenReturn(user2);
// ... 10 more

// ✅ Prefer simple, focused tests
```

---

## 🛑 When NOT to Mock

- ❌ Core business logic (test real code)
- ❌ Value objects, simple utilities
- ✅ DO use: External APIs, DB, time/randomness

---

**Last Updated:** February 22, 2026  
**Next: [Q48_test_coverage.md](Q48_test_coverage.md)**
