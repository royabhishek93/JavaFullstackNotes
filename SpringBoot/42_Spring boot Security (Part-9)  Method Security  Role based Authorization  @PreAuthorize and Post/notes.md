# Method Security — Role-Based Authorization with @PreAuthorize and @PostAuthorize

## What is this? (Plain English)

Think of a large office building with hundreds of rooms. One approach to security is to station a single guard at the main entrance holding a giant list: "room 101 → managers only, room 102 → HR only, room 103 → everyone," and so on for every room in the building. That's exactly what URL-level security in `SecurityConfig` (matching request paths to roles) looks like — one central list that has to know about every single endpoint. It works, but once you have hundreds of API endpoints, that list becomes a nightmare to maintain.

Method Security is the alternative: instead of one guard checking a master list, **every individual door has its own keycard reader** that decides on the spot whether to let someone in — right at the door (the controller/service method) instead of at the building entrance. Some doors go a step further: after you walk in and pick something up, a second reader checks *what you're carrying out* before letting you leave the room — that's `@PostAuthorize` inspecting the method's return value (e.g., making sure the order you fetched actually belongs to you) before the response is handed back.

- `@PreAuthorize` = keycard check **before** you're allowed to enter the room (before the method body runs).
- `@PostAuthorize` = a second check **after** you've done something inside the room, but **before** you're allowed to leave with what you picked up (after the method runs, before the response is sent).

## The Problem It Solves

Filter-chain / URL-level authorization (the `.requestMatchers("/api/orders").hasRole("USER")` style config seen in earlier videos) works fine for small applications, but it has a scalability problem:

- Every single API path and its required role has to be registered in one central `SecurityConfig` class.
- Real organizations can easily have hundreds of APIs — keeping all of them listed and up to date in one filter chain becomes difficult to manage and error-prone.
- It only supports coarse role checks based on the URL pattern. It cannot express "read is allowed, but delete on this same resource is not" or "only let a user fetch *their own* record" without extra hand-written logic outside the security config.

The better solution is to move the authorization decision to the place where the endpoint is actually defined — the controller (or service) method itself — using annotations. This is **method-level security**:

- `@PreAuthorize` — evaluate an authorization expression **before** the method executes. If it fails, the method body never runs at all.
- `@PostAuthorize` — evaluate an authorization expression **after** the method executes, using the method's **return value**, but before that value is sent back to the caller. This is needed when the authorization decision depends on data that is only known once the business logic has actually run (e.g., "does this order belong to the user who's asking for it?").

Since the same `Authentication` object (populated during the authentication filter stage, containing the granted authorities: roles + permissions) flows all the way to the controller layer, these annotations can read directly from it to make their decision.

## How Method Security Works (Flow, ASCII)

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

```text
Client --> [AOP Proxy around controller bean]
               |
               v
   AuthorizationManagerBeforeMethodInterceptor
   (reads @PreAuthorize SpEL string, e.g. "hasRole('USER') and hasAuthority('order_read')")
               |
               v
        SpelExpressionParser
        builds an Abstract Syntax Tree (AST)
               |
               v
     Recursively resolve AST nodes:
     - operators: AND / OR / NOT / relational (==, !=, ...)
     - hasRole(...) / hasAuthority(...)
     - method arguments, e.g. #id
     - authentication.principal.id
               |
               v
        Expression true? ----No----> AccessDeniedException (403 Forbidden)
               |                       (method body NEVER executes)
              Yes
               |
               v
      Target method executes (business logic runs)
               |
               v
   AuthorizationManagerAfterMethodInterceptor
   (reads @PostAuthorize SpEL string, e.g. "returnObject.userId == authentication.principal.id")
               |
               v
     Same SpEL parsing/resolution, but now
     "returnObject" is bound to the method's return value
               |
               v
        Expression true? ----No----> AccessDeniedException (403 Forbidden)
               |                       (response is discarded, never sent to client)
              Yes
               |
               v
     Return value sent back to the client as the HTTP response
```

## Setting Up: Users, Roles & Permissions

To test method security, a dynamic user (with a role **and** a set of fine-grained permissions) is created, instead of a single hard-coded role:

- **Role** — a coarse, high-level distinction (e.g. `USER`, `ADMIN`).
- **Permission** — a granular capability the user is allowed to perform (e.g. `order_read`, `order_delete`, `sales_create`), modeled as a **one-to-many** relationship (one user can have many permissions).

A user like "SJ" could have role `USER`, with permissions `order_read` only — meaning: even though SJ has the general `USER` role, SJ can read orders and (for example) delete orders, but cannot create them; SJ can, however, create sales if that permission was granted separately.

```java
@Entity
@Table(name = "user_login")
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String username;
    private String password;
    private String role; // e.g. "USER", "ADMIN"

    @OneToMany(cascade = CascadeType.ALL, fetch = FetchType.EAGER)
    @JoinColumn(name = "user_id")
    private List<UserPermission> permissions;

    // getters and setters
}

@Entity
public class UserPermission {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name; // e.g. "order_read", "sales_read", "sales_create"

    // getters and setters
}
```

The `UserDetailsService` implementation combines the role **and** every permission into a single list of granted authorities. This is the same list the `Authentication` object carries all the way to the controller layer:

```java
@Service
public class UserDetailsServiceImpl implements UserDetailsService {

    @Autowired
    private UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String username) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new UsernameNotFoundException("User not found"));

        return org.springframework.security.core.userdetails.User
                .withUsername(user.getUsername())
                .password(user.getPassword())
                .authorities(getAuthorities(user))
                .build();
    }

    private List<GrantedAuthority> getAuthorities(User user) {
        List<GrantedAuthority> authorities = new ArrayList<>();

        // role goes into the granted authorities list
        authorities.add(new SimpleGrantedAuthority(user.getRole()));

        // every fine-grained permission also goes into the same list
        user.getPermissions()
            .forEach(p -> authorities.add(new SimpleGrantedAuthority(p.getName())));

        return authorities;
        // final list looks like: [USER, order_read, sales_create, ...]
    }
}
```

## Enabling Method Security

`@PreAuthorize` and `@PostAuthorize` are **ignored** unless method security is explicitly turned on in the security configuration:

```java
@Configuration
@EnableMethodSecurity(prePostEnabled = true)
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .httpBasic(Customizer.withDefaults()) // basic auth used here purely to keep the focus on authorization, not authentication
            .authorizeHttpRequests(auth -> auth.anyRequest().authenticated());
        return http.build();
    }
}
```

Without `prePostEnabled = true`, both annotations are silently ignored and every method becomes reachable regardless of role or permission.

## @PreAuthorize Examples

`@PreAuthorize` runs its expression **before** the controller method body executes. If the expression evaluates to `false`, the method is never invoked and the caller gets `403 Forbidden`.

```java
@RestController
@RequestMapping("/api")
public class OrderController {

    @PreAuthorize("hasRole('USER') and hasAuthority('order_read')")
    @GetMapping("/orders")
    public String getOrders() {
        return "All orders have been fetched successfully.";
    }
}

@RestController
@RequestMapping("/api")
public class SalesController {

    @PreAuthorize("hasAuthority('sales_read')")
    @GetMapping("/sales")
    public String getSales() {
        return "All sales have been fetched successfully.";
    }
}
```

Test: a user `SJ` created with role `USER` and permission `order_read` (basic auth `SJ` / `123`):

- `GET /api/orders` → **200 OK**, `"All orders have been fetched successfully."` — SJ has `USER` role *and* `order_read` authority, so both conditions in the `and` expression pass.
- `GET /api/sales` → **403 Forbidden** — the endpoint requires `sales_read`, which SJ was never granted.

## hasRole vs hasAuthority — No Real Difference

A common point of confusion: `hasRole('USER')` vs `hasAuthority('USER')`.

- At the code level, **there is no functional difference**. Both ultimately check whether a given value is present in the same list of granted authorities returned by `getAuthorities()`.
- The **only** difference: `hasRole('X')` automatically prepends the prefix `ROLE_` before checking (so `hasRole('USER')` checks for `ROLE_USER` in the authority list), while `hasAuthority('X')` checks for the exact string you pass, with nothing added.
- By convention, `hasRole` is used for high-level, coarse role distinctions (`ADMIN`, `USER`), while `hasAuthority` is used for granular, fine-grained permissions (`order_read`, `sales_create`).

Internally (in `SecurityExpressionRoot`), the call chain is:

- `hasAuthority(...)` → `hasAnyAuthority(...)` → `hasAnyAuthorityName(...)`
- `hasRole(...)` → `hasAnyRole(...)` → the **same** underlying `hasAnyAuthorityName(...)` method, just with the `ROLE_` prefix already added to the value being checked.

Either way, the check ends up iterating the same flat list of granted authorities (role + all permissions combined) and asking: "is this exact string present in the list?" If yes, the expression resolves to `true`.

## SpEL Under the Hood

The string passed to `@PreAuthorize`/`@PostAuthorize` (e.g. `"hasRole('USER') and hasAuthority('order_read')"`) is **Spring Expression Language (SpEL)**. Here's what happens step by step when a protected method is invoked:

1. **Interception** — `@PreAuthorize` is intercepted by `AuthorizationManagerBeforeMethodInterceptor` (the equivalent for `@PostAuthorize` is `AuthorizationManagerAfterMethodInterceptor`). This works the same way as any other Spring interceptor: it wraps the target method call via an AOP proxy.
2. **Parsing** — the interceptor reads the raw SpEL string from the annotation and hands it to Spring's `SpelExpressionParser`, which converts the string into an **Abstract Syntax Tree (AST)**. For an expression like `A and B`, the root node is the `AND` operation, with a left operand (`A`) and a right operand (`B`) as its children.
3. **Recursive resolution** — the interceptor recursively resolves the tree: it resolves the left operand first (which may itself be a nested operation, e.g. an `OR` with its own left/right children), then the right operand, invoking whichever method calls (`hasRole`, `hasAuthority`, relational comparisons, etc.) are referenced at each node.
4. **Authentication access** — `@PreAuthorize`/`@PostAuthorize` expressions have full access to the current `Authentication` object. The interceptor's `attemptAuthorization` logic reads it from the same `SecurityContextHolderStrategy` that the authentication filter populated earlier in the request lifecycle.
5. **Decision** — once every node in the AST has been resolved to a boolean, the interceptor validates the final result and decides whether to allow the method invocation (`@PreAuthorize`) or allow the response to be returned (`@PostAuthorize`). A `false` result throws an `AccessDeniedException`.

Beyond `and`/`or`/`not`, SpEL also supports **relational operators** (`==`, `!=`, etc.) and can reference **method arguments directly**. For example, for an endpoint like:

```java
@PreAuthorize("#id == authentication.principal.id")
@GetMapping("/user/{id}")
public UserDto fetchUserDetails(@PathVariable Long id) {
    // ...
}
```

`#id` refers to the method's `id` path-variable argument, and `authentication.principal.id` refers to the unique ID of the currently authenticated user (the "principal"). This ensures a user can only fetch their **own** details — a user with principal ID `2` calling `/user/3` gets denied before the method even runs, because `3 == 2` is `false`.

## @PostAuthorize Example

`@PostAuthorize` runs its expression **after** the method body has executed but **before** the response is returned to the caller. This is intercepted by `AuthorizationManagerAfterMethodInterceptor`. It's used when the authorization decision depends on data that only exists once the business logic has produced a result — for example, checking that a fetched record actually belongs to the caller.

Inside a `@PostAuthorize` expression, `returnObject` refers to the method's return value (already cast to its actual type — no manual casting needed).

```java
public class OrderDto {
    private Long id;
    private Long userId; // which user this order belongs to
    // getters and setters
}

@RestController
@RequestMapping("/api")
public class OrderController {

    @PreAuthorize("hasRole('USER') and hasAuthority('order_read')")
    @PostAuthorize("returnObject.userId == authentication.principal.id")
    @GetMapping("/orders")
    public OrderDto getOrder() {
        OrderDto order = new OrderDto();
        order.setId(101L);
        order.setUserId(1L); // hard-coded for demonstration: this order belongs to user id 1
        return order;
    }
}
```

Test setup: two users are created with identical role (`USER`) and permission (`order_read`) — user **A** with principal ID `1`, user **B** with principal ID `2`.

- Both A and B pass the `@PreAuthorize` check (both have `USER` role and `order_read` authority), so the method executes for either of them.
- The method returns an `OrderDto` hard-coded with `userId = 1`.
- `@PostAuthorize` then checks `returnObject.userId == authentication.principal.id`:
  - User **A** (principal id `1`): `1 == 1` → `true` → the order is returned normally.
  - User **B** (principal id `2`): `1 == 2` → `false` → **403 Forbidden**, even though the method already ran and produced a result — the response is simply never handed back to B.

This demonstrates the key use case for `@PostAuthorize`: enforcing "you can only access your own data" style rules that can't be checked until after the actual record has been fetched.

## Important Concepts

- **Method Security**: Authorization enforced at the controller/service method level via annotations, instead of centrally in the security filter chain — solves the scalability problem of managing hundreds of URL-to-role mappings in one place.
- **`@PreAuthorize`**: Evaluates a SpEL expression **before** the method executes. If it fails, the method body never runs. Intercepted by `AuthorizationManagerBeforeMethodInterceptor`.
- **`@PostAuthorize`**: Evaluates a SpEL expression **after** the method executes (using `returnObject` to inspect the return value), but before the response is sent. Intercepted by `AuthorizationManagerAfterMethodInterceptor`.
- **`@EnableMethodSecurity(prePostEnabled = true)`**: Must be set in the security config, otherwise `@PreAuthorize`/`@PostAuthorize` are silently ignored.
- **Role vs Permission**: Role is a coarse, high-level grouping (`USER`, `ADMIN`); permission is a fine-grained capability (`order_read`, `sales_create`). Both end up in the same flat list of granted authorities returned by `getAuthorities()`.
- **`hasRole` vs `hasAuthority`**: Functionally identical under the hood — both check membership in the granted-authorities list. The only difference is `hasRole` auto-prepends the `ROLE_` prefix; `hasAuthority` does not.
- **SpEL (Spring Expression Language)**: The expression language used inside `@PreAuthorize`/`@PostAuthorize` strings. Parsed into an AST by `SpelExpressionParser` and resolved recursively (operators, method calls, method arguments like `#id`, and `authentication`/`returnObject` references).
- **`AccessDeniedException`**: Thrown when a `@PreAuthorize` or `@PostAuthorize` expression evaluates to `false`, resulting in a `403 Forbidden` response to the client.

## Interview Q&A

**Q1: Why isn't URL-level (filter-chain) security enough for large applications?**
A: It requires every single endpoint-to-role mapping to be registered centrally in the security config. With hundreds of APIs, this list becomes hard to maintain and doesn't scale well. Method-level security (`@PreAuthorize`/`@PostAuthorize`) moves the authorization decision to where the endpoint is defined, and supports far more granular expressions than a simple URL-to-role match.

**Q2: What is the difference between `@PreAuthorize` and `@PostAuthorize`?**
A: `@PreAuthorize` evaluates its expression before the method executes — if it fails, the method body never runs. `@PostAuthorize` evaluates its expression after the method has executed, with access to the return value via `returnObject`, but before the response is sent back to the client — if it fails, the already-computed response is discarded and the caller gets `403 Forbidden`.

**Q3: What happens if you forget to add `@EnableMethodSecurity(prePostEnabled = true)`?**
A: Both `@PreAuthorize` and `@PostAuthorize` annotations are silently ignored, meaning every annotated method becomes accessible to any authenticated (or even unauthenticated, depending on the rest of the config) caller regardless of role or permission checks.

**Q4: Is there any real difference between `hasRole('X')` and `hasAuthority('X')`?**
A: No functional difference — both ultimately check the same flat list of granted authorities. The only distinction is that `hasRole('X')` automatically checks for `ROLE_X` (prepending the `ROLE_` prefix), while `hasAuthority('X')` checks for the exact string with no prefix added. By convention, roles are used for coarse-grained checks and authorities for fine-grained permission checks.

**Q5: How does `@PreAuthorize("hasRole('USER') and hasAuthority('order_read')")` actually get evaluated at runtime?**
A: The annotation is intercepted by `AuthorizationManagerBeforeMethodInterceptor`. It reads the SpEL string and passes it to `SpelExpressionParser`, which builds an Abstract Syntax Tree — here, an `AND` node with `hasRole('USER')` and `hasAuthority('order_read')` as its two operands. The interceptor recursively resolves each operand (invoking the corresponding methods against the current `Authentication` object's granted authorities), combines the results per the `AND` operator, and only allows the method to execute if the overall expression is `true`.

**Q6: How would you implement "a user can only fetch their own record" using method security?**
A: Use `@PreAuthorize` with a SpEL expression that references the method's path-variable argument and compares it against the authenticated principal's ID, e.g. `@PreAuthorize("#id == authentication.principal.id")` on a method with `@PathVariable Long id`. This denies the call before the method body runs if the requested ID doesn't match the caller's own principal ID. Alternatively, if the check depends on data only available after fetching the record (e.g. checking a field on the loaded entity rather than the path variable), use `@PostAuthorize` with `returnObject` instead, since that data isn't available until after the method executes.
