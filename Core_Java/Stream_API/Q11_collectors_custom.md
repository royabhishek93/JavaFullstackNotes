# 🎯 Q11: How to Create Custom Collectors?

> **Interview Frequency:** 72% | **Difficulty:** ⭐⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Understanding `Collectors` API and creating custom collectors for complex aggregations.

### Code Scenario
```java
List<Product> products = // products list

// Can easily collect to List
List<String> names = products.stream()
    .map(Product::getName)
    .collect(Collectors.toList());

// What about custom collection logic?
Map<String, List<Product>> byCategory = // How to create?
```

---

## 📌 Why It Happens

`Collectors` provide:
1. **Pre-built collectors** for common operations (toList, toMap, groupingBy)
2. **Custom collectors** for specialized logic via `Collector.of()`

---

## ❌ Wrong (Imperative Loop Instead of Collector)

```java
// WRONG: Manual aggregation - miss stream benefits
List<String> categories = new ArrayList<>();
Set<String> uniqueCategories = new HashSet<>();

for (Product p : products) {
    for (String cat : p.getCategories()) {
        if (!uniqueCategories.contains(cat)) {
            categories.add(cat);
            uniqueCategories.add(cat);
        }
    }
}
```

---

## ✅ Right (Using Built-in & Custom Collectors)

```java
// RIGHT: Using built-in collectors
Map<String, Long> categoryCounts = products.stream()
    .flatMap(p -> p.getCategories().stream())
    .collect(Collectors.groupingBy(
        Function.identity(),
        Collectors.counting()
    ));

// RIGHT: Custom collector for unique, ordered categories
List<String> uniqueCategories = products.stream()
    .flatMap(p -> p.getCategories().stream())
    .collect(Collectors.toCollection(LinkedHashSet::new))
    .stream()
    .collect(Collectors.toList());

// RIGHT: Custom collector from scratch
List<String> customCollected = products.stream()
    .map(Product::getName)
    .collect(
        Collector.of(
            ArrayList::new,           // Supplier: create container
            List::add,                // Accumulator: add element
            (list1, list2) -> {       // Combiner: merge parallel results
                list1.addAll(list2);
                return list1;
            }
        )
    );
```

---

## 💬 Interview Tip (Say This Exactly)

"Use `Collectors.groupingBy()` for grouping, `toMap()` for key-value pairs. For complex logic, create custom collectors with `Collector.of()` providing supplier, accumulator, and combiner functions."

---

## ☑️ Quick Checklist

- ✅ `Collectors.toList()` - collect to ArrayList
- ✅ `Collectors.toSet()` - unique elements
- ✅ `Collectors.toMap(keyFunc, valueFunc)` - create map
- ✅ `Collectors.groupingBy(classifier)` - group by key
- ✅ `Collectors.groupingBy(classifier, downstream)` - nested aggregation
- ✅ `Collectors.joining(delimiter)` - concat strings
- ✅ `Collector.of(supplier, accumulator, combiner)` - custom collector
- ✅ Supplier: creates empty container
- ✅ Accumulator: adds element to container
- ✅ Combiner: merges two containers (for parallel streams)

---

## 📚 Real Flipkart Scenario

```java
class Product {
    String id;
    String category;
    double price;
    int rating;
}

// Group products by category with average price
Map<String, Double> avgPriceByCategory = products.stream()
    .collect(Collectors.groupingBy(
        Product::getCategory,
        Collectors.averagingDouble(Product::getPrice)
    ));

// Group by category and then get top-rated product in each
Map<String, Optional<Product>> topRatedByCategory = products.stream()
    .collect(Collectors.groupingBy(
        Product::getCategory,
        Collectors.maxBy(Comparator.comparing(Product::getRating))
    ));

// Custom: Collect to CSV-like format per category
Map<String, String> csvByCategory = products.stream()
    .collect(Collectors.groupingBy(
        Product::getCategory,
        Collectors.mapping(
            p -> p.id + "," + p.price,
            Collectors.joining("|")
        )
    ));

// Custom collector: Collect with running totals
class Revenue {
    double total = 0;
    List<Product> products = new ArrayList<>();
}

List<Revenue> revenueAccum = products.stream()
    .collect(
        Collector.of(
            () -> new ArrayList<Revenue>(),
            (list, product) -> {
                Revenue latest = list.isEmpty() ? 
                    new Revenue() : list.get(list.size() - 1);
                if (latest.total + product.price > 10000) {
                    latest = new Revenue();
                    list.add(latest);
                }
                latest.total += product.price;
                latest.products.add(product);
            },
            (list1, list2) -> {
                list1.addAll(list2);
                return list1;
            }
        )
    );
```

---

## ➡️ Bonus Follow-ups

1. **"When do you need combiner in Collector?"** → For parallel streams, merges results from different threads
2. **"Collectors vs reduce()?"** → Collectors for stateful aggregation, reduce() for functional reduction
3. **"Can collectors be reused?"** → Yes, multiple times on different streams

---

## 🔗 Related Questions

- **Q8:** `.map()` vs `.flatMap()` (use together with collectors)
- **Q9:** Lazy Evaluation (collectors are terminal operations)
- **Q12:** Parallel Streams (collectors with parallel() need proper combiner)

---

**Last Updated:** February 22, 2026  
**Next: [Q12_parallel_streams.md](Q12_parallel_streams.md)**
