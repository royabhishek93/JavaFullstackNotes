# Debounce Inside the Render Body
> **Topic:** Debounce & Throttle | **Level:** Senior Trap | **Frequency:** High

## The Setup
A candidate passes a coding screen with a working debounce implementation. In the React integration round they write this:

```js
function SearchBox() {
  const debouncedSearch = debounce(searchAPI, 300); // looks fine at a glance
  return <input onChange={e => debouncedSearch(e.target.value)} />;
}
```

The interviewer asks: "Does this actually debounce?" The candidate insists it does. You need to explain why it does not.

## The Question
Why does creating the debounced function inside the React render body break debounce? What exactly happens, and what are the two correct fixes?

## Diagram

```
Render 1:  debounce(searchAPI, 300) → fn_A  (timerId_A = undefined)
  User types "b" → fn_A called → timerId_A = setTimeout(…, 300)
  "b" triggers setState → React re-renders

Render 2:  debounce(searchAPI, 300) → fn_B  (timerId_B = undefined)  ← NEW CLOSURE
  onChange now points to fn_B
  fn_A is abandoned — timerId_A still pending in event loop but no one calls fn_A again

  User types "i" → fn_B called → timerId_B = setTimeout(…, 300)
  "i" triggers setState → React re-renders

Render 3:  debounce(searchAPI, 300) → fn_C  (timerId_C = undefined)  ← ANOTHER NEW CLOSURE
  ...

Result: A new debounce wrapper with a fresh timer is created on every render.
        Debounce NEVER fires — the timer is always reset by re-render before it expires.
        Also leaks: abandoned timers in the event loop for every keystroke.
```

## Model Answer (15 YOE)

**Why the render body is wrong:**

JavaScript closures are created fresh each time the function they are defined in executes. Every React render is a function call. `debounce(searchAPI, 300)` inside the render body creates a new closure with its own `let timerId = undefined` each time React re-renders.

The component re-renders on every keystroke (because `onChange` triggers state updates). So each keystroke:
1. Fires the current debounced function, scheduling a timer
2. Triggers a re-render
3. Creates a brand-new debounced function with a fresh `timerId = undefined`
4. Renders `<input>` with the new function as the `onChange` handler
5. The old pending timer is now orphaned — it will fire eventually, calling `searchAPI` with a stale argument

The net effect: debounce never fires its deferred action from user input (it is always replaced before it can), but the orphaned timers eventually fire with stale values.

**Fix 1 — `useRef` (preferred):**

```ts
function SearchBox() {
  const debouncedSearch = useRef(debounce(searchAPI, 300)).current;
  // useRef creates the value once on first render and returns the same ref on every render
  // .current gives the stable reference

  useEffect(() => () => debouncedSearch.cancel(), [debouncedSearch]);

  return <input onChange={e => debouncedSearch(e.target.value)} />;
}
```

**Fix 2 — `useMemo` with empty deps:**

```ts
function SearchBox() {
  const debouncedSearch = useMemo(() => debounce(searchAPI, 300), []);
  // [] means "compute once, never recompute"

  useEffect(() => () => debouncedSearch.cancel(), [debouncedSearch]);

  return <input onChange={e => debouncedSearch(e.target.value)} />;
}
```

`useRef` is semantically clearer for "I need a single stable instance." `useMemo` with empty deps also works but React's docs note that memoization is a performance hint, not a guarantee — in future concurrent mode React may re-evaluate memos. `useRef` is the guaranteed stable slot.

**What does NOT work:**

```ts
// BROKEN: debounce() called fresh on every render; useCallback memoizes that fresh fn
const debouncedSearch = useCallback(debounce(searchAPI, 300), []);

// BROKEN: same problem — the argument is evaluated before useMemo sees it
const debouncedSearch = useMemo(debounce(searchAPI, 300), []);
//                              ↑ called here, not inside the factory function
```

## Why It's a Trap

This bug is entirely invisible in tests that mock timers without simulating re-renders, and it does not appear in simple Storybook previews. It only manifests in real use: the search bar simply never fires API calls, which might look like a network issue or a race condition to someone debugging without knowing to check the closure identity.

The subtlety is that `debounce` looks like a pure utility function — you expect it to "just work." The React render model breaks that assumption because closures are tied to the function execution that created them.

## What NOT to Say

- "I would use `useCallback` around the debounce call." — `useCallback` receives the already-evaluated result of `debounce(fn, 300)`, not a factory that re-uses the same instance.
- "It works fine, I've used this pattern." — It appears to work in environments with no re-renders or with very slow typing. Under real conditions with state updates, it silently fails.
- "The debounce timer resets on re-render, which is correct behaviour." — Resets caused by re-renders are not the developer's intent; they are a side-effect of incorrect placement.

## Follow-up

**Q:** Are there other hooks that have this "create inside render body" pitfall?
**A:** Yes — `throttle`, any function that holds internal state (cursor objects, class instances, WebSocket clients, timers). The rule is: if a utility function has internal mutable state (`timerId`, `lastCall`, `socket`), it must live outside the render body — in `useRef`, `useMemo([])`, or a module-level variable. Stateless utilities (pure functions like `formatDate`) are safe to call inside the render body.
