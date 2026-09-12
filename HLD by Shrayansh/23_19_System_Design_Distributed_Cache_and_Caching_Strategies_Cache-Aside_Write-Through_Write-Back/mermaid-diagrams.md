# Mermaid Diagrams — Extracted

Diagrams extracted from `interviewguide.md` and replaced in-place with ASCII-art equivalents. Kept here verbatim for anyone who wants the interactive/renderable Mermaid version.

## From `interviewguide.md` — "Choosing a Strategy (Decision Flowchart)"

```mermaid
flowchart TD
    Start["Choose a caching strategy"] --> ReadWrite{"Read-heavy or write-heavy?"}
    ReadWrite -->|Read-heavy| PopWho{"Who should populate the cache on a miss?"}
    PopWho -->|App code owns miss-handling| CacheAside["Cache-Aside (Lazy Loading)"]
    PopWho -->|Caching library owns miss-handling| ReadThrough["Read-Through"]
    ReadWrite -->|Write-heavy or write+read combo| Consistency{"Must cache & DB stay consistent on every write?"}
    Consistency -->|Yes, only needs invalidation not re-population| WriteAround["Write-Around (pair with Cache-Aside/Read-Through)"]
    Consistency -->|Yes, and can tolerate write latency| WriteThrough["Write-Through (pair with Cache-Aside/Read-Through for reads)"]
    Consistency -->|No - want lowest write latency + DB fault tolerance| WriteBack["Write-Back / Write-Behind (watch TTL vs DB-outage risk)"]
```
