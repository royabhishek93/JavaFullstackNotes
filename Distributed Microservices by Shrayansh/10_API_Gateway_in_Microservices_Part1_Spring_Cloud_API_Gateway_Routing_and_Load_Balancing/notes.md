# API Gateway Part 1 — Routing and Load Balancing (Spring Cloud Gateway)

## What is this? (Plain English)

If you have hundreds of clients and hundreds of microservices, you don't want every client to know the host/port of every single microservice. An **API Gateway** sits between clients and your microservices as a **single entry point** — every request passes through it first. The gateway decides which microservice should actually handle each request and forwards it there.

## The Problem It Solves

Without a gateway, every client must hard-code the location (host/port) of every microservice it talks to. The moment your architecture changes — say, `Order Service` gets merged into `Sales Service` — **every one of those clients** has to be updated to point at the new location. With a gateway in the middle, clients only ever talk to the gateway; only the gateway's routing config needs to change when microservices are split, merged, renamed, or rescaled. This is on top of the other benefits a gateway centralizes: **authentication** (no duplicating JWT validation in every service), **rate limiting** (stop floods at the front door instead of every microservice defending itself), **resilience** (circuit breaker/retry applied at the edge), **request/response transformation**, and **centralized logging/monitoring**.

## Architecture Diagram

```
   Client (Postman / browser / mobile app)
        │
        │  http://localhost:8083/products/1
        ▼
 ┌─────────────────────────────────────────┐
 │           API GATEWAY (port 8083)        │
 │                                          │
 │  Route 0: id=product-service             │
 │           predicate: path=/products/**   │
 │           uri: lb://PRODUCT-SERVICE      │
 │                                          │
 │  Route 1: id=order-service                │
 │           predicate: path=/orders/**     │
 │           uri: lb://ORDER-SERVICE        │
 └─────────────────────────────────────────┘
        │                         │
        ▼                         ▼
 ┌───────────────┐        ┌───────────────┐
 │ Product Service│        │  Order Service │
 │ (instance 1,2..)│      │ (instance 1,2..)│
 └───────────────┘        └───────────────┘
        ▲                         ▲
        └───────────┬─────────────┘
                     │ registers with
                     ▼
            ┌──────────────────┐
            │   Eureka Server   │  (service discovery)
            └──────────────────┘
```

## Request Flow (Sequence)

```
Lanes: Client | GW = API Gateway | SD = Eureka (Service Discovery) | LB = Load Balancer | PS = Product Service instance

1)  Client ──────────> GW : GET /products/1
2)  GW ──(self-call)─>    : match route by Path predicate
    ┌─ alt: uri = lb://PRODUCT-SERVICE ──────────────────────────────────┐
3)  │  GW ──────────> SD : get healthy instances for PRODUCT-SERVICE      │
4)  │  GW <────────── SD : [instance1, instance2, ...]                    │
5)  │  GW ──────────> LB : choose one instance                            │
6)  │  GW <────────── LB : instance2                                     │
    └─────────────────────────────────────────────────────────────────────┘
7)  GW ─────────────────────────────────────────────> PS : forward request to chosen instance
8)  GW <───────────────────────────────────────────── PS : response
9)  Client <────────── GW : response
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## How It Works — Step by Step

1. A client sends a request to the gateway's own port (e.g. `localhost:8083/products/1`) — **never** directly to a microservice's port.
2. The gateway matches the request path against configured **routes**, each with an `id`, a `uri` (where to forward to), and one or more **predicates** (matching rules — most commonly `Path` and `Method`).
3. If the URI is hardcoded (`http://localhost:8082`), the gateway always forwards to that one instance — fine for a demo, but doesn't scale.
4. For real load balancing across multiple instances, the URI is written as `lb://SERVICE-NAME` instead of a hardcoded host/port. `lb://` tells the gateway to use **Spring Cloud LoadBalancer** — it queries **Eureka** (service discovery) for all live instances registered under that name, then picks one using a client-side load-balancing algorithm (the same mechanism covered in the Service Discovery / Client-Side Load Balancer topics — no new internals here).
5. The request is forwarded to the chosen instance, and the response flows back through the gateway to the client.

## Key Code / Config

```properties
# API Gateway itself (port 8083), registered as a Eureka client
server.port=8083
eureka.client.service-url.defaultZone=http://localhost:8761/eureka/

# Route 0 — Product Service
spring.cloud.gateway.routes[0].id=product-service
spring.cloud.gateway.routes[0].uri=lb://PRODUCT-SERVICE
spring.cloud.gateway.routes[0].predicates[0]=Path=/products/**
spring.cloud.gateway.routes[0].predicates[1]=Method=GET,POST

# Route 1 — Order Service
spring.cloud.gateway.routes[1].id=order-service
spring.cloud.gateway.routes[1].uri=lb://ORDER-SERVICE
spring.cloud.gateway.routes[1].predicates[0]=Path=/orders/**
```
```xml
<!-- API Gateway pom.xml -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-gateway</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
</dependency>
```

## Important Concepts

- **API Gateway**: A single entry point that sits between clients and microservices, handling routing, load balancing, auth, rate limiting, resilience, and transformation centrally.
- **Route**: A configured mapping of `id` + `uri` + `predicates[]` — "if the request matches these predicates, forward it to this URI."
- **Predicate**: A matching rule for a route. `Path=/products/**` and `Method=GET,POST` are the two most commonly used; header-based predicates also exist but are rarely needed.
- **`lb://SERVICE-NAME`**: Tells the gateway to resolve the URI dynamically via service discovery + client-side load balancing, instead of hardcoding a single instance's host/port.
- **Decoupling clients from topology changes**: The single most important reason to introduce a gateway — clients only ever need to know the gateway's address; microservice splits/merges/rescaling only require updating the gateway's route config, not every client.
