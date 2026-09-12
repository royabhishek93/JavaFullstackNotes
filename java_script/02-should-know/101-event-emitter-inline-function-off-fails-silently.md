# Inline Arrow Function in off() — Silent No-Op
> **Topic:** Event Emitter | **Level:** Senior Trap | **Frequency:** High

## The Setup
A developer writes a useEffect that subscribes to an event bus and returns a cleanup function. The code looks correct at a glance — there is a cleanup. But in development (React Strict Mode), the cart count still doubles. The `off()` call in the cleanup is silently doing nothing.

## The Question
Why does this cleanup fail, and what is the exact fix?

```js
useEffect(() => {
  eventBus.on('cart.updated', ({ count }) => setCartCount(count));

  return () => {
    // looks correct — but isn't
    eventBus.off('cart.updated', ({ count }) => setCartCount(count));
  };
}, []);
```

## Diagram

```
MEMORY IDENTITY OF FUNCTIONS IN JAVASCRIPT
───────────────────────────────────────────
Every time an arrow function expression is evaluated, JavaScript
creates a NEW function object at a NEW memory address.

Line 2: ({ count }) => setCartCount(count)   → 0xA1B2 (object at address A1B2)
Line 6: ({ count }) => setCartCount(count)   → 0xC3D4 (DIFFERENT object, different address)

They look identical in source code.
They are NOT the same value — different objects in memory.

eventBus.on('cart.updated', 0xA1B2)     → listeners = [fn@0xA1B2]
eventBus.off('cart.updated', 0xC3D4)
  → filter(fn => fn !== 0xC3D4)
  → fn@0xA1B2 !== 0xC3D4 → TRUE → kept in array
  → listeners = [fn@0xA1B2]   ← UNCHANGED, no-op

Result: cleanup registers but does nothing.
        Strict Mode double-mount → [fn@0xA1B2, fn@0xE5F6] after remount.
        emit fires setCartCount twice.
```

## Model Answer (15 YOE)

**Root cause:**

JavaScript arrow function expressions are object literals. Each evaluation of `() => ...` creates a brand-new function object. The two arrow functions in the `on` and `off` calls are textually identical but are different values in memory — they fail the `===` identity check inside `off()`'s filter.

`off()` works by reference equality: `filter(fn => fn !== listener)`. If `listener` is not the same object that was passed to `on()`, the filter removes nothing.

**The fix — name the handler so both calls share the same reference:**

```js
useEffect(() => {
  // Named const — same reference captured by both the on() call and the cleanup
  const handler = ({ count }: { count: number }) => setCartCount(count);

  eventBus.on('cart.updated', handler);

  return () => eventBus.off('cart.updated', handler); // same object ✓
}, []);
```

`handler` is declared once in the `useEffect` closure. Both `on(handler)` and `off(handler)` reference the same variable — the same function object at the same memory address. `off()`'s filter correctly identifies and removes it.

**Common variations of this mistake:**

```js
// BROKEN — method call creates new bound function each time:
useEffect(() => {
  eventBus.on('resize', this.handleResize.bind(this));
  return () => eventBus.off('resize', this.handleResize.bind(this)); // different bound fn
}, []);

// FIXED:
const handler = this.handleResize.bind(this); // one bind, one object
eventBus.on('resize', handler);
return () => eventBus.off('resize', handler);

// BROKEN — object destructuring inline creates new fn:
eventBus.on('data', function({ id }) { process(id); });
eventBus.off('data', function({ id }) { process(id); }); // different fn object

// FIXED: named function reference
function handleData({ id }) { process(id); }
eventBus.on('data', handleData);
eventBus.off('data', handleData);
```

**Why this is a senior trap:**

The cleanup *exists* — the code looks correct to a code reviewer. The bug is invisible without knowing that arrow function literals create new objects on every evaluation. It requires understanding JavaScript's reference semantics and how `off()` is implemented internally.

## Why It's a Trap

Junior developers expect that two functions with the same source code are equal. In Python (with `==` operator on simple lambdas), this might sometimes pass. In JavaScript, `===` on functions always checks object identity — same source code, different objects, not equal.

The bug is doubly tricky because:
1. It looks like a cleanup is in place (no obvious omission)
2. It only manifests as doubling under Strict Mode — invisible in production
3. The fix is a single-line refactor that looks trivially simple once you know it

## What NOT to Say

- "I need to use `useCallback` to memoize the handler." — `useCallback` memoizes across renders but is not needed here. A `const` inside `useEffect` is sufficient — both the `on` and `off` calls are in the same effect execution, sharing the same scope.
- "The `off()` function is broken." — `off()` works correctly; the bug is at the call site.

## Follow-up

**Q:** Is there a way to implement `off()` that is more forgiving — matching by source code rather than reference?
**A:** Technically you could compare `fn.toString()`, but this breaks as soon as two different handlers have the same source code, and it is slow (string comparison vs reference comparison). Reference equality is the correct contract for `off()`. The caller is responsible for preserving the reference. This is also how `removeEventListener` works in the browser DOM — you must pass the exact same function object that was passed to `addEventListener`.
