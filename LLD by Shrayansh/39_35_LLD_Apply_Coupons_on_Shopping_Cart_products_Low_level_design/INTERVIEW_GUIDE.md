# 🛒 Shopping Cart Coupons - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## **Design Pattern Used**: Strategy Pattern (for discount types) + Chain of Responsibility (for coupon stacking rules)

**Interviewer**: "Design a coupon system for a shopping cart - support percentage discounts, flat discounts, BOGO (buy-one-get-one), and combinations."

**You**: "Great question! Core insight: **Different coupon types have fundamentally different calculation logic, but the cart shouldn't care about the specifics - just needs a common `applyDiscount()` interface. This is Strategy Pattern.** Additionally, if multiple coupons can apply, we need rules for ORDER of application and stacking limits - that's where Chain of Responsibility helps."

### ⚖️ Strategy vs Decorator: Two Valid Answers to This Question

**Interviewer**: "I've also seen this solved with Decorator Pattern - wrapping the product with `CouponDecorator` classes that chain (`TypeCoupon(PercentageCoupon(item))`). Is that wrong?"

**You**: "Not wrong at all - it's a legitimate alternative, and honestly a very elegant one for this specific problem. Both solve 'apply N coupons to a price' - they just organize the computation differently:

```java
// STRATEGY APPROACH (this guide): Cart owns a list of strategies, applies them in a loop
double finalPrice = cart.getTotal();
for (DiscountStrategy strategy : appliedStrategies) {
    finalPrice -= strategy.calculateDiscount(cart, coupon);
}

// DECORATOR APPROACH: Each coupon WRAPS the product, price computed via recursive delegation
Product priced = new Item1("Fan", 1000, ELECTRONIC);
priced = new PercentageCouponDecorator(priced, 10);      // wraps item
priced = new TypeCouponDecorator(priced, 5, ELECTRONIC); // wraps the wrapper
priced.getPrice();  // recurses inward: Item -> Percentage -> Type
```

**When I'd pick Strategy (this guide's approach)**:
- Coupons apply to the **cart/order total**, not to individual product instances
- I need a validation **pipeline** before applying anything (expiry, min-cart-value, stackability) - Chain of Responsibility slots in naturally
- I want to easily answer 'what coupons are currently applied and in what order' without walking a wrapper chain

**When Decorator is the better fit**:
- Coupons are conceptually **per-item wrappers** (e.g., 'this specific Fan has a 10% + 5% coupon applied', tracked per product instance)
- I want the SAME object (`Product`) to represent both a plain item and a discounted item polymorphically - `ShoppingCart` just stores `List<Product>` and calls `getPrice()`, no `if (hasDiscount)` branching anywhere
- Order of discount application is a first-class part of the design (decorator nesting order = application order, made explicit in code rather than a separate 'ordering' field)

**Senior-level answer if asked which is 'more correct'**: *"Both are correct engineering choices - I'd choose Strategy when discounts are cart-level financial rules with cross-cutting validation, and Decorator when discounts are best modeled as composable per-item wrappers. If the interviewer has a preference, I'd ask: 'Do coupons apply to the whole cart or per product line?' - that answer usually decides it for me."*

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│               SHOPPING CART COUPON ARCHITECTURE                      │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   SHOPPING CART   │
                    │                  │
                    │  items: List<Item>│
                    │  appliedCoupons[] │
                    │  totalPrice       │
                    └────────┬─────────┘
                             │
                             ▼
              ┌──────────────────────┐
              │   DiscountStrategy     │  ◄── Interface
              │     (interface)        │
              │                        │
              │  apply(cart): Discount │
              │  isApplicable(cart)     │
              └───────────┬────────────┘
                          │
        ┌─────────────────┼─────────────────┬──────────────────┐
        ▼                 ▼                 ▼                  ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ PERCENTAGE     │ │  FLAT AMOUNT   │ │     BOGO       │ │  CATEGORY      │
│  DISCOUNT      │ │   DISCOUNT     │ │  (Buy1Get1)    │ │  SPECIFIC      │
│               │ │               │ │               │ │               │
│ 10% off total │ │ ₹100 off if   │ │ Cheapest item │ │ 20% off all   │
│               │ │ cart > ₹500   │ │  free          │ │ "Electronics" │
└───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘

    COUPON STACKING RULES (Chain of Responsibility):
    ┌────────────────────────────────────────────┐
    │  CouponValidator Chain:                     │
    │  1. ExpiryCheck → passes to next             │
    │  2. MinCartValueCheck → passes to next       │
    │  3. UserEligibilityCheck → passes to next    │
    │  4. StackabilityCheck (max 1 coupon of type) │
    │                                              │
    │  Each link can REJECT and stop the chain    │
    └────────────────────────────────────────────┘
```

---

## 2. API Design

```http
POST /api/v1/carts/{cartId}/coupons
Request: {"couponCode": "SAVE20"}
Response: 200 OK
{
  "couponCode": "SAVE20",
  "discountType": "PERCENTAGE",
  "discountAmount": 200.00,
  "originalTotal": 1000.00,
  "newTotal": 800.00
}

// Invalid coupon:
Response: 400 BAD_REQUEST
{"error": "COUPON_EXPIRED", "couponCode": "SAVE20"}

// Not stackable:
Response: 409 CONFLICT
{"error": "COUPON_ALREADY_APPLIED", "message": "Only one percentage-type coupon allowed"}

---

DELETE /api/v1/carts/{cartId}/coupons/{couponCode}
Response: 200 OK
{"newTotal": 1000.00}

---

GET /api/v1/carts/{cartId}/eligible-coupons
Response: 200 OK
{
  "eligibleCoupons": [
    {"code": "SAVE20", "description": "20% off", "estimatedSavings": 200.00},
    {"code": "FLAT100", "description": "Flat ₹100 off orders above ₹500", "estimatedSavings": 100.00}
  ]
}
```

---

## 3. ER Diagram & Database Design

```sql
CREATE TABLE coupons (
    coupon_code VARCHAR(50) PRIMARY KEY,
    discount_type VARCHAR(20) NOT NULL,  -- PERCENTAGE, FLAT, BOGO, CATEGORY
    discount_value DECIMAL(10,2) NOT NULL,  -- 20 (for 20%) or 100 (for ₹100)
    min_cart_value DECIMAL(10,2) DEFAULT 0,
    max_discount_cap DECIMAL(10,2),  -- Cap for percentage discounts
    applicable_category VARCHAR(50),  -- NULL if applies to all
    max_uses_per_user INT DEFAULT 1,
    stackable BOOLEAN DEFAULT FALSE,
    valid_from TIMESTAMP,
    valid_until TIMESTAMP,
    
    CHECK (discount_type IN ('PERCENTAGE', 'FLAT', 'BOGO', 'CATEGORY'))
);

CREATE TABLE cart_applied_coupons (
    cart_id VARCHAR(50) NOT NULL,
    coupon_code VARCHAR(50) NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    discount_amount DECIMAL(10,2),
    
    PRIMARY KEY (cart_id, coupon_code),
    FOREIGN KEY (coupon_code) REFERENCES coupons(coupon_code)
);

CREATE TABLE coupon_usage_history (
    usage_id VARCHAR(50) PRIMARY KEY,
    coupon_code VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50),
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_coupon_user (coupon_code, user_id)  -- Fast "has user used this?" check
);
```

---

## 4. Sequence Diagrams

```
User   Cart   CouponValidatorChain   DiscountStrategy   PricingEngine
  │      │              │                    │                 │
  │─applyCoupon("SAVE20")▶│                    │                 │
  │      ├─validate(coupon)─────▶│                 │
  │      │              │  ExpiryCheck: OK, pass to next        │
  │      │              │  MinCartValueCheck: OK, pass to next  │
  │      │              │  UserEligibilityCheck: OK, pass       │
  │      │              │  StackabilityCheck: OK (no conflict)  │
  │      │◀valid─────────│                    │                 │
  │      ├─getStrategy(PERCENTAGE)─────────────▶│                 │
  │      │              │                    │  PercentageDiscountStrategy
  │      ├─apply(cart)──────────────────────────▶│                 │
  │      │              │                    ├─calculate()─────▶│
  │      │              │                    │                 │  1000 * 0.20 = 200
  │      │              │                    │◀discount=200────│
  │◀newTotal=800─────────│                    │                 │
```

---

## 5. Scenario-First Explanations

### **5.1 Why Strategy Pattern for Discount Calculation?**

**You**: "Without Strategy Pattern:
```java
// ❌ Giant switch statement, grows unwieldy
double calculateDiscount(Coupon coupon, Cart cart) {
    switch (coupon.getType()) {
        case PERCENTAGE:
            return cart.getTotal() * (coupon.getValue() / 100);
        case FLAT:
            return cart.getTotal() >= coupon.getMinCartValue() ? coupon.getValue() : 0;
        case BOGO:
            Item cheapest = cart.getItems().stream().min(...).get();
            return cheapest.getPrice();
        case CATEGORY:
            return cart.getItems().stream()
                .filter(i -> i.getCategory().equals(coupon.getCategory()))
                .mapToDouble(Item::getPrice)
                .sum() * (coupon.getValue() / 100);
    }
}
```

With Strategy Pattern:
```java
interface DiscountStrategy {
    BigDecimal calculateDiscount(Cart cart, Coupon coupon);
    boolean isApplicable(Cart cart, Coupon coupon);
}

class PercentageDiscountStrategy implements DiscountStrategy {
    public BigDecimal calculateDiscount(Cart cart, Coupon coupon) {
        BigDecimal discount = cart.getTotal()
            .multiply(coupon.getValue())
            .divide(new BigDecimal(100));
        
        // Apply cap if specified
        if (coupon.getMaxDiscountCap() != null) {
            discount = discount.min(coupon.getMaxDiscountCap());
        }
        return discount;
    }
    
    public boolean isApplicable(Cart cart, Coupon coupon) {
        return cart.getTotal().compareTo(coupon.getMinCartValue()) >= 0;
    }
}

class BogoDiscountStrategy implements DiscountStrategy {
    public BigDecimal calculateDiscount(Cart cart, Coupon coupon) {
        // Find items matching BOGO category, sort by price, cheapest becomes free
        List<Item> eligibleItems = cart.getItemsByCategory(coupon.getCategory());
        if (eligibleItems.size() < 2) return BigDecimal.ZERO;
        
        eligibleItems.sort(Comparator.comparing(Item::getPrice));
        return eligibleItems.get(0).getPrice();  // Cheapest item free
    }
}

class DiscountStrategyFactory {
    private Map<DiscountType, DiscountStrategy> strategies = Map.of(
        DiscountType.PERCENTAGE, new PercentageDiscountStrategy(),
        DiscountType.FLAT, new FlatDiscountStrategy(),
        DiscountType.BOGO, new BogoDiscountStrategy(),
        DiscountType.CATEGORY, new CategoryDiscountStrategy()
    );
    
    DiscountStrategy getStrategy(DiscountType type) {
        return strategies.get(type);
    }
}
```

**Benefit**: Adding a new coupon type (e.g., 'Free shipping') = new class, zero changes to Cart or existing strategies."

### **5.2 Why Chain of Responsibility for Coupon Stacking Validation?**

**You**: "Multiple business rules must ALL pass before a coupon is applied:

```java
abstract class CouponValidator {
    protected CouponValidator next;
    
    CouponValidator setNext(CouponValidator next) {
        this.next = next;
        return next;
    }
    
    ValidationResult validate(Cart cart, Coupon coupon) {
        ValidationResult result = check(cart, coupon);
        if (!result.isValid()) {
            return result;  // Stop chain, reject immediately
        }
        return (next != null) ? next.validate(cart, coupon) : ValidationResult.success();
    }
    
    abstract ValidationResult check(Cart cart, Coupon coupon);
}

class ExpiryValidator extends CouponValidator {
    ValidationResult check(Cart cart, Coupon coupon) {
        if (LocalDateTime.now().isAfter(coupon.getValidUntil())) {
            return ValidationResult.fail("COUPON_EXPIRED");
        }
        return ValidationResult.success();
    }
}

class MinCartValueValidator extends CouponValidator {
    ValidationResult check(Cart cart, Coupon coupon) {
        if (cart.getTotal().compareTo(coupon.getMinCartValue()) < 0) {
            return ValidationResult.fail("MIN_CART_VALUE_NOT_MET");
        }
        return ValidationResult.success();
    }
}

class StackabilityValidator extends CouponValidator {
    ValidationResult check(Cart cart, Coupon coupon) {
        boolean hasConflictingCoupon = cart.getAppliedCoupons().stream()
            .anyMatch(applied -> !coupon.isStackable() && 
                                 applied.getType() == coupon.getType());
        if (hasConflictingCoupon) {
            return ValidationResult.fail("COUPON_NOT_STACKABLE");
        }
        return ValidationResult.success();
    }
}

// Chain setup:
CouponValidator chain = new ExpiryValidator();
chain.setNext(new MinCartValueValidator())
     .setNext(new UserEligibilityValidator())
     .setNext(new StackabilityValidator());

ValidationResult result = chain.validate(cart, coupon);
```

**Why this matters**: Each validation rule is independently testable, and business rules can be ADDED/REMOVED/REORDERED without touching other validators - very common requirement as promotional rules evolve."

---

## 6. Cross Questions

**Interviewer**: "What's the order of applying multiple stackable coupons - does it matter?"

**You**: "YES, order matters significantly for percentage-based stacking:

```
Cart total: ₹1000
Coupon A: 10% off
Coupon B: Flat ₹100 off

Order 1 (Percentage first, then flat):
1000 × 0.9 = 900
900 - 100 = 800

Order 2 (Flat first, then percentage):
1000 - 100 = 900
900 × 0.9 = 810

Different results! (800 vs 810)
```

**Standard convention** (used by most e-commerce): Apply FLAT discounts first, then PERCENTAGE discounts, since percentage should apply to the 'already reduced' amount typically for maximum customer benefit... but this is a BUSINESS DECISION that must be clearly defined and consistently applied, documented in the coupon engine's processing order."

---

## 7. Trade-offs

### **Client-Side vs Server-Side Discount Calculation**

| Aspect | Client-Side | Server-Side (chosen) |
|--------|--------------|------------------------|
| **Security** | Vulnerable (user can manipulate) | Secure (trusted computation) |
| **Latency** | Instant feedback | Network round-trip |
| **Best for** | UI preview estimate only | Actual order calculation |

**You**: "ALWAYS recalculate final discount server-side at checkout, even if client shows an estimate for UX responsiveness. Never trust client-submitted discount amounts - classic price manipulation vulnerability if you do!"

---

## 8. Senior Trap Questions

### **Trap: "Just apply whatever discount the client sends in the request!"**

**✅ Senior**: "Absolutely NOT - this is a critical **OWASP security vulnerability** (broken access control / trust boundary violation). If your API accepts `{"discountAmount": 500}` directly from the client without server-side recalculation, an attacker can simply modify the request to apply arbitrary discounts. ALWAYS: client sends `couponCode` only, server independently validates coupon eligibility AND recalculates discount amount server-side using trusted cart data. Never trust discount AMOUNTS from client input."

---

## 9. Technology Choices

**You**: "**Rules engine consideration**: For SIMPLE coupon logic (as shown), hand-coded Strategy + Chain of Responsibility is appropriate. For COMPLEX promotional campaigns with dozens of interacting business rules (common at scale - Amazon-style), consider a proper rules engine (Drools) to let business teams configure rules without code deployment."

---

## 🎓 **Final Tips**

1. **Strategy Pattern**: Each discount type = independent calculation logic
2. **Chain of Responsibility**: Sequential validation rules (expiry, min value, stackability)
3. **Server-side recalculation**: NEVER trust client-submitted discount amounts (security!)
4. **Discount ordering matters**: Document and consistently apply stacking order

Good luck! This tests **Strategy + Chain of Responsibility combined** plus security awareness around trust boundaries. 🚀
