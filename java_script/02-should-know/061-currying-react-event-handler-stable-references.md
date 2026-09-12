# React Event Handler Pattern — Stable References with Currying
> **Topic:** Currying | **Level:** Intermediate | **Frequency:** Medium

## The Setup
You are a senior React engineer at Zomato optimizing a restaurant listing page. Performance profiling shows that a `RestaurantCard` component re-renders on every parent render even though it is wrapped in `React.memo`. Investigation reveals that an inline arrow function on a `handleFavorite` click prop creates a new function reference every render, busting the memo comparison.

## The Question
How does currying solve the stable function reference problem in React, and what are the nuances of this pattern in production?

## Diagram
```
  WITHOUT CURRYING — new fn every render
  ┌────────────────────────────────────────────────────────┐
  │  Parent render()                                       │
  │    <RestaurantCard                                     │
  │      onFavorite={() => handleFavorite(rest.id)}  ◀──  │
  │    />                   new arrow fn on every render   │
  │                         React.memo sees !== → re-render│
  └────────────────────────────────────────────────────────┘

  WITH CURRYING — stable reference returned from useCallback
  ┌────────────────────────────────────────────────────────┐
  │  const handleFavorite = useCallback(                   │
  │    (id) => (event) => {                                │
  │      event.preventDefault();                          │
  │      dispatch(toggleFavorite(id));                     │
  │    }, []                                               │
  │  );                                                    │
  │                                                        │
  │  <RestaurantCard                                       │
  │    onFavorite={handleFavorite(rest.id)}  ◀──          │
  │  />                                                    │
  │  handleFavorite itself is stable (useCallback)        │
  │  handleFavorite(rest.id) returns a NEW fn each render │
  │  BUT: React.memo needs the prop to be stable too...   │
  │  → still need useMemo or pass id as prop separately   │
  └────────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)
The curried form `(id) => (event) => { ... }` separates the configuration-time argument (`id`) from the execution-time argument (`event`). This is the right shape for React event handlers because the component only knows `id` at render time and receives `event` at click time.

However, I want to be precise about when this actually helps versus when it is cosmetic. Wrapping `handleFavorite` in `useCallback` with an empty dependency array makes `handleFavorite` itself stable across renders. But `handleFavorite(rest.id)` still produces a new function object on every render because currying creates a new closure each time it is called. So passing `handleFavorite(rest.id)` directly as a prop still breaks `React.memo`.

The correct production pattern has three variants depending on the situation. First, if performance is critical, pass `id` and the stable `handleFavorite` as separate props to the memoized child, and let the child compose them — `onClick={() => handleFavorite(id)}` inside the child. React.memo then compares `id` (primitive, stable) and `handleFavorite` (reference, stable via useCallback) correctly. Second, use `useMemo` to memoize `handleFavorite(rest.id)` keyed on `rest.id`. Third — and this is the architecture I prefer — lift the handler entirely, use a data attribute on the DOM element, and read from `event.currentTarget.dataset.id` in a single delegated listener. Zero per-item closures, zero re-render concerns.

The curried pattern shines in non-React contexts: Redux middleware, Express route handlers, functional pipelines where you genuinely build up a chain of partially-applied functions.

```js
// OPTION 1: pass id + handler as separate props (cleanest)
const handleFavorite = useCallback((id, event) => {
  event.preventDefault();
  dispatch(toggleFavorite(id));
}, [dispatch]);

// In child component (React.memo stable):
// <button onClick={(e) => handleFavorite(id, e)} />

// OPTION 2: memoize the partially applied fn
const handleFavoriteForId = useMemo(
  () => handleFavorite(rest.id),
  [handleFavorite, rest.id]
);
<RestaurantCard onFavorite={handleFavoriteForId} />

// OPTION 3: event delegation (no closures at all)
<ul onClick={(e) => {
  const id = e.target.closest('[data-id]')?.dataset.id;
  if (id) dispatch(toggleFavorite(id));
}}>
```

## Follow-up
**Q:** Is `handleFavorite(rest.id)` referentially stable between renders if `rest.id` is the same primitive value?

**A:** No. Each call to `handleFavorite(rest.id)` returns a brand-new closure object even if `rest.id` is the same value. JavaScript does not automatically memoize function calls. You need an explicit `useMemo(() => handleFavorite(rest.id), [rest.id])` to get a stable reference.
