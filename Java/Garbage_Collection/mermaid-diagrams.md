## [Q6_generational_gc.md] Which GC Runs When (Mermaid Decision Flow)

```mermaid
flowchart TD
    Start["Allocation request"] --> EdenFull{"Eden full?"}
    EdenFull -->|Yes| MinorGC["Minor GC: Young Gen only (10-50ms, frequent)"]
    EdenFull -->|No| Resume["Resume app threads"]
    MinorGC --> OldFull{"Old Gen nearly full?"}
    OldFull -->|Yes| MajorGC["Major GC: Old Gen (100ms-5s, rare)"]
    OldFull -->|No| Resume
    MajorGC --> HeapCritical{"Heap still critical?"}
    HeapCritical -->|Yes| FullGC["Full GC: entire heap + Metaspace (1-10s+, emergency)"]
    HeapCritical -->|No| Resume
    FullGC --> Resume
```

## [Q3_gc_marking_phase.md] Reachability Graph (Mermaid)

```mermaid
graph TD
    Stack["GC Root: Stack (p)"] --> Person
    StaticRoot["GC Root: Static Config.db"] --> Database
    Person --> Address
    Person --> List1["List"]
    List1 --> Order1
    List1 --> Order2
    Orphan -. "no GC Root points here" .-> LostObject
    classDef live fill:#c8e6c9,stroke:#2e7d32
    classDef dead fill:#ffcdd2,stroke:#c62828
    class Person,Address,List1,Order1,Order2,Database live
    class Orphan,LostObject dead
```

## [Q5_heap_generations.md] Object Promotion Flow (Mermaid)

```mermaid
flowchart LR
    New["New Object"] --> Eden
    Eden -->|Minor GC: survives| S0["Survivor 0"]
    S0 -->|Minor GC: age++| S1["Survivor 1"]
    S1 -->|Minor GC: age++| S0
    S0 -->|age >= 15| Old["Old Generation"]
    S1 -->|age >= 15| Old
    Eden -->|Minor GC: dies| Dead["Garbage Collected"]
```

## [Q4_gc_sweeping_phase.md] All Three Strategies Side-by-Side (Mermaid)

```mermaid
flowchart TD
    subgraph MarkSweep["1. Mark-Sweep — fast, fragments memory"]
        direction LR
        A1((A live)) ~~~ B1[dead: freed] ~~~ C1((C live)) ~~~ D1[dead: freed]
    end
    subgraph MarkSweepCompact["2. Mark-Sweep-Compact — slower, no fragmentation"]
        direction LR
        A2((A)) --> C2((C)) --> F2((F)) --> Free2["contiguous free space"]
    end
    subgraph Copy["3. Copy — fastest, needs 2x space"]
        direction LR
        From["From-space: A,B,C,D,E,F,G"] -->|copy live objects only| To["To-space: A,C,F"]
    end
```
