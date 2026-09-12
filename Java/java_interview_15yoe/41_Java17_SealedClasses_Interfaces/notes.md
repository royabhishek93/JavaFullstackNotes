# Java 17 Sealed Classes and Interfaces

## What is this? (Plain English)

Before Java 17, once you published an interface or a non-final class, you had **zero control** over who could extend it. Any engineer, anywhere in the codebase (or even a different codebase), could write `class Triangle implements Shape` and your `switch`/`if-else` chains handling `Shape` would silently need a `default`/`else` catch-all for cases you never anticipated. **Sealed classes let the author of a type explicitly declare the complete, closed list of permitted direct subclasses** — no surprises, no silent gaps.

**Real-world analogy:** think of an exclusive members-only club with a fixed guest list at the door (the `permits` clause). Nobody uninvited gets past the entrance, and every invited guest must declare in advance whether *they* can bring more guests of their own (`non-sealed`), a further restricted guest list (`sealed permits ...`), or no further sub-invitations at all (`final`).

## The Problem It Solves

Uncontrolled inheritance means: (1) you can't guarantee you've handled every possible subtype in your `switch`/`if-else` logic, forcing defensive `default` branches; (2) a new subclass added by someone else can silently break assumptions your code made, with no compiler warning.

## Declaring a Sealed Hierarchy

```java
sealed interface Shape permits Circle, Rectangle {}

final class Circle implements Shape { }        // no further subclasses allowed
non-sealed class Rectangle implements Shape { } // open — anyone can extend Rectangle further
```

Every class/interface named in `permits` **must** choose exactly one of three modifiers:

| Modifier | Meaning |
|---|---|
| `final` | Dead end — no further subclassing allowed at all |
| `sealed` (with its own `permits`) | Restrict further — only the newly named subclasses are allowed |
| `non-sealed` | Open the branch back up — any class can extend this one, unrestricted |

## Rules

1. Every class/interface in the `permits` list must be a **direct** subclass/subinterface of the sealed type (not a grandchild).
2. Every named class must pick one of `final` / `sealed` / `non-sealed` — there's no fourth option.
3. Every class named in `permits` must actually be implemented **today** — you cannot list a future/planned subclass that doesn't exist yet.

## Mixed Hierarchy Example

```
┌───────────────────────────────────────────┐
│                   Shape                    │
│           <<sealed interface>>             │
│   permits Circle, Polygon, AbstractShape   │
└───────────────────────┬─────────────────────┘
            │ implements(..)   │ implements(..)      │ extends(--)
            ▼                  ▼                     ▼
┌───────────────┐   ┌─────────────────────┐   ┌───────────────────────┐
│     Circle     │   │       Polygon        │   │      AbstractShape     │
│   <<final>>    │   │  <<non-sealed         │   │   <<sealed abstract>>  │
│                │   │      interface>>      │   │  permits Rectangle,    │
│                │   │                       │   │          Triangle      │
└───────────────┘   └───────────┬───────────┘   └──────────┬─────────────┘
                                 │ extends(..)              │ extends(--)        │ extends(--)
                     [open branch: any subclass ▼                                ▼
                      allowed]                 ┌────────────────┐   ┌────────────────┐
                                 ┌───────────┐  │    Rectangle    │   │    Triangle     │
                                 │  Hexagon   │  │   <<final>>     │   │  <<non-sealed>> │
                                 └───────────┘  └────────────────┘   └────────┬─────────┘
                                                                              │ extends(--)
                                                                  [allowed, non-sealed] ▼
                                                                        ┌───────────────────────┐
                                                                        │   AnyFutureSubclass     │
                                                                        └───────────────────────┘
```

Legend: `implements(..)` = realization edge (interface implementation), `extends(--)` = inheritance edge. Edge labels in `[...]` mirror the original diagram's annotations.

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

- `Circle` is `final` — a dead end, no further subclasses ever.
- `Polygon` is `non-sealed` — deliberately reopened, so `Hexagon` (and anything else) can extend it freely with no restriction.
- `AbstractShape` is itself `sealed` with its own restricted `permits` list (`Rectangle`, `Triangle`) — you can nest sealing at any depth in the hierarchy.
- `Triangle` is `non-sealed` — even though it sits under a sealed branch, it reopens the hierarchy from that point downward.

**Key insight:** sealing is a *per-node* decision. You control exactly where the hierarchy stays closed and exactly where you deliberately reopen it — you're not forced to seal every level.

## Interview Q&A

**Q: What's the difference between marking a subclass `final` vs `non-sealed`?**
A: `final` permanently closes that branch — no further subclasses, ever. `non-sealed` deliberately reopens that branch — any class, known or unknown, can extend it from that point on, with no compiler-enforced restriction.

**Q: Can a class listed in `permits` be a subclass at any depth, or must it be direct?**
A: It must be a **direct** subclass/subinterface of the sealed type. A grandchild class cannot be listed directly in the parent's `permits` clause.

**Q: What's the benefit of sealed classes for `switch` statements specifically?**
A: When pattern-matching on a sealed hierarchy in a `switch` expression, the compiler can verify **exhaustiveness** — if you've covered every permitted subtype, you don't need a `default` case at all, and the compiler will actually flag it as an error if you're missing a case for one of the permitted types.

**Q: Can you declare a sealed interface with a subclass that doesn't exist yet, planning to add it later?**
A: No — every class named in the `permits` list must already exist and be compiled. You cannot pre-declare a placeholder for a future subclass.

**Q: If `AbstractShape` is `sealed permits Rectangle, Triangle`, and `Triangle` is `non-sealed`, is the whole hierarchy still considered "sealed"?**
A: No — sealing only guarantees closure up to the point where a branch is marked `non-sealed`. Beyond `Triangle`, the hierarchy is fully open; anyone can create further subclasses of `Triangle` without restriction.
