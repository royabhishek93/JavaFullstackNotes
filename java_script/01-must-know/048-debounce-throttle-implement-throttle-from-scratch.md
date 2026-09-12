# Implement Throttle from Scratch
> **Topic:** Debounce & Throttle | **Level:** Fundamental | **Frequency:** High

## The Setup
Companion question to debounce implementation. Asked in the same sessions — the interviewer often asks for both in sequence to confirm you understand the distinction in code, not just words.

## The Question
Implement a `throttle(fn, limit)` function from scratch in JavaScript. The returned function should:
1. Execute `fn` immediately on the first call
2. Ignore all subsequent calls within `limit` ms
3. Preserve the `this` context and all arguments

## Diagram

```
Calls arriving:  call  call  call  call  call        call
Time:             0    200   400   600   800          2100
limit = 2000ms

Executes:         ↑                                    ↑
                 t=0                                 t=2100

Gate closes at t=0, reopens at t=2000.
Call at t=2100 is outside the window → fires.
Calls at t=200, 400, 600, 800 are inside the window → dropped.
```

## Model Answer (15 YOE)

```ts
function throttle<T extends (...args: any[]) => void>(fn: T, limit: number): T {
  let lastCall = 0;

  return function (this: unknown, ...args: Parameters<T>) {
    const now = Date.now();
    if (now - lastCall >= limit) {   // window has expired
      lastCall = now;                 // reset the gate
      fn.apply(this, args);           // execute
    }
    // calls within the window are silently dropped — no timer, no queue
  } as T;
}
```

**Why each line matters:**

- `lastCall = 0` — initializes to epoch 0, so `Date.now() - 0` is always >= `limit` on the first call. This ensures the first call always fires without any special-case check.
- `now - lastCall >= limit` — timestamp comparison, not `setTimeout`. This is the architectural choice that makes throttle fundamentally different from debounce: there is no pending timer to reset.
- Silent drop — calls within the window are not queued. If you need the *last* call in a window to fire (e.g., to capture the user's final scroll position), you need the trailing-call variant.

**The limitation — dropped trailing calls:**

```ts
// Basic throttle: last call in a burst is lost if it lands within the window
function throttleWithTrailing<T extends (...args: any[]) => void>(fn: T, limit: number): T {
  let lastCall = 0;
  let trailingTimer: ReturnType<typeof setTimeout> | undefined;

  return function (this: unknown, ...args: Parameters<T>) {
    const now = Date.now();
    const remaining = limit - (now - lastCall);

    clearTimeout(trailingTimer);

    if (remaining <= 0) {
      lastCall = now;
      fn.apply(this, args);
    } else {
      // Schedule the last dropped call to fire when the window expires
      trailingTimer = setTimeout(() => {
        lastCall = Date.now();
        fn.apply(this, args);
      }, remaining);
    }
  } as T;
}
```

**Production note:** Lodash `throttle` includes trailing call behavior by default — one more reason to use it in production rather than a naive implementation.

## Follow-up

**Q:** What is the difference between `Date.now()` comparison throttle and a `setTimeout`-based throttle?
**A:** Timestamp comparison sets a flag and checks elapsed time — it is stateless between calls and fires synchronously. `setTimeout`-based throttle schedules a future call and has a pending timer in the JS event loop between calls. Timestamp throttle is simpler and has no lingering timers. `setTimeout`-based throttle naturally supports trailing calls (fire once at the end of the window) at the cost of added complexity.

**Q:** Throttle fires the first call immediately but debounce fires after a delay. Is there a debounce that also fires the first call immediately?
**A:** Yes — leading-edge debounce: `debounce(fn, delay, { leading: true, trailing: false })`. It fires on the first call, then blocks for `delay` ms before allowing the next call. This is the right pattern for "Submit Payment" buttons: instant feedback on first click, all rapid follow-up clicks ignored.
