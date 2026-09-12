# Implement a Generic `curry()` Utility
> **Topic:** Currying | **Level:** Fundamental | **Frequency:** High

## The Setup
You are a principal engineer at Flipkart building an internal functional utilities library used by 50+ teams. Teams want to take existing multi-argument functions and curry them on demand — without manually rewriting every function. You need to implement a `curry` utility that handles functions of any arity and supports both one-at-a-time and grouped argument calls.

## The Question
Implement a production-grade generic `curry` utility. Walk through exactly how it works, including the edge cases with `fn.length`.

## Diagram
```
  curry(fn) — argument accumulation loop
  ┌────────────────────────────────────────────────────────┐
  │  curry(fn)                                             │
  │    creates curried(...args)                            │
  │                                                        │
  │  curried(1) → args=[1], fn.length=3, need more        │
  │    returns (...more) => curried(...[1], ...more)       │
  │                                                        │
  │  curried(1)(2) → args=[1,2], fn.length=3, need more  │
  │    returns (...more) => curried(...[1,2], ...more)     │
  │                                                        │
  │  curried(1)(2)(3) → args=[1,2,3], fn.length=3, DONE  │
  │    calls fn(1, 2, 3) → result                         │
  └────────────────────────────────────────────────────────┘

  ALSO VALID (grouped args):
  curried(1, 2)(3)  → args accumulate to [1,2,3] → fn called
  curried(1)(2, 3)  → args accumulate to [1,2,3] → fn called
  curried(1, 2, 3)  → args.length >= fn.length   → fn called directly
```

## Model Answer (15 YOE)
The key insight is that `curry` is a recursive wrapper. The returned `curried` function checks whether it has received enough arguments to satisfy the original function's declared arity (`fn.length`). If yes, it delegates immediately. If not, it returns a new function that concatenates the new arguments with the ones already collected and calls `curried` again. This is tail-recursive partial application.

```js
function curry(fn) {
  return function curried(...args) {
    if (args.length >= fn.length) {
      return fn.apply(this, args);
    }
    return function (...moreArgs) {
      return curried.apply(this, args.concat(moreArgs));
    };
  };
}
```

The `apply(this, ...)` matters — it preserves the calling context if the original function relies on `this`, which is relevant when currying class methods or framework callbacks.

Now the edge cases I always mention in interviews: `fn.length` only counts parameters up to the first one with a default value or a rest parameter. `function f(a, b = 0, ...rest)` has `fn.length === 1`. This means `curry` will think `f` is a unary function and call it after one argument. The fix is to either avoid defaults in functions you intend to curry, or pass the expected arity explicitly: `curry(fn, 3)` and use that instead of `fn.length`. Libraries like Ramda take this approach.

Another production consideration: this implementation allows calling with more than `fn.length` arguments — the extras are passed through. That is usually desirable. If you want strict arity enforcement, add a check that `args.length === fn.length` rather than `>=`.

```js
// curryN variant — explicit arity
function curryN(fn, n) {
  return function curried(...args) {
    if (args.length >= n) return fn.apply(this, args);
    return (...more) => curried.apply(this, args.concat(more));
  };
}

// Usage
const sum3 = curryN((a, b, c) => a + b + c, 3);
sum3(1)(2)(3);   // 6
sum3(1, 2)(3);   // 6
```

## Follow-up
**Q:** Why does Ramda's `curry` handle variadic functions differently from this implementation?

**A:** Ramda's `curry` uses the declared arity and does not support rest parameters natively. For variadic functions (`...args`), `fn.length` is 0, so Ramda treats them as nullary and calls immediately. Ramda's `curryN(n, fn)` is the escape hatch — you declare the arity explicitly, bypassing `fn.length`.
