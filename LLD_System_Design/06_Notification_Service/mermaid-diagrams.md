## [06_Notification_Service_PRINT.md] Extra Visual 1 (Mermaid)

```mermaid
flowchart LR
        A[Client] --> B[Notification API]
        B --> C[Queue]
        C --> D[Email Worker]
        C --> E[SMS Worker]
        C --> F[Push Worker]
        D --> G[Email Provider]
        E --> H[SMS Provider]
        F --> I[Push Provider]
        D --> J[Status Store]
        E --> J
        F --> J
        D --> K[Metrics/Logs]
        E --> K
        F --> K
        D --> L[DLQ]
        E --> L
        F --> L
```
