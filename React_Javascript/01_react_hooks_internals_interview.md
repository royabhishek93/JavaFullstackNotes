# React Hooks Internals — 15-YOE Interview Prep

> Target: Staff/Principal Engineer interviews, System Design + Deep Dive rounds
> Depth: Internals, tradeoffs, production war stories, not just API surface

---

## 1. Big Picture — React Fiber Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     REACT FIBER ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────────┘

  USER CODE (JSX / Components)
         │
         ▼
  ┌─────────────┐      createElement()     ┌──────────────────┐
  │  JSX / TSX  │ ──────────────────────►  │  React Elements  │
  │  (Babel)    │                          │  (plain objects) │
  └─────────────┘                          └────────┬─────────┘
                                                    │
                                                    ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                    FIBER RECONCILER                         │
  │                                                             │
  │  ┌──────────────────────────────────────────────────────┐  │
  │  │                  WORK LOOP                           │  │
  │  │                                                      │  │
  │  │  workInProgress ──► performUnitOfWork()              │  │
  │  │         │                  │                         │  │
  │  │         │           beginWork() ──► reconcile        │  │
  │  │         │                  │        children         │  │
  │  │         │           completeWork()──► build effect   │  │
  │  │         │                              list          │  │
  │  │         ▼                                            │  │
  │  │  [Each Fiber Node = unit of work]                   │  │
  │  │   • type, key, stateNode                            │  │
  │  │   • pendingProps, memoizedProps                     │  │
  │  │   • memoizedState  ◄── LINKED LIST OF HOOKS         │  │
  │  │   • effectTag (Placement/Update/Deletion)           │  │
  │  │   • child / sibling / return (parent)               │  │
  │  └──────────────────────────────────────────────────────┘  │
  │                                                             │
  │  TWO FIBER TREES (double buffering):                        │
  │  ┌─────────────────┐      ┌─────────────────┐             │
  │  │  current tree   │ ◄──► │ workInProgress  │             │
  │  │  (on screen)    │      │ tree (building) │             │
  │  └─────────────────┘      └─────────────────┘             │
  └─────────────────────────────────────────────────────────────┘
                        │
          scheduleMicrotask / scheduler
                        │
                        ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                   COMMIT PHASE (sync)                       │
  │                                                             │
  │  Phase 1: BeforeMutation  (getSnapshotBeforeUpdate)         │
  │  Phase 2: Mutation        (insertions, updates, deletions)  │
  │           └─► DOM is mutated here                          │
  │  Phase 3: Layout          (useLayoutEffect, componentDid*)  │
  │           └─► fires synchronously after DOM paint          │
  │                                                             │
  │  [PASSIVE EFFECTS — async after paint]                      │
  │  Phase 4: Passive         (useEffect callbacks)             │
  └─────────────────────────────────────────────────────────────┘
                        │
                        ▼
              Browser paints to screen

  ┌─────────────────────────────────────────────────────────────┐
  │            CONCURRENT MODE — INTERRUPTIBLE WORK LOOP        │
  │                                                             │
  │  Render phase (can be interrupted):                         │
  │  ┌─────────┐  timeSlice?  ┌──────────┐  yield?  ┌───────┐ │
  │  │ Fiber 1 │ ──────────── │ Fiber 2  │ ──────── │ yield │ │
  │  └─────────┘    yes       └──────────┘    yes   └───────┘ │
  │       ▲                                              │      │
  │       └──────────── resume next frame ───────────────┘      │
  │                                                             │
  │  Commit phase (NEVER interrupted):                          │
  │  BeforeMutation ──► Mutation ──► Layout ──► Passive         │
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │              HOOK LINKED LIST (per fiber node)              │
  │                                                             │
  │  fiber.memoizedState                                        │
  │        │                                                    │
  │        ▼                                                    │
  │  ┌───────────┐    ┌───────────┐    ┌───────────┐           │
  │  │ Hook #0   │ ─► │ Hook #1   │ ─► │ Hook #2   │ ─► null  │
  │  │ useState  │    │ useEffect │    │ useRef    │           │
  │  │ {state,   │    │ {create,  │    │ {current} │           │
  │  │  queue}   │    │  deps}    │    │           │           │
  │  └───────────┘    └───────────┘    └───────────┘           │
  │                                                             │
  │  On re-render: walk list in order, match by position        │
  │  If conditional hook: position shifts → WRONG STATE READ    │
  └─────────────────────────────────────────────────────────────┘
```

---

## 2. Conversational Interview Script

> How a 15-YOE engineer actually speaks — confident, concrete, no hand-waving.

---

### "Walk me through React Fiber — what problem does it solve?"

**Say this out loud:**

"Pre-Fiber, React used a recursive, synchronous reconciler. The call stack would get deep with complex trees and you couldn't interrupt it — if reconciliation took 50ms you'd drop frames. Fiber was a complete rewrite that turned the call stack into a heap-allocated linked list of work units, where each node is a Fiber. The key insight is that now the work loop can check after each unit whether the browser needs to do higher-priority work — input handling, animations — and yield. The render phase becomes interruptible. The commit phase stays synchronous because you can't partially mutate the DOM.

In practice this unlocks Concurrent Mode — React 18 features like useTransition and Suspense streaming depend entirely on this. When you wrap a state update in startTransition, you're telling React 'this render is low priority, yield if something more urgent comes in.' The scheduler handles that via message channel micro-tasks."

---

### "How do hooks actually work internally?"

**Say this out loud:**

"Every Fiber node has a `memoizedState` field that's the head of a singly-linked list. Each call to useState, useEffect, useRef — each one appends a node to that list on the first render. On subsequent renders, React walks the list in order, matching each hook call to its position in the list. That's why hooks can't be conditional — if you add or skip a hook call, every subsequent hook reads from the wrong node in the list. The linter catches it statically, but the real enforcement is this runtime linked list.

When you call a useState setter, React enqueues an update on that hook's queue object. On the next render, it replays pending updates to compute the new state."

---

### "Explain useEffect cleanup timing — when exactly does it run?"

**Say this out loud:**

"Cleanup runs in two situations: before the effect re-runs due to changed deps, and when the component unmounts. The order is: cleanup previous effect, then run new effect. Both happen asynchronously after paint, in the passive effects phase. useLayoutEffect cleanup is synchronous after DOM mutation but before paint — that's the right place if you're touching scroll position or measuring layout.

The gotcha I've hit in production: if your component mounts, renders with data, then the dep changes, you get cleanup → new effect. If you're not careful you'll cancel and restart a subscription more times than intended. I usually add a debug log in cleanup during development to verify it's running exactly as often as I expect."

---

### "What's the difference between useRef and useState?"

**Say this out loud:**

"Both persist values across renders, but useState triggers a re-render when updated, useRef does not. The ref object's `.current` property is mutable and React never reads it during rendering — it's completely outside the reactive model. This makes refs the right tool for: DOM node references, storing the previous value of a prop, holding a timer ID or subscription handle, or caching something you compute once and want stable across renders without re-rendering.

The trap is using a ref to store display state — 'I'll use a ref because setState feels heavy.' If you need the UI to reflect a value, it must be state. If the mutation is side-effecty and invisible to the UI, ref is correct."

---

### "When does useCallback actually help performance?"

**Say this out loud:**

"useCallback memoizes a function reference — it returns the same function object across renders as long as deps don't change. It only helps performance in two specific scenarios: when you pass the function to a child wrapped in React.memo, and when the function is a dependency of another hook like useEffect or useMemo. In those cases, stable reference prevents unnecessary child re-renders or effect re-runs.

What it does NOT do is make the function faster to execute. And it's not free — it adds a comparison on every render. I've seen codebases where every function in every component is wrapped in useCallback 'for performance.' That's a net negative. Profile first, wrap second."

---

## 3. Scenario-Based Q&As — Production Context

---

### Q1: Your useEffect is causing an infinite loop in production. How do you diagnose and fix it?

**Answer:**

An infinite loop means the effect is re-running continuously. The cause is always either: (1) a dep in the dependency array is a new object/function reference on every render, or (2) you're setting state inside the effect using a value that's in the dependency array.

Diagnosis steps I follow in production:
1. Add `console.count('effect name')` in the effect body.
2. Log the deps manually to see which one changed: `console.log({ dep1, dep2 })`.
3. Use `useWhyDidYouUpdate` from ahooks or write a small custom hook.

Common fix patterns:

```typescript
// Problem: object dep recreated every render
useEffect(() => {
  fetchData(config);
}, [config]); // config = { url: '/api' } inline

// Fix 1: move config outside component or useMemo
const config = useMemo(() => ({ url: '/api' }), []);

// Fix 2: use specific primitive deps instead
useEffect(() => {
  fetchData({ url });
}, [url]);
```

The deeper fix is understanding that useEffect deps should be exhaustive (ESLint react-hooks/exhaustive-deps enforces this) but stable. Whenever an object or function is a dep, it should either come from outside the component, be memoized, or you need to extract the primitive values from it.

---

### Q2: A form component re-renders on every keystroke, making the UI slow. What do you do?

**Answer:**

First, profile with React DevTools Profiler to confirm the bottleneck is render count vs render cost. Then apply the appropriate fix:

```typescript
// Controlled input — re-renders parent on every keystroke
const SlowForm = () => {
  const [name, setName] = useState('');
  return <ExpensiveChild data={someHeavyData} />;
};

// Fix 1: Split state — isolate fast-changing state
const FastForm = () => {
  return (
    <>
      <NameInput />         {/* isolated, only this re-renders */}
      <ExpensiveChild data={someHeavyData} />  {/* stable */}
    </>
  );
};

// Fix 2: Memo the expensive child
const ExpensiveChild = React.memo(({ data }) => {
  // only re-renders when data changes
});

// Fix 3: Uncontrolled + useRef for fire-on-submit forms
const UncontrolledForm = () => {
  const nameRef = useRef<HTMLInputElement>(null);
  const handleSubmit = () => {
    const value = nameRef.current?.value;
    // process value
  };
  return <input ref={nameRef} />;
};
```

I usually reach for Fix 1 (state isolation) before memoization — it's structural and doesn't require maintaining deps arrays.

---

### Q3: You need to fetch data on mount, but you're in React 18 Strict Mode and the effect runs twice. What happens?

**Answer:**

In React 18 Strict Mode (development only), effects deliberately mount → unmount → remount to surface bugs in cleanup logic. If your fetch runs twice, it means your cleanup is not cancelling the in-flight request.

```typescript
// Broken: two requests fire, second overwrites first
useEffect(() => {
  fetch('/api/data').then(setData);
}, []);

// Correct: AbortController cancels the first fetch on cleanup
useEffect(() => {
  const controller = new AbortController();
  
  fetch('/api/data', { signal: controller.signal })
    .then(res => res.json())
    .then(setData)
    .catch(err => {
      if (err.name !== 'AbortError') throw err;
    });

  return () => controller.abort();
}, []);
```

The double-invocation is intentional — it's React telling you "cleanup must fully undo what the effect did." If you're using React Query or SWR, they handle this for you (deduplication + cancellation built in). For raw fetches, AbortController is the pattern.

---

### Q4: A component subscribes to a WebSocket in useEffect. Users report memory leaks. What's wrong?

**Answer:**

Classic case: the cleanup function isn't unsubscribing, or the component is conditionally rendered and the WebSocket stays open.

```typescript
// Problematic version
useEffect(() => {
  const ws = new WebSocket('wss://api.example.com');
  ws.onmessage = (e) => setMessages(prev => [...prev, JSON.parse(e.data)]);
  // no cleanup!
}, []);

// Fixed version
useEffect(() => {
  const ws = new WebSocket('wss://api.example.com');
  
  const handleMessage = (e: MessageEvent) => {
    setMessages(prev => [...prev, JSON.parse(e.data) as Message]);
  };
  
  ws.addEventListener('message', handleMessage);
  
  return () => {
    ws.removeEventListener('message', handleMessage);
    ws.close();
  };
}, []); // empty deps: one connection for component lifetime
```

I'd also advocate extracting this into a custom hook `useWebSocket(url)` so the lifecycle is encapsulated and reusable — and testable in isolation.

---

### Q5: You have a custom hook that wraps a third-party analytics SDK. How do you ensure it initializes once per app, not once per component?

**Answer:**

Move initialization outside the hook or use a module-level singleton. useEffect runs per component instance — if 50 components call your hook, you get 50 initializations.

```typescript
// Module-level singleton — initialized once when module loads
let analyticsInstance: Analytics | null = null;

const getAnalytics = (): Analytics => {
  if (!analyticsInstance) {
    analyticsInstance = new Analytics({ key: process.env.REACT_APP_ANALYTICS_KEY! });
  }
  return analyticsInstance;
};

export const useAnalytics = () => {
  const analytics = useMemo(() => getAnalytics(), []);
  
  const track = useCallback((event: string, props?: Record<string, unknown>) => {
    analytics.track(event, props);
  }, [analytics]);
  
  return { track };
};
```

For SSR environments (Next.js), the module singleton pattern works but you need to guard against server-side initialization of browser-only SDKs — check `typeof window !== 'undefined'`.

---

### Q6: A dashboard renders 500 rows. Users complain about sluggish interactions. What's your approach?

**Answer:**

Three-stage approach:

1. **Profile first** — React DevTools Profiler, identify which component is expensive and how often it renders.

2. **Virtualization** — 500 DOM nodes is too many. Use react-window or TanStack Virtual. Only render visible rows.

3. **Memoization as last resort** — if each row is expensive to render and re-renders due to parent state:

```typescript
// Row memoized — only re-renders when its specific data changes
const DashboardRow = React.memo(({ row }: { row: RowData }) => {
  return <tr>{/* expensive cells */}</tr>;
}, (prevProps, nextProps) => {
  // custom comparison — only re-render if row data actually changed
  return prevProps.row.id === nextProps.row.id && 
         prevProps.row.updatedAt === nextProps.row.updatedAt;
});
```

The production reality: virtualization usually gives you 10x improvement; memoization gives you 1.2x. Do virtualization first.

---

### Q7: How do you share state between two sibling components without prop drilling through 5 levels?

**Answer:**

Three options depending on scope:

1. **Lift state + Context** — for state that's logically "app-wide" or "feature-wide":

```typescript
const DashboardContext = createContext<DashboardContextValue | null>(null);

export const DashboardProvider = ({ children }: { children: React.ReactNode }) => {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  
  const value = useMemo(
    () => ({ selectedId, setSelectedId }),
    [selectedId]
  );
  
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
};

// Custom hook enforces context is available
export const useDashboard = () => {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error('useDashboard must be used within DashboardProvider');
  return ctx;
};
```

2. **Component composition** — for state that only spans a subtree, lift the state to the closest common ancestor and pass via children/render props.

3. **External store** — Zustand or Redux Toolkit for truly global state (auth, cart, etc.) where Context performance won't scale.

---

### Q8: You're seeing stale closures in an event handler. The state is always the value from the first render. How do you fix it?

**Answer:**

Stale closure happens when a function captures a snapshot of state at creation time and the state updates, but the function is never recreated. Classic in event listeners attached in useEffect with empty deps.

```typescript
// Stale closure — count is always 0
useEffect(() => {
  const handleKey = () => {
    console.log(count); // stale: always the initial value
  };
  window.addEventListener('keydown', handleKey);
  return () => window.removeEventListener('keydown', handleKey);
}, []); // empty deps — handler never updated

// Fix 1: ref pattern — ref always points to latest value
const countRef = useRef(count);
useEffect(() => { countRef.current = count; }, [count]);

useEffect(() => {
  const handleKey = () => console.log(countRef.current); // always fresh
  window.addEventListener('keydown', handleKey);
  return () => window.removeEventListener('keydown', handleKey);
}, []);

// Fix 2: functional updater — no closure on state needed
const increment = () => setCount(c => c + 1);
```

The ref pattern is the standard idiom. I've also seen useEffectEvent (React 19 proposal) designed specifically for this case — it creates a stable function that always reads the latest state.

---

## 4. Advanced Scenario Q&As — Deep Dive

---

### A1: Explain how useTransition works internally in Concurrent Mode.

**Answer:**

`startTransition` marks a state update as "transition" priority — lower priority than urgent updates. Internally, React 18 uses a priority lane system (lanes are bit-flags). A transition update goes into the TransitionLane; urgent updates (like typing) go into InputContinuousLane or SyncLane.

When the work loop processes work, it checks the current time budget (via `shouldYield()`). If an urgent update arrives during a transition render, React can interrupt the transition render, process the urgent update, commit it (so the UI stays responsive), then resume the transition render from scratch or continue from where it yielded.

```typescript
// useTransition: UI stays responsive during expensive state change
const [isPending, startTransition] = useTransition();

const handleSearch = (query: string) => {
  setInputValue(query); // urgent: updates input immediately
  
  startTransition(() => {
    setSearchResults(expensiveFilter(query)); // low priority: can be interrupted
  });
};

// isPending = true while transition render is in-flight
return (
  <div>
    <Input value={inputValue} onChange={e => handleSearch(e.target.value)} />
    {isPending && <Spinner />}
    <ResultList results={searchResults} />
  </div>
);
```

Key distinction: `isPending` is true during the transition. The old results stay visible until the new render is ready — no intermediate loading flash. This is fundamentally different from showing a loading state while fetching; this is about rendering being async.

---

### A2: What is useDeferredValue and how does it differ from useTransition?

**Answer:**

`useDeferredValue` defers re-renders of a specific value — it returns a "stale" copy of the value and schedules a lower-priority re-render with the fresh value. The conceptual difference: `useTransition` wraps the state update; `useDeferredValue` wraps the consumed value. You use `useDeferredValue` when you don't control where the state is set (e.g., it comes from a parent prop).

```typescript
// When you control the setter: useTransition
const [value, setValue] = useState('');
const [isPending, startTransition] = useTransition();
const handleChange = (v: string) => {
  startTransition(() => setValue(v));
};

// When you don't control the setter (value comes from props/context): useDeferredValue
const SearchResults = ({ query }: { query: string }) => {
  const deferredQuery = useDeferredValue(query);
  const isStale = query !== deferredQuery;
  
  return (
    <div style={{ opacity: isStale ? 0.7 : 1 }}>
      <ExpensiveList filter={deferredQuery} />
    </div>
  );
};
```

Internally, `useDeferredValue` schedules a second render at transition priority with the new value. The first render uses the old deferred value — which is what makes the component "lag behind" by one priority cycle.

---

### A3: Walk through the reconciliation algorithm — how does React decide what changed?

**Answer:**

React's reconciler performs a tree diff using two heuristics that trade theoretical completeness (O(n³)) for practical performance (O(n)):

1. **Type assumption**: if two elements have different types (e.g., `<div>` → `<span>`), React tears down the entire subtree and builds a new one. No attempt to reuse children.

2. **Key assumption**: for lists, `key` is the stable identity. Without keys, React matches by index — inserting at the front forces all siblings to re-render. With keys, React can identify which item moved, was added, or was removed.

```typescript
// Index-keyed: adding "Alice" at position 0 invalidates all nodes
const BadList = ({ users }: { users: User[] }) => (
  <ul>
    {users.map((u, i) => <UserCard key={i} user={u} />)}
  </ul>
);

// Stable-keyed: only new item is mounted
const GoodList = ({ users }: { users: User[] }) => (
  <ul>
    {users.map(u => <UserCard key={u.id} user={u} />)}
  </ul>
);
```

At the Fiber level, reconciliation happens in `beginWork`. For each Fiber, React creates a new "work in progress" fiber, diffs it against the current fiber, and marks it with effect tags (Placement, Update, Deletion). The effect list is collected and replayed in the commit phase.

---

### A4: How does React 18 automatic batching change behavior compared to React 17?

**Answer:**

In React 17, batching only happened inside React-controlled event handlers (synthetic events). Any state updates inside `setTimeout`, `Promise.then`, native event listeners, or async code fired separate re-renders.

React 18 batches all state updates by default — regardless of where they originate — using the scheduler. This is a breaking behavior change for some patterns.

```typescript
// React 17: three separate renders
setTimeout(() => {
  setCount(c => c + 1);  // render 1
  setFlag(true);          // render 2
  setData([]);            // render 3
}, 1000);

// React 18: one render (automatic batching)
setTimeout(() => {
  setCount(c => c + 1);
  setFlag(true);
  setData([]);
  // single re-render
}, 1000);

// React 18: opt OUT of batching (rare, but sometimes needed)
import { flushSync } from 'react-dom';
setTimeout(() => {
  flushSync(() => setCount(c => c + 1)); // immediate render
  flushSync(() => setFlag(true));         // another immediate render
}, 1000);
```

Real-world impact: if you had code that depended on intermediate state between setters (e.g., reading DOM layout between two state changes), React 18 batching will change that. `flushSync` is the escape hatch. I've hit this in animation code that needed to read layout between state updates.

---

## 5. Senior Trap Questions

> Format: TRAP NAME → What interviewers expect you to say → What's actually true → Correct answer

---

### Trap 1: "useEffect with [] runs only once"

**The trap:** Candidate says "empty array means it runs once, done."

**What's actually true:**
- The EFFECT runs once on mount — correct.
- The CLEANUP runs on unmount — often forgotten.
- In React 18 Strict Mode (dev), the component mounts, unmounts, then remounts — so the effect runs TWICE and cleanup runs ONCE in between.
- The ESLint `react-hooks/exhaustive-deps` rule enforces that all referenced values in the effect body are in the deps array. Empty array is often wrong if you're using any component values inside.

**Correct answer:**
"Empty array means the effect runs after initial mount and cleanup runs on unmount. But be careful — Strict Mode in development runs effects twice to surface cleanup bugs. And the deps array should be exhaustive: if you're referencing a prop or state inside the effect and it's not in the array, you have a stale closure bug. Empty array is only correct when the effect truly has no dependencies — like a one-time analytics page view event."

---

### Trap 2: "useCallback always improves performance"

**The trap:** Candidate wraps every callback in useCallback "as a best practice."

**What's actually true:**
- useCallback adds cost: it creates a closure AND runs a dep comparison on every render.
- It only prevents re-renders when the function is passed to a `React.memo`-wrapped child.
- It only prevents effect re-runs when the function is in a useEffect/useMemo dep array.
- In all other cases it's overhead, not optimization.

**Correct answer:**
"useCallback memoizes a function reference so it's stable across renders. It's not free — it allocates and compares on every render. It only pays off if (a) you pass it to a memoized child as a prop, or (b) it's a dep in another hook and you don't want that hook to re-run. I've audited codebases where every component function was wrapped in useCallback 'for performance' — it was actually slowing things down. My rule: profile first, wrap second."

---

### Trap 3: "useState setter is synchronous"

**The trap:** Candidate assumes `setState(value)` immediately updates state, and accesses state right after the call.

**What's actually true:**
- In React 18, ALL state updates are batched — including in event handlers — so the state variable is NOT updated on the next line.
- Even in React 17, within React event handlers, updates were batched (not synchronous).
- The update is applied on the next render cycle.

**Correct answer:**
"setState is not synchronous. React 18 batches all state updates — you won't see the new value on the next line after a setState call. If you need to act on the new value, use the functional updater form or a useEffect that depends on the state. If you absolutely need synchronous application, flushSync is the escape hatch but it's rare and has performance cost."

```typescript
// Wrong assumption
const handleClick = () => {
  setCount(5);
  console.log(count); // still 0 (or previous value) — stale closure
};

// Correct: use functional form or read from next render
const handleClick = () => {
  setCount(prev => {
    console.log('next value:', prev + 1);
    return prev + 1;
  });
};
```

---

### Trap 4: "Mutating useRef causes a re-render"

**The trap:** Candidate thinks `ref.current = newValue` triggers a render.

**What's actually true:**
- `ref.current` mutation is completely invisible to React. No re-render occurs.
- React does not track ref mutations in any way.
- This is exactly why refs exist — stable mutable container that doesn't trigger renders.
- Trying to use a ref to drive UI is a common bug: the UI never updates.

**Correct answer:**
"Mutating ref.current does NOT cause a re-render. The ref object is a plain mutable container — React does not observe it. That's the whole point: for side-effecty, non-display data like timer IDs, DOM node references, or cached values you need across renders without triggering a render cycle. If you accidentally store display state in a ref, the UI silently goes stale. I use the rule: if the UI needs to reflect it, it's state; if it's plumbing, it's a ref."

---

### Trap 5: "Can I call hooks inside loops or conditions?"

**The trap:** Candidate says "no, because the linter will yell at you."

**What's actually true:**
- The linter catches it statically — but the real reason is runtime correctness.
- Hooks are stored in a linked list on the fiber node, indexed by call order.
- A conditional or loop changes how many nodes are in the list between renders.
- On re-render, React walks the list by position — a skipped hook shifts every subsequent hook to the wrong node.
- This causes wrong state to be returned for every subsequent hook in the component.
- The error is not always immediate — it can cause subtle, hard-to-reproduce bugs.

**Correct answer:**
"No, and the reason isn't just ESLint. Hooks are stored as a linked list on the fiber node. React matches each hook call to its position in the list on every render. A conditional hook call changes the list length, so every hook after it reads from the wrong node — you get wrong state, wrong refs, wrong effects. The linter is a static guard but it doesn't prevent you from doing this if you bypass it. The architectural solution: move the conditional logic inside the hook, not around it."

```typescript
// WRONG — breaks linked list
if (isLoggedIn) {
  const user = useCurrentUser(); // hook #3 sometimes, sometimes skipped
}

// CORRECT — hook always called, condition inside
const user = useCurrentUser({ enabled: isLoggedIn }); // always hook #3
```

---

### Trap 6: "React.memo prevents all re-renders"

**The trap:** Candidate says "wrap in memo and it won't re-render."

**What's actually true:**
- React.memo only does a shallow prop comparison by default.
- If any prop is a new reference (object, array, function) on every render, memo is bypassed every time.
- memo has a cost: the comparison itself runs on every parent re-render.
- memo does NOT prevent re-renders triggered by context changes or internal state.

**Correct answer:**
"React.memo does a shallow comparison of props by default — it only skips the re-render if all props pass a `===` check. Object and function props are new references on every render unless memoized with useMemo/useCallback. So memo on a component that receives an inline object prop does nothing. And memo doesn't prevent re-renders from useContext changes — that's a different problem requiring context splitting or a state management library. I treat memo as a last resort after profiling, not a default."

---

## 6. Production Code Examples

---

### Custom Hook: Data Fetching with Cancellation

```typescript
interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
}

function useFetch<T>(url: string): FetchState<T> {
  const [state, setState] = useState<FetchState<T>>({
    data: null, loading: true, error: null,
  });

  useEffect(() => {
    const controller = new AbortController();
    setState(s => ({ ...s, loading: true, error: null }));

    fetch(url, { signal: controller.signal })
      .then(res => { if (!res.ok) throw new Error(res.statusText); return res.json(); })
      .then(data => setState({ data, loading: false, error: null }))
      .catch(err => {
        if (err.name !== 'AbortError') {
          setState({ data: null, loading: false, error: err });
        }
      });

    return () => controller.abort();
  }, [url]);

  return state;
}
```

---

### Custom Hook: Debounced Value

```typescript
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Usage: search input that doesn't fire on every keystroke
const SearchBar = () => {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);
  const { data } = useFetch<Result[]>(`/api/search?q=${debouncedQuery}`);
  // ...
};
```

---

### Custom Hook: Previous Value (useRef pattern)

```typescript
function usePrevious<T>(value: T): T | undefined {
  const ref = useRef<T | undefined>(undefined);

  useEffect(() => {
    ref.current = value;
  }); // no deps: runs after every render, stores current as "previous" for next render

  return ref.current;
}

// Usage: animate on value change
const Counter = ({ count }: { count: number }) => {
  const prevCount = usePrevious(count);
  const direction = prevCount !== undefined && count > prevCount ? 'up' : 'down';
  return <span className={`animate-${direction}`}>{count}</span>;
};
```

---

### useTransition: Non-Blocking Search Filter

```typescript
interface Product { id: string; name: string; category: string; }

const ProductSearch = ({ products }: { products: Product[] }) => {
  const [query, setQuery] = useState('');
  const [filtered, setFiltered] = useState(products);
  const [isPending, startTransition] = useTransition();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value); // urgent: update input immediately

    startTransition(() => {
      // low-priority: expensive filtering doesn't block the input
      setFiltered(products.filter(p =>
        p.name.toLowerCase().includes(value.toLowerCase())
      ));
    });
  };

  return (
    <div>
      <input value={query} onChange={handleChange} placeholder="Search..." />
      {isPending && <span>Filtering...</span>}
      <ul style={{ opacity: isPending ? 0.6 : 1 }}>
        {filtered.map(p => <li key={p.id}>{p.name}</li>)}
      </ul>
    </div>
  );
};
```

---

### Context with Stable Reference (Avoids All-Consumer Re-Render)

```typescript
interface AuthContextValue {
  user: User | null;
  login: (credentials: Credentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);

  const login = useCallback(async (credentials: Credentials) => {
    const u = await authService.login(credentials);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  // useMemo prevents new context value on every render (only changes when user changes)
  const value = useMemo(() => ({ user, login, logout }), [user, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
```

---

### Stale Closure Fix with useRef

```typescript
// Timer that logs current count — without ref, always logs initial value
const TimerDisplay = () => {
  const [count, setCount] = useState(0);
  const countRef = useRef(count);

  // Keep ref in sync with state
  useEffect(() => { countRef.current = count; }, [count]);

  useEffect(() => {
    const interval = setInterval(() => {
      // ref always has the latest value — no stale closure
      console.log('Current count:', countRef.current);
    }, 1000);
    return () => clearInterval(interval);
  }, []); // interval set up once, but reads fresh value via ref

  return <button onClick={() => setCount(c => c + 1)}>{count}</button>;
};
```

---

### Form Handling with useReducer (Complex State)

```typescript
type FormAction =
  | { type: 'SET_FIELD'; field: string; value: string }
  | { type: 'SET_ERROR'; field: string; error: string }
  | { type: 'RESET' };

interface FormState { values: Record<string, string>; errors: Record<string, string>; }

const formReducer = (state: FormState, action: FormAction): FormState => {
  switch (action.type) {
    case 'SET_FIELD':
      return { ...state, values: { ...state.values, [action.field]: action.value },
               errors: { ...state.errors, [action.field]: '' } };
    case 'SET_ERROR':
      return { ...state, errors: { ...state.errors, [action.field]: action.error } };
    case 'RESET':
      return { values: {}, errors: {} };
    default: return state;
  }
};

const useForm = (initial: Record<string, string>) => {
  const [state, dispatch] = useReducer(formReducer, { values: initial, errors: {} });
  const setField = useCallback((field: string, value: string) =>
    dispatch({ type: 'SET_FIELD', field, value }), []);
  const setError = useCallback((field: string, error: string) =>
    dispatch({ type: 'SET_ERROR', field, error }), []);
  const reset = useCallback(() => dispatch({ type: 'RESET' }), []);
  return { ...state, setField, setError, reset };
};
```

---

## 7. Interview Cheat Sheet

> One paragraph per topic — memorize these as your verbal "opening statement" for each concept.

---

**React Fiber Architecture**
Fiber is a complete rewrite of React's reconciler that turned a recursive synchronous algorithm into an iterative, interruptible one. Each component maps to a Fiber node — a heap-allocated object with type, props, state (as a hook linked list), and effect tags. React maintains two trees: current (what's on screen) and workInProgress (what's being built). The render phase walks and diffs the Fiber tree and is interruptible in Concurrent Mode. The commit phase mutates the DOM and is always synchronous. This architecture is what makes Concurrent Mode, Suspense, and streaming possible.

**useState Internals**
Every useState call appends a node to the Fiber's memoizedState linked list. On mount, nodes are created; on update, React walks the list by position, matching each hook call to its node. The setter enqueues an update on the hook's queue object, and on the next render, React replays the queue to compute new state. Because React matches hooks by position, any hook call that's conditional or inside a loop changes the list structure and corrupts all subsequent hook reads — that's why the Rules of Hooks exist at a structural, not stylistic, level.

**useEffect Cleanup and Deps**
useEffect runs after the browser has painted — asynchronously in the passive effects phase. The cleanup function runs before the next effect execution and on unmount. Empty deps array means run once on mount / cleanup on unmount, but React 18 Strict Mode doubles this in dev to expose missing cleanup. The dependency array must be exhaustive — every value from the component scope referenced inside the effect should be listed, or you get a stale closure bug. Infinite loops arise when a dep is a new object/function reference every render, or when the effect sets state that's in its own dep array.

**useRef vs useState**
Both persist values across renders. useState triggers a re-render on update; useRef mutation is invisible to React and never triggers a re-render. Use refs for: DOM node access, timer/subscription handles, storing previous values, and any mutable value that drives side effects rather than UI. The wrong pattern: storing display data in a ref to "avoid re-renders" — the UI silently goes stale. The right pattern: refs as escape hatches from React's reactive model, not shortcuts around it.

**useCallback vs useMemo**
useMemo memoizes a computed value; useCallback memoizes a function reference (which is really useMemo for a function factory). Both take a dep array and only recompute when deps change. Neither is free — they add closure allocation and dep comparison overhead on every render. They pay off when (a) the memoized value/function is passed to a React.memo-wrapped child as a prop (prevents child re-renders), or (b) it's in a hook's dep array (prevents hook re-execution). Never apply them preemptively; profile to confirm render costs exist before memoizing.

**Custom Hooks**
Custom hooks are functions that start with `use`, follow the Rules of Hooks internally, and encapsulate stateful logic. They enable sharing stateful behavior — fetch logic, form state, subscriptions, media queries — without render prop gymnastics or HOC wrapping. Each component that calls a custom hook gets its own isolated state — hooks compose behavior, not state. The key design rule: a custom hook should have a single, well-defined responsibility and should return a clean API, not raw internal state. Extract hooks when the same effect/state pattern appears in two or more components.

**React 18: useTransition and useDeferredValue**
useTransition gives you `startTransition`, which marks a state update as low priority. The scheduler can interrupt a transition render if an urgent update arrives, keeping the UI responsive. useDeferredValue defers a specific consumed value — you use it when you don't control the state setter. Both produce "concurrent" renders: the old UI stays visible while the new render is in progress. `isPending` (from useTransition) or a `value !== deferredValue` check lets you show a loading indicator. These are the tools that replace manual debouncing for render-heavy UI paths.

**Strict Mode Double-Invocation**
React 18 Strict Mode (dev only) deliberately mounts, unmounts, then remounts every component. Effects run, cleanup runs, effects run again. This is intentional: React is asserting that your effect-cleanup pair is idempotent — that cleanup fully undoes the effect. If this reveals bugs (duplicate network requests, doubled subscriptions, stale state), those are real bugs that would surface in production during fast navigation or React's planned "offscreen" feature. Fix them with proper cleanup (AbortController, unsubscribe, clearInterval) rather than working around Strict Mode.

**Hooks Ordering Constraint**
The linked list structure of hooks means call order must be stable across renders. React matches hooks by position — hook #1 always gets the first node, hook #2 the second, and so on. A conditional hook changes the list length for one render path, shifting all subsequent hooks to the wrong nodes. You get state from a different variable, effects from different deps — silent, hard-to-reproduce bugs. The solution is always to keep all hook calls unconditional and move branching logic inside hooks: `const data = useData({ enabled: condition })` rather than `if (condition) { const data = useData(); }`.

**Concurrent Mode**
Concurrent Mode is React's execution model where the render phase is time-sliced and interruptible. The scheduler allocates time budgets per frame; `shouldYield()` is called after each Fiber unit of work. If time is up or a higher-priority update arrived, React yields control back to the browser, then resumes. The commit phase is always synchronous and non-interruptible to ensure DOM consistency. Concurrent Mode enables features like useTransition, Suspense with streaming, and future "offscreen" prerendering. It doesn't automatically make everything faster — it makes the app more responsive under load by preventing long rendering tasks from blocking input handling.

**Hook Rules Enforcement**
The two Rules of Hooks — only call hooks at the top level, only call hooks from React functions — are enforced by the `eslint-plugin-react-hooks` linter rule. The linter does static analysis on call patterns and flags violations. However, it cannot catch every dynamic violation (e.g., conditionals based on runtime data that look like compile-time patterns). The runtime enforcement is the linked list itself — violations don't throw immediately, they silently corrupt hook state. This is why the rules feel strict: they're not stylistic constraints, they're correctness invariants for the underlying data structure.

---

## Appendix: Quick Reference — Hooks Behavior Matrix

```
Hook            | Re-renders on change? | Survives re-render? | Cleanup? | Async?
----------------|----------------------|--------------------|---------|---------
useState        | YES                  | YES                | NO      | Batched
useReducer      | YES                  | YES                | NO      | Batched
useRef          | NO                   | YES                | NO      | N/A
useMemo         | NO (value recomputed)| YES                | NO      | NO
useCallback     | NO (fn recomputed)   | YES                | NO      | NO
useEffect       | N/A (side effect)    | YES (cleanup)      | YES     | After paint
useLayoutEffect | N/A (side effect)    | YES (cleanup)      | YES     | Before paint
useContext      | YES (on ctx change)  | YES                | NO      | NO
useTransition   | YES (isPending)      | YES                | NO      | Concurrent
useDeferredValue| YES (on settle)      | YES                | NO      | Concurrent
```

---

*This file covers React 18 internals at the depth expected of a Staff/Principal engineer.
Review the Cheat Sheet section aloud 2-3x before any technical interview round.*
