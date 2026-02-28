# Q1: How to Implement Interceptor in Spring Boot? (Interview Guide)

**Study Time:** 8-10 minutes | **Frequency:** 70% in Spring Boot interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## What Is an Interceptor?

### Definition

An **Interceptor** in Spring Boot is a component that **intercepts HTTP requests and responses** before they reach your controller and after they leave your controller.

```
HTTP Request
    ↓
Interceptor (preHandle)
    ↓
Controller Handler
    ↓
Interceptor (postHandle)
    ↓
HTTP Response
```

---

## Common Use Cases

| Use Case | Why Interceptors? |
|----------|------------------|
| **Authentication** | Check token/session before request reaches handler |
| **Logging** | Log request/response details |
| **CORS handling** | Add CORS headers |
| **Request/Response modification** | Add headers, modify attributes |
| **Performance monitoring** | Track request execution time |
| **Security** | Validate security headers |

---

## Wrong Approach: Not Using Interceptors

### ❌ WRONG Way - Code Duplication in Filters/Aspects

```java
@RestController
@RequestMapping("/api")
public class UserController {
    
    @PostMapping("/users")
    public ResponseEntity<?> createUser(@RequestBody User user) {
        // ❌ Repeated in EVERY endpoint
        String token = getTokenFromRequest();
        if (!isTokenValid(token)) {
            return ResponseEntity.status(401).body("Unauthorized");
        }
        
        // ❌ Repeated logging
        long startTime = System.currentTimeMillis();
        
        // Actual business logic
        User savedUser = userService.save(user);
        
        // ❌ Repeated response time logging
        long endTime = System.currentTimeMillis();
        logger.info("Request took: " + (endTime - startTime) + "ms");
        
        return ResponseEntity.ok(savedUser);
    }
    
    @GetMapping("/users/{id}")
    public ResponseEntity<?> getUser(@PathVariable Long id) {
        // ❌ Same authentication check duplicated
        String token = getTokenFromRequest();
        if (!isTokenValid(token)) {
            return ResponseEntity.status(401).body("Unauthorized");
        }
        
        // ❌ Same logging duplicated
        long startTime = System.currentTimeMillis();
        
        User user = userService.findById(id);
        
        long endTime = System.currentTimeMillis();
        logger.info("Request took: " + (endTime - startTime) + "ms");
        
        return ResponseEntity.ok(user);
    }
    
    // More endpoints... more duplication...
}
```

**Problems:**
- ❌ Code duplication in every endpoint
- ❌ Hard to maintain (change auth logic in 50 places)
- ❌ Easy to forget checks in new endpoints
- ❌ Mixing cross-cutting concerns with business logic

---

## ✅ RIGHT Approach: Using Interceptors

### Step 1: Create HandlerInterceptor Implementation

```java
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.ModelAndView;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

@Component
public class AuthenticationInterceptor implements HandlerInterceptor {
    
    private static final Logger logger = LoggerFactory.getLogger(AuthenticationInterceptor.class);
    
    /**
     * Called BEFORE the request reaches the controller
     * Return true to proceed, false to stop
     */
    @Override
    public boolean preHandle(HttpServletRequest request, 
                            HttpServletResponse response, 
                            Object handler) throws Exception {
        
        // Log incoming request
        logger.info("Incoming request: {} {}", request.getMethod(), request.getRequestURI());
        
        // Check authentication
        String token = request.getHeader("Authorization");
        if (token == null || token.isEmpty()) {
            logger.warn("No authorization token provided");
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.getWriter().write("Unauthorized: Missing token");
            return false;  // ← Stop request processing
        }
        
        // Validate token
        if (!isValidToken(token)) {
            logger.warn("Invalid token: {}", token);
            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.getWriter().write("Forbidden: Invalid token");
            return false;  // ← Stop request processing
        }
        
        // Store user info in request for later use
        String userId = extractUserIdFromToken(token);
        request.setAttribute("userId", userId);
        
        logger.info("Authentication successful for user: {}", userId);
        return true;  // ← Allow request to proceed
    }
    
    /**
     * Called AFTER the controller handler executes
     * Before view is rendered
     */
    @Override
    public void postHandle(HttpServletRequest request,
                          HttpServletResponse response,
                          Object handler,
                          ModelAndView modelAndView) throws Exception {
        
        String userId = (String) request.getAttribute("userId");
        logger.info("Response prepared for user: {}", userId);
        
        // Modify response if needed
        response.addHeader("X-Custom-Header", "Custom Value");
    }
    
    /**
     * Called AFTER response is sent to client
     * Good for cleanup, final logging
     */
    @Override
    public void afterCompletion(HttpServletRequest request,
                               HttpServletResponse response,
                               Object handler,
                               Exception ex) throws Exception {
        
        long requestTime = (long) request.getAttribute("startTime");
        long duration = System.currentTimeMillis() - requestTime;
        
        String userId = (String) request.getAttribute("userId");
        logger.info("Request completed for user: {} - Duration: {}ms", userId, duration);
        
        if (ex != null) {
            logger.error("Request failed with exception", ex);
        }
    }
    
    // Helper methods
    private boolean isValidToken(String token) {
        // Implement token validation logic
        return token.startsWith("Bearer ") && token.length() > 7;
    }
    
    private String extractUserIdFromToken(String token) {
        // Extract user ID from token
        return token.substring(7);  // Remove "Bearer " prefix
    }
}
```

---

### Step 2: Register Interceptor in Configuration

```java
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebMvcConfiguration implements WebMvcConfigurer {
    
    private final AuthenticationInterceptor authenticationInterceptor;
    
    // Constructor injection
    public WebMvcConfiguration(AuthenticationInterceptor authenticationInterceptor) {
        this.authenticationInterceptor = authenticationInterceptor;
    }
    
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(authenticationInterceptor)
            .addPathPatterns("/api/**")          // Apply to these paths
            .excludePathPatterns("/api/auth/**", "/api/public/**");  // Exclude public endpoints
    }
}
```

---

### Step 3: Use in Controller (Clean!)

```java
@RestController
@RequestMapping("/api")
public class UserController {
    
    @Autowired
    private UserService userService;
    
    @PostMapping("/users")
    public ResponseEntity<?> createUser(@RequestBody User user, 
                                       HttpServletRequest request) {
        // ✅ Authentication already handled by interceptor
        String userId = (String) request.getAttribute("userId");
        
        // ✅ No auth check needed, no logging code
        // Just business logic
        User savedUser = userService.save(user);
        
        return ResponseEntity.ok(savedUser);
    }
    
    @GetMapping("/users/{id}")
    public ResponseEntity<?> getUser(@PathVariable Long id,
                                    HttpServletRequest request) {
        // ✅ Already authenticated by interceptor
        String userId = (String) request.getAttribute("userId");
        
        User user = userService.findById(id);
        return ResponseEntity.ok(user);
    }
}
```

**Difference:**
- ✅ No auth check in controller
- ✅ No repeated logging
- ✅ Clean, focused on business logic

---

## Multiple Interceptors Example

You can register multiple interceptors that execute in order:

```java
@Configuration
public class WebMvcConfiguration implements WebMvcConfigurer {
    
    @Autowired
    private AuthenticationInterceptor authenticationInterceptor;
    
    @Autowired
    private LoggingInterceptor loggingInterceptor;
    
    @Autowired
    private PerformanceInterceptor performanceInterceptor;
    
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        // Execution order:
        registry.addInterceptor(loggingInterceptor)
            .addPathPatterns("/**");  // All paths
        
        registry.addInterceptor(authenticationInterceptor)
            .addPathPatterns("/api/**")
            .excludePathPatterns("/api/auth/**");
        
        registry.addInterceptor(performanceInterceptor)
            .addPathPatterns("/**");
    }
}
```

**Execution Order (preHandle):**
1. LoggingInterceptor.preHandle()
2. AuthenticationInterceptor.preHandle()
3. PerformanceInterceptor.preHandle()
4. → Controller Handler
5. PerformanceInterceptor.postHandle()
6. AuthenticationInterceptor.postHandle()
7. LoggingInterceptor.postHandle()

---

## Real-World Examples

### Example 1: Logging Interceptor

```java
@Component
public class LoggingInterceptor implements HandlerInterceptor {
    
    private static final Logger logger = LoggerFactory.getLogger(LoggingInterceptor.class);
    
    @Override
    public boolean preHandle(HttpServletRequest request, 
                            HttpServletResponse response, 
                            Object handler) throws Exception {
        
        request.setAttribute("startTime", System.currentTimeMillis());
        
        logger.info("→ {} {} from {}",
            request.getMethod(),
            request.getRequestURI(),
            request.getRemoteAddr()
        );
        
        return true;
    }
    
    @Override
    public void afterCompletion(HttpServletRequest request,
                               HttpServletResponse response,
                               Object handler,
                               Exception ex) throws Exception {
        
        long startTime = (long) request.getAttribute("startTime");
        long duration = System.currentTimeMillis() - startTime;
        
        logger.info("← {} {} [{}ms] Status: {}",
            request.getMethod(),
            request.getRequestURI(),
            duration,
            response.getStatus()
        );
    }
}
```

---

### Example 2: Performance Monitoring Interceptor

```java
@Component
public class PerformanceInterceptor implements HandlerInterceptor {
    
    @Autowired
    private MetricsService metricsService;
    
    @Override
    public boolean preHandle(HttpServletRequest request,
                            HttpServletResponse response,
                            Object handler) throws Exception {
        
        request.setAttribute("startTime", System.currentTimeMillis());
        return true;
    }
    
    @Override
    public void afterCompletion(HttpServletRequest request,
                               HttpServletResponse response,
                               Object handler,
                               Exception ex) throws Exception {
        
        long startTime = (long) request.getAttribute("startTime");
        long duration = System.currentTimeMillis() - startTime;
        
        String endpoint = request.getRequestURI();
        metricsService.recordLatency(endpoint, duration);
        
        // Alert if slow
        if (duration > 5000) {  // 5 seconds
            metricsService.recordSlowRequest(endpoint, duration);
        }
    }
}
```

---

### Example 3: CORS Interceptor

```java
@Component
public class CORSInterceptor implements HandlerInterceptor {
    
    @Override
    public boolean preHandle(HttpServletRequest request,
                            HttpServletResponse response,
                            Object handler) throws Exception {
        
        response.setHeader("Access-Control-Allow-Origin", "*");
        response.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
        response.setHeader("Access-Control-Allow-Headers", "Authorization, Content-Type");
        
        // Handle preflight requests
        if ("OPTIONS".equals(request.getMethod())) {
            response.setStatus(HttpServletResponse.SC_OK);
            return false;  // Don't proceed with actual request
        }
        
        return true;
    }
}
```

---

## Interceptor vs Filter vs AOP

### Comparison Table

| Aspect | Interceptor | Filter | AOP |
|--------|-------------|--------|-----|
| **Scope** | Spring MVC only | All servlets | All beans |
| **Access to** | HttpServletRequest/Response | HttpServletRequest/Response | Method arguments |
| **Best for** | HTTP-specific | Servlet pipeline | Business logic |
| **Exception handling** | Harder | Easier | Cleanest |
| **Order control** | Easy (registry) | Complex | Aspect order |
| **Modification** | Request/Response headers | Request/Response body | Arguments, return |

**When to use each:**
- **Interceptor:** Authentication, logging, headers
- **Filter:** Charset encoding, request encoding
- **AOP:** Business logic auditing, transaction management

---

## Interview Q&A

### Q1: "What's the difference between preHandle, postHandle, and afterCompletion?"

**Answer:**
```
preHandle:
  - Runs BEFORE controller handler
  - Return false to stop request
  - For authentication, validation
  
postHandle:
  - Runs AFTER controller but BEFORE response sent
  - Request completed successfully
  - For modifying model, adding headers
  - NOT called if controller throws exception

afterCompletion:
  - Runs AFTER response sent (cleanup phase)
  - ALWAYS called (even if exception)
  - For logging, cleanup resources
```

---

### Q2: "How do you exclude certain paths from interceptor?"

**Answer:**
```java
registry.addInterceptor(authInterceptor)
    .addPathPatterns("/api/**")
    .excludePathPatterns(
        "/api/auth/login",
        "/api/auth/register",
        "/api/public/**"
    );
```

---

### Q3: "Can interceptor handle exceptions?"

**Answer:**
```
Partially:
- preHandle: Can throw exceptions (caught by servlet)
- postHandle: Can throw exceptions
- afterCompletion: Has exception parameter (can check)

For exception handling, use @ControllerAdvice/@ExceptionHandler
which is designed for it.

Interceptor + ControllerAdvice together:
Interceptor → ControllerAdvice (cleaner)
```

---

### Q4: "What if you need interceptor to work with @Async methods?"

**Answer:**
```
Interceptor only works with synchronous requests.

For async, use:
1. AOP
2. WebAsyncManager in interceptor

Example:
@Override
public boolean preHandle(HttpServletRequest request, ...) {
    WebAsyncManager.from(request)
        .registerCallableInterceptor("myInterceptor", 
            new CallableProcessingInterceptor() { ... });
    return true;
}
```

---

## Complete Production-Ready Example

```java
// Step 1: Custom interceptor
@Component
public class ApiInterceptor implements HandlerInterceptor {
    
    private static final Logger logger = LoggerFactory.getLogger(ApiInterceptor.class);
    
    @Autowired
    private JwtTokenProvider tokenProvider;
    
    @Autowired
    private AuditService auditService;
    
    @Override
    public boolean preHandle(HttpServletRequest request,
                            HttpServletResponse response,
                            Object handler) throws Exception {
        
        // Timing
        request.setAttribute("startTime", System.currentTimeMillis());
        
        // Authentication
        String authHeader = request.getHeader("Authorization");
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7);
            if (tokenProvider.isValidToken(token)) {
                String userId = tokenProvider.getUserIdFromToken(token);
                request.setAttribute("userId", userId);
                return true;
            }
        }
        
        // Not authenticated
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        response.getWriter().write("Unauthorized");
        return false;
    }
    
    @Override
    public void afterCompletion(HttpServletRequest request,
                               HttpServletResponse response,
                               Object handler,
                               Exception ex) throws Exception {
        
        String userId = (String) request.getAttribute("userId");
        long startTime = (long) request.getAttribute("startTime");
        long duration = System.currentTimeMillis() - startTime;
        
        // Audit logging
        auditService.log(
            userId,
            request.getMethod(),
            request.getRequestURI(),
            response.getStatus(),
            duration
        );
        
        logger.info("Request: {} {} | User: {} | Status: {} | Time: {}ms",
            request.getMethod(),
            request.getRequestURI(),
            userId,
            response.getStatus(),
            duration
        );
    }
}

// Step 2: Register
@Configuration
public class SecurityConfiguration implements WebMvcConfigurer {
    
    @Autowired
    private ApiInterceptor apiInterceptor;
    
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(apiInterceptor)
            .addPathPatterns("/api/**")
            .excludePathPatterns("/api/auth/**");
    }
}

// Step 3: Use in controller
@RestController
@RequestMapping("/api/users")
public class UserController {
    
    @GetMapping("/{id}")
    public ResponseEntity<User> getUser(@PathVariable Long id,
                                       HttpServletRequest request) {
        String userId = (String) request.getAttribute("userId");
        User user = userService.findById(id);
        return ResponseEntity.ok(user);
    }
}
```

---

## Wrong vs Right Comparison

| Aspect | ❌ Wrong | ✅ Right |
|--------|---------|----------|
| **Code repetition** | Auth check in every endpoint | Interceptor handles once |
| **Separation of concerns** | Business + security mixed | Separated cleanly |
| **Maintenance** | Change auth in 50 places | Change in interceptor only |
| **New endpoints** | Easy to forget security | Automatic for matched patterns |
| **Exception handling** | Try-catch in each method | Interceptor + ControllerAdvice |
| **Cross-cutting logic** | Duplicated | Centralized |

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| **HandlerInterceptor interface** | Core knowledge | ⭐⭐⭐⭐⭐ |
| **Lifecycle (3 methods)** | Understanding flow | ⭐⭐⭐⭐⭐ |
| **WebMvcConfigurer registration** | Configuration | ⭐⭐⭐⭐ |
| **Path patterns** | Practical application | ⭐⭐⭐⭐ |
| **vs Filter vs AOP** | Design decisions | ⭐⭐⭐⭐ |
| **Authentication use case** | Common pattern | ⭐⭐⭐⭐⭐ |

