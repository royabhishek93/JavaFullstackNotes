# Impure Functions in Composition Pipelines
> **Topic:** Composition | **Level:** Senior Trap | **Frequency:** Medium

## The Setup
A candidate confidently explains `pipe` and `compose`, then the interviewer asks: "Your `enrichWithTax` stage reads a config object from module scope. It still composes fine — what's the problem?"

## The Question
What happens when you compose an impure function into a pipeline?

## Diagram

```
Impure stage hidden inside a compose pipeline:

  pipe(parse, enrichWithTax, normalize, formatForDb)
                    ^
                    |
         reads taxRate from module scope  <-- hidden dependency

  Unit test environment:
    taxRate = 0.05 (stale test config)
    enrichWithTax({ price: 100 }) => { priceWithTax: 105 }  -- test passes

  Production:
    taxRate = 0.18 (real config, loaded at runtime)
    enrichWithTax({ price: 100 }) => { priceWithTax: 118 }  -- different result, no failure
    test was silently wrong all along
```

## Model Answer (15 YOE)

It works until it doesn't — and when it breaks, it breaks silently in surprising ways. An impure function inside a compose pipeline couples an otherwise isolated stage to the outside world. If `enrichWithTax` reads a config object from module scope, your unit test for `enrichWithTax` will silently pass with stale test config and fail in production with the real config. If `logAndReturn` writes to a file, running the pipeline twice in a test suite produces two log entries — your test is no longer deterministic.

```js
// BAD — enrichWithTax is impure: hidden dependency on module-scope config
import { taxConfig } from './config';
const enrichWithTax = prod => ({ ...prod, priceWithTax: prod.price * (1 + taxConfig.rate) });

// GOOD — pass config via closure (partial application) — stage is now pure
const makeEnrichWithTax = rate => prod => ({ ...prod, priceWithTax: +(prod.price * (1 + rate)).toFixed(2) });

// Compose the pipeline — config loaded once at the edge, not inside the stage
const taxRate = await loadTaxConfig(); // I/O at the edge
const processProduct = pipe(
  parse,
  makeEnrichWithTax(taxRate),  // pure stage with config baked in
  normalize,
  formatForDb
);
```

The correct pattern: push all I/O to the edges (the final `save` stage, a preceding `loadConfig` call), and keep every internal stage pure. Impurity in a pipeline is a hidden dependency that `compose` has no mechanism to express or enforce.

## Follow-up

**Q:** How do you debug which stage introduced bad data in a live pipeline?

**A:** Insert a `tap` stage: `const tap = label => x => { console.log(label, x); return x; }`. Place it between stages — `pipe(parse, tap('after parse'), validate, tap('after validate'), ...)`. It passes the value through unchanged, so the pipeline is not disrupted. Remove tap stages before production or gate them behind a debug flag.

## Why It's a Trap

Candidates who say "it still works" are missing the real risk. An impure function *does* compose syntactically — the issue is correctness and testability, not a runtime error. Interviewers are testing whether you understand that composition correctness depends on purity, not just syntactic compatibility.

## What NOT to Say

- "It still works, composition doesn't care about purity" — true but dangerously incomplete
- "Just add a test for it" — the problem is the test cannot catch the real-world difference
- "Impurity is fine at the edges" — correct, but missing that the question is about impurity *inside* the pipeline
