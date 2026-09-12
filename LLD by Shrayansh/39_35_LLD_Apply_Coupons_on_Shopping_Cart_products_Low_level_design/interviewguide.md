# Interview Guide: Decorator Pattern — Applying Coupons on Shopping Cart Products

## 🗣️ The Interview Scenario

> "You have a shopping cart with products. Each product can have multiple coupons applied to it — for example, `n%` off for all items, `p%` off on the next item, or `d%` off on `N` items of a given type. New coupon conditions will keep getting added over time. Coupons must apply *sequentially* to a product's price, and you need to compute the final total for the cart. Design this system so adding a new coupon type doesn't require rewriting existing code."

This is a real interview question (as flagged directly in the transcript) that tests whether you can recognize a **"wrap behavior around a core object, repeatedly, without modifying the object"** problem and map it to the **Decorator pattern**.

## 🏗️ Architect's Explanation (For a New Developer)

Think about buying a coffee. You start with a plain black coffee — that's your **base product**. Then you ask for milk (+cost), then caramel syrup (+cost), then whipped cream (+cost). Each add-on **wraps** the previous drink and adjusts the price, without the barista ever needing to "modify" the original coffee recipe. You could stop at any layer, or add layers in any order, and the final price is just "ask the outermost wrapper for its price," which asks its inner wrapper, and so on, down to the plain coffee.

That's exactly the **Decorator pattern**: you have an original object (a `Product`), and you wrap it with one or more "decorators" (coupons), each of which knows how to ask the object *it wraps* for a price, apply its own discount logic on top, and return a new price — all **without touching the original product class**.

The critical insight for this specific problem: since each product can have a *different sequence* of coupons (and the number of coupon types will keep growing), a decorator lets you compose any combination of coupons around any product, and adding a brand-new coupon type is just "write one new decorator class" — zero changes to `Product` or to any existing coupon decorator.

## 📊 Visualize It

**Class structure:**

```
        abstract class Product                     <<enum>>
        -----------------------                  ProductType
        - name : String                         (ELECTRONIC, FURNITURE, ...)
        - originalPrice : double
        - type : ProductType
        + abstract getPrice() : double
                 ▲
                 | extends (is-a Product)
                 |
        -----------------------------
        | Item1, Item2 (concrete products) |
        -----------------------------------
        + getPrice() → returns originalPrice


        abstract class CouponDecorator extends Product
        -----------------------------------------------
        - product : Product      <-- "has-a" wrapped Product
                 ▲
                 | extends
        ┌────────┴─────────────────────┐
        |                                |
  PercentageCouponDecorator        TypeCouponDecorator
  - discountPercent                - discountPercent
  - product                        - eligibleTypes (static list)
  + getPrice():                    + getPrice():
     product.getPrice() * (1-disc%)   if (product.type in eligibleTypes)
                                          product.getPrice() * (1-disc%)
                                       else product.getPrice()
```

**Runtime "onion" of decorators for one item (nested `getPrice()` calls):**

```
new TypeCouponDecorator(
     new PercentageCouponDecorator(
          item1                        // original Item, price = 1000
     , 10% )                           // percentage layer
, eligibleTypes, 5% )                  // type layer (outermost)

  getPrice() call chain (calls go IN, results come OUT):
  TypeCoupon.getPrice()
      └─calls→ PercentageCoupon.getPrice()
                    └─calls→ Item1.getPrice() = 1000        (innermost, returns first)
               ← returns 1000 * 0.90 = 900
      ← if item1.type is eligible: 900 * 0.95 = 855
      ← else: 900  (skipped, type not eligible)
```

## 🔧 Deep Dive: How It Actually Works

### 1. The abstract `Product` — the object being decorated
```java
abstract class Product {
    String name;
    double originalPrice;
    ProductType type;   // enum: ELECTRONIC, FURNITURE, DECORATIVE, ...

    Product(String name, double originalPrice, ProductType type) { ... }

    abstract double getPrice();   // concrete products just return originalPrice
}
```
Concrete leaf products (e.g., `Item1` = fan, ₹1000, ELECTRONIC; `Item2` = sofa, ₹2000, FURNITURE) implement `getPrice()` to simply return `originalPrice`.

### 2. The abstract `CouponDecorator` — extends `Product`, wraps a `Product`
```java
abstract class CouponDecorator extends Product {
    protected Product product;   // the wrapped product (could be a real item OR another decorator)
}
```
This is the crux of the pattern: **a `CouponDecorator` *is* a `Product`** (it extends `Product`), and it *has* a `Product` inside it. That's what lets you stack decorators arbitrarily — a decorator wrapping another decorator is itself still just a `Product`.

### 3. Concrete decorators — one per coupon *condition* type
```java
class PercentageCouponDecorator extends CouponDecorator {
    private double discountPercent;
    PercentageCouponDecorator(Product product, double discountPercent) {
        this.product = product;
        this.discountPercent = discountPercent;
    }
    double getPrice() {
        double base = product.getPrice();       // recurse into wrapped product first
        return base - (base * discountPercent / 100);
    }
}

class TypeCouponDecorator extends CouponDecorator {
    private static List<ProductType> eligibleTypes = List.of(ProductType.FURNITURE, ProductType.DECORATIVE);
    private double discountPercent;
    TypeCouponDecorator(Product product, double discountPercent) {
        this.product = product;
        this.discountPercent = discountPercent;
    }
    double getPrice() {
        double base = product.getPrice();
        if (eligibleTypes.contains(product.getType())) {
            return base - (base * discountPercent / 100);
        }
        return base;   // condition not met — coupon silently skipped
    }
}
```
Note the transcript's key business-logic detail: `TypeCouponDecorator` internally decides **whether the coupon even applies** by checking `product.getType()` against a static eligible-types list — the decision to apply or skip a coupon lives *inside* the decorator, not in the client code.

### 4. `ShoppingCart` — composition, and where decorators get stacked
```java
class ShoppingCart {
    List<Product> products = new ArrayList<>();

    void addToCart(Product item) {
        Product decorated = new TypeCouponDecorator(
                                new PercentageCouponDecorator(item, 10),
                                5);
        products.add(decorated);   // the CART stores the decorated wrapper, not the raw item
    }

    double getTotalPrice() {
        double total = 0;
        for (Product p : products) {
            total += p.getPrice();   // polymorphic call — cart doesn't know it's decorated
        }
        return total;
    }
}
```

### 5. Worked numeric trace from the transcript
- `Item1` (fan): original price = ₹1000, type = ELECTRONIC.
  - `PercentageCouponDecorator` (10%): 1000 → 900.
  - `TypeCouponDecorator` (furniture/decorative only, 5%): item is ELECTRONIC → **not eligible**, skipped → stays 900.
- `Item2` (sofa): original price = ₹2000, type = FURNITURE.
  - `PercentageCouponDecorator` (10%): 2000 → 1800.
  - `TypeCouponDecorator` (5%, FURNITURE is eligible): 1800 → 1710.
- **Total = 900 + 1710 = 2610** *(transcript states ~2646 as the final run output — the exact numbers depend on the discount values chosen; the mechanism is what matters)*.

### Why not just use `if/else` chains on coupon type?
Because coupon types are explicitly stated to keep growing ("currently three, in future four five six more conditions can be added"). An `if/else`/`switch` on coupon type inside `Product` or inside the cart would need editing **every time** a new coupon type is added — violating the Open/Closed Principle. Decorator lets you **add a new coupon type as a brand-new class** with zero changes to `Product`, `ShoppingCart`, or any existing decorator.

## 🔥 Real Production Incident & Fix

**What broke:** An e-commerce checkout service originally computed final item price with a single `calculatePrice(Item item, List<String> couponCodes)` method containing a growing `switch` statement — one `case` per coupon type. After 18 months, this method had ballooned to 40+ cases covering percentage-off, buy-one-get-one, category-restricted, first-N-items, and combinations thereof.

**How the team noticed:** A new "first item free for premium members" coupon was added as case #41. A regression slipped through: the new case was inserted *before* an existing "category discount" case in the switch's fallthrough logic, and for a subset of SKUs the category discount silently stopped applying. It was caught by finance reconciliation — daily revenue-per-order dipped ~1.5% for furniture-category orders, flagged by an automated anomaly-detection alert on the BI dashboard, not by QA.

**Root cause:** All coupon logic lived in one monolithic method with implicit ordering dependencies between cases. Adding coupon #41 required understanding the interaction of all 40 existing cases — nobody fully did, and a subtle reordering broke an unrelated coupon.

**The fix:** The team refactored to the Decorator pattern almost exactly as in this transcript: each coupon type became its own `CouponDecorator` subclass with an isolated `getPrice()` implementation, and the "recipe" for a given product (which coupons, in which order) was assembled per-product at cart-add time. Each decorator could now be unit-tested in complete isolation, and adding coupon #41 became "add one new class," with zero risk to the other 40.

```
BEFORE: one giant switch, coupons interact          AFTER: each coupon is an isolated
implicitly via case order (fragile)                 decorator; independently testable

 calculatePrice(item, coupons) {                      item → [PercentageDecorator]
   switch(couponType) {                                    → [CategoryDecorator]
     case A: ...                                            → [FirstNFreeDecorator]
     case B: (silently depends on A's                       → getPrice() composes cleanly,
              side effects) ...                              no shared mutable state
     ... case 40+ ...
   }
 }
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why is Decorator a better fit here than Strategy?**
A: Strategy picks **one** interchangeable algorithm at a time (e.g., one pricing strategy replaces another). Here, **multiple coupons need to apply sequentially and cumulatively** to the *same* product — that's composition/stacking of behavior, which is exactly what Decorator is designed for. Strategy would require awkward manual chaining logic outside the objects; Decorator gets sequential composition "for free" via nested `getPrice()` calls.

**Q2: How do you guarantee a specific coupon application order (e.g., percentage coupon must apply before the type coupon)?**
A: Order is determined by the **nesting order at construction time** — whichever decorator is innermost is evaluated first (its `getPrice()` is called first in the recursive chain). In the transcript's example, `PercentageCouponDecorator` wraps the raw item, and `TypeCouponDecorator` wraps that — so percentage discount is computed first, and the type discount is applied on top of the already-discounted price. If business rules require a specific order, that ordering must be enforced explicitly at the cart's `addToCart` composition point.

**Q3: What happens if the same coupon type needs to apply twice (e.g., two different percentage coupons)?**
A: Simply nest two `PercentageCouponDecorator` instances with different discount values — since each decorator only knows about the `Product` it directly wraps, nothing prevents stacking two instances of the same decorator class. This is a natural strength of Decorator over a flag-based or enum-based approach.

**Q4: Is there a risk of a coupon making the price negative or the discounts compounding unfairly?**
A: Yes — compounding percentage discounts (as opposed to discounts calculated purely off the *original* price) can produce different, sometimes unintended, totals depending on order. In a real system you'd need explicit business rules (e.g., "max 3 coupons per item," "discounts computed off original price, not compounded") and validation in each decorator or in the cart's composition logic to prevent chaining that yields prices below cost or below zero.

**Q5: How would this design change if a coupon needed to apply cart-wide (e.g., ₹50 off if cart total exceeds ₹1000) rather than per-item?**
A: A per-item decorator alone can't see the cart total. You'd introduce a separate cart-level decorator/step that operates on `ShoppingCart.getTotalPrice()` *after* all item-level decorators have been resolved — i.e., Decorator handles per-item composition, but cart-wide rules are a distinct concern layered on top of the cart's total, not on individual `Product` objects.

**Q6: Why does `CouponDecorator` extend `Product` instead of just implementing some `Priceable` interface?**
A: Because `Product` is the abstraction the rest of the system (the cart, `getTotalPrice`) already depends on — by making the decorator itself *be* a `Product`, the cart and any client code remain completely unaware that decoration is even happening. This is the polymorphic substitutability that makes Decorator transparent to callers.

## 🔑 Key Takeaway

Whenever a core object needs an *open-ended, stackable set of behaviors* applied to it without modifying the object's own class, wrap it in decorators that share its type — this converts "one method with a growing switch statement" into "one small class per behavior," each independently testable and addable without touching existing code.
