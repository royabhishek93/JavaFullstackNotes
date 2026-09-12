# Java 8 Optional — Complete Guide

## What is this? (Plain English)

Methods that might not have a value to return traditionally just returned `null` — but `null` carries no information about *whether* a caller should expect it. This silently forces every caller to remember to add a null-check, and forgetting even one causes a `NullPointerException`. **`Optional<T>` makes "this might be absent" part of the method's declared return type**, so the caller is compiler-forced to explicitly handle the absent case instead of being trusted to remember a null-check.

**Real-world analogy:** instead of handing someone a box that might be empty with no label (`null`), you hand them a box that's clearly labeled "MAY BE EMPTY — CHECK BEFORE OPENING" (`Optional<T>`). They can't pretend they didn't know to check.

## The Problem It Solves

`user.getName()` where `user` might be `null` throws `NullPointerException` if the caller forgot to guard it — and there was no way for the method signature itself to warn the caller. `Optional<User> findUserById(id)` makes the possible absence part of the type itself; you cannot call `.getName()` directly on an `Optional` without first unwrapping it.

## Optional Method Categories

```
                                                     ┌─────────────────┐
                                                     │   Optional<T>    │
                                                     └─────────┬─────────┘
        ┌───────────────┬───────────────┬────────────────┬─────┴─────┬───────────────┬───────────────┬───────────────────┐
        │                │               │                │           │               │               │                    │
        ▼                ▼               ▼                ▼           ▼               ▼               ▼                    ▼
┌───────────────┐┌───────────────┐┌────────────────┐┌──────────────┐┌──────────────┐┌────────────────┐┌────────────────────┐
│   Creation    ││   Presence    ││   Retrieving    ││ Transforming ││ Action-Based ││ Alt. Selection ││ Stream Integration │
│               ││   Checking    ││     Values      ││              ││              ││                ││                    │
│ of()          ││ isPresent()   ││ get()           ││ map()        ││ ifPresent()  ││ or()           ││ stream()           │
│ ofNullable()  ││ isEmpty()     ││ orElse()        ││ flatMap()    ││ ifPresentOr  ││ (Java 9)       ││ (Java 9)           │
│ empty()       ││ (Java 11)     ││ orElseGet()     ││ filter()     ││ Else()       ││                ││                    │
│               ││               ││ orElseThrow()   ││              ││ (Java 9)     ││                ││                    │
└───────────────┘└───────────────┘└─────────────────┘└──────────────┘└──────────────┘└────────────────┘└────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

### Creation
- `Optional.of(value)` — throws `NullPointerException` immediately if `value` is `null`. Use only when you're certain the value is non-null.
- `Optional.ofNullable(value)` — returns a shared empty instance if `value` is `null`, otherwise wraps it. This is the safe general-purpose factory.
- `Optional.empty()` — returns a shared, cached empty instance (no new object allocated each time).

### Presence Checking
- `isPresent()` — `true` if a value exists.
- `isEmpty()` (Java 11) — logical negation of `isPresent()`, avoids writing `!optional.isPresent()`.

### Retrieving Values
| Method | Behavior |
|---|---|
| `get()` | Returns the value, or throws `NoSuchElementException` if empty. Always guard with `isPresent()` first, or prefer one of the below. |
| `orElse(default)` | Returns the value if present, else the given default. |
| `orElseGet(supplier)` | Returns the value if present, else computes a default lazily via a `Supplier` — use when computing the default is expensive/complex. |
| `orElseThrow()` (Java 10) | Returns the value, or throws `NoSuchElementException` if empty. |
| `orElseThrow(supplier)` | Returns the value, or throws a **custom** exception you supply. |

### Transforming (mirrors Stream's `map`/`flatMap`/`filter`, but for exactly 0-or-1 values)
- `map(fn)` — transforms the wrapped value and re-wraps the result in a new `Optional`. If your mapper function itself already returns an `Optional`, `map` would double-wrap it (`Optional<Optional<T>>`).
- `flatMap(fn)` — same as `map`, but when the mapper itself returns an `Optional`, it is *not* re-wrapped — avoiding the double-`Optional` problem.
- `filter(predicate)` — keeps the value only if it satisfies the predicate; otherwise returns `Optional.empty()`.

```java
Optional<String> name = Optional.of("Shan");
Optional<Integer> length = name.map(String::length);      // Optional[4]

// If a method already returns Optional, use flatMap to avoid Optional<Optional<T>>
Optional<String> result = name.flatMap(n -> Optional.of(n.toUpperCase()));
```

### Action-Based (no return value expected)
- `ifPresent(consumer)` — runs the consumer only if a value is present; does nothing otherwise.
- `ifPresentOrElse(consumer, runnable)` (Java 9) — runs the consumer if present, or the given `Runnable` if empty.

### Alternative Selection
- `or(supplier)` (Java 9) — like `orElseGet`, but the supplier itself must return an `Optional` — useful for chained fallback lookups (e.g. cache → main DB → backup DB, stopping at the first non-empty source).

```java
Optional<Data> result = findFromCache(id)
    .or(() -> findFromMainDb(id))
    .or(() -> findFromBackupDb(id));
```

### Stream Integration
- `stream()` (Java 9) — converts the `Optional` into a `Stream` of zero or one element. This exists specifically because `Stream.map()` operations frequently call methods that themselves return `Optional`, producing an awkward `Stream<Optional<T>>`. Combine with `flatMap(Optional::stream)` to flatten that into a clean `Stream<T>` with all empty values automatically dropped — no manual `isPresent()`/`get()` filtering needed.

```java
List<UserDetail> users = ...; // some emails are null
List<String> emails = users.stream()
    .map(UserDetail::getEmail)       // returns Optional<String> per user
    .flatMap(Optional::stream)       // flattens to Stream<String>, drops empties
    .toList();
```

## Where NOT to Use Optional

| Location | Why it's discouraged |
|---|---|
| **Class fields** | Breaks frameworks (Lombok, Jackson, JPA, Hibernate) that expect a standard getter returning the raw value, not `Optional`. |
| **Method parameters** | Doesn't remove the null-check problem — callers can still pass `null` as the `Optional` reference itself, so you're back to needing a null-check before you can even call `.isPresent()`. |
| **Fields on a `Serializable` class** | JSON libraries like Jackson don't natively understand `Optional`'s internal structure — even if it "works," the serialized payload bloats with `Optional`'s internal fields (`present`, `value`) instead of a clean value. |
| **DAO / repository layer return types** | `Optional` here forces *every* calling layer above it (service, controller) to also handle `Optional`, spreading the wrapping through the entire call chain instead of resolving it once. Prefer resolving `Optional` at the **service layer**, where business logic decides what ultimately gets exposed to callers. |

## Interview Q&A

**Q: What's the difference between `Optional.of()` and `Optional.ofNullable()`?**
A: `of()` throws `NullPointerException` immediately if the argument is `null` — use it only when you're certain the value can't be null. `ofNullable()` gracefully returns the shared empty instance instead of throwing, making it the safer general-purpose factory.

**Q: When would you use `flatMap` instead of `map`?**
A: When the transformation function itself already returns an `Optional`. Using `map` in that case would produce a nested `Optional<Optional<T>>`; `flatMap` flattens that automatically into a single `Optional<T>`.

**Q: Why shouldn't `Optional` be used as a class field?**
A: Frameworks like Lombok, Jackson, and JPA expect a conventional getter that returns the plain value, not an `Optional`. Wrapping fields in `Optional` breaks their expected access pattern and can cause serialization or persistence issues.

**Q: Why is using `Optional` as a DAO-layer return type discouraged, even though it's a valid return type in general?**
A: Because the DAO layer sits at the bottom of the call chain — every layer above it (service, controller) then also has to unwrap the `Optional`, spreading the "might be absent" handling everywhere instead of resolving it once. It's recommended to resolve/unwrap at the service layer, where the business logic decides the final contract exposed upward.

**Q: What's the purpose of `Optional.stream()`?**
A: To bridge `Optional` and `Stream` cleanly. It's especially useful when a `Stream.map()` call invokes a method that returns `Optional`, producing an awkward `Stream<Optional<T>>` — replacing `map` with `flatMap(Optional::stream)` collapses that into a plain `Stream<T>`, automatically discarding empty values.
