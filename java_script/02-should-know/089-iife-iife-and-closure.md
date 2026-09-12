# Senior Trap — Does an IIFE Create a Closure?
> **Topic:** IIFE | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

An interviewer asks: "You said an IIFE creates a private scope. Does that mean an IIFE always creates a closure?" A candidate answers: "Yes — every IIFE is a closure because it wraps code in a function scope."

## The Question

Is that answer correct? What is the precise relationship between an IIFE and a closure, and how do you tell whether a specific IIFE has created one?

## Model Answer (15 YOE)

The candidate is wrong — or at least imprecise in a way that matters.

A closure is formed when a function retains a reference to variables in its outer (enclosing) scope after that outer scope has finished executing. The classic definition: a function plus the environment in which it was created.

An IIFE that runs and returns a primitive value — or nothing at all — does not create a persistent closure. Its execution context is pushed onto the call stack, runs to completion, and pops. The variables declared inside go out of scope and become eligible for garbage collection. There is no function left behind that holds a reference to the IIFE's scope. This is why IIFEs are described as creating a "temporary scope" — for code that just needs isolation, the scope is created and immediately discarded.

An IIFE creates a closure only when it returns a function or an object containing functions that reference its internal variables. In the module pattern:

```js
const Cart = (function() {
  let _items = [];              // lives in IIFE scope
  return {
    add: (item) => _items.push(item),   // closure over _items
    total: () => _items.length          // closure over _items
  };
})();
```

The returned `add` and `total` functions close over `_items`. Those functions hold a reference to the IIFE's scope, which keeps `_items` alive in memory for as long as `Cart` exists. That is a genuine closure. The IIFE was merely the delivery mechanism — the scope it created happens to be kept alive because something escaped it.

The cleanest test: after the IIFE finishes, is there any function anywhere that still references a variable from inside it? If yes, that variable is in a closure and the scope is live. If no, the IIFE's scope is garbage-collected and there is no closure.

## Why It's a Trap

Candidates conflate "function scope" with "closure." An IIFE always creates a scope, but only creates a persistent closure when a returned function captures variables from that scope.

## What NOT to Say

"Every IIFE is a closure because it's a function." This confuses scope creation with closure formation. Scope is created every time any function is called; closure requires that an inner function outlive the outer scope and retains a reference to it.

## Follow-up

**Q:** If an IIFE returns only a plain object with no methods — `return { version: '1.0.0', name: 'SDK' }` — is there a closure?

**A:** No. A plain data object holds no function references, so no function captures the IIFE's scope. The returned object is just a value copied out of the IIFE. The internal variables (if any) that were used to compute those values become unreachable after the IIFE returns, and the garbage collector can reclaim them. Closures require a function in the returned value (or registered as a callback) that references the enclosing scope's variables — a data object alone does not qualify.
