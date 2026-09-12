# Implement EventEmitter with on / off / emit / once
> **Topic:** Event Emitter | **Level:** Fundamental | **Frequency:** High

## The Setup
The canonical hard JavaScript interview question. Asked at every senior front-end and full-stack interview. The interviewer wants to test whether you understand the Observer pattern, closures, reference equality, and defensive array mutation handling — all in one implementation.

## The Question
Implement an `EventEmitter` class from scratch with the following API:
- `on(event, listener)` — subscribe
- `off(event, listener)` — unsubscribe
- `emit(event, ...args)` — notify all listeners
- `once(event, listener)` — subscribe for exactly one emission

All methods should return `this` for fluent chaining.

## Diagram

```
INTERNAL STATE
──────────────
                  ┌─────────────────────────────────────────────┐
                  │  listeners: Map<string, Function[]>          │
                  │                                             │
                  │  "login"   → [ fn1, fn2, fn3 ]             │
                  │  "payment" → [ fn4 ]                        │
                  │  "logout"  → [ fn5, fn6 ]                   │
                  └─────────────────────────────────────────────┘
                                    ▲    │
  ┌── on("login", fn3) ─────────────┘    │
  │   off("login", fn2) ──────────────► removes fn2 from array
  └── emit("login", data) ───────────────┴──► calls fn1(data), fn3(data)

ONCE WRAPPER MECHANISM
──────────────────────
  once("payment", originalFn)
       │
       ▼
  wrapper = (...args) => {
    originalFn(...args);       // ① call the real listener
    off("payment", wrapper);   // ② self-remove (wrapper knows its own ref)
  }
  on("payment", wrapper)   ← wrapper stored, NOT originalFn
```

## Model Answer (15 YOE)

```js
class EventEmitter {
  constructor() {
    this.listeners = new Map(); // Map<string, Function[]>
  }

  on(event, listener) {
    if (!this.listeners.has(event)) this.listeners.set(event, []);
    this.listeners.get(event).push(listener);
    return this; // fluent chaining
  }

  off(event, listener) {
    if (!this.listeners.has(event)) return this;
    const updated = this.listeners.get(event).filter(fn => fn !== listener);
    this.listeners.set(event, updated);
    return this;
  }

  emit(event, ...args) {
    if (!this.listeners.has(event)) return this;
    // Snapshot the array — a listener calling off() during emit
    // must not affect this current iteration
    [...this.listeners.get(event)].forEach(fn => fn(...args));
    return this;
  }

  once(event, listener) {
    const wrapper = (...args) => {
      listener(...args);
      this.off(event, wrapper); // self-remove via closure over `wrapper`
    };
    this.on(event, wrapper);
    return this;
  }
}
```

**Design decisions worth articulating:**

1. **`Map` over plain object** — A plain object risks collision with inherited properties like `constructor`, `toString`, `hasOwnProperty`. `Map` has O(1) has/get/set with no prototype chain interference.

2. **Array snapshot in `emit`** — `[...this.listeners.get(event)].forEach(...)` spreads the array before iterating. If a listener calls `off()` during emit, it mutates `this.listeners.get(event)` — but the snapshot is unaffected. Without the spread, mid-emit removal causes index skipping.

3. **`once` stores the wrapper, not the original** — The wrapper is a new function that calls the original and then self-removes. `this.listeners` contains `[wrapper]`, not `[listener]`. This is the most-tested senior trap on this topic.

4. **Return `this`** — All mutating methods return `this`, enabling `.on('a', fn1).on('b', fn2).on('c', fn3)` chains.

## Follow-up

**Q:** What happens if `emit` is called for an event with no listeners?
**A:** The early-return guard `if (!this.listeners.has(event)) return this` handles it safely — no error, no empty array iteration. This is important for event-driven systems where emitters fire regardless of whether anyone is listening.

**Q:** How would you add error isolation so one throwing listener does not stop the rest?
**A:** Wrap each `fn(...args)` call in a `try/catch` inside the `forEach`. For async listeners, check `if (result instanceof Promise) result.catch(err => console.error(...))`. This is critical in payment/order pipelines where one non-critical listener (analytics) must not block critical listeners (notifications, ledger writes).
