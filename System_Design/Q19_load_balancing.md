# 🎯 Q19: Explain Load Balancing Algorithms

> **Interview Frequency:** 76% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

How do you distribute 100k user requests across 10 servers?

---

## 📌 Load Balancing Algorithms

### 1. **Round-Robin**
- Distribute sequentially to each server
- Server 1 → Server 2 → Server 3 → Server 1
- Good for: Uniform workloads
- Problem: Ignores server capacity

### 2. **Least Connections**
- Send request to server with fewest active connections
- Good for: Long-lived connections (WebSocket)
- Best: Most real-world scenarios

### 3. **IP Hash**
- Hash user IP → always same server
- Good for: Session persistence (sticky sessions)
- Problem: Server goes down = many requests rerouted

### 4. **Weighted Round-Robin**
- More powerful servers get more requests
- Server 1 (2x) → 2 requests, Server 2 (1x) → 1 request
- Good for: Heterogeneous servers

---

## 💬 Interview Tip (Say This Exactly)

"Use least-connections for general cases. Use IP-hash for session stickiness if sessions not shared. Use weighted round-robin for different server capacities. Monitor: request latency, active connections per server, server utilization."

---

## 📚 Flow

```
[100k Requests]
     ↓
[Load Balancer]
  ↙ ↓ ↘ ↖ ↗
[S1] [S2] [S3] ... [S10]
```

**Least Connections Strategy:**
- S1: 50 connections
- S2: 48 connections (next request goes here)
- S3: 45 connections

---

## ⚠️ Common Pitfalls

**Pitfall 1: Using round-robin with unequal servers**
```
// ❌ Round-robin with different capacity servers
Server 1: 32 cores, 64GB RAM
Server 2: 2 cores, 4GB RAM
// Both get same number of requests!

// ✅ Use weighted round-robin
Server 1: weight = 16
Server 2: weight = 1
```

**Pitfall 2: Health check not configured**
```
// ❌ Load balancer sends traffic to dead server
Server 3 crashed, but LB doesn't know → 33% of requests fail!

// ✅ Configure health checks
Health check: GET /health every 5 seconds
If 3 consecutive failures → remove from pool
```

**Pitfall 3: Sticky sessions without session replication**
```
// ❌ IP-hash sends user to Server 1
// Server 1 crashes → user loses session

// ✅ Session replication or external session store
Store sessions in Redis (all servers access same session)
```

**Pitfall 4: Not terminating SSL at load balancer**
```
// ❌ Each backend server does SSL decryption (CPU expensive)
User → [LB] → Server 1 (decrypts SSL)
           → Server 2 (decrypts SSL)

// ✅ Terminate SSL at load balancer
User → [LB decrypts SSL] → Server 1 (plain HTTP)
                        → Server 2 (plain HTTP)
```

**Pitfall 5: Single load balancer (single point of failure)**
```
// ❌ Load balancer crashes = entire system down

// ✅ Multiple load balancers + DNS failover
DNS → LB1 (primary)
DNS → LB2 (failover)
```

---

## 🛑 When NOT to Use Each Algorithm

- ❌ **Round-Robin**: Unequal servers, long-lived connections
- ❌ **Least Connections**: Servers have different capacities (use weighted)
- ❌ **IP Hash**: No session persistence needed (adds inflexibility)
- ❌ **Weighted**: All servers identical capacity
- ✅ **Default**: Least Connections for most scenarios

---

## 🔗 Related Questions

- [Q17_database_scaling.md](Q17_database_scaling.md) - Database read replicas and load distribution
- [Q18_caching_strategies.md](Q18_caching_strategies.md) - Caching layer before load balancer
- [Q20_microservices_monolith.md](Q20_microservices_monolith.md) - Load balancing microservices
- [Q22_message_queues.md](Q22_message_queues.md) - Event distribution across services

---

**Last Updated:** February 22, 2026  
**Next: [Q20_microservices_monolith.md](Q20_microservices_monolith.md)**
