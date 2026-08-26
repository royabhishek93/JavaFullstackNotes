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

## ⚠️ Common Pitfalls

**Pitfall 1: Synchronous notification blocks**
```java
// ❌ Email sending blocks order placement
void notifyObservers() {
    observers.forEach(o -> o.onOrderPlaced(this));  // EmailNotifier takes 5 seconds!
}
// Result: Order placement takes 5 seconds

// ✅ Async notification
void notifyObservers() {
    observers.forEach(o -> CompletableFuture.runAsync(() -> o.onOrderPlaced(this)));
}
```

**Pitfall 2: Not handling observer exceptions**
```java
// ❌ One observer fails, others not notified
void notifyObservers() {
    observers.forEach(o -> o.onOrderPlaced(this));  // InventoryUpdater throws exception!
    // EmailNotifier never called
}

// ✅ Catch exceptions per observer
void notifyObservers() {
    observers.forEach(o -> {
        try {
            o.onOrderPlaced(this);
        } catch (Exception e) {
            log.error("Observer failed: " + o, e);
        }
    });
}
```

**Pitfall 3: Memory leak from observers**
```java
// ❌ Observer never unregistered
order.registerObserver(new EmailNotifier());  // Strong reference
// EmailNotifier never garbage collected!

// ✅ Provide unregister + use weak references
public void registerObserver(OrderObserver observer) {
    observers.add(new WeakReference<>(observer));
}
```

**Pitfall 4: Using observer when event bus is better**
```java
// ❌ 100 classes register as observers
order.registerObserver(obs1);
order.registerObserver(obs2);
// ... 98 more

// ✅ Use event bus (Spring @EventListener)
@EventListener
public void onOrderPlaced(OrderPlacedEvent event) {
    // Clean decoupling
}
```

---

## 🛑 When NOT to Use Observer

- ❌ When event bus/message queue available (Spring Events, Kafka)
- ❌ Complex notification logic (use mediator pattern)
- ❌ Few observers (direct method call is simpler)
- ✅ DO use: Decoupling publishers/subscribers, multiple listeners

---

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
