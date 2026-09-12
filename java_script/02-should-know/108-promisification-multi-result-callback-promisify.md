# Multi-Result Callback — util.promisify Drops Values
> **Topic:** Promisification | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

You are working with an older geolocation library that passes multiple coordinate values to its callback:

```js
geolib.getBounds(coordinates, function(err, minLat, minLng, maxLat, maxLng) {
  if (err) return;
  drawBoundingBox(minLat, minLng, maxLat, maxLng);
});
```

A team member promisifies it with `util.promisify`. The resulting code never throws, but the bounding box is always wrong. You are asked to diagnose.

## The Question

What does `util.promisify` return from this callback, and what is the correct wrapper?

## Diagram

```
  Callback arguments:  err, minLat, minLng, maxLat, maxLng
                        ^     ^       ^       ^       ^
                      [0]   [1]     [2]     [3]     [4]

  util.promisify captures only arg[1]:
    (err, result) => resolve(result)
    result = minLat only — the other three values are silently lost

  Correct: capture all result arguments with rest syntax
    (err, ...results) => resolve(results)
    results = [minLat, minLng, maxLat, maxLng]
```

## Model Answer (15 YOE)

`util.promisify` generates a callback of the form `(err, result) => ...` — it captures exactly one result value. When the underlying callback passes four result values, only the first (`minLat`) is captured. The Promise resolves with a single number instead of an array, which explains the broken bounding box without any thrown errors — the silent data loss is the dangerous part.

The fix is a custom promisify wrapper that uses rest syntax to collect all result values:

```js
function promisifyMulti(fn) {
  return function(...args) {
    return new Promise((resolve, reject) => {
      fn.call(this, ...args, (err, ...results) => {
        if (err) reject(err);
        else resolve(results);    // resolve with an array of ALL results
      });
    });
  };
}

const getBoundsAsync = promisifyMulti(geolib.getBounds.bind(geolib));

async function renderMap(coordinates) {
  const [minLat, minLng, maxLat, maxLng] = await getBoundsAsync(coordinates);
  drawBoundingBox(minLat, minLng, maxLat, maxLng);
}
```

Alternatively, if you own or can patch the library, define a `util.promisify.custom` property that returns a named object instead of an array — positional destructuring is fragile if the library ever adds more return values:

```js
geolib.getBounds[require('util').promisify.custom] = function(coordinates) {
  return new Promise((resolve, reject) => {
    geolib.getBounds(coordinates, (err, minLat, minLng, maxLat, maxLng) => {
      if (err) reject(err);
      else resolve({ minLat, minLng, maxLat, maxLng });  // named properties
    });
  });
};
```

## Follow-up

**Q:** How do you handle a callback-based EventEmitter — can you promisify it?

**A:** No, not with `promisify`. EventEmitters emit multiple events over time, which does not map to a single-value Promise. The correct tool is `events.once(emitter, 'event')` for awaiting one emission, or converting the stream to an async iterable. Trying to promisify an EventEmitter typically results in the Promise never resolving or only capturing the first event and ignoring the rest.

## Why It's a Trap

`util.promisify` silently resolves with only the first result value — it does not throw, it does not warn. The broken code looks correct, the tests may pass (if they only check whether the Promise resolved), and the bug only surfaces when the UI renders wrong output. This is the definition of a silent failure.

## What NOT to Say

- "`util.promisify` captures all the callback arguments." — It captures only the first result value (arg[1]).
- "I can get the other values from the resolved object." — The resolved value is a single primitive, not an object with multiple properties.
- "The bounding box bug is a data issue from the API." — The API is correct. The wrapper is losing data.
