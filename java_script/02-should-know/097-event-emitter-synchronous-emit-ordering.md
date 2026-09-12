# Synchronous Emit Ordering — The Recursive Emit Trap
> **Topic:** Event Emitter | **Level:** Senior Trap | **Frequency:** Medium

## The Setup
A developer is debugging unexpected call ordering in a production event pipeline. A listener for `'data'` emits the same `'data'` event (to re-process transformed data). The output order is surprising. The interviewer shows the code and asks you to predict the exact console output and explain why.

## The Question
`emit()` in a standard EventEmitter is synchronous. What does that mean for execution ordering? Predict the output of the following code and explain the mechanism:

```js
emitter.on('data', () => {
  console.log('listener A start');
  emitter.emit('data', 'recursive');
  console.log('listener A end');
});
emitter.on('data', () => console.log('listener B'));

emitter.emit('data', 'first');
```

## Diagram

```
Call stack when emit('data', 'first') is called:

emit('data', 'first')                   ← outer emit
  └── listener A('first')
        console.log('listener A start')
        └── emit('data', 'recursive')   ← inner emit — synchronous call stack push
              └── listener A('recursive')
                    console.log('listener A start')    [2]
                    emit('data', 'recursive²')  ... (infinite if unchecked)
                    (stopped here for illustration)
                    console.log('listener A end')      [3]
              └── listener B('recursive')
                    console.log('listener B')          [4]
             ← inner emit returns
        console.log('listener A end')                  [5]
  └── listener B('first')
        console.log('listener B')                      [6]
```

## Model Answer (15 YOE)

**Output (for a single recursive call, not infinite):**

```
listener A start      ← outer emit, listener A begins
listener A start      ← inner emit (recursive), listener A begins again
listener A end        ← inner emit's listener A ends
listener B            ← inner emit's listener B
listener A end        ← outer emit's listener A ends
listener B            ← outer emit's listener B
```

**Why this happens:**

`emit()` is a synchronous function call — it iterates over listeners and calls each one before returning. When listener A calls `emit()` recursively, that inner `emit()` also runs synchronously on the same call stack, running through all listeners again before returning. The outer `emit()`'s iteration is paused (its call stack frame is suspended) while the inner `emit()` runs to completion.

This is depth-first traversal of a call tree, not a queue. There is no async scheduling, no microtask queue involvement, no `setTimeout`.

**The practical implication:**

Every listener runs to completion before the next one starts. A listener that does heavy synchronous work blocks the entire emit chain — and the caller that triggered `emit()` is blocked for that entire duration. Never do synchronous database queries, blocking loops, or synchronous file I/O inside a listener.

**Protecting against recursive emit stack overflow:**

```js
emit(event, ...args) {
  if (!this.listeners.has(event)) return this;
  const fns = [...this.listeners.get(event)];
  for (const fn of fns) {
    fn(...args); // synchronous — recursive calls nest here
  }
  return this;
}
```

There is no built-in recursion guard. If listener A always emits the same event, you get infinite recursion and a stack overflow. Guard in your application logic: use a processing flag, or use `setImmediate`/`queueMicrotask` to break the synchronous chain when re-emitting.

## Why It's a Trap

Most developers assume event systems are asynchronous. Node.js streams, browser events — both feel async. The mental model is "I fire an event and listeners will run... later." But EventEmitter is synchronous. The `emit()` call does not return until every listener has run. This surprises people who instrument `emit()` for performance profiling and find their "fast" emit taking 200ms because one listener is slow.

The recursive emit case is rarer but produces output ordering that looks impossible until you understand the synchronous call stack model.

## What NOT to Say

- "Listeners run in the next tick." — They run synchronously in the current tick.
- "The order is non-deterministic." — The order is completely deterministic: listeners run in the order they were registered, depth-first through recursive emits.
- "EventEmitter uses Promises internally." — It does not. Zero async machinery is involved in a basic implementation.

## Follow-up

**Q:** How would you make emit asynchronous so listeners run in the next microtask?
**A:** Wrap each listener call: `Promise.resolve().then(() => fn(...args))` or `queueMicrotask(() => fn(...args))`. This defers each listener to the microtask queue, decoupling the emitter's call stack from the listener's execution. The trade-off: the emitter's caller can no longer assume all listeners have run by the time `emit()` returns, and error handling becomes async. Use async emit only when you specifically need to avoid blocking the emitter — most EventEmitter use cases are better served by the synchronous default.
