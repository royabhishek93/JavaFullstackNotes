# Ride-Sharing Service - High-Level Design

## System Overview
A ride-sharing platform like Uber, Lyft, or Didi enables real-time matching between riders and drivers, GPS-based tracking, dynamic pricing, payments, ratings, and route optimization. The system handles millions of concurrent users, processes real-time location updates, calculates ETAs, manages surge pricing during peak demand, and ensures safety through background checks and in-ride monitoring.

## Requirements

### Functional Requirements
1. **User Management**: Rider and driver registration, profiles, verification, documents
2. **Location Tracking**: Real-time GPS tracking of drivers and active rides
3. **Ride Matching**: Match riders with nearby available drivers based on location, rating, vehicle type
4. **Ride Request**: Request ride, specify pickup/destination, select ride type (economy, premium, XL)
5. **ETA Calculation**: Estimate time of arrival for driver to pickup and trip duration
6. **Pricing**: Base fare + distance + time + surge pricing + tolls
7. **Payment**: Credit/debit cards, wallets, cash, split payment, tips
8. **Navigation**: Turn-by-turn directions for drivers, optimal route calculation
9. **Ride Status**: Real-time ride tracking for riders, share ETA with friends
10. **Ratings & Reviews**: Riders rate drivers, drivers rate riders (1-5 stars)
11. **Safety**: SOS button, share trip, driver background checks, ride recording
12. **Notifications**: Push, SMS for ride requests, driver arrival, trip complete

### Non-Functional Requirements
- **Availability**: 99.99% uptime (52 minutes downtime/year)
- **Latency**: < 100ms for location updates, < 3 seconds for ride matching
- **Throughput**: 10M concurrent riders, 5M active drivers globally
- **Scalability**: Handle 100M rides/day, 500 ride requests/second
- **Consistency**: Strong consistency for payments, eventual for location
- **Geo-Distribution**: Multi-region deployment for global coverage
- **Real-time**: WebSocket for live location updates (1-second intervals)

## Capacity Estimation

### Traffic Estimates
- **Daily Active Users**: 50M riders, 10M drivers
- **Rides per day**: 25M rides
- **Rides per second**: 25M / 86400 = 289 RPS (average)
- **Peak RPS**: 289 * 3 = 867 RPS (rush hour)
- **Location updates**: 10M drivers * 1 update/sec = 10M updates/sec
- **WebSocket connections**: 15M concurrent (active drivers + riders in trip)

### Storage Estimates
- **Users**: 100M riders * 5KB = 500GB, 10M drivers * 10KB = 100GB
- **Rides**: 25M rides/day * 2KB = 50GB/day = 18TB/year
- **Location History**: 10M drivers * 86400 sec/day * 100 bytes = 86TB/day
- **Total Storage (3 years)**: 18TB * 3 + 86TB * 365 * 3 = 94PB

### Bandwidth Estimates
- **Location Updates In**: 10M updates/sec * 200 bytes = 2GB/s = 16 Gbps
- **Location Updates Out** (riders tracking): 10M riders * 200 bytes/sec = 2GB/s = 16 Gbps
- **Total Bandwidth**: 32 Gbps

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Client Applications                                │
│         (Rider App, Driver App, Web Dashboard, Admin Panel)                 │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ HTTPS/WSS
┌──────────────────────────────▼──────────────────────────────────────────────┐
│                API Gateway + WebSocket Gateway                               │
│          (Auth, Rate Limiting, Protocol Translation)                         │
└──────┬───────────┬───────────┬─────────┬─────────┬──────────┬──────────────┘
       │           │           │         │         │          │
  ┌────▼─────┐ ┌──▼──────┐ ┌──▼────┐ ┌──▼─────┐ ┌▼──────┐ ┌─▼───────┐
  │Location  │ │Matching │ │Trip   │ │Payment │ │Pricing│ │Notif    │
  │Service   │ │Service  │ │Service│ │Service │ │Service│ │Service  │
  └────┬─────┘ └───┬─────┘ └───┬───┘ └───┬────┘ └───┬───┘ └────┬────┘
       │           │           │         │          │          │
  ┌────▼───────────▼───────────▼─────────▼──────────▼──────────▼─────┐
  │              Redis Cluster (Cache + Geospatial)                   │
  │     (Driver Locations, Active Trips, Pricing Cache)               │
  └────────────────────────────┬──────────────────────────────────────┘
                               │
  ┌────────────────────────────▼──────────────────────────────────────┐
  │           PostgreSQL Cluster (Primary + Replicas)                  │
  │      (Users, Drivers, Trips, Payments, Ratings)                   │
  └────────────────────────────┬──────────────────────────────────────┘
                               │
  ┌────────────────────────────▼──────────────────────────────────────┐
  │              Cassandra (Time-Series Data)                          │
  │         (Location History, Trip Events, Analytics)                │
  └────────────────────────────┬──────────────────────────────────────┘
                               │
  ┌────────────────────────────▼──────────────────────────────────────┐
  │                  Kafka (Event Streaming)                           │
  │      (Location Events, Trip Events, Payment Events)               │
  └────┬──────────┬───────────┬──────────────┬────────────────────────┘
       │          │           │              │
  ┌────▼────┐ ┌──▼─────┐ ┌───▼────┐ ┌──────▼──────┐
  │Analytics│ │ML/ETA  │ │Fraud   │ │ Metrics     │
  │Pipeline │ │Service │ │Detection│ │ Aggregation │
  └─────────┘ └────────┘ └────────┘ └─────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              External Integrations                                │
├──────────────┬─────────────────┬──────────────┬────────────────┤
│ Google Maps  │ Payment Gateway │ SMS/Push     │ Background     │
│ (Routes/ETA) │ (Stripe)        │ (Twilio/FCM) │ Check APIs     │
└──────────────┴─────────────────┴──────────────┴────────────────┘
```

## Core Components

### 1. Location Service
**Responsibilities**:
- Receive real-time GPS updates from drivers (1-second intervals)
- Store driver locations in Redis Geospatial index
- Query nearby drivers within radius
- Track ride progress and update ETA
- Store location history for auditing

**Technology**: Go (high throughput), Redis Geo
**Protocol**: WebSocket (bidirectional real-time)

**Implementation**:
```go
// Location update from driver
func (s *LocationService) UpdateDriverLocation(driverID string, lat, lng float64) {
    // Store in Redis Geospatial index
    redis.GeoAdd(ctx, "drivers:locations", &redis.GeoLocation{
        Name:      driverID,
        Longitude: lng,
        Latitude:  lat,
    })
    
    // Set TTL (5 minutes - if no update, considered offline)
    redis.Expire(ctx, "driver:"+driverID+":location", 5*time.Minute)
    
    // Publish to Kafka for history
    kafka.Publish("location.updates", LocationEvent{
        DriverID:  driverID,
        Latitude:  lat,
        Longitude: lng,
        Timestamp: time.Now(),
    })
    
    // If driver is on active trip, notify rider
    if trip := s.getActiveTrip(driverID); trip != nil {
        s.notifyRider(trip.RiderID, lat, lng)
    }
}

// Find nearby drivers
func (s *LocationService) FindNearbyDrivers(lat, lng float64, radiusKm float64) []Driver {
    // Redis GeoRadius query
    locations := redis.GeoRadius(ctx, "drivers:locations", lng, lat, &redis.GeoRadiusQuery{
        Radius: radiusKm,
        Unit:   "km",
        Sort:   "ASC", // Nearest first
        Count:  20,
    })
    
    var drivers []Driver
    for _, loc := range locations {
        driver := s.getDriver(loc.Name)
        
        // Filter only available drivers
        if driver.Status == "AVAILABLE" {
            drivers = append(drivers, driver)
        }
    }
    
    return drivers
}
```

### 2. Matching Service
**Responsibilities**:
- Match ride requests with suitable drivers
- Consider distance, rating, vehicle type, driver acceptance rate
- Handle driver rejection and retry logic
- Implement matching algorithms (closest first, highest rated, etc.)

**Technology**: Spring Boot, Redis
**Algorithm**: Closest driver with rating > 4.5

**Matching Flow**:
```java
@Service
public class MatchingService {
    
    public MatchResult matchRide(RideRequest request) {
        // 1. Find nearby drivers (within 5km)
        List<Driver> nearbyDrivers = locationService
            .findNearbyDrivers(request.getPickupLat(), 
                             request.getPickupLng(), 5.0);
        
        // 2. Filter by vehicle type and rating
        List<Driver> eligible = nearbyDrivers.stream()
            .filter(d -> d.getVehicleType().equals(request.getRideType()))
            .filter(d -> d.getRating() >= 4.5)
            .filter(d -> d.getAcceptanceRate() >= 0.8)
            .collect(Collectors.toList());
        
        if (eligible.isEmpty()) {
            return MatchResult.noDriversAvailable();
        }
        
        // 3. Sort by distance (closest first)
        eligible.sort(Comparator.comparing(d -> 
            calculateDistance(request.getPickupLat(), request.getPickupLng(),
                            d.getLatitude(), d.getLongitude())));
        
        // 4. Try to assign to drivers (top 5)
        for (Driver driver : eligible.subList(0, Math.min(5, eligible.size()))) {
            // Send ride request to driver
            boolean accepted = sendRideRequest(driver.getId(), request);
            
            if (accepted) {
                // Create trip
                Trip trip = createTrip(request, driver);
                return MatchResult.success(trip);
            }
        }
        
        // No driver accepted
        return MatchResult.noDriversAccepted();
    }
    
    private boolean sendRideRequest(String driverID, RideRequest request) {
        // Send via push notification and WebSocket
        notificationService.sendToDriver(driverID, 
            new RideRequestNotification(request));
        
        // Wait for response (30 seconds timeout)
        CompletableFuture<Boolean> response = new CompletableFuture<>();
        pendingRequests.put(driverID + ":" + request.getId(), response);
        
        try {
            return response.get(30, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            // Driver didn't respond, try next driver
            return false;
        }
    }
}
```

### 3. Trip Service
**Responsibilities**:
- Manage trip lifecycle (requested → matched → started → completed → paid)
- Calculate fare based on distance, time, surge pricing
- Handle trip cancellations
- Store trip details and receipts

**Technology**: Spring Boot, PostgreSQL
**State Machine**: Trip status transitions

**Trip State Machine**:
```java
public enum TripStatus {
    REQUESTED,        // Rider requested
    DRIVER_ASSIGNED,  // Driver matched
    DRIVER_ARRIVED,   // Driver at pickup
    IN_PROGRESS,      // Trip started
    COMPLETED,        // Trip ended
    CANCELLED,        // Cancelled by rider/driver
    PAID              // Payment completed
}

@Service
public class TripService {
    
    @Transactional
    public Trip startTrip(String tripId, String otp) {
        Trip trip = tripRepository.findById(tripId);
        
        // Verify OTP
        if (!trip.getOtp().equals(otp)) {
            throw new InvalidOTPException();
        }
        
        // Verify driver at pickup location
        Driver driver = driverService.getDriver(trip.getDriverId());
        double distance = calculateDistance(
            trip.getPickupLat(), trip.getPickupLng(),
            driver.getLatitude(), driver.getLongitude()
        );
        
        if (distance > 0.1) { // 100 meters
            throw new DriverNotAtPickupException();
        }
        
        // Update trip status
        trip.setStatus(TripStatus.IN_PROGRESS);
        trip.setStartTime(Instant.now());
        trip.setStartOdometerReading(driver.getOdometerReading());
        tripRepository.save(trip);
        
        // Notify rider
        notificationService.notifyRider(trip.getRiderId(), 
            "Your trip has started");
        
        // Publish event
        kafka.publish("trip.started", trip);
        
        return trip;
    }
    
    @Transactional
    public Trip completeTrip(String tripId) {
        Trip trip = tripRepository.findById(tripId);
        
        // Calculate final fare
        BigDecimal fare = pricingService.calculateFare(trip);
        
        // Update trip
        trip.setStatus(TripStatus.COMPLETED);
        trip.setEndTime(Instant.now());
        trip.setFinalFare(fare);
        tripRepository.save(trip);
        
        // Process payment
        paymentService.chargeRider(trip.getRiderId(), fare, trip.getId());
        
        // Update driver earnings
        driverService.addEarnings(trip.getDriverId(), 
            fare.multiply(new BigDecimal("0.75"))); // 75% to driver
        
        // Request ratings
        notificationService.requestRating(trip.getRiderId(), trip.getDriverId());
        
        return trip;
    }
}
```

### 4. Pricing Service
**Responsibilities**:
- Calculate fare: base + distance + time + surge + tolls
- Implement surge pricing during high demand
- Apply discounts and promo codes
- Store pricing history

**Technology**: Spring Boot, Redis (surge multiplier cache)

**Pricing Formula**:
```
Total Fare = (Base Fare + Distance Fee + Time Fee) × Surge Multiplier + Tolls + Taxes
Where:
- Base Fare: $2.50
- Distance Fee: $1.50/km
- Time Fee: $0.30/minute
- Surge Multiplier: 1.0 to 5.0 (based on demand)
```

**Implementation**:
```java
@Service
public class PricingService {
    
    public BigDecimal calculateFare(Trip trip) {
        // 1. Base fare
        BigDecimal baseFare = getBaseFare(trip.getRideType());
        
        // 2. Distance fee
        double distanceKm = calculateDistance(trip);
        BigDecimal distanceFee = getDistanceRate(trip.getRideType())
            .multiply(BigDecimal.valueOf(distanceKm));
        
        // 3. Time fee
        long durationMinutes = ChronoUnit.MINUTES.between(
            trip.getStartTime(), trip.getEndTime());
        BigDecimal timeFee = getTimeRate(trip.getRideType())
            .multiply(BigDecimal.valueOf(durationMinutes));
        
        // 4. Subtotal
        BigDecimal subtotal = baseFare.add(distanceFee).add(timeFee);
        
        // 5. Apply surge multiplier
        BigDecimal surgeMultiplier = getSurgeMultiplier(
            trip.getPickupLat(), trip.getPickupLng(), trip.getStartTime());
        BigDecimal fareWithSurge = subtotal.multiply(surgeMultiplier);
        
        // 6. Add tolls
        BigDecimal tolls = calculateTolls(trip.getRoute());
        
        // 7. Apply discount
        BigDecimal discount = applyDiscount(trip.getRiderId(), 
                                           trip.getPromoCode());
        
        // 8. Final fare
        BigDecimal finalFare = fareWithSurge.add(tolls).subtract(discount);
        
        return finalFare.setScale(2, RoundingMode.HALF_UP);
    }
    
    private BigDecimal getSurgeMultiplier(double lat, double lng, Instant time) {
        String geoHash = GeoHash.encode(lat, lng, 6); // ~1km precision
        String cacheKey = "surge:" + geoHash + ":" + 
                         time.truncatedTo(ChronoUnit.MINUTES);
        
        // Check cache
        String cached = redis.get(cacheKey);
        if (cached != null) {
            return new BigDecimal(cached);
        }
        
        // Calculate surge based on demand/supply ratio
        int demandCount = getRideRequestCount(geoHash, time);
        int supplyCount = getAvailableDriverCount(geoHash);
        
        double ratio = (double) demandCount / Math.max(supplyCount, 1);
        
        BigDecimal multiplier;
        if (ratio < 1.0) {
            multiplier = BigDecimal.ONE; // No surge
        } else if (ratio < 2.0) {
            multiplier = new BigDecimal("1.5"); // 1.5x
        } else if (ratio < 3.0) {
            multiplier = new BigDecimal("2.0"); // 2x
        } else {
            multiplier = new BigDecimal("3.0"); // 3x (max)
        }
        
        // Cache for 1 minute
        redis.setex(cacheKey, 60, multiplier.toString());
        
        return multiplier;
    }
}
```

### 5. Payment Service
**Responsibilities**:
- Process payments via multiple methods (card, wallet, cash)
- Handle payment failures and retries
- Manage driver payouts
- Apply refunds for cancellations

**Technology**: Spring Boot, Stripe, PostgreSQL

### 6. ETA Service
**Responsibilities**:
- Calculate estimated time of arrival for driver to pickup
- Calculate trip duration estimate
- Consider real-time traffic
- Re-calculate ETA dynamically during trip

**Technology**: Go, Google Maps API

**ETA Calculation**:
```go
func (s *ETAService) CalculateETA(fromLat, fromLng, toLat, toLng float64) (time.Duration, error) {
    // Call Google Maps Directions API
    resp, err := s.mapsClient.Directions(context.Background(), &maps.DirectionsRequest{
        Origin:      fmt.Sprintf("%f,%f", fromLat, fromLng),
        Destination: fmt.Sprintf("%f,%f", toLat, toLng),
        Mode:        maps.TravelModeDriving,
        DepartureTime: "now", // Real-time traffic
    })
    
    if err != nil {
        return 0, err
    }
    
    if len(resp) == 0 || len(resp[0].Legs) == 0 {
        return 0, errors.New("no route found")
    }
    
    duration := resp[0].Legs[0].Duration
    
    // Cache result (5 minutes TTL)
    cacheKey := fmt.Sprintf("eta:%f:%f:%f:%f", fromLat, fromLng, toLat, toLng)
    s.redis.Set(ctx, cacheKey, duration.Seconds(), 5*time.Minute)
    
    return duration, nil
}
```

## Database Design

### Users Table
```sql
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone VARCHAR(20) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    name VARCHAR(100) NOT NULL,
    profile_image_url VARCHAR(500),
    rating DECIMAL(3, 2) DEFAULT 5.0,
    total_trips INTEGER DEFAULT 0,
    account_status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rating CHECK (rating >= 1.0 AND rating <= 5.0),
    CONSTRAINT chk_account_status CHECK (account_status IN 
        ('ACTIVE', 'SUSPENDED', 'BANNED'))
);

CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_users_email ON users(email);
```

### Drivers Table
```sql
CREATE TABLE drivers (
    driver_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id),
    license_number VARCHAR(50) UNIQUE NOT NULL,
    vehicle_type VARCHAR(20) NOT NULL,
    vehicle_make VARCHAR(50),
    vehicle_model VARCHAR(50),
    vehicle_year INTEGER,
    vehicle_plate VARCHAR(20),
    rating DECIMAL(3, 2) DEFAULT 5.0,
    total_trips INTEGER DEFAULT 0,
    acceptance_rate DECIMAL(3, 2) DEFAULT 1.0,
    status VARCHAR(20) DEFAULT 'OFFLINE',
    background_check_status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_vehicle_type CHECK (vehicle_type IN 
        ('ECONOMY', 'PREMIUM', 'XL', 'POOL')),
    CONSTRAINT chk_driver_status CHECK (status IN 
        ('OFFLINE', 'AVAILABLE', 'ON_TRIP', 'SUSPENDED'))
);

CREATE INDEX idx_drivers_status ON drivers(status);
CREATE INDEX idx_drivers_rating ON drivers(rating DESC);
```

### Trips Table
```sql
CREATE TABLE trips (
    trip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rider_id UUID NOT NULL REFERENCES users(user_id),
    driver_id UUID REFERENCES drivers(driver_id),
    ride_type VARCHAR(20) NOT NULL,
    pickup_lat DECIMAL(10, 8) NOT NULL,
    pickup_lng DECIMAL(11, 8) NOT NULL,
    pickup_address TEXT,
    destination_lat DECIMAL(10, 8),
    destination_lng DECIMAL(11, 8),
    destination_address TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'REQUESTED',
    otp VARCHAR(6),
    estimated_fare DECIMAL(10, 2),
    final_fare DECIMAL(10, 2),
    distance_km DECIMAL(8, 2),
    duration_minutes INTEGER,
    surge_multiplier DECIMAL(3, 2) DEFAULT 1.0,
    promo_code VARCHAR(50),
    discount_amount DECIMAL(10, 2) DEFAULT 0,
    requested_at TIMESTAMP NOT NULL DEFAULT NOW(),
    driver_assigned_at TIMESTAMP,
    driver_arrived_at TIMESTAMP,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    cancelled_at TIMESTAMP,
    cancellation_reason TEXT,
    cancelled_by VARCHAR(20),
    CONSTRAINT chk_trip_status CHECK (status IN 
        ('REQUESTED', 'DRIVER_ASSIGNED', 'DRIVER_ARRIVED', 
         'IN_PROGRESS', 'COMPLETED', 'CANCELLED', 'PAID'))
);

CREATE INDEX idx_trips_rider ON trips(rider_id, requested_at DESC);
CREATE INDEX idx_trips_driver ON trips(driver_id, requested_at DESC);
CREATE INDEX idx_trips_status ON trips(status);
CREATE INDEX idx_trips_requested_at ON trips(requested_at DESC);
```

### Ratings Table
```sql
CREATE TABLE ratings (
    rating_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(trip_id),
    rater_id UUID NOT NULL REFERENCES users(user_id),
    ratee_id UUID NOT NULL REFERENCES users(user_id),
    rating SMALLINT NOT NULL,
    feedback TEXT,
    tags VARCHAR(200), -- Comma-separated: "polite,clean,safe"
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_rating CHECK (rating >= 1 AND rating <= 5),
    CONSTRAINT uk_trip_rater UNIQUE(trip_id, rater_id)
);

CREATE INDEX idx_ratings_ratee ON ratings(ratee_id, created_at DESC);
```

### Payments Table
```sql
CREATE TABLE payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES trips(trip_id),
    user_id UUID NOT NULL REFERENCES users(user_id),
    amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    payment_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    transaction_id VARCHAR(100),
    failure_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    CONSTRAINT chk_payment_method CHECK (payment_method IN 
        ('CARD', 'WALLET', 'CASH', 'UPI')),
    CONSTRAINT chk_payment_status CHECK (payment_status IN 
        ('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED'))
);

CREATE INDEX idx_payments_trip ON payments(trip_id);
CREATE INDEX idx_payments_user ON payments(user_id, created_at DESC);
```

### Cassandra (Location History)
```cql
CREATE TABLE location_history (
    driver_id UUID,
    timestamp TIMESTAMP,
    latitude DOUBLE,
    longitude DOUBLE,
    speed DOUBLE,
    bearing DOUBLE,
    PRIMARY KEY (driver_id, timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC);
```

## API Design

### 1. Request Ride
```http
POST /api/v1/rides/request
Authorization: Bearer <jwt_token>

Request:
{
  "pickup_lat": 37.7749,
  "pickup_lng": -122.4194,
  "pickup_address": "123 Market St, San Francisco",
  "destination_lat": 37.8044,
  "destination_lng": -122.2712,
  "destination_address": "Oakland Airport",
  "ride_type": "ECONOMY"
}

Response: 201 Created
{
  "trip_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "REQUESTED",
  "estimated_fare": 25.50,
  "estimated_duration_minutes": 30,
  "surge_multiplier": 1.0,
  "requested_at": "2026-04-07T10:30:00Z"
}
```

### 2. Get Nearby Drivers
```http
GET /api/v1/drivers/nearby?lat=37.7749&lng=-122.4194&radius_km=5&ride_type=ECONOMY
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "drivers": [
    {
      "driver_id": "660e8400-e29b-41d4-a716-446655440000",
      "name": "John Driver",
      "rating": 4.8,
      "vehicle_type": "ECONOMY",
      "vehicle_model": "Toyota Camry",
      "distance_km": 0.5,
      "eta_minutes": 3
    }
  ],
  "total_count": 15
}
```

### 3. Track Trip (WebSocket)
```javascript
// WebSocket connection
ws = new WebSocket("wss://api.rideshare.com/trips/550e8400/track");

// Receive real-time location updates
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log(update);
  /*
  {
    "trip_id": "550e8400-e29b-41d4-a716-446655440000",
    "driver_lat": 37.7750,
    "driver_lng": -122.4195,
    "eta_minutes": 2,
    "distance_to_pickup_km": 0.3,
    "timestamp": "2026-04-07T10:32:00Z"
  }
  */
};
```

### 4. Complete Trip
```http
POST /api/v1/trips/{trip_id}/complete
Authorization: Bearer <jwt_token>

Response: 200 OK
{
  "trip_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "final_fare": 27.80,
  "distance_km": 18.5,
  "duration_minutes": 32,
  "payment_status": "COMPLETED",
  "receipt_url": "https://cdn.example.com/receipts/550e8400.pdf",
  "completed_at": "2026-04-07T11:02:00Z"
}
```

### 5. Rate Driver
```http
POST /api/v1/trips/{trip_id}/rate
Authorization: Bearer <jwt_token>

Request:
{
  "rating": 5,
  "feedback": "Great driver, very polite!",
  "tags": ["polite", "clean_car", "safe_driving"]
}

Response: 201 Created
{
  "rating_id": "770e8400-e29b-41d4-a716-446655440000",
  "rating": 5,
  "created_at": "2026-04-07T11:05:00Z"
}
```

## Caching Strategy

**1. Driver Locations (Redis Geospatial)**
```
Key: drivers:locations
Type: Geospatial index
TTL: 5 minutes (auto-expire if no updates)
Commands: GEOADD, GEORADIUS
```

**2. Active Trips**
```
Key: trip:active:{trip_id}
TTL: 6 hours
Value: Trip JSON
```

**3. Surge Pricing**
```
Key: surge:{geohash}:{minute}
TTL: 1 minute
Value: Multiplier (1.0 to 5.0)
```

## Scalability

### Geospatial Sharding
- Shard by city/region
- Each region has dedicated Redis cluster for driver locations
- Cross-region matching not allowed (performance)

### WebSocket Scaling
- 15M concurrent WebSocket connections
- Use WebSocket gateway cluster (50 nodes)
- Each node handles 300K connections
- Sticky sessions for connection persistence

### Database Sharding
- Trips sharded by city_id
- Users sharded by user_id hash
- Read replicas for analytics queries

## Fault Tolerance

- **Circuit breaker** for external APIs (Google Maps)
- **Graceful degradation**: If ETA service down, show static estimate
- **Multi-region**: Active-active deployment
- **Database failover**: Automatic promotion of replica
- **Retry logic**: Exponential backoff for payment failures

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Client** | React Native, Flutter |
| **API Gateway** | Kong |
| **Services** | Spring Boot, Go |
| **Real-time** | WebSocket, Socket.io |
| **Cache** | Redis Cluster with Geo |
| **RDBMS** | PostgreSQL |
| **NoSQL** | Cassandra |
| **Message Queue** | Kafka |
| **Maps** | Google Maps API |
| **Payment** | Stripe |
| **Monitoring** | Prometheus, Grafana |
| **Container** | Docker, Kubernetes |

## Interview Discussion Points

### Q1: How do you handle 10M location updates per second?

**Answer**: Use WebSocket for bidirectional real-time communication, Redis Geospatial for fast proximity queries, and Kafka for async processing:

```go
// Driver app sends location via WebSocket
func (s *LocationService) HandleLocationUpdate(ws *websocket.Conn) {
    for {
        var update LocationUpdate
        err := ws.ReadJSON(&update)
        if err != nil {
            break
        }
        
        // Update Redis (synchronous, < 1ms)
        redis.GeoAdd(ctx, "drivers:locations", &redis.GeoLocation{
            Name:      update.DriverID,
            Longitude: update.Longitude,
            Latitude:  update.Latitude,
        })
        
        // Publish to Kafka (asynchronous)
        go kafka.Publish("location.updates", update)
    }
}
```

**Scaling**:
- Redis Cluster with 50 nodes
- Each node handles 200K writes/sec
- Kafka with 100 partitions for parallel processing

---

### Q2: How do you implement surge pricing?

**Answer**: Calculate demand/supply ratio per region in real-time:

```java
public BigDecimal calculateSurgeMultiplier(String geoHash) {
    // Count ride requests in last 5 minutes
    long demand = redis.zcount("requests:" + geoHash, 
        Instant.now().minus(5, ChronoUnit.MINUTES).toEpochMilli(),
        Instant.now().toEpochMilli());
    
    // Count available drivers
    long supply = redis.georadius("drivers:locations", 
        lat, lng, 5, GeoUnit.KM).size();
    
    double ratio = (double) demand / Math.max(supply, 1);
    
    if (ratio < 1.0) return BigDecimal.ONE;
    else if (ratio < 2.0) return new BigDecimal("1.5");
    else if (ratio < 3.0) return new BigDecimal("2.0");
    else return new BigDecimal("3.0");
}
```

---

### Q3: How do you ensure driver-rider safety?

**Answer**:
1. **Background checks**: Verify driver license, criminal record
2. **Real-time monitoring**: Track trip route, detect anomalies
3. **SOS button**: Direct line to emergency services
4. **Trip sharing**: Share live location with friends
5. **Two-way ratings**: Low-rated drivers/riders flagged for review
6. **In-app calling**: Masked phone numbers for privacy

---

### Q4: How do you handle payment failures?

**Answer**: Retry logic with exponential backoff:

```java
@Retryable(maxAttempts = 3, backoff = @Backoff(delay = 1000, multiplier = 2))
public Payment processPayment(String tripId, BigDecimal amount) {
    try {
        return stripeClient.charge(amount);
    } catch (PaymentFailedException e) {
        // Log failure
        paymentFailureRepository.save(new PaymentFailure(tripId, e));
        throw e;
    }
}
```

**Fallback**: Allow trip completion, retry payment later, suspend account if payment fails repeatedly.

---

### Q5: How do you optimize matching algorithm?

**Answer**: Multi-factor scoring:

```java
double score = 0.0;
score += (1.0 / distance) * 100;        // Closer is better (weight: 100)
score += (driver.getRating() - 4.0) * 50; // Higher rating is better (weight: 50)
score += driver.getAcceptanceRate() * 30; // Higher acceptance rate (weight: 30)

// Sort drivers by score
drivers.sort(Comparator.comparing(Driver::getScore).reversed());
```

**A/B Testing**: Test different weight combinations to optimize rider satisfaction and driver utilization.

## Cost Estimation

| Component | Monthly Cost |
|-----------|--------------|
| **Compute (EKS)** | $100,000 |
| **Database** | $80,000 |
| **Redis** | $20,000 |
| **Kafka** | $15,000 |
| **Google Maps API** | $500,000 |
| **SMS/Push** | $50,000 |
| **Monitoring** | $10,000 |
| **Total** | **$775,000/month** |

**Revenue**: 25M rides/month @ $2 commission = $50M/month  
**Profit**: $49M/month

---

**Document Version**: 1.0  
**Last Updated**: 2026-04-07  
**Review Status**: Production-Ready
