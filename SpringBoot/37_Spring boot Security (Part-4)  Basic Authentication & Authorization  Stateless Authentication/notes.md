# Spring Security — HTTP Basic Authentication (Stateless Authentication)

## What is this? (Plain English)

Imagine a building where, instead of issuing you a visitor badge after checking your ID once, the security guard makes you show your passport **every single time** you walk through **any** door — the lobby, the elevator, your office, the cafeteria. No badge is ever issued, so the guard remembers nothing about you between doors; each door check is a fresh, independent verification of your passport.

That's HTTP Basic Authentication: the client attaches its username and password to **every** request (inside the `Authorization` header, Base64-encoded), and the server validates those credentials from scratch on every single call. No session, no token, no memory of "you already proved who you are five seconds ago." This is why it's called **stateless** authentication — the server holds no authentication state between requests, unlike form-based login (stateful), where a session is created once and then reused via a session ID/cookie on subsequent requests.

## The Problem It Solves

Form-based login (seen in earlier videos) is a two-step, stateful flow: (1) the user submits username/password once, a session is created and stored, and (2) subsequent requests just carry the session identifier, which the server looks up to know "who is this and are they authenticated."

Basic Authentication collapses this into **a single step per request**: the username and password themselves are sent with every request, authenticated and authorized in that same request — there is no "second call" that merely carries a session token. This is useful when you explicitly don't want the server to maintain any session state (e.g. simple service-to-service calls, quick testing, or systems that must remain fully stateless).

## How Credentials Are Sent

The client sends the literal string `username:password`, Base64-encodes it, and places it in the `Authorization` header:

```
Authorization: Basic <Base64(username:password)>
```

Important: Base64 is **encoding, not encryption**. Anyone who intercepts the header can trivially decode it back to `username:password` in plain text. This is why Basic Authentication must **only ever be used over HTTPS** — never over plain HTTP — since HTTPS is the only thing actually protecting the credentials in transit.

### Why the `Authorization` header specifically (not body or query params)?

1. **Standardization** — [RFC 7617](https://datatracker.ietf.org/doc/html/rfc7617) mandates that HTTP credentials be passed via the `Authorization` header. Without a single standard, every client/framework would invent its own convention (body, query param, custom header), making interoperability painful.
2. **Security** — Many web servers/proxies log request bodies and query parameters (for debugging or analytics), often via third-party logging tools the company doesn't fully control. Headers are typically **not** logged, so keeping credentials in a header reduces the risk of accidental exposure.
3. **Support for all HTTP methods** — `GET` requests generally don't carry a body, so a body-based credential scheme wouldn't work consistently across `GET`, `POST`, `PUT`, etc. A header is always available regardless of method or body presence, keeping the scheme consistent across all request types.

## The Authentication Flow (Sequence Diagram, ASCII)

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

```text
Client                BasicAuthFilter        AuthManager/DaoProvider        SecurityContextHolder      AuthorizationFilter      Controller
  |                          |                          |                            |                        |                    |
  |--GET /api/users--------->|                          |                            |                        |                    |
  |   (no Authorization)     |                          |                            |                        |                    |
  |<--401 + WWW-Authenticate-|                          |                            |                        |                    |
  |                          |                          |                            |                        |                    |
  [Client Base64-encodes "username:password"]
  |                          |                          |                            |                        |                    |
  |--GET /api/users--------->|                          |                            |                        |                    |
  |  Authorization: Basic..  |                          |                            |                        |                    |
  |                          |--decode header----------->|                            |                        |                    |
  |                          |  (username, password)    |                            |                        |                    |
  |                          |--Authentication(false)--->|                            |                        |                    |
  |                          |                          |--hash password (PasswordEncoder)                    |                    |
  |                          |                          |--fetch UserDetails (DB/in-memory)                   |                    |
  |                          |                          |--compare hashed vs stored-->|                        |                    |
  |                          |                          |   MATCH                    |                        |                    |
  |                          |<--Authentication(true)----|                            |                        |                    |
  |                          |--store in SecurityContext--------------------------->  |                        |                    |
  |                          |--forward request-------------------------------------------------------------->|                    |
  |                          |                          |                            |     check role required vs user's role       |
  |                          |                          |                            |             MATCH ------>|-------forward---->|
  |<-----------------------------------------------------------------------------------------------------200 OK response-----------|
  |                          |                          |                            |                        |                    |
  [No session anywhere — the ENTIRE sequence above repeats from step 1 on the NEXT request]
```

## What Happens When Roles Don't Match

If the authenticated user's role doesn't satisfy the role required for the endpoint (e.g. endpoint requires `ROLE_USER` but the authenticated user only has `ROLE_ADMIN`), the authorization filter rejects the request with **403 Forbidden** — authentication succeeded, but authorization failed.

## Key Code / Config

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // Override Spring Boot's default (form-based login) with HTTP Basic
            .httpBasic(Customizer.withDefaults())
            // Stateless: never create or use an HTTP session
            .sessionManagement(session ->
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            // CSRF protection is only relevant when sessions/cookies are involved;
            // not applicable to stateless, credential-per-request authentication
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/users").hasRole("USER")
                .anyRequest().authenticated()
            );
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

Hardcoded in-memory user for testing (username `user`, password `pass`, role `ADMIN`):

```java
@Bean
public UserDetailsService userDetailsService(PasswordEncoder passwordEncoder) {
    UserDetails user = User.builder()
        .username("user")
        .password(passwordEncoder.encode("pass"))
        .roles("ADMIN")
        .build();
    return new InMemoryUserDetailsManager(user); // stored in memory, not DB
}
```

Only the `spring-boot-starter-security` dependency is required — the JDBC/session-store dependency used for form-based login (to persist sessions in a DB) is **not needed** here, since Basic Authentication never creates a session at all.

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```

Sample request header sent by the client:

```
GET /api/users HTTP/1.1
Authorization: Basic dXNlcjpwYXNz
```

(`dXNlcjpwYXNz` is simply `Base64("user:pass")` — trivially reversible, which is why HTTPS is mandatory.)

## Disadvantages of Basic Authentication

1. **Security exposure** — credentials travel with every single request. If HTTPS isn't enforced, they can be intercepted and decoded (Base64 is not encryption). And unlike a session or token, if credentials are compromised there is no way to "invalidate" just that session — the only remedy is changing the password itself.
2. **Poor user experience for large-scale applications** — the same username/password must be validated on every request, which doesn't scale well as an authentication *experience* (no "stay logged in").
3. **Performance overhead per request**:
   - **Increased request size** — every request carries the encoded `Authorization` header, adding bytes to each call.
   - **Repeated decode + hash work** — the header must be decoded and the incoming password hashed on every request (at scale, e.g. 1 billion requests/day, this work is repeated 1 billion times).
   - **DB/user-store lookup on every request** — the stored username/password must be fetched (from DB or in-memory store) and compared on every single call, adding latency compared to a cached session lookup.

Because of these overheads and security tradeoffs, Basic Authentication — despite being simple and genuinely stateless — is not popular for large-scale production systems. This is the motivation for token-based schemes like **JWT**, covered next.

## Important Concepts

- **Basic Authentication**: Stateless auth scheme where the client sends `username:password` (Base64-encoded) in the `Authorization` header on every request; the server has no memory of prior requests.
- **Stateless**: No session is ever created or maintained (`SessionCreationPolicy.STATELESS`) — contrast with form-based login, which is stateful and reuses a session after one initial credential check.
- **Base64 encoding ≠ encryption**: Trivially reversible; Basic Auth must only be used over HTTPS.
- **RFC 7617**: The HTTP standard mandating that credentials be sent via the `Authorization` header for interoperability across clients/frameworks.
- **`BasicAuthenticationFilter`**: The Spring Security filter that decodes the `Authorization` header and builds an unauthenticated `Authentication` object from the extracted username/password.
- **`AuthenticationManager` → `DaoAuthenticationProvider`**: Delegate that hashes the incoming password (via `PasswordEncoder`), fetches stored `UserDetails` (via `UserDetailsService`), and compares them.
- **`SecurityContextHolder`**: Stores the authenticated `Authentication` object for the duration of the request only (no persistence across requests, since there's no session).
- **Authorization filter**: Runs after authentication succeeds; checks whether the authenticated user's role satisfies the role required for the requested endpoint — mismatch results in `403 Forbidden`.
- **CSRF disabled for Basic Auth**: CSRF protection matters for session/cookie-based (stateful) flows; it doesn't apply to stateless, credential-per-request schemes.
- **No dependency on session-store**: Unlike form-based login (which may persist sessions to a DB), Basic Authentication only needs `spring-boot-starter-security` — no session-store dependency at all.

## Interview Q&A

**Q1: Why is Basic Authentication called "stateless"?**
A: Because the server does not create or store any session for the user. Every request must independently carry and prove the user's identity via the `Authorization` header; the server retains no memory of previous requests.

**Q2: Is the password sent in Basic Authentication encrypted?**
A: No — it's only Base64-**encoded**, which is trivially reversible. It is not encryption. This is exactly why Basic Authentication must always run over HTTPS; without TLS, anyone intercepting the request can decode the credentials instantly.

**Q3: Why are credentials sent in the `Authorization` header instead of the request body or a query parameter?**
A: Three reasons: (1) RFC 7617 standardizes header-based credential transport so all clients/frameworks interoperate consistently; (2) headers are less likely to be logged by web servers/proxies than bodies or query parameters, reducing accidental credential exposure; (3) headers work uniformly across all HTTP methods, including `GET`, which typically has no body.

**Q4: How does Basic Authentication compare to form-based (session) login?**
A: Form-based login is stateful and two-phase — the user submits credentials once, a session is created, and subsequent requests just carry the session ID. Basic Authentication is stateless and single-phase — the username and password are sent, authenticated, and authorized within the *same* request every time, with no session ever created.

**Q5: What happens if the authenticated user doesn't have the required role for an endpoint?**
A: Authentication succeeds (their credentials are valid), but the authorization filter rejects the request with a `403 Forbidden` because their role doesn't satisfy what the endpoint requires.

**Q6: Why isn't Basic Authentication popular for large-scale production systems despite being simple and stateless?**
A: It has real overhead on every single request: increased request size from the encoded header, repeated password-hashing and header-decoding work, and a DB/user-store lookup to validate credentials each time — none of which can be cached the way a session lookup can. There's also no way to "revoke" compromised credentials short of changing the password entirely (no session/token to invalidate). These tradeoffs are what motivate token-based schemes like JWT.
