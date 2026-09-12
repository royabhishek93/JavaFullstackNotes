# #120 — String.intern() Abuse

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"What happens when you call `String.intern()` on user-supplied data at scale?"

## 😊 Explain It Simply (for anyone)
`String.intern()` (a method that says "store exactly ONE copy of this text forever, and give me back that shared copy") is like a librarian who agrees to keep a permanent, single master copy of any phrase you hand her — forever, so that anyone else asking for the same phrase gets the same copy instead of printing a new one. That's efficient IF there are only a handful of repeated phrases (like "ACTIVE", "INACTIVE"). But if you start handing her every visitor's unique ID number (millions of one-of-a-kind values, never repeated), she now has a permanent, ever-growing shelf of one-off entries that will NEVER be reused and NEVER thrown away — that's not saving space, that's building an infinite hoarding room.

## 📊 Visualize It
```
 String Pool (permanent storage of interned strings)

  "ACTIVE"    -> shared by 10,000 objects   (GOOD use of intern)
  "user-a1b2" -> used by exactly 1 object   (BAD: unique, wasted)
  "user-c3d4" -> used by exactly 1 object   (BAD)
  "user-e5f6" -> used by exactly 1 object   (BAD)
  ... millions of one-off unique IDs pile up, never collected
```

## 🏭 The Real Production Answer (15-YOE Level)

Buggy code:
```java
public class SessionManager {
    private final Map<String, Session> sessions = new HashMap<>();

    public void register(String userId, Session session) {
        // LEAK: interning arbitrary user IDs fills the String pool forever
        sessions.put(userId.intern(), session);
    }
}
```

In Java 7 and earlier: `String.intern()` stored strings in PermGen (method area), which has a fixed size. With millions of unique user IDs (UUIDs, hashed tokens), PermGen fills up: `java.lang.OutOfMemoryError: PermGen space`.

In Java 8+: String pool is in the heap (not Metaspace), but it is still a permanent interning pool — interned strings are GC roots and are only collected when the JVM has aggressive GC pressure. With unique strings, you get unbounded growth in the heap.

Fix: never intern untrusted or high-cardinality user input.
```java
// No intern() — HashMap handles equality via equals() just fine
sessions.put(userId, session);
```

Use `intern()` only for a small, known, finite set of strings (e.g., a fixed set of status codes you compare frequently). Even then, consider `enum` instead.

## 🔑 Key Takeaway
Only intern strings from a small, finite, known set — interning high-cardinality user input turns the String pool into an unbounded leak.
