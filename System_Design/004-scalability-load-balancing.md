# SD_Q01: Scalability & Load Balancing — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 25-30 minutes | **Frequency:** 95% in architect rounds 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "Your e-commerce site gets 10x traffic on Black Friday. How do you handle it? Walk me through every component." — The most common architect opener.

---

## NEW LEARNER FOUNDATION

### What is Scalability? (Plain English)
```
Scalability = your system's ability to handle MORE load
              without redesigning everything.

Vertical Scaling (Scale Up):
  Buy a bigger server (more CPU, more RAM).
  Simple — just pay more.
  LIMIT: biggest server in the world still has a ceiling.
         single point of failure (one machine crashes → down)

Horizontal Scaling (Scale Out):
  Add MORE servers of the same size.
  Used by Google, Netflix, Amazon.
  COMPLEX: you need to distribute work across machines.
  NO ceiling: add servers until you can handle anything.
```

### What is a Load Balancer? (Plain English)
```
You have 10 identical servers.
1 million requests come in.
Load balancer = the traffic cop that routes each request to one server.

Without LB: all traffic hits server 1 → crashes. Servers 2-10 idle.
With LB:    each server gets ~100k requests → all stay healthy.

L4 Load Balancer (Network layer):
  Routes by IP + port. Fast. No idea what's in the request.
  Example: AWS Network Load Balancer, HAProxy TCP mode

L7 Load Balancer (Application layer):
  Reads the actual HTTP request. Routes by URL, headers, cookies.
  Example: AWS Application Load Balancer, Nginx
  Can do: route /api → backend, /static → CDN, /checkout → payment service
```

---

## BIG PICTURE — Scalability Architecture

```
 USER TRAFFIC — BLACK FRIDAY 10M REQUESTS/MIN
 ┌────────────────────────────────────────────────────────────────────┐
 │                                                                    │
 │  Users (Mobile/Web/API)                                           │
 │       │                                                           │
 │       ▼                                                           │
 │  [Route53 DNS]  ← geographic routing: India→Mumbai, US→Virginia   │
 │       │                                                           │
 │       ▼                                                           │
 │  [CloudFront CDN]  ← serves static assets (JS/CSS/images)        │
 │       │ cache MISS only                                           │
 │       ▼                                                           │
 │  [ALB: L7 Load Balancer]  ← routes by path, terminates SSL       │
 │   /api/orders  → Order Service pods                               │
 │   /api/payment → Payment Service pods                             │
 │   /api/search  → Search Service pods                              │
 │       │                                                           │
 │       ▼                                                           │
 │  ┌─────────────────────────────────────────────┐                 │
 │  │  EKS — Auto-Scaling Pod Fleet               │                 │
 │  │  [Order-1][Order-2][Order-3]...[Order-50]   │                 │
 │  │  HPA: CPU > 70% → add pod                   │                 │
 │  │  Each pod: STATELESS (no session state)      │                 │
 │  └────────────────────┬────────────────────────┘                 │
 │                       │                                           │
 │       ┌───────────────┴───────────────┐                          │
 │       ▼                               ▼                          │
 │  [ElastiCache Redis]          [RDS Aurora + Read Replicas]        │
 │  (session, hot data)          (writes → primary)                  │
 │                               (reads  → replica × 5)             │
 │                                                                   │
 └────────────────────────────────────────────────────────────────────┘

 STATELESS PODS — the key to horizontal scaling:
 ┌───────────────────────────────────────────────────────┐
 │  Each pod treats every request as brand new           │
 │  No local state → ANY pod can handle ANY request      │
 │  Session data stored in Redis (not in pod memory)     │
 │  If pod crashes: load balancer routes to others       │
 └───────────────────────────────────────────────────────┘
```

---

## Scenario 1: Flash Sale — 10x Traffic Spike

### The Question
> "Flipkart's Big Billion Days sale starts tomorrow. You expect 10x normal traffic for 2 hours. What do you do?"

### Architecture Answer
```
PRE-SALE PREPARATION (do the day before):
  1. Pre-scale: manually increase pod count before traffic hits
     → Don't wait for HPA to react — pre-warm 10x capacity
     → HPA reacts in 2-3 minutes; flash sale traffic spikes in seconds

  2. Pre-warm caches: load hot product/inventory data into Redis
     → Cache miss during sale = DB hit = DB overwhelmed
     → Run a cache warming script at 11:45pm (sale starts midnight)

  3. Reduce DB load with read replicas:
     → Product catalog, inventory counts → route to read replicas
     → Only writes (inventory decrement, order creation) → primary

  4. Enable CDN aggressive caching:
     → Product pages, images, CSS → CloudFront with long TTL
     → Cache-Control: max-age=300 (5 min) for product price (can change)
     → Cache-Control: max-age=86400 for images (rarely change)

  5. Enable Circuit Breakers:
     → Payment gateway, inventory service: fail fast, return fallback
     → Don't let slow dependency cascade to full outage

DURING SALE:
  6. Queue-based order processing:
     → Client submits order → 200 Accepted immediately
     → Order goes to SQS → processed by consumers at controlled rate
     → Don't overwhelm inventory DB with burst writes
     → Client polls /orders/{id}/status for result

  7. Rate limiting per user:
     → Token bucket: 5 requests/second per userId in Redis
     → Prevents bots/resellers from hammering the API
```

---

## Scenario 2: Consistent Hashing — Cache Scaling Trap

### The Problem
```
You have 4 Redis nodes. You shard by: node = hash(key) % 4

Redis node 0: keys where hash % 4 == 0
Redis node 1: keys where hash % 4 == 1
Redis node 2: keys where hash % 4 == 2
Redis node 3: keys where hash % 4 == 3

TRAFFIC GROWS: you add a 5th Redis node.
Now: node = hash(key) % 5

ALL KEYS REMAP! Every single cache key now points to a different node.
Cache hit rate: 100% → 0% (entire cache is suddenly wrong)
→ All 10M requests/min slam your DB simultaneously
→ DB crashes — this is called a "cache avalanche"
```

### Fix: Consistent Hashing
```
Consistent hashing: keys map to a RING, not modulo.
Adding/removing a node only remaps ~1/N of keys (not all of them).

Ring: 0 ─────────────────────────────────────── 360°
  Node A at position 90°
  Node B at position 180°
  Node C at position 270°

  Key maps to position X on ring → routes to the NEXT node clockwise
  Add Node D at 45°: only keys in [0°-90°] remap from A to D
  All other keys unchanged → cache still valid!

PRODUCTION: Use Redis Cluster (built-in consistent hashing via hash slots)
            Or: AWS ElastiCache Cluster Mode
            Or: Ketama consistent hashing for Memcached
```

---

## Trap 1: Sticky Sessions Breaks Auto-Scaling

### The Bug
```
Old architecture: sticky sessions (session affinity)
  Load balancer routes user123 ALWAYS to Server 3
  Session data stored in Server 3's memory

Problem during auto-scaling:
  Traffic spikes → LB adds Server 10
  But Server 3 already has all the sticky users
  Server 3: 80% CPU
  Servers 1-10: 10% CPU each

  Even worse: Server 3 crashes (OOM)
  → All users pinned to Server 3 lose their sessions!
  → 500 errors, logged-out users during peak sale

  Auto-scaling CANNOT help — all load is pinned to one server
```

```
FIX: Make services STATELESS
  Store sessions in Redis (not server memory)
  Any server can handle any request
  Load balancer can route freely
  Auto-scaling works correctly

// Spring Boot config for Redis sessions
spring:
  session:
    store-type: redis
    timeout: 30m
  data:
    redis:
      host: elasticache-endpoint
      port: 6379
// Now: pod crashes → user's next request goes to another pod
//      that reads session from Redis → seamless
```

---

## Trap 2: L7 LB SSL Termination Leaking Headers

### The Bug
```
L7 load balancer terminates SSL (decrypts HTTPS).
Client sends: X-Forwarded-For: 203.0.113.5

Backend code reads:
  String clientIP = request.getRemoteAddr(); // returns LB's internal IP!

Rate limiter uses clientIP as key:
  All users appear to come from the same IP (the LB)
  Rate limiter blocks EVERYONE when ANY user exceeds limit
```

```java
// FIX: read the real client IP from X-Forwarded-For header
String clientIP = request.getHeader("X-Forwarded-For");
// Or in Spring Boot:
String clientIP = request.getHeader("X-Real-IP");

// Production config (Spring Boot behind ALB):
server:
  forward-headers-strategy: framework
// Enables RemoteAddrFilter to unwrap forwarded headers automatically
// request.getRemoteAddr() then returns the real client IP ✅
```

---

## Scenario 3: Health Checks and Connection Draining

### The Question
> "During a rolling deploy, some users get 502 errors for 5-10 seconds. Why?"

```
What happens without connection draining:
  LB marks old pod as "removing" → immediately stops routing new requests
  But old pod still has 50 in-flight requests being processed!
  Those requests get killed mid-flight → 502 errors

FIX 1: Connection draining (deregistration delay)
  LB stops sending NEW requests to pod being removed
  Waits 30 seconds for in-flight requests to complete
  Then pod terminates cleanly
  → Zero dropped requests

  # AWS ALB: deregistration_delay.timeout_seconds = 30

FIX 2: Readiness probe in Kubernetes
  New pod starts → passes readiness check → LB starts routing
  Without readiness probe: LB routes to new pod before app is ready
  → First 200 requests get 503 (app still warming up)

  readinessProbe:
    httpGet:
      path: /actuator/health/readiness
      port: 8080
    initialDelaySeconds: 10
    periodSeconds: 5
    failureThreshold: 3

FIX 3: Pre-stop hook
  lifecycle:
    preStop:
      exec:
        command: ["sleep", "10"]
  # Gives LB 10s to notice pod is terminating before SIGTERM is sent
  # Prevents race condition between LB deregistration and pod termination
```

---

## Interview Cheat Sheet

> "For any scale problem I start with: make services stateless so you can add pods freely (sessions in Redis, not memory). For routing, ALB at L7 routes by path to the right microservice and terminates SSL; consistent hashing in the cache layer prevents cache avalanche when you add/remove nodes. For flash sales: pre-scale before traffic hits, pre-warm caches, and put order submission behind an async queue so burst writes go to SQS not directly to the DB. The most common trap I see is sticky sessions — it kills auto-scaling because all load pins to one server. The fix is to externalize all session state."
