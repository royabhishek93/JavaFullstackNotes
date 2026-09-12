# What Is a Closure and How Does Lexical Scope Enable It?
> **Topic:** Closures | **Level:** Fundamental | **Frequency:** High

## The Setup
You are in a senior JavaScript interview at any product-first company — Flipkart, Amazon, Atlassian, a fintech startup. The interviewer opens with the most foundational JavaScript question. How you answer this sets the tone for the entire interview: a shallow answer signals memorisation; a deep answer signals fluency.

## The Question
What is a closure? How does lexical scoping make closures possible in JavaScript? Give a concrete example and explain what actually happens in memory.

## Diagram
```
  CALL STACK                 HEAP (Closure Environment)
  ┌────────────────┐         ┌──────────────────────────┐
  │  outer()       │         │  [[Environment]]          │
  │  ┌──────────┐  │  keeps  │  ┌────────────────────┐  │
  │  │ count=0  │──┼─alive──▶│  │  count  → 0        │  │
  │  │ inner fn │  │         │  │  inner  → fn ref   │  │
  │  └──────────┘  │         │  └────────────────────┘  │
  └────────────────┘         └──────────┬───────────────┘
  outer() returns                       │ inner fn holds
  and is popped                         │ reference to env
                                        ▼
                             ┌──────────────────────────┐
                             │  const counter = outer() │
                             │  counter() → count++     │
                             │  count is STILL ALIVE    │
                             └──────────────────────────┘

  SCOPE CHAIN LOOKUP ORDER:
  inner fn → its own scope → outer scope (closure) → global
  ┌───────┐   ┌─────────────┐   ┌───────────────┐   ┌────────┐
  │ local │──▶│ closure env │──▶│  module scope │──▶│ global │
  └───────┘   └─────────────┘   └───────────────┘   └────────┘
```

## Model Answer (15 YOE)
A closure is a function packaged together with a live reference to the variables in the scope where it was defined. "Live reference" is the key phrase — it is not a snapshot, it is a pointer. When the outer function finishes and its execution context is destroyed, any variable that an inner function still references is kept alive by the JavaScript engine's garbage collector. The function and its captured environment travel together as one unit.

Lexical scoping is what makes this possible. In JavaScript, a function's scope is determined by where it is written in the source code, not where it is called from. When the engine parses the inner function, it attaches a `[[Environment]]` slot to it pointing at the outer function's variable environment. That link persists regardless of where or when the inner function is eventually executed.

Concrete example: `makeCounter` returns an `increment` function. After `makeCounter` returns, its execution context is popped off the call stack. But `count` is kept alive on the heap because `increment`'s `[[Environment]]` still references it. Every call to `increment()` reads and mutates that same `count` — not a copy, the live variable.

```js
function makeCounter() {
  let count = 0;
  return {
    increment: () => ++count,
    value:     () => count,
  };
}
const c = makeCounter();
c.increment(); // 1
c.increment(); // 2
c.value();     // 2
```

The two practical consequences that interviewers test against: (1) because it is a live reference, mutating the closed-over variable after closure creation changes what the closure sees — this is the root cause of the `var` loop bug and React stale closures. (2) Because the GC keeps the referenced objects alive, closures holding large objects can cause memory leaks if they outlive their expected lifetime.

## Follow-up
**Q:** What is the difference between lexical scope and dynamic scope, and which does JavaScript use?

**A:** Lexical scope means a variable's scope is determined by its position in the written source code — the "lexical structure" of the program. Dynamic scope means a variable's scope is determined by the call stack at runtime — which function called the current one. JavaScript uses lexical scope for variables. The one place JavaScript uses something like dynamic scope is `this` — the value of `this` is determined by how a function is called, not where it is defined, which is why arrow functions (which capture `this` lexically) were introduced to avoid the confusion.
