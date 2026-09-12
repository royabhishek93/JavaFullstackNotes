# Senior Trap — "Arrow Functions Are Always Better Than Regular Functions for Methods"
> **Topic:** Arrow Functions | **Level:** Senior Trap | **Frequency:** High

## The Setup

You are interviewing a senior candidate. They have described their React and Node.js experience confidently. You ask: "What's your general approach to writing methods on a class — arrow class fields or regular prototype methods?"

## The Question

The candidate says: "I always use arrow functions for class methods. They're cleaner and avoid `this` binding bugs entirely." What is wrong with this position, and what would a correct answer look like?

## Model Answer (15 YOE)

That is not accurate as a general rule. Arrow functions as class fields solve the callback detachment problem elegantly, but they come with a real cost: the method is an instance property, not a prototype property. This means subclasses cannot reliably override it through the prototype chain, and `jest.spyOn(MyClass.prototype, 'method')` does not intercept arrow field calls because the instance property shadows the prototype.

Regular prototype methods are the right choice when inheritance or prototype-level mocking is needed. The correct rule is: use arrow class fields for methods that will be used as detached callbacks and that are not intended to be overridden; use regular prototype methods for everything else.

There is also a memory cost. Every `new MyClass()` allocates its own copy of each arrow class field. For a few handlers in a React component this is irrelevant. For a model object instantiated thousands of times — a row in a virtualised list, an entity in a game engine, a node in a graph — the difference is measurable.

The mature position is: choose the right tool per use case, and document why. Blanket rules in either direction signal that the engineer has not been burned by the edge cases yet.

## Why It's a Trap

Sounds like a best-practice statement but breaks prototype mocking, inheritance, and memory efficiency for frequently-instantiated classes.

## What NOT to Say

"Arrow functions are cleaner so I always use them" — this misses the prototype implications entirely and signals the candidate has not debugged inheritance bugs in a real codebase.

## Follow-up

**Q:** You're adding a base class to a shared library that other teams will subclass. Which method style do you use and why?

**A:** Regular prototype methods, without question. Library consumers subclass to override behaviour — that is the entire contract of inheritance. If base methods are arrow class fields, overriding them requires redefining in the subclass constructor rather than on the prototype, which is non-obvious and breaks `super` calls. For a public library, the API contract must support the expected usage pattern. Arrow fields are a private implementation detail for leaf components and services, not for extensible base classes.
