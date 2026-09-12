# Interview Guide: Low-Level Design of Inventory / Order Management System (Zepto/Quick-Commerce Style)

## 🗣️ The Interview Scenario

> "Design the backend low-level classes for a quick-commerce app like Zepto or Blinkit. A user should be able to browse products, add items to a cart, place an order that gets fulfilled by exactly one warehouse (never split across warehouses), see a generated invoice, and pay via UPI or card. The system runs many warehouses across different locations, and each warehouse manages its own inventory of product categories. Design the class diagram, including how a warehouse gets selected for a user, and walk me through the full order flow from browsing to payment."

This is a "build the whole domain model" question — the interviewer wants to see systematic requirement-gathering, sensible entity boundaries (Product vs. ProductCategory vs. Inventory), a pluggable strategy for warehouse selection, and a clean flow for cart → order → invoice → payment → inventory rollback on failure.

## 🏗️ Architect's Explanation (For a New Developer)

Picture a real quick-commerce warehouse. It doesn't store "3,847,201 individual physical items" as separate database rows with different prices — it groups identical items into **categories** (e.g., "500ml Coke bottle") and a customer just says "give me 3 of these," not "give me item #48213, #48214, #48215." That's the first big design insight in this lecture: **`ProductCategory` — not raw `Product` — is what the cart, the price, and the count actually revolve around.**

Second insight: a single order can never be split across two physical warehouses (you wouldn't want your ice cream from one warehouse and your milk from another, arriving separately) — so exactly **one warehouse must be selected** for the *entire* cart before checkout, using a pluggable **selection strategy** (nearest warehouse today, cheapest warehouse tomorrow — without rewriting the rest of the system).

Third insight: the object model separates "the catalog side" (Product → ProductCategory → Inventory → Warehouse) from "the transactional side" (User → Cart → Order → Invoice → Payment), connected only at the few points where they actually interact (checkout reduces inventory; a failed payment adds it back).

## 📊 Visualize It

**Class structure (catalog + inventory side):**
```
┌────────────┐        ┌──────────────────┐        ┌───────────┐        ┌────────────────────┐
│  Product   │ N────1 │  ProductCategory   │ N────1 │ Inventory │ 1────1 │     Warehouse       │
├────────────┤        ├──────────────────┤        ├───────────┤        ├────────────────────┤
│ productId  │        │ categoryId        │        │ list<     │        │ warehouseId          │
│ name       │        │ categoryName      │        │  Product  │        │ inventory            │
└────────────┘        │ list<Product>     │        │  Category>│        │ address (Address)    │
                       │ price  ◄──shared  │        └───────────┘        └──────────┬─────────┘
                       │        across all │                                        │ N
                       │        products   │                             ┌──────────▼─────────┐
                       │        in category│                             │ WarehouseController  │
                       └──────────────────┘                             │ - list<Warehouse>    │
                                                                          │ - WarehouseSelection  │
                                                                          │   Strategy            │
                                                                          │ + selectWarehouse()   │
                                                                          └──────────────────────┘
                                                            <<interface>> WarehouseSelectionStrategy
                                                                       + selectWarehouse(): Warehouse
                                                                       ▲
                                                            NearestWarehouseSelectionStrategy
```

**Transactional side (user, cart, order):**
```
┌──────────┐  1───1  ┌────────┐          ┌───────────────────┐
│   User   │─────────│  Cart  │          │  UserController     │
├──────────┤         ├────────┤          │ - list<User>        │
│ userId   │         │ Map<   │          └───────────────────┘
│ username │         │  categoryId,      
│ list<    │         │  count>│          Order-flow (place order → checkout):
│  orderId>│         └────────┘
└──────────┘
                                          ┌───────────────────────────────┐
                                          │             Order              │
                                          ├───────────────────────────────┤
                                          │ user, deliveryAddress          │
                                          │ Map<categoryId, count>         │
                                          │ warehouse (fulfilling WH)      │
                                          │ invoice: Invoice                │
                                          │ payment: Payment                │
                                          │ orderStatus: enum               │
                                          └───────────────────────────────┘
                                                     ▲ managed by
                                          ┌───────────────────────────────┐
                                          │        OrderController         │
                                          │ + placeOrder() / checkout()    │
                                          │ + getOrderByUser()              │
                                          └───────────────────────────────┘
```

**Runtime interaction sequence (happy path + failure path):**
```
User ─get─► UserController ─► User
User ─select WH─► WarehouseController ─(NearestStrategy)─► Warehouse
Warehouse ─show─► Inventory (categories + products)
User ─addToCart(categoryId, count)─► Cart
User ─placeOrder()─► OrderController ─creates─► Order (copies cart map + warehouse) + Invoice
User ─checkout()─►
   1. Warehouse.removeItemFromInventory(orderMap)   // reserve/deduct stock FIRST
   2. Payment.makePayment(UPI/Card)
        ├─ success ─► Cart.empty()
        └─ failure ─► Warehouse.addItemToInventory(orderMap)   // rollback stock
```

## 🔧 Deep Dive: How It Actually Works

### Step 1 — Identify the flow before the objects
The lecture explicitly walks the "happy path" first: **View Product → Add to Cart → Place Order (generates Invoice) → Payment/Checkout**. Every class in the model exists to support exactly one of these steps — this is the recommended interview approach: narrate the user journey before drawing boxes.

### Step 2 — `Product` and `ProductCategory` (and why price lives on the category, not the product)
```java
class Product {
    int productId;
    String productName;
}

class ProductCategory {
    int categoryId;
    String categoryName;
    List<Product> products;
    double price;              // ALL products in this category share one price
    void addProduct(Product p) { ... }
    void removeProduct(Product p) { ... }
}
```
Why: in a real app you never browse a wall of 10,000 identical single-item listings — you see *one* tile per category ("Coke 500ml") and pick a quantity. This also directly answers a natural follow-up: "how would you support per-brand or per-size categorization?" — answer: nested/filterable `ProductCategory` groupings.

### Step 3 — `Inventory` and `Warehouse`
```java
class Inventory {
    List<ProductCategory> productCategories;
    void addItemToInventory(...)
    void removeItemFromInventory(Map<Integer, Integer> categoryIdToCount) { ... }
}

class Warehouse {
    Inventory inventory;
    Address address;   // pinCode, city, state
}
```
`Inventory` is a plain aggregation of categories; `Warehouse` owns exactly one `Inventory` plus its physical `Address`.

### Step 4 — Multi-warehouse management and the selection Strategy pattern
```java
class WarehouseController {
    List<Warehouse> warehouses;
    void addWarehouse(Warehouse w) { ... }
}

interface WarehouseSelectionStrategy {
    Warehouse selectWarehouse(List<Warehouse> warehouses, /* user location, etc. */);
}
class NearestWarehouseSelectionStrategy implements WarehouseSelectionStrategy { ... }
```
The transcript explicitly flags this as a **Strategy pattern** insertion point — because *which* warehouse to pick can evolve (nearest today, cheapest tomorrow, load-balanced next quarter) without touching `WarehouseController`'s other responsibilities. This is a strong signal to call out explicitly in an interview: "I'm using Strategy here so warehouse-selection logic is swappable."

### Step 5 — `User` and `Cart`
```java
class User {
    int userId;
    String username;
    Cart cart;                 // one cart per user — 1:1 relationship
    List<Integer> orderIds;    // user only stores IDs, not full Order objects
}

class Cart {
    Map<Integer, Integer> categoryIdToCount;   // category selected -> quantity
    void addItem(int categoryId, int count) { ... }
    void removeItem(int categoryId) { ... }
    void emptyCart() { ... }
}
```
Key design call-out from the transcript: **`User` stores only `orderIds`, not full `Order` objects** — because `Order` is the "source of truth" object that already knows which user it belongs to; duplicating full order data on `User` would be redundant and risk going out of sync.

### Step 6 — `Order`, `Invoice`, `Payment`
```java
class Order {
    User user;
    Address deliveryAddress;
    Map<Integer, Integer> categoryIdToCount;   // copied from Cart at placeOrder time
    Warehouse warehouse;                       // the ONE warehouse fulfilling this order
    Invoice invoice;
    Payment payment;
    OrderStatus status;      // enum: PENDING, DELIVERED, CANCELLED, UNDELIVERED
}
class Invoice {
    double totalItemPrice;
    double totalTax;
    double finalPrice;
}
class Payment {
    PaymentMode mode;         // enum: UPI, CARD
    boolean makePayment();
}
class OrderController {
    List<Order> orders;
    Order placeOrder(User user, Warehouse warehouse) { ... }  // builds Order + generates Invoice
    void checkout(Order order) { ... }
}
```

### Step 7 — The `checkout()` sequence, including rollback
This is the most interview-relevant part of the deep dive:
1. `checkout()` first calls `warehouse.removeItemFromInventory(order.categoryIdToCount)` — **stock is deducted before payment succeeds**, to prevent overselling while payment is in flight.
2. Then `payment.makePayment(mode)` is invoked (UPI or Card).
3. **If payment succeeds** → `cart.emptyCart()`.
4. **If payment fails (or times out)** → `warehouse.addItemToInventory(order.categoryIdToCount)` — inventory is rolled back, restoring the deducted stock.

This deduct-before-pay-then-rollback-on-failure pattern is exactly the kind of edge case interviewers probe for — be ready to discuss race conditions here (see the incident below).

## 🔥 Real Production Incident & Fix

**What broke:** A quick-commerce clone (very similar in shape to this lecture's design) shipped with the "deduct inventory, then attempt payment, roll back on failure" flow implemented with **no locking around the inventory decrement**. During a flash sale, two customers in different app sessions both had "Coke 500ml (only 1 left)" in their carts and hit checkout within milliseconds of each other.

**How the team noticed:** Customer support tickets spiked ("I paid but my order says out of stock") and the on-call engineer found the smoking gun in the inventory audit log: the same `categoryId` had been decremented to `-1` — a negative stock count that should be structurally impossible.

**Root cause:** `Inventory.removeItemFromInventory()` did a plain read-check-then-write (`if (count >= requestedQty) count -= requestedQty;`) with no synchronization or atomic compare-and-swap. Both requests read `count = 1` *before either write happened*, both passed the check, and both decremented — a classic **race condition / lost-update bug**, invisible in local testing because it requires genuinely concurrent requests to manifest.

**The fix:** The team wrapped the check-and-decrement in a database-level atomic operation (`UPDATE inventory SET count = count - :qty WHERE category_id = :id AND count >= :qty`, checking the affected-row count) instead of an in-memory read-then-write, and added a compensating-transaction step so a payment failure re-credits inventory idempotently (keyed by `orderId`, so a retry can't double-credit).

```
BEFORE (race condition):                      AFTER (atomic, DB-level guard):
Thread A: read count=1                        UPDATE inventory
Thread B: read count=1                          SET count = count - 1
Thread A: count>=1 → write count=0               WHERE category_id = X AND count >= 1
Thread B: count>=1 → write count=0            → if 0 rows affected: reject checkout
  (both "succeed", stock goes to -1 logically)   → if 1 row affected: proceed to payment
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why does the cart store `categoryId → count` instead of a list of individual `Product` references?**
Because the user never selects a specific physical unit — they select "3 of this category" (e.g., "Coke 500ml"), and all items in a category share the same price. Storing individual `Product` references would force the system to arbitrarily pick *which* 3 physical units to reserve, which is unnecessary complexity the category abstraction avoids.

**Q2: What happens if a user's cart spans products that exist in Warehouse A but not Warehouse B, and the nearest warehouse doesn't have everything?**
This is exactly why warehouse selection happens *before* browsing/adding to cart in this design — the user only ever sees inventory belonging to the one warehouse already selected for them, so a cart can never reference a category unavailable in that warehouse. A valid follow-up design extension: if the nearest warehouse lacks a category, the `WarehouseSelectionStrategy` could be enhanced to consider stock availability, not just distance.

**Q3: Why is `Order` given a full `Warehouse` reference instead of just a `warehouseId`?**
Either works, but keeping the object reference (or ID, resolved via `WarehouseController`) lets the checkout flow directly call `warehouse.removeItemFromInventory(...)` without an extra lookup. In a real system you'd likely store the ID for persistence and hydrate the object at read time — call this trade-off out explicitly to show you understand persistence vs. in-memory object graphs.

**Q4: How would you extend this design to support partial order fulfillment (e.g., backorder one item, ship the rest)?**
You'd need to break the "one order = one warehouse" invariant, which is a significant redesign: introduce a `Shipment` or `Fulfillment` entity between `Order` and `Warehouse` (one order → many shipments, each tied to one warehouse), and move inventory-deduction logic to the shipment level instead of the order level.

**Q5: Where would you add idempotency to prevent double-charging if the payment gateway callback is retried?**
Attach an idempotency key (e.g., `orderId` + attempt number) to the `Payment.makePayment()` call and have `OrderController` check `order.status` before re-processing — if `payment.status == SUCCESS` already, a duplicate callback should be a no-op rather than triggering a second charge or second inventory rollback.

**Q6: Why is `Invoice` a separate class instead of just fields on `Order`?**
Separating `Invoice` keeps tax/pricing computation logic isolated and reusable (e.g., regenerating an invoice PDF, or supporting invoice amendments/credit notes later) without bloating the `Order` class, and mirrors how real systems often persist invoices as independently queryable/auditable financial records.

## 🔑 Key Takeaway
The core LLD insight here is modeling around **categories, not individual products**, enforcing **one order = one warehouse** via a pluggable selection Strategy, and treating checkout as a two-phase sequence (deduct inventory → attempt payment → roll back on failure) — say this sequence out loud, since it's the part interviewers dig into most.
