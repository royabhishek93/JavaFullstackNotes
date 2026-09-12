# Promise.all vs allSettled vs race vs any
> **Topic:** Promises | **Level:** Intermediate | **Frequency:** High

## The Setup

You are in a system design interview discussing how your team handles multiple concurrent async operations in a Node.js microservice. The interviewer asks you to compare the four Promise combinators.

## The Question

Walk me through `Promise.all`, `Promise.allSettled`, `Promise.race`, and `Promise.any`. When does each one reject? Give a real use case for each.

## Diagram

```
  Input: [P1, P2, P3]   (P2 rejects at t=200ms, P1 fulfills at t=300ms, P3 fulfills at t=400ms)

  Promise.all        → rejects at t=200ms with P2's reason (fail-fast)
                       P1 and P3 results discarded

  Promise.allSettled → resolves at t=400ms with:
                       [ { status:'fulfilled', value: P1result },
                         { status:'rejected',  reason: P2reason },
                         { status:'fulfilled', value: P3result } ]

  Promise.race       → rejects at t=200ms with P2's reason (first to SETTLE wins)
                       P2 settled first (as rejection), so race resolves with it

  Promise.any        → fulfills at t=300ms with P1's value (first to FULFILL wins)
                       P2's rejection is ignored; needs at least one fulfillment
                       Throws AggregateError only if ALL reject
```

## Model Answer (15 YOE)

**`Promise.all`** — use when all results are required and any failure is fatal. Short-circuits on the first rejection. Classic use case: loading all required data before rendering a page that cannot function without any piece of it.

```js
const [user, permissions, config] = await Promise.all([
  fetchUser(id),
  fetchPermissions(id),
  fetchConfig(),
]);
```

**`Promise.allSettled`** — use when partial success is acceptable. Always waits for every Promise to settle, then gives you a per-item outcome. Classic use case: sending notifications to a list of users where you want to know which ones failed without stopping the rest.

```js
const results = await Promise.allSettled(users.map(u => sendEmail(u)));
const failed = results.filter(r => r.status === 'rejected');
```

**`Promise.race`** — use when you want the first settler regardless of whether it fulfills or rejects. Classic use case: a timeout wrapper — race the real operation against a timer that rejects after N ms.

```js
const result = await Promise.race([
  fetchInventory(sku),
  new Promise((_, reject) => setTimeout(() => reject(new Error('Timeout')), 3000)),
]);
```

**`Promise.any`** — use when you want the first success and are willing to ignore failures. Classic use case: redundant API calls where you have three mirrors and want whichever responds first without caring that the other two are slow.

```js
const data = await Promise.any([
  fetchFromRegionA(url),
  fetchFromRegionB(url),
  fetchFromRegionC(url),
]);
```

`Promise.any` throws an `AggregateError` only if every input Promise rejects — it contains all the rejection reasons.

## Follow-up

**Q:** If you pass an empty array to `Promise.all` vs `Promise.any`, what happens?

**A:** `Promise.all([])` resolves immediately with an empty array — vacuously, all zero Promises fulfilled. `Promise.any([])` rejects immediately with an `AggregateError` containing no reasons — there were no Promises to fulfill, so the "first fulfillment" condition can never be met.
