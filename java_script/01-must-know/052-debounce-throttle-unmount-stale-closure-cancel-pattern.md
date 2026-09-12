# Unmount Stale Closure and the Cancel Pattern
> **Topic:** Debounce & Throttle | **Level:** Senior Trap | **Frequency:** High

## The Setup
You have implemented debounce correctly. The search component works perfectly in isolation. But in the app, navigating away from the search page sometimes triggers a console warning — or in older codebases, an error — about setting state on an unmounted component. The interviewer asks why.

## The Question
What happens to a pending debounced call when the React component that created it unmounts? What is the correct fix? Walk through the exact sequence of events that causes the bug.

## Diagram

```
t=0ms   User types "bir" → debounce schedules call at t=300ms
t=150ms User navigates away → React unmounts SearchBox component
t=300ms setTimeout callback fires:
          → fn.apply(this, args) runs
          → calls setResults(data) — but component is GONE
          → React 17: "Warning: Can't perform a React state update on unmounted component"
          → React 18: silent, but the fetch() still goes out, CPU/network wasted,
                      stale closure holds reference to old state setter

The setTimeout is alive in the JS event loop.
React unmounting a component does NOT cancel pending timers.
```

## Model Answer (15 YOE)

**The root cause:**

The debounced function closes over `setResults` (or any state setter). When the component unmounts, React discards the component's state slots and fiber node. But the `setTimeout` callback — already queued in the JS event loop — has no knowledge of this. When the timer fires, it calls `setResults` on a dead component.

In React 17 this produced a warning. In React 18 the warning was removed (because the leak rarely caused real bugs), but the problem remains: the pending fetch still goes out, `setResults` still runs, and the stale closure holds references that prevent garbage collection until the timer resolves.

**The fix — `.cancel()` in useEffect cleanup:**

```ts
function debounce<T extends (...args: any[]) => void>(fn: T, delay: number) {
  let timerId: ReturnType<typeof setTimeout>;

  const debounced = function (this: unknown, ...args: Parameters<T>) {
    clearTimeout(timerId);
    timerId = setTimeout(() => fn.apply(this, args), delay);
  };

  debounced.cancel = () => clearTimeout(timerId); // ← this is the key
  return debounced;
}

function SearchBox() {
  const debouncedSearch = useRef(
    debounce(async (query: string) => {
      const data = await fetch(`/api/search?q=${query}`).then(r => r.json());
      setResults(data);
    }, 300)
  ).current;

  useEffect(() => {
    return () => debouncedSearch.cancel(); // fires when component unmounts
  }, [debouncedSearch]);
  // ...
}
```

`useEffect` cleanup runs synchronously when the component unmounts. `cancel()` calls `clearTimeout`, removing the pending callback from the event loop before it has a chance to fire.

**Why `useRef` alone is not enough:**

`useRef` prevents the debounced function from being re-created on every render — but it does nothing about cleanup on unmount. The two concerns are orthogonal: stability across renders (use `useRef`) and cleanup on unmount (use `useEffect` return).

## Why It's a Trap

Most candidates describe the debounce timer correctly but answer the unmount question with "React cleans it up" or "the component is unmounted so nothing happens." Neither is true. JavaScript timers are owned by the browser's event loop, not by React's component lifecycle. React has no mechanism to cancel timers it did not create.

A second group of candidates adds `useRef` and considers the problem solved. They are fixing the re-render stability bug but not the unmount bug. The interviewer who designed this question knows the difference.

## What NOT to Say

- "React will cancel the timer when the component unmounts." — React does not cancel timers.
- "In React 18 this is not an issue anymore." — The warning was removed; the underlying problem was not.
- "I would just use an `AbortController` on the fetch." — Correct for cancelling in-flight network requests, but does not cancel the `setTimeout` itself. You need both: `cancel()` to clear the timer and `AbortController` to abort the fetch if the timer fired and the request is in flight.

## Follow-up

**Q:** What if the debounced function is async and the fetch is in flight when the component unmounts?
**A:** You need two layers of cancellation: `cancel()` clears the pending `setTimeout` (prevents the fetch from starting), and an `AbortController` with `signal` passed to `fetch()` cancels the in-flight request if unmount happens after the timer fires. The `useEffect` cleanup should call both `debouncedSearch.cancel()` and `abortController.abort()`.
