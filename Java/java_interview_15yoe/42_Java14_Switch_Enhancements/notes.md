# Java 14 Switch Enhancements

## What is this? (Plain English)

The classic `switch` statement (`case X: ... break;`) has three long-standing pain points: you need one line per case even when several cases share identical logic, forgetting a `break` silently "falls through" to the next case, and it can never directly produce a value — you always need a separate variable assigned inside each branch. **Java 14 introduces an arrow-based switch (`case X ->`) that fixes all three at once**, plus the ability to use `switch` as an *expression* that returns a value directly.

**Real-world analogy:** the old `switch` is like a row of dominoes — once one falls, it keeps knocking down the next unless you physically stop it (`break`). The new arrow syntax is like a row of separate light switches — flipping one only affects that one bulb, nothing else, by design.

## The Problem It Solves

## Fall-Through Behavior: Old vs New

```
  Old: Classic switch (colon) — FALL-THROUGH by default
  ┌────────────────┐   no break!   ┌─────────────────┐   break   ┌──────────────┐
  │ case Monday:    │ ────────────>│ case Tuesday:    │ ────────>│ exit switch  │
  └────────────────┘               └─────────────────┘           └──────────────┘

  New: Arrow switch — NEVER falls through
  ┌────────────────┐               ┌───────────────────────┐               ┌───────────────────────┐
  │ case Monday ->  │ ────────────>│ only this code runs    │ ────────────>│ exit switch automatically │
  └────────────────┘               └───────────────────────┘               └───────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

### 1. Comma-separated case grouping
Old: each shared case needed its own `case` line stacked on top of the next (case stacking). New: `case MONDAY, FRIDAY, SUNDAY -> ...` groups them on one line.

### 2. No accidental fall-through
With `->`, only the code on the right of the arrow for the *matching* case executes — there is no concept of falling through to the next case, so `break` is never needed (and has no meaning) with arrow syntax. The old colon syntax (`case X:`) still exists and still falls through exactly as before if you omit `break` — arrow and colon styles are not mixed within logic, but the language still supports the old style for backward compatibility.

### 3. Switch as an expression returning a value
```java
int count = switch (day) {
    case MONDAY, FRIDAY, SUNDAY -> 6;   // single statement: value auto-returned
    case TUESDAY -> 7;
    case THURSDAY, SATURDAY -> 8;
    case WEDNESDAY -> {
        // multiple statements need a block + explicit yield
        System.out.println("computing...");
        yield 9;
    }
};
```
- A single-statement arrow branch's value is automatically returned — no `yield` needed.
- A **block** (`{ ... }`) branch must explicitly `yield` a value (or `throw`).
- Because it's an *expression*, every branch must either yield a value or throw an exception — you cannot fall through without producing something.

### 4. Exhaustiveness checking (expressions only)
When `switch` is used as an **expression**, the compiler forces you to cover every possible input — either explicitly (every enum constant) or via a `default` branch/exception. This check does **not** apply when `switch` is used as a plain statement (no return value expected) — an unmatched case there simply does nothing.

### 5. Independent scope per arrow case
With colon syntax, all cases in the same switch block share one variable scope — declaring the same variable name twice across two cases is a compile error unless you wrap each case in its own `{ }` block. With arrow syntax, **each case has its own independent scope automatically** — no manual blocking required for repeated local variable names across different cases.

### Mixing styles
Colon-style cases can still use comma-grouping and `yield` (new Java 14 features) while retaining fall-through semantics — colon always means "fall-through is possible, use `break` or `yield` to stop it deliberately." Arrow always means "never falls through, no `break` needed."

## Interview Q&A

**Q: Do you need `break` statements when using arrow (`->`) case labels?**
A: No — arrow cases never fall through, so `break` is unnecessary and has no effect. Fall-through only exists with the classic colon (`:`) syntax.

**Q: What's the difference between using `yield` and just letting a single statement return its value?**
A: If an arrow case body is a single expression/statement, its value is implicitly returned — no `yield` needed. If the case body is a `{ }` block with multiple statements, you must explicitly call `yield <value>` to produce the switch expression's result.

**Q: When does the compiler enforce exhaustiveness on a `switch`?**
A: Only when `switch` is used as an **expression** (expected to produce a value). As a plain statement, the compiler does not require every possible input to be handled.

**Q: Can you mix colon-style and arrow-style cases in the same switch?**
A: You use one style consistently within a single switch construct — but the language still fully supports the old colon style (including with new features like comma-grouped labels and `yield`) for backward compatibility; it's not that colon-style disappeared, only that fall-through still applies to it.

**Q: Why does each arrow case get its own variable scope, unlike colon cases?**
A: Because each arrow case is treated as an independent, self-contained code block by the language spec — this was a deliberate design choice specifically to eliminate the old "variable already defined" errors that occurred when the same local variable name was declared in two different colon-style cases sharing one physical block scope.
