# Client-Side Load Balancer in Microservices (Spring Cloud Load Balancer)

## What is this? (Plain English)

A load balancer decides which server to send a request to when there are multiple copies (instances) of the same service running. In a **client-side** load balancer, that decision-making logic lives inside the caller (your app), not on a separate machine. Think of it like a taxi app that already knows all available drivers and picks one for you — instead of calling a dispatcher who then finds a driver for you.

## The Problem It Solves

In a microservices system you often run several identical copies of a service (e.g. three instances of Product Service) so the system can handle more traffic and survive crashes. If your caller just hardcodes one address like `192.168.1.5:8080`, it always hits the same instance — that one gets overloaded while the others sit idle, and if it goes down, everything breaks. A load balancer spreads the requests across all healthy instances automatically.

## Architecture Diagram

```
                         Order Service (your app)
                        +---------------------------+
                        |                           |
                        |  RestTemplate             |
                        |  @LoadBalanced  --------> LoadBalancerInterceptor
                        |                           |        |
                        +---------------------------+        |
                                                             | 1. Get all instances
                                                             v
                                               +---------------------+
                                               |   Service Discovery  |
                                               |   (Eureka Server)    |
                                               +---------------------+
                                                             |
                                               2. Returns list of instances
                                                             |
                                                             v
                                               +---------------------+
                                               |  Load Balancing      |
                                               |  Algorithm           |
                                               |  (Round Robin /      |
                                               |   Random / Custom)   |
                                               +---------------------+
                                                             |
                                               3. Picks one instance
                                                             |
                              +-----------------+-----------+----------+
                              |                 |                      |
                              v                 v                      v
                   +------------------+ +------------------+ +------------------+
                   | Product Service  | | Product Service  | | Product Service  |
                   |   Instance 1     | |   Instance 2     | |   Instance 3     |
                   |  192.168.1.5:8081| |  192.168.1.6:8082| |  192.168.1.7:8083|
                   +------------------+ +------------------+ +------------------+
```

## Resolution Flow (Sequence)

```
Lanes: OC = Order Service code | RT = @LoadBalanced RestTemplate | LBI = LoadBalancerInterceptor
       SD = Service Discovery (Eureka) | Algo = LB Algorithm (RoundRobin/Random) | PS = Product Service instance

1)  OC  ──────────> RT   : getForObject("http://product-service/api/products")
2)  RT  ──────────> LBI  : intercept call (service name, not real host)
3)  LBI ──────────────────────> SD : get healthy instances for "product-service"
4)  LBI <────────────────────── SD : [instance1, instance2, instance3]
5)  LBI ────────────────────────────────> Algo : choose(instances)
6)  LBI <──────────────────────────────── Algo : instance2 (e.g. round robin)
7)  LBI ──(self-call)─>                        : rewrite URL to real IP:port
8)  LBI ────────────────────────────────────────────────> PS : forward actual HTTP call
9)  OC  <──────────────────────────────────────────────── PS : response
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## How It Works — Step by Step

1. You add the `spring-cloud-starter-loadbalancer` dependency to your `pom.xml`.
2. When creating your `RestTemplate` bean, you annotate it with `@LoadBalanced`. This tells Spring to attach a `LoadBalancerInterceptor` to every HTTP call made through that template.
3. In your code, instead of a hardcoded IP, you use the service name as the hostname: `http://product-service/api/products`. Spring knows to treat this as a service name, not a real hostname.
4. When your code calls `restTemplate.getForObject(...)`, the interceptor kicks in before the actual HTTP call goes out.
5. The interceptor calls `LoadBalancerClientFactory.getInstance(serviceId)` to fetch the load balancing algorithm configured for that specific service.
6. It then calls `loadBalancer.choose(request)`, which internally contacts Service Discovery (Eureka) and gets the current list of healthy instances for `product-service`.
7. The algorithm picks one instance from the list (e.g. Round Robin picks the next one in rotation).
8. The interceptor rewrites the URL from `http://product-service/api/products` to `http://192.168.1.6:8082/api/products` and forwards the request.
9. The response comes back normally — your code never knew any of this happened.

## Key Code / Config

**Step 1 — Add dependency in `pom.xml`:**
```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-loadbalancer</artifactId>
</dependency>
```

**Step 2 — Create a `@LoadBalanced` RestTemplate bean:**
```java
@Configuration
public class AppConfig {

    @Bean
    @LoadBalanced  // This tells Spring to intercept every call and apply load balancing
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
```

**Step 3 — Use the service name (not IP) in your call:**
```java
// application.properties
product.service.base-url=http://product-service  // service name, NOT an IP address

// In your service class:
String url = "http://product-service/api/products/" + productId;
Product product = restTemplate.getForObject(url, Product.class);
// The @LoadBalanced interceptor resolves "product-service" to a real instance
```

**Step 4 — Override algorithm for a specific service (Random instead of Round Robin):**
```java
// In your ORDER service application class — tells Spring which config to use for product-service
@SpringBootApplication
@LoadBalancerClient(name = "product-service", configuration = LoadBalancerProductClientConfig.class)
public class OrderServiceApplication { ... }

// The config class for product-service load balancing
// NOTE: Do NOT annotate this with @Configuration — it is loaded lazily at runtime, not at startup
public class LoadBalancerProductClientConfig {

    @Bean
    ReactorLoadBalancer<ServiceInstance> randomLoadBalancer(
            Environment environment,
            LoadBalancerClientFactory loadBalancerClientFactory) {

        // Get the service ID ("product-service") so the algorithm knows which service it belongs to
        String name = environment.getProperty(LoadBalancerClientFactory.PROPERTY_NAME);

        return new RandomLoadBalancer(
            // This supplier lazily contacts Eureka to get the instance list when needed
            loadBalancerClientFactory.getLazyProvider(name, ServiceInstanceListSupplier.class),
            name  // Attach this algorithm to "product-service" specifically
        );
    }
}
```

**Step 5 — Global default + per-service override (mix of both):**
```java
@SpringBootApplication
@LoadBalancerClients(
    // Per-service override: product-service uses Random
    value = {
        @LoadBalancerClient(name = "product-service", configuration = LoadBalancerProductClientConfig.class)
    },
    // Default for all OTHER services: Round Robin
    defaultConfiguration = LoadBalancerGlobalConfig.class
)
public class OrderServiceApplication { ... }

// Global config — applies to every service that does NOT have a specific override
public class LoadBalancerGlobalConfig {

    @Bean
    @ConditionalOnMissingBean  // IMPORTANT: only create if no bean already exists for this service ID
                               // Without this, product-service would get TWO algorithms and crash
    ReactorLoadBalancer<ServiceInstance> defaultLoadBalancer(
            Environment environment,
            LoadBalancerClientFactory loadBalancerClientFactory) {

        // service ID is resolved dynamically at runtime (e.g. "order-service", "sales-service")
        String name = environment.getProperty(LoadBalancerClientFactory.PROPERTY_NAME);

        return new RoundRobinLoadBalancer(
            loadBalancerClientFactory.getLazyProvider(name, ServiceInstanceListSupplier.class),
            name
        );
    }
}
```

**Step 6 — Custom load balancer (write your own algorithm):**
```java
public class CustomLoadBalancer implements ReactorServiceInstanceLoadBalancer {

    private final String serviceId;
    private final ObjectProvider<ServiceInstanceListSupplier> serviceInstanceListSupplierProvider;

    public CustomLoadBalancer(ObjectProvider<ServiceInstanceListSupplier> provider, String serviceId) {
        this.serviceInstanceListSupplierProvider = provider;
        this.serviceId = serviceId;
    }

    @Override
    public Mono<Response<ServiceInstance>> choose(Request request) {
        ServiceInstanceListSupplier supplier = serviceInstanceListSupplierProvider.getIfAvailable();
        return supplier.get().next().map(instances -> {
            if (instances.isEmpty()) {
                return new EmptyResponse();  // No instances available
            }
            // Write your custom selection logic here
            // e.g. pick instance with lowest active connections, or weighted selection
            ServiceInstance chosen = instances.get(0); // example: always pick first
            return new DefaultResponse(chosen);
        });
    }
}
```

## Important Concepts

- **Load Balancer**: A component that spreads incoming requests across multiple servers so no single one is overwhelmed.
- **Server-Side Load Balancer**: A dedicated external machine (like Nginx or AWS ELB) that sits between callers and servers and routes traffic. The caller has no load balancing logic itself.
- **Client-Side Load Balancer**: The load balancing logic lives inside the calling application. The caller itself decides which instance to talk to.
- **Service Discovery (Eureka)**: A registry that keeps track of all running instances of every service and their addresses. The load balancer queries this to get the current instance list.
- **`@LoadBalanced`**: A Spring annotation on a `RestTemplate` (or `WebClient`) bean that tells Spring to wrap it with a `LoadBalancerInterceptor`.
- **`LoadBalancerInterceptor`**: A Spring class that intercepts outgoing HTTP requests, resolves the service name to a real IP:port via load balancing, and then lets the request proceed.
- **Service ID / Client Name**: The application name of a target service (e.g. `product-service`). Each load balancing algorithm is bound to one specific service ID.
- **`ServiceInstanceListSupplier`**: An object that lazily fetches the list of healthy instances from Service Discovery when needed.
- **Round Robin**: The default algorithm — requests are distributed one-by-one in order: instance 1, instance 2, instance 3, instance 1, instance 2...
- **Random**: Picks a random instance from the list on every request.
- **`@LoadBalancerClient`**: Annotation that maps a specific service name to a specific load balancer configuration class.
- **`@LoadBalancerClients`**: Allows you to configure multiple per-service overrides AND a global default in one place.
- **`@ConditionalOnMissingBean`**: Tells Spring "only create this bean if one does not already exist for this service ID" — prevents duplicate algorithm beans from crashing the app.
- **Lazy / Runtime Loading**: Load balancer config classes are NOT loaded at application startup — they are loaded the first time you actually call that service. This is needed because the service ID is only known at the moment of the actual call.
- **Spring Cloud Load Balancer**: The current standard client-side load balancer library from Spring (replaced deprecated Netflix Ribbon).
- **Netflix Ribbon**: The older client-side load balancer (now deprecated). Spring Cloud Load Balancer is its replacement.
- **Istio / Service Mesh**: An infrastructure-level load balancing solution (sidecar pattern) that supports more advanced algorithms like least connections and weighted routing.

## Interview Q&A

**Q1: What is the difference between server-side and client-side load balancing?**
A: In server-side load balancing, there is a dedicated external component (like Nginx or AWS ELB) that receives all requests and forwards them to one of the backend instances — the caller has no knowledge of how many instances exist. In client-side load balancing, the caller itself holds the load balancing logic. It queries Service Discovery to get all available instances and then picks one using an algorithm before making the actual call. Client-side LB removes a network hop but adds complexity to the client.

**Q2: Why does `@LoadBalanced` on a `RestTemplate` enable load balancing? What does it actually do under the hood?**
A: The `@LoadBalanced` annotation is a qualifier that tells Spring to add a `LoadBalancerInterceptor` to the `RestTemplate`'s interceptor chain. When you make an HTTP call, this interceptor intercepts it, reads the hostname (which is a service name, not a real host), calls the `LoadBalancerClientFactory` to get the configured algorithm for that service, invokes the algorithm to pick an instance from Service Discovery, rewrites the URL with the actual IP and port, and then lets the request proceed.

**Q3: Why is each load balancing algorithm attached to a specific service ID rather than being global?**
A: Different services can have different traffic patterns and reliability requirements. A payment service might need a least-response-time algorithm while a notification service is fine with round robin. By binding each algorithm to a service ID, you get per-service control. It also prevents a single algorithm instance from maintaining shared state (like a round-robin counter) across multiple unrelated services.

**Q4: What happens if you forget to add `@ConditionalOnMissingBean` in the global load balancer config when you also have a per-service config?**
A: At runtime, when you call a service that has a specific config (e.g. `product-service`), Spring first loads the specific config and creates a `RandomLoadBalancer` tied to `product-service`. Then Spring loads the global config and tries to create a `RoundRobinLoadBalancer` also tied to `product-service`. Now two algorithms are mapped to the same service ID, which causes a runtime exception. The `@ConditionalOnMissingBean` guard in the global config prevents the global bean from being created when a specific bean already exists for that service ID.

**Q5: Why is it important that load balancer configuration classes are loaded lazily at runtime rather than at application startup?**
A: The service ID (e.g. `product-service`) is passed dynamically from the environment at runtime — it is not known at startup time. The global config especially relies on this because it can't hardcode which service is being called; it reads the service name from the environment at the moment of the call. If the config ran at startup, the service ID would be null and the algorithm would get tied to a null service ID, making it useless.

**Q6: What happens if you publish a request to `http://product-service/api/products` but all instances of `product-service` are down?**
A: The `ServiceInstanceListSupplier` will return an empty list from Service Discovery. The load balancer's `choose()` method will get zero instances, and it will return an `EmptyResponse`. The interceptor will fail to resolve the URL and throw an exception — typically resulting in a `503 Service Unavailable` or an `IllegalStateException`. This is where resilience patterns like circuit breakers (Resilience4j) come in to handle this gracefully.

**Q7: Spring Cloud Load Balancer supports only Round Robin and Random out of the box. How would you implement weighted load balancing where Instance A gets 70% of traffic and Instance B gets 30%?**
A: You implement a custom load balancer by creating a class that implements `ReactorServiceInstanceLoadBalancer` and overrides the `choose()` method. Inside `choose()`, you call `serviceInstanceListSupplierProvider.getIfAvailable().get()` to get the list of instances, then apply your weighted selection logic (e.g. use metadata tags on service instances to read the weight, then use a weighted random algorithm to pick one). You then wire this custom class into a `@LoadBalancerClient` configuration for the target service.

**Q8: Can you use the same load balancing configuration approach with Feign Client as with RestTemplate?**
A: Yes. Feign Client uses the same `LoadBalancerInterceptor` underneath. When you configure Feign with Service Discovery, you already get Round Robin by default. To override the algorithm for a specific service, you use the same `@LoadBalancerClient(name = "product-service", configuration = MyConfig.class)` annotation on your application class — the same configuration class and the same algorithm binding approach work identically. The only difference is that with Feign you don't need to add `@LoadBalanced` because Feign handles the interception through its own mechanism.

## Common Mistakes

1. **Annotating the load balancer config class with `@Configuration`**: The load balancer config class (the one you pass to `@LoadBalancerClient`) must NOT be annotated with `@Configuration` or be component-scanned by Spring. If it is, Spring will treat it as a regular startup bean and create it at startup with a null service ID, rather than lazily at runtime. Keep it as a plain class with no Spring stereotype annotations.

2. **Forgetting `@ConditionalOnMissingBean` in the global config**: When you have both a global default config and a per-service override, omitting `@ConditionalOnMissingBean` in the global config causes Spring to create two algorithms for the same service ID, resulting in a runtime crash. Always add this guard in the global/default configuration.

3. **Using a hardcoded IP/port instead of the service name in the URL**: Writing `http://192.168.1.5:8082/api/products` defeats the entire purpose. The URL hostname must be the exact registered service name (e.g. `http://product-service/api/products`) so the `LoadBalancerInterceptor` can recognize it, look it up in Service Discovery, and apply the algorithm.

4. **Mixing `@LoadBalancerClient` (singular) with `@LoadBalancerClients` (plural) incorrectly**: If you need both per-service overrides AND a global default, you must use `@LoadBalancerClients` with both the `value` (array of per-service configs) and `defaultConfiguration` attributes. Using multiple `@LoadBalancerClient` annotations without the plural wrapper, or forgetting the `defaultConfiguration`, means some services fall back to the built-in Round Robin rather than your intended global default.

5. **Assuming Netflix Ribbon is still the right choice**: Ribbon has been deprecated. New projects should use Spring Cloud Load Balancer. Ribbon-specific configuration (e.g. `@RibbonClient`) will not work in newer Spring Cloud versions and can cause subtle startup or runtime failures.