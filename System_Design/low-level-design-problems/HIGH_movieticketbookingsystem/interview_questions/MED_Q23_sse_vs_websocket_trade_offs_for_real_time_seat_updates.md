# Q23: SSE vs WebSocket - Trade-offs for real-time seat updates

### Comparison:

```
SERVER-SENT EVENTS (SSE)
═══════════════════════════════════════════════════════════
Protocol: HTTP (one-way: server → client)
Connection: Long-lived HTTP GET request
Browser support: All modern browsers
Reconnection: Automatic
Message format: text/event-stream

Pros:
✅ Simple (just HTTP)
✅ Auto-reconnect built-in
✅ Works through proxies
✅ EventSource API (native)

Cons:
❌ One-way only (no client → server)
❌ 6 connection limit per domain (HTTP/1.1)
❌ No binary data support


WEBSOCKET
═══════════════════════════════════════════════════════════
Protocol: WebSocket (full-duplex: both directions)
Connection: Upgraded HTTP connection
Browser support: All modern browsers
Reconnection: Manual (need library)
Message format: Binary or text

Pros:
✅ Full-duplex (bidirectional)
✅ Binary data support
✅ Lower overhead
✅ No connection limit

Cons:
❌ More complex
❌ Manual reconnect logic
❌ Some proxies block
```

**For BookMyShow: Use WebSocket ✅**

**Reason:**
- Need bidirectional communication (user selects seat → server)
- No 6-connection limit (users open multiple tabs)
- Lower latency (no HTTP overhead)

**SSE Implementation (Alternative):**

```java
@RestController
public class SeatUpdateSSEController {
    
    @GetMapping(value = "/stream/show/{showId}", 
                produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<SeatUpdateEvent>> streamSeatUpdates(
            @PathVariable Long showId) {
        
        return Flux.create(sink -> {
            
            // Subscribe to Redis channel
            MessageListener listener = (message, pattern) -> {
                SeatUpdateEvent event = JsonUtils.fromJson(
                    new String(message.getBody()),
                    SeatUpdateEvent.class
                );
                
                // Send SSE event
                sink.next(ServerSentEvent.<SeatUpdateEvent>builder()
                    .id(String.valueOf(event.getTimestamp()))
                    .event("seat-update")
                    .data(event)
                    .build());
            };
            
            redisContainer.addMessageListener(
                listener,
                new ChannelTopic("seat:updates:" + showId)
            );
            
            // Cleanup on disconnect
            sink.onDispose(() -> 
                redisContainer.removeMessageListener(listener)
            );
        });
    }
}
```

**Client-Side SSE:**

```javascript
// Connect to SSE endpoint
const eventSource = new EventSource('/stream/show/123');

eventSource.addEventListener('seat-update', function(event) {
    const update = JSON.parse(event.data);
    console.log('Seat update:', update);
    
    // Update UI
    updateSeatStatus(update.seatIds, update.status);
});

// Auto-reconnect on disconnect
eventSource.onerror = function(error) {
    console.log('Connection lost, reconnecting...');
    // EventSource auto-reconnects
};
```

---
