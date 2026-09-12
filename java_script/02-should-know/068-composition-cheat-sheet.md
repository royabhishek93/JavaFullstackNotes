# Composition Cheat Sheet

```
IMPLEMENTATIONS
---------------
compose: right-to-left
  const compose = (...fns) => x => fns.reduceRight((acc, fn) => fn(acc), x);
  compose(f, g, h)(x)  ==  f(g(h(x)))

pipe: left-to-right
  const pipe = (...fns) => x => fns.reduce((acc, fn) => fn(acc), x);
  pipe(h, g, f)(x)     ==  f(g(h(x)))

pipeAsync: handles Promise-returning stages
  const pipeAsync = (...fns) => x => fns.reduce((p, fn) => p.then(fn), Promise.resolve(x));

composeAll: first function can be multi-arg
  const composeAll = (...fns) => (...args) => {
    const last = fns[fns.length - 1];
    const rest = fns.slice(0, -1);
    return rest.reduceRight((acc, fn) => fn(acc), last(...args));
  };

RULES FOR COMPOSABLE FUNCTIONS
-------------------------------
  Pure     : same input -> same output, no side effects
  Unary    : one argument (except rightmost in compose / leftmost in pipe)
  Focused  : does exactly one thing
  Typed    : output type matches next stage's input type

ASCII FLOW DIAGRAMS
-------------------
  pipe(parse, validate, enrich, format)(rawData)
  rawData --> [parse] --> [validate] --> [enrich] --> [format] --> result

  compose(format, enrich, validate, parse)(rawData)
  result <-- [format] <-- [enrich] <-- [validate] <-- [parse] <-- rawData
  (same pipeline, different argument order in the call)

REAL-WORLD USES
---------------
  ETL / data ingestion  : pipe(parse, validate, enrich, normalize, formatForDb)
  Redux store setup     : compose(applyMiddleware(...), DevTools.instrument())
  React HOC chaining    : compose(withAuth, withTheme, withAnalytics)(Component)
  Express (conceptual)  : app.use(mw1); app.use(mw2); -- pipe in spirit
  Point-free transform  : const process = pipe(sanitize, addDefaults, toApiShape);

SENIOR GOTCHAS
--------------
  Order matters          : compose(f, g) !== compose(g, f) — different pipelines
  Type contract          : output of stage N must match input of stage N+1
  Async stages           : use pipeAsync; plain pipe breaks on Promise-returning stages
  Impure functions       : push I/O to pipeline edges; never inside a stage
  Multi-arg functions    : only the first-to-run stage can accept multiple args
  Debugging              : add a tap() stage: const tap = fn => x => { fn(x); return x; }

COMPOSE VS PIPE QUICK PICK
--------------------------
  Default choice         : pipe (readable, intuitive)
  Redux / Ramda / fp-ts  : compose (library convention)
  HOC wrapping           : compose (outer HOC = first arg = renders first)
  ETL, API transforms    : pipe (steps read top-to-bottom = execution order)
```

## compose vs pipe — When to Choose

| Dimension | `compose` | `pipe` |
|---|---|---|
| Execution order | Right to left: last arg runs first | Left to right: first arg runs first |
| Reading order | Matches math notation: `f(g(x))` | Matches description of steps |
| Used by | Redux `compose`, Ramda, `fp-ts` | RxJS `.pipe()`, most application code |
| Best for | Wrapping enhancers (HOCs, store enhancers) where outer-first matters | Sequential data transforms (ETL, API transforms) where step order is the story |
| Argument position | Rightmost function receives initial input | Leftmost function receives initial input |
| Team readability | Requires knowing FP convention | Natural for engineers from any background |
| Pitfall | Easy to get argument order wrong — `compose(validate, parse)` parses first | No common pitfall — order is obvious |
| When to choose | Redux middleware, HOC chains, existing FP codebase | New code, data pipelines, API layers, onboarding junior engineers |

**Rule of thumb:** Use `pipe` as the default. Use `compose` when integrating with libraries (Redux, Ramda) that expect it, or when composing functions whose names read naturally right-to-left.
