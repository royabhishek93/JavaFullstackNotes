# Mermaid Diagrams — Extracted

Diagrams extracted from `interviewguide.md` and replaced in-place with ASCII-art equivalents. Kept here verbatim for anyone who wants the interactive/renderable Mermaid version.

## From `interviewguide.md` — "Request Routing (Sequence Diagram)"

```mermaid
sequenceDiagram
    participant Client
    participant DNS as DNS Load Balancer (Route 53)
    participant GW as API Gateway (region/AZ)
    participant SD as Service Discovery
    participant LB as Load Balancer
    participant MS as Microservice instance

    Client->>DNS: request
    DNS->>GW: route to nearest healthy region
    GW->>GW: authenticate token (validate once, at the edge)
    GW->>GW: match endpoint (e.g. /api/invoice) to target service
    GW->>SD: lookup current location of target service
    SD-->>GW: healthy instance list / load balancer address
    GW->>LB: forward request
    LB->>MS: route to one instance
    MS-->>Client: response (via LB and GW)
```
