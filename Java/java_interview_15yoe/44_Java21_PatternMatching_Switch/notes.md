# Java 21 Pattern Matching for `switch`

## What is this? (Plain English)

Java 16 let you pattern-match with `instanceof`. Java 21 brings that same idea into `switch` itself — instead of only matching primitives, wrapper types, `enum`s, and `String`s (the classic switch's limits), you can now `switch` directly on **objects**: classes, interfaces, abstract types. Internally, a `switch` on an object is really just syntactic sugar over a chain of `instanceof` pattern-matching `if`/`else if` checks — which is also why it doesn't get the raw-primitive speed benefit (jump tables) that a classic `switch` on `int`/`enum` gets; it's purely a readability improvement for object-based branching, not a performance one.

## The Problem It Solves

Before Java 21, branching on an object's concrete runtime type required a manual `if (obj instanceof X) ... else if (obj instanceof Y) ...` chain — verbose, and without any compiler-enforced completeness check.

## How It Works

```java
Object obj = "hello world";

switch (obj) {
    case String s  -> System.out.println("String of length " + s.length());
    case Integer i -> System.out.println("Integer: " + i);
    default        -> System.out.println("something else");
}
```
Internally this compiles down to essentially: `if (obj instanceof String s) { ... } else if (obj instanceof Integer i) { ... } else { ... }`.

### Scope of the pattern variable
Just like `instanceof` pattern matching, a variable bound in one `case` (e.g. `s` in `case String s`) is only visible **within that case's own block** — it cannot be read in another `case`, in `default`, or after the switch ends.

### Works across a class hierarchy — with exhaustiveness rules
```
                    ┌───────────┐
                    │  Vehicle  │
                    └─────┬─────┘
             ┌────────────┴────────────┐
             │                         │
   ┌─────────▼──────────┐    ┌─────────▼──────────┐
   │     TwoWheeler      │    │     FourWheeler     │
   └─────────┬──────────┘    └─────────────────────┘
        ┌─────┴─────┐
        │           │
   ┌────▼────┐ ┌────▼────┐
   │   Bike   │ │  Cycle  │
   └─────────┘ └─────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

Given the hierarchy above, valid `case` labels for an object known to be a `TwoWheeler` are: `Bike`, `Cycle`, `TwoWheeler` itself, or `Vehicle` (the parent, since a parent type can always catch any child). But **you cannot have both `Vehicle` and `TwoWheeler` as cases in the same switch** — the compiler rejects this as a "duplicate unconditional pattern," because both are capable of catching every possible value (`Bike`, `Cycle`, and everything else under `TwoWheeler`) — pick only one all-catching case per switch.

### Null-safety
Pattern-matching `switch` is **null-safe by design**: if `obj` is `null`, every `instanceof`-style case check simply evaluates to false (no `NullPointerException`) and control falls through to `default` (or a case that explicitly matches `null`, a related Java 21 feature) — you never need a manual pre-check for `null` before the switch.

### No grouping of pattern-variable cases
```java
// ❌ Not allowed — ambiguous which pattern variable would be bound
case Circle c, Square s -> ...
```
Just like `instanceof` pattern matching disallows `||`, `switch` pattern matching disallows comma-grouping two different pattern-typed cases together — there's no guarantee which one actually matched, so neither variable could be safely used.

### Guarded patterns with `when`
```java
case String s when s.contains("h") -> System.out.println("has an h: " + s);
```
`when` adds an extra boolean condition (an implicit **AND**) evaluated only after the type pattern already matched — there is no `when`-based OR equivalent, mirroring the same restriction seen with `instanceof` pattern matching.

### Works with `enum` values too
```java
switch (colorObj) {
    case Color c -> System.out.println(c.name());  // auto-cast to Color enum, no manual casting
}
```

## Interview Q&A

**Q: Is pattern-matching `switch` on objects faster than an `if`/`else if` chain?**
A: No — it compiles down to essentially the same `instanceof` chain internally, so there's no speed advantage. The benefit is purely readability/expressiveness; the classic performance advantage of `switch` (jump/lookup tables) only applies to primitive/`enum` switches, not object pattern matching.

**Q: Why can't you have both `Vehicle` and `TwoWheeler` as separate `case` labels in the same switch, if the object is known to be a `TwoWheeler`?**
A: Both types can catch every possible value the object could be (any `TwoWheeler` subtype) — the compiler flags this as a "duplicate unconditional pattern" since only one all-encompassing case is meaningful; you must pick just one of them.

**Q: What happens if you switch on a `null` object using pattern matching?**
A: Nothing crashes — pattern-matching `switch` is null-safe. Every type-check case simply evaluates false for `null`, so control proceeds to `default` (or an explicit `case null` if declared), with no `NullPointerException`.

**Q: Can you combine two type patterns with `when` to express an OR condition?**
A: No — `when` only expresses an additional AND-style guard on a single already-matched pattern. There's no supported OR equivalent for combining multiple type patterns in one case, matching the same restriction seen in `instanceof` pattern matching.

**Q: Is the pattern variable from one `case` visible in another `case` or in `default`?**
A: No — each case's pattern variable is scoped strictly to that case's own block, exactly like with `instanceof` pattern matching.
