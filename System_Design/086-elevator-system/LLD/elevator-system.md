# Designing an Elevator System

## Requirements
1. The elevator system should consist of multiple elevators serving multiple floors.
2. Each elevator should have a capacity limit and should not exceed it.
3. Users should be able to request an elevator from any floor and select a destination floor.
4. The elevator system should efficiently handle user requests and optimize the movement of elevators to minimize waiting time.
5. The system should prioritize requests based on the direction of travel and the proximity of the elevators to the requested floor.
6. The elevators should be able to handle multiple requests concurrently and process them in an optimal order.
7. The system should ensure thread safety and prevent race conditions when multiple threads interact with the elevators.

## UML Class Diagram

![](diagrams/elevatorsystem-class-diagram.png)

## Implementations
#### [Java Implementation](elevatorsystem/) 

## Classes, Interfaces and Enumerations
1. The **Direction** enum represents the possible directions of elevator movement (UP or DOWN).
2. The **Request** class represents a user request for an elevator, containing the source floor and destination floor.
3. The **Elevator** class represents an individual elevator in the system. It has a capacity limit and maintains a list of 4. requests. The elevator processes requests concurrently and moves between floors based on the requests.
4. The **ElevatorController** class manages multiple elevators and handles user requests. It finds the optimal elevator to serve a request based on the proximity of the elevators to the requested floor.
5. The **ElevatorSystem** class is the entry point of the application and demonstrates the usage of the elevator system.

---

## Interview Discussion Points

### Common Interview Questions

1. **What algorithm do you use to select which elevator serves a request?**
   - **Current**: Nearest elevator (Manhattan distance)
   - **Better**: SCAN/LOOK algorithm (elevator continues in direction, serves requests along the way)
   - **Best**: Predictive algorithms using ML based on historical patterns

2. **How do you handle emergency situations (fire, power outage)?**
   - Add `EmergencyMode` state that overrides normal operation
   - Direct all elevators to ground floor
   - Disable new requests, complete current passengers safely
   - Add `EmergencyProtocol` interface with different implementations

3. **How would you optimize for peak hours (morning rush to office floors)?**
   - Implement **Zone Partitioning**: Assign elevators to floor ranges
   - **Group Control**: Multiple elevators work as a coordinated team
   - **Predictive Positioning**: Pre-position elevators at lobby during morning

4. **How do you prevent starvation (someone waiting forever)?**
   - Add **aging mechanism**: Increase request priority over time
   - Set maximum wait time threshold
   - Force assignment if threshold exceeded

5. **What if an elevator is overweight or over capacity?**
   - Add `WeightSensor` class
   - Check `currentWeight <= maxWeight` before closing doors
   - Display warning, reject last entry, or request passenger to exit

### Design Trade-offs

| Decision | Why Chosen | Trade-off |
|----------|------------|-----------|
| **Concurrent request processing** | Realistic multi-threaded environment | Complex synchronization, potential deadlocks |
| **Simple nearest-elevator selection** | Easy to implement and understand | Not optimal for high-traffic scenarios |
| **Single request queue per elevator** | Simplifies elevator logic | Doesn't consider direction efficiency |
| **No request prioritization** | Fair FIFO processing | Emergency/VIP requests can't jump queue |

### Scheduling Algorithms Comparison

| Algorithm | Pros | Cons | Best For |
|-----------|------|------|----------|
| **FCFS** (First Come First Serve) | Simple, fair | Inefficient, lots of direction changes | Low traffic |
| **SCAN** (Elevator Algorithm) | Efficient, predictable | Requests at ends wait longer | Medium-high traffic |
| **LOOK** | Like SCAN but reverses at last request | More efficient than SCAN | Most scenarios |
| **SSTF** (Shortest Seek Time First) | Minimizes travel time | Can cause starvation | Needs aging mechanism |
| **Destination Dispatch** | Pre-groups passengers by destination | Complex, expensive hardware | Modern high-rises |

### Optimizations to Discuss

1. **Request Batching**
   - Group requests going in same direction
   - Pick up multiple passengers on the way
   - Reduces total trips

2. **Load Balancing**
   - Distribute requests evenly across elevators
   - Consider current load of each elevator
   - Prevents one elevator from being overworked

3. **Energy Optimization**
   - Put idle elevators in sleep mode
   - Use regenerative braking
   - Smart positioning to minimize future travel

### Complexity Analysis

- **Request Assignment**: O(n) where n = number of elevators
- **Floor Movement**: O(m) where m = number of floors to travel
- **Optimal Elevator Selection**: O(n) linear search through elevators
- **Space Complexity**: O(e * r) where e = elevators, r = requests per elevator

### Real-World Considerations

1. **Hardware Integration**
   - Motor control APIs
   - Door sensor integration
   - Emergency button handling
   - Floor display updates

2. **Fault Tolerance**
   - What if an elevator breaks down?
   - Redistribute requests to other elevators
   - Maintenance mode scheduling

3. **Accessibility**
   - Audio announcements for visually impaired
   - Braille buttons
   - Wheelchair capacity considerations

### Follow-up Features
- **VIP/Express Elevators**: Non-stop service to certain floors
- **Double-Deck Elevators**: Two cars in one shaft serving adjacent floors
- **Destination Entry System**: Enter floor before boarding (modern systems)
- **Mobile App Integration**: Call elevator from phone, pre-select floor
- **Analytics**: Track usage patterns, maintenance prediction, energy consumption