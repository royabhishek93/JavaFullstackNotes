# Q2: Why does `c == d` return false when both are `"hi"`?

**Study Time:** 2-3 minutes

---

## Problem

Confusing behavior of string equality with concatenation.

## Code Scenario

```java
String a = "hi";
String b = "hi";
System.out.println(a == b);  // true - literals in pool

String c = a + b;            // Runtime concatenation
String d = "hihi";           // Literal
System.out.println(c == d);  // false - Why?!
```

## Why It Happens

- `a + b` happens at **runtime** → result goes to **Heap**
- `"hihi"` is a **literal** → goes to **String Pool**
- Different memory regions = different objects = `==` returns false

## Visual Memory Layout

```
String Pool:        Heap:
┌─────────┐         ┌─────────┐
│ "hi"    │         │ "hihi"  │ ← c points here (a + b)
│ "hihi"  │ ← d     │         │
└─────────┘         └─────────┘
```

## ❌ Wrong (Comparing with ==)

```java
String c = a + b;
String d = "hihi";
System.out.println(c == d);  // false - different objects
```

## ✅ Right (Using equals())

```java
String c = a + b;
String d = "hihi";

// Use equals() for content comparison
System.out.println(c.equals(d));        // true ✅
System.out.println(c == d);             // false (different objects)

// If you need == to work: use intern()
System.out.println(c.intern() == d);    // true
```

## Interview Tip

"The `+` operator creates strings on the heap at runtime. Literals are in the pool. So `c == d` is false even though they have same content. Use `equals()` for comparison, not `==`."

## Quick Checklist

- ✅ `==` checks object reference (not content)
- ✅ `.equals()` checks string content
- ✅ Runtime concatenation always → Heap
- ✅ Literals always → String Pool
- ✅ Different memory regions → different objects

---

**Next:** Study Q3 to learn when `.intern()` is useful
