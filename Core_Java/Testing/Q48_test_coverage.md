# 🎯 Q48: Test Coverage Metrics?

> **Interview Frequency:** 45% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Team says "90% code coverage". Is that good?

---

## 📌 Coverage Types

| Type | Meaning | Target |
|------|---------|--------|
| **Line** | % of lines executed | 80%+ |
| **Branch** | % of if/else paths | 75%+ |
| **Method** | % of methods tested | 90%+ |

---

## ⚠️ High Coverage ≠ Quality

```java
@Test
void testCalculator() {
    assertEquals(5, calculator.add(2, 3));  // 100% coverage
    // But doesn't test: edge cases, errors, negative numbers
}
```

---

## ✅ Meaningful Coverage

1. **Happy path** - Normal operation
2. **Error cases** - Exceptions
3. **Edge cases** - Null, empty, boundaries
4. **Integration points** - How components interact

---

## 💬 Interview Tip (Say This Exactly)

"Aim for 80% coverage but focus on quality. Cover happy path, errors, edges. High coverage numbers without meaningful tests are useless. Use JaCoCo for metrics, but don't blindly chase %."

---

**Last Updated:** February 22, 2026  
**Next: [Q49_testing_async.md](Q49_testing_async.md)**
