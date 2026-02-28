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

## ⚠️ Common Pitfalls

**Pitfall 1: Trying to mutate record fields**

❌ **Wrong approach:**
```java
public record Person(String name, int age) {}

Person p = new Person("Alice", 30);
p.name = "Bob";  // ❌ Compilation error - final field!

// Records are immutable by design
// If you find yourself wanting to mutate, records are WRONG choice
```
**Why it fails:** Records are fundamentally immutable. If your class needs mutation, use traditional class.

✅ **Right approach:**
```java
// For mutable data: use traditional class
public class Person {
    private String name;
    private int age;
    
    public void setName(String name) { this.name = name; }
}

// For immutable: use record
public record PersonRecord(String name, int age) {}

// If you need a modified version of record:
PersonRecord p = new PersonRecord("Alice", 30);
PersonRecord p2 = new PersonRecord("Bob", 30);  // Create new instance
```

---

**Pitfall 2: Using records with too many fields (should use nested records instead)**

❌ **Wrong approach:**
```java
// ❌ 15 fields in one record - hard to understand
public record UserProfile(
    String name, String email, String phone, String address,
    String city, String state, String zip, String country,
    LocalDate birthDate, String occupation, String company,
    LocalDate joinDate, String tier, int points, boolean active
) {}

// Calling it is confusing
UserProfile p = new UserProfile(
    "John", "john@...", "555-1234", "123 Main St",
    "NYC", "NY", "10001", "USA",
    LocalDate.of(1990, 1, 1), "Engineer", "Google",
    LocalDate.now(), "PREMIUM", 1000, true
);

// Which field is which?
```
**Why it fails:** Too many fields makes records unreadable and error-prone.

✅ **Right approach:**
```java
// Compose records instead
public record Address(String street, String city, String state, String zip, String country) {}
public record PersonalInfo(String name, String email, String phone, LocalDate birthDate) {}
public record ProfessionalInfo(String occupation, String company) {}
public record SubscriptionInfo(LocalDate joinDate, String tier, int points, boolean active) {}

// Main record is clean
public record UserProfile(
    PersonalInfo personal,
    Address address,
    ProfessionalInfo professional,
    SubscriptionInfo subscription
) {}

// Much clearer!
UserProfile p = new UserProfile(
    new PersonalInfo("John", "john@...", "555-1234", LocalDate.of(1990, 1, 1)),
    new Address("123 Main St", "NYC", "NY", "10001", "USA"),
    new ProfessionalInfo("Engineer", "Google"),
    new SubscriptionInfo(LocalDate.now(), "PREMIUM", 1000, true)
);
```

---

## 🛑 When NOT to Use Records

1. **When you need mutable objects** → Use traditional class
2. **For behavior-heavy objects** → Classes are better (records for data only)
3. **When you need to extend a class** → Records can't extend other records
4. **For backward compatibility with Java < 14** → Use traditional class
5. **With too many fields (10+)** → Use nested records or composition

---

**Next:** Study Q7 on Sealed Classes for type safety
