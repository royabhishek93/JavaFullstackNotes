# Promises in JavaScript — Cheat Sheet

```
PROMISE STATES
  pending    -> operation in flight
  fulfilled  -> resolved with value    -> .then() fires
  rejected   -> failed with reason     -> .catch() fires
  .finally() fires on BOTH

CONSUMPTION
  fetch(url)
    .then(res  => res.json())
    .then(data => render(data))
    .catch(err => showError(err))
    .finally(() => hideSpinner())

ASYNC/AWAIT
  async function load() {
    try {
      const res  = await fetch(url);    // suspends function, not thread
      const data = await res.json();
      return data;                      // wraps in fulfilled Promise
    } catch (err) {
      throw err;                        // wraps in rejected Promise
    } finally {
      hideSpinner();
    }
  }

PARALLEL vs SEQUENTIAL
  // Sequential — 3x latency
  const a = await fetchA();
  const b = await fetchB();
  const c = await fetchC();

  // Parallel — max(latency) not sum(latency)
  const [a, b, c] = await Promise.all([fetchA(), fetchB(), fetchC()]);

COMBINATOR COMPARISON
  Promise.all([...])         -> rejects if ANY rejects (fail-fast)
  Promise.allSettled([...])  -> always resolves, reports each outcome
  Promise.race([...])        -> first to settle wins (timeout pattern)
  Promise.any([...])         -> first to FULFILL wins (ignore rejections)

CREATING A PROMISE (only when wrapping callbacks)
  new Promise((resolve, reject) => {
    legacyFn(args, (err, result) => {
      if (err) reject(err);
      else     resolve(result);
    });
  });

MICROTASK QUEUE ORDER
  1. Synchronous code (call stack)
  2. Microtasks: Promise .then / .catch / .finally, queueMicrotask()
  3. Macrotasks: setTimeout, setInterval, I/O callbacks
  Rule: microtasks drain COMPLETELY before next macrotask

COMMON PITFALLS
  1. Forgetting to return in .then()  -> rejection escapes the chain
  2. Sequential await on independent fetches -> 3x slower than Promise.all
  3. new Promise() wrapping a Promise -> anti-pattern, adds error surface
  4. fire-and-forget without .catch   -> unhandled rejection, crashes Node 15+
  5. useEffect fetch without cleanup  -> race condition, stale data

.then() vs async/await
  .then()      : single transform, library return value, non-async context
  async/await  : multi-step flow, branching, Express handlers, everything else
```
