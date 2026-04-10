# Designing a Parking Lot System

## Requirements
1. The parking lot should have multiple levels, each level with a certain number of parking spots.
2. The parking lot should support different types of vehicles, such as cars, motorcycles, and trucks.
3. Each parking spot should be able to accommodate a specific type of vehicle.
4. The system should assign a parking spot to a vehicle upon entry and release it when the vehicle exits.
5. The system should track the availability of parking spots and provide real-time information to customers.
6. The system should handle multiple entry and exit points and support concurrent access.

## UML Class Diagram

![](diagrams/parkinglot-class-diagram.png)

## Implementations
#### [Java Implementation](parkinglot/) 

## Classes, Interfaces and Enumerations
1. The **ParkingLot** class follows the Singleton pattern to ensure only one instance of the parking lot exists. It maintains a list of levels and provides methods to park and unpark vehicles.
2. The **ParkingFloor** class represents a level in the parking lot and contains a list of parking spots. It handles parking and unparking of vehicles within the level.
3. The **ParkingSpot** class represents an individual parking spot and tracks the availability and the parked vehicle.
4. The **Vehicle** class is an abstract base class for different types of vehicles. It is extended by Car, Motorcycle, and Truck classes.
5. The **VehicleSize** enum defines the different types of vehicles supported by the parking lot.
6. Multi-threading is achieved through the use of synchronized keyword on critical sections to ensure thread safety.
7. The **Main** class demonstrates the usage of the parking lot system.

## Design Patterns Used:
1. Singleton Pattern: Ensures only one instance of the ParkingLot class.
2. Factory Pattern (optional extension): Could be used for creating vehicles based on input.
3. Observer Pattern (optional extension): Could notify customers about available spots.

---

## Interview Discussion Points

### Common Interview Questions
1. **How would you handle pricing based on vehicle type and duration?**
   - Add a `PricingStrategy` interface with different implementations (HourlyPricing, FlatRate)
   - Store entry time in `ParkingSpot` or `Ticket` class
   - Calculate on exit: `price = strategy.calculate(vehicleType, duration)`

2. **How would you scale this system for multiple parking lots in different locations?**
   - Add a `Location` class with GPS coordinates
   - Create a `ParkingLotManager` that manages multiple `ParkingLot` instances
   - Use distributed caching (Redis) for real-time availability across locations

3. **What if we need to reserve parking spots in advance?**
   - Add `ReservationStatus` enum (RESERVED, OCCUPIED, AVAILABLE)
   - Create `Reservation` class with time slots
   - Implement time-based validation in `parkVehicle()` method

4. **How would you handle payment processing?**
   - Add `Payment` interface with implementations (Cash, Card, Mobile)
   - Create `PaymentProcessor` singleton
   - Store payment history with bookings

5. **How do you prevent race conditions when multiple vehicles try to park simultaneously?**
   - Use `synchronized` blocks on critical sections
   - Atomic operations with `ConcurrentHashMap`
   - Database-level locks for distributed systems

### Design Trade-offs

| Decision | Why Chosen | Trade-off |
|----------|------------|-----------|
| **Singleton for ParkingLot** | Ensures single source of truth for availability | Harder to test, global state |
| **Synchronized methods** | Thread safety for concurrent access | Performance overhead, potential bottlenecks |
| **Enum for VehicleSize** | Type safety, clear categories | Less flexible for custom vehicle types |
| **ArrayList for spots** | Simple, ordered access | O(n) search time for available spots |

### Optimizations to Discuss

1. **Use Priority Queue for Spot Assignment**
   - Current: Linear search O(n)
   - Optimized: Min-heap based on spot number O(log n)

2. **Add Caching Layer**
   - Cache available spot counts per floor
   - Update cache atomically on park/unpark
   - Reduces full scan for "is parking full?" queries

3. **Event-Driven Architecture**
   - Publish events: `SpotOccupied`, `SpotFreed`, `FloorFull`
   - Subscribers: Pricing service, notification service, analytics

### Complexity Analysis

- **Park Vehicle**: O(n) where n = total spots (linear search)
- **Unpark Vehicle**: O(1) if we store vehicle-to-spot mapping
- **Check Availability**: O(n) without caching, O(1) with counter
- **Space Complexity**: O(n) for storing n parking spots

### Follow-up Features
- **Valet Parking**: Add `ValetService` class with key management
- **Electric Vehicle Charging**: Add `ChargingSpot` subclass
- **Handicap Parking**: Priority queue with special spot types
- **Mobile App Integration**: REST API with real-time WebSocket updates
- **Analytics Dashboard**: Track occupancy rates, peak hours, revenue
