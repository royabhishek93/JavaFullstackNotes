# Interview Guide: Car Rental System (LLD) — ZoomCar-style

## 🗣️ The Interview Scenario

> "This question was actually asked at Microsoft: design a car rental system like ZoomCar. A user picks a location, browses available vehicles at nearby stores, reserves one, gets billed, and pays. Keep it as simple as possible — don't over-engineer — but make sure the design could scale to renting bikes or other vehicle types later without a rewrite."

The phrase "keep it as simple as possible" is not filler — it's the actual grading criterion the interviewer is listening for. A common failure mode here is candidates volunteering extra scope ("should I also handle insurance? Loyalty points? Multi-currency billing?") that the interviewer never asked for, burning time and diluting the core design. The correct move, as the transcript emphasizes, is to **never offer options the interviewer didn't request** — clarify scope narrowly, then build exactly that.

## 🏗️ Architect's Explanation (For a New Developer)

Think about the actual user journey, because in this design the objects fall directly out of the journey, not out of abstract nouns you brainstorm in isolation:

1. You open the app and give a **location** (city/pincode) — this determines which **stores** (branches) are relevant.
2. You pick a **store**, and the store shows you a filtered list of its **vehicles** (by type — car vs. bike — and by availability).
3. You pick a vehicle and make a **reservation** — a real-world commitment tied to a specific vehicle, specific dates, and a specific user.
4. The reservation generates a **bill** (how much this rental costs).
5. You **pay** the bill — creating a **payment** record.

That's it — five nouns (`Location`, `Store`, `Vehicle`, `Reservation`, `Bill`/`Payment`) and one umbrella object (`User`) tie them together, plus a top-level `VehicleRentalSystem` object that holds the whole thing together. The architectural discipline worth internalizing here: **whenever a group of operations on a class threatens to make that class huge (e.g., "Store" doing everything about vehicles), extract a dedicated manager class** (here, `VehicleInventoryManagement`) so that the class whose job is "represent a store" doesn't also carry "know how to add/remove/filter vehicles." This is a direct, practical application of the Single Responsibility Principle, and it's also what gives you a clean seam for future vehicle-type-specific inventory logic (e.g., a `CarInventoryManagement` vs. `BikeInventoryManagement` if car and bike filtering rules ever diverge).

## 📊 Visualize It

Class structure:

```
                    +------------------------+
                    | VehicleRentalSystem     |
                    +------------------------+
                    | - List<User>            |
                    | - List<Store>           |
                    +------------------------+
                          |             |
              has-a many  |             |  has-a many
                          v             v
                 +----------------+   +------------------+
                 |     User        |   |      Store        |
                 +----------------+   +------------------+
                 | - userId         |   | - storeId         |
                 | - name           |   | - Location         |
                 | - drivingLicense |   | - VehicleInventoryManagement |
                 +----------------+   | - List<Reservation> |
                                       +------------------+
                                             |        |
                                  has-a      |        |  has-a
                                             v        v
                       +---------------------------+   +----------------+
                       | VehicleInventoryManagement |   |   Location      |
                       +---------------------------+   +----------------+
                       | - List<Vehicle>            |   | - address       |
                       | +addVehicle/removeVehicle   |   | - city, state   |
                       | +getVehicles(filterType)    |   | - pincode       |
                       +---------------------------+   +----------------+
                                    |
                                    v (abstract)
                       +----------------+
                       |    Vehicle      |
                       +----------------+
                       | - vehicleNumber |
                       | - chassisNumber |
                       | - vehicleType   |
                       | - model, company|
                       | - status (ACTIVE/INACTIVE) |
                       +----------------+
                          ▲          ▲
                extends   |          |  extends
                +----------+   +----------+
                |    Car    |   |   Bike    |   ... extensible for future vehicle types
                +----------+   +----------+

  +----------------+   references   +----------------+
  |  Reservation    |--------------->|    Vehicle      |
  +----------------+                +----------------+
  | - reservationId |    references
  | - User          |--------------->|      User        |
  | - bookingDate   |
  | - fromDate/toDate|
  | - pickup/drop location |
  | - reservationStatus (SCHEDULED/IN_PROGRESS/COMPLETED/CANCELLED) |
  +----------------+
          |
          v generates
  +----------------+   generates   +----------------+
  |      Bill       |--------------->|    Payment      |
  +----------------+                +----------------+
  | - reservation    |                | - bill          |
  | - totalAmount    |                | - amount        |
  | - isPaid         |                | - paymentMode   |
  +----------------+                +----------------+
```

Runtime reservation flow:

```
 User provides Location
        |
        v
 VehicleRentalSystem finds matching Store(s) for that Location
        |
        v
 Store.vehicleInventoryManagement.getVehicles(filterType="CAR")
        |
        v
 User selects a Vehicle --> Store.createReservation(vehicle, user, dates)
        |
        v
 New Reservation object created, added to Store's reservation list, status = SCHEDULED
        |
        v
 Bill generated against Reservation (computed from duration/vehicle rate)
        |
        v
 User calls Payment.payBill(bill) --> Bill.isPaid = true, Payment record created
        |
        v
 User picks up vehicle --> Store.updateReservation(reservationId) --> status = IN_PROGRESS
        |
        v
 User drops off vehicle --> Store.updateReservation(reservationId) --> status = COMPLETED
```

## 🔧 Deep Dive: How It Actually Works

### Requirement clarification (the transcript's explicit first move)

Two clarifying questions are asked *before* any class is drawn:
1. **"Is this specifically for cars, or should it be extensible to other vehicle types (bikes) later?"** — Answer: keep it vehicle-type-extensible even though the immediate ask is cars, because the business may expand into bikes.
2. **"Is dynamic filtering (make/model/seats) in scope?"** — Answer: keep filtering simple (vehicle type only) unless told otherwise, per the "design as simple as possible" principle. The interviewer's real interest is the object model and relationships, not an exhaustive filter engine.

### `Vehicle` — the base type, designed for extension

```java
abstract class Vehicle {
    String vehicleId;
    String vehicleNumber;
    String chassisNumber;
    VehicleType vehicleType;   // CAR, BIKE, ... — kept generic on purpose
    String company;
    String model;
    int kilometersDriven;
    Date manufacturingDate;
    VehicleStatus status;      // ACTIVE, INACTIVE
}

class Car extends Vehicle { /* car-specific fields, if any, go here */ }
class Bike extends Vehicle { /* future extension point */ }
```

`VehicleStatus` is deliberately kept to just two values in the transcript's simplified version — **ACTIVE** (available for rent) and **INACTIVE** (not available: could mean under maintenance, damaged, in an accident — but those distinctions are *collapsed* into one INACTIVE state for simplicity, with the explicit caveat that a real system might split this into more granular states).

### `VehicleInventoryManagement` — the extraction that keeps `Store` thin

```java
class VehicleInventoryManagement {
    List<Vehicle> vehicles;

    void addVehicle(Vehicle v) { vehicles.add(v); }
    void removeVehicle(Vehicle v) { vehicles.remove(v); }
    List<Vehicle> getVehicles(VehicleType filterType) {
        // filters and returns matching vehicles; all filtering logic isolated here
        return vehicles.stream().filter(v -> v.vehicleType == filterType).toList();
    }
}
```

The transcript is explicit about *why* this extraction exists: if `Store` directly owned `List<Vehicle>` plus all the add/remove/filter methods, the `Store` class would balloon in responsibility. By delegating to `VehicleInventoryManagement`, you also get a natural seam for future divergence — e.g., a `CarInventoryManagement` subclass with car-specific inventory rules — without ever touching `Store`.

### `Store` — a location-bound branch that owns inventory and reservations

```java
class Store {
    String storeId;
    Location location;
    VehicleInventoryManagement inventoryManagement;
    List<Reservation> reservations;

    Reservation createReservation(User user, Vehicle vehicle, Date from, Date to) {
        Reservation r = new Reservation(user, vehicle, from, to);
        reservations.add(r);
        return r;
    }

    void updateReservation(String reservationId, ReservationStatus newStatus) {
        Reservation r = findReservationById(reservationId);
        r.setStatus(newStatus);
    }
}
```

Why does `Reservation` live inside `Store` rather than floating independently in the system? Because, as the transcript states, **a reservation cannot independently exist without being tied to a vehicle, and every vehicle belongs to exactly one store** — so the natural ownership chain is `Store → Reservation → Vehicle`, and `Store` is the right place to hold the list of reservations active against its own inventory.

### `Location` — deliberately not tied to the user

```java
class Location {
    String address;
    String city;
    String state;
    String pincode;
}
```

The transcript makes a subtle but important point here: **`User` does *not* need to store a `Location`** as a permanent attribute, because a user's home city is irrelevant to the rental — what matters is *which* location they want to rent from *right now* (e.g., "I live in Bangalore but I'm traveling to Delhi, so I want to rent in Delhi"). The `Location` that matters is attached to the **reservation** (pickup/drop location), not the user profile.

### `Reservation` — the central transactional object

```java
class Reservation {
    String reservationId;
    User user;
    Vehicle vehicle;
    Date bookingDate;
    Date fromDate;
    Date toDate;
    Location pickupLocation;
    Location dropLocation;
    ReservationStatus status;  // SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
}
```

`ReservationStatus` state meanings, straight from the transcript:
- **SCHEDULED** — reservation is booked but the vehicle hasn't been physically picked up yet.
- **IN_PROGRESS** — vehicle has been picked up, rental is actively ongoing.
- **COMPLETED** — vehicle has been returned/dropped off; rental is finished.
- **CANCELLED** — user cancelled before pickup.

### `User` — minimal, with one non-negotiable field

```java
class User {
    String userId;
    String name;
    String drivingLicenseNumber;   // mandatory — you cannot rent without this
}
```

### `Bill` and `Payment` — generated *against* a reservation, never independently

```java
class Bill {
    Reservation reservation;
    double totalAmount;   // computed from reservation duration × vehicle's rental rate
    boolean isPaid;

    double computeAmount() {
        // duration = toDate - fromDate; totalAmount = duration * vehicle's per-day rate
        return totalAmount;
    }
}

class Payment {
    Bill bill;
    double amountPaid;
    PaymentMode mode;   // CASH, ONLINE, CARD, ...

    void payBill() {
        bill.isPaid = true;
        // record payment mode/amount
    }
}
```

The ordering constraint called out explicitly: **a `Bill` cannot exist without a `Reservation`** ("if there's no reservation, a bill can't be generated at all") — this dependency direction is worth stating out loud in the interview because it justifies why `Bill` holds a `Reservation` reference and not the other way around.

### `VehicleRentalSystem` — the top-level aggregate root

```java
class VehicleRentalSystem {
    List<User> users;
    List<Store> stores;

    void addStore(Store s) { stores.add(s); }
    void addUser(User u) { users.add(u); }
}
```

### End-to-end operational walkthrough (exactly as demoed in the transcript)

1. System is bootstrapped: a few `User`s, a few `Vehicle`s, and `Store`s are created; vehicles are added into each store's `VehicleInventoryManagement`; stores are added into the `VehicleRentalSystem`.
2. User picks a `Location` → system finds the matching `Store`.
3. `store.inventoryManagement.getVehicles(CAR)` returns available vehicles.
4. User selects a vehicle → `store.createReservation(user, vehicle, dates)` — this both creates the `Reservation` object *and* adds it into the store's reservation list in one step.
5. `Bill` is generated against that `Reservation`; amount is computed from the reservation's date range and the vehicle's rate.
6. `Payment.payBill()` marks the bill as paid.
7. When the user physically returns the vehicle, `store.updateReservation(reservationId, COMPLETED)` is called — the store looks up the specific reservation by ID and flips its status.

## 🔥 Real Production Incident & Fix

**What broke**: An early version of a fleet-rental backend modeled `User.currentLocation` as a persistent field on the `User` entity (set once at signup) and used it — instead of a location captured per-booking — to determine which store's vehicles to show and, worse, which store a reservation's bill should be computed against (different cities had different per-day rates). This matched the "obvious" data model but ignored the exact pitfall called out in this transcript.

**How the team noticed**: Customer support started receiving complaints from users who had signed up while living in Bangalore but were now traveling and renting cars in Delhi — their bills were coming back computed at **Bangalore's daily rate**, not Delhi's, because the billing service read `user.currentLocation` (still "Bangalore" from signup) instead of the reservation's actual `pickupLocation`. The discrepancy was flagged first as a spike in refund-request tickets referencing "wrong city pricing," then confirmed via a data audit comparing `reservation.pickupLocation` against the store used for billing.

**Root cause**: Location was modeled as a property of the *user* rather than a property of the *reservation* — exactly the modeling mistake this transcript explicitly warns against ("a user's own location doesn't matter; what matters is where they're renting from *right now*"). Because `User` is a long-lived entity that's read from cache/session state across many requests, using it as the source of truth for a transient, booking-specific fact (rental city) meant stale or simply irrelevant data silently leaked into pricing.

**The fix**: The team moved `pickupLocation`/`dropLocation` to live exclusively on the `Reservation` object (as shown in the Deep Dive), removed the billing service's dependency on `User.currentLocation` entirely, and added a validation rule that `Bill.computeAmount()` must read location strictly from the `Reservation` it's attached to. A regression test was added asserting that changing a user's profile location after a reservation is created has zero effect on that reservation's bill.

```
BEFORE: billing reads stale User.currentLocation           AFTER: billing reads Reservation.pickupLocation

 User { currentLocation: "Bangalore" (set at signup) }       User { } // no location field at all
        |                                                    Reservation { pickupLocation: "Delhi",
        v  (used for billing, even for out-of-city rentals)                 dropLocation: "Delhi" }
 Bill computed at Bangalore's rate  <-- WRONG                       |
                                                                     v
                                                              Bill computed at Delhi's rate  <-- CORRECT
```

## ❓ Likely Interview Follow-Up Questions & Answers

1. **"Why is `Reservation` owned by `Store` instead of being a top-level entity managed directly by `VehicleRentalSystem`?"**
   Because a reservation is meaningless without a specific vehicle, and every vehicle belongs to exactly one store's inventory — so the natural containment chain is store → its vehicles' reservations. This also keeps reservation lookups localized (you typically know which store you're interacting with before you touch a reservation), avoiding a need to search a global reservation list.

2. **"Why extract `VehicleInventoryManagement` as its own class instead of putting `List<Vehicle>` and its operations directly on `Store`?"**
   Single Responsibility: `Store` should represent "a physical branch with a location and its business objects," not also implement inventory CRUD and filtering logic. The extraction also gives a clean extension point — if car and bike inventories need genuinely different management logic later, you can introduce `CarInventoryManagement`/`BikeInventoryManagement` without touching `Store` at all.

3. **"How would you compute the bill amount, and where does that logic live?"**
   It lives inside `Bill` itself (e.g., `computeAmount()`), reading `reservation.fromDate`/`toDate` for duration and `reservation.vehicle`'s rate. Keeping the computation inside `Bill` (rather than in `Store` or `Reservation`) means billing logic changes (e.g., adding late-fee surcharges) are isolated to one class.

4. **"What happens if a user wants to cancel a reservation before pickup — walk through the object interactions."**
   The store looks up the `Reservation` by ID (same mechanism as `updateReservation`) and transitions its `status` to `CANCELLED`. If a `Bill` was already generated and paid, a refund flow would need to be triggered against the associated `Payment` — worth mentioning as a follow-on concern even if not fully designed, to show you're aware of the edge case.

5. **"Your `VehicleStatus` only has ACTIVE/INACTIVE. Isn't that too coarse for a real system — what about 'in maintenance' vs 'in an accident'?"**
   Yes, in a production system you'd likely model this as a richer enum or even a separate `VehicleCondition` value; the transcript intentionally collapses these into a single INACTIVE state as a scope-simplification decision, made explicit to the interviewer. The right interview move is to name the simplification and note you'd revisit it if the interviewer wants that granularity — not to silently under-model it.

6. **"How would you extend this design to support bikes without duplicating the whole class hierarchy?"**
   Because `Vehicle` is already an abstract base class with `VehicleType` as a field (not baked into class names or logic), adding bikes means: (a) add a `Bike extends Vehicle` subclass for any bike-specific attributes, and (b) nothing else changes in `Store`, `Reservation`, `Bill`, or `Payment` — they all operate on the abstract `Vehicle` reference. This is the direct payoff of the "keep it vehicle-type-extensible" requirement clarified at the very start.

## 🔑 Key Takeaway

Model objects around the *actual user journey* (location → store → vehicle → reservation → bill → payment), keep `Vehicle` abstract and type-agnostic for future extensibility, and — critically — attach transient, booking-specific facts like pickup location to the `Reservation`, never to the long-lived `User` entity.
