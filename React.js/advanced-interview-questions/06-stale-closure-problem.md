# What is the stale closure problem?

> **Interview priority:** MUST KNOW

## Question

What is the stale closure problem?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

**STRONG answer with example:**

```
REAL APP: Live Chat — Message counter that broke in production

  // The bug: online user count showed "1" forever in the window title
  useEffect(() => {
    const interval = setInterval(() => {
      document.title = `(${onlineCount}) New messages`;
      // onlineCount is FROZEN at its value when this effect ran
    }, 1000);
    return () => clearInterval(interval);
  }, []); // empty deps = closure captures onlineCount=1 at mount, NEVER UPDATES

  WHAT HAPPENS:
  ┌──────────────────────────────────────────────────────┐
  │  Component mounts: onlineCount = 1                    │
  │  Closure captures: onlineCount = 1  (frozen snapshot) │
  │                                                        │
  │  t=5s:  onlineCount updates to 47 (WebSocket event)   │
  │         Interval still runs with onlineCount = 1 ❌   │
  │                                                        │
  │  t=10s: onlineCount updates to 52                      │
  │         Interval still runs with onlineCount = 1 ❌   │
  │  Title always shows "(1) New messages" — stale!        │
  └──────────────────────────────────────────────────────┘

  FIX 1: Use a ref (doesn't trigger re-render, always fresh):
  ─────────────────────────────────────────────────────────
  const countRef = useRef(onlineCount);
  useEffect(() => {
    countRef.current = onlineCount; // update ref on every render
  });
  useEffect(() => {
    const interval = setInterval(() => {
      document.title = `(${countRef.current}) New messages`; // always fresh
    }, 1000);
    return () => clearInterval(interval);
  }, []); // empty deps OK now — reads from ref, not closure

  FIX 2: Include in deps (creates new interval on change):
  ─────────────────────────────────────────────────────────
  useEffect(() => {
    const interval = setInterval(() => {
      document.title = `(${onlineCount}) New messages`;
    }, 1000);
    return () => clearInterval(interval);
  }, [onlineCount]); // new interval whenever count changes
  // OK here — interval is cheap to recreate

  FIX 3: Functional update (for setState specifically):
  ─────────────────────────────────────────────────────
  // setCount(count + 1) ← stale closure problem
  // setCount(prev => prev + 1) ← reads CURRENT state, not closure
```

---

## One-Page Cheat Sheet

```
╔══════════════════════════════════════════════════════════════════════╗
║  INTERNALS                                                           ║
║  Fiber = linked list of work units. Can pause between nodes.         ║
║  Render phase = interruptible diff. Commit = atomic DOM write.       ║
╠══════════════════════════════════════════════════════════════════════╣
║  CONCURRENT MODE                                                     ║
║  startTransition → non-urgent setState (typing search filter)        ║
║  useTransition   → same + isPending for loading UI                   ║
║  useDeferredValue → lag a value received as prop                     ║
╠══════════════════════════════════════════════════════════════════════╣
║  SERVER COMPONENTS                                                   ║
║  Server = no JS shipped, async by default, direct DB                 ║
║  Client = 'use client', has hooks/events                             ║
║  Server CAN hold Client children. Client CANNOT import Server.       ║
╠══════════════════════════════════════════════════════════════════════╣
║  STATE CATEGORIES                                                    ║
║  Server state → React Query   (cache, refetch, invalidate)           ║
║  Global UI    → Zustand/RTK   (sidebar, user, theme)                 ║
║  URL state    → Search params (filter, sort, page — survives refresh)║
║  Form state   → React Hook Form (uncontrolled, fast)                 ║
║  Local state  → useState (keep it where it's used)                   ║
╠══════════════════════════════════════════════════════════════════════╣
║  PERFORMANCE RULES                                                   ║
║  1. Profile first (DevTools Profiler, Chrome Perf)                   ║
║  2. Virtualize large lists (react-window, @tanstack/virtual)         ║
║  3. React.memo on expensive child components                         ║
║  4. useCallback only if passed to memo child or in effect deps       ║
║  5. Split context by update frequency                                ║
╠══════════════════════════════════════════════════════════════════════╣
║  PATTERNS                                                            ║
║  Compound Components → design system (Tabs, Select, Modal)           ║
║  Render Props       → renderItem in lists/tables (react-window)      ║
║  HOC                → cross-cutting at route level (auth, analytics) ║
║  Custom Hook        → logic sharing in new code (preferred)          ║
╠══════════════════════════════════════════════════════════════════════╣
║  SECURITY                                                            ║
║  DOMPurify before dangerouslySetInnerHTML                            ║
║  Validate href protocols (block javascript:)                         ║
║  Refresh tokens → HTTP-only cookie, NEVER localStorage               ║
╠══════════════════════════════════════════════════════════════════════╣
║  STALE CLOSURE                                                       ║
║  setCount(prev => prev + 1) — not setCount(count + 1) in intervals   ║
║  useRef for mutable latest values read inside effects                ║
╠══════════════════════════════════════════════════════════════════════╣
║  REACT 19                                                            ║
║  use(promise) → suspends if pending, throws to ErrorBoundary         ║
║  Server Actions → 'use server' fn, no API route needed               ║
║  useOptimistic → instant UI + auto rollback on failure               ║
║  ref as prop → forwardRef no longer needed                           ║
╚══════════════════════════════════════════════════════════════════════╝
```
