# Is Currying the Same as Partial Application?
> **Topic:** Currying | **Level:** Senior Trap | **Frequency:** High

## The Setup
You have just implemented a `curry` utility. The interviewer asks a definitional follow-up that most candidates answer incorrectly, revealing whether they have memorised the concept or actually understand it.

## The Question
Is currying the same as partial application? What is the precise difference?

## Diagram
```
  CURRYING — strictly one argument per step:
  ┌─────────────────────────────────────────────────────┐
  │  f(a, b, c)  →  f(a)(b)(c)                         │
  │                                                     │
  │  const add = a => b => c => a + b + c;             │
  │  add(1)      → returns g (waits for b)             │
  │  add(1)(2)   → returns h (waits for c)             │
  │  add(1)(2)(3) → 6                                  │
  │                                                     │
  │  You CANNOT call add(1, 2) — that gives NaN        │
  │  (tries to call a number as a function)             │
  └─────────────────────────────────────────────────────┘

  PARTIAL APPLICATION — fix any number of args at once:
  ┌─────────────────────────────────────────────────────┐
  │  function add(a, b, c) { return a + b + c; }        │
  │                                                     │
  │  const add1and2 = add.bind(null, 1, 2);            │
  │  add1and2(3); // 6 — fixed TWO args in one call     │
  │                                                     │
  │  The original add was NEVER curried.                │
  │  Partial application does NOT require currying.     │
  └─────────────────────────────────────────────────────┘

  RELATIONSHIP:
  A curried call with fewer than N args IS partial application.
  Partial application does NOT require currying.
  ┌──────────────────┐
  │ Partial          │
  │ Application      │
  │   ┌────────────┐ │
  │   │  Currying  │ │  Currying is a SUBSET of partial application
  │   └────────────┘ │
  └──────────────────┘
```

## Model Answer (15 YOE)
They are related but distinct. Currying is a transformation technique: it converts a function of N arguments into a chain of N unary functions. Every step takes exactly one argument. Partial application is a broader technique: it pre-fills some arguments of a function and returns a function expecting the remaining arguments — those remaining arguments can be one or many.

A curried function naturally supports partial application because calling it with fewer than N arguments gives you a partially applied function. But partial application does not require currying — `fn.bind(null, a, b)` partially applies two arguments to a function that was never curried.

```js
// Currying — strictly one arg per step
const curriedAdd = a => b => c => a + b + c;
curriedAdd(1)(2)(3); // must apply one at a time

// Partial application — can fix multiple at once
function add(a, b, c) { return a + b + c; }
const addFrom1and2 = add.bind(null, 1, 2);
addFrom1and2(3); // 6 — fixed two args in one call

// A generic curry() utility blurs this line intentionally:
// curried(1, 2)(3) is partial application using a curried-style utility
// but the underlying function was never strictly curried
```

The wrong answer candidates give: "they're the same thing, currying is just another name for partial application." That collapses a meaningful distinction that becomes important when you are designing library APIs or reading code in Ramda/fp-ts.

## Follow-up
**Q:** In practice, when should you choose strictly curried arrow functions (`a => b => c => ...`) over using a generic `curry()` utility?

**A:** Strict arrow currying for new code you control — it is explicit, zero overhead, and the shape is visible in the source. Use `curry()` when adapting a function you cannot rewrite, or when you need grouped-argument calls (e.g., `f(1, 2)(3)`). The generic utility exists for adaptation, not as the primary pattern.

## Why It's a Trap
Most candidates who know what currying is conflate it with partial application. Getting this wrong signals surface-level knowledge of functional programming — the kind that comes from reading a blog post rather than using the patterns in production.

## What NOT to Say
"Currying and partial application are the same thing." Or: "Currying is just a special case of partial application." The directionality is the other way around — partial application is the broader concept; currying is one specific way to achieve it.
