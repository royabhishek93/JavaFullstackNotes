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

**Next:** Study Q6 on defensive copying techniques
