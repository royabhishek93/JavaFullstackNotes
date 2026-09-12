# `setTimeout` in a React Component — Stale `this`
> **Topic:** Arrow Functions | **Level:** Intermediate | **Frequency:** High

## The Setup

You are debugging a live-tracking feature on a logistics dashboard. A React class component polls a GPS endpoint every 5 seconds using `setTimeout`. Engineers report that after the first interval fires, the map stops updating. The console shows `TypeError: this.setState is not a function`.

## The Question

The timer callback is a regular function. Explain exactly why `this.setState` fails inside it, and walk through the two historical approaches engineers used before class fields became standard.

## Diagram

```
┌──────────────────────────────────────────────────────┐
│           SETTIMEOUT this TRAP                       │
│                                                      │
│  componentDidMount() {       ← this = component ✓   │
│    setTimeout(function() {   ← NEW this context      │
│      this.setState(...)      ← this = window/undef ✗ │
│    }, 5000)                                          │
│  }                                                   │
│                                                      │
│  WHY: setTimeout calls callback from the event loop  │
│  with no receiver object → this = global/undefined   │
│                                                      │
│  ┌──────── Fix 1: capture self ──────────────────┐   │
│  │ const self = this;                            │   │
│  │ setTimeout(function() {                       │   │
│  │   self.setState(...)  ← closure variable ✓   │   │
│  │ }, 5000)                                      │   │
│  └───────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────── Fix 2: arrow function ────────────────┐   │
│  │ setTimeout(() => {                            │   │
│  │   this.setState(...)  ← lexical this ✓        │   │
│  │ }, 5000)                                      │   │
│  └───────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

`setTimeout` hands the callback to the browser's timer API. When the timer fires, the event loop calls the function with no object as the receiver — it is a plain function call. In non-strict mode `this` becomes `window`; in strict mode it becomes `undefined`. Either way, `this.setState` is not there.

The pre-ES6 idiom was `var self = this` — capture `this` into a regular variable before entering the callback, then use `self` inside. It works because closures capture variables, not bindings. You see this in pre-2015 jQuery code, AngularJS 1.x controllers, and basically any codebase older than seven years.

The ES6 fix is to replace the regular function with an arrow function. Arrow functions have no `this` binding of their own, so the engine looks up the scope chain and finds the `this` from `componentDidMount`, which is the component instance. Clean and idiomatic.

In a modern codebase I would actually use the class field form: declare the poll callback as `pollGPS = async () => { ... }` and pass `this.pollGPS` to `setTimeout`. This makes the callback independently testable, gives it a name that appears in stack traces, and removes it from the tangle of method body code. It also makes cleanup easier in `componentWillUnmount` because you have a stable reference to pass to `clearTimeout`.

## Follow-up

**Q:** Does `setInterval` have the same problem?

**A:** Identical problem, identical fix. `setInterval` follows the same calling convention as `setTimeout` — the callback is invoked by the event loop with no receiver. Arrow function or captured `self` both work. The additional concern with `setInterval` in React is cleanup: store the interval ID in `this.intervalId` and call `clearInterval(this.intervalId)` in `componentWillUnmount`. Missing that cleanup is a memory and state leak that is very hard to reproduce in unit tests but shows up as ghost setState calls on unmounted components in production.
