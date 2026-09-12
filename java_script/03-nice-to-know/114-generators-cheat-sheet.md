# Generator Functions — Cheat Sheet
> **Topic:** Generator Functions | **Level:** Reference | **Frequency:** High

```
SYNTAX
======
function* myGen() { yield value; }      // declare sync generator
async function* myAsyncGen() {          // declare async generator
  yield await asyncOp();
}
const gen = myGen();                    // create object (does NOT run body)
gen.next()         -> { value, done }  // advance one step
gen.next(val)      -> { value, done }  // send val back into generator at yield
gen.return(val)    -> { value: val, done: true }  // force complete, runs finally
gen.throw(err)     -> throws err at current yield point, runs finally

CONSUMING
=========
for (const v of gen)         { }   // sync — works on sync generators
for await (const v of gen)   { }   // async — required for async generators
const arr = [...gen];              // exhausts sync generator into array
const [a, b] = gen;               // destructure first N values

YIELD*
======
yield* [1,2,3]               // yields 1, then 2, then 3
yield* otherGenerator()      // delegate entirely; returns otherGen's return value
const ret = yield* inner();  // capture inner generator's return value

PATTERNS
========

Infinite sequence (O(1) memory):
  function* naturals() { let n=1; while(true) yield n++; }

Paginated async API:
  async function* pages(url) {
    let page=0;
    while(true) {
      const data = await fetch(`${url}?page=${page}`).then(r=>r.json());
      if (!data.length) return;
      yield data;
      page++;
    }
  }

Lazy pipeline:
  const result = stage3(stage2(stage1(source)));
  for (const item of result) { process(item); }  // one item flows at a time

Resource-safe generator:
  async function* dbCursor(query) {
    const conn = await pool.connect();
    try { /* yield batches */ }
    finally { conn.release(); }  // always runs — break, throw, or return
  }

STATES
======
suspended-start  -> never called .next()
executing        -> currently inside function body
suspended-yield  -> paused at yield, waiting for .next()
completed        -> returned or fell off the end — forever done

COMMON MISTAKES
===============
1. for...of on async generator         -> use for await...of
2. reusing a completed generator       -> call the function again for a fresh instance
3. assuming break finishes gen         -> break leaves gen in suspended-yield
4. forgetting finally for cleanup      -> resources leak if consumer exits early
5. yield* on a promise                 -> yield* needs an ITERABLE, not a promise

WHEN TO USE
===========
- Paginated API consumption (load next page on demand)
- Infinite sequences with lazy evaluation
- Streaming large datasets (DB export, file processing)
- Lazy pipelines that avoid intermediate array allocation
- Stateful iteration with encapsulated state

WHEN NOT TO USE
===============
- Simple one-shot transformations (use .map / .filter)
- All results needed immediately (return an array)
- Parallel async work (use Promise.all / Promise.allSettled)
- Push-based event streams (use EventEmitter or RxJS Observable)
```
