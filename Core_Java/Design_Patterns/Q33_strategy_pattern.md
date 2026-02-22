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

- **Sorting:** Different sort algorithms (quicksort, mergesort)
- **Compression:** Different compression strategies
- **Authentication:** Different auth methods (OAuth, JWT, API key)

---

## 💬 Interview Tip (Say This Exactly)

"Strategy pattern encapsulates algorithms and lets client choose at runtime. Similar to dependency injection of behavior. Use when you have multiple ways to do something."

---

**Last Updated:** February 22, 2026  
**Next: [Q34_observer_pattern.md](Q34_observer_pattern.md)**
