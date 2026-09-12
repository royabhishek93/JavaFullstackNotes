# Hotel Booking System - Complete LLD Interview Guide

**Interview Duration: 45 minutes | Difficulty: Medium | Must-Know: ⭐⭐⭐**

**Note:** This is 90% similar to Parking Lot System. Focus on time-based reservations!

---

## CONVERSATIONAL SCRIPT (How to approach in interview)

### Phase 1: Requirements Clarification (5 mins)

**You:** "This is very similar to Parking Lot - instead of parking spots, we have hotel rooms with time-based bookings."

**Functional Requirements:**
- "Search hotels by location, dates, room type"
- "View available rooms for specific dates"
- "Book rooms with check-in and check-out dates"
- "Support different room types - Single, Double, Suite"
- "Handle cancellations and refunds"
- "User booking history"
- "Payment processing"
- "Should we support amenities, special requests?"

**Interviewer:** "Keep it simple. Focus on availability and booking flow."

**You:** "For non-functional requirements:"
- "No double booking - strong consistency"
- "Handle concurrent bookings (race conditions)"
- "Search should be fast (< 500ms)"
- "Scalable for multiple hotels"
- "Price calculation based on room type and duration"

**Interviewer:** "Yes, focus on preventing double booking with time overlaps."

---

### Phase 2: Key Difference from Parking Lot (3 mins)

**You:** "The main difference from Parking Lot is TIME. Let me explain:"

```
┌──────────────────────────────────────────────────────────────┐
│         PARKING LOT vs HOTEL BOOKING                         │
└──────────────────────────────────────────────────────────────┘

PARKING LOT:
═══════════════════════════════════════════════════════
Spot A1: [AVAILABLE] or [OCCUPIED]
Simple state: Available/Occupied
Duration: Open-ended until user exits

HOTEL BOOKING:
═══════════════════════════════════════════════════════
Room 101: Timeline-based availability

Jan 1   Jan 5   Jan 10  Jan 15  Jan 20  Jan 25
├───────┼───────┼───────┼───────┼───────┼───────┤
        [Booking A]      [Booking B]
        
Booking A: Jan 5-10 (Guest: John)
Booking B: Jan 15-20 (Guest: Mary)

KEY CHALLENGE: Check for OVERLAPPING bookings!

Overlap Scenarios:
──────────────────────────────────────────────────────
Existing:     [════════]
New booking:   [════]        ✗ OVERLAP (contained)
New booking: [════]          ✗ OVERLAP (starts before)
New booking:       [════]    ✗ OVERLAP (ends after)
New booking: [════════════]  ✗ OVERLAP (surrounds)
New booking:             [═] ✓ NO OVERLAP (after)

Overlap Formula:
(newStart < existingEnd) AND (newEnd > existingStart)
```

---

### Phase 3: Class Design (5 mins)

**You:** "The structure is similar to Parking Lot, with TIME added:"

```
┌─────────────────────────────────────────────────────────────┐
│                    CLASS STRUCTURE                           │
└─────────────────────────────────────────────────────────────┘

┌────────────────────────┐
│  HotelBookingSystem    │ (Facade - Like ParkingLot)
│  ────────────────────  │
│  - hotels: List        │
│  ────────────────────  │
│  + searchRooms()       │
│  + bookRoom()          │
│  + cancelBooking()     │
└────────┬───────────────┘
         │ 1
         │ *
         ↓
┌────────────────────────┐
│       Hotel            │
│  ────────────────────  │
│  - id: String          │
│  - name: String        │
│  - location: String    │
│  - rooms: List         │
│  ────────────────────  │
│  + searchAvailableRooms│
│    (dates, type)       │
└────────┬───────────────┘
         │ 1
         │ *
         ↓
┌────────────────────────┐
│       Room             │ (Like ParkingSpot)
│  ────────────────────  │
│  - roomNumber: String  │
│  - type: RoomType      │
│  - pricePerNight: $    │
│  - bookings: List      │
│  ────────────────────  │
│  + isAvailable(dates)  │
│  + addBooking()        │
└────────────────────────┘


┌────────────────────────┐
│      Booking           │ (NEW - time-based)
│  ────────────────────  │
│  - bookingId: String   │
│  - room: Room          │
│  - guest: User         │
│  - checkIn: Date       │
│  - checkOut: Date      │
│  - totalPrice: double  │
│  - status: BookingStatus
│  ────────────────────  │
│  + overlaps(other)     │
│  + calculatePrice()    │
└────────────────────────┘


┌────────────────────────┐
│      RoomType          │ (Enum - Like SpotType)
│  ────────────────────  │
│  - SINGLE              │
│  - DOUBLE              │
│  - DELUXE              │
│  - SUITE               │
└────────────────────────┘


┌────────────────────────┐
│   BookingStatus        │ (Enum)
│  ────────────────────  │
│  - PENDING             │
│  - CONFIRMED           │
│  - CANCELLED           │
│  - COMPLETED           │
└────────────────────────┘
```

---

### Phase 4: Core Implementation (20 mins)

**You:** "Let me implement the key classes:"

#### 1. Enums and Basic Classes

```java
public enum RoomType {
    SINGLE(100.0),
    DOUBLE(150.0),
    DELUXE(250.0),
    SUITE(400.0);
    
    private final double basePrice;
    
    RoomType(double basePrice) {
        this.basePrice = basePrice;
    }
    
    public double getBasePrice() {
        return basePrice;
    }
}

public enum BookingStatus {
    PENDING,
    CONFIRMED,
    CANCELLED,
    COMPLETED
}

public class User {
    private String userId;
    private String name;
    private String email;
    private String phone;
    
    public User(String userId, String name, String email, String phone) {
        this.userId = userId;
        this.name = name;
        this.email = email;
        this.phone = phone;
    }
    
    // Getters
    public String getUserId() { return userId; }
    public String getName() { return name; }
    public String getEmail() { return email; }
    public String getPhone() { return phone; }
}
```

---

#### 2. Booking Class (KEY CLASS - Time-based)

```java
import java.time.LocalDate;
import java.time.temporal.ChronoUnit;
import java.util.UUID;

public class Booking {
    private String bookingId;
    private Room room;
    private User guest;
    private LocalDate checkInDate;
    private LocalDate checkOutDate;
    private double totalPrice;
    private BookingStatus status;
    private LocalDate bookingDate;
    
    public Booking(Room room, User guest, LocalDate checkIn, LocalDate checkOut) {
        this.bookingId = UUID.randomUUID().toString();
        this.room = room;
        this.guest = guest;
        this.checkInDate = checkIn;
        this.checkOutDate = checkOut;
        this.status = BookingStatus.PENDING;
        this.bookingDate = LocalDate.now();
        this.totalPrice = calculateTotalPrice();
    }
    
    // CRITICAL: Check if this booking overlaps with another
    public boolean overlapsWith(Booking other) {
        // Overlap formula: (start1 < end2) AND (end1 > start2)
        return this.checkInDate.isBefore(other.checkOutDate) &&
               this.checkOutDate.isAfter(other.checkInDate);
    }
    
    public boolean overlapsWith(LocalDate checkIn, LocalDate checkOut) {
        return this.checkInDate.isBefore(checkOut) &&
               this.checkOutDate.isAfter(checkIn);
    }
    
    private double calculateTotalPrice() {
        long nights = ChronoUnit.DAYS.between(checkInDate, checkOutDate);
        return room.getPricePerNight() * nights;
    }
    
    public void confirm() {
        this.status = BookingStatus.CONFIRMED;
    }
    
    public void cancel() {
        this.status = BookingStatus.CANCELLED;
    }
    
    // Getters
    public String getBookingId() { return bookingId; }
    public Room getRoom() { return room; }
    public User getGuest() { return guest; }
    public LocalDate getCheckInDate() { return checkInDate; }
    public LocalDate getCheckOutDate() { return checkOutDate; }
    public double getTotalPrice() { return totalPrice; }
    public BookingStatus getStatus() { return status; }
    
    @Override
    public String toString() {
        return String.format("Booking{%s | Room: %s | Guest: %s | %s to %s | $%.2f | %s}",
            bookingId.substring(0, 8), room.getRoomNumber(), guest.getName(),
            checkInDate, checkOutDate, totalPrice, status);
    }
}
```

---

#### 3. Room Class (Like ParkingSpot with bookings list)

```java
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.locks.ReentrantLock;

public class Room {
    private String roomNumber;
    private RoomType type;
    private double pricePerNight;
    private List<Booking> bookings;
    private ReentrantLock lock;
    
    public Room(String roomNumber, RoomType type) {
        this.roomNumber = roomNumber;
        this.type = type;
        this.pricePerNight = type.getBasePrice();
        this.bookings = new ArrayList<>();
        this.lock = new ReentrantLock();
    }
    
    // Check if room is available for given dates
    public boolean isAvailable(LocalDate checkIn, LocalDate checkOut) {
        lock.lock();
        try {
            for (Booking booking : bookings) {
                // Skip cancelled bookings
                if (booking.getStatus() == BookingStatus.CANCELLED) {
                    continue;
                }
                
                // Check for overlap
                if (booking.overlapsWith(checkIn, checkOut)) {
                    return false;
                }
            }
            return true;
        } finally {
            lock.unlock();
        }
    }
    
    // Add booking (with thread safety)
    public synchronized boolean addBooking(Booking booking) {
        lock.lock();
        try {
            // Double-check availability
            if (!isAvailable(booking.getCheckInDate(), booking.getCheckOutDate())) {
                return false;
            }
            
            bookings.add(booking);
            return true;
        } finally {
            lock.unlock();
        }
    }
    
    // Cancel booking
    public void cancelBooking(String bookingId) {
        lock.lock();
        try {
            for (Booking booking : bookings) {
                if (booking.getBookingId().equals(bookingId)) {
                    booking.cancel();
                    break;
                }
            }
        } finally {
            lock.unlock();
        }
    }
    
    public List<Booking> getBookings() {
        return new ArrayList<>(bookings); // Return copy for thread safety
    }
    
    // Getters
    public String getRoomNumber() { return roomNumber; }
    public RoomType getType() { return type; }
    public double getPricePerNight() { return pricePerNight; }
    
    @Override
    public String toString() {
        return String.format("Room{%s | %s | $%.2f/night}", 
            roomNumber, type, pricePerNight);
    }
}
```

---

#### 4. Hotel Class

```java
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

public class Hotel {
    private String hotelId;
    private String name;
    private String location;
    private List<Room> rooms;
    
    public Hotel(String hotelId, String name, String location) {
        this.hotelId = hotelId;
        this.name = name;
        this.location = location;
        this.rooms = new ArrayList<>();
    }
    
    public void addRoom(Room room) {
        rooms.add(room);
    }
    
    // Search available rooms by type and dates
    public List<Room> searchAvailableRooms(RoomType type, 
                                          LocalDate checkIn, 
                                          LocalDate checkOut) {
        return rooms.stream()
            .filter(room -> room.getType() == type)
            .filter(room -> room.isAvailable(checkIn, checkOut))
            .collect(Collectors.toList());
    }
    
    // Get all available rooms (any type)
    public List<Room> getAllAvailableRooms(LocalDate checkIn, LocalDate checkOut) {
        return rooms.stream()
            .filter(room -> room.isAvailable(checkIn, checkOut))
            .collect(Collectors.toList());
    }
    
    public Room getRoomByNumber(String roomNumber) {
        return rooms.stream()
            .filter(room -> room.getRoomNumber().equals(roomNumber))
            .findFirst()
            .orElse(null);
    }
    
    // Getters
    public String getHotelId() { return hotelId; }
    public String getName() { return name; }
    public String getLocation() { return location; }
    public List<Room> getRooms() { return rooms; }
    
    public void displayInventory() {
        System.out.println("\n=== " + name + " (" + location + ") ===");
        System.out.println("Total Rooms: " + rooms.size());
        
        for (RoomType type : RoomType.values()) {
            long count = rooms.stream().filter(r -> r.getType() == type).count();
            System.out.println("  " + type + ": " + count + " rooms");
        }
    }
}
```

---

#### 5. Hotel Booking System (Main Facade)

```java
import java.time.LocalDate;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class HotelBookingSystem {
    private static HotelBookingSystem instance;
    private Map<String, Hotel> hotels;
    private Map<String, Booking> bookings; // bookingId -> Booking
    private Map<String, List<Booking>> userBookings; // userId -> List<Booking>
    
    private HotelBookingSystem() {
        this.hotels = new HashMap<>();
        this.bookings = new ConcurrentHashMap<>();
        this.userBookings = new ConcurrentHashMap<>();
    }
    
    public static synchronized HotelBookingSystem getInstance() {
        if (instance == null) {
            instance = new HotelBookingSystem();
        }
        return instance;
    }
    
    public void addHotel(Hotel hotel) {
        hotels.put(hotel.getHotelId(), hotel);
        System.out.println("Added hotel: " + hotel.getName());
    }
    
    // Search rooms across all hotels
    public List<Room> searchRooms(String location, 
                                   RoomType type,
                                   LocalDate checkIn,
                                   LocalDate checkOut) {
        List<Room> availableRooms = new ArrayList<>();
        
        for (Hotel hotel : hotels.values()) {
            if (hotel.getLocation().equalsIgnoreCase(location)) {
                availableRooms.addAll(
                    hotel.searchAvailableRooms(type, checkIn, checkOut)
                );
            }
        }
        
        return availableRooms;
    }
    
    // Book a room (CRITICAL - prevent double booking)
    public synchronized Booking bookRoom(String hotelId,
                                        String roomNumber,
                                        User guest,
                                        LocalDate checkIn,
                                        LocalDate checkOut) {
        Hotel hotel = hotels.get(hotelId);
        if (hotel == null) {
            System.out.println("Hotel not found");
            return null;
        }
        
        Room room = hotel.getRoomByNumber(roomNumber);
        if (room == null) {
            System.out.println("Room not found");
            return null;
        }
        
        // Validate dates
        if (checkIn.isAfter(checkOut) || checkIn.isBefore(LocalDate.now())) {
            System.out.println("Invalid dates");
            return null;
        }
        
        // Create booking
        Booking booking = new Booking(room, guest, checkIn, checkOut);
        
        // Try to add booking to room (thread-safe)
        if (room.addBooking(booking)) {
            booking.confirm();
            bookings.put(booking.getBookingId(), booking);
            
            // Track user bookings
            userBookings.computeIfAbsent(guest.getUserId(), k -> new ArrayList<>())
                       .add(booking);
            
            System.out.println("✓ Booking confirmed: " + booking.getBookingId());
            System.out.println("  Room: " + roomNumber);
            System.out.println("  Dates: " + checkIn + " to " + checkOut);
            System.out.println("  Total: $" + booking.getTotalPrice());
            
            return booking;
        } else {
            System.out.println("✗ Room not available for selected dates");
            return null;
        }
    }
    
    // Cancel booking
    public boolean cancelBooking(String bookingId) {
        Booking booking = bookings.get(bookingId);
        
        if (booking == null) {
            System.out.println("Booking not found");
            return false;
        }
        
        if (booking.getStatus() == BookingStatus.CANCELLED) {
            System.out.println("Booking already cancelled");
            return false;
        }
        
        // Cancel in room's booking list
        booking.getRoom().cancelBooking(bookingId);
        
        System.out.println("✓ Booking cancelled: " + bookingId);
        return true;
    }
    
    // Get user's booking history
    public List<Booking> getUserBookings(String userId) {
        return userBookings.getOrDefault(userId, new ArrayList<>());
    }
    
    // Get booking details
    public Booking getBooking(String bookingId) {
        return bookings.get(bookingId);
    }
    
    public void displaySystemStats() {
        System.out.println("\n╔════════════════════════════════════════╗");
        System.out.println("║    HOTEL BOOKING SYSTEM STATS          ║");
        System.out.println("╚════════════════════════════════════════╝");
        System.out.println("Total Hotels: " + hotels.size());
        System.out.println("Total Bookings: " + bookings.size());
        
        long confirmed = bookings.values().stream()
            .filter(b -> b.getStatus() == BookingStatus.CONFIRMED)
            .count();
        long cancelled = bookings.values().stream()
            .filter(b -> b.getStatus() == BookingStatus.CANCELLED)
            .count();
        
        System.out.println("Confirmed: " + confirmed);
        System.out.println("Cancelled: " + cancelled);
        System.out.println();
    }
}
```

---

### Phase 5: Usage Example (5 mins)

**You:** "Here's a complete demo:"

```java
import java.time.LocalDate;
import java.util.List;

public class HotelBookingDemo {
    public static void main(String[] args) throws InterruptedException {
        System.out.println("╔══════════════════════════════════════════╗");
        System.out.println("║    HOTEL BOOKING SYSTEM DEMO             ║");
        System.out.println("╚══════════════════════════════════════════╝\n");
        
        HotelBookingSystem system = HotelBookingSystem.getInstance();
        
        // Setup: Create hotels
        Hotel taj = new Hotel("H001", "Taj Hotel", "Mumbai");
        taj.addRoom(new Room("101", RoomType.SINGLE));
        taj.addRoom(new Room("102", RoomType.SINGLE));
        taj.addRoom(new Room("201", RoomType.DOUBLE));
        taj.addRoom(new Room("202", RoomType.DOUBLE));
        taj.addRoom(new Room("301", RoomType.SUITE));
        
        Hotel oberoi = new Hotel("H002", "Oberoi Hotel", "Mumbai");
        oberoi.addRoom(new Room("101", RoomType.DELUXE));
        oberoi.addRoom(new Room("102", RoomType.SUITE));
        
        system.addHotel(taj);
        system.addHotel(oberoi);
        
        taj.displayInventory();
        oberoi.displayInventory();
        
        // Create users
        User alice = new User("U001", "Alice", "alice@email.com", "1234567890");
        User bob = new User("U002", "Bob", "bob@email.com", "9876543210");
        
        // Scenario 1: Search and book
        System.out.println("\n--- SCENARIO 1: Search & Book ---");
        LocalDate checkIn1 = LocalDate.now().plusDays(1);
        LocalDate checkOut1 = LocalDate.now().plusDays(3);
        
        List<Room> available = system.searchRooms("Mumbai", RoomType.DOUBLE, 
                                                   checkIn1, checkOut1);
        System.out.println("Available DOUBLE rooms: " + available.size());
        
        // Alice books room 201
        Booking booking1 = system.bookRoom("H001", "201", alice, checkIn1, checkOut1);
        
        // Scenario 2: Try to book same room for overlapping dates
        System.out.println("\n--- SCENARIO 2: Overlapping Booking (Should Fail) ---");
        LocalDate checkIn2 = LocalDate.now().plusDays(2); // Overlaps with booking1
        LocalDate checkOut2 = LocalDate.now().plusDays(4);
        
        Booking booking2 = system.bookRoom("H001", "201", bob, checkIn2, checkOut2);
        // This should fail - room already booked
        
        // Scenario 3: Book same room for non-overlapping dates
        System.out.println("\n--- SCENARIO 3: Non-Overlapping Booking (Should Succeed) ---");
        LocalDate checkIn3 = LocalDate.now().plusDays(5); // After booking1
        LocalDate checkOut3 = LocalDate.now().plusDays(7);
        
        Booking booking3 = system.bookRoom("H001", "201", bob, checkIn3, checkOut3);
        // This should succeed
        
        // Scenario 4: Concurrent bookings (race condition test)
        System.out.println("\n--- SCENARIO 4: Concurrent Bookings ---");
        
        Thread t1 = new Thread(() -> {
            User user1 = new User("U003", "Charlie", "charlie@email.com", "111");
            system.bookRoom("H001", "101", user1, 
                LocalDate.now().plusDays(10), LocalDate.now().plusDays(12));
        });
        
        Thread t2 = new Thread(() -> {
            User user2 = new User("U004", "David", "david@email.com", "222");
            system.bookRoom("H001", "101", user2,
                LocalDate.now().plusDays(10), LocalDate.now().plusDays(12));
        });
        
        t1.start();
        t2.start();
        t1.join();
        t2.join();
        
        System.out.println("Only one should have succeeded!");
        
        // Scenario 5: Cancellation
        if (booking1 != null) {
            System.out.println("\n--- SCENARIO 5: Cancellation ---");
            system.cancelBooking(booking1.getBookingId());
            
            // Now this room should be available again
            System.out.println("\nAfter cancellation, booking same dates again:");
            Booking booking4 = system.bookRoom("H001", "201", bob, checkIn1, checkOut1);
        }
        
        // Show user booking history
        System.out.println("\n--- Alice's Booking History ---");
        List<Booking> aliceBookings = system.getUserBookings(alice.getUserId());
        for (Booking b : aliceBookings) {
            System.out.println(b);
        }
        
        System.out.println("\n--- Bob's Booking History ---");
        List<Booking> bobBookings = system.getUserBookings(bob.getUserId());
        for (Booking b : bobBookings) {
            System.out.println(b);
        }
        
        // Final stats
        system.displaySystemStats();
    }
}
```

---

### Phase 6: Key Differences from Parking Lot (3 mins)

**You:** "Let me summarize the key differences:"

```
┌──────────────────────────────────────────────────────────────┐
│      PARKING LOT vs HOTEL BOOKING COMPARISON                 │
└──────────────────────────────────────────────────────────────┘

Aspect              Parking Lot           Hotel Booking
──────────────────────────────────────────────────────────────
Availability        Instant (now)         Date range
State               Boolean (free/busy)   Timeline-based
Booking Duration    Open-ended            Fixed (check-in/out)
Key Challenge       Concurrency           Time overlaps
Locking Logic       Lock spot instantly   Check date conflicts
Price Calculation   Hourly * duration     Per night * nights
Cancellation        Release spot          Mark cancelled, keep record
Search Query        By type only          By type + dates + location

CODE DIFFERENCES:
══════════════════════════════════════════════════════════════

1. Spot vs Room:
   spot.isAvailable() → boolean
   room.isAvailable(dates) → check all bookings

2. Booking:
   Parking: One active booking per spot
   Hotel: Multiple bookings per room (different dates)

3. Overlap Check (CRITICAL):
   boolean overlaps(checkIn1, checkOut1, checkIn2, checkOut2) {
       return checkIn1.isBefore(checkOut2) && 
              checkOut1.isAfter(checkIn2);
   }

4. Thread Safety:
   Both need it, but hotel needs it per date range, not just instant
```

---

## KEY TAKEAWAYS

### Same as Parking Lot:
✅ **Singleton** - System controller
✅ **Factory** - Can create different hotel types
✅ **Thread Safety** - Prevent double booking
✅ **Booking flow** - Search → Reserve → Confirm

### New Concepts:
✅ **Time-based availability** - Check date ranges
✅ **Overlap detection** - Critical algorithm
✅ **Booking history** - Keep past bookings
✅ **Cancellation** - Don't delete, mark status

### SOLID Principles:
✅ **Single Responsibility** - Each class has one job
✅ **Open/Closed** - Easy to add new room types
✅ **Extensibility** - Add amenities, pricing strategies

---

## COMMON MISTAKES TO AVOID

❌ Not checking for overlapping bookings
❌ Deleting cancelled bookings (keep for history)
❌ Not handling concurrent requests (race conditions)
❌ Forgetting to validate dates (check-in < check-out)
❌ Not considering time zones (if global)
❌ Inefficient overlap checking (O(n²) vs O(n))

---

## FOLLOW-UP QUESTIONS

**Interviewer:** "How would you add pricing strategies (weekend rates, peak season)?"

**You:**
```java
public interface PricingStrategy {
    double calculatePrice(RoomType type, LocalDate checkIn, LocalDate checkOut);
}

public class DynamicPricingStrategy implements PricingStrategy {
    @Override
    public double calculatePrice(RoomType type, LocalDate checkIn, LocalDate checkOut) {
        double basePrice = type.getBasePrice();
        long nights = ChronoUnit.DAYS.between(checkIn, checkOut);
        
        double total = 0;
        for (LocalDate date = checkIn; date.isBefore(checkOut); date = date.plusDays(1)) {
            double dayPrice = basePrice;
            
            // Weekend multiplier
            if (date.getDayOfWeek().getValue() >= 6) {
                dayPrice *= 1.5;
            }
            
            // Peak season (e.g., December)
            if (date.getMonthValue() == 12) {
                dayPrice *= 2.0;
            }
            
            total += dayPrice;
        }
        
        return total;
    }
}
```

**Interviewer:** "How would you handle overbooking?"

**You:**
```java
public class OverbookingStrategy {
    private final double overbookingPercentage = 0.1; // 10% overbook
    
    public boolean allowBooking(Room room, LocalDate checkIn, LocalDate checkOut) {
        long confirmedBookings = room.getBookings().stream()
            .filter(b -> b.getStatus() == BookingStatus.CONFIRMED)
            .filter(b -> b.overlapsWith(checkIn, checkOut))
            .count();
        
        int maxAllowed = (int)(room.getCapacity() * (1 + overbookingPercentage));
        
        return confirmedBookings < maxAllowed;
    }
}
```

---

## SOLID PRINCIPLES IN DEPTH

**You:** "Let me explain how SOLID principles apply to hotel booking - it's very similar to Parking Lot but with time added!"

---

### 1. Single Responsibility Principle (SRP)

**Purpose:** Each class should have only ONE reason to change.

**Problem it solves:**
Without SRP, booking logic becomes tangled:
```java
// BAD: Hotel class doing everything
class Hotel {
    // Room management
    public void addRoom(Room r) { ... }
    
    // Booking logic
    public Booking bookRoom(User u, LocalDate checkIn, LocalDate checkOut) { ... }
    
    // Pricing logic
    public double calculatePrice(Room r, LocalDate checkIn, LocalDate checkOut) { ... }
    
    // Payment processing
    public void processPayment(double amount) { ... }
    
    // Email notifications
    public void sendConfirmationEmail(Booking b) { ... }
}
// Too many responsibilities! Changing pricing affects hotel class.
```

**Advantages:**
- ✅ **Clear ownership** - Each class has one clear job
- ✅ **Easy to test** - Test booking separately from pricing
- ✅ **Parallel development** - Different devs work on different classes
- ✅ **Localized changes** - Fix pricing without touching booking logic

**In our design:**
```java
// GOOD: Separated responsibilities

// Room: ONLY stores room data and manages its bookings
class Room {
    private String roomNumber;
    private RoomType type;
    private List<Booking> bookings;
    
    public boolean isAvailable(LocalDate checkIn, LocalDate checkOut) { ... }
}

// Booking: ONLY stores booking session data
class Booking {
    private Room room;
    private User guest;
    private LocalDate checkIn, checkOut;
    
    public boolean overlapsWith(Booking other) { ... }
}

// Hotel: ONLY manages rooms and availability search
class Hotel {
    private List<Room> rooms;
    
    public List<Room> searchAvailableRooms(RoomType type, LocalDate checkIn, LocalDate checkOut) { ... }
}

// HotelBookingSystem: ONLY coordinates booking operations (Facade)
class HotelBookingSystem {
    public Booking bookRoom(String hotelId, String roomNumber, User guest, 
                           LocalDate checkIn, LocalDate checkOut) { ... }
}

// PricingStrategy: ONLY calculates pricing (separate)
interface PricingStrategy {
    double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut);
}

// NotificationService: ONLY sends notifications (separate)
class NotificationService {
    public void sendConfirmation(Booking booking) { ... }
}
```

**Interview tip:** "If I need to change pricing logic, I only touch `PricingStrategy`. If I add a new room type, I only modify `RoomType` enum and Room class. Each class has one clear responsibility."

---

### 2. Open/Closed Principle (OCP)

**Purpose:** Classes should be OPEN for extension but CLOSED for modification.

**Problem it solves:**
Without OCP, adding features requires modifying existing code:
```java
// BAD: Hard-coded pricing logic
class HotelBookingSystem {
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        long nights = ChronoUnit.DAYS.between(checkIn, checkOut);
        double basePrice = room.getPricePerNight() * nights;
        
        // If weekend, add 50%
        // If peak season, add 100%
        // If holiday, add 150%
        
        // To add dynamic pricing, you must MODIFY this method - RISKY!
        return basePrice;
    }
}
```

**Advantages:**
- ✅ **Zero regression** - Existing pricing unaffected
- ✅ **Easy to add strategies** - Just create new pricing class
- ✅ **A/B testing** - Deploy new pricing without changing core
- ✅ **Stable core** - Booking system never changes

**In our design:**
```java
// GOOD: Strategy pattern for extensibility

interface PricingStrategy {
    double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut);
}

class StandardPricing implements PricingStrategy {
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        long nights = ChronoUnit.DAYS.between(checkIn, checkOut);
        return room.getPricePerNight() * nights;
    }
}

class WeekendPricing implements PricingStrategy {
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        double total = 0;
        for (LocalDate date = checkIn; date.isBefore(checkOut); date = date.plusDays(1)) {
            double dayPrice = room.getPricePerNight();
            if (date.getDayOfWeek().getValue() >= 6) {  // Weekend
                dayPrice *= 1.5;
            }
            total += dayPrice;
        }
        return total;
    }
}

class DynamicPricing implements PricingStrategy {
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        // Consider: weekends, holidays, peak season, demand, competitor prices
    }
}

// NEW: Add Loyalty Pricing - zero changes to existing code!
class LoyaltyPricing implements PricingStrategy {
    private Map<User, Double> discountMap;
    
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        double basePrice = new StandardPricing().calculatePrice(room, checkIn, checkOut);
        double discount = discountMap.getOrDefault(room.getUser(), 0.0);
        return basePrice * (1 - discount);
    }
}

class HotelBookingSystem {
    private PricingStrategy pricingStrategy = new StandardPricing();
    
    public void setPricingStrategy(PricingStrategy strategy) {
        this.pricingStrategy = strategy;
    }
}
```

**Interview tip:** "To add loyalty discounts, I create `LoyaltyPricing` implementing the interface. Zero changes to `HotelBookingSystem`. The system is closed for modification but open for extension."

---

### 3. Liskov Substitution Principle (LSP)

**Purpose:** Subclasses must be substitutable for their parent classes without breaking behavior.

**Problem it solves:**
Without LSP, some strategies violate contracts:
```java
// BAD: Violates LSP
interface PricingStrategy {
    double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut);
    // Contract: Returns positive price or throws exception
}

class StandardPricing implements PricingStrategy {
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        return room.getPricePerNight() * nights;  // Returns positive price
    }
}

class BrokenPricing implements PricingStrategy {
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        return -100.0;  // BREAKS CONTRACT! Negative price!
    }
}

// Code expecting positive price will break:
PricingStrategy pricing = new BrokenPricing();
double price = pricing.calculatePrice(room, checkIn, checkOut);
if (price > 0) {  // FALSE when it should be TRUE
    processPayment(price);  // Never executes!
}
```

**Advantages:**
- ✅ **Predictable behavior** - All strategies work the same way
- ✅ **Polymorphism works** - Can swap strategies at runtime
- ✅ **Testing is easy** - Mock strategies behave like real ones
- ✅ **No surprises** - Code doesn't break when switching implementations

**In our design:**
```java
// GOOD: All strategies honor the contract

interface PricingStrategy {
    double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut);
    // Contract: Returns non-negative price or throws IllegalArgumentException
}

class StandardPricing implements PricingStrategy {
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        if (checkIn.isAfter(checkOut)) {
            throw new IllegalArgumentException("Invalid dates");  // ✓ Clear exception
        }
        long nights = ChronoUnit.DAYS.between(checkIn, checkOut);
        return room.getPricePerNight() * nights;  // ✓ Returns non-negative price
    }
}

class DynamicPricing implements PricingStrategy {
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        if (checkIn.isAfter(checkOut)) {
            throw new IllegalArgumentException("Invalid dates");  // ✓ Clear exception
        }
        // Complex pricing logic
        return calculatedPrice;  // ✓ Returns non-negative price
    }
}

class FreePricing implements PricingStrategy {
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        return 0.0;  // ✓ Zero is valid (promotional pricing)
    }
}

// Polymorphism works perfectly:
PricingStrategy pricing = new StandardPricing();  // Or Dynamic or Free
double price = pricing.calculatePrice(room, checkIn, checkOut);  // Works for ANY strategy
processPayment(price);  // No surprises, always valid price
```

**Interview tip:** "Any code that works with `PricingStrategy` will work with `Standard`, `Dynamic`, or `Free` pricing. They all honor the contract - `calculatePrice()` always returns a non-negative price or throws a clear exception."

---

### 4. Interface Segregation Principle (ISP)

**Purpose:** Clients should not be forced to depend on interfaces they don't use.

**Problem it solves:**
Without ISP, interfaces become bloated:
```java
// BAD: Fat interface forces unnecessary implementations
interface BookingOperations {
    Booking createBooking(User u, Room r, LocalDate checkIn, LocalDate checkOut);
    void cancelBooking(String bookingId);
    void modifyBooking(String bookingId, LocalDate newCheckIn, LocalDate newCheckOut);
    List<Booking> getUserBookings(String userId);
    double calculateRefund(String bookingId);   // Not all systems support refunds
    void transferBooking(String bookingId, User newUser);  // Not all support transfers
    void addInsurance(String bookingId);        // Not all offer insurance
}

// Simple booking system must implement ALL methods!
class SimpleBookingSystem implements BookingOperations {
    @Override
    public double calculateRefund(String bookingId) { 
        throw new UnsupportedOperationException();  // Forced!
    }
    
    @Override
    public void transferBooking(String bookingId, User newUser) {
        throw new UnsupportedOperationException();  // Forced!
    }
}
```

**Advantages:**
- ✅ **Lean interfaces** - Only necessary methods
- ✅ **Better cohesion** - Related methods together
- ✅ **No dummy code** - No forced implementations
- ✅ **Clear contracts** - Interface tells you what to expect

**In our design:**
```java
// GOOD: Segregated interfaces

// Core: Every booking system must implement this
interface BookingOperations {
    Booking createBooking(User user, Room room, LocalDate checkIn, LocalDate checkOut);
    void cancelBooking(String bookingId);
    Booking getBooking(String bookingId);
}

// Optional: Only for systems that support modifications
interface ModifiableBooking extends BookingOperations {
    void modifyCheckInDate(String bookingId, LocalDate newCheckIn);
    void modifyCheckOutDate(String bookingId, LocalDate newCheckOut);
}

// Optional: Only for systems with refund policies
interface RefundableBooking extends BookingOperations {
    double calculateRefund(String bookingId);
    void processRefund(String bookingId);
}

// Optional: Only for systems with insurance
interface InsurableBooking extends BookingOperations {
    void addInsurance(String bookingId, InsuranceType type);
    void removeInsurance(String bookingId);
}

// Implement only what you need:

// Basic hotel: Just core operations
class BasicHotelBooking implements BookingOperations {
    // Only create, cancel, get - nothing else!
}

// Standard hotel: Core + Modifications + Refunds
class StandardHotelBooking implements BookingOperations, 
                                       ModifiableBooking, 
                                       RefundableBooking {
    // Supports modifications and refunds
}

// Premium hotel: Everything
class PremiumHotelBooking implements BookingOperations,
                                      ModifiableBooking,
                                      RefundableBooking,
                                      InsurableBooking {
    // Full-featured booking system
}
```

**Interview tip:** "Core interface has only basic booking operations. If a system supports refunds, it implements `RefundableBooking`. If it supports insurance, it implements `InsurableBooking`. Clients depend only on what they need."

---

### 5. Dependency Inversion Principle (DIP)

**Purpose:** High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Problem it solves:**
Without DIP, high-level code is tightly coupled:
```java
// BAD: HotelBookingSystem tightly coupled to concrete pricing
class HotelBookingSystem {
    private StandardPricing pricing = new StandardPricing();  // TIGHT COUPLING!
    
    public Booking bookRoom(User user, Room room, LocalDate checkIn, LocalDate checkOut) {
        double price = pricing.calculatePrice(room, checkIn, checkOut);
        // Can't switch to Dynamic Pricing without modifying this class!
    }
}
```

**Advantages:**
- ✅ **Loose coupling** - Easy to swap pricing strategies
- ✅ **Testability** - Inject mock pricing for testing
- ✅ **Flexibility** - Change strategies at runtime
- ✅ **Maintainability** - Low-level changes don't affect high-level

**In our design:**
```java
// GOOD: Depend on abstraction (interface)

interface PricingStrategy {
    double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut);
}

class StandardPricing implements PricingStrategy { ... }
class DynamicPricing implements PricingStrategy { ... }
class LoyaltyPricing implements PricingStrategy { ... }

class HotelBookingSystem {
    private Map<String, Hotel> hotels;
    private PricingStrategy pricingStrategy;  // Interface, not concrete class!
    
    // Dependency Injection via setter
    public void setPricingStrategy(PricingStrategy strategy) {
        this.pricingStrategy = strategy;
    }
    
    public synchronized Booking bookRoom(String hotelId, String roomNumber,
                                        User guest, LocalDate checkIn, LocalDate checkOut) {
        Hotel hotel = hotels.get(hotelId);
        Room room = hotel.getRoomByNumber(roomNumber);
        
        // Calculate price using injected strategy - don't care about implementation!
        double price = pricingStrategy.calculatePrice(room, checkIn, checkOut);
        
        Booking booking = new Booking(room, guest, checkIn, checkOut, price);
        room.addBooking(booking);
        
        return booking;
    }
}

// Production usage - inject real pricing:
HotelBookingSystem system = HotelBookingSystem.getInstance();
system.setPricingStrategy(new DynamicPricing());

// During promotions - switch pricing:
system.setPricingStrategy(new LoyaltyPricing());

// Test usage - inject mock pricing:
class MockPricing implements PricingStrategy {
    @Override
    public double calculatePrice(Room room, LocalDate checkIn, LocalDate checkOut) {
        return 100.0;  // Fixed price for testing
    }
}

HotelBookingSystem testSystem = HotelBookingSystem.getInstance();
testSystem.setPricingStrategy(new MockPricing());
```

**Interview tip:** "HotelBookingSystem doesn't know if it's using Standard or Dynamic pricing - it just calls `calculatePrice()` on the interface. I can swap strategies at runtime. For testing, I inject a mock that returns fixed prices."

---

## REAL-WORLD APPLICATIONS

✅ **Hotels** - OYO, Marriott, Airbnb
✅ **Restaurants** - Table booking (OpenTable)
✅ **Flights** - Seat reservations
✅ **Events** - Ticket booking (BookMyShow)
✅ **Venues** - Conference room booking
✅ **Rentals** - Car rental, equipment rental

---

## KEY TAKEAWAYS

### SOLID Principles Applied:
✅ **Single Responsibility (SRP)** - Room manages availability, Booking stores session, PricingStrategy calculates fees
✅ **Open/Closed (OCP)** - Add new pricing strategies without modifying core booking system
✅ **Liskov Substitution (LSP)** - All PricingStrategy implementations are interchangeable
✅ **Interface Segregation (ISP)** - Separate interfaces for core booking, modifications, refunds, insurance
✅ **Dependency Inversion (DIP)** - HotelBookingSystem depends on PricingStrategy interface, not concrete implementations

---

**END OF HOTEL BOOKING SYSTEM GUIDE**

This is **90% similar to Parking Lot** - just add TIME!
