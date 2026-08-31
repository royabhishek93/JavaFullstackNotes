# 🏗️ Builder Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

**Interviewer**: "Explain the Builder Design Pattern."

**You**: "Builder Pattern solves the **'telescoping constructor' problem** - when an object has MANY optional parameters, constructors become unwieldy. Builder provides a fluent, step-by-step way to construct complex objects while keeping them IMMUTABLE."

---

## 1. Architecture Diagram

```
┌──────────────────────┐
│   Pizza (immutable)   │  ◄── Final product, no setters!
│                       │
│  size, cheese,        │
│  toppings[], crust     │
└──────────┬────────────┘
           │ constructed by
           ▼
┌──────────────────────┐
│   Pizza.Builder        │  ◄── Nested static builder class
│                       │
│  setSize()             │  Each method returns 'this' (fluent chaining)
│  addTopping()          │
│  setCrust()            │
│  build() → Pizza       │  ◄── Final method creates immutable object
└──────────────────────┘
```

## 2. Code Example - The 'Telescoping Constructor' Problem

```java
// ❌ WITHOUT Builder: Telescoping constructors nightmare
class Pizza {
    Pizza(String size) {...}
    Pizza(String size, boolean cheese) {...}
    Pizza(String size, boolean cheese, boolean pepperoni) {...}
    Pizza(String size, boolean cheese, boolean pepperoni, boolean mushroom) {...}
    // Explosion of constructors for every combination!
}

// ✅ WITH Builder Pattern
class Pizza {
    private final String size;
    private final boolean cheese;
    private final List<String> toppings;
    private final String crust;
    
    private Pizza(Builder builder) {  // Private constructor - only Builder can create!
        this.size = builder.size;
        this.cheese = builder.cheese;
        this.toppings = builder.toppings;
        this.crust = builder.crust;
    }
    
    static class Builder {
        private String size;
        private boolean cheese = false;  // Sensible defaults
        private List<String> toppings = new ArrayList<>();
        private String crust = "REGULAR";
        
        Builder setSize(String size) {
            this.size = size;
            return this;  // Enables fluent chaining!
        }
        
        Builder addCheese() {
            this.cheese = true;
            return this;
        }
        
        Builder addTopping(String topping) {
            this.toppings.add(topping);
            return this;
        }
        
        Builder setCrust(String crust) {
            this.crust = crust;
            return this;
        }
        
        Pizza build() {
            if (size == null) throw new IllegalStateException("Size is mandatory!");
            return new Pizza(this);  // Immutable object created here
        }
    }
}

// Usage - fluent, readable, only specify what you need!
Pizza pizza = new Pizza.Builder()
    .setSize("LARGE")
    .addCheese()
    .addTopping("Pepperoni")
    .addTopping("Mushroom")
    .setCrust("THIN")
    .build();
```

---

## 3. Scenario-First Explanations

### **Why Builder Instead of Setters on a Mutable Object?**

**You**: "Without Builder, you might use a no-arg constructor + setters:
```java
Pizza pizza = new Pizza();
pizza.setSize('LARGE');
pizza.setCheese(true);
// PROBLEM: Pizza object exists in INVALID/INCOMPLETE state between these calls!
// Also: pizza is MUTABLE forever - anyone can call pizza.setSize() later and corrupt it
```

Builder Pattern ensures:
1. **Immutability**: Once `build()` returns, the `Pizza` object can NEVER be changed (thread-safe by default!)
2. **Validation at construction**: The `build()` method can enforce invariants ('size is mandatory') BEFORE the object exists - no invalid intermediate states
3. **Readability**: Method chaining reads like natural language describing what you're constructing"

---

## 4. Cross Questions

**Interviewer**: "How does Builder differ from the Factory Pattern?"

**You**: "
- **Factory Pattern**: Creates ONE object in ONE call, hides WHICH concrete class to instantiate (`getShape('CIRCLE')` returns a `Circle`)
- **Builder Pattern**: Constructs a COMPLEX object STEP BY STEP over multiple method calls, dealing with MANY optional parameters

Use Factory when the choice is about WHICH TYPE to create. Use Builder when the challenge is HOW to assemble many optional pieces into one object cleanly."

---

## 5. Trade-offs

| Aspect | Builder Pattern | Telescoping Constructors | Setters (mutable) |
|--------|-------------------|------------------------------|--------------------------|
| **Readability** | Excellent (fluent) | Poor (positional args) | OK but verbose |
| **Immutability** | Yes | Yes | No |
| **Validation** | At build() time | Per constructor | Scattered, hard to enforce |

---

## 6. Senior Trap Questions

### **Trap: "Just use a constructor with default parameter values, simpler!"**

**✅ Senior**: "Java doesn't support default parameter values natively (unlike Kotlin/Python). Even in languages that DO support it, Builder Pattern still wins for objects with 5+ optional params because:
1. **Named parameters clarity**: `.setSize('LARGE').addCheese()` is self-documenting vs `new Pizza('LARGE', true, false, null, 'THIN')` - what do these booleans even mean?!
2. **Validation logic**: Builder's `build()` can validate cross-field constraints ('THIN crust requires size <= MEDIUM') that a simple constructor can't cleanly express.
3. **Immutability guarantee**: Even with default params in a constructor, you'd still need explicit immutability enforcement (final fields, no setters) - Builder naturally provides this via its 2-phase construction."

---

## 7. Technology Choices

**You**: "**Lombok's `@Builder` annotation** auto-generates this exact boilerplate in Java projects. **StringBuilder** itself is a real-world Builder (though not immutable at the end - a slight variation). Also, **OkHttp's `Request.Builder`** and **Java's `StringBuilder`/`Stream.Builder`** are production examples of this exact pattern."

---

## 🎓 Final Tips
1. **Solves telescoping constructor problem** for objects with many optional params
2. **Ensures immutability**: private constructor, only Builder can create instances
3. **Validation at build() time**: catch invalid states before object creation
4. **Different from Factory**: Builder = step-by-step assembly, Factory = choosing WHICH type

Good luck! 🚀
