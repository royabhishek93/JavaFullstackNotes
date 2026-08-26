# Q5: What makes a class immutable?

**Study Time:** 2-3 minutes

---

## Problem

Understanding all requirements for truly immutable classes.

## Why It Happens

Immutability requires multiple safeguards - no partial implementation works.

## ❌ Wrong (Partial Immutability)

```java
// Looks immutable but isn't!
public class Person {
    private final String name;
    private final List<String> hobbies;  // final reference, but list is mutable
    
    public Person(String name, List<String> hobbies) {
        this.name = name;
        this.hobbies = hobbies;  // Direct reference!
    }
}

// Usage - breaks immutability!
List<String> list = new ArrayList<>();
list.add("coding");
Person p = new Person("John", list);
list.add("gaming");  // Modifies p's hobbies!
```

## ✅ Correct (True Immutability)

```java
public final class Person {  // 1. final class
    private final String name;  // 2. final fields
    private final List<String> hobbies;
    
    // 3. Constructor with defensive copy
    public Person(String name, List<String> hobbies) {
        this.name = name;
        this.hobbies = new ArrayList<>(hobbies);  // Deep copy!
    }
    
    // 4. No setters
    
    // Getter with defensive copy
    public List<String> getHobbies() {
        return new ArrayList<>(hobbies);  // Return copy, not reference
    }
}

// Usage - safe!
List<String> list = new ArrayList<>();
list.add("coding");
Person p = new Person("John", list);
list.add("gaming");  // p is still immutable!
```

## Four Requirements for Immutability

1. **final class** - prevent inheritance/extension
2. **final fields** - prevent reassignment
3. **No setters** - prevent modification
4. **Defensive copying** - prevent external modification

## Interview Tip

"Immutable classes need FOUR things: final class, final fields, no setters, and defensive copying in constructor and getters. Missing any one breaks immutability. String is immutable because all four requirements are met."

## Quick Checklist

- ✅ `public final class` - not `public class`
- ✅ `private final fields` - all mutable fields
- ✅ No setter methods at all
- ✅ Copy in constructor: `new ArrayList<>(list)`
- ✅ Copy in getter: `new ArrayList<>(list)`
- ✅ All nested objects also immutable or copied

---

## ⚠️ Common Pitfalls

**Pitfall 1: Forgetting defensive copy in constructor**
```java
public Person(List<String> hobbies) {
    this.hobbies = hobbies;  // ❌ Shares reference - not immutable!
}
// Fix: this.hobbies = new ArrayList<>(hobbies);
```

**Pitfall 2: Returning mutable reference from getter**
```java
public List<String> getHobbies() {
    return hobbies;  // ❌ Caller can modify internal state!
}
// Fix: return new ArrayList<>(hobbies) or Collections.unmodifiableList()
```

**Pitfall 3: Not making class final**
```java
public class Person { }  // ❌ Subclass can add mutable state
// Fix: public final class Person { }
```

**Pitfall 4: Mutable nested objects**
```java
private final Address address;  // ❌ If Address is mutable, Person isn't!
// Fix: Address must also be immutable, or deep copy it
```

**Pitfall 5: Date/Calendar fields**
```java
private final Date birthDate;  // ❌ Date is mutable!
public Date getBirthDate() { return birthDate; }  // ❌ Caller can modify!

// Fix: Use LocalDate (immutable) or return new Date(birthDate.getTime())
private final LocalDate birthDate;  // ✅ LocalDate is immutable
```

---

## 🛑 When NOT to Use Immutable Classes

- ❌ Frequent state changes (game character position, counters)
- ❌ Large objects with many fields that change (creates too many objects)
- ❌ Performance-critical paths with tight memory (heap churn)
- ✅ DO use: DTOs, configuration, API responses, value objects

---

**Next:** Study Q6 on defensive copying techniques
