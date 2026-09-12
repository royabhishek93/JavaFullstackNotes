# What is compose vs pipe — Implement Both
> **Topic:** Composition | **Level:** Fundamental | **Frequency:** High

## The Setup
Every functional programming interview and many JavaScript architecture interviews open with this question. Understanding compose and pipe is the prerequisite for Redux middleware, React HOC chaining, ETL pipelines, and point-free style.

## The Question
What is function composition? What is the difference between `compose` and `pipe`? Implement both from scratch without using any libraries.

## Diagram

```
pipe (left-to-right):
                                                      result
  raw data                                              |
     |                                                  |
     v                                                  v
 +--------+    +----------+    +---------+    +----------+
 |  fn1   | -> |   fn2    | -> |   fn3   | -> |   fn4    |
 | parse  |    | validate |    | enrich  |    | format   |
 +--------+    +----------+    +---------+    +----------+

compose (right-to-left — same pipeline, arguments reversed):
  compose(fn4, fn3, fn2, fn1)(rawData)
  reads: "fn4 of fn3 of fn2 of fn1 of rawData"

Function as a value flowing through transforms:
  input --> [pure fn] --> [pure fn] --> [pure fn] --> output
            ^                                ^
            |                                |
     independently testable          independently testable
```

## Model Answer (15 YOE)

Composition is the art of wiring the output of one function directly into the input of the next, building a data pipeline where each stage has one job.

```js
// compose: right-to-left (mathematical convention)
// compose(f, g, h)(x) === f(g(h(x)))
const compose = (...fns) => x => fns.reduceRight((acc, fn) => fn(acc), x);

// pipe: left-to-right (sequential readability)
// pipe(h, g, f)(x) === f(g(h(x)))
const pipe = (...fns) => x => fns.reduce((acc, fn) => fn(acc), x);

// composeAll: when the first-to-run stage needs multiple arguments
const composeAll = (...fns) => (...args) => {
  const last = fns[fns.length - 1];
  const rest = fns.slice(0, -1);
  return rest.reduceRight((acc, fn) => fn(acc), last(...args));
};

// Demo — both produce the same result, argument order differs
const double = x => x * 2;
const addOne = x => x + 1;
const square = x => x * x;

pipe(double, addOne, square)(3);     // double(3)=6 -> addOne(6)=7 -> square(7)=49
compose(square, addOne, double)(3);  // same pipeline: double first, square last -> 49

// Real usage — user data transform
const sanitize    = u => ({ ...u, email: u.email?.toLowerCase().trim() });
const addDefaults = u => ({ role: 'viewer', ...u });
const toApiShape  = u => ({ id: u.id, email: u.email, role: u.role });

const processUser = pipe(sanitize, addDefaults, toApiShape);
// processUser({ id: 1, email: '  BOB@EXAMPLE.COM  ' })
// => { id: 1, email: 'bob@example.com', role: 'viewer' }
```

Key rules for functions to be composable:
1. **Pure**: same input always produces same output, no side effects
2. **Unary**: one argument (except the first-to-run stage)
3. **Focused**: does exactly one thing
4. **Typed**: output type must match the next stage's input type

`pipe` is the default choice — order matches execution order, readable by any engineer. Use `compose` when integrating with libraries (Redux, Ramda) that expect it.

## Follow-up

**Q:** What is the implementation difference between `compose` and `pipe` internally?

**A:** `compose` uses `reduceRight` — it starts accumulating from the rightmost function. `pipe` uses `reduce` — it starts from the leftmost. Both pass the accumulator (the current value) as the single argument to each function. The only real difference is which end of the `fns` array you start from. Both are O(n) in the number of functions.
