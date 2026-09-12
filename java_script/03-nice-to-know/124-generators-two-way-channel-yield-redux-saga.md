# Two-Way Channel with yield — Redux-Saga Pattern (Advanced Senior Trap)
> **Topic:** Generator Functions | **Level:** Senior Trap | **Frequency:** Low

## The Setup

Most candidates understand generators as output devices — they yield values out. The advanced trap is that `yield` is a two-way channel: it sends a value out AND receives the next value passed into `.next(val)`. This is the mechanism that powers Redux-Saga's effect orchestration and makes generators capable of expressing complex async workflows as synchronous-looking code.

## The Question

"What does `yield` return when the caller passes a value to `.next()`? Build a stateful adder that accumulates values sent in via `.next()` and returns the total when `null` is sent. Then explain how Redux-Saga uses this pattern."

## Diagram

```
  caller           generator (adder)
  ──────           ─────────────────
  g.next()    →    starts, sum=0, yields sum(0)  →  { value: 0, done: false }
  g.next(10)  →    incoming=10, sum=10, yields sum(10)  →  { value: 10, done: false }
  g.next(5)   →    incoming=5, sum=15, yields sum(15)   →  { value: 15, done: false }
  g.next(null)→    incoming=null, return sum(15)         →  { value: 15, done: true }

  THE CHANNEL:
    yield → sends value OUT (right)
    .next(val) → sends val IN (left), which becomes the return value of yield
```

## Model Answer (15 YOE)

```js
function* adder() {
  let sum = 0;
  while (true) {
    const incoming = yield sum; // yield SENDS sum out AND RECEIVES the next .next(value)
    if (incoming === null) return sum;
    sum += incoming;
  }
}

const g = adder();
g.next();        // first .next() starts the generator — incoming is undefined, yields 0
g.next(10);      // sends 10 into the generator, incoming = 10, sum = 10, yields 10
g.next(5);       // sends 5, sum = 15, yields 15
g.next(null);    // sends null → return 15 → { value: 15, done: true }
```

**The critical rule about the first `.next()` call:**

The first `.next()` call must be called with no argument (or `undefined`). It starts the generator from the top and runs until the first `yield`. The value passed to the first `.next()` is silently discarded — there is no `yield` expression yet to receive it. Calling `g.next(10)` as the first call sends 10 nowhere.

**How Redux-Saga uses this:**

```js
function* fetchUserSaga() {
  // yield sends an "effect descriptor" OUT to the Saga middleware
  // the middleware executes the effect (calls the API)
  // then calls generator.next(result) to send the result back IN
  const user = yield call(fetchUser, userId);
  //            ↑ yield sends: { type: 'CALL', fn: fetchUser, args: [userId] }
  //                     ↑ incoming from .next(apiResult) — the resolved user object

  yield put(userLoaded(user));
  //    ↑ sends: { type: 'PUT', action: userLoaded(user) }
  //      middleware dispatches the action, then calls .next()
}
```

The Saga middleware is a driver that:
1. Calls `generator.next()` to get the next effect descriptor
2. Executes the effect (API call, dispatch, etc.)
3. Calls `generator.next(result)` to inject the result back
4. Repeat until `{ done: true }`

This architecture makes sagas fully testable without mocking: the test just calls `.next()` with mock values and asserts on the yielded descriptors.

## Why It's a Trap

Nearly every candidate who "knows generators" only knows the output direction. The two-way channel is the 15% of the topic that separates senior engineers from mid-level ones. Without it, you cannot understand Redux-Saga's architecture, cannot build coroutines, and cannot explain how generators are used for cooperative multitasking.

## What NOT to Say

- "yield only sends values out" — it also receives values in via `.next(val)`.
- "The first `.next()` call can pass a value to the generator" — the first call's argument is discarded.
- "This is too advanced for production use" — Redux-Saga uses this pattern in thousands of production apps.

## Follow-up

**Q:** "Why does Saga use `yield call(fn, args)` instead of `yield fn(args)` directly?"

**A:** `call(fn, args)` returns a plain object descriptor `{ type: 'CALL', fn, args }`. This is what the middleware receives at the yield point. The middleware inspects the descriptor and decides how to execute it. This indirection makes the saga testable: in tests, you assert that the generator yielded `call(fetchUser, id)` — a plain object comparison — rather than having to mock the actual API function.
