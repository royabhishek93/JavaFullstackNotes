# React Class Component — Broken Event Handler in Production
> **Topic:** Arrow Functions | **Level:** Fundamental | **Frequency:** High

## The Setup

You are a senior engineer at a fintech startup. A junior dev ships a React class component for a payment form. In the browser, clicking "Submit" throws `TypeError: Cannot read properties of undefined (reading 'setState')`. The component works fine in isolation tests but crashes in production.

## The Question

The junior says "I wrote `handleSubmit` as a regular method on the class — why is `this` undefined?" Walk me through what is happening and how you would fix it without changing to a functional component.

## Diagram

```
┌──────────────────────────────────────────────────────┐
│              CLASS METHOD this PROBLEM               │
│                                                      │
│  class PaymentForm extends React.Component {         │
│    handleSubmit() {          ← regular fn            │
│      this.setState(...)      ← this = ???            │
│    }                                                 │
│                                                      │
│    render() {                                        │
│      return <button                                  │
│        onClick={this.handleSubmit}  ← DETACHED       │
│      />                                              │
│    }                                                 │
│  }                                                   │
│                                                      │
│  When React fires onClick:                           │
│  ┌─────────────────────────────────┐                 │
│  │ handler = this.handleSubmit     │                 │
│  │ handler()  ← called standalone  │                 │
│  │ this = undefined (strict mode)  │                 │
│  └─────────────────────────────────┘                 │
│                                                      │
│  Fix: Arrow function as class field                  │
│  handleSubmit = () => { this.setState(...) }         │
│  this = always the component instance        ✓       │
└──────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

This is a classic detachment bug. When you write `onClick={this.handleSubmit}`, you are not calling the method — you are passing a reference to it. React stores that reference and later calls it as a plain function, not as `obj.method()`. At that point the method has lost its receiver. In strict mode (which React uses by default via JSX transforms), `this` becomes `undefined` rather than `window`, so any attempt to call `this.setState` throws.

I have seen three fixes in production codebases, and they have different trade-offs.

The constructor bind approach — `this.handleSubmit = this.handleSubmit.bind(this)` — is explicit but creates boilerplate for every handler, and engineers forget it constantly.

The inline bind on JSX — `onClick={() => this.handleSubmit()}` — works but creates a new function on every render, which matters when the button is inside a list or a `React.memo` child.

The right answer for a class component is the class field arrow function: `handleSubmit = () => { this.setState(...) }`. This is transpiled by Babel to an assignment in the constructor, so `this` is the instance at creation time and it never changes. No bind boilerplate, no per-render allocation.

The deeper principle is that arrow functions do not create their own `this`, so there is nothing to lose when you detach them. That is why they are the canonical pattern for class method handlers.

## Follow-up

**Q:** If arrow class fields are so good, why would you ever write a regular method on a class?

**A:** Prototype methods are shared across all instances — one function object in memory. Arrow class fields are instance properties — every `new PaymentForm()` gets its own function object. For most UI components the difference is negligible, but if you are constructing thousands of instances (say, a grid with virtualized rows each being a class instance) the memory cost of per-instance arrow functions adds up. Regular prototype methods also work correctly with `super`, while arrow fields do not inherit from the prototype chain in the same way. For event handlers in typical React components, class fields are fine. For heavily instantiated model objects, prefer prototype methods and bind explicitly.
