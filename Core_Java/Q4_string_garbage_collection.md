# Q4: How does garbage collection work with the String Pool?

**Study Time:** 2 minutes

---

## Problem

Do strings in the pool get garbage collected?

## Why It Happens

The String Pool is part of heap memory (Java 7+, in MetaSpace before). If a string has no references, GC can collect it.

## ✅ Correct Understanding

```java
String a = "hello";      // In pool
String b = new String("world");  // In heap

a = null;    // Can be GC'd if no other refs
b = null;    // Can be GC'd immediately

// String pool entries with no refs can also be GC'd
```

## Timeline

```
T=0: Create "hello" in pool (reference count = 1)
T=1: String a = "hello"
T=2: a = null (reference count = 0)
T=3: GC runs → collects "hello" from pool
```

## Interview Tip

"Yes, String Pool entries are garbage collected if there are no references. The pool is part of the heap, not a permanent memory region. However, strings created with literals may have implicit references."

## Quick Checklist

- ✅ String Pool is part of heap (Java 7+)
- ✅ Yes, pool strings can be GC'd
- ✅ Unreferenced strings removed during GC cycles
- ✅ String deduplication reduces pool size
- ✅ Long-lived pools can cause memory leaks
- ✅ Monitor with JVisualVM or Mission Control

---

**Next:** Study Q5 on immutable class requirements
