# 🎯 Q31: Builder Pattern vs Constructor Overloading?

> **Interview Frequency:** 62% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Create Order with: id, amount, optional discount, optional customerId, optional shippingAddress. Use 8 constructors or builder?

---

## 📌 Constructor Overload Problem

```java
// WRONG: Telescoping constructors
Order(long id, double amount) { }
Order(long id, double amount, double discount) { }
Order(long id, double amount, double discount, long customerId) { }
Order(long id, double amount, double discount, long customerId, String address) { }
// Hard to read, which param is which?
```

---

## ✅ Builder Solution

```java
Order order = new Order.Builder()
    .id(123)
    .amount(500)
    .discount(50)
    .customerId(456)
    .shippingAddress("Bangalore")
    .build();
// Clear intent, optional fields, no confusion
```

---

## 💬 Interview Tip (Say This Exactly)

"Builder for objects with many optional fields. Constructor for simple objects with few required fields. Builders are also immutable-friendly (final fields)."

---

**Last Updated:** February 22, 2026  
**Next: [Q32_decorator_pattern.md](Q32_decorator_pattern.md)**
