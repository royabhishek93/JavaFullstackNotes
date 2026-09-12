# Spring Boot Security — OAuth2 Login Implementation (Authorization Code Grant)

## What is this? (Plain English)

Think of "Sign in with Google/GitHub" buttons you see on almost every app today. Instead of that app building its own username/password system and storing your credentials, it borrows your identity from a provider you already trust (GitHub, Auth0, Google...). You log in on the *provider's* page, the provider vouches for you, and your app gets a token proving who you are — without ever seeing your password.

`spring-boot-starter-oauth2-client` is Spring's ready-made implementation of this handshake. You register your app with the provider (getting a client ID/secret), drop a few properties into `application.properties`, flip on `oauth2Login()` in your security config, and Spring Security wires up **all** the redirect filters, token-exchange calls, and session handling for you — no custom OAuth2 protocol code required for the basic flow.

**The core rule:** the app never touches the user's provider password. It only ever sees an **authorization code** (short-lived, one-time) which it exchanges server-to-server for a **token**, and — if using OpenID Connect (OIDC) — an **ID token** that proves identity.

## The Problem It Solves

1. **The user shouldn't have to create yet another account/password** for every third-party app — they reuse an identity they already have with a trusted provider (GitHub, Auth0, Google, etc.).
2. **The third-party app should never see the user's actual provider password** — only a token, scoped to whatever access the user consented to.
3. **Implementing this handshake by hand is tedious and error-prone** — redirect construction, authorization-code exchange, JWT signature verification against a rotating public key (JWKS), session vs. stateless handling. Spring Security's OAuth2 client support does all of this out of the box once it's configured.

### OAuth2 vs OIDC (the distinction the whole implementation hinges on)

| | OAuth2 | OIDC (OpenID Connect) |
|---|---|---|
| Purpose | **Authorization** — grant a third party access to protected data (e.g. read your Gmail, calendar) | **Authentication** — verify *who* the user is |
| Built on | — | A layer on top of OAuth2 |
| Token returned | Access token (often **opaque** — no dots, unreadable by the client; only the authorization server understands it) | **ID token**, always a **JWT** (three dot-separated parts: header, claims, signature) |
| What the token contains | Nothing meaningful to the client — must be sent back to the resource server to be understood | Minimal user info (profile, username, email, picture) needed purely for authentication |
| Scope used | `read`, `write`, etc. | `openid` — tells the authorization server "this client only wants to authenticate the user" |
| Can it fetch more protected data afterward? | Yes — that's the whole point | Not with the ID token; it's meant only for the third-party app, not for calling the resource server |

Because the implementation in this note uses scope `openid`, the token that matters is the **ID token**, and the authentication provider Spring Security picks internally is the **OIDC** authorization-code provider (not the plain OAuth2 one).

## Login + Token Exchange + Stateless Validation Flow (ASCII)

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

```text
User                Spring Boot App              Authorization Server        Custom Success   Custom Validation
(Browser)           (Security Filter Chain)      (GitLab / Auth0)            Handler          Filter
  |                        |                             |                        |                 |
  |--GET /login----------->|                             |                        |                 |
  |<--login page (links per registration-id from-------- |                        |                 |
  |   application.properties: GitLab, Auth0)              |                        |                 |
  |                        |                             |                        |                 |
  |--click "GitLab"------->|                             |                        |                 |
  |  GET /oauth2/authorization/gitlab                     |                        |                 |
  |          (OAuth2AuthorizationRequestRedirectFilter)   |                        |                 |
  |                        |--302 redirect (client_id,--->|                        |                 |
  |                        |  redirect_uri, scope=openid) |                        |                 |
  |<-----------------------|-----------------------------|  show login+consent    |                 |
  |--submit username/password + consent------------------>|                        |                 |
  |<-----------------------|--302 redirect to redirect_uri (authorization code)----|                 |
  |--GET /login/oauth2/code/gitlab?code=...--------------->|                        |                 |
  |                        | (OAuth2LoginAuthenticationFilter catches callback)    |                 |
  |                        | builds OAuth2LoginAuthenticationToken(code)           |                 |
  |                        | -> AuthenticationManager -> OidcAuthorizationCodeAuthenticationProvider  |
  |                        |--POST token URI (code, client_id, client_secret)----->|                 |
  |                        |<--access_token + id_token (JWT) [+ refresh_token]-----|                 |
  |                        | store tokens in OAuth2AuthorizedClientService (in-memory, default)       |
  |                        |----------------------------------------------------->| onAuthenticationSuccess()
  |<-----------------------------------------------------------------------------| response body: { id_token }
  |                        |                             |                        |  (stateless, no session cookie)
  |                        |                             |                        |                 |
  |--GET /user  Authorization: Bearer <id_token>--------->|                        |                 |
  |                        |------------------------------------------------------------------------>| extract token,
  |                        |                             |                        |                 | parse "issuer" claim
  |                        |                             |<-----------------------------------------| JwtDecoder.withIssuerLocation(issuer)
  |                        |                             |--JWK Set URI: public key---------------->| verify signature
  |                        |<-----------------------------------------------------------------------| valid -> set
  |                        |                             |                        |                 | SecurityContextHolder
  |<--200 "fetched details successfully"------------------|                        |                 |
```

## Registration Step (Before Any Code)

The Spring Boot app is the OAuth2 **client** (the "third-party app"). Before writing anything, it must be registered with each authorization server it wants to support:

- **GitLab**: Settings → Applications → add application name, **redirect URI** (where the auth server sends the authorization code back), and **scope** — `openid` was selected here since only authentication (read-only profile access) is needed, not broader read/write access.
- **Auth0** ("O-zero"): same idea — create an application, enable OIDC, choose a signing algorithm (RS256 — asymmetric, private key signs, public key verifies, same as in JWT topics), and configure redirect URI/scope.

Both registrations return a **client ID** and a **client secret** — the secret is shown only once and must be copied/stored immediately (it can be regenerated later, invalidating the old one).

**Gotcha:** across different authorization servers, the URL *shape* is nearly identical — `authorization-uri`, `token-uri`, `issuer-uri`, `jwk-set-uri` — only the hostname/authorization server changes. Adding a new provider is mostly copy-paste of the same property block with a different `registrationId`.

## Key Code / Config

### 1. `pom.xml` — the one dependency needed for the whole flow

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-oauth2-client</artifactId>
</dependency>
```

### 2. `application.properties` — client registration + provider details

```properties
# ---- GitLab registration ----
spring.security.oauth2.client.registration.gitlab.client-id=YOUR_GITLAB_CLIENT_ID
spring.security.oauth2.client.registration.gitlab.client-secret=YOUR_GITLAB_CLIENT_SECRET
spring.security.oauth2.client.registration.gitlab.scope=openid
spring.security.oauth2.client.registration.gitlab.authorization-grant-type=authorization_code
spring.security.oauth2.client.registration.gitlab.redirect-uri={baseUrl}/login/oauth2/code/{registrationId}

spring.security.oauth2.client.provider.gitlab.authorization-uri=https://gitlab.com/oauth/authorize
spring.security.oauth2.client.provider.gitlab.token-uri=https://gitlab.com/oauth/token
spring.security.oauth2.client.provider.gitlab.issuer-uri=https://gitlab.com
spring.security.oauth2.client.provider.gitlab.jwk-set-uri=https://gitlab.com/oauth/discovery/keys

# ---- Auth0 registration ----
spring.security.oauth2.client.registration.auth0.client-id=YOUR_AUTH0_CLIENT_ID
spring.security.oauth2.client.registration.auth0.client-secret=YOUR_AUTH0_CLIENT_SECRET
spring.security.oauth2.client.registration.auth0.scope=openid
spring.security.oauth2.client.registration.auth0.authorization-grant-type=authorization_code
spring.security.oauth2.client.registration.auth0.redirect-uri={baseUrl}/login/oauth2/code/{registrationId}

spring.security.oauth2.client.provider.auth0.authorization-uri=https://YOUR_DOMAIN.auth0.com/authorize
spring.security.oauth2.client.provider.auth0.token-uri=https://YOUR_DOMAIN.auth0.com/oauth/token
spring.security.oauth2.client.provider.auth0.issuer-uri=https://YOUR_DOMAIN.auth0.com/
spring.security.oauth2.client.provider.auth0.jwk-set-uri=https://YOUR_DOMAIN.auth0.com/.well-known/jwks.json
```

- `registration.<id>.*` — describes *this app's* credentials/scope for that provider ("registration id" is just the key you pick, e.g. `gitlab`, `auth0`).
- `provider.<id>.*` — describes the provider's well-known endpoints: `authorization-uri` (where the browser is redirected to log in and consent), `token-uri` (server-to-server exchange of code → tokens), `issuer-uri` (who issued the token — used to validate it), `jwk-set-uri` (where the provider's public key lives, used to verify the JWT signature).

### 3. Basic `SecurityConfig` — the "it just works" version

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
            .oauth2Login(Customizer.withDefaults()); // default /login page + default redirect handling
        return http.build();
    }
}
```

With just the dependency, the two property blocks above, and this three-line security config, Spring Security automatically provides:
- a default `/login` page listing every configured registration,
- the `/oauth2/authorization/{registrationId}` redirect endpoint,
- authorization-code exchange for tokens,
- session creation and `SecurityContextHolder` population on success.

### 4. Basic controller used to test the flow

```java
@RestController
public class HomeController {

    @GetMapping("/")
    public String home() {
        return "Hello, you are logged in";
    }

    @GetMapping("/user")
    public String user() {
        return "Fetched the details successfully";
    }
}
```

### 5. Gotcha #1 — stateful by default, breaks in Postman

With the config above, logging in through a **browser** works because Spring Security creates an **HTTP session** on successful authentication and returns a session cookie; every subsequent request just checks "is there a valid session?" — it does **not** re-validate the underlying token on each request. Hitting `/user` from **Postman** without that session cookie fails and re-triggers the login redirect, because Postman never received/stored the cookie.

This also means it's possible for the ID token to expire or become invalid while the **session** is still active — the session filter grants access purely because the session exists, without re-checking the token.

### 6. Making it stateless — custom success handler returns the ID token

```java
@Component
public class CustomOAuth2LoginSuccessHandler implements AuthenticationSuccessHandler {

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request,
                                         HttpServletResponse response,
                                         Authentication authentication) throws IOException {
        OAuth2AuthenticationToken oauthToken = (OAuth2AuthenticationToken) authentication;
        OidcUser oidcUser = (OidcUser) oauthToken.getPrincipal();
        String idToken = oidcUser.getIdToken().getTokenValue();

        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write("{\"id_token\":\"" + idToken + "\"}");
    }
}
```

### 7. Custom validation filter — verifies the ID token on every request

```java
@Component
public class OAuth2ValidationFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {

        String authHeader = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (authHeader != null && authHeader.startsWith("Bearer ")) {
            String token = authHeader.substring(7);

            if (isTokenValid(token)) {
                Authentication authentication =
                        new UsernamePasswordAuthenticationToken("oauth2-user", null, Collections.emptyList());
                SecurityContextHolder.getContext().setAuthentication(authentication);
            }
        }
        filterChain.doFilter(request, response);
    }

    // Reads the "iss" claim out of the JWT, then lets Spring build a JwtDecoder
    // that fetches the provider's JWK Set URI and verifies the signature.
    private boolean isTokenValid(String token) {
        String issuer = JwtHelper.extractIssuer(token); // parses the unverified JWT claims to read "iss"
        JwtDecoder jwtDecoder = JwtDecoders.fromIssuerLocation(issuer);
        try {
            jwtDecoder.decode(token); // fetches JWKS, verifies signature, throws if invalid
            return true;
        } catch (JwtException ex) {
            return false;
        }
    }
}
```

### 8. Updated `SecurityConfig` — stateless + custom success handler + custom filter

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final CustomOAuth2LoginSuccessHandler successHandler;
    private final OAuth2ValidationFilter oAuth2ValidationFilter;

    public SecurityConfig(CustomOAuth2LoginSuccessHandler successHandler,
                           OAuth2ValidationFilter oAuth2ValidationFilter) {
        this.successHandler = successHandler;
        this.oAuth2ValidationFilter = oAuth2ValidationFilter;
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth.anyRequest().authenticated())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .oauth2Login(oauth2 -> oauth2.successHandler(successHandler))
            .addFilterBefore(oAuth2ValidationFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }
}
```

## Important Concepts

- **Resource owner**: the user, who owns the data on the resource server (e.g. GitLab profile).
- **Client (third-party app)**: the Spring Boot app in this note — registered with the authorization server to obtain a client ID/secret.
- **Authorization server**: issues authorization codes and tokens (GitLab, Auth0 here); also exposes the JWKS endpoint for signature verification.
- **Registration ID**: the key (`gitlab`, `auth0`) used to namespace each provider's config in `application.properties`; it's also appended to the well-known endpoints Spring Security exposes, e.g. `/oauth2/authorization/{registrationId}`.
- **Authorization code**: short-lived, one-time code returned to the redirect URI after the user authenticates and consents; exchanged server-to-server for tokens.
- **Access token**: used to call resource-server APIs for protected data; may be **opaque** (unreadable by the client, e.g. GitLab's) or a JWT, depending on the provider.
- **ID token**: OIDC-specific, always a JWT, contains minimal profile info needed purely for authentication, meant only for the client app — never sent to the resource server.
- **`scope=openid`**: tells the authorization server "this client only wants to authenticate the user," which is why an ID token (not just an access token) comes back.
- **`DefaultLoginPageGeneratingFilter`**: auto-generates the `/login` page listing every configured registration, reading the info straight from `application.properties`.
- **`OAuth2AuthorizationRequestRedirectFilter`**: handles `/oauth2/authorization/{registrationId}`, redirecting the browser to the provider's authorization endpoint with the client ID.
- **`OAuth2LoginAuthenticationFilter`**: catches the callback at the redirect URI, builds the authentication token containing the authorization code.
- **`OidcAuthorizationCodeAuthenticationProvider`**: the provider chosen automatically because the `openid` scope is used; calls the token URI and extracts the ID token from the response.
- **`OAuth2AuthorizedClientService`**: stores the exchanged tokens — in-memory by default, but overridable to persist to a database.
- **Stateful vs. stateless**: by default Spring creates an HTTP session on login success and trusts the session cookie afterward (no re-validation of the token per request); can be switched to `SessionCreationPolicy.STATELESS` plus a custom filter that re-validates the token (via JWKS) on every single request.
- **`JwtDecoder` / `JwtDecoders.fromIssuerLocation(issuer)`**: given an issuer, automatically resolves that provider's JWKS endpoint, fetches the public key, and verifies the JWT's signature.

## Interview Q&A

**Q1: Why does Spring Security choose `OidcAuthorizationCodeAuthenticationProvider` instead of the plain OAuth2 authentication provider here?**
Because the client registration's scope is `openid`. Spring Security inspects the requested scope and authentication token type; when `openid` is present it routes authentication through the OIDC-specific provider, which knows how to extract and validate the ID token rather than just an opaque access token.

**Q2: Why does calling `/user` work fine from a browser but fail from Postman with the default (stateful) configuration?**
Because Spring Security's default `oauth2Login()` flow authenticates once and stores the result in an HTTP session, returning a session cookie. The browser automatically resends that cookie on every subsequent request, so the session filter grants access without re-checking the token. Postman never received/stored that cookie, so it has no session and gets redirected back to `/login`.

**Q3: If the session is still active, does that guarantee the underlying ID token is still valid?**
No — that's exactly the trap. In the stateful flow, once a session exists, access is granted purely because the session is present; the ID token itself isn't re-validated on each request. The token could technically expire or be revoked while the session remains active and requests would still succeed.

**Q4: How do you make the OAuth2 login flow stateless instead of session-based?**
Set `sessionManagement().sessionCreationPolicy(SessionCreationPolicy.STATELESS)` in the security config, return the ID token to the client from a custom `AuthenticationSuccessHandler` on login success, and add a custom `OncePerRequestFilter` that extracts the `Authorization: Bearer <token>` header on every request and validates it via a `JwtDecoder` built from the token's issuer before setting the `SecurityContextHolder`.

**Q5: How is the ID token cryptographically validated without hardcoding a public key?**
The filter first parses the unverified JWT to read the `iss` (issuer) claim, then calls `JwtDecoders.fromIssuerLocation(issuer)`, which uses the corresponding `jwk-set-uri` from `application.properties` to fetch the provider's current public key(s) and verify the JWT's signature — the same asymmetric private-key-signs/public-key-verifies model used for any JWT.

**Q6: Why is GitLab's access token not a JWT, while the ID token always is?**
GitLab issues an **opaque** access token — just an identifier string, no dots, meaningless to anyone except GitLab's own authorization server; the client must send it back to GitLab to get anything useful. The **ID token**, however, is defined by the OIDC spec to always be a JWT (header.claims.signature) so that the client itself can decode and read the user's basic profile info directly, without another network call.
