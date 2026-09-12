# Interview Guide: API Gateway & Microservices Architecture

## 🗣️ The Interview Scenario

> "You keep saying 'API Gateway is a single entry point' — but if it's truly a single point of entry, how does it handle millions of requests per second without becoming a single point of failure? And honestly, isn't that just what a load balancer already does?"

This is one of the most common HLD interview traps: candidates conflate API Gateway with load balancer, and very few can actually explain the multi-region, DNS-backed architecture that makes "single entry point" not mean "single point of failure."

## 🏗️ Architect's Explanation (For a New Developer)

Think of an **API Gateway** as a smart **hotel concierge**, and a **load balancer** as a simple **traffic cop** directing cars into parking spots.

- The traffic cop (load balancer) doesn't care *what* you're doing — they just make sure cars are evenly spread across the available parking spots (instances of the *same* service).
- The concierge (API Gateway) actually **reads your request** and decides *which department* you need: "Ah, you want to check your invoice? Let me route you to the billing department. You want to place an order? That's the order department." It understands the **structure of your request** (the API endpoint) and routes accordingly to the *correct, different* backend service.

So the key distinction: **load balancer** = distribute traffic across *multiple instances of the same service*; **API Gateway** = understand the API request and route it to the *correct, potentially different* microservice — plus handle a whole set of cross-cutting concerns (auth, rate limiting, composition) so individual microservices don't have to duplicate that logic.

## 📊 Visualize It

**API Gateway vs. Load Balancer:**

```
                         API GATEWAY (understands the request)
Client --/api/invoice--> |                                    
Client --/api/order----> |---- routes based on endpoint ----> Invoice Microservice
Client --/api/sales-----> |                                    Order Microservice
                          |                                    Sales Microservice
                          
                         LOAD BALANCER (doesn't understand the request,
                                          just spreads traffic evenly)
Requests -------------> | Invoice MS instance 1
                        | Invoice MS instance 2
                        | Invoice MS instance 3
```

**Full multi-region architecture (how "single entry point" avoids being a single point of failure):**

```
Client
   |
   v
DNS-based Load Balancer (e.g., AWS Route 53 / Azure Traffic Manager)
   | picks nearest/compliant region based on latency & compliance rules
   |
   +----------------------+----------------------+
   v                      v                       v
Region 1 (Mumbai)     Region 2 (Chennai)      Region N...
   |                      |
   +-- AZ 1 --+           +-- AZ 1 --+
   |  API GW  |           |  API GW  |
   |    |     |           |    |     |
   |    v     |           |    v     |
   | Service  |           | Service  |
   | Discovery|           | Discovery|
   |    |     |           |    |     |
   |    v     |           |    v     |
   | Load     |           | Load     |
   | Balancer |           | Balancer |
   |    |     |           |    |     |
   |    v     |           |    v     |
   | MS       |           | MS       |
   | instances|           | instances|
   +----------+           +----------+
   +-- AZ 2 (backup, independent data center) --+
```
If AZ1 fails, AZ2 in the same region absorbs traffic. If the entire region fails, the DNS-based load balancer routes to another region entirely.

## Request Routing (Sequence Diagram)

```text
Client          -> DNS Load Balancer (Route 53) : request
DNS Load Balancer -> API Gateway (region/AZ)    : route to nearest healthy region
API Gateway     -> API Gateway                  : authenticate token (validate once, at the edge)
API Gateway     -> API Gateway                  : match endpoint (e.g. /api/invoice) to target service
API Gateway     -> Service Discovery             : lookup current location of target service
Service Discovery --> API Gateway                : healthy instance list / load balancer address
API Gateway     -> Load Balancer                 : forward request
Load Balancer   -> Microservice instance         : route to one instance
Microservice instance --> Client                 : response (via LB and GW)
```

*(Interactive Mermaid version: [mermaid-diagrams.md](mermaid-diagrams.md))*

## 🔧 Deep Dive: How It Actually Works

### API Gateway's Core Job: Intelligent Routing

An API Gateway accepts client API requests and **routes them to the correct backend service based on the API endpoint** (e.g., `/api/invoice` → Invoice microservice, `/api/order` → Order microservice). A plain load balancer has no such intelligence — it just distributes traffic across multiple instances of a *single* microservice.

### Feature 1: API Composition

**Problem it solves:** A mobile client (limited bandwidth) viewing "my orders" might only need product + invoice details (2 API calls). A desktop client, with more bandwidth, might show the same page with additional ratings, reviews, and recommendations — requiring more API calls, possibly to different microservices. Without a gateway, the **client** has to know about and orchestrate all these calls itself — extra complexity duplicated across every client type.

**The fix:** Configure a single endpoint (e.g., `/api/my-order`) at the API Gateway. The gateway itself contains the intelligence to know: "if this is a mobile device, call these 2 services and combine the result; if it's a desktop client, call these 4 services and combine the result" — returning **one single composed response** to the client. This dramatically reduces client-side complexity. (This is a heavily used pattern at companies like **Netflix**.)

### Feature 2: Authentication

The client first obtains an **access token** from an authorization server (see the OAuth 2.0 flow). On subsequent requests, the client passes this token to the API Gateway. The **API Gateway integrates with the authorization server** to validate the token *once, at the edge* — instead of duplicating authentication logic inside every individual microservice. Only validated requests are forwarded downstream.

### Feature 3: Rate Limiting (Three Sub-Mechanisms)

- **Burst limit** — the maximum number of **concurrent** requests the gateway will handle before returning `429 Too Many Requests`. (Both AWS and Azure API Gateway offerings expose a configurable burst limit setting.)
- **API throttling** — a more granular rule, e.g., "endpoint `/api/invoice` cannot be invoked more than 10 times per minute" — and this can be scoped even further, e.g., 10 times per minute **per individual user**. Once the limit is crossed (the 11th call in that minute), the request is blocked/fails.
- **IP-based blocking** — block a specific IP address from making requests entirely.
- **API queueing** — hold requests that cannot be processed immediately in a waiting queue rather than rejecting them outright; this directly helps mitigate the **Thundering Herd** problem (see the related HLD topic) by smoothing bursts instead of dropping them.

### Feature 4: Service Discovery

**Why it's needed:** microservices scale up/down dynamically, so their IP addresses and port numbers constantly change. Something needs to track their current location.

**Two approaches:**
1. **Self-registration** — each microservice instance registers/deregisters itself with the service discovery component as it scales up/down.
2. **Active health checking** — the service discovery component periodically health-checks all registered instances and automatically removes any that stop responding (no heartbeat), keeping only active instances in its directory.

Popular service discovery tools mentioned: **Zookeeper (Zul) and Eureka**-style software. When a request arrives, the API Gateway queries service discovery for the correct microservice/load-balancer location before forwarding the request.

### Other Notable Capabilities
- **Request/response transformation** — modify request/response payloads to match company/API needs.
- **Caching** — cache outbound responses so identical subsequent requests don't need to re-invoke the backend API.
- **Logging** — centralized request/response logging at the edge.

### How a "Single Entry Point" Handles Millions of Requests Without Being a Single Point of Failure

This requires understanding **Regions** and **Availability Zones (AZs):**

- A **Region** (e.g., Mumbai) contains multiple **Availability Zones** (e.g., two distinct areas within Mumbai).
- Each AZ has its **own dedicated data center** and **does not share resources** with other AZs.
- If one AZ goes down, traffic shifts to another AZ **within the same region** — the region itself isn't down.
- If **all** AZs in a region go down, only *then* is the entire region considered down — and companies operate **multiple regions** (e.g., Mumbai + Chennai) so that even a full-region failure doesn't cause a global outage.

**Layered architecture within this model:**
1. Within each AZ: microservice instances (multiple) → Load Balancer (distributes across instances of one microservice) → API Gateway (region/AZ-level, routes based on endpoint + queries service discovery to find the correct load balancer).
2. Across AZs within a region: if one AZ's load balancer/services fail, the other AZ absorbs traffic.
3. Across regions: a **DNS-based load balancer** sits above everything — e.g., **AWS Route 53** or **Azure Traffic Manager** — routing client requests to the *appropriate region's* API Gateway, based on factors like **latency** and **compliance** (e.g., certain countries' traffic may be legally restricted to certain regions, even if a closer region exists).

### Isn't DNS Itself a Single Point of Failure?

No — DNS is inherently distributed/hierarchical (local DNS, root DNS, top-level domain DNS, authoritative DNS — covered in depth in the companion DNS topic), so there is no single DNS instance whose failure takes down the whole system. (The transcript defers the full DNS mechanics to a dedicated follow-up video.)

## 🔥 Real Production Incident & Fix

**What broke:** An e-commerce platform's API Gateway was configured with authentication and routing logic, but **rate limiting/throttling had been left at default (essentially unlimited)** because the team assumed the downstream services' own internal safeguards (thread pools) were "good enough." During a flash sale, a small number of aggressive third-party integration partners (each retrying failed calls without backoff) generated a disproportionate share of total traffic to a single popular endpoint, `/api/inventory/check`.

**How it was detected:** On-call engineers noticed via API Gateway access logs and per-endpoint request-rate dashboards that `/api/inventory/check` alone accounted for over 60% of total gateway throughput, overwhelmingly from a handful of API keys/IPs, while legitimate customer checkout traffic on other endpoints started timing out due to shared backend resource contention.

**Root cause:** Without **per-client/per-endpoint API throttling** configured at the gateway, a small number of misbehaving integration partners were able to consume a disproportionate share of shared backend capacity, starving legitimate traffic — the gateway was correctly *routing* requests, but had no rate-limiting policy to prevent one client from monopolizing shared resources.

**The fix:**
1. Configured **API throttling** at the gateway: capped `/api/inventory/check` to a defined number of calls per minute **per API key**, rejecting excess calls with `429` instead of letting them consume backend capacity.
2. Set an explicit **burst limit** on the gateway as a whole to protect against any single momentary spike regardless of source.
3. Added **API queueing** for legitimate retriable overflow instead of hard failures, smoothing out short bursts.
4. Notified the offending integration partners and required them to implement proper backoff on their end.

```
BEFORE:                                        AFTER:
All clients share gateway with NO per-client   Gateway enforces per-API-key throttling
throttling -> one aggressive partner           (e.g., max N calls/min per key)
consumes 60%+ of shared backend capacity       + burst limit + queueing
-> legitimate customer traffic starves         -> misbehaving partner capped at 429,
                                                   legitimate traffic protected
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: If API Gateway sits "in front of" load balancers, why not just make the load balancer smarter instead of having two separate components?**
Separation of concerns keeps each component focused and simpler to scale/reason about — a load balancer is a lightweight, high-throughput traffic distributor optimized purely for spreading load across homogeneous instances, whereas an API Gateway carries heavier, request-aware logic (routing rules, auth integration, composition, rate limiting) that benefits from being a distinct layer that can evolve independently and be scaled/deployed on its own cadence.

**Q2: How does API composition actually reduce latency, given the gateway still has to call multiple backend services?**
It doesn't necessarily reduce the number of backend calls, but it moves the orchestration from the client (which may be on a slow mobile network making sequential round-trips) to the gateway (which is typically co-located in the same data center as the backend services, so those calls happen over a fast internal network) — and the gateway can often call the needed services in parallel and return one consolidated response, reducing the total round-trip time experienced by the client.

**Q3: What's the difference between burst limit and API throttling?**
Burst limit is a coarse-grained, gateway-wide (or per-route) cap on maximum concurrent requests at any given moment, protecting overall system capacity from momentary spikes; API throttling is a finer-grained, sustained-rate limit (e.g., N requests per minute) that can be scoped down to a specific endpoint, user, or API key, protecting fair usage and preventing any single client from consuming a disproportionate share of capacity over time.

**Q4: Why is service discovery necessary if you could just hardcode IP addresses in configuration?**
Modern microservice deployments scale instances up/down dynamically and get rescheduled with new IPs/ports (especially in containerized/cloud environments), so hardcoded addresses would become stale almost immediately; service discovery provides a live, continuously updated directory of healthy instance locations that the API Gateway (or client-side load balancer) can query at request time.

**Q5: How does a DNS-based load balancer like Route 53 decide which region to send a user to?**
It typically factors in latency (routing to the geographically/network-nearest healthy region), health checks (avoiding regions currently reporting failures), and compliance/data-residency rules (some countries mandate that certain traffic/data stay within specific regions regardless of latency), combining these signals to pick the most appropriate region-level API Gateway endpoint for that specific client.

**Q6: Doesn't adding an API Gateway introduce an extra network hop and therefore extra latency?**
Yes, there's a small added hop, but it's a worthwhile trade-off because the gateway is typically deployed very close (network-wise) to the backend services and absorbs cross-cutting concerns (auth, rate limiting, routing intelligence) that would otherwise have to be duplicated and independently maintained inside every microservice, which would introduce far more complexity and inconsistency risk than the marginal latency cost of one extra hop.

## 🔑 Key Takeaway

An API Gateway is fundamentally different from a load balancer because it **understands the request** (routes based on API endpoint to different services) and centralizes cross-cutting concerns (auth, rate limiting, composition, service discovery) — and it avoids being a true single point of failure by being deployed per-Availability-Zone, per-Region, with a DNS-based load balancer (like Route 53) sitting above everything to route traffic across regions based on latency, health, and compliance.
