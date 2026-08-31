# What is Concurrent Mode? How does startTransition work in practice?

> **Interview priority:** MUST KNOW

## Question

What is Concurrent Mode? How does startTransition work in practice?

## Beginner Lens

Before memorizing the interview answer, follow the scenario and notice three things: the problem React is solving, the state or browser work that changes, and the rule that keeps the UI correct. Read the code blocks slowly and predict the next result before reading the explanation.

## Detailed Explanation

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
