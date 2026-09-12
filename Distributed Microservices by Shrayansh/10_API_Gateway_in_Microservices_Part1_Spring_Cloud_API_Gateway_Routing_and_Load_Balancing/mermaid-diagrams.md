## [notes.md] Request Flow (Sequence)

```mermaid
sequenceDiagram
    participant Client
    participant GW as API Gateway
    participant SD as Eureka (Service Discovery)
    participant LB as Load Balancer
    participant PS as Product Service instance

    Client->>GW: GET /products/1
    GW->>GW: match route by Path predicate
    alt uri = lb://PRODUCT-SERVICE
        GW->>SD: get healthy instances for PRODUCT-SERVICE
        SD-->>GW: [instance1, instance2, ...]
        GW->>LB: choose one instance
        LB-->>GW: instance2
    end
    GW->>PS: forward request to chosen instance
    PS-->>GW: response
    GW-->>Client: response
```
