# Feign Client in Spring Boot Microservices — Synchronous Communication using Declarative HTTP Client

## What is this? (Plain English)

Feign Client is a way for one microservice to call another microservice's API without writing any HTTP connection code yourself. Think of it like ordering food at a restaurant — you just tell the waiter what you want (declare the order), and the kitchen figures out how to make it. You declare which API you want to call by writing a Java interface, and Feign figures out all the HTTP plumbing behind the scenes. It was originally built by Netflix and is available in Spring Boot via the `spring-cloud-openfeign` library.

## The Problem It Solves

Without Feign, you have to manually write HTTP connection code using RestTemplate or RestClient — you handle URLs, serialization, error handling, and retry logic yourself. This is repetitive and error-prone. Feign removes all that boilerplate: you just write a Java interface that mirrors the endpoint you want to call, annotate it, and Feign creates a working implementation at runtime. It also integrates cleanly with other Spring Cloud features like service discovery, load balancing, and circuit breakers — so you're not wiring those together yourself either.

## Architecture Diagram

```
  +---------------------------+
  |       Order Service       |
  |        (port 8081)        |
  |                           |
  |  +---------------------+  |
  |  |  OrderController    |  |
  |  |  @Autowired         |  |
  |  |  ProductClient      |  |
  |  +--------+------------+  |
  |           |               |
  |  +--------v------------+  |
  |  |  ProductClient      |  |
  |  |  (Feign Interface)  |  |
  |  |  @FeignClient       |  |
  |  +--------+------------+  |
  |           |               |
  |  +--------v------------+  |
  |  | Feign Runtime Proxy |  |
  |  | (Dynamic Proxy)     |  |
  |  | MethodHandler       |  |
  |  | InvocationHandler   |  |
  |  +--------+------------+  |
  |           |               |
  +-----------|---------------+
              | HTTP GET /product/{id}
              v
  +---------------------------+
  |      Product Service      |
  |        (port 8082)        |
  |                           |
  |  +---------------------+  |
  |  | ProductController   |  |
  |  | GET /product/{id}   |  |
  |  +---------------------+  |
  +---------------------------+
```

## Request Flow (Sequence)

```
Lanes: OC = OrderController | Proxy = Feign Dynamic Proxy | IH = InvocationHandler | MH = MethodHandler | PS = Product Service

1)  OC    ──────────────> Proxy : productClient.getProductById(id)
2)  Proxy ──────────────> IH    : intercept method call
3)  IH    ──────────────> MH    : look up MethodHandler for this method
4)  MH    ──(self-call)─>       : build request (URL, headers, encoder)
5)  MH    ──────────────────────────────────────────> PS : HTTP GET /product/{id}
    ┌─ alt: success (2xx) ──────────────────────────────────────────────────┐
6)  │  PS ──────────────────────────────────────────> MH : 200 OK + body            │
7)  │  MH ──(self-call)─>                                 : Decoder converts JSON -> Java object │
8)  │  MH ──────────────> OC : return deserialized result                            │
    ├─ else: error (4xx/5xx) ────────────────────────────────────────────────┤
9)  │  PS ──────────────────────────────────────────> MH : error response            │
10) │  MH ──(self-call)─>                                 : ErrorDecoder builds exception │
11) │  MH ──────────────> OC : throw exception                                       │
    └──────────────────────────────────────────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## How It Works — Step by Step

1. **Add the dependency** — Add `spring-cloud-openfeign` to `pom.xml`. Use Spring Cloud BOM (dependency management) so you never have to manually match version numbers across multiple Spring Cloud libraries.

2. **Enable Feign** — Add `@EnableFeignClients` to your main Spring Boot application class. Without this, Spring Boot will not even scan for Feign interfaces.

3. **Write the interface** — Create a Java interface in the calling service (e.g., Order Service). Annotate it with `@FeignClient`, give it an arbitrary name, and provide the base URL of the target service (e.g., `http://localhost:8082`). Write method signatures that mirror the endpoints you want to call, using the same `@GetMapping`, `@PostMapping`, `@PathVariable`, `@RequestParam`, `@RequestHeader`, and `@RequestBody` annotations you use in controllers.

4. **Feign builds a proxy at startup** — When the application starts, Feign scans for all `@FeignClient` interfaces. For each interface, it:
   - Parses each method and its annotations to build a `MethodHandler` (stores target URL, HTTP method, headers, encoder, decoder, error decoder, retry settings).
   - Creates an `InvocationHandler` that holds a map of method → MethodHandler.
   - Uses Java's **dynamic proxy** to generate a runtime implementation of your interface. You never write this class; Feign generates it invisibly.

5. **Autowire and call** — In your controller or service layer, autowire the Feign interface just like any Spring bean. Call the method as if it were a normal Java method call.

6. **Feign intercepts the call** — The dynamic proxy intercepts the call, looks up the right `MethodHandler`, serializes the request body (via Encoder), makes the actual HTTP call, deserializes the response (via Decoder), and returns the result to your code.

7. **Errors and retries are handled** — If the HTTP response is 4xx/5xx, the `ErrorDecoder` kicks in. If there is a network/connection timeout, the `Retryer` kicks in to retry the call automatically.

## Key Code / Config

**pom.xml — add the dependency (no version needed; BOM manages it)**
```xml
<!-- Spring Cloud BOM handles compatible versions for all Spring Cloud libs -->
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>2023.0.1</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependencies>
    <!-- Feign Client library -->
    <dependency>
        <groupId>org.springframework.cloud</groupId>
        <artifactId>spring-cloud-starter-openfeign</artifactId>
        <!-- No version: BOM picks a compatible version automatically -->
    </dependency>
</dependencies>
```

**Main Application — enable Feign scanning**
```java
@SpringBootApplication
@EnableFeignClients // Without this, Spring won't scan for @FeignClient interfaces
public class OrderServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }
}
```

**Feign Interface — declare what to call, not how**
```java
@FeignClient(
    name = "product-service",           // Arbitrary name; used in config/properties
    url = "${feign.client.product-service.url}", // Base URL read from application.properties
    configuration = ProductClientConfig.class    // Optional: custom encoder/decoder/error handler
)
public interface ProductClient {

    // Mirrors the exact endpoint on Product Service — GET /product/{id}
    @GetMapping("/product/{id}")
    String getProductById(@PathVariable("id") Long id);

    // Another example with path variable, request param, header, and body
    @PutMapping(value = "/product/update/{id}", consumes = "application/json")
    String updateProduct(
        @PathVariable("id") Long id,
        @RequestBody ProductDto product,          // Feign's Encoder serializes this to JSON
        @RequestParam("sendMail") boolean sendMail,
        @RequestHeader("X-Custom-Header") String header
    );
    // Note: parameter ORDER does not need to match the target controller — annotations drive mapping
}
```

**application.properties — base URL and timeouts**
```properties
# Base URL for product-service Feign client
feign.client.product-service.url=http://localhost:8082

# Timeout specific to product-service Feign client only
feign.client.config.product-service.connect-timeout=3000
feign.client.config.product-service.read-timeout=5000

# Apply same timeout to ALL Feign clients using "default"
# feign.client.config.default.connect-timeout=3000
```

**Custom Configuration — per-client encoder, decoder, error decoder, retryer**
```java
@Configuration
public class ProductClientConfig {

    @Bean
    public Encoder feignEncoder() {
        // Custom encoder: converts Java object → JSON for request body
        return new ProductEncoder(); // implements feign.codec.Encoder
    }

    @Bean
    public Decoder feignDecoder() {
        // Custom decoder: converts JSON response → Java object
        return new ProductDecoder(); // implements feign.codec.Decoder
    }

    @Bean
    public ErrorDecoder errorDecoder() {
        // Custom error decoder: called when response is 4xx or 5xx
        return new ProductErrorDecoder(); // implements feign.codec.ErrorDecoder
    }

    @Bean
    public Retryer retryer() {
        // Default: 5 attempts, 100ms initial wait, doubles each time, max 1s cap
        // Never retry: return Retryer.NEVER_RETRY;
        // Custom: extend Retryer.Default and override values
        return new Retryer.Default(100, 1000, 5);
    }
}
```

**Custom Error Decoder**
```java
public class ProductErrorDecoder implements ErrorDecoder {
    private final ErrorDecoder defaultDecoder = new Default();

    @Override
    public Exception decode(String methodKey, Response response) {
        if (response.status() >= 400 && response.status() < 500) {
            throw new ClientErrorException("Client error: " + response.status());
        }
        if (response.status() >= 500) {
            throw new ServerErrorException("Server error: " + response.status());
        }
        // Fall back to Feign's default for anything else
        return defaultDecoder.decode(methodKey, response);
    }
}
```

**Controller — autowire and use like a normal bean**
```java
@RestController
public class OrderController {

    @Autowired
    private ProductClient productClient; // Feign-generated proxy is injected here

    @GetMapping("/order/{productId}")
    public String placeOrder(@PathVariable Long productId) {
        String product = productClient.getProductById(productId); // looks like a local call
        System.out.println("Response from product API: " + product);
        return "Order placed successfully";
    }
}
```

## Important Concepts

- **Declarative HTTP client** — You declare *what* to call (interface + annotations), not *how* to connect. The framework handles the HTTP mechanics.
- **@FeignClient** — Marks an interface as a Feign client; required for Spring to generate a proxy for it.
- **@EnableFeignClients** — Tells Spring Boot to scan for `@FeignClient`-annotated interfaces at startup. Nothing works without this.
- **Spring Cloud OpenFeign** — The Spring Cloud library that wraps Netflix's Feign and integrates it with Spring Boot, service discovery, and load balancing.
- **Spring Cloud BOM** — A Bill of Materials that ensures all Spring Cloud libraries you add are on mutually compatible versions, so you never version-clash.
- **Dynamic Proxy** — A Java mechanism (via `java.lang.reflect.Proxy`) that generates a concrete class implementing an interface at runtime. Feign uses this to give you a working implementation of your declared interface.
- **MethodHandler** — An internal Feign object created per-method; holds all parsed info (target URL, HTTP method, headers, encoder, decoder, timeout, retry settings) needed to make the actual HTTP call.
- **InvocationHandler** — Bridges the dynamic proxy and the MethodHandler; intercepts each method call, looks up the right MethodHandler, and delegates execution.
- **Encoder** — Converts a Java request-body object into the HTTP wire format (e.g., JSON). Default uses Jackson.
- **Decoder** — Converts the HTTP response body (e.g., JSON) back into a Java object. Default uses Jackson.
- **ErrorDecoder** — Called when the response status is non-2xx (4xx/5xx). Default wraps it in a `FeignException`. You can override to throw custom exceptions.
- **Retryer** — Controls retry behavior on retriable exceptions (connection/network timeouts). Default: up to 5 total attempts, 100ms initial wait, doubling each time, capped at 1s.
- **Per-client configuration** — Each `@FeignClient` can have its own `configuration` class, letting you give different encoders, decoders, timeouts, and error handling to different target services.
- **Base URL vs. Relative path** — The `url` in `@FeignClient` is the base (host + port). The path in `@GetMapping`/`@PostMapping` is the relative endpoint. Feign combines them for the final request URL.

## Interview Q&A

**Q1: What is Feign Client and why would you use it over RestTemplate?**
Feign is a declarative HTTP client — you define an interface describing which APIs to call, and Feign generates the implementation at runtime using dynamic proxies. Compared to RestTemplate, you write zero boilerplate HTTP code, error handling and retry are configurable out of the box, and it integrates seamlessly with Spring Cloud components like service discovery and load balancing. For mature microservice architectures, Feign is strongly preferred.

**Q2: Why do you annotate the main class with `@EnableFeignClients`? What happens if you forget it?**
`@EnableFeignClients` tells Spring Boot's component scan to look for interfaces annotated with `@FeignClient` and register them as beans. Without it, Spring ignores all `@FeignClient` interfaces entirely — you will get a `NoSuchBeanDefinitionException` at startup or runtime when you try to autowire them, because no proxy was ever created.

**Q3: How does Feign create a working object from a plain interface with no implementation class?**
At application startup, Feign uses Java's **dynamic proxy** mechanism (`java.lang.reflect.Proxy`) to generate a concrete implementation of your interface at runtime. For each method, it builds a `MethodHandler` by parsing the annotations (URL, HTTP method, headers, parameters). An `InvocationHandler` bridges the proxy and the `MethodHandler`. When you call a method on the autowired bean, the proxy intercepts it, the `InvocationHandler` routes it to the right `MethodHandler`, which builds the HTTP request, executes it, and decodes the response.

**Q4: Why should you use Spring Cloud's dependency management (BOM) instead of specifying Feign's version directly?**
When you build microservices with Spring Cloud, you typically use multiple libraries — Feign, service discovery (Eureka), load balancer, circuit breaker, etc. Each of these has its own version, and they must all be compatible with each other. The Spring Cloud BOM (Bill of Materials) guarantees that every Spring Cloud dependency you pull in is on a mutually compatible, tested set of versions. If you pin Feign's version yourself, you risk version conflicts when you later add Eureka or Ribbon.

**Q5: Why is it safe to have different `configuration` classes for different `@FeignClient` interfaces?**
Each `@FeignClient` can specify its own `configuration` class (e.g., `ProductClientConfig`, `SalesClientConfig`). The beans defined in that class (Encoder, Decoder, ErrorDecoder, Retryer, timeouts) are scoped specifically to that client. This means Product Service calls can have a 3-second timeout and a custom error decoder, while Sales Service calls have a 10-second timeout and a different retry policy, with zero interference between them.

**Q6: What is an ErrorDecoder and when is it invoked?**
`ErrorDecoder` is called by Feign whenever the HTTP response status code is non-2xx (i.e., 4xx or 5xx). Feign's default implementation wraps the status, headers, and body in a `FeignException` and throws it. You can provide a custom `ErrorDecoder` to throw domain-specific exceptions (e.g., `ProductNotFoundException` for 404, `ServiceUnavailableException` for 503), which makes your error handling much cleaner in calling code.

**Q7: What happens if a Feign call gets a connection timeout — will it retry automatically, and how many times?**
Yes. Feign's default `Retryer` retries on retriable exceptions like connection timeouts (`IOException`). The default behavior is up to **5 total attempts** (1 original + 4 retries), with an initial wait of 100ms that **doubles** on each retry (100ms → 200ms → 400ms → 800ms), capped at 1 second. 4xx/5xx HTTP errors do NOT trigger retries — those go straight to the `ErrorDecoder`. You can disable retries entirely with `Retryer.NEVER_RETRY`, or customize the attempt count and wait times.

**Q8: What happens if you do not set a TTL / timeout on a Feign client and the downstream service hangs indefinitely?**
Without a configured `connect-timeout` and `read-timeout`, Feign will wait indefinitely for the downstream service to respond. In a synchronous microservices chain, one slow service will block a thread in the calling service for as long as the call hangs. Under load, all available threads in the calling service can be exhausted waiting for the unresponsive service, causing the calling service itself to stop handling new requests — a cascading failure. Always configure explicit timeouts per client via `feign.client.config.<name>.connect-timeout` and `read-timeout`.

## Common Mistakes

1. **Forgetting `@EnableFeignClients` on the main application class.** This is the most common mistake. Without it, Spring never scans for `@FeignClient` interfaces and the autowire fails with `NoSuchBeanDefinitionException`. Always add it to the `@SpringBootApplication` class.

2. **Hardcoding the base URL directly in `@FeignClient(url = "http://localhost:8082")`.** This works locally but breaks in every other environment (dev, staging, prod). The URL should always be externalized to `application.properties` and referenced with `${feign.client.product-service.url}`. For production microservices, the URL should be resolved via service discovery (Eureka), not hardcoded at all.

3. **Specifying individual Spring Cloud library versions instead of using the BOM.** Engineers manually pin `spring-cloud-starter-openfeign` to a version, then later add Eureka at a different version. The two libraries are incompatible, causing subtle runtime failures. Always use `spring-cloud-dependencies` BOM in `<dependencyManagement>` and omit version tags on all Spring Cloud starters.

4. **Not configuring timeouts and assuming Feign will fail fast.** By default, Feign has no read timeout cap. In production, if a downstream service is slow, Feign will hold the HTTP thread open indefinitely. Always configure `connect-timeout` and `read-timeout` — either globally via `feign.client.config.default.*` or per client via the client name.

5. **Assuming the parameter order in the Feign interface must match the controller method order in the target service.** Engineers sometimes reorder parameters trying to match the controller signature. In Feign, **annotations drive the mapping**, not position. `@PathVariable`, `@RequestParam`, `@RequestHeader`, and `@RequestBody` can appear in any order in the Feign interface method — Feign resolves them by annotation type, not position.