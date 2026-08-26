# React Performance Optimization — 15-YOE Interview Prep

---

## 1. Big Picture: React Render Cycle & Reconciliation

```
WHAT TRIGGERS A RE-RENDER?
─────────────────────────────────────────────────────────────────────
  1. setState / useState setter called (even with same value* — object identity)
  2. Parent component re-renders  →  child re-renders by default
  3. Context value changes          →  all consumers re-render
  4. key prop changes               →  full unmount + remount (new instance)
  5. forceUpdate (class components) →  always re-renders

*Exception: React bails out if primitive state value is same via Object.is()

RENDER PROPAGATION TREE
─────────────────────────────────────────────────────────────────────

          App (state: theme)
          │
          ├── Sidebar  ← re-renders (parent changed)
          │     └── NavItem x5  ← re-renders (parent changed)
          │
          ├── Dashboard (no props from App)  ← re-renders (parent changed)
          │     ├── StatsBar  ← re-renders
          │     └── DataTable (memo'd) ✓  ← SKIPPED if props unchanged
          │           └── Row x1000  ← SKIPPED (DataTable skipped)
          │
          └── ThemeProvider (context: theme)
                └── Button (context consumer)  ← re-renders via context


REACT RECONCILIATION (Diffing Algorithm)
─────────────────────────────────────────────────────────────────────

  Trigger (setState)
       │
       ▼
  Render Phase  ──── React calls your component function
       │              Builds new Virtual DOM (fiber tree)
       │              Diffs old vs new fiber tree
       │              Marks fibers as: UPDATE / INSERT / DELETE
       ▼
  Commit Phase  ──── DOM mutations applied (synchronous)
       │              useLayoutEffect fires
       ▼
  Paint (browser)
       │
       ▼
  useEffect fires (async, after paint)


CONCURRENT MODE (React 18)
─────────────────────────────────────────────────────────────────────

  Urgent update (typing)   →  rendered immediately
  startTransition(fn)      →  deferred, can be interrupted
                              browser stays responsive
```

---

## 2. Conversational Interview Script

**Q: Walk me through how you approach performance optimization on a large React app.**

> "My first instinct is always to measure, not guess. I open React DevTools Profiler and record a user interaction — say, clicking a filter on a data table. I look at the flamegraph for components with long render times or ones that are rendering when they shouldn't be.
>
> The second thing I check is bundle size. A slow initial load is often a bundle problem, not a React problem. I'll run webpack-bundle-analyzer and look for large third-party deps that could be lazy-loaded or replaced with lighter alternatives.
>
> Then I look at the runtime. The usual suspects in a large app are: expensive computations running on every render that should be memoized, large lists rendered as flat DOM nodes that should be virtualized, and context providers whose value object is recreated every render, causing all consumers to re-render.
>
> For a dashboard app, I'd also check Core Web Vitals in the field — not just synthetic testing. LCP tells me if my server response or largest image is slow. CLS tells me if my layout is shifting because images lack dimensions or async content pops in. INP tells me if React's work is blocking user input.
>
> The thing I always tell my team: don't add React.memo or useMemo everywhere preemptively. Measure first. Memoization has its own cost."

---

## 3. Scenario-Based Q&As (Production Context)

**Q1: Your data table with 500 rows is laggy when sorting. What do you do?**

> First, profile it. In DevTools Profiler, I record a sort click and look at what rendered. 99% of the time the problem is one of two things: (1) all 500 row components re-rendered because their identity changed, or (2) the sort computation itself is expensive and runs on every render.
>
> For (1): I virtualize with `react-window` or TanStack Virtual. Only ~20 DOM nodes exist at any time regardless of list size. For (2): I wrap the sort with `useMemo`, keyed on the data array reference and sort config.
>
> After that, I'd check if row components can be memoized with `React.memo` — but only if the parent is re-rendering frequently for unrelated reasons. If the parent only re-renders when the data changes, memo on rows is wasted overhead.

---

**Q2: A filter input in your dashboard causes the entire page to re-render on every keystroke. How do you fix it?**

> This is a classic context or state placement problem. If the filter value lives in a top-level context or component, every keystroke triggers a cascade down the whole tree.
>
> My fix: co-locate state. Move the filter state to the lowest component that needs it. If multiple distant components need it, consider splitting context — one context for stable data, a separate one for volatile UI state. Consumers of the stable context won't re-render when UI state changes.
>
> Also, for the search itself I'd use `startTransition` in React 18 — mark the list filtering as a non-urgent transition. The input stays responsive even if the filtered list computation takes a few frames.

```tsx
// Before: every keystroke blocks rendering
const [query, setQuery] = useState('');
const filtered = items.filter(i => i.name.includes(query)); // runs sync

// After: input is urgent, filtering is deferred
const [query, setQuery] = useState('');
const [deferredQuery, setDeferredQuery] = useState('');

const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  setQuery(e.target.value);                    // urgent — input updates immediately
  startTransition(() => {
    setDeferredQuery(e.target.value);          // deferred — list update can wait
  });
};

const filtered = useMemo(
  () => items.filter(i => i.name.includes(deferredQuery)),
  [items, deferredQuery]
);
```

---

**Q3: Your React app's LCP is 4.2s. What's your investigation plan?**

> LCP measures the time until the largest content element is visible. In a React SPA, common causes are: (1) large JavaScript bundle blocking rendering, (2) hero image not loading fast enough, (3) server response time.
>
> I'd look at network waterfall in Lighthouse or WebPageTest. If JS is the bottleneck, I'd implement route-based code splitting with React.lazy + Suspense so the initial bundle only includes what's needed for the landing route. If the image is the bottleneck, I'd add `loading="eager"`, `fetchpriority="high"`, serve WebP via `<picture>` with srcset, and preload the image in `<head>`. If it's TTFB, that's a server/CDN problem.

---

**Q4: You have a complex form with 30 fields. Typing in any field re-renders all fields. Fix it.**

> The root cause is usually one of: (1) a single `formState` object at the top level that updates on every keystroke, (2) callback props recreated on every render, breaking memo on field components.
>
> Solutions: Use a library like React Hook Form, which keeps form state in a ref (uncontrolled) and only triggers re-renders on submit/validation. Or if rolling your own, use `useReducer` and pass dispatch down (stable reference), wrap each field in `React.memo`, and pass only the specific field's value — not the whole form object.

---

**Q5: A dropdown component is used 200 times on a page. Each has an `onSelect` prop that's a new arrow function. Is this a problem?**

> It depends on whether the dropdown is memoized. If `Dropdown` is wrapped in `React.memo`, then yes — new function references on every parent render will invalidate the memo and cause all 200 dropdowns to re-render. Fix: wrap the handler in `useCallback` in the parent so the reference is stable.
>
> If `Dropdown` is NOT memoized, then `useCallback` adds zero benefit — it just adds overhead. Don't add useCallback without memo'd children; it's pointless.

---

**Q6: How do React Server Components improve performance vs traditional SSR?**

> Traditional SSR renders on the server but still ships the component JS to the client for hydration. The client re-executes the component tree to attach event listeners — this is the hydration cost.
>
> Server Components go further: they render on the server and send serialized React elements (not HTML) to the client. The component code itself never ships to the client bundle. Zero JS for that component. Particularly powerful for data-fetching components — a Server Component can hit the DB directly, render the data, and send it down. No client-side fetch, no loading state, no bundle cost.
>
> The constraint: Server Components can't use state, effects, or event handlers. They're for pure rendering + data fetching.

---

**Q7: Your infinite scroll list grows to 2000 items. Performance degrades over time. Diagnosis and fix?**

> Classic DOM bloat problem. Every item in a `map()` call creates a real DOM node. 2000 nodes means the browser spends significant time in layout, paint, and event delegation.
>
> Fix: virtualize. With TanStack Virtual or react-window, only the visible items (typically 10-30) are in the DOM at any time. Items scrolled out of view are unmounted. Memory and render time stay constant regardless of total item count.
>
> For infinite scroll specifically, I'd also implement data windowing — don't keep all 2000 items in React state. Keep only a rolling window of data and discard old pages as new ones load. Otherwise even with virtualization, the JS heap grows unbounded.

---

**Q8: How do you handle code splitting for a large dashboard app with 15+ routes?**

> Route-based splitting is the default approach. Each route chunk is only loaded when navigated to.

```tsx
// router.tsx
import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';

const Dashboard   = lazy(() => import('./pages/Dashboard'));
const Analytics   = lazy(() => import('./pages/Analytics'));
const UserTable   = lazy(() => import('./pages/UserTable'));
const Settings    = lazy(() => import('./pages/Settings'));

export function AppRouter() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route path="/"          element={<Dashboard />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/users"     element={<UserTable />} />
        <Route path="/settings"  element={<Settings />} />
      </Routes>
    </Suspense>
  );
}
```

> Beyond routes, I'd split heavy components: rich text editors, chart libraries, PDF viewers. These can be lazy-loaded on first use with a skeleton fallback. I'd also use `/* webpackPrefetch: true */` comments to preload routes the user is likely to visit next.

---

## 4. Advanced Scenario Q&As

**A1: Explain how React's reconciliation algorithm decides what to update, and what "key" really does under the hood.**

> React's reconciler (the Fiber architecture) builds a tree of fiber nodes — one per component/element. When state changes, it creates a work-in-progress tree and diffs it against the current tree using a heuristic O(n) algorithm (not O(n³) like a general tree diff).
>
> The heuristic: if element type at a position changes (e.g., `<div>` becomes `<span>`), React tears down the subtree completely. If type is the same, it updates in place (reuses the DOM node, updates attributes).
>
> `key` is React's mechanism for identity across renders. In a list without keys, if you prepend an item, React sees the first position has a different value and updates all n items. With stable keys, React can match old and new fibers by key and only insert the new item. Wrong keys (using index) cause worse problems: React maps fiber identity to index, so inserting at position 0 shifts all identities, causing full re-renders AND loss of uncontrolled component state (inputs, focus).

---

**A2: How does the Context API cause performance problems at scale, and what are the architectural solutions?**

> Context works by broadcasting: when the context value changes, all consumers re-render regardless of which part of the value they use. If you put `{ user, theme, notifications, featureFlags }` in one context and `notifications` changes every 5 seconds, every component consuming any part of that context re-renders.
>
> Solutions:
> 1. **Split contexts** — separate, highly-scoped contexts: `UserContext`, `ThemeContext`, `NotificationContext`. Consumers subscribe to only what they need.
> 2. **Context selector pattern** — use `use-context-selector` library, which lets consumers subscribe to a specific slice and only re-render when that slice changes.
> 3. **Move to a state manager** — Zustand, Jotai, or Redux Toolkit selectors solve this by design. Components subscribe to specific atoms/selectors and only re-render when their subscribed value changes.
> 4. **Memo the value** — if your context value is an object, memoize it: `useMemo(() => ({ user, logout }), [user, logout])`. Prevents re-renders when the provider's parent re-renders for unrelated reasons.

---

**A3: A React app has an INP of 450ms (poor). Walk through your full investigation and fix strategy.**

> INP (Interaction to Next Paint) measures the worst interaction delay. 450ms means some user action — click, type, toggle — is taking 450ms before the browser can paint.
>
> Investigation: Chrome DevTools Performance panel. Record the interaction. Look for: (1) long tasks on the main thread, (2) React render time in the task, (3) JS execution from third-party scripts.
>
> Common React causes:
> - A click handler triggers a state update that causes an expensive synchronous render of a large component tree. Fix: optimize with memo/virtualization OR use `startTransition` to defer the render.
> - Third-party analytics or ad scripts hogging the main thread. Fix: load them with `defer`/`async`, move to a Web Worker if possible.
> - Large event handler doing synchronous DOM reads (forced reflow). Fix: batch reads/writes, use `requestAnimationFrame`.
>
> In React 18, `startTransition` is the primary tool — it tells React that a state update is non-urgent, allowing the browser to process input events between render chunks (time slicing).

---

**A4: How would you implement a high-performance data grid with 100k rows, real-time updates, and column sorting?**

> This requires multiple layers working together:
>
> **Virtualization**: TanStack Virtual for row and column virtualization. Only visible cells render. Critical for 100k rows.
>
> **Data management**: Don't hold 100k rows in React state. Use a ref or external store (Zustand). React state for UI state only (sort config, scroll position). Avoid triggering React reconciliation for pure data updates.
>
> **Real-time updates**: WebSocket or SSE stream. Batch incoming updates — don't call setState for every message. Accumulate updates in a ref for 100ms, then flush to state once. This turns 100 individual re-renders into 1.
>
> **Sorting**: Worker thread for sort computation on large datasets. Main thread stays unblocked. Post sorted indices back to main thread. Only re-render after sort completes.
>
> **Cell rendering**: Memoize row components. Memoize expensive cell renderers. Use CSS transforms for scrolling (avoids layout thrash).

```tsx
// Batched real-time updates pattern
const pendingUpdates = useRef<Update[]>([]);

useEffect(() => {
  const ws = new WebSocket(WS_URL);
  ws.onmessage = (e) => {
    pendingUpdates.current.push(JSON.parse(e.data));
  };

  const interval = setInterval(() => {
    if (pendingUpdates.current.length === 0) return;
    const batch = pendingUpdates.current.splice(0);
    setRows(prev => applyUpdates(prev, batch));   // single state update
  }, 100);

  return () => { ws.close(); clearInterval(interval); };
}, []);
```

---

## 5. Senior Trap Questions

**TRAP 1: "React.memo prevents all re-renders, right?"**

- **The trap**: Engineers assume memo is a complete shield. It only does a shallow comparison of props.
- **What memo does NOT prevent**: (1) re-renders triggered by hooks inside the component (`useState`, `useReducer`), (2) re-renders triggered by context changes the component consumes, (3) re-renders when the key prop changes.
- **Correct answer**: React.memo prevents re-renders caused by the parent re-rendering with unchanged props. A memoized component will still re-render if its own state changes, if it reads from a context that changed, or if a hook it uses triggers a re-render. Memo only intercepts the "parent re-render" trigger.

```tsx
const MemoizedChild = React.memo(({ label }: { label: string }) => {
  const theme = useContext(ThemeContext); // ← context change = re-render, memo can't stop it
  const [count, setCount] = useState(0); // ← own state change = re-render, memo can't stop it
  return <div>{label} {theme} {count}</div>;
});
```

---

**TRAP 2: "useMemo is always good to add — it only helps, never hurts."**

- **The trap**: useMemo has real costs. Memory allocation for the cached value. Computation cost of comparing deps on every render. JS engine overhead for the closure.
- **When useMemo is net-negative**: wrapping cheap computations (string concatenation, simple filter on <100 items), using it on values that change every render anyway.
- **Correct answer**: useMemo is beneficial when (a) the computation is genuinely expensive (>1ms as a rule of thumb), AND (b) the memoized value is used as a prop to a memoized child or as a dep to another hook. Outside those two cases, you're adding overhead for no benefit. Profile first.

---

**TRAP 3: "For large lists, just use .map() — React handles it efficiently."**

- **The trap**: React's virtual DOM diffing is efficient. But diffing is a JS problem. The real bottleneck with large lists is the DOM itself — 1000 DOM nodes means 1000 elements the browser must layout, paint, and hold in memory.
- **Correct answer**: At ~100 items you should start considering virtualization. At 500+ items, virtualize. The DOM is the bottleneck, not React's diffing. `react-window` (fixed size) or TanStack Virtual (dynamic size) keep DOM node count constant. React's reconciliation of 20 virtual rows is trivially fast.

---

**TRAP 4: "I wrap every function in useCallback to prevent re-renders."**

- **The trap**: useCallback only prevents re-renders in children if those children are wrapped in React.memo. Without memo'd children, useCallback is pure overhead — you're paying the cost of memoizing a function with zero benefit.
- **Secondary trap**: useCallback on an inline function that uses frequently-changing deps means the "stabilized" reference changes on every render anyway.
- **Correct answer**: useCallback is beneficial exactly when: (1) the function is passed as a prop to a React.memo'd child, OR (2) it's a dependency of another hook (useEffect, useMemo) and you don't want to trigger that hook on every render. Outside those cases, skip it.

---

**TRAP 5: "React is slow — we should migrate to Svelte/Vue."**

- **The trap**: This is an architectural diagnosis without data. React itself is rarely the bottleneck. The bottleneck is almost always: unoptimized render patterns, too many DOM nodes, blocking the main thread, or large bundles.
- **How to actually diagnose**: React DevTools Profiler → flamegraph → find components with long render time or excessive render count. Chrome Performance panel → find long tasks → attribute them to React, user code, or third-party code. Only if React's own reconciliation overhead is measurably significant after optimization does a framework migration become a real conversation.
- **Correct answer**: "React is slow" is a symptom statement. You diagnose with DevTools before prescribing treatment. Most React performance problems are solvable with memoization, virtualization, code splitting, and proper state architecture. I've shipped React apps with sub-100ms interactions on 10k row data grids.

---

**TRAP 6: "Server-Side Rendering solves all performance problems."**

- **The trap**: SSR improves Time to First Byte and initial content paint but introduces hydration cost — React must re-execute the component tree on the client to attach event handlers. A large SSR app can still have a slow TTI (Time to Interactive) if the JS bundle is large.
- **Correct answer**: SSR improves perceived performance (faster first paint) and is important for SEO. But bundle size still matters for TTI. The modern answer is: SSR + code splitting + React Server Components for static parts (zero client JS) + Streaming SSR (React 18's `renderToPipeableStream`) which sends HTML in chunks, unblocking the browser earlier. These work together, not as a single silver bullet.

---

**TRAP 7: "useEffect with an empty dep array runs exactly once — it's safe for subscriptions."**

- **The trap**: In React 18 Strict Mode (development), effects run twice — mount, unmount, remount. This deliberately surfaces cleanup bugs. If your useEffect creates a WebSocket connection and you don't return a cleanup function, you'll have two open connections in dev mode. In production it runs once, masking the bug until edge cases arise.
- **Correct answer**: Always return cleanup from subscriptions, timers, and event listeners. Treat the double-fire as a feature — it's a lint check for your cleanup logic.

```tsx
useEffect(() => {
  const ws = new WebSocket(url);
  ws.onmessage = handleMessage;
  return () => ws.close();   // ← mandatory: cleanup runs on unmount + StrictMode remount
}, [url]);
```

---

## 6. Production Code Examples

### React.memo with custom comparator

```tsx
interface RowProps {
  id: string;
  name: string;
  value: number;
  metadata: Record<string, unknown>; // deep object — default shallow check fails
}

const TableRow = React.memo(
  ({ id, name, value }: RowProps) => (
    <tr>
      <td>{id}</td><td>{name}</td><td>{value}</td>
    </tr>
  ),
  (prev, next) =>
    prev.id === next.id &&
    prev.name === next.name &&
    prev.value === next.value
  // custom comparator: ignore metadata, skip deep comparison cost
);
```

---

### useMemo — expensive computation

```tsx
function SalesReport({ transactions }: { transactions: Transaction[] }) {
  const summary = useMemo(() => {
    // O(n) aggregation — runs once per transactions array identity change
    return transactions.reduce(
      (acc, t) => ({
        total: acc.total + t.amount,
        byCategory: {
          ...acc.byCategory,
          [t.category]: (acc.byCategory[t.category] ?? 0) + t.amount,
        },
      }),
      { total: 0, byCategory: {} as Record<string, number> }
    );
  }, [transactions]);

  return <ReportDisplay summary={summary} />;
}
```

---

### useCallback — stable reference for memo'd child

```tsx
function UserTable({ users }: { users: User[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Without useCallback: new function on every UserTable render → Row memo busted
  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
  }, []); // stable — setSelectedId reference never changes

  return (
    <>
      {users.map(u => (
        <MemoizedRow key={u.id} user={u} onSelect={handleSelect} />
      ))}
    </>
  );
}
```

---

### Virtualized list with TanStack Virtual

```tsx
import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef } from 'react';

function VirtualList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 48,        // estimated row height in px
    overscan: 5,                   // render 5 extra rows above/below viewport
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map(vItem => (
          <div
            key={vItem.key}
            style={{ transform: `translateY(${vItem.start}px)`, position: 'absolute' }}
          >
            <ItemRow item={items[vItem.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

### Code splitting with React.lazy

```tsx
import { lazy, Suspense } from 'react';

// Heavy chart library — only loaded when ChartPage is visited
const ChartPage = lazy(() =>
  import(/* webpackChunkName: "charts", webpackPrefetch: true */ './pages/ChartPage')
);

function App() {
  return (
    <Suspense fallback={<div className="skeleton" aria-label="Loading..." />}>
      <ChartPage />
    </Suspense>
  );
}
```

---

### startTransition — keeping input responsive

```tsx
import { useState, startTransition, useMemo } from 'react';

function SearchableList({ items }: { items: Product[] }) {
  const [inputValue, setInputValue] = useState('');
  const [filterTerm, setFilterTerm] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);           // urgent: input reflects immediately
    startTransition(() => {
      setFilterTerm(e.target.value);         // non-urgent: can be deferred/interrupted
    });
  };

  const results = useMemo(
    () => items.filter(i => i.name.toLowerCase().includes(filterTerm.toLowerCase())),
    [items, filterTerm]
  );

  return (
    <>
      <input value={inputValue} onChange={handleChange} placeholder="Search..." />
      <ul>{results.map(i => <li key={i.id}>{i.name}</li>)}</ul>
    </>
  );
}
```

---

### Context split — avoid over-broadcasting

```tsx
// Bad: one fat context — theme change re-renders user consumers, and vice versa
const AppContext = createContext({ user: null, theme: 'light', notifications: [] });

// Good: split contexts by update frequency and consumer overlap
const UserContext    = createContext<User | null>(null);
const ThemeContext   = createContext<'light' | 'dark'>('light');
const NotifContext   = createContext<Notification[]>([]);

// Components subscribe only to what they need
function Avatar() {
  const user = useContext(UserContext);  // re-renders only when user changes
  return <img src={user?.avatar} alt={user?.name} />;
}
```

---

### Image optimization

```tsx
function HeroImage({ src, alt }: { src: string; alt: string }) {
  return (
    <picture>
      <source
        srcSet={`${src}?w=800&fmt=webp 800w, ${src}?w=1600&fmt=webp 1600w`}
        type="image/webp"
      />
      <img
        src={`${src}?w=800`}
        srcSet={`${src}?w=800 800w, ${src}?w=1600 1600w`}
        sizes="(max-width: 768px) 100vw, 50vw"
        alt={alt}
        loading="eager"          // LCP image — don't lazy load
        fetchPriority="high"     // preload hint to browser
        decoding="async"
        width={800}
        height={450}             // prevents CLS — reserves space before load
      />
    </picture>
  );
}
```

---

### Bundle analysis workflow

```bash
# 1. Install analyzer
npm install --save-dev webpack-bundle-analyzer

# 2. Generate stats file
npx react-scripts build --stats
# or for Vite:
npx vite build --reporter=verbose

# 3. Visualize
npx webpack-bundle-analyzer build/bundle-stats.json

# What to look for:
# - moment.js (300KB) → replace with date-fns (tree-shakable)
# - lodash (full build) → import { debounce } from 'lodash-es'
# - large icon libraries → import specific icons, not entire set
# - duplicate packages at different versions (two copies of react-dom)
```

---

## 7. React DevTools Profiler — Reading Flamegraphs

```
FLAMEGRAPH INTERPRETATION
─────────────────────────────────────────────────────────────────────

  ┌──────────────────────────────────────────────────────┐
  │  App  (2.3ms)                                        │
  ├────────────────────┬─────────────────────────────────┤
  │  Sidebar (0.1ms)   │  Dashboard (2.1ms) ← hot!       │
  │  [grey - not       ├──────────┬──────────────────────┤
  │   re-rendered]     │StatsBar  │  DataTable (1.8ms)   │
  │                    │(0.2ms)   ├──────┬───────────────┤
  │                    │          │Row   │  Row (1.5ms)  │
  │                    │          │x50   │  ← wasted?    │
  └────────────────────┴──────────┴──────┴───────────────┘

  Color coding:
  ● Grey    = did not render this commit (good)
  ● Green   = rendered, fast
  ● Yellow  = rendered, moderate
  ● Red     = rendered, slow — investigate

  "Why did this render?" button:
  → Shows: "Props changed: [value]" or "Hook 3 changed" or "Parent rendered"
  → If "Parent rendered" with no prop changes → React.memo candidate

  Ranked chart:
  → Shows components sorted by render duration
  → Jump straight to the worst offenders
```

**What to look for in a profiler session:**
1. Components rendering on every interaction that don't need to (grey = good, anything colored = cost)
2. "Wasted renders": component re-rendered but output didn't change (memo candidate)
3. Unexpectedly deep render cascades from a single state change
4. useEffect chains causing multiple sequential renders (waterfall)

---

## 8. Core Web Vitals — React's Impact

```
METRIC          WHAT IT MEASURES                    REACT'S IMPACT
─────────────────────────────────────────────────────────────────────
LCP             Largest Contentful Paint             Bundle size → parse/execute delay
(target <2.5s)  Time to largest visible element      Hydration blocking paint
                                                     Image optimization (srcset, WebP)
                                                     Route-based code splitting

CLS             Cumulative Layout Shift              Dynamic content without reserved space
(target <0.1)   Visual stability score               Lazy-loaded images missing dimensions
                                                     Font swap (FOUT)
                                                     Async components shifting layout

FID/INP         Interaction to Next Paint            Heavy render tasks blocking main thread
(target <200ms) Input responsiveness                 startTransition for non-urgent updates
                                                     Virtualization reducing reconciliation work
                                                     Debouncing expensive event handlers

TTFB            Time to First Byte                   SSR / streaming SSR (React 18)
(target <800ms) Server response time                 RSC (React Server Components)
                                                     Edge rendering (Cloudflare Workers / Vercel Edge)
```

---

## 9. Interview Cheat Sheet

```
QUICK-REFERENCE: WHEN TO USE WHAT
─────────────────────────────────────────────────────────────────────

React.memo         → When: parent re-renders often, child props are stable
                   → Not when: child re-renders for own state/context anyway
                   → Gotcha: need stable prop references (useCallback/useMemo for objects/fns)

useMemo            → When: expensive computation (>1ms) AND result is dep of hook or memo'd child
                   → Not when: computation is cheap, result changes every render
                   → Gotcha: memoized value persists in memory; adds closure overhead

useCallback        → When: function passed to React.memo'd child OR used as hook dep
                   → Not when: child is not memo'd (zero benefit, adds overhead)
                   → Gotcha: if deps change every render, function reference still changes

startTransition    → When: state update triggers expensive render that's not urgent (filtering, sorting)
                   → Not when: the update IS urgent (input value itself, user-expected immediate feedback)
                   → Effect: browser can process input events between render chunks

Virtualization     → When: list > ~100 items, especially if items are complex components
                   → Tool: TanStack Virtual (dynamic sizes), react-window (fixed sizes)
                   → Why: DOM nodes are the bottleneck, not React diffing

Code splitting     → Default: route-based (React.lazy per route)
                   → Also: heavy components (editors, chart libs, PDF viewers)
                   → Hint: webpackPrefetch for likely-next routes

Context split      → Rule: one context per update frequency group
                   → Test: if context A changes, should context B consumers re-render?
                   → Alternative: Zustand/Jotai for fine-grained subscriptions

Server Components  → When: pure rendering + data fetching, no interactivity
                   → Benefit: component JS never ships to client (zero bundle impact)
                   → Constraint: no useState, useEffect, event handlers

Bundle size        → Tool: webpack-bundle-analyzer / rollup-plugin-visualizer
                   → Targets: moment→date-fns, lodash→lodash-es (tree-shaking), icon sets (individual imports)
                   → Measure: main chunk <200KB gzipped as starting target

Core Web Vitals    → LCP: bundle size + image optimization + SSR
                   → CLS: set image dimensions, avoid layout-shifting async content
                   → INP: startTransition, virtualization, avoid blocking main thread

─────────────────────────────────────────────────────────────────────
THE GOLDEN RULE: MEASURE FIRST. OPTIMIZE SECOND.
Profile with DevTools before adding memo/useMemo anywhere.
─────────────────────────────────────────────────────────────────────

RE-RENDER TRIGGER CHEAT SHEET
  1. Own state changes       → always re-renders
  2. Parent re-renders       → re-renders (unless React.memo + stable props)
  3. Context changes         → re-renders (React.memo does NOT stop this)
  4. key prop changes        → full unmount + remount
  5. forceUpdate (class)     → always re-renders

TRAP QUESTION ANSWERS (summary)
  "memo prevents all re-renders"    → False: own state + context still trigger
  "useMemo always helps"            → False: cheap ops + frequent dep changes = net loss
  "map() is fine for big lists"     → False: DOM nodes are the bottleneck, virtualize
  "useCallback on every function"   → False: useless without memo'd child
  "React is slow"                   → Diagnose first: Profiler → flamegraph → real data
  "SSR solves performance"          → Partial: improves FCP, not TTI; need splitting + streaming too
  "empty dep [] = runs once"        → Strict Mode runs twice; always write cleanup
```

---

*Last updated: 2026-08-22 | 15-YOE Level | TypeScript + React 18*
