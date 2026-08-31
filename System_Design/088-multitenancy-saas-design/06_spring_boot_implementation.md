# Spring Boot Core Implementation

## Project Structure

```
saas-platform/
├── gateway-service/          ← Spring Cloud Gateway (tenant routing)
├── tenant-registry-service/  ← Tenant onboarding/offboarding
├── core-api-service/         ← Business logic
│   ├── config/
│   │   ├── SecurityConfig.java
│   │   ├── DataSourceConfig.java
│   │   └── WebMvcConfig.java
│   ├── multitenancy/
│   │   ├── TenantContextHolder.java
│   │   ├── TenantContextFilter.java
│   │   ├── SchemaRoutingInterceptor.java
│   │   └── TenantAwareRepository.java
│   ├── domain/
│   │   └── order/
│   │       ├── Order.java
│   │       ├── OrderRepository.java
│   │       └── OrderService.java
│   └── CoreApiApplication.java
└── shared-lib/               ← TenantContext, events, DTOs
```

---

## 1. TenantContextHolder (Thread-Local)

```java
// shared-lib — used across all services

public final class TenantContextHolder {

    private TenantContextHolder() {}

    private static final ThreadLocal<TenantContext> CONTEXT =
        new InheritableThreadLocal<>();

    public static void set(TenantContext ctx) {
        CONTEXT.set(ctx);
    }

    public static TenantContext get() {
        TenantContext ctx = CONTEXT.get();
        if (ctx == null) throw new TenantContextMissingException(
            "No tenant context on current thread");
        return ctx;
    }

    public static String getTenantId()   { return get().tenantId(); }
    public static String getSchemaName() { return get().schemaName(); }
    public static boolean hasContext()   { return CONTEXT.get() != null; }
    public static void clear()           { CONTEXT.remove(); }

    public record TenantContext(String tenantId, String schemaName) {
        public static TenantContext of(String tenantId) {
            String schema = "tenant_" + tenantId.replace("-", "_");
            return new TenantContext(tenantId, schema);
        }
    }
}
```

---

## 2. Tenant Filter — Extract X-Tenant-ID Header

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 1)
public class TenantContextFilter extends OncePerRequestFilter {

    private static final String TENANT_HEADER = "X-Tenant-ID";

    @Override
    protected void doFilterInternal(HttpServletRequest req,
                                    HttpServletResponse res,
                                    FilterChain chain)
            throws ServletException, IOException {

        String tenantId = req.getHeader(TENANT_HEADER);

        if (tenantId == null || tenantId.isBlank()) {
            res.sendError(SC_BAD_REQUEST, "Missing tenant context");
            return;
        }

        if (!isValidTenantId(tenantId)) {
            res.sendError(SC_BAD_REQUEST, "Invalid tenant identifier");
            return;
        }

        try {
            TenantContextHolder.set(TenantContext.of(tenantId));
            chain.doFilter(req, res);
        } finally {
            TenantContextHolder.clear();
        }
    }

    private boolean isValidTenantId(String tenantId) {
        return tenantId.matches("^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$");
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest req) {
        String path = req.getServletPath();
        return path.startsWith("/actuator") || path.equals("/health");
    }
}
```

---

## 3. Schema Routing Interceptor

Sets PostgreSQL `search_path` to the tenant schema on each request:

```java
@Component
public class SchemaRoutingInterceptor implements HandlerInterceptor {

    private final JdbcTemplate jdbc;

    public SchemaRoutingInterceptor(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    @Override
    public boolean preHandle(HttpServletRequest req,
                             HttpServletResponse res, Object handler) {
        if (TenantContextHolder.hasContext()) {
            String schema = TenantContextHolder.getSchemaName();
            // Parameterized to prevent injection — schema names are validated upstream
            jdbc.execute("SET search_path TO " + schema + ", public");
        }
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest req,
                                HttpServletResponse res,
                                Object handler, Exception ex) {
        // Always reset — critical to prevent schema bleeding across connections
        try {
            jdbc.execute("SET search_path TO public");
        } catch (Exception ignored) {
            // connection may be closed — that's fine
        }
    }
}

@Configuration
public class WebMvcConfig implements WebMvcConfigurer {

    private final SchemaRoutingInterceptor schemaInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(schemaInterceptor)
            .addPathPatterns("/api/**")
            .excludePathPatterns("/actuator/**");
    }
}
```

---

## 4. Async — Propagate TenantContext Across Threads

`ThreadLocal` doesn't cross thread boundaries. Use a wrapper for async:

```java
@Configuration
@EnableAsync
public class AsyncConfig implements AsyncConfigurer {

    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(10);
        executor.setMaxPoolSize(50);
        executor.setQueueCapacity(100);
        executor.setTaskDecorator(new TenantContextTaskDecorator()); // ← key
        executor.initialize();
        return executor;
    }
}

public class TenantContextTaskDecorator implements TaskDecorator {

    @Override
    public Runnable decorate(Runnable runnable) {
        // Capture context from submitting thread
        TenantContext ctx = TenantContextHolder.hasContext()
            ? TenantContextHolder.get() : null;

        return () -> {
            try {
                if (ctx != null) TenantContextHolder.set(ctx);
                runnable.run();
            } finally {
                TenantContextHolder.clear();
            }
        };
    }
}
```

---

## 5. Domain Repository — No Tenant Boilerplate

With schema isolation, repositories look completely standard:

```java
@Repository
public interface OrderRepository extends JpaRepository<Order, Long> {

    // No tenant filtering needed — schema isolation handles it
    List<Order> findByStatus(OrderStatus status);

    @Query("SELECT o FROM Order o WHERE o.total > :minAmount ORDER BY o.createdAt DESC")
    List<Order> findHighValueOrders(@Param("minAmount") BigDecimal minAmount);

    Page<Order> findAll(Pageable pageable);
}
```

```java
@Entity
@Table(name = "orders")  // resolves to tenant_{id}.orders via search_path
@EntityListeners(AuditingEntityListener.class)
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE,
                    generator = "order_seq")
    @SequenceGenerator(name = "order_seq",
                       sequenceName = "orders_id_seq", allocationSize = 1)
    private Long id;

    private String orderNo;

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    @Column(precision = 10, scale = 2)
    private BigDecimal total;

    @CreatedDate
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;
}
```

---

## 6. Service Layer — Tenant-Transparent

```java
@Service
@Transactional
public class OrderService {

    private final OrderRepository orderRepository;

    // No tenant ID parameter needed — it's in the context
    public List<OrderDto> getOrders(OrderFilter filter) {
        Pageable pageable = PageRequest.of(
            filter.getPage(), filter.getSize(),
            Sort.by("createdAt").descending());

        return orderRepository.findAll(pageable)
            .map(OrderDto::from)
            .getContent();
    }

    public OrderDto createOrder(CreateOrderRequest request) {
        Order order = Order.builder()
            .orderNo(generateOrderNo())
            .status(OrderStatus.PENDING)
            .total(request.getTotal())
            .build();

        return OrderDto.from(orderRepository.save(order));
    }

    // Audit log — always records which tenant performed the action
    private void auditLog(String action, Object resource) {
        auditRepository.save(AuditEntry.builder()
            .tenantId(TenantContextHolder.getTenantId())  // from context
            .action(action)
            .resource(resource.toString())
            .timestamp(LocalDateTime.now())
            .build());
    }
}
```

---

## 7. Redis Cache — Tenant-Prefixed Keys

Always prefix Redis keys with tenant ID to prevent cross-tenant cache hits:

```java
@Service
public class TenantAwareCacheService {

    private final RedisTemplate<String, Object> redisTemplate;

    private String key(String suffix) {
        // tenant:acmecorp:products:list
        return "tenant:" + TenantContextHolder.getTenantId() + ":" + suffix;
    }

    public <T> Optional<T> get(String cacheKey, Class<T> type) {
        Object cached = redisTemplate.opsForValue().get(key(cacheKey));
        return Optional.ofNullable(type.cast(cached));
    }

    public void put(String cacheKey, Object value, Duration ttl) {
        redisTemplate.opsForValue().set(key(cacheKey), value, ttl);
    }

    public void evict(String cacheKey) {
        redisTemplate.delete(key(cacheKey));
    }

    // Evict ALL cache for this tenant (e.g., on tenant config change)
    public void evictTenant(String tenantId) {
        String pattern = "tenant:" + tenantId + ":*";
        redisTemplate.delete(redisTemplate.keys(pattern));
    }
}
```

---

## 8. S3 — Tenant-Isolated File Storage

```java
@Service
public class TenantFileStorageService {

    private final S3Client s3Client;
    private static final String BUCKET = "saas-platform-files";

    private String s3Key(String filename) {
        // tenants/acmecorp/invoices/inv-001.pdf
        return "tenants/" + TenantContextHolder.getTenantId() + "/" + filename;
    }

    public String uploadFile(String filename, InputStream content, String contentType) {
        PutObjectRequest request = PutObjectRequest.builder()
            .bucket(BUCKET)
            .key(s3Key(filename))
            .contentType(contentType)
            .serverSideEncryption(ServerSideEncryption.AWS_KMS)
            .build();

        s3Client.putObject(request, RequestBody.fromInputStream(content, -1));

        return s3Key(filename);
    }

    public PresignedGetObjectRequest generatePresignedUrl(
            String filename, Duration expiry) {
        GetObjectRequest objectRequest = GetObjectRequest.builder()
            .bucket(BUCKET)
            .key(s3Key(filename))
            .build();

        return s3Presigner.presignGetObject(r ->
            r.getObjectRequest(objectRequest)
             .signatureDuration(expiry));
    }
}
```

---

## 9. Global Exception Handler

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(TenantContextMissingException.class)
    public ResponseEntity<ErrorResponse> handleTenantMissing(
            TenantContextMissingException e) {
        return ResponseEntity.status(FORBIDDEN)
            .body(new ErrorResponse("TENANT_CONTEXT_MISSING", e.getMessage()));
    }

    @ExceptionHandler(TenantNotFoundException.class)
    public ResponseEntity<ErrorResponse> handleTenantNotFound(
            TenantNotFoundException e) {
        return ResponseEntity.status(NOT_FOUND)
            .body(new ErrorResponse("TENANT_NOT_FOUND", e.getMessage()));
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<ErrorResponse> handleAccessDenied(
            AccessDeniedException e) {
        return ResponseEntity.status(FORBIDDEN)
            .body(new ErrorResponse("ACCESS_DENIED", "Insufficient permissions"));
    }
}
```

---

## 10. Integration Tests — Tenant Isolation Verification

```java
@SpringBootTest
@ActiveProfiles("test")
class TenantIsolationTest {

    @Autowired OrderRepository orderRepository;
    @Autowired SchemaRoutingInterceptor interceptor;

    @Test
    void tenantA_cannot_see_tenantB_orders() {
        // Seed data for tenant A
        withTenant("tenant_a", () -> {
            orderRepository.save(Order.builder().orderNo("A-001").build());
        });

        // Seed data for tenant B
        withTenant("tenant_b", () -> {
            orderRepository.save(Order.builder().orderNo("B-001").build());
        });

        // Query as tenant A — must only see A's orders
        withTenant("tenant_a", () -> {
            List<Order> orders = orderRepository.findAll();
            assertThat(orders).hasSize(1);
            assertThat(orders.get(0).getOrderNo()).isEqualTo("A-001");
        });
    }

    private void withTenant(String tenantId, Runnable action) {
        TenantContextHolder.set(TenantContext.of(tenantId));
        try {
            action.run();
        } finally {
            TenantContextHolder.clear();
        }
    }
}
```
