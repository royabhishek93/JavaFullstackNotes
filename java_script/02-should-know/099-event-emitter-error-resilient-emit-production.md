# Error-Resilient Emit in Production
> **Topic:** Event Emitter | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A payments platform uses an event bus to fan out `payment.processed` to 6 listeners: receipt email, SMS, ledger writer, fraud flag update, loyalty points, and analytics tracker. During a traffic spike, the analytics service throws an unhandled promise rejection. Without error isolation, the remaining five listeners — including the receipt email and ledger writer — never execute. Customer support receives calls about missing receipts.

## The Question
How do you make an EventEmitter's `emit()` resilient so that one failing listener does not prevent the rest from running? Handle both synchronous throws and async listener failures.

## Diagram

```
NAIVE emit — one failure stops the rest:
  emit('payment.processed', data)
    ├── receiptService(data)    ✓ runs
    ├── smsService(data)        ✓ runs
    ├── analyticsService(data)  ✗ THROWS → exception propagates up
    ├── ledgerService(data)     ✗ NEVER RUNS ← data integrity issue
    ├── loyaltyService(data)    ✗ NEVER RUNS
    └── fraudService(data)      ✗ NEVER RUNS

RESILIENT emit — each listener isolated:
  emit('payment.processed', data)
    ├── receiptService(data)    ✓ runs
    ├── smsService(data)        ✓ runs
    ├── analyticsService(data)  ✗ throws → caught, logged, CONTINUES
    ├── ledgerService(data)     ✓ runs
    ├── loyaltyService(data)    ✓ runs
    └── fraudService(data)      ✓ runs
```

## Model Answer (15 YOE)

```js
emit(event, ...args) {
  if (!this.listeners.has(event)) return this;

  const fns = [...this.listeners.get(event)]; // snapshot

  for (const fn of fns) {
    try {
      const result = fn(...args);

      // Catch async listener failures without blocking the loop
      if (result instanceof Promise) {
        result.catch(err =>
          console.error(`[EventEmitter] Async listener error on "${event}":`, err)
        );
      }
    } catch (err) {
      // Catch sync listener failures — log and continue to next listener
      console.error(`[EventEmitter] Sync listener error on "${event}":`, err);
    }
  }

  return this;
}
```

**Why the `instanceof Promise` check matters:**

An async function `async (data) => { ... }` always returns a Promise. If the async function throws, the Promise is rejected — but a synchronous `try/catch` around the function call catches the returned Promise object, not the rejection. The `try/catch` block sees the function return successfully (with a rejected Promise). Without the `instanceof Promise` check and the `.catch()`, async listener errors are completely silent — unhandled promise rejections in Node.js crash the process (or emit warnings).

**The `'error'` event contract (Node.js compatibility):**

Node.js EventEmitter has a special contract: if you `emit('error', err)` and no listener is registered for `'error'`, Node.js throws the error as an uncaught exception and crashes the process. Production EventEmitter wrappers should replicate this:

```js
emit(event, ...args) {
  if (event === 'error' && !this.listeners.has('error')) {
    const err = args[0] instanceof Error ? args[0] : new Error(String(args[0]));
    throw err; // replicate Node.js contract
  }
  // ... rest of resilient emit
}
```

**Telemetry in production:**

Replace `console.error` with your observability stack:

```js
catch (err) {
  observability.captureException(err, {
    tags: { event, listenerName: fn.name || 'anonymous' }
  });
}
```

`fn.name` is the function's name property — useful for identifying which listener failed in logs.

## Follow-up

**Q:** Should `emit` log errors or re-throw them? How do you decide?
**A:** For a fan-out bus (one event → many listeners), log and continue. The emitter does not know which listeners are critical — the caller cannot meaningfully handle "listener 3 of 6 failed." For a pipeline where order matters and failures should halt execution, do not use an event bus — use a sequential async chain with `try/catch` at the pipeline level.

**Q:** The analytics service's async failure is logged but the promise rejection is unhandled from the analytics service's perspective. Is there a better pattern?
**A:** The `.catch()` in the emitter handles the rejection from the emitter's perspective. The analytics service itself should handle its own errors internally — wrap its async logic in `try/catch` and report to its own error boundary. The emitter's `.catch()` is a last-resort guard for listeners that fail to handle their own errors. Defense in depth: fix in the listener first, guard in the emitter as a backstop.
