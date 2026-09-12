# Non-Standard Callback — util.promisify Silent Failure
> **Topic:** Promisification | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

You are integrating an older payment gateway SDK from 2013. The SDK's `charge` function uses this callback signature:

```js
// Non-standard: success value comes first, then error
gateway.charge(amount, currency, function(result, err) {
  if (err) handleError(err);
  else processResult(result);
});
```

A junior wraps it with `util.promisify` and ships it. The integration tests pass, but production charges occasionally error silently. You are asked to review the code.

## The Question

Why does `util.promisify` fail here, and what is the correct fix?

## Diagram

```
  Standard Node.js callback:    callback(err, result)
                                         ^     ^
                                     arg[0]  arg[1]

  Payment SDK callback:         callback(result, err)
                                         ^       ^
                                     arg[0]    arg[1]   <- REVERSED

  util.promisify injects:
    fn(...args, (err, result) => {
      if (err) reject(err);        <- reads arg[0] as error
      else resolve(result);        <- arg[0] is actually the RESULT
    });

  What happens on a successful charge:
    SDK calls: callback(chargeResult, null)
    promisify sees: err = chargeResult  (truthy object!)
    promisify calls: reject(chargeResult)
    Your code catches an "error" that is actually a successful response.
```

## Model Answer (15 YOE)

`util.promisify` hard-codes the assumption of error-first callbacks. It always treats the first callback argument as the error. When the SDK reverses the convention — result first, error second — promisify interprets every successful result as a rejection. The integration tests likely mock the SDK and do not exercise the real callback ordering.

**Option 1 — write a manual Promise wrapper:**

```js
function chargeAsync(amount, currency) {
  return new Promise((resolve, reject) => {
    gateway.charge(amount, currency, (result, err) => {
      if (err) reject(err);
      else resolve(result);
    });
  });
}

// Usage
const receipt = await chargeAsync(9999, 'USD');
```

**Option 2 — use `util.promisify.custom` to register the correct behavior:**

```js
const { promisify } = require('util');

gateway.charge[promisify.custom] = function(amount, currency) {
  return new Promise((resolve, reject) => {
    gateway.charge(amount, currency, (result, err) => {
      if (err) reject(err);
      else resolve(result);
    });
  });
};

const chargeAsync = promisify(gateway.charge);
// Now promisify uses the custom implementation
```

In practice, option 1 is simpler for a single non-standard function. The `custom` symbol approach makes sense when you are building a compatibility layer for an entire library.

The broader lesson: always read the callback signature of the specific API you are wrapping. Do not assume `util.promisify` works for every callback-based function — it only works for functions that follow the Node.js convention exactly. The silent wrongness (resolving with the wrong value rather than throwing) is what makes this dangerous in production.

## Follow-up

**Q:** How would you test that the wrapper correctly handles both success and failure paths?

**A:** Unit-test the wrapper with a mock that calls the callback in the non-standard order for both cases. Verify that a success response resolves the Promise with the correct value, and an error response rejects the Promise with the correct error. The key assertion is that a successful SDK response does not appear in the `catch` block.

## Why It's a Trap

`util.promisify` is presented as "the way to promisify Node.js callbacks" and most examples only show standard Node.js APIs. Candidates apply it to any callback-based function without checking the signature. The danger is that `util.promisify` does not throw — it silently produces the wrong behavior, which only surfaces in production with real data.

## What NOT to Say

- "`util.promisify` works with any callback-based function." — It only works with error-first callbacks where the callback is the last argument.
- "The integration tests prove it works." — Tests that mock the SDK can pass even with inverted argument order. Always test the real callback ordering.
- "We can just check if the resolved value looks like an error." — Fragile and incorrect. Fix the adapter, not the consumer.
