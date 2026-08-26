# Q14: Spring Security & JWT — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 25-30 minutes | **Frequency:** Every senior/architect round 🔥🔥🔥 | **Difficulty:** ⭐⭐⭐⭐⭐

> "The token was expired but the user was still browsing for 3 hours — turns out nobody implemented token blacklisting." — Classic JWT trap.

---

## How Spring Security Filter Chain Works (Plain English)

```
HTTP Request
    ↓
DelegatingFilterProxy  (Spring bridges Servlet filters to Spring beans)
    ↓
SecurityFilterChain (ordered list of filters)
    ├── DisableEncodeUrlFilter
    ├── WebAsyncManagerIntegrationFilter
    ├── SecurityContextPersistenceFilter  ← loads SecurityContext from session/token
    ├── HeaderWriterFilter
    ├── CorsFilter
    ├── CsrfFilter                        ← validates CSRF token (disabled for REST APIs)
    ├── LogoutFilter
    ├── JwtAuthenticationFilter           ← YOUR custom filter (JWT validation)
    ├── UsernamePasswordAuthenticationFilter
    ├── ExceptionTranslationFilter        ← converts AuthenticationException → 401/403
    └── FilterSecurityInterceptor         ← checks method/URL authorization
    ↓
DispatcherServlet → Controller
```

---

## Scenario 1: JWT — The Complete Production Flow

### The Token Structure
```
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyQGV4LmNvbSIsInJvbGVzIjpbIlJPTEVfVVNFUiJdLCJpYXQiOjE2MDAsImV4cCI6MTYwMDM2MDB9.signature

HEADER.PAYLOAD.SIGNATURE

Header:  { "alg": "HS256" }
Payload: { "sub": "user@ex.com", "roles": ["ROLE_USER"], "iat": 1600, "exp": 1600+3600 }
Signature: HMAC(base64(header) + "." + base64(payload), secret)
```

### Production JWT Filter
```java
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain)
            throws ServletException, IOException {

        String header = request.getHeader("Authorization");

        // No token → let request proceed (public endpoint or will be rejected downstream)
        if (header == null || !header.startsWith("Bearer ")) {
            chain.doFilter(request, response);
            return;
        }

        String token = header.substring(7);

        try {
            Claims claims = jwtService.validateAndParseClaims(token);

            // Check token blacklist (revoked tokens) — CRITICAL for logout!
            if (tokenBlacklist.isBlacklisted(token)) {
                response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Token revoked");
                return;
            }

            String username = claims.getSubject();
            List<String> roles = claims.get("roles", List.class);

            List<GrantedAuthority> authorities = roles.stream()
                .map(SimpleGrantedAuthority::new)
                .collect(toList());

            UsernamePasswordAuthenticationToken auth =
                new UsernamePasswordAuthenticationToken(username, null, authorities);
            auth.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

            SecurityContextHolder.getContext().setAuthentication(auth);

        } catch (ExpiredJwtException ex) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Token expired");
            return;
        } catch (JwtException ex) {
            response.sendError(HttpServletResponse.SC_UNAUTHORIZED, "Invalid token");
            return;
        }

        chain.doFilter(request, response);
    }
}
```

### Security Config
```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity   // enables @PreAuthorize, @PostAuthorize
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)           // REST API — no CSRF needed
            .sessionManagement(s -> s
                .sessionCreationPolicy(SessionCreationPolicy.STATELESS)) // no sessions
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .requestMatchers(HttpMethod.GET, "/api/products/**").permitAll()
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class)
            .exceptionHandling(ex -> ex
                .authenticationEntryPoint(customAuthEntryPoint)   // custom 401 JSON
                .accessDeniedHandler(customAccessDeniedHandler)   // custom 403 JSON
            );

        return http.build();
    }
}
```

---

## Trap 1: JWT Has No Logout (Stateless = Can't Invalidate)

### The Problem
```
User logs out → frontend deletes token from localStorage
               → but server has NO STATE → token is still valid until expiry!
               → If token is stolen, attacker can use it for remaining TTL (hours!)
```

### The Illusion of Logout
```java
// WRONG ❌ — This is NOT logout for JWT
@PostMapping("/logout")
public ResponseEntity<Void> logout() {
    SecurityContextHolder.clearContext(); // clears server-side context
    // But JWT is still valid! Any request with the old token still authenticates!
    return ResponseEntity.ok().build();
}
```

### Fix: Token Blacklist (Redis)
```java
@Service
public class TokenBlacklistService {

    private final RedisTemplate<String, String> redis;

    // Called on logout — add token to blacklist
    public void revokeToken(String token, Date expiry) {
        long ttlSeconds = (expiry.getTime() - System.currentTimeMillis()) / 1000;
        if (ttlSeconds > 0) {
            // Store until natural expiry — Redis auto-deletes after TTL
            redis.opsForValue().set(
                "blacklist:" + token,
                "revoked",
                ttlSeconds, TimeUnit.SECONDS
            );
        }
    }

    public boolean isBlacklisted(String token) {
        return redis.hasKey("blacklist:" + token);
    }
}

@PostMapping("/logout")
public ResponseEntity<Void> logout(@RequestHeader("Authorization") String authHeader) {
    String token = authHeader.substring(7);
    Claims claims = jwtService.parseClaims(token);
    blacklistService.revokeToken(token, claims.getExpiration());
    return ResponseEntity.ok().build();
}
```

### Trade-off to Explain in Interview
> "Blacklisting sacrifices the stateless nature of JWT — now every request does a Redis lookup. For most systems this is fine (Redis is sub-millisecond). Alternatively, keep token TTL very short (15 min) and use refresh tokens. Refresh tokens are stored server-side and can be truly revoked."

---

## Trap 2: Roles vs Authorities (ROLE_ Prefix)

### The Bug
```java
// In JWT token:
claims.put("roles", List.of("ADMIN", "USER"));

// In filter, you load:
authorities.add(new SimpleGrantedAuthority("ADMIN"));  // ← NO "ROLE_" prefix

// In security config:
.requestMatchers("/admin/**").hasRole("ADMIN")
```

```
hasRole("ADMIN") internally checks for "ROLE_ADMIN" authority.
You stored "ADMIN" (no prefix).
Result: admin users get 403 Forbidden everywhere.
No error in logs. Just 403. Very confusing to debug.
```

### Fix: Be Consistent
```java
// Option A: Store with ROLE_ prefix in token
claims.put("roles", List.of("ROLE_ADMIN", "ROLE_USER"));

// Filter:
authorities.add(new SimpleGrantedAuthority(role)); // already has ROLE_ prefix

// Config: hasRole() strips ROLE_ prefix automatically
.requestMatchers("/admin/**").hasRole("ADMIN")  // checks for "ROLE_ADMIN" ✅

// Option B: Store without prefix, use hasAuthority() (no prefix magic)
.requestMatchers("/admin/**").hasAuthority("ADMIN")  // checks for "ADMIN" exactly
```

### hasRole vs hasAuthority Summary
```
hasRole("ADMIN")       → checks for authority "ROLE_ADMIN" (adds prefix)
hasAuthority("ADMIN")  → checks for authority "ADMIN" exactly (no prefix)
@PreAuthorize("hasRole('ADMIN')")      → checks "ROLE_ADMIN"
@PreAuthorize("hasAuthority('ADMIN')") → checks "ADMIN"
```

---

## Trap 3: SecurityContext Lost in @Async Threads

### The Bug
```java
@Service
public class ReportService {

    @Async
    public CompletableFuture<Report> generateReport(Long userId) {
        // Get current user for audit
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        System.out.println(auth);  // → NULL !
        // SecurityContext is ThreadLocal — not propagated to async threads by default
    }
}
```

### Fix: SecurityContextHolder Strategy
```java
// Option 1: Global strategy — propagate to child threads
// Add to application startup:
SecurityContextHolder.setStrategyName(
    SecurityContextHolder.MODE_INHERITABLETHREADLOCAL
);
// Caution: thread pools reuse threads — context may leak between requests!

// Option 2: Explicitly pass the context (safest)
@Async
public CompletableFuture<Report> generateReport(Long userId,
                                                 Authentication auth) {
    SecurityContextHolder.getContext().setAuthentication(auth);
    // ... work ...
    SecurityContextHolder.clearContext(); // clear when done!
    return result;
}

// Caller:
Authentication auth = SecurityContextHolder.getContext().getAuthentication();
reportService.generateReport(userId, auth);

// Option 3: DelegatingSecurityContextExecutor wraps thread pool
@Bean
public Executor securityAwareExecutor() {
    ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
    executor.initialize();
    return new DelegatingSecurityContextExecutor(executor);
    // Automatically copies SecurityContext to pooled threads ✅
}
```

---

## Trap 4: CSRF Disabled for REST but Not for HTML Forms

### When to Enable/Disable CSRF
```
CSRF attack: malicious website tricks browser into submitting a form to your site.
             Browser automatically sends session cookies → attacker's form authenticated.

REST API with JWT (no cookies): CSRF not needed — no cookies to steal/abuse.
REST API with session cookies:  CSRF IS needed!
Web app with forms + sessions:  CSRF IS needed!
```

```java
// REST API with JWT — correct to disable CSRF
http.csrf(AbstractHttpConfigurer::disable)

// If you use cookie-based sessions (Spring MVC + Thymeleaf), keep CSRF ON
// Spring Security enables CSRF by default — don't disable it!

// Trap: Disabling CSRF for a cookie-based app because "API is hard to configure"
// → Opens the app to CSRF attacks (banking transfer, password change, etc.)
```

---

## Scenario 2: Method-Level Security with @PreAuthorize

### Production Pattern
```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    // Only ADMIN or the order's own user can see it
    @GetMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN') or @orderSecurityService.isOwner(#id, authentication)")
    public Order getOrder(@PathVariable Long id) { ... }

    // Only ADMIN can delete
    @DeleteMapping("/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public void deleteOrder(@PathVariable Long id) { ... }

    // User can only see their own orders (data-level filtering)
    @GetMapping
    @PostFilter("hasRole('ADMIN') or filterObject.userId == authentication.name")
    public List<Order> getAllOrders() { ... }
}

// Custom security expression bean
@Service("orderSecurityService")
public class OrderSecurityService {
    public boolean isOwner(Long orderId, Authentication auth) {
        Order order = orderRepo.findById(orderId).orElseThrow();
        return order.getUserId().equals(auth.getName());
    }
}
```

### Trap: @PreAuthorize on private methods
```java
@Service
public class OrderService {

    @PreAuthorize("hasRole('ADMIN')")
    private void deleteOrderInternal(Long id) {   // ❌ private method!
        // Spring AOP cannot proxy private methods
        // @PreAuthorize silently IGNORED — NO security check!
        orderRepo.deleteById(id);
    }
}
// Fix: make the method public, or move to a separate @Service bean
```

---

## Scenario 3: Refresh Token Pattern (Production-Grade Auth)

```
Access Token:  short-lived (15 min), stored in memory (JS variable)
Refresh Token: long-lived (7 days), stored in HttpOnly cookie (not accessible by JS)

Flow:
  Login → issue both tokens
  API call with access token → works for 15 min
  Access token expires → silently use refresh token to get new access token
  Refresh token expired/revoked → redirect to login

Security:
  Access token stolen (XSS)? → expires in 15 min → small damage window
  Refresh token (HttpOnly cookie) can't be stolen by XSS (JS can't read it)
  Refresh token can be revoked server-side (stored in DB/Redis)
```

```java
@PostMapping("/refresh")
public ResponseEntity<TokenResponse> refresh(
        @CookieValue("refresh_token") String refreshToken,
        HttpServletResponse response) {

    // Validate refresh token against database
    RefreshTokenEntity stored = refreshTokenRepo.findByToken(refreshToken)
        .orElseThrow(() -> new UnauthorizedException("Invalid refresh token"));

    if (stored.getExpiresAt().isBefore(Instant.now())) {
        refreshTokenRepo.delete(stored);
        throw new UnauthorizedException("Refresh token expired");
    }

    // Issue new access token
    String newAccessToken = jwtService.generateAccessToken(stored.getUser());

    // Rotate refresh token (prevents replay attacks)
    refreshTokenRepo.delete(stored);
    String newRefreshToken = jwtService.generateRefreshToken();
    refreshTokenRepo.save(new RefreshTokenEntity(stored.getUser(), newRefreshToken));

    // Set new refresh token in HttpOnly cookie
    ResponseCookie cookie = ResponseCookie.from("refresh_token", newRefreshToken)
        .httpOnly(true)
        .secure(true)        // HTTPS only
        .sameSite("Strict")  // CSRF protection
        .maxAge(Duration.ofDays(7))
        .path("/api/auth/refresh")  // only sent on refresh endpoint
        .build();
    response.addHeader(HttpHeaders.SET_COOKIE, cookie.toString());

    return ResponseEntity.ok(new TokenResponse(newAccessToken));
}
```

---

## Advanced Trap: Spring Security Ordering — Multiple SecurityFilterChain Beans

### The Problem
```java
@Bean
@Order(1)
public SecurityFilterChain apiChain(HttpSecurity http) throws Exception {
    http.securityMatcher("/api/**")
        .csrf(AbstractHttpConfigurer::disable)
        .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
        .authorizeHttpRequests(a -> a.anyRequest().authenticated());
    return http.build();
}

@Bean
@Order(2)
public SecurityFilterChain webChain(HttpSecurity http) throws Exception {
    http.securityMatcher("/**")   // matches everything including /api/**
        // Trap: if @Order(2) has no sessionManagement config,
        //       it defaults to stateful sessions!
        // If requests somehow match this chain, JWT won't work.
        .authorizeHttpRequests(a -> a.anyRequest().authenticated());
    return http.build();
}
```

**Rule**: Most specific matchers (narrower path patterns) → higher priority (lower @Order number). The first matching chain wins.

---

## Interview Cheat Sheet

> "For JWT in production: short-lived access tokens (15 min) + long-lived HttpOnly cookie refresh tokens. On logout, add the access token to a Redis blacklist until its natural expiry — JWT is stateless but logout requires state. Roles use ROLE_ prefix convention — `hasRole('ADMIN')` checks for `ROLE_ADMIN` authority. SecurityContext is ThreadLocal — @Async threads don't inherit it by default, so I use DelegatingSecurityContextExecutor. @PreAuthorize only works on public methods through proxied beans — private method security is silently bypassed. And CSRF: disable only for true stateless REST APIs with JWT, keep enabled for any cookie/session-based flow."
