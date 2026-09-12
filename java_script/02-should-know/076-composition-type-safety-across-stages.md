# Type Safety Across Composition Pipeline Stages
> **Topic:** Composition | **Level:** Senior Trap | **Frequency:** Medium

## The Setup
A payments team has a five-stage pipe in plain JavaScript. It works in dev, but randomly crashes in production with `TypeError: Cannot read property 'stock' of undefined`. The compose call itself never complained.

## The Question
What is the type-safety problem in a compose pipeline, and how do you defend against it?

## Diagram

```
Type contract violation — caught at runtime, not at definition:

  pipe(parse, validate, enrichGst, normalize, formatForDb)

  parse returns:    { name, price }
                                  |
                                  v
  validate expects: { name, price, stock }  <-- stock is missing!
                                             compose() succeeds -- no error here
                                             runtime crash: prod.stock is undefined
```

## Model Answer (15 YOE)

Each stage's output type must exactly match the next stage's input type. In JavaScript there is no compile-time check for this — if `parse` returns `{ name, price }` and `validate` expects `{ name, price, stock }`, the compose call succeeds at definition time but crashes at runtime when `validate` tries to read `prod.stock`.

In TypeScript, `pipe`/`compose` types (as in `fp-ts` or manually typed generics) will catch this at compile time:

```ts
// TypeScript — type mismatch caught at compile time
type ParsedProduct  = { name: string; price: number };
type ValidProduct   = { name: string; price: number; stock: number };

const parse    = (raw: RawRow): ParsedProduct  => ({ name: raw.name, price: Number(raw.price) });
const validate = (prod: ValidProduct): ValidProduct => { /* ... */ return prod; };

// TypeScript error: ParsedProduct is not assignable to ValidProduct (stock missing)
const process = pipe(parse, validate); // compile error caught here
```

In plain JavaScript, the three safeguards are:

```js
// 1. Shared shape contract — all stages agree on a single type definition (comment/JSDoc)
// @typedef {{ name: string, price: number, stock: number, category?: string }} Product

// 2. Unit tests that assert both input AND output shape
test('parse returns correct shape', () => {
  const result = parse(rawRow);
  expect(result).toMatchObject({ name: expect.any(String), price: expect.any(Number) });
  expect(result.stock).toBeDefined(); // explicitly check each field downstream stages need
});

// 3. Runtime validation at pipeline boundaries for critical paths (zod)
import { z } from 'zod';
const ParsedProductSchema = z.object({ name: z.string(), price: z.number().positive(), stock: z.number() });
const parseWithValidation = raw => ParsedProductSchema.parse(parse(raw)); // throws on shape mismatch
```

For a payments pipeline or catalog ingestion (high data volume, costly failures), I add `zod` validation at the pipeline entry and between any two stages owned by different teams. For internal pipelines with full visibility, TypeScript generics plus unit tests are sufficient.

## Follow-up

**Q:** How does `fp-ts` handle type safety in compose pipelines?

**A:** `fp-ts`'s `pipe` is fully typed with generics — each function in the chain is typed `(a: A) => B`, and TypeScript infers that `B` must match the input of the next stage. If there is a mismatch, the compiler reports it at the `pipe()` call. The `Either` and `Option` types in `fp-ts` also handle error propagation with full type safety, replacing runtime `try/catch` with compile-time-checked types.

## Why It's a Trap

Candidates who use JavaScript composition every day often never think about the type contract between stages — because as long as the data shape is consistent, it works. The interviewer is checking whether you understand the implicit contract that compose enforces at runtime but not at definition time.

## What NOT to Say

- "JavaScript is dynamically typed, so this is expected" — true but not an answer; the question is how you defend against it
- "Just be careful when writing the stages" — not a system; not a safeguard
- "This is why you should use TypeScript" — incomplete without explaining what TypeScript actually catches and how
