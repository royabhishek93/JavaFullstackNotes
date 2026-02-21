# Q6: What's the difference between `new ArrayList<>(list)` and `.clone()`?

**Study Time:** 2-3 minutes

---

## Problem

Defensive copying - which method to use?

## Code Scenario

```java
List<String> original = new ArrayList<>();
original.add("item1");

List<String> copy1 = original.clone();       // Method 1
List<String> copy2 = new ArrayList<>(original);  // Method 2
```

## Why It Matters

Both create copies, but there's a crucial difference when the list contains **mutable objects**.

## Deep vs Shallow Copy

```java
// Shallow copy - elements are still referenced
List<Person> people = new ArrayList<>();
people.add(new Person("John", 25));

List<Person> shallow = new ArrayList<>(people);
shallow.get(0).setAge(30);  // ❌ Modifies original!

// Deep copy - new person objects
List<Person> deep = people.stream()
    .map(p -> new Person(p.getName(), p.getAge()))
    .collect(Collectors.toList());
deep.get(0).setAge(30);  // ✅ Original unchanged
```

## ✅ For Immutable Elements (Strings, Integers)

```java
List<String> original = new ArrayList<>(Arrays.asList("a", "b", "c"));
List<String> copy = new ArrayList<>(original);  // Safe - Strings are immutable
```

## ❌ For Mutable Elements

```java
List<Person> original = new ArrayList<>();
original.add(new Person("John", 25));

List<Person> shallow = new ArrayList<>(original);  // Unsafe - Person is mutable
shallow.get(0).setAge(30);  // Modifies original person object!
```

## Interview Tip

"Use `new ArrayList<>(list)` for defensive copying of immutable elements. For mutable objects in the list, do deep copy using streams or iteration. Shallow vs deep depends on what's inside the collection."

## Quick Checklist

- ✅ `new ArrayList<>(list)` for immutable elements
- ✅ `.clone()` is another option but less clear
- ✅ Shallow copy = fine for String, Integer, etc.
- ✅ Deep copy needed for object collections
- ✅ Use streams for elegant deep copy
- ✅ Always consider element mutability

---

**Next:** Study Q7 on returning mutable collections safely
