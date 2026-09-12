# Node.js Express — `this` Lost in a Service Method
> **Topic:** Arrow Functions | **Level:** Intermediate | **Frequency:** High

## The Setup

You are reviewing a PR for a Node.js REST API. A service class method is passed as a route handler directly. Integration tests pass locally, but in staging the handler crashes on every request with `TypeError: Cannot read properties of undefined`.

## The Question

The code reads `router.get('/orders', orderService.getOrders)`. The `getOrders` method calls `this.db.findAll()`. Why does it break and what is the right architectural fix?

## Diagram

```
┌─────────────────────────────────────────────────────┐
│          SERVICE METHOD DETACHMENT                  │
│                                                     │
│  class OrderService {                               │
│    constructor(db) { this.db = db; }                │
│    getOrders(req, res) {                             │
│      this.db.findAll()  ← this = undefined!         │
│    }                                                │
│  }                                                  │
│                                                     │
│  router.get('/orders', orderService.getOrders)      │
│                         ─────────────────────       │
│                         detached reference          │
│                                                     │
│  Three fixes:                                       │
│  ┌──────────────────────────────────────────────┐   │
│  │ 1. Wrapper arrow:                            │   │
│  │    router.get('/orders',                     │   │
│  │      (req,res) => orderService.getOrders(    │   │
│  │        req, res))                            │   │
│  │                                              │   │
│  │ 2. Bind in constructor:                      │   │
│  │    this.getOrders = this.getOrders.bind(this)│   │
│  │                                              │   │
│  │ 3. Arrow class field (cleanest):             │   │
│  │    getOrders = async (req, res) => { ... }   │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

The same detachment problem as in React, just in a different runtime. Express calls the handler as a plain callback — `handler(req, res, next)` — so `this` is lost. The method cannot reach `this.db`.

In production Node.js codebases I have maintained, there are three patterns I have seen work well. The wrapper arrow lambda on the router line is quick and obvious, but it adds noise at every route registration. Constructor bind centralises the fix but requires remembering to bind every method you intend to export.

The architectural fix I now reach for first is to convert service methods that will be used as callbacks into arrow class fields. It is self-contained — the method carries its binding with it, independent of how it is invoked. This matters especially when the same method is used in multiple places: as an Express handler, as an event listener, and as a promise callback.

One thing I flag in code review: if the team is using TypeScript, arrow class fields play well with strict mode and interface conformance. The prototype-based approach requires careful typing around `this` parameter signatures. So from a type-safety perspective, the arrow field is usually the right call for service methods intended to be used as callbacks.

## Follow-up

**Q:** Can you use `async/await` with arrow class fields?

**A:** Yes, the `async` keyword composes cleanly: `getOrders = async (req, res) => { const orders = await this.db.findAll(); res.json(orders); }`. The resulting function is an async function that returns a Promise, `this` is bound correctly, and it can be passed anywhere as a callback without losing context. Just make sure Express error handling is wired correctly — unhandled promise rejections from async handlers need either a try-catch inside or a wrapper like `express-async-errors`.
