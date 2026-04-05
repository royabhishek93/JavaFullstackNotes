# Load Balancing Algorithms: When to Use Each

**Study Time:** 12-15 minutes | **Frequency:** 75% in senior interviews | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 Problem Scenario

You have 10,000 requests/second hitting your API:

```
       [Users: 10k req/sec]
            ↓
    [Load Balancer]
       ↙  ↓  ↖
    /    |    \
  [API-1] [API-2] [API-3]

How to distribute traffic fairly?
```

**Challenge:** Different algorithms handle different workloads.

---

## 🧠 Key Principle: Common Load Balancing Algorithms

| Algorithm | Distribution | Best For | When to Avoid |
|-----------|--------------|----------|--------------|
| **Round-Robin** | Cyclic (1→2→3→1) | Equal capacity servers | Variable load, slow servers |
| **Least Connections** | Fewest active | Long-lived connections | Stateless requests |
| **Weighted** | Proportional to power | Mixed capacity | All servers equal |
| **IP Hash** | Hash(IP) % servers | Session affinity | Hot spots from same IP |
| **Consistent Hash** | Consistent mapping | Cache aware, scaling | Simpler workloads |

---

## ✅ Algorithm 1: Round-Robin

**Cycle through servers in order:**

```
Request 1 → Server: API-1
Request 2 → Server: API-2
Request 3 → Server: API-3
Request 4 → Server: API-1 (cycle repeats)

Simple 1→2→3→1→2→3...
```

### Implementation:

```java
public class RoundRobinLoadBalancer {
    private final List<Server> servers;
    private int currentIndex = 0;
    private final ReentrantLock lock = new ReentrantLock();
    
    public RoundRobinLoadBalancer(List<Server> servers) {
        this.servers = servers;
    }
    
    public Server selectServer() {
        lock.lock();
        try {
            Server server = servers.get(currentIndex);
            currentIndex = (currentIndex + 1) % servers.size();
            return server;
        } finally {
            lock.unlock();
        }
    }
    
    public void routeRequest(Request req) {
        Server server = selectServer();
        server.handle(req);
    }
}
```

### Pros & Cons:

```
✅ Very simple
✅ No overhead (just counter)
✅ Fair distribution

❌ Ignores server capacity
❌ Ignores current load
❌ Bad for long connections (WebSocket)
```

### When to Use:

```
✅ Stateless requests (REST API)
✅ All servers equal (identical specs)
✅ Short-lived connections

❌ Servers vary in capacity
❌ WebSocket/long-lived connections
```

---

## ✅ Algorithm 2: Least Connections

**Route to server with fewest active connections:**

```
Server metrics:
  API-1: 50 active connections
  API-2: 20 active connections
  API-3: 80 active connections

New connection → API-2 (20 is minimum)

Great for long-lived connections!
```

### Implementation:

```java
public class LeastConnectionsLoadBalancer {
    private final List<Server> servers;
    private final ReentrantLock lock = new ReentrantLock();
    
    public LeastConnectionsLoadBalancer(List<Server> servers) {
        this.servers = servers;
    }
    
    public Server selectServer() {
        lock.lock();
        try {
            return servers.stream()
                .min(Comparator.comparingInt(Server::getActiveConnections))
                .orElseThrow();
        } finally {
            lock.unlock();
        }
    }
    
    public void routeRequest(Request req) {
        Server server = selectServer();
        server.handle(req);
    }
}

class Server {
    private int activeConnections = 0;
    private final ReentrantLock lock = new ReentrantLock();
    
    public void handle(Request req) {
        lock.lock();
        try {
            activeConnections++;
            process(req);
        } finally {
            activeConnections--;
            lock.unlock();
        }
    }
    
    public int getActiveConnections() {
        lock.lock();
        try {
            return activeConnections;
        } finally {
            lock.unlock();
        }
    }
    
    private void process(Request req) {
        // Process request
    }
}
```

### Pros & Cons:

```
✅ Adapts to load (doesn't ignore busy servers)
✅ Great for long-lived connections
✅ Works with variable request durations

❌ Overhead (tracking per-server connections)
❌ Requires active monitoring
❌ Bad for short requests (connection tracking overhead > benefit)
```

### When to Use:

```
✅ WebSocket connections (long-lived)
✅ Database connections (pooled, long-lived)
✅ SSH sessions

❌ REST APIs (short, request/response)
❌ When connection count unreliable
```

---

## ✅ Algorithm 3: Weighted Round-Robin

**Servers have different capacity**, distribute proportionally:

```
Servers:
  API-1: weight=100 (powerful)
  API-2: weight=50 (medium)
  API-3: weight=25 (weak)

Distribution pattern:
  API-1 → API-1 → API-2 → API-1 → API-1 → API-2 → API-1 → API-1 → API-1 → API-3

API-1 gets 100/175 = 57% of traffic
API-2 gets 50/175 = 29% of traffic
API-3 gets 25/175 = 14% of traffic
```

### Implementation:

```java
public class WeightedRoundRobinLoadBalancer {
    private static class ServerWithWeight {
        final Server server;
        final int weight;
        int currentWeight;  // Current weight in round
        
        ServerWithWeight(Server server, int weight) {
            this.server = server;
            this.weight = weight;
            this.currentWeight = 0;
        }
    }
    
    private final List<ServerWithWeight> servers;
    private final int totalWeight;
    private final ReentrantLock lock = new ReentrantLock();
    
    public WeightedRoundRobinLoadBalancer(Map<Server, Integer> serverWeights) {
        this.servers = serverWeights.entrySet().stream()
            .map(e -> new ServerWithWeight(e.getKey(), e.getValue()))
            .collect(Collectors.toList());
        this.totalWeight = serverWeights.values().stream()
            .mapToInt(Integer::intValue)
            .sum();
    }
    
    public Server selectServer() {
        lock.lock();
        try {
            // Add weight to each server
            int totalCurrentWeight = 0;
            ServerWithWeight selectedServer = null;
            
            for (ServerWithWeight sw : servers) {
                sw.currentWeight += sw.weight;
                if (selectedServer == null || sw.currentWeight > selectedServer.currentWeight) {
                    selectedServer = sw;
                }
            }
            
            // Reduce selected server's weight
            selectedServer.currentWeight -= totalWeight;
            
            return selectedServer.server;
        } finally {
            lock.unlock();
        }
    }
    
    public void routeRequest(Request req) {
        Server server = selectServer();
        server.handle(req);
    }
}
```

### Pros & Cons:

```
✅ Respects server capacity
✅ Works with mixed hardware
✅ Simple mechanism

❌ Hardcoded weights (must update config)
❌ Ignores dynamic load
❌ Weights must be tuned manually
```

### When to Use:

```
✅ Mixed server capacity (some powerful, some weak)
✅ Known, stable performance differences
✅ Stateless workloads

❌ Servers with variable load
❌ Unknown performance characteristics
```

---

## ✅ Algorithm 4: IP Hash

**Hash client IP to consistent server:**

```
Client IP: 192.168.1.100
hash(192.168.1.100) % 3 = 1
→ Route to Server 2

Same client always goes to same server!
```

### Implementation:

```java
public class IPHashLoadBalancer {
    private final List<Server> servers;
    private final ReentrantLock lock = new ReentrantLock();
    
    public IPHashLoadBalancer(List<Server> servers) {
        this.servers = servers;
    }
    
    public Server selectServer(String clientIP) {
        lock.lock();
        try {
            int hash = clientIP.hashCode();
            int index = Math.abs(hash % servers.size());
            return servers.get(index);
        } finally {
            lock.unlock();
        }
    }
    
    public void routeRequest(Request req) {
        String clientIP = req.getClientIP();
        Server server = selectServer(clientIP);
        server.handle(req);
    }
}
```

### Pros & Cons:

```
✅ Session affinity (same client → same server)
✅ No state loss (cached data stays)
✅ Simple hash function

❌ HOT SPOTS (some IPs get hashed to same server)
❌ Uneven distribution (if 3 IPs hash to same server)
❌ Problem: Data center all on same IP (corporate proxy)
  → All 1000 employees → same server!
```

### When to Use:

```
✅ Session affinity needed
✅ In-memory caching on server
✅ Stateful services

❌ When traffic comes from few IPs (corporate network)
❌ Microservices (share nothing)
```

---

## ✅ Algorithm 5: Consistent Hashing

**Hash that minimizes reshuffling on scale:**

```
Problem with IP Hash:
  Add new server:
    N = 3 → 4
    hash(IP) % 4 ≠ hash(IP) % 3
    All clients rehash to different servers!
    Cache becomes worthless

Solution: Consistent Hashing
  Servers placed on hash ring
  Add server → only ~1/N keys reshuffle
  Remove server → only ~1/(N-1) keys reshuffle
```

### Implementation:

```java
public class ConsistentHashLoadBalancer {
    private final TreeMap<Long, Server> ring = new TreeMap<>();
    private final int replicas = 3;  // Virtual nodes per server
    private final ReentrantLock lock = new ReentrantLock();
    
    public void addServer(Server server) {
        lock.lock();
        try {
            for (int i = 0; i < replicas; i++) {
                long hash = hash(server.getId() + ":" + i);
                ring.put(hash, server);
            }
        } finally {
            lock.unlock();
        }
    }
    
    public void removeServer(Server server) {
        lock.lock();
        try {
            for (int i = 0; i < replicas; i++) {
                long hash = hash(server.getId() + ":" + i);
                ring.remove(hash);
            }
        } finally {
            lock.unlock();
        }
    }
    
    public Server selectServer(String key) {
        lock.lock();
        try {
            long hash = hash(key);
            
            // Find server with hash >= key's hash
            Map.Entry<Long, Server> entry = ring.ceilingEntry(hash);
            
            // Wrap around if needed
            if (entry == null) {
                entry = ring.firstEntry();
            }
            
            return entry.getValue();
        } finally {
            lock.unlock();
        }
    }
    
    private long hash(String key) {
        return Math.abs((long) key.hashCode());
    }
    
    public void routeRequest(Request req) {
        Server server = selectServer(req.getClientIP());
        server.handle(req);
    }
}
```

### Pros & Cons:

```
✅ Minimal reshuffle on scale (1/N, not all)
✅ Session affinity maintained
✅ Great for caching systems (Redis cluster)

❌ Complex implementation
❌ Hot spots (uneven distribution without virtual nodes)
❌ Overhead of virtual node management
```

### When to Use:

```
✅ Distributed caching (Redis, Memcached)
✅ Sharded databases
✅ Scaling frequently

❌ Simple load balancing (overkill)
❌ When consistency not needed
```

---

## 📊 Algorithm Comparison

| Algorithm | Fairness | Overhead | Session Affinity | Scaling |
|-----------|----------|----------|-----------------|---------|
| Round-Robin | ⭐⭐ (ignores load) | ⭐⭐⭐⭐⭐ | ❌ | Simple |
| Least Connections | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | Good |
| Weighted RR | ⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | Fair |
| IP Hash | ⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | Bad |
| Consistent Hash | ⭐⭐⭐ | ⭐⭐ | ✅ | Excellent |

---

## 🚨 Advanced Scenarios

### Client-Side vs Server-Side Load Balancing

```
Server-Side Load Balancer (traditional):
  [Client] → [LB] → [Server A/B/C]
  
  Pros: Single point of decision
  Cons: LB becomes bottleneck

Client-Side Load Balancer (microservices):
  [Client] → Direct to [Server A/B/C]
  Client has balancing logic
  
  Pros: Distributed, no bottleneck
  Cons: Complex client logic
```

### Health Checks

```java
public class HealthCheckLoadBalancer {
    private final List<Server> servers;
    private final ScheduledExecutorService executor = 
        Executors.newScheduledThreadPool(1);
    

    ---

    ## ⚠️ Operational Pitfalls (From Production)

    ### 1) Unequal servers + round-robin

    ```
    Problem: Different capacity servers get same traffic
    Solution: Weighted round-robin
    ```

    ### 2) Sticky sessions without shared session store

    ```
    Problem: IP hash sends a user to one server
    Server crashes → session lost

    Solution: External session store (Redis) or stateless auth (JWT)
    ```

    ### 3) No SSL termination at the load balancer

    ```
    Problem: Every backend decrypts SSL (CPU heavy)
    Solution: Terminate SSL at LB, forward HTTP internally
    ```

    ### 4) Single load balancer (SPOF)

    ```
    Problem: One LB fails → entire system down
    Solution: Multi-LB + DNS failover or active-active LB
    ```
    public HealthCheckLoadBalancer(List<Server> servers) {
        this.servers = servers;
        startHealthChecks();
    }
    
    private void startHealthChecks() {
        executor.scheduleAtFixedRate(() -> {
            for (Server server : servers) {
                try {
                    // Ping server
                    server.ping();
                    server.setHealthy(true);
                } catch (Exception e) {
                    server.setHealthy(false);
                }
            }
        }, 0, 5, TimeUnit.SECONDS);
    }
    
    public Server selectServer() {
        // Only select healthy servers
        return servers.stream()
            .filter(Server::isHealthy)
            .min(Comparator.comparingInt(Server::getActiveConnections))
            .orElseThrow(() -> new RuntimeException("No healthy servers"));
    }
}
```

---

## 🎯 Interview Q&A

### Q1: "API has 10k req/sec, which algorithm?"

**Answer (1 min):**
```
Least Connections is best for REST APIs.

Why:
- Adaptive (responds to current load)
- No server overload
- Works with variable request times

Since REST is stateless:
- No need for session affinity (IP Hash problematic)
- Round-Robin ignores actual load

Plus health checks:
  Only route to healthy servers
```

---

### Q2: "Cache cluster with 100 servers, not consistent hashing?"

**Answer:**
```
Question: Why is consistent hashing critical for caching?

Scenario without consistent hashing:
  Have 100 cache servers
  Add 1 new server (now 101)
  Old hash: key % 100
  New hash: key % 101
  
Result: 99% of keys rehash!
  → Keys spread to different servers
  → Cache misses everywhere
  → Thundering herd on database

With Consistent Hashing:
  Add server → only ~1% of keys rehash
  Minimize cache misses
  Maintain performance
```

---

### Q3: "Rate limiting + load balancing?"

**Answer:**
```
LB doesn't handle rate limiting!

LB routes traffic.
Rate limiting checks quota.

Order matters:
1. LB distributes to servers
2. Each server applies rate limit

If need global rate limit:
  → Rate limiter before LB
  → Reject excess requests before reaching servers
  → Special middleware

Trade-off:
- Per-server: Simple, distributed
- Global: Accurate, prevents resource waste
```

---

## 🔑 Key Takeaways

| Concept | Interview Value |
|---------|-----------------|
| Algorithm selection | ⭐⭐⭐⭐⭐ |
| Trade-offs (affinity vs distribution) | ⭐⭐⭐⭐⭐ |
| Consistent hashing for scaling | ⭐⭐⭐⭐ |
| Health checks and resilience | ⭐⭐⭐⭐ |
| Client vs server side LB | ⭐⭐⭐ |

---

**Priority:** 🔥 MUST KNOW (75% senior interviews)

**Related:**
- Distributed Caching
- Service Discovery
- Reverse Proxy

---

**Last Updated:** March 5, 2026
