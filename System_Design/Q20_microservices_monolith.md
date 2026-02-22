# 🎯 Q20: Microservices vs Monolith - Trade-offs?

> **Interview Frequency:** 72% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Should Flipkart be one big monolith or 100+ microservices?

---

## 📌 Comparison

| Aspect | Monolith | Microservices |
|--------|----------|---------------|
| **Deployment** | Single unit, all-or-nothing | Independent, fast |
| **Scaling** | Scale entire app | Scale only needed services |
| **Debugging** | Single codebase, easy | Distributed tracing hard |
| **Tech Stack** | One language/framework | Each service chooses tech |
| **Latency** | Function calls (1ms) | Network calls (100ms) |
| **Failure** | One bug crashes all | Isolated failures |
| **Team Size** | Large teams bottleneck | Small autonomous teams |
| **Complexity** | Code simple, ops simple | Code simple, ops complex |

---

## 💬 Interview Tip (Say This Exactly)

"Start with monolith for MVP. Split to microservices when: 1) Scaling specific services differently, 2) Teams need independent deployment, 3) Tech stack needs vary. Microservices cost: complexity, latency, debugging. Only worth trade-off at scale (100k+ QPS)."

---

## 📚 When Each?

**Monolith suited for:**
- Early stage startups
- Small team (< 20 engineers)
- QPS < 10k
- Consistent tech stack needed

**Microservices needed for:**
- Large companies (100+ engineers)
- QPS > 100k
- Independent scaling needs
- Different tech per domain

---

**Last Updated:** February 22, 2026  
**Next: [Q21_cap_theorem.md](Q21_cap_theorem.md)**
