# 🎯 Q9: Explain Lazy Evaluation in Streams

> **Interview Frequency:** 88% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Why do intermediate operations (`.map()`, `.filter()`) NOT execute until a terminal operation? Why does this matter?

### Code Scenario
```java
List<Integer> numbers = Arrays.asList(1, 2, 3, 4, 5);

// When does the lambda execute?
Stream<Integer> stream = numbers.stream()
    .map(n -> {
        System.out.println("Mapping: " + n);
        return n * 2;
    });

// Nothing printed yet! Why?
System.out.println("No output above!");

// Now print final result
stream.forEach(n -> System.out.println("Result: " + n));
```

---

## 📌 Why It Happens

Streams are **lazy** - intermediate operations don't execute until:
1. A **terminal operation** is called (`.forEach()`, `.collect()`, `.reduce()`, etc.)
2. All intermediate operations are chained together
3. THEN the stream processes elements one-by-one through the entire pipeline

**Terminal Operations:** `.collect()`, `.forEach()`, `.reduce()`, `.count()`, `.findFirst()`, `.anyMatch()`, `.allMatch()`

**Intermediate Operations:** `.map()`, `.filter()`, `.flatMap()`, `.distinct()`, `.sorted()`

---

## ❌ Wrong (Expecting Immediate Execution)

```java
List<Integer> numbers = Arrays.asList(1, 2, 3, 4, 5);

// WRONG: Thinking map() executes here
numbers.stream()
    .map(n -> {
        System.out.println("Mapping: " + n);  // NOT executed yet!
        return n * 2;
    });

System.out.println("Done");  // Prints immediately - map() didn't execute!
```

Output:
```
Done
```

---

## ✅ Right (Terminal Operation Triggers Execution)

```java
List<Integer> numbers = Arrays.asList(1, 2, 3, 4, 5);

// RIGHT: Terminal operation (.collect()) triggers execution
List<Integer> doubled = numbers.stream()
    .map(n -> {
        System.out.println("Mapping: " + n);  // NOW it executes!
        return n * 2;
    })
    .collect(Collectors.toList());

System.out.println("Done");
```

Output:
```
Mapping: 1
Mapping: 2
Mapping: 3
Mapping: 4
Mapping: 5
Done
```

---

## 💬 Interview Tip (Say This Exactly)

"Streams are lazy. Intermediate operations like `.map()` and `.filter()` don't execute until a terminal operation is called. This is done for performance optimization - unnecessary operations are skipped and processing stops early when possible."

---

## ☑️ Quick Checklist

- ✅ Intermediate operations are lazy (don't execute immediately)
- ✅ Terminal operations trigger execution (`.collect()`, `.forEach()`, `.count()`)
- ✅ Short-circuit operations stop early (`.findFirst()`, `.anyMatch()`)
- ✅ Each element flows through entire pipeline (not processing all with first op)
- ✅ Lazy evaluation enables optimization and prevents unnecessary work

---

## 📚 Real Flipkart Scenario

```java
// Performance-critical: Find first product under price with discount applied
class Product {
    String id;
    double price;
    boolean inStock;
}

List<Product> products = // 10 million products

Product cheapest = products.stream()
    .filter(p -> {
        System.out.println("Checking stock: " + p.id);
        return p.inStock;  // Expensive DB call
    })
    .filter(p -> {
        System.out.println("Checking price: " + p.id);
        return p.price < 1000;
    })
    .map(p -> {
        System.out.println("Applying discount: " + p.id);
        p.price *= 0.9;
        return p;
    })
    .findFirst()  // Terminal operation - stops after first match!
    .orElse(null);

// Output: Only checks until FIRST product found matching criteria
// If item #3 matches, items #4-10M are NEVER checked!
// Lazy evaluation is crucial for performance here!
```

---

## ➡️ Bonus Follow-ups

1. **"What's the difference between lazy and eager evaluation?"** → Lazy: execute on-demand. Eager: execute immediately.
2. **"Does forEach() execute lazily?"** → No, it's terminal and executes everything.
3. **"How to make stream execution eager?"** → Add a terminal operation immediately (but defeats lazy advantage).

---

## 🔗 Related Questions

- **Q8:** `.map()` vs `.flatMap()` (understand how they're lazily combined)
- **Q12:** Parallel Streams (same lazy principles apply)
- **Q11:** Custom Collectors (terminal operations that enable lazy processing)

---

**Last Updated:** February 22, 2026  
**Next: [Q10_optional_usage.md](Q10_optional_usage.md)**
