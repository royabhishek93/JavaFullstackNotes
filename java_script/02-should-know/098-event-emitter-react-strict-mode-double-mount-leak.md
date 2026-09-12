# React Strict Mode Double-Mount Listener Leak
> **Topic:** Event Emitter | **Level:** Senior Trap | **Frequency:** High

## The Setup
A senior engineer adds an event bus subscription to a React component. Tests pass. The component works correctly in production. But in development, the cart count badge always shows double the correct number. Refreshing the page fixes it temporarily but the doubling returns. There are no errors in the console.

## The Question
Why does an `eventBus.on()` registration inside a React `useEffect` without a cleanup function leak in development but not in production? What is React Strict Mode double-mount? What is the correct fix?

## Diagram

```
React 18 Strict Mode (development only):
  Component mounts   → useEffect fires → bus.on('cart.updated', handler)
  Component unmounts → no cleanup      → handler stays in listeners array
  Component remounts → useEffect fires → bus.on('cart.updated', handler)
                                          ↑ SECOND COPY ADDED

listeners['cart.updated'] = [handler, handler]

bus.emit('cart.updated', { itemCount: 3 })
  → handler({ itemCount: 3 }) → setCount(3)
  → handler({ itemCount: 3 }) → setCount(3)  ← called twice
  → UI shows count = 3 (last write wins) but the update ran twice

After 5 Fast Refreshes:
  listeners['cart.updated'] = [handler × 5]
  emit triggers 5 setCount calls → 5 re-renders per event

Node.js EventEmitter emits MaxListenersExceededWarning at 11 listeners.
Browser EventEmitter: silently accumulates.

PRODUCTION (Strict Mode disabled):
  Mount once → one on() → one handler → correct behaviour
```

## Model Answer (15 YOE)

**What React Strict Mode does:**

React 18 Strict Mode intentionally mounts each component twice in development (mount → unmount → remount) to surface missing cleanup bugs. This is not a bug in React — it is a deliberate tool for catching exactly this category of error. In production builds, Strict Mode is disabled and components mount once.

**Why the bug only shows in development:**

Production: `mount → on() → [handler]` — one copy, correct.
Development: `mount → on() → unmount (no cleanup) → remount → on() → [handler, handler]` — two copies, double-firing.

**The fix — always pair every `on()` with an `off()` in the cleanup:**

```js
// BROKEN: no cleanup
useEffect(() => {
  eventBus.on('cart.updated', handleCartUpdate);
  // missing return
}, []);

// CORRECT: paired cleanup
useEffect(() => {
  const handler = ({ itemCount }: { itemCount: number }) => setCount(itemCount);
  eventBus.on('cart.updated', handler);
  return () => eventBus.off('cart.updated', handler); // ← runs on unmount
}, []);
```

The cleanup function (the function returned from `useEffect`) runs when:
1. The component unmounts
2. The effect re-runs (dependency changed) — the previous effect is cleaned up before the new one runs

For a subscription, cleanup on unmount is the critical case. Strict Mode's deliberate unmount/remount cycle exercises this path in development.

**The rule:** Every `on()` call has one corresponding `off()` call. No exceptions.

**Detecting the leak in production (if it somehow slips through):**

```js
// Health check — alert if any event exceeds 20 listeners
setInterval(() => {
  for (const [event, fns] of eventBus.listeners) {
    if (fns.length > 20) {
      alerting.warn(`Possible listener leak: ${event} has ${fns.length} listeners`);
    }
  }
}, 30_000);
```

## Why It's a Trap

This bug is invisible in production (Strict Mode only runs in development). Many engineers disable Strict Mode to "fix" the doubling, which removes the diagnostic tool rather than the bug. The correct response to Strict Mode exposing a bug is to fix the bug.

The second trap layer: even after fixing the Strict Mode doubling, engineers sometimes use an inline arrow function in the cleanup (new reference, `off()` is a no-op). The leak persists despite having a cleanup function. The fix is not just "add a cleanup" — it is "add a cleanup with the same reference."

## What NOT to Say

- "I'll disable Strict Mode — it causes this double-mount issue." — Strict Mode is revealing a bug; disabling it hides the bug.
- "I'll use `useEffect` with `[]` so it only runs once." — `[]` is already used in the correct pattern above. The problem is missing cleanup, not the dependency array.
- "This doesn't happen in production so it's fine." — This class of bug (missing cleanup) also causes leaks when components re-mount for legitimate reasons (route changes, conditional rendering, tab switching in SPAs).

## Follow-up

**Q:** Why does Strict Mode unmount and remount in development? What bugs does it find besides this one?
**A:** Strict Mode simulates what might happen in React's future concurrent rendering model, where components may be mounted and unmounted multiple times as React prepares off-screen trees. Beyond event bus leaks, it surfaces: `setInterval`/`setTimeout` without cleanup, WebSocket connections not closed on unmount, `addEventListener` without `removeEventListener`, and subscription libraries that accumulate listeners. Any stateful setup without teardown is exposed.
