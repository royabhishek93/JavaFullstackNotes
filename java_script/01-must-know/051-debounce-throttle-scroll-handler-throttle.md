# Scroll Handler with Throttle — Reading Progress Bar
> **Topic:** Debounce & Throttle | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A long-form article page (think Medium, Substack) shows a reading progress bar at the top. The `scroll` event fires at ~60fps — 60 times per second. Calling `getBoundingClientRect()` or reading `scrollY` on every frame forces a synchronous layout reflow, causing jank on mid-range Android devices. The performance team flags it in Lighthouse.

## The Question
You need to add a scroll-driven reading progress bar. Walk through your choice of rate-limiting strategy and implement it with proper cleanup and performance considerations.

## Diagram

```
scroll events at 60fps:
|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||
0ms                                                          1000ms
(60 events — each triggers scrollY read + DOM style mutation)

throttle(handler, 100) — ~10 updates per second:
|         |         |         |         |         |         |
0ms      100ms     200ms     300ms     400ms     500ms    600ms
(6 events — visually smooth, 90% fewer reflows)
```

## Model Answer (15 YOE)

**Why throttle, not debounce:**

The progress bar should update *during* scrolling, not only after the user stops. Debounce would freeze the bar at its last position until the user pauses — jarring UX. Throttle gives smooth-enough updates at ~10fps (every 100ms) with minimal CPU cost. 100ms is below the human threshold for noticing lag in a continuous visual update.

```ts
const handleScroll = throttle(() => {
  const scrolled = window.scrollY;
  const total = document.documentElement.scrollHeight - window.innerHeight;
  const pct = Math.min(100, Math.round((scrolled / total) * 100));
  progressBarRef.current?.style.setProperty('width', `${pct}%`);
}, 100);

useEffect(() => {
  window.addEventListener('scroll', handleScroll, { passive: true });
  return () => window.removeEventListener('scroll', handleScroll);
}, []);
```

**`{ passive: true }` — why it matters:**

Tells the browser you will not call `preventDefault()` on this scroll event. This allows the browser to scroll on the compositor thread without waiting for your JavaScript to finish. Without `passive: true`, the browser must pause scrolling to check if your listener will cancel it — causing scroll latency even when you never actually call `preventDefault`. Always use `{ passive: true }` on scroll and touchstart listeners that do not need to block scrolling.

**`handleScroll` must be stable:** The `removeEventListener` call in the cleanup must receive the exact same function reference that was passed to `addEventListener`. If `handleScroll` is re-created on every render, the cleanup removes a *different* function object and the original listener leaks. Create it outside the component or with `useRef`/`useMemo`.

**Alternative — `requestAnimationFrame`:** For the smoothest possible progress bar, use `rAF` instead of throttle. `rAF` synchronises your update to the browser's own paint cycle (~16ms), preventing visual tearing. The trade-off is more CPU than 100ms throttle. Use `rAF` for animations, throttle for less visually sensitive updates.

## Follow-up

**Q:** What is the difference between throttling scroll at 100ms vs using `requestAnimationFrame`?
**A:** `throttle(fn, 100)` fires at most once per 100ms regardless of frame rate — roughly 10fps. `requestAnimationFrame` fires once per frame, typically 60fps on high-refresh displays. For a reading progress bar, 10fps is invisible to users and uses far less CPU. `rAF` is the right choice only when you need smooth per-frame animation — canvas drawing, physics simulations, parallax effects.

**Q:** The progress bar uses `style.setProperty` directly instead of React state. Is that a React anti-pattern?
**A:** It is a deliberate performance optimisation. Setting React state inside a 60fps scroll handler creates 60 re-renders per second. Direct DOM mutation via `ref` bypasses the React reconciler entirely — one style write per throttle interval, no virtual DOM diffing. This is the accepted pattern for performance-critical animations in React. The trade-off is that the value is not in React state, so it cannot be read by other components — acceptable for a purely visual indicator.
