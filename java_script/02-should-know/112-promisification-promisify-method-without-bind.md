# Promisifying a Method Without .bind — The this Context Trap
> **Topic:** Promisification | **Level:** Senior Trap | **Frequency:** High

## The Setup

A developer promisifies a database client method and immediately gets a runtime error in production: "Cannot read properties of undefined (reading 'connection')".

```js
const { promisify } = require('util');
const client = db.createClient(process.env.DB_URL);

// Developer writes:
const query = promisify(client.query);

// At call time:
const rows = await query('SELECT * FROM users');
// TypeError: Cannot read properties of undefined (reading 'connection')
```

## The Question

Why does this fail, and how do you fix it?

## Diagram

```
  What promisify does internally:
  function promisifyWrapper(...args) {
    return new Promise((resolve, reject) => {
      fn.apply(this, [...args, callback]);
      //       ^
      //  'this' is the context of the WRAPPER call,
      //  not 'client' — it is undefined in strict mode
    });
  }

  client.query extracted from client:
    const query = client.query;    // method detached from its object
    query('SELECT...')             // 'this' inside query = undefined (strict mode)
                                   //                     = global (sloppy mode)
    client.query is never referenced — this.connection throws

  Fix: bind before extracting
    const query = promisify(client.query.bind(client));
    //                                   ^^^^^^^^^^^
    //                           permanently ties 'this' to client
```

## Model Answer (15 YOE)

When you write `promisify(client.query)`, the `query` method is extracted from the `client` object and passed as a plain function reference. The connection between the method and its object is broken. When `util.promisify` later calls it via `fn.apply(this, args)`, `this` is the wrapper function's context — not `client`. Since `client.query` internally references `this.connection`, `this.pool`, or similar, it throws "Cannot read properties of undefined."

The fix is to bind the method to its instance before passing it to `promisify`:

```js
const { promisify } = require('util');
const client = db.createClient(process.env.DB_URL);

// WRONG — this context lost
const query = promisify(client.query);

// CORRECT — bind first
const query = promisify(client.query.bind(client));

// Usage — works correctly
const rows = await query('SELECT * FROM users WHERE id = $1', [userId]);
```

The `.bind(client)` call returns a new function that permanently has `this = client`, regardless of how or where it is called. `util.promisify` wraps the bound function, so when the wrapper invokes `fn.apply(this, args)`, `this` inside `client.query` is always the client instance.

A common pattern for adapter modules:

```js
// adapters/db.js
const { promisify } = require('util');
const driver = require('legacy-db-driver');
const client = driver.createClient(process.env.DB_URL);

module.exports = {
  query:      promisify(client.query.bind(client)),
  connect:    promisify(client.connect.bind(client)),
  disconnect: promisify(client.disconnect.bind(client)),
};
```

## Follow-up

**Q:** Is there a way to avoid `.bind()` altogether?

**A:** Yes — use an arrow function wrapper: `promisify((...args) => client.query(...args))`. Arrow functions capture `this` lexically at definition time, so `client` is always in scope via closure. However, `.bind(client)` is the idiomatic, more explicit convention for this pattern.

## Why It's a Trap

JavaScript's `this` context is one of the most consistently misunderstood parts of the language. The bug is invisible at wrap time (the `promisify` call succeeds) and only surfaces at call time when the method tries to access instance properties. In a test environment with mocked methods that do not use `this`, the bug may not surface at all — making it a production-only failure.

## What NOT to Say

- "`util.promisify` automatically preserves `this`." — It preserves the wrapper's `this` via `fn.apply(this, args)`, but if the method was detached from its object, the wrapper's `this` is not the client instance.
- "This is a bug in `util.promisify`." — It is the correct behavior of JavaScript's `this` binding. `.bind()` is the developer's responsibility.
- "Just use `client.query.call(client, ...)` each time." — Tedious and error-prone. Bind once at the promisification site.
