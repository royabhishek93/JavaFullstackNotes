# generator.return() vs generator.throw() with finally (Senior Trap)
> **Topic:** Generator Functions | **Level:** Senior Trap | **Frequency:** Low

## The Setup

`generator.return(val)` and `generator.throw(err)` are the two control signals a consumer can inject into a running generator. Both trigger `finally` blocks. Candidates often know `yield` and `.next()` but are unaware these two methods exist — let alone their exact semantics. In production, `.return()` is the correct teardown mechanism for generator-based resource management.

## The Question

"What is the difference between `generator.return(val)` and `generator.throw(err)`? When would you call each in production? What do `finally` blocks do in each case?"

## Diagram

```
  generator.return('early exit')
  ─────────────────────────────
  current yield point receives a "return signal"
  finally block runs
  generator transitions to COMPLETED
  caller receives { value: 'early exit', done: true }
  no exception propagates to caller

  generator.throw(new Error('abort'))
  ───────────────────────────────────
  Error is injected at the current yield point
  If generator catches it → can yield again (stays alive)
  If generator does not catch it → finally runs, then error re-throws to caller
  generator transitions to COMPLETED (if uncaught)
```

## Model Answer (15 YOE)

```js
function* steps() {
  try {
    yield 'step 1';
    yield 'step 2';
    yield 'step 3';
  } finally {
    console.log('cleanup ran'); // runs for BOTH .return() and .throw()
  }
}

const g = steps();
g.next(); // { value: 'step 1', done: false }

// .return(val): forces the generator to the completed state
// The finally block runs, then { value: val, done: true } is returned
g.return('early exit');
// logs "cleanup ran"
// returns { value: 'early exit', done: true }

// .throw(err): injects an exception AT the current yield point
// If the generator catches it, it can continue; otherwise it completes
const g2 = steps();
g2.next();             // { value: 'step 1', done: false }
g2.throw(new Error('abort'));
// logs "cleanup ran", then re-throws — uncaught here
```

**When `.return()` matters in production:**

When a consumer exits mid-iteration (user navigates away, HTTP request cancelled, AbortSignal fired), calling `generator.return()` is the correct teardown. The generator runs its `finally` block, releasing DB connections, closing file handles, or flushing buffers.

```js
// React cleanup — generator used as a data stream
useEffect(() => {
  const paginator = fetchOrderHistory(restaurantId);
  let active = true;

  (async () => {
    for await (const orders of paginator) {
      if (!active) break;
      setOrders(prev => [...prev, ...orders]);
    }
  })();

  return () => {
    active = false;
    paginator.return(); // trigger finally block, release resources
  };
}, [restaurantId]);
```

**When `.throw()` matters in production:**

In Redux-Saga, the middleware injects cancellation errors into saga generators via `.throw()`. A saga can catch the cancellation, perform cleanup, and re-yield a different effect — or let it propagate to complete the saga. This is how `takeLatest` cancels a previous saga run.

## Why It's a Trap

Candidates know `.next()` but not `.return()` or `.throw()`. They either leak resources on early exit (no `.return()` call) or crash the saga incorrectly (unhandled `.throw()`). The `finally` guarantee is the key: both signals respect it, making generators safe for resource management in a way that plain promises are not.

## What NOT to Say

- "You can't cancel a generator" — you can, with `.return()`.
- "`.throw()` always kills the generator" — only if uncaught inside the generator body.
- "The `finally` block only runs when the generator completes normally" — it runs for `.return()`, `.throw()`, and natural completion.

## Follow-up

**Q:** "If the `finally` block itself `yield`s a value, what happens?"

**A:** During a `.return(val)` call, if the `finally` block contains a `yield`, the generator enters suspended-yield state again. The `.return()` call returns `{ value: yieldedValue, done: false }`. The generator is not yet completed. The caller must call `.next()` again to continue through the `finally` block. This is a rare edge case but a real gotcha.
