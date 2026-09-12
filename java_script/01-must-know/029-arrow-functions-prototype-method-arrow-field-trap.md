# Prototype Method Trap — Arrow Function Breaks Inheritance
> **Topic:** Arrow Functions | **Level:** Intermediate | **Frequency:** Medium

## The Setup

You are doing an architectural review of a shared utility library used across five microservices. A developer has written all methods as arrow class fields for consistency. A colleague points out that one of the service's Jest tests is failing because `instanceof` checks are passing but method overriding in a subclass is silently failing.

## The Question

Why does defining a method as an arrow class field break subclass method overriding, and in what production scenarios does this matter?

## Diagram

```
┌────────────────────────────────────────────────────────┐
│         PROTOTYPE vs CLASS FIELD METHODS               │
│                                                        │
│  Prototype method (regular):                           │
│  ┌──────────────────────┐                              │
│  │   Base.prototype     │◄── shared by all instances   │
│  │   ┌──────────────┐   │                              │
│  │   │ format() { } │   │    Child.prototype           │
│  │   └──────────────┘   │    ┌──────────────┐          │
│  └──────────────────────┘    │ format() { } │ ◄── overrides
│                               └──────────────┘          │
│                                                        │
│  Arrow class field:                                    │
│  ┌──────────────────────┐                              │
│  │   base instance      │                              │
│  │   ┌──────────────┐   │  ← owns the method           │
│  │   │ format = ()=>│   │    NOT on prototype          │
│  │   └──────────────┘   │                              │
│  └──────────────────────┘                              │
│                                                        │
│  child instance ALSO gets its own format = ()=>        │
│  BUT: if child doesn't redefine it, it uses            │
│  the one from Base's constructor — NOT the             │
│  prototype chain lookup. Polymorphism breaks.          │
└────────────────────────────────────────────────────────┘
```

## Model Answer (15 YOE)

Arrow class fields are instance properties, not prototype properties. Babel compiles `format = () => {}` to `this.format = () => {}` inside the constructor. When you subclass and do not redefine `format`, the instance gets the `Base` constructor's version — it is not a prototype lookup at all. If you do define `format = () => {}` in the subclass, both run during construction and the child wins, but `super.format()` does not work the way you expect because arrow fields are not on the prototype.

This matters in several real-world patterns. The first is strategy pattern implementations where subclasses override processing logic — the override silently fails if the base used arrow fields. The second is when you write unit tests that mock a method via `MyClass.prototype.format = jest.fn()` — the arrow field on the instance takes precedence over the prototype mock, so your test is not actually testing the real call path.

The rule I use in practice: methods that are always called as callbacks and never overridden in subclasses are good candidates for arrow class fields — React event handlers, Express route handlers bound to service instances. Methods that participate in inheritance or that test suites need to mock via prototype should be regular prototype methods. Making this distinction explicit in a project's coding standards prevents exactly the kind of silent override bug you are describing.

## Follow-up

**Q:** How would you explain this distinction in a code review comment without being condescending?

**A:** I would frame it around intent rather than correctness. Something like: "This works for the current use case, but since `Base` is designed to be subclassed, a prototype method gives consumers the ability to override it without constructor conflicts. Arrow field is better when we want to guarantee `this` binding for use as a standalone callback — if that's the goal here, worth a comment explaining why." That separates the pattern decision from a value judgment about the engineer's knowledge.
