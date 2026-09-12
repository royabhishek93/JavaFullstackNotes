# Unhandled Rejection Crashing the Node.js Process
> **Topic:** Promises | **Level:** Intermediate | **Frequency:** High

## The Setup

Your Express service is crashing overnight with `UnhandledPromiseRejectionWarning`. The crashes are intermittent. No `try/catch` is visible in the code around the offending function.

## The Question

A senior on your team says "we have an unhandled Promise rejection somewhere." Where are the common places this hides, and how do you find and fix it?

## Diagram

```
  async function sendEmail(user) {            // async fn returns a Promise
    await mailer.send(user.email, ...);       // if this rejects...
  }

  // Caller 1 — SAFE
  app.post('/register', async (req, res) => {
    try { await sendEmail(req.body); }
    catch (e) { res.status(500).send(); }
  });

  // Caller 2 — DANGEROUS (fire-and-forget, no .catch)
  sendEmail(newUser);   // <-- Promise created, rejection has no handler
                        //     Node.js 15+ terminates the process
```

## Model Answer (15 YOE)

Unhandled rejections come from two patterns.

**Pattern 1 — fire-and-forget calls:** `sendEmail(user)` with no `.catch()` and no `await` inside a `try/catch`. The rejection goes nowhere. The function was called and its Promise was discarded. When it rejects, Node has no handler for it.

**Pattern 2 — the forgotten return in `.then()` chains:** A `.then()` callback that calls an async function but does not return the resulting Promise. The inner Promise's rejection escapes the chain entirely.

```js
// Pitfall — rejection on the inner fetch is NOT caught by the outer .catch
fetch('/api/orders')
  .then(res => {
    fetch('/api/details/' + res.id);  // <-- missing return
  })
  .catch(err => console.error(err));  // only catches the outer fetch

// Fixed
fetch('/api/orders')
  .then(res => fetch('/api/details/' + res.id))  // return the inner Promise
  .catch(err => console.error(err));
```

**Diagnostic approach:** add a global listener during development to log the stack trace:

```js
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // optionally: process.exit(1);
});
```

In production, use a proper APM (Datadog, Sentry) that captures async stack traces. Then audit all async function calls that are neither awaited nor `.catch()`-ed.

For intentional fire-and-forget cases (background jobs), be explicit:

```js
sendEmail(user).catch(err => logger.error('email failed', err));
```

## Follow-up

**Q:** How does Node.js 15+ handle unhandled rejections differently from Node 14?

**A:** Node.js 14 emitted a warning but kept running. From Node.js 15 onward, an unhandled rejection crashes the process by default — the same behavior as an uncaught synchronous exception. This was the right call: silently swallowing errors is worse than crashing loudly. In practice it means legacy code that relied on the "just a warning" behavior in Node 14 started crashing on upgrade to 15, which is exactly the kind of breakage that forces teams to fix their error handling.
