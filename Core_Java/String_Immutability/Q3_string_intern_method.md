# Q3: What does `.intern()` do and when should you use it?

**Study Time:** 2-3 minutes

---

## Problem

When to use `.intern()` and what it actually does.

## Code Scenario

```java
String str1 = new String("hello");  // Heap
String str2 = "hello";              // Pool

System.out.println(str1 == str2);   // false

// Using intern()
System.out.println(str1.intern() == str2);  // true
```

## Why It Happens

`.intern()` does one of two things:
- If string exists in pool → returns that reference
- If string doesn't exist → adds it to pool, returns reference

## ✅ Correct Usage

```java
// Case 1: Dynamic string that MIGHT appear multiple times
String userInput = readFromFile();  // e.g., "userID"
String pooled = userInput.intern();
// Now if another part of code reads same value,
// pooled references will be identical

// Case 2: Large dataset with many duplicates
String[] filenames = readMillionFilenames();
for (String name : filenames) {
    String interned = name.intern();  // Saves memory if many duplicates
}
```

## ❌ When NOT to use

```java
// DON'T - Performance killer
for (int i = 0; i < 1_000_000; i++) {
    String str = new String("ID: " + i).intern();  // Creates hammer
}

// DO - Just use literals
String str = "ID: " + i;  // Compiles to efficient bytecode
```

## Interview Tip

"`.intern()` adds a string to the pool or returns existing pool reference. Use it only when you have many string duplicates and memory is critical. Otherwise avoid it - it's slow and can cause memory issues."

## Quick Checklist

- ✅ Use `.intern()` only for duplicate-heavy scenarios
- ✅ Avoid loop use of `.intern()`
- ✅ Pool has finite size (Metaspace limits)
- ✅ For most cases: use `.equals()` instead
- ✅ Performance cost: can be significant

---

**Next:** Study Q4 on garbage collection and the String Pool
