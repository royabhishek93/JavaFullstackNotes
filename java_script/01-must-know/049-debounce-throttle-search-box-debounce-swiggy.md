# Search Box with Debounce — Swiggy Scenario
> **Topic:** Debounce & Throttle | **Level:** Intermediate | **Frequency:** High

## The Setup
You are interviewing at Swiggy (or any food-delivery / e-commerce company). The interviewer describes a real production pain point: the search bar fires an API call on every keystroke. A user typing "biryani bangalore" generates 18 network requests. Responses arrive out of order, causing wrong results to flash on screen. They ask you to fix it.

## The Question
A search box fires an API call on every `input` event. Fix it with debounce. Write the complete React component including:
- The debounce utility
- Correct React integration so the debounced function is stable across renders
- Cleanup to prevent state updates on unmounted components

## Diagram

```
WITHOUT DEBOUNCE (18 chars = 18 API calls):
b  bi  bir  birya  biryan  biryani  biryani   biryani b ...
↓   ↓    ↓     ↓       ↓        ↓         ↓          ↓
API API  API   API     API      API       API        API
                                      (responses arrive out of order → wrong UI)

WITH DEBOUNCE (300ms wait after last keystroke):
b  bi  bir  birya  biryan  biryani  biryani   biryani bangalore
                                                     [300ms silence]
                                                              ↓
                                                             API  ← 1 call, correct query
```

## Model Answer (15 YOE)

```ts
// hooks/useDebounce.ts
function debounce<T extends (...args: any[]) => void>(fn: T, delay: number) {
  let timerId: ReturnType<typeof setTimeout>;

  const debounced = function (this: unknown, ...args: Parameters<T>) {
    clearTimeout(timerId);
    timerId = setTimeout(() => fn.apply(this, args), delay);
  };

  debounced.cancel = () => clearTimeout(timerId);
  return debounced;
}

// SearchBox.tsx
function SearchBox() {
  const [results, setResults] = useState<string[]>([]);

  // useRef: stable reference across renders, debounced fn not recreated on every render
  const debouncedSearch = useRef(
    debounce(async (query: string) => {
      if (!query.trim()) return;
      const data = await fetch(`/api/search?q=${encodeURIComponent(query)}`).then(r => r.json());
      setResults(data);
    }, 300)
  ).current;

  // Cancel pending call on unmount — prevents setState on unmounted component
  useEffect(() => () => debouncedSearch.cancel(), [debouncedSearch]);

  return (
    <input
      type="text"
      onChange={e => debouncedSearch(e.target.value)}
      placeholder="Search for restaurants..."
    />
  );
}
```

**Why `useRef` and not `useMemo` or inline creation:**

`useRef` creates the debounced function once and holds it for the component's lifetime. `useMemo` with an empty dependency array also works but is semantically "memoize for performance" rather than "persist an instance." The real danger is creating the debounced function inside the render body without any memoization — every render creates a new closure with a fresh `timerId = undefined`, silently breaking debounce.

**Why the `useEffect` cleanup matters:**

When the component unmounts, the pending `setTimeout` is still alive in the JS event loop. When it fires, it calls `setResults` on a dead component. In React 18 the console warning was removed, but the stale closure still runs — wasting a network call and potentially setting state on a component that has been replaced. `.cancel()` prevents this entirely.

## Follow-up

**Q:** Why not just use `useCallback` with debounce?
**A:** `useCallback(debounce(fn, 300), [])` looks correct but has a subtle bug: `debounce(fn, 300)` is evaluated as the argument to `useCallback` on every render, creating a new debounced function each time. `useCallback` then memoizes that *new* function, discarding the old one. The closure is reset on every render. The fix is `useRef` — it creates the function once and never re-evaluates.

**Q:** How would you handle showing a loading spinner while the debounced call is in flight?
**A:** Set a `loading` state to `true` inside the debounced function before the `await`, and `false` in a `finally` block. Because the debounced call is always the most recent one (earlier calls were cancelled), there is never a race condition between loading states.
