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

## ⚠️ Common Pitfalls

**Pitfall 1: Increasing heap without fixing leak**
```text
// ❌ OOM? Just add more heap
// Leak still exists, now takes longer to fail

// ✅ Take heap dump, find retained objects
```

**Pitfall 2: Assuming GC will fix everything**
```text
// ❌ GC cannot collect referenced objects
// Static collections, ThreadLocal, listeners still hold references

// ✅ Remove references or use weak refs
```

**Pitfall 3: Not comparing heap dumps over time**
```text
// ❌ Single heap dump doesn't show growth trend

// ✅ Take 2-3 dumps and compare retained sizes
```

---

## 🛑 When NOT to Use Weak References

- ❌ Critical caches that must retain data
- ❌ Objects with strict lifetime requirements
- ✅ DO use: Optional caches where eviction is safe

---

**Last Updated:** February 22, 2026  
**Next: [Q44_jvm_tuning.md](Q44_jvm_tuning.md)**
