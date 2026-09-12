# Callback Hell — Recognize and Refactor
> **Topic:** Higher-Order Functions | **Level:** Intermediate | **Frequency:** High

## The Setup
You are reviewing a three-year-old Swiggy backend service that chains user lookup, order fetch, payment validation, and invoice send — all in nested callbacks. The team wants to understand why it is hard to maintain before migrating.

## The Question
Diagram the pyramid of doom, name every problem, and show the migration path.

## Diagram

```
CALLBACK HELL — the pyramid of doom:

loadUser(id, (err, user) => {
  if (err) return handle(err);
  loadOrders(user.id, (err, orders) => {       // indent level 2
    if (err) return handle(err);
    validatePayment(orders[0], (err, payment) => {    // indent level 3
      if (err) return handle(err);
      sendInvoice(payment, (err, result) => {         // indent level 4
        if (err) return handle(err);
        notifyUser(user, result, (err) => {           // indent level 5
          if (err) return handle(err);
          console.log('done');                        // indent level 6
        });
      });
    });
  });
});

PROBLEMS:
  1. Error handling: duplicated at every level (5x `if (err)`)
  2. Readability: real logic buried at indent level 5+
  3. Testing: cannot test step 3 without running steps 1-2
  4. Parallelism: steps run sequentially even when independent
  5. Control flow: early returns, breaks, try/catch — all broken inside callbacks
  6. Stack traces: async callbacks lose their original call site
```

## Model Answer (15 YOE)

The pyramid of doom is not an aesthetic problem — it is a structural one. Each async step creates a new closure scope, so variable scoping becomes tangled, error handling cannot be centralized, and you cannot use `try/catch` across async boundaries. The migration path has three stages:

```js
// Stage 1 — Promisify each callback-based function (one-time work)
const loadUser      = id      => new Promise((res, rej) => _loadUser(id, (e, d) => e ? rej(e) : res(d)));
const loadOrders    = userId  => new Promise((res, rej) => _loadOrders(userId, (e, d) => e ? rej(e) : res(d)));
const validatePay   = order   => new Promise((res, rej) => _validatePayment(order, (e, d) => e ? rej(e) : res(d)));
const sendInvoice   = payment => new Promise((res, rej) => _sendInvoice(payment, (e, d) => e ? rej(e) : res(d)));
const notifyUser    = (u, r)  => new Promise((res, rej) => _notifyUser(u, r, e => e ? rej(e) : res()));

// Stage 2 — async/await: flat, readable, one try/catch for all
async function processOrder(userId) {
  try {
    const user    = await loadUser(userId);
    const orders  = await loadOrders(user.id);
    const payment = await validatePay(orders[0]);
    const result  = await sendInvoice(payment);
    await notifyUser(user, result);
  } catch (err) {
    logger.error({ userId, err }, 'Order processing failed');
    throw err;
  }
}

// Stage 3 — parallelize independent steps
async function processOrder(userId) {
  const user   = await loadUser(userId);
  // loadOrders and fetchUserPreferences are independent — run in parallel
  const [orders, prefs] = await Promise.all([loadOrders(user.id), fetchUserPreferences(user.id)]);
  // ...rest of pipeline
}
```

The callbacks still exist under the hood (Promises are built on microtasks, which are callbacks), but the pyramid is eliminated. One try/catch handles all five failure modes. The code reads top-to-bottom, matching the mental model of the flow.

## Follow-up

**Q:** When is it acceptable to keep callback style instead of migrating to Promises?

**A:** Three cases: event listeners (`addEventListener`) — they fire multiple times, Promises resolve once; Node.js streams — the `data`/`end`/`error` event model is not naturally Promise-shaped; and performance-critical tight loops where Promise overhead (microtask allocation) matters. For everything else — DB calls, HTTP requests, file I/O — Promises plus async/await are the right model.
