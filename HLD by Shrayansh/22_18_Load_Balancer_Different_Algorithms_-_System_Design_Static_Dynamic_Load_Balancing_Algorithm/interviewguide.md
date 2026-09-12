# Interview Guide: Load Balancer & Load Balancing Algorithms (Static & Dynamic)

## 🗣️ The Interview Scenario

> "You have two backend servers behind a load balancer. One server has 10x the CPU/memory capacity of the other, and incoming requests have wildly different processing times — some finish in milliseconds, some take 10+ seconds. Walk me through which load balancing algorithm you'd pick and why a plain round-robin would fail here. Also, what's the difference between an L4 and an L7 load balancer, and when would you pick one over the other?"

This question is popular because it tests whether a candidate memorized algorithm *names* or actually understands the **failure mode** each algorithm is designed to fix.

## 🏗️ Architect's Explanation (For a New Developer)

A load balancer's core job is simple: given many clients sending requests and multiple servers able to handle them, **don't let any single server get overwhelmed** — spread the load out. That's it. Everything else (logging, caching, SSL termination) is a bonus feature bolted on top.

Load balancers come in two flavors based on **which OSI layer they operate at**:
- **L4 (Network Load Balancer)** — operates at the transport layer. It can only see low-level info: TCP/UDP port, source IP, destination IP. It's fast because it doesn't need to inspect the actual request content.
- **L7 (Application Load Balancer)** — operates at the application layer. It can read HTTP headers, session cookies, and even the response body. This lets it make smarter routing decisions (e.g., route based on a cookie) and even do caching — but it's more computationally expensive since it has to parse more of the request.

Beyond that split, load balancing algorithms fall into two philosophies:
- **Static algorithms** — the routing decision doesn't depend on real-time server state; it's decided by a fixed rule (round-robin order, a pre-assigned weight, or a hash of the client IP).
- **Dynamic algorithms** — the routing decision depends on real-time signals like the number of active connections or measured response time, and gets recalculated for every incoming request.

The whole reason algorithms evolved from static to dynamic is that **static approaches can't tell the difference between "cheap" and "expensive" requests, or "fast" and "slow" servers** — which is exactly the scenario the interviewer's question sets up.

## 📊 Visualize It

**Static: Weighted Round Robin (server capacity considered, but not request cost):**

```
Server-1 (weight=3, 3x capacity) ─── gets requests 1, 2, 3
Server-2 (weight=1, 1x capacity) ─── gets request 4
                                       (then repeats: 5,6,7 → Server-1, 8 → Server-2)

PROBLEM: if request "4" happens to be a 10-second heavy request,
Server-2 (the weaker server) gets overloaded anyway —
weight only balances REQUEST COUNT, not REQUEST COST.
```

**Dynamic: Least Response Time (active connections × TTFB) — before/after a request arrives:**

```
                      active_conn   ttfb   score(=conn × ttfb)
Server-1                  3          2          6
Server-2                  1          4          4
Server-3                  0          2          0   ◄── LOWEST → gets the new request

After routing:
Server-3: active_conn becomes 1 → score recalculated on next request
(if two servers tie on score, load balancer falls back to round-robin between them)
```

## 🔧 Deep Dive: How It Actually Works

### L4 vs L7 Load Balancers
| | L4 (Network LB) | L7 (Application LB) |
|---|---|---|
| OSI Layer | Transport layer | Application layer |
| Visibility | TCP/UDP port, source & destination IP | HTTP headers, session, cookies, response/body data |
| Capabilities | Fast routing decisions | Can do caching, content-based routing, more advanced logic |
| Speed | Faster (less to inspect) | Slower relatively (more advanced processing) |

Most of the classic named algorithms below (round robin, weighted round robin, IP hash, least connection, etc.) are, per the transcript's framing, generally understood as **network (L4) load balancer** algorithms.

### Static Algorithm 1: Round Robin
Requests are distributed to servers in strict rotating order: Server-1, Server-2, Server-1, Server-2, ...

- **Pro:** trivially easy to implement; guarantees **equal request count** distribution.
- **Con:** treats a high-capacity server and a low-capacity server identically. If Server-1 has 10x the resources of Server-2 but both get the same number of requests, Server-2 is disproportionately more likely to get overloaded and go down.

### Static Algorithm 2: Weighted Round Robin
Each server is assigned a **weight representing its relative capacity**. E.g., Server-1 (weight 3) receives 3 requests for every 1 request Server-2 (weight 1) receives — request sequence becomes: 1→S1, 2→S1, 3→S1, 4→S2, 5→S1, 6→S1, 7→S1, 8→S2...

- **Pro:** low-capacity servers are protected from receiving a disproportionate request *count*; weights are static, so there's **no dynamic computation overhead** — set once when a server joins the pool.
- **Con:** it only balances **request count**, not **request processing time**. If the low-weighted server happens to receive several long-running requests (e.g., 10–20 second tasks) while the high-weighted server's requests all finish in milliseconds, the "protected" low-capacity server can still get overwhelmed, because weighted round robin has no visibility into how expensive each request actually is.

### Static Algorithm 3: IP Hash
The load balancer computes a **hash of the client's source IP address** and uses that hash to consistently map the client to the same server every time.

- **Pro:** ideal for use cases requiring **session affinity/stickiness** — the same client always reaches the same server (useful for session-based state).
- **Cons:**
  1. If client requests arrive through a **forward proxy** (all clients sharing one apparent source IP, as covered in the proxy topic), the load balancer sees only the proxy's IP — meaning *all* clients behind that proxy hash to the **same single server**, causing severe imbalance.
  2. Hashing provides **no guarantee of equal distribution** — even without a proxy in the mix, it's entirely possible for the hash function to skew disproportionately toward one server.

### Dynamic Algorithm 1: Least Connection
The load balancer tracks each server's **current active connection count** and routes each new request to whichever server has the **fewest active connections** at that moment.

- **Pro:** truly dynamic — adapts in real time instead of relying on a fixed formula, reducing the chance of any one server becoming overloaded, especially when all servers have roughly equal capacity.
- **Con:** an "active TCP connection" doesn't necessarily mean active traffic — a connection can be open with **zero or minimal traffic**, while another connection carries a heavy, continuous stream of requests. Least Connection doesn't distinguish between a low-capacity server with fewer-but-heavier connections and a high-capacity server with more-but-lighter connections.

### Dynamic Algorithm 2: Weighted Least Connection
Combines a static **weight** (representing server capacity) with the dynamic **active connection count**. For each new request, the load balancer computes:

```
ratio = active_connections / weight
```

...for every server, and routes the new request to the server with the **minimum ratio**.

Example from the transcript: Server-A has 2 active connections and weight 10 → ratio = 2/10 = 0.2. Server-B has 1 active connection and weight 1 → ratio = 1/1 = 1.0. The request goes to Server-A because 0.2 < 1.0 — even though Server-B has fewer raw connections, Server-A's much higher capacity means it's still the "less loaded" choice relative to its own capability.

### Dynamic Algorithm 3: Least Response Time (using TTFB)
**TTFB (Time To First Byte)** = the time interval between sending a request and receiving the first byte of the response from a server. The load balancer continuously tracks TTFB per server by monitoring live traffic.

For each incoming request, it computes a score per server:

```
score = active_connections × least_ttfb
```

...and routes to the server with the **lowest score**. Worked example from the transcript:
- Server-1: 3 active connections, TTFB = 2 → score = 3 × 2 = 6
- Server-2: 1 active connection, TTFB = 4 → score = 1 × 4 = 4
- Server-3: 0 active connections, TTFB = 2 → score = 0 × 2 = **0** ← lowest, gets the request

After routing, Server-3's active connection count increments to 1, and the score is **recomputed fresh for the very next incoming request** (not cached) — so decisions continuously adapt as load shifts. **If two or more servers tie on the computed score, the load balancer falls back to round-robin** among the tied servers.

## 🔥 Real Production Incident & Fix

**What broke:** A payments platform used plain **IP Hash** load balancing to achieve session stickiness for a legacy service that stored session state in server-local memory. After onboarding a large enterprise customer whose entire office sat behind a single corporate NAT/proxy IP, one backend server started receiving 40% of total traffic while three others sat mostly idle, and that server began timing out under load.

**How it was detected:** CPU/memory dashboards (via Prometheus + Grafana) showed one server pegged near 95% CPU while sibling servers in the same pool hovered around 15–20% — a classic asymmetric load signature. Cross-referencing load balancer access logs showed an unusually large fraction of requests all originating from the same source IP (the corporate NAT gateway of the new enterprise customer).

**Root cause:** IP-hash load balancing hashes on source IP for stickiness, but it doesn't account for the fact that many real-world clients share a single visible IP address (corporate NATs, mobile carrier NATs, forward proxies). All requests from that shared IP hashed to the exact same backend server, overloading it while the rest of the fleet remained underutilized.

**The fix:** The team migrated the stateful legacy service to store session state in a shared external store (Redis) instead of server-local memory, which removed the *need* for IP-based stickiness entirely. They switched the load balancer algorithm to **Weighted Least Connection**, which distributes based on real-time load rather than a fixed hash, and added session-affinity via a signed cookie (an L7 technique) for the few remaining flows that still needed stickiness — decoupling "session affinity" from "load distribution" so one customer's shared IP could no longer skew the whole fleet.

```
BEFORE (IP Hash):                             AFTER (Weighted Least Connection + cookie affinity):
Corp-NAT-IP ──► always Server-2 (95% CPU) ✖   Corp-NAT-IP requests ──► spread across least-loaded servers
Server-1/3/4: ~15-20% CPU (idle)               all servers: balanced CPU utilization
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why would you ever choose Round Robin over a dynamic algorithm today?**
Simplicity and predictability — when all backend servers have equal capacity and requests have roughly uniform processing cost, round robin achieves perfectly even distribution with zero computational overhead. Dynamic algorithms add tracking overhead (connection counts, TTFB measurements) that's unnecessary when the static assumption of "equal servers, equal requests" actually holds.

**Q2: How would you fix the IP Hash + proxy problem without abandoning session stickiness?**
Move to L7 load balancing and use **cookie-based session affinity** instead of IP-based hashing — the load balancer issues/reads a session cookie unique per client session rather than relying on the network-level source IP, which sidesteps the "many clients, one visible IP" problem entirely.

**Q3: What's the tradeoff of using Least Response Time over simpler Least Connection?**
Least Response Time is more adaptive to real server performance (it reacts to servers that are alive but slow, not just busy), but it requires continuously measuring and maintaining TTFB per server, which is more operational overhead than simply counting active connections.

**Q4: Can Weighted Round Robin and Least Connection be combined?**
Yes — that's essentially what Weighted Least Connection does: it takes the static, capacity-aware weight from weighted round robin and combines it with the dynamic, real-time active-connection signal from least connection, producing a ratio-based decision that accounts for both server capacity and current load.

**Q5: In a microservices architecture with many small, cheap requests and a few expensive ones, which algorithm would you recommend and why?**
Least Response Time (or Weighted Least Connection if response-time instrumentation isn't available) — because static algorithms like round robin or weighted round robin have no visibility into per-request cost, so an unlucky run of expensive requests routed to one server can overload it even under an otherwise "fair" distribution scheme.

**Q6: Does an L7 load balancer's ability to read response data mean it can also do caching?**
Yes — since an L7 load balancer inspects the full request/response including headers and body, it has the information needed to cache responses server-side, unlike an L4 load balancer which only sees transport-layer metadata (ports/IPs) and has no visibility into cacheable content.

## 🔑 Key Takeaway
Say this out loud: **"Static algorithms (round robin, weighted round robin, IP hash) make routing decisions from fixed, precomputed information and are cheap but blind to real-time load; dynamic algorithms (least connection, weighted least connection, least response time) recompute the decision per request using live signals like active connections and TTFB, trading a bit of overhead for resilience against uneven request costs."**
