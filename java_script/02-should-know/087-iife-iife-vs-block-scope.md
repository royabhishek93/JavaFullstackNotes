# Senior Trap — "An IIFE and a Block `{}` with `let` Are the Same Thing"
> **Topic:** IIFE | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

A candidate refactoring a legacy codebase replaces every IIFE with a bare block: `{ let x = 1; }`. They argue: "ES6 block scoping does the same thing as an IIFE — I can simplify all of this."

## The Question

Are an IIFE and a block statement with `let`/`const` equivalent? Where does this claim hold, and where does it break down?

## Model Answer (15 YOE)

They achieve the same thing for exactly one use case — preventing a temporary variable from leaking into the surrounding scope. For that specific purpose, `{ let x = computeX(); }` is simpler and clearer than `(function() { var x = computeX(); })()`. The bare block is strictly better there.

The claim breaks down everywhere else, and the differences matter in practice.

An IIFE can return a value and assign it to a variable. The entire module pattern depends on this: `const Cart = (function() { ...; return { add, total }; })()`. A bare block has no return value — you cannot write `const Cart = { let items = []; ... }`. There is no equivalent.

An IIFE creates a new `this` context; a bare block does not. Code that relies on `this` inside a function scope behaves differently than code in a block scope at the same level.

An IIFE's `return` statement exits the function early, giving you a clean exit path from complex initialisation. A bare block has no early exit; you would need a label and `break`, which is arcane.

An IIFE can be async — `(async () => { await ... })()`. A bare block cannot be awaited; you cannot write `await { ... }`.

An IIFE appears as a distinct execution context in stack traces and profiler output. A bare block does not; debugging anonymous inline code is harder.

The correct rule: use a bare block when all you need is scope isolation for a temporary variable. Use an IIFE when you need a return value, async execution, early exit, or a named execution unit in stack traces.

## Why It's a Trap

Block scoping sounds like a drop-in replacement for IIFEs, but the two patterns have genuinely different capabilities — return values, async, early exit — that matter in the module pattern and initialisation code.

## What NOT to Say

"They're basically the same." Acceptable only if immediately followed by precise distinctions. Stopping at "the same" signals superficial understanding of both patterns.

## Follow-up

**Q:** In a code review, you see `(function() { var count = 0; return count; })()` assigned to a variable. Would you suggest replacing it with a bare block?

**A:** No. The bare block cannot return a value, so it is not a valid replacement here. I would suggest replacing it with a `const` declaration directly — `const count = 0;` — since the IIFE is doing nothing useful: it immediately returns a primitive, so there is no encapsulation benefit. The IIFE is vestigial in this case. If the function contained real initialisation logic and returned a meaningful value, the IIFE form is correct and I would keep it as-is or suggest migrating to a factory function for readability.
