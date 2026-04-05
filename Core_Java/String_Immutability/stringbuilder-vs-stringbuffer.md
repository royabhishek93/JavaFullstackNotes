# StringBuilder vs StringBuffer: When to Use Each

**Study Time:** 7-9 minutes | **Frequency:** 65% in interviews | **Difficulty:** ⭐⭐⭐

---

## 🤔 Problem Scenario

Which should you use for string concatenation?

```java
// Using String concatenation (inefficient)
String result = "";
for (int i = 0; i < 1000; i++) {
    result += "item";  // Creates new string each time - O(n²)!
}

// Option 1: StringBuilder
StringBuilder sb1 = new StringBuilder();
for (int i = 0; i < 1000; i++) {
    sb1.append("item");  // Modifies same object - O(n)
}

// Option 2: StringBuffer
StringBuffer sb2 = new StringBuffer();
for (int i = 0; i < 1000; i++) {
    sb2.append("item");  // Also modifies same object - but synchronized
}

String result1 = sb1.toString();  // ~1ms
String result2 = sb2.toString();  // ~2ms
```

**Question:** Which is faster? When should you use each?

---

## 🧠 Key Principle: StringBuilder (Fast, Not Thread-Safe) vs StringBuffer (Slower, Thread-Safe)

| Feature | StringBuilder | StringBuffer |
|---------|---------------|--------------|
| **Thread-safe?** | NO | YES (synchronized) |
| **Performance** | FAST | SLOWER (sync overhead) |
| **Use case** | Single thread | Multiple threads |
| **API** | Same | Same |
| **Introduced** | Java 5 | Java 1.0 |

**Simple Rule:**
```
Single thread → StringBuilder (FAST)
Multiple threads → StringBuffer (SAFE)
```

---

## ✅ Scenario 1: StringBuilder (Single Thread - Preferred)

```java
// Building string in single-threaded context
public String buildQuery(List<String> names) {
    StringBuilder query = new StringBuilder("SELECT * FROM users WHERE id IN (");
    
    for (int i = 0; i < names.size(); i++) {
        if (i > 0) query.append(",");
        query.append("?");
    }
    
    query.append(")");
    return query.toString();
}

// Usage
String query = buildQuery(List.of("user1", "user2", "user3"));
// "SELECT * FROM users WHERE id IN (?,?,?)"
```

**Performance:**
```
Time: O(n) - single pass
Space: O(n) - result size
```

---

## ✅ Scenario 2: StringBuffer (Multi-threaded)

```java
// Shared across threads
public class ThreadSafeLogger {
    private StringBuffer log = new StringBuffer();
    
    // Called from multiple threads
    public synchronized void appendLog(String message) {
        log.append(message).append("\n");
    }
    
    // Or let StringBuffer handle sync
    public void appendLogUnsync(String message) {
        log.append(message).append("\n");  // Each method is synchronized
    }
    
    public String getLog() {
        return log.toString();
    }
}
```

**Why StringBuffer here:**
- Multiple threads append simultaneously
- Each `append()` is synchronized
- Thread-safe without external synchronization

---

## ✅ Scenario 3: Performance Comparison

```java
public class PerformanceTest {
    
    public static void main(String[] args) {
        int iterations = 100000;
        
        // Test 1: String concatenation
        long start = System.nanoTime();
        String result = "";
        for (int i = 0; i < iterations; i++) {
            result += "a";
        }
        long stringTime = System.nanoTime() - start;
        System.out.println("String: " + stringTime + "ns");  // ~5000ms (SLOW!)
        
        // Test 2: StringBuilder
        start = System.nanoTime();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < iterations; i++) {
            sb.append("a");
        }
        long sbTime = System.nanoTime() - start;
        System.out.println("StringBuilder: " + sbTime + "ns");  // ~1ms (FAST!)
        
        // Test 3: StringBuffer
        start = System.nanoTime();
        StringBuffer sbf = new StringBuffer();
        for (int i = 0; i < iterations; i++) {
            sbf.append("a");
        }
        long sbfTime = System.nanoTime() - start;
        System.out.println("StringBuffer: " + sbfTime + "ns");  // ~2ms (slower than SB)
        
        System.out.println("String is " + (stringTime / sbTime) + "x slower than SB");
    }
}

// Output (typical):
// String: 5000000000ns (5 seconds)
// StringBuilder: 1000000ns (1 millisecond)
// StringBuffer: 2000000ns (2 milliseconds)
// String is 5000x slower than SB!
```

---

## ❌ Common Mistakes

### ❌ Mistake 1: Using String Concatenation in Loop

```java
// WRONG - Creates new string each iteration
String result = "";
for (int i = 0; i < 10000; i++) {
    result += "item";  // O(n²) - very slow!
}

// Timeline:
// Iteration 1: "" + "item" = "item" (4 chars)
// Iteration 2: "item" + "item" = "itemitem" (8 chars) - copy old + new
// Iteration 3: "itemitem" + "item" (12 chars) - copy 8 chars + new
// ... keeps copying entire string each time!

// CORRECT - Use StringBuilder
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 10000; i++) {
    sb.append("item");  // O(n) - modifies same buffer
}
String result = sb.toString();
```

**Performance difference on 10000 iterations:**
```
String concat: ~100ms
StringBuilder: ~0.1ms
Improvement: 1000x FASTER!
```

---

### ❌ Mistake 2: Over-Synchronizing StringBuffer

```java
// WRONG - Double synchronization
StringBuffer sb = new StringBuffer();

synchronized(sb) {
    sb.append("a");
    sb.append("b");
    sb.append("c");
}

// WHY WRONG?
// Each append() is already synchronized
// External sync is redundant (but not harmful)

// CORRECT - Let StringBuffer handle it
StringBuffer sb = new StringBuffer();
sb.append("a");
sb.append("b");
sb.append("c");

// Each method is atomic, but sequence is not guaranteed threadsafe
// If you need atomic multi-operation:

synchronized(sb) {
    sb.append("a");
    sb.append("b");
    sb.append("c");  // This entire sequence happens atomically
}
```

---

### ❌ Mistake 3: Using StringBuilder in Multi-threaded Context

```java
// WRONG - Race condition
StringBuilder sb = new StringBuilder();

new Thread(() -> {
    for (int i = 0; i < 1000; i++) {
        sb.append("a");  // ❌ Not thread-safe
    }
}).start();

new Thread(() -> {
    for (int i = 0; i < 1000; i++) {
        sb.append("b");  // ❌ Conflicts with other thread
    }
}).start();

// Result: Unpredictable length, possibly corrupted

// CORRECT - Use StringBuffer
StringBuffer sb = new StringBuffer();  // Thread-safe

new Thread(() -> {
    for (int i = 0; i < 1000; i++) {
        sb.append("a");  // ✅ Thread-safe
    }
}).start();

new Thread(() -> {
    for (int i = 0; i < 1000; i++) {
        sb.append("b");  // ✅ Synchronized
    }
}).start();
```

---

### ❌ Mistake 4: Concatenating in Method Parameter

```java
// WRONG - Compiler inefficient
System.out.println("Value: " + value1 + " and " + value2);

// Compiler actually does:
new StringBuilder()
    .append("Value: ")
    .append(value1)
    .append(" and ")
    .append(value2)
    .toString();

// Modern compilers optimize this, but avoid:
method(str1 + str2 + str3);  // Creates intermediate strings

// Better:
StringBuilder sb = new StringBuilder();
sb.append(str1).append(str2).append(str3);
method(sb.toString());

// Or use String.join()
String result = String.join("", str1, str2, str3);
```

---

## 🎯 Interview Q&A

### Q1: "Should you use StringBuilder or StringBuffer?"

**Answer (20 seconds):**
```
StringBuilder - In almost ALL cases (single thread)

StringBuffer - Only if:
- Multiple threads accessing it
- Explicit synchronization needed

StringBuilder is FASTER (no sync overhead).
StringBuffer is THREAD-SAFE (sync built-in).

If unsure: Use StringBuilder
If multi-threaded: Use StringBuffer OR
synchronize externally + StringBuilder
```

---

### Q2: "Why not always use StringBuffer?"

**Answer:**
```
StringBuffer has synchronization overhead:
- Every method is synchronized
- Acquires/releases locks
- Slower even with one thread

Example (single thread):
StringBuilder: 1ms
StringBuffer: 2-3ms (2-3x slower)

If you're not using multiple threads,
you pay a performance penalty for sync you don't need.

RULE: Use simplest safe option
- Single thread: StringBuilder
- Multi-thread: StringBuffer OR external sync + StringBuilder
```

---

### Q3: "Can you mix StringBuilder and String concatenation?"

**Answer:**
```
YES - It's fine, compiler optimizes:

String name = "John";
String result = "Hello " + name + "!";

Modern compiler converts to:
new StringBuilder()
    .append("Hello ")
    .append(name)
    .append("!")
    .toString();

But in loops, don't rely on this:

// Bad - Relies on compiler optimization
String result = "";
for (String item : list) {
    result = result + item;  // Still O(n²) without SB
}

// Good - Explicit
StringBuilder sb = new StringBuilder();
for (String item : list) {
    sb.append(item);  // Guaranteed O(n)
}
```

---

### Q4: "What about StringJoiner or String.join()?"

**Answer:**
```
Use String.join() when you have delimiter:

NOT:
String result = item1 + "," + item2 + "," + item3;

USE:
String result = String.join(",", item1, item2, item3);
// "item1,item2,item3"

Or for collections:
String result = String.join(",", list);

Internally uses StringBuilder, but cleaner!

StringJoiner for complex cases:
StringJoiner joiner = new StringJoiner(",", "[", "]");
joiner.add("a").add("b").add("c");
System.out.println(joiner);  // [a,b,c]
```

---

## 📊 When to Use What

| Scenario | Use |
|----------|-----|
| **Single thread, building string** | StringBuilder |
| **Multiple threads, shared** | StringBuffer |
| **Joining with delimiter** | String.join() |
| **Complex joining** | StringJoiner |
| **One-time concatenation** | String + (compiler optimizes) |
| **Loop concatenation** | StringBuilder |

---

## ❌ Anti-Patterns

```java
// WRONG
String s = new String("hello");  // Unnecessary new

// WRONG
StringBuilder sb = new StringBuilder("a");
for (int i = 0; i < 1000; i++) {
    sb = new StringBuilder(sb.toString()).append("b");  // Creates new SB!
}

// WRONG
StringBuffer sb = new StringBuffer();
String result = sb.toString() + "suffix";  // Defeats purpose

// CORRECT
StringBuilder sb = new StringBuilder("a");
for (int i = 0; i < 1000; i++) {
    sb.append("b");  // Reuse same SB
}
String result = sb.append("suffix").toString();  // Chain
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| StringBuffer sync | Performance vs safety trade-off | ⭐⭐⭐⭐⭐ |
| StringBuilder default | Right tool for job | ⭐⭐⭐⭐⭐ |
| Loop concatenation | Critical performance issue | ⭐⭐⭐⭐ |
| String immutability | Understanding memory | ⭐⭐⭐⭐ |
| Modern alternatives | String.join(), StringJoiner | ⭐⭐⭐ |

---

## ✅ Best Practices

```java
// 1. Default to StringBuilder
StringBuilder sb = new StringBuilder();
sb.append("Hello ").append("World");

// 2. Use String.join() for delimiter
String csv = String.join(",", "a", "b", "c");

// 3. Chain append calls
String result = sb.append("a")
                   .append("b")
                   .append("c")
                   .toString();

// 4. Only use StringBuffer if multi-threaded
StringBuffer threadSafe = new StringBuffer();

// 5. Avoid String concatenation in loops
// ❌ String result = "" + item + item + item;
// ✅ StringBuilder sb = new StringBuilder();
//    sb.append(item).append(item).append(item);
```

---

**Priority:** ✅ SHOULD KNOW (65% interview frequency)

**Related Topics:**
- [String Pool vs Heap](#)
- [String Immutability](#)
- [Performance Optimization](#)

---

**Last Updated:** March 5, 2026
