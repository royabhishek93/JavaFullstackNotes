# Explain how the React Fiber reconciler works.

> **Interview priority:** MUST KNOW

## Question

Explain how the React Fiber reconciler works.

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**HOW TO SAY IT (spoken to interviewer):**

> "Let me use a real example to explain this. Imagine you're building an Amazon-style
> product listing page with 500 items. Without Fiber, React would lock up the
> browser for the entire duration of rendering those 500 items — you couldn't
> click, scroll, or type. Fiber broke that into tiny pauseable steps.
>
> Here's the problem Fiber solved..."

```
REAL APP: Amazon Product Listing Page
──────────────────────────────────────────────────────────────────
WITHOUT FIBER (React < 16):

  User searches "laptop" → 500 results come back
  React starts rendering ALL 500 items as one giant job

  Timeline:
  |--render item 1--|--item 2--|--...--|--item 500--|
  <───────────── 80ms ─────────────────────────────>
                          ↑
                  Browser FROZEN here
                  User clicks "Sort by Price" — NO RESPONSE
                  User types in search box — NOTHING HAPPENS
                  User sees spinner, gets frustrated, leaves

WITH FIBER (React 16+):

  React renders item 1... checks: "browser need to do anything?"
  → NO → item 2... checks → NO → item 3... checks...
  → YES (user clicked!) → PAUSE rendering
  → handle click IMMEDIATELY (< 1ms)
  → RESUME from item 3 where we left off

  Timeline:
  |-item 1-|-item 2-|[PAUSE→click handled]|-item 3-|-...-|-item 500-|
              ↑                  ↑
        2ms per item     16ms frame budget respected
        always responsive     no jank
```

```
HOW FIBER WORKS INTERNALLY:

OLD WAY: Recursive call stack (can't pause)
──────────────────────────────────────────
renderPage()
  └─ renderSidebar()
       └─ renderFilters()
            └─ renderFilter() × 20
  └─ renderProductGrid()
       └─ renderProductCard() × 500   ← stuck here, can't escape

NEW WAY: Linked list of fiber nodes (can pause at any node)
───────────────────────────────────────────────────────────

  [Page]─child─►[Sidebar]─sibling─►[ProductGrid]
                    │                    │
                  child                child
                    │                    │
                [Filters]           [Card #1]─sibling─►[Card #2]─►...
                    │
                  child
                    │
                [Filter]─sibling─►[Filter]─►...

  Each box = one Fiber Node (JS object):
  ┌──────────────────────────────────────────────────────┐
  │  type:         ProductCard (function reference)       │
  │  stateNode:    actual <div> in the DOM                │
  │  child:   ──►  first child fiber                      │
  │  sibling: ──►  next sibling fiber                     │
  │  return:  ──►  parent fiber                           │
  │  pendingProps: { title: "Dell Laptop", price: 45000 } │
  │  memoizedProps:{ title: "Dell Laptop", price: 40000 } │
  │  effectTag:    UPDATE  (price changed)                │
  │  lanes:        0b0000010  (DefaultLane priority)      │
  └──────────────────────────────────────────────────────┘

  React walks this linked list one node at a time.
  Can stop between ANY two nodes — just remember current position.
```

```
TWO PHASES:

  PHASE 1: RENDER PHASE  (can be interrupted)
  ─────────────────────────────────────────────
  React walks the fiber tree
  For each node: "did anything change?"
  Marks effects: UPDATE / PLACEMENT / DELETION
  CAN PAUSE HERE — work in progress stays in memory

  PHASE 2: COMMIT PHASE  (cannot be interrupted)
  ──────────────────────────────────────────────
  Applies ALL marked changes to the real DOM at once
  Runs useLayoutEffect (sync, before paint)
  Runs useEffect (async, after paint)
  Must be atomic — partial DOM = broken UI
  Usually < 5ms

  WHY CAN'T COMMIT BE INTERRUPTED?
  Imagine showing the user a product card with price updated
  but image still showing old product — that's a partial commit.
  Fiber ensures "all or nothing" for DOM writes.
```

> "The key insight is: Fiber turns rendering from a recursive function call
> that can't be paused, into a linked list traversal that can stop at any node.
> That's what makes Concurrent Mode possible."

---
