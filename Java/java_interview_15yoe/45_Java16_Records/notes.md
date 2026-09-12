# Java 16 Records

## What is this? (Plain English)

Writing a simple, correct immutable data class in Java has always required a large amount of mechanical, repetitive code: mark the class `final`, declare every field `private final`, write a constructor, write getters only (no setters), and implement `equals()`/`hashCode()`/`toString()` by hand (or via Lombok). A **record** compresses all of that down to a single line: `record User(String name, int age) {}` — the compiler generates the constructor, accessors, `equals()`, `hashCode()`, and `toString()` for you, automatically, with no external library required.

**Real-world analogy:** think of a record as pre-printed carbon-copy form — you just fill in the blanks (the fields), and every standard section (constructor, getters, printable summary, equality check) is already formatted and ready, instead of you drafting the whole form from a blank page every time.

## The Problem It Solves

Boilerplate for basic "data carrier" classes (POJOs) is repetitive and error-prone to hand-write, and even with Lombok (an external library), nothing stops another engineer from accidentally adding a setter or breaking immutability. Records make immutability a **language-enforced guarantee**, not just a convention.

## How Records Work Internally

```java
public record User(String name, int age) {}
```

This single line generates all of the following automatically:

| Generated | Detail |
|---|---|
| `private final` fields | One per declared component (`name`, `age`) — called **record components** |
| Canonical constructor | Takes all components, in the declared order, and assigns them |
| Accessor methods | Named exactly like the component (`name()`, `age()`) — **not** `getName()`/`getAge()` |
| `equals()` / `hashCode()` | Based on all components |
| `toString()` | `User[name=..., age=...]` format |

Every record implicitly extends `java.lang.Record` — this is how the JVM identifies "this is a record" and applies record-specific rules. Because Java has single inheritance, **a record can never extend another class** (that inheritance slot is already used) — but it **can implement interfaces** just like a normal class.

### Rules unique to records

1. **No extra instance fields** — you cannot declare additional instance fields beyond the record components. This is intentional: a record is meant to be a **transparent data carrier** — just from reading the component list, you know everything it holds. **Static** fields, however, are allowed, because they belong to the class, not to any individual instance, so immutability of the object itself is unaffected.
2. **Canonical constructor can be overridden** — to add validation logic — but must still initialize every component. A **compact constructor** (`public User { if (age < 0) throw ...; }`) is shorthand that skips repeating the parameter list and the field assignments — the compiler still auto-assigns fields after your custom logic runs.
3. **Additional constructors are allowed**, but every one of them must ultimately delegate to the canonical constructor (directly or via another constructor), ensuring no component is ever left uninitialized.
4. **Access level can only stay the same or widen**, never narrow, relative to the record's own access level (e.g. you can't make the canonical constructor `private` on a `public` record).
5. **Defensive copying is your responsibility** — marking a field `private final` only protects the *reference*, not a mutable object it points to (e.g. a `List`). If a component is a mutable collection, override the canonical/compact constructor to wrap it (e.g. `List.copyOf(hobbies)`) if true immutability of contents is required.
6. **Nested records are implicitly `static`, always** — unlike nested classes (which can be static or non-static), a nested record cannot be non-static. This is because a non-static nested type would need an implicit reference back to its enclosing instance, which would let it access the parent's instance fields — violating the "transparent data carrier" guarantee, since that hidden reference wouldn't show up in the record's declared components.
7. **Local records** (declared inside a method/block) follow the same restrictions as local classes: no access modifiers (their scope is already limited to the enclosing block), cannot be instantiated outside that block, and — consistent with rule 6 — cannot be `static` either, since a local record's scope is tied to a block, not a class.

## Records vs Lombok

| | Lombok | Records |
|---|---|---|
| Requires external dependency | Yes (`pom.xml`) | No — native Java |
| Enforces immutability | No — a manually-added setter still works | Yes — the language itself prevents adding setters |
| Integration with newer language features | N/A | Works directly with sealed classes and pattern matching (`switch` on record types) |

## Interview Q&A

**Q: Why can't you add extra instance fields to a record beyond its declared components?**
A: Because a record is designed to be a "transparent data carrier" — its entire state must be visible just from its component list. Allowing hidden extra instance fields would break that guarantee. Static fields are still allowed because they belong to the class, not any instance, so they don't affect the object's declared, transparent state.

**Q: Why must nested records always be static, even though nested classes can be non-static?**
A: A non-static nested type implicitly holds a reference to its enclosing instance so it can access the parent's instance fields — but that hidden reference isn't declared as one of the record's components, which would silently violate the record's transparency guarantee. Making nested records always static removes any implicit link to a parent instance.

**Q: If a record's field is `private final List<String>`, is the list itself immutable?**
A: No — `final` only prevents the *reference* from being reassigned; the underlying `List` object can still be mutated through that reference unless you explicitly wrap it (e.g., `List.copyOf(...)`) in a compact or overridden canonical constructor.

**Q: What's a "compact constructor" and how is it different from overriding the canonical constructor normally?**
A: A compact constructor lets you write validation/transformation logic without repeating the full parameter list or the `this.field = field` assignments — the compiler still generates those assignments automatically after your custom code runs, whereas a fully custom canonical constructor requires you to write every assignment yourself.

**Q: Why does Java prefer records over Lombok going forward?**
A: Records are a native language feature — no external dependency needed — and they provide a hard, compiler-enforced immutability guarantee (no setters possible at all), whereas Lombok only reduces boilerplate without stopping someone from manually adding a mutator method. Records also integrate directly with newer features like sealed types and pattern matching in `switch`.
