# RestClient in Spring Boot Microservices — Synchronous Communication

## What is this? (Plain English)

RestClient is Spring Boot's modern, cleaner way to call another service over HTTP. Think of it like ordering food through an app — you tap through a series of screens in a fixed order (where to order from, what to order, confirm) and you wait at the counter until the food is ready before you leave. RestClient works the same way: you chain steps in order to build your HTTP request, then your thread waits (blocks) until the other service responds. It was introduced in Spring Framework 6 and Spring Boot 3 as the recommended replacement for the older RestTemplate.

## The Problem It Solves

RestTemplate (the old way) had dozens of overloaded methods like `getForObject`, `getForEntity`, `postForObject`, `exchange` — you had to remember which method to use for which situation, and the signatures were inconsistent and hard to read. RestClient replaces all of that with one fluent, readable chain: `.get().uri(...).retrieve().body(...)`. It also adds built-in support for HTTP/2, which RestTemplate could never do.

## Architecture Diagram

```
  ┌────────────────────────────────────────────────────────────┐
  │                    Order Service (:8081)                   │
  │                                                            │
  │  ┌──────────────┐    ┌─────────────────────────────────┐  │
  │  │  Controller  │───▶│         RestClient Bean         │  │
  │  │  /order/{id} │    │  (created via RestClient.create │  │
  │  └──────────────┘    │   or .builder().build())        │  │
  │                      └───────────┬─────────────────────┘  │
  └──────────────────────────────────┼─────────────────────────┘
                                     │
                          HTTP Request│(synchronous — thread waits)
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │  JDK HttpClient (java.net.http) │
                    │  (supports HTTP/1.1 + HTTP/2)   │
                    └───────────────┬────────────────┘
                                    │  TCP Connection
                                    ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                   Product Service (:8082)                   │
  │                                                             │
  │  ┌──────────────────────────────────────────────────────┐  │
  │  │  REST Controller — returns product data as JSON/text │  │
  │  └──────────────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────────────┘
                                    │
                         HTTP Response (body)
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │        ResponseSpec            │
                    │  - onStatus() for errors       │
                    │  - body() / toEntity() mapping │
                    └───────────────────────────────┘
```

## Request Flow (Sequence)

```
Lanes:  OC = OrderController | RC = RestClient | RS = ResponseSpec | HC = JDK HttpClient | PS = Product Service

1)  OC ──────────────────────> RC : .get().uri(...).accept(...)
    note: request fields accumulated, NO network call yet
2)  RC ──────────────────────> RS : .retrieve()
    note: prepares error handlers, still NO network call
3)  OC ──────────────────────────────────────────────────> RS : .body(String.class)
4)          RS ──────────────> HC : fire actual HTTP request (thread blocks)
5)                  HC ──────────────────────────────────> PS : GET /products/{id}
6)                  PS ──────────────────────────────────> HC : 200 OK + JSON
7)          RS <────────────── HC : raw response
8)  OC <──────────────────────────────────────────────────RS : mapped response body
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## How It Works — Step by Step

1. **Create a RestClient bean** — call `RestClient.create()` (shorthand) or `RestClient.builder().build()` to get a RestClient object. This is typically a Spring bean created once and reused.

2. **Pick the HTTP method** — call `.get()`, `.post()`, `.put()`, or `.delete()` on the RestClient. Internally this creates a `DefaultRequestBodyUriSpec` object and sets the HTTP method on it.

3. **Set the URL** — chain `.uri("http://localhost:8082/products/1")`. This fills in the target address on the internal request object.

4. **Set headers (optional)** — chain `.accept(MediaType.APPLICATION_JSON)` or `.header("X-Custom", "value")` to add HTTP headers.

5. **Set the request body (POST/PUT only)** — chain `.contentType(MediaType.APPLICATION_JSON).body(myObject)` to attach a payload.

6. **Call retrieve()** — this returns a `ResponseSpec` object. No HTTP call has happened yet — this step just prepares the response-handling configuration.

7. **Register error handlers (optional)** — chain `.onStatus(response -> response.is4xxClientError(), ...)` on the ResponseSpec to define what exception to throw on 4xx or 5xx responses.

8. **Extract the body** — chain `.body(String.class)` or `.toEntity(MyDto.class)`. This is the step that actually fires the TCP connection, sends the HTTP request, waits for the response, maps the response body to your class, and returns the result. Your thread blocks here until the response arrives.

9. **Interceptors run automatically** — if you registered a `ClientHttpRequestInterceptor` when building the RestClient, it runs just before the TCP connection is made (between steps 6 and 8 internally), letting you modify or log the request.

## Key Code / Config

```java
// ---------- AppConfig.java ----------
@Configuration
public class AppConfig {

    // Create a single RestClient bean — reused across all requests
    // RestClient.create() is shorthand for RestClient.builder().build()
    @Bean
    public RestClient restClient() {
        return RestClient.builder()
                .requestInterceptor(new MyCustomRequestInterceptor()) // optional interceptor
                .build();
    }
}

// ---------- MyCustomRequestInterceptor.java ----------
@Component
public class MyCustomRequestInterceptor implements ClientHttpRequestInterceptor {

    @Override
    public ClientHttpResponse intercept(HttpRequest request, byte[] body,
                                        ClientHttpRequestExecution execution) throws IOException {
        // Intercept every outbound request — add a custom header before it goes out
        request.getHeaders().add("X-Custom-Header", "my-value");
        // MUST call proceed() or the request never actually gets sent
        return execution.execute(request, body);
    }
}

// ---------- OrderController.java ----------
@RestController
public class OrderController {

    @Autowired
    private RestClient restClient;

    @GetMapping("/order/{id}")
    public String getOrder(@PathVariable int id) {

        // Fluent chain — each method returns the next "step" object
        String response = restClient
                .get()                                              // Step 1: set HTTP method to GET
                .uri("http://localhost:8082/products/" + id)       // Step 2: set the target URL
                .accept(MediaType.APPLICATION_JSON)                // Step 3: set Accept header
                .retrieve()                                        // Step 4: prepare response handling (no HTTP call yet)
                .onStatus(                                         // Step 5: register error handlers
                    r -> r.is4xxClientError(),
                    (req, res) -> { throw new RuntimeException("Client error: " + res.getStatusCode()); }
                )
                .onStatus(
                    r -> r.is5xxServerError(),
                    (req, res) -> { throw new RuntimeException("Server error"); }
                )
                .body(String.class);                               // Step 6: THIS fires the actual HTTP call and maps response

        System.out.println("Response from product API: " + response);
        return "order call successful";
    }

    @PostMapping("/order")
    public String createOrder(@RequestBody MyOrderRequest order) {

        // POST example — body must be set before retrieve()
        String response = restClient
                .post()
                .uri("http://localhost:8082/products")
                .contentType(MediaType.APPLICATION_JSON)           // Tell server we are sending JSON
                .body(order)                                       // Attach the request payload
                .retrieve()
                .body(String.class);

        return response;
    }

    @GetMapping("/order/advanced/{id}")
    public String getOrderWithExchange(@PathVariable int id) {

        // Alternative: skip retrieve() and use exchange() directly for full control
        // Useful when you want to inspect raw request/response yourself
        String response = restClient
                .get()
                .uri("http://localhost:8082/products/" + id)
                .exchange((request, res) -> {                      // You own the mapping logic here
                    if (res.getStatusCode().is4xxClientError()) {
                        throw new RuntimeException("Bad request");
                    }
                    return new String(res.getBody().readAllBytes());
                });

        return response;
    }
}
```

## Important Concepts

- **Fluent API**: A coding style where each method returns an object that exposes the next set of valid methods — you chain calls like `.get().uri().retrieve().body()`. The chain enforces the correct order at compile time.
- **Method chaining**: Calling methods one after another on the return value of the previous call, where each method belongs to a potentially different class.
- **Synchronous / blocking**: The calling thread stops and waits until the remote service sends back a full response before moving on. Opposite of async/non-blocking.
- **WebClient**: Spring's async, non-blocking HTTP client — used in reactive (Spring WebFlux) applications. RestClient is the synchronous alternative for regular Spring MVC apps.
- **RestTemplate**: The older Spring HTTP client that RestClient replaces. Has many confusing overloaded methods and only supports HTTP/1.0 and HTTP/1.1.
- **RequestHeaderUriSpec**: Internal RestClient interface that exposes methods for setting the URI and headers.
- **RequestBodyUriSpec**: Internal RestClient interface that additionally exposes methods for setting a request body (needed for POST/PUT).
- **ResponseSpec**: Internal RestClient object returned by `.retrieve()`. Holds error-handler configuration and provides `.body()` / `.toEntity()` methods to trigger the actual HTTP call and map the response.
- **DefaultRequestBodyUriSpec**: The single concrete implementation class that implements all the above interfaces. It accumulates all the request details (URL, headers, body, method) as you chain methods, then fires the real request when you call `.body()` or `.toEntity()`.
- **ClientHttpRequestInterceptor**: An interface you implement to intercept every outbound HTTP request — useful for adding auth headers, logging, or request tracing.
- **JDK HttpClient (`java.net.http.HttpClient`)**: The underlying Java standard-library class that RestClient uses to open TCP connections and send HTTP requests. Supports both HTTP/1.1 and HTTP/2.
- **HTTP/2**: A newer HTTP protocol version that allows multiple concurrent requests and responses over one connection. RestClient supports it; RestTemplate does not.
- **`onStatus()`**: A method on `ResponseSpec` that registers a callback to throw a custom exception when the response status matches a condition (e.g., 4xx, 5xx).
- **`exchange()`**: A lower-level method that bypasses `ResponseSpec` entirely and lets you write your own request/response handling logic as a lambda.

## Interview Q&A

**Q1: What is RestClient and why was it introduced in Spring Boot 3?**
RestClient is a synchronous, fluent HTTP client introduced in Spring Framework 6 / Spring Boot 3 as the modern replacement for RestTemplate. RestTemplate had too many overloaded methods that were hard to remember and maintain. RestClient solves this with a single fluent chain that is readable, consistent, and easier to maintain. It also supports HTTP/2, which RestTemplate cannot.

**Q2: What does "fluent API" mean in the context of RestClient?**
A fluent API is a design where each method call returns an object that exposes the next valid set of operations, enabling method chaining. In RestClient, calling `.get()` returns a `RequestHeaderUriSpec`, calling `.uri()` on that returns a `RequestBodySpec`, calling `.retrieve()` on that returns a `ResponseSpec`, and calling `.body()` on that fires the actual HTTP request. Each step in the chain belongs to a different interface or class, and the compiler enforces that you can only call what makes sense next — you cannot call `.body()` before `.uri()`, for example, because `.body()` is not on the object returned by `.get()`.

**Q3: Why does the order of method calls in RestClient matter?**
Because RestClient is a fluent API, each method returns an object of a specific type that only exposes certain next methods. If you call `.accept()` (a header method) before `.uri()`, you get back a `RequestHeaderSpec` object that no longer has a `.uri()` method on it — the chain is broken and you can never set the URL. The correct sequence is: HTTP method → URI → headers/body → retrieve → body/toEntity.

**Q4: What is the difference between RestClient and WebClient?**
RestClient is synchronous and blocking — the calling thread waits until the remote service responds. It is the right choice for standard Spring MVC (servlet-based) applications. WebClient is asynchronous and non-blocking — the thread is not held while waiting, and it is designed for Spring WebFlux reactive applications. If you are not using reactive programming, prefer RestClient.

**Q5: Why does calling `.retrieve()` not actually send the HTTP request?**
`.retrieve()` just creates and returns a `ResponseSpec` object, which is a container for response-handling configuration (error handlers, response mappers). The actual TCP connection and HTTP request are triggered only when you call `.body()` or `.toEntity()` on the `ResponseSpec`. This design separates the "what should happen when the response arrives" configuration from the "actually go get the response" action.

**Q6: What happens if you call `.body()` and the server returns a 500 error — but you never registered an `.onStatus()` handler?**
By default, RestClient will throw a `RestClientResponseException` (specifically `HttpServerErrorException` for 5xx) with the status code and the raw response body. If you want to throw your own custom exception (e.g., a domain-specific error), you must explicitly register an `.onStatus()` handler that catches 5xx responses and throws your exception. Without it you still get an exception, just a generic Spring one.

**Q7: How do you add a request interceptor to RestClient, and at what point in the flow does it run?**
You implement the `ClientHttpRequestInterceptor` interface, override its `intercept()` method to modify the request (add headers, log, etc.), and register it on the builder: `RestClient.builder().requestInterceptor(new MyInterceptor()).build()`. The interceptor runs inside the `execute()` step — after all request fields (URI, headers, body) have been assembled into the `DefaultRequestBodyUriSpec`, but just before the JDK `HttpClient` opens the TCP connection. You must call `execution.execute(request, body)` inside the interceptor or the request will never be sent.

**Q8: What internal HTTP client does RestClient use, and what advantage does that bring over RestTemplate?**
RestClient uses `java.net.http.HttpClient` (from the JDK standard library via `JdkClientHttpRequestFactory`). This client supports HTTP/2, which allows multiple concurrent HTTP requests and responses over a single TCP connection, reducing overhead and improving throughput. RestTemplate used older Apache HttpClient or `HttpURLConnection` and was limited to HTTP/1.0 and HTTP/1.1.

## Common Mistakes

1. **Calling header/accept methods before URI and then trying to set URI afterward.** Once you call `.accept()` or `.header()` on the `RequestHeaderUriSpec`, the chain returns a `RequestHeaderSpec` that no longer exposes `.uri()`. You lose the ability to set the URL. Always set `.uri()` first, before any headers.

2. **Forgetting to call `.body()` or `.toEntity()` and wondering why no HTTP request is made.** Neither `RestClient.get()` nor `.retrieve()` actually sends anything. The HTTP request is fired only when you call the terminal method (`.body()`, `.toEntity()`). Logging or debugging "before .body()" shows no network traffic at all.

3. **Creating a new RestClient instance per request instead of using a singleton bean.** `RestClient.create()` is not cheap — it initialises an `HttpClient`, connection pools, and factories. It should be created once as a `@Bean` and injected everywhere via `@Autowired`. Creating it per request leaks resources and is much slower.

4. **Not registering `.onStatus()` handlers and letting generic Spring exceptions bubble up to the caller.** In a microservices context, a product service returning a 404 should ideally throw a meaningful `ProductNotFoundException`, not a generic `HttpClientErrorException.NotFound`. Always register `.onStatus()` to translate HTTP error codes into domain-specific exceptions so callers can handle them cleanly.

5. **Using RestClient in a Spring WebFlux (reactive) application.** RestClient is blocking — it holds a thread while waiting for the response. In a reactive app built on WebFlux (which uses a tiny thread pool and expects non-blocking code), using RestClient blocks one of those precious threads and can cause the entire application to stall under load. Use WebClient in reactive applications instead.