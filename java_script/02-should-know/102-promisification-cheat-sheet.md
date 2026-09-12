# Promisification — Cheat Sheet

```
WHAT IS PROMISIFICATION
  Wrap a callback-based function with a new function that returns a Promise.
  Original function is never modified.
  Applied once at the module boundary; used everywhere via async/await.

ERROR-FIRST CALLBACK CONVENTION (required for util.promisify)
  fn(arg1, arg2, callback)          <- callback is last
  callback(err, result)             <- err is first (null on success)
  On success: err = null
  On failure: err = Error instance
  Deviation from this convention = silent bugs with util.promisify

PROMISIFY SKELETON (what util.promisify does internally)
  function promisify(fn) {
    return function(...args) {
      return new Promise((resolve, reject) => {
        fn.apply(this, [...args, (err, result) => {
          if (err) reject(err);
          else     resolve(result);
        }]);
      });
    };
  }

NODE.JS BUILT-IN OPTIONS
  require('fs/promises')            <- pre-promisified fs (preferred)
  require('util').promisify(fn)     <- wrap any error-first callback fn
  require('stream').pipeline        <- promisify(pipeline) for streams
  events.once(emitter, 'eventName') <- await one event emission

MULTI-RESULT CALLBACK
  Standard promisify only captures first result value.
  Use rest syntax to capture all:
    fn(...args, (err, ...results) => {
      if (err) reject(err);
      else resolve(results);   // array of all values
    });

TIMEOUT WRAPPER PATTERN
  function withTimeout(promise, ms) {
    let id;
    const timeout = new Promise((_, reject) => {
      id = setTimeout(() => reject(new Error(`Timeout after ${ms}ms`)), ms);
    });
    return Promise.race([promise, timeout]).finally(() => clearTimeout(id));
  }

LIMITATIONS OF util.promisify
  Assumes error-first convention       -> silent wrong behavior otherwise
  Assumes callback is last argument    -> fails if callback is in middle
  Captures only first result value     -> multi-result needs custom wrapper
  Not for EventEmitters                -> use events.once or async iteration
  Not for streams                      -> use stream.pipeline

METHOD BINDING (critical)
  promisify(client.method)             -> WRONG: this context lost
  promisify(client.method.bind(client))-> CORRECT: this preserved

SEQUENTIAL vs CONCURRENT
  // Sequential: sum of all latencies
  const a = await promisifiedFnA();
  const b = await promisifiedFnB();

  // Concurrent: max latency (fastest when independent)
  const [a, b] = await Promise.all([promisifiedFnA(), promisifiedFnB()]);

WHEN TO USE EACH
  util.promisify      : error-first, standard, no extra logic needed
  manual wrapper      : non-standard callback, multi-result, need retry/log/transform
  fs/promises         : always prefer over promisify(fs.*) for Node.js fs
  Promise.race        : timeout, first-result-wins (not retry — use a loop for retry)
  Promise.allSettled  : parallel queries where partial success is acceptable
```
