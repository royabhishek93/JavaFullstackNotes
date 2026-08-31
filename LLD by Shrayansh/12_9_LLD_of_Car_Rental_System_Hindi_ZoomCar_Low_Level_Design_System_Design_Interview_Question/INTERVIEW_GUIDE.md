# 🚗 Car Rental System - Low Level Design Interview Guide
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

## **Design Patterns Used**: Strategy (Pricing) + Factory (Vehicle types) + Observer (Availability)

**Interviewer**: "Design a car rental system like ZoomCar."

**You**: "Great! Let me clarify scope:
1. Vehicle search and reservation with date ranges?
2. Dynamic pricing (surge, seasonal)?
3. Multiple vehicle types (hatchback, SUV, luxury)?
4. Booking conflict prevention (double-booking)?

The core challenge is: **Preventing double-booking while handling concurrent reservation requests, plus flexible pricing strategies.**"

> **Note on the accompanying diagram**: `CarRental_LLD.drawio` centers on the **Template Method** pattern for the `Vehicle` → `Car`/`Bike` hierarchy and the reservation/billing object model - it's a good reference for the class structure, but it doesn't model the concurrency-safety mechanics (the `EXCLUDE` constraint / date-range overlap prevention below). That race-condition story is the part of this guide most worth rehearsing out loud - it's the detail that separates "I drew some boxes" from "I understand why two simultaneous bookings can't both succeed."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                  CAR RENTAL ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  RESERVATION     │
                    │    SERVICE       │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   VEHICLE    │ │  PRICING     │ │ AVAILABILITY │
    │  INVENTORY   │ │  STRATEGY    │ │   CALENDAR   │
    │              │ │              │ │              │
    │ Vehicle Types│ │ - Standard   │ │ Date Ranges  │
    │ - Hatchback  │ │ - Surge      │ │ Booked Slots │
    │ - SUV        │ │ - Seasonal   │ │              │
    │ - Luxury     │ │ - Long-term  │ │              │
    └──────────────┘ └──────────────┘ └──────────────┘

    BOOKING CONFLICT PREVENTION (Core Challenge):
    ┌────────────────────────────────────────────┐
    │  Vehicle Availability using Interval Tree   │
    │  or DB-level date range overlap check       │
    │                                              │
    │  Booking: Jan 5-10                          │
    │  New Request: Jan 8-12                      │
    │  → OVERLAP DETECTED! Reject.                │
    │                                              │
    │  SQL: WHERE NOT (new.end < existing.start   │
    │              OR new.start > existing.end)   │
    └────────────────────────────────────────────┘
```

---

## 2. API Design

```http
GET /api/v1/vehicles/search?city=Bangalore&startDate=2026-09-01&endDate=2026-09-05&type=SUV
Response: 200 OK
{
  "vehicles": [
    {
      "vehicleId": "veh-1234",
      "model": "Toyota Fortuner",
      "type": "SUV",
      "pricePerDay": 3500,
      "available": true
    }
  ]
}

---

POST /api/v1/reservations
Request:
{
  "vehicleId": "veh-1234",
  "userId": "user-5678",
  "startDate": "2026-09-01",
  "endDate": "2026-09-05",
  "pickupLocation": "Bangalore Airport"
}

Response: 201 CREATED
{
  "reservationId": "res-9999",
  "totalPrice": 14000,  // 4 days × 3500
  "status": "CONFIRMED"
}

// Conflict:
Response: 409 CONFLICT
{
  "error": "VEHICLE_UNAVAILABLE",
  "message": "Vehicle already booked for overlapping dates",
  "conflictingReservation": "res-1111"
}
```

---

## 3. ER Diagram & Database Design

```sql
CREATE TABLE vehicles (
    vehicle_id VARCHAR(50) PRIMARY KEY,
    model VARCHAR(100),
    type VARCHAR(20),  -- HATCHBACK, SEDAN, SUV, LUXURY
    base_price_per_day DECIMAL(10,2),
    city VARCHAR(100),
    status VARCHAR(20) DEFAULT 'AVAILABLE'
);

CREATE TABLE reservations (
    reservation_id VARCHAR(50) PRIMARY KEY,
    vehicle_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'CONFIRMED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (end_date > start_date),
    FOREIGN KEY (vehicle_id) REFERENCES vehicles(vehicle_id),
    INDEX idx_vehicle_dates (vehicle_id, start_date, end_date)
);

-- CRITICAL: Prevent overlapping bookings using EXCLUSION constraint (PostgreSQL)
ALTER TABLE reservations ADD CONSTRAINT no_overlap
EXCLUDE USING gist (
    vehicle_id WITH =,
    daterange(start_date, end_date) WITH &&
) WHERE (status = 'CONFIRMED');
```

### **Why This Schema?**

**You**: "The `EXCLUDE` constraint with `daterange` and `gist` index is PostgreSQL's native way to prevent overlapping ranges **at the database level**. This is far more reliable than application-level checks which suffer from race conditions!"

---

## 4. Sequence Diagrams

### **Concurrent Booking Attempt (Race Condition Prevention)**

```
User1        User2        ReservationService    DB (with EXCLUDE constraint)
  │            │                  │                      │
  │─Book Sep1-5▶│                  │                      │
  │            │─Book Sep3-7──────▶│                      │
  │            │                  ├─INSERT (Sep1-5)───────▶│
  │            │                  │◀SUCCESS───────────────│
  │◀CONFIRMED──│                  │                      │
  │            │                  ├─INSERT (Sep3-7)───────▶│
  │            │                  │              [EXCLUDE constraint violated!]
  │            │                  │◀ERROR: overlap─────────│
  │            │◀409 CONFLICT─────│                      │
```

**You**: "Notice: Both requests hit the service concurrently, but the DATABASE serializes them. Whichever INSERT executes first wins; the second violates the exclusion constraint and fails atomically. **No application-level locking needed!**"

---

## 5. Scenario-First Explanations

### **5.1 Why Strategy Pattern for Pricing?**

```java
interface PricingStrategy {
    BigDecimal calculatePrice(Vehicle vehicle, int days, LocalDate startDate);
}

class StandardPricingStrategy implements PricingStrategy {
    public BigDecimal calculatePrice(Vehicle vehicle, int days, LocalDate startDate) {
        return vehicle.getBasePrice().multiply(new BigDecimal(days));
    }
}

class SurgePricingStrategy implements PricingStrategy {
    public BigDecimal calculatePrice(Vehicle vehicle, int days, LocalDate startDate) {
        double surgeMultiplier = demandService.getCurrentSurge(vehicle.getCity());
        return vehicle.getBasePrice()
            .multiply(new BigDecimal(days))
            .multiply(new BigDecimal(surgeMultiplier));
    }
}

class LongTermDiscountStrategy implements PricingStrategy {
    public BigDecimal calculatePrice(Vehicle vehicle, int days, LocalDate startDate) {
        BigDecimal base = vehicle.getBasePrice().multiply(new BigDecimal(days));
        if (days >= 30) return base.multiply(new BigDecimal(0.7));  // 30% off monthly
        if (days >= 7) return base.multiply(new BigDecimal(0.85));   // 15% off weekly
        return base;
    }
}
```

**You**: "Different pricing strategies plug in without changing reservation logic. Same pattern as Uber's surge pricing!"

### **5.2 Why Database-Level Constraint Over Application Lock?**

**You**: "Junior approach - use `synchronized` or distributed lock (Redis) per vehicle. **Problems**:
1. Doesn't scale across multiple service instances easily
2. Redis lock failure = potential double-booking
3. Extra infrastructure complexity

**Senior approach** - Let the DATABASE be the single source of truth for consistency. PostgreSQL's `EXCLUDE` constraint with `daterange` + `gist` index handles this natively, atomically, without any application-level coordination."

---

## 6. Cross Questions

**Interviewer**: "What if user cancels mid-rental and wants partial refund?"

**You**: "Prorated refund with cancellation policy:
```java
class CancellationService {
    RefundResult cancelReservation(String reservationId) {
        Reservation res = reservationRepo.findById(reservationId);
        long daysUsed = ChronoUnit.DAYS.between(res.getStartDate(), LocalDate.now());
        long totalDays = ChronoUnit.DAYS.between(res.getStartDate(), res.getEndDate());
        
        BigDecimal usedAmount = res.getTotalPrice()
            .multiply(new BigDecimal(daysUsed))
            .divide(new BigDecimal(totalDays), 2, RoundingMode.HALF_UP);
        
        BigDecimal refundAmount = res.getTotalPrice().subtract(usedAmount);
        
        // Apply cancellation fee based on policy (e.g., 10% if <24hrs notice)
        if (isLastMinuteCancellation(res)) {
            refundAmount = refundAmount.multiply(new BigDecimal(0.9));
        }
        
        return processRefund(res, refundAmount);
    }
}
```"

---

## 7. Trade-offs

### **Database Constraint vs Distributed Lock**

| Aspect | DB Exclusion Constraint | Redis Distributed Lock |
|--------|--------------------------|--------------------------|
| **Consistency** | Guaranteed (ACID) | Best-effort |
| **Complexity** | Low (DB handles it) | High (lock management, TTL, retries) |
| **Performance** | Excellent (indexed) | Good but extra network hop |
| **Portability** | PostgreSQL-specific | Works with any DB |

**My choice**: DB constraint when using PostgreSQL. Distributed lock only if using a DB without native range-exclusion support.

---

## 8. Senior Trap Questions

### **Trap: "Just check for overlaps in application code before inserting!"**

**❌ Junior**: 
```java
// RACE CONDITION!
if (!hasOverlap(vehicleId, startDate, endDate)) {
    createReservation(...);  // Another request could sneak in here!
}
```

**✅ Senior**: "This is a classic **TOCTOU (Time-of-check-time-of-use)** bug. Between checking for overlap and inserting, another thread could insert a conflicting reservation. Must use DB-level atomic constraint (EXCLUDE) OR wrap in `SERIALIZABLE` isolation transaction with retry logic."

---

## 9. Technology Choices

**You**: "**PostgreSQL** over MySQL specifically for this use case - native `daterange` type and `EXCLUDE USING gist` constraint. MySQL would require manual overlap-checking with `SELECT FOR UPDATE`, which is more error-prone."

---

## 🎓 **Final Tips**

1. **DB-level overlap prevention**: Show you know `EXCLUDE` constraints, not just app-level locks
2. **Strategy Pattern for pricing**: Surge, seasonal, long-term discounts
3. **TOCTOU awareness**: Critical race condition to call out
4. **Prorated refunds**: Shows business logic depth

Good luck! This tests **concurrency control** and **pricing flexibility** design. 🚀
