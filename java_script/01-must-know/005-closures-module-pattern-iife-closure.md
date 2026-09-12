# Module Pattern for a Payment SDK
> **Topic:** Closures | **Level:** Intermediate | **Frequency:** Medium

## The Setup
You are building an internal payment SDK at Razorpay that will be consumed by dozens of engineering teams. The SDK must expose a clean public API (`init`, `charge`, `refund`) but must hide internal state like the API key, retry counters, and the request queue. You cannot use ES modules because this SDK is injected as a script tag in merchant pages.

## The Question
How do you use closures to implement a module pattern that exposes a controlled public API and hides private state — without classes or ES module syntax?

## Diagram
```
  IIFE creates private scope
  ┌───────────────────────────────────────────────┐
  │  (function() {                                │
  │    let apiKey = null;        // PRIVATE       │
  │    let retryCount = 0;       // PRIVATE       │
  │    const queue = [];         // PRIVATE       │
  │                                               │
  │    function _validateKey(k) { ... } // PRIV  │
  │    function _flush() { ... }        // PRIV  │
  │                                               │
  │    return {                  // PUBLIC API    │
  │      init:   (key) => { ... },               │
  │      charge: (amt) => { ... },               │
  │      refund: (txnId) => { ... }              │
  │    };     ↑ these three close over           │
  │  })();    │ apiKey, queue, retryCount         │
  └───────────┼───────────────────────────────────┘
              │
     window.RazorpaySDK = returned object
     Only init/charge/refund are reachable from outside
```

## Model Answer (15 YOE)
This is the Revealing Module Pattern, and it is still the correct answer for script-tag-injected code in 2024. The outer IIFE creates a fresh execution context. Everything declared inside — `apiKey`, the retry counter, the internal queue, the private validation functions — lives in that context's scope. We return a plain object whose methods are closures over that private scope. The returned object is assigned to `window.RazorpaySDK` and that is the only surface area merchant developers can touch.

The key property is that the private state is genuinely inaccessible. Unlike a class where someone can cast to `any` and reach private fields in TypeScript, or use reflection in Java, a closure-based module's private variables have no path from outside the closure. You cannot prototype-chain your way in, you cannot serialize and deserialize to get at them. The encapsulation is enforced by the language's scoping rules, not a convention.

One nuance I always address: the returned methods share the same closure environment, so they can communicate through the private variables. `charge` can set `retryCount`, and `refund` can read it. This is intentional and is how you implement internal coordination without exposing state. The tradeoff versus a class is testability — private closure state cannot be injected or replaced in tests. I address this by designing private functions to accept their dependencies as parameters rather than reading from the closed-over scope directly.

```js
const RazorpaySDK = (function () {
  let apiKey = null;
  let retryCount = 0;
  const queue = [];

  function _validate(k) { return k.startsWith('rzp_'); }
  function _flush() { /* process queue */ }

  return {
    init: (key) => {
      if (_validate(key)) apiKey = key;
      else throw new Error('Invalid API key');
    },
    charge: (amt) => {
      queue.push({ type: 'charge', amt, key: apiKey });
      _flush();
    },
    refund: (txnId) => {
      retryCount = 0;
      queue.push({ type: 'refund', txnId, key: apiKey });
      _flush();
    },
  };
})();

window.RazorpaySDK = RazorpaySDK;
// apiKey, retryCount, queue — completely unreachable from merchant code
```

## Follow-up
**Q:** How does this compare to ES module privacy?

**A:** ES module top-level variables are module-scoped and unexported variables are genuinely private — you cannot import them. The module pattern with closures replicates that for pre-module environments. ES modules are strictly better when available because they are statically analyzable, tree-shakeable, and have cleaner syntax. The IIFE module pattern is the right answer only when you are constrained to a single script tag or a legacy bundler environment.
