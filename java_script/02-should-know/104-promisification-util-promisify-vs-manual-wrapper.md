# util.promisify vs Manual Promise Wrapper — When to Use Each
> **Topic:** Promisification | **Level:** Fundamental | **Frequency:** High

## The Setup

You are doing a code review of a Node.js adapter layer. The codebase mixes `util.promisify` wrappers, manual `new Promise()` wrappers, and direct use of `fs/promises`. A junior asks: "When should I use each approach?"

## The Question

Walk through the decision: when does `util.promisify` work, when do you write a manual wrapper, and when do you use neither?

## Diagram

```
  Decision tree:

  Is the function a Node.js built-in (fs, dns, crypto)?
    └── YES → Use fs/promises, dns.promises, etc. (already promisified)

  Does it follow error-first callback convention exactly?
  (callback is last arg, first callback arg is err or null)
    └── YES → util.promisify(fn.bind(ctx))   ← one line
    └── NO  → Manual new Promise() wrapper   ← 5-7 lines

  Does it pass multiple result values to the callback?
  (err, a, b, c)
    └── YES → Manual wrapper with rest syntax (...results)

  Does it need retry logic, logging, or value transformation?
    └── YES → Manual wrapper (add logic inside)

  Is it an EventEmitter or stream?
    └── YES → events.once() or stream.pipeline (not promisify)
```

## Model Answer (15 YOE)

**Use `fs/promises` (or the `*.promises` namespace) first.** For Node.js built-ins, the officially pre-promisified API is the right answer. No wrappers needed.

```js
// Preferred for Node.js fs
const { readFile, writeFile } = require('fs/promises');
const content = await readFile('config.json', 'utf8');
```

**Use `util.promisify` for third-party libraries that follow the Node.js error-first convention.** It is a one-liner, preserves `this` via `fn.apply`, and checks for `util.promisify.custom` overrides.

```js
const { promisify } = require('util');
const redis = require('redis');
const client = redis.createClient();

const get = promisify(client.get.bind(client));
const set = promisify(client.set.bind(client));

const value = await get('my-key');
```

**Write a manual `new Promise()` wrapper when:**
1. The callback convention is non-standard (result first, error second).
2. The callback passes multiple result values `(err, a, b, c)` — `util.promisify` only captures the first.
3. You need to add retry logic, logging, or transform the result inside the wrapper.
4. The API is unusual enough that `util.promisify`'s behavior would be surprising to the next reader.

```js
// Manual wrapper for non-standard or enriched cases
function chargeAsync(amount, currency) {
  return new Promise((resolve, reject) => {
    gateway.charge(amount, currency, (result, err) => {  // result-first
      if (err) reject(err);
      else resolve(result);
    });
  });
}
```

The decision rule: if the function follows the Node.js error-first convention exactly and needs no extra behavior, `util.promisify` is right. For any deviation or enrichment, write the manual wrapper — it is only 5-7 lines and is far less surprising than the subtle failures that come from forcing a non-standard function through `util.promisify`.

## Follow-up

**Q:** What is `util.promisify.custom` and when would you use it?

**A:** It is a well-known Symbol that library authors can attach to a function to override what `util.promisify` does with it. When `util.promisify` sees this symbol on the function, it uses the custom implementation instead of generating the default callback-wrapping behavior. This lets library authors ship a better Promise version while keeping the callback API for backward compatibility. As a consumer, you use it to correct `util.promisify`'s behavior for a function whose author set it up — or when you own the function and want to register a better default.
