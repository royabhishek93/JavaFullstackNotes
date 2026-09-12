# Currying — Cheat Sheet
> **Topic:** Currying | **Level:** Reference | **Frequency:** Always

```js
// ─── BASIC SHAPE ──────────────────────────────────────────────────────────
// ES5
function add(a) {
  return function(b) {
    return function(c) { return a + b + c; };
  };
}

// Modern arrow (preferred)
const add = a => b => c => a + b + c;

add(1)(2)(3);            // 6
const add10 = add(10);   // partial application
add10(5)(3);             // 18

// ─── GENERIC CURRY UTILITY ────────────────────────────────────────────────
function curry(fn) {
  return function curried(...args) {
    if (args.length >= fn.length) {
      return fn.apply(this, args);
    }
    return (...moreArgs) => curried.apply(this, args.concat(moreArgs));
  };
}

const sum = curry((a, b, c) => a + b + c);
sum(1)(2)(3);    // 6
sum(1, 2)(3);    // 6 — grouped args also work
sum(1)(2, 3);    // 6

// ─── FN.LENGTH GOTCHA ─────────────────────────────────────────────────────
function f(a, b = 0) {}  // f.length === 1 (NOT 2)
function g(...args) {}   // g.length === 0

// Fix: pass arity explicitly
function curryN(fn, n) {
  return function curried(...args) {
    if (args.length >= n) return fn.apply(this, args);
    return (...more) => curried.apply(this, args.concat(more));
  };
}

// ─── PARTIAL APPLICATION ──────────────────────────────────────────────────
// Currying: strictly one arg per step
const curriedAdd = a => b => c => a + b + c;

// Partial application: fix any number of args, rest later
const addFrom1and2 = add.bind(null, 1, 2); // fixes two at once
addFrom1and2(3); // 6

// ─── REACT EVENT HANDLER PATTERN ─────────────────────────────────────────
const handleChange = useCallback(
  (field) => (event) => {
    setForm(prev => ({ ...prev, [field]: event.target.value }));
  }, []
);

// In JSX — handleChange is stable, handleChange('name') creates new fn each render
// For true stability, also useMemo on the invocation:
const handleNameChange = useMemo(() => handleChange('name'), [handleChange]);

<input onChange={handleNameChange} />

// ─── LOGGER PATTERN ───────────────────────────────────────────────────────
const logger = (service) => (correlationId) => (level) => (msg) =>
  console.log(JSON.stringify({ service, correlationId, level, msg,
                                ts: Date.now() }));

const svcLog = logger('order-service');       // at startup
const reqLog = svcLog(req.headers['x-rid']);  // at request entry
reqLog('info')('Order created');              // at call site

// ─── API CLIENT PATTERN ───────────────────────────────────────────────────
const apiClient = (baseUrl) => (token) => (endpoint) => (params = {}) =>
  fetch(`${baseUrl}${endpoint}`, {
    headers: { Authorization: `Bearer ${token}` },
    ...params,
  });

const api      = apiClient('https://api.example.com/v2');
const authed   = api(session.token);
authed('/users')({ method: 'GET' });
authed('/orders')({ method: 'POST', body: JSON.stringify(order) });

// ─── CURRYING vs PARTIAL APPLICATION ─────────────────────────────────────
// Currying:            f(a, b, c) → f(a)(b)(c), one arg per step
// Partial application: f(a, b, c) → g(c), fix any number of leading args
// A curried call IS partial application. Partial application is NOT always currying.

// ─── DO NOT SAY IN AN INTERVIEW ──────────────────────────────────────────
// "Currying and partial application are the same thing" — they are not
// "Currying improves performance" — it adds tiny overhead per intermediate call
// "fn.length always gives the arity" — fails with defaults and rest params
```
