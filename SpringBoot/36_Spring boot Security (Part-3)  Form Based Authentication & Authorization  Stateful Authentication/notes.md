# Form-Based Authentication & Stateful (Session-Based) Authorization in Spring Security

## What is this? (Plain English)

Think of checking into a hotel: the first time you arrive at the front desk you show your ID and pay (this is the login form — username + password). The receptionist doesn't make you show your ID again every time you want to use the elevator or open your room door for the rest of your stay — instead they hand you a **key card**. Every door you swipe the card at just checks "is this key card still active and what does it unlock?" That key card is the equivalent of the **session ID** stored in a cookie (`JSESSIONID`). The hotel's internal system that remembers "key card #482 belongs to guest X, room 12, valid until checkout" is the equivalent of the server-side **HTTP session**.

Form-based authentication in Spring Security is exactly this pattern: it is a **stateful authentication method**, meaning the server maintains state about the client (the session), so the client only has to prove who it is once (via the login form) and after that just presents its "key card" (the session ID) with every request instead of the username and password again.

## The Problem It Solves

Without a session, a client would have to send its username and password with *every single request*, which is inefficient and repeatedly re-runs the full credential-validation logic. Form-based/session authentication solves this by:
- Validating credentials **once**, at `/login`.
- Creating a server-side `HttpSession` that stores the authenticated user's details (username, roles, authenticated flag).
- Returning a session ID to the client (via the `JSESSIONID` cookie).
- Letting all subsequent requests simply present that session ID; the server looks up the session, confirms it's valid/not expired, and fulfills the request — no username/password re-entry needed.

This is the **default authentication method in Spring Boot Security** — if you don't configure anything else (like JWT), Spring Boot silently assumes form login. Only when you explicitly want a stateless method like JWT do you need to write your own `SecurityFilterChain` to override this default.

## The Login Flow, Step by Step

1. User exists already (created dynamically or via `application.properties`, as shown in the previous video).
2. User calls the default endpoint `/login` (Spring Boot auto-generates this HTML login form — no code required).
3. User submits username, password, and a CSRF token.
4. The request hits the **security filter chain**, starting with `UsernamePasswordAuthenticationFilter`.
5. This filter builds a `UsernamePasswordAuthenticationToken` (a child of `Authentication`) containing just the principal (username) and credential (raw password); `authenticated = false` at this point.
6. This `Authentication` object is passed to the `AuthenticationManager`, which delegates to `DaoAuthenticationProvider`.
7. `DaoAuthenticationProvider`:
   - Hashes the incoming raw password using the configured `PasswordEncoder`.
   - Loads the stored `UserDetails` (username, stored hashed password, roles) via `UserDetailsService`.
   - Compares the incoming (hashed) password against the stored hashed password.
   - If they match, it returns a **fully authenticated** `Authentication` object: `authenticated = true`, roles populated. (Password itself is not put back on the object.)
8. No session exists yet at this point — only an authenticated `Authentication` object exists in memory.
9. The next filter, the security-context-holder filter, creates a `SecurityContext` object and stores the `Authentication` object inside it.
10. This `SecurityContext` is passed to `HttpSessionSecurityContextRepository`, which **creates a brand-new `HttpSession` object** and saves the `SecurityContext` inside it.
11. The `HttpSession` (with its session ID, creation time, expiry time, and the embedded security context data) is persisted — either in memory (default, e.g. inside Tomcat) or in a database (if `spring-session-jdbc` is configured).
12. The response sets the session ID in a cookie (`JSESSIONID`).
13. Since the `/login` endpoint was used, the request is then forwarded to the default root endpoint (`/`) and its controller executes (e.g. printing `hello`). If a protected resource like `/users` was hit directly instead of `/login`, and the user wasn't authenticated yet, Spring Security instead redirects to the login page first, and after successful login it forwards to that originally requested resource (not to `/`).

## The Subsequent-Request Flow (Session Validation)

1. Client sends a request to a protected resource (e.g. `/users`) with the `JSESSIONID` cookie attached — no username/password this time.
2. `UsernamePasswordAuthenticationFilter` is **not** involved this time. Instead, the **security-context-holder filter** runs first.
3. It passes the request to `HttpSessionSecurityContextRepository`, which tries to find the `HttpSession` matching the given session ID (looking in memory or the DB, depending on configuration).
4. If the session is **not found or expired**, the request is redirected to `/login` to re-authenticate.
5. If the session **is found and valid**, the repository extracts the stored `SecurityContext` (which holds the `Authentication` data: username, roles, authenticated flag).
6. That `SecurityContext` is placed into `SecurityContextHolder` — a placeholder available throughout the entire lifecycle of that request, so controllers and any downstream code can access the authenticated user's details.
7. Next, the **authorization filter** runs: it checks whether the authenticated user's role satisfies the role required for the requested endpoint.
8. If authorized, the request proceeds to `DispatcherServlet` and then the controller, which fulfills the request.
9. If not authorized, a **403 Forbidden** exception is thrown.

## Sequence Diagram

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## ASCII Fallback Diagram

```text
STEP 1 — LOGIN (creates the session)
=====================================
Client                UsernamePasswordAuthFilter        AuthManager        DaoAuthenticationProvider        UserDetailsService
  | POST /login(user,pass,csrf) ----->|                     |                        |                              |
  |                                   | authenticate() ---->|                        |                              |
  |                                   |                     | delegate -------------->|                              |
  |                                   |                     |                        | hash incoming password       |
  |                                   |                     |                        | loadUserByUsername() ------->|
  |                                   |                     |                        |<---- UserDetails(hash,roles) |
  |                                   |                     |                        | compare hashes                |
  |                                   |                     |<--- Authentication(authenticated=true, roles) ---------|
  |                                   |<--- Authentication -|                        |                              |
  |                                   |
  |                                   v
                       SecurityContextHolder Filter                HttpSessionSecurityContextRepository        Session Store
                              | create SecurityContext(Auth) --------------------> save() ------------------------->|
                              |                                                                                     | create HttpSession
                              |                                                                                     | (id, expiry) + store
                              |                                                                                     | SecurityContext
  Client <-------------------------------------------------- Set-Cookie: JSESSIONID=xyz ------------------------------|
  Client ---- GET / (forwarded) --------------------------------------------------> Controller ---> 200 OK "hello"


STEP 2 — SUBSEQUENT REQUEST (restores session)
===============================================
Client            SecurityContextHolder Filter        HttpSessionSecurityContextRepository        Session Store        Authorization Filter        Controller
  | GET /users (Cookie: JSESSIONID=xyz) ->|                                                                                 |                          |
  |                                       | loadContext(request) ------------------------------------->|                  |                          |
  |                                       |                                                              | findById(xyz) ->|                          |
  |                                       |                                                              |<---- HttpSession(SecurityContext) OR not found
  |                                       |                                                              |                  |                          |
  |                            [found & valid]                                                           |                  |                          |
  |                                       |<--- SecurityContext ------------------------------------------|                  |                          |
  |                                       | SecurityContextHolder.setContext(SecurityContext)             |                  |                          |
  |                                       | ---------------------------------------------------------------------------->|                          |
  |                                       |                                                                                 | check role vs Authentication.roles
  |                                       |                                                                                 | -----> role OK -----------> 200 OK
  |                                       |                                                                                 | -----> role mismatch -----> 403 Forbidden
  |                            [not found / expired]
  |<---------------------------- redirect to /login ------------------------------------------------------------------------|
```

## Session Details & Gotchas

- **`HttpSession` object contents**: session ID, creation time, expiry time, and (once populated) the embedded `SecurityContext` data — plus flags like whether the account is enabled, credentials expired, etc.
- **Default storage**: in memory (e.g. inside Tomcat's servlet container) if nothing else is configured.
- **Default time-to-live**: 30 minutes (depends on the servlet container in use — Tomcat defaults to 30 minutes; can be configured).
- **Inactivity-based expiry, not absolute expiry**: the timeout is a sliding window of *inactivity*. Every time the user makes a request, the expiry time is recalculated from that request's timestamp — so a session only expires after N minutes with *no* activity at all, not N minutes after creation.
- **Multi-instance / distributed problem**: if sessions are stored in memory and there are multiple server instances behind a load balancer, a request that lands on a different instance than the one that created the session won't find it — forcing the user to re-authenticate. This is a bad user experience. The fix is to store sessions in a shared DB (or cache) instead of in memory, using `spring-session-jdbc`.
- **Spring Session JDBC auto-creates two tables**: `SPRING_SESSION` (primary key, session ID, creation time, last access time, max inactive interval, expiry time, principal name) and `SPRING_SESSION_ATTRIBUTES` (the serialized session attribute data, including the serialized `SecurityContext`). The expiry time is recalculated as `last_access_time + max_inactive_interval` on every request.
- It's also possible to manage session tables and expiry entirely manually (this was common practice historically, e.g. around 2015–2016), but relying on Spring's built-in session management is preferred unless the business has custom session requirements.
- **Authorization has two phases**: (1) at the security-filter-chain level (the authorization filter, unique per authentication method), and (2) at the controller level (common to all authentication methods — form login, basic auth, JWT, etc.), which is covered separately.
- **No restrictions by default**: Spring Security does not restrict any endpoint by default — every authenticated user can access every endpoint unless roles are explicitly configured with `.hasRole(...)` / `.hasAnyRole(...)`.
- **CSRF is enabled by default** for form-based login and should **not** be disabled in real applications — form login is vulnerable to CSRF attacks, and CSRF protection exists specifically to defend against that.
- **Session hijacking risk**: because the session ID travels in a cookie, if that cookie is stolen the attacker can access the victim's resources using the stolen session ID.

## Key Code / Config

### Custom `SecurityFilterChain` (customizing login page, public endpoints, and role-based authorization)

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                // Example: making an endpoint public (no authentication required)
                .requestMatchers("/public/**").permitAll()
                // Example: restricting an endpoint to a specific role
                .requestMatchers("/users").hasRole("USER")   // internally becomes ROLE_USER
                // Example: allowing multiple roles on an endpoint
                .requestMatchers("/admin/**").hasAnyRole("USER", "ADMIN")
                .anyRequest().authenticated()
            )
            .formLogin(form -> form
                // omit loginPage(...) to use Spring Boot's default /login page
                .loginPage("/my-login")           // custom login page, if desired
                .permitAll()
            )
            .logout(logout -> logout
                .logoutUrl("/logout")             // default is already /logout
                .permitAll()
            )
            // CSRF is enabled by default for form login — do not disable in production
            // .csrf(csrf -> csrf.disable())
            .sessionManagement(session -> session
                .sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED) // default
                .maximumSessions(1)                   // only 1 active session per user
                .maxSessionsPreventsLogin(true)        // block new logins once limit is hit
            );

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

`SessionCreationPolicy` values:
- `IF_REQUIRED` (default) — a session is only created when actually needed (e.g. after a successful authentication); public endpoints don't get a session.
- `ALWAYS` — a session is always created, even for public endpoints.
- `NEVER` — never creates a new session, but will use one if it already exists.
- `STATELESS` — no session is ever created or used at all (used for stateless auth like JWT).

### Default (hardcoded, dev-only) user + session-in-DB configuration

```properties
# application.properties

# Dev-only hardcoded default user (created at startup) - see previous video for
# the recommended dynamic-user-creation approach for real applications.
spring.security.user.name=user
spring.security.user.password=pass
spring.security.user.roles=USER

# Store the HTTP session in the database instead of in memory (needed once you
# have multiple server instances behind a load balancer).
spring.session.jdbc.initialize-schema=always

# Session timeout: expires after this much continuous inactivity.
server.servlet.session.timeout=5m
```

```xml
<!-- pom.xml -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.session</groupId>
    <artifactId>spring-session-jdbc</artifactId>
</dependency>
```

### Custom `UserDetailsService` (used by `DaoAuthenticationProvider` to load stored user details)

```java
@Service
public class CustomUserDetailsService implements UserDetailsService {

    @Autowired
    private UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String username) {
        User user = userRepository.findByUsername(username)
            .orElseThrow(() -> new UsernameNotFoundException("User not found: " + username));

        return org.springframework.security.core.userdetails.User
            .withUsername(user.getUsername())
            .password(user.getPassword())   // already-hashed password
            .roles(user.getRole())          // e.g. "USER", "ADMIN"
            .build();
    }
}
```

### Default endpoint invoked after successful login

```java
@RestController
public class HomeController {

    @GetMapping("/")
    public String home() {
        return "hello";
    }
}
```

## Important Concepts

- **Stateful authentication**: the server maintains an authentication state (a session) about the client, so credentials only need to be sent once.
- **`HttpSession`**: server-side object holding session ID, creation time, expiry time, and (when populated by Spring Security) the `SecurityContext`.
- **`UsernamePasswordAuthenticationFilter`**: the first filter invoked on `/login`; builds the initial (unauthenticated) `Authentication` object from the submitted credentials.
- **`AuthenticationManager` → `DaoAuthenticationProvider`**: validates credentials by hashing the incoming password, loading stored `UserDetails`, and comparing hashes; returns a fully authenticated `Authentication` object on success.
- **`SecurityContext` / `SecurityContextHolder`**: the container for the `Authentication` object; `SecurityContextHolder` makes it available throughout a request's entire lifecycle (e.g. inside the controller).
- **`HttpSessionSecurityContextRepository`**: creates the `HttpSession` on login and saves the `SecurityContext` in it; on later requests, looks up the `HttpSession` by session ID and restores the `SecurityContext` from it.
- **Authorization filter**: enforces role-based access at the filter-chain level; throws `403 Forbidden` on a role mismatch. This is distinct from controller-level authorization checks, which are common across all authentication methods.
- **`JSESSIONID` cookie**: the session identifier returned to the client after login and sent back on every subsequent request.
- **Session storage**: in memory by default (fine for a single instance); must be moved to a shared DB (`spring-session-jdbc`) or cache once there are multiple server instances behind a load balancer, to avoid forcing re-authentication when requests land on a different instance.
- **Session timeout is inactivity-based**: the expiry time is recalculated from the timestamp of the last activity, not from session creation time.
- **`SessionCreationPolicy`**: `IF_REQUIRED` (default), `ALWAYS`, `NEVER`, `STATELESS`.
- **Per-user session limiting**: `maximumSessions(n)` + `maxSessionsPreventsLogin(true)` restricts how many concurrent sessions a single user (principal) can hold.
- **Disadvantages of form-based/session authentication**: vulnerable to CSRF (mitigated by CSRF protection, which is on by default) and session hijacking; session management is operational overhead (session tables, expiry logic); doesn't scale cleanly in distributed systems without a shared session store, which adds DB/cache lookup latency to every request.

## Interview Q&A

**Q1: What is the default authentication method in Spring Boot Security — is it JWT?**
No. Form-based (session/stateful) authentication is the default. Spring Boot's own `SecurityFilterChain` auto-configuration enables form login (and HTTP basic) unless you explicitly override it — which is why you never need to write a `SecurityFilterChain` bean for form-based login, but you do need to write one to switch to JWT or another method.

**Q2: Where is the session actually created, and what gets stored in it?**
After `DaoAuthenticationProvider` returns a fully authenticated `Authentication` object, a `SecurityContext` is created and populated with it. `HttpSessionSecurityContextRepository` then creates a new `HttpSession` object and stores that `SecurityContext` inside it. The session itself also has metadata like session ID, creation time, and expiry time.

**Q3: How does the server validate a session on a subsequent request, and what filter is responsible?**
The security-context-holder filter runs first (not `UsernamePasswordAuthenticationFilter`, which only runs during the actual login POST). It asks `HttpSessionSecurityContextRepository` to find the `HttpSession` matching the `JSESSIONID` from the request's cookie. If found and valid, the stored `SecurityContext` is extracted and placed into `SecurityContextHolder` for the rest of the request's lifecycle. If not found or expired, the request is redirected to `/login`.

**Q4: Does the session timeout count down from creation time or from last activity?**
From last activity — it's a sliding inactivity window. Every request the user makes resets the countdown, so a session only expires after a period of *total* inactivity equal to the configured timeout, not a fixed time after creation.

**Q5: Why would you store sessions in a database instead of in memory?**
Because in a distributed system with multiple server instances behind a load balancer, a session created in one instance's memory won't be visible to another instance. If a later request lands on a different instance, the server won't recognize the session and will force the user to re-authenticate — a poor user experience. Storing sessions in a shared DB (e.g. via `spring-session-jdbc`) or cache lets every instance look up the same session data.

**Q6: What are the main disadvantages of form-based (stateful) authentication?**
It's vulnerable to CSRF attacks (though CSRF protection is enabled by default and shouldn't be turned off) and to session hijacking if the session cookie is stolen. It also adds session-management overhead (tables, expiry housekeeping) and, in distributed systems, requires a shared session store, which adds DB/cache lookup latency to every request and creates a scalability consideration.
