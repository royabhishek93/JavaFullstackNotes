# Event Emitter — Cheat Sheet
> **Topic:** Event Emitter | **Level:** Reference | **Frequency:** High

```
CORE DATA STRUCTURE
───────────────────
  Map<string, Function[]>   (or plain object — Map is safer)
  Key   = event name
  Value = array of listener functions

API REFERENCE
─────────────
  on(event, fn)         push fn to listeners[event]
  off(event, fn)        filter fn out of listeners[event]  ← needs exact reference
  emit(event, ...args)  [...listeners[event]].forEach(fn => fn(...args))
  once(event, fn)       register wrapper that calls fn then calls off(wrapper)

IMPLEMENTATION RULES
─────────────────────
  1. Snapshot listeners before iterating: [...listeners[event]].forEach(...)
     → prevents mutation bugs when a listener calls off() during emit
  2. Return `this` from on/off/emit/once → enables fluent chaining
  3. emit() is SYNCHRONOUS — all listeners run before emit() returns
  4. once() stores the WRAPPER, not the original fn
     → off(event, originalFn) after once() is a silent no-op
  5. Use Map, not plain object — avoids __proto__ / constructor key collisions

FULL IMPLEMENTATION
───────────────────
class EventEmitter {
  constructor() {
    this.listeners = new Map();
  }

  on(event, listener) {
    if (!this.listeners.has(event)) this.listeners.set(event, []);
    this.listeners.get(event).push(listener);
    return this;
  }

  off(event, listener) {
    if (!this.listeners.has(event)) return this;
    const updated = this.listeners.get(event).filter(fn => fn !== listener);
    this.listeners.set(event, updated);
    return this;
  }

  emit(event, ...args) {
    if (!this.listeners.has(event)) return this;
    [...this.listeners.get(event)].forEach(fn => fn(...args)); // snapshot!
    return this;
  }

  once(event, listener) {
    const wrapper = (...args) => {
      listener(...args);
      this.off(event, wrapper); // self-remove via closure
    };
    this.on(event, wrapper);
    return this;
  }

  removeAllListeners(event) {
    if (event !== undefined) this.listeners.delete(event);
    else this.listeners.clear();
    return this;
  }

  listenerCount(event) {
    return this.listeners.get(event)?.length ?? 0;
  }
}

SENIOR TRAPS
─────────────
  1. once() + off() with original fn → silent no-op (wrapper is what's stored)
  2. emit() is synchronous → throwing listener stops remaining listeners (add try/catch)
  3. React: no cleanup in useEffect → listeners accumulate on re-mount
  4. Inline arrow fn in off() → new object, indexOf = -1, never removed
  5. Recursive emit → nested synchronous call stacks, ordering surprises

REACT SAFE PATTERN
──────────────────
  useEffect(() => {
    const handler = (data) => doSomething(data);   // named — same reference
    bus.on('event', handler);
    return () => bus.off('event', handler);         // paired cleanup
  }, []);                                           // empty deps — subscribe once

OBSERVER vs PUB/SUB
────────────────────
  Observer:   emitter.on(e, fn)   — direct registration, same process, no broker
  Pub/Sub:    PUBLISH / SUBSCRIBE — broker in middle, cross-process, async

REAL-WORLD USES
───────────────
  Node.js core         → stream.on('data'), server.on('request')
  Browser DOM          → element.addEventListener (EventEmitter pattern)
  Socket.io client     → socket.on('message', fn)
  React event bus      → module-level EventEmitter for cross-component comms
  Custom middleware    → req/res lifecycle hooks in Express-style frameworks
```
