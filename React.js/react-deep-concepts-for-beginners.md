# React — Deep Concepts for New Learners
## Every "Why" Explained | Real Analogies | Step-by-Step Diagrams

> Written for someone who knows basic React (components, useState, useEffect)
> and wants to understand HOW and WHY things work under the hood.

---

## Before You Read This — Quick Vocabulary

```
DOM         = the actual webpage elements your browser shows
Virtual DOM = React's copy of the DOM kept in memory (JavaScript object)
Render      = React figuring out what the UI should look like
Re-render   = React doing that again because something changed
Component   = a function that returns JSX (your UI building block)
State       = data that lives inside a component and can change
Props       = data passed INTO a component from a parent
Hook        = a special React function (starts with "use")
Bundle      = all your JS files compressed into one file for the browser
```

---

# CHAPTER 1: Why Does React Even Exist?

## The Problem Before React

Imagine you're building a shopping cart. The user adds an item.
Now you need to update:
- The cart count in the header (shows "3")
- The cart sidebar (shows the new item)
- The total price at the bottom
- The "Add to Cart" button (maybe disable it if max quantity reached)

**Without React (plain JavaScript):**

```
PLAIN JS APPROACH:
─────────────────────────────────────────────────────────
User clicks "Add to Cart"
  │
  ▼
You write code to:
  document.getElementById('cart-count').innerText = '3';
  document.getElementById('cart-sidebar').innerHTML = '...new HTML...';
  document.getElementById('total-price').innerText = '₹2,499';
  document.getElementById('add-btn-101').disabled = true;

PROBLEM 1: You manually track EVERYTHING
PROBLEM 2: If you forget one element → UI shows wrong data
PROBLEM 3: 50 elements to update? You write 50 lines of update code
PROBLEM 4: Order matters — update price before quantity = wrong total
```

**With React:**

```
REACT APPROACH:
─────────────────────────────────────────────────────────
User clicks "Add to Cart"
  │
  ▼
setCartItems([...cartItems, newItem]);  ← just update the data
  │
  ▼
React automatically figures out what changed on the page
React updates ONLY those parts of the DOM

YOU think about DATA.
REACT handles the DOM.
```

**That's the core idea:** React lets you describe what your UI *should look like* based on your data, and it handles making the real webpage match that description.

---

# CHAPTER 2: The Virtual DOM — React's Draft Paper

## What Is The Virtual DOM?

Think of it like this:

```
ANALOGY: Editing a document
────────────────────────────────────────────────────────────
WITHOUT Virtual DOM (direct DOM manipulation):
  You're editing a PUBLISHED newspaper
  Every change = reprint the whole newspaper
  Want to fix one typo? Reprint all 50 pages. Expensive.

WITH Virtual DOM:
  You have a DRAFT on paper
  Edit the draft as much as you want (cheap)
  Compare draft vs published version
  Only reprint the PAGES THAT CHANGED
  One typo fix = reprint 1 page, not 50
```

```
HOW IT WORKS IN REACT:
────────────────────────────────────────────────────────────

STEP 1: Initial Render
─────────────────────
Your Component returns JSX:
  <div>
    <h1>Cart (2 items)</h1>
    <p>Total: ₹1,500</p>
  </div>

React creates a Virtual DOM (just a JS object):
  {
    type: 'div',
    children: [
      { type: 'h1', children: 'Cart (2 items)' },
      { type: 'p',  children: 'Total: ₹1,500' }
    ]
  }

React also creates the REAL DOM (what you see in browser):
  <div>
    <h1>Cart (2 items)</h1>
    <p>Total: ₹1,500</p>
  </div>

STEP 2: User adds one more item (state changes)
───────────────────────────────────────────────
Your Component re-renders, returns NEW JSX:
  <div>
    <h1>Cart (3 items)</h1>    ← CHANGED
    <p>Total: ₹2,000</p>       ← CHANGED
  </div>

React creates NEW Virtual DOM:
  {
    type: 'div',
    children: [
      { type: 'h1', children: 'Cart (3 items)' },  ← different
      { type: 'p',  children: 'Total: ₹2,000' }    ← different
    ]
  }

STEP 3: Diffing (comparing old vs new Virtual DOM)
───────────────────────────────────────────────────
  OLD Virtual DOM          NEW Virtual DOM
  ───────────────          ───────────────
  div         ←────────►  div          [same — no update]
  └─ h1: "2"  ←────────►  └─ h1: "3"  [DIFFERENT — update]
  └─ p: 1500  ←────────►  └─ p: 2000  [DIFFERENT — update]

STEP 4: Only update what changed in REAL DOM
─────────────────────────────────────────────
  document.querySelector('h1').textContent = 'Cart (3 items)';
  document.querySelector('p').textContent = 'Total: ₹2,000';

  The <div> was NOT touched — it didn't change.
  Only 2 DOM operations instead of rebuilding everything.
```

**Why this matters:** DOM operations are slow. Reading/writing the real DOM is 10-100x slower than working with plain JavaScript objects. Virtual DOM lets React work fast in JS land first, then do the minimum necessary DOM work.

---

# CHAPTER 3: React Fiber — The Engine Inside React

## First, What's The Problem Fiber Solves?

```
ANALOGY: Cooking a 10-course meal
─────────────────────────────────────────────────────────
WITHOUT Fiber:
  You start cooking Course 1, then 2, then 3...
  While cooking Course 7, your guest knocks on the door.
  You CANNOT answer the door until all 10 courses are done.
  Guest waits, gets frustrated, leaves.

WITH Fiber:
  You cook Course 1 for 5 minutes.
  Guest knocks → you open the door, say hello, come back.
  Continue Course 1 from where you stopped.
  Guest is happy. Meal gets done.

In React terms:
  "Guest knocking" = user clicking a button or typing
  "Cooking" = React rendering your components
```

```
WHAT ACTUALLY HAPPENED IN OLD REACT (before version 16):

User has a page with 1000 product cards.
User types in a search box.

React starts re-rendering:
  renderProductCard(1)
  renderProductCard(2)
  renderProductCard(3)
  ...
  renderProductCard(500)  ← browser is LOCKED here
  ...
  renderProductCard(1000)
  ← ONLY NOW can React process the keystroke

User sees: input box doesn't show the letter they typed
           for 80-150ms... then suddenly shows it
           Feels like the keyboard is lagging
```

## How Fiber Fixed It — Units of Work

```
FIBER CONCEPT: Break rendering into tiny "units of work"

One unit = rendering ONE component

  renderProductCard(1)  ← unit 1 (takes ~0.1ms)
         ↓
  "Browser, do you need to do anything?"
         ↓ NO
  renderProductCard(2)  ← unit 2 (takes ~0.1ms)
         ↓
  "Browser, do you need to do anything?"
         ↓ YES — user typed a letter!
  PAUSE rendering. Handle the keystroke. Resume from unit 2.

Result: keystroke handled in < 1ms. User never notices the pause.
```

```
WHAT A FIBER NODE LOOKS LIKE:

Every component becomes a "fiber" — a simple JavaScript object:

  ┌──────────────────────────────────────────────────────┐
  │  FIBER (for a <ProductCard title="Laptop" /> )        │
  │  ─────────────────────────────────────────────        │
  │  type       = ProductCard  (the component function)   │
  │  props      = { title: "Laptop", price: 45000 }       │
  │  stateNode  = the actual <div> in the browser         │
  │                                                        │
  │  child      ──────────────► fiber for first child     │
  │  sibling    ──────────────► fiber for next component  │
  │  return     ──────────────► fiber for parent          │
  └──────────────────────────────────────────────────────┘

The "return" pointer is confusingly named — it means "parent"
(the fiber to go back to after processing this one)
```

```
HOW FIBERS CONNECT — A REAL COMPONENT TREE:

Your code:
  <App>
    <Header>
      <Logo />
      <SearchBar />
    </Header>
    <ProductList>
      <ProductCard />
      <ProductCard />
    </ProductList>
  </App>

As a Fiber linked list:
  [App]
    │ child
    ▼
  [Header] ──sibling──► [ProductList]
    │ child                │ child
    ▼                      ▼
  [Logo] ──sibling──► [SearchBar]    [ProductCard] ──sibling──► [ProductCard]
    │                   │               │
   return             return           return
    │                   │               │
   [Header]           [Header]        [ProductList]

React walks this left-to-right, top-to-bottom.
At any point it can STOP and come back later.
A recursive function stack CAN'T do that — Fiber CAN.
```

## The Two Phases

```
PHASE 1: RENDER PHASE (the planning phase)
──────────────────────────────────────────
React walks through all the fibers.
For each one, it answers: "What changed?"

  ProductCard fiber: props.price was ₹40,000, now ₹45,000 → mark as UPDATE
  Header fiber: nothing changed → skip
  Logo fiber: nothing changed → skip

This phase CAN be interrupted.
React does it in small chunks between browser frames.
If it gets interrupted, it THROWS AWAY the work and starts over.
(That's why you shouldn't have side effects during render)

PHASE 2: COMMIT PHASE (the doing phase)
────────────────────────────────────────
React takes everything it planned in Phase 1
and applies it to the REAL DOM all at once.

  document.querySelector('.price').textContent = '₹45,000';
  ← just this one change, nothing else needed

This phase CANNOT be interrupted.
Why? Imagine React showed ₹45,000 in the price but still showed
the old "Add to Cart" button state — inconsistent UI.
Commit is atomic: all changes happen together or not at all.
```

---

# CHAPTER 4: useState and useEffect — The Deep Version

## useState — What's Actually Happening

```
COMMON MISUNDERSTANDING:
  const [count, setCount] = useState(0);
  setCount(5);
  console.log(count); // prints 0 ← WHY?!

BEGINNER THINKS: "setCount updates count immediately"
REALITY: setCount schedules a re-render with the new value
         count in the CURRENT render is still 0
         NEXT render, count will be 5
```

```
WHAT ACTUALLY HAPPENS WHEN YOU CALL setCount(5):

  setCount(5) called
       │
       ▼
  React adds this to a queue: "Counter component needs re-render with count=5"
       │
       ▼
  Current function execution CONTINUES (count is still 0)
       │
       ▼
  React processes its queue (when the call stack is free)
       │
       ▼
  React calls Counter() again (re-render)
       │
       ▼
  This time useState(0) returns [5, setCount]  ← the new value
       │
       ▼
  JSX renders with count = 5

ANALOGY: setCount is like putting a post-it note on React's desk.
React will read it and re-render, but not immediately.
The current render is already in progress — can't change it.
```

```
BATCHING — multiple setStates in one go:

  function handleClick() {
    setCount(1);     // post-it note 1
    setName("John"); // post-it note 2
    setAge(25);      // post-it note 3
  }
  // React does NOT re-render 3 times
  // React collects all 3 updates, then re-renders ONCE
  // This is called "batching" — React 18 batches even async updates

  WHY THIS MATTERS:
  Bad (before batching):
    3 setStates → 3 re-renders → 3 DOM updates → slow

  Good (with batching):
    3 setStates → 1 re-render → 1 DOM update → fast
```

## useEffect — The Full Mental Model

```
WHAT useEffect ACTUALLY IS:
"Run this code AFTER React has updated the DOM"

  useEffect(() => {
    // This runs AFTER the component renders and the browser has painted
    // Not during render — after it
    document.title = `You have ${count} notifications`;
  }, [count]);

WHY "AFTER"?
Because sometimes your effect needs the actual DOM to exist.
If you tried to do document.title during render, React might
be in the middle of working — not safe.
```

```
THE DEPENDENCY ARRAY — what it really means:

  // No dependency array — runs after EVERY render
  useEffect(() => { ... });

  // Empty array — runs ONCE after first render only
  useEffect(() => { ... }, []);

  // With [count] — runs after first render, then again
  useEffect(() => { ... }, [count]); // whenever count changes

  HOW REACT DECIDES WHETHER TO RE-RUN:
  After each render, React checks:
    "Did any value in the dependency array change since last time?"
    YES → run the effect
    NO  → skip it

  // Example:
  // Render 1: count = 0 → [count] = [0]
  // Render 2: count = 0 → [count] = [0] → same! Skip effect.
  // Render 3: count = 1 → [count] = [1] → different! Run effect.
```

```
CLEANUP FUNCTION — the return value:

  useEffect(() => {
    // 1. Set up
    const timer = setInterval(() => {
      setCount(prev => prev + 1);
    }, 1000);

    // 2. Return cleanup
    return () => {
      clearInterval(timer); // ← this runs BEFORE the effect runs again
    };                      //   and when the component unmounts
  }, []);

  WHAT HAPPENS:
  ─────────────────────────────────────────────────────
  Component mounts
       │
       ▼
  Effect runs → timer starts ticking every 1 second
       │
       ▼  (later, component is removed from page)
  Cleanup runs → clearInterval(timer) → timer stops
       │
       ▼
  Component unmounts

  WITHOUT CLEANUP:
  Timer keeps running even after component is gone.
  Timer tries to update state of a component that doesn't exist.
  Memory leak. Console warning: "Can't perform state update on unmounted component"
```

---

# CHAPTER 5: The Stale Closure Problem — Explained Simply

## What Is A Closure?

```
CLOSURE BASICS (JavaScript concept):

  function makeCounter() {
    let count = 0;  // ← this variable is "closed over"

    return function() {
      count = count + 1;  // can access count even though makeCounter() is done
      return count;
    };
  }

  const counter = makeCounter();
  counter(); // 1
  counter(); // 2
  counter(); // 3

  The inner function "remembers" count from when makeCounter() ran.
  This is a closure — a function that captures variables from its outer scope.
```

```
HOW THIS CAUSES BUGS IN REACT:

  function LiveUserCount() {
    const [onlineUsers, setOnlineUsers] = useState(1);

    useEffect(() => {
      const timer = setInterval(() => {
        // This function is a CLOSURE
        // It captured onlineUsers = 1 when the effect first ran
        document.title = `${onlineUsers} users online`;
        //                  ↑
        //                  ALWAYS 1, even when onlineUsers = 100
      }, 1000);

      return () => clearInterval(timer);
    }, []); // ← empty array means: run once, never re-run

    // Simulating users joining
    useEffect(() => {
      setTimeout(() => setOnlineUsers(100), 5000);
    }, []);

    return <div>{onlineUsers} users online</div>; // shows 100 correctly
    // But document.title shows "1 users online" forever!
  }
```

```
THE PROBLEM VISUALIZED:

  Component renders for the first time:
    onlineUsers = 1
    Effect runs → creates timer
    Timer's closure captures: onlineUsers = 1

  ─── 5 seconds later ───

  setOnlineUsers(100) called
  Component re-renders: onlineUsers = 100
  Effect does NOT re-run (empty dependency array)
  Timer is STILL the one created at mount
  Timer still has onlineUsers = 1 in its closure
  Timer sets title to "1 users online" ← STALE VALUE

  ┌─────────────────────────────────────────────────────┐
  │  STALE CLOSURE = a function that remembers an OLD   │
  │  value of a variable, even though the variable has  │
  │  since changed                                      │
  └─────────────────────────────────────────────────────┘
```

## Three Ways To Fix It

```
FIX 1: Functional update — don't READ state, get it from React
────────────────────────────────────────────────────────────────
  // BROKEN: reads count from closure (stale)
  setCount(count + 1);

  // FIXED: React passes you the CURRENT value
  setCount(prev => prev + 1);
  //        ↑
  //        React gives you the real current value, not the closure value
  //        Works correctly even in timers, even with empty deps

  ANALOGY:
  Stale version: you ask your friend "what's the score?" and they
    say "3-1" based on what they saw 5 minutes ago.
  Functional update: you call the official scorekeeper who always
    has the live score.

FIX 2: useRef — a mutable box that React doesn't re-render for
────────────────────────────────────────────────────────────────
  const onlineUsersRef = useRef(1);

  // Keep ref in sync with state
  useEffect(() => {
    onlineUsersRef.current = onlineUsers;
  }); // no deps — runs after every render

  useEffect(() => {
    const timer = setInterval(() => {
      // Read from ref, not closure — ref is always fresh
      document.title = `${onlineUsersRef.current} users online`;
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  ANALOGY:
  ref.current is like a whiteboard on your wall.
  Anyone can update it, anyone can read it.
  It doesn't care about JavaScript closures.
  Timer walks to the whiteboard and reads the latest number.

FIX 3: Add to dependency array (sometimes)
────────────────────────────────────────────
  useEffect(() => {
    const timer = setInterval(() => {
      document.title = `${onlineUsers} users online`; // always fresh
    }, 1000);
    return () => clearInterval(timer);
  }, [onlineUsers]); // re-create timer when onlineUsers changes

  TRADE-OFF: Timer gets destroyed and re-created every time
             onlineUsers changes. For a timer, that's usually fine.
             For a WebSocket connection, that would be too expensive.
```

---

# CHAPTER 6: Keys in Lists — Why React Needs Them

## The Problem Keys Solve

```
IMAGINE: React sees this list re-render
─────────────────────────────────────────────────────────────
BEFORE:                    AFTER (you deleted "Sam"):
  <li>John</li>              <li>John</li>
  <li>Sam</li>               <li>Priya</li>
  <li>Priya</li>

WITHOUT KEYS, React compares by POSITION:
  Position 1: "John" vs "John" → same, no update
  Position 2: "Sam"  vs "Priya" → different! UPDATE this DOM node
  Position 3: "Priya" exists in old, not in new → DELETE

React updated the wrong things!
It modified position 2 instead of deleting it.
It deleted position 3 instead of keeping it.

Result: 2 DOM operations (update + delete)
        But the intent was just 1 operation (delete "Sam")
```

```
WITH KEYS, React compares by IDENTITY:
  Key "john-1": present before, present after → no update
  Key "sam-2":  present before, NOT after     → DELETE this specific one
  Key "priya-3": present before, present after → no update

React deletes the CORRECT item in 1 DOM operation.
No unnecessary updates to John or Priya.
```

```
THE RANDOM KEY DISASTER:

  // NEVER DO THIS:
  items.map((item) => <Item key={Math.random()} data={item} />)

  WHAT HAPPENS:
  Every render generates NEW random keys for everything.

  Render 1 keys: [0.723, 0.451, 0.892]
  Render 2 keys: [0.115, 0.667, 0.334] ← ALL DIFFERENT

  React sees: ALL items have new keys → ALL are "new" items
  React: destroys all 3 old items, creates 3 fresh items
  10x more DOM work than necessary.
  Also destroys all local state (input values, focus, scroll position)

  BEST PRACTICE:
  Use a stable, unique ID from your data:
    items.map(item => <Item key={item.id} data={item} />)

  ACCEPTABLE (only when items never reorder):
    items.map((item, index) => <Item key={index} data={item} />)

  INTENTIONALLY USING KEY TO RESET STATE:
    <UserProfile key={selectedUserId} />
    // When user switches to a different profile,
    // key changes → component fully unmounts and remounts
    // All local state cleared — intentional fresh start
```

---

# CHAPTER 7: React.memo, useMemo, useCallback — When and Why

## The Re-render Problem First

```
PROBLEM: Every parent re-render re-renders ALL children

  function Dashboard() {
    const [count, setCount] = useState(0);

    return (
      <div>
        <button onClick={() => setCount(c => c + 1)}>Click me</button>
        <ExpensiveChart data={bigData} /> {/* re-renders on every click! */}
        <UserList users={userList} />     {/* re-renders on every click! */}
      </div>
    );
  }

  Every time you click the button:
  1. Dashboard re-renders
  2. ExpensiveChart re-renders (takes 50ms to render)
  3. UserList re-renders

  But ExpensiveChart and UserList don't NEED to re-render —
  their data (bigData, userList) didn't change!
  Wasted 50ms on every single click.
```

## React.memo — Skip Re-render If Props Didn't Change

```
WHAT React.memo DOES:
"Only re-render this component if its props actually changed"

  // Before memo:
  function ExpensiveChart({ data }) {
    // expensive calculation every render...
    return <div>...</div>;
  }

  // After memo:
  const ExpensiveChart = React.memo(function({ data }) {
    // only runs when `data` actually changes
    return <div>...</div>;
  });

  HOW IT CHECKS:
  React compares props using Object.is() (like ===)
    Old props: { data: bigData }
    New props: { data: bigData }
    bigData === bigData? YES (same reference) → SKIP RE-RENDER ✅

  Dashboard clicks → count changes → Dashboard re-renders
  → ExpensiveChart: "is data still the same reference?" YES → skip ✅
  → UserList: "is users still the same reference?" YES → skip ✅

  Button feels instant now.
```

## useCallback — Keep Function References Stable

```
THE PROBLEM memo doesn't solve alone:

  function Dashboard() {
    const [count, setCount] = useState(0);

    const handleChartClick = () => {  // ← NEW FUNCTION every render
      console.log('chart clicked');
    };

    return (
      <ExpensiveMemoChart
        data={bigData}
        onClick={handleChartClick}  // ← new reference every render!
      />
    );
  }

  Even with React.memo on ExpensiveMemoChart:
  Dashboard re-renders → handleChartClick is a NEW function object
  Old onClick: function@address#1234
  New onClick: function@address#5678  ← different reference!
  React.memo: "props changed (onClick)" → re-renders anyway!
  memo is USELESS here because of the unstable function reference.
```

```
FIX WITH useCallback:

  const handleChartClick = useCallback(() => {
    console.log('chart clicked');
  }, []); // ← no dependencies = same function reference forever

  Now:
  Dashboard re-renders → handleChartClick is the SAME function object
  React.memo: "props same" → SKIP re-render ✅

  useCallback(fn, deps) means:
  "Give me back the SAME function reference unless deps changed"
```

```
SUMMARY — WHEN EACH IS USEFUL:

  React.memo   → wrap a COMPONENT to skip re-renders
  useCallback  → wrap a FUNCTION so it has stable reference
                 (useful when passed to memo components or effect deps)
  useMemo      → wrap a CALCULATION to avoid recomputing it
                 (useful for expensive derived data)

  ┌───────────────┬──────────────────────────────────────┐
  │               │ Without useMemo                       │
  │               │   const sorted = items.sort(...)      │
  │ useMemo       │   runs on EVERY render                │
  │               │ With useMemo                          │
  │               │   const sorted = useMemo(             │
  │               │     () => items.sort(...), [items])   │
  │               │   runs only when items changes        │
  └───────────────┴──────────────────────────────────────┘

  IMPORTANT: Don't use these everywhere!
  They add complexity and their own small overhead.
  Only use when you've MEASURED a performance problem.
  Premature optimization makes code harder to read for no benefit.
```

---

# CHAPTER 8: Context API — Global State Without Prop Drilling

## What Is Prop Drilling?

```
PROBLEM: Passing data through components that don't need it

  App  ←── has currentUser data
   │
   └─ Navbar  ← needs currentUser
        │
        └─ NavLinks  ← doesn't need it, but must pass it down
               │
               └─ UserAvatar  ← NEEDS currentUser

  Without Context, you must pass currentUser through EVERY level:
  <App currentUser={user}>
    <Navbar currentUser={user}>
      <NavLinks currentUser={user}>
        <UserAvatar currentUser={user} />   ← finally used here
      </NavLinks>
    </Navbar>
  </App>

  NavLinks has to accept and pass along a prop it NEVER USES.
  This is called "prop drilling" — like drilling through walls
  to run a wire that only the end destination needs.
```

## How Context Fixes It

```
CONTEXT = a global variable that React manages safely

  STEP 1: CREATE the context (define what data will be shared)
  ─────────────────────────────────────────────────────────────
  const UserContext = React.createContext(null);
  // null is the default value (used if no Provider wraps the component)

  STEP 2: PROVIDE the context (wrap your app with the data)
  ─────────────────────────────────────────────────────────────
  function App() {
    const [user, setUser] = useState({ name: 'Priya', role: 'admin' });

    return (
      <UserContext.Provider value={{ user, setUser }}>
        {/* Everything inside can access user */}
        <Navbar />
      </UserContext.Provider>
    );
  }

  STEP 3: CONSUME the context (use it anywhere in the tree)
  ─────────────────────────────────────────────────────────────
  function UserAvatar() {
    const { user } = useContext(UserContext);
    // Got user directly — skipped Navbar and NavLinks entirely!
    return <img src={user.avatar} alt={user.name} />;
  }

  VISUAL:
  App (provides user)
   └─ Navbar         ← doesn't need to know about user
        └─ NavLinks  ← doesn't need to know about user
             └─ UserAvatar ← gets user directly from Context ✅
```

```
CONTEXT RE-RENDER TRAP (important to know!):

  When the value in a Context.Provider changes,
  ALL components that useContext() ANYWHERE IN THE TREE re-render.

  // Problem:
  const { user, notifications } = useContext(AppContext);

  If notifications updates every 5 seconds:
  → UserAvatar re-renders every 5 seconds
  → Even though UserAvatar only cares about user (which hasn't changed)

  // FIX: Separate contexts for data that changes at different rates
  const UserContext = createContext(null);       // rare changes
  const NotifContext = createContext(null);      // frequent changes

  UserAvatar uses useContext(UserContext) only
  → not affected by notification updates ✅
```

---

# CHAPTER 9: Custom Hooks — Reusing Logic

## What Custom Hooks Are For

```
PROBLEM: Same logic repeated in 5 components

  // In ProductPage.jsx:
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  useEffect(() => {
    fetch('/api/products').then(r => r.json()).then(d => {
      setData(d); setLoading(false);
    }).catch(e => {
      setError(e); setLoading(false);
    });
  }, []);

  // In UserPage.jsx: SAME 10 LINES (different URL)
  // In OrdersPage.jsx: SAME 10 LINES (different URL)
  // ...repeated 5 times
```

```
SOLUTION: Extract into a custom hook

  // useFetch.js
  function useFetch(url) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
      setLoading(true);
      fetch(url)
        .then(r => r.json())
        .then(d => { setData(d); setLoading(false); })
        .catch(e => { setError(e); setLoading(false); });
    }, [url]);

    return { data, loading, error };
  }

  // Now in every component — 1 line:
  const { data: products, loading, error } = useFetch('/api/products');
  const { data: users,    loading, error } = useFetch('/api/users');
  const { data: orders,   loading, error } = useFetch('/api/orders');

  RULES FOR CUSTOM HOOKS:
  1. Name MUST start with "use" (React enforces this)
  2. Can call other hooks inside (useState, useEffect, etc.)
  3. Each component calling useFetch gets its OWN state
     (hooks don't share state — they share LOGIC)
```

---

# CHAPTER 10: Reconciliation — How React Decides What To Update

## The Diffing Algorithm

```
REACT'S DIFFING RULES (simplified):

RULE 1: Different element types = destroy and recreate
──────────────────────────────────────────────────────
  Old: <div><Counter /></div>
  New: <span><Counter /></span>
  ← <div> changed to <span>
  React destroys everything inside the div (including Counter's state)
  Creates fresh span + fresh Counter
  Counter starts from scratch, loses its count value

  WHY: React assumes if you changed the container type,
  the children are probably completely different too.

RULE 2: Same element type = update the attributes
──────────────────────────────────────────────────
  Old: <div className="old" id="main">...</div>
  New: <div className="new" id="main">...</div>
  ← same <div>, just different className
  React only updates the className attribute
  Everything else (id, children) stays the same
  Very fast — minimal DOM work

RULE 3: Keys help identify which list items are the same
──────────────────────────────────────────────────────────
  Old list:                New list (item removed):
  <li key="a">Apple</li>   <li key="a">Apple</li>
  <li key="b">Banana</li>  <li key="c">Cherry</li>
  <li key="c">Cherry</li>

  React sees: "b" is gone → delete Banana's DOM node
              "a" and "c" are same → no update
  
  Without keys, React compares by position:
    Position 1: Apple = Apple → no update
    Position 2: Banana ≠ Cherry → update text to Cherry
    Position 3: Cherry exists old, gone in new → delete
  
  With keys: 1 operation (delete)
  Without keys: 2 operations (update + delete)
  At 1000 items: the difference is massive
```

---

# CHAPTER 11: Error Boundaries — Graceful Failures

## What Happens Without Error Boundaries

```
SCENARIO: Your app is a news feed with 100 articles.
Article #47 has a null value for the author name.
Your ArticleCard component does: author.name
This throws: "Cannot read properties of null"

WITHOUT Error Boundary:
  React has no way to catch the error
  The ENTIRE app crashes
  User sees a blank white page
  All 100 articles disappear
  User has to refresh and lose their place

WITH Error Boundary around each ArticleCard:
  Article #47 crashes
  Error Boundary catches it
  Shows a small "This article couldn't load" placeholder
  All other 99 articles still show fine ✅
  User barely notices
```

```
HOW AN ERROR BOUNDARY WORKS:

  class ErrorBoundary extends React.Component {
    constructor(props) {
      super(props);
      this.state = { hasError: false };
    }

    // React calls this when a child throws during render
    static getDerivedStateFromError(error) {
      return { hasError: true }; // tell the component to show fallback
    }

    // React calls this for logging (after showing fallback)
    componentDidCatch(error, errorInfo) {
      // Send to your error tracking (Sentry, Datadog, etc.)
      logErrorToService(error, errorInfo.componentStack);
    }

    render() {
      if (this.state.hasError) {
        return this.props.fallback; // show the fallback UI
      }
      return this.props.children; // show children normally
    }
  }

  // Usage:
  <ErrorBoundary fallback={<p>Article failed to load</p>}>
    <ArticleCard article={article} />
  </ErrorBoundary>

  // Why class component? Because getDerivedStateFromError and
  // componentDidCatch only exist on class components.
  // There's no hook equivalent (yet). React 19 will add use-error-boundary.
```

---

# CHAPTER 12: useRef — The Mutable Box

## When useState is Too Much

```
USE CASE 1: Accessing a DOM element directly

  function SearchBar() {
    const inputRef = useRef(null);

    function handleButtonClick() {
      inputRef.current.focus(); // directly focus the input element
    }

    return (
      <>
        <input ref={inputRef} type="text" />
        <button onClick={handleButtonClick}>Focus Input</button>
      </>
    );
  }

  WHY NOT useState?
  useState(null) + document.querySelector('.search-input').focus()
  → querySelector is brittle, doesn't work with multiple instances
  → ref is component-scoped, always points to the right element

  WHAT ref.current IS:
  inputRef = { current: <input> }
  inputRef.current = the actual HTML input DOM node
  You can call any DOM method on it: .focus(), .blur(), .value, etc.
```

```
USE CASE 2: Storing a value without triggering re-render

  SCENARIO: Count how many times a button has been clicked
  but DON'T re-render the component when count changes

  // With useState — re-renders on every click:
  const [clickCount, setClickCount] = useState(0);
  // Every increment → re-render → expensive if component is complex

  // With useRef — NO re-render:
  const clickCountRef = useRef(0);
  function handleClick() {
    clickCountRef.current += 1; // update the value
    // component does NOT re-render
    // current value always accessible via clickCountRef.current
  }

  RULE OF THUMB:
  Use useState when you want the UI to update when the value changes
  Use useRef  when you need to remember a value but UI doesn't change
```

---

# CHAPTER 13: React 18 — Concurrent Features Simply Explained

## startTransition — Tell React "This Can Wait"

```
ANALOGY: Hospital Triage
──────────────────────────────────────────────────────────
Normal hospital (no triage):
  Patient 1 arrives: mild cold → starts treatment (1 hour)
  Patient 2 arrives: heart attack → WAITS behind the cold patient
  ← Patient 2 might die because hospital has no priority system

Hospital with triage:
  Patient 1 arrives: mild cold → marked LOW priority
  Patient 2 arrives: heart attack → marked HIGH priority → treated FIRST
  Patient 1 waits a bit longer, but that's okay — it's just a cold

In React:
  Input update (user typing)    = heart attack → HIGH priority
  Filtering 1000 items          = mild cold    → LOW priority
  startTransition = the triage tag
```

```
WITHOUT startTransition — typing feels laggy:
────────────────────────────────────────────
  function Search() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState(allData);

    function handleChange(e) {
      setQuery(e.target.value);              // input updates
      setResults(filter(allData, e.target.value)); // list filters
      // BOTH happen together, synchronously
      // filter(allData, ...) takes 40ms
      // React can't show the updated input until BOTH are done
      // Input lags by 40ms on every keystroke
    }

    return (
      <>
        <input value={query} onChange={handleChange} />
        <ResultList items={results} />
      </>
    );
  }

WITH startTransition — typing is instant:
────────────────────────────────────────────
  function Search() {
    const [query, setQuery] = useState('');
    const [results, setResults] = useState(allData);

    function handleChange(e) {
      setQuery(e.target.value);  // HIGH priority — shows immediately

      startTransition(() => {
        setResults(filter(allData, e.target.value)); // LOW priority — can wait
      });
    }
    // Input always shows what you typed instantly ✅
    // Results update when React has time ✅
  }
```

---

# QUICK REFERENCE CARD

```
╔═══════════════════════════════════════════════════════════════════╗
║  CONCEPT           WHAT IT IS          WHEN TO USE                ║
╠═══════════════════════════════════════════════════════════════════╣
║  Virtual DOM       JS copy of the DOM  Always (automatic)         ║
║  Fiber             Work unit system    Always (automatic)         ║
║  useState          Local component     Any data the UI shows      ║
║                    state               that can change            ║
║  useEffect         Side effects        API calls, subscriptions,  ║
║                    after render        document.title updates      ║
║  useRef            Mutable box, no     DOM access, timers,        ║
║                    re-render           counting without UI update  ║
║  useMemo           Cache calculation   Expensive computations      ║
║                    result              on large datasets           ║
║  useCallback       Cache function      Stable fn refs for memo    ║
║                    reference           children or effect deps     ║
║  React.memo        Skip child          Expensive child that       ║
║                    re-renders          re-renders unnecessarily    ║
║  Context           Share data without  Theme, auth user, locale   ║
║                    prop drilling       across many components      ║
║  Custom Hook       Reusable stateful   Same logic in 3+ places    ║
║                    logic               (data fetching, forms)     ║
║  Error Boundary    Catch render errors Route level + card level   ║
║  startTransition   Mark update as      Search filters, sorting,   ║
║                    non-urgent          navigation                  ║
╚═══════════════════════════════════════════════════════════════════╝

KEY RULES TO MEMORIZE:
1. setCount doesn't change count immediately — schedules re-render
2. useEffect deps array: [] = once, [x] = when x changes, none = every render
3. Keys identify list items — never use Math.random() as key
4. useCallback only helps if passed to React.memo child or effect dep
5. Stale closure fix: setX(prev => prev + 1), not setX(x + 1) in timers
6. Error boundaries must be CLASS components (no hook equivalent yet)
7. Context re-renders ALL consumers — split by update frequency
```
