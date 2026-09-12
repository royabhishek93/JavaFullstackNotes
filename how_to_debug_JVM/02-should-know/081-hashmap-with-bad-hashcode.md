# #81 — HashMap With a Bad hashCode()

> **Category:** CPU Profiling & Flame Graphs | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"A cache lookup that should be O(1) is showing up as a significant CPU consumer in profiling. How?"

## 😊 Explain It Simply (for anyone)
Imagine a library where every book is supposed to have a unique shelf number so you can walk straight to it. Now imagine someone mislabeled every single book with the exact same shelf number — suddenly, "finding" any book means digging through the entire pile on that one shelf, one book at a time, instead of walking directly there. A fast lookup structure called a HashMap works the same way: it uses a quick "shelf number" calculation (called `hashCode()`) to jump straight to the right spot. If that shelf-number calculation is broken — either it always produces the same number, or it's needlessly slow to compute (like recalculating a book's entire content summary every time instead of just reading its printed ISBN) — the "instant lookup" silently turns into a slow, linear search through a pile. This is sneaky because the code calling the HashMap looks completely innocent; the real problem is buried inside the key object's own `hashCode()` method, and it only shows up clearly once you look at a flame graph and see `hashCode()`/`equals()` eating time right above `HashMap.get()`.

## 📊 Visualize It
```
Good hashCode: key -> [hash: O(1)] -> bucket[42] -> found instantly

Bad hashCode (always same value):
  key1 -> [hash: always 7] -> bucket[7]: [key1,key2,key3,...,keyN]
                                          ^ linear scan through ALL of them

Bad hashCode (recursive, deep object graph):
  key -> [hash: walks entire child tree, O(n) per call] -> slow every time
```

## 🏭 The Real Production Answer (15-YOE Level)
If the key's `hashCode()` has poor distribution or is expensive to compute, HashMap degrades to O(n).

Two scenarios:
1. `hashCode()` always returns the same value (classic bug) — every key lands in the same bucket, lookup is a linear scan
2. `hashCode()` traverses a deep object graph (e.g., a recursive data structure) — each lookup triggers a full traversal

```java
// Problematic — deeply nested object as cache key
public class GraphNode {
    List<GraphNode> children;
    @Override public int hashCode() {
        return Objects.hash(children); // recursive — O(n^2) for deep graphs
    }
}

// Fix — use a stable identifier-based key
public class GraphNode {
    final String id;
    @Override public int hashCode() { return id.hashCode(); }
}
```

Async-profiler will show `hashCode()` / `equals()` high in the flame graph, directly above `HashMap.get()`. Check the implementation of the key class.

## 🔑 Key Takeaway
If `hashCode()`/`equals()` shows up hot right above `HashMap.get()` in a flame graph, the bottleneck is the key class's hash implementation, not the HashMap itself.
