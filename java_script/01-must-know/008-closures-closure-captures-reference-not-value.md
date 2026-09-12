# Does a Closure Capture the Variable's Value or a Reference?
> **Topic:** Closures | **Level:** Senior Trap | **Frequency:** High

## The Setup
You have just finished explaining what a closure is to the interviewer. They nod and ask a deceptively simple follow-up. Candidates who answered the previous question well often fall here by confusing "how closures work" with "how you work around them."

## The Question
Does a closure capture the variable's value at the time of creation, or a reference to the variable?

## Diagram
```
  REFERENCE capture (how it actually works):
  ┌─────────────────────────────────────────────┐
  │  let x = 1;                                 │
  │  const fn = () => x;   // fn holds ref to x │
  │  x = 2;                                     │
  │  fn(); // → 2, not 1                        │
  │         ↑ reads the CURRENT value of x      │
  └─────────────────────────────────────────────┘

  If it were VALUE capture (it is not):
  ┌─────────────────────────────────────────────┐
  │  const fn = () => x;   // would snapshot x=1│
  │  x = 2;                                     │
  │  fn(); // would return 1 — BUT THIS IS WRONG│
  └─────────────────────────────────────────────┘

  WHY THIS MATTERS — the var loop bug:
  ┌─────────────────────────────────────────────┐
  │  for (var i = 0; i < 3; i++) {             │
  │    fns.push(() => i);  // all capture ref   │
  │  }                     // to the SAME i var │
  │  fns[0](); // 3 — not 0, because i=3 now   │
  └─────────────────────────────────────────────┘
```

## Model Answer (15 YOE)
A closure captures a reference to the variable itself, not a copy of its value at the time of closure creation. This is why mutating the variable after the closure is created affects what the closure sees — and it is the exact mechanism behind both the `var` loop bug and React's stale closure problem.

The nuance is that when the closed-over variable is a primitive, mutating it means reassigning the variable binding (e.g., `i = i + 1`), which the closure sees. When it is an object, both the closure and any other reference to the same variable see mutations to the object's properties — this is standard JavaScript reference semantics, not specific to closures.

```js
// Proves reference capture:
let count = 0;
const getCount = () => count;
count = 42;
getCount(); // 42 — the live variable, not a snapshot

// Stale closure is a consequence of the same mechanics:
// React creates a new render-scope variable on each render.
// A callback born in render 1 holds a reference to render 1's variable.
// Render 2 creates a DIFFERENT variable with the same name.
// The callback never sees render 2's variable — it still points at render 1's.
// That is why it is "stale" — not because closures snapshot values,
// but because the variable being referenced is from the old render scope.
```

## Follow-up
**Q:** If closures capture references, why does the IIFE fix for the `var` loop bug work?

**A:** The IIFE creates a new variable (`capturedI`) that is a copy of `i` at the time of the call. The closure then closes over `capturedI` — a different variable from `i`. When `i` changes, `capturedI` does not, because they are independent variables. The closure still captures a reference, but that reference now points to a variable that never changes.

## Why It's a Trap
Candidates who have seen the IIFE loop fix often say "closures capture values" because that is the behaviour the IIFE produces — but they are confusing the fix with the default mechanism.

## What NOT to Say
"Closures capture the value of the variable at the time the closure is created." This is the most common wrong answer and is precisely backwards — it describes what an IIFE workaround does, not how closures work.
