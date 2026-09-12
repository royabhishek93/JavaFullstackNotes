# Async Compose — ETL Pipeline with a DB Lookup Stage
> **Topic:** Composition | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A Meesho logistics team has a product enrichment pipeline: parse -> validate -> fetchCategoryFromDb -> applyPricing -> save. The DB fetch breaks their synchronous `pipe`. They are debating rewriting from scratch.

## The Question
Extend the standard `pipe` to handle async stages without rewriting the business logic functions.

## Diagram

```
Async pipeline — each stage may return a value OR a Promise:

  rawProduct
      |
      v
  parse (sync)      -> { id, name, price }
      |
      v
  validate (sync)   -> same obj or throws
      |
      v
  fetchCategory     -> Promise<{ ...obj, category }> -- async I/O
  (async, DB call)
      |  (awaited internally by asyncPipe)
      v
  applyPricing      -> { ...obj, finalPrice }
  (sync)
      |
      v
  save (async)      -> Promise<savedRecord>
      |
      v
  result
```

## Model Answer (15 YOE)

The fix is a `pipeAsync` variant that awaits each stage before passing its result to the next:

```js
const pipeAsync = (...fns) => x =>
  fns.reduce(
    (promise, fn) => promise.then(fn),
    Promise.resolve(x)
  );

// Stages — mix of sync and async, no changes needed
const parse         = raw  => ({ id: raw.id, name: raw.name.trim(), price: Number(raw.price) });
const validate      = prod => { if (prod.price <= 0) throw new Error('Bad price'); return prod; };
const fetchCategory = async prod => {
  const cat = await db.categories.findOne({ id: prod.categoryId });
  return { ...prod, category: cat.name };
};
const applyPricing  = prod => ({ ...prod, finalPrice: prod.price * (prod.category === 'electronics' ? 1.18 : 1.05) });
const save          = async prod => db.products.insert(prod);

const processProduct = pipeAsync(parse, validate, fetchCategory, applyPricing, save);

// Usage
await processProduct(rawRow);
```

`pipeAsync` wraps the initial value in `Promise.resolve`, then chains `.then(fn)` for each stage. Sync functions work fine inside `.then` — they run synchronously and their return value resolves the next `.then`. The async stages (`fetchCategory`, `save`) return Promises, which `.then` unwraps before passing to the next stage. Error handling: a `throw` in any stage rejects the chain — wrap the call in `try/catch` or `.catch()` at the call site. For production, I add a generic error-logging stage at the end of the pipe rather than scattering try/catch inside stages.

## Follow-up

**Q:** How do you run two independent enrichment stages in parallel inside this pipeline?

**A:** Insert a `fanOut` stage that calls both in parallel and merges the results: `const fanOut = async prod => { const [cat, pricing] = await Promise.all([fetchCategory(prod), fetchPricing(prod)]); return { ...prod, ...cat, ...pricing }; }`. Then include `fanOut` as a single stage in the pipe. The parallel work is encapsulated inside one pipeline step — the pipe itself stays linear.
