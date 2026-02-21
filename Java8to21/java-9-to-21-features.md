# Java 9 to Java 21 Features for Interview 2026

## Overview
This guide covers the most important Java features from Java 9 to Java 21, organized by priority and use case in production environments.

---

## 📊 Priority Summary Table

| Priority | Feature | Java Version | Use Case | Interview Importance |
|----------|---------|--------------|----------|----------------------|
| 🔥 MUST KNOW | Sealed Classes | 17 | Enforce controlled inheritance | Very High |
| 🔥 MUST KNOW | Pattern Matching (instanceof) | 16/17 | Clean type-check & casting | Very High |
| 🔥 MUST KNOW | New HttpClient API | 11 | REST calls, async APIs | Very High |
| ✅ SHOULD KNOW | Records | 14/17 | DTOs, immutable data | High |
| ✅ SHOULD KNOW | Text Blocks | 15/17 | Multiline SQL/JSON | High |
| ✅ SHOULD KNOW | TLS 1.3 Support | 11 | Secure communication | Medium |
| ✅ SHOULD KNOW | Local Variable Type (var) | 10 | Cleaner declarations | Medium |
| 👍 GOOD TO KNOW | Single-File Scripts | 11 | DevOps automation | Medium |
| 👍 GOOD TO KNOW | SecurityManager Deprecated | 17 | Container-level security | Low-Medium |
| 👍 GOOD TO KNOW | Helpful NullPointerExceptions | 14 | Better debugging | Low-Medium |
| ⚙️ NICHE | Epsilon GC | 11 | Performance benchmarking | Low |
| ⚙️ NICHE | ZGC/Shenandoah GC | 17 | Low-latency systems | Low |

---

## 🔥 MUST KNOW FEATURES (Production Critical)

### 1. Sealed Classes (Java 17)

**What:** Restrict which classes can extend or implement a class/interface.

**Purpose:** Enforce domain control over inheritance hierarchy. Prevents unwanted or malicious subclassing in sensitive domains.

**When to Use:**
- API design to control extension points
- Domain models (Payment, Event, Status types)
- SDKs and libraries
- Microservices APIs

**Example:**

```java
// Define permitted subclasses
public sealed class Vehicle permits Car, Truck, Motorcycle {
    public abstract void drive();
}

// Subclass must declare its inheritance strategy
public final class Car extends Vehicle {
    @Override
    public void drive() {
        System.out.println("Car driving");
    }
}

public final class Truck extends Vehicle {
    @Override
    public void drive() {
        System.out.println("Truck driving");
    }
}

// Non-sealed allows further extension
public non-sealed class CustomVehicle extends Vehicle {
    @Override
    public void drive() {
        System.out.println("Custom vehicle");
    }
}

// This will FAIL - not in permits list
// public class Bus extends Vehicle {} // ❌ Compiler Error
```

**Benefits:**
- ✅ Compile-time safety on inheritance hierarchy
- ✅ Better pattern matching with sealed types
- ✅ Defense against unknown subclasses in security-critical code
- ✅ Makes API contracts explicit

**Interview Ready Explanation:**
"Sealed classes let us control which classes can extend ours. We list permitted subclasses, and each subclass must declare if it's final (no more extension), sealed (limited extension), or non-sealed (open for all). This is useful in APIs where we want controlled extension points."

---

### 2. Pattern Matching for instanceof (Java 16/17)

**What:** Combine type-check and casting in one expression.

**Purpose:** Reduce boilerplate, improve code readability, and enable cleaner conditional logic.

**When to Use:**
- Multiple type checking (if-else chains)
- Visitor pattern implementations
- REST controller logic
- Domain model validation

**Before (Java 10):**

```java
Object obj = "Hello World";

// ❌ Old way: check then cast
if (obj instanceof String) {
    String s = (String) obj;  // Redundant casting
    System.out.println(s.toLowerCase());
}
```

**After (Java 16+):**

```java
Object obj = "Hello World";

// ✅ New way: check and cast in one go
if (obj instanceof String s) {
    System.out.println(s.toLowerCase());  // 's' is already String
}
```

**Advanced Example - Multiple Type Checking:**

```java
public class PaymentProcessor {
    
    // Old way (verbose)
    public BigDecimal getProcessingFee_Old(Payment payment) {
        if (payment instanceof CreditCardPayment) {
            CreditCardPayment cc = (CreditCardPayment) payment;
            return BigDecimal.valueOf(cc.getAmount() * 0.025);
        } else if (payment instanceof PayPalPayment) {
            PayPalPayment pp = (PayPalPayment) payment;
            return BigDecimal.valueOf(pp.getAmount() * 0.035);
        } else if (payment instanceof CryptoPayment) {
            CryptoPayment cp = (CryptoPayment) payment;
            return BigDecimal.valueOf(cp.getAmount() * 0.001);
        }
        return BigDecimal.ZERO;
    }

    // New way with pattern matching (cleaner!)
    public BigDecimal getProcessingFee_New(Payment payment) {
        return switch (payment) {
            case CreditCardPayment cc -> BigDecimal.valueOf(cc.getAmount() * 0.025);
            case PayPalPayment pp -> BigDecimal.valueOf(pp.getAmount() * 0.035);
            case CryptoPayment cp -> BigDecimal.valueOf(cp.getAmount() * 0.001);
            default -> BigDecimal.ZERO;
        };
    }
}
```

**Pattern Matching with Conditions (Java 17):**

```java
public String analyzeObject(Object obj) {
    // Pattern matching with guard condition
    if (obj instanceof String s && s.length() > 5) {
        return "Long string: " + s;
    }
    
    if (obj instanceof Integer i && i > 100) {
        return "Large number: " + i;
    }
    
    return "Other type";
}
```

**Benefits:**
- ✅ Less boilerplate code
- ✅ Improved readability
- ✅ Reduced casting errors
- ✅ Works with sealed classes for exhaustive checking

**Interview Ready Explanation:**
"Pattern matching for instanceof combines type-checking and casting in one line. Instead of checking `instanceof String` then casting to String, we declare the variable directly in the condition: `if (obj instanceof String s)`. The variable `s` is automatically scoped and typed within that block."

---

### 3. New HttpClient API (Java 11)

**What:** Modern, async HTTP client replacing deprecated HttpURLConnection.

**Purpose:** Simplify HTTP calls in microservices, 3rd-party integrations, and async operations.

**When to Use:**
- REST API calls to external services
- Microservices communication
- Async HTTP workflows
- WebSocket connections

**Synchronous Request:**

```java
HttpClient client = HttpClient.newHttpClient();

HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com/users/123"))
    .header("Accept", "application/json")
    .header("Authorization", "Bearer token123")
    .GET()
    .build();

HttpResponse<String> response = client.send(request, 
    HttpResponse.BodyHandlers.ofString());

System.out.println("Status: " + response.statusCode());
System.out.println("Body: " + response.body());
```

**Asynchronous Request:**

```java
HttpClient client = HttpClient.newHttpClient();

HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com/users"))
    .POST(HttpRequest.BodyPublishers.ofString("""
        {
            "name": "John",
            "email": "john@example.com"
        }
        """))
    .header("Content-Type", "application/json")
    .build();

// Async call returns CompletableFuture
client.sendAsync(request, HttpResponse.BodyHandlers.ofString())
    .thenApply(HttpResponse::statusCode)
    .thenAccept(status -> System.out.println("Status: " + status))
    .exceptionally(ex -> {
        System.err.println("Error: " + ex.getMessage());
        return null;
    });
```

**Production Example - Microservice Call:**

```java
@Service
public class PaymentService {
    
    private final HttpClient httpClient = HttpClient.newHttpClient();
    
    public CompletableFuture<PaymentResponse> validatePayment(String orderId) {
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("https://payment-gateway.com/validate/" + orderId))
            .timeout(Duration.ofSeconds(5))
            .GET()
            .build();
        
        return httpClient.sendAsync(request, 
                HttpResponse.BodyHandlers.ofString())
            .thenApply(response -> {
                if (response.statusCode() == 200) {
                    return parsePaymentResponse(response.body());
                }
                throw new PaymentGatewayException("Validation failed");
            });
    }
}
```

**Benefits:**
- ✅ Async/await pattern support (CompletableFuture)
- ✅ HTTP/2 and HTTP/1.1 support (automatic)
- ✅ Connection pooling
- ✅ Timeout handling
- ✅ Cleaner API than HttpURLConnection

**Interview Ready Explanation:**
"Java 11 introduced HttpClient to replace HttpURLConnection. It supports both sync and async calls, built-in connection pooling, timeouts, and automatic HTTP/2 negotiation. We use `send()` for blocking calls and `sendAsync()` for non-blocking CompletableFuture-based operations."

---

## ✅ SHOULD KNOW FEATURES (High Priority)

### 4. Records (Java 14/17)

**What:** Concise syntax for immutable data transfer objects.

**Purpose:** Reduce boilerplate for DTOs, avoiding manual getters, setters, equals, hashCode, and toString.

**When to Use:**
- REST API request/response DTOs
- Kafka message payloads
- Database query projections
- Event objects in event streaming
- Configuration objects

**Problem Without Records:**

```java
// ❌ Verbose POJO - lots of boilerplate
public class UserDto {
    private final String name;
    private final int age;
    private final String email;
    
    public UserDto(String name, int age, String email) {
        this.name = name;
        this.age = age;
        this.email = email;
    }
    
    public String getName() { return name; }
    public int getAge() { return age; }
    public String getEmail() { return email; }
    
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        UserDto userDto = (UserDto) o;
        return age == userDto.age && 
               name.equals(userDto.name) && 
               email.equals(userDto.email);
    }
    
    @Override
    public int hashCode() {
        return Objects.hash(name, age, email);
    }
    
    @Override
    public String toString() {
        return "UserDto{" +
                "name='" + name + '\'' +
                ", age=" + age +
                ", email='" + email + '\'' +
                '}';
    }
}
```

**Solution With Records:**

```java
// ✅ Clean and concise
public record UserDto(String name, int age, String email) {}

// That's it! Auto-generates:
// - Constructor(String, int, String)
// - Getters: name(), age(), email()
// - equals(Object)
// - hashCode()
// - toString()
```

**REST API Example:**

```java
// Request DTO
public record CreateUserRequest(
    String name,
    int age,
    String email
) {}

// Response DTO
public record UserResponse(
    Long id,
    String name,
    int age,
    String email
) {}

@RestController
@RequestMapping("/api/users")
public class UserController {
    
    @PostMapping
    public UserResponse createUser(@RequestBody CreateUserRequest request) {
        // request.name(), request.age(), request.email() directly available
        User user = new User(request.name(), request.age(), request.email());
        User saved = userService.save(user);
        
        return new UserResponse(saved.getId(), saved.getName(), 
                               saved.getAge(), saved.getEmail());
    }
}
```

**Database Projection Example:**

```java
public record UserProjection(Long id, String name, String email) {}

@Repository
public interface UserRepository extends JpaRepository<User, Long> {
    
    // Spring automatically maps to record constructor
    @Query("SELECT new com.example.UserProjection(u.id, u.name, u.email) FROM User u")
    List<UserProjection> findAllProjections();
}
```

**Immutability Note - Defensive Copying:**

```java
// Record with mutable fields - need defensive copies
public record EmployeeRecord(
    int id,
    String name,
    double[] salaries,
    List<String> projects
) {
    // Compact constructor for validation/defensive copying
    public EmployeeRecord {
        salaries = Arrays.copyOf(salaries, salaries.length);
        projects = List.copyOf(projects);  // Immutable copy
    }
}

// Usage
double[] mutableArray = {10000, 20000};
var emp = new EmployeeRecord(1, "Alice", mutableArray, List.of("Java", "Spring"));

// Modifying original array doesn't affect record
mutableArray[0] = 99999;
System.out.println(emp.salaries()[0]); // Still 10000 ✅
```

**Benefits:**
- ✅ 80% less code than traditional POJOs
- ✅ Immutable by design
- ✅ Automatic equals/hashCode/toString
- ✅ Pattern matching compatible
- ✅ Perfect for DTOs and domain objects

**Limitations:**
- ❌ No setters (immutable)
- ❌ No no-arg constructor (must provide all fields)
- ❌ Limited JPA support (JPA 3.1+)
- ❌ Shallow immutability (inner objects need defensive copies)

**Interview Ready Explanation:**
"Records are immutable data containers that auto-generate constructors, getters, equals, hashCode, and toString. We use them for DTOs, Kafka messages, and database projections. Instead of writing 50 lines of boilerplate, a record does it in one line. The trade-off is immutability - no setters."

---

### 5. Text Blocks (Java 15/17)

**What:** Multiline string literals using triple quotes (""").

**Purpose:** Cleaner code for SQL queries, JSON, HTML, and formatted text.

**When to Use:**
- SQL queries in code
- JSON/XML payloads
- HTML templates
- API documentation in code
- Formatted error messages

**Before (Java 14):**

```java
// ❌ Messy string concatenation
String query = "SELECT id, name, email FROM users " +
               "WHERE status = 'ACTIVE' " +
               "AND created_date > '2024-01-01' " +
               "ORDER BY name ASC";

// ❌ Or with escape characters
String json = "{\"name\":\"John\",\"age\":30,\"email\":\"john@example.com\"}";

// ❌ Formatted text requires manual newlines
String html = "<html>\n" +
              "  <body>\n" +
              "    <h1>Welcome</h1>\n" +
              "  </body>\n" +
              "</html>";
```

**After (Java 15+):**

```java
// ✅ Clean and readable
String query = """
    SELECT id, name, email FROM users
    WHERE status = 'ACTIVE'
    AND created_date > '2024-01-01'
    ORDER BY name ASC
    """;

// ✅ JSON is readable
String json = """
    {
        "name": "John",
        "age": 30,
        "email": "john@example.com"
    }
    """;

// ✅ HTML template
String html = """
    <html>
        <body>
            <h1>Welcome</h1>
            <p>This is a test page</p>
        </body>
    </html>
    """;
```

**Production Example - Database Query:**

```java
@Repository
public class ReportService {
    
    private final JdbcTemplate jdbc;
    
    public List<Map<String, Object>> generateMonthlyReport(int month) {
        String query = """
            SELECT 
                DATE_FORMAT(order_date, '%Y-%m-%d') as order_date,
                SUM(amount) as total_amount,
                COUNT(*) as order_count,
                AVG(amount) as avg_amount
            FROM orders
            WHERE MONTH(order_date) = ?
            AND status IN ('COMPLETED', 'SHIPPED')
            GROUP BY DATE_FORMAT(order_date, '%Y-%m-%d')
            ORDER BY order_date DESC
            """;
        
        return jdbc.queryForList(query, month);
    }
}
```

**String Interpolation (Java 21 Preview - String Templates):**

```java
// Java 21 preview feature
String name = "Alice";
int age = 30;

// Old way
String message = "Name: " + name + ", Age: " + age;

// New way (multi-line)
String profile = """
    User Profile:
    Name: \{name}
    Age: \{age}
    Status: Active
    """;
```

**Benefits:**
- ✅ Preserves formatting
- ✅ No escape characters
- ✅ Easy to read/modify
- ✅ Automatic indentation handling

**Interview Ready Explanation:**
"Text blocks use triple quotes for multiline strings. They preserve formatting exactly as written, so SQL queries, JSON, and HTML are readable without concatenation or escape characters. Great for embedded queries and API payloads."

---

### 6. Local Variable Type Inference - var (Java 10+)

**What:** Use `var` keyword for local variable type inference.

**Purpose:** Reduce verbosity while maintaining type safety through compiler inference.

**When to Use:**
- Complex generic types
- Stream operations
- Builder patterns
- Loop variables
- Local-scope variables only

**Example Comparison:**

```java
// ❌ Before: verbose generic types
Map<String, List<String>> userGroups = new HashMap<>();
List<String> names = new ArrayList<>();
Set<Integer> ids = new HashSet<>();

// ✅ After: using var
var userGroups = new HashMap<String, List<String>>();
var names = new ArrayList<String>();
var ids = new HashSet<Integer>();
```

**Real-World Stream Example:**

```java
// ❌ Old way
List<UserDto> activeUsers = userRepository.findAll()
    .stream()
    .filter(u -> u.isActive())
    .map(u -> new UserDto(u.getName(), u.getEmail()))
    .collect(Collectors.toList());

// ✅ With var - cleaner
var activeUsers = userRepository.findAll()
    .stream()
    .filter(u -> u.isActive())
    .map(u -> new UserDto(u.getName(), u.getEmail()))
    .collect(Collectors.toList());
```

**Collections and Loops:**

```java
// Collections
var users = List.of(
    new User("Alice", "alice@example.com"),
    new User("Bob", "bob@example.com")
);

// Loops
for (var user : users) {
    System.out.println(user.getName());
}

// Map operations
var userMap = users.stream()
    .collect(Collectors.toMap(User::getName, User::getEmail));
```

**Limitations (What var CANNOT do):**

```java
// ❌ NOT allowed at class level
class User {
    var name;  // ❌ ERROR - var only for local variables
}

// ❌ NOT allowed in method parameters
public void printUser(var user) {  // ❌ ERROR
    System.out.println(user);
}

// ❌ NOT allowed without initializer
var x;  // ❌ ERROR - compiler can't infer type

// ❌ Diamond operator alone doesn't work
var list = new ArrayList<>();  // ❌ Compiler can't infer generic type

// ✅ But this works
var list = new ArrayList<String>();

// ❌ NOT allowed with null initializer
var obj = null;  // ❌ ERROR - null type is ambiguous
```

**Benefits:**
- ✅ Less boilerplate
- ✅ Type-safe (compiler still checks)
- ✅ Easier refactoring
- ✅ Works with complex generics

**Cautions:**
- ❌ Can reduce readability if type isn't obvious
- ❌ IDE assistance needed to see actual type
- ❌ Local scope only

**Interview Ready Explanation:**
"The `var` keyword allows the compiler to infer local variable types. Instead of writing `List<String> names = new ArrayList<>()`, we write `var names = new ArrayList<String>()`. It's type-safe because the compiler still enforces types. We use it where the type is obvious from the initializer."

---

### 7. TLS 1.3 Support (Java 11)

**What:** Java 11 automatically supports TLS 1.3 for HTTPS connections.

**Purpose:** Improve security and performance for encrypted communication.

**When to Use:**
- HTTPS APIs
- Secure WebSocket connections
- Database connections (SSL)
- Any encrypted network communication

**How It Works (Automatic):**

```java
// No special code needed - TLS 1.3 is used automatically
HttpClient client = HttpClient.newHttpClient();

HttpRequest request = HttpRequest.newBuilder()
    .uri(URI.create("https://api.example.com/data"))  // TLS 1.3 automatically
    .GET()
    .build();

HttpResponse<String> response = client.send(request, 
    HttpResponse.BodyHandlers.ofString());
```

**Verify TLS Version (For Debugging):**

```java
@Service
public class SecureApiClient {
    
    public void checkTlsVersion() {
        // Get supported TLS versions
        SSLContext sslContext = SSLContext.getDefault();
        System.out.println("Default SSL Provider: " + sslContext.getProvider());
        
        // Java 11+ uses TLS 1.3 by default
        // TLS versions: TLSv1.3, TLSv1.2, TLSv1.1, TLSv1
    }
    
    public HttpClient createSecureClient() {
        // Custom TLS configuration (if needed)
        SSLContext sslContext = SSLContext.getInstance("TLSv1.3");
        sslContext.init(null, null, null);
        
        return HttpClient.newBuilder()
            .sslContext(sslContext)
            .build();
    }
}
```

**Benefits:**
- ✅ Faster handshake than TLS 1.2 (reduced latency)
- ✅ Better security than TLS 1.2
- ✅ Automatic support (no config needed)
- ✅ Works for all HTTPS, WSS connections

**Interview Ready Explanation:**
"Java 11 added native TLS 1.3 support. Any HTTPS connection automatically uses TLS 1.3 when available, providing better security and faster handshake. It's automatic - no code changes needed."

---

## 👍 GOOD TO KNOW FEATURES (Medium Priority)

### 8. Single-File Programs / Launch Single File Scripts (Java 11)

**What:** Run `.java` files directly without explicit compilation.

**Purpose:** Simplify scripting, automation, and learning Java without build tools.

**When to Use:**
- DevOps scripts
- Kubernetes init containers
- Quick automation tasks
- Learning/prototyping
- CI/CD automation

**Example Script:**

```java
// File: HelloWorld.java
import java.time.LocalDateTime;

void main() {
    System.out.println("Hello, World!");
    System.out.println("Current time: " + LocalDateTime.now());
}
```

**Run Directly:**

```bash
$ java HelloWorld.java
Hello, World!
Current time: 2024-02-21T14:30:45.123456
```

**Production Example - Monitoring Script:**

```java
// File: K8sHealthCheck.java
import java.net.HttpURLConnection;
import java.net.URL;

void main(String[] args) throws Exception {
    String serviceUrl = args.length > 0 ? args[0] : "http://localhost:8080/health";
    
    URL url = new URL(serviceUrl);
    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
    conn.setRequestMethod("GET");
    conn.setConnectTimeout(5000);
    
    int status = conn.getResponseCode();
    System.out.println("Service Status: " + status);
    System.exit(status == 200 ? 0 : 1);
}
```

**Run with Arguments:**

```bash
$ java K8sHealthCheck.java http://api.example.com/health
Service Status: 200
```

**Benefits:**
- ✅ No compilation step
- ✅ Great for scripts and automation
- ✅ Fast iteration for prototypes
- ✅ Can be used in shebang (#!) for Unix scripts

**Interview Ready Explanation:**
"Java 11 lets you run `.java` files directly without compilation. The JVM automatically compiles them in memory. Great for scripts, DevOps automation, and prototyping without setting up a build system."

---

### 9. Helpful NullPointerExceptions (Java 14/17)

**What:** NullPointerExceptions now show exactly which variable is null.

**Purpose:** Faster debugging by pinpointing the exact null reference.

**Before (Java 13):**

```java
// ❌ Vague error message
Exception in thread "main" java.lang.NullPointerException
    at TestNPE.main(TestNPE.java:5)
// Help! Which variable is null?
```

**After (Java 14+):**

```java
// ✅ Exact variable shown
Exception in thread "main" java.lang.NullPointerException: 
    Cannot invoke String method "length()" because "user.email" is null
    at TestNPE.main(TestNPE.java:5)
// Now we know user.email is null!
```

**Real Example:**

```java
public class User {
    public String name;
    public String email;
    
    public int getEmailLength() {
        return email.length();  // If email is null...
    }
}

// Usage
var user = new User();
user.name = "Alice";
// user.email left as null

int len = user.getEmailLength();
// OLD MESSAGE:
// Exception: NullPointerException at line 7
// 
// NEW MESSAGE (Java 14+):
// Exception: NullPointerException: Cannot invoke String method "length()" 
// because "user.email" is null
```

**Benefits:**
- ✅ Immediate understanding of what's null
- ✅ Faster debugging
- ✅ Automatic - no changes needed

**Interview Ready Explanation:**
"Java 14+ enhanced NullPointerExceptions to show exactly which variable is null. Instead of just a line number, you get the actual variable name. Extremely helpful for debugging complex call chains."

---

### 10. SecurityManager Deprecated (Java 17)

**What:** SecurityManager marking for removal in future Java versions.

**Purpose:** Shift security responsibility to modern container/OS-level solutions.

**Old Paradigm (Deprecated):**

```java
// ❌ Old JVM-level security
System.setSecurityManager(new SecurityManager() {
    @Override
    public void checkConnect(String host, int port) {
        if (!host.equals("trusted.server.com")) {
            throw new SecurityException("Unauthorized connection");
        }
    }
});
```

**Modern Approach (Docker/Kubernetes):**

```yaml
# Docker - Network policies, capability dropping
version: '3'
services:
  app:
    image: myapp:latest
    networks:
      - backend
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

```yaml
# Kubernetes - SecurityContext, NetworkPolicy
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    readOnlyRootFilesystem: true
  containers:
  - name: app
    image: myapp:latest
    securityContext:
      allowPrivilegeEscalation: false
```

**Benefits:**
- ✅ Cleaner, more modern approach
- ✅ Better integration with container orchestration
- ✅ Easier to manage across distributed systems
- ✅ No JVM internal security overhead

**Interview Ready Explanation:**
"SecurityManager was Java's old way of enforcing security policies at the JVM level. Modern Java (17+) deprecates it in favor of container and OS-level security (Docker, Kubernetes RBAC). You should use container security policies instead."

---

## ⚙️ NICHE FEATURES (Advanced/Low Priority)

### 11. Epsilon GC (Java 11)

**What:** A garbage collector that does no garbage collection (no memory reclamation).

**Purpose:** Performance benchmarking and testing on short-lived applications.

**Use Cases:**
- Micro benchmarking (JMH)
- Testing GC impact
- Very short-lived containers
- Analyzing allocation patterns

**Enable Epsilon GC:**

```bash
java -XX:+UseEpsilonGC -XX:EpsilonMaxTenuringThreshold=0 MyApp
```

**Benchmark Example:**

```java
// Only test allocation performance without GC overhead
// Useful for understanding true allocation cost
public static void main(String[] args) {
    long start = System.nanoTime();
    
    for (int i = 0; i < 1_000_000; i++) {
        var list = new ArrayList<String>();
        list.add("test");
    }
    
    long elapsed = System.nanoTime() - start;
    System.out.println("Time: " + elapsed + " ns");
}
```

**Caution:** ⚠️ Never use in production - will cause OutOfMemoryError!

---

### 12. ZGC & Shenandoah GC (Java 17)

**What:** Low-latency garbage collectors designed for large heaps.

**Purpose:** Sub-millisecond pause times for latency-sensitive applications.

**When to Use:**
- High-frequency trading systems
- Real-time gaming backends
- Ultra-low-latency microservices
- Large heap sizes (testing)

**Enable ZGC:**

```bash
java -XX:+UseZGC MyApp
```

**Enable Shenandoah GC:**

```bash
java -XX:+UseShenandoahGC MyApp
```

**Real Example - Low Latency Trading:**

```java
public class TradeExecutor {
    
    // Run with: java -XX:+UseZGC TradeExecutor
    public static void main(String[] args) {
        // With ZGC: GC pauses < 10ms, even with large heaps
        // Without ZGC: GC pauses > 500ms
        
        TradeExecutor executor = new TradeExecutor();
        
        for (int i = 0; i < 1_000_000; i++) {
            long tradeTime = executor.executeTrade();
            if (tradeTime > 1000) {  // 1ms latency spike
                System.out.println("WARNING: Latency spike!");
            }
        }
    }
    
    private long executeTrade() {
        long start = System.nanoTime();
        // Trade execution logic
        return (System.nanoTime() - start) / 1_000_000;  // Convert to ms
    }
}
```

**Comparison Table:**

| GC | Max Pause | Heap Size | Use Case |
|----|-----------|-----------|----------|
| G1GC | 50-200ms | Large | Default, balanced |
| ZGC | < 10ms | Very large | Ultra-low latency |
| Shenandoah | < 10ms | Large | Low latency |
| Epsilon | N/A | N/A | Benchmarking only |

---

## 📋 Quick Reference - When to Use Each Feature

### REST API Development
- ✅ Records for DTOs
- ✅ Pattern Matching for validation
- ✅ Text Blocks for error messages
- ✅ New HttpClient for 3rd-party calls

### Core Business Logic
- ✅ Sealed Classes for domain models
- ✅ Records for immutable value objects
- ✅ Local Variable Type (var)

### Microservices Architecture
- ✅ New HttpClient for service-to-service calls
- ✅ TLS 1.3 for HTTPS
- ✅ Sealed Classes for API contracts
- ✅ Records for Kafka events

### Performance-Critical Systems
- ✅ ZGC for ultra-low latency
- ✅ Shenandoah for large heaps
- ✅ Pattern Matching to reduce object allocation

### DevOps / Automation
- ✅ Single-File Scripts for automation
- ✅ New HttpClient for health checks
- ✅ Local Variable Type for quick scripting

---

## 🎯 Interview Preparation Checklist

### Must Master (Asked in 90%+ interviews)

- [ ] Sealed Classes - inheritance control
- [ ] Pattern Matching instanceof - code cleanup
- [ ] New HttpClient API - microservices calls
- [ ] Records - DTOs and immutability
- [ ] Text Blocks - multiline strings

### Should Know (Asked in 60%+ interviews)

- [ ] Local Variable Type (var) - when and when not to use
- [ ] Records defensive copying - immutability pitfalls
- [ ] TLS 1.3 - security improvements
- [ ] Single-File Scripts - DevOps use cases

### Good to Know (Asked in 30%+ interviews)

- [ ] Helpful NullPointerExceptions - debugging
- [ ] SecurityManager deprecation - modern approaches
- [ ] ZGC/Shenandoah - when to use low-latency GCs

---

## 💡 Interview Tips

1. **Always provide a real-world example** - Show how you'd use the feature in production code
2. **Know the trade-offs** - Records have limitations, var can reduce readability
3. **Connect features** - sealed classes + pattern matching is more powerful together
4. **Mention migration path** - How older code can adopt new features
5. **Performance context** - When each feature improves performance or maintainability

---

**Last Updated:** February 21, 2026  
**Java Versions Covered:** Java 9 - Java 21  
**Difficulty Level:** Intermediate to Senior  
**Estimated Study Time:** 45-60 minutes for mastery
