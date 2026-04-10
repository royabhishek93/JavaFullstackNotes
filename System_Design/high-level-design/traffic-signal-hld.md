# Smart Traffic Signal System - High-Level Design

## 1. System Overview

A Smart Traffic Signal System is an IoT-enabled traffic management platform that optimizes traffic flow in smart cities. The system collects data from sensors, cameras, and vehicles, processes it in real-time to adjust signal timings dynamically, reduces congestion and emissions, integrates with emergency vehicle systems, provides analytics to city planners, and scales to manage thousands of intersections across a metropolitan area with high availability and fault tolerance.

## 2. Requirements

### Functional Requirements
- **Traffic Monitoring**: Detect vehicle count, speed, queue length at each lane
- **Signal Control**: Dynamic signal timing based on traffic density
- **Emergency Override**: Priority lanes for ambulances, fire trucks, police
- **Pedestrian Management**: Pedestrian crossing buttons, countdown timers
- **Coordination**: Synchronize signals across intersections (green wave)
- **Violation Detection**: Detect red-light violations, capture images
- **Analytics**: Traffic patterns, peak hours, congestion hotspots
- **Manual Override**: City operators can manually control signals
- **Adaptive Learning**: ML models predict traffic patterns
- **Integration**: Connect with GPS navigation apps (Google Maps, Waze)
- **Alerts**: Notify city control center of malfunctions, accidents

### Non-Functional Requirements
- **Availability**: 99.99% uptime (critical infrastructure)
- **Latency**: Signal decisions < 100ms
- **Scalability**: Support 10,000+ intersections per city
- **Reliability**: Fail-safe mode (flashing red/yellow on failure)
- **Real-time**: Process sensor data within 500ms
- **Security**: Encrypted communication, prevent signal manipulation
- **Resilience**: Continue operation during network outages
- **Audit**: Complete audit trail for compliance

## 3. Capacity Estimation

### Scale Assumptions
- **Total Intersections**: 10,000 intersections in a large city
- **Sensors per Intersection**: 12 sensors (3 per direction × 4 directions)
- **Sensor Data Rate**: 1 reading per second per sensor
- **Total Sensor Data**: 10K × 12 × 1 = 120K readings/sec
- **Signal Changes**: 10K intersections × 60 changes/hour = 167 changes/sec
- **Violation Events**: 1000 violations/day = 0.012 events/sec
- **Emergency Overrides**: 500 events/day = 0.006 events/sec

### Storage Estimation
- **Sensor Data**: 120K readings/sec × 100 bytes × 86400 sec/day = 1.04TB/day
- **Signal State Logs**: 167 changes/sec × 500 bytes × 86400 = 7.2GB/day
- **Violation Images**: 1000 violations/day × 500KB = 500MB/day
- **Analytics Data**: Aggregated hourly data = 10GB/day
- **Total Storage** (1 year): ~380TB (raw), ~50TB (aggregated)

### Bandwidth
- **Sensor Uplink**: 120K readings/sec × 100 bytes = 12MB/s
- **Signal Commands Downlink**: 167 commands/sec × 200 bytes = 33KB/s
- **Video Streams**: 1000 cameras × 2Mbps = 2Gbps (processed at edge)

## 4. System Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Edge Layer (Intersection)                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Single Intersection                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │  │
│  │  │  Vehicle │  │Pedestrian│  │  Camera  │              │  │
│  │  │ Sensors  │  │  Button  │  │ (Vision) │              │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘              │  │
│  │       └─────────────┼─────────────┘                     │  │
│  │                     │                                    │  │
│  │          ┌──────────▼──────────┐                        │  │
│  │          │ Edge Controller     │                        │  │
│  │          │ (Raspberry Pi/      │                        │  │
│  │          │  Industrial PC)     │                        │  │
│  │          │  - Local Logic      │                        │  │
│  │          │  - Fail-safe Mode   │                        │  │
│  │          │  - Cache Schedules  │                        │  │
│  │          └──────────┬──────────┘                        │  │
│  │                     │                                    │  │
│  │          ┌──────────▼──────────┐                        │  │
│  │          │ Traffic Light       │                        │  │
│  │          │ Controller (Relay)  │                        │  │
│  │          └─────────────────────┘                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────┬───────────────────────────────────────────────────┘
             │ (MQTT/CoAP over 4G/5G)
             │
┌────────────▼───────────────────────────────────────────────────┐
│                      Cloud Layer                               │
│                                                                 │
│          ┌──────────────────────┐                              │
│          │  IoT Gateway (MQTT)  │                              │
│          │  - Message Broker    │                              │
│          └──────────┬───────────┘                              │
│                     │                                           │
│        ┌────────────┼────────────────────┐                     │
│        │            │                    │                     │
│   ┌────▼─────┐ ┌───▼──────┐  ┌──────▼──────┐                 │
│   │  Signal  │ │  Sensor  │  │  Emergency  │                 │
│   │ Control  │ │  Data    │  │  Override   │                 │
│   │ Service  │ │ Service  │  │   Service   │                 │
│   └────┬─────┘ └───┬──────┘  └──────┬──────┘                 │
│        │           │                 │                         │
│        └───────────┼─────────────────┘                         │
│                    │                                           │
│        ┌───────────┼──────────────────────┐                   │
│        │           │                      │                   │
│   ┌────▼─────┐ ┌──▼────────┐  ┌──────▼──────┐               │
│   │  Traffic │ │Coordination│  │  Violation  │               │
│   │ Analytics│ │   Engine   │  │  Detection  │               │
│   │  (ML)    │ │            │  │   Service   │               │
│   └────┬─────┘ └──┬────────┘  └──────┬──────┘               │
│        │          │                   │                       │
│        └──────────┼───────────────────┘                       │
│                   │                                           │
│        ┌──────────▼──────────────────────┐                   │
│        │   Message Queue (Kafka)         │                   │
│        │  - sensor.data                  │                   │
│        │  - signal.changed               │                   │
│        │  - emergency.alert              │                   │
│        └──────────┬──────────────────────┘                   │
│                   │                                           │
│        ┌──────────┼────────────┐                             │
│        │          │            │                             │
│   ┌────▼────┐ ┌──▼──────┐ ┌───▼──────┐                      │
│   │  City   │ │ Time    │ │  Alert   │                      │
│   │ Control │ │ Series  │ │ Service  │                      │
│   │Dashboard│ │   DB    │ │          │                      │
│   └─────────┘ └─────────┘ └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Data Layer                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐              │
│  │PostgreSQL  │  │  InfluxDB  │  │   Redis    │              │
│  │(Metadata,  │  │ (Sensor    │  │  (State,   │              │
│  │ Configs)   │  │Time-Series)│  │   Cache)   │              │
│  └────────────┘  └────────────┘  └────────────┘              │
│                                                                 │
│  ┌────────────┐  ┌────────────┐                               │
│  │  MongoDB   │  │  Amazon S3 │                               │
│  │  (Events,  │  │ (Violation │                               │
│  │   Logs)    │  │  Images)   │                               │
│  └────────────┘  └────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## 5. Core Components

### Edge Controller (Intersection)
```python
class EdgeController:
    """Runs on industrial PC at each intersection"""
    
    def __init__(self, intersection_id):
        self.intersection_id = intersection_id
        self.current_phase = "NORTH_SOUTH_GREEN"
        self.sensor_readings = {}
        self.mqtt_client = MQTTClient()
        self.fail_safe_mode = False
        
        # Load cached schedule from local storage
        self.schedule = self.load_schedule()
    
    def run(self):
        """Main control loop"""
        while True:
            try:
                # Read sensors
                self.read_sensors()
                
                # Send data to cloud
                self.send_telemetry()
                
                # Get signal decision
                if self.mqtt_client.is_connected():
                    decision = self.request_signal_decision()
                    self.fail_safe_mode = False
                else:
                    # Fallback to local logic
                    decision = self.local_decision_logic()
                    self.fail_safe_mode = True
                
                # Apply signal change
                if decision:
                    self.change_signal(decision)
                
                time.sleep(1)  # 1 Hz control loop
                
            except Exception as e:
                logging.error(f"Error in control loop: {e}")
                self.activate_fail_safe()
    
    def read_sensors(self):
        """Read vehicle detection sensors"""
        
        # Loop detectors (magnetic sensors embedded in road)
        north_count = self.read_loop_detector("north")
        south_count = self.read_loop_detector("south")
        east_count = self.read_loop_detector("east")
        west_count = self.read_loop_detector("west")
        
        # Ultrasonic sensors (queue length)
        north_queue = self.read_ultrasonic_sensor("north")
        south_queue = self.read_ultrasonic_sensor("south")
        east_queue = self.read_ultrasonic_sensor("east")
        west_queue = self.read_ultrasonic_sensor("west")
        
        # Pedestrian buttons
        ped_north = self.read_button("ped_north")
        ped_south = self.read_button("ped_south")
        ped_east = self.read_button("ped_east")
        ped_west = self.read_button("ped_west")
        
        self.sensor_readings = {
            "vehicle_count": {
                "north": north_count,
                "south": south_count,
                "east": east_count,
                "west": west_count
            },
            "queue_length": {
                "north": north_queue,
                "south": south_queue,
                "east": east_queue,
                "west": west_queue
            },
            "pedestrian_waiting": {
                "north": ped_north,
                "south": ped_south,
                "east": ped_east,
                "west": ped_west
            },
            "timestamp": datetime.now().isoformat()
        }
    
    def send_telemetry(self):
        """Send sensor data to cloud"""
        
        message = {
            "intersection_id": self.intersection_id,
            "sensor_data": self.sensor_readings,
            "current_phase": self.current_phase,
            "fail_safe_mode": self.fail_safe_mode
        }
        
        self.mqtt_client.publish(
            topic=f"traffic/sensor/{self.intersection_id}",
            payload=json.dumps(message)
        )
    
    def local_decision_logic(self):
        """Fallback logic when cloud connection lost"""
        
        # Use pre-programmed schedule based on time of day
        current_time = datetime.now().time()
        
        # Peak hours: longer green for major roads
        if self.is_peak_hour(current_time):
            return self.schedule["peak_hour"]
        else:
            return self.schedule["off_peak"]
    
    def change_signal(self, decision):
        """Change traffic light colors"""
        
        new_phase = decision["phase"]
        duration = decision["duration"]
        
        # Safety: Always have yellow phase before red
        if self.requires_yellow_phase(self.current_phase, new_phase):
            self.set_lights(self.get_yellow_phase())
            time.sleep(3)  # 3 seconds yellow
        
        # Set new phase
        self.set_lights(new_phase)
        self.current_phase = new_phase
        
        # Log state change
        self.log_signal_change(new_phase, duration)
    
    def set_lights(self, phase):
        """Control relay to change lights"""
        
        # Example: North-South Green, East-West Red
        if phase == "NORTH_SOUTH_GREEN":
            self.relay.set("north_green", HIGH)
            self.relay.set("south_green", HIGH)
            self.relay.set("east_red", HIGH)
            self.relay.set("west_red", HIGH)
    
    def activate_fail_safe(self):
        """Emergency mode: flashing red/yellow"""
        
        while not self.mqtt_client.is_connected():
            self.relay.set_all("red", HIGH)
            time.sleep(1)
            self.relay.set_all("red", LOW)
            time.sleep(1)
```

### Signal Control Service
```python
class SignalControlService:
    """Cloud service for adaptive signal timing"""
    
    def __init__(self):
        self.redis = Redis()
        self.ml_model = load_model("traffic_predictor.pkl")
    
    def compute_signal_decision(self, intersection_id, sensor_data):
        """Compute optimal signal timing"""
        
        # Get intersection configuration
        config = self.get_intersection_config(intersection_id)
        
        # Get current signal state
        current_state = self.redis.hgetall(f"signal_state:{intersection_id}")
        
        # Check for emergency override
        emergency = self.check_emergency_override(intersection_id)
        if emergency:
            return self.emergency_signal_plan(emergency)
        
        # Calculate traffic density for each direction
        density = self.calculate_density(sensor_data)
        
        # Predict next 5 minutes traffic
        prediction = self.ml_model.predict(
            intersection_id=intersection_id,
            current_density=density,
            time_of_day=datetime.now().hour,
            day_of_week=datetime.now().weekday()
        )
        
        # Optimize signal timing using adaptive algorithm
        optimal_phase = self.adaptive_timing_algorithm(
            current_state=current_state,
            density=density,
            prediction=prediction,
            config=config
        )
        
        # Apply coordination with neighboring intersections
        if config["coordination_enabled"]:
            optimal_phase = self.coordinate_with_neighbors(
                intersection_id,
                optimal_phase
            )
        
        return optimal_phase
    
    def adaptive_timing_algorithm(self, current_state, density, prediction, config):
        """Webster's Method for optimal signal timing"""
        
        # Calculate cycle length (total time for all phases)
        total_traffic_flow = sum(density.values())
        
        if total_traffic_flow == 0:
            # No traffic: use minimum cycle
            cycle_length = config["min_cycle_length"]
        else:
            # Webster's formula
            L = config["lost_time"]  # Lost time per phase change
            Y = sum(density[d] / config["saturation_flow"] for d in density)
            
            cycle_length = (1.5 * L + 5) / (1 - Y)
            cycle_length = max(config["min_cycle_length"], 
                             min(cycle_length, config["max_cycle_length"]))
        
        # Allocate green time proportional to traffic density
        green_times = {}
        for direction, d in density.items():
            if total_traffic_flow > 0:
                green_times[direction] = (d / total_traffic_flow) * cycle_length
            else:
                green_times[direction] = cycle_length / len(density)
        
        # Build phase plan
        phases = []
        
        # Phase 1: North-South
        phases.append({
            "phase": "NORTH_SOUTH_GREEN",
            "duration": int(green_times["north"] + green_times["south"]),
            "directions": ["north", "south"]
        })
        
        # Phase 2: East-West
        phases.append({
            "phase": "EAST_WEST_GREEN",
            "duration": int(green_times["east"] + green_times["west"]),
            "directions": ["east", "west"]
        })
        
        # Return next phase
        current_phase = current_state["current_phase"]
        current_phase_start = datetime.fromisoformat(current_state["phase_start_time"])
        elapsed = (datetime.now() - current_phase_start).seconds
        
        # Find current phase in plan
        for i, phase in enumerate(phases):
            if phase["phase"] == current_phase:
                if elapsed >= phase["duration"]:
                    # Time to switch
                    next_phase = phases[(i + 1) % len(phases)]
                    return next_phase
                else:
                    # Continue current phase
                    return None
        
        # Default: start first phase
        return phases[0]
    
    def coordinate_with_neighbors(self, intersection_id, optimal_phase):
        """Coordinate with neighboring intersections (green wave)"""
        
        neighbors = self.get_neighboring_intersections(intersection_id)
        
        # Get states of all neighbors
        neighbor_states = {}
        for neighbor_id in neighbors:
            state = self.redis.hgetall(f"signal_state:{neighbor_id}")
            neighbor_states[neighbor_id] = state
        
        # Calculate offset to create green wave
        # Example: If arterial road, sync green phases
        arterial_direction = self.get_arterial_direction(intersection_id)
        
        if arterial_direction:
            # Calculate travel time to next intersection
            travel_time = self.calculate_travel_time(
                intersection_id,
                neighbors[arterial_direction]
            )
            
            # Adjust phase start time to align with neighbor
            optimal_phase["start_delay"] = travel_time
        
        return optimal_phase
```

### Emergency Override Service
```python
class EmergencyOverrideService:
    """Handle emergency vehicle priority"""
    
    def __init__(self):
        self.redis = Redis()
    
    def handle_emergency_vehicle(self, vehicle_id, location, destination):
        """Activate emergency mode for vehicle route"""
        
        # Calculate route from current location to destination
        route = self.calculate_route(location, destination)
        
        # Get all intersections on route
        intersections = self.get_intersections_on_route(route)
        
        # Activate emergency mode for each intersection
        for intersection_id in intersections:
            self.activate_emergency_mode(
                intersection_id,
                vehicle_id,
                estimated_arrival=self.estimate_arrival_time(vehicle_id, intersection_id)
            )
        
        # Monitor vehicle progress
        self.track_vehicle(vehicle_id, route)
    
    def activate_emergency_mode(self, intersection_id, vehicle_id, estimated_arrival):
        """Set intersection to emergency priority mode"""
        
        # Store emergency status in Redis
        self.redis.hset(
            f"emergency:{intersection_id}",
            vehicle_id,
            json.dumps({
                "activated_at": datetime.now().isoformat(),
                "estimated_arrival": estimated_arrival.isoformat(),
                "status": "ACTIVE"
            })
        )
        
        # Send command to edge controller
        mqtt_client.publish(
            topic=f"traffic/command/{intersection_id}",
            payload=json.dumps({
                "command": "EMERGENCY_OVERRIDE",
                "vehicle_id": vehicle_id,
                "direction": self.get_vehicle_direction(vehicle_id, intersection_id)
            })
        )
        
        # Notify city control center
        alert_service.send_alert(
            level="HIGH",
            message=f"Emergency override activated at intersection {intersection_id}",
            vehicle_id=vehicle_id
        )
    
    def deactivate_emergency_mode(self, intersection_id, vehicle_id):
        """Resume normal operation"""
        
        self.redis.hdel(f"emergency:{intersection_id}", vehicle_id)
        
        mqtt_client.publish(
            topic=f"traffic/command/{intersection_id}",
            payload=json.dumps({
                "command": "RESUME_NORMAL",
                "vehicle_id": vehicle_id
            })
        )
```

### Traffic Analytics Service
```python
class TrafficAnalyticsService:
    """Analyze traffic patterns and generate insights"""
    
    def __init__(self):
        self.influxdb = InfluxDBClient()
    
    def analyze_congestion(self, time_window="1h"):
        """Identify congestion hotspots"""
        
        # Query sensor data from InfluxDB
        query = f"""
        SELECT MEAN(vehicle_count) as avg_vehicles, 
               MEAN(queue_length) as avg_queue
        FROM sensor_data
        WHERE time > now() - {time_window}
        GROUP BY intersection_id
        """
        
        results = self.influxdb.query(query)
        
        # Identify congested intersections
        congested = []
        for point in results:
            if point["avg_queue"] > CONGESTION_THRESHOLD:
                congested.append({
                    "intersection_id": point["intersection_id"],
                    "avg_vehicles": point["avg_vehicles"],
                    "avg_queue": point["avg_queue"],
                    "congestion_level": self.calculate_congestion_level(point)
                })
        
        return sorted(congested, key=lambda x: x["congestion_level"], reverse=True)
    
    def generate_daily_report(self):
        """Generate daily traffic report"""
        
        report = {
            "date": datetime.now().date().isoformat(),
            "total_vehicles": self.count_total_vehicles(),
            "peak_hours": self.identify_peak_hours(),
            "congestion_hotspots": self.analyze_congestion("24h"),
            "signal_changes": self.count_signal_changes(),
            "violations": self.count_violations(),
            "emergency_overrides": self.count_emergency_overrides(),
            "average_wait_time": self.calculate_avg_wait_time()
        }
        
        return report
```

## 6. Database Design

```sql
-- Intersections Table
CREATE TABLE intersections (
    intersection_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    intersection_type VARCHAR(50), -- 4_WAY, T_JUNCTION, ROUNDABOUT
    lanes_config JSONB,
    coordination_group VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Signal Configurations Table
CREATE TABLE signal_configs (
    config_id BIGSERIAL PRIMARY KEY,
    intersection_id VARCHAR(50) REFERENCES intersections(intersection_id),
    min_cycle_length INT, -- seconds
    max_cycle_length INT,
    yellow_duration INT,
    all_red_duration INT,
    pedestrian_crossing_time INT,
    phases JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- InfluxDB Schema (Time-Series)
measurement: sensor_data
tags: intersection_id, direction
fields: vehicle_count, queue_length, avg_speed
time: timestamp

-- MongoDB Schema (Events)
{
  "_id": ObjectId,
  "event_type": "VIOLATION",
  "intersection_id": "INT001",
  "direction": "north",
  "vehicle_plate": "ABC123",
  "image_url": "s3://violations/...",
  "timestamp": ISODate,
  "violation_type": "RED_LIGHT"
}
```

## 7. API Design

### Get Signal State
```http
GET /api/v1/intersections/{intersection_id}/state
Authorization: Bearer <token>

Response: 200 OK
{
  "intersection_id": "INT001",
  "current_phase": "NORTH_SOUTH_GREEN",
  "phase_start_time": "2026-04-07T10:00:00Z",
  "remaining_seconds": 25,
  "next_phase": "EAST_WEST_GREEN"
}
```

### Emergency Override
```http
POST /api/v1/emergency/activate
Authorization: Bearer <token>

{
  "vehicle_id": "AMBULANCE_123",
  "current_location": {"lat": 37.7749, "lon": -122.4194},
  "destination": {"lat": 37.7849, "lon": -122.4294}
}

Response: 200 OK
{
  "route_id": "uuid",
  "intersections_activated": ["INT001", "INT002", "INT003"],
  "estimated_time_saved": 120
}
```

## 8. Scalability Strategy

- **Edge Computing**: Process sensor data locally
- **MQTT**: Lightweight protocol for IoT devices
- **Time-Series DB**: InfluxDB for sensor data
- **Redis**: Cache signal states
- **Kafka**: Stream processing for analytics

## 9. Technology Stack

| Component | Technology |
|-----------|-----------|
| **Edge Controller** | Raspberry Pi, Python |
| **IoT Protocol** | MQTT, CoAP |
| **Backend** | Java Spring Boot |
| **Time-Series DB** | InfluxDB |
| **Message Queue** | Kafka |
| **Cache** | Redis |
| **Analytics** | Apache Spark |

## 10. Interview Discussion Points

### Q1: How do you handle network failures?

**Answer**: Edge controllers have local fail-safe logic with pre-programmed schedules. They operate autonomously when cloud connection is lost.

### Q2: How do you prevent signal manipulation attacks?

**Answer**: Encrypted MQTT over TLS, signed commands with digital certificates, anomaly detection for suspicious patterns.

### Q3: How do you optimize for emergency vehicles?

**Answer**: GPS tracking of emergency vehicles, pre-clear intersections on predicted route, green wave coordination.

---

**End of Document**
