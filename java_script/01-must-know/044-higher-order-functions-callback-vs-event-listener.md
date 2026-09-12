# Callback vs Event Listener — Not the Same Thing
> **Topic:** Higher-Order Functions | **Level:** Senior Trap | **Frequency:** Medium

## The Setup
A junior engineer on a chat application wraps a WebSocket message handler in a Promise, expecting to capture incoming messages. Messages after the first one silently disappear. The bug report says "messages are being dropped." You are doing the code review.

## The Question
What is the difference between a callback and an event listener? Are they really the same thing?

## Diagram

```
CALLBACK (one-shot — resolves once, subsequent events silently ignored):

  new Promise(resolve => {
    ws.onmessage = e => resolve(e.data);  // fires on first message
  });                                      // Promise is settled — done
                                           // message 2, 3, 4... silently dropped

EVENT LISTENER (multi-fire — called on every matching event):

  ws.addEventListener('message', e => {
    handleMessage(e.data);  // called for every message, forever
  });                        // correct model for a data stream

  INVOCATION CARDINALITY:
  +--------------------+-------------------+---------------------------+
  | Mechanism          | Fires how many    | Right abstraction for     |
  |                    | times?            |                           |
  +--------------------+-------------------+---------------------------+
  | Promise callback   | Once (settled)    | Single async result       |
  | Event listener     | 0 to N times      | Stream / repeated events  |
  | setTimeout cb      | Once (after delay)| Deferred one-shot action  |
  | setInterval cb     | N times           | Periodic action           |
  | Node EventEmitter  | N times           | Internal event bus        |
  +--------------------+-------------------+---------------------------+
```

## Model Answer (15 YOE)

Both use functions passed as arguments — the mechanism is identical at the JavaScript level. The semantic difference is in invocation cardinality and lifecycle.

A callback passed to `fetch` or `setTimeout` is called exactly once and then discarded. A Promise is a one-shot container — once settled (resolved or rejected), it never changes state.

An event listener registered with `addEventListener` may be called zero, one, or thousands of times — once per matching event — for as long as the listener is registered. It is the correct abstraction for multi-event scenarios.

```js
// WRONG — wrapping a repeated event in a Promise
function waitForMessage(ws) {
  return new Promise(resolve => {
    ws.onmessage = e => resolve(e.data); // captures first message only
  });
}
const firstMsg = await waitForMessage(ws); // works once — all subsequent messages lost

// CORRECT — event listener for a stream of messages
ws.addEventListener('message', e => {
  messageQueue.push(e.data);
  processNextMessage();
});

// CORRECT — using an Observable (RxJS) for streams
import { fromEvent } from 'rxjs';
const messages$ = fromEvent(ws, 'message').pipe(
  map(e => e.data),
  filter(msg => msg.type === 'chat')
);
messages$.subscribe(msg => renderMessage(msg));
```

This distinction matters architecturally: if you model a "data stream" (WebSocket messages, user clicks, sensor readings) as a Promise-based callback, you can only capture the first event. Event listeners, RxJS Observables, or Node.js EventEmitter are the correct abstractions for multi-event scenarios. Mixing them causes silent data loss — the most dangerous kind of bug.

## Follow-up

**Q:** When should you convert an event stream into a Promise?

**A:** When you genuinely need only the first occurrence — for example, "wait for the WebSocket connection to open before sending." `new Promise(resolve => ws.addEventListener('open', resolve, { once: true }))` is correct here. The `{ once: true }` option auto-removes the listener after the first fire, making the cardinality explicit and preventing memory leaks.

## Why It's a Trap

The trap is treating JavaScript's event system as syntactic sugar over Promises. Both look like "passing a function in." The candidate who conflates them will write subtle cardinality bugs — capturing one click, one WebSocket message, one sensor reading — and wonder why data disappears. The interviewer is checking whether you reason about cardinality, not just syntax.

## What NOT to Say

- "They're basically the same — both pass a function as an argument" — mechanically true but architecturally wrong
- "You can always wrap an event listener in a Promise" — only safe for one-shot events
- "Event listeners are just callbacks that fire multiple times" — this is actually correct, but incomplete without explaining why it changes your abstraction choice
