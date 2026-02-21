# Q6: What are Records and why were they added?

**Study Time:** 3 minutes

---

## Problem

Excessive boilerplate for immutable data holders (DTOs).

## ❌ Traditional Class (Lots of Boilerplate)

```java
public class Person {
    private final String name;
    private final int age;
    
    // Constructor
    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }
    
    // Getters
    public String getName() { return name; }
    public int getAge() { return age; }
    
    // Equals
    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Person person = (Person) o;
        return age == person.age && Objects.equals(name, person.name);
    }
    
    // HashCode
    @Override
    public int hashCode() {
        return Objects.hash(name, age);
    }
    
    // ToString
    @Override
    public String toString() {
        return "Person{" + "name='" + name + '\'' + ", age=" + age + '}';
    }
}

// Total: ~40 lines for simple data holder!
```

## ✅ Record (Same Class - 1 Line)

```java
public record Person(String name, int age) {}

// Gets automatically:
// ✅ Constructor Person(String name, int age)
// ✅ Getters name() and age()
// ✅ equals() comparing all fields
// ✅ hashCode() using all fields
// ✅ toString() showing all fields
// ✅ Immutability (final fields)

// Total: 1 line!
```

## Why They Were Added

**Problem:** DTOs, value objects, and data carriers required massive boilerplate

**Solution:** Records automatically generate everything

**Impact:** 98% less code, same safety, easier maintenance

## ✅ Usage

```java
// Create
Person p = new Person("Alice", 30);

// Use
System.out.println(p.name());     // "Alice" (note: name(), not getName())
System.out.println(p.age());      // 30

// Collections
Set<Person> people = new HashSet<>();
people.add(p);  // Works - auto-generated hashCode/equals

// Maps
Map<Person, String> jobs = new HashMap<>();
jobs.put(p, "Engineer");  // Works - records are hashable
```

## Custom Methods in Records

```java
public record Person(String name, int age) {
    // Can add custom methods
    public boolean isAdult() {
        return age >= 18;
    }
    
    // Can add validation in constructor
    public Person {
        if (age < 0) throw new IllegalArgumentException("Age cannot be negative");
    }
}

// Usage
Person p = new Person("Bob", -5);  // Throws exception ✅
```

## Records vs Classes

| Aspect | Record | Traditional Class |
|--------|--------|------------------|
| **Immutability** | ✅ Automatic | Manual |
| **Boilerplate** | ✅ None | ~40 lines |
| **Inheritance** | ❌ Cannot extend | ✅ Can extend |
| **Fields** | ✅ Auto-final | Manual final |
| **Equals/Hash** | ✅ Auto-generated | Manual @Override |
| **Use Case** | Data carriers | Behavior-heavy objects |

## Interview Tip

"Records eliminate boilerplate for immutable data classes. One line replaces ~40. They're final, all fields immutable, and auto-generate equals/hashCode/toString. Perfect for DTOs, value objects, and domain objects."

## Quick Checklist

- ✅ `public record Name(Type field1, Type field2) {}`
- ✅ Auto-generates: constructor, getters (fieldName()), equals, hashCode, toString
- ✅ Fields are final (immutable)
- ✅ Record cannot extend other records
- ✅ Record CAN implement interfaces
- ✅ Java 14+ (preview), Java 16+ (final)
- ✅ Perfect for: DTOs, REST request/response bodies, database POJOs

---

**Next:** Study Q7 on Sealed Classes for type safety
