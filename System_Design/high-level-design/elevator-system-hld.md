# IoT Building Elevator Management System - High Level Design

## System Overview

A comprehensive IoT-enabled elevator management system for modern smart buildings that monitors and controls multiple elevators, optimizes elevator dispatching algorithms, tracks real-time location and status, predicts maintenance needs, handles emergency situations, provides analytics on usage patterns, supports remote monitoring and control, integrates with building access control, minimizes wait times, balances load distribution, and ensures passenger safety. The system must manage hundreds of elevators across multiple buildings, process thousands of ride requests daily, provide sub-second response times for elevator assignment, maintain 99.9% uptime, support peak hour traffic efficiently, and enable predictive maintenance to prevent failures.

## Requirements

### Functional Requirements

1. **Elevator Control & Monitoring**
   - Real-time elevator status tracking (floor, direction, occupancy)
   - Monitor elevator health (door sensors, cables, motors)
   - Emergency stop and alarm handling
   - Manual override for maintenance
   - Remote elevator control

2. **Request Handling**
   - Floor call buttons (up/down)
   - Cabin destination buttons
   - Priority requests (VIP, emergency)
   - Group elevator control
   - Destination dispatch systems

3. **Dispatching Algorithm**
   - Optimal elevator assignment for requests
   - Load balancing across elevators
   - Minimize average wait time
   - Energy-efficient routing
   - Peak hour optimization

4. **Access Control Integration**
   - RFID/key card integration
   - Restricted floor access
   - Visitor management
   - Touchless controls (mobile app)

5. **Maintenance & Monitoring**
   - Predictive maintenance alerts
   - Service scheduling
   - Fault detection and diagnostics
   - Usage analytics and reporting
   - Energy consumption monitoring

6. **User Features**
   - Mobile app for elevator calls
   - Estimated arrival time display
   - Real-time occupancy information
   - Building navigation
   - Accessibility features

### Non-Functional Requirements

1. **Performance**
   - Elevator assignment within 500ms
   - Real-time status updates (< 1 second latency)
   - Handle 1000+ requests per minute during peak hours
   - Support 500+ elevators per system

2. **Availability**
   - 99.9% system uptime
   - Graceful degradation (manual operation if system fails)
   - Zero single point of failure
   - Hot standby for critical components

3. **Reliability**
   - No missed floor requests
   - Accurate floor position tracking
   - Fail-safe emergency handling
   - Data persistence for audit trails

4. **Safety**
   - Emergency stop within 1 second
   - Overload detection and prevention
   - Fire mode operation
   - Earthquake mode operation
   - Door obstruction detection

5. **Scalability**
   - Support multiple buildings (multi-tenancy)
   - Scale from 1 to 500+ elevators per building
   - Distributed architecture
   - Cloud-based management

## Capacity Estimation

### Traffic Estimates

**Assumptions:**
- Buildings managed: 100 buildings
- Average elevators per building: 10
- Total elevators: 1,000
- Average floors per building: 30
- Daily rides per elevator: 500
- Peak hour rides: 100 rides/hour per elevator
- Average ride duration: 2 minutes

**Calculations:**

**Requests Per Second (RPS):**
- Daily rides: 1,000 elevators * 500 rides = 500K rides/day
- Average RPS: 500K / 86400 = ~6 requests/second
- Peak RPS (8-9 AM rush hour): 1,000 elevators * 100 rides/hour / 3600 = ~28 requests/second

**Sensor Data (Telemetry):**
- Telemetry frequency: 1 update per second per elevator
- Total telemetry: 1,000 elevators * 1 update/second = 1,000 messages/second
- Daily telemetry messages: 1,000 * 86,400 = 86.4M messages/day

**Events:**
- Floor arrivals: 500K rides * 10 floors average = 5M events/day
- Door open/close: 500K * 2 * 2 (per floor) = 2M events/day
- Button presses: 500K * 3 average = 1.5M events/day

### Storage Estimates

**Elevator Metadata:**
- 1,000 elevators * 10KB = 10MB

**Ride History:**
- 500K rides/day * 2KB per ride = 1GB/day
- Annual: 365GB
- 5-year retention: ~1.8TB

**Telemetry Data (Time-Series):**
- 86.4M messages/day * 500 bytes = 43.2GB/day
- With compression (5:1): ~8.6GB/day
- 90-day retention: ~780GB
- 1-minute aggregates (1 year): ~100GB
- Total telemetry: ~880GB

**Maintenance Logs:**
- 1,000 elevators * 2 maintenance/month * 5KB = 10MB/month = 600MB/5 years

**Event Logs:**
- 8.5M events/day * 1KB = 8.5GB/day
- 30-day retention: ~255GB

**Total Storage:**
- Primary: ~3TB
- With replicas (3x): ~9TB
- Total with backups: ~12TB

### Bandwidth Estimates

**Incoming (Telemetry + Events):**
- Telemetry: 1,000 updates/second * 500 bytes = 500 KB/s
- Floor requests: 28 requests/second (peak) * 500 bytes = 14 KB/s
- Events: ~100 events/second * 1KB = 100 KB/s
- Total incoming: ~600 KB/s (~5 Mbps)

**Outgoing (Control Commands + UI):**
- Elevator assignments: 28 commands/second * 1KB = 28 KB/s
- Dashboard updates: 100 clients * 10 KB/s = 1 MB/s
- Mobile app updates: 1,000 active users * 1 KB/s = 1 MB/s
- Total outgoing: ~2 MB/s (~16 Mbps)

**Total Bandwidth: ~3 MB/s (~25 Mbps)**

## System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Physical Elevator System                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Floor Call  │  │  Cabin       │  │  Sensors     │        │
│  │  Buttons     │  │  Controller  │  │  (Position,  │        │
│  │  (Up/Down)   │  │  (PLC)       │  │   Door,      │        │
│  │              │  │              │  │   Weight)    │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                 │                 │                 │
│  ┌──────▼─────────────────▼─────────────────▼──────┐         │
│  │        Elevator Controller (Edge Device)         │         │
│  │        - Raspberry Pi / Industrial PC            │         │
│  │        - MQTT Client                             │         │
│  │        - Local control logic                     │         │
│  │        - Offline operation support               │         │
│  └──────┬───────────────────────────────────────────┘         │
│         │ 4G/5G/WiFi/Ethernet                                 │
└─────────┼──────────────────────────────────────────────────────┘
          │
          │ MQTT over TLS
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                    IoT Gateway / MQTT Broker                   │
│               (AWS IoT Core / Azure IoT Hub)                   │
│  - Device authentication                                      │
│  - Message routing                                            │
│  - Protocol translation                                       │
└─────────┬─────────────────────────────────────────────────────┘
          │
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                       Cloud Backend                            │
│                                                                │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────┐           │
│  │   API      │  │   Device    │  │   Elevator   │           │
│  │  Gateway   │  │  Management │  │   Control    │           │
│  └─────┬──────┘  └──────┬──────┘  └──────┬───────┘           │
│        │                │                 │                   │
│  ┌─────▼────────────────▼─────────────────▼──────┐            │
│  │        Message Queue (Kafka / RabbitMQ)       │            │
│  │  Topics: telemetry, requests, commands        │            │
│  └─────┬────────────────┬─────────────────┬──────┘            │
│        │                │                 │                   │
│  ┌─────▼──────┐  ┌─────▼──────┐  ┌──────▼────────┐          │
│  │ Dispatching│  │ Maintenance│  │  Analytics    │          │
│  │  Service   │  │  Prediction│  │   Service     │          │
│  │  (Core     │  │  Service   │  │               │          │
│  │  Algorithm)│  │  (ML)      │  │               │          │
│  └─────┬──────┘  └─────┬──────┘  └──────┬────────┘          │
│        │                │                 │                   │
│  ┌─────▼────────────────▼─────────────────▼──────┐            │
│  │           Time-Series Database                │            │
│  │             (InfluxDB / TimescaleDB)          │            │
│  └────────────────────────────────────────────────┘            │
│                                                                │
│  ┌────────────────────────────────────────────────┐            │
│  │           PostgreSQL (Elevators, Buildings,    │            │
│  │           Maintenance Records, Users)          │            │
│  └────────────────────────────────────────────────┘            │
│                                                                │
│  ┌────────────────────────────────────────────────┐            │
│  │           Redis (Elevator State Cache,         │            │
│  │           Request Queue, Locks)                │            │
│  └────────────────────────────────────────────────┘            │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                  Client Applications                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Admin      │  │   Mobile     │  │   Building   │        │
│  │  Dashboard   │  │   App        │  │   Management │        │
│  │  (Web)       │  │  (iOS/       │  │   Dashboard  │        │
│  │              │  │   Android)   │  │              │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
└────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Elevator Controller (Edge Device)

**Hardware:**
- Industrial PC or Raspberry Pi
- Connected to elevator's PLC (Programmable Logic Controller)
- Sensors: Position sensors, weight sensors, door sensors
- Actuators: Motor control, door control

**Software:**
- MQTT client for communication
- Local control logic (fallback for offline operation)
- Real-time OS for deterministic behavior
- Buffering for offline scenarios

**Responsibilities:**
- Read sensor data (position, speed, door status, weight)
- Execute movement commands
- Handle emergency stops
- Report telemetry to cloud
- Local safety checks

**Communication:**
```
MQTT Topics:
- Publish: elevator/{elevator_id}/telemetry
- Publish: elevator/{elevator_id}/events
- Subscribe: elevator/{elevator_id}/commands
```

### 2. IoT Gateway (AWS IoT Core / Azure IoT Hub)

**Responsibilities:**
- Device authentication (X.509 certificates)
- MQTT message brokering
- Message routing to backend services
- Device registry and management
- Device shadow (desired vs reported state)

**Device Shadow Example:**
```json
{
  "desired": {
    "target_floor": 10,
    "door_state": "OPEN"
  },
  "reported": {
    "current_floor": 8,
    "door_state": "CLOSED",
    "direction": "UP",
    "occupancy": 5,
    "weight_kg": 375,
    "status": "MOVING"
  },
  "timestamp": 1712345678
}
```

### 3. Elevator Control Service

**Responsibilities:**
- Process floor requests
- Assign elevators to requests (dispatching)
- Send movement commands to elevators
- Handle priority requests (VIP, emergency)
- Coordinate group elevator control

**API Endpoints:**
```
POST /api/v1/elevators/{elevatorId}/request-floor
POST /api/v1/buildings/{buildingId}/call-elevator
GET /api/v1/elevators/{elevatorId}/status
POST /api/v1/elevators/{elevatorId}/emergency-stop
```

### 4. Dispatching Service (Core Algorithm)

**Responsibilities:**
- Optimal elevator assignment
- Minimize average wait time
- Load balancing
- Energy optimization
- Group control algorithms

**Dispatching Algorithms:**

**1. Nearest Car (Simple)**
```python
def nearest_car_algorithm(request_floor, direction, elevators):
    """
    Assign elevator that is closest to request floor
    """
    available_elevators = [e for e in elevators if e.status == 'IDLE' or 
                          (e.direction == direction and 
                           ((direction == 'UP' and e.current_floor <= request_floor) or
                            (direction == 'DOWN' and e.current_floor >= request_floor)))]
    
    if not available_elevators:
        # All busy, assign least loaded
        return min(elevators, key=lambda e: len(e.pending_requests))
    
    # Find nearest
    return min(available_elevators, key=lambda e: abs(e.current_floor - request_floor))
```

**2. SCAN Algorithm (Elevator goes up, then down)**
```python
class ElevatorController:
    def __init__(self, elevator_id):
        self.elevator_id = elevator_id
        self.current_floor = 0
        self.direction = 'UP'  # UP, DOWN, IDLE
        self.pending_requests = set()
        self.destination_floors = set()
    
    def add_request(self, floor, direction):
        self.pending_requests.add((floor, direction))
    
    def next_floor(self):
        """
        SCAN algorithm: Move in current direction, serve all requests in that direction
        Then reverse direction
        """
        if self.direction == 'UP':
            # Get floors above current floor
            floors_above = [f for f, d in self.pending_requests if f > self.current_floor]
            floors_above.extend([f for f in self.destination_floors if f > self.current_floor])
            
            if floors_above:
                return min(floors_above)  # Go to nearest floor above
            else:
                # No more floors above, reverse direction
                self.direction = 'DOWN'
                return self.next_floor()
        
        elif self.direction == 'DOWN':
            # Get floors below current floor
            floors_below = [f for f, d in self.pending_requests if f < self.current_floor]
            floors_below.extend([f for f in self.destination_floors if f < self.current_floor])
            
            if floors_below:
                return max(floors_below)  # Go to nearest floor below
            else:
                # No more floors below, reverse direction
                self.direction = 'UP'
                return self.next_floor()
        
        else:  # IDLE
            if self.pending_requests or self.destination_floors:
                self.direction = 'UP'
                return self.next_floor()
            return self.current_floor
```

**3. Destination Dispatch (Advanced)**
```python
def destination_dispatch_algorithm(passenger_request, elevators):
    """
    Assign elevator that minimizes total wait time for all passengers
    """
    best_elevator = None
    min_cost = float('inf')
    
    for elevator in elevators:
        # Calculate cost (wait time) if this elevator is assigned
        simulated_elevator = simulate_elevator_with_request(elevator, passenger_request)
        
        # Cost function: average wait time for all passengers
        cost = calculate_total_wait_time(simulated_elevator)
        
        if cost < min_cost:
            min_cost = cost
            best_elevator = elevator
    
    return best_elevator

def calculate_total_wait_time(elevator):
    """
    Calculate total wait time for all passengers in elevator
    """
    current_floor = elevator.current_floor
    current_time = 0
    total_wait = 0
    
    for request in sorted(elevator.pending_requests, key=lambda r: r.pickup_floor):
        # Time to reach pickup floor
        travel_time = abs(request.pickup_floor - current_floor) * 3  # 3 seconds per floor
        current_time += travel_time
        
        # Wait time for this passenger
        total_wait += current_time
        
        # Update current floor
        current_floor = request.destination_floor
    
    return total_wait
```

**4. Group Elevator Control (Zoning)**
```python
def group_control_with_zoning(building_floors, elevators):
    """
    Assign elevators to specific floor zones during peak hours
    """
    # Divide building into zones
    floors_per_zone = building_floors // len(elevators)
    
    zones = {}
    for i, elevator in enumerate(elevators):
        start_floor = i * floors_per_zone
        end_floor = start_floor + floors_per_zone
        zones[elevator.elevator_id] = (start_floor, end_floor)
    
    # Assign requests to elevators based on zone
    def assign_to_zone(request_floor):
        for elevator_id, (start, end) in zones.items():
            if start <= request_floor < end:
                return elevator_id
        return elevators[0].elevator_id  # Fallback
```

### 5. Maintenance Prediction Service (ML)

**Responsibilities:**
- Predict component failures
- Generate maintenance alerts
- Optimize maintenance schedules
- Reduce unplanned downtime

**ML Model:**
```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

class MaintenancePredictionModel:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100)
    
    def prepare_features(self, elevator_telemetry):
        """
        Extract features for maintenance prediction
        """
        features = {
            # Usage metrics
            'total_trips': elevator_telemetry['trip_count'],
            'operating_hours': elevator_telemetry['operating_hours'],
            'avg_trips_per_day': elevator_telemetry['trip_count'] / 30,
            
            # Performance metrics
            'avg_door_open_time': elevator_telemetry['avg_door_open_time'],
            'door_open_failures': elevator_telemetry['door_open_failures'],
            'emergency_stops': elevator_telemetry['emergency_stop_count'],
            'avg_response_time': elevator_telemetry['avg_response_time'],
            
            # Health metrics
            'motor_temperature': elevator_telemetry['motor_temp_avg'],
            'motor_vibration': elevator_telemetry['motor_vibration_avg'],
            'cable_tension': elevator_telemetry['cable_tension'],
            'brake_wear': elevator_telemetry['brake_wear_level'],
            
            # Age
            'days_since_last_maintenance': elevator_telemetry['days_since_maintenance'],
            'elevator_age_years': elevator_telemetry['age_years']
        }
        
        return pd.DataFrame([features])
    
    def predict_maintenance_needed(self, elevator_id):
        """
        Predict if maintenance is needed in next 7 days
        """
        # Fetch recent telemetry
        telemetry = get_elevator_telemetry(elevator_id, days=30)
        
        # Prepare features
        features = self.prepare_features(telemetry)
        
        # Predict (0 = no maintenance, 1 = maintenance needed)
        prediction = self.model.predict(features)[0]
        probability = self.model.predict_proba(features)[0][1]
        
        if probability > 0.7:
            create_maintenance_alert(elevator_id, priority='HIGH', 
                                    reason=f'ML model predicts failure (probability: {probability})')
        
        return prediction, probability
```

**Anomaly Detection:**
```python
def detect_anomalies(elevator_id):
    """
    Detect unusual patterns in elevator behavior
    """
    # Get recent metrics
    recent_metrics = influx.query(f"""
        SELECT mean(door_open_time), stddev(door_open_time),
               mean(trip_duration), stddev(trip_duration)
        FROM elevator_telemetry
        WHERE elevator_id = '{elevator_id}'
        AND time > now() - 7d
    """)
    
    current_metrics = influx.query(f"""
        SELECT door_open_time, trip_duration
        FROM elevator_telemetry
        WHERE elevator_id = '{elevator_id}'
        AND time > now() - 1h
    """)
    
    # Check for anomalies (> 3 standard deviations)
    mean_door_time = recent_metrics['mean_door_open_time']
    std_door_time = recent_metrics['stddev_door_open_time']
    
    for metric in current_metrics:
        if abs(metric['door_open_time'] - mean_door_time) > 3 * std_door_time:
            create_alert(elevator_id, 'DOOR_ANOMALY', 
                        f'Door open time: {metric["door_open_time"]}s (normal: {mean_door_time}s)')
```

### 6. Analytics Service

**Responsibilities:**
- Usage statistics (rides per day, peak hours)
- Performance metrics (average wait time, trip duration)
- Energy consumption analysis
- Occupancy patterns
- Building traffic flow

**Metrics:**
- Average wait time per floor
- Average ride duration
- Peak hour traffic
- Elevator utilization rate
- Energy consumption per ride
- Maintenance frequency
- Uptime percentage

### 7. Access Control Integration

**Responsibilities:**
- RFID/key card authentication
- Restricted floor access
- Visitor management
- Integration with building security

**Flow:**
```
1. User taps RFID card at elevator lobby
2. System checks user permissions
3. If authorized, send request to elevator with user's allowed floors
4. Elevator assigned and arrives
5. User enters cabin, only authorized floors are lit
6. User selects floor, elevator moves
7. Log access event
```

## Database Schema

### Buildings Table

```sql
CREATE TABLE buildings (
    building_id SERIAL PRIMARY KEY,
    building_name VARCHAR(255) NOT NULL,
    address VARCHAR(500),
    total_floors INT,
    basement_floors INT,
    timezone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (building_name)
);
```

### Elevators Table

```sql
CREATE TABLE elevators (
    elevator_id SERIAL PRIMARY KEY,
    building_id INT REFERENCES buildings(building_id),
    elevator_name VARCHAR(100),
    capacity_kg INT,
    max_passengers INT,
    min_floor INT, -- Can be negative for basement
    max_floor INT,
    speed_mps DECIMAL(4,2), -- meters per second
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, MAINTENANCE, OUT_OF_SERVICE
    installation_date DATE,
    last_maintenance_date DATE,
    next_maintenance_date DATE,
    model VARCHAR(100),
    manufacturer VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_building (building_id),
    INDEX idx_status (status)
);
```

### Elevator State (Redis)

```
Key: elevator:state:{elevator_id}
Value: JSON
{
  "elevator_id": 1,
  "current_floor": 8,
  "target_floor": 12,
  "direction": "UP", // UP, DOWN, IDLE
  "door_state": "CLOSED", // OPEN, CLOSED, OPENING, CLOSING
  "occupancy": 5,
  "weight_kg": 375,
  "speed_mps": 1.5,
  "status": "MOVING", // IDLE, MOVING, DOOR_OPEN, MAINTENANCE, ERROR
  "pending_requests": [
    {"floor": 10, "direction": "UP"},
    {"floor": 15, "direction": "DOWN"}
  ],
  "destination_floors": [12, 15],
  "last_updated": 1712345678
}

TTL: 2 hours (auto-expire if elevator offline)
```

### Ride Requests Table (Redis Queue)

```
Key: requests:{building_id}:{floor}
Value: List of requests

{
  "request_id": "req_xyz123",
  "building_id": 1,
  "floor": 10,
  "direction": "UP",
  "user_id": 12345, // Optional, if from mobile app
  "priority": "NORMAL", // NORMAL, VIP, EMERGENCY
  "requested_at": 1712345678,
  "assigned_elevator_id": 3,
  "status": "ASSIGNED" // PENDING, ASSIGNED, COMPLETED, CANCELLED
}
```

### Rides History Table (Partitioned)

```sql
CREATE TABLE rides (
    ride_id BIGSERIAL,
    elevator_id INT REFERENCES elevators(elevator_id),
    start_floor INT,
    end_floor INT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INT,
    wait_time_seconds INT,
    passenger_count INT,
    weight_kg INT,
    ride_date DATE,
    PRIMARY KEY (ride_id, ride_date),
    INDEX idx_elevator_date (elevator_id, ride_date),
    INDEX idx_building_date (building_id, ride_date)
) PARTITION BY RANGE (ride_date);

-- Monthly partitions
CREATE TABLE rides_2026_04 PARTITION OF rides
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
```

### Maintenance Records Table

```sql
CREATE TABLE maintenance_records (
    maintenance_id SERIAL PRIMARY KEY,
    elevator_id INT REFERENCES elevators(elevator_id),
    maintenance_type VARCHAR(50), -- PREVENTIVE, CORRECTIVE, EMERGENCY
    description TEXT,
    issue_detected TEXT,
    action_taken TEXT,
    parts_replaced JSONB,
    cost DECIMAL(10,2),
    technician_name VARCHAR(255),
    scheduled_date TIMESTAMP,
    completed_date TIMESTAMP,
    status VARCHAR(20), -- SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED
    next_maintenance_date DATE,
    INDEX idx_elevator (elevator_id, scheduled_date),
    INDEX idx_status (status)
);
```

### Telemetry Data (InfluxDB)

```
Measurement: elevator_telemetry

Tags:
- elevator_id
- building_id

Fields:
- current_floor (int)
- direction (string)
- speed_mps (float)
- door_state (string)
- occupancy (int)
- weight_kg (int)
- motor_temperature (float)
- motor_vibration (float)
- cable_tension (float)
- door_open_time (float)
- trip_duration (float)

Timestamp: time

Retention Policies:
- Raw data: 90 days
- 1-minute aggregates: 1 year
- 1-hour aggregates: 5 years
```

### Alerts Table

```sql
CREATE TABLE alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    elevator_id INT REFERENCES elevators(elevator_id),
    alert_type VARCHAR(50), -- MAINTENANCE_DUE, DOOR_FAILURE, OVERLOAD, ERROR
    severity VARCHAR(20), -- INFO, WARNING, CRITICAL, EMERGENCY
    message TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(255),
    INDEX idx_elevator_unresolved (elevator_id, resolved, created_at)
);
```

## API Design

### Elevator Control APIs

```
POST /api/v1/buildings/{buildingId}/call-elevator
Authorization: Bearer <jwt_token>

{
  "floor": 10,
  "direction": "UP"
}

Response: 200 OK
{
  "request_id": "req_xyz123",
  "assigned_elevator_id": 3,
  "elevator_name": "Elevator A",
  "current_floor": 5,
  "estimated_arrival_time_seconds": 15,
  "message": "Elevator A is on the way"
}

POST /api/v1/elevators/{elevatorId}/request-floor
Authorization: Bearer <jwt_token>

{
  "destination_floor": 20
}

Response: 200 OK
{
  "status": "ACCEPTED",
  "current_floor": 10,
  "estimated_time_seconds": 30
}

GET /api/v1/elevators/{elevatorId}/status

Response: 200 OK
{
  "elevator_id": 3,
  "elevator_name": "Elevator A",
  "building_id": 1,
  "current_floor": 12,
  "target_floor": 15,
  "direction": "UP",
  "door_state": "CLOSED",
  "occupancy": 5,
  "max_passengers": 10,
  "weight_kg": 375,
  "capacity_kg": 750,
  "status": "MOVING",
  "next_stops": [15, 18, 20]
}

POST /api/v1/elevators/{elevatorId}/emergency-stop
Authorization: Bearer <admin_token>

Response: 200 OK
{
  "status": "STOPPED",
  "current_floor": 12,
  "message": "Elevator stopped. Emergency services notified."
}
```

### Analytics APIs

```
GET /api/v1/buildings/{buildingId}/analytics?period=7d

Response: 200 OK
{
  "building_id": 1,
  "period": "7d",
  "total_rides": 5432,
  "avg_wait_time_seconds": 18,
  "avg_ride_duration_seconds": 45,
  "peak_hours": [
    {"hour": 8, "rides": 320},
    {"hour": 9, "rides": 280},
    {"hour": 17, "rides": 290},
    {"hour": 18, "rides": 310}
  ],
  "elevator_utilization": [
    {"elevator_id": 1, "utilization_percent": 72},
    {"elevator_id": 2, "utilization_percent": 68},
    {"elevator_id": 3, "utilization_percent": 75}
  ],
  "energy_consumption_kwh": 1250
}

GET /api/v1/elevators/{elevatorId}/maintenance-prediction

Response: 200 OK
{
  "elevator_id": 3,
  "maintenance_probability": 0.75,
  "recommended_action": "SCHEDULE_MAINTENANCE",
  "estimated_days_until_failure": 12,
  "issues": [
    "Door mechanism showing increased opening time",
    "Motor temperature slightly elevated"
  ]
}
```

### MQTT Protocol (Device Communication)

```
# Elevator publishes telemetry
Topic: elevator/{elevator_id}/telemetry

Payload:
{
  "elevator_id": 3,
  "current_floor": 12,
  "direction": "UP",
  "speed_mps": 1.5,
  "door_state": "CLOSED",
  "occupancy": 5,
  "weight_kg": 375,
  "motor_temp_c": 65,
  "timestamp": 1712345678
}

# Server sends command to elevator
Topic: elevator/{elevator_id}/commands

Payload:
{
  "command": "MOVE_TO_FLOOR",
  "target_floor": 15,
  "command_id": "cmd_abc123"
}

# Elevator acknowledges command
Topic: elevator/{elevator_id}/commands/ack

Payload:
{
  "command_id": "cmd_abc123",
  "status": "ACCEPTED",
  "timestamp": 1712345680
}

# Elevator sends event (floor arrival)
Topic: elevator/{elevator_id}/events

Payload:
{
  "event_type": "FLOOR_ARRIVAL",
  "floor": 15,
  "timestamp": 1712345720
}
```

## Scalability Strategies

### 1. Multi-Building Support (Multi-Tenancy)

```
Isolation:
- Each building has separate Redis keyspace
- Database partitioning by building_id
- Dedicated message queue per building

Routing:
- API Gateway routes requests based on building_id
- Each building can have dedicated processing pods
```

### 2. Horizontal Scaling

**Stateless Services:**
- Elevator Control Service: Scale based on request rate
- Analytics Service: Scale based on query load

**Stateful Components:**
- Redis Cluster: Shared state for elevator positions
- Kafka: Distributed message queue

### 3. Geographic Distribution

**Multi-Region Deployment:**
```
Region 1 (US-East): Buildings in East Coast
Region 2 (US-West): Buildings in West Coast
Region 3 (EU): Buildings in Europe

Benefits:
- Low latency (closer to elevators)
- Compliance (data residency)
- High availability (region failover)
```

## Safety & Reliability

### 1. Fail-Safe Design

```
Offline Operation:
- If cloud connection lost, elevator controller operates independently
- Basic SCAN algorithm runs locally
- When reconnected, sync state to cloud

Redundancy:
- Dual IoT gateways (primary + backup)
- Redis Sentinel for automatic failover
- Database replication (primary + standby)
```

### 2. Emergency Handling

```python
def handle_emergency(elevator_id, emergency_type):
    if emergency_type == 'FIRE':
        # Fire mode: Return all elevators to ground floor
        send_command(elevator_id, 'FIRE_MODE', target_floor=0)
    
    elif emergency_type == 'EARTHQUAKE':
        # Stop at nearest floor, open doors
        send_command(elevator_id, 'STOP_NEAREST_FLOOR')
        send_command(elevator_id, 'OPEN_DOORS')
    
    elif emergency_type == 'OVERLOAD':
        # Alert passengers, don't close doors
        send_command(elevator_id, 'OVERLOAD_ALERT')
        send_command(elevator_id, 'KEEP_DOORS_OPEN')
    
    elif emergency_type == 'POWER_FAILURE':
        # Activate emergency power, move to nearest floor
        send_command(elevator_id, 'EMERGENCY_POWER_MODE')
    
    # Notify building security and emergency services
    notify_emergency_services(elevator_id, emergency_type)
```

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Edge Device** | Raspberry Pi / Industrial PC | GPIO for sensors, MQTT support |
| **IoT Platform** | AWS IoT Core / Azure IoT Hub | Managed MQTT, device registry |
| **Message Protocol** | MQTT over TLS | Lightweight, pub/sub, reliable |
| **Backend** | Python / Go | Real-time processing, ML support |
| **API Gateway** | Kong / AWS API Gateway | Auth, routing, rate limiting |
| **Primary DB** | PostgreSQL | ACID, complex queries |
| **Time-Series DB** | InfluxDB / TimescaleDB | Optimized for telemetry |
| **Cache** | Redis Cluster | Real-time state, low latency |
| **Message Queue** | Kafka / RabbitMQ | Event streaming |
| **ML Framework** | Scikit-learn / TensorFlow | Predictive maintenance |
| **Monitoring** | Prometheus + Grafana | Metrics, dashboards |
| **Alerting** | PagerDuty | On-call alerts |

## Interview Q&A

### Question 1: How would you design an optimal elevator dispatching algorithm to minimize average wait time?

**Answer:**

Use **collective control** with **cost-based assignment**:

```python
class OptimalDispatchingAlgorithm:
    def assign_elevator(self, request, elevators):
        """
        Assign elevator that minimizes total system cost
        """
        best_elevator = None
        min_cost = float('inf')
        
        for elevator in elevators:
            # Calculate cost for assigning this elevator
            cost = self.calculate_cost(elevator, request)
            
            if cost < min_cost:
                min_cost = cost
                best_elevator = elevator
        
        return best_elevator
    
    def calculate_cost(self, elevator, request):
        """
        Cost function considers:
        1. Wait time for new passenger
        2. Additional time for existing passengers
        3. Energy consumption
        4. Load balancing
        """
        # Component 1: Wait time for new passenger
        wait_time = self.estimate_wait_time(elevator, request.floor)
        
        # Component 2: Impact on existing passengers
        existing_passenger_delay = self.estimate_delay_for_existing(elevator, request)
        
        # Component 3: Energy cost (prefer elevator moving in same direction)
        energy_cost = self.calculate_energy_cost(elevator, request)
        
        # Component 4: Load balancing (penalize overutilized elevators)
        load_penalty = len(elevator.pending_requests) * 5
        
        # Weighted sum
        total_cost = (wait_time * 1.0 + 
                     existing_passenger_delay * 0.5 + 
                     energy_cost * 0.3 + 
                     load_penalty * 0.2)
        
        return total_cost
    
    def estimate_wait_time(self, elevator, request_floor):
        """
        Estimate time for elevator to reach request floor
        """
        if elevator.status == 'IDLE':
            # Simple: distance * time per floor
            return abs(elevator.current_floor - request_floor) * 3  # 3 seconds per floor
        
        # Elevator is busy, simulate its path
        simulated_floor = elevator.current_floor
        simulated_time = 0
        
        # Process existing stops
        for stop_floor in elevator.get_stops_before(request_floor):
            simulated_time += abs(stop_floor - simulated_floor) * 3
            simulated_time += 5  # Door open/close time
            simulated_floor = stop_floor
        
        # Time to reach request floor
        simulated_time += abs(request_floor - simulated_floor) * 3
        
        return simulated_time
    
    def estimate_delay_for_existing(self, elevator, new_request):
        """
        How much delay does adding this request cause for existing passengers?
        """
        # Calculate total travel time without new request
        time_without = self.total_travel_time(elevator.pending_requests)
        
        # Calculate total travel time with new request
        time_with = self.total_travel_time(elevator.pending_requests + [new_request])
        
        return time_with - time_without
    
    def calculate_energy_cost(self, elevator, request):
        """
        Energy cost based on direction changes
        """
        if elevator.direction == request.direction:
            return 0  # Same direction, no extra cost
        elif elevator.status == 'IDLE':
            return 5  # Small cost to start moving
        else:
            return 20  # High cost to reverse direction
```

**Advanced: Machine Learning Approach**

```python
class MLBasedDispatching:
    def __init__(self):
        self.model = train_rl_model()  # Reinforcement Learning
    
    def assign_elevator(self, request, elevators, historical_data):
        """
        Use RL model trained on historical data
        """
        # State: current elevator positions, request queue, time of day
        state = self.encode_state(elevators, request)
        
        # Action: which elevator to assign
        action = self.model.predict(state)
        
        return elevators[action]
    
    def encode_state(self, elevators, request):
        """
        Encode current system state for ML model
        """
        return {
            'elevator_positions': [e.current_floor for e in elevators],
            'elevator_directions': [e.direction for e in elevators],
            'request_floor': request.floor,
            'time_of_day': current_hour(),
            'queue_length': len(get_pending_requests())
        }
```

### Question 2: How do you handle the "elevator paradox" where an elevator keeps serving requests in one direction and never reverses?

**Answer:**

Implement **maximum service time** and **fairness constraints**:

```python
class FairDispatchingAlgorithm:
    MAX_SERVICE_TIME = 120  # Max 2 minutes in one direction
    MAX_WAIT_TIME = 60      # Max wait time for any request
    
    def should_reverse_direction(self, elevator):
        """
        Decide if elevator should reverse even if there are more requests in current direction
        """
        # Check 1: Has elevator been moving in same direction too long?
        if elevator.time_in_current_direction > self.MAX_SERVICE_TIME:
            return True
        
        # Check 2: Are there starving requests in opposite direction?
        opposite_requests = self.get_opposite_direction_requests(elevator)
        for request in opposite_requests:
            wait_time = time.time() - request.requested_at
            if wait_time > self.MAX_WAIT_TIME:
                return True  # Priority to starving requests
        
        # Check 3: No more requests in current direction?
        if not self.has_requests_in_current_direction(elevator):
            return True
        
        return False
    
    def get_next_direction(self, elevator):
        """
        Determine next direction considering fairness
        """
        if self.should_reverse_direction(elevator):
            # Reverse direction
            return 'DOWN' if elevator.direction == 'UP' else 'UP'
        
        # Continue in current direction
        return elevator.direction
```

**Starvation Prevention:**

```python
class PriorityQueue:
    def add_request(self, request):
        # Assign priority based on wait time
        request.priority = self.calculate_priority(request)
        self.queue.append(request)
        self.queue.sort(key=lambda r: r.priority, reverse=True)
    
    def calculate_priority(self, request):
        """
        Higher priority for longer wait times
        """
        wait_time = time.time() - request.requested_at
        
        # Priority increases exponentially with wait time
        if wait_time < 15:
            return 1  # Normal priority
        elif wait_time < 30:
            return 5  # Medium priority
        elif wait_time < 60:
            return 10  # High priority
        else:
            return 100  # Critical (starvation prevention)
```

### Question 3: How would you implement predictive maintenance using IoT sensor data?

**Answer:**

**Multi-Model Approach:**

```python
class PredictiveMaintenanceSystem:
    def __init__(self):
        # Model 1: Anomaly detection
        self.anomaly_detector = IsolationForest(contamination=0.1)
        
        # Model 2: Time-to-failure prediction
        self.survival_model = RandomSurvivalForest()
        
        # Model 3: Component-specific failure prediction
        self.component_models = {
            'door': RandomForestClassifier(),
            'motor': RandomForestClassifier(),
            'cable': RandomForestClassifier(),
            'brake': RandomForestClassifier()
        }
    
    def predict_maintenance(self, elevator_id):
        """
        Multi-stage prediction
        """
        # Stage 1: Fetch recent telemetry
        telemetry = self.fetch_telemetry(elevator_id, days=30)
        
        # Stage 2: Anomaly detection (real-time)
        is_anomaly = self.detect_anomaly(telemetry)
        if is_anomaly:
            create_alert(elevator_id, 'ANOMALY_DETECTED')
        
        # Stage 3: Predict time until failure
        time_to_failure = self.predict_time_to_failure(telemetry)
        
        # Stage 4: Predict component-specific failures
        component_risks = self.predict_component_failures(telemetry)
        
        # Stage 5: Generate maintenance recommendation
        return self.generate_recommendation(time_to_failure, component_risks)
    
    def detect_anomaly(self, telemetry):
        """
        Detect unusual patterns using Isolation Forest
        """
        features = self.extract_features(telemetry)
        anomaly_score = self.anomaly_detector.decision_function([features])[0]
        
        # Negative score = anomaly
        return anomaly_score < -0.5
    
    def predict_time_to_failure(self, telemetry):
        """
        Predict days until failure using survival analysis
        """
        features = self.extract_features(telemetry)
        survival_probability = self.survival_model.predict_survival_function([features])
        
        # Find time when survival probability drops below 20%
        for t, prob in enumerate(survival_probability):
            if prob < 0.2:
                return t  # days
        
        return None  # No failure predicted
    
    def predict_component_failures(self, telemetry):
        """
        Predict failure probability for each component
        """
        risks = {}
        
        for component, model in self.component_models.items():
            features = self.extract_component_features(telemetry, component)
            failure_prob = model.predict_proba([features])[0][1]
            risks[component] = failure_prob
        
        return risks
    
    def generate_recommendation(self, time_to_failure, component_risks):
        """
        Generate actionable maintenance recommendation
        """
        if time_to_failure and time_to_failure < 7:
            # Critical: Schedule immediate maintenance
            return {
                'priority': 'CRITICAL',
                'action': 'SCHEDULE_IMMEDIATE',
                'estimated_days': time_to_failure,
                'components_at_risk': [c for c, r in component_risks.items() if r > 0.7]
            }
        
        elif any(risk > 0.7 for risk in component_risks.values()):
            # High risk component detected
            high_risk_components = [c for c, r in component_risks.items() if r > 0.7]
            return {
                'priority': 'HIGH',
                'action': 'SCHEDULE_WITHIN_WEEK',
                'components_at_risk': high_risk_components
            }
        
        elif time_to_failure and time_to_failure < 30:
            # Medium priority
            return {
                'priority': 'MEDIUM',
                'action': 'SCHEDULE_WITHIN_MONTH',
                'estimated_days': time_to_failure
            }
        
        else:
            # Normal maintenance schedule
            return {
                'priority': 'NORMAL',
                'action': 'ROUTINE_MAINTENANCE'
            }
    
    def extract_features(self, telemetry):
        """
        Extract relevant features from raw telemetry
        """
        return {
            'avg_door_open_time': np.mean(telemetry['door_open_time']),
            'std_door_open_time': np.std(telemetry['door_open_time']),
            'door_failures': np.sum(telemetry['door_failures']),
            'avg_motor_temp': np.mean(telemetry['motor_temp']),
            'max_motor_temp': np.max(telemetry['motor_temp']),
            'avg_vibration': np.mean(telemetry['motor_vibration']),
            'trip_count': len(telemetry['trips']),
            'emergency_stops': np.sum(telemetry['emergency_stops']),
            'cable_tension_variance': np.var(telemetry['cable_tension']),
            'days_since_maintenance': (datetime.now() - telemetry['last_maintenance']).days
        }
```

---

**End of Document**
