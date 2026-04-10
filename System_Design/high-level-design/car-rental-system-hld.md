# Car Rental System - High-Level Design

## 1. System Overview

A car rental system is a comprehensive platform that manages vehicle inventory, booking reservations, customer rentals, payment processing, vehicle tracking, and fleet management. The system must support multiple rental locations globally, handle millions of bookings annually, provide real-time vehicle availability, manage pricing dynamically, and integrate with insurance, payment gateways, and GPS tracking systems for seamless operations.

## 2. Requirements

### Functional Requirements
- **Vehicle Management**: Add, update, remove vehicles with specifications
- **Search & Discovery**: Search vehicles by location, type, dates, features
- **Booking Management**: Reserve, modify, cancel bookings
- **Pricing Engine**: Dynamic pricing based on demand, duration, vehicle type
- **Payment Processing**: Handle deposits, full payments, refunds
- **Check-in/Check-out**: Vehicle pickup and return process
- **User Management**: Customer profiles, rental history, loyalty programs
- **Fleet Management**: Maintenance tracking, vehicle status, utilization
- **Insurance Integration**: Optional insurance coverage
- **Location Management**: Multiple pickup/dropoff locations

### Non-Functional Requirements
- **Availability**: 99.9% uptime
- **Scalability**: Handle 1M+ bookings/month
- **Consistency**: Strong consistency for vehicle availability
- **Performance**: Search results < 500ms, booking < 2s
- **Reliability**: Zero double-bookings
- **Security**: PCI-DSS compliant payments

## 3. Capacity Estimation

### Scale Assumptions
- **Total Users**: 10M registered, 500K MAU
- **Daily Searches**: 2M searches/day = 23 QPS (peak 120 QPS)
- **Daily Bookings**: 30K bookings/day = 0.35 QPS (peak 2 QPS)
- **Fleet Size**: 100K vehicles across 500 locations
- **Average Booking**: 3 days rental
- **Booking Data Size**: 3KB per booking

### Storage Estimation
- **User Data**: 10M users × 2KB = 20GB
- **Vehicle Data**: 100K vehicles × 5KB = 500MB
- **Booking Data**: 30K/day × 3KB × 365 = 32.85GB/year
- **Historical Data** (5 years): ~165GB
- **Total Storage**: ~200GB (with replicas: 600GB)

### Bandwidth
- **Incoming**: 0.35 bookings/sec × 3KB = 1KB/s
- **Outgoing**: 23 searches/sec × 15KB = 345KB/s
- **Peak Bandwidth**: ~2MB/s

## 4. System Architecture

```
┌──────────────┐                    ┌─────────────────┐
│   Mobile     │◄───────────────────┤   API Gateway   │
│   Apps       │                    │  (Rate Limit,   │
└──────────────┘                    │   Auth, Route)  │
                                    └────────┬────────┘
┌──────────────┐                             │
│   Web        │◄────────────────────────────┘
│   Portal     │                             │
└──────────────┘              ┌──────────────┴──────────────┐
                              │                             │
                    ┌─────────▼─────────┐       ┌──────────▼──────────┐
                    │  Search Service   │       │  Booking Service    │
                    │  (Elasticsearch)  │       │  (Strong Consistency)│
                    └─────────┬─────────┘       └──────────┬──────────┘
                              │                             │
                    ┌─────────▼─────────┐       ┌──────────▼──────────┐
                    │   Redis Cache     │       │  Inventory Service  │
                    │ (Vehicle Avail.)  │       │  (Vehicle Locking)  │
                    └───────────────────┘       └──────────┬──────────┘
                                                            │
┌──────────────────────────────────────────────────────────┴──────────────┐
│                                                                          │
│    ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌──────────────┐     │
│    │ Vehicle  │  │  Pricing  │  │  Payment   │  │   Location   │     │
│    │ Service  │  │  Service  │  │  Service   │  │   Service    │     │
│    └────┬─────┘  └─────┬─────┘  └─────┬──────┘  └──────┬───────┘     │
│         │              │              │                 │              │
│    ┌────▼──────────────▼──────────────▼─────────────────▼───┐         │
│    │         Message Queue (Kafka)                           │         │
│    │  Topics: bookings, payments, notifications, tracking    │         │
│    └────┬──────────────┬──────────────┬─────────────────┬───┘         │
│         │              │              │                 │              │
│    ┌────▼────┐  ┌─────▼──────┐  ┌───▼──────┐  ┌──────▼──────┐       │
│    │ GPS     │  │Notification│  │ Analytics│  │   Audit     │       │
│    │Tracking │  │  Service   │  │ Service  │  │   Service   │       │
│    └─────────┘  └────────────┘  └──────────┘  └─────────────┘       │
└──────────────────────────────────────────────────────────────────────────┘

                    ┌────────────────────────────────┐
                    │  PostgreSQL (Primary/Replica)  │
                    │  Sharded by: location/region   │
                    └────────────────────────────────┘
```

## 5. Core Components

### Search Service
- **Elasticsearch**: Index vehicles with attributes (type, features, location)
- **Filters**: Price range, vehicle type, transmission, fuel type
- **Geo-Search**: Find vehicles within radius of location
- **Availability Check**: Query inventory service for real-time availability

### Booking Service
- **Reservation Logic**: Create, modify, cancel bookings
- **Two-Phase Commit**: Ensure atomicity (vehicle lock + payment)
- **Idempotency**: Prevent duplicate bookings
- **Timeout Management**: Release locked vehicles after 15 minutes

### Inventory Service
- **Vehicle Locking**: Lock vehicle during booking process
- **Availability Calculation**: Check vehicle not booked for requested dates
- **Maintenance Blocking**: Mark vehicles unavailable during maintenance
- **Real-time Updates**: Publish availability changes to cache

### Pricing Service
- **Dynamic Pricing**: Adjust prices based on demand, season, location
- **Discounts**: Apply promo codes, loyalty discounts, long-term rental rates
- **Surge Pricing**: Increase prices during high demand (holidays, events)
- **Rate Calculation**: Base rate + insurance + extras (GPS, child seat)

### Vehicle Service
- **Fleet Management**: Track vehicle status (AVAILABLE, RENTED, MAINTENANCE)
- **Maintenance Scheduling**: Schedule oil changes, inspections, repairs
- **Utilization Tracking**: Monitor vehicle usage, idle time
- **Damage Reporting**: Document damages with photos

### GPS Tracking Service
- **Real-time Location**: Track vehicle location every 30 seconds
- **Geofencing**: Alert if vehicle leaves allowed area
- **Telematics**: Monitor speed, harsh braking, fuel level
- **Theft Prevention**: Immobilize vehicle remotely if stolen

## 6. Database Design

### Schema Design

```sql
-- Vehicles Table
CREATE TABLE vehicles (
    vehicle_id BIGSERIAL PRIMARY KEY,
    license_plate VARCHAR(20) UNIQUE NOT NULL,
    vin VARCHAR(17) UNIQUE NOT NULL,
    make VARCHAR(50),
    model VARCHAR(50),
    year INT,
    color VARCHAR(30),
    vehicle_type VARCHAR(30), -- SEDAN, SUV, TRUCK, VAN
    transmission VARCHAR(20), -- AUTOMATIC, MANUAL
    fuel_type VARCHAR(20), -- GASOLINE, DIESEL, ELECTRIC, HYBRID
    seating_capacity INT,
    mileage INT,
    location_id BIGINT REFERENCES locations(location_id),
    status VARCHAR(20) DEFAULT 'AVAILABLE', -- AVAILABLE, RENTED, MAINTENANCE, RETIRED
    daily_rate DECIMAL(10,2),
    features JSONB, -- {"gps": true, "bluetooth": true, "backup_camera": true}
    last_maintenance_date DATE,
    next_maintenance_mileage INT,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_location_status (location_id, status),
    INDEX idx_type (vehicle_type),
    INDEX idx_plate (license_plate)
);

-- Locations Table
CREATE TABLE locations (
    location_id BIGSERIAL PRIMARY KEY,
    location_code VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50),
    postal_code VARCHAR(20),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    phone VARCHAR(20),
    operating_hours JSONB,
    is_airport BOOLEAN DEFAULT FALSE,
    INDEX idx_city (city),
    INDEX idx_geo (latitude, longitude)
);

-- Users Table
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    drivers_license_number VARCHAR(50),
    license_expiry_date DATE,
    license_state VARCHAR(50),
    loyalty_points INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_email (email),
    INDEX idx_license (drivers_license_number)
);

-- Bookings Table (Sharded by location_id)
CREATE TABLE bookings (
    booking_id BIGSERIAL PRIMARY KEY,
    booking_reference VARCHAR(10) UNIQUE NOT NULL,
    user_id BIGINT REFERENCES users(user_id),
    vehicle_id BIGINT REFERENCES vehicles(vehicle_id),
    pickup_location_id BIGINT REFERENCES locations(location_id),
    dropoff_location_id BIGINT REFERENCES locations(location_id),
    pickup_datetime TIMESTAMP NOT NULL,
    dropoff_datetime TIMESTAMP NOT NULL,
    booking_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, CONFIRMED, ACTIVE, COMPLETED, CANCELLED
    payment_status VARCHAR(20) DEFAULT 'PENDING',
    total_amount DECIMAL(10,2),
    deposit_amount DECIMAL(10,2),
    insurance_included BOOLEAN DEFAULT FALSE,
    extras JSONB, -- {"gps": true, "child_seat": 1}
    booking_date TIMESTAMP DEFAULT NOW(),
    idempotency_key VARCHAR(100) UNIQUE,
    INDEX idx_user_booking (user_id, booking_date),
    INDEX idx_vehicle_dates (vehicle_id, pickup_datetime, dropoff_datetime),
    INDEX idx_booking_ref (booking_reference),
    INDEX idx_status (booking_status)
);

-- Reservations Calendar (Availability Check)
CREATE TABLE vehicle_availability (
    availability_id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT REFERENCES vehicles(vehicle_id),
    booking_id BIGINT REFERENCES bookings(booking_id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20), -- RESERVED, BLOCKED, MAINTENANCE
    UNIQUE(vehicle_id, start_date, end_date),
    INDEX idx_vehicle_dates (vehicle_id, start_date, end_date)
);

-- Payments Table
CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    booking_id BIGINT REFERENCES bookings(booking_id),
    amount DECIMAL(10,2),
    payment_type VARCHAR(20), -- DEPOSIT, FULL_PAYMENT, REFUND
    payment_method VARCHAR(50),
    transaction_id VARCHAR(100),
    status VARCHAR(20),
    payment_date TIMESTAMP DEFAULT NOW(),
    INDEX idx_booking_payment (booking_id)
);

-- Vehicle Inspection Table
CREATE TABLE inspections (
    inspection_id BIGSERIAL PRIMARY KEY,
    booking_id BIGINT REFERENCES bookings(booking_id),
    vehicle_id BIGINT REFERENCES vehicles(vehicle_id),
    inspection_type VARCHAR(20), -- PICKUP, RETURN
    fuel_level DECIMAL(3,2), -- 0.00 to 1.00
    mileage INT,
    damages JSONB, -- [{"type": "scratch", "location": "front_bumper", "photo_url": "..."}]
    inspector_notes TEXT,
    inspected_by VARCHAR(100),
    inspection_date TIMESTAMP DEFAULT NOW(),
    INDEX idx_booking (booking_id),
    INDEX idx_vehicle (vehicle_id, inspection_date)
);

-- Maintenance Records Table
CREATE TABLE maintenance_records (
    maintenance_id BIGSERIAL PRIMARY KEY,
    vehicle_id BIGINT REFERENCES vehicles(vehicle_id),
    maintenance_type VARCHAR(50), -- OIL_CHANGE, TIRE_ROTATION, INSPECTION
    description TEXT,
    cost DECIMAL(10,2),
    mileage_at_service INT,
    service_date DATE,
    next_service_date DATE,
    performed_by VARCHAR(255),
    INDEX idx_vehicle (vehicle_id, service_date)
);
```

## 7. API Design

### Search Vehicles API
```http
POST /api/v1/vehicles/search
Content-Type: application/json

{
  "pickup_location": "LAX",
  "dropoff_location": "LAX",
  "pickup_datetime": "2026-06-15T10:00:00Z",
  "dropoff_datetime": "2026-06-18T10:00:00Z",
  "filters": {
    "vehicle_type": ["SEDAN", "SUV"],
    "transmission": "AUTOMATIC",
    "max_price_per_day": 100,
    "features": ["gps", "bluetooth"]
  }
}

Response: 200 OK
{
  "vehicles": [
    {
      "vehicle_id": 12345,
      "make": "Toyota",
      "model": "Camry",
      "year": 2024,
      "vehicle_type": "SEDAN",
      "transmission": "AUTOMATIC",
      "seating_capacity": 5,
      "daily_rate": 65.00,
      "total_price": 195.00,
      "features": ["gps", "bluetooth", "backup_camera"],
      "image_url": "https://cdn.carrental.com/toyota-camry.jpg"
    }
  ],
  "total_results": 15
}
```

### Create Booking API
```http
POST /api/v1/bookings
Content-Type: application/json
Authorization: Bearer <jwt_token>
Idempotency-Key: <unique_key>

{
  "vehicle_id": 12345,
  "pickup_location": "LAX",
  "dropoff_location": "LAX",
  "pickup_datetime": "2026-06-15T10:00:00Z",
  "dropoff_datetime": "2026-06-18T10:00:00Z",
  "insurance_included": true,
  "extras": {
    "gps": true,
    "child_seat": 1
  },
  "driver_info": {
    "license_number": "D1234567",
    "license_state": "CA",
    "license_expiry": "2028-12-31"
  }
}

Response: 201 Created
{
  "booking_id": 98765,
  "booking_reference": "CR123XYZ",
  "status": "PENDING",
  "total_amount": 245.00,
  "deposit_amount": 100.00,
  "payment_url": "https://pay.carrental.com/cr123xyz",
  "expires_at": "2026-04-07T10:15:00Z"
}
```

### Check Availability API
```http
GET /api/v1/vehicles/{vehicle_id}/availability?start=2026-06-15&end=2026-06-18

Response: 200 OK
{
  "vehicle_id": 12345,
  "available": true,
  "blocked_dates": [],
  "daily_rate": 65.00,
  "total_price": 195.00
}
```

### Vehicle Inspection API
```http
POST /api/v1/bookings/{booking_id}/inspection
Authorization: Bearer <jwt_token>

{
  "inspection_type": "PICKUP",
  "fuel_level": 1.0,
  "mileage": 15234,
  "damages": [
    {
      "type": "scratch",
      "location": "rear_bumper",
      "photo_url": "https://s3.carrental.com/damage-123.jpg"
    }
  ],
  "inspector_notes": "Minor scratch on rear bumper, pre-existing"
}

Response: 200 OK
{
  "inspection_id": 55678,
  "status": "COMPLETED",
  "booking_status": "ACTIVE"
}
```

## 8. Scalability Strategy

### Horizontal Scaling
- **Stateless Services**: All services are stateless for horizontal scaling
- **Auto-Scaling**: Kubernetes HPA based on CPU/memory
- **Load Balancer**: Distribute traffic across service instances

### Database Sharding
```
Shard Key Strategy:
- Vehicles: Shard by location_id (data locality)
- Bookings: Shard by pickup_location_id
- Users: Shard by user_id hash

Shard Distribution:
- US-West: Handles LAX, SFO, SEA locations
- US-East: Handles JFK, BOS, MIA locations
- Europe: Handles LHR, CDG, FRA locations
```

### Caching Strategy
```
Redis Cache:
- Vehicle availability (5 min TTL)
- Popular search results (15 min TTL)
- Pricing rules (1 hour TTL)
- Location details (24 hour TTL)

Cache Invalidation:
- Write-through: Update cache on booking creation
- Event-driven: Kafka events trigger cache updates
```

### Read Replicas
- **PostgreSQL**: 2 read replicas per primary
- **Search Service**: Dedicated read replicas for search queries
- **Replication Lag**: < 1 second

## 9. Fault Tolerance & High Availability

### Distributed Transactions
```python
class BookingOrchestrator:
    def create_booking(self, booking_request):
        try:
            # Step 1: Check availability and lock vehicle
            vehicle_lock = inventory_service.lock_vehicle(booking_request)
            
            # Step 2: Calculate pricing
            pricing = pricing_service.calculate(booking_request)
            
            # Step 3: Create booking record
            booking = booking_service.create(booking_request, pricing)
            
            # Step 4: Process payment
            payment = payment_service.charge(booking.deposit_amount)
            
            # Step 5: Confirm booking
            booking_service.confirm(booking.id)
            
            return booking
        except Exception as e:
            self.rollback(booking, vehicle_lock, payment)
            raise BookingFailedException()
```

### Circuit Breaker Pattern
```
Service          Threshold    Timeout    Fallback
Payment Service  50% errors   5s         Queue for retry
GPS Service      60% errors   3s         Skip tracking update
Pricing Service  70% errors   2s         Use cached base rate
```

### Data Backup & Recovery
- **Automated Backups**: Daily full backup + hourly incremental
- **Point-in-Time Recovery**: WAL archiving
- **RTO/RPO**: RTO < 30 minutes, RPO < 5 minutes

## 10. Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **API Gateway** | Kong | Rate limiting, auth, routing |
| **Application** | Node.js / Java Spring Boot | Microservices architecture |
| **Search Engine** | Elasticsearch | Full-text search, geo-search |
| **Primary Database** | PostgreSQL 14+ | ACID compliance |
| **Cache** | Redis Cluster | High-performance caching |
| **Message Queue** | Apache Kafka | Event streaming |
| **Object Storage** | AWS S3 | Vehicle images, inspection photos |
| **GPS Tracking** | AWS IoT Core | Vehicle telematics |
| **Payment Gateway** | Stripe | Payment processing |
| **Monitoring** | Prometheus + Grafana | Metrics, dashboards |

## 11. Interview Discussion Points

### Q1: How do you prevent double-booking of vehicles?

**Answer**: Pessimistic locking with time-based availability checks:

```sql
-- Check availability for date range
SELECT vehicle_id 
FROM vehicles v
WHERE v.vehicle_id = 12345
AND v.status = 'AVAILABLE'
AND NOT EXISTS (
    SELECT 1 FROM vehicle_availability va
    WHERE va.vehicle_id = v.vehicle_id
    AND va.start_date < '2026-06-18'
    AND va.end_date > '2026-06-15'
    AND va.status IN ('RESERVED', 'BLOCKED')
)
FOR UPDATE NOWAIT;

-- If available, insert reservation
INSERT INTO vehicle_availability (vehicle_id, booking_id, start_date, end_date, status)
VALUES (12345, 98765, '2026-06-15', '2026-06-18', 'RESERVED');
```

### Q2: How do you implement dynamic pricing?

**Answer**: ML-based pricing engine:

```python
def calculate_price(vehicle_id, pickup_date, dropoff_date, location_id):
    base_rate = get_base_rate(vehicle_id)
    
    # Factor 1: Demand (historical booking rate for dates)
    demand_multiplier = predict_demand(location_id, pickup_date)
    
    # Factor 2: Season (holidays, summer vs winter)
    season_multiplier = get_season_multiplier(pickup_date)
    
    # Factor 3: Duration (discount for longer rentals)
    duration_days = (dropoff_date - pickup_date).days
    duration_discount = 1.0 - (duration_days * 0.02 if duration_days > 7 else 0)
    
    # Factor 4: Inventory (lower price if many vehicles available)
    inventory_multiplier = get_inventory_multiplier(location_id, vehicle_type)
    
    final_rate = base_rate * demand_multiplier * season_multiplier * duration_discount * inventory_multiplier
    return final_rate * duration_days
```

### Q3: How do you handle vehicle tracking and theft prevention?

**Answer**: GPS tracking with geofencing:

```python
class VehicleTrackingService:
    def track_vehicle(self, vehicle_id):
        # Receive GPS data every 30 seconds
        location = get_gps_location(vehicle_id)
        
        # Check if vehicle is currently rented
        booking = get_active_booking(vehicle_id)
        
        if booking:
            # Check geofence (allowed area)
            if not is_within_geofence(location, booking.allowed_area):
                send_alert(booking.user_id, "Vehicle outside allowed area")
                notify_authorities(vehicle_id, location)
        else:
            # Vehicle not rented, should be at rental location
            if not is_at_rental_location(location, vehicle_id):
                send_alert(ADMIN, "Vehicle moved without active booking")
```

### Q4: How do you manage vehicle maintenance scheduling?

**Answer**: Predictive maintenance based on mileage and time:

```python
def schedule_maintenance(vehicle_id):
    vehicle = get_vehicle(vehicle_id)
    
    # Check mileage-based maintenance
    if vehicle.mileage >= vehicle.next_maintenance_mileage:
        block_vehicle(vehicle_id, "MAINTENANCE")
        create_maintenance_task(vehicle_id, "OIL_CHANGE")
    
    # Check time-based maintenance (annual inspection)
    if (today - vehicle.last_maintenance_date).days >= 365:
        block_vehicle(vehicle_id, "MAINTENANCE")
        create_maintenance_task(vehicle_id, "ANNUAL_INSPECTION")
    
    # Predictive maintenance (ML model)
    predicted_failure = predict_failure(vehicle_id, vehicle.mileage, vehicle.age)
    if predicted_failure.probability > 0.7:
        create_maintenance_task(vehicle_id, predicted_failure.component)
```

### Q5: How do you handle one-way rentals (different pickup/dropoff locations)?

**Answer**: Fleet rebalancing with pricing adjustments:

```python
def handle_one_way_rental(pickup_location, dropoff_location):
    # Calculate additional fee for one-way rental
    distance = calculate_distance(pickup_location, dropoff_location)
    one_way_fee = distance * PER_MILE_FEE
    
    # Check if this helps fleet rebalancing
    pickup_inventory = get_inventory_count(pickup_location)
    dropoff_inventory = get_inventory_count(dropoff_location)
    
    if pickup_inventory > dropoff_inventory:
        # Encourage this rental (discount)
        one_way_fee *= 0.5
    elif dropoff_inventory > pickup_inventory:
        # Discourage this rental (surcharge)
        one_way_fee *= 1.5
    
    # Schedule vehicle repositioning if needed
    schedule_vehicle_repositioning(pickup_location, dropoff_location)
    
    return one_way_fee
```

---

**End of Document**
