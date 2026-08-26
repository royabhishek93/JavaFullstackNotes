# JavaScript Core & Async — 15-YOE Interview Prep

> Target: Senior/Staff/Principal-level interviews. Every answer here reflects the depth expected at 15 years of production experience.

---

## 1. Big Picture: JavaScript Runtime Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        JavaScript Runtime (V8 + Browser/Node)           │
│                                                                          │
│  ┌──────────────────┐    ┌───────────────────────────────────────────┐  │
│  │   CALL STACK     │    │              WEB APIs / Node APIs          │  │
│  │                  │    │                                            │  │
│  │  [main()]        │    │  setTimeout / setInterval                  │  │
│  │  [fn3()]   ───── │───▶│  fetch / XHR                               │  │
│  │  [fn2()]         │    │  DOM Events                                │  │
│  │  [fn1()]         │    │  fs.readFile (Node)                        │  │
│  └────────┬─────────┘    │  MessageChannel                           │  │
│           │              └──────────────────┬────────────────────────┘  │
│           │ (stack empty)                    │ callback ready             │
│           │                                  ▼                           │
│           │              ┌───────────────────────────────────────────┐  │
│           │              │         TASK QUEUES                        │  │
│           │              │                                            │  │
│           │              │  ┌─────────────────────────────────────┐  │  │
│           │              │  │  MICROTASK QUEUE  (higher priority)  │  │  │
│           │              │  │                                      │  │  │
│           │              │  │  Promise.then()  ◀── resolved proms  │  │  │
│           │              │  │  queueMicrotask()                    │  │  │
│           │              │  │  MutationObserver                    │  │  │
│           │              │  │  async/await continuations           │  │  │
│           │              │  └──────────────────┬───────────────────┘  │  │
│           │              │                     │ drain ALL before next  │  │
│           │              │  ┌──────────────────▼───────────────────┐  │  │
│           │              │  │  MACROTASK QUEUE  (lower priority)   │  │  │
│           │              │  │                                      │  │  │
│           │              │  │  setTimeout(fn, 0)                   │  │  │
│           │              │  │  setInterval                         │  │  │
│           │              │  │  I/O callbacks                       │  │  │
│           │              │  │  MessageChannel.postMessage          │  │  │
│           │              │  │  requestAnimationFrame (browser)     │  │  │
│           │              │  └──────────────────────────────────────┘  │  │
│           │              └───────────────────────────────────────────┘  │
│           │                                  ▲                           │
│           └──────────────────────────────────┘                          │
│                     EVENT LOOP picks next task                           │
└─────────────────────────────────────────────────────────────────────────┘

EXECUTION ORDER EXAMPLE:
  console.log("1")                          → call stack      → prints 1
  setTimeout(() => console.log("2"), 0)     → macrotask queue
  Promise.resolve().then(() => console.log("3")) → microtask queue
  console.log("4")                          → call stack      → prints 4
  // stack empty → drain microtasks         → prints 3
  // microtasks empty → next macrotask      → prints 2
  // Final order: 1, 4, 3, 2
```

---

## 2. Conversational Interview Script

> This is how a 15-YOE engineer actually talks in an interview. Confident, specific, trade-off aware.

---

**"Walk me through the JavaScript event loop."**

"JavaScript is single-threaded, but it achieves concurrency through an event loop layered on top of the runtime's async APIs. When JS executes, there's a call stack — synchronous code runs there, frame by frame. When the stack empties, the event loop steps in.

It first drains the entire microtask queue — that's Promise resolutions, `queueMicrotask`, MutationObserver. Every single microtask runs, including any microtasks queued by other microtasks, before we look at the macrotask queue. This is critical for correctness — it's why Promise chains are deterministic.

After microtasks are fully drained, the event loop picks one macrotask from the macrotask queue — `setTimeout`, `setInterval`, I/O callbacks — executes it, then drains microtasks again before the next macrotask. This one-at-a-time macrotask processing is what prevents starvation but also means a long-running setTimeout callback can block rendering.

In production, I've used this knowledge to debug subtle ordering bugs — like why a `useState` updater in React fired after a network callback seemed delayed, or why queuing too many `setTimeout(fn, 0)` calls created frame drops while `queueMicrotask` didn't."

---

**"Explain closures — not the definition, the production value."**

"Closures are how you create private state in JavaScript without classes. The classic use case I reach for is memoization — wrapping a function so the cache lives in the closure, invisible to callers. Another real use: event handlers that need to reference state from a setup phase without global leaks. In React, every `useCallback` and `useEffect` is a closure — which is exactly why stale closure bugs are so common. The function closes over the value at capture time, not the latest value. I've fixed more than a few production bugs where a `setInterval` inside an effect captured an old value of `count` because the cleanup function didn't deregister it before a re-render recreated it."

---

**"How does prototypal inheritance differ from classical OOP?"**

"JavaScript doesn't have classes in the traditional sense — the `class` keyword is syntactic sugar over the prototype chain. Every object has an internal `[[Prototype]]` slot. When you access a property, JS walks the chain: own properties first, then the prototype, then the prototype's prototype, until `null`. `Object.create(proto)` gives you raw prototype linkage without constructors. Classes add constructor syntax and `super`, but under the hood it's still prototype delegation. The meaningful difference: classical inheritance copies behavior at instantiation time; JavaScript delegates — the prototype is live, so changes to it propagate to all instances. That's powerful but can burn you in tests if you mutate a prototype accidentally."

---

**"When do you choose Promise chaining over async/await?"**

"async/await is almost always more readable — it flattens the code and makes error handling with try/catch feel natural. But I reach for promise chaining when I'm building pipelines — a sequence of transformations where I want to pass a single value through and each step is a pure function. `.then().then().then()` reads like a Unix pipe and keeps functions small and composable. I also prefer explicit `.catch()` when I need to handle errors at specific stages of a chain differently, rather than one big try/catch that might accidentally swallow an unexpected error. In Node stream processing, for example, I chain transforms and attach `.catch()` at each stage to emit structured error events."

---

## 3. Scenario-Based Q&As (Production Context)

---

### Q1. Your API endpoint has a 3-second timeout. How do you implement cancelable fetches?

```typescript
// Production-grade: AbortController with timeout
async function fetchWithTimeout<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs = 3000
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    return await res.json() as T;
  } catch (err) {
    if ((err as Error).name === "AbortError") {
      throw new Error(`Request to ${url} timed out after ${timeoutMs}ms`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
```

**Why it matters**: Without `clearTimeout` in `finally`, you leak a timer even on success. The `AbortError` check distinguishes timeout from other fetch errors — critical for error telemetry.

---

### Q2. You need to cancel in-flight fetches when a React component unmounts or a search query changes.

```typescript
// In a custom hook
function useSearch(query: string) {
  const [results, setResults] = useState<string[]>([]);

  useEffect(() => {
    if (!query) return;
    const controller = new AbortController();

    fetch(`/api/search?q=${encodeURIComponent(query)}`, {
      signal: controller.signal,
    })
      .then((r) => r.json())
      .then((data) => setResults(data.results))
      .catch((err) => {
        if (err.name !== "AbortError") console.error("Search failed:", err);
      });

    return () => controller.abort(); // cleanup cancels in-flight request
  }, [query]);

  return results;
}
```

**Senior detail**: If you forget the cleanup and the component unmounts, the `.then` fires after unmount and calls `setResults` on an unmounted component — a memory leak and a React warning in dev mode.

---

### Q3. You have 50 API calls to make. How do you control concurrency?

```typescript
async function batchWithConcurrency<T, R>(
  items: T[],
  processor: (item: T) => Promise<R>,
  concurrency = 5
): Promise<R[]> {
  const results: R[] = [];
  const queue = [...items];

  async function worker(): Promise<void> {
    while (queue.length > 0) {
      const item = queue.shift()!;
      results.push(await processor(item));
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(concurrency, items.length) }, worker)
  );
  return results;
}

// Usage
const userData = await batchWithConcurrency(userIds, fetchUser, 5);
```

**Why not Promise.all directly?** 50 simultaneous requests saturates the connection pool, trips rate limiters, and creates backpressure in downstream services. This pattern is production-essential.

---

### Q4. Explain the stale closure problem and how to fix it in React.

```typescript
// BUG: stale closure captures initial count=0
function BuggyCounter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      console.log(count); // always 0 — captured at mount
      setCount(count + 1); // stale, always sets to 1
    }, 1000);
    return () => clearInterval(id);
  }, []); // empty deps = closure captures initial count
}

// FIX: use functional update — no dependency on captured count
function CorrectCounter() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setCount((prev) => prev + 1); // reads latest state
    }, 1000);
    return () => clearInterval(id);
  }, []);
}
```

---

### Q5. How would you implement a memoization cache that doesn't prevent garbage collection?

```typescript
// WeakMap allows keys (objects) to be GC'd when no other refs exist
function memoizeWeak<K extends object, V>(
  fn: (key: K) => V
): (key: K) => V {
  const cache = new WeakMap<K, V>();
  return (key: K) => {
    if (cache.has(key)) return cache.get(key)!;
    const result = fn(key);
    cache.set(key, result);
    return result;
  };
}

// DOM nodes as keys: cache freed automatically when node is removed
const getNodeMetrics = memoizeWeak((node: Element) => ({
  rect: node.getBoundingClientRect(),
  id: node.id,
}));
```

**Production context**: In a virtual DOM diff system, caching computed layout metrics on DOM nodes via WeakMap avoids the manual cache invalidation dance. When the node is removed from DOM and dereferenced, the cache entry disappears automatically.

---

### Q6. Describe how Vue 3's reactivity system works under the hood.

```typescript
// Simplified Vue 3-style reactive using Proxy + Reflect
function reactive<T extends object>(target: T): T {
  return new Proxy(target, {
    get(obj, key, receiver) {
      track(obj, key as string); // record dependency
      return Reflect.get(obj, key, receiver);
    },
    set(obj, key, value, receiver) {
      const result = Reflect.set(obj, key, value, receiver);
      trigger(obj, key as string); // notify subscribers
      return result;
    },
  });
}

// When a computed/effect reads a property → get trap → track()
// When a property is written → set trap → trigger() → re-run effects
const state = reactive({ count: 0 });
effect(() => console.log(state.count)); // auto-tracks "count"
state.count++; // triggers effect re-run
```

**Why Reflect?** `Reflect.get/set` preserves the receiver correctly — without it, getters defined on the prototype receive the proxy as `this` in a broken way.

---

### Q7. How do generators enable lazy evaluation and streaming?

```typescript
// Infinite sequence — values computed on demand, no memory explosion
function* range(start: number, end = Infinity, step = 1): Generator<number> {
  for (let i = start; i < end; i += step) yield i;
}

// Async generator for streaming API responses
async function* streamChatResponse(prompt: string): AsyncGenerator<string> {
  const res = await fetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ prompt }),
    headers: { "Content-Type": "application/json" },
  });

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    yield decoder.decode(value, { stream: true });
  }
}

// Consumer — processes chunks as they arrive
for await (const chunk of streamChatResponse("Hello")) {
  process.stdout.write(chunk);
}
```

---

### Q8. How do ESM circular imports behave differently from CommonJS?

**CommonJS**: Circular imports return a partially constructed object. If module A requires module B which requires module A, B gets whatever A has exported so far — which may be `{}` if A hasn't finished executing. This silently returns `undefined` for not-yet-exported bindings, causing runtime errors that are hard to trace.

**ESM**: Exports are live bindings. The module graph is analyzed statically before execution. Circular imports work correctly as long as the binding is initialized before it's actually read at runtime (i.e., inside a function body, not at the top level). If you reference a binding before it's initialized, you get a `ReferenceError` — explicit and debuggable.

**Production rule**: Circular imports almost always signal a design problem — extract the shared code to a third module. But when unavoidable (e.g., types in a monorepo), ESM is far safer than CJS.

---

## 4. Advanced Scenario Q&As

---

### A1. You're seeing a memory leak in a long-running Node.js service. Walk through your diagnostic process.

**Immediate steps:**
1. Take a heap snapshot in `node --inspect`, baseline at startup.
2. Run the suspect workload, take a second snapshot.
3. In Chrome DevTools → Memory → Comparison view, sort by "Size Delta" — look for growing object counts.

**Common culprits I've hit in production:**

- **Closures capturing large objects in event handlers never removed** — `EventEmitter.on` without a matching `.off`. Always audit max listeners; Node warns at 11 listeners by default.
- **Timers not cleared** — `setInterval` in a module-level scope that's "reloaded" in development hot reload. Each reload adds a new interval, previous never clears.
- **Promise chains that never resolve** — a `new Promise` where the executor has a code path that calls neither `resolve` nor `reject`. The promise and everything in its closure is retained forever.
- **WeakRef misuse** — using regular `Map` for a component registry when `WeakMap` should be used. Each component instance retained.
- **Async generators not fully consumed** — if you `break` out of a `for await...of` loop, the generator's `return` method should be called (it is, by the spec), but manually created generators from third-party libraries sometimes leak the held resources.

```typescript
// Leak pattern: listener added but never removed
class DataService extends EventEmitter {
  subscribe(handler: (data: unknown) => void) {
    this.on("data", handler); // LEAK if caller never calls unsubscribe
  }
  unsubscribe(handler: (data: unknown) => void) {
    this.off("data", handler); // must call this
  }
}
```

---

### A2. Explain temporal dead zone and how it affects module initialization order.

TDZ applies to `let` and `const` — the binding exists in the scope from the start of the block but is uninitialized until the declaration line runs. Accessing it before initialization throws a `ReferenceError`.

```typescript
console.log(x); // ReferenceError: Cannot access 'x' before initialization
let x = 5;

console.log(y); // undefined (var is hoisted AND initialized to undefined)
var y = 5;
```

**Module initialization TDZ trap:**

```typescript
// moduleA.ts
import { b } from "./moduleB"; // circular — moduleB also imports from moduleA
export const a = 1;
export function useB() { return b; } // safe: called after init

console.log(b); // ReferenceError in some bundler/Node configurations
// At this point, moduleB hasn't finished initializing 'b' yet
```

**Production impact**: In large applications with Webpack/Rollup, circular module initialization can cause `undefined` on `const` exports if the execution order places the consumer before the provider. Static analysis tools like `eslint-plugin-import` catch most of these, but always check bundle entry ordering for shared utilities.

---

### A3. How would you implement a reactive state system using Proxy that supports nested objects?

```typescript
type Effect = () => void;

const effectStack: Effect[] = [];
const dependencies = new WeakMap<object, Map<string, Set<Effect>>>();

function track(target: object, key: string) {
  const currentEffect = effectStack[effectStack.length - 1];
  if (!currentEffect) return;
  if (!dependencies.has(target)) dependencies.set(target, new Map());
  const targetMap = dependencies.get(target)!;
  if (!targetMap.has(key)) targetMap.set(key, new Set());
  targetMap.get(key)!.add(currentEffect);
}

function trigger(target: object, key: string) {
  dependencies.get(target)?.get(key)?.forEach((eff) => eff());
}

function reactive<T extends object>(target: T): T {
  return new Proxy(target, {
    get(obj, key: string, receiver) {
      track(obj, key);
      const val = Reflect.get(obj, key, receiver);
      // Recursively wrap nested objects
      return val !== null && typeof val === "object" ? reactive(val as object) : val;
    },
    set(obj, key: string, value, receiver) {
      const result = Reflect.set(obj, key, value, receiver);
      trigger(obj, key);
      return result;
    },
  });
}

function effect(fn: Effect) {
  effectStack.push(fn);
  fn(); // initial run collects dependencies
  effectStack.pop();
}

// Usage
const state = reactive({ user: { name: "Alice", age: 30 } });
effect(() => console.log(`Name: ${state.user.name}`));
state.user.name = "Bob"; // triggers effect → logs "Name: Bob"
```

---

### A4. How do you handle Promise.all when some requests should be fire-and-forget vs awaited?

```typescript
// Pattern: structured concurrency with mixed criticality
async function loadDashboard(userId: string) {
  // Critical path — all must succeed
  const [profile, permissions] = await Promise.all([
    fetchProfile(userId),
    fetchPermissions(userId),
  ]);

  // Non-critical — log failures but don't block render
  const [analytics, recommendations] = await Promise.allSettled([
    fetchAnalytics(userId),
    fetchRecommendations(userId),
  ]);

  return {
    profile,
    permissions,
    analytics: analytics.status === "fulfilled" ? analytics.value : null,
    recommendations:
      recommendations.status === "fulfilled" ? recommendations.value : [],
  };
}
```

**The key insight**: `Promise.all` for critical path (fail-fast is correct here), `Promise.allSettled` for non-critical data. Never use `Promise.all` for "nice to have" data — one flaky endpoint will break the entire page.

---

## 5. Senior Trap Questions

---

### Trap 1: "async/await is better than Promises — you should always use it."

**The trap**: Treating async/await as a complete replacement rather than syntactic sugar.

**What gets said wrong**: "async/await is newer and cleaner, just use it everywhere."

**Correct answer**:

async/await IS syntactic sugar over Promises — under the hood, an `async` function returns a Promise and `await` desugars to `.then()`. The behavior is identical. The choice is stylistic and context-dependent.

Where `.then()` chaining is actually cleaner:
- **Fan-out patterns**: `fetchAll().then(transform).then(validate)` is a clean pipeline
- **Partial error handling**: attach `.catch()` at specific stages with different handlers
- **Fire-and-forget with error logging**: `doSomething().catch(logger.error)` — no try/catch boilerplate

Where async/await wins:
- Sequential logic with conditionals (if/else after await)
- Loops with sequential awaits
- Complex error handling with `finally`

```typescript
// Chaining wins: clean transformation pipeline
const result = await fetch(url)
  .then((r) => r.json())
  .then(normalize)
  .then(validate)
  .catch(handleApiError);

// async/await wins: branching logic
async function process(id: string) {
  const item = await fetchItem(id);
  if (item.status === "draft") {
    await publishItem(item);
  }
  return item;
}
```

---

### Trap 2: "setTimeout(fn, 0) runs immediately after the current line."

**The trap**: Assuming delay=0 means zero delay.

**What gets said wrong**: "It runs right after the current function, so you can use it to defer to the next line."

**Correct answer**:

`setTimeout(fn, 0)` enqueues `fn` in the **macrotask queue**. It will only run after:
1. The current call stack fully empties
2. The entire microtask queue drains (all Promise resolutions, queueMicrotask calls)

```typescript
console.log("A");
setTimeout(() => console.log("B"), 0);
Promise.resolve().then(() => console.log("C"));
console.log("D");
// Output: A, D, C, B
// B is last because it's a macrotask; C runs before it (microtask)
```

**Production implication**: If you queue a chain of `setTimeout(fn, 0)` for work that generates Promises inside (e.g., 10 setTimeout calls each doing a fetch), the promise resolutions interleave between macrotasks — not between the setTimeouts. Use `queueMicrotask` if you need to defer while staying in the microtask lane.

---

### Trap 3: "Promise.all fails everything if one promise fails."

**The trap**: Using `Promise.all` for independent operations where partial success is acceptable.

**What gets said wrong**: "Promise.all is the way to run things in parallel."

**Correct answer**:

`Promise.all` rejects immediately when ANY promise rejects — it does not wait for others to settle. The remaining in-flight promises are NOT canceled (JavaScript has no built-in promise cancellation; you need AbortController for that). You get neither the succeeded results nor the error context of the others.

```typescript
// WRONG: one flaky analytics call brings down the whole page load
const [user, orders, analytics] = await Promise.all([
  fetchUser(),    // critical
  fetchOrders(),  // critical
  fetchAnalytics(), // non-critical, flaky
]);

// RIGHT: segregate by criticality
const [user, orders] = await Promise.all([fetchUser(), fetchOrders()]);
const analyticsResult = await Promise.allSettled([fetchAnalytics()]);
const analytics = analyticsResult[0].status === "fulfilled"
  ? analyticsResult[0].value
  : null;
```

**Promise combinator cheat sheet**:
- `Promise.all` — all must succeed; fail-fast on first rejection
- `Promise.allSettled` — wait for all; returns status+value or status+reason for each
- `Promise.race` — first to settle (fulfill OR reject) wins
- `Promise.any` — first to FULFILL wins; rejects only if ALL reject (AggregateError)

---

### Trap 4: "var is just like let but older — it's function-scoped."

**The trap**: Missing the loop closure problem and hoisting semantics.

**What gets said wrong**: "var is function-scoped, let/const are block-scoped — that's the only difference."

**Correct answer**:

Three distinct differences:

1. **Hoisting + initialization**: `var` is hoisted AND initialized to `undefined`. `let`/`const` are hoisted but NOT initialized — accessing them before the declaration throws `ReferenceError` (temporal dead zone).

2. **Block scoping vs function scoping**: `var` leaks out of `if`, `for`, and other blocks.

3. **The loop closure trap**:

```typescript
// Classic interview trap
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0); // prints 3, 3, 3
}
// Why: one var 'i' shared across all iterations; by the time callbacks run, i=3

for (let i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 0); // prints 0, 1, 2
}
// Why: let creates a new binding per iteration — each closure captures its own i
```

**Production impact**: The `var` loop trap has caused real bugs in event handler registration loops. Always use `let`/`const`.

---

### Trap 5: "Arrow functions have their own `this`, just like regular functions."

**The trap**: Inverting the actual behavior.

**What gets said wrong**: "Arrow functions create their own execution context so `this` is the arrow function."

**Correct answer**:

Arrow functions do NOT have their own `this`. They capture `this` from the **lexical enclosing scope** at definition time — it's fixed, never rebound by `.call()`, `.apply()`, `.bind()`, or `new`.

```typescript
class Timer {
  count = 0;

  startBroken() {
    // Regular function: 'this' is rebound by setTimeout to global/undefined
    setInterval(function () {
      this.count++; // TypeError in strict mode — 'this' is undefined
    }, 1000);
  }

  startCorrect() {
    // Arrow function: 'this' is captured from startCorrect's scope = the Timer instance
    setInterval(() => {
      this.count++; // works correctly
    }, 1000);
  }
}
```

**The deeper trap**: Arrow functions also cannot be used as constructors (`new ArrowFn()` throws), have no `arguments` object, and cannot be generator functions.

---

### Trap 6: "WeakMap is just a Map with weak keys — use it wherever you want."

**The trap**: Not understanding the constraints that come with weakness.

**What gets said wrong**: "WeakMap is a performance optimization over Map."

**Correct answer**:

WeakMap has severe constraints with good reason:

1. **Keys must be objects** (or registered symbols) — no primitives
2. **Not iterable** — no `.keys()`, `.values()`, `.entries()`, `.forEach()`, `for...of`
3. **No `.size`** — you can't count entries
4. **Keys are held weakly** — if no other reference to the key object exists, the entry is eligible for GC

These constraints ENABLE the use case: associating metadata with objects you don't own, without preventing their garbage collection.

```typescript
// RIGHT USE: DOM node metadata that shouldn't block GC
const nodeData = new WeakMap<Element, { clickCount: number }>();

document.querySelectorAll("button").forEach((btn) => {
  nodeData.set(btn, { clickCount: 0 });
  btn.addEventListener("click", () => {
    const data = nodeData.get(btn)!;
    data.clickCount++;
  });
});
// When buttons are removed from DOM and dereferenced, entries are GC'd automatically

// WRONG USE: when you need to iterate all entries or count them
// (WeakMap can't do this — use Map instead)
```

---

## 6. Production Code Examples

### Execution Context & Hoisting

```typescript
// Demonstrates hoisting, TDZ, and scope chain in one example
var globalLeak = "I am on global scope";

function outer() {
  console.log(typeof innerVar); // "undefined" — var hoisted, not initialized
  // console.log(blockLet);    // ReferenceError — TDZ

  var innerVar = "function scope";

  if (true) {
    let blockLet = "block scope";
    var stillFunctionScoped = "leaked";
    console.log(blockLet); // accessible
  }

  // console.log(blockLet); // ReferenceError — out of block scope
  console.log(stillFunctionScoped); // "leaked" — var escapes block
}
```

---

### Module Pattern with Closures

```typescript
// Pre-ES6 module pattern — still seen in legacy codebases and interview questions
const ApiClient = (() => {
  let authToken: string | null = null; // private, inaccessible from outside
  let requestCount = 0;

  function buildHeaders(): Record<string, string> {
    return authToken ? { Authorization: `Bearer ${authToken}` } : {};
  }

  return {
    authenticate(token: string) {
      authToken = token;
    },
    async get<T>(url: string): Promise<T> {
      requestCount++;
      const res = await fetch(url, { headers: buildHeaders() });
      return res.json() as Promise<T>;
    },
    getStats() {
      return { requestCount };
    },
  };
})();

ApiClient.authenticate("my-token");
const data = await ApiClient.get<User[]>("/api/users");
```

---

### Prototype Chain

```typescript
function Animal(name: string) {
  this.name = name;
}
Animal.prototype.speak = function () {
  return `${this.name} makes a sound`;
};

function Dog(name: string, breed: string) {
  Animal.call(this, name); // borrow constructor
  this.breed = breed;
}
Dog.prototype = Object.create(Animal.prototype); // set up chain
Dog.prototype.constructor = Dog; // repair constructor reference
Dog.prototype.bark = function () {
  return `${this.name} barks!`;
};

const rex = new Dog("Rex", "Lab");
console.log(rex.speak()); // walks prototype chain to Animal.prototype
console.log(rex instanceof Dog);   // true
console.log(rex instanceof Animal); // true — chain works
```

---

### Promise Combinators in a Data Fetching Pipeline

```typescript
interface DashboardData {
  profile: User;
  feed: Post[];
  trending: Topic[] | null;
  notifications: Notification[] | null;
}

async function loadDashboard(userId: string): Promise<DashboardData> {
  // Stage 1: Critical — fail fast
  const [profile, feed] = await Promise.all([
    fetchProfile(userId),
    fetchFeed(userId),
  ]);

  // Stage 2: Non-critical — never fail the page
  const optionalResults = await Promise.allSettled([
    fetchTrending(),
    fetchNotifications(userId),
  ]);

  const [trendingResult, notifResult] = optionalResults;

  return {
    profile,
    feed,
    trending: trendingResult.status === "fulfilled" ? trendingResult.value : null,
    notifications: notifResult.status === "fulfilled" ? notifResult.value : null,
  };
}
```

---

### Async Generator for Paginated API

```typescript
async function* paginate<T>(
  fetchPage: (cursor: string | null) => Promise<{ items: T[]; nextCursor: string | null }>
): AsyncGenerator<T> {
  let cursor: string | null = null;

  do {
    const { items, nextCursor } = await fetchPage(cursor);
    for (const item of items) yield item;
    cursor = nextCursor;
  } while (cursor !== null);
}

// Consumer — process each record as it arrives, no full load into memory
const allUsers = paginate((cursor) =>
  fetch(`/api/users?cursor=${cursor ?? ""}`).then((r) => r.json())
);

for await (const user of allUsers) {
  await processUser(user); // handles one at a time
}
```

---

### Proxy-Based Validation

```typescript
function createValidated<T extends object>(
  target: T,
  validators: Partial<Record<keyof T, (val: unknown) => boolean>>
): T {
  return new Proxy(target, {
    set(obj, key: string, value) {
      const validate = validators[key as keyof T];
      if (validate && !validate(value)) {
        throw new TypeError(`Invalid value for ${key}: ${value}`);
      }
      return Reflect.set(obj, key, value);
    },
  });
}

const user = createValidated(
  { name: "", age: 0 },
  {
    name: (v) => typeof v === "string" && v.length > 0,
    age: (v) => typeof v === "number" && v >= 0 && v < 150,
  }
);

user.name = "Alice";  // ok
user.age = -5;        // TypeError: Invalid value for age: -5
```

---

## 7. Interview Cheat Sheet

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    JAVASCRIPT 15-YOE INTERVIEW CHEAT SHEET                 ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  EVENT LOOP EXECUTION ORDER                                                 ║
║  ─────────────────────────                                                  ║
║  1. Synchronous code (call stack)                                           ║
║  2. Microtasks (drain ALL): Promise.then, queueMicrotask, MutationObserver ║
║  3. ONE Macrotask: setTimeout, setInterval, I/O, MessageChannel            ║
║  4. Repeat from 2                                                           ║
║                                                                              ║
║  PROMISE COMBINATOR QUICK REFERENCE                                         ║
║  ──────────────────────────────────                                         ║
║  Promise.all(arr)        → fail-fast; use for critical parallel calls      ║
║  Promise.allSettled(arr) → all settle; use for non-critical parallel calls ║
║  Promise.race(arr)       → first to settle (fulfill OR reject) wins        ║
║  Promise.any(arr)        → first to FULFILL wins; AggregateError if all    ║
║                            reject                                           ║
║                                                                              ║
║  SCOPE & HOISTING                                                            ║
║  ────────────────                                                            ║
║  var   → function-scoped, hoisted + initialized (undefined), no TDZ        ║
║  let   → block-scoped, hoisted + UNINITIALIZED, TDZ until declaration      ║
║  const → block-scoped, TDZ, must be initialized at declaration             ║
║  Loop closures → use let (new binding per iteration), NOT var              ║
║                                                                              ║
║  THIS BINDING RULES                                                          ║
║  ──────────────────                                                          ║
║  Regular function → depends on call site                                    ║
║  Arrow function   → lexical this (fixed at definition, not rebindable)     ║
║  .call/.apply/.bind → explicit this (doesn't work on arrows)               ║
║  new              → creates new object as this                             ║
║                                                                              ║
║  WEAK COLLECTION USE CASES                                                  ║
║  ─────────────────────────                                                  ║
║  WeakMap  → metadata on objects you don't own; cache keyed by objects      ║
║  WeakSet  → track which objects have been processed (visited sets)         ║
║  WeakRef  → hold reference without preventing GC; use FinalizationRegistry ║
║  NOTE     → all non-iterable, no .size — that's intentional                ║
║                                                                              ║
║  ABORTCONTROLLER CHECKLIST                                                  ║
║  ─────────────────────────                                                  ║
║  □ Create new AbortController per request/effect                           ║
║  □ Pass signal to fetch AND any sub-operations                             ║
║  □ Always clearTimeout in finally when using timeout pattern               ║
║  □ Catch AbortError separately from other errors                           ║
║  □ In useEffect, return () => controller.abort() as cleanup                ║
║                                                                              ║
║  GENERATOR QUICK REFERENCE                                                  ║
║  ─────────────────────────                                                  ║
║  function* gen()   → synchronous generator                                 ║
║  yield value       → pause + emit value                                    ║
║  yield* iterable   → delegate to another iterable                         ║
║  async function*   → async generator; use for await...of to consume        ║
║  for...of breaks   → calls generator.return() — trigger cleanup there     ║
║                                                                              ║
║  COMMON MEMORY LEAK PATTERNS                                                ║
║  ────────────────────────────                                               ║
║  □ EventEmitter.on without .off                                            ║
║  □ setInterval/setTimeout not cleared in useEffect cleanup                 ║
║  □ Closures capturing large objects in long-lived handlers                 ║
║  □ Map/Set used as cache without eviction or WeakMap                       ║
║  □ Promise that never resolves (neither resolve nor reject called)         ║
║  □ AbortController signals not aborted on component unmount                ║
║                                                                              ║
║  PROTOTYPE CHAIN                                                             ║
║  ───────────────                                                             ║
║  Object.create(proto)  → set prototype without constructor                 ║
║  class X extends Y     → syntactic sugar, still prototype delegation       ║
║  instanceof            → walks prototype chain                             ║
║  Object.getPrototypeOf → read prototype slot                               ║
║  hasOwnProperty        → check own vs inherited                            ║
║                                                                              ║
║  ESM vs CJS                                                                  ║
║  ─────────                                                                  ║
║  ESM: static imports, live bindings, async module loading, tree-shakeable  ║
║  CJS: dynamic require(), copied values at require time, sync               ║
║  Circular imports: CJS → partial object (silent undefined); ESM → TDZ if  ║
║  top-level, ok inside functions                                             ║
║  Dynamic import(): ESM only, returns Promise<module>, code-splitting       ║
║                                                                              ║
║  TOP TRAP ANSWERS (one line each)                                           ║
║  ─────────────────────────────────                                          ║
║  async/await vs promises → same behavior; sugar over .then()               ║
║  setTimeout(fn,0)        → macrotask; runs AFTER all microtasks drain      ║
║  Promise.all failure     → use allSettled for partial failures             ║
║  var in loop closures    → always use let; new binding per iteration       ║
║  arrow this              → NO own this; captures lexical this              ║
║  WeakMap not Map         → when keys are objects and GC must be allowed    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Appendix: Quick Mental Models

**Event Loop = Waiter Model**
The JS engine is one waiter. It handles one table (task) at a time. Before going to the next table, it MUST check the urgent messages board (microtasks) and clear it entirely. Only then does it look at the reservation list (macrotask queue) for the next table.

**Closures = Backpacks**
Every function carries a backpack containing references to variables from its enclosing scope at the time the function was defined. The backpack contents stay alive as long as the function lives.

**Prototype Chain = Inheritance by Lookup, Not Copy**
Reading a property walks up the chain. Writing a property always creates on the object itself. This is why mutations to a prototype property from one instance don't affect others — as soon as you write, the lookup short-circuits on the own property.

**Proxy = Intercepted Property Access**
Think of a Proxy as a doorman standing in front of an object. Every get, set, has, delete — the doorman intercepts and can run arbitrary logic. Reflect calls the "natural" behavior behind the doorman. Vue 3's reactivity is exactly this.

**Generators = Pauseable Functions**
Normal functions run to completion. Generators are functions with a remote control. `yield` is the pause button. The caller holds the remote. This makes them ideal for lazy sequences (infinite ranges, streaming data) and coroutines.
