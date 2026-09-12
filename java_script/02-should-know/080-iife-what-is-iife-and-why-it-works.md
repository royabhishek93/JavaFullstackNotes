# What Is an IIFE and Why Does It Work?
> **Topic:** IIFE | **Level:** Fundamental | **Frequency:** High

## The Setup

You are reviewing a codebase and encounter this at the top of a file:

```js
(function() {
  var secret = 42;
  window.API = {
    getValue: function() { return secret; }
  };
})();
```

A junior engineer asks what this pattern is, why the extra parentheses are needed around `function`, and why this was ever necessary.

## The Question

What is an IIFE? Why does wrapping a function in parentheses allow it to be called immediately? What problem does it solve that a plain function declaration cannot?

## Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    IIFE EXECUTION MODEL                         │
│                                                                 │
│   (function() {           ← parser sees function EXPRESSION     │
│     let secret = 42;      ← local scope, unreachable outside    │
│     window.API = {        ← explicit export to outer scope      │
│       getValue: () => secret                                    │
│     };                                                          │
│   })();                   ← called immediately                  │
│    ▲                                                            │
│    └── trailing () = invocation                                 │
│                                                                 │
│   After execution:                                              │
│   ┌──────────────────┐    ┌──────────────────────────────┐      │
│   │  IIFE scope      │    │  outer / global scope        │      │
│   │  secret = 42     │    │  API = { getValue: fn }      │      │
│   │  (GC eligible)   │    │  secret = NOT HERE           │      │
│   └──────────────────┘    └──────────────────────────────┘      │
│                                                                 │
│   Module Pattern (closure keeps scope alive):                   │
│   ┌────────────────────────────────────────────────────┐        │
│   │  const Cart = (function() {                        │        │
│   │    let items = [];          ← closure variable     │        │
│   │    return {                 ← returned object       │        │
│   │      add: (i) => items.push(i),                    │        │
│   │      total: () => items.length                     │        │
│   │    };                                              │        │
│   │  })();                                             │        │
│   │                                                    │        │
│   │  items is unreachable but ALIVE in closure         │        │
│   └────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

IIFE stands for Immediately Invoked Function Expression. It is a function expression that is invoked the moment it is defined. The name describes the mechanic precisely.

The outer parentheses are necessary because of how the JavaScript parser works. When the parser sees the `function` keyword at the start of a statement, it expects a function declaration — which requires a name and cannot be immediately invoked with `()`. By wrapping the function in parentheses, you force the parser into expression mode. In expression mode, `function() {}` is a function expression, which can be called immediately by appending `()`.

The key consequence is scope isolation. Every variable declared with `var`, `let`, or `const` inside the IIFE lives in that function's scope and is unreachable from outside — unless the IIFE deliberately returns it. Before ES modules gave every file its own scope, the IIFE was the only reliable way to create a private namespace in the browser. Any variable not explicitly exported via `window.X = ...` or a return value simply never exists outside the IIFE.

This made it the backbone of pre-2015 library architecture. jQuery, Lodash, Moment.js, Google Analytics — all wrapped their internals in IIFEs. The pattern is not dead either: every Webpack bundle you ship today wraps application code in an IIFE for the same reason.

## Follow-up

**Q:** What happens to variables declared inside an IIFE after it finishes executing?

**A:** If nothing returned from the IIFE holds a reference to them, they become unreachable and are eligible for garbage collection — same as any local variable after a function returns. However, if the IIFE returns a function or object whose methods reference the internal variables (a closure), the engine must keep those variables alive in memory because the returned functions still need them. This is the foundation of the IIFE module pattern: the returned public API methods hold references to the private variables, so the private scope stays alive for the lifetime of the returned object.
