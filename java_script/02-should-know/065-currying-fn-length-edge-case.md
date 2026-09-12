# Why Does `fn.length` Break with Default Parameters and Rest Parameters?
> **Topic:** Currying | **Level:** Senior Trap | **Frequency:** Medium

## The Setup
You have just implemented a `curry` utility that relies on `fn.length` to determine arity. The interviewer asks a pointed follow-up that most candidates who can implement `curry` have never stopped to question. This exposes whether they have actually used the utility in production code or only in toy examples.

## The Question
Why does `fn.length` break when functions have default parameters or rest parameters? Show the exact failure modes and how you fix them.

## Diagram
```
  fn.length RULES:
  ┌──────────────────────────────────────────────────────┐
  │  function f(a, b, c)     {}  │  f.length === 3  ✓   │
  │  function f(a, b, c = 0) {}  │  f.length === 2  ⚠️  │
  │  function f(a = 0, b, c) {}  │  f.length === 0  ⚠️  │
  │  function f(a, ...rest)  {}  │  f.length === 1  ⚠️  │
  │  function f(...args)     {}  │  f.length === 0  ⚠️  │
  └──────────────────────────────────────────────────────┘

  FAILURE MODE WITH curry():
  ┌──────────────────────────────────────────────────────┐
  │  function greet(name, greeting = 'Hello') { ... }    │
  │  greet.length === 1                                  │
  │                                                      │
  │  const curriedGreet = curry(greet);                  │
  │  curriedGreet('Alice')                               │
  │    → args.length (1) >= fn.length (1) → CALLS NOW   │
  │    → greet('Alice') → "Hello, Alice"  ← works here  │
  │                                                      │
  │  But if you wanted to supply greeting:               │
  │  curriedGreet('Alice')('Hi') → TypeError!           │
  │  (tries to call a string as a function)              │
  └──────────────────────────────────────────────────────┘

  CATASTROPHIC FAILURE:
  ┌──────────────────────────────────────────────────────┐
  │  function h(a = 0, b, c) {}  h.length === 0         │
  │  curry(h)() → calls h() immediately with no args    │
  │  No chance to supply a, b, or c                     │
  └──────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)
`fn.length` returns the number of parameters before the first one with a default value or before a rest parameter. It does not count defaults or rest.

```js
function f(a, b, c = 0)  { }   // f.length === 2
function g(a, ...rest)   { }   // g.length === 1
function h(a = 0, b, c)  { }   // h.length === 0
```

This means `curry(f)` built on `fn.length` will call `f` after two arguments, treating `c` as absent (it gets its default `0`). That is probably fine in practice. But `curry(h)` will think `h` is a nullary function and call it immediately with zero arguments — completely wrong.

The production fix: never use defaults in functions you intend to curry, or provide the arity explicitly via `curryN(fn, expectedArity)`. Ramda's `curryN(n, fn)` is this pattern.

```js
// Fix: curryN — explicit arity overrides fn.length
function curryN(fn, n) {
  return function curried(...args) {
    if (args.length >= n) return fn.apply(this, args);
    return (...more) => curried.apply(this, args.concat(more));
  };
}

// Now works correctly for functions with defaults:
function greet(name, greeting = 'Hello') {
  return `${greeting}, ${name}!`;
}

const curriedGreet = curryN(greet, 2); // tell it arity is 2
curriedGreet('Alice')('Hi'); // "Hi, Alice!"
curriedGreet('Bob');          // "Hello, Bob!" (uses default)
```

There is a second subtle issue: if you call a curried function with more arguments than the arity, this implementation passes the extras through to the original function. With rest parameters that is intentional, but it can lead to surprising behavior when the original function ignores extra arguments silently.

## Follow-up
**Q:** Is there a way to introspect a function's true arity including default parameters at runtime?

**A:** Not via `fn.length`. You would need to either parse the function's source code with `fn.toString()` (fragile and not recommended), declare the arity via a separate metadata property on the function, or use TypeScript at compile time to enforce arity contracts. In practice, the standard convention in functional libraries is to document the expected arity and use `curryN` when it cannot be inferred from `fn.length`.

## Why It's a Trap
Most candidates who can implement `curry` have never stopped to question the `fn.length` assumption. Asking this exposes whether they have actually used the utility in production code or only in toy examples with plain multi-argument functions.

## What NOT to Say
"fn.length always gives you the number of parameters a function takes." This is only true for functions with no defaults and no rest parameter — a significant constraint that is easy to forget in modern JavaScript.
