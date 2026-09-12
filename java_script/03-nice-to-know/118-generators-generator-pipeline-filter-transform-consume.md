# Generator Pipeline — Lazy Filter, Transform, Consume
> **Topic:** Generator Functions | **Level:** Intermediate | **Frequency:** High

## The Setup

A log processing job has 500,000 raw log lines. A naive implementation allocates three intermediate arrays: one after filter, one after transform, one before writing. A senior engineer composes generator stages into a pipeline where exactly one line travels through the pipe at any moment.

## The Question

"You have a stream of 500,000 raw log entries. You need to filter for ERROR level, transform each to a structured object, and write to a report. How do you avoid allocating three intermediate arrays? Also explain what `yield*` does."

## Diagram

```
  Consumer calls .next() on parseLogLine
        │
        v
  parseLogLine calls .next() on filterErrors
        │
        v
  filterErrors calls .next() on logSource
        │
        v
  logSource yields line-1 ("INFO  startup complete")
        │
        v  filterErrors sees "INFO" → NOT an error → calls logSource.next() again
  logSource yields line-2 ("ERROR null pointer at ...")
        │
        v  filterErrors sees "ERROR" → yields line-2 up
        │
        v  parseLogLine receives line-2 → parses → yields { timestamp, level, message }
        │
        v
  Consumer receives one structured error object

  MEMORY AT ANY MOMENT: exactly ONE line travelling through the pipe.
  No intermediate arrays. No backpressure needed.
```

## Model Answer (15 YOE)

```js
// Stage 1: source
function* logSource(rawLines) {
  yield* rawLines;  // yield* delegates to any iterable — array, Set, another generator
}

// Stage 2: filter
function* filterErrors(source) {
  for (const line of source) {
    if (line.includes('ERROR')) yield line;
  }
}

// Stage 3: transform
function* parseLogLine(source) {
  for (const line of source) {
    const [timestamp, level, ...messageParts] = line.split(' ');
    yield { timestamp, level, message: messageParts.join(' ') };
  }
}

// Wire the pipeline — nothing has run yet
const rawLines = getLinesFromFile('/var/log/app.log'); // returns an iterable
const pipeline = parseLogLine(filterErrors(logSource(rawLines)));

// Pull values through — THIS is when computation happens
for (const entry of pipeline) {
  writeToReport(entry);
}
```

The pipeline is lazy by composition. No stage runs ahead of what the consumer pulls. `filterErrors` may consume many lines from `logSource` before it finds an ERROR and yields upward — but it never materialises a filtered array.

**`yield*` delegation explained:**

```js
yield* rawLines
// is exactly equivalent to:
for (const item of rawLines) { yield item; }

// yield* works on ANY iterable: arrays, Sets, Maps, strings, other generators
yield* [1, 2, 3];            // yields 1, then 2, then 3
yield* anotherGenerator();   // delegates entirely — resumes when anotherGenerator completes
yield* 'abc';                // yields 'a', 'b', 'c'

// yield* also RETURNS the final value of a delegated generator:
function* inner() { yield 1; return 'done'; }
function* outer() {
  const result = yield* inner(); // result = 'done'
  console.log(result);           // 'done'
}
```

## Follow-up

**Q:** "What is the memory complexity of this pipeline versus the array-based approach?"

**A:** Array approach: O(N) for each of the three stages = O(3N) ≈ O(N). Generator pipeline: O(1) — exactly one item exists in memory at any time regardless of input size.

**Q:** "Can you make any stage async — for example, if `parseLogLine` needed to look up a value from a database?"

**A:** Yes. Change `function*` to `async function*` and `yield` to `yield await dbLookup(...)`. The consumer switches from `for...of` to `for await...of`. Each stage can independently be sync or async.
