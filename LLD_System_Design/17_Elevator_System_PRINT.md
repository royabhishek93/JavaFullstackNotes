# Elevator System - Complete LLD Interview Guide

**Interview Duration: 45 minutes | Difficulty: Medium-High | Must-Know: ⭐⭐⭐**

---

## 🎯 WHAT TO ACTUALLY WRITE IN INTERVIEW (20 mins coding)

**✅ MUST WRITE ON WHITEBOARD/SCREEN:**

### 1. State Interface (~2 mins)
```java
public interface ElevatorState {
    void moveUp(Elevator elevator);
    void moveDown(Elevator elevator);
    void stop(Elevator elevator);
}
```

### 2. Elevator Core Class (~10 mins)
```java
public class Elevator {
    private int currentFloor;
    private Direction direction;
    private ElevatorState state;
    private TreeSet<Integer> upQueue;      // Sorted requests going up
    private TreeSet<Integer> downQueue;    // Sorted requests going down
    private ReentrantLock lock;
    
    public Elevator(int id) {
        this.currentFloor = 0;
        this.direction = Direction.IDLE;
        this.state = new IdleState();
        this.upQueue = new TreeSet<>();
        this.downQueue = new TreeSet<>(Collections.reverseOrder());
        this.lock = new ReentrantLock();
    }
    
    public void addRequest(int floor) {
        lock.lock();
        try {
            if (floor > currentFloor) {
                upQueue.add(floor);
            } else if (floor < currentFloor) {
                downQueue.add(floor);
            }
        } finally {
            lock.unlock();
        }
    }
    
    public void processRequests() {
        while (true) {
            lock.lock();
            try {
                if (direction == Direction.UP && !upQueue.isEmpty()) {
                    int nextFloor = upQueue.first();
                    moveToFloor(nextFloor);
                    upQueue.remove(nextFloor);
                } else if (direction == Direction.DOWN && !downQueue.isEmpty()) {
                    int nextFloor = downQueue.first();
                    moveToFloor(nextFloor);
                    downQueue.remove(nextFloor);
                } else {
                    direction = Direction.IDLE;
                }
            } finally {
                lock.unlock();
            }
        }
    }
    
    private void moveToFloor(int floor) {
        while (currentFloor != floor) {
            if (currentFloor < floor) {
                currentFloor++;
            } else {
                currentFloor--;
            }
        }
        stop();
    }
}
```

### 3. Strategy Interface - SchedulingStrategy (~3 mins)
```java
public interface SchedulingStrategy {
    Elevator selectElevator(List<Elevator> elevators, int requestFloor);
}

public class NearestCarStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int requestFloor) {
        Elevator nearest = null;
        int minDistance = Integer.MAX_VALUE;
        
        for (Elevator e : elevators) {
            int distance = Math.abs(e.getCurrentFloor() - requestFloor);
            if (distance < minDistance) {
                nearest = e;
                minDistance = distance;
            }
        }
        return nearest;
    }
}
```

### 4. Controller Singleton (~5 mins)
```java
public class ElevatorController {
    private static ElevatorController instance;
    private List<Elevator> elevators;
    private SchedulingStrategy strategy;
    
    private ElevatorController() {
        this.elevators = new ArrayList<>();
        this.strategy = new NearestCarStrategy();
    }
    
    public static synchronized ElevatorController getInstance() {
        if (instance == null) {
            instance = new ElevatorController();
        }
        return instance;
    }
    
    public void requestElevator(int floor) {
        Elevator elevator = strategy.selectElevator(elevators, floor);
        elevator.addRequest(floor);
    }
}
```

**🗣️ EXPLAIN VERBALLY (Don't write full code):**
- "IdleState, MovingState, StoppedState implement ElevatorState interface"
- "SCAN algorithm: use TreeSet to serve requests in one direction"
- "LOOK algorithm: reverse at last request instead of end of building"
- "Direction enum: UP, DOWN, IDLE"
- "For multiple requests: use PriorityQueue or TreeSet for sorted order"
- "Thread safety: ReentrantLock protects queue modifications"

---

## CONVERSATIONAL SCRIPT (How to approach in interview)

### Phase 1: Requirements Clarification (5 mins)

**You:** "Let me clarify the requirements for the Elevator System."

**Functional Requirements:**
- "Multiple elevators in a building"
- "Users can request elevators from any floor (external requests)"
- "Users can select destination floors from inside (internal requests)"
- "Elevator should move up/down and handle requests optimally"
- "Display current floor and direction"
- "Handle multiple simultaneous requests"
- "Should we support emergency mode, maintenance mode?"

**Interviewer:** "Yes, add emergency mode. Focus on the scheduling algorithm."

**You:** "Got it. For non-functional requirements:"
- "Minimize wait time for users"
- "Energy efficient - minimize unnecessary movements"
- "Fair distribution across elevators"
- "Thread-safe for concurrent requests"
- "Handle edge cases like door malfunction"

**Interviewer:** "Good. Focus on the state machine and scheduling algorithm."

---

### Phase 2: Core Design Approach (5 mins)

**You:** "I'll use State Pattern for elevator states and Strategy Pattern for scheduling:"

```
┌──────────────────────────────────────────────────────────────┐
│              ELEVATOR SYSTEM ARCHITECTURE                    │
└──────────────────────────────────────────────────────────────┘

Key Design Patterns:
1. State Pattern        - Elevator states (Moving, Idle, etc.)
2. Strategy Pattern     - Different scheduling algorithms
3. Singleton Pattern    - Elevator Controller
4. Observer Pattern     - Display updates

Elevator States:
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  IDLE   │────→│ MOVING  │────→│ STOPPED │────→│  IDLE   │
│         │     │  UP/DN  │     │ DOORS   │     │         │
└─────────┘     └─────────┘     │  OPEN   │     └─────────┘
                                 └─────────┘

System Flow:
┌─────────┐     ┌──────────────┐     ┌──────────────┐
│  User   │────→│  Controller  │────→│  Elevator    │
│ Request │     │ (Scheduler)  │     │  (State)     │
└─────────┘     └──────────────┘     └──────────────┘
                        │
                        ↓
              ┌──────────────────┐
              │  Request Queue   │
              │  - UP Queue      │
              │  - DOWN Queue    │
              └──────────────────┘
```

**You:** "Each elevator maintains its own state and handles requests. The controller assigns requests to the most optimal elevator."

---

### Phase 3: Class Diagram (5 mins)

**You:** "Let me design the class structure:"

```
┌─────────────────────────────────────────────────────────────┐
│                    CLASS STRUCTURE                           │
└─────────────────────────────────────────────────────────────┘

┌────────────────────────┐
│  ElevatorController    │ (Singleton)
│  ────────────────────  │
│  - elevators: List     │
│  - scheduler: Strategy │
│  ────────────────────  │
│  + requestElevator()   │
│  + getOptimalElevator()│
└────────┬───────────────┘
         │ 1
         │ *
         ↓
┌────────────────────────┐
│      Elevator          │
│  ────────────────────  │
│  - id: int             │
│  - currentFloor: int   │
│  - state: ElevatorState│
│  - direction: Direction│
│  - upQueue: Set        │
│  - downQueue: Set      │
│  ────────────────────  │
│  + moveUp()            │
│  + moveDown()          │
│  + stop()              │
│  + addRequest()        │
│  + run()               │
└────────┬───────────────┘
         │
         │ uses
         ↓
┌────────────────────────┐
│   ElevatorState        │ (Interface)
│  ────────────────────  │
│  + moveUp()            │
│  + moveDown()          │
│  + openDoor()          │
│  + closeDoor()         │
│  + stop()              │
└────────┬───────────────┘
         │
         ▲
         │
    ┌────┴────┬─────────┬──────────┬──────────┐
    │         │         │          │          │
┌───▼───┐ ┌──▼────┐ ┌──▼─────┐ ┌──▼──────┐ ┌─▼────┐
│ Idle  │ │Moving │ │Stopped │ │Emergency│ │Maint │
│ State │ │ State │ │ State  │ │  State  │ │State │
└───────┘ └───────┘ └────────┘ └─────────┘ └──────┘


┌────────────────────────┐
│  ElevatorScheduler     │ (Interface)
│  ────────────────────  │
│  + selectElevator()    │
└────────┬───────────────┘
         │
         ▲
         │
    ┌────┴────┬─────────────┐
    │         │             │
┌───▼────┐ ┌──▼────────┐ ┌──▼──────────┐
│Nearest │ │   SCAN    │ │    LOOK     │
│ Car    │ │(Elevator  │ │  (Similar   │
│        │ │Algorithm) │ │  to SCAN)   │
└────────┘ └───────────┘ └─────────────┘


┌────────────────────────┐
│      Request           │
│  ────────────────────  │
│  - sourceFloor: int    │
│  - destFloor: int      │
│  - direction: Direction│
│  - timestamp           │
└────────────────────────┘


┌────────────────────────┐
│      Direction         │ (Enum)
│  ────────────────────  │
│  - UP                  │
│  - DOWN                │
│  - IDLE                │
└────────────────────────┘


┌────────────────────────┐
│      Door              │
│  ────────────────────  │
│  - isOpen: boolean     │
│  ────────────────────  │
│  + open()              │
│  + close()             │
└────────────────────────┘
```

---

### Phase 4: Core Implementation (20 mins)

**You:** "Let me implement the key components:"

#### 1. Enums and Basic Classes

```java
public enum Direction {
    UP(1),
    DOWN(-1),
    IDLE(0);
    
    private final int value;
    
    Direction(int value) {
        this.value = value;
    }
    
    public int getValue() {
        return value;
    }
}

public enum ElevatorStatus {
    IDLE,
    MOVING_UP,
    MOVING_DOWN,
    STOPPED,
    MAINTENANCE,
    EMERGENCY
}

public class Request {
    private final int sourceFloor;
    private final int destinationFloor;
    private final Direction direction;
    private final long timestamp;
    
    public Request(int sourceFloor, int destinationFloor) {
        this.sourceFloor = sourceFloor;
        this.destinationFloor = destinationFloor;
        this.direction = destinationFloor > sourceFloor ? Direction.UP : Direction.DOWN;
        this.timestamp = System.currentTimeMillis();
    }
    
    // External request (button pressed outside elevator)
    public Request(int sourceFloor, Direction direction) {
        this.sourceFloor = sourceFloor;
        this.destinationFloor = -1; // Unknown destination
        this.direction = direction;
        this.timestamp = System.currentTimeMillis();
    }
    
    public int getSourceFloor() { return sourceFloor; }
    public int getDestinationFloor() { return destinationFloor; }
    public Direction getDirection() { return direction; }
    public long getTimestamp() { return timestamp; }
    
    @Override
    public String toString() {
        return "Request{" + sourceFloor + " → " + destinationFloor + " " + direction + "}";
    }
}
```

---

#### 2. Door Class

```java
public class Door {
    private boolean isOpen;
    private final int elevatorId;
    
    public Door(int elevatorId) {
        this.elevatorId = elevatorId;
        this.isOpen = false;
    }
    
    public void open() {
        if (!isOpen) {
            System.out.println("[Elevator " + elevatorId + "] 🚪 Doors OPENING...");
            simulateOperation(1000); // 1 second to open
            isOpen = true;
            System.out.println("[Elevator " + elevatorId + "] 🚪 Doors OPEN");
        }
    }
    
    public void close() {
        if (isOpen) {
            System.out.println("[Elevator " + elevatorId + "] 🚪 Doors CLOSING...");
            simulateOperation(1000); // 1 second to close
            isOpen = false;
            System.out.println("[Elevator " + elevatorId + "] 🚪 Doors CLOSED");
        }
    }
    
    public boolean isOpen() {
        return isOpen;
    }
    
    private void simulateOperation(long millis) {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
```

---

#### 3. Elevator Class (Core Logic)

```java
import java.util.*;
import java.util.concurrent.locks.ReentrantLock;

public class Elevator implements Runnable {
    private final int id;
    private int currentFloor;
    private Direction currentDirection;
    private ElevatorStatus status;
    
    // Two priority queues for efficient scheduling
    private final TreeSet<Integer> upQueue;      // Ascending order
    private final TreeSet<Integer> downQueue;    // Descending order
    
    private final Door door;
    private final ReentrantLock lock;
    private volatile boolean running;
    
    private static final int MIN_FLOOR = 0;
    private static final int MAX_FLOOR = 10;
    private static final int FLOOR_TRAVEL_TIME_MS = 2000; // 2 seconds per floor
    
    public Elevator(int id) {
        this.id = id;
        this.currentFloor = 0; // Start at ground floor
        this.currentDirection = Direction.IDLE;
        this.status = ElevatorStatus.IDLE;
        this.upQueue = new TreeSet<>();
        this.downQueue = new TreeSet<>(Collections.reverseOrder());
        this.door = new Door(id);
        this.lock = new ReentrantLock();
        this.running = true;
    }
    
    // Main elevator logic
    @Override
    public void run() {
        System.out.println("[Elevator " + id + "] Started at floor " + currentFloor);
        
        while (running) {
            lock.lock();
            try {
                if (hasRequests()) {
                    processRequests();
                } else {
                    // Idle state
                    status = ElevatorStatus.IDLE;
                    currentDirection = Direction.IDLE;
                }
            } finally {
                lock.unlock();
            }
            
            // Small delay
            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                break;
            }
        }
    }
    
    private void processRequests() {
        // Determine direction if idle
        if (currentDirection == Direction.IDLE) {
            if (!upQueue.isEmpty()) {
                currentDirection = Direction.UP;
            } else if (!downQueue.isEmpty()) {
                currentDirection = Direction.DOWN;
            }
        }
        
        // Process based on direction
        if (currentDirection == Direction.UP) {
            processUpRequests();
        } else if (currentDirection == Direction.DOWN) {
            processDownRequests();
        }
    }
    
    private void processUpRequests() {
        while (!upQueue.isEmpty()) {
            int targetFloor = upQueue.first();
            
            // Move to target floor
            moveToFloor(targetFloor);
            
            // Stop and open doors
            stop(targetFloor);
            upQueue.remove(targetFloor);
        }
        
        // After completing all up requests, switch to down if needed
        if (!downQueue.isEmpty()) {
            currentDirection = Direction.DOWN;
        } else {
            currentDirection = Direction.IDLE;
        }
    }
    
    private void processDownRequests() {
        while (!downQueue.isEmpty()) {
            int targetFloor = downQueue.first();
            
            // Move to target floor
            moveToFloor(targetFloor);
            
            // Stop and open doors
            stop(targetFloor);
            downQueue.remove(targetFloor);
        }
        
        // After completing all down requests, switch to up if needed
        if (!upQueue.isEmpty()) {
            currentDirection = Direction.UP;
        } else {
            currentDirection = Direction.IDLE;
        }
    }
    
    private void moveToFloor(int targetFloor) {
        while (currentFloor != targetFloor) {
            if (currentFloor < targetFloor) {
                moveUp();
            } else {
                moveDown();
            }
            
            // Check if we should stop at current floor
            if (shouldStopAtCurrentFloor()) {
                stop(currentFloor);
                removeCurrentFloorFromQueues();
            }
        }
    }
    
    private void moveUp() {
        status = ElevatorStatus.MOVING_UP;
        currentDirection = Direction.UP;
        currentFloor++;
        
        System.out.println("[Elevator " + id + "] ↑ Moving UP to floor " + currentFloor);
        simulateMovement();
    }
    
    private void moveDown() {
        status = ElevatorStatus.MOVING_DOWN;
        currentDirection = Direction.DOWN;
        currentFloor--;
        
        System.out.println("[Elevator " + id + "] ↓ Moving DOWN to floor " + currentFloor);
        simulateMovement();
    }
    
    private void stop(int floor) {
        status = ElevatorStatus.STOPPED;
        System.out.println("[Elevator " + id + "] ⏹ STOPPED at floor " + floor);
        
        door.open();
        
        // Wait for passengers (simulate)
        try {
            Thread.sleep(3000); // 3 seconds for passengers
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        
        door.close();
    }
    
    private boolean shouldStopAtCurrentFloor() {
        if (currentDirection == Direction.UP) {
            return upQueue.contains(currentFloor);
        } else if (currentDirection == Direction.DOWN) {
            return downQueue.contains(currentFloor);
        }
        return false;
    }
    
    private void removeCurrentFloorFromQueues() {
        upQueue.remove(currentFloor);
        downQueue.remove(currentFloor);
    }
    
    private void simulateMovement() {
        try {
            Thread.sleep(FLOOR_TRAVEL_TIME_MS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
    
    // Add request to elevator
    public void addRequest(int floor) {
        lock.lock();
        try {
            if (floor < MIN_FLOOR || floor > MAX_FLOOR) {
                System.out.println("Invalid floor: " + floor);
                return;
            }
            
            if (floor == currentFloor) {
                return; // Already at this floor
            }
            
            // Add to appropriate queue
            if (floor > currentFloor) {
                upQueue.add(floor);
                System.out.println("[Elevator " + id + "] Added floor " + floor + " to UP queue");
            } else {
                downQueue.add(floor);
                System.out.println("[Elevator " + id + "] Added floor " + floor + " to DOWN queue");
            }
        } finally {
            lock.unlock();
        }
    }
    
    private boolean hasRequests() {
        return !upQueue.isEmpty() || !downQueue.isEmpty();
    }
    
    // Calculate cost (for scheduling algorithm)
    public int calculateCost(int floor, Direction direction) {
        int cost = 0;
        
        if (status == ElevatorStatus.IDLE) {
            // Simple distance
            cost = Math.abs(currentFloor - floor);
        } else if (currentDirection == direction) {
            // Going in same direction
            if (currentDirection == Direction.UP && floor >= currentFloor) {
                cost = floor - currentFloor;
            } else if (currentDirection == Direction.DOWN && floor <= currentFloor) {
                cost = currentFloor - floor;
            } else {
                // Need to finish current direction first
                cost = Math.abs(currentFloor - floor) + getTotalPendingFloors();
            }
        } else {
            // Going in opposite direction - high cost
            cost = Math.abs(currentFloor - floor) + getTotalPendingFloors() + 20;
        }
        
        return cost;
    }
    
    private int getTotalPendingFloors() {
        return upQueue.size() + downQueue.size();
    }
    
    public void stop() {
        running = false;
    }
    
    // Getters
    public int getId() { return id; }
    public int getCurrentFloor() { return currentFloor; }
    public Direction getCurrentDirection() { return currentDirection; }
    public ElevatorStatus getStatus() { return status; }
    
    public void displayStatus() {
        System.out.println("\n[Elevator " + id + " Status]");
        System.out.println("  Current Floor: " + currentFloor);
        System.out.println("  Direction: " + currentDirection);
        System.out.println("  Status: " + status);
        System.out.println("  UP Queue: " + upQueue);
        System.out.println("  DOWN Queue: " + downQueue);
    }
}
```

---

#### 4. Scheduling Strategy (Strategy Pattern)

```java
import java.util.List;

public interface ElevatorScheduler {
    Elevator selectElevator(List<Elevator> elevators, int floor, Direction direction);
}

// Nearest Car Algorithm
public class NearestCarScheduler implements ElevatorScheduler {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int floor, Direction direction) {
        Elevator bestElevator = null;
        int minCost = Integer.MAX_VALUE;
        
        for (Elevator elevator : elevators) {
            // Skip elevators in maintenance/emergency
            if (elevator.getStatus() == ElevatorStatus.MAINTENANCE ||
                elevator.getStatus() == ElevatorStatus.EMERGENCY) {
                continue;
            }
            
            int cost = elevator.calculateCost(floor, direction);
            
            if (cost < minCost) {
                minCost = cost;
                bestElevator = elevator;
            }
        }
        
        return bestElevator;
    }
}

// SCAN Algorithm (like disk scheduling)
public class ScanScheduler implements ElevatorScheduler {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int floor, Direction direction) {
        // Prefer elevator going in same direction
        Elevator sameDirectionElevator = null;
        int minDistance = Integer.MAX_VALUE;
        
        for (Elevator elevator : elevators) {
            if (elevator.getStatus() == ElevatorStatus.MAINTENANCE ||
                elevator.getStatus() == ElevatorStatus.EMERGENCY) {
                continue;
            }
            
            // Check if elevator is going in same direction and can pick up
            if (elevator.getCurrentDirection() == direction ||
                elevator.getCurrentDirection() == Direction.IDLE) {
                
                int distance = Math.abs(elevator.getCurrentFloor() - floor);
                
                if (distance < minDistance) {
                    minDistance = distance;
                    sameDirectionElevator = elevator;
                }
            }
        }
        
        // If no elevator going in same direction, find nearest idle
        if (sameDirectionElevator == null) {
            for (Elevator elevator : elevators) {
                if (elevator.getStatus() == ElevatorStatus.IDLE) {
                    int distance = Math.abs(elevator.getCurrentFloor() - floor);
                    if (distance < minDistance) {
                        minDistance = distance;
                        sameDirectionElevator = elevator;
                    }
                }
            }
        }
        
        return sameDirectionElevator != null ? sameDirectionElevator : elevators.get(0);
    }
}
```

---

#### 5. Elevator Controller (Singleton)

```java
import java.util.ArrayList;
import java.util.List;

public class ElevatorController {
    private static ElevatorController instance;
    private final List<Elevator> elevators;
    private final List<Thread> elevatorThreads;
    private ElevatorScheduler scheduler;
    
    private ElevatorController(int numElevators) {
        this.elevators = new ArrayList<>();
        this.elevatorThreads = new ArrayList<>();
        this.scheduler = new NearestCarScheduler();
        
        // Initialize elevators
        for (int i = 0; i < numElevators; i++) {
            Elevator elevator = new Elevator(i + 1);
            elevators.add(elevator);
            
            Thread thread = new Thread(elevator);
            elevatorThreads.add(thread);
            thread.start();
        }
        
        System.out.println("\n=== Elevator Controller Initialized ===");
        System.out.println("Number of elevators: " + numElevators);
        System.out.println("Scheduling algorithm: " + scheduler.getClass().getSimpleName());
        System.out.println("======================================\n");
    }
    
    public static synchronized ElevatorController getInstance(int numElevators) {
        if (instance == null) {
            instance = new ElevatorController(numElevators);
        }
        return instance;
    }
    
    public static ElevatorController getInstance() {
        if (instance == null) {
            throw new IllegalStateException("Controller not initialized");
        }
        return instance;
    }
    
    // External request (button outside elevator)
    public void requestElevator(int floor, Direction direction) {
        System.out.println("\n>>> External Request: Floor " + floor + " going " + direction);
        
        Elevator selectedElevator = scheduler.selectElevator(elevators, floor, direction);
        
        if (selectedElevator != null) {
            System.out.println(">>> Assigned Elevator " + selectedElevator.getId());
            selectedElevator.addRequest(floor);
        } else {
            System.out.println(">>> No elevator available");
        }
    }
    
    // Internal request (button inside elevator)
    public void selectFloor(int elevatorId, int destinationFloor) {
        System.out.println("\n>>> Internal Request: Elevator " + elevatorId + 
                          " to floor " + destinationFloor);
        
        Elevator elevator = getElevator(elevatorId);
        if (elevator != null) {
            elevator.addRequest(destinationFloor);
        }
    }
    
    private Elevator getElevator(int id) {
        return elevators.stream()
            .filter(e -> e.getId() == id)
            .findFirst()
            .orElse(null);
    }
    
    public void setScheduler(ElevatorScheduler scheduler) {
        this.scheduler = scheduler;
        System.out.println("Scheduler changed to: " + scheduler.getClass().getSimpleName());
    }
    
    public void displayAllStatus() {
        System.out.println("\n╔════════════════════════════════════════╗");
        System.out.println("║      ELEVATOR SYSTEM STATUS            ║");
        System.out.println("╚════════════════════════════════════════╝");
        
        for (Elevator elevator : elevators) {
            elevator.displayStatus();
        }
        System.out.println();
    }
    
    public void shutdown() {
        System.out.println("\n=== Shutting down elevator system ===");
        
        for (Elevator elevator : elevators) {
            elevator.stop();
        }
        
        for (Thread thread : elevatorThreads) {
            try {
                thread.join(5000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        }
        
        System.out.println("=== System shut down ===");
    }
}
```

---

### Phase 5: Usage Example (5 mins)

**You:** "Here's a complete demo:"

```java
public class ElevatorSystemDemo {
    public static void main(String[] args) throws InterruptedException {
        System.out.println("╔══════════════════════════════════════════╗");
        System.out.println("║    ELEVATOR SYSTEM SIMULATION            ║");
        System.out.println("╚══════════════════════════════════════════╝\n");
        
        // Initialize system with 3 elevators
        ElevatorController controller = ElevatorController.getInstance(3);
        
        // Wait for initialization
        Thread.sleep(2000);
        
        // Scenario 1: Person on floor 0 wants to go up
        System.out.println("\n--- SCENARIO 1: Person on floor 0 going UP ---");
        controller.requestElevator(0, Direction.UP);
        Thread.sleep(1000);
        
        // They select floor 5 inside elevator
        controller.selectFloor(1, 5);
        
        // Wait for elevator to reach
        Thread.sleep(8000);
        
        // Scenario 2: Multiple simultaneous requests
        System.out.println("\n--- SCENARIO 2: Multiple Requests ---");
        controller.requestElevator(7, Direction.DOWN);
        controller.requestElevator(3, Direction.UP);
        controller.requestElevator(9, Direction.DOWN);
        
        Thread.sleep(5000);
        
        // Internal selections
        controller.selectFloor(2, 0); // Elevator 2 to ground
        controller.selectFloor(3, 2); // Elevator 3 to floor 2
        
        Thread.sleep(15000);
        
        // Display status
        controller.displayAllStatus();
        
        // Scenario 3: Test with SCAN scheduler
        System.out.println("\n--- SCENARIO 3: Switching to SCAN Scheduler ---");
        controller.setScheduler(new ScanScheduler());
        
        controller.requestElevator(8, Direction.DOWN);
        controller.requestElevator(4, Direction.UP);
        
        Thread.sleep(10000);
        
        // Final status
        controller.displayAllStatus();
        
        // Shutdown
        Thread.sleep(5000);
        controller.shutdown();
        
        System.out.println("\n╔══════════════════════════════════════════╗");
        System.out.println("║         SIMULATION COMPLETE              ║");
        System.out.println("╚══════════════════════════════════════════╝");
    }
}
```

---

### Phase 6: Advanced Features (3 mins)

**You:** "Let me add some advanced features:"

#### 1. Emergency Mode

```java
public class EmergencyMode {
    public void activate(Elevator elevator) {
        System.out.println("[EMERGENCY] Elevator " + elevator.getId() + 
                          " entering emergency mode!");
        
        // Clear all requests
        elevator.clearAllRequests();
        
        // Move to nearest floor
        elevator.moveToNearestFloor();
        
        // Open doors
        elevator.getDoor().open();
        
        // Update status
        elevator.setStatus(ElevatorStatus.EMERGENCY);
    }
}
```

#### 2. Load Balancing

```java
public class LoadBalancedScheduler implements ElevatorScheduler {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int floor, Direction direction) {
        // Select elevator with least pending requests
        Elevator leastBusy = null;
        int minRequests = Integer.MAX_VALUE;
        
        for (Elevator elevator : elevators) {
            int pendingRequests = elevator.getPendingRequestCount();
            
            if (pendingRequests < minRequests) {
                minRequests = pendingRequests;
                leastBusy = elevator;
            }
        }
        
        return leastBusy;
    }
}
```

---

## SOLID PRINCIPLES IN DEPTH

**You:** "Let me explain how SOLID principles make this elevator system robust and extensible."

---

### 1. Single Responsibility Principle (SRP)

**Purpose:** Each class should have only ONE reason to change.

**Problem it solves:**
Without SRP, elevator logic becomes a mess:
```java
// BAD: Elevator class doing everything
class Elevator {
    // Movement logic
    public void moveUp() { ... }
    public void moveDown() { ... }
    
    // Scheduling logic
    public void assignRequest(int floor) { ... }
    public int findNextFloor() { ... }
    
    // State management
    public void changeState() { ... }
    
    // UI/Display logic
    public void updateDisplay() { ... }
    
    // Door operations
    public void openDoors() { ... }
    public void closeDoors() { ... }
}
// Too many responsibilities! Changing scheduling affects movement logic.
```

**Advantages:**
- ✅ **Clear ownership** - Each class has one clear job
- ✅ **Easy to test** - Test movement separately from scheduling
- ✅ **Parallel development** - Different devs work on different classes
- ✅ **Localized changes** - Fix scheduling without touching movement

**In our design:**
```java
// GOOD: Separated responsibilities

// Elevator: ONLY manages elevator state and movement
class Elevator {
    private int currentFloor;
    private Direction direction;
    private ElevatorState state;
    
    public void moveUp() { currentFloor++; }
    public void moveDown() { currentFloor--; }
    public void stop() { ... }
}

// SchedulingStrategy: ONLY determines which elevator to assign
interface SchedulingStrategy {
    Elevator selectElevator(List<Elevator> elevators, int requestFloor);
}

// ElevatorState: ONLY manages state transitions
interface ElevatorState {
    void moveUp(Elevator elevator);
    void moveDown(Elevator elevator);
    void stop(Elevator elevator);
}

// ElevatorController: ONLY coordinates elevators (Facade)
class ElevatorController {
    public void requestElevator(int floor) { ... }
}

// Door: ONLY handles door operations (if needed)
class Door {
    public void open() { ... }
    public void close() { ... }
}
```

**Interview tip:** "If I need to change the scheduling algorithm, I only touch `SchedulingStrategy`. If I need to add emergency state, I only add a new `ElevatorState` implementation. Each class has one clear responsibility."

---

### 2. Open/Closed Principle (OCP)

**Purpose:** Classes should be OPEN for extension but CLOSED for modification.

**Problem it solves:**
Without OCP, adding features requires modifying existing code:
```java
// BAD: Hard-coded scheduling logic
class ElevatorController {
    public Elevator selectElevator(int requestFloor) {
        // Nearest Car logic hard-coded here
        Elevator nearest = null;
        int minDistance = Integer.MAX_VALUE;
        
        for (Elevator e : elevators) {
            int distance = Math.abs(e.getCurrentFloor() - requestFloor);
            if (distance < minDistance) {
                nearest = e;
                minDistance = distance;
            }
        }
        
        // To add SCAN algorithm, you must MODIFY this method - RISKY!
        return nearest;
    }
}
```

**Advantages:**
- ✅ **Zero regression** - Existing algorithms unaffected
- ✅ **Easy to add algorithms** - Just create new strategy class
- ✅ **A/B testing** - Deploy new algorithms without changing core
- ✅ **Stable core** - ElevatorController never changes

**In our design:**
```java
// GOOD: Strategy pattern for extensibility

interface SchedulingStrategy {
    Elevator selectElevator(List<Elevator> elevators, int requestFloor);
}

class NearestCarStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int requestFloor) {
        // Find nearest elevator
    }
}

class SCANStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int requestFloor) {
        // SCAN algorithm
    }
}

class LOOKStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int requestFloor) {
        // LOOK algorithm
    }
}

// NEW: Add load-balancing algorithm - zero changes to existing code!
class LeastBusyStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int requestFloor) {
        // Select elevator with fewest pending requests
    }
}

class ElevatorController {
    private SchedulingStrategy strategy;
    
    public void setStrategy(SchedulingStrategy strategy) {
        this.strategy = strategy;
    }
    
    public void requestElevator(int floor) {
        Elevator elevator = strategy.selectElevator(elevators, floor);  // Works for ANY strategy!
        elevator.addRequest(floor);
    }
}

// Usage:
controller.setStrategy(new NearestCarStrategy());
// Later, switch to SCAN without changing ElevatorController:
controller.setStrategy(new SCANStrategy());
```

**Interview tip:** "To add a new scheduling algorithm like 'Least Busy', I create `LeastBusyStrategy` implementing the interface. Zero changes to `ElevatorController`. The system is closed for modification but open for extension."

---

### 3. Liskov Substitution Principle (LSP)

**Purpose:** Subclasses must be substitutable for their parent classes without breaking behavior.

**Problem it solves:**
Without LSP, some strategies violate contracts:
```java
// BAD: Violates LSP
interface SchedulingStrategy {
    Elevator selectElevator(List<Elevator> elevators, int requestFloor);
    // Contract: Always returns an elevator if list is non-empty
}

class NearestCarStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int requestFloor) {
        // Returns nearest elevator as expected
    }
}

class BrokenStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int requestFloor) {
        return null;  // BREAKS CONTRACT! Should return elevator, not null
    }
}

// Code expecting an elevator will crash:
SchedulingStrategy strategy = new BrokenStrategy();
Elevator elevator = strategy.selectElevator(elevators, floor);
elevator.addRequest(floor);  // BOOM! NullPointerException
```

**Advantages:**
- ✅ **Predictable behavior** - All strategies work the same way
- ✅ **Polymorphism works** - Can swap strategies at runtime
- ✅ **Testing is easy** - Mock strategies behave like real ones
- ✅ **No surprises** - Code doesn't break when switching implementations

**In our design:**
```java
// GOOD: All strategies honor the contract

interface SchedulingStrategy {
    Elevator selectElevator(List<Elevator> elevators, int requestFloor);
    // Contract: Returns an elevator, or throws exception if none available
}

class NearestCarStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int requestFloor) {
        if (elevators.isEmpty()) {
            throw new IllegalStateException("No elevators available");  // ✓ Honors contract
        }
        
        // Find nearest
        Elevator nearest = elevators.get(0);
        int minDistance = Math.abs(nearest.getCurrentFloor() - requestFloor);
        
        for (Elevator e : elevators) {
            int distance = Math.abs(e.getCurrentFloor() - requestFloor);
            if (distance < minDistance) {
                nearest = e;
                minDistance = distance;
            }
        }
        
        return nearest;  // ✓ Always returns an elevator
    }
}

class SCANStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int requestFloor) {
        if (elevators.isEmpty()) {
            throw new IllegalStateException("No elevators available");  // ✓ Honors contract
        }
        
        // SCAN logic
        return selectedElevator;  // ✓ Always returns an elevator
    }
}

// Polymorphism works perfectly:
SchedulingStrategy strategy = new NearestCarStrategy();  // Or SCANStrategy or LOOKStrategy
Elevator elevator = strategy.selectElevator(elevators, floor);  // Works for ANY strategy
elevator.addRequest(floor);  // No crashes, no surprises
```

**Interview tip:** "Any code that works with `SchedulingStrategy` will work with `NearestCar`, `SCAN`, or `LOOK`. They all honor the contract - `selectElevator()` always returns an elevator or throws a clear exception."

---

### 4. Interface Segregation Principle (ISP)

**Purpose:** Clients should not be forced to depend on interfaces they don't use.

**Problem it solves:**
Without ISP, interfaces become bloated:
```java
// BAD: Fat interface forces unnecessary implementations
interface ElevatorOperations {
    void moveUp();
    void moveDown();
    void stop();
    void openDoors();
    void closeDoors();
    void emergencyStop();
    void playMusic();              // Not all elevators have music
    void displayAds();             // Not all elevators show ads
    void airConditioning();        // Not all have AC control
    void voiceAnnouncement();      // Not all have voice
}

// Basic elevator must implement ALL methods!
class BasicElevator implements ElevatorOperations {
    @Override
    public void playMusic() { 
        throw new UnsupportedOperationException();  // Forced!
    }
    
    @Override
    public void displayAds() {
        throw new UnsupportedOperationException();  // Forced!
    }
}
```

**Advantages:**
- ✅ **Lean interfaces** - Only necessary methods
- ✅ **Better cohesion** - Related methods grouped
- ✅ **No dummy code** - No forced implementations
- ✅ **Clear contracts** - Interface tells you what to expect

**In our design:**
```java
// GOOD: Segregated interfaces

// Core: Every elevator must implement this
interface Elevator {
    void moveUp();
    void moveDown();
    void stop();
    int getCurrentFloor();
    Direction getDirection();
}

// Optional: Only for elevators with door control
interface DoorOperations {
    void openDoors();
    void closeDoors();
    boolean areDoorsOpen();
}

// Optional: Only for elevators with emergency features
interface EmergencyOperations {
    void emergencyStop();
    void callFireService();
    void enableEmergencyLighting();
}

// Optional: Only for elevators with multimedia
interface MultimediaElevator {
    void playMusic();
    void displayAds();
    void voiceAnnouncement(String message);
}

// Implement only what you need:

// Basic elevator: Just core operations
class BasicElevator implements Elevator {
    // Only implements movement methods - nothing else!
}

// Standard elevator: Core + doors
class StandardElevator implements Elevator, DoorOperations {
    // Implements movement + door operations
}

// Premium elevator: Everything
class PremiumElevator implements Elevator, 
                                  DoorOperations, 
                                  EmergencyOperations,
                                  MultimediaElevator {
    // Implements all features - by choice!
}

// Freight elevator: Core + emergency (no multimedia)
class FreightElevator implements Elevator, EmergencyOperations {
    // Heavy-duty elevator with emergency features but no ads/music
}
```

**Interview tip:** "Core interface has only movement methods. If an elevator has doors, it implements `DoorOperations`. If it has emergency features, it implements `EmergencyOperations`. Clients depend only on what they need."

---

### 5. Dependency Inversion Principle (DIP)

**Purpose:** High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Problem it solves:**
Without DIP, high-level code is tightly coupled:
```java
// BAD: ElevatorController tightly coupled to concrete strategy
class ElevatorController {
    private NearestCarStrategy strategy = new NearestCarStrategy();  // TIGHT COUPLING!
    
    public void requestElevator(int floor) {
        Elevator elevator = strategy.selectElevator(elevators, floor);
        // Can't switch to SCAN without modifying this class!
    }
}
```

**Advantages:**
- ✅ **Loose coupling** - Easy to swap strategies
- ✅ **Testability** - Inject mock strategies for testing
- ✅ **Flexibility** - Change strategies at runtime
- ✅ **Maintainability** - Low-level changes don't affect high-level

**In our design:**
```java
// GOOD: Depend on abstraction (interface)

interface SchedulingStrategy {
    Elevator selectElevator(List<Elevator> elevators, int requestFloor);
}

class NearestCarStrategy implements SchedulingStrategy { ... }
class SCANStrategy implements SchedulingStrategy { ... }
class LOOKStrategy implements SchedulingStrategy { ... }

class ElevatorController {
    private SchedulingStrategy strategy;  // Interface, not concrete class!
    
    // Dependency Injection via constructor
    public ElevatorController(SchedulingStrategy strategy) {
        this.strategy = strategy;
    }
    
    // Or via setter (more flexible)
    public void setStrategy(SchedulingStrategy strategy) {
        this.strategy = strategy;
    }
    
    public void requestElevator(int floor) {
        Elevator elevator = strategy.selectElevator(elevators, floor);  // Don't care about implementation!
        elevator.addRequest(floor);
    }
}

// Production usage - inject real strategy:
ElevatorController controller = new ElevatorController(new NearestCarStrategy());

// Later, switch algorithm at runtime:
controller.setStrategy(new SCANStrategy());

// Test usage - inject mock strategy:
class MockStrategy implements SchedulingStrategy {
    @Override
    public Elevator selectElevator(List<Elevator> elevators, int floor) {
        return elevators.get(0);  // Always return first elevator for testing
    }
}

ElevatorController testController = new ElevatorController(new MockStrategy());
```

**Interview tip:** "ElevatorController doesn't know if it's using NearestCar or SCAN - it just calls `selectElevator()` on the interface. I can swap strategies at runtime without modifying the controller. For testing, I inject a mock strategy that returns predictable results."

---

## KEY TAKEAWAYS

### Design Patterns Used:
✅ **State Pattern** - Elevator states (Idle, Moving, Stopped, Emergency)
✅ **Strategy Pattern** - Different scheduling algorithms (NearestCar, SCAN, LOOK)
✅ **Singleton Pattern** - Controller (single point of control)
✅ **Observer Pattern** - Could add for display updates

### Key Algorithms:
✅ **SCAN** - Move in one direction, service all requests
✅ **LOOK** - Similar to SCAN, but reverse at last request
✅ **Nearest Car** - Select closest elevator

### SOLID Principles Applied:
✅ **Single Responsibility (SRP)** - Elevator handles movement, SchedulingStrategy handles selection, ElevatorState manages states
✅ **Open/Closed (OCP)** - Add new scheduling algorithms by creating new strategy classes
✅ **Liskov Substitution (LSP)** - All SchedulingStrategy implementations are interchangeable
✅ **Interface Segregation (ISP)** - Separate interfaces for core Elevator, DoorOperations, EmergencyOperations, Multimedia
✅ **Dependency Inversion (DIP)** - ElevatorController depends on SchedulingStrategy interface, not concrete implementations

### Thread Safety:
✅ **ReentrantLock** - Protects elevator state
✅ **TreeSet** - Efficient sorted queues
✅ **Volatile** - Running flag for threads

---

## COMMON MISTAKES TO AVOID

❌ Not handling concurrent requests (thread safety)
❌ Inefficient scheduling (starvation)
❌ Not considering direction when assigning elevators
❌ Forgetting door operations
❌ No emergency handling
❌ Hard-coding number of floors/elevators

---

## REAL-WORLD APPLICATIONS

✅ **Buildings** - Office towers, malls
✅ **Hotels** - Guest elevators
✅ **Hospitals** - Patient/staff elevators
✅ **Parking Garages** - Car elevators

---

**END OF ELEVATOR SYSTEM GUIDE**

This covers **ATM** (state machine) and **Vending Machine** patterns!
