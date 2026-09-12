# Food Delivery (Zomato/Swiggy) — Complete LLD Interview Guide

**Interview Duration: 50 min | Difficulty: Hard | Must-Know: ⭐⭐⭐⭐⭐ | 15-YOE Focus: Order State Machine + Delivery Assignment + Restaurant Acceptance Timeout**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │               FOOD DELIVERY SYSTEM                              │
 │                                                                  │
 │  CUSTOMER            PLATFORM              RESTAURANT  DELIVERY  │
 │  ┌────────┐         ┌───────────────────┐ ┌────────┐ ┌───────┐ │
 │  │Browse  │         │  Order Service    │ │Accept/ │ │IDLE   │ │
 │  │Add Cart│────────►│  Pricing Engine   │►│Reject  │ │ON_WAY │ │
 │  │Place   │         │  Assign Delivery  │ │Prepare │ │DELIVER│ │
 │  │Track   │◄────────│  Track Location   │ └────────┘ └───────┘ │
 │  └────────┘         └───────────────────┘                       │
 │                                                                  │
 │  ORDER STATE MACHINE:                                           │
 │  [PLACED]─restaurant accepts─►[CONFIRMED]                       │
 │     │                              │                            │
 │  timeout/reject               preparing                         │
 │     │                              │                            │
 │  [CANCELLED]            [BEING_PREPARED]                        │
 │                                    │                            │
 │                          delivery partner                        │
 │                          assigned + picked                      │
 │                                    │                            │
 │                         [OUT_FOR_DELIVERY]                      │
 │                                    │                            │
 │                            delivered                            │
 │                                    │                            │
 │                            [DELIVERED]                          │
 │                                                                  │
 │  DELIVERY ASSIGNMENT SCORING:                                   │
 │  ┌──────────────────────────────────────────────────────────┐  │
 │  │  Score = 0.5×distance + 0.3×(1-rating) + 0.2×activeOrders│ │
 │  │  Lowest score = best delivery partner                     │  │
 │  │  Only IDLE partners within 5km of restaurant considered   │  │
 │  └──────────────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Let me clarify.

Functional:
- Customer browses restaurants by location → views menus → adds to cart → places order
- Restaurant receives order notification and has 3 minutes to accept or reject
- If rejected or timeout: cancel order + refund
- On acceptance: system finds nearest available delivery partner
- Delivery partner lifecycle: IDLE → assigned → picked up food → delivered
- Real-time tracking: customer sees delivery partner's location on map
- Ratings: customer rates food + delivery after order completes

Non-functional:
- Restaurant acceptance is time-critical: 3-minute window
- Delivery assignment: must assign within 2 minutes of restaurant acceptance
- Location updates: delivery partner sends GPS every 10 seconds
- Peak load: 12-2pm and 7-9pm — 100x normal traffic

Key design challenges:
1. Order state machine with multiple actors (customer, restaurant, delivery partner)
2. Restaurant acceptance timeout — what happens if they don't respond?
3. Delivery partner assignment — similar to ride sharing but with food readiness timing"

---

### Phase 3 — Implementation

```java
// ─── Order State ─────────────────────────────────────────────────
public enum OrderStatus {
    PLACED, CONFIRMED, BEING_PREPARED, READY_FOR_PICKUP,
    PARTNER_ASSIGNED, OUT_FOR_DELIVERY, DELIVERED, CANCELLED
}

// ─── Cart Item ────────────────────────────────────────────────────
public record CartItem(String menuItemId, String name, double price, int quantity) {
    public double total() { return price * quantity; }
}

// ─── Order ───────────────────────────────────────────────────────
public class Order {
    private final String      orderId;
    private final String      customerId;
    private final String      restaurantId;
    private final List<CartItem> items;
    private volatile OrderStatus status;
    private String            deliveryPartnerId;
    private final double      totalAmount;
    private final double      deliveryFee;
    private Location          deliveryAddress;
    private final Instant     placedAt;
    private Instant           estimatedDeliveryTime;

    public Order(String customerId, String restaurantId, List<CartItem> items,
                 double deliveryFee, Location deliveryAddress) {
        this.orderId         = UUID.randomUUID().toString();
        this.customerId      = customerId;
        this.restaurantId    = restaurantId;
        this.items           = Collections.unmodifiableList(new ArrayList<>(items));
        this.totalAmount     = items.stream().mapToDouble(CartItem::total).sum();
        this.deliveryFee     = deliveryFee;
        this.deliveryAddress = deliveryAddress;
        this.status          = OrderStatus.PLACED;
        this.placedAt        = Instant.now();
    }

    public synchronized boolean transitionTo(OrderStatus newStatus) {
        boolean valid = isValidTransition(this.status, newStatus);
        if (valid) this.status = newStatus;
        return valid;
    }

    private boolean isValidTransition(OrderStatus from, OrderStatus to) {
        return switch (from) {
            case PLACED          -> to == OrderStatus.CONFIRMED || to == OrderStatus.CANCELLED;
            case CONFIRMED       -> to == OrderStatus.BEING_PREPARED || to == OrderStatus.CANCELLED;
            case BEING_PREPARED  -> to == OrderStatus.READY_FOR_PICKUP;
            case READY_FOR_PICKUP-> to == OrderStatus.PARTNER_ASSIGNED;
            case PARTNER_ASSIGNED-> to == OrderStatus.OUT_FOR_DELIVERY;
            case OUT_FOR_DELIVERY-> to == OrderStatus.DELIVERED;
            default              -> false;
        };
    }

    public String getOrderId()      { return orderId; }
    public String getRestaurantId() { return restaurantId; }
    public String getCustomerId()   { return customerId; }
    public OrderStatus getStatus()  { return status; }
    public double getTotalAmount()  { return totalAmount; }
    public double getDeliveryFee()  { return deliveryFee; }
    public Location getDeliveryAddress() { return deliveryAddress; }
    public void setDeliveryPartnerId(String id) { this.deliveryPartnerId = id; }
    public void setEstimatedDelivery(Instant time) { this.estimatedDeliveryTime = time; }
}

// ─── Delivery Partner ─────────────────────────────────────────────
public class DeliveryPartner {
    public enum Status { IDLE, ASSIGNED, PICKED_UP, OFFLINE }

    private final String   partnerId;
    private volatile Location location;
    private volatile Status  status;
    private volatile int    activeOrders;  // for multi-order delivery
    private double           rating;

    public DeliveryPartner(String partnerId) {
        this.partnerId    = partnerId;
        this.status       = Status.IDLE;
        this.activeOrders = 0;
        this.rating       = 5.0;
    }

    public synchronized boolean assign() {
        if (status != Status.IDLE) return false;
        status = Status.ASSIGNED;
        activeOrders++;
        return true;
    }

    public synchronized void pickupFood()  { status = Status.PICKED_UP; }
    public synchronized void delivered() {
        activeOrders = Math.max(0, activeOrders - 1);
        status = activeOrders == 0 ? Status.IDLE : Status.PICKED_UP;
    }

    public String   getPartnerId()  { return partnerId; }
    public Location getLocation()   { return location; }
    public Status   getStatus()     { return status; }
    public double   getRating()     { return rating; }
    public int      getActiveOrders() { return activeOrders; }
    public void updateLocation(Location loc) { this.location = loc; }
}

// ─── Order Service ────────────────────────────────────────────────
public class OrderService {
    private final Map<String, Order>           orders   = new ConcurrentHashMap<>();
    private final Map<String, DeliveryPartner> partners = new ConcurrentHashMap<>();
    private final Map<String, Restaurant>      restaurants = new ConcurrentHashMap<>();
    private final NotificationService          notifier;
    private final PaymentService               paymentService;
    private final ScheduledExecutorService     scheduler =
        Executors.newScheduledThreadPool(8);

    public OrderService(NotificationService notifier, PaymentService payment) {
        this.notifier       = notifier;
        this.paymentService = payment;
    }

    // ─── Place Order ─────────────────────────────────────────────
    public Order placeOrder(String customerId, String restaurantId,
                             List<CartItem> items, Location deliveryAddress) {
        Restaurant restaurant = restaurants.get(restaurantId);
        if (restaurant == null) throw new IllegalArgumentException("Restaurant not found");
        if (!restaurant.isOpen())
            throw new IllegalStateException("Restaurant is currently closed");

        double deliveryFee = calculateDeliveryFee(restaurant.getLocation(), deliveryAddress);
        Order order = new Order(customerId, restaurantId, items, deliveryFee, deliveryAddress);
        orders.put(order.getOrderId(), order);

        // Hold payment
        paymentService.hold(customerId, order.getTotalAmount() + deliveryFee);

        // Notify restaurant
        notifier.notifyRestaurant(restaurantId, "New order: " + order.getOrderId());

        // 3-minute acceptance timeout
        scheduler.schedule(() -> handleRestaurantTimeout(order),
            3, TimeUnit.MINUTES);

        System.out.println("Order placed: " + order.getOrderId());
        return order;
    }

    // ─── Restaurant Accepts ──────────────────────────────────────
    public void restaurantAccept(String orderId, int estimatedPrepMinutes) {
        Order order = getOrder(orderId);
        if (!order.transitionTo(OrderStatus.CONFIRMED))
            throw new IllegalStateException("Cannot confirm order in state: " + order.getStatus());

        // Confirm payment hold
        paymentService.capture(order.getCustomerId(),
            order.getTotalAmount() + order.getDeliveryFee());

        notifier.notifyCustomer(order.getCustomerId(),
            "Your order is confirmed! Estimated delivery: " + (estimatedPrepMinutes + 25) + " min");

        order.transitionTo(OrderStatus.BEING_PREPARED);
        // Pre-assign delivery partner slightly before food is ready
        int assignAt = Math.max(1, estimatedPrepMinutes - 5);
        scheduler.schedule(() -> assignDeliveryPartner(order),
            assignAt, TimeUnit.MINUTES);
    }

    // ─── Restaurant Rejects ─────────────────────────────────────
    public void restaurantReject(String orderId, String reason) {
        Order order = getOrder(orderId);
        order.transitionTo(OrderStatus.CANCELLED);
        paymentService.release(order.getCustomerId(),
            order.getTotalAmount() + order.getDeliveryFee());
        notifier.notifyCustomer(order.getCustomerId(),
            "Sorry, restaurant rejected your order: " + reason + ". Full refund issued.");
    }

    private void handleRestaurantTimeout(Order order) {
        if (order.getStatus() == OrderStatus.PLACED) {
            restaurantReject(order.getOrderId(), "Restaurant did not respond in time");
        }
    }

    // ─── Assign Delivery Partner ──────────────────────────────────
    private void assignDeliveryPartner(Order order) {
        Restaurant restaurant = restaurants.get(order.getRestaurantId());
        Optional<DeliveryPartner> best = findBestPartner(restaurant.getLocation());

        if (best.isEmpty()) {
            // No partner available — retry in 1 minute
            System.out.println("No partner found. Retrying in 60s for order " + order.getOrderId());
            scheduler.schedule(() -> assignDeliveryPartner(order), 60, TimeUnit.SECONDS);
            return;
        }

        DeliveryPartner partner = best.get();
        boolean assigned = partner.assign();
        if (!assigned) {
            // Race condition — try again
            assignDeliveryPartner(order);
            return;
        }

        order.setDeliveryPartnerId(partner.getPartnerId());
        order.transitionTo(OrderStatus.PARTNER_ASSIGNED);
        notifier.notifyPartner(partner.getPartnerId(),
            "Pickup from: " + restaurant.getName() + " for order " + order.getOrderId());
        notifier.notifyCustomer(order.getCustomerId(),
            "Delivery partner assigned: " + partner.getPartnerId());
    }

    private Optional<DeliveryPartner> findBestPartner(Location restaurantLoc) {
        return partners.values().stream()
            .filter(p -> p.getStatus() == DeliveryPartner.Status.IDLE)
            .filter(p -> p.getLocation() != null)
            .filter(p -> p.getLocation().distanceKm(restaurantLoc) <= 5.0)
            .min(Comparator.comparingDouble(p -> partnerScore(p, restaurantLoc)));
    }

    private double partnerScore(DeliveryPartner p, Location restaurantLoc) {
        return 0.5 * p.getLocation().distanceKm(restaurantLoc)
             + 0.3 * (5.0 - p.getRating())
             + 0.2 * p.getActiveOrders();
    }

    // ─── Delivery events ─────────────────────────────────────────
    public void partnerPickedUp(String orderId) {
        Order order = getOrder(orderId);
        order.transitionTo(OrderStatus.OUT_FOR_DELIVERY);
        DeliveryPartner partner = partners.get(order.getDeliveryPartnerId());
        if (partner != null) partner.pickupFood();
        notifier.notifyCustomer(order.getCustomerId(),
            "Your order is on its way!");
    }

    public void orderDelivered(String orderId) {
        Order order = getOrder(orderId);
        order.transitionTo(OrderStatus.DELIVERED);
        DeliveryPartner partner = partners.get(order.getDeliveryPartnerId());
        if (partner != null) partner.delivered();
        notifier.notifyCustomer(order.getCustomerId(),
            "Order delivered! Please rate your experience.");
    }

    private double calculateDeliveryFee(Location restaurant, Location delivery) {
        double distKm = restaurant.distanceKm(delivery);
        return distKm <= 3 ? 20.0 : 20.0 + (distKm - 3) * 8.0; // ₹20 base + ₹8/km beyond 3km
    }

    private Order getOrder(String orderId) {
        Order o = orders.get(orderId);
        if (o == null) throw new IllegalArgumentException("Order not found: " + orderId);
        return o;
    }

    public void addRestaurant(Restaurant r) { restaurants.put(r.getRestaurantId(), r); }
    public void addPartner(DeliveryPartner p) { partners.put(p.getPartnerId(), p); }
}
```

---

## Component Choices

```
COMPONENT               CHOICE                 WHY
──────────────────────────────────────────────────────────────────────
Order state transitions  Synchronized method   Multiple actors (customer,
                                               restaurant, partner) can
                                               trigger transitions concurrently.
                                               Only valid transitions allowed.

Restaurant timeout       ScheduledExecutorService 3-min auto-cancel.
                                               Non-blocking. Partner
                                               assigned proactively 5min
                                               before food is ready.

Delivery fee             Distance-based        ₹20 base + ₹8/km beyond 3km.
                                               Transparent to customer.
                                               Varies by distance only.

Partner assignment       Optimistic + retry    partner.assign() is atomic.
race condition           on failure            If two orders compete:
                                               only one wins, other retries.

Multi-order delivery     activeOrders counter  Partner can carry multiple
                                               orders in one trip.
                                               Only goes IDLE when 0 orders.

Payment hold-and-capture Pre-auth + capture    Hold on place, capture on
                                               confirmation. Release on
                                               cancel. No money taken
                                               until confirmed.
```

---

## Senior Trap Questions

**Q1: "What if food is ready but no delivery partner is available for 30 minutes?"**
```
Food quality degrades. Customer experience suffers.
Options:

1. Dynamic incentives: increase payout for this order to attract partners.
   System: mark order as "high priority", increase earnings by 20%.
   Partners see high-priority orders first in their app.

2. Widen search radius: start at 3km, expand to 5km, 8km, 10km over time.
   Tradeoff: longer wait for partner to arrive.

3. Notify customer: "Partner not yet assigned. Your food is being kept warm."
   Better than silence — manages expectations.

4. Restaurant SLA: if this happens frequently for a restaurant (bad location):
   flag restaurant for review — consider requiring dark kitchen partnerships.

5. Cancel and refund: after 30 min without partner → cancel with full refund.
   Last resort. Better to widen radius and incentivize.
```

**Q2: "Customer orders from Restaurant A and Restaurant B simultaneously (multi-restaurant cart). How do you handle this?"**
```
Most platforms don't support multi-restaurant orders (complexity too high).
If they did:

Option 1: Separate orders, separate deliveries
  Two orders, two delivery partners, two delivery windows.
  Simple. Customer pays two delivery fees.
  Items arrive at different times.

Option 2: Batch pickup (one partner picks up from both)
  Partner picks from A first (closer), then B, then delivers.
  ETA must account for both pickups + travel.
  Harder: timing coordination (both restaurants must be ready at similar times).
  
Production (Swiggy Genie): treats it as two orders with optional batching
at the delivery partner level when restaurants are close together.
```

**Q3: "Order placed but payment gateway times out. Is the order placed or not?"**
```
The payment hold needs to be atomic with order creation.
If hold fails: order is NOT placed (no order without payment hold).
If hold succeeds, order saved, then app crashes:
  On restart: check orders with PLACED status + no payment hold record.
  These are orphaned orders → auto-cancel them.

Implementation:
  1. payment.hold() first
  2. If hold fails → throw exception, no order created
  3. If hold succeeds → create order
  4. If crash after step 3: reconciliation job finds PLACED orders with
     no capture/release → release the hold → cancel order
  
Idempotency key: hold(customerId, amount, orderId) — if order already has a hold,
don't double-charge on retry.
```

---

## Failure Modes

```
SCENARIO              WHAT HAPPENS             FIX
────────────────────────────────────────────────────────────────────
Restaurant app         3-min timer fires,       Auto-cancel + refund.
crashes/offline        order auto-cancelled     Notify customer.
                                               Platform calls restaurant
                                               on phone for critical cases.

Partner GPS lost       Location stale, can't   Last location used for 5 min.
                       track order             After 5 min: partner marked
                                               OFFLINE. Re-assign order.

Customer not home,     Partner can't deliver   Partner waits 5 min at door.
partner waits                                  Marks as DELIVERY_ATTEMPTED.
                                               Tries 2 more times.
                                               After 3 fails: order returned,
                                               partial refund (food cost, not
                                               delivery fee).

Payment capture        Partner delivered,       Retry capture 3x.
fails after delivery   platform not paid       Manual reconciliation queue.
                                               Platform absorbs the loss
                                               and resolves with payment GW.
```

---

## Interview Cheat Sheet

> "Food delivery is a multi-actor state machine problem. The Order entity transitions through states driven by different actors — customer places it, restaurant confirms or rejects it, platform assigns a delivery partner, partner picks up and delivers it. Each transition is synchronized and validates against allowed transitions. The restaurant acceptance timeout is implemented with ScheduledExecutorService — 3 minutes to accept, then auto-cancel + refund. Payment uses hold-and-capture: hold on order placement, capture on restaurant acceptance, release on cancellation — this prevents charging for rejected orders. Delivery partner assignment is similar to ride sharing: score by distance + rating + active orders, assign() is atomic to prevent race conditions. The hardest production scenario is 'no partners available' — solve with dynamic earnings incentives, radius expansion, and eventual order cancellation with full refund after a maximum wait."
