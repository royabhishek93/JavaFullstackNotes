# Q1: Where does `"hello"` go in memory?

**Study Time:** 2-3 minutes

---

## Problem

Understanding where Java stores string literals vs runtime strings.

## Why It Happens

Java has a special memory region called the **String Pool** for string literals. This saves memory by reusing identical strings.

## ❌ Wrong Understanding

```java
String a = "hello";     // Goes to regular heap
String b = "hello";     // Also goes to regular heap
// Developers think: a and b are different objects
```

## ✅ Right Understanding

```java
String a = "hello";           // Goes to String Pool
String b = "hello";           // Reuses same String Pool reference
System.out.println(a == b);   // true - SAME object!
```

## Deep Explanation

**String Pool** is part of heap memory where identical string literals are stored once and reused. When the compiler sees `"hello"` twice, it stores it in the pool only once, and both references point to that single object.

```java
// Timeline
String a = "hello";  // Time 0: Create in pool
String b = "hello";  // Time 1: Check if "hello" in pool → YES → reuse
// Both a and b point to same object
```

## Interview Tip

"String literals go to the String Pool in memory. Multiple references to the same literal share ONE object. This is why `a == b` returns true for literals but false for `new String("hello")`."

## Quick Checklist

- ✅ Literals → String Pool (memory efficient)
- ✅ `new String()` → Heap (always new object)
- ✅ `+` concatenation at runtime → Heap
- ✅ `.intern()` → Moves to pool or returns pool reference
- ✅ String Pool is part of heap, not separate memory

---

## ⚠️ Common Pitfalls

**Pitfall 1: Using `new String()` unnecessarily**
```java
String s = new String("hello");  // ❌ Creates 2 objects (pool + heap)
String s = "hello";              // ✅ Creates 1 object (pool only)
```

**Pitfall 2: Comparing strings with `==` instead of `.equals()`**
```java
String a = "hi";
String b = new String("hi");
if (a == b) { }  // ❌ Always false (different memory locations)
if (a.equals(b)) { }  // ✅ Compares content
```

**Pitfall 3: String concatenation in loops**
```java
// ❌ Creates N new String objects on heap
String result = "";
for (int i = 0; i < 1000; i++) {
    result += i;  // New String each iteration!
}

// ✅ Use StringBuilder for loops
StringBuilder sb = new StringBuilder();
for (int i = 0; i < 1000; i++) {
    sb.append(i);
}
String result = sb.toString();
```

**Pitfall 4: Misunderstanding `.intern()` performance**
```java
// ❌ Overusing intern() can slow down application
for (String s : millionsOfStrings) {
    s.intern();  // Hash lookup + pool insertion overhead
}
// Use intern() only for limited set of strings (config keys, etc.)
```

---

## 🛑 When NOT to Worry About String Pool

- ❌ Short-lived strings in local scope
- ❌ Strings from user input (use directly)
- ❌ Dynamic runtime strings (API responses, DB results)
- ✅ DO care: Configuration keys, enum-like values, repeated constants

---

## 🔗 Related Questions

- [Q2_string_concatenation.md](Q2_string_concatenation.md) - Why `c == d` returns false
- [Q3_string_intern_method.md](Q3_string_intern_method.md) - When to use `.intern()`
- [Q5_immutable_class_requirements.md](Q5_immutable_class_requirements.md) - Building immutable classes

---

**Next:** Study Q2 to understand what happens with concatenation
