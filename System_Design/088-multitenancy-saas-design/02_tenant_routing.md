# Tenant Identification & Routing

## Concept: SAP BTP's TENANT_HOST_PATTERN → AWS Subdomain Routing

In SAP BTP, the App Router uses a regex `TENANT_HOST_PATTERN` to extract the tenant subdomain from the URL.

**AWS equivalent:**
- Route 53 wildcard record `*.app.yourdomain.com`
- CloudFront passes the full `Host` header downstream
- Spring Cloud Gateway filter extracts the subdomain = tenantId

---

## URL Pattern

```
https://{tenantId}.app.yourdomain.com/api/orders

Examples:
  https://acmecorp.app.yourdomain.com/api/orders    → tenantId = acmecorp
  https://globex.app.yourdomain.com/api/products    → tenantId = globex
  https://initech.app.yourdomain.com/api/users      → tenantId = initech
```

Regex pattern (same idea as SAP's TENANT_HOST_PATTERN):
```
^([a-z0-9-]+)\.app\.yourdomain\.com$
         └─── capture group = tenantId
```

---

## Route 53 Configuration

```
Zone: yourdomain.com

Record:
  Name:  *.app.yourdomain.com
  Type:  A (Alias)
  Target: CloudFront distribution (d1234abcd.cloudfront.net)
```

No per-tenant DNS records needed. Wildcard covers all.

---

## Spring Cloud Gateway — Tenant Resolution Filter

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class TenantResolutionFilter implements GlobalFilter {

    private static final Pattern TENANT_PATTERN =
        Pattern.compile("^([a-z0-9-]+)\\.app\\.yourdomain\\.com$");

    private final TenantRegistry tenantRegistry;
    private final RedisTemplate<String, TenantInfo> redisTemplate;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String host = exchange.getRequest().getHeaders().getFirst("Host");

        if (host == null) {
            return reject(exchange, "Missing Host header");
        }

        Matcher matcher = TENANT_PATTERN.matcher(host);
        if (!matcher.matches()) {
            return reject(exchange, "Invalid tenant host");
        }

        String tenantId = matcher.group(1);

        return resolveTenant(tenantId)
            .flatMap(tenant -> {
                if (!tenant.isActive()) {
                    return reject(exchange, "Tenant subscription inactive");
                }

                ServerWebExchange mutatedExchange = exchange.mutate()
                    .request(r -> r.header("X-Tenant-ID", tenant.getTenantId())
                                   .header("X-Tenant-Schema", tenant.getSchemaName()))
                    .build();

                return chain.filter(mutatedExchange);
            })
            .onErrorResume(TenantNotFoundException.class,
                e -> reject(exchange, "Tenant not found: " + tenantId));
    }

    private Mono<TenantInfo> resolveTenant(String tenantId) {
        String cacheKey = "tenant:info:" + tenantId;
        TenantInfo cached = redisTemplate.opsForValue().get(cacheKey);

        if (cached != null) return Mono.just(cached);

        return tenantRegistry.findBySubdomain(tenantId)
            .doOnNext(t -> redisTemplate.opsForValue()
                .set(cacheKey, t, Duration.ofMinutes(5)));
    }

    private Mono<Void> reject(ServerWebExchange exchange, String reason) {
        exchange.getResponse().setStatusCode(HttpStatus.FORBIDDEN);
        exchange.getResponse().getHeaders()
            .setContentType(MediaType.APPLICATION_JSON);
        DataBuffer buffer = exchange.getResponse().bufferFactory()
            .wrap(("{\"error\":\"" + reason + "\"}").getBytes());
        return exchange.getResponse().writeWith(Mono.just(buffer));
    }
}
```

---

## TenantContextHolder — Thread-Local Carrier

```java
public final class TenantContextHolder {

    private static final ThreadLocal<String> TENANT_ID = new InheritableThreadLocal<>();
    private static final ThreadLocal<String> SCHEMA_NAME = new InheritableThreadLocal<>();

    public static void setTenantId(String tenantId) {
        TENANT_ID.set(tenantId);
        SCHEMA_NAME.set("tenant_" + tenantId.replace("-", "_"));
    }

    public static String getTenantId() {
        String tenantId = TENANT_ID.get();
        if (tenantId == null) throw new TenantContextMissingException("No tenant in context");
        return tenantId;
    }

    public static String getSchemaName() {
        return SCHEMA_NAME.get();
    }

    public static void clear() {
        TENANT_ID.remove();
        SCHEMA_NAME.remove();
    }
}
```

---

## Core API — Tenant Filter (Servlet)

Extracts `X-Tenant-ID` (injected by Gateway) and sets ThreadLocal:

```java
@Component
@Order(1)
public class TenantContextFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String tenantId = request.getHeader("X-Tenant-ID");

        if (tenantId == null || tenantId.isBlank()) {
            response.sendError(HttpServletResponse.SC_BAD_REQUEST,
                "Missing X-Tenant-ID header");
            return;
        }

        try {
            TenantContextHolder.setTenantId(tenantId);
            chain.doFilter(request, response);
        } finally {
            TenantContextHolder.clear(); // always clean up
        }
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // Health checks and actuator endpoints skip tenant context
        String path = request.getServletPath();
        return path.startsWith("/actuator") || path.equals("/health");
    }
}
```

---

## Tenant Identification Flow (End-to-End)

```
1. Browser → https://acmecorp.app.yourdomain.com/api/orders

2. Route 53 wildcard → CloudFront (SSL terminated, Host preserved)

3. CloudFront behavior /api/* → API Gateway

4. API Gateway:
   - Lambda Authorizer validates JWT
   - Extracts tenantId from JWT claim: { "custom:tenantId": "acmecorp" }
   - Validates JWT tenantId matches subdomain tenantId  ← SECURITY CHECK
   - Passes X-Tenant-ID: acmecorp header to Gateway

5. Spring Cloud Gateway:
   - TenantResolutionFilter: host=acmecorp.app.yourdomain.com → tenantId=acmecorp
   - Validates tenantId exists in registry (Redis cache)
   - Validates tenant.status == ACTIVE
   - Adds X-Tenant-Schema: tenant_acmecorp header

6. Core API (Spring Boot):
   - TenantContextFilter: sets TenantContextHolder.tenantId = "acmecorp"
   - DataSource routing: sets search_path to "tenant_acmecorp"
   - Business logic runs — always tenant-isolated

7. Response returns to browser
```

---

## Security: Cross-Tenant Access Prevention

The critical security check is step 4 above — the JWT `tenantId` claim **must match** the subdomain.

```java
// In Lambda Authorizer (or Spring Security)
String subdomainTenant = extractSubdomain(event.getHost()); // from Host header
String jwtTenant = jwtClaims.get("custom:tenantId");

if (!subdomainTenant.equals(jwtTenant)) {
    throw new UnauthorizedException("Tenant mismatch: subdomain vs JWT claim");
}
```

This prevents a user from `tenantA` calling `tenantB.app.com` with their own JWT — a critical cross-tenant data leak vector.

---

## Admin / Provider Routes

Provider's own dashboard runs on a separate domain:
```
admin.yourdomain.com  →  different CloudFront behavior
                          →  Admin Spring Boot app
                          →  No tenant resolution filter
                          →  Uses platform schema
```
