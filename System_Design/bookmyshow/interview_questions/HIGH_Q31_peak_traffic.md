# Question 31: Avengers Premiere - Handle 1M Users at 10 AM (100x Traffic Spike)

## Difficulty Level: ⭐⭐⭐⭐ (Staff/Principal)

## Expected Answer Duration: 15-20 minutes

---

## The Scenario:

**Interviewer:** "Avengers: Endgame tickets go on sale tomorrow at 10 AM. You expect 1 million concurrent users, which is 100x your normal traffic. Normal load is 10k concurrent users with 1000 bookings/second. How do you handle this?"

---

## ❌ Poor Answer (Mid-Level):

> "I'll scale up the servers to handle more traffic and add more database replicas."

**Why this fails:**
- No specific numbers or calculations
- Doesn't address the thundering herd problem
- No queue system mentioned
- Ignores cache warming, rate limiting, load shedding

---

## ✅ Excellent Answer (Staff/Principal Level):

### **Part 1: Capacity Planning - The Math**

```
Current Capacity:
────────────────────────────────────────────────────────
- Normal: 10k concurrent users
- Booking rate: 1000 bookings/second
- Application servers: 20 instances (50 bookings/sec each)
- Database: 1 master + 5 read replicas
- Cache: 3 Redis nodes (cluster mode)
- Average response time: 200ms

Peak Load (10 AM):
────────────────────────────────────────────────────────
- Expected: 1M concurrent users (100x spike)
- Target booking rate: 50,000 bookings/second (50x spike)
- Duration: 30 minutes of sustained peak

Resource Calculation:
────────────────────────────────────────────────────────
Application Servers:
- Current: 20 servers × 50 bookings/sec = 1000 bookings/sec
- Needed: 50,000 bookings/sec ÷ 50 bookings/sec = 1000 servers
- Buffer: 1.5x safety margin = 1500 servers
- Auto-scaling ready: Pre-warm 500 servers, scale to 1500

Database:
- Writes (bookings): 50k/sec → Need 50 PostgreSQL shards
- Reads (search): 500k queries/sec → 100 read replicas
- Connection pooling: 100 connections per server

Cache (Redis):
- Current: 3 nodes (10k requests/sec each) = 30k req/sec
- Needed: 1M users × 5 cache hits/sec = 5M req/sec
- Redis cluster: 200 nodes (25k req/sec each)
- Pre-warm: Load all popular shows into cache

Load Balancer:
- Current: 1 ALB (50k connections)
- Needed: 1M concurrent connections
- Solution: 20 ALBs (50k each) + DNS round-robin
```

---

### **Part 2: The Strategy - Load Shedding with Queue**

```
┌─────────────────────────────────────────────────────────────────┐
│                   TRAFFIC MANAGEMENT STRATEGY                    │
└─────────────────────────────────────────────────────────────────┘

                        1M Concurrent Users
                              │
                              ▼
                    ┌─────────────────┐
                    │  CDN (CloudFlare)│
                    │  - Static assets │
                    │  - Rate limiting │
                    │    (100 req/min) │
                    └────────┬─────────┘
                             │
                  ┌──────────┼──────────┐
                  │          │          │
         ┌────────▼────┐ ┌──▼─────┐ ┌──▼────────┐
         │   TIER 1    │ │ TIER 2 │ │  TIER 3   │
         │  IMMEDIATE  │ │ QUEUED │ │ REJECTED  │
         │   ACCEPT    │ │  WAIT  │ │  RETRY    │
         └──────┬──────┘ └───┬────┘ └─────┬─────┘
                │            │            │
         50k users      450k users    500k users
         Process Now    Queue 30s     HTTP 429
                │            │            │
                ▼            ▼            ▼
         ┌──────────┐  ┌─────────┐  ┌─────────┐
         │ Process  │  │  SQS    │  │ Return  │
         │ Booking  │  │  Queue  │  │ "Please │
         │  (Sync)  │  │  FIFO   │  │  retry  │
         └──────────┘  └────┬────┘  │  in 1m" │
                            │        └─────────┘
                            │ Async consumer
                            ▼
                       ┌─────────┐
                       │ Process │
                       │ Booking │
                       │ (Async) │
                       └─────────┘

CAPACITY ALLOCATION:
─────────────────────────────────────────────────────────
Tier 1 (5%):   50k users  → Sub-second response
Tier 2 (45%): 450k users  → 30-second queue
Tier 3 (50%): 500k users  → Graceful rejection

Why this works:
✓ Protects system from overload
✓ Fair queuing (first-come-first-served)
✓ Better UX than crashing
✓ Clear expectations for users
```

---

### **Part 3: Architecture for Peak Load**

```java
@RestController
@RequestMapping("/api/v1/bookings")
public class BookingController {
    
    private final RateLimiter globalRateLimiter;
    private final QueueService queueService;
    private final MetricsService metrics;
    
    @PostMapping
    public ResponseEntity<?> bookSeats(
            @RequestBody BookingRequest request,
            @RequestHeader("X-User-Id") String userId) {
        
        // Step 1: Global rate limiting (per user)
        if (!rateLimiter.tryAcquire(userId, 5, Duration.ofMinutes(1))) {
            return ResponseEntity.status(429)
                .body(ErrorResponse.builder()
                    .error("RATE_LIMIT_EXCEEDED")
                    .message("Maximum 5 booking attempts per minute")
                    .retryAfter(Duration.ofSeconds(60))
                    .build());
        }
        
        // Step 2: Check system load
        SystemLoad currentLoad = metrics.getCurrentLoad();
        
        if (currentLoad.getQps() < TIER1_THRESHOLD) {
            // TIER 1: Process immediately
            return processBookingSync(request);
            
        } else if (currentLoad.getQps() < TIER2_THRESHOLD) {
            // TIER 2: Queue it
            String queueId = queueService.enqueue(request, userId);
            
            return ResponseEntity.status(202) // Accepted
                .body(QueueResponse.builder()
                    .queueId(queueId)
                    .status("QUEUED")
                    .estimatedWaitTime(Duration.ofSeconds(30))
                    .pollUrl("/api/v1/queue/" + queueId)
                    .websocketUrl("wss://api.bookmyshow.com/queue/" + queueId)
                    .message("You're in the queue. We'll process your booking shortly.")
                    .build());
            
        } else {
            // TIER 3: Reject with retry
            return ResponseEntity.status(503) // Service Unavailable
                .body(ErrorResponse.builder()
                    .error("SYSTEM_OVERLOAD")
                    .message("High traffic detected. Please try again in 1 minute.")
                    .retryAfter(Duration.ofMinutes(1))
                    .build());
        }
    }
    
    @GetMapping("/queue/{queueId}")
    public ResponseEntity<?> checkQueueStatus(@PathVariable String queueId) {
        
        QueueItem item = queueService.getStatus(queueId);
        
        return ResponseEntity.ok(QueueStatusResponse.builder()
            .queueId(queueId)
            .status(item.getStatus()) // QUEUED, PROCESSING, COMPLETED, FAILED
            .position(item.getPosition()) // "You are #1,234 in queue"
            .estimatedWaitTime(item.getEstimatedWait())
            .result(item.getResult()) // Booking details if COMPLETED
            .build());
    }
}
```

---

### **Part 4: Queue System Implementation**

```java
@Service
public class QueueService {
    
    private final AmazonSQS sqsClient;
    private final RedisTemplate<String, QueueItem> redisTemplate;
    
    public String enqueue(BookingRequest request, String userId) {
        
        String queueId = UUID.randomUUID().toString();
        
        // Store in Redis for status tracking
        QueueItem item = QueueItem.builder()
            .queueId(queueId)
            .userId(userId)
            .request(request)
            .status(QueueStatus.QUEUED)
            .enqueuedAt(Instant.now())
            .estimatedWait(calculateEstimatedWait())
            .build();
        
        redisTemplate.opsForValue().set(
            "queue:" + queueId, 
            item, 
            Duration.ofMinutes(30)
        );
        
        // Send to SQS FIFO queue
        sqsClient.sendMessage(SendMessageRequest.builder()
            .queueUrl(BOOKING_QUEUE_URL)
            .messageBody(JsonUtils.toJson(request))
            .messageGroupId(request.getShowId().toString()) // FIFO per show
            .messageDeduplicationId(queueId)
            .messageAttributes(Map.of(
                "queueId", stringValue(queueId),
                "userId", stringValue(userId),
                "priority", stringValue(calculatePriority(request))
            ))
            .build());
        
        // Publish to WebSocket for real-time updates
        webSocketPublisher.publish(
            "queue:" + queueId,
            new QueueUpdateEvent(queueId, QueueStatus.QUEUED)
        );
        
        return queueId;
    }
    
    private Duration calculateEstimatedWait() {
        // Based on current queue depth and processing rate
        long queueDepth = sqsClient.getQueueAttributes(
            GetQueueAttributesRequest.builder()
                .queueUrl(BOOKING_QUEUE_URL)
                .attributeNames(QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES)
                .build()
        ).attributes().get(QueueAttributeName.APPROXIMATE_NUMBER_OF_MESSAGES);
        
        int processingRate = 1000; // bookings per second
        
        long waitSeconds = queueDepth / processingRate;
        return Duration.ofSeconds(waitSeconds);
    }
}

@Service
public class QueueConsumer {
    
    @SqsListener(value = "${booking.queue.url}", deletionPolicy = ON_SUCCESS)
    public void processQueuedBooking(
            @Payload String message,
            @Header("queueId") String queueId) {
        
        try {
            // Update status
            updateQueueStatus(queueId, QueueStatus.PROCESSING);
            
            // Process booking
            BookingRequest request = JsonUtils.fromJson(message, BookingRequest.class);
            Booking booking = bookingService.bookSeats(request);
            
            // Update status
            updateQueueStatus(queueId, QueueStatus.COMPLETED, booking);
            
            // Notify user
            notificationService.sendBookingConfirmation(booking);
            
        } catch (SeatNotAvailableException e) {
            updateQueueStatus(queueId, QueueStatus.FAILED, e.getMessage());
            notificationService.sendBookingFailure(queueId, e.getMessage());
            
        } catch (Exception e) {
            log.error("Failed to process queued booking: {}", queueId, e);
            throw e; // Retry via SQS
        }
    }
}
```

---

### **Part 5: Cache Warming Strategy**

```java
@Component
public class CacheWarmingJob {
    
    /**
     * Run 1 hour before ticket sales (9 AM)
     */
    @Scheduled(cron = "0 0 9 * * *")
    public void warmCacheBeforeTicketSales() {
        
        log.info("Starting cache warming for Avengers premiere...");
        
        // 1. Warm movie details
        Movie avengers = movieRepository.findByTitle("Avengers: Endgame");
        cacheService.set("movie:" + avengers.getId(), avengers, Duration.ofHours(24));
        
        // 2. Warm all shows
        List<Show> shows = showRepository.findByMovieId(avengers.getId());
        
        for (Show show : shows) {
            // Cache show details
            cacheService.set("show:" + show.getId(), show, Duration.ofHours(6));
            
            // Cache seat availability (all seats AVAILABLE initially)
            Map<Long, String> seatMap = generateInitialSeatMap(show);
            cacheService.set("show:" + show.getId() + ":seats", seatMap, Duration.ofMinutes(30));
            
            // Cache available seat count
            cacheService.set("show:" + show.getId() + ":available", show.getTotalSeats(), Duration.ofMinutes(1));
        }
        
        // 3. Warm theater details
        List<Theater> theaters = shows.stream()
            .map(Show::getTheaterId)
            .distinct()
            .map(theaterRepository::findById)
            .flatMap(Optional::stream)
            .collect(Collectors.toList());
        
        for (Theater theater : theaters) {
            cacheService.set("theater:" + theater.getId(), theater, Duration.ofHours(24));
        }
        
        // 4. Pre-compute search results
        List<String> topCities = List.of("Mumbai", "Delhi", "Bangalore", "Hyderabad");
        
        for (String city : topCities) {
            SearchResult result = elasticsearchService.search(
                SearchQuery.builder()
                    .movieTitle("Avengers")
                    .city(city)
                    .date(LocalDate.now())
                    .build()
            );
            
            cacheService.set("search:" + city + ":Avengers", result, Duration.ofMinutes(30));
        }
        
        log.info("Cache warming completed. {} shows cached.", shows.size());
    }
    
    private Map<Long, String> generateInitialSeatMap(Show show) {
        return seatRepository.findByScreenId(show.getScreenId())
            .stream()
            .collect(Collectors.toMap(
                Seat::getId,
                seat -> "AVAILABLE"
            ));
    }
}
```

---

### **Part 6: Auto-Scaling Configuration**

```yaml
# AWS Auto Scaling Group Configuration

AutoScalingGroup:
  MinSize: 100              # Always running (off-peak)
  MaxSize: 1500             # Peak capacity
  DesiredCapacity: 100
  
  # Scaling Policies
  ScalingPolicies:
    
    # Scale UP aggressively
    - PolicyName: ScaleUpOnHighCPU
      MetricAggregationType: Average
      TargetValue: 60        # CPU > 60%
      ScaleOutCooldown: 60   # Add instances every 60s
      StepAdjustments:
        - MetricIntervalLowerBound: 0
          MetricIntervalUpperBound: 20
          ScalingAdjustment: 10    # Add 10 instances
        - MetricIntervalLowerBound: 20
          ScalingAdjustment: 50    # Add 50 instances if CPU > 80%
    
    # Scale DOWN conservatively
    - PolicyName: ScaleDownOnLowCPU
      MetricAggregationType: Average
      TargetValue: 30        # CPU < 30%
      ScaleInCooldown: 300   # Wait 5 mins before removing
      ScaleInProtectedFromScaleIn: true
    
  # Scheduled Scaling (pre-warm before 10 AM)
  ScheduledActions:
    - ScheduledActionName: PreWarmFor10AM
      Recurrence: "0 9 * * *"    # 9 AM daily
      MinSize: 500               # Pre-warm 500 servers
      DesiredCapacity: 500
      
    - ScheduledActionName: ScaleDownAfter11AM
      Recurrence: "0 11 * * *"   # 11 AM daily
      MinSize: 100
      DesiredCapacity: 100

  # Health Checks
  HealthCheckType: ELB
  HealthCheckGracePeriod: 300
  
  # Launch Template
  LaunchTemplate:
    InstanceType: c5.2xlarge   # 8 vCPU, 16GB RAM
    ImageId: ami-bookmyshow-app
    UserData: |
      #!/bin/bash
      aws s3 cp s3://bookmyshow-config/application.yml /app/config/
      java -Xms8g -Xmx12g -jar /app/booking-service.jar
```

---

### **Part 7: Database Sharding for Peak Load**

```
DATABASE SHARDING STRATEGY
═══════════════════════════════════════════════════════════

Shard by: city_id (geographic distribution)

┌─────────────────────────────────────────────────────────┐
│           Application Layer (Routing Logic)              │
│         Hash(city_id) % 50 → Shard Number               │
└──────────┬──────────────┬──────────────┬────────────────┘
           │              │              │
    ┌──────▼──────┐ ┌────▼─────┐ ┌─────▼──────┐
    │  Shard 1    │ │ Shard 2  │ │  Shard 50  │
    │  Mumbai     │ │  Delhi   │ │  Chennai   │
    │  Pune       │ │ Gurgaon  │ │  Kolkata   │
    └─────────────┘ └──────────┘ └────────────┘
         │               │             │
    Cities 1-10     Cities 11-20  Cities 41-50

Each Shard:
├─ Master: 1 PostgreSQL instance (writes)
├─ Replicas: 3 read replicas (reads)
├─ Capacity: 1000 bookings/sec per shard
├─ Total: 50 shards × 1000 = 50,000 bookings/sec ✅

Routing Logic:
──────────────────────────────────────────────────────────
public class ShardRouter {
    
    private static final int SHARD_COUNT = 50;
    
    public DataSource getShardForCity(Long cityId) {
        int shardId = (int) (cityId % SHARD_COUNT);
        return dataSources.get(shardId);
    }
    
    @Transactional
    public Booking bookSeats(BookingRequest request) {
        Long cityId = getCityIdForShow(request.getShowId());
        DataSource shard = getShardForCity(cityId);
        
        // Execute on specific shard
        return jdbcTemplate.execute(shard, connection -> {
            // Booking logic here
        });
    }
}
```

---

### **Part 8: Monitoring & Alerts**

```yaml
# CloudWatch Alarms

Alarms:
  
  # Critical: Booking latency
  - AlarmName: HighBookingLatency
    MetricName: BookingLatencyP99
    Threshold: 1000ms         # Alert if p99 > 1s
    EvaluationPeriods: 2
    Actions:
      - sns:alert-oncall
      - lambda:auto-scale-up
  
  # Critical: Error rate
  - AlarmName: HighBookingErrorRate
    MetricName: BookingErrorRate
    Threshold: 5%             # Alert if >5% errors
    EvaluationPeriods: 3
    Actions:
      - sns:alert-oncall
      - lambda:enable-circuit-breaker
  
  # Warning: Queue depth
  - AlarmName: HighQueueDepth
    MetricName: SQSQueueDepth
    Threshold: 100000         # 100k messages
    EvaluationPeriods: 2
    Actions:
      - sns:alert-team
      - lambda:scale-consumers
  
  # Info: Cache hit rate
  - AlarmName: LowCacheHitRate
    MetricName: RedisCacheHitRate
    Threshold: 80%            # Alert if <80%
    EvaluationPeriods: 5
    Actions:
      - sns:alert-team

# Grafana Dashboard Metrics
Dashboards:
  - Name: Peak Load Dashboard
    Panels:
      - Booking Rate (per second)
      - Queue Depth (current)
      - Cache Hit Rate (%)
      - P50/P95/P99 Latency
      - Error Rate (%)
      - Active Users (concurrent)
      - Database Connections (pool usage)
      - Redis Memory Usage
```

---

### **Part 9: Load Testing Before Launch**

```java
/**
 * JMeter/Gatling script to simulate 1M users
 */
public class PeakLoadTest {
    
    public void simulateAvengersPremiere() {
        
        // Phase 1: Ramp up (9:55 AM - 10:00 AM)
        scenario("RampUp")
            .exec(http("Search Movies")
                .get("/api/v1/movies/search?city=Mumbai&title=Avengers"))
            .pause(2)
            .exec(http("View Seats")
                .get("/api/v1/shows/123/seats"))
            .during(Duration.ofMinutes(5))
            .users(rampFrom(0).to(100_000).over(Duration.ofMinutes(5)));
        
        // Phase 2: Peak (10:00 AM - 10:30 AM)
        scenario("Peak")
            .exec(http("Book Seats")
                .post("/api/v1/bookings")
                .body(StringBody("""
                    {
                      "showId": 123,
                      "seatIds": [1, 2, 3],
                      "userId": "#{userId}"
                    }
                    """)))
            .pause(1)
            .exec(http("Confirm Payment")
                .post("/api/v1/bookings/#{bookingId}/confirm"))
            .during(Duration.ofMinutes(30))
            .users(constant(1_000_000));
        
        // Phase 3: Cool down (10:30 AM - 11:00 AM)
        scenario("CoolDown")
            .exec(/* same as phase 2 */)
            .during(Duration.ofMinutes(30))
            .users(rampFrom(1_000_000).to(100_000).over(Duration.ofMinutes(30)));
        
        // Assertions
        assertions()
            .global().responseTime().p99().lt(2000)  // p99 < 2s
            .global().successfulRequests().percent().gt(95);  // >95% success
    }
}
```

---

### **Part 10: Disaster Recovery Plan**

```
DISASTER SCENARIOS & RESPONSES
═══════════════════════════════════════════════════════════

Scenario 1: Database Master Goes Down
──────────────────────────────────────────────────────────
Impact: Cannot process bookings
Response:
  1. Automatic failover to read replica (promoted to master)
  2. Time: 30 seconds (RDS Multi-AZ)
  3. Data loss: 0 (synchronous replication)
  4. Action: Monitor replication lag

Scenario 2: Redis Cluster Failure
──────────────────────────────────────────────────────────
Impact: Cache misses, higher database load
Response:
  1. Degrade gracefully: Serve from database
  2. Circuit breaker: Limit database queries
  3. Queue non-critical requests
  4. Restore from snapshot: 5 minutes

Scenario 3: Payment Gateway Down
──────────────────────────────────────────────────────────
Impact: Cannot confirm bookings
Response:
  1. Circuit breaker: Stop calling gateway after 5 failures
  2. Queue payment confirmations
  3. Fallback: Secondary gateway (Razorpay)
  4. Notify users: "Payment processing delayed"

Scenario 4: Entire AWS Region Failure
──────────────────────────────────────────────────────────
Impact: Total outage
Response:
  1. DNS failover to backup region: 2 minutes
  2. Data sync: Asynchronous (RPO: 5 minutes)
  3. Cold start: 10 minutes to warm up cache
  4. Communicate: Status page + social media
```

---

## 💡 Key Takeaways for Interview:

**Perfect Summary:**

> "For Avengers premiere with 1M users (100x spike), I'd implement a 3-tier load shedding strategy:
> 
> **Tier 1 (5%)**: 50k users processed immediately via pre-warmed 500 servers
> 
> **Tier 2 (45%)**: 450k users queued in SQS FIFO, processed within 30 seconds
> 
> **Tier 3 (50%)**: 500k users gracefully rejected with HTTP 429, retry after 1 minute
> 
> **Key preparations:**
> 1. Cache warming at 9 AM (all shows, seats, theaters)
> 2. Auto-scaling: 100 → 1500 servers with scheduled pre-warming
> 3. Database sharding: 50 shards by city (50k bookings/sec capacity)
> 4. CDN for static assets (posters, images)
> 5. Rate limiting: 5 bookings/min per user
> 6. Load testing: Simulate 1M users 1 week before
> 
> **Monitoring:**
> - Alert if p99 latency >1s or error rate >5%
> - Real-time dashboard: booking rate, queue depth, cache hit rate
> 
> This approach protects the system while maximizing bookings (95%+ success rate vs crash)."

---

## 📊 Cost Analysis:

```
NORMAL LOAD (10k users):
────────────────────────────────────────────────────────
- Servers: 100 × c5.2xlarge × $0.34/hr × 730hr = $24,820/mo
- Database: 10 instances × db.r5.xlarge × $350/mo = $3,500/mo
- Cache: 5 Redis nodes × $100/mo = $500/mo
- Load Balancer: $25/mo
TOTAL: $28,845/month

PEAK LOAD (1M users, 30 minutes):
────────────────────────────────────────────────────────
- Servers: 1500 × c5.2xlarge × $0.34/hr × 0.5hr = $255
- Database: Same (sharded, always running)
- Cache: 200 nodes × $100/mo ÷ 730hr × 0.5hr = $13.70
TOTAL: $268.70 for 30-minute peak

Annual savings vs always running 1500 servers:
$268.70 × 12 peaks = $3,224
vs
$510,000/year (1500 servers 24/7)

Savings: $506,776/year (99.4% cost reduction)
```

This is Staff/Principal level expertise! 🎯

