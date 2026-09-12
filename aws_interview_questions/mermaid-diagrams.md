## [8.spring-security-jwt-postgres-auth-eks-interview-print.md] Registration → Hash → JWT Issue → Validate (Sequence Diagram)

```mermaid
sequenceDiagram
    participant Client
    participant API as Spring Boot (Pod)
    participant DB as PostgreSQL (RDS)

    Client->>API: POST /auth/register {email, password}
    API->>API: BCryptPasswordEncoder.encode(password)
    API->>DB: INSERT users (email, password_hash)
    DB-->>API: 201 Created
    API-->>Client: 201 Created

    Client->>API: POST /auth/login {email, password}
    API->>DB: SELECT user WHERE email = ?
    DB-->>API: password_hash, role
    API->>API: BCrypt.matches(password, hash)
    API->>API: generate accessToken (15min) + refreshToken (7d)
    API-->>Client: body accessToken, Set-Cookie refresh_token (HttpOnly)

    Client->>API: GET /api/orders (Authorization Bearer accessToken)
    API->>API: JwtAuthFilter validates signature + expiry
    API->>API: SecurityContextHolder.setAuthentication(user)
    API-->>Client: 200 OK (protected data)
```

## [9.rds-aurora-connection-pooling-eks-interview-print.md] Connection Multiplexing Flow (500 App Conns → 20 DB Conns)

```mermaid
flowchart LR
    subgraph Pods["EKS Pods: 200 pods x 10 HikariCP conns = 2000 app connections"]
        P1["Pod 1"]
        P2["Pod 2"]
        P3["Pod 200"]
    end
    P1 --> Proxy["RDS Proxy (multiplexer)"]
    P2 --> Proxy
    P3 --> Proxy
    Proxy -->|"only 20-30 real DB connections"| Aurora["Aurora Cluster (Primary + Read Replicas)"]
    Proxy -.->|"idle conn between queries lent to another caller; pinned only during an active transaction"| Info["Multiplexing rule"]
```

## [10.eks-hpa-keda-production-traps-interview-print.md] HPA → KEDA → Cluster Autoscaler (Decision Flowchart)

```mermaid
flowchart TD
    Traffic["Traffic / load increases"] --> Signal{"What's the right scaling signal?"}
    Signal -->|CPU/memory correlates with load| HPA["HPA: add pods based on CPU/memory (1-2 min)"]
    Signal -->|Event/queue-depth based, CPU stays low| KEDA["KEDA: add pods based on SQS depth/Kafka lag (30s), can scale to ZERO"]
    HPA --> Fit{"Do new pods fit on existing nodes?"}
    KEDA --> Fit
    Fit -->|Yes| Done["Pods scheduled, traffic served"]
    Fit -->|No - Pending pods, nodes full| CA["Cluster Autoscaler: provision new EC2 node (2-5 min)"]
    CA --> Done
```
