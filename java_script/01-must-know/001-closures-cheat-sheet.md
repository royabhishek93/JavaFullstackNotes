# Closures — Cheat Sheet
> **Topic:** Closures | **Level:** Reference | **Frequency:** Always

```js
// ─── CORE SHAPE ───────────────────────────────────────────────────────────
function outer() {
  const secret = 42;               // lives in closure env
  return function inner() {
    return secret;                 // inner closes over secret
  };
}
const fn = outer();
fn(); // 42 — outer's execution context gone, but secret survives

// ─── FACTORY FUNCTION ─────────────────────────────────────────────────────
function makeAdder(x) {
  return (y) => x + y;             // x is closed over per call
}
const add5 = makeAdder(5);
add5(3);  // 8 — independent from makeAdder(10)

// ─── PRIVATE STATE (Counter) ──────────────────────────────────────────────
function makeCounter() {
  let count = 0;                   // unreachable from outside
  return {
    increment: () => ++count,
    decrement: () => --count,
    value:     () => count,
  };
}
const c = makeCounter();
c.increment(); // 1
c.value();     // 1

// ─── MODULE PATTERN ───────────────────────────────────────────────────────
const PaymentSDK = (function () {
  let apiKey = null;               // private
  function _validate(k) { return k.startsWith('rzp_'); } // private
  return {
    init:   (key) => { if (_validate(key)) apiKey = key; },
    charge: (amt) => { /* uses apiKey */ },
  };
})();

// ─── MEMOIZE UTILITY ──────────────────────────────────────────────────────
function memoize(fn) {
  const cache = new Map();         // private, per-instance
  return function (...args) {
    const key = JSON.stringify(args);
    if (cache.has(key)) return cache.get(key);
    const result = fn(...args);
    cache.set(key, result);
    return result;
  };
}

// ─── STALE CLOSURE IN REACT — THE TRAP ───────────────────────────────────
// BAD: eta is captured from render 1, never updates
useEffect(() => {
  const id = setInterval(() => console.log(eta), 5000);
  return () => clearInterval(id);
}, []); // empty array = stale closure

// FIX 1: useRef for latest value
const etaRef = useRef(eta);
useEffect(() => { etaRef.current = eta; }, [eta]);
useEffect(() => {
  const id = setInterval(() => console.log(etaRef.current), 5000);
  return () => clearInterval(id);
}, []); // reads ref.current at execution time, not closure time

// FIX 2: functional setState (when new value derives from old)
setCount(prev => prev + 1); // never stale, always uses latest

// ─── LOOP BUG ─────────────────────────────────────────────────────────────
// BAD: var — all callbacks share same i
for (var i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 100); // prints 3, 3, 3
}

// GOOD: let — each iteration gets its own binding
for (let i = 0; i < 3; i++) {
  setTimeout(() => console.log(i), 100); // prints 0, 1, 2
}

// ─── GOTCHAS ──────────────────────────────────────────────────────────────
// 1. Closure captures REFERENCE, not value — mutations are visible
// 2. Objects in closure are not deep-cloned — shared mutation is possible
// 3. Closure over large object = that object stays in heap until closure is GC'd
// 4. window/document listeners must be removed on unmount — they outlive components
// 5. Async callbacks (setTimeout, fetch .then) always carry render-time snapshots
```
