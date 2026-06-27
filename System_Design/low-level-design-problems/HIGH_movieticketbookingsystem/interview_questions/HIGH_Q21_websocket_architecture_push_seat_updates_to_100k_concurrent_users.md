# Q21: WebSocket Architecture - Push seat updates to 100k concurrent users

### Difficulty: ⭐⭐⭐⭐ (Staff)

### ✅ Solution: WebSocket + Redis Pub/Sub + Horizontal Scaling

```java
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {
    
    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // Enable simple broker for pub/sub
        config.enableSimpleBroker("/topic", "/queue")
            .setHeartbeatValue(new long[]{25000, 25000})  // 25s keepalive
            .setTaskScheduler(heartbeatScheduler());
        
        config.setApplicationDestinationPrefixes("/app");
    }
    
    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
            .setAllowedOrigins("*")
            .withSockJS()
            .setStreamBytesLimit(512 * 1024)  // 512KB buffer
            .setHttpMessageCacheSize(1000)
            .setDisconnectDelay(30 * 1000);   // 30s disconnect delay
    }
}
```

**Scaling WebSocket Servers:**

```java
@Service
public class DistributedWebSocketService {
    
    private final RedisMessageListenerContainer listenerContainer;
    private final SimpMessagingTemplate messagingTemplate;
    
    // Subscribe to Redis channel for distributed broadcast
    @PostConstruct
    public void subscribeToSeatUpdates() {
        listenerContainer.addMessageListener(
            this::onSeatUpdateMessage,
            new PatternTopic("seat:updates:*")
        );
    }
    
    // When seat is booked, publish to Redis
    public void broadcastSeatUpdate(Long showId, SeatUpdateEvent event) {
        // Publish to Redis (all WebSocket servers receive)
        redisTemplate.convertAndSend(
            "seat:updates:" + showId,
            JsonUtils.toJson(event)
        );
    }
    
    // Each WebSocket server pushes to its own connected clients
    private void onSeatUpdateMessage(Message message, byte[] pattern) {
        SeatUpdateEvent event = JsonUtils.fromJson(
            new String(message.getBody()),
            SeatUpdateEvent.class
        );
        
        // Broadcast to all clients subscribed to this show
        messagingTemplate.convertAndSend(
            "/topic/show/" + event.getShowId(),
            event
        );
    }
}
```

**Architecture:**

```
USER BOOKS SEAT
═══════════════════════════════════════════════════════════
1. POST /bookings
   ↓
2. API Server: Reserve seat in DB
   ↓
3. Publish to Redis: seat:updates:123
   ↓
4. ALL WebSocket servers receive message
   ↓
5. Each WS server broadcasts to its clients
   ↓
6. 100k clients receive update within 100-200ms


SCALING PATTERN
═══════════════════════════════════════════════════════════
┌────────────┐
│ Redis      │ ← Pub/Sub hub
│ (Pub/Sub)  │
└─────┬──────┘
      │ Broadcast to all
      ├────────────┬────────────┬────────────┐
      ↓            ↓            ↓            ↓
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│ WS      │  │ WS      │  │ WS      │  │ WS      │
│ Server 1│  │ Server 2│  │ Server 3│  │ Server 4│
└────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘
     │            │            │            │
  25k clients  25k clients  25k clients  25k clients
  
Total: 100k concurrent connections
Each server: 25k connections (c5.2xlarge capacity)
```

**Client-Side Code:**

```javascript
// Subscribe to show updates
const socket = new SockJS('/ws');
const stompClient = Stomp.over(socket);

stompClient.connect({}, function(frame) {
    // Subscribe to specific show
    stompClient.subscribe('/topic/show/123', function(message) {
        const update = JSON.parse(message.body);
        
        if (update.eventType === 'SEAT_BOOKED') {
            // Update UI: mark seats as unavailable
            update.seatIds.forEach(seatId => {
                document.getElementById('seat-' + seatId)
                    .classList.add('unavailable');
            });
        } else if (update.eventType === 'SEAT_RELEASED') {
            // Update UI: mark seats as available
            update.seatIds.forEach(seatId => {
                document.getElementById('seat-' + seatId)
                    .classList.remove('unavailable');
            });
        }
    });
});
```

---
