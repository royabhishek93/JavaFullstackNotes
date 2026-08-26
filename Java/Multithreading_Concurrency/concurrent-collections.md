# Concurrent Collections Deep Dive

**Study Time:** 10-12 minutes | **Frequency:** 60% in interviews | **Difficulty:** ⭐⭐⭐

---

## 🤔 Problem Scenario

```java
// Non-thread-safe
Map<String, Integer> map = new HashMap<>();

new Thread(() -> {
    for (int i = 0; i < 1000; i++) {
        map.put("key" + i, i);  // ❌ Not thread-safe
    }
}).start();

new Thread(() -> {
    for (String key : map.keySet()) {
        map.remove(key);  // ❌ ConcurrentModificationException
    }
}).start();
```

**Problem:** ConcurrentModificationException, data races, lost updates.

**Solution:** Use concurrent collections!

---

## 🧠 Key Principle: Segment-Based Locking

Instead of locking entire collection, lock only segments:

```
HashMap (Single Lock):
┌─────────────────────────┐
│ [Entire map locked]     │
│ No concurrent access    │
└─────────────────────────┘

ConcurrentHashMap (Segment Locks):
┌──────────────┬──────────────┬──────────────┐
│ Segment 1    │ Segment 2    │ Segment 3    │
│ (locked)     │ (unlocked)   │ (unlocked)   │
│              │ (T2 access)  │ (T3 access)  │
└──────────────┴──────────────┴──────────────┘

Multiple threads can access different segments simultaneously!
```

---

## ✅ Scenario 1: ConcurrentHashMap

```java
import java.util.concurrent.ConcurrentHashMap;

class ConcurrentMapExample {
    public static void main(String[] args) throws InterruptedException {
        Map<String, Integer> map = new ConcurrentHashMap<>();

        // Multiple writers
        new Thread(() -> {
            for (int i = 0; i < 100; i++) {
                map.put("T1-" + i, i);
            }
        }).start();

        new Thread(() -> {
            for (int i = 0; i < 100; i++) {
                map.put("T2-" + i, i);
            }
        }).start();

        // Multiple readers
        new Thread(() -> {
            map.values().forEach(v -> System.out.println(v));
        }).start();

        Thread.sleep(1000);
        System.out.println("Total: " + map.size());  // 200
    }
}
```

**Output:**
```
Total: 200
(No errors - thread-safe!)
```

---

## ✅ Scenario 2: CopyOnWriteArrayList

```java
import java.util.concurrent.CopyOnWriteArrayList;

class CopyOnWriteExample {
    public static void main(String[] args) {
        List<String> list = new CopyOnWriteArrayList<>();

        // Multiple writers
        new Thread(() -> {
            for (int i = 0; i < 5; i++) {
                list.add("T1-" + i);
            }
        }).start();

        new Thread(() -> {
            for (int i = 0; i < 5; i++) {
                list.add("T2-" + i);
            }
        }).start();

        // Multiple readers (NO ConcurrentModificationException)
        new Thread(() -> {
            for (String item : list) {
                System.out.println(item);
            }
        }).start();

        Thread.sleep(1000);
        System.out.println("Total: " + list.size());  // 10
    }
}
```

**How it works:**
- Read: Returns current array snapshot
- Write: Creates copy, modifies, replaces reference
- Safe iteration even during writes

---

## ✅ Scenario 3: ConcurrentLinkedQueue

```java
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;

class QueueExample {
    public static void main(String[] args) throws InterruptedException {
        Queue<Integer> queue = new ConcurrentLinkedQueue<>();

        // Producers
        new Thread(() -> {
            for (int i = 0; i < 5; i++) {
                queue.offer(i);  // Thread-safe add
                System.out.println("Produced: " + i);
            }
        }).start();

        // Consumers
        new Thread(() -> {
            while (!queue.isEmpty()) {
                Integer item = queue.poll();  // Thread-safe remove
                if (item != null) {
                    System.out.println("Consumed: " + item);
                }
            }
        }).start();

        Thread.sleep(1000);
    }
}
```

---

## ✅ Scenario 4: Comparing Collection Options

```java
// Scenario: Cache with frequent reads, occasional writes

// Option 1: Collections.synchronizedMap (Full lock)
Map<String, Data> cache = Collections.synchronizedMap(new HashMap<>());
// Entire map locked on each operation
// Performance: POOR under concurrent read load

// Option 2: ConcurrentHashMap (Segment locks)
Map<String, Data> cache = new ConcurrentHashMap<>();
// Multiple readers can read different segments simultaneously
// Performance: GOOD under concurrent read load

// Option 3: ReadWriteLock (Separate read/write locks)
ReadWriteLock lock = new ReentrantReadWriteLock();
Map<String, Data> cache = new HashMap<>();

Data get(String key) {
    lock.readLock().lock();
    try {
        return cache.get(key);
    } finally {
        lock.readLock().unlock();
    }
}

void put(String key, Data value) {
    lock.writeLock().lock();
    try {
        cache.put(key, value);
    } finally {
        lock.writeLock().unlock();
    }
}
// Performance: BEST when reads >> writes

// RECOMMENDATION: ConcurrentHashMap in most cases
cache = new ConcurrentHashMap<>();
```

---

## 📊 Concurrent Collections Comparison

| Collection | When to Use | Pros | Cons |
|-----------|------------|------|------|
| **ConcurrentHashMap** | General purpose concurrent map | Low contention, scalable | Slight overhead |
| **CopyOnWriteArrayList** | Many reads, few writes | Safe iteration, snapshot | Write is O(n) copy |
| **ConcurrentLinkedQueue** | Producer-consumer, queue | Unbounded, lock-free | No direct access by index |
| **Collections.synchronizedMap()** | Legacy, simple cases | Simple | Single lock (poor throughput) |
| **ReadWriteLock** | Read-heavy workloads | Separate read/write locks | Manual lock management |

---

## 💬 Interview Tip (Exact Answer)

"`ConcurrentHashMap` avoids a global lock and provides atomic operations like `compute`, `merge`, and `putIfAbsent`. It scales better than synchronized collections under high concurrency."

---

## ☑️ Quick Checklist

- Use `ConcurrentHashMap` for shared maps.
- Use `CopyOnWriteArrayList` only for read-heavy lists.
- Use `BlockingQueue` for producer-consumer.
- Avoid `Collections.synchronizedMap` for high contention.

## ❌ Common Mistakes

### ❌ Mistake 1: Assuming Map Methods Are Atomic

```java
// WRONG - Multiple operations, not atomic
ConcurrentHashMap<String, Integer> map = new ConcurrentHashMap<>();

if (!map.containsKey("count")) {  // Step 1
    map.put("count", 0);          // Step 2
}

// Race condition!
// T1: Check "count", not found
// T2: Check "count", not found
// T1: Put "count" = 0
// T2: Put "count" = 0  (duplicate work)

// CORRECT - Use atomic operation
map.putIfAbsent("count", 0);  // Atomic replacement

// Or for increment
map.merge("count", 1, Integer::sum);  // Atomic merge
```

---

### ❌ Mistake 2: Using CopyOnWriteArrayList for Heavy Writing

```java
// WRONG - CopyOnWriteArrayList in heavy write scenario
List<Event> events = new CopyOnWriteArrayList<>();

for (int i = 0; i < 100000; i++) {
    events.add(new Event());  // Creates copy each time! O(n)
    // Total: O(n²) - very slow
}

// CORRECT - Use regular ArrayList with external lock
List<Event> events = new ArrayList<>();
synchronized(events) {
    for (int i = 0; i < 100000; i++) {
        events.add(new Event());  // O(1)
    }
}

// Or use queue
Queue<Event> events = new ConcurrentLinkedQueue<>();
for (int i = 0; i < 100000; i++) {
    events.offer(new Event());  // O(1), lock-free
}
```

---

### ❌ Mistake 3: Compound Operations Not Atomic

```java
// WRONG - putIfAbsent would not work after check
ConcurrentHashMap<String, List<String>> map = new ConcurrentHashMap<>();

// T1: Put user1 → list1
List<String> list = map.get("user1");
if (list == null) {
    list = new ArrayList<>();
    map.put("user1", list);  // Race: T2 also creates list!
}
list.add("item");  // Might add to wrong list!

// CORRECT - Use computeIfAbsent (atomic)
map.computeIfAbsent("user1", k -> new ArrayList<>())
   .add("item");  // Guaranteed atomic
```

---

### ❌ Mistake 4: Forgetting About Iterator Snapshot

```java
// Even though CopyOnWriteArrayList is safe from CME...
CopyOnWriteArrayList<String> list = new CopyOnWriteArrayList<>();
list.addAll(List.of("a", "b", "c"));

Iterator<String> iter = list.iterator();
// Iterator sees snapshot at creation time

while (iter.hasNext()) {
    String item = iter.next();
    list.add("x");  // This doesn't affect iterator
    // Iterator finished with original snapshot
}

// Iterator is safe, but behavior might be unexpected
```

---

## 🎯 Interview Q&A

### Q1: "Why ConcurrentHashMap instead of synchronized?"

**Answer (30 seconds):**
```
ConcurrentHashMap:
- Segment-based locking (multiple concurrent access)
- Better performance under concurrent load
- get() doesn't lock if value exists

synchronized/synchronizedMap:
- Single lock for entire map
- One thread at a time
- Simpler but slower

Example throughput (10 threads, 10000 operations):
ConcurrentHashMap: ~5000 ops/sec per thread
synchronizedMap: ~500 ops/sec per thread

Use ConcurrentHashMap by default!
```

---

### Q2: "CopyOnWriteArrayList - when?"

**Answer:**
```
When: Many reads, few writes

Examples:
✅ Event listeners (add listeners once, call many times)
✅ Configuration list (load once, read many times)
✅ Cached allowed values (set once, read in loops)

NOT FOR:
❌ Frequent writes (add/remove in loop)
❌ Large lists being modified constantly

Why?
- Write = copy entire list = O(n)
- Read = return snapshot = O(1)

If 90% reads: CopyOnWriteArrayList
If 50% writes: Regular ArrayList + lock
```

---

### Q3: "Code - which is better?"

```java
// Option A
ConcurrentHashMap<String, Integer> counters = new ConcurrentHashMap<>();

for (int i = 0; i < 10000; i++) {
    counters.merge("count", 1, Integer::sum);
}

// Option B
Map<String, Integer> counters = Collections.synchronizedMap(new HashMap<>());

synchronized(counters) {
    for (int i = 0; i < 10000; i++) {
        counters.merge("count", 1, Integer::sum);
    }
}
```

**Answer:**
```
Option A is better.

Option A:
- Each merge is atomic
- ConcurrentHashMap handles locking internally
- Better for this pattern

Option B:
- Entire loop is locked
- One thread at a time (defeats purpose of concurrent map)
- If you need external sync, use regular HashMap

Actually best:
int count = 0;
for (int i = 0; i < 10000; i++) {
    count++;
}
counters.put("count", counters.getOrDefault("count", 0) + count);
// Minimal synchronization
```

---

## 🔑 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Segment-based locking | Performance understanding | ⭐⭐⭐⭐⭐ |
| Collection selection | Real-world effectiveness | ⭐⭐⭐⭐⭐ |
| Atomic operations | Correctness assurance | ⭐⭐⭐⭐ |
| CopyOnWriteArrayList trade-offs | Edge case awareness | ⭐⭐⭐ |
| vs Collections.synchronized() | Performance comparison | ⭐⭐⭐ |

---

## Concurrent Collections Quick Reference

```java
// Map
ConcurrentHashMap<K, V>              // Best default choice
ConcurrentSkipListMap<K, V>          // Sorted, lock-free
Collections.synchronizedMap(...)     // Avoid (single lock)

// List
CopyOnWriteArrayList<E>              // Read-heavy
ConcurrentLinkedDeque<E>             // Lock-free

// Set
ConcurrentHashMap.newKeySet()        // Concurrent set
CopyOnWriteArraySet<E>               // Read-heavy
Collections.synchronizedSet(...)     // Avoid

// Queue
ConcurrentLinkedQueue<E>             // Unbounded, lock-free
LinkedBlockingQueue<E>               // Bounded, blocking
PriorityBlockingQueue<E>             // Priority ordering
SynchronousQueue<E>                  // Hand-off (no buffering)
```

---

**Priority:** ⭐⭐⭐ DIFFERENTIATOR (60% interview, shows advanced knowledge)

**Related Topics:**
- [Producer-Consumer Pattern](#)
- [ReentrantLock](#)
- [Thread Performance](#)

---

**Last Updated:** March 5, 2026
