# #33 — Diagnosing an Unbounded Static Collection Leak

> **Category:** Heap Dump Analysis | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Walk me through diagnosing an unbounded static collection causing OOM."

## 😊 Explain It Simply (for anyone)
A "static" collection is like a single shared filing cabinet that belongs to the whole company (not to any one employee), and it exists for as long as the company exists. If someone builds a "quick fix" process where every new customer request gets a folder filed into that cabinet, but nobody is ever assigned to REMOVE old folders once the customer's business is done, the cabinet just keeps growing — one more folder per request, forever — until the room physically cannot hold more cabinets and everything grinds to a halt.

Since the cabinet belongs to the company itself (a `static` field), it's never seen as "unused" by the automatic cleanup crew, so it's never cleared no matter how much regular cleanup happens elsewhere.

## 📊 Visualize It
```
static Map<String, RequestMetadata> activeRequests = new ConcurrentHashMap<>();

req-1 →  put("req-1", meta)   [cabinet: 1 folder]
req-2 →  put("req-2", meta)   [cabinet: 2 folders]
 ...                           ...
req-N →  put("req-N", meta)   [cabinet: N folders]   ← never removed!

GC Root path (found in MAT):
  RequestTracker.class (classloader, GC root)
     └─ static field activeRequests
          └─ ConcurrentHashMap$Node[] (millions of entries)

Fix: bounded cache with TTL (Caffeine: maximumSize + expireAfterWrite)
  cabinet self-empties old folders → flat memory over time
```

## 🏭 The Real Production Answer (15-YOE Level)

```java
// The bug — seen in "quick fix" caches
public class RequestTracker {
    // BUG: Never evicted, grows forever with unique request IDs
    private static final Map<String, RequestMetadata> activeRequests =
        new ConcurrentHashMap<>();

    public static void track(String requestId, RequestMetadata meta) {
        activeRequests.put(requestId, meta);
    }

    // Missing: removal on request completion
}
```

MAT diagnosis:
1. Dominator Tree → find the large `ConcurrentHashMap$Node[]` array
2. Right-click → "Path to GC Roots" → exclude weak/soft/phantom refs
3. Path will show: `ConcurrentHashMap` → `RequestTracker.activeRequests` (static field) → `RequestTracker.class` → classloader → GC root
4. The static field is the GC root anchor — that's your leak

Fix:
```java
// Correct — bounded with automatic eviction
private static final Cache<String, RequestMetadata> activeRequests =
    Caffeine.newBuilder()
        .maximumSize(10_000)
        .expireAfterWrite(Duration.ofMinutes(5))
        .recordStats()
        .build();
```

## 🔑 Key Takeaway
A `static` collection is a guaranteed GC root — if nothing ever calls `remove()`, MAT's "Path to GC Roots" will point straight at the static field.
