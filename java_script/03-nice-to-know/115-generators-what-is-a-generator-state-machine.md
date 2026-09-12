# What Is a Generator Function — State Machine and Basic Yield
> **Topic:** Generator Functions | **Level:** Fundamental | **Frequency:** High

## The Setup

Every JavaScript interview that touches async patterns, lazy evaluation, or Redux-Saga eventually bottoms out here. Understanding the generator as a suspended state machine — not as a fancy function — is the mental model that makes every follow-up question trivial.

## The Question

"What is a generator function? How does its execution model differ from a regular function? Walk me through the states a generator goes through."

## Diagram

```
GENERATOR STATE MACHINE
========================

  gen = count(1,5)        gen.next()          yield 1
  ┌──────────────┐       ┌──────────┐        ┌─────────────────┐
  │              │──────>│          │───────>│                 │
  │  SUSPENDED   │       │ EXECUTING│        │  SUSPENDED      │
  │  (start)     │       │          │        │  (at yield)     │
  │              │       └──────────┘        │                 │
  └──────────────┘                           └────────┬────────┘
                                                      │ gen.next()
                                                      v
                                             ┌─────────────────┐
                                             │   EXECUTING     │
                                             │  (resumes from  │
                                             │   yield line)   │
                                             └────────┬────────┘
                                                      │ function ends
                                                      v
                                             ┌─────────────────┐
                                             │   COMPLETED     │
                                             │ { done: true }  │
                                             └─────────────────┘

TRANSITIONS
-----------
  suspended-start  --[.next()]-->  executing  --[yield v]-->  suspended-yield
  suspended-yield  --[.next()]-->  executing  --[yield v]-->  suspended-yield
  executing        --[return]-->   completed
  any state        --[.throw(e)]--> executing (throws inside fn) or completed
  any state        --[.return(v)]--> completed (forces done:true)

LOCAL VARIABLES
---------------
  Each generator OBJECT holds its own frozen stack frame.
  gen1 = count(1,5)  and  gen2 = count(10,20)  are INDEPENDENT machines.
  Calling count() a second time does NOT reset gen1.
```

## Model Answer (15 YOE)

A regular function is a vending machine: you press the button, it runs completely, dispenses one item, forgets you existed.

A generator is a checkout counter: you call it, the cashier picks up the first item, hands it to you (`yield`), and stands frozen. You come back with `.next()`, the cashier unfreezes and moves to the next item. The cashier's memory — which item they were on, what the running total was — survives between your visits. When there is nothing left, they hand back `{ done: true }` and go home.

The key consequence: **you control the pace of execution, not the function.**

```js
function* count(from, to) {
  for (let i = from; i <= to; i++) {
    yield i;
  }
}

const gen = count(1, 3);  // body does NOT run here

gen.next(); // { value: 1, done: false } — runs until first yield
gen.next(); // { value: 2, done: false } — resumes, runs to second yield
gen.next(); // { value: 3, done: false }
gen.next(); // { value: undefined, done: true } — function returned
```

Four states:
- **suspended-start**: generator object created, body never entered
- **executing**: currently running inside the function body
- **suspended-yield**: paused at a `yield` expression, waiting for `.next()`
- **completed**: function returned or fell off the end — permanently done, all further `.next()` calls return `{ value: undefined, done: true }`

Each generator object holds its own independent frozen stack frame. Two generators created from the same function are entirely independent machines.

## Follow-up

**Q:** "What does calling the generator function return? When does the body actually run?"

**A:** Calling the generator function returns a generator object (the iterator). The body does not run at all. The first call to `.next()` starts execution from the top of the function body and runs until the first `yield` or `return`.

**Q:** "Can you reset a generator?"

**A:** No. A completed generator is permanently done. To get a fresh one, call the generator function again — that creates a new generator object with its own independent state.
