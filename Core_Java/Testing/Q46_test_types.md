# 🎯 Q46: Unit vs Integration vs E2E Testing?

> **Interview Frequency:** 55% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

How much of each test type? How to structure?

---

## 📌 Pyramid

```
       E2E (5%)
     Integration (15%)
     Unit (80%)
```

---

## 📌 Comparison

| Type | Scope | Speed | Cost | Frequency |
|------|-------|-------|------|-----------|
| **Unit** | Single method | <1ms | Low | Always |
| **Integration** | Multiple components | 1-10s | Medium | Before commit |
| **E2E** | Full system | 10s+ | High | Nightly |

---

## 💬 Interview Tip (Say This Exactly)

"80% unit tests (fast), 15% integration (slower), 5% E2E (slowest). Unit catches logic bugs early. Integration finds component issues. E2E validates user workflows. Balance speed vs coverage."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Too many E2E tests**
```text
// ❌ 50% E2E tests → slow, flaky CI

// ✅ Keep E2E small (5%), focus on critical user flows
```

**Pitfall 2: Only unit tests**
```text
// ❌ 100% unit tests, zero integration
// Fails when DB config changes or services don't integrate

// ✅ Add integration tests for key components
```

**Pitfall 3: Mocking everything**
```text
// ❌ Even core logic is mocked
// Tests pass but system fails in real usage

// ✅ Mock external boundaries only (DB, API)
```

---

## 🛑 When NOT to Use E2E Tests

- ❌ Every build (too slow)
- ❌ For simple logic (use unit tests)
- ✅ DO use: Critical workflows, release validation

---

**Last Updated:** February 22, 2026  
**Next: [Q47_mockito_mocking.md](Q47_mockito_mocking.md)**
