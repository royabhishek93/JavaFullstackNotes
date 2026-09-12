# once() + off() with the Original Function — Silent No-Op Trap
> **Topic:** Event Emitter | **Level:** Senior Trap | **Frequency:** High

## The Setup
A developer registers a payment handler with `once()`, then realizes a condition changed and wants to cancel it before it fires. They call `off()` with the original function reference. Nothing breaks — but the handler still fires when the event is emitted. This is a silent bug that reaches production.

## The Question
Why does calling `off(event, originalFn)` after `once(event, originalFn)` fail to remove the listener? What is stored in the listeners array? What is the correct fix?

## Diagram

```
emitter.once('payment', handler)
         │
         ▼
  wrapper = (...args) => { handler(...args); off('payment', wrapper); }
  listeners['payment'] = [wrapper]    ← wrapper stored, NOT handler

emitter.off('payment', handler)
         │
         ▼
  filter(fn => fn !== handler)
  listeners['payment'].indexOf(handler) = -1   ← handler is NOT in the array
  result: listeners['payment'] = [wrapper]     ← unchanged, no-op

emitter.emit('payment', data)
         │
         ▼
  wrapper(data) → handler(data) fires   ← developer expected silence
                → off('payment', wrapper) removes wrapper
```

## Model Answer (15 YOE)

**Root cause:**

`once()` never stores the original listener. It creates a `wrapper` function that calls the original and then self-removes. The listeners array contains `[wrapper]`. When you call `off(event, originalFn)`, the `filter(fn => fn !== originalFn)` comparison looks for `originalFn` in the array, does not find it, and returns the same array unchanged. The wrapper is still registered and will fire.

**Fix 1 — Return the wrapper from `once` so callers can cancel it:**

```js
once(event, listener) {
  const wrapper = (...args) => {
    listener(...args);
    this.off(event, wrapper);
  };
  wrapper._originalListener = listener; // optional: tag for debugging
  this.on(event, wrapper);
  return wrapper; // ← caller holds the cancellable reference
}

// Usage:
const cancel = emitter.once('payment', handler);
// ...conditions changed...
emitter.off('payment', cancel); // passes the actual wrapper → works
```

**Fix 2 — Search by `_originalListener` tag in `off()`:**

```js
off(event, listener) {
  if (!this.listeners.has(event)) return this;
  const updated = this.listeners.get(event).filter(fn =>
    fn !== listener && fn._originalListener !== listener // check both
  );
  this.listeners.set(event, updated);
  return this;
}
```

This lets callers pass either the wrapper or the original function to `off()`. Node.js's built-in EventEmitter uses a similar approach — it stores `{ listener: originalFn, once: true }` objects in the array rather than bare wrapper functions.

**Which fix to choose:**

Fix 1 (return wrapper) is cleaner and more explicit — the caller opts into cancellability by capturing the return value. Fix 2 (tag-based off) is more ergonomic for callers who don't store the return value, but it adds complexity to `off()`. Returning the wrapper from `once` is the industry convention (also what the DOM's `{ once: true }` option does internally).

## Why It's a Trap

The trap works because the developer's mental model is: "`once` is like `on` but with auto-removal." So they assume `off(originalFn)` works the same way it works after `on(originalFn)`. The implementation detail — that `once` stores a wrapper — is hidden from the caller, which makes the silent no-op especially dangerous.

Node.js EventEmitter v12+ exposes `emitter.rawListeners(event)` to inspect the underlying wrappers, which helps diagnose this exact bug in production.

## What NOT to Say

- "`off()` should accept original functions and look them up automatically." — Without the `_originalListener` tag, this is impossible; the array only contains wrappers.
- "Just use `on()` and manually call `off()` instead of `once()`." — That is a workaround, not a fix. `once()` is semantically clearer and correctly handles the case where `emit` fires before you get a chance to call `off()` manually.

## Follow-up

**Q:** Node.js EventEmitter's `emitter.listeners(event)` returns original functions, not wrappers, for `once` listeners. How?
**A:** Node.js stores `{ fn: wrapper, listener: originalFn }` objects (not bare functions) in the internal array. `listeners()` maps these objects to their `.listener` property, presenting the original functions. `rawListeners()` returns the actual wrappers. This is a more ergonomic API design — it hides the wrapper from most callers while still making it accessible for cancellation.
