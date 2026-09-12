# once() Self-Removal Mechanism — WebSocket Handshake
> **Topic:** Event Emitter | **Level:** Intermediate | **Frequency:** Medium

## The Setup
A WebSocket client needs to perform a one-time authentication handshake after the connection opens. The connection may be opened multiple times due to reconnection logic. The handshake must fire exactly once per connection — but the listener is registered before any connection is established and must not fire again on reconnections.

## The Question
Explain how `once()` works internally. Implement it. Then show a scenario where it is the correct tool and walk through the execution step-by-step.

## Diagram

```
ONCE WRAPPER MECHANISM
──────────────────────
  once("open", authFn)
       │
       ▼
  wrapper = (...args) => {
    authFn(...args);          // ① run the real handler
    off("open", wrapper);     // ② self-remove from listeners array
  }
       │
       ▼
  on("open", wrapper)   ← wrapper stored in listeners, NOT authFn

EXECUTION:
  First emit("open"):
    listeners["open"] = [wrapper]
    wrapper(socket) runs → authFn(socket) ✓ → off("open", wrapper) → listeners["open"] = []

  Second emit("open") — reconnection:
    listeners["open"] = []  → nothing runs ✓

  off("open", authFn):  ← would NOT work — authFn is not in the array
    indexOf(authFn) = -1 → no-op (this is the trap — see file 06)
```

## Model Answer (15 YOE)

**Implementation:**

```js
once(event, listener) {
  const wrapper = (...args) => {
    listener(...args);
    this.off(event, wrapper); // self-remove — wrapper knows its own ref via closure
  };
  this.on(event, wrapper);
  return this;
}
```

The key insight: `wrapper` is defined with `const`, so the closure captures a reference to `wrapper` itself. When `wrapper` executes, `this.off(event, wrapper)` passes the exact same function object that is stored in the listeners array — the `filter(fn => fn !== wrapper)` in `off()` correctly identifies and removes it.

**Production use — WebSocket authentication handshake:**

```js
const socketBus = new EventEmitter();

// once() guarantees this fires exactly once even if 'open' emits multiple times
socketBus.once('open', (socket) => {
  socket.send(JSON.stringify({ type: 'auth', token: getAuthToken() }));
  console.log('Handshake sent — listener is now removed');
});

// Simulate initial connection + reconnection
socketBus.emit('open', ws1); // → handshake sent, wrapper removed
socketBus.emit('open', ws2); // → nothing (listener array is empty)
```

**Step-by-step trace:**

```
1. once('open', authFn) called
   → wrapper created (closes over authFn and wrapper itself)
   → on('open', wrapper) → listeners.get('open') = [wrapper]

2. emit('open', ws1)
   → snapshot: [wrapper]
   → wrapper(ws1) called:
       a. authFn(ws1) → sends auth message ✓
       b. off('open', wrapper) → filter(fn !== wrapper) → listeners.get('open') = []

3. emit('open', ws2)
   → listeners.get('open') = []
   → forEach over empty array → nothing executes ✓
```

**Other good `once` use cases:**
- Database connection "ready" event — initialize schema once
- User "first visit" modal — show exactly once per session
- Payment "confirmed" event — trigger receipt email exactly once
- Test teardown events — fire assertions after the first matching event

## Follow-up

**Q:** What if you need the handshake to fire once per connection (not once per process lifetime)?
**A:** On each WebSocket reconnect, register a new `once('open', handler)` inside the reconnect logic. Each `once` registration creates a new wrapper and adds it to the listeners array. Since the previous wrapper removed itself, the array is empty at reconnect time — the new registration is the only entry. No duplicates.

**Q:** How is `once` different from unsubscribing manually after the first emission?
**A:** Functionally equivalent, but `once` handles the self-removal atomically inside the emission path. Manual unsubscribe requires the caller to hold the reference and call `off()` — which breaks for listeners that need to fire in order (if another listener earlier in the array fires `off()` during the same `emit`, the snapshot pattern in `emit` ensures the current run still completes).
