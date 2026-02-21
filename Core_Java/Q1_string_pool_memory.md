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

**Next:** Study Q2 to understand what happens with concatenation
