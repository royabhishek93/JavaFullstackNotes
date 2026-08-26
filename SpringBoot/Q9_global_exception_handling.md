# Q9: @ControllerAdvice & Global Exception Handling — RFC 7807, Validation, Async (Architect Guide)

**Study Time:** 15-20 minutes | **Frequency:** 90% in architect interviews 🔥🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## Why This Matters in Production

Without global exception handling:
- Stack traces leak to clients (security vulnerability)
- Each controller duplicates try-catch blocks
- Error response format is inconsistent — breaks API consumers
- Validation errors return 500 instead of 400
- Unhandled exceptions crash the request thread

---

## The Problem: Without Global Handling

```java
// Without @ControllerAdvice — every controller handles its own errors
@RestController
public class OrderController {

    @GetMapping("/orders/{id}")
    public Order getOrder(@PathVariable Long id) {
        Order order = orderService.findById(id);
        if (order == null) throw new RuntimeException("Not found"); // returns 500 ❌
        return order;
    }

    @PostMapping("/orders")
    public Order createOrder(@RequestBody Order order) {
        try {
            return orderService.create(order);
        } catch (Exception e) {
            // What do you return? How? Repeated in every controller ❌
            throw e;
        }
    }
}
```

---

## @ControllerAdvice — The Solution

```
HTTP Request → Controller → throws Exception
                                ↓
                        ExceptionHandlerExceptionResolver
                                ↓
                        finds matching @ExceptionHandler in @ControllerAdvice
                                ↓
                        returns structured error response
```

### Basic Structure

```java
@RestControllerAdvice  // = @ControllerAdvice + @ResponseBody
public class GlobalExceptionHandler {

    // Handles specific exception type
    @ExceptionHandler(ResourceNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ErrorResponse handleNotFound(ResourceNotFoundException ex, HttpServletRequest request) {
        return ErrorResponse.of(404, ex.getMessage(), request.getRequestURI());
    }

    // Handles validation failures
    @ExceptionHandler(MethodArgumentNotValidException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ValidationErrorResponse handleValidation(MethodArgumentNotValidException ex) {
        List<FieldError> errors = ex.getBindingResult().getFieldErrors().stream()
            .map(fe -> new FieldError(fe.getField(), fe.getDefaultMessage()))
            .collect(Collectors.toList());
        return new ValidationErrorResponse(400, "Validation failed", errors);
    }

    // Catch-all — last resort
    @ExceptionHandler(Exception.class)
    @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
    public ErrorResponse handleAll(Exception ex, HttpServletRequest request) {
        log.error("Unhandled exception for {}: {}", request.getRequestURI(), ex.getMessage(), ex);
        // Never expose internal details to client
        return ErrorResponse.of(500, "An unexpected error occurred", request.getRequestURI());
    }
}
```

---

## RFC 7807 — Problem Details (Industry Standard Error Format)

Spring Boot 3.x ships with RFC 7807 support via `ProblemDetail`. Use it — it's what mature APIs return.

### ProblemDetail Structure

```json
{
  "type": "https://api.example.com/errors/order-not-found",
  "title": "Order Not Found",
  "status": 404,
  "detail": "Order with id 12345 does not exist",
  "instance": "/orders/12345",
  "timestamp": "2026-08-21T10:30:00Z",
  "traceId": "abc123def456"
}
```

### Implementation with ProblemDetail (Spring Boot 3.x)

```java
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ProblemDetail handleNotFound(ResourceNotFoundException ex, HttpServletRequest request) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setTitle("Resource Not Found");
        problem.setType(URI.create("https://api.example.com/errors/not-found"));
        problem.setInstance(URI.create(request.getRequestURI()));
        problem.setProperty("timestamp", Instant.now());
        problem.setProperty("traceId", MDC.get("traceId")); // from distributed tracing
        return problem;
    }

    @ExceptionHandler(BusinessRuleViolationException.class)
    public ProblemDetail handleBusinessRule(BusinessRuleViolationException ex, HttpServletRequest request) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.UNPROCESSABLE_ENTITY, ex.getMessage());
        problem.setTitle("Business Rule Violation");
        problem.setType(URI.create("https://api.example.com/errors/business-rule"));
        problem.setProperty("errorCode", ex.getErrorCode());
        problem.setProperty("timestamp", Instant.now());
        return problem;
    }
}

// Enable in application.yml (Spring Boot 3.x):
// spring.mvc.problemdetails.enabled=true
```

---

## Custom Exception Hierarchy

```java
// Base exception — all app exceptions extend this
public abstract class AppException extends RuntimeException {
    private final String errorCode;
    private final HttpStatus httpStatus;

    protected AppException(String message, String errorCode, HttpStatus httpStatus) {
        super(message);
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
    }

    // getters...
}

// Domain exceptions
public class ResourceNotFoundException extends AppException {
    public ResourceNotFoundException(String resource, Object id) {
        super(resource + " not found with id: " + id, "RESOURCE_NOT_FOUND", HttpStatus.NOT_FOUND);
    }
}

public class DuplicateResourceException extends AppException {
    public DuplicateResourceException(String resource, String field, Object value) {
        super(resource + " already exists with " + field + ": " + value,
              "DUPLICATE_RESOURCE", HttpStatus.CONFLICT);
    }
}

public class BusinessRuleViolationException extends AppException {
    public BusinessRuleViolationException(String message, String errorCode) {
        super(message, errorCode, HttpStatus.UNPROCESSABLE_ENTITY);
    }
}

public class InsufficientStockException extends BusinessRuleViolationException {
    public InsufficientStockException(Long productId, int requested, int available) {
        super("Insufficient stock for product " + productId
              + ". Requested: " + requested + ", Available: " + available,
              "INSUFFICIENT_STOCK");
    }
}

// Handler — handles all AppException subclasses in one method
@ExceptionHandler(AppException.class)
public ResponseEntity<ProblemDetail> handleAppException(AppException ex, HttpServletRequest request) {
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(ex.getHttpStatus(), ex.getMessage());
    problem.setProperty("errorCode", ex.getErrorCode());
    problem.setProperty("timestamp", Instant.now());
    problem.setInstance(URI.create(request.getRequestURI()));
    return ResponseEntity.status(ex.getHttpStatus()).body(problem);
}
```

---

## Validation Error Handling

```java
// Bean validation on request body
@PostMapping("/orders")
public ResponseEntity<Order> createOrder(@Valid @RequestBody CreateOrderRequest request) {
    // @Valid triggers validation before method body runs
    return ResponseEntity.status(201).body(orderService.create(request));
}

// Request DTO with validation annotations
public class CreateOrderRequest {
    @NotNull(message = "Product ID is required")
    private Long productId;

    @Min(value = 1, message = "Quantity must be at least 1")
    @Max(value = 1000, message = "Quantity cannot exceed 1000")
    private Integer quantity;

    @NotBlank(message = "Delivery address is required")
    @Size(max = 500, message = "Address too long")
    private String deliveryAddress;
}

// Global handler — clean field-level error response
@ExceptionHandler(MethodArgumentNotValidException.class)
@ResponseStatus(HttpStatus.BAD_REQUEST)
public ProblemDetail handleValidationErrors(MethodArgumentNotValidException ex) {
    ProblemDetail problem = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
    problem.setTitle("Validation Failed");
    problem.setDetail("One or more fields failed validation");

    Map<String, List<String>> fieldErrors = ex.getBindingResult()
        .getFieldErrors()
        .stream()
        .collect(Collectors.groupingBy(
            FieldError::getField,
            Collectors.mapping(FieldError::getDefaultMessage, Collectors.toList())
        ));

    problem.setProperty("fieldErrors", fieldErrors);
    problem.setProperty("timestamp", Instant.now());
    return problem;
}

// Response example:
// {
//   "title": "Validation Failed",
//   "status": 400,
//   "fieldErrors": {
//     "productId": ["Product ID is required"],
//     "quantity": ["Quantity must be at least 1"]
//   }
// }
```

---

## Exception Handler Priority & Specificity

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    // Most specific — handles only this exception type
    @ExceptionHandler(InsufficientStockException.class)
    public ProblemDetail handleInsufficientStock(InsufficientStockException ex) { ... }

    // Handles parent — catches InsufficientStockException too IF above not present
    @ExceptionHandler(BusinessRuleViolationException.class)
    public ProblemDetail handleBusinessRule(BusinessRuleViolationException ex) { ... }

    // Handles all AppExceptions including above
    @ExceptionHandler(AppException.class)
    public ProblemDetail handleApp(AppException ex) { ... }

    // Catch-all — only if no specific handler matches
    @ExceptionHandler(Exception.class)
    public ProblemDetail handleAll(Exception ex) { ... }
}
```

Spring picks the **most specific** handler. `InsufficientStockException` → matches `InsufficientStockException` handler first.

---

## Handling Exceptions in WebFlux (Reactive)

```java
// WebFlux uses @ControllerAdvice too, but returns Mono<ResponseEntity>
@RestControllerAdvice
public class ReactiveGlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public Mono<ResponseEntity<ProblemDetail>> handleNotFound(ResourceNotFoundException ex,
                                                               ServerHttpRequest request) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setInstance(request.getURI());
        return Mono.just(ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem));
    }
}

// Inside reactive pipeline — handle inline
orderRepository.findById(id)
    .switchIfEmpty(Mono.error(new ResourceNotFoundException("Order", id)))
    .onErrorMap(DataAccessException.class,
                ex -> new AppException("Database error", "DB_ERROR", HttpStatus.SERVICE_UNAVAILABLE))
    .onErrorReturn(TimeoutException.class,
                   Order.empty()); // fallback value for timeouts
```

---

## Logging Best Practices in Exception Handlers

```java
@ExceptionHandler(AppException.class)
public ResponseEntity<ProblemDetail> handleApp(AppException ex, HttpServletRequest request) {
    // Business exceptions: WARN (expected, not a bug)
    log.warn("Business rule violation [{}] on {}: {}",
             ex.getErrorCode(), request.getRequestURI(), ex.getMessage());
    // ...
}

@ExceptionHandler(Exception.class)
public ResponseEntity<ProblemDetail> handleAll(Exception ex, HttpServletRequest request) {
    // Unexpected exceptions: ERROR with full stack trace
    log.error("Unexpected error on {} [traceId={}]: {}",
              request.getRequestURI(), MDC.get("traceId"), ex.getMessage(), ex);
    // Never expose stack trace to client — log it, return generic message
    ProblemDetail problem = ProblemDetail.forStatusAndDetail(
        HttpStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred");
    problem.setProperty("traceId", MDC.get("traceId")); // let client reference it in support
    return ResponseEntity.internalServerError().body(problem);
}
```

---

## @ExceptionHandler in Controller vs @ControllerAdvice

```java
// Local handler — only for this controller, takes priority over global
@RestController
public class PaymentController {

    // Handles only in PaymentController context
    @ExceptionHandler(PaymentDeclinedException.class)
    public ProblemDetail handleDeclined(PaymentDeclinedException ex) {
        // Payment-specific response with retry hint
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(
            HttpStatus.PAYMENT_REQUIRED, ex.getMessage());
        problem.setProperty("retryAfter", ex.getRetryAfterSeconds());
        return problem;
    }
}
```

**Priority:** local `@ExceptionHandler` in controller → `@ControllerAdvice` (most specific match) → catch-all.

---

## Interview Cheat Sheet

```
@RestControllerAdvice = @ControllerAdvice + @ResponseBody
  → catches exceptions from ALL @RestController methods globally

Handler priority (most to least specific):
  Local @ExceptionHandler in controller
  → @ControllerAdvice handler for exact exception type
  → @ControllerAdvice handler for parent exception type
  → catch-all @ExceptionHandler(Exception.class)

RFC 7807 ProblemDetail (Spring Boot 3.x):
  type, title, status, detail, instance + custom properties
  Enable: spring.mvc.problemdetails.enabled=true

Validation exceptions:
  MethodArgumentNotValidException → @Valid on @RequestBody
  ConstraintViolationException   → @Validated on @PathVariable/@RequestParam

Never expose:
  - Stack traces to client (log them, return traceId)
  - Internal class names or DB error messages

Business exceptions → log.warn (expected)
Unexpected exceptions → log.error with full stack trace
```

---

## Key Architect Questions

**Q: What's the difference between @ControllerAdvice and @RestControllerAdvice?**
`@RestControllerAdvice` = `@ControllerAdvice` + `@ResponseBody`. It automatically serialises return values to JSON. Use `@RestControllerAdvice` for REST APIs.

**Q: Can you scope @ControllerAdvice to specific packages or controllers?**
Yes: `@ControllerAdvice(basePackages = "com.example.orders")` or `@ControllerAdvice(assignableTypes = {OrderController.class, PaymentController.class})`.

**Q: What happens if two @ControllerAdvice beans both handle the same exception?**
Undefined order unless `@Order` is used. Best practice: one global `@ControllerAdvice` per app. Use `@Order(1)` for higher priority.

**Q: How do you handle exceptions that occur in filters (before controller)?**
`@ControllerAdvice` doesn't catch filter exceptions — they happen outside the DispatcherServlet. Use a custom `OncePerRequestFilter` with try-catch, or implement `ErrorController` (`/error` endpoint mapping).

**Q: How does exception handling work in @Async methods with @ControllerAdvice?**
It doesn't — `@ControllerAdvice` only handles exceptions on the HTTP request thread. Async method exceptions must be handled via `AsyncUncaughtExceptionHandler` (see Q6).

**Q: What is RFC 7807 and why should you use it?**
RFC 7807 "Problem Details for HTTP APIs" defines a standard JSON error format (type, title, status, detail, instance). Using it means API consumers, monitoring tools, and API gateways all understand your error format without custom parsing.
