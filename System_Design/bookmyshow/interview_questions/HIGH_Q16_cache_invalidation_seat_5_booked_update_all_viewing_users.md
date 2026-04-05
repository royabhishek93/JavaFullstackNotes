# Q16: Cache Invalidation - Seat 5 booked, update all viewing users

### ✅ Solution: Redis Pub/Sub + WebSocket

```java
@Service
public class CacheInvalidationService {
    
    @Transactional
    public Booking bookSeats(BookingRequest request) {
        
        // Book seats in database
        Booking booking = doBookSeats(request);
        
        // Step 1: Invalidate cache
        String cacheKey = "show:" + request.getShowId() + ":seats";
        redisTemplate.delete(cacheKey);
        
        // Step 2: Publish update event
        SeatUpdateEvent event = new SeatUpdateEvent(
            request.getShowId(),
            request.getSeatIds(),
            SeatStatus.BOOKED
        );
        
        redisPublisher.publish("show:updates", event);
        
        return booking;
    }
}

@Component
public class SeatUpdateListener implements MessageListener {
    
    @Override
    public void onMessage(Message message, byte[] pattern) {
        SeatUpdateEvent event = JsonUtils.fromJson(
            message.getBody(), 
            SeatUpdateEvent.class
        );
        
        // Broadcast to all WebSocket clients watching this show
        webSocketService.broadcast(
            "/topic/show/" + event.getShowId(),
            event
        );
    }
}
```

---
