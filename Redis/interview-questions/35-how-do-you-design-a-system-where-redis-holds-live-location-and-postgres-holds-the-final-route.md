# How do you design a system where Redis holds live location and Postgres holds the final route?

**Type:** Advanced Scenario-Based
**Topic:** Redis Architecture — In-Memory Hot Path vs Permanent Storage
**Level:** Staff Interview (12–15+ YOE)

## Direct Answer
Split responsibilities by lifecycle: Redis owns the *volatile, frequently-changing* state (current coordinates, short TTL, overwritten every update), while Postgres owns the *durable, rarely-changing* state (the completed trip's full path, written once when the trip ends). The backend is the only component that talks to both — Redis for "where are they right now," Postgres for "what happened on this trip, permanently."

## Easy Explanation
Think of a whiteboard (Redis) next to a filing cabinet (Postgres). While a trip is happening, you keep erasing and rewriting the rider's current position on the whiteboard — fast, cheap, temporary. The moment the trip ends, you take one clean summary — the whole route — and file it permanently in the cabinet. You never file every single whiteboard update; you only file the final result.

## Diagram
```
                     +-----------------------------+
Rider device ------> |     Backend Service          |
  (GPS ping/sec)     |                               |
                     |  while trip active:           |
                     |   SET rider:8842:loc "lat,lng"|-----> Redis (TTL ~ 30s,
                     |     EX 30                     |        overwritten every ping)
                     |                                |
                     |  when trip ends:               |
                     |   assemble full path            |
                     |   INSERT INTO trips(             |
                     |     rider_id, path, ended_at)     |----> Postgres (durable,
                     +-----------------------------------+       written ONCE)

Customer app "where is my rider now?" -> reads from Redis (fast, current)
Support team "what route did trip #900 take?" -> reads from Postgres (durable, historical)
```

## Production Example
```java
// While trip is active — cheap, frequent, disposable writes
redisTemplate.opsForValue().set("rider:8842:location", "12.9716,77.5946", Duration.ofSeconds(30));

// When trip completes — one durable write, not thousands
List<Coordinate> fullPath = tripTracker.assembleFinalPath("trip:900");
tripRepository.save(new Trip(riderId, fullPath, Instant.now()));
```

The key architectural decision is that the backend service is the single source of truth for *which store to write to and when* — clients never write directly to Postgres for live tracking, and Redis is never treated as a permanent record.

## Why Interviewers Ask This
It checks whether a candidate can design a two-tier storage strategy end-to-end — not just "use Redis for speed," but specifically *when* data moves from the disposable tier to the durable tier, and who is responsible for making that transition happen.
