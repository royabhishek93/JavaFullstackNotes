# Structured Logger with Context Injection
> **Topic:** Currying | **Level:** Intermediate | **Frequency:** Medium

## The Setup
You are building observability infrastructure at Netflix. Each service needs structured logging where every log line carries a correlation ID (set at request entry), a service name (set at deployment), and a severity level (set at the log call site). Logs go to Elasticsearch and must be parseable JSON. The logging utility is used in hundreds of modules and must be zero-overhead when the severity is below the configured threshold.

## The Question
Design the logger using currying so that context is injected at the appropriate layer, log calls at usage sites are minimal, and severity filtering happens before object allocation.

## Diagram
```
  logger(config)(correlationId)(level)(message)

  ┌─────────────────────────────────────────────────────┐
  │  At service init:                                   │
  │  const svcLog = logger({ service: 'api-gateway',   │
  │                           minLevel: 'info' })       │
  │  ← service name and threshold locked in             │
  └─────────────────────────────────────────────────────┘
                      │
  ┌─────────────────────────────────────────────────────┐
  │  At request entry (middleware):                     │
  │  const reqLog = svcLog(req.headers['x-request-id'])│
  │  ← correlationId locked in for this request        │
  └─────────────────────────────────────────────────────┘
                      │
  ┌─────────────────────────────────────────────────────┐
  │  At usage:                                          │
  │  reqLog('info')('User authenticated');              │
  │  reqLog('error')('DB connection failed');           │
  │  ← just level + message, everything else inherited  │
  └─────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)
The curried shape means each layer only knows what it needs. The module registering the service name does not know about request IDs. The middleware injecting the request ID does not know about what level individual log calls will use. The feature code writing the log does not need to pass service name or request ID — both are already in the closure.

```js
const logger = (config) => (correlationId) => (level) => (message) => {
  const levels = { debug: 0, info: 1, warn: 2, error: 3 };
  if (levels[level] < levels[config.minLevel]) return; // short-circuit before alloc

  const entry = {
    timestamp: new Date().toISOString(),
    service:   config.service,
    correlationId,
    level,
    message,
  };
  process.stdout.write(JSON.stringify(entry) + '\n');
};

// Service init
const svcLog = logger({ service: 'payment-service', minLevel: 'info' });

// Request middleware
app.use((req, res, next) => {
  req.log = svcLog(req.headers['x-correlation-id'] || crypto.randomUUID());
  next();
});

// Feature handler
app.post('/charge', (req, res) => {
  req.log('info')('Charge initiated');
  req.log('error')('Stripe timeout');
});
```

The severity check before JSON object allocation is a real production concern. At Netflix's log volume, even allocating an object that is immediately discarded adds GC pressure. The curried form enables that check at the level layer — if `level < minLevel`, we return before building the log entry.

The pattern also composes naturally with log sampling. You can replace the inner function with one that samples at a percentage: `if (Math.random() > config.sampleRate) return;` — inserted at the `correlationId` layer so debug logs are sampled per-request, not per-call.

## Follow-up
**Q:** How would you add structured metadata (request path, user ID) to every log line without changing call sites?

**A:** Add a metadata layer between the correlationId and level layers. Middleware builds `req.log = svcLog(correlationId)({ path: req.path, userId: req.user?.id })`, and the innermost function merges this metadata into the log entry. Call sites do not change — they still call `req.log('info')('message')`.
