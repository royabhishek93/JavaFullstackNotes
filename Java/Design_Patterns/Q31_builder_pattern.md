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

## ⚠️ Common Pitfalls

**Pitfall 1: Not validating in build()**
```java
// ❌ Builder allows invalid object
Order order = new Order.Builder()
    .id(0)  // Invalid ID!
    .amount(-100)  // Negative amount!
    .build();  // No validation

// ✅ Validate in build()
public Order build() {
    if (id <= 0) throw new IllegalArgumentException("ID must be positive");
    if (amount < 0) throw new IllegalArgumentException("Amount must be >= 0");
    return new Order(this);
}
```

**Pitfall 2: Mutable builder after build()**
```java
// ❌ Reusing builder modifies original object
Order.Builder builder = new Order.Builder().id(1).amount(100);
Order order1 = builder.build();
Order order2 = builder.amount(200).build();  // Modifies order1 if not careful!

// ✅ Make Order immutable, builder creates new instance
public Order build() {
    return new Order(id, amount, discount);  // New object
}
```

**Pitfall 3: Builder for simple objects**
```java
// ❌ Builder overkill
User user = new User.Builder()
    .id(1)
    .name("John")
    .build();
// Only 2 required fields, constructor is better

// ✅ Use constructor
User user = new User(1, "John");
```

**Pitfall 4: Not making object immutable**
```java
// ❌ Setters on built object
public class Order {
    private long id;
    public void setId(long id) { this.id = id; }  // Defeats immutability!
}

// ✅ No setters, final fields
public class Order {
    private final long id;
    // No setters
}
```

---

## 🛑 When NOT to Use Builder

- ❌ Few required fields, no optional fields (use constructor)
- ❌ Object is mutable (Builder for immutable objects)
- ❌ Simple POJOs (use Lombok @Builder)
- ✅ DO use: Many optional fields, immutable objects, fluent API

---

---

**Last Updated:** February 22, 2026  
**Next: [Q32_decorator_pattern.md](Q32_decorator_pattern.md)**
