# #119 — Inner/Anonymous Class Holding Outer Reference

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"How can an anonymous Runnable submitted to a thread pool cause a memory leak?"

## 😊 Explain It Simply (for anyone)
In Java, when you create a small "helper" task defined right inside another class (an "anonymous inner class" — a mini object created on the spot, without giving it a formal class name), it secretly keeps a hidden string attached back to its "parent" object, even if it never actually needs anything from that parent. It's like sending a courier out to deliver ONE small package, but tying a rope from the courier back to your entire house — so as long as the courier hasn't arrived, your whole house is considered "in transit" and can't be sold (garbage collected), even though the courier only needed the one package, not the house.

## 📊 Visualize It
```
 OrderService instance
   |
   +-- pendingOrders: [huge list]
   |
   +-- (implicit link "this$0") <-- anonymous Runnable holds this!
             |
             v
        Runnable queued in executor
        (only needs orderId, but drags whole OrderService along)

 Fix: use a lambda or static class that captures
      ONLY the small piece of data it actually needs.
```

## 🏭 The Real Production Answer (15-YOE Level)

Buggy code:
```java
public class OrderService {
    private final List<Order> pendingOrders = new ArrayList<>(); // large list

    public void scheduleNotification(String orderId) {
        // LEAK: anonymous Runnable implicitly holds 'this' (OrderService instance)
        executor.submit(new Runnable() {
            @Override
            public void run() {
                // only uses orderId, but 'this$0' (OrderService) is captured
                notificationService.send(orderId);
            }
        });
    }
}
```

The anonymous `Runnable` holds an implicit strong reference to the enclosing `OrderService` instance (`this$0`). As long as that Runnable is queued or running in the executor, the entire `OrderService` — including `pendingOrders` — is reachable.

Fix — use a static nested class or lambda capturing only what's needed:
```java
// Lambda captures only orderId (String), not 'this'
public void scheduleNotification(String orderId) {
    executor.submit(() -> notificationService.send(orderId));
}

// Or explicit static class
private static class NotificationTask implements Runnable {
    private final String orderId;
    private final NotificationService svc;
    NotificationTask(String id, NotificationService svc) {
        this.orderId = id; this.svc = svc;
    }
    @Override public void run() { svc.send(orderId); }
}
```

## 🔑 Key Takeaway
Anonymous inner classes silently capture `this` from the enclosing instance — prefer lambdas or static nested classes that capture only the exact data they need.
