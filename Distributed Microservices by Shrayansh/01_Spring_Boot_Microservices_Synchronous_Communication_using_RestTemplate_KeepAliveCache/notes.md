# Spring Boot Microservices: Synchronous Communication using RestTemplate and KeepAlive Cache

## What is this? (Plain English)

When you split a large app into separate microservices, those services still need to talk to each other over the network. Synchronous communication is like a phone call — Service A calls Service B and waits on the line until it gets an answer before doing anything else. RestTemplate is Spring Boot's built-in tool (now considered legacy) that handles all the low-level networking details for you so you can make that call with a single line of code instead of writing 30 lines of Java yourself.

## The Problem It Solves

Without a framework abstraction like RestTemplate, every HTTP call between microservices requires manually creating a connection object, setting headers and timeouts, initiating a TCP handshake, reading a raw input stream, parsing the response bytes, and closing the stream — all by hand. This is error-prone boilerplate. One missed stream close can leak connections. RestTemplate replaces all of that with one method call and handles connection reuse (via KeepAlive cache) automatically.

## Architecture Diagram

```
  +---------------------+          HTTP/1.1 (Keep-Alive)         +----------------------+
  |    Order Service    |  -------- GET /product/{id} ----------> |   Product Service    |
  |    (port 8081)      |                                         |    (port 8082)       |
  |                     | <------- 200 OK + JSON body ----------- |                      |
  |  OrderController    |                                         |  ProductController   |
  |  RestTemplate bean  |                                         |  /product/{id}       |
  +---------------------+                                         +----------------------+
           |
           | uses
           v
  +----------------------------+
  |       RestTemplate         |  <-- Spring's HTTP client wrapper
  |  (configured as @Bean)     |
  +----------------------------+
           |
           | internally uses
           v
  +-------------------------------------+
  | SimpleClientHttpRequestFactory      |  <-- creates HttpURLConnection objects
  | (sets connectTimeout, readTimeout)  |
  +-------------------------------------+
           |
           | on every call checks
           v
  +-------------------------------------+
  |       KeepAlive Cache               |  <-- key: host+port, value: HTTP client (TCP conn)
  |  { "localhost:8082" -> HttpClient } |
  +-------------------------------------+
           |
           | if cache miss, creates new TCP connection (3-way handshake)
           | if cache hit, reuses existing TCP connection
           v
  +-------------------------------------+
  |     TCP Connection (HttpClient)     |  <-- actual socket to Product Service
  +-------------------------------------+
```

## Request Flow (Sequence)

```
Lanes:  OC = OrderController | RT = RestTemplate | KA = KeepAlive Cache | PS = Product Service

 1)  OC  ────────────────────────────────> RT  : getForObject(url, String.class)
 2)          RT  ──(self-call)───────────>     : SimpleClientHttpRequestFactory.createRequest()
 3)          RT  ────────────────────────> KA  : check cache for host:port
     ┌─ alt: cache hit ──────────────────────────────────────────────────┐
 4)  │       KA  ────────────────────────> RT  : reuse existing TCP connection      │
     ├─ else: cache miss ─────────────────────────────────────────────────┤
 5)  │       RT  ──────────────────────────────────────────> PS : TCP 3-way handshake │
 6)  │       PS  ──────────────────────────────────────────> RT : connection established │
 7)  │       RT  ────────────────────────> KA  : store new connection                │
     └────────────────────────────────────────────────────────────────────┘
 8)          RT  ──────────────────────────────────────────> PS : send HTTP GET request (thread blocks)
 9)          PS  ──────────────────────────────────────────> RT : 200 OK + JSON body
10)          RT  ────────────────────────> KA  : mark connection "free" (not closed)
11)  OC <──────────────────────────────── RT  : deserialized response object
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## How It Works — Step by Step

1. Order Service starts on port 8081, Product Service starts on port 8082. Both are plain Spring Boot apps with a REST controller each.

2. A `RestTemplate` bean is created once in a `@Configuration` class. Spring injects it wherever needed via `@Autowired`.

3. When a request hits Order Service's `/order/{id}` endpoint, it calls `restTemplate.getForObject(url, String.class)`.

4. RestTemplate internally calls `SimpleClientHttpRequestFactory.createRequest()`, which builds an `HttpURLConnection` object (the same low-level Java object you'd use manually) and sets the HTTP method, headers, connect timeout, and read timeout.

5. RestTemplate then calls `execute()` on the request object. This triggers `connection.connect()`.

6. Before opening a brand new TCP socket, the JVM checks the **KeepAlive cache** (a map keyed by `host:port`). If a warm connection to `localhost:8082` is already sitting idle in cache, it gets reused — no new 3-way TCP handshake needed.

7. If there is no cached connection, a new TCP connection is established (3-way handshake), stored in the cache, and marked "in use."

8. The HTTP request is sent over the TCP connection. The calling thread blocks and waits for a response (this is the "synchronous / blocking" nature).

9. The server sends back the HTTP response. RestTemplate reads the response stream, automatically deserialises it to the requested type (e.g., `String.class` or `Product.class`), closes the stream, and marks the TCP connection as "free" in the cache (does NOT close the TCP socket).

10. The TCP connection stays in the cache until either the server's `Keep-Alive: timeout=5` (idle timeout in seconds) expires, or the `max=50` (maximum requests on one connection) limit is reached — after which a 4-way TCP termination closes the socket.

## Key Code / Config

```java
// --- AppConfig.java ---
@Configuration
public class AppConfig {

    @Bean
    public RestTemplate restTemplate() {
        // Use the factory when you need custom timeouts; otherwise just: new RestTemplate()
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(3000);  // 3 s to establish TCP connection
        factory.setReadTimeout(5000);     // 5 s to wait for the server's response
        return new RestTemplate(factory);
    }
}

// --- OrderController.java ---
@RestController
public class OrderController {

    @Autowired
    private RestTemplate restTemplate; // Spring injects the bean above

    @GetMapping("/order/{id}")
    public String getOrder(@PathVariable String id) {

        String productServiceUrl = "http://localhost:8082/product/" + id;

        // getForObject: makes the GET call, returns ONLY the response body
        // Spring auto-deserialises the JSON response into a String here
        String product = restTemplate.getForObject(productServiceUrl, String.class);

        return "Order processed. Product details: " + product;
    }
}

// --- When you also need status code + headers, use getForEntity instead ---
ResponseEntity<Product> response =
    restTemplate.getForEntity(productServiceUrl, Product.class);
int status = response.getStatusCodeValue();   // e.g. 200
Product body = response.getBody();

// --- POST example ---
Product newProduct = new Product("Laptop", 1200.00);
Product created = restTemplate.postForObject(
    "http://localhost:8082/product",
    newProduct,      // request body — Spring serialises this to JSON automatically
    Product.class    // expected response body type
);

// --- exchange: full control over headers (e.g., add auth token) ---
HttpHeaders headers = new HttpHeaders();
headers.setContentType(MediaType.APPLICATION_JSON);
headers.set("Authorization", "Bearer " + token); // custom header
HttpEntity<Product> entity = new HttpEntity<>(newProduct, headers);

ResponseEntity<Product> result = restTemplate.exchange(
    "http://localhost:8082/product",
    HttpMethod.POST,
    entity,           // carries both header and body
    Product.class     // Spring handles JSON deserialisation for you
);
```

## Important Concepts

- **Synchronous communication**: Caller sends a request and blocks until the response arrives — like a phone call you stay on until the other side answers.
- **Blocking in nature**: The calling thread is paused ("blocked") for the entire duration of the network round-trip.
- **HTTP/1.0 vs HTTP/1.1**: In 1.0, the TCP connection closes after every response. In 1.1 (the default), the connection stays open (Keep-Alive) for reuse.
- **Keep-Alive**: An HTTP/1.1 header that tells both sides "do not tear down this TCP connection after this response — keep it open for more requests."
- **KeepAlive cache (in JVM)**: A map (`host:port` → `HttpClient`) that stores open TCP connections so they can be reused for the next request without a new 3-way handshake.
- **connectTimeout**: Maximum time (milliseconds) to wait while establishing the TCP connection. Fails fast if the server is unreachable.
- **readTimeout**: Maximum time (milliseconds) to wait for the server to send back a response after the connection is open.
- **HttpURLConnection**: Low-level Java class that represents one HTTP request/response cycle and wraps the underlying TCP socket.
- **SimpleClientHttpRequestFactory**: RestTemplate's default factory class that creates `HttpURLConnection` objects and is where you set timeouts.
- **getForObject**: Returns only the response body, auto-deserialised into your requested type.
- **getForEntity**: Returns the full `ResponseEntity` (status code + headers + body).
- **exchange**: Use when you need to customise request headers or the HTTP method yourself, but still want Spring to handle serialisation/deserialisation.
- **execute**: The lowest-level RestTemplate method — you control everything including serialisation; all other methods call this internally.
- **Feign Client**: A Spring Cloud abstraction built on top of the same HTTP machinery, designed for microservice-to-microservice calls with load balancing and service discovery.

## Interview Q&A

**Q1: What is the difference between synchronous and asynchronous communication in microservices?**
A: Synchronous means the caller blocks its thread and waits for the response before proceeding — like a normal phone call. Asynchronous means the caller fires a message and moves on; the response (if any) comes back later via a callback or message queue. RestTemplate and Feign Client are synchronous. Kafka/RabbitMQ-based messaging is asynchronous.

**Q2: Why is RestTemplate considered "legacy" in Spring Boot?**
A: RestTemplate has dozens of overloaded methods (`getForObject`, `getForEntity`, `postForObject`, `postForEntity`, `exchange`, `execute`, etc.) that are hard to remember and maintain. Every new feature (circuit breaker, retry, new HTTP method) requires adding yet another overloaded variant. Spring introduced `RestClient` (Spring 6 / Boot 3) with a fluent builder-style API that is easier to read, maintain, and extend without method explosion. RestTemplate is now in maintenance-only mode — bug fixes only, no new features.

**Q3: Why does RestTemplate reuse TCP connections instead of creating a new one for every HTTP call?**
A: Opening a TCP connection requires a 3-way handshake (SYN → SYN-ACK → ACK), which adds latency. HTTP/1.1 defaults to Keep-Alive, meaning the server signals the client to keep the socket open after each response. The JVM's KeepAlive cache stores the open connection keyed by `host:port`. On the next call to the same service, RestTemplate finds the cached connection and skips the handshake — reducing latency and OS resource usage.

**Q4: What is the difference between `connectTimeout` and `readTimeout`?**
A: `connectTimeout` governs the TCP handshake phase — how long to wait for the remote server to accept the connection. If the server is down or firewalled, you want this to fail quickly (e.g., 3 seconds). `readTimeout` governs the HTTP response phase — after the connection is open and the request is sent, how long to wait for the server to start sending back a response. A slow backend could hang your thread indefinitely without a readTimeout.

**Q5: What happens if you call `restTemplate.getForObject(...)` and the Product Service is down?**
A: RestTemplate will attempt to connect. If `connectTimeout` is set, the call throws a `ResourceAccessException` (wrapping `java.net.ConnectException`) after that timeout elapses. If no `connectTimeout` is set, the thread could block for a very long time (OS-level TCP timeout, often minutes) before failing. This is why always setting timeouts is critical in production, and why circuit breakers (Resilience4j) are layered on top to stop hammering a failing service.

**Q6: Why does `disconnect()` on `HttpURLConnection` not always close the TCP socket immediately?**
A: Because in HTTP/1.1 with Keep-Alive, the JVM wants to keep the TCP connection alive for reuse. When you call `disconnect()`, the JVM checks whether the response was fully read. If it was, the underlying `HttpClient` (TCP wrapper) is returned to the KeepAlive cache as "free" — not closed. The socket is only physically closed when the Keep-Alive timeout expires, the max-requests limit is hit, or the server explicitly sends `Connection: close`.

**Q7: When would you choose `exchange` over `getForObject` / `postForObject`?**
A: Use `exchange` when you need to set custom request headers (e.g., an `Authorization: Bearer` token, a tracing ID, a custom content type) or when you want access to the full response including status code and response headers. `getForObject` and `postForObject` give you only the response body and give you no control over request headers. `exchange` still handles JSON serialisation/deserialisation automatically — that is what separates it from `execute`, where you manage serialisation yourself.

**Q8: What is the difference between `RestTemplate`, `RestClient`, and `FeignClient`, and when would you use each?**
A: `RestTemplate` is the legacy Spring HTTP client — functional but verbose API, maintenance-only mode. `RestClient` (Spring Boot 3+) is the modern replacement with a readable fluent API; use it for direct HTTP calls when you are not using Spring Cloud. `FeignClient` is a declarative HTTP client from Spring Cloud — you define an interface with annotations and Spring Cloud generates the implementation; it integrates automatically with Eureka service discovery and Ribbon/Spring Cloud LoadBalancer, making it the right choice in a full microservices stack.

## Common Mistakes

1. **Not setting timeouts.** Creating `new RestTemplate()` without configuring `connectTimeout` and `readTimeout` means a slow or dead downstream service will block the calling thread indefinitely, exhausting your thread pool and bringing down your entire service. Always set both timeouts explicitly via `SimpleClientHttpRequestFactory`.

2. **Creating a new `RestTemplate` instance per request.** Instantiating `new RestTemplate()` inside a controller method or service method bypasses the KeepAlive connection cache — every call pays the full TCP handshake cost. RestTemplate should be a singleton `@Bean` created once and injected everywhere.

3. **Using `getForObject` when you need error details.** `getForObject` throws a `HttpClientErrorException` on 4xx/5xx but swallows the response headers and body. If you need the error response body for debugging or to pass upstream, use `getForEntity` or `exchange` and read the `ResponseEntity`.

4. **Hardcoding `localhost` and port numbers in the URL.** Microservice instances can scale horizontally or move. Hardcoded URLs break the moment you deploy more than one instance or containerise. The correct approach is to register services with a discovery server (Eureka) and use `FeignClient` or a load-balanced `RestTemplate` (annotated `@LoadBalanced`) with logical service names like `http://PRODUCT-SERVICE/product/{id}`.

5. **Confusing `exchange` and `execute`.** A common mistake is reaching for `execute` thinking it is "more powerful," then struggling with manual serialisation. In almost all real-world cases `exchange` is the right choice when you need header/method control — it still auto-serialises your request body and auto-deserialises the response. Only drop to `execute` if you have a very specific streaming or binary protocol need.