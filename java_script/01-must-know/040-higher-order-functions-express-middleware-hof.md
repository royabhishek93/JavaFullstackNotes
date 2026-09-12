# Express Middleware HOF Chain
> **Topic:** Higher-Order Functions | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A Myntra API needs every authenticated endpoint to: validate JWT, check rate limits, log the request, and then run the route handler. A junior is copying these three checks into every controller function.

## The Question
Redesign using HOF-based middleware composition and explain the `next` callback contract.

## Diagram

```
Express middleware — a left-to-right HOF chain:

  Request arrives
       |
       v
  +-------------+    next()   +-----------+    next()   +--------+    next()   +---------+
  | validateJwt | ----------> | rateLimit | ----------> |  log   | ----------> | handler |
  |  (HOF/mw)   |             |  (HOF/mw) |             | (HOF)  |             | (plain) |
  +-------------+             +-----------+             +--------+             +---------+
       |                           |                                                 |
    next(err)                   next(err)                                         res.json
       |                           |
       v                           v
  +----------------+          +----------------+
  | errorHandler   |          | errorHandler   |  (Express calls error handler when next(err))
  +----------------+          +----------------+

  Each middleware = (req, res, next) => { /* work */ next() or next(err) or res.end() }
  HOF pattern: factory that returns a middleware function pre-configured with options
```

## Model Answer (15 YOE)

```js
// Middleware factories — HOFs that return configured middleware
function requireAuth(options = {}) {
  return (req, res, next) => {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return next({ status: 401, message: 'No token' });
    try {
      req.user = jwt.verify(token, process.env.JWT_SECRET, options);
      next();
    } catch (e) {
      next({ status: 401, message: 'Invalid token' });
    }
  };
}

function rateLimit(maxPerMinute) {
  const counts = new Map(); // in production: use Redis
  return (req, res, next) => {
    const key = req.user?.id || req.ip;
    const count = (counts.get(key) || 0) + 1;
    counts.set(key, count);
    setTimeout(() => counts.set(key, counts.get(key) - 1), 60000);
    if (count > maxPerMinute) return next({ status: 429, message: 'Rate limit exceeded' });
    next();
  };
}

function requestLogger(req, res, next) { // not a factory — no config needed
  const start = Date.now();
  res.on('finish', () => logger.info({ method: req.method, url: req.url, ms: Date.now() - start }));
  next();
}

// Apply once to a router — DRY, no duplication in controllers
const authRouter = express.Router();
authRouter.use(requireAuth({ algorithms: ['HS256'] }));
authRouter.use(rateLimit(100));
authRouter.use(requestLogger);

authRouter.get('/cart',    cartController.get);
authRouter.post('/order',  orderController.create);
// ... all routes get the three middleware for free

// Centralized error handler (receives next(err) calls)
app.use((err, req, res, next) => {
  res.status(err.status || 500).json({ error: err.message });
});
```

The `next` callback is the HOF mechanism: Express calls each middleware with `next` — the middleware calls `next()` to pass control forward, `next(err)` to skip to the error handler, or responds directly to short-circuit. This is a manually managed callback chain. The factory pattern (`requireAuth(options)`, `rateLimit(100)`) lets you configure once and reuse across routers without global state.

## Follow-up

**Q:** How would you make `rateLimit` production-safe with Redis instead of an in-process Map?

**A:** Replace the Map with `ioredis` and an atomic `INCR` + `EXPIRE` sequence: `await redis.multi().incr(key).expire(key, 60).exec()`. The `incr` returns the new count atomically — if it equals 1, the key just appeared and `expire` is set once. This is safe across multiple Node.js instances. The factory interface (`rateLimit(100)`) does not change — only the implementation inside the returned middleware changes. That is the value of the HOF factory: callers are decoupled from the storage backend.
