# 🎯 Q10: When and How to Use Optional?

> **Interview Frequency:** 75% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Understanding when to use `Optional<T>` and common pitfalls like chaining `.orElse()` unsafely.

### Code Scenario
```java
// Which is safer?
User user1 = userRepository.findById(123).orElse(null);

User user2 = userRepository.findById(456)
    .ifPresentOrElse(
        u -> System.out.println("User: " + u),
        () -> System.out.println("User not found")
    );
```

---

## 📌 Why It Happens

`Optional` was designed to:
1. Make null references **explicit** - forces you to handle absence
2. Avoid null pointer exceptions
3. Express "value may not exist" semantically

**BUT:** Misuse turns it into another null-checking mechanism!

---

## ❌ Wrong (Defeating Optional's Purpose)

```java
// WRONG: Converting back to nullable
User user = userRepository.findById(123)
    .orElse(null);  // Back to null! Defeats Optional purpose
if (user != null) { }

// WRONG: Throwing exception for flow control
String result = Optional.of(value)
    .orElseThrow(() -> new RuntimeException("Not found"));  // Bad flow control

// WRONG: Chaining with another Optional
Optional<Optional<User>> nested = userRepository.findById(123)
    .map(id -> userRepository.findById(id));  // Nested Optional!
```

---

## ✅ Right (Proper Optional Usage)

```java
// RIGHT: Use ifPresent or ifPresentOrElse
userRepository.findById(123)
    .ifPresent(user -> System.out.println("Found: " + user));

// RIGHT: Chain with flatMap to avoid nested Optional
String userName = userRepository.findById(123)
    .flatMap(user -> Optional.ofNullable(user.getPreferences()))
    .map(prefs -> prefs.getName())
    .orElse("default");

// RIGHT: Use filter for conditional logic
userRepository.findById(123)
    .filter(user -> user.isActive())
    .ifPresent(user -> sendEmail(user));

// RIGHT: Use orElseGet for lazy evaluation
String city = user.getAddress()
    .map(Address::getCity)
    .orElseGet(() -> getDefaultCity());  // Only called if empty
```

---

## 💬 Interview Tip (Say This Exactly)

"Use `Optional` to make null-handling explicit. Use `.ifPresent()` or `.filter()` + `.ifPresent()` for side effects. Use `.map()` and `.flatMap()` for transformations. Avoid `.orElse(null)` or throwing exceptions - that defeats the purpose."

---

## ☑️ Quick Checklist

- ✅ `.of(value)` - value is non-null, throws NPE if null
- ✅ `.ofNullable(value)` - handles null, returns empty Optional
- ✅ `.ifPresent(consumer)` - execute if present
- ✅ `.ifPresentOrElse(consumer, runnable)` - execute one or other
- ✅ `.map(function)` - transform if present
- ✅ `.flatMap(function)` - chain Optional-returning functions
- ✅ `.filter(predicate)` - filter by condition
- ✅ `.orElse(default)` - safe default value
- ✅ `.orElseGet(supplier)` - lazy default (prefer over orElse)
- ✅ NEVER use `.orElse(null)` or `.orElseThrow()`

---

## 📚 Real Flipkart Scenario

```java
// User preferences: Optional chain
class User {
    long id;
    Optional<Preferences> preferences;
    Optional<Address> address;
}

// Get user's city with defaults
String userCity = userRepository.findById(123)
    .flatMap(u -> u.getAddress())  // Avoid nested Optional
    .map(a -> a.getCity())
    .orElseGet(() -> "Default City");

// Apply discount if user has premium membership
userRepository.findById(456)
    .filter(u -> u.isPremium())
    .ifPresent(u -> applyDiscount(u));  // Only for premium users

// Get user email or send default notification
userRepository.findById(789)
    .flatMap(u -> u.getEmail())
    .ifPresentOrElse(
        email -> sendEmail(email),
        () -> sendPushNotification()  // Fallback
    );
```

---

## ⚠️ Common Pitfalls

**Pitfall 1: Using .get() without checking**
```java
Optional<User> opt = findUser(123);
User user = opt.get();  // ❌ NoSuchElementException if empty!
User user = opt.orElseThrow(() -> new UserNotFoundException());  // ✅ Better
```

**Pitfall 2: Using .isPresent() + .get() instead of better methods**
```java
// ❌ Verbose, defeats purpose of Optional
if (opt.isPresent()) {
    return opt.get().getName();
}
return "Unknown";

// ✅ Use map() + orElse()
return opt.map(User::getName).orElse("Unknown");
```

**Pitfall 3: Using Optional as parameter**
```java
public void process(Optional<User> user) { }  // ❌ Bad - caller confusion
public void process(User user) { }  // ✅ Use null or overload
```

**Pitfall 4: Creating Optional with .of() when value can be null**
```java
Optional<String> opt = Optional.of(getName());  // ❌ NPE if getName() returns null!
Optional<String> opt = Optional.ofNullable(getName());  // ✅ Handles null
```

**Pitfall 5: Using .orElse() with expensive operations**
```java
user.orElse(createDefaultUser());  // ❌ createDefaultUser() ALWAYS called!
user.orElseGet(() -> createDefaultUser());  // ✅ Only called if empty
```

**Pitfall 6: Nesting Optionals**
```java
Optional<Optional<String>> nested = ...;  // ❌ Bad design!
// Use .flatMap() to unwrap: opt.flatMap(Function.identity())
```

**Pitfall 7: Using Optional for collections**
```java
Optional<List<User>> users = ...;  // ❌ Use empty list instead!
List<User> users = ...;  // ✅ Return Collections.emptyList() if none
```

---

## 🛑 When NOT to Use Optional

- ❌ Method parameters (use overloading or null)
- ❌ Class fields (wastes memory, use null)
- ❌ Collections/arrays (return empty instead)
- ❌ Serializable DTOs (Optional not Serializable)
- ✅ DO use: Return values from query methods, chaining operations

---

## ➡️ Bonus Follow-ups

1. **"Should you return Optional from methods?"** → Yes, for queries. No, for setters/state changes.
2. **"Difference between .orElse() and .orElseGet()?"** → `.orElse()` evaluates always, `.orElseGet()` only if empty
3. **"Can you use Optional in streams?"** → Yes, `.flatMap(Optional::stream)` to flatten

---

## 🔗 Related Questions

- **Q8:** `.map()` vs `.flatMap()` (Optional uses same concepts)
- **Q9:** Lazy Evaluation (`.orElseGet()` is lazy)
- **Q35:** REST API (Optional for result handling)

---

**Last Updated:** February 22, 2026  
**Next: [Q11_collectors_custom.md](Q11_collectors_custom.md)**
