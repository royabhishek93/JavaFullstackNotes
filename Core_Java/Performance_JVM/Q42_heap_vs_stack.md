# 🎯 Q42: Heap vs Stack Memory?

> **Interview Frequency:** 48% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Stack overflowed with recursive calls. Heap alloc failed. What's the difference?

---

## 📌 Comparison

| Aspect | Stack | Heap |
|--------|-------|------|
| **Allocation** | LIFO (automatic) | Manual (GC) |
| **Speed** | Very fast | Slower |
| **Size** | Small (~1MB) | Large (~GB) |
| **Thread** | Per-thread | Shared |
| **Objects** | Primitives, references | All objects |
| **Lifetime** | End of scope | GC-dependent |
| **Exception** | StackOverflowError | OutOfMemoryError |

---

## ✅ Examples

```java
void method() {
    int x = 5;              // Stack: primitive value
    String s = "hello";     // Stack: reference, Heap: "hello"
    User user = new User(); // Stack: reference, Heap: User object
}  // All stack vars freed automatically
```

---

## 💬 Interview Tip (Say This Exactly)

"Stack for primitives and references (auto freed). Heap for objects (GC frees). Stack overflow from deep recursion, OutOfMemory from object leaks. Monitor: `-Xms2g -Xmx2g` for heap size."

---

**Last Updated:** February 22, 2026  
**Next: [Q43_memory_leak_detection.md](Q43_memory_leak_detection.md)**
