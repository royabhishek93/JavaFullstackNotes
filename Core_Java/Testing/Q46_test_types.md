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

**Last Updated:** February 22, 2026  
**Next: [Q47_mockito_mocking.md](Q47_mockito_mocking.md)**
