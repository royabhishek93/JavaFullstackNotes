## [deadlock-scenarios-prevention.md] Classic Deadlock Pattern (Mermaid)

```mermaid
sequenceDiagram
    participant T1 as Thread-1
    participant L1 as lock1
    participant L2 as lock2
    participant T2 as Thread-2
    T1->>L1: acquire lock1 (success)
    T2->>L2: acquire lock2 (success)
    T1->>L2: try acquire lock2 (BLOCKED - held by T2)
    T2->>L1: try acquire lock1 (BLOCKED - held by T1)
    Note over T1,T2: Circular wait, DEADLOCK forever
```

## [race-conditions-thread-problems.md] Lost Update, Visualized (Mermaid)

```mermaid
sequenceDiagram
    participant T1 as Thread-1
    participant Mem as count (shared, starts at 0)
    participant T2 as Thread-2
    T1->>Mem: read count = 0
    T2->>Mem: read count = 0
    T1->>Mem: write count = 1 (0+1)
    T2->>Mem: write count = 1 (0+1)
    Note over Mem: Expected 2, got 1, lost update
```

## [threadlocal-usage-patterns.md] Key Principle: ThreadLocal Storage (diagram)

```mermaid
flowchart TB
    subgraph Shared["Without ThreadLocal (shared static field)"]
        T1a["Thread-1"] --> SharedVar["static userId"]
        T2a["Thread-2"] --> SharedVar
    end
    subgraph Isolated["With ThreadLocal"]
        T1b["Thread-1"] --> M1["userId = 'user1' (T1's own copy)"]
        T2b["Thread-2"] --> M2["userId = 'user2' (T2's own copy)"]
    end
```
