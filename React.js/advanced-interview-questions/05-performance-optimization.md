# We have a 10,000-row data table that's slow. How do you fix it?

> **Interview priority:** MUST KNOW

## Question

We have a 10,000-row data table that's slow. How do you fix it?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT:**

> "First thing I'd do is not touch the code. I'd open React DevTools Profiler,
> record an interaction, and see the flame chart. In my experience, the actual
> slow component is often not where you expect. Let me walk through the
> systematic approach I'd use for a financial dashboard with 10k rows..."

```
REAL APP: Financial Dashboard — Transaction Table

  PROFILING FIRST (before touching code):
  ──────────────────────────────────────
  React DevTools → Profiler → record "sort by amount"
  
  Flame chart shows:
  ┌──────────────────────────────────────────────────────────┐
  │  Dashboard        2ms  ← fast, ignore                    │
  │  └─ FilterBar     1ms  ← fast, ignore                    │
  │  └─ TransTable  145ms  ← HERE IS THE PROBLEM             │
  │       └─ Row ×10000  0.014ms each but ×10000 = 140ms     │
  └──────────────────────────────────────────────────────────┘

  Root cause: Sorting triggers top-level state change
              → all 10,000 Row components re-render
              → even rows that didn't change
```

```
FIX LADDER (apply in order, stop when fast enough):

  STEP 1: VIRTUALIZATION — only render visible rows
  ─────────────────────────────────────────────────
  import { useVirtualizer } from '@tanstack/react-virtual';

  Browser viewport = 800px tall
  Row height = 40px
  Visible rows = 800/40 = 20
  Buffer = 10 above + 10 below

  BEFORE:  10,000 DOM nodes in memory
  AFTER:   40 DOM nodes  (+ absolute-positioned spacers)

  ┌─────────────────────────────────────────┐
  │ VIEWPORT (800px)                         │
  │ ┌─────────────────────────────────────┐ │
  │ │  Row 8   [DOM node]  ← visible      │ │   Real
  │ │  Row 9   [DOM node]  ← visible      │ │   DOM
  │ │  Row 10  [DOM node]  ← visible      │ │   nodes:
  │ │  ...     ...                        │ │   ~40
  │ └─────────────────────────────────────┘ │
  │                                          │
  │  Rows 1-7: spacer div (height: 280px)    │ (no DOM)
  │  Rows 28+: spacer div (height: 39720px)  │ (no DOM)
  └─────────────────────────────────────────┘

  Result: 10,000 rows → ~40 DOM nodes → 10-50x faster

  STEP 2: React.memo on Row
  ──────────────────────────
  const Row = React.memo(({ transaction }) => {
    return (
      <tr>
        <td>{transaction.date}</td>
        <td>{transaction.amount}</td>
        <td>{transaction.merchant}</td>
      </tr>
    );
  });
  // Without memo: sort triggers parent render → all 10k rows re-render
  // With memo: only rows whose data changed re-render (usually 0-2)

  STEP 3: useMemo for sort/filter computation
  ────────────────────────────────────────────
  const sortedTransactions = useMemo(
    () => [...transactions].sort((a, b) => b.amount - a.amount),
    [transactions, sortColumn, sortDirection]
  );
  // Without: every render (even unrelated state changes) re-sorts 10k items
  // With: only re-sorts when data or sort config changes

  STEP 4: State colocation — move selectedRow DOWN
  ──────────────────────────────────────────────────
  // BAD: selectedRowId in top-level Dashboard state
  // Every click → Dashboard re-renders → all 10k rows check "am I selected?"

  // GOOD: selectedRowId in URL params or Zustand atom
  // Only the prev-selected and newly-selected Row re-render
```

```
useCallback — WHEN IT HELPS vs WHEN IT'S NOISE:

  SCENARIO A: Passed to React.memo child → HELPS ✅
  ──────────────────────────────────────────────────
  Parent
    └─ React.memo(Row)  ← only re-renders if props change

  const handleRowClick = useCallback((id) => {
    setSelectedId(id);
  }, []); // stable reference

  <Row onClick={handleRowClick} />
  // Without useCallback: parent re-renders → new fn reference
  //   → Row sees new prop → re-renders despite React.memo
  // With useCallback: same reference → Row stays memoized ✅

  SCENARIO B: Standalone, not passed to memo child → NOISE ❌
  ─────────────────────────────────────────────────────────────
  const handleSort = useCallback((column) => {
    setSortColumn(column);
  }, []);
  <button onClick={handleSort}>Sort</button>
  // handleSort is never passed to a memoized child
  // useCallback adds deps array comparison cost with zero benefit
  // REMOVE IT — it's just noise
```

---
