# Can Closures Cause Memory Leaks? Give a Concrete Production Example
> **Topic:** Closures | **Level:** Senior Trap | **Frequency:** Medium

## The Setup
You have described closures and their uses. The interviewer probes your production awareness: "We know closures are powerful, but I've heard they can cause memory leaks. Can you walk me through a real scenario?" This is asked specifically to see whether you understand GC retention chains or are just pattern-matching on "closures bad."

## The Question
Can closures cause memory leaks? Give a concrete production example with the full GC retention chain.

## Diagram
```
  PRODUCTION LEAK PATTERN — window listener in a React component:

  Component mounts
  ┌──────────────────────────────────────────────────┐
  │  useEffect(() => {                               │
  │    window.addEventListener('resize', handler);   │
  │    // handler closes over: props, state, refs    │
  │  }, []);                                         │
  └──────────────────────────────────────────────────┘

  Component unmounts (no cleanup)
  ┌──────────────────────────────────────────────────┐
  │  React removes component DOM — but NOT the       │
  │  window listener. window is never GC'd.          │
  └──────────────────────────────────────────────────┘

  RETENTION CHAIN (everything stays alive):
  window
    └──▶ resize event listener list
           └──▶ handler function
                  └──▶ closure environment
                         └──▶ props object
                                └──▶ child component trees
                                       └──▶ fetched data arrays
                                              └──▶ ... grows per mount/unmount cycle
```

## Model Answer (15 YOE)
A closure leaks memory when it keeps a reference to a large object alive longer than needed, and that closure itself is kept alive by something with an unexpectedly long lifetime.

The production scenario I see most: a single-page app where a component registers an event listener on `window` or `document` — not a component-local DOM node. When the component unmounts, React tears down the component's DOM subtree but it does not — and cannot — remove listeners attached to `window`. The listener holds a closure over the component's props or state object, which is now a detached but GC-reachable graph. That object includes all child component trees, any fetched data arrays, everything. The leak grows on every mount/unmount cycle.

```js
// LEAKING — grows on every mount/unmount
useEffect(() => {
  const handler = () => {
    setDimensions({ width: window.innerWidth, height: window.innerHeight });
    // closes over: setDimensions, which closes over the fiber node
  };
  window.addEventListener('resize', handler);
  // no cleanup = listener lives until page reload
}, []);

// FIXED
useEffect(() => {
  const handler = () => { /* ... */ };
  window.addEventListener('resize', handler);
  return () => window.removeEventListener('resize', handler); // ← critical
}, []);
```

The fix is always the same: clean up in `useEffect`'s return function. And architecturally: never attach listeners to global objects in leaf components — centralize global listeners in a single manager that owns the cleanup lifecycle.

## Follow-up
**Q:** How do you detect a closure-induced memory leak in a running React app?

**A:** Chrome DevTools heap snapshot + allocation timeline. Take a baseline, mount/unmount the suspected component 10 times, force GC, take another snapshot. Compare the two — look for "Detached HTMLElement" entries and trace their retaining path. If the path goes through a listener → closure → React fiber, you found it. Tools like `why-did-you-render` help with render-related leaks; for raw closure leaks, heap snapshots are the ground truth.

## Why It's a Trap
Most candidates say "yes, closures can leak" but cannot explain the precise GC retention chain or name a realistic scenario — which signals they have read about it but never debugged one.

## What NOT to Say
"Closures always cause memory leaks if you're not careful." That is vague and wrong — closures only leak when the closure itself is held alive by a root reference (like a global event listener) longer than intended. A closure that goes out of scope is collected normally.
