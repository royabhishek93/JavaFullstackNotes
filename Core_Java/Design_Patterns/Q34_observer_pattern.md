# 🎯 Q34: Observer Pattern in Production Systems

> **Interview Frequency:** 48% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Order placed → trigger email, SMS, update inventory, update analytics. Decouple notifications from order service.

---

## 📌 Pattern

```java
interface OrderObserver {
    void onOrderPlaced(Order order);
}

class Order {
    List<OrderObserver> observers = new ArrayList<>();
    
    void placeOrder() {
        // process order
        notifyObservers();
    }
    
    void notifyObservers() {
        observers.forEach(o -> o.onOrderPlaced(this));
    }
}

class EmailNotifier implements OrderObserver {
    @Override public void onOrderPlaced(Order order) {
        sendEmail(order);
    }
}

// Usage
Order order = new Order();
order.registerObserver(new EmailNotifier());
order.registerObserver(new InventoryUpdater());
order.registerObserver(new AnalyticsLogger());
order.placeOrder();  // Notifies all observers
```

---

## 📚 Real Examples

- **Spring Events:** `ApplicationEvent`, `@EventListener`
- **Message queues:** Kafka topic subscribers
- **UI frameworks:** Property change listeners
- **Webhooks:** External observers of events

---

## 💬 Interview Tip (Say This Exactly)

"Observer decouples event producers from consumers. One-to-many relationship. Use with sync for tight coupling, async (message queues) for loose coupling at scale."

---

**Last Updated:** February 22, 2026  
**Previous: [Q33_strategy_pattern.md](Q33_strategy_pattern.md) | Next: [../../API_Design/Q35_rest_http_methods.md](../../API_Design/Q35_rest_http_methods.md)**
