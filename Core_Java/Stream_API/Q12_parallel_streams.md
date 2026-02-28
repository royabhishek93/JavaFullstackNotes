# 🎯 Q12: When to Use Parallel Streams and What to Watch For?

> **Interview Frequency:** 68% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Understanding when parallel streams improve performance and when they hurt it.

### Code Scenario
```java
List<Integer> numbers = IntStream.rangeClosed(1, 1_000_000)
    .boxed()
    .collect(Collectors.toList());

// Sequential: 2ms
long seq = numbers.stream()
    .filter(n -> isPrime(n))
    .count();

// Parallel: 5ms (SLOWER!)
long par = numbers.parallelStream()
    .filter(n -> isPrime(n))
    .count();
```

---

## 📌 Why It Happens

**Parallel streams use multiple threads** but have overhead:
1. **Thread creation** - expensive
2. **Context switching** - CPU overhead
3. **Data splitting** - dividing work
4. **Result merging** - combining thread results

For small datasets or light operations, this overhead **exceeds the gain**.

---

## ❌ Wrong (Using Parallel Everywhere)

```java
// WRONG: Parallel on small list
List<Integer> small = Arrays.asList(1, 2, 3, 4, 5);
small.parallelStream()
    .map(n -> n * 2)
    .collect(Collectors.toList());
// Overhead > benefit!

// WRONG: Parallel with stateful operations
List<Integer> numbers = // large list
numbers.parallelStream()
    .peek(n -> System.out.println(n))  // Racing condition!
    .collect(Collectors.toList());

// WRONG: Parallel with synchronized() or locks
numbers.parallelStream()
    .forEach(n -> synchronized(lock) {  // Defeats parallelism!
        // locked code
    });
```

---

## ✅ Right (Strategic Parallel Use)

```java
// RIGHT: Parallel on LARGE dataset with expensive operation
List<Integer> large = IntStream.rangeClosed(1, 10_000_000)
    .boxed()
    .collect(Collectors.toList());

// Expensive calculation, large dataset = worth parallel overhead
long primes = large.parallelStream()
    .filter(n -> isPrime(n))  // CPU-intensive
    .count();

// RIGHT: Parallel with stateless operations only
List<String> results = large.parallelStream()
    .filter(n -> n % 2 == 0)      // Stateless
    .map(String::valueOf)          // No side effects
    .collect(Collectors.toList()); // Thread-safe collector

// RIGHT: Parallel with proper combiner in collector
Map<String, Long> counts = large.parallelStream()
    .collect(Collectors.groupingBy(
        String::valueOf,
        Collectors.counting()  // Combiner handles merge
    ));
```

---

## 💬 Interview Tip (Say This Exactly)

"Use parallel streams for large datasets (10k+) with CPU-intensive operations. Avoid parallel with I/O, side effects, or small lists. The overhead of thread creation usually exceeds benefit."

---

## ☑️ Quick Checklist

- ✅ Parallel only for LARGE datasets (>10,000 elements)
- ✅ Parallel only for CPU-INTENSIVE operations (not I/O)
- ✅ Use STATELESS operations (no shared mutable state)
- ✅ AVOID `.peek()` (debugging breaks parallelism)
- ✅ AVOID `.forEach()` with side effects
- ✅ Use collectors with proper combiner
- ✅ Don't use locks/synchronized (defeats parallelism)
- ✅ Measure performance with JMH (don't guess)

---

## 📚 Real Flipkart Scenario

```java
// Process 1M orders: parallel makes sense
class Order {
    long id;
    double amount;
    String customerId;
}

List<Order> orders = // 1 million orders from DB

// RIGHT: Expensive calculation on large dataset
Map<String, Double> totalsByCustomer = orders.parallelStream()
    .collect(Collectors.groupingBy(
        Order::getCustomerId,
        Collectors.summingDouble(Order::getAmount)
    ));
// Parallelism + proper combiner = fast!

// WRONG: Should NOT be parallel
orders.parallelStream()
    .forEach(order -> database.save(order));  // I/O operation!
    // Concurrent DB access = slower + possible issues

// RIGHT: Sequential for I/O
orders.stream()
    .forEach(order -> database.save(order));  // I/O is sequential

// RIGHT: Find expensive orders in parallel
List<Order> expensive = orders.parallelStream()
    .filter(o -> o.amount > 10000)  // Stateless filter
    .collect(Collectors.toList());
```

---

## ⚠️ Common Pitfalls

**Pitfall 1: Using parallel streams for I/O operations**
```java
// ❌ Parallel doesn't help I/O - actually slower!
list.parallelStream()
    .forEach(item -> database.save(item));  // DB bottleneck, not CPU

// ✅ Use sequential for I/O
list.stream().forEach(item -> database.save(item));
```

**Pitfall 2: Shared mutable state in parallel operations**
```java
List<String> results = new ArrayList<>();  // ❌ Not thread-safe!
list.parallelStream()
    .forEach(item -> results.add(item.toUpperCase()));  // Race condition!

// ✅ Use proper collector
List<String> results = list.parallelStream()
    .map(String::toUpperCase)
    .collect(Collectors.toList());  // Thread-safe collector
```

**Pitfall 3: Using parallel for small datasets**
```java
// ❌ Overhead > benefit for < 1000 elements
List.of(1, 2, 3, 4, 5).parallelStream().filter(...);  // Slower than sequential!

// ✅ Use parallel only for large datasets
if (list.size() > 10000) {
    list.parallelStream()...
} else {
    list.stream()...
}
```

**Pitfall 4: Order-dependent operations in parallel**
```java
// ❌ Order not guaranteed in parallel
list.parallelStream().forEach(System.out::println);  // Random order!

// ✅ Use forEachOrdered() if order matters
list.parallelStream().forEachOrdered(System.out::println);
// Or just use sequential: list.stream().forEach(...)
```

**Pitfall 5: Using non-thread-safe collectors**
```java
// ❌ HashMap not thread-safe
Map<String, Integer> map = list.parallelStream()
    .collect(HashMap::new, (m, s) -> m.put(s, s.length()), HashMap::putAll);

// ✅ Use Collectors.toMap() or ConcurrentHashMap
Map<String, Integer> map = list.parallelStream()
    .collect(Collectors.toMap(s -> s, String::length));
```

**Pitfall 6: Blocking operations in parallel stream**
```java
// ❌ Thread.sleep() blocks ForkJoinPool threads
list.parallelStream().forEach(item -> {
    Thread.sleep(1000);  // Blocks thread!
    process(item);
});
```

---

## 🛑 When NOT to Use Parallel Streams

- ❌ Small datasets (< 1000 elements)
- ❌ I/O-bound operations (DB, file, network)
- ❌ Operations with locks/synchronization
- ❌ Order-dependent logic
- ❌ Complex stateful operations
- ✅ DO use: CPU-intensive calculations on large datasets (> 10k), pure functions, stateless operations

---

## ➡️ Bonus Follow-ups

1. **"When is parallel SLOWER?"** → Small datasets, I/O operations, complex side effects
2. **"How to debug parallel streams?"** → Don't use `.peek()`, test sequential first
3. **"Thread pool for parallelStream()?** → ForkJoinPool.commonPool(), can configure
4. **"Is HashMap safe in parallelStream()?"** → No, use thread-safe collector

---

## 🔗 Related Questions

- **Q8:** `.map()` & `.flatMap()` (must be stateless in parallel)
- **Q11:** Custom Collectors (combiner is critical for parallel)
- **Q9:** Lazy Evaluation (parallel has different execution model)

---

**Last Updated:** February 22, 2026  
**Previous: [Q11_collectors_custom.md](Q11_collectors_custom.md) | Next: [../../System_Design/Q17_database_scaling.md](../../System_Design/Q17_database_scaling.md)**
