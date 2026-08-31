# 🛗 Elevator System - Low Level Design Interview Guide
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

## **Algorithm Used**: LOOK (Elevator Scheduling Algorithm)

**Interviewer**: "Design an elevator system for a building."

**You**: "Great question! Let me clarify the scope. How many floors and how many elevators? Should I handle features like emergency mode, maintenance, or VIP priority?"

**Interviewer**: "10 floors, 3 elevators. Focus on efficient request dispatching and elevator movement."

**You**: "Perfect. The key challenges here are:
1. **Request Dispatching**: When user presses UP on Floor 5, which elevator responds?
2. **Elevator Scheduling**: Which floor to visit next? (LOOK algorithm)
3. **Direction Management**: Minimize direction changes

I'll use **Strategy Pattern** for dispatching algorithms and the **LOOK algorithm** for elevator movement. Let me walk you through..."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ELEVATOR SYSTEM ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────┐
                            │   BUILDING   │
                            │              │
                            │  Floors: 10  │
                            └──────┬───────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │   FLOOR 1    │  │   FLOOR 2    │  │   FLOOR 10   │
         │              │  │              │  │              │
         │ ExternalBtn  │  │ ExternalBtn  │  │ ExternalBtn  │
         │  (UP/DOWN)   │  │  (UP/DOWN)   │  │  (UP/DOWN)   │
         └──────────────┘  └──────────────┘  └──────────────┘
                 │                 │                 │
                 └─────────────────┼─────────────────┘
                                   ▼
                        ┌──────────────────────┐
                        │ EXTERNAL DISPATCHER  │
                        │                      │
                        │ Algorithm: Choose    │
                        │ - Nearest Elevator   │
                        │ - Odd/Even Split     │
                        │ - Zone-based         │
                        └──────────┬───────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │ ELEVATOR 1   │  │ ELEVATOR 2   │  │ ELEVATOR 3   │
         │              │  │              │  │              │
         │ Controller   │  │ Controller   │  │ Controller   │
         │ Display      │  │ Display      │  │ Display      │
         │ InternalBtn  │  │ InternalBtn  │  │ InternalBtn  │
         │ Door         │  │ Door         │  │ Door         │
         └──────────────┘  └──────────────┘  └──────────────┘

         ELEVATOR CONTROLLER (per elevator):
         ┌─────────────────────────────────┐
         │  Current Floor: 3               │
         │  Direction: UP                  │
         │  Status: MOVING                 │
         │                                 │
         │  Pending Requests:              │
         │  ┌───────────────────────────┐ │
         │  │ UP Queue (MinHeap):       │ │
         │  │   [4, 6, 8]              │ │
         │  │                           │ │
         │  │ DOWN Queue (MaxHeap):     │ │
         │  │   [7, 5, 2]              │ │
         │  └───────────────────────────┘ │
         └─────────────────────────────────┘
```

### **Why This Design?**

**You**: "See, I've separated concerns:

1. **External Dispatcher**: Decides WHICH elevator responds to floor button press. This is pluggable—can use nearest elevator, load balancing, or zone-based.

2. **Elevator Controller**: Each elevator independently manages its own request queue. Uses **LOOK algorithm** (like disk scheduling):
   - Continue in current direction until no more requests
   - Then reverse direction

3. **Priority Queues**: 
   - UP requests: Min-Heap (visit lowest floor first when going UP)
   - DOWN requests: Max-Heap (visit highest floor first when going DOWN)

This design allows adding more elevators without changing core logic."

---

## 2. API Design

### **2.1 Floor Request APIs**

```http
POST /api/v1/buildings/{buildingId}/floors/{floorNumber}/call
Request:
{
  "direction": "UP",  // or "DOWN"
  "timestamp": "2026-08-31T10:00:00Z"
}

Response: 200 OK
{
  "requestId": "req-1234",
  "assignedElevator": "elevator-2",
  "estimatedArrivalTime": "30s",
  "currentFloor": 1,
  "direction": "UP"
}

---

GET /api/v1/buildings/{buildingId}/elevators/status
Response: 200 OK
{
  "elevators": [
    {
      "elevatorId": "elevator-1",
      "currentFloor": 3,
      "direction": "UP",
      "status": "MOVING",
      "occupancy": 5,
      "maxCapacity": 8,
      "pendingStops": [4, 7, 9]
    },
    {
      "elevatorId": "elevator-2",
      "currentFloor": 8,
      "direction": "DOWN",
      "status": "IDLE",
      "occupancy": 0,
      "pendingStops": []
    }
  ]
}
```

### **2.2 Internal Elevator APIs**

```http
POST /api/v1/elevators/{elevatorId}/selectFloor
Request:
{
  "destinationFloor": 7,
  "userId": "user-5678"  // Optional: for analytics
}

Response: 200 OK
{
  "elevatorId": "elevator-1",
  "addedToQueue": true,
  "queuePosition": 2,
  "estimatedArrivalTime": "45s"
}

---

GET /api/v1/elevators/{elevatorId}/display
Response: 200 OK
{
  "currentFloor": 5,
  "direction": "UP",
  "nextStop": 7,
  "doorStatus": "CLOSED"
}

---

POST /api/v1/elevators/{elevatorId}/emergency
Request:
{
  "type": "FIRE",  // or "EARTHQUAKE", "POWER_OUTAGE"
  "initiatedBy": "system"
}

Response: 200 OK
{
  "elevatorId": "elevator-1",
  "emergencyMode": true,
  "action": "MOVING_TO_GROUND_FLOOR",
  "allRequestsCancelled": true
}
```

### **Why This API Design?**

**You**: "Notice:
1. **Asynchronous by nature**: APIs don't wait for elevator arrival—return estimated time instead
2. **WebSocket for real-time updates**: Clients subscribe to elevator position changes
3. **Emergency override**: Critical for safety—cancels all requests, moves to ground floor"

---

## 3. ER Diagram & Database Design

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            ER DIAGRAM                                     │
└───────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │  BUILDING    │
    │──────────────│
    │*buildingId   │
    │ name         │
    │ totalFloors  │
    │ address      │
    └──────┬───────┘
           │
           │ 1:N
           ▼
    ┌──────────────┐                    ┌──────────────┐
    │  ELEVATOR    │                    │    FLOOR     │
    │──────────────│                    │──────────────│
    │*elevatorId   │                    │*floorId      │
    │ buildingId(FK)│                   │ buildingId(FK│
    │ currentFloor │                    │ floorNumber  │
    │ direction    │                    │ hasExternalBtn│
    │ status       │                    └──────────────┘
    │ maxCapacity  │
    │ maxWeight    │
    └──────┬───────┘
           │
           │ 1:N
           ▼
    ┌──────────────┐
    │   REQUEST    │
    │──────────────│
    │*requestId    │
    │ elevatorId(FK│
    │ sourceFloor  │
    │ destFloor    │
    │ direction    │
    │ type         │  // EXTERNAL or INTERNAL
    │ status       │
    │ createdAt    │
    │ completedAt  │
    └──────────────┘

    ┌──────────────┐
    │ MAINTENANCE  │
    │──────────────│
    │*maintenanceId│
    │ elevatorId(FK│
    │ startTime    │
    │ endTime      │
    │ type         │
    │ notes        │
    └──────────────┘
```

### **Schema Details**

```sql
CREATE TABLE elevators (
    elevator_id VARCHAR(50) PRIMARY KEY,
    building_id VARCHAR(50) NOT NULL,
    current_floor INT NOT NULL DEFAULT 1,
    direction VARCHAR(10) NOT NULL,  -- 'UP', 'DOWN', 'IDLE'
    status VARCHAR(20) NOT NULL,  -- 'MOVING', 'STOPPED', 'MAINTENANCE', 'EMERGENCY'
    max_capacity INT DEFAULT 8,
    max_weight_kg INT DEFAULT 680,  -- ~85kg per person
    last_maintenance TIMESTAMP,
    
    CHECK (direction IN ('UP', 'DOWN', 'IDLE')),
    CHECK (status IN ('MOVING', 'STOPPED', 'IDLE', 'MAINTENANCE', 'EMERGENCY')),
    INDEX idx_building_status (building_id, status)
);

CREATE TABLE requests (
    request_id VARCHAR(50) PRIMARY KEY,
    elevator_id VARCHAR(50),  -- NULL if not assigned yet
    source_floor INT NOT NULL,
    destination_floor INT,  -- NULL for external requests
    direction VARCHAR(10) NOT NULL,
    type VARCHAR(10) NOT NULL,  -- 'EXTERNAL' or 'INTERNAL'
    status VARCHAR(20) DEFAULT 'PENDING',
    priority INT DEFAULT 0,  -- Higher = VIP/emergency
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    CHECK (type IN ('EXTERNAL', 'INTERNAL')),
    CHECK (status IN ('PENDING', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
    INDEX idx_elevator_status (elevator_id, status),
    INDEX idx_created (created_at)
);

-- Analytics table
CREATE TABLE elevator_trips (
    trip_id VARCHAR(50) PRIMARY KEY,
    elevator_id VARCHAR(50) NOT NULL,
    start_floor INT NOT NULL,
    end_floor INT NOT NULL,
    direction VARCHAR(10),
    passengers_count INT,
    duration_seconds INT,
    wait_time_seconds INT,
    trip_date DATE,
    
    INDEX idx_elevator_date (elevator_id, trip_date)
);
```

### **Why This Schema?**

**You**: "Key decisions:
1. **Separate `requests` table**: Tracks both external (floor button) and internal (destination button) requests. Useful for analytics—average wait time, peak hours.
2. **Real-time state in `elevators`**: `current_floor` and `direction` updated every second. Other systems can query this for display boards.
3. **Analytics table**: `elevator_trips` enables monitoring—which elevator is most used, average trip duration, predictive maintenance."

---

## 4. Sequence Diagrams

### **4.1 External Request: User Calls Elevator**

```
User    FloorBtn  Dispatcher  Elevator1  Elevator2  Elevator3
 │         │         │            │          │          │
 │─Press UP──▶│         │            │          │          │
 │         ├─findBestElevator────▶│            │          │          │
 │         │         │  Check:                            │
 │         │         │  - E1: Floor 8, going DOWN  ❌    │
 │         │         │  - E2: Floor 2, going UP    ✓ Nearest!
 │         │         │  - E3: Floor 5, IDLE        ✓    │
 │         │         │            │          │          │
 │         │         │  Algorithm: Pick E2 (nearest + same direction)
 │         │         │────────────────────▶│          │
 │         │         │                    ├─addRequest(floor=5, UP)
 │         │         │                    │  Add to UP queue: [5, 7]
 │         │         │◀───assigned────────│          │
 │◀──ETA 30s─────────│            │          │          │
 │         │         │            │          │          │
 │         │         │            │  E2 moves: 2→3→4→5  │
 │         │         │            │          ▼          │
 │         │         │            │  Arrival at Floor 5│
 │         │         │            │  Door opens        │
 │─Enter───────────────────────────────▶│          │
 │         │         │            │  User presses '7' │
 │         │         │            ├─addRequest(dest=7) │
 │         │         │            │  Already in queue!│
 │         │         │            │          ▼          │
 │         │         │            │  E2 moves: 5→6→7  │
```

### **4.2 LOOK Algorithm in Action**

```
Scenario: Elevator at Floor 3, going UP
Pending Requests:
- UP queue: [4, 6, 8]
- DOWN queue: [7, 5, 2]

Movement:
Floor 3 (current) → Direction: UP
  ↓ Check UP queue
Floor 4 → STOP (serve request)
  ↓
Floor 5 → SKIP (no request)
  ↓
Floor 6 → STOP (serve request)
  ↓
Floor 7 → SKIP (request is in DOWN queue, not UP)
  ↓
Floor 8 → STOP (serve request)
  ↓ UP queue empty
  ✓ Change direction to DOWN
  ↓ Check DOWN queue
Floor 7 → STOP (serve request from DOWN queue)
  ↓
Floor 6 → SKIP
  ↓
Floor 5 → STOP (serve request)
  ↓
Floor 4 → SKIP
  ↓
Floor 3 → SKIP
  ↓
Floor 2 → STOP (serve request)
  ↓ DOWN queue empty
  ✓ Change to IDLE
```

**You**: "See the efficiency? LOOK algorithm minimizes direction changes. Like a disk head scanning cylinders, elevator continues in one direction until no more requests, then reverses."

---

## 5. Scenario-First Explanations

### **5.1 Why LOOK Instead of FCFS (First-Come-First-Served)?**

**Scenario**: "Elevator at Floor 1. Requests come in order: Floor 10, Floor 2, Floor 9, Floor 3"

**FCFS Approach**:
```
Start: Floor 1
Request 1: Go to 10 → Move 1→10 (9 floors)
Request 2: Go to 2  → Move 10→2 (8 floors)
Request 3: Go to 9  → Move 2→9 (7 floors)
Request 4: Go to 3  → Move 9→3 (6 floors)

Total movement: 9 + 8 + 7 + 6 = 30 floors
Direction changes: 4 times
```

**LOOK Approach**:
```
Start: Floor 1, going UP
Sort UP requests: [2, 3, 9, 10]

Move: 1→2→3→9→10 (9 floors UP)
Then DOWN (if any DOWN requests)

Total movement: 9 floors
Direction changes: 0 times (all in same direction!)
```

**You**: "LOOK is **3x more efficient**! This is why:
- Elevator at Floor 1, going UP → naturally visits 2, 3, 9, 10 in sequence
- Minimizes wear on motor (fewer direction changes)
- Better user experience (predictable wait times)

Real elevators use LOOK or SCAN (similar algorithm from disk scheduling)."

### **5.2 Why Separate UP and DOWN Queues?**

**Scenario**: "Elevator at Floor 5, going UP. Requests: Floor 3 (DOWN), Floor 7 (UP), Floor 2 (DOWN)"

**You**: "Without separate queues:
```java
// ❌ Single queue (by floor number)
Queue: [2, 3, 7]
Current: Floor 5, going UP

// Problem: Should elevator serve Floor 3 now?
// - Floor 3 < 5 (below current position)
// - But we're going UP!
// - Serving Floor 3 now = direction change (inefficient)
```

With separate queues:
```java
// ✅ Separate UP and DOWN queues
UP_queue (MinHeap): [7]     // Only floors above current + going UP
DOWN_queue (MaxHeap): [3, 2] // Floors to visit when going DOWN

Current: Floor 5, going UP
1. Serve UP queue first: 5→7
2. Change direction to DOWN
3. Serve DOWN queue: 7→3→2

// ✅ Efficient! No unnecessary direction changes
```

**Implementation**:
```java
class ElevatorController {
    PriorityQueue<Integer> upQueue = new PriorityQueue<>();  // Min-heap
    PriorityQueue<Integer> downQueue = new PriorityQueue<>(Collections.reverseOrder());  // Max-heap
    
    void addRequest(int floor, Direction direction) {
        if (direction == Direction.UP && floor > currentFloor) {
            upQueue.offer(floor);
        } else if (direction == Direction.DOWN && floor < currentFloor) {
            downQueue.offer(floor);
        } else {
            // Request is opposite direction → add to pending
            pendingRequests.add(floor, direction);
        }
    }
    
    int getNextFloor() {
        if (currentDirection == Direction.UP) {
            if (!upQueue.isEmpty()) {
                return upQueue.poll();  // Get lowest floor (min-heap)
            } else {
                changeDirection(Direction.DOWN);
                transferPendingToDownQueue();
                return downQueue.poll();
            }
        } else {
            // Similar for DOWN
        }
    }
}
```

**Why this works**:
- **Min-Heap for UP**: When going UP, visit lowest floor first (5→6→7, not 5→7→6)
- **Max-Heap for DOWN**: When going DOWN, visit highest floor first (7→5→3, not 7→3→5)
- **Pending queue**: Handles requests in opposite direction (defer until direction changes)"

### **5.3 Why External Dispatcher Needs Multiple Strategies?**

**Scenario**: "Building has 3 elevators. Which one should respond to Floor 5 UP request?"

**You**: "Different buildings have different needs. That's why I use **Strategy Pattern**:

**Strategy 1: Nearest Elevator**
```java
class NearestElevatorStrategy implements DispatchStrategy {
    Elevator dispatch(List<Elevator> elevators, Request request) {
        return elevators.stream()
            .filter(e -> e.getStatus() != Status.MAINTENANCE)
            .min(Comparator.comparingInt(e -> 
                Math.abs(e.getCurrentFloor() - request.getFloor())
            )).orElse(null);
    }
}

// Example:
Request: Floor 5, UP
E1: Floor 2, going UP   → Distance: |2-5| = 3  ✓ NEAREST!
E2: Floor 8, going DOWN → Distance: |8-5| = 3
E3: Floor 1, IDLE       → Distance: |1-5| = 4

// Pick E1 (nearest + same direction)
```

**Strategy 2: Odd-Even Floor Split** (for heavy traffic buildings)
```java
class OddEvenStrategy implements DispatchStrategy {
    Elevator dispatch(List<Elevator> elevators, Request request) {
        if (request.getFloor() % 2 == 0) {
            return findElevatorForEvenFloors(elevators);
        } else {
            return findElevatorForOddFloors(elevators);
        }
    }
}

// Elevator 1 & 2: Handle odd floors (1, 3, 5, 7, 9)
// Elevator 3: Handle even floors (2, 4, 6, 8, 10)
// ✅ Reduces contention during peak hours
```

**Strategy 3: Zone-Based** (for tall buildings)
```java
class ZoneBasedStrategy implements DispatchStrategy {
    // Elevator 1: Floors 1-4 (Low zone)
    // Elevator 2: Floors 5-7 (Mid zone)
    // Elevator 3: Floors 8-10 (High zone)
}

// ✅ Minimizes travel time for users
// ✅ Common in 30+ floor buildings (express elevators)
```

**Real-world**:
- **Office buildings (9am-5pm)**: Nearest elevator (general use)
- **Residential buildings (evening rush)**: Odd-even split (everyone going to same floors)
- **Skyscrapers**: Zone-based (express elevators to high floors)

**Plug-and-play**:
```java
class Building {
    private DispatchStrategy strategy;
    
    void setStrategy(DispatchStrategy strategy) {
        this.strategy = strategy;  // ✅ Change at runtime!
    }
    
    void handleRequest(Request request) {
        Elevator elevator = strategy.dispatch(elevators, request);
        elevator.addRequest(request);
    }
}
```"

---

## 6. Cross Questions

**Interviewer**: "What if two elevators are equally close to the request?"

**You**: "Great edge case! I'd use a **tiebreaker hierarchy**:

```java
class SmartDispatcher {
    Elevator dispatch(List<Elevator> elevators, Request request) {
        // Filter eligible elevators
        List<Elevator> candidates = elevators.stream()
            .filter(e -> e.getStatus() != Status.MAINTENANCE)
            .collect(Collectors.toList());
        
        // Tiebreaker 1: Same direction preference
        candidates = filterByDirection(candidates, request);
        
        if (candidates.size() == 1) return candidates.get(0);
        
        // Tiebreaker 2: Least load (occupancy)
        candidates = filterByLoad(candidates);
        
        if (candidates.size() == 1) return candidates.get(0);
        
        // Tiebreaker 3: Least pending requests
        candidates = filterByQueueLength(candidates);
        
        if (candidates.size() == 1) return candidates.get(0);
        
        // Tiebreaker 4: Round-robin (load balancing)
        return getNextInRoundRobin(candidates);
    }
}
```

**Example**:
```
Request: Floor 5, UP

E1: Floor 3, going UP, 2 passengers, 3 pending requests
E2: Floor 7, going DOWN, 5 passengers, 1 pending request
E3: Floor 3, going UP, 1 passenger, 2 pending requests

Tiebreaker 1 (Direction): E1 and E3 are going UP ✓ (E2 eliminated)
Tiebreaker 2 (Load): E3 has 1 passenger ✓ (E1 has 2)
Result: Pick E3
```

**Senior insight**: Amazon's elevators use **ML models** trained on historical traffic patterns. Predict which elevator will serve the request fastest based on time-of-day, floor patterns, etc."

---

**Interviewer**: "How do you handle emergency scenarios like fire alarm?"

**You**: "Emergency mode is critical. Here's my approach:

```java
class ElevatorController {
    void activateEmergencyMode(EmergencyType type) {
        switch (type) {
            case FIRE:
                handleFireEmergency();
                break;
            case EARTHQUAKE:
                handleEarthquakeEmergency();
                break;
            case POWER_OUTAGE:
                handlePowerOutage();
                break;
        }
    }
    
    void handleFireEmergency() {
        // 1. Cancel ALL pending requests
        upQueue.clear();
        downQueue.clear();
        
        // 2. Stop accepting new requests
        status = Status.EMERGENCY;
        
        // 3. Move to ground floor (or nearest floor) and open doors
        if (currentFloor > 1) {
            moveToFloor(1, Priority.EMERGENCY);
        }
        
        // 4. Keep doors open
        door.open();
        door.disableAutoClose();
        
        // 5. Notify building management system
        buildingSystem.notifyEmergency(this.elevatorId, EmergencyType.FIRE);
        
        // 6. Disable elevator (prevent use during fire)
        disableElevator();
        displayMessage("FIRE ALARM - USE STAIRS");
    }
}
```

**Why these steps**:
1. **Go to ground floor**: People trapped inside can exit safely
2. **Disable elevator**: Fire safety rule—NEVER use elevators during fire (smoke inhalation risk)
3. **Keep doors open**: Prevents trapping people inside

**Power outage handling**:
```java
void handlePowerOutage() {
    // 1. If between floors → use backup battery to reach nearest floor
    if (isMoving()) {
        useBackupPower();
        int nearestFloor = findNearestFloor();
        moveToFloor(nearestFloor, Priority.EMERGENCY);
    }
    
    // 2. Open doors
    door.open();
    
    // 3. Activate emergency lighting
    emergencyLight.activate();
    
    // 4. Trigger alarm bell
    alarm.sound();
}
```

**Real elevators**:
- Have **backup batteries** (can operate for 30-60 minutes)
- **Emergency phone** inside elevator (direct line to building security)
- **Earthquake sensors** (auto-stop at nearest floor during tremors)

**Code safety standards**: EN 81 (European) and ASME A17.1 (US) mandate emergency protocols."

---

**Interviewer**: "How would you prevent elevator from moving if weight limit exceeded?"

**You**: "Weight sensors + admission control:

```java
class ElevatorController {
    private static final int MAX_WEIGHT_KG = 680;  // ~8 people @ 85kg each
    private static final int WARNING_THRESHOLD_KG = 650;
    
    private WeightSensor weightSensor;
    
    void checkWeight() {
        int currentWeight = weightSensor.getWeight();
        
        if (currentWeight > MAX_WEIGHT_KG) {
            // CRITICAL: Prevent movement
            door.preventClosing();
            alarm.sound();
            display.show("OVERWEIGHT - PLEASE EXIT");
            
            // Log for safety compliance
            logger.error("Elevator {} overweight: {}kg (max: {}kg)", 
                        elevatorId, currentWeight, MAX_WEIGHT_KG);
            
            // Wait until weight reduces
            while (weightSensor.getWeight() > MAX_WEIGHT_KG) {
                Thread.sleep(1000);
            }
            
            alarm.stop();
            display.show("Thank you");
            
        } else if (currentWeight > WARNING_THRESHOLD_KG) {
            // WARNING: Near limit
            display.show("NEAR CAPACITY");
        }
    }
    
    void closeDoors() {
        checkWeight();  // ✅ Always check before closing doors
        
        if (weightSensor.getWeight() <= MAX_WEIGHT_KG) {
            door.close();
        }
    }
}
```

**Production features**:
1. **Load sensors**: Strain gauges under elevator floor
2. **Redundancy**: Multiple sensors (if one fails, others take over)
3. **Calibration**: Regular calibration (sensors drift over time)

**Edge case**: What if sensor malfunctions?
```java
if (weightSensor.isFaulty()) {
    // Fallback: Count passengers via camera/IR sensors
    int estimatedWeight = passengerCount * AVG_WEIGHT_PER_PERSON;
    
    if (estimatedWeight > MAX_WEIGHT_KG) {
        preventMovement();
    }
    
    // Alert maintenance
    maintenanceSystem.createTicket("Weight sensor failure", elevatorId);
}
```

**Real-world**: ThyssenKrupp elevators use **AI-based passenger counting** via ceiling cameras."

---

## 7. Trade-offs

### **7.1 LOOK vs SCAN vs FCFS**

| Algorithm | Efficiency | Predictability | Starvation Risk |
|-----------|------------|----------------|-----------------|
| **FCFS** | Low (lots of direction changes) | High (guaranteed order) | None |
| **SCAN** | High (like LOOK but goes to extremes) | Medium | Low |
| **LOOK** | High (optimal for most cases) | Medium | Low |

**You**: "For elevators, **LOOK is best** because:
- Buildings have middle floors with most traffic (ground + popular floors)
- SCAN's 'go to top/bottom always' wastes time
- FCFS causes too many direction reversals

**FCFS example**:
```
Requests: 10, 2, 9, 3 (from Floor 1)
FCFS: 1→10→2→9→3 = 28 floors traveled
LOOK: 1→2→3→9→10 = 9 floors traveled
```

But for **emergency/VIP**, override with FCFS:
```java
if (request.getPriority() == Priority.EMERGENCY) {
    insertAtFrontOfQueue(request);  // ✅ Serve immediately
}
```"

### **7.2 Centralized vs Decentralized Control**

| Aspect | Centralized Dispatcher | Decentralized (Each Elevator Decides) |
|--------|------------------------|--------------------------------------|
| **Coordination** | Excellent (global optimization) | Poor (local decisions) |
| **Fault Tolerance** | Single point of failure | High (one fails, others work) |
| **Scalability** | Harder (one dispatcher for 100 elevators?) | Easy (add more elevators) |
| **Complexity** | Higher | Lower |

**You**: "I use **hybrid approach**:

**Centralized External Dispatcher**:
```java
// Handles floor button presses (choose which elevator)
class ExternalDispatcher {
    Elevator dispatch(Request request) {
        // Global view: optimize across all elevators
        return findBestElevator(elevators, request);
    }
}
```

**Decentralized Elevator Controllers**:
```java
// Each elevator independently manages its own queue
class ElevatorController {
    void processQueue() {
        // Local decisions: which floor to visit next
        int nextFloor = getNextFromLOOK();
        moveToFloor(nextFloor);
    }
}
```

**Why hybrid**:
- Dispatcher needs **global view** (don't send all elevators to same floor!)
- Each elevator needs **autonomy** (manage its own queue efficiently)

**Failure handling**:
```java
if (externalDispatcher.isDown()) {
    // Fallback: Elevators accept requests directly
    elevators.forEach(e -> e.enableDirectRequests());
}
```"

### **7.3 Priority Queue vs Simple Queue**

| Data Structure | Time Complexity (Insert) | Time Complexity (Poll) | Memory |
|----------------|--------------------------|------------------------|--------|
| **PriorityQueue (Heap)** | O(log n) | O(log n) | O(n) |
| **Simple Queue** | O(1) | O(1) | O(n) |

**You**: "For elevators, **PriorityQueue wins** because:

Without PriorityQueue:
```java
// ❌ Simple queue: Must iterate to find next floor
Queue<Integer> requests = new LinkedList<>(Arrays.asList(7, 3, 9, 5));
// Current floor: 3, going UP
// Need to find: Min floor >= 3
int next = requests.stream().filter(f -> f >= 3).min().orElse(0);  // O(n)
```

With PriorityQueue:
```java
// ✅ Min-heap: Automatically sorted
PriorityQueue<Integer> upQueue = new PriorityQueue<>(Arrays.asList(5, 7, 9));
int next = upQueue.poll();  // O(log n), returns 5 (smallest)
```

**Real-world at scale**:
- Office building: 50 floors, 20 elevators, 100 requests/minute
- Simple queue: O(50) per request = slow!
- Heap: O(log 50) = 5.6 operations

**Memory overhead acceptable**: 100 requests × 8 bytes = 800 bytes (negligible)"

---

## 8. Senior Trap Questions

### **Trap #1: "Use a global sorted list for all elevators!"**

**Interviewer**: "Why not maintain one global sorted list of all pending requests?"

**❌ Junior Answer**: "Sure, one global list is simpler."

**✅ Senior Answer**: "Global list creates a **bottleneck**. Let me show you:

**Problem**:
```java
// ❌ Global list (shared state)
class Building {
    SortedSet<Request> globalRequests = new TreeSet<>();
    
    synchronized void addRequest(Request request) {
        globalRequests.add(request);  // Lock entire list!
    }
    
    synchronized Request getNext(Elevator elevator) {
        // All elevators compete for same lock
        return globalRequests.pollFirst();
    }
}

// Concurrency problem:
// - 20 elevators × 1000 req/sec = 20,000 lock acquisitions/sec
// - Lock contention destroys throughput
```

**Better: Per-Elevator Queues**:
```java
// ✅ Each elevator has independent queue
class Elevator {
    PriorityQueue<Integer> upQueue = new PriorityQueue<>();
    PriorityQueue<Integer> downQueue = new PriorityQueue<>();
    
    void addRequest(int floor) {
        // No shared state = no locks needed!
        if (direction == UP) {
            upQueue.offer(floor);
        } else {
            downQueue.offer(floor);
        }
    }
}
```

**Why this scales**:
- Each elevator processes **independently** (no cross-elevator locks)
- Dispatcher assigns request to ONE elevator (then that elevator owns it)
- Throughput: Linear scaling with # of elevators

**Benchmark**:
- Global list: 5,000 requests/sec (lock bottleneck)
- Per-elevator queues: 50,000 requests/sec (10x faster!)

**Senior insight**: This is similar to **Kafka partitions** vs **single queue**. Always avoid shared mutable state in concurrent systems."

---

### **Trap #2: "Just calculate distance, pick closest!"**

**Interviewer**: "For dispatching, just pick the elevator with minimum `|currentFloor - requestFloor|`, right?"

**❌ Junior Answer**: "Yes, closest elevator is best."

**✅ Senior Answer**: "Distance alone is misleading. Consider **direction and load**:

**Counter-example**:
```
Request: Floor 5, going UP

Elevator 1: Floor 4, going DOWN, empty
Elevator 2: Floor 1, going UP, 6 passengers

Distance metric:
- E1: |4 - 5| = 1  ✓ Closest!
- E2: |1 - 5| = 4

But reality:
- E1 is going DOWN (must reverse direction to serve Floor 5)
  → Will first go to Floor 1, THEN come UP to Floor 5
  → Total distance: 4→1→5 = 8 floors
  
- E2 is already going UP (same direction!)
  → Direct path: 1→5 = 4 floors
  
E2 is actually faster!
```

**Smart dispatching algorithm**:
```java
class SmartDispatcher {
    int calculateCost(Elevator elevator, Request request) {
        int distance = Math.abs(elevator.getCurrentFloor() - request.getFloor());
        
        // Penalty for opposite direction
        if (elevator.getDirection() == request.getDirection().opposite()) {
            distance += 20;  // Heavy penalty
        }
        
        // Penalty for high load
        double loadFactor = elevator.getOccupancy() / (double) elevator.getMaxCapacity();
        distance += (int) (loadFactor * 10);
        
        // Penalty for many pending requests
        distance += elevator.getPendingCount() * 2;
        
        return distance;
    }
    
    Elevator dispatch(Request request) {
        return elevators.stream()
            .min(Comparator.comparingInt(e -> calculateCost(e, request)))
            .orElse(null);
    }
}
```

**Example with weights**:
```
Request: Floor 5, UP

E1: Floor 4, DOWN, 0 passengers, 1 pending
Cost = |4-5| + 20 (opposite dir) + 0 (empty) + 2 (1 pending) = 23

E2: Floor 1, UP, 6 passengers (75% load), 5 pending
Cost = |1-5| + 0 (same dir) + 7.5 (load) + 10 (5 pending) = 21.5

E3: Floor 7, IDLE, 2 passengers, 0 pending
Cost = |7-5| + 0 (idle) + 2.5 (load) + 0 = 4.5  ✓ Best!

Pick E3!
```

**Real-world**: Otis elevators use **predictive algorithms** that factor in:
- Time of day (morning rush = everyone going UP from ground)
- Floor popularity (reception floor gets more traffic)
- Historical patterns (lunch time = cafeteria floor busy)"

---

### **Trap #3: "Store current state in database!"**

**Interviewer**: "Should we persist elevator state (current floor, direction) to database?"

**❌ Junior Answer**: "Yes, for recovery after crashes."

**✅ Senior Answer**: "For **real-time state**, database is **too slow**. Here's why:

**Problem**:
```java
// ❌ DB write on every floor change
class Elevator {
    void moveToNextFloor() {
        currentFloor++;
        
        // DB write (10-50ms latency)
        elevatorRepo.updateCurrentFloor(elevatorId, currentFloor);
        
        // Elevator moves every 3 seconds
        // = 0.33 floors/sec × 20 elevators = 6.6 DB writes/sec
        // At scale (1000 buildings): 6,600 writes/sec to DB!
    }
}
```

**Better: In-Memory State with Periodic Snapshots**:
```java
class Elevator {
    private volatile int currentFloor;  // In-memory (fast!)
    private volatile Direction direction;
    
    void moveToNextFloor() {
        currentFloor++;  // O(1), no I/O
        
        // Broadcast state change via WebSocket (for displays)
        eventBus.publish(new ElevatorStateChangeEvent(elevatorId, currentFloor));
    }
    
    @Scheduled(fixedRate = 30000)  // Every 30 seconds
    void snapshotState() {
        // Periodic persist (not critical for real-time)
        elevatorRepo.updateState(elevatorId, currentFloor, direction);
    }
}
```

**Why this works**:
- **Real-time state**: In-memory (nanoseconds)
- **Crash recovery**: Use last snapshot + replay event log
- **Monitoring**: Subscribe to event bus (real-time dashboard)

**Event Sourcing for recovery**:
```java
// Event log (append-only, fast writes)
class ElevatorEventLog {
    void logEvent(Event event) {
        // Kafka or file-based log
        eventLog.append(event);  // Fast! Append-only
    }
}

// Crash recovery
class ElevatorRecoveryService {
    void recoverState(String elevatorId) {
        // 1. Load last snapshot from DB
        ElevatorState snapshot = db.getSnapshot(elevatorId);
        
        // 2. Replay events since snapshot
        List<Event> events = eventLog.getEventsSince(snapshot.getTimestamp());
        
        ElevatorState current = snapshot;
        for (Event event : events) {
            current = current.apply(event);  // Rebuild state
        }
        
        elevator.setState(current);
    }
}
```

**Real-world**:
- **Redis**: Store current state (in-memory, millisecond latency)
- **PostgreSQL**: Store historical trips (analytics)
- **Kafka**: Event stream (audit log + recovery)

**Senior insight**: Never use DB for **mutable hot state**. Use DB for **immutable history**."

---

## 9. Technology Choices

### **9.1 Messaging: MQTT vs WebSocket vs REST**

| Aspect | MQTT | WebSocket | REST |
|--------|------|-----------|------|
| **Real-time** | Excellent (pub/sub) | Excellent (bidirectional) | Poor (polling required) |
| **Overhead** | Low (binary protocol) | Medium | High (HTTP headers) |
| **Connection** | Persistent | Persistent | Request-response |
| **Use Case** | IoT devices | Real-time dashboards | CRUD operations |

**When MQTT**:
```java
// Elevator sends floor updates to MQTT broker
public class ElevatorMQTTClient {
    void publishFloorChange(int floor) {
        String topic = "building/elevator-" + elevatorId + "/floor";
        mqttClient.publish(topic, String.valueOf(floor).getBytes());
    }
}

// Floor displays subscribe
mqttClient.subscribe("building/elevator-+/floor", (topic, message) -> {
    String elevatorId = topic.split("/")[1];
    int floor = Integer.parseInt(new String(message));
    updateDisplay(elevatorId, floor);
});

// ✅ MQTT perfect for elevator → display communication (low bandwidth)
```

**When WebSocket**:
```javascript
// Real-time monitoring dashboard
const ws = new WebSocket('ws://building-server/elevators');

ws.onmessage = (event) => {
    const state = JSON.parse(event.data);
    updateElevatorPosition(state.elevatorId, state.floor);
};

// ✅ WebSocket for dashboards (richer data, JSON)
```

**When REST**:
```java
// User requests elevator (doesn't need real-time response)
@PostMapping("/floors/{floor}/call")
public ResponseEntity<Request> callElevator(@PathVariable int floor) {
    Request request = dispatcherService.dispatch(floor, Direction.UP);
    return ResponseEntity.ok(request);
}

// ✅ REST for user actions (simple, stateless)
```

**My Choice: All three!**
- **MQTT**: Elevator ↔ Hardware (low overhead, IoT)
- **WebSocket**: Dashboard ↔ Server (real-time monitoring)
- **REST**: User ↔ Server (call elevator, check status)

---

### **9.2 Event Bus: Kafka vs RabbitMQ vs Redis Pub/Sub**

| Aspect | Kafka | RabbitMQ | Redis Pub/Sub |
|--------|-------|----------|---------------|
| **Persistence** | Yes (replay-able) | Optional | No (in-memory) |
| **Throughput** | 1M msg/sec | 50K msg/sec | 100K msg/sec |
| **Latency** | 10-50ms | <5ms | <1ms |
| **Use Case** | Event sourcing | Task queues | Real-time events |

**When Kafka**:
```java
// Audit log (permanent record of all elevator events)
producer.send("elevator-events", new ElevatorEvent(
    elevatorId, EventType.FLOOR_CHANGED, floor, timestamp
));

// Consumers:
// 1. Analytics service (batch process daily)
// 2. Compliance auditor (replay events for investigation)
// 3. ML service (train predictive models)

// ✅ Kafka allows replay + multiple consumers
```

**When Redis Pub/Sub**:
```java
// Real-time floor display updates
redis.publish("elevator:" + elevatorId + ":floor", String.valueOf(floor));

// Floor displays subscribe (ephemeral, don't need history)
redis.subscribe("elevator:*:floor", (channel, message) -> {
    updateDisplay(message);
});

// ✅ Redis Pub/Sub for transient real-time events (no persistence needed)
```

**My Choice**: **Kafka for events** + **Redis Pub/Sub for real-time**
- Kafka: Audit log, analytics (persistent, replay-able)
- Redis: Floor displays, dashboards (ephemeral, low latency)

---

## 🎓 **Final Tips for 15 YOE Elevator Interview**

1. **LOOK Algorithm is Key**: Explain why it's better than FCFS/SCAN
2. **Separate Queues**: UP vs DOWN queues (Min-Heap vs Max-Heap)
3. **Dispatcher Strategy**: Show you know multiple algorithms (Nearest, Odd/Even, Zone)
4. **Emergency Handling**: Fire alarm, power outage, overweight
5. **Real-World Examples**: Reference actual elevators (Otis, Schindler, ThyssenKrupp)

**Senior insights**:
- Mention **regenerative braking** (elevators generate power when going down)
- Discuss **destination dispatch** systems (Singapore, modern offices)
- Talk about **double-deck elevators** (serve two floors simultaneously)
- Consider **AI-based predictive dispatching** (learns building traffic patterns)

**Good luck!** Elevator design tests your understanding of **scheduling algorithms**, **concurrent systems**, and **real-time processing**. Show you can build production-grade systems! 🚀
