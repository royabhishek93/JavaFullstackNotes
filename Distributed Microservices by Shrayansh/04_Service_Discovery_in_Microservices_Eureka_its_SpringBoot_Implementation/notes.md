# Service Discovery in Microservices — Eureka and Spring Boot

## What is this? (Plain English)

Service Discovery is like a phone book for your microservices. Instead of every service hard-coding the address of every other service it needs to talk to, they all register themselves in a central directory (Eureka Server), and when one service needs to call another, it looks up the current address from that directory. Think of it like your phone's contact list — you store "Mom" and let the phone figure out the number, rather than memorising a number that might change.

## The Problem It Solves

Without service discovery, every service must hard-code the IP address and port of every other service it calls. This breaks in three major ways:

- **Single point of failure**: If you hard-code `product-service:8081` and that exact instance goes down, your order service is stuck — it does not know about the other healthy instances running alongside it.
- **No load balancing**: Even if you have 10 instances of product-service, all traffic goes to the one hard-coded address. The other 9 sit idle.
- **Tight coupling and environment pain**: Different environments (dev, staging, prod) have different IPs. You end up changing config files constantly, and moving a service to a new machine means updating every other service that calls it.

## Architecture Diagram

```
                        +---------------------------+
                        |      EUREKA SERVER        |
                        |  (The Phone Book / Registry)|
                        |                           |
                        |  Key: app/instance-id     |
                        |  Value: IP, port, status  |
                        |  (stored in memory only)  |
                        +---------------------------+
                          ^    |            ^    |
              (1)Register |    | (2)Lookup  |    | (1)Register
              (Heartbeat) |    | instances  |    | (Heartbeat)
                          |    v            |    v
              +-----------------+      +--------------------+
              |  ORDER SERVICE  |      | PRODUCT SERVICE    |
              |  (Eureka Client)|      | (Eureka Client)    |
              |                 |      |                    |
              |  Local Cache:   |      | Instance 1: :8081  |
              |  product-svc    |      | Instance 2: :8082  |
              |  -> :8081,:8082 |      | Instance 3: :8083  |
              +-----------------+      +--------------------+
                        |                    ^
                        |  (3) Direct call   |
                        |  (load balanced,   |
                        |   no hard-coded URL)|
                        +--------------------+
```

- **Eureka Server**: The central registry that holds instance details for all registered services.
- **Order Service**: A Eureka client that registers itself AND looks up other services.
- **Product Service**: A Eureka client that registers itself with the server (multiple instances possible).
- **Local Cache**: Each client keeps a local copy of the registry so it does not hit the Eureka Server on every single request.

## Registration, Heartbeat & Discovery (Sequence)

```
Lanes: PS = Product Service (client) | ES = Eureka Server | OS = Order Service (client)

1)   PS ──────────────────> ES : register (name, IP, port, status)
     ┌─ loop: every 30s (default) ────────────────────────┐
2)   │  PS ──────────────> ES : heartbeat ("still alive")  │
     └──────────────────────────────────────────────────────┘
3)   OS ──────────────────> ES : fetch full registry (on startup)
4)   OS <────────────────── ES : registry snapshot
5)   OS ──(self-call)────>     : store in local cache
     ┌─ loop: every 30s (default) ────────────────────────┐
6)   │  OS ──────────────> ES : refresh local cache        │
     └──────────────────────────────────────────────────────┘
     note: Order Service reads from LOCAL CACHE, not Eureka, for each call
7)   OS ──────────────────> PS : direct HTTP call to a chosen instance (load balanced)
8)   OS <────────────────── PS : response
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## How It Works — Step by Step

1. **Eureka Server starts up.** It is a plain Spring Boot app with `@EnableEurekaServer`. It is now an empty phone book, waiting for registrations.

2. **Each microservice (client) starts up.** On startup, the client sends a registration request to the Eureka Server with its own details: service name, IP address, port number, and health status.

3. **Eureka Server stores the details in memory.** It maintains a map where the key is `app-name/instance-id` and the value holds IP, port, status, last-heartbeat time, etc.

4. **Clients send heartbeats periodically.** Every 30 seconds by default, each client sends a "I am still alive" signal (heartbeat) to the server. If the server does not receive a heartbeat within the configured expiry window (default 90 seconds), it removes that instance from the registry.

5. **On graceful shutdown, the client deregisters.** The client sends a deregistration request and the server marks it as DOWN immediately.

6. **When Order Service needs to call Product Service**, it does NOT call Eureka Server directly for every request. Instead:
   - At startup, Order Service fetches the full registry from Eureka Server and stores it in a local cache.
   - It reads from the local cache to find available Product Service instances.
   - It picks one instance (via load balancing — round-robin by default with Spring Cloud Load Balancer).
   - It makes the direct HTTP call to that instance.

7. **The local cache refreshes on a schedule** (default every 30 seconds). This keeps the list fresh without hammering the Eureka Server on every API call.

## Key Code / Config

### Eureka Server — pom.xml dependency
```xml
<!-- Tells Spring Boot this app is a Eureka registry server -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-server</artifactId>
</dependency>

<!-- Use dependency management so Spring Cloud handles version compatibility -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>2023.0.0</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

### Eureka Server — Main Class
```java
@SpringBootApplication
@EnableEurekaServer   // Without this annotation, the Eureka beans are never created
public class EurekaServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(EurekaServerApplication.class, args);
    }
}
```

### Eureka Server — application.properties
```properties
spring.application.name=eureka-server
server.port=8761

# This IS the server, so it should NOT register itself as a client
eureka.client.register-with-eureka=false

# This IS the server, so it does not need to fetch other registrations
eureka.client.fetch-registry=false

# Allow the server to evict instances that stop sending heartbeats
eureka.server.enable-self-preservation=false

# Check for dead instances every 6 seconds (good for testing; tune for production)
eureka.server.eviction-interval-timer-in-ms=6000
```

### Eureka Client (e.g. Product Service) — pom.xml dependency
```xml
<!-- Tells Spring Boot this app should register with Eureka -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
</dependency>

<!-- Required when using Feign Client or REST Client so the framework
     can automatically load-balance across multiple instances -->
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-loadbalancer</artifactId>
</dependency>
```

### Eureka Client — application.properties
```properties
spring.application.name=product-service   # This name appears in the Eureka dashboard
server.port=8081

# Register this service with Eureka (true by default, shown here for clarity)
eureka.client.register-with-eureka=true

# Fetch the registry so this service can discover others (true by default)
eureka.client.fetch-registry=true

# REQUIRED: Tell the client where the Eureka Server lives
# Without this, the client cannot talk to the server at all
eureka.client.service-url.defaultZone=http://localhost:8761/eureka

# Send a heartbeat every 60 seconds (default is 30)
eureka.instance.lease-renewal-interval-in-seconds=60

# Tell the server: if you don't hear from me for 90 seconds, consider me dead
# (default is 90; keep this larger than lease-renewal-interval)
eureka.instance.lease-expiration-duration-in-seconds=90

# How often to refresh the local cache of the registry (default is 30 seconds)
eureka.client.registry-fetch-interval-seconds=30
```

### Calling Another Service — Using DiscoveryClient (RestTemplate approach)
```java
@Autowired
private DiscoveryClient discoveryClient;  // Spring Cloud's built-in service lookup

public Product getProduct(String productId) {
    // Look up all healthy instances of "product-service" from local cache
    List<ServiceInstance> instances = discoveryClient.getInstances("product-service");

    // You MUST add your own load balancing logic here with RestTemplate
    // (round-robin, random, etc.) — this example just picks the first one
    ServiceInstance instance = instances.get(0);

    // instance.getUri() gives you http://192.168.x.x:8081 — no hard-coding!
    String url = instance.getUri() + "/products/" + productId;
    return restTemplate.getForObject(url, Product.class);
}
```

### Calling Another Service — Using Feign Client (recommended, load balancing is automatic)
```java
// Just use the service name registered in Eureka — no IP, no port
// Spring Cloud Load Balancer picks an instance automatically
@FeignClient(name = "product-service")
public interface ProductClient {
    @GetMapping("/products/{id}")
    Product getProduct(@PathVariable String id);
}
```

## Important Concepts

- **Eureka Server**: The central registry — stores which services are alive and where they live. Acts as a phone book for all registered microservices.
- **Eureka Client**: Any microservice that registers itself with the Eureka Server and/or looks up other services. Most microservices are both (they register AND they discover).
- **Service Registration**: When a client starts up, it tells the Eureka Server "I exist, here is my name, IP, and port."
- **Heartbeat**: A periodic "I am still alive" signal the client sends to the server. Prevents the server from thinking a service is dead just because it has been running quietly.
- **Deregistration**: When a service shuts down gracefully, it tells the Eureka Server "remove me." The server marks it as DOWN immediately.
- **Self-Preservation Mode**: A safety feature on the Eureka Server. If many heartbeats suddenly go missing (e.g., a network partition), the server assumes it is a network problem and does NOT remove the instances. Set to false in development so you can test eviction.
- **Local Cache (Client-Side Registry)**: Each Eureka client keeps its own in-memory copy of the registry. Requests use this cache, not a live call to Eureka Server, so there is no extra network hop on every API call.
- **Registry Fetch Interval**: How often the client refreshes its local cache from the Eureka Server. Trade-off between freshness and load on the server.
- **Eureka Server Cluster**: Running three Eureka Server instances that each act as clients to each other. Ensures no single point of failure for the registry itself. Uses eventual consistency — data syncs across nodes but not instantly.
- **Eventual Consistency**: Data changes on one Eureka Server node will eventually propagate to all other nodes, but there is a brief window where different nodes may show different data.
- **Spring Cloud Load Balancer**: The library that picks one instance from the list when Feign Client or REST Client fetches multiple healthy instances. Uses round-robin by default.

## Interview Q&A

**Q1: Why can't we just hard-code service URLs in production microservices?**

Hard-coding assumes that a service always lives at the same IP and port, and that only one instance ever exists. In production, instances are scaled up and down dynamically based on traffic. If you hard-code one URL, you get no load balancing (one instance takes all the traffic), and if that instance goes down, your calling service is broken even though other healthy instances are running. You also get tight coupling — moving a service to a new server requires changing every service that calls it.

**Q2: What are the two things a Eureka client does?**

Register itself — it tells the Eureka Server "I am here, this is my name, IP, and port." And discover instances — it asks the server for the list of available instances of another service it needs to call. Some services may only do one (e.g., a gateway might only discover, not register itself publicly).

**Q3: How does the Eureka Server know when a service goes down?**

Two ways. First, graceful shutdown: when a service is stopped cleanly, the Eureka client sends a deregistration request and the server immediately marks it as DOWN. Second, missed heartbeat: every client sends a heartbeat on a configured interval (default 30 seconds). If the server does not receive a heartbeat within the lease expiration window (default 90 seconds), it evicts that instance. This handles crashes and network failures where no clean shutdown happens.

**Q4: Where does the Eureka Server store its data? What are the implications?**

Eureka Server stores all registry data only in memory — there is no database persistence. This means if the server restarts, all registered instances must re-register. It also means a single Eureka Server is a single point of failure. That is why you always run a Eureka Server cluster (typically three nodes) in production, where each server is also a client that registers with and syncs to the other two.

**Q5: Why does adding Eureka not cause a latency increase on every API call?**

Because the Eureka Server is not called on every request. When a client starts up, it fetches the full registry and stores it in a local in-memory cache. All service discovery lookups hit this local cache, which involves no network call at all. The cache is refreshed on a configurable interval (default 30 seconds). The only latency cost is at application startup.

**Q6: What happens if the Eureka Server itself goes down?**

If you are running a single Eureka Server, it is a single point of failure. However, in production you run a cluster of three Eureka Servers. Each server is also configured as a client that registers with and syncs data to the other two. If one server goes down, clients automatically fall back to the other two. Additionally, because clients cache the registry locally, they can continue making calls to already-known instances even if all Eureka Servers become temporarily unreachable.

**Q7: What is the risk of setting the registry fetch interval too high on the client?**

The client's local cache becomes stale. If an instance that was healthy gets marked as DOWN, the client will not know for a long time and will keep trying to call it, resulting in failed requests until the cache refreshes. You must balance freshness (small interval) against the load you place on the Eureka Server (large interval). A reasonable default is 30 seconds.

**Q8: What happens if you forget to set `eureka.client.service-url.defaultZone` on a client service?**

The client will not know where the Eureka Server is and will keep trying to connect to `http://localhost:8761/eureka` (the default). If your Eureka Server is on a different host or port, registration will silently fail and the service will not appear in the registry. Other services will not be able to discover it. This is a common cause of "service not found" errors in Eureka setups.

## Common Mistakes

1. **Forgetting `eureka.client.register-with-eureka=false` and `fetch-registry=false` on the Eureka Server itself.** By default these are both `true`, so the server will try to register itself with another Eureka Server and keep throwing connection-refused errors in the logs because no other server exists. Always explicitly set both to `false` on the server application.

2. **Setting `lease-expiration-duration-in-seconds` smaller than `lease-renewal-interval-in-seconds` on the client.** This means the server will consider the client dead before the client even has a chance to send its next heartbeat. The instance will be evicted and re-registered in a loop. Always make the expiration duration larger than the renewal interval (e.g., renewal = 30s, expiration = 90s).

3. **Using a single Eureka Server in production.** It stores data only in memory and is a single point of failure. If it goes down, service discovery stops working for the entire system. Always run a three-node Eureka cluster with each node configured as a client of the other two.

4. **Not adding the Spring Cloud Load Balancer dependency when using Feign Client with service discovery.** When multiple instances are available, the framework needs load-balancing logic to pick one. Without the `spring-cloud-starter-loadbalancer` dependency, Feign cannot resolve the service name to an actual URL and calls will fail with a connection error.

5. **Setting the registry fetch interval (`registry-fetch-interval-seconds`) too high.** Engineers sometimes set this to a large number (hundreds of seconds) to reduce network traffic, not realising that their local cache will be severely stale. If an instance goes down, the client will keep attempting to call it for a long time before the cache refreshes, causing widespread request failures that are hard to diagnose.