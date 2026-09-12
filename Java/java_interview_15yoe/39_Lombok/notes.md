# Lombok — Reducing Boilerplate with Annotations

## What is this? (Plain English)

Lombok is a Java library that removes repetitive "plumbing" code — getters, setters, constructors, `toString()`, `equals()`/`hashCode()` — by generating it automatically during **compilation**, based on annotations you put on your class or fields. Think of it like a tailor who takes your rough measurements (a few annotations) and produces a fully-fitted suit (all the boilerplate code) without you cutting a single stitch yourself. The generated code doesn't exist in your `.java` source file — it only appears in the compiled `.class` file, which is why your IDE might show a "red squiggly" error on code that actually compiles and runs fine, until you install the Lombok IDE plugin and enable annotation processing.

## The Problem It Solves

Java classes — especially simple data classes (POJOs) — traditionally require large amounts of mechanical, repetitive code: a getter and setter per field, a constructor for every combination of fields you might want, a `toString()` for logging, `equals()`/`hashCode()` for correctness in collections. This is exactly the kind of code that has nothing to do with business logic but has to exist anyway. Lombok annotations replace all of it with a one-line declaration, injected at compile time.

## The Annotation Catalog

```
┌────────────────────┐
│ Lombok Annotations │ (A)
└──────────┬─────────┘
           │
           ├──> ┌───────────────────────────────────────┐
           │    │ Local variable typing: var / val       │ (B)
           │    └───────────────────────────────────────┘
           ├──> ┌───────────────────────────────────────┐
           │    │ Null safety: @NonNull                  │ (C)
           │    └───────────────────────────────────────┘
           ├──> ┌───────────────────────────────────────┐
           │    │ Accessors: @Getter / @Setter           │ (D)
           │    └───────────────────────────────────────┘
           ├──> ┌───────────────────────────────────────┐
           │    │ Debugging: @ToString                   │ (E)
           │    └───────────────────────────────────────┘
           ├──> ┌───────────────────────────────────────┐
           │    │ Constructors:                          │ (F)
           │    │   @NoArgsConstructor                    │
           │    │   @AllArgsConstructor                   │
           │    │   @RequiredArgsConstructor               │
           │    └───────────────────────────────────────┘
           ├──> ┌───────────────────────────────────────┐
           │    │ Object identity: @EqualsAndHashCode    │ (G)
           │    └───────────────────────────────────────┘
           ├──> ┌───────────────────────────────────────┐
           │    │ All-in-one: @Data / @Value             │ (H)
           │    └───────────────────────────────────────┘
           ├──> ┌───────────────────────────────────────┐
           │    │ Object building: @Builder               │ (I)
           │    └───────────────────────────────────────┘
           └──> ┌───────────────────────────────────────┐
                │ Resource safety: @Cleanup               │ (J)
                └───────────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

### 1. `var` / `val` — inferred local variable types
Only valid for **local variables** (not fields or parameters). Type is inferred from the initializer expression. `val` additionally makes the variable `final` (immutable reference); `var` does not.

### 2. `@NonNull` — parameter null-check
Placed on a constructor/method parameter. Lombok injects an `if (param == null) throw new NullPointerException(...)` at the top of the method body.

### 3. `@Getter` / `@Setter`
Field-level or class-level. Generates public getters/setters by default; access level is configurable (`@Getter(AccessLevel.PRIVATE)`). At class level, applies to all non-static fields; setters are skipped for `final` fields (can't be reassigned) and static fields. Use `@Setter(AccessLevel.NONE)` on a specific field to opt it out when the class-level annotation would otherwise generate one.

### 4. `@ToString`
Generates `ClassName(field1=value1, field2=value2)`. Use `@ToString.Exclude` on a field to omit it from the output (e.g., to keep sensitive data out of logs), or `@ToString(includeFieldNames = false)` to print only values.

### 5. Constructor annotations
| Annotation | Generates constructor with |
|---|---|
| `@NoArgsConstructor` | No parameters |
| `@AllArgsConstructor` | Every field |
| `@RequiredArgsConstructor` | Only `final` and `@NonNull` fields |

### 6. `@EqualsAndHashCode`
Generates both methods using all non-static, non-transient fields by default; individual fields can be excluded with `@EqualsAndHashCode.Exclude`.

### 7. `@Data` — the common shortcut
Equivalent to combining `@ToString` + `@EqualsAndHashCode` + `@Getter` (all fields) + `@Setter` (non-final fields) + `@RequiredArgsConstructor`.

### 8. `@Value` — the immutable shortcut
Makes all fields `private final`, makes the class itself `final` (non-subclassable), generates `@ToString`, `@EqualsAndHashCode`, getters for all fields — but **no setters** (fields are final) — and an all-fields constructor (equivalent to `@AllArgsConstructor`, since every field is now final).

### 9. `@Builder`
Generates a full builder class with a fluent `.fieldName(value)` API and a final `.build()` that produces the object. Combined with no setters on the target class, this is a common way to get both flexible object construction and immutability.

```java
@Builder
class TestPojo { private String name; private int age; }

TestPojo p = TestPojo.builder().name("Alice").age(30).build();
```

### 10. `@Cleanup`
Placed on a local variable holding a closeable resource (e.g. `FileInputStream`). Lombok wraps the rest of the method in a `try { ... } finally { resource.close(); }` block automatically.

## Interview Q&A

**Q: Why does my IDE show a compile error on Lombok-generated code, even though `mvn compile` succeeds?**
A: Lombok injects code during the annotation-processing phase of compilation — the IDE's own incremental compiler/linter doesn't know about this unless you install the Lombok IDE plugin and enable annotation processing in your build settings. Once enabled, the IDE understands the generated methods and the false errors disappear.

**Q: What's the difference between `@Data` and `@Value`?**
A: `@Data` assumes a mutable class — fields get both getters and setters (except final ones), and only a required-args constructor. `@Value` assumes an immutable class — all fields become `private final`, the class becomes `final`, and only getters (plus an all-args constructor) are generated; no setters exist at all.

**Q: How does `@RequiredArgsConstructor` decide which fields go into the constructor?**
A: Only fields marked `final` or annotated `@NonNull` are considered "required" and included. Optional fields are left out and must be set via setters or a builder afterward.

**Q: If I put `@Getter @Setter` at the class level, will every field get a setter?**
A: No — `static` and `final` fields are excluded from setter generation automatically (you can't legally set a final field after construction), even though getters are still generated for non-static fields including final ones.

**Q: Why is `@Builder` often paired with immutability?**
A: Because a builder lets you construct an object piece-by-piece across multiple calls before finally producing the object via `.build()`, without exposing any setters afterward — the resulting object's fields can never be mutated once built, achieving the same effect as a traditional immutable class with an all-args constructor, but with more readable, self-documenting construction code.
