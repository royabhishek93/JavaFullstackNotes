# Q13: Third Highest Salary with Optional (Java 8 Streams)

**Study Time:** 6-8 minutes | **Frequency:** 65% in interviews 🔥 | **Difficulty:** ⭐⭐⭐

---

## Scenario

**Find the third highest distinct salary** using Java 8 Streams:

```java
Optional<Integer> thirdHighest =
        employees.stream()
                .map(Employee::getSalary)
                .distinct()
                .sorted(Comparator.reverseOrder())
                .skip(2)
                .findFirst();
```

---

## Key Principle

- `distinct()` removes duplicates
- `sorted(reverseOrder())` gives descending order
- `skip(2)` ignores top two
- `findFirst()` returns the third highest if it exists

---

## Complete Example

```java
List<Employee> employees = Arrays.asList(
    new Employee("A", 90),
    new Employee("B", 120),
    new Employee("C", 120),
    new Employee("D", 110),
    new Employee("E", 100)
);

Optional<Integer> thirdHighest = employees.stream()
        .map(Employee::getSalary)
        .distinct()
        .sorted(Comparator.reverseOrder())
        .skip(2)
        .findFirst();

System.out.println(thirdHighest.orElse(null));
// Output: 100
```

Distinct salaries: `120, 110, 100, 90`
Third highest → `100`

---

## Edge Cases

### Case 1: Less than 3 distinct salaries

```java
List<Employee> employees = Arrays.asList(
    new Employee("A", 100),
    new Employee("B", 100),
    new Employee("C", 90)
);

Optional<Integer> thirdHighest = employees.stream()
        .map(Employee::getSalary)
        .distinct()
        .sorted(Comparator.reverseOrder())
        .skip(2)
        .findFirst();

System.out.println(thirdHighest.isPresent());
// false
```

---

## Interview Q&A

### Q1: Why use `distinct()`?

**Answer:**
```
To avoid duplicates. If the top salary appears twice,
we still want the third DISTINCT highest value.
```

---

### Q2: What is the time complexity?

**Answer:**
```
O(n log n) due to sorting.
```

---

### Q3: Can we do it without sorting?

**Answer:**
```
Yes, use a TreeSet with size 3 or a min-heap of size 3.
That gives O(n log k) with k=3.
```

---

## Alternative (TreeSet)

```java
TreeSet<Integer> top3 = new TreeSet<>();
for (Employee e : employees) {
    top3.add(e.getSalary());
    if (top3.size() > 3) {
        top3.pollFirst();
    }
}

Integer thirdHighest = top3.size() == 3 ? top3.first() : null;
```

---

## Interview Answer (Concise)

**Q: "Find the third highest distinct salary using streams."**

**Answer:**

> "Map salaries, remove duplicates, sort descending, skip two, and take the first. The result is wrapped in `Optional` to handle fewer than three distinct salaries."

---

## Key Takeaways

| Concept | Why It Matters | Interview Score |
|---------|----------------|-----------------|
| distinct() | Removes duplicates | ⭐⭐⭐⭐ |
| skip(2) | Picks third highest | ⭐⭐⭐⭐ |
| Optional | Null-safe result | ⭐⭐⭐⭐ |
| Sorting cost | Complexity awareness | ⭐⭐⭐⭐ |
