# Q25: Real-time Seat Status Synchronization - Handle 10k users viewing same show

### Problem:

```
10k users viewing "Avengers" show
Each user needs real-time seat updates
Challenge: Minimize bandwidth and latency
```

### ✅ Solution: Differential Updates + Batching

```java
@Service
public class SeatSyncService {
    
    private final SimpMessagingTemplate messagingTemplate;
    private final ScheduledExecutorService scheduler = 
        Executors.newScheduledThreadPool(10);
    
    // Buffer updates for batching
    private final Map<Long, ConcurrentLinkedQueue<SeatUpdate>> 
        updateBuffer = new ConcurrentHashMap<>();
    
    @PostConstruct
    public void startBatchProcessor() {
        // Flush updates every 100ms
        scheduler.scheduleAtFixedRate(
            this::flushBatchedUpdates,
            100,
            100,
            TimeUnit.MILLISECONDS
        );
    }
    
    // Called when seat is booked/released
    public void enqueueSeatUpdate(Long showId, SeatUpdate update) {
        updateBuffer
            .computeIfAbsent(showId, k -> new ConcurrentLinkedQueue<>())
            .add(update);
    }
    
    private void flushBatchedUpdates() {
        updateBuffer.forEach((showId, updates) -> {
            if (updates.isEmpty()) return;
            
            // Collect all updates
            List<SeatUpdate> batch = new ArrayList<>();
            SeatUpdate update;
            while ((update = updates.poll()) != null) {
                batch.add(update);
            }
            
            // Deduplicate (keep latest per seat)
            Map<Long, SeatUpdate> deduplicated = batch.stream()
                .collect(Collectors.toMap(
                    SeatUpdate::getSeatId,
                    Function.identity(),
                    (existing, replacement) -> replacement  // Keep latest
                ));
            
            // Send batched update
            BatchedSeatUpdate batchedUpdate = new BatchedSeatUpdate(
                showId,
                new ArrayList<>(deduplicated.values()),
                System.currentTimeMillis()
            );
            
            messagingTemplate.convertAndSend(
                "/topic/show/" + showId,
                batchedUpdate
            );
            
            log.debug("Flushed {} seat updates for show {}", 
                     deduplicated.size(), showId);
        });
    }
}

@Data
class BatchedSeatUpdate {
    private Long showId;
    private List<SeatUpdate> updates;  // Multiple seats in one message
    private Long timestamp;
}

@Data
class SeatUpdate {
    private Long seatId;
    private SeatStatus status;  // AVAILABLE, RESERVED, BOOKED
    private String userId;      // Who booked it (for analytics)
}
```

**Batching Benefits:**

```
WITHOUT BATCHING
═══════════════════════════════════════════════════════════
100 seats booked in 100ms window
↓
100 separate WebSocket messages
↓
10k clients × 100 messages = 1M messages sent
↓
Network: ~50 MB (assuming 500 bytes per message)


WITH BATCHING (100ms window)
═══════════════════════════════════════════════════════════
100 seats booked in 100ms window
↓
1 batched WebSocket message (100 updates)
↓
10k clients × 1 message = 10k messages sent
↓
Network: ~5 MB (100x reduction) ✅
↓
Latency: Still <200ms (acceptable for real-time)
```

**Deduplication Example:**

```
TIME: 0-100ms window
═══════════════════════════════════════════════════════════
0ms:   Seat 5 → RESERVED (User A)
20ms:  Seat 5 → AVAILABLE (User A timeout)
50ms:  Seat 5 → RESERVED (User B)
80ms:  Seat 5 → BOOKED (User B paid)

Without deduplication: 4 messages
With deduplication: 1 message (latest state: BOOKED)

Result: 75% reduction in messages ✅
```

**Client-Side Handling:**

```javascript
stompClient.subscribe('/topic/show/123', function(message) {
    const batchedUpdate = JSON.parse(message.body);
    
    // Process all updates in batch
    batchedUpdate.updates.forEach(update => {
        const seatElement = document.getElementById('seat-' + update.seatId);
        
        // Update UI based on status
        seatElement.className = 'seat ' + update.status.toLowerCase();
        
        if (update.status === 'BOOKED' || update.status === 'RESERVED') {
            seatElement.disabled = true;
        } else {
            seatElement.disabled = false;
        }
    });
    
    console.log(`Applied ${batchedUpdate.updates.length} seat updates`);
});
```

---

## Advanced: Connection Management

### Handling WebSocket Disconnects

```java
@Component
public class WebSocketEventListener {
    
    private final ConcurrentHashMap<String, SessionInfo> 
        activeSessions = new ConcurrentHashMap<>();
    
    @EventListener
    public void handleConnect(SessionConnectedEvent event) {
        String sessionId = event.getMessage()
            .getHeaders()
            .get("simpSessionId")
            .toString();
        
        SessionInfo info = new SessionInfo(
            sessionId,
            LocalDateTime.now(),
            null  // showId set when user subscribes
        );
        
        activeSessions.put(sessionId, info);
        
        log.info("WebSocket connected: {}", sessionId);
    }
    
    @EventListener
    public void handleDisconnect(SessionDisconnectEvent event) {
        String sessionId = event.getSessionId();
        
        SessionInfo info = activeSessions.remove(sessionId);
        
        if (info != null && info.getShowId() != null) {
            // User was viewing a show, log metrics
            Duration viewDuration = Duration.between(
                info.getConnectedAt(),
                LocalDateTime.now()
            );
            
            metricsService.recordViewDuration(
                info.getShowId(),
                viewDuration.toSeconds()
            );
        }
        
        log.info("WebSocket disconnected: {} (duration: {})", 
                 sessionId, viewDuration);
    }
    
    @EventListener
    public void handleSubscribe(SessionSubscribeEvent event) {
        String sessionId = event.getMessage()
            .getHeaders()
            .get("simpSessionId")
            .toString();
        
        String destination = event.getMessage()
            .getHeaders()
            .get("simpDestination")
            .toString();
        
        // Extract showId from destination: /topic/show/123
        if (destination.startsWith("/topic/show/")) {
            Long showId = Long.parseLong(
                destination.substring("/topic/show/".length())
            );
            
            SessionInfo info = activeSessions.get(sessionId);
            if (info != null) {
                info.setShowId(showId);
            }
            
            log.info("Session {} subscribed to show {}", sessionId, showId);
        }
    }
}

@Data
class SessionInfo {
    private final String sessionId;
    private final LocalDateTime connectedAt;
    private Long showId;  // Set when user subscribes to show
}
```

---

## Monitoring Real-time System

```java
@Component
public class WebSocketMetrics {
    
    private final MeterRegistry meterRegistry;
    
    @Scheduled(fixedRate = 10000)  // Every 10 seconds
    public void recordMetrics() {
        
        // Active connections
        meterRegistry.gauge("websocket.connections.active",
            activeSessions.size());
        
        // Messages sent per second
        meterRegistry.counter("websocket.messages.sent");
        
        // Average message size
        meterRegistry.summary("websocket.message.size.bytes");
        
        // Connection duration
        meterRegistry.timer("websocket.connection.duration");
    }
    
    // Alert if too many connections
    @Scheduled(fixedRate = 60000)  // Every minute
    public void checkConnectionLimit() {
        int activeConnections = activeSessions.size();
        int maxCapacity = 25000;  // Per server
        
        double utilization = (double) activeConnections / maxCapacity;
        
        if (utilization > 0.8) {
            alertService.send(
                "WebSocket High Utilization",
                String.format("Connections: %d / %d (%.1f%%)",
                    activeConnections, maxCapacity, utilization * 100)
            );
        }
    }
}
```

---

## Key Takeaways:

```
Q21: WebSocket Architecture
✅ Redis Pub/Sub for distributed broadcast
✅ Horizontal scaling with multiple WS servers
✅ Each server handles 25k connections
✅ 100k total capacity

Q22: Redis Pub/Sub vs Message Queue
✅ Pub/Sub for real-time (fire-and-forget)
✅ Message Queue for critical workflows
✅ Understand trade-offs

Q23: SSE vs WebSocket
✅ SSE: Simple, one-way, auto-reconnect
✅ WebSocket: Full-duplex, lower overhead
✅ BookMyShow: WebSocket wins

Q24: Optimistic UI Updates
✅ Instant feedback (perceived performance)
✅ Rollback on error (reality check)
✅ Refresh from server (state sync)

Q25: Real-time Synchronization
✅ Batching: 100x reduction in messages
✅ Deduplication: Keep latest state
✅ 100ms window (balance latency vs efficiency)
```

This demonstrates production-level real-time system expertise! 🎯
