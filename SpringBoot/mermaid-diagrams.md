## [Q12_circuit_breaker_resilience4j.md] State Diagram (Mermaid)

```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open: failure rate exceeds threshold
    Open --> HalfOpen: wait duration elapses
    HalfOpen --> Closed: success threshold met
    HalfOpen --> Open: probe call fails
```

## [40_OAuth 2.0 Explained with API Request and Response Sample  High Level System Design/notes.md] Sequence Diagram

```mermaid
sequenceDiagram
    actor User as Resource Owner (Shan)
    participant Client as Client (Instagram)
    participant AuthServer as Authorization Server (Gmail)
    participant ResServer as Resource Server (Gmail)

    Note over Client,AuthServer: One-time setup
    Client->>AuthServer: POST /register (client_name, redirect_uris)
    AuthServer-->>Client: client_id, client_secret

    Note over User,ResServer: Authorization Code Grant flow
    User->>Client: Click "Sign in with Gmail"
    Client->>User: Redirect to /authorize?response_type=code&client_id=...&redirect_uri=...&scope=...&state=sj1
    User->>AuthServer: Authenticate (login) + view consent screen
    AuthServer->>User: Show consent ("Instagram wants email, profile, address")
    User->>AuthServer: Approve consent
    AuthServer-->>Client: Redirect to redirect_uri?code=AUTH_CODE&state=sj1
    Client->>Client: Verify returned state == sj1 (CSRF check)
    Client->>AuthServer: POST /token (grant_type=authorization_code, code, redirect_uri, client_id, client_secret)
    AuthServer-->>Client: access_token, refresh_token, expires_in=3600, token_type=Bearer
    Client->>ResServer: GET /profile (Authorization: Bearer access_token)
    ResServer->>AuthServer: Validate access_token
    AuthServer-->>ResServer: valid / invalid
    alt token valid
        ResServer-->>Client: 200 OK { name, email, address }
        Client-->>User: Signed in successfully
    else token invalid
        ResServer-->>Client: 401 Unauthorized
    end
```

## [16_Spring boot @Transactional Annotation - Part3  Isolation Level and its different types/notes.md] Isolation Level Ladder (Mermaid)

```mermaid
flowchart TD
    A["READ_UNCOMMITTED<br/>No shared lock on read, no lock held on write<br/>Suffers: Dirty Read, Non-Repeatable Read, Phantom Read"]
    B["READ_COMMITTED<br/>Shared lock on read (released immediately after read)<br/>Exclusive lock on write (held until commit/rollback)<br/>Eliminates: Dirty Read"]
    C["REPEATABLE_READ<br/>Shared lock on read (held until end of transaction)<br/>Exclusive lock on write (held until end of transaction)<br/>Eliminates: + Non-Repeatable Read"]
    D["SERIALIZABLE<br/>Same as REPEATABLE_READ + range lock on the query's row range<br/>Eliminates: + Phantom Read"]

    A -->|"add read-lock + release-after-read,<br/>hold write-lock till end of txn"| B
    B -->|"hold read-lock till end of txn<br/>instead of releasing immediately"| C
    C -->|"apply range lock over the<br/>queried row range"| D

    style A fill:#ffcccc
    style B fill:#ffe0b3
    style C fill:#fff2b3
    style D fill:#ccffcc
```

## [Q3_transactional_proxy_flow.md] Sequence Diagram (Mermaid)

```mermaid
sequenceDiagram
    participant Caller
    participant Proxy as OrderService$$CGLIB (proxy)
    participant Pool as Connection Pool
    participant Real as OrderService (real)
    participant DB

    Caller->>Proxy: placeOrder(order)
    Proxy->>Pool: borrow connection
    Pool-->>Proxy: conn1
    Proxy->>Proxy: conn1.setAutoCommit(false)
    Proxy->>Real: super.placeOrder(order)
    Real->>DB: INSERT INTO orders (conn1)
    Real->>DB: INSERT INTO payments (conn1)
    Real-->>Proxy: returns
    Proxy->>DB: conn1.commit()
    Proxy-->>Caller: result
```

## [webflux-senior-interview-questions.md] Event Loop Architecture (Mermaid)

```mermaid
flowchart LR
    Clients["20k concurrent clients"] --> EL["Netty Event Loop (small fixed thread pool, e.g. 8 threads)"]
    EL -->|non-blocking dispatch| Pipeline["Reactive pipeline (Mono/Flux)"]
    Pipeline -->|async I/O callback resumes| EL
    EL --> Response["Response streamed back"]
```

## [36_Spring boot Security (Part-3)  Form Based Authentication & Authorization  Stateful Authentication/notes.md] Sequence Diagram

```mermaid
sequenceDiagram
    participant C as Client
    participant UPF as UsernamePasswordAuthenticationFilter
    participant AM as AuthenticationManager
    participant DAP as DaoAuthenticationProvider
    participant UDS as UserDetailsService
    participant SCF as SecurityContextHolder Filter
    participant REPO as HttpSessionSecurityContextRepository
    participant SESSION as Session Store (memory / DB)
    participant AUTHZ as Authorization Filter
    participant CTRL as Controller

    Note over C,CTRL: Step 1 — Login (creates the session)
    C->>UPF: POST /login (username, password, csrf)
    UPF->>AM: authenticate(UsernamePasswordAuthenticationToken)
    AM->>DAP: delegate
    DAP->>DAP: hash incoming raw password
    DAP->>UDS: loadUserByUsername(username)
    UDS-->>DAP: UserDetails (hashed password, roles)
    DAP->>DAP: compare hashes
    DAP-->>AM: Authentication (authenticated=true, roles set)
    AM-->>UPF: Authentication
    UPF->>SCF: pass Authentication forward
    SCF->>SCF: create SecurityContext(Authentication)
    SCF->>REPO: save(SecurityContext)
    REPO->>SESSION: create HttpSession(id, expiry) + store SecurityContext
    SESSION-->>REPO: session persisted
    REPO-->>C: Set-Cookie: JSESSIONID=xyz
    C->>CTRL: (forwarded) GET / 
    CTRL-->>C: 200 OK "hello"

    Note over C,CTRL: Step 2 — Subsequent authenticated request (restores session)
    C->>SCF: GET /users (Cookie: JSESSIONID=xyz)
    SCF->>REPO: loadContext(request)
    REPO->>SESSION: findById(JSESSIONID)
    alt session found and not expired
        SESSION-->>REPO: HttpSession (with SecurityContext)
        REPO-->>SCF: SecurityContext
        SCF->>SCF: SecurityContextHolder.setContext(SecurityContext)
        SCF->>AUTHZ: continue filter chain
        AUTHZ->>AUTHZ: check required role vs Authentication roles
        alt role matches
            AUTHZ->>CTRL: allow request
            CTRL-->>C: 200 OK
        else role mismatch
            AUTHZ-->>C: 403 Forbidden
        end
    else session not found / expired
        REPO-->>C: redirect to /login
    end
```

## [Q5_transactional_propagation_deep_dive.md] Side-by-Side Comparison (Mermaid)

```mermaid
flowchart TB
    subgraph REQUIRED["REQUIRED (default)"]
        direction LR
        R1["placeOrder() on conn#42"] --> R2["inventoryService joins SAME conn#42"] --> R3["single commit"]
    end
    subgraph REQUIRES_NEW["REQUIRES_NEW"]
        direction LR
        N1["placeOrder() on conn#42"] --> N2["SUSPEND conn#42"] --> N3["auditService on NEW conn#99"] --> N4["commit conn#99"] --> N5["RESUME conn#42"]
    end
    subgraph NESTED["NESTED"]
        direction LR
        S1["placeOrder() on conn#42"] --> S2["SAVEPOINT sp1"] --> S3["rewardService fails"] --> S4["ROLLBACK TO sp1 (outer TX survives)"]
    end
```

## [15_Spring boot @Transactional Annotation - Part2  Declarative, Programmatic Approach and Propagation/notes.md] Propagation Decision Flow

```mermaid
flowchart TD
    Start["Method B is invoked from Method A.<br/>Method B has @Transactional"] --> CheckProp{"What propagation<br/>is set on Method B?"}

    CheckProp -->|"REQUIRED (default)"| ReqCheck{"Does a parent<br/>transaction exist?"}
    ReqCheck -->|Yes| JoinParent["Join the parent transaction<br/>no new transaction is created"]
    ReqCheck -->|No| CreateNew1["Create a brand new transaction"]

    CheckProp -->|REQUIRES_NEW| ReqNewCheck{"Does a parent<br/>transaction exist?"}
    ReqNewCheck -->|Yes| SuspendCreate["Suspend the parent transaction,<br/>create an independent new one,<br/>resume parent after commit/rollback"]
    ReqNewCheck -->|No| CreateNew2["Create a brand new transaction"]

    CheckProp -->|SUPPORTS| SupCheck{"Does a parent<br/>transaction exist?"}
    SupCheck -->|Yes| JoinParent2["Join the parent transaction"]
    SupCheck -->|No| NoTxn1["Run with NO transaction at all"]

    CheckProp -->|NOT_SUPPORTED| NotSupCheck{"Does a parent<br/>transaction exist?"}
    NotSupCheck -->|Yes| SuspendNoTxn["Suspend the parent transaction,<br/>run with no transaction,<br/>resume parent after"]
    NotSupCheck -->|No| NoTxn2["Run with NO transaction at all"]

    CheckProp -->|MANDATORY| MandCheck{"Does a parent<br/>transaction exist?"}
    MandCheck -->|Yes| JoinParent3["Join the parent transaction"]
    MandCheck -->|No| ThrowEx1["Throw IllegalTransactionStateException"]

    CheckProp -->|NEVER| NeverCheck{"Does a parent<br/>transaction exist?"}
    NeverCheck -->|Yes| ThrowEx2["Throw IllegalTransactionStateException"]
    NeverCheck -->|No| NoTxn3["Run with NO transaction at all"]
```

## [43_Spring Boot Actuator in depth/notes.md] Actuator Endpoint Request Flow

```mermaid
flowchart TD
    A["HTTP Request: GET /manage/health"] --> B{"Is endpoint exposed?<br/>management.endpoints.web.exposure.include"}
    B -- "not in include list<br/>(default only health, info)" --> B1["404 Not Found"]
    B -- "exposed" --> C["Security Filter Chain:<br/>health, info -> permitAll<br/>everything else -> authenticated"]
    C --> D{"Authenticated?"}
    D -- "No" --> D1["401 Unauthorized"]
    D -- "Yes / not required" --> E["Endpoint Handler Dispatch"]

    E --> F["Health Endpoint"]
    E --> G["Metrics Endpoint"]
    E --> H["Custom Actuator Endpoint<br/>@Endpoint id=myCustomStats"]

    F --> F1["DatabaseHealthIndicator.health()"]
    F --> F2["CacheHealthIndicator.health()"]
    F1 --> F3["Aggregate Status<br/>UP only if all components UP"]
    F2 --> F3
    F3 --> F4{"show-details=always?"}
    F4 -- "yes" --> F5["Return status + per-component details"]
    F4 -- "no" --> F6["Return aggregated status only"]

    G --> G1["MeterRegistry lookup<br/>e.g. jvm.memory.used, http.server.requests"]
    G1 --> G2["Return metric measurements"]

    H --> H1{"HTTP method + selectors"}
    H1 -- "GET" --> H2["@ReadOperation method"]
    H1 -- "POST" --> H3["@WriteOperation method<br/>always requires auth"]
    H1 -- "DELETE" --> H4["@DeleteOperation method<br/>always requires auth"]

    F5 --> Z["HTTP Response"]
    F6 --> Z
    G2 --> Z
    H2 --> Z
    H3 --> Z
    H4 --> Z
```

## [Q16_microservices_distributed_traps.md] Sequence Diagram (Mermaid)

```mermaid
sequenceDiagram
    participant O as OrderService
    participant I as InventoryService
    participant P as PaymentService

    O->>O: create order
    O-->>I: OrderCreated event
    I->>I: decrement inventory
    I-->>P: InventoryReserved event
    P->>P: charge payment
    alt payment fails
        P-->>I: PaymentFailed event
        I->>I: release reservation
        I-->>O: OrderCancelled event
        O->>O: mark order CANCELLED
    else payment succeeds
        P-->>O: OrderCompleted event
    end
```

## [Q8_bean_lifecycle.md] Simplified Flow (Mermaid)

```mermaid
flowchart TD
    A["BeanDefinition loaded"] --> B["Constructor + DI (constructor/setter/field)"]
    B --> C["Aware callbacks (BeanName/BeanFactory/ApplicationContext)"]
    C --> D["BeanPostProcessor.postProcessBeforeInitialization"]
    D --> E["@PostConstruct / InitializingBean / init-method"]
    E --> F["BeanPostProcessor.postProcessAfterInitialization (AOP proxies created here)"]
    F --> G["Bean ready in ApplicationContext"]
    G --> H["... application runs ..."]
    H --> I["@PreDestroy / DisposableBean / destroy-method"]
```

## [Q14_spring_security_jwt_traps.md] JWT Filter Sequence (Mermaid)

```mermaid
sequenceDiagram
    participant C as Client
    participant F as SecurityFilterChain
    participant J as JwtAuthenticationFilter
    participant Ctx as SecurityContextHolder
    participant Ctrl as Controller

    C->>F: HTTP request + Bearer token
    F->>J: doFilterInternal
    J->>J: validate and parse claims
    alt token blacklisted or invalid
        J-->>C: 401 Unauthorized
    else valid
        J->>Ctx: setAuthentication(user, roles)
        J->>Ctrl: chain.doFilter -> continue
        Ctrl-->>C: response
    end
```

## [Q4_aop_log_execution_time.md] Interceptor Chain (Mermaid)

```mermaid
flowchart LR
    Req["HTTP Request"] --> Sec["[1] SecurityAspect @Before"]
    Sec --> Met["[2] MetricsAspect @Around: start timer"]
    Met --> Tx["[3] TransactionInterceptor: begin TX"]
    Tx --> Real["[4] Real OrderService.placeOrder()"]
    Real --> TxEnd["[3] TransactionInterceptor: commit"]
    TxEnd --> MetEnd["[2] MetricsAspect: log duration"]
    MetEnd --> Resp["Response to caller"]
```

## [Q15_kafka_event_driven_traps.md] Poison Pill → DLT Flow (Mermaid)

```mermaid
flowchart TD
    Msg["Order msg (bad data)"] --> Consumer["@KafkaListener handleOrder"]
    Consumer -->|NullPointerException| Retry{"Retry count < max?"}
    Retry -->|Yes, backoff 1s/2s/4s| Consumer
    Retry -->|No, exhausted| DLT["Publish to orders-dlt topic"]
    DLT --> Monitor["DLT consumer: alert on-call + store for manual review"]
```

## [42_Spring boot Security (Part-9)  Method Security  Role based Authorization  @PreAuthorize and Post/notes.md] How Method Security Works (Flow)

```mermaid
flowchart TD
    A["Client calls a @PreAuthorize/@PostAuthorize\nprotected controller method"] --> B["AOP Proxy intercepts the call\n(Spring generates a proxy around the bean)"]
    B --> C["AuthorizationManagerBeforeMethodInterceptor\nreads the @PreAuthorize SpEL string"]
    C --> D["SpelExpressionParser converts the string\ninto an Abstract Syntax Tree (AST)"]
    D --> E["Interceptor recursively resolves the AST:\nhasRole/hasAuthority, AND/OR/NOT,\nmethod args like #id, authentication object"]
    E --> F{"Expression\nevaluates true?"}
    F -->|No| G["AccessDeniedException\n(HTTP 403 Forbidden)\nmethod body never runs"]
    F -->|Yes| H["Target method executes\n(actual business logic runs)"]
    H --> I["AuthorizationManagerAfterMethodInterceptor\nreads the @PostAuthorize SpEL string"]
    I --> J["SpEL evaluated again, now with\nreturnObject bound to the method's return value"]
    J --> K{"Expression\nevaluates true?"}
    K -->|No| L["AccessDeniedException\n(HTTP 403 Forbidden)\nresponse discarded, never sent"]
    K -->|Yes| M["Return value sent back\nto the client as the response"]
```

## [37_Spring boot Security (Part-4)  Basic Authentication & Authorization  Stateless Authentication/notes.md] The Authentication Flow (Sequence Diagram)

```mermaid
sequenceDiagram
    participant C as Client
    participant BAF as BasicAuthenticationFilter
    participant AM as AuthenticationManager
    participant DAP as DaoAuthenticationProvider
    participant PE as PasswordEncoder
    participant UDS as UserDetailsService
    participant SCH as SecurityContextHolder
    participant AZ as Authorization Filter
    participant Ctrl as Controller

    C->>BAF: GET /api/users (no Authorization header)
    BAF-->>C: 401 Unauthorized + WWW-Authenticate: Basic
    Note over C: Client encodes "username:password" as Base64
    C->>BAF: GET /api/users<br/>Authorization: Basic base64(username:password)
    BAF->>BAF: Decode header -> raw username + password
    BAF->>AM: Authentication(username, password, authenticated=false)
    AM->>DAP: delegate authentication
    DAP->>PE: hash incoming raw password
    DAP->>UDS: loadUserByUsername(username)
    UDS-->>DAP: UserDetails (stored username, hashed password, roles)
    DAP->>DAP: compare hashed incoming vs stored password
    alt credentials match
        DAP-->>AM: Authentication(username, roles, authenticated=true)
        AM-->>BAF: authenticated Authentication object
        BAF->>SCH: store Authentication in SecurityContext
        BAF->>AZ: forward request
        AZ->>AZ: check required role for /api/users vs user's role
        alt role matches
            AZ->>Ctrl: forward request
            Ctrl-->>C: 200 OK (response)
        else role does not match
            AZ-->>C: 403 Forbidden
        end
    else credentials do not match
        DAP-->>C: 401 Unauthorized
    end
    Note over SCH: No session stored anywhere (SessionCreationPolicy.STATELESS).<br/>The ENTIRE flow above repeats from scratch on the very next request.
```

## [41_Spring boot Security (Part-8)  OAUTH2 Authentication Implementation/notes.md] Login + Token Exchange + Stateless Validation Flow

```mermaid
sequenceDiagram
    participant User as User (Browser)
    participant App as Spring Boot App<br/>Security Filter Chain
    participant AuthServer as Authorization Server<br/>GitLab / Auth0
    participant Handler as Custom OAuth2<br/>Success Handler
    participant Filter as Custom OAuth2<br/>Validation Filter

    User->>App: GET /login
    App-->>User: DefaultLoginPageGeneratingFilter renders login links<br/>per registration-id gitlab, auth0 from application.properties
    User->>App: Click GitLab link, GET /oauth2/authorization/gitlab
    App->>AuthServer: OAuth2AuthorizationRequestRedirectFilter:<br/>302 redirect with client_id, redirect_uri, scope=openid
    AuthServer-->>User: Show username/password plus consent page
    User->>AuthServer: Submit credentials and consent
    AuthServer-->>App: 302 redirect to redirect_uri with authorization code
    Note over App: OAuth2LoginAuthenticationFilter catches<br/>the login/oauth2/code/gitlab callback
    App->>App: Build OAuth2LoginAuthenticationToken with code,<br/>route via AuthenticationManager to<br/>OidcAuthorizationCodeAuthenticationProvider
    App->>AuthServer: POST token URI with code, client_id, client_secret
    AuthServer-->>App: access_token plus id_token JWT, plus refresh_token
    App->>App: Store tokens in OAuth2AuthorizedClientService,<br/>in-memory by default, overridable to DB
    App->>Handler: onAuthenticationSuccess authentication
    Handler-->>User: HTTP response body contains id_token,<br/>no session cookie relied upon, stateless
    Note over User,App: Later, calling a protected API
    User->>App: GET /user with Authorization Bearer id_token header
    App->>Filter: OncePerRequestFilter extracts token,<br/>parses issuer claim from JWT
    Filter->>AuthServer: JwtDecoder withIssuerLocation issuer,<br/>fetches JWK Set URI for public key
    Filter->>Filter: Verify JWT signature with public key
    Filter->>App: Valid, set Authentication in SecurityContextHolder
    App-->>User: 200 response fetched details successfully
```

## [44_Spring Boot ConfigurationProperties in-depth/notes.md] How `@ConfigurationProperties` Binding Works

```mermaid
flowchart TD
    A["application.properties / application.yml<br/>e.g. user.name, user.age, user.active"] --> B["Spring Boot Binder<br/>(relaxed binding: kebab-case, camelCase,<br/>underscore all map to the same field)"]
    B --> C{"How is the bean registered?"}
    C -->|"@Component + @ConfigurationProperties(prefix)"| D["Spring creates an EMPTY bean first<br/>via the default no-arg constructor<br/>(fields = defaults: null / 0 / false)"]
    C -->|"@ConfigurationPropertiesScan (main class)<br/>or @EnableConfigurationProperties"| E["Binder itself creates the bean<br/>by invoking the all-args constructor<br/>(constructor binding)"]
    D --> F["Binder calls SETTER methods<br/>to fill in each field from the properties"]
    E --> G["Fields set once, at construction time<br/>(final fields → immutable object, no setters needed)"]
    F --> H["Fully-populated bean registered<br/>in the ApplicationContext"]
    G --> H
    H --> I{"Is @Validated present on the class?"}
    I -->|"yes"| J["JSR-303 annotations checked<br/>(@NotBlank, @Min, @Max, ...)<br/>app FAILS TO START on violation"]
    I -->|"no"| K["Bean injected wherever needed<br/>(@Autowired / constructor injection)"]
    J --> K
```

## [38_JWT Explained  JWT vs SessionID  JSON Web Token  Security Challenges with JWT & its Handling/notes.md] JWT Encoding Flow (Mermaid)

```mermaid
flowchart TD
    A["Header\ntyp: JWT\nalg: HS256 or RS256"] --> B["base64url encode"]
    C["Payload / Claims\nRegistered: iss, sub, aud, exp, nbf, iat, jti\nPublic: email, country (custom, shared meaning)\nPrivate: internal-only fields (not standardized)"] --> D["base64url encode"]
    B --> E["Encoded Header"]
    D --> F["Encoded Payload"]
    E --> G["Concatenate: EncodedHeader + '.' + EncodedPayload"]
    F --> G
    G --> H["Sign with HMAC secret (symmetric) or RSA private key (asymmetric)"]
    H --> I["Raw signature bytes"]
    I --> J["base64url encode"]
    J --> K["Encoded Signature"]
    G --> L["Final JWT = EncodedHeader . EncodedPayload . EncodedSignature"]
    K --> L
```

## [38_JWT Explained  JWT vs SessionID  JSON Web Token  Security Challenges with JWT & its Handling/notes.md] JWT Validation Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Resource Server
    participant A as Auth Server / Key Store

    C->>R: GET /resource  (Header: Authorization: Bearer <JWT>)
    R->>R: Split token into header . payload . signature
    R->>A: Verify signature (shared HMAC secret or RSA public key)
    A-->>R: Signature valid / invalid
    alt Signature invalid
        R-->>C: 401 Unauthorized
    else Signature valid
        R->>R: Decode payload, check exp / nbf
        R->>R: Check jti against blacklist (revocation check)
        alt Expired or blacklisted
            R-->>C: 401 / 403 Rejected
        else All checks pass
            R->>R: Read roles/claims for authorization
            R-->>C: 200 OK + requested data
        end
    end
```
