## [notes.md] Request Flow (Sequence)

```mermaid
sequenceDiagram
    participant OC as OrderController
    participant Proxy as Feign Dynamic Proxy
    participant IH as InvocationHandler
    participant MH as MethodHandler
    participant PS as Product Service

    OC->>Proxy: productClient.getProductById(id)
    Proxy->>IH: intercept method call
    IH->>MH: look up MethodHandler for this method
    MH->>MH: build request (URL, headers, encoder)
    MH->>PS: HTTP GET /product/{id}
    alt success (2xx)
        PS-->>MH: 200 OK + body
        MH->>MH: Decoder converts JSON -> Java object
        MH-->>OC: return deserialized result
    else error (4xx/5xx)
        PS-->>MH: error response
        MH->>MH: ErrorDecoder builds exception
        MH-->>OC: throw exception
    end
```
