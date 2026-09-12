# Java 16 Pattern Matching for `instanceof`

## What is this? (Plain English)

Before Java 16, checking an object's type and then using it as that type was always a two-step manual dance: `if (obj instanceof String) { String s = (String) obj; ... }`. You had to explicitly re-cast the object yourself even though the `instanceof` check already proved what type it was. **Pattern matching lets you declare the cast-target variable right inside the `instanceof` check itself** — if the check succeeds, the compiler automatically performs the cast and binds the variable for you, scoped to the code that only runs when the check is true.

**Real-world analogy:** it's like a security guard who checks your ID *and* automatically hands you the right-colored access badge for the building you're entering — you don't have to separately go exchange your ID for a badge afterward.

## The Problem It Solves

Manual casting after `instanceof` is repetitive boilerplate and a place where copy-paste mistakes happen (casting to the wrong type, or forgetting the cast entirely and getting a `ClassCastException` elsewhere).

## How It Works

```java
// Old way
if (obj instanceof String) {
    String s = (String) obj;   // manual, repetitive cast
    System.out.println(s.length());
}

// Pattern matching (Java 16+)
if (obj instanceof String s) {
    System.out.println(s.length());   // 's' is already the right type, no cast needed
}
```

Internally, the compiler does two things once the type check passes: (1) casts the object to the declared pattern type, (2) initializes the pattern variable with that cast result — in that order. This means you **cannot** use the pattern variable before the type check has definitely succeeded.

### Scope rules
The pattern variable (`s` above) is only in scope **inside the block where the check is guaranteed true** — you cannot use it outside that `if` block, and you cannot use it in an `else` branch (where the check, by definition, was false).

### Works with `&&`, not with `||`
```java
if (obj instanceof Integer i && i > 10) { ... }   // ✅ valid — 'i' is guaranteed an Integer here
if (obj instanceof Integer i || obj instanceof String s) { ... }  // ❌ pattern variables unusable — no guarantee which type matched
```
With `&&`, the second condition only evaluates once the first is already true, so the compiler knows `i` is safely bound. With `||`, there's no guarantee *which* branch matched, so neither pattern variable can be safely used inside the combined condition.

### Works across an interface hierarchy
```java
interface Vehicle { void drive(); }
class TwoWheeler implements Vehicle { public void drive() {} }
class FourWheeler implements Vehicle { public void drive() {} }

// A single instance-of check against the common parent interface
if (obj instanceof Vehicle v) {
    v.drive();   // works whether obj is a TwoWheeler, FourWheeler, or any other Vehicle
}
```
Checking against a shared parent type (like `Vehicle`) lets one pattern match handle any subtype, instead of writing a separate `instanceof` branch per concrete class.

## Interview Q&A

**Q: What exactly happens internally when `obj instanceof String s` evaluates to true?**
A: Two things happen in order: first the object is confirmed to be an instance of `String` and cast to it, then the pattern variable `s` is initialized with that cast value — only after both steps does the code inside the `if` block execute.

**Q: Can you use a pattern variable declared in an `if` condition, inside the corresponding `else` block?**
A: No. The pattern variable is only definitely assigned when the check is true, so it's only in scope within the `true` branch — never in the `else` branch or after the block ends.

**Q: Why doesn't pattern matching work with `||`?**
A: Because with `||`, the compiler cannot guarantee which side of the condition actually matched by the time you'd want to use the pattern variable — there's no single type it can safely bind, so neither variable is considered definitely assigned.

**Q: Can pattern matching for `instanceof` be used with interfaces and their multiple implementing classes?**
A: Yes — checking `instanceof` against a common parent interface (or abstract class) lets a single check handle any of its subtypes uniformly, as long as the code inside only needs the members defined on that shared parent type.
