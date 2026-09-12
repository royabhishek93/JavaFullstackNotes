# Is Promisification the Right Approach for Streaming File Reads?
> **Topic:** Promisification | **Level:** Senior Trap | **Frequency:** Low

## The Setup

A developer needs to process a large log file (2 GB) in a Node.js service. They plan to promisify the `fs.createReadStream` setup callback and use `await` to read the file.

## The Question

Is promisification the right approach for streaming operations? What is the correct tool?

## Diagram

```
  WRONG mental model — stream as a single-value Promise:

  fs.createReadStream('large.log')
    ↓
  promisify(?)  ← what do you promisify? the 'open' event? 'finish'?
    ↓
  Promise resolves with ??? ← the stream emits MANY chunks, not one value

  CORRECT mental model — stream as a sequence over time:

  t=0ms    [stream opens]
  t=10ms   [chunk 1 emitted: 64KB]
  t=20ms   [chunk 2 emitted: 64KB]
  ...
  t=800ms  [chunk N emitted: 64KB]
  t=801ms  [stream ends]

  This is an async SEQUENCE, not a single async VALUE.
  Promises model single values. Streams model sequences.
  Promisification is the wrong abstraction.
```

## Model Answer (15 YOE)

Promisification wraps a function that produces a **single result**. A readable stream emits many chunks of data over time — that is not a single-value resolved Promise. Using `promisify` on a stream setup function gives you a Promise that resolves when the stream is opened, not when it is finished. The actual data never arrives in your Promise.

There are three correct approaches depending on what you need:

**Option 1 — `stream.pipeline` for pipe-based processing** (Node.js 10+):

```js
const { pipeline } = require('stream/promises');  // pre-promisified in Node 15+
const fs = require('fs');
const zlib = require('zlib');

async function compressLog() {
  await pipeline(
    fs.createReadStream('large.log'),
    zlib.createGzip(),
    fs.createWriteStream('large.log.gz')
  );
  console.log('Pipeline complete');
}
```

`stream.pipeline` handles backpressure, error propagation, and cleanup automatically. It resolves when the pipeline finishes and rejects if any stream errors.

**Option 2 — async iteration for chunk-by-chunk processing** (Node.js 12+):

```js
async function processLog() {
  const stream = fs.createReadStream('large.log', { encoding: 'utf8' });
  for await (const chunk of stream) {
    processChunk(chunk);  // process each chunk as it arrives
  }
}
```

**Option 3 — `events.once` for awaiting a single lifecycle event** (open, close, finish):

```js
const { once } = require('events');
const stream = fs.createReadStream('large.log');
await once(stream, 'open');  // await just the open event, not the data
```

For collecting the entire stream into memory (only for small files):

```js
async function readAll(stream) {
  const chunks = [];
  for await (const chunk of stream) chunks.push(chunk);
  return Buffer.concat(chunks);
}
```

## Follow-up

**Q:** When would `util.promisify(stream.pipeline)` be valid?

**A:** `stream.pipeline` is a function that takes streams and a callback, and follows the error-first convention exactly. `util.promisify(stream.pipeline)` is valid and was the standard pattern before Node.js 15 added `stream/promises`. After Node 15, import directly from `stream/promises` — the pre-promisified version is preferred.

## Why It's a Trap

"Promisify all the things" is a natural impulse during a migration. Streams look like async operations, so engineers reach for promisification. The trap is that streams are a different async abstraction — they represent sequences, not single values. The mental model mismatch produces code that compiles and runs but never delivers data.

## What NOT to Say

- "I can promisify `createReadStream` and `await` the full file content." — `createReadStream` does not have a completion callback that delivers the full content. You get a stream object, not file data.
- "I'll listen for the `data` event inside the promisified callback." — The `data` event fires many times. A Promise settles once. These models are incompatible.
- "Streams are just slow Promises." — Fundamentally wrong. Streams are async iterables/event emitters that model sequences. Promises model single deferred values.
