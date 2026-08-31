# 📦 Inventory Management System - Low Level Design Interview Guide
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

## **Design Patterns Used**: Observer (stock alerts) + Strategy (reorder policies)

**Interviewer**: "Design an Inventory Management System for a warehouse/e-commerce platform."

**You**: "Let me clarify scope:
1. Multiple warehouses with stock tracking?
2. Reserve inventory during checkout (prevent overselling)?
3. Automatic reordering when stock is low?
4. Multi-SKU, multi-location tracking?

The core challenge: **preventing overselling under concurrent orders while maintaining accurate real-time stock levels across distributed warehouses.**"

### 🎯 Two Valid Interpretations of "Inventory Management"

**Interviewer**: "I've seen this question modeled as a full Zomato/Zepto-style order platform (Product, Cart, Order, Invoice, Payment, warehouse selection) rather than a stock-safety layer. Which is right?"

**You**: "Both are legitimate, and which one to build depends on what the interviewer actually wants to probe:

| Aspect | Stock-Safety Focus (this guide) | Order-Platform Focus |
|---|---|---|
| **Core question being tested** | Concurrency control - how do you prevent overselling? | End-to-end order flow - cart, checkout, warehouse selection, invoicing |
| **Central entity** | `Inventory` with `reserved_quantity` / `total_quantity`, `Reservation` with TTL | `Product`, `ProductCategory`, `Warehouse`, `Cart`, `Order`, `Invoice`, `Payment` |
| **Key pattern** | Reserve → Confirm → Release, atomic `UPDATE ... WHERE available >= ?` | Strategy Pattern for warehouse selection (nearest/cheapest), Cart as `Map<categoryId, count>` |
| **Hardest problem solved** | Race condition: two orders reserving the last unit simultaneously | Consistency across checkout steps: inventory deducted but payment fails - needs rollback |
| **When to reach for this** | Interviewer says "prevent overselling", "flash sale", "concurrent orders on last item" | Interviewer says "design the ordering flow for a grocery/food app" |

**My approach**: I lead with the **stock-safety angle** below because 'Inventory Management System' as an interview prompt is most often testing whether you know how to prevent overselling under concurrency - that's the classic trap question. But if the interviewer frames it as 'design how a user orders products end-to-end' (more like a mini e-commerce system), I'd pivot to the order-platform model: `Product` → `ProductCategory` (price lives at category level since identical SKUs share it) → `Warehouse` (selected once per session via a `WarehouseSelectionStrategy` - NEAREST or CHEAPEST) → `Cart` (stores `categoryId → count`, not individual product objects) → `Order` → checkout does inventory deduction **then** payment, with rollback (add stock back) if payment fails. Either way, the underlying concurrency-safety principles from this guide still apply at the deduction step."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│              INVENTORY MANAGEMENT ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  INVENTORY        │
                    │    SERVICE        │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  WAREHOUSE 1  │    │  WAREHOUSE 2  │    │  REORDER     │
│              │    │              │    │  STRATEGY    │
│ SKU: A123    │    │ SKU: A123    │    │              │
│ Qty: 500     │    │ Qty: 200     │    │ - Fixed      │
│ Reserved: 50 │    │ Reserved: 10 │    │ - Dynamic    │
│ Available:450│    │ Available:190│    │ - JIT        │
└──────────────┘    └──────────────┘    └──────────────┘

    RESERVATION FLOW (Prevent Overselling):
    ┌────────────────────────────────────────────┐
    │  Order placed → RESERVE stock (not deduct)  │
    │  Payment success → CONFIRM (deduct reserved)│
    │  Payment fails/timeout → RELEASE reservation │
    │                                              │
    │  Available = Total - Reserved                │
    └────────────────────────────────────────────┘

    LOW STOCK OBSERVER PATTERN:
    ┌────────────────────────────────────────────┐
    │  Inventory (Subject)                        │
    │    └─notifies→ ReorderService (Observer)     │
    │    └─notifies→ AlertService (Observer)       │
    │    └─notifies→ AnalyticsService (Observer)    │
    └────────────────────────────────────────────┘
```

---

## 2. API Design

```http
GET /api/v1/inventory/{sku}
Response: 200 OK
{
  "sku": "A123",
  "totalQuantity": 700,
  "reserved": 60,
  "available": 640,
  "warehouses": [
    {"warehouseId": "wh-1", "quantity": 500, "reserved": 50},
    {"warehouseId": "wh-2", "quantity": 200, "reserved": 10}
  ]
}

---

POST /api/v1/inventory/{sku}/reserve
Request: {"quantity": 5, "orderId": "order-9999", "warehouseId": "wh-1"}
Response: 200 OK
{
  "reservationId": "res-1234",
  "sku": "A123",
  "quantity": 5,
  "expiresAt": "2026-08-31T10:15:00Z"  // 15-min hold
}

// Insufficient stock:
Response: 409 CONFLICT
{"error": "INSUFFICIENT_STOCK", "available": 3, "requested": 5}

---

POST /api/v1/inventory/reservations/{reservationId}/confirm
Response: 200 OK
{"status": "CONFIRMED", "quantityDeducted": 5}

---

POST /api/v1/inventory/reservations/{reservationId}/release
Response: 200 OK
{"status": "RELEASED", "quantityReturned": 5}
```

---

## 3. ER Diagram & Database Design

```sql
CREATE TABLE inventory (
    sku VARCHAR(50) NOT NULL,
    warehouse_id VARCHAR(50) NOT NULL,
    total_quantity INT NOT NULL DEFAULT 0,
    reserved_quantity INT NOT NULL DEFAULT 0,
    reorder_threshold INT DEFAULT 50,
    reorder_quantity INT DEFAULT 200,
    
    PRIMARY KEY (sku, warehouse_id),
    CHECK (reserved_quantity <= total_quantity),
    CHECK (total_quantity >= 0)
);

CREATE TABLE reservations (
    reservation_id VARCHAR(50) PRIMARY KEY,
    sku VARCHAR(50) NOT NULL,
    warehouse_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    quantity INT NOT NULL,
    status VARCHAR(20) DEFAULT 'PENDING',
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (status IN ('PENDING', 'CONFIRMED', 'RELEASED', 'EXPIRED')),
    FOREIGN KEY (sku, warehouse_id) REFERENCES inventory(sku, warehouse_id),
    INDEX idx_expires (status, expires_at)  -- For cleanup job
);
```

### **Why This Schema?**

**You**: "The `reserved_quantity` column with CHECK constraint `reserved_quantity <= total_quantity` prevents overselling AT THE DATABASE LEVEL. Combined with atomic UPDATE:

```sql
UPDATE inventory 
SET reserved_quantity = reserved_quantity + ? 
WHERE sku = ? AND warehouse_id = ? 
  AND (total_quantity - reserved_quantity) >= ?;
-- Returns 0 rows affected if insufficient available stock → application detects failure
```

This atomic check-and-update prevents the classic TOCTOU race condition without needing explicit locks!"

---

## 4. Sequence Diagrams

```
Order    InventoryService    DB              ReservationCleanupJob
  │            │                │                     │
  │─reserve(5)─▶│                │                     │
  │            ├─atomic UPDATE──▶│                     │
  │            │  (reserved += 5 WHERE available >= 5) │
  │            │◀rows=1 (success)│                     │
  │            ├─INSERT reservation (expires in 15min)▶│
  │◀reservationId───────────────│                     │
  │            │                │                     │
  │  ... user doesn't complete payment in time ...     │
  │            │                │                     │
  │            │                │◀── SELECT WHERE status='PENDING' AND expires_at < NOW()
  │            │                │       auto-release expired reservations
  │            │◀───────────────│  UPDATE reserved -= 5, status='EXPIRED'
```

**You**: "Background cleanup job is CRITICAL - without it, abandoned carts would permanently lock inventory. Runs every minute, releases expired reservations."

---

## 5. Scenario-First Explanations

### **5.1 Why Reserve-then-Confirm (Not Direct Deduction)?**

**You**: "Two-phase approach prevents inventory being 'stuck' during payment processing:

```java
class InventoryService {
    @Transactional
    Reservation reserveStock(String sku, String warehouseId, int quantity, String orderId) {
        int rowsUpdated = jdbcTemplate.update(
            "UPDATE inventory SET reserved_quantity = reserved_quantity + ? " +
            "WHERE sku = ? AND warehouse_id = ? " +
            "AND (total_quantity - reserved_quantity) >= ?",
            quantity, sku, warehouseId, quantity
        );
        
        if (rowsUpdated == 0) {
            throw new InsufficientStockException(sku);
        }
        
        Reservation reservation = new Reservation(sku, warehouseId, quantity, orderId,
                                                    LocalDateTime.now().plusMinutes(15));
        reservationRepo.save(reservation);
        return reservation;
    }
    
    @Transactional
    void confirmReservation(String reservationId) {
        Reservation res = reservationRepo.findById(reservationId);
        // Convert reservation into actual deduction
        jdbcTemplate.update(
            "UPDATE inventory SET total_quantity = total_quantity - ?, " +
            "reserved_quantity = reserved_quantity - ? WHERE sku = ? AND warehouse_id = ?",
            res.getQuantity(), res.getQuantity(), res.getSku(), res.getWarehouseId()
        );
        res.setStatus(ReservationStatus.CONFIRMED);
    }
    
    @Transactional
    void releaseReservation(String reservationId) {
        Reservation res = reservationRepo.findById(reservationId);
        jdbcTemplate.update(
            "UPDATE inventory SET reserved_quantity = reserved_quantity - ? " +
            "WHERE sku = ? AND warehouse_id = ?",
            res.getQuantity(), res.getSku(), res.getWarehouseId()
        );
        res.setStatus(ReservationStatus.RELEASED);
    }
}
```

**Why not direct deduction?** If payment fails or times out, you'd need a COMPENSATING transaction to add stock back - more error-prone than simply releasing a reservation that never became permanent."

### **5.2 Why Multi-Warehouse Requires Smart Selection?**

**You**: "When order comes in, WHICH warehouse fulfills it?

```java
class WarehouseSelector {
    Warehouse selectBestWarehouse(String sku, int quantity, Address shippingAddress) {
        List<Warehouse> candidates = warehouseRepo.findWithStock(sku, quantity);
        
        return candidates.stream()
            .min(Comparator.comparingDouble(w -> 
                calculateDistance(w.getLocation(), shippingAddress)
            ))
            .orElseThrow(() -> new InsufficientStockException(sku));
    }
}
```

**Real-world**: Amazon's fulfillment algorithm considers: distance to customer, warehouse current load, shipping cost, delivery SLA - NOT just distance. This is a full optimization problem in production."

---

## 6. Cross Questions

**Interviewer**: "How do you handle automatic reordering when stock is low?"

**You**: "Observer Pattern - Inventory notifies ReorderService on every deduction:

```java
interface InventoryObserver {
    void onStockChanged(String sku, String warehouseId, int newAvailable);
}

class ReorderService implements InventoryObserver {
    public void onStockChanged(String sku, String warehouseId, int newAvailable) {
        Inventory inv = inventoryRepo.find(sku, warehouseId);
        
        if (newAvailable <= inv.getReorderThreshold()) {
            PurchaseOrder po = new PurchaseOrder(sku, inv.getReorderQuantity(), warehouseId);
            supplierService.placeOrder(po);
            notificationService.notify("Reorder triggered for " + sku);
        }
    }
}

class Inventory {
    private List<InventoryObserver> observers = new ArrayList<>();
    
    void deductStock(int quantity) {
        this.totalQuantity -= quantity;
        notifyObservers();
    }
    
    void notifyObservers() {
        int available = totalQuantity - reservedQuantity;
        observers.forEach(obs -> obs.onStockChanged(sku, warehouseId, available));
    }
}
```"

---

## 7. Trade-offs

### **Pessimistic Lock vs Optimistic Lock for Stock Updates**

| Aspect | Pessimistic (SELECT FOR UPDATE) | Optimistic (atomic UPDATE with WHERE) |
|--------|-----------------------------------|------------------------------------------|
| **Throughput** | Lower (blocking) | Higher (no blocking) |
| **Deadlock risk** | Yes if multiple SKUs locked in different order | None |
| **Best for** | Low contention SKUs | High contention (flash sale items) |

**You**: "Atomic UPDATE with WHERE clause (shown above) is essentially optimistic and scales better under high contention - like flash sale scenarios. No explicit locks needed."

---

## 8. Senior Trap Questions

### **Trap: "Just SELECT then check quantity then UPDATE, simple!"**

**❌ Junior**:
```java
Inventory inv = inventoryRepo.findBySku(sku);  // SELECT
if (inv.getAvailable() >= quantity) {           // CHECK
    inv.setReserved(inv.getReserved() + quantity);
    inventoryRepo.save(inv);                    // UPDATE - RACE CONDITION!
}
```

**✅ Senior**: "Classic TOCTOU race - between SELECT and UPDATE, another thread could reserve the same 'available' stock. MUST use atomic UPDATE with WHERE clause condition (shown earlier) OR use `SELECT FOR UPDATE` with explicit transaction. Never trust application-level read-then-write for inventory decisions - this is exactly how flash sales oversell products!"

---

## 9. Technology Choices

**You**: "**PostgreSQL** for strong consistency (inventory is money-adjacent, correctness > raw speed). **Redis** as a fast-fail pre-check layer (quick 'probably available' check before hitting DB) - NOT source of truth, just optimization to reduce DB load during flash sales."

---

## 🎓 **Final Tips**

1. **Reserve-Confirm-Release pattern**: Prevents inventory lockup during payment
2. **Atomic UPDATE with WHERE**: Prevents overselling race conditions
3. **Observer Pattern**: Auto-reorder on low stock
4. **Multi-warehouse selection**: Distance + load balancing

Good luck! Tests **concurrency control** for real-world overselling prevention. 🚀
