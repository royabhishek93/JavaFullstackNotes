# Module Pattern — Encapsulated State Without a Class
> **Topic:** IIFE | **Level:** Intermediate | **Frequency:** Medium

## The Setup

You are reviewing code in a legacy Angular 1.x application that your team must maintain while incrementally migrating it to React. The team asks you to explain a `CartService` that uses neither a class nor a plain object, but instead an IIFE that returns an object. They want to know if it is safe to refactor.

## The Question

Walk through the IIFE module pattern, explain how it achieves encapsulation, and compare it to what a modern ES class with private fields does differently.

## Diagram

```
┌───────────────────────────────────────────────────────────────┐
│              IIFE MODULE PATTERN vs ES CLASS                  │
│                                                               │
│  IIFE Module Pattern:                                         │
│  ┌─────────────────────────────────────────────────────┐      │
│  │  const CartService = (function() {                  │      │
│  │    let _items = [];          ← truly private        │      │
│  │    let _discount = 0;        ← no syntax marker     │      │
│  │                                                     │      │
│  │    return {                  ← public API only      │      │
│  │      addItem,                                       │      │
│  │      applyDiscount,                                 │      │
│  │      getTotal                                       │      │
│  │    };                                               │      │
│  │  })();                                              │      │
│  │                                                     │      │
│  │  CartService._items   → undefined                   │      │
│  │  CartService._discount → undefined                  │      │
│  └─────────────────────────────────────────────────────┘      │
│                                                               │
│  ES Class with Private Fields (ES2022):                       │
│  ┌─────────────────────────────────────────────────────┐      │
│  │  class CartService {                                │      │
│  │    #items = [];              ← engine-enforced      │      │
│  │    #discount = 0;            ← # syntax marker      │      │
│  │                                                     │      │
│  │    addItem(i) { this.#items.push(i); }              │      │
│  │    getTotal() { ... }                               │      │
│  │  }                                                  │      │
│  │                                                     │      │
│  │  new CartService().#items → SyntaxError             │      │
│  └─────────────────────────────────────────────────────┘      │
│                                                               │
│  Key difference: IIFE = one singleton instance                │
│                  Class = instantiated as needed               │
└───────────────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

The IIFE module pattern achieves encapsulation through closure, not language-level access control. The private variables `_items` and `_discount` exist in the IIFE's function scope. The returned object's methods are closures that close over those variables — they can read and write them. External code cannot, because external code has no reference to that scope. The variables are private by inaccessibility, not by enforcement.

This is subtly different from ES2022 private class fields, which use the `#` prefix and are enforced by the engine. You literally cannot write `instance.#items` from outside the class definition — it is a SyntaxError, not just `undefined`. The IIFE pattern gives you the same practical result, but through scope rather than specification.

For the refactoring question: the key risk is that the IIFE pattern produces a singleton. `CartService` is a single object. A class produces a constructor you can instantiate: `new CartService()`. If the Angular 1.x code treats the service as a singleton — which Angular 1 services are, by design — the behavior is equivalent. If the refactor creates a class but forgets to reason about instantiation (for example, accidentally creating two instances in different React components), the cart state will no longer be shared, which is a regression.

My recommendation: if the module will remain a singleton, the IIFE pattern is fine to keep, and refactoring it is low-value churn. If you need multiple independent instances, migrate to a class. If you need React-specific state management, migrate to a Context with a reducer. Each of those is a different refactoring with a different scope and different risk.

## Follow-up

**Q:** The IIFE module pattern uses closure-based privacy. Can you break into it from the browser console in production?

**A:** Not through normal JavaScript — the closure scope is inaccessible. However, if the private function is ever inadvertently exported (via `window.debug = { _items }` or similar), or if the application was built with source maps exposed in production, a developer with console access could potentially read state through indirect means. More practically, the bigger concern is that closure-based privacy provides no compile-time or linting enforcement. A developer adding a method to the returned object could accidentally capture a reference to the private state and expose it. The `#` private field syntax gives you static analysis, editor warnings, and runtime enforcement — three layers the IIFE pattern does not have. For security-critical code, the class private field is the stronger choice.
