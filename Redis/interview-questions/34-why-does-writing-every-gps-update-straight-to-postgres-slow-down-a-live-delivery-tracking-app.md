# Why does writing every GPS update straight to Postgres slow down a live delivery-tracking app?

**Type:** Scenario-Based
**Topic:** Redis Architecture — In-Memory Hot Path vs Permanent Storage
**Level:** Senior Interview (8–12+ YOE)

## Direct Answer
Because a moving delivery rider generates a write roughly every second, and multiplied across hundreds of concurrent riders, that becomes an enormous number of disk-backed read/write operations hitting a relational database that was designed for durability, not for this kind of high-frequency churn. Redis absorbs that same load easily because it keeps data in RAM, which is dramatically faster for this kind of short-lived, rapidly changing data.

## Easy Explanation
Imagine writing down a runner's exact position with pen and paper every single second, for hundreds of runners at once — your paper (disk) fills up fast and your hand (the database) cramps under the load. Now imagine using a whiteboard instead (Redis, in-memory) — you erase and rewrite instantly, because whiteboards are built for constant, temporary updates, not permanent record-keeping. The runner's *final* route, once they finish, is worth writing down properly on paper — but not every single second along the way.

## Diagram
```
100 riders x 1 GPS update/sec = 100 writes/sec, continuously, for the whole trip

Direct-to-Postgres design (expensive):
Rider App --> Backend --> Postgres (disk-backed)
                              |
                    100s of writes/sec, disk I/O, index updates,
                    replication lag, connection pool pressure

Redis-backed design (cheap):
Rider App --> Backend --> Redis (in-memory)   <- absorbs the high-frequency churn
                              |
                    trip ends
                              |
                              v
                        Backend computes final route
                              |
                              v
                        ONE write to Postgres (the durable, final path)
```

## Production Example
A food-delivery platform updates a rider's live coordinates in Redis (`SET rider:8842:location "lat,lng"` with a short TTL) while a trip is active. Only once the trip completes does the backend assemble the full path and persist it as a single row/document in the permanent database — dramatically reducing write volume against the durable store while still keeping live tracking fast for the customer-facing map.

## Why Interviewers Ask This
It tests whether a candidate can identify *which* data genuinely needs durability versus which data is disposable once it has served its short-lived purpose — a core skill in deciding what belongs in Redis versus a permanent database.
