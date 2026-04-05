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

## ⚠️ Common Pitfalls

**Pitfall 1: Premature microservices**
```
// ❌ 3-person startup with 20 microservices
// Result: More time debugging network than building features

// ✅ Start with modular monolith
// Split to microservices when: >50 engineers, >100k QPS, independent scaling needs
```

**Pitfall 2: Distributed transactions**
```java
// ❌ Trying to use @Transactional across microservices
@Transactional  // Does NOT work across services!
public void placeOrder(Order order) {
    paymentService.charge(order);  // Service 1
    inventoryService.reserve(order);  // Service 2 (different DB!)
}
// If inventory fails, payment already charged!

// ✅ Use saga pattern (compensating transactions)
public void placeOrder(Order order) {
    try {
        paymentService.charge(order);
        inventoryService.reserve(order);
    } catch (InventoryException e) {
        paymentService.refund(order);  // Compensate!
    }
}
```

**Pitfall 3: Shared database across microservices**
```
// ❌ Multiple services write to same database
OrderService → [shared DB] ← PaymentService
// Defeats purpose of microservices!

// ✅ Each service owns its data
OrderService → [Order DB]
PaymentService → [Payment DB]
// Communicate via API or events
```

**Pitfall 4: Too many network calls**
```java
// ❌ N+1 problem across services
for (Order order : orders) {
    User user = userService.getUser(order.getUserId());  // 100ms per call!
}
// 100 orders = 100 network calls = 10 seconds!

// ✅ Batch API or denormalize data
List<User> users = userService.getUsers(orderUserIds);  // 1 call
// Or store user name in order (denormalization)
```

**Pitfall 5: No distributed tracing**
```
// ❌ Request fails, no idea which of 10 services crashed

// ✅ Use distributed tracing (Zipkin, Jaeger)
Request ID: abc123
  → OrderService (50ms)
  → PaymentService (200ms) ← SLOW!
  → InventoryService (30ms)
```

---

## 🛑 When NOT to Use Microservices

- ❌ Startup with <10 engineers (complexity not worth it)
- ❌ QPS <10k (monolith handles easily)
- ❌ Tight coupling between domains (can't split cleanly)
- ❌ Team not experienced with distributed systems
- ✅ DO use: Large teams, independent scaling, polyglot tech stack

---

## 🔗 Related Questions

- [load-balancing-algorithms.md](load-balancing-algorithms.md) - Load balancing microservices
- [message-queues.md](message-queues.md) - Inter-service communication
- [cap-theorem-trade-offs.md](cap-theorem-trade-offs.md) - Distributed system trade-offs
- [../API_Design/Q37_api_versioning.md](../API_Design/Q37_api_versioning.md) - Versioning microservice APIs

---

**Last Updated:** February 22, 2026  
**Next: [cap-theorem-trade-offs.md](cap-theorem-trade-offs.md)**
