# Higher-Order Functions Cheat Sheet

```
DEFINITIONS
-----------
HOF      : A function that takes a function as argument OR returns a function (or both)
Callback : A function passed to a HOF to be invoked at the HOF's discretion
Closure  : The mechanism that lets returned functions capture outer-scope variables
           -- what makes factory functions and memoize work

IMPLEMENTATIONS FROM SCRATCH
-----------------------------
myMap(arr, fn):
  const r = []; for (let i = 0; i < arr.length; i++) r.push(fn(arr[i], i, arr)); return r;

myFilter(arr, fn):
  const r = []; for (let i = 0; i < arr.length; i++) if (fn(arr[i], i, arr)) r.push(arr[i]); return r;

myReduce(arr, fn, init):
  let acc = init ?? arr[0]; let s = init !== undefined ? 0 : 1;
  for (let i = s; i < arr.length; i++) acc = fn(acc, arr[i], i, arr); return acc;

memoize(fn):
  const c = new Map();
  return (...a) => { const k = JSON.stringify(a); if (c.has(k)) return c.get(k); const r = fn(...a); c.set(k,r); return r; };

memoizeAsync(fn):
  const c = new Map();
  return async (...a) => {
    const k = JSON.stringify(a); if (c.has(k)) return c.get(k);
    const p = fn(...a); c.set(k, p);
    try { return await p; } catch(e) { c.delete(k); throw e; }
  };

factory(config) returns fn:
  const createCalc = rate => amount => +(amount * rate).toFixed(2);
  const gstCalc = createCalc(0.18); // config baked in via closure
  gstCalc(1000); // 180

CALLBACK HELL PYRAMID (what to avoid)
--------------------------------------
  asyncA(x, (e, a) => {
    asyncB(a, (e, b) => {
      asyncC(b, (e, c) => {
        asyncD(c, (e, d) => {  // <-- 4 levels deep, 4x duplicate error handling
          // ...
        });
      });
    });
  });

  FIX: promisify each fn, then:
  const d = await asyncD(await asyncC(await asyncB(await asyncA(x))));
  // or: pipeAsync(asyncA, asyncB, asyncC, asyncD)(x)

BUILT-IN HOF QUICK REFERENCE
-----------------------------
  map(fn)            -> new array, same length, values transformed
  filter(fn)         -> new array, subset, fn returns boolean
  reduce(fn, init)   -> single value of any type
  forEach(fn)        -> undefined (side effects only, not chainable)
  sort(cmp)          -> sorted array (MUTATES original — watch out)
  find(fn)           -> first matching element or undefined
  some(fn)           -> true if any element matches
  every(fn)          -> true if all elements match
  flatMap(fn)        -> map + flatten one level (replaces map().flat())
  setTimeout(fn, ms) -> fn called after ms — async callback
  addEventListener   -> fn called on every matching event — multi-fire

FACTORY / MIDDLEWARE PATTERN
-----------------------------
  const makeMiddleware = (config) => (req, res, next) => { /* use config */ next(); };
  app.use(makeMiddleware({ limit: 100 }));
  -- factory configures once, middleware runs on every request

SENIOR GOTCHAS
--------------
  sort() mutates          : always a.slice().sort(fn) when original matters
  forEach not chainable   : returns undefined; use map then chain
  reduce no initial value : throws on empty array; always provide initial value
  memoize only pure fns   : side-effectful fn memoized = side effect silently skipped
  async memoize           : cache the Promise, not the resolved value (thundering herd)
  callback vs listener    : callback = once; listener = N times — wrong choice = silent data loss
  HOF + closure memory    : factory creates closures; long-lived factories holding large data = leak

HOF vs OOP QUICK PICK
---------------------
  Stateless transform     : HOF (map/filter/reduce, factory)
  Shared mutable state    : class instance
  Behavior injection      : HOF (strategy as fn argument)
  Entity with lifecycle   : class (Repository, Service)
  Utility / pipeline step : HOF (pure, composable)
  Framework integration   : class (NestJS controllers, Angular services)
```

## HOF vs OOP — When to Choose

| Dimension | HOF Pattern | OOP Equivalent |
|---|---|---|
| Core idea | Pass behavior as a function argument | Override methods in a subclass or pass strategy object |
| Example | `arr.filter(isActive)` | `new ActiveFilter().apply(arr)` |
| Boilerplate | Minimal — a function expression | Class definition, constructor, method |
| State sharing | Via closure (implicit, private) | Via `this` (explicit, mutable, shared) |
| Composability | Natural — chain HOFs | Requires explicit interface design |
| Testability | High — pure functions, no setup | Requires instantiation, mock setup |
| Reusability | High — any context that accepts a function | Tied to class hierarchy and interface contract |
| When HOF wins | Stateless transforms, pipelines, utilities, callbacks | When you need shared mutable state, lifecycle hooks, or multiple related methods on one object |
| When OOP wins | When behavior needs identity (same instance across calls), serialization, or framework integration | Repository, Service, Controller patterns in NestJS/Spring |
| Real world | `Array.map/filter`, Redux reducers, Express middleware factories | Repository pattern, Strategy pattern, Template Method |
| Risk | Closure memory leaks; accidental shared mutable state in closure | God objects; deep inheritance making behavior hard to trace |

**Rule of thumb:** Default to HOFs for transformations and utilities. Use classes/objects when you need to model an entity with identity, lifecycle, and multiple related behaviors that share state.
