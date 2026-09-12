# What is a HOF — Implement map, filter, reduce From Scratch
> **Topic:** Higher-Order Functions | **Level:** Fundamental | **Frequency:** High

## The Setup
During an Atlassian interview, the interviewer says: "Forget the built-ins. Implement Array.map, Array.filter, and Array.reduce from scratch. Then use your implementations to process a cart."

## The Question
Implement all three HOFs from scratch. Explain the HOF contract each one enforces.

## Diagram

```
map — transform every element, preserve length:
  [100, 200, 300]  -->  myMap(x => x * 0.9)  -->  [90, 180, 270]
   input array          callback = transform       output array (same length)

filter — keep elements matching predicate, may reduce length:
  [item1, item2, item3]  -->  myFilter(x => x.available)  -->  [item1, item3]
   all items                  callback = boolean test         available only

reduce — collapse entire array to one value:
  [90, 180, 270]  -->  myReduce((sum, x) => sum + x, 0)  -->  540
   values              callback = accumulator fn, seed=0      single number
```

## Model Answer (15 YOE)

```js
// --- myMap ---
Array.prototype.myMap = function(callback) {
  const result = [];
  for (let i = 0; i < this.length; i++) {
    if (i in this) result.push(callback(this[i], i, this));
  }
  return result;
};

// --- myFilter ---
Array.prototype.myFilter = function(callback) {
  const result = [];
  for (let i = 0; i < this.length; i++) {
    if (i in this && callback(this[i], i, this)) result.push(this[i]);
  }
  return result;
};

// --- myReduce ---
Array.prototype.myReduce = function(callback, initialValue) {
  let hasInitial = arguments.length >= 2;
  let acc = hasInitial ? initialValue : this[0];
  let start = hasInitial ? 0 : 1;
  for (let i = start; i < this.length; i++) {
    if (i in this) acc = callback(acc, this[i], i, this);
  }
  return acc;
};

// Zomato cart: available items, discounted prices, total
const cart = [
  { name: 'Biryani', price: 280, available: true },
  { name: 'Lassi',   price: 60,  available: false },
  { name: 'Naan',    price: 40,  available: true },
];

const total = cart
  .myFilter(item => item.available)       // [Biryani, Naan]
  .myMap(item => item.price * 0.9)        // [252, 36]
  .myReduce((sum, p) => sum + p, 0);      // 288

console.log(total); // 288
```

The `i in this` guard handles sparse arrays correctly — a detail the built-ins handle and naive implementations miss. For `reduce`, the no-initial-value form (start at index 1, use `this[0]` as seed) matches the spec and matters when you reduce typed or structured arrays. Each HOF's contract: `map` guarantees output length equals input length; `filter` guarantees output is a subset; `reduce` guarantees a single return value of any type.

HOF taxonomy:
- `map` and `filter` take a function as argument — they are HOFs
- The `callback` passed to each is the behavior they customize
- This is the separation of concerns HOFs provide: `map` owns the iteration algorithm; the callback owns the transform logic

## Follow-up

**Q:** Why does `reduce` with no initial value throw on an empty array, but `map` and `filter` return empty arrays?

**A:** `map` and `filter` loop zero times on an empty array and return `[]` — valid results. `reduce` without an initial value needs `this[0]` as its seed; on an empty array that is `undefined`, and the spec mandates a `TypeError` because there is no meaningful value to collapse to. Always pass an initial value when the input array may be empty — `myReduce(fn, 0)`, `myReduce(fn, [])`, `myReduce(fn, {})` depending on the expected output type.
