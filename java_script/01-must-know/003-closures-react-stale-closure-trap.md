# React Stale Closure in a setInterval Effect
> **Topic:** Closures | **Level:** Intermediate | **Frequency:** High

## The Setup
You are a senior engineer at Swiggy working on a live order tracking page. A junior dev writes a `useEffect` that polls the backend every 5 seconds using `setInterval`. In production, users report that the displayed ETA stops updating even though the API returns fresh data. The component re-renders but the old ETA value stays on screen.

## The Question
Why does `setInterval` inside `useEffect` sometimes read stale state, and how do you fix it without removing the interval?

## Diagram
```
  Render 1 (eta = "30 min")
  ┌────────────────────────────────────────────┐
  │  useEffect(() => {                         │
  │    const id = setInterval(() => {          │
  │      console.log(eta); // "30 min" ◀──┐   │
  │    }, 5000);                           │   │
  │  }, []);  // empty dep array           │   │
  └────────────────────────────────────────┘   │
                                               │ closure captures
  Render 2 (eta = "12 min")                   │ eta from Render 1
  ┌────────────────────────────────────────────┘
  │  NEW eta = "12 min" exists in render scope
  │  BUT the interval callback was born in Render 1
  │  It still sees eta = "30 min" ← STALE CLOSURE
  └───────────────────────────────────────────
```

## Model Answer (15 YOE)
This is one of the most common production bugs I see in React codebases, and it bites teams who understand hooks syntactically but not mechanically.

When `useEffect` with an empty dependency array runs, it captures the values from that first render in a closure. The `setInterval` callback is born in that closure. Every subsequent render creates a new `eta` value in its own render scope, but the interval callback is still holding a reference to the original render's `eta`. The JS engine keeps that stale value alive specifically because the interval's closure references it.

The three production-grade fixes: First, use a `useRef` to hold the latest value — refs are mutable and live outside the render cycle, so the callback always reads the current ref value rather than a captured snapshot. Second, include `eta` in the effect's dependency array and clean up/restart the interval on each change — less elegant but semantically honest. Third, use the functional update form of setState when the new value derives from the old value, bypassing the captured reference entirely.

At Swiggy scale, stale closures in polling effects also cause silent API over-calls because the cleanup function itself can be stale — always verify your cleanup captures the correct interval ID.

```js
// FIX 1: useRef for latest value
const etaRef = useRef(eta);
useEffect(() => { etaRef.current = eta; }, [eta]);
useEffect(() => {
  const id = setInterval(() => console.log(etaRef.current), 5000);
  return () => clearInterval(id);
}, []); // reads ref.current at execution time, not closure time

// FIX 2: functional setState (when new value derives from old)
setCount(prev => prev + 1); // never stale, always uses latest
```

## Follow-up
**Q:** Why does using `useRef` solve the stale closure problem?

**A:** A ref object is a stable mutable container that exists outside the render cycle. `ref.current` is always a live pointer to the latest value, not a closure-captured snapshot. The interval callback reads `ref.current` at execution time rather than closing over a specific value at creation time — so it always gets fresh data regardless of how many re-renders have happened.
