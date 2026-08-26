# Q17: Configuration, Profiles & Secrets — Scenario, Advanced & Trap Questions (15-Yr Architect)

**Study Time:** 15-20 minutes | **Frequency:** 75% in senior/architect rounds 🔥🔥 | **Difficulty:** ⭐⭐⭐⭐

> "The DB password was printed to the console on startup. The Actuator /env endpoint exposed all environment variables to anyone with the URL. Both in production." — Real config security incidents.

---

## How Spring Boot Loads Config (Priority Order)

```
Highest priority (wins)
  1. Command-line args:  --server.port=9090
  2. SPRING_APPLICATION_JSON env var
  3. OS environment variables: SERVER_PORT=9090
  4. application-{profile}.properties (active profile)
  5. application.properties (default)
  6. @PropertySource annotations
  7. Default values in code

Lowest priority (overridden by all above)
```

```
Profile activation:
  spring.profiles.active=prod            (in application.properties)
  SPRING_PROFILES_ACTIVE=prod            (environment variable — overrides above)
  --spring.profiles.active=prod          (command line — overrides all)

Property file resolution with profile "prod":
  application-prod.properties loaded IN ADDITION TO application.properties
  application-prod.properties overrides application.properties for same keys
```

---

## Scenario 1: @ConfigurationProperties vs @Value (The Right Tool)

### The Problem with @Value
```java
@Service
public class EmailService {

    @Value("${email.host}")
    private String host;

    @Value("${email.port}")
    private int port;

    @Value("${email.username}")
    private String username;

    @Value("${email.timeout-ms:5000}")  // default 5000
    private long timeoutMs;

    @Value("${email.retry-count:3}")
    private int retryCount;

    // 5 separate @Value annotations for related properties
    // No IDE autocomplete, no type safety, no validation
    // Typo in property name → fails at runtime, not compile time
}
```

### Fix: @ConfigurationProperties (Production Standard)
```java
@ConfigurationProperties(prefix = "email")
@Validated   // enables Bean Validation on the properties
public class EmailProperties {

    @NotBlank
    private String host;

    @Min(1) @Max(65535)
    private int port = 587;      // default value

    @NotBlank
    private String username;

    @NotBlank
    private String password;

    @DurationUnit(ChronoUnit.MILLIS)
    private Duration timeout = Duration.ofMillis(5000);  // type-safe Duration

    @Min(1) @Max(10)
    private int retryCount = 3;

    // Getters and setters (or use @ConstructorBinding for immutability)
}

@SpringBootApplication
@ConfigurationPropertiesScan  // or @EnableConfigurationProperties(EmailProperties.class)
public class Application { }
```

```yaml
# application.yml — IDE autocomplete + validation at startup
email:
  host: smtp.gmail.com
  port: 587
  username: noreply@company.com
  password: ${EMAIL_PASSWORD}   # from env var — never hardcode
  timeout: 5000ms
  retry-count: 3
```

```java
// Usage: inject the typed class, not individual strings
@Service
public class EmailService {
    private final EmailProperties emailProps;

    public EmailService(EmailProperties emailProps) {
        this.emailProps = emailProps;
    }
}
```

### Startup Validation Advantage
```
@Value typo: app starts fine → fails at runtime when method is called → 2 AM incident
@ConfigurationProperties + @Validated: validation at startup → fail-fast, caught in CI
```

---

## Trap 1: Profiles Not Loaded (Silent Wrong Config)

### The Bug
```yaml
# application-prod.yml
spring:
  datasource:
    url: jdbc:postgresql://prod-db:5432/orders

# application.yml (no profile)
spring:
  profiles:
    active: dev   # ← hardcoded in application.properties!

# Kubernetes deployment sets:
# SPRING_PROFILES_ACTIVE=prod  ← but wait...
```

```
Result: SPRING_PROFILES_ACTIVE env var = prod
        BUT application.properties has spring.profiles.active=dev
        Since env var > application.properties → prod wins ✅

ACTUALLY: Spring Boot 2.4+ has a different rule:
  spring.profiles.active IN application.properties is lowest priority
  But spring.config.activate.on-profile (multi-document YAML) can be confusing
```

### The Real Trap: Profile-Specific Files Not Found
```
App packaged as jar, deployed to K8s.
No application-prod.yml in the jar (it was in .gitignore by mistake).
App starts — no error! Spring just uses application.yml defaults.
→ App connects to dev DB from production pod!
→ No error thrown because connection URL is not invalid, just wrong.
```

### Fix: Fail-Fast on Missing Config
```java
@ConfigurationProperties(prefix = "datasource")
@Validated
public class DataSourceProperties {

    @NotBlank(message = "Database URL must be configured — check your profile")
    private String url;

    @NotBlank
    private String username;
}
// If prod profile misses datasource.url → ConstraintViolationException on startup
// Caught in K8s → pod doesn't start → alert fires → caught before prod traffic hits it
```

---

## Trap 2: Actuator Exposing Secrets (Critical Security Trap)

### The Problem
```
Spring Boot Actuator /env endpoint exposes ALL environment variables and properties.
Including: DATABASE_PASSWORD, JWT_SECRET, STRIPE_API_KEY

# GET http://myapp.com/actuator/env
{
  "DATABASE_PASSWORD": { "value": "S3cr3tPassw0rd!" },  ← IN PLAIN TEXT
  "JWT_SECRET": { "value": "my-super-secret-key" }
}
```

### Production Actuator Config
```yaml
management:
  # Only expose what monitoring needs
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus  # NOT env, not beans, not heapdump!
        # NEVER include: env, configprops, httptrace, heapdump in production

  endpoint:
    health:
      show-details: when-authorized   # full details only for authenticated requests
      probes:
        enabled: true
    info:
      enabled: true

  # Secure all actuator endpoints
  security:
    enabled: true
```

```java
@Configuration
public class ActuatorSecurityConfig {
    @Bean
    public SecurityFilterChain actuatorSecurityChain(HttpSecurity http) throws Exception {
        http
            .securityMatcher("/actuator/**")
            .authorizeHttpRequests(a -> a
                .requestMatchers("/actuator/health/**").permitAll()  // K8s probes
                .requestMatchers("/actuator/prometheus").hasAuthority("MONITORING")
                .anyRequest().denyAll()  // everything else: blocked
            );
        return http.build();
    }
}
```

### Sanitizing Sensitive Properties in /env
```yaml
# Even if /env is enabled for internal tools, sensitive values are masked:
management:
  endpoint:
    env:
      keys-to-sanitize:
        - password
        - secret
        - key
        - token
        - credentials
        - ".*password.*"
# → Values for matching keys shown as "******" in /env output
```

---

## Trap 3: @Value Injection Fails in @PostConstruct (Field Not Yet Injected)

### The Bug
```java
@Component
public class CacheWarmup {

    @Value("${cache.ttl-minutes}")
    private int ttlMinutes;

    // WRONG ❌ — constructor runs before field injection
    public CacheWarmup() {
        System.out.println(ttlMinutes); // → 0 (int default, not injected yet)
        warmupCache(ttlMinutes);        // uses wrong value!
    }
}
```

### Why This Fails
```
Bean lifecycle:
  1. Constructor called ← @Value fields NOT yet set (still defaults)
  2. Field injection (@Autowired, @Value fields SET here)
  3. @PostConstruct method ← safe to use @Value fields
```

### Fix: @PostConstruct
```java
@Component
public class CacheWarmup {

    @Value("${cache.ttl-minutes}")
    private int ttlMinutes;

    @PostConstruct
    public void init() {
        System.out.println(ttlMinutes); // ✅ value properly injected
        warmupCache(ttlMinutes);
    }
}

// Better: use @ConfigurationProperties + constructor injection (always safe)
@Component
public class CacheWarmup {
    private final CacheProperties props;

    public CacheWarmup(CacheProperties props) {
        // Constructor injection: fully initialised at construction time
        warmupCache(props.getTtlMinutes()); // ✅ safe in constructor
    }
}
```

---

## Scenario 2: Spring Cloud Config — @RefreshScope Traps

### Config Server Setup
```yaml
# bootstrap.yml (or application.yml with spring.config.import)
spring:
  config:
    import: "configserver:http://config-server:8888"
  application:
    name: order-service
  profiles:
    active: prod
# → Loads: order-service-prod.yml from Git repo via config server
```

### The Trap: @RefreshScope Not Applied
```java
// Trigger config refresh at runtime (without restart):
// POST /actuator/refresh → Spring re-fetches config from server

// PROBLEM: Only @RefreshScope beans pick up new values!
@Service  // ← NOT @RefreshScope
public class FraudDetectionService {

    @Value("${fraud.threshold}")
    private double threshold;  // ← will NOT update on /actuator/refresh
}

// FIX:
@Service
@RefreshScope  // ← re-creates bean on /actuator/refresh
public class FraudDetectionService {

    @Value("${fraud.threshold}")
    private double threshold;  // ✅ updates dynamically
}
```

### Trap: @RefreshScope + Singleton Dependency
```java
@Service
@RefreshScope   // refreshed bean
public class FraudService {
    private final FraudConfig config;  // injected dependency

    public FraudService(FraudConfig config) {
        this.config = config;
    }
}

@ConfigurationProperties(prefix = "fraud")
// NOT @RefreshScope ← trap! FraudConfig itself doesn't refresh
// FraudService is re-created, but its injected FraudConfig is the old bean
```

```java
// Fix: Mark the @ConfigurationProperties bean as @RefreshScope too
@ConfigurationProperties(prefix = "fraud")
@RefreshScope
public class FraudConfig { ... }
```

---

## Scenario 3: Environment-Specific Secrets (12-Factor App)

### Anti-Pattern: Secrets in application-prod.yml
```yaml
# WRONG ❌ — never commit secrets to Git, even in environment-specific files
spring:
  datasource:
    url: jdbc:postgresql://prod.db.internal:5432/orders
    username: orders_app
    password: Pr0d$ecretP@ss!   # ← in Git → security incident waiting to happen
```

### Production Patterns

**Pattern 1: Environment Variables (Simple)**
```yaml
# application.yml — safe to commit
spring:
  datasource:
    url: ${DATABASE_URL}              # from env var
    username: ${DATABASE_USERNAME}    # from env var
    password: ${DATABASE_PASSWORD}    # from env var
```

```
Kubernetes: store in K8s Secrets
  kubectl create secret generic app-secrets \
    --from-literal=DATABASE_PASSWORD=S3cr3tPassw0rd

  Mount as env vars in deployment.yaml:
    env:
      - name: DATABASE_PASSWORD
        valueFrom:
          secretKeyRef:
            name: app-secrets
            key: DATABASE_PASSWORD
```

**Pattern 2: Vault Integration (Enterprise)**
```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-vault-config</artifactId>
</dependency>
```

```yaml
spring:
  config:
    import: "vault://"
  cloud:
    vault:
      host: vault.internal
      port: 8200
      authentication: KUBERNETES    # pod uses its SA token to authenticate
      kv:
        enabled: true
        backend: secret
        application-name: order-service
# Vault path: secret/order-service/prod → all keys injected as Spring properties
# Dynamic credentials: Vault generates DB username/password per-pod, rotated automatically
```

---

## Trap 4: @ConditionalOnProperty Evaluation Timing

### The Bug
```java
@Configuration
@ConditionalOnProperty(name = "feature.new-payment-flow.enabled", havingValue = "true")
public class NewPaymentFlowConfig {
    @Bean
    public NewPaymentProcessor newPaymentProcessor() {
        return new NewPaymentProcessor();
    }
}
```

```yaml
# application.yml
feature:
  new-payment-flow:
    enabled: false   # disabled by default

# application-prod.yml
feature:
  new-payment-flow:
    enabled: true   # enabled in prod
```

```
TRAP: @ConditionalOnProperty is evaluated during ApplicationContext initialisation,
      BEFORE @RefreshScope can apply.
      → Can't be toggled at runtime with /actuator/refresh!
      → Requires app restart to change.

This is by design — bean creation is a startup-time decision.
For runtime toggles, use feature flags (LaunchDarkly, Unleash, or @Value + if/else).
```

### Runtime Feature Toggle (No Restart)
```java
@Service
public class PaymentService {

    @Value("${feature.new-payment-flow.enabled:false}")
    private boolean newFlowEnabled;    // can be refreshed with @RefreshScope

    public PaymentResult process(PaymentRequest request) {
        if (newFlowEnabled) {
            return newPaymentProcessor.process(request);
        }
        return legacyPaymentProcessor.process(request);
    }
}
// With @RefreshScope on PaymentService:
// Change property in Config Server → POST /actuator/refresh
// → newFlowEnabled updated WITHOUT restart
```

---

## Quick Reference: Configuration Best Practices

| Practice | Reason |
|---|---|
| `@ConfigurationProperties` over `@Value` | Type safety, validation, IDE support |
| `@Validated` on config classes | Fail-fast at startup, not runtime |
| Secrets via env vars or Vault | Never commit secrets to Git |
| Actuator: expose only health + metrics | `/env` leaks secrets in plain text |
| Constructor injection over field injection | Safe to use in constructor, testable |
| `SPRING_PROFILES_ACTIVE` env var | K8s sets this, overrides app.properties |
| `@RefreshScope` on dynamic config beans | Only beans with this annotation pick up live updates |

---

## Interview Cheat Sheet

> "In production, I use @ConfigurationProperties with @Validated for all typed configuration — it validates at startup, gives IDE autocomplete, and groups related properties together. Secrets never go in yaml files — they come from environment variables in Kubernetes Secrets or from Vault for dynamic rotation. Actuator is locked down to only expose health and prometheus endpoints — the /env endpoint prints secrets in plain text if left open. @Value fields are not available in constructors (field injection happens after constructor) — use @PostConstruct or better, constructor injection with @ConfigurationProperties. @RefreshScope enables live config refresh, but @ConditionalOnProperty beans are evaluated at startup and can't be toggled at runtime without a restart — for runtime flags, use @Value + @RefreshScope and guard with an if-else."
