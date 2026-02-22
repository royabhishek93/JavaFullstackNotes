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

**Last Updated:** February 22, 2026  
**Next: [Q20_microservices_monolith.md](Q20_microservices_monolith.md)**
