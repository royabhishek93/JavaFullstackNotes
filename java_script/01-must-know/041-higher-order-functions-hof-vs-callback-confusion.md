# HOF vs Callback — Definition Confusion
> **Topic:** Higher-Order Functions | **Level:** Senior Trap | **Frequency:** High

## The Setup
In code review, a junior says: "I moved the logic into a callback, so it's now a Higher Order Function." The senior pauses. In the interview, the interviewer says: "HOFs and callbacks are the same thing, right?"

## The Question
Are Higher Order Functions and callbacks the same thing? Clarify the relationship precisely.

## Diagram

```
HOF taxonomy — two distinct roles:

  arr.map(fn)
  ^           ^
  |           |
  HOF         Callback
  (the        (the function
  container)   you hand in)

  map is the HOF:
  - provides the algorithm (iterate over every element)
  - accepts a function as argument
  - calls it at its own discretion

  fn is the callback:
  - provides the specific behavior (transform each element)
  - is passed in, not defined here
  - has no knowledge it is inside map

  They are complementary roles, not synonyms.
```

## Model Answer (15 YOE)

They are complementary, not synonyms. A HOF is the container — the function that accepts or returns functions. A callback is the payload — the function passed in. In `arr.map(fn)`, `map` is the HOF and `fn` is the callback. Both roles have distinct concerns: the HOF provides the algorithm (iterate, filter, accumulate); the callback provides the specific behavior (transform, predicate, reducer).

Confusing them leads to imprecise communication in code reviews — when you say "the callback is broken," you mean the predicate logic; when you say "the HOF is broken," you mean the iteration machinery.

A function can be both simultaneously: `setTimeout` is a HOF (it accepts a callback). The function you pass to `setTimeout` is a callback. If that function itself accepts a function argument — say it calls `arr.map(x => x * 2)` inside — then your callback is also a HOF. The roles are positional and relational, not intrinsic to any specific function.

```js
// arr.map(fn) — map is the HOF, fn is the callback
const doubled = [1, 2, 3].map(x => x * 2); // x => x * 2 is the callback

// setTimeout — setTimeout is the HOF, the arrow fn is the callback
setTimeout(() => console.log('tick'), 1000);

// factory — createMultiplier is a HOF (returns a function)
const createMultiplier = factor => n => n * factor;
const triple = createMultiplier(3); // triple is not a HOF — it just returns a number
triple(5); // 15

// A function playing both roles at once
const withLogging = fn => (...args) => { // withLogging is a HOF (returns a function)
  console.log('called with', args);
  return fn(...args); // fn is the callback withLogging received
};
```

## Follow-up

**Q:** Is `setTimeout` a HOF?

**A:** Yes — it takes a function (the callback) as its first argument and calls it after the specified delay. By definition, any function that accepts a function as an argument is a HOF. `setTimeout` is a HOF provided by the runtime; it delegates the work to the callback while managing the timer itself.

## Why It's a Trap

Candidates conflate the two terms because they often appear together. The trap is that a confident wrong answer ("yes they're the same") signals shallow understanding of the abstraction. The interviewer is checking whether you can articulate the architectural separation of concerns between the algorithm (HOF) and the behavior (callback).

## What NOT to Say

- "HOFs and callbacks are basically the same thing" — technically wrong
- "A callback is just a HOF that's passed in" — inverts the relationship; the HOF is the one that *accepts* the callback
- "It depends on the context" — vague non-answer; the distinction is always the same
