# Mermaid Diagrams (extracted from advanced-interview-questions)

This file collects the original Mermaid source blocks that were replaced with ASCII-art diagrams in their source files, so the Mermaid source is preserved for rendering elsewhere.

## [08-error-boundaries.md] Detailed Explanation

```mermaid
flowchart TD
    App["App ErrorBoundary (catch-all -> AppCrashPage)"] --> Route["Route ErrorBoundary (/feed -> FeedError)"]
    Route --> Feed["Feed component"]
    Feed --> T1["Tweet ErrorBoundary #1 -> BrokenTweetPlaceholder"]
    Feed --> T2["Tweet ErrorBoundary #2 -> BrokenTweetPlaceholder"]
    Feed --> T3["Tweet ErrorBoundary #247 -> BrokenTweetPlaceholder (CRASHES)"]
    T1 --> Tw1["Tweet #1 (renders fine)"]
    T2 --> Tw2["Tweet #2 (renders fine)"]
    T3 -.->|"error caught HERE, does not propagate past this boundary"| Placeholder["Only this tweet shows placeholder - siblings unaffected"]
```

## [10-testing-strategy.md] Detailed Explanation

```mermaid
flowchart TD
    E2E["E2E - Playwright - ~5 tests - critical flows only"] --> Integration["Integration - RTL + MSW - 50-100 tests"]
    Integration --> Unit["Unit - Jest - 200+ tests - reducers, utils, hooks"]
```

## [16-useeffect-cleanup-lifecycle.md] Detailed Explanation

```mermaid
sequenceDiagram
    participant React
    participant Effect as Effect (setup)
    participant Cleanup as Cleanup (return fn)

    Note over React: Mount (symbol = TSLA)
    React->>Effect: run effect
    Effect->>Effect: create WebSocket #1

    Note over React: Re-render (symbol changes to AAPL)
    React->>Cleanup: run cleanup from PREVIOUS effect (closes WS #1)
    React->>Effect: run NEW effect (deps changed)
    Effect->>Effect: create WebSocket #2

    Note over React: Unmount
    React->>Cleanup: run cleanup from LAST effect (closes WS #2)
```

## [07-react-design-patterns.md] Detailed Explanation

```mermaid
flowchart TD
    Need["Need flexible, reusable component composition"] --> Q1{"Do you control the structure via children, like <Select> <Select.Option>?"}
    Q1 -->|Yes, consumer controls structure| Compound["Compound Components (Context + sub-components)"]
    Q1 -->|No, structure is fixed by the library| Q2{"Does the library control WHAT/WHERE, giving you only content via function-as-children?"}
    Q2 -->|Yes| RenderProps["Render Props (e.g. react-window itemRenderer)"]
    Q2 -->|No| Q3{"Is this a cross-cutting concern wrapping an ENTIRE component (auth, tracking)?"}
    Q3 -->|Yes, at route/page level| HOC["HOC (withAuth, withPageTracking)"]
    Q3 -->|No, logic needed INSIDE a component| Hook["Prefer a Custom Hook instead"]
```
