# Decoupled Order Processing with Event Bus — Swiggy Scenario
> **Topic:** Event Emitter | **Level:** Intermediate | **Frequency:** High

## The Setup
You are designing the order placement flow at Swiggy. When an order is placed, five things must happen: notify the restaurant, send an SMS to the customer, initialize live tracking, award loyalty points, and log to the analytics pipeline. A junior engineer writes `OrderService` to call all five directly. You need to explain why this is wrong and refactor it.

## The Question
The `OrderService` directly imports and calls RestaurantService, SMSService, TrackingService, LoyaltyService, and AnalyticsService. What is wrong with this architecture? How would you refactor it using an event bus?

## Diagram

```
BEFORE — Tight coupling:
  OrderService.placeOrder()
    ├── restaurantService.notify()    ← direct import
    ├── smsService.send()             ← direct import
    ├── trackingService.init()        ← direct import
    ├── loyaltyService.award()        ← direct import
    └── analyticsService.track()     ← direct import

  Adding a 6th service = modifying OrderService = risky, needs re-deploy

AFTER — Event bus (loose coupling):
  OrderService.placeOrder()
    └── orderBus.emit('order.placed', payload)   ← only this

  RestaurantService  ← orderBus.on('order.placed', ...)
  SMSService         ← orderBus.on('order.placed', ...)
  TrackingService    ← orderBus.on('order.placed', ...)
  LoyaltyService     ← orderBus.on('order.placed', ...)
  AnalyticsService   ← orderBus.on('order.placed', ...)

  Adding a 6th service = one new .on() registration, zero changes to OrderService
```

## Model Answer (15 YOE)

```js
class EventEmitter {
  constructor() {
    this.listeners = new Map();
  }

  on(event, listener) {
    if (!this.listeners.has(event)) this.listeners.set(event, []);
    this.listeners.get(event).push(listener);
    return this;
  }

  off(event, listener) {
    if (!this.listeners.has(event)) return this;
    this.listeners.set(event, this.listeners.get(event).filter(fn => fn !== listener));
    return this;
  }

  emit(event, ...args) {
    if (!this.listeners.has(event)) return this;
    [...this.listeners.get(event)].forEach(fn => fn(...args));
    return this;
  }

  once(event, listener) {
    const wrapper = (...args) => { listener(...args); this.off(event, wrapper); };
    return this.on(event, wrapper);
  }
}

// --- singleton bus ---
const orderBus = new EventEmitter();

// --- downstream services wire up independently ---
orderBus.on('order.placed', ({ orderId, restaurantId }) =>
  restaurantService.notify(restaurantId, orderId)
);
orderBus.on('order.placed', ({ orderId, userId }) =>
  smsService.send(userId, `Order ${orderId} confirmed`)
);
orderBus.on('order.placed', ({ orderId }) =>
  trackingService.init(orderId)
);
orderBus.on('order.placed', ({ userId, total }) =>
  loyaltyService.award(userId, total)
);
orderBus.on('order.placed', (payload) =>
  analyticsService.track('order_placed', payload)
);

// --- OrderService knows nothing about downstream ---
class OrderService {
  placeOrder(orderData) {
    const order = db.orders.create(orderData);
    orderBus.emit('order.placed', {
      orderId: order.id,
      userId: orderData.userId,
      restaurantId: orderData.restaurantId,
      total: orderData.total,
    });
    return order;
  }
}
```

**Why `Map` over a plain object:** Using a `Map` for `listeners` handles edge cases where an event name collides with an `Object.prototype` property (e.g., someone registers an event named `"constructor"` or `"toString"`). A plain object would silently read the prototype method instead of `undefined`. `Map` has no prototype — it is safe for arbitrary string keys.

**Architecture benefit:** Adding a 6th downstream service (e.g., `fraudService.flag()`) requires zero changes to `OrderService`. The service registers itself with the bus. This is the Open/Closed Principle in practice: `OrderService` is closed for modification but open for extension via the bus.

## Follow-up

**Q:** What happens if one listener throws? Does the order event reach the remaining listeners?
**A:** With the basic `forEach` implementation, a throwing listener stops all subsequent listeners in that `emit` call — the exception propagates up and the loop is aborted. In a payments/order pipeline this is critical: a non-critical analytics listener throwing must not prevent the restaurant notification from firing. Fix: wrap each `fn(...args)` in a `try/catch` inside `emit`. See the error-resilient emit pattern.

**Q:** This is an in-process event bus. What if OrderService and RestaurantService are separate microservices?
**A:** Then you need a real message broker — Redis Pub/Sub (fire-and-forget) or Kafka (persisted log with consumer groups for retries). The EventEmitter pattern applies only within a single Node.js process. Across services, the Observer becomes Pub/Sub with a broker in the middle.
