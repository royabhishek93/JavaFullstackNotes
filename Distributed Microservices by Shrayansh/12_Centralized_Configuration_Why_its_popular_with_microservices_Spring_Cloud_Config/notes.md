# Centralized Configuration — Spring Cloud Config

## What is this? (Plain English)

Instead of every microservice keeping its own `application.properties` baked into its jar, **Spring Cloud Config** stores all configuration in one central place (a Git repository) and serves it to every microservice at startup over HTTP. Change a value in one place, and every service that reads it gets the update — without editing code inside each service.

## The Problem It Solves

Without centralized config, four painful problems show up in production:

1. **Rebuild-and-redeploy for a config change**: A single property change means editing `application.properties`, rebuilding the jar, and redeploying — for something that isn't even a code change.
2. **Inconsistent config across services**: Related microservices (e.g. `pre-order` and `post-order`, split from one big `order` service) often share configuration like a DB URL. Update it in one and forget the other, and you get silent inconsistency.
3. **No runtime updates**: `application.properties` is read exactly once, at startup. A running instance has no way to notice the file changed on disk.
4. **Slow rollback**: Any config fix requires the full PR → build → redeploy cycle again, and if multiple services were affected by the same bad value, you repeat this for each one.

## Architecture — Three Layers

```
 LAYER 1: Config File Git Repo (plain .properties files, no code)
   global/
     application.properties          <- applies to ALL services, ALL profiles
     application-dev.properties       <- ALL services, dev profile only
     application-prod.properties
     application-qa.properties
   order-service/
     order-service.properties        <- order-service ONLY, ALL profiles
     order-service-dev.properties     <- order-service ONLY, dev profile
     order-service-prod.properties
     order-service-qa.properties
   invoice-service/
     invoice-service.properties
     ...

 LAYER 2: Config Server (Spring Boot app, @EnableConfigServer)
   Fetches files from the Git repo above and exposes them over HTTP:
     GET /{application}/{profile}/{label}
   e.g. GET /order-service/dev/main

 LAYER 3: Microservices (Config Clients)
   Each service, on startup, calls the Config Server to fetch its
   properties instead of reading a local application.properties.
```

## The Precedence Rule (the part everyone gets confused by)

When `order-service` asks for profile `dev`, the Config Server resolves properties in this exact order — **first match wins**, falling through to the next only if a key is missing:

1. `order-service-dev.properties` — exact application, exact profile
2. `application-dev.properties` — global (all services), but exact profile
3. `order-service.properties` — exact application, default (all profiles)
4. `application.properties` — global, default — the ultimate fallback
5. *(only if the config server itself is unreachable or the key still isn't found)* the microservice's own **local** `application.properties`/`application-dev.properties` — local config always has the **lowest** precedence.

**The mental model to remember:** exact-application always beats global, and exact-profile always beats default-profile — but "exact application, default profile" still outranks "global, exact profile" is a common trap. The real order is: profile-exact-application → profile-exact-global → default-exact-application → default-global → local.

## Fetch Flow (Sequence)

```
Lanes: OS = Order Service (Client) | CS = Config Server | Git = Git Repo

1)  OS ──────────> CS  : GET /order-service/dev/main
2)  CS ──────────────────────> Git : fetch order-service-dev.properties, application-dev.properties, etc. (cached if clone-on-start=true)
3)  CS <────────────────────── Git : file contents
4)  CS ──(self-call)─>             : resolve precedence: order-service-dev > application-dev > order-service > application
5)  OS <────────── CS  : merged property set
    ┌─ alt: Config Server unreachable (spring.config.import=optional:...) ─┐
6)  │  OS ──(self-call)─>  : fall back to local application.properties     │
    └─────────────────────────────────────────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Key Code / Config

### Config Server
```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-config-server</artifactId>
</dependency>
```
```java
@SpringBootApplication
@EnableConfigServer   // turns this Boot app into a central config server
public class ConfigServerApplication { ... }
```
```properties
server.port=8888
spring.cloud.config.server.git.uri=https://github.com/you/config-repo.git
spring.cloud.config.server.git.search-paths=global,order-service,invoice-service
spring.cloud.config.server.git.clone-on-start=true   # download at startup, not on first request
spring.cloud.config.server.git.default-label=main    # branch to fetch from

# Private repo — never hardcode credentials, use environment variables
spring.cloud.config.server.git.username=${GIT_USERNAME}
spring.cloud.config.server.git.password=${GIT_ACCESS_TOKEN}
```

### Config Client (e.g. Order Service)
```properties
spring.application.name=order-service   # MUST match the filename prefix used in the Git repo
spring.config.import=optional:configserver:http://localhost:8888
# "optional:" means the app still starts even if the config server is down —
# it just falls back to its own local application.properties as source of truth
spring.profiles.active=dev
```

## Important Concepts

- **Spring Cloud Config Server**: A Spring Boot app annotated `@EnableConfigServer` that fetches property files from a Git repository and exposes them via `/{application}/{profile}/{label}`.
- **Config Client**: Any microservice with `spring-cloud-starter-config` that fetches its properties from the Config Server at startup instead of (or in addition to) its local `application.properties`.
- **Precedence Fallback Chain**: exact-application+exact-profile → global+exact-profile → exact-application+default → global+default → local application.properties (lowest priority).
- **`git.clone-on-start`**: Whether the config server downloads and caches the Git repo at application startup (`true`, recommended) or lazily on the first incoming request (`false`).
- **`spring.config.import=optional:configserver:...`**: The `optional:` prefix prevents a config-server outage from blocking the microservice's own startup — it degrades to local config instead of failing entirely.
- **`spring.application.name`**: Must exactly match the filename prefix used in the config repo (e.g. `order-service` → `order-service.properties`, `order-service-dev.properties`) — this is how the config server knows which files belong to which caller.
