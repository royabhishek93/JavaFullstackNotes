# 🎯 Q43: Memory Leak Detection and Prevention?

> **Interview Frequency:** 42% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

App memory grows from 500MB → 5GB over 3 days. Memory leak!

---

## 📌 Common Causes

1. **Static collections** - Keep growing
2. **Event listeners** - Not unregistered
3. **Circular references** - Objects reference each other
4. **Resource leaks** - Files, connections not closed

---

## ✅ Prevention

```java
// WRONG: Holds references forever
static List<User> userData = new ArrayList<>();
// App adds users, never removes → grows indefinitely

// RIGHT: Use weak references for caches
private static final WeakHashMap<String, User> cache = new WeakHashMap<>();

// RIGHT: Unregister listeners
button.addListener(myListener);
button.removeListener(myListener);  // When done

// RIGHT: Use try-with-resources
try (Connection conn = dataSource.getConnection()) {
    // Auto-closed
}
```

---

## ✅ Detection

```bash
# Generate heap dump
jmap -dump:live,format=b,file=heap.bin 12345

# Analyze with JProfiler or Eclipse Memory Analyzer
# Look for: Retained Size (holding references)
```

---

## 💬 Interview Tip (Say This Exactly)

"Avoid static collections. Use weak references for caches. Always unregister listeners. Close resources. Monitor heap growth over time. If OutOfMemory, use heap dumps and profilers to find culprit."

---

**Last Updated:** February 22, 2026  
**Next: [Q44_jvm_tuning.md](Q44_jvm_tuning.md)**
