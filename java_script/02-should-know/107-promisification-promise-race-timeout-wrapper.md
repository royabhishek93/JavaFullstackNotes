# Promise.race Timeout Wrapper and Timer Leak
> **Topic:** Promisification | **Level:** Intermediate | **Frequency:** Medium

## The Setup

Your Node.js microservice calls an upstream inventory API. Sometimes the upstream hangs for 30+ seconds, holding your Express worker threads. You want all upstream calls to time out after 3 seconds and return a graceful error.

## The Question

Implement a reusable timeout wrapper. How does `Promise.race` enable this, and what are the edge cases?

## Diagram

```
  Promise.race semantics:
  ┌──────────────────────────────────────────────────┐
  │  Promise.race([fetchInventory(sku), timeoutIn(3s)]) │
  │                                                  │
  │  t=0ms    [fetch starts]  [timeout starts]       │
  │  t=2.8s                   [timeout rejects]  <-- wins
  │  t=4.1s   [fetch resolves]                   (ignored)
  │                                                  │
  │  Result: rejects with TimeoutError at t=2.8s     │
  └──────────────────────────────────────────────────┘

  Edge case: slow request is not actually cancelled.
  The fetch continues running after race() resolves.
  AbortController is required to cancel it at the network level.
```

## Model Answer (15 YOE)

```js
function withTimeout(promise, ms, label = 'operation') {
  let timeoutId;
  const timeout = new Promise((_, reject) => {
    timeoutId = setTimeout(
      () => reject(new Error(`${label} timed out after ${ms}ms`)),
      ms
    );
  });

  return Promise.race([promise, timeout])
    .finally(() => clearTimeout(timeoutId));  // prevent timer leak
}
```

Usage in an Express route handler:

```js
app.get('/inventory/:sku', async (req, res) => {
  try {
    const inventory = await withTimeout(
      fetchInventory(req.params.sku),
      3000,
      'inventory fetch'
    );
    res.json(inventory);
  } catch (err) {
    if (err.message.includes('timed out')) {
      res.status(504).json({ error: 'Upstream inventory service unavailable' });
    } else {
      res.status(500).json({ error: 'Internal error' });
    }
  }
});
```

Three edge cases worth knowing:

**1. The `.finally(() => clearTimeout(timeoutId))` is mandatory.** Without it, the timer keeps running even after the Promise settles. In a long-lived process this leaks memory and triggers Jest "open handle" warnings in tests.

**2. `Promise.race` does not cancel the losing Promise.** `fetchInventory` continues running in the background even after the timeout rejects. To actually cancel the network request at the OS level, pass an `AbortController` signal:

```js
app.get('/inventory/:sku', async (req, res) => {
  const controller = new AbortController();
  const timeoutId  = setTimeout(() => controller.abort(), 3000);

  try {
    const res2 = await fetch(`/upstream/inventory/${req.params.sku}`, {
      signal: controller.signal
    });
    res.json(await res2.json());
  } catch (err) {
    if (err.name === 'AbortError') {
      res.status(504).json({ error: 'Upstream timed out' });
    } else {
      res.status(500).json({ error: 'Internal error' });
    }
  } finally {
    clearTimeout(timeoutId);
  }
});
```

**3. `Promise.race([])` with an empty array returns a Promise that never settles** — it stays pending forever.

## Follow-up

**Q:** Is `Promise.race` the right tool for implementing retry with backoff?

**A:** No. `Promise.race` is for competing Promises — pick the first winner. Retry with backoff is sequential: try, fail, wait, try again. The correct pattern uses a loop with `await`:

```js
async function withRetry(fn, maxAttempts = 3, baseDelayMs = 200) {
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err) {
      if (attempt === maxAttempts) throw err;
      await new Promise(r => setTimeout(r, baseDelayMs * 2 ** (attempt - 1)));
    }
  }
}
```
