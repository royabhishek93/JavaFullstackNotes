# Senior Trap — "You Can Use Arrow Functions as Constructors with `new`"
> **Topic:** Arrow Functions | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

During a code review, a developer submits the following and defends it: `const Person = (name) => { this.name = name; }; const p = new Person('Alice');`. They argue it is equivalent to a regular function constructor.

## The Question

What happens when you run `new Person('Alice')` where `Person` is an arrow function? Why does it fail, and what does this reveal about arrow functions at the specification level?

## Model Answer (15 YOE)

This throws `TypeError: Person is not a constructor`. Arrow functions explicitly do not have a `[[Construct]]` internal method, so attempting to use them with `new` is a hard error — not a silent misbehaviour.

The reason is by design. Arrow functions have no `prototype` property and no `[[Construct]]` internal slot. The language specification removed both because an arrow function that captured lexical `this` would create an ambiguous situation if also used as a constructor — which `this` would win, the captured lexical one or the newly-allocated instance? Rather than define an arbitrary tie-breaking rule, the spec simply forbids it.

Regular functions, class constructors, and generator functions all support `new`. Arrow functions, methods in object shorthand (`{ method() {} }`), and async arrow functions do not. This is not an obscure edge case — it is a fundamental part of the specification that reflects a deliberate design decision about the separation of concerns between "functions as callbacks" and "functions as constructors."

In practice this rarely causes bugs because modern code uses `class` syntax for constructors and arrow functions for callbacks. The danger zone is legacy code that uses factory functions written as arrow functions, or developers trying to port a pattern from Python or Ruby where the distinction does not exist.

## Why It's a Trap

Arrow functions look syntactically similar to regular functions, and developers who learned primarily through functional patterns may never have needed `new` — leading them to assume arrow functions are general-purpose function replacements.

## What NOT to Say

"I have never tried it" — acceptable only if followed by correct reasoning about why it should not work. Silence or guessing that it works the same as a regular function signals a significant gap in specification knowledge.

## Follow-up

**Q:** Can arrow functions have a `prototype` property manually assigned to them?

**A:** You can technically set `ArrowFn.prototype = { ... }` but it has no effect on `new` behaviour — the `[[Construct]]` slot is still absent, so `new ArrowFn()` still throws. The `prototype` property on a regular function is what `new` uses to set the `__proto__` of the created instance. Without `[[Construct]]`, the property assignment is meaningless at the language level. It is not a workaround; it is a no-op that might confuse readers.
