# Spring Boot: `@ConfigurationProperties` In-Depth

## What is this? (Plain English)

Imagine you're filling out a government form with 30 fields — name, age, address, preferences — one box at a time, copying each value by hand from a separate sheet of paper. That's `@Value`: you inject one property into one field, one annotation at a time. `@ConfigurationProperties` is the alternative where you hand the whole form to a clerk (Spring's binder) who reads the entire sheet of paper and fills out the whole form — including nested sections like "Address" — for you in one shot, and then double-checks the answers against your rules (validation) before letting the form go through.

**The core rule:** `@ConfigurationProperties` maps a *group* of related configuration values from `application.properties`/`.yml` into a single, structured, reusable, and optionally validated Java object — instead of wiring each value one field at a time.

## The Problem It Solves

`@Value` has two real problems once configuration grows past a handful of properties:

1. **Duplication / doesn't scale.** Every single property needs its own `@Value("${...}")` annotation on its own field. If you have 10 related properties, that's 10 separate annotations repeated across your codebase. In large tech organizations, where configuration is huge and much of the system behavior is configuration-driven, this becomes unmanageable.
2. **No built-in validation.** With `@Value`, once a value is injected there is no declarative way to say "this password must be between 10 and 25 characters" or "this must not be null." You'd have to manually validate every value yourself after injection.

`@ConfigurationProperties` solves both: it binds a whole group of related properties into one Java object (structured + reusable — inject it anywhere and reuse the same object), and it supports declarative validation via annotations on top of that object.

## How `@ConfigurationProperties` Binding Works (ASCII)

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

```text
application.properties/yml
(user.name=..., user.age=..., user.active=...)
              |
              v
    Spring Boot Binder
 (relaxed binding: kebab-case /
  camelCase / underscore all match)
              |
              v
   How is the bean registered?
    /                         \
   /                           \
@Component +               @ConfigurationPropertiesScan
@ConfigurationProperties   or @EnableConfigurationProperties
   |                                    |
   v                                    v
Spring creates EMPTY bean       Binder creates the bean itself
(default no-arg constructor,    by invoking the all-args
fields = null/0/false)          constructor (constructor binding)
   |                                    |
   v                                    v
Binder calls SETTER methods      Fields set once at construction
to fill each field                (final fields -> immutable,
                                   no setters needed)
   \                                    /
    \                                  /
     v                                v
      Fully-populated bean registered in ApplicationContext
                       |
                       v
          Is @Validated present on the class?
           /                          \
          yes                          no
           |                            |
           v                            v
   JSR-303 checks run              Bean injected wherever
 (@NotBlank, @Min, @Max...)        needed (@Autowired)
 app FAILS TO START on violation          |
           |                              |
           +--------------> Bean injected wherever needed
```

### Note on nested objects, lists, and maps

The diagram above covers simple flat properties. `@ConfigurationProperties` also binds richer shapes onto the same Java object:

- **Nested object** (e.g. `user.address.city`, `user.address.country`): modeled as a **static nested class** inside the outer configuration class, with its own getters/setters and matching field names.
- **List** (e.g. `user.roles[0]=admin`, `user.roles[1]=editor`, or a list of objects like `user.courses[0].name`): modeled as a `List<String>` or `List<SomeStaticNestedClass>` field, bound in index order.
- **Map** (e.g. `user.preference.theme=dark`, or `user.locations.home.city=...`): modeled as a `Map<String, String>` or `Map<String, SomeStaticNestedClass>` field, where the property segment right after the map's field name becomes the map key.

**Why the nested class must be `static`:** when the binder needs to populate a nested field, it uses reflection to instantiate that nested type via its **no-arg constructor**. A non-static inner class's implicit constructor actually takes a hidden reference to the enclosing instance (`Outer.new Inner()`) — there is no true no-arg constructor. The binder's reflection call fails in that case, so binding breaks. A `static` nested class has a real no-arg constructor, which is what the binder can invoke — so it must always be static.

## Key Code / Config

### 1. Simple flat properties (setter-based binding)

```properties
user.name=John
user.age=27
user.active=true
```

```java
@Component
@ConfigurationProperties(prefix = "user")
public class UserConfiguration {

    private String name;
    private int age;
    private boolean active;

    // getters and setters required — the binder uses setters to populate fields
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public int getAge() { return age; }
    public void setAge(int age) { this.age = age; }

    public boolean isActive() { return active; }
    public void setActive(boolean active) { this.active = active; }
}
```

Usage anywhere in the codebase:

```java
@Autowired
private UserConfiguration userConfiguration;

// userConfiguration.getName(), getAge(), isActive()
```

Relaxed binding means `user.is-enabled` in properties can bind to a field named `isEnabled`/`enabled` via kebab-case/camelCase matching — but keeping property names and field names identical is safer, since the binder's automatic matching isn't guaranteed for every naming variation.

### 2. Nested object

```properties
user.address.city=Bangalore
user.address.country=India
```

```java
@Component
@ConfigurationProperties(prefix = "user")
public class UserConfiguration {

    private String name;
    private int age;
    private boolean active;
    private AddressConfig address;

    // ... getters/setters for name, age, active

    public AddressConfig getAddress() { return address; }
    public void setAddress(AddressConfig address) { this.address = address; }

    // MUST be static so the binder can invoke its no-arg constructor via reflection
    public static class AddressConfig {
        private String city;
        private String country;

        public String getCity() { return city; }
        public void setCity(String city) { this.city = city; }
        public String getCountry() { return country; }
        public void setCountry(String country) { this.country = country; }
    }
}
```

### 3. List of primitives and list of objects

```properties
user.roles[0]=admin
user.roles[1]=editor

user.courses[0].name=Java
user.courses[0].enrolled=true
user.courses[1].name=Spring
user.courses[1].enrolled=false
```

```java
private List<String> roles;
private List<Course> courses; // getters/setters omitted for brevity

public static class Course {
    private String name;
    private boolean enrolled;
    // getters/setters
}
```

### 4. Map of strings and map of objects

```properties
user.preference.theme=dark
user.preference.language=en
user.preference.timeZone=IST

user.locations.home.city=Bangalore
user.locations.home.country=India
user.locations.office.city=Pune
user.locations.office.country=India
```

```java
private Map<String, String> preference;      // key = theme/language/timeZone
private Map<String, AddressConfig> locations; // key = home/office, value = nested object

// getters/setters
```

### 5. Registering the bean: `@Component` vs `@ConfigurationPropertiesScan`

- With `@Component` on the configuration class, Spring itself creates the (empty) bean via the default no-arg constructor, and the binder then calls setters to fill it in.
- Alternatively, put `@ConfigurationPropertiesScan` on the main application class (or use `@EnableConfigurationProperties(UserConfiguration.class)`) to hand the *entire* responsibility — creating the object and binding it — to the configuration binder itself:

```java
@SpringBootApplication
@ConfigurationPropertiesScan
public class MyApplication {
    public static void main(String[] args) {
        SpringApplication.run(MyApplication.class, args);
    }
}
```

### 6. Validation (`@Validated` + JSR-303)

Requires the `spring-boot-starter-validation` dependency, which brings in the validation annotations.

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
</dependency>
```

```java
@Component
@ConfigurationProperties(prefix = "user")
@Validated
public class UserConfiguration {

    @NotBlank(message = "name must not be empty")
    private String name;

    @Min(value = 1, message = "age cannot be zero")
    private int age;

    private boolean active;

    // getters/setters
}
```

Validation runs after the properties are bound and **before the application fully starts** — if a constraint is violated (e.g. `user.age=0` with `@Min(1)`), the application fails to start with the given error message. Other commonly used constraints follow the same (Hibernate Validator-based) style: `@NotNull`, `@NotEmpty` (for lists/maps), `@Max`, `@Positive`, `@PositiveOrZero`, `@Negative`, `@NegativeOrZero`.

### 7. Immutable configuration via constructor binding

Making a `@ConfigurationProperties` class immutable means: `final` fields, no setters, and all values supplied through the constructor at object-creation time — instead of created empty and mutated afterward via setters.

```java
@ConfigurationProperties(prefix = "user")
public class ImmutableUserConfiguration {

    private final String name;
    private final int age;
    private final boolean active;

    public ImmutableUserConfiguration(String name, int age, boolean active) {
        this.name = name;
        this.age = age;
        this.active = active;
    }

    public String getName() { return name; }
    public int getAge() { return age; }
    public boolean isActive() { return active; }
}
```

Note the key differences from the mutable version:

- **No `@Component`.** With `@Component`, Spring's IoC container would try to create the bean itself, but it has no way of knowing what constructor arguments to pass — so `@Component` is removed and the responsibility for creating the object is handed to the configuration binder instead (via `@ConfigurationPropertiesScan`/`@EnableConfigurationProperties` on the main class, as shown above). The binder already knows the property values, so it can call this constructor directly with the correct arguments.
- **No setters, `final` fields.** Once constructed, the values can never change — a true immutable object.

(Note: on Spring Boot versions before 3.0, a class with a single parameterized constructor may additionally need the `@ConstructorBinding` annotation for the binder to recognize constructor binding instead of setter binding; Spring Boot 3+ infers this automatically when there is exactly one parameterized constructor.)

## Important Concepts

- **`@Value`**: injects a single property into a single field — simple but doesn't scale for large/grouped configuration and has no built-in validation.
- **`@ConfigurationProperties`**: binds a *group* of related properties (sharing a common prefix) into one structured, reusable Java object.
- **Configuration Binding**: the process (performed by Spring Boot's `Binder`) of reading properties and populating a `@ConfigurationProperties` object's fields — either via setters (bean already exists) or via a constructor (constructor binding).
- **Relaxed Binding**: the binder tolerates kebab-case, camelCase, and similar naming variants between property keys and Java field names — though matching names exactly is the safest choice.
- **Static nested class requirement**: nested configuration objects must be `static` nested classes, because the binder instantiates them via reflection using a true no-arg constructor, which only exists on `static` nested classes (non-static inner classes implicitly require a reference to the enclosing instance).
- **List/Map binding**: `@ConfigurationProperties` can bind indexed properties (`prop[0]`, `prop[1]`) into a `List`, and dotted key segments (`prop.key.field`) into a `Map`, including maps/lists of nested objects.
- **`@Validated` + JSR-303 annotations**: enables declarative validation (`@NotBlank`, `@NotNull`, `@Min`, `@Max`, `@Positive`, `@Negative`, etc., internally powered by Hibernate Validator) on top of a bound configuration object; requires `spring-boot-starter-validation`. Validation runs after binding and before the app fully starts — a violation prevents startup.
- **Constructor Binding (immutability)**: supplying all field values through the constructor at creation time instead of via setters, producing an immutable configuration object (`final` fields, no setters). Requires removing `@Component` and instead registering the class via `@ConfigurationPropertiesScan` (or `@EnableConfigurationProperties`) so the binder — not Spring's default IoC bean creation — is responsible for constructing the object.

## Interview Q&A

**Q: What are the two main problems with `@Value` that `@ConfigurationProperties` solves?**
A: First, duplication/scaling — every property needs its own `@Value` annotation, which becomes unmanageable as configuration grows in large systems. Second, no validation — with `@Value` there's no declarative way to enforce constraints (length, range, non-null) on injected values; you'd have to validate manually after injection.

**Q: Why must a nested configuration class (like an `AddressConfig` inside a `UserConfiguration`) be declared `static`?**
A: The binder populates nested fields via reflection, calling the nested class's no-arg constructor. A non-static inner class's implicit constructor actually requires a reference to its enclosing instance (there's no true no-arg constructor), so reflection-based instantiation fails. A static nested class has a genuine no-arg constructor, which the binder can invoke successfully.

**Q: How do you make a `@ConfigurationProperties` class immutable, and how is the sequence different from the mutable version?**
A: Use constructor binding: make all fields `final`, remove setters, and supply every value through the constructor. In the mutable version, Spring creates an empty bean first (default constructor, default field values) and the binder later calls setters to update it. In the immutable version there's no empty-bean step — the binder invokes the class's constructor directly with the correct values already read from the properties, so the object is fully and permanently initialized at creation time.

**Q: Why do you have to remove `@Component` when switching to an immutable, constructor-bound configuration class?**
A: With `@Component`, Spring's IoC container manages bean creation itself, but for an immutable class it doesn't know what argument values to pass into the constructor. Removing `@Component` and instead using `@ConfigurationPropertiesScan` (or `@EnableConfigurationProperties`) hands the responsibility for creating the object to the configuration binder, which already knows the correct values from `application.properties` and can invoke the constructor correctly.

**Q: When does validation run for a `@ConfigurationProperties` class, and what happens if a constraint fails?**
A: Validation runs after the binder has finished populating the object's fields, and before the application has fully started. It requires `@Validated` on the class plus JSR-303 annotations (`@NotBlank`, `@Min`, `@Max`, etc.) on the fields, and depends on the `spring-boot-starter-validation` dependency. If any constraint is violated, the application fails to start, showing the configured validation message.

**Q: Can `@ConfigurationProperties` bind lists and maps, not just flat/nested objects?**
A: Yes. Indexed properties like `user.roles[0]=admin`, `user.roles[1]=editor` bind into a `List<String>` in order; indexed object properties like `user.courses[0].name=...` bind into a `List` of a static nested class. Dotted-key properties like `user.preference.theme=dark` bind into a `Map<String, String>` where the segment after the map's field name becomes the key; the same pattern extends to a `Map` of nested objects (e.g. `user.locations.home.city=...` into `Map<String, AddressConfig>`).
