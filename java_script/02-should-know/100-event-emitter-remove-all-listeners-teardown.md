# removeAllListeners and Session Teardown
> **Topic:** Event Emitter | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A real-time dashboard instantiates an EventEmitter per user session. Each session registers dozens of listeners across multiple event channels. When the session expires — tab close, timeout, or user logout — the dashboard must release all listeners so the garbage collector can reclaim the session object and all its closures. Without teardown, long-running Node.js servers accumulate dead sessions that are never collected.

## The Question
Implement `removeAllListeners(event?)` on your EventEmitter. Show how to use it for session teardown, and add a `listenerCount()` health check that can detect leaks before they cause memory pressure.

## Diagram

```
Session lifecycle:

  Session created → eventBus per session instantiated
  Listeners registered:
    sessionBus.on('data.update', handler1)   → listeners['data.update']  = [handler1]
    sessionBus.on('alert',       handler2)   → listeners['alert']        = [handler2]
    sessionBus.on('data.update', handler3)   → listeners['data.update']  = [handler1, handler3]

  Session expires (tab close / timeout):
    sessionBus.removeAllListeners()          → listeners Map cleared
    sessionBus = null                        → bus GC eligible

  Without teardown:
    listeners hold closures → closures hold references to session data
    → session data cannot be GC'd → memory grows linearly with active sessions
    → Node.js heap grows until OOM or process restart

  Health check (every 30s):
    if listenerCount('data.update') > 20 → probable leak → alert
```

## Model Answer (15 YOE)

```js
// Add to EventEmitter class:

removeAllListeners(event?: string) {
  if (event !== undefined) {
    this.listeners.delete(event); // remove one event's listener array
  } else {
    this.listeners.clear();       // remove all events — nuclear teardown
  }
  return this;
}

listenerCount(event: string): number {
  return this.listeners.get(event)?.length ?? 0;
}
```

**Session teardown pattern:**

```ts
class UserSession {
  private bus = new EventEmitter();
  private sessionId: string;

  constructor(sessionId: string) {
    this.sessionId = sessionId;
    this.wire();
  }

  private wire() {
    this.bus.on('data.update', this.handleDataUpdate.bind(this));
    this.bus.on('alert',       this.handleAlert.bind(this));
    this.bus.on('ping',        this.handlePing.bind(this));
  }

  destroy() {
    this.bus.removeAllListeners(); // release all listener closures
    this.bus = null!;              // allow bus itself to be GC'd
    // at this point, no closure in the bus holds a reference to this session
  }

  // ... handlers
}

// Session registry:
const sessions = new Map<string, UserSession>();

function expireSession(sessionId: string) {
  const session = sessions.get(sessionId);
  if (session) {
    session.destroy();     // tears down all bus listeners
    sessions.delete(sessionId); // removes the session from the registry
    // session and bus are now eligible for GC
  }
}
```

**Health check — detect leaks before OOM:**

```js
setInterval(() => {
  for (const [event, fns] of sessionBus.listeners) {
    if (fns.length > 20) {
      alerting.warn(
        `Possible listener leak: "${event}" has ${fns.length} listeners`,
        { sessionId, event }
      );
    }
  }
}, 30_000);
```

Node.js's built-in `EventEmitter` emits a `MaxListenersExceededWarning` when a single event accumulates more than 10 listeners (configurable via `setMaxListeners()`). This is the production-grade version of the same health check. In browser JS, there is no equivalent — you must instrument it yourself.

**`removeAllListeners(event)` vs `removeAllListeners()`:**

- `removeAllListeners('data.update')` — surgical: removes only the `'data.update'` listener array, other events untouched. Use when a feature is disabled but the session continues.
- `removeAllListeners()` — nuclear: clears the entire `Map`. Use only on full session teardown or test cleanup between test cases.

## Follow-up

**Q:** Why does holding a reference to a listener function prevent GC of the session object?
**A:** JavaScript closures capture variables from their enclosing scope. A listener function defined as `this.handleDataUpdate.bind(this)` holds a reference to `this` (the session). As long as the listener is in the EventEmitter's array, the array → listener → session chain keeps the session in the reference graph — the GC cannot collect it. `removeAllListeners()` breaks this chain by emptying the array.

**Q:** Is `removeAllListeners()` safe to call if some listeners are in the middle of processing an emit?
**A:** Yes, because `emit()` snapshots the listener array with `[...this.listeners.get(event)]` before iterating. The in-progress iteration runs on the snapshot. `removeAllListeners()` clears `this.listeners` (the source), but the snapshot is unaffected. The current emit completes normally; subsequent emits see an empty listeners map.
