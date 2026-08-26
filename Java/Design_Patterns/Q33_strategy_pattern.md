# 🎯 Q33: Strategy Pattern Implementation and Use Cases

> **Interview Frequency:** 50% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Different payment methods (credit card, PayPal, UPI). Switch between implementations at runtime.

---

## 📌 Pattern

```java
interface PaymentStrategy {
    void pay(double amount);
}

class CreditCardPayment implements PaymentStrategy {
    @Override public void pay(double amount) { 
        // charge card
    }
}

class PayPalPayment implements PaymentStrategy {
    @Override public void pay(double amount) { 
        // call paypal api
    }
}

class Order {
    PaymentStrategy strategy;
    void processPayment(double amount) {
        strategy.pay(amount);  // Use selected strategy
    }
}

// Usage
Order order = new Order();
order.setStrategy(new CreditCardPayment());
order.processPayment(100);  // Use card

order.setStrategy(new PayPalPayment());
order.processPayment(200);  // Use PayPal
```

---

## 📚 Real Examples

## ⚠️ Common Pitfalls

**Pitfall 1: Using if-else instead of strategy**
```java
// ❌ Violates Open-Closed principle
void processPayment(String method, double amount) {
    if (method.equals("card")) {
        // credit card logic
    } else if (method.equals("paypal")) {
        // paypal logic
    } else if (method.equals("upi")) {
        // upi logic
    }
    // Adding new method = modify this method
}

// ✅ Use strategy pattern
PaymentStrategy strategy = strategyMap.get(method);
strategy.pay(amount);  // No modification needed for new strategies
```

**Pitfall 2: Not handling null strategy**
```java
// ❌ NullPointerException if strategy not set
order.processPayment(100);  // strategy is null!

// ✅ Default strategy or validation
public void processPayment(double amount) {
    if (strategy == null) throw new IllegalStateException("Payment method not set");
    strategy.pay(amount);
}
```

**Pitfall 3: Stateful strategies**
```java
// ❌ Strategy holds state (thread-unsafe!)
class CreditCardPayment implements PaymentStrategy {
    private double amount;  // Shared across threads!
    public void pay(double amount) {
        this.amount = amount;  // Race condition
    }
}

// ✅ Stateless strategies
public void pay(double amount) {
    // Use parameters, not instance variables
    chargeCard(amount);
}
```

---

## 🛑 When NOT to Use Strategy

- ❌ Only one implementation (no variation)
- ❌ Algorithms rarely change (overkill)
- ❌ Simple logic (if-else is fine)
- ✅ DO use: Multiple algorithms, runtime selection, testing variations

---

- **Sorting:** Different sort algorithms (quicksort, mergesort)
- **Compression:** Different compression strategies
- **Authentication:** Different auth methods (OAuth, JWT, API key)

---

## 💬 Interview Tip (Say This Exactly)

"Strategy pattern encapsulates algorithms and lets client choose at runtime. Similar to dependency injection of behavior. Use when you have multiple ways to do something."

---

**Last Updated:** February 22, 2026  
**Next: [Q34_observer_pattern.md](Q34_observer_pattern.md)**
