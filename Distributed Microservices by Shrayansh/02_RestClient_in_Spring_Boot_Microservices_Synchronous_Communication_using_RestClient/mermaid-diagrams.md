## [notes.md] Request Flow (Sequence)

```mermaid
sequenceDiagram
    participant OC as OrderController
    participant RC as RestClient
    participant RS as ResponseSpec
    participant HC as JDK HttpClient
    participant PS as Product Service

    OC->>RC: .get().uri(...).accept(...)
    Note over RC: request fields accumulated, NO network call yet
    RC->>RS: .retrieve()
    Note over RS: prepares error handlers, still NO network call
    OC->>RS: .body(String.class)
    RS->>HC: fire actual HTTP request (thread blocks)
    HC->>PS: GET /products/{id}
    PS-->>HC: 200 OK + JSON
    HC-->>RS: raw response
    RS-->>OC: mapped response body
```
