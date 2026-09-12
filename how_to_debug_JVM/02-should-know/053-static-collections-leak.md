# #53 — Static Collections Leak

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Your service leaks memory through a static Map. Show the bug and fix."

## 😊 Explain It Simply (for anyone)
Imagine a company keeps a permanent "guest sign-in book" (a *static* list — meaning there's only ONE copy for the whole building, shared by everyone, and it never gets thrown away). Every visitor signs in, but nobody ever crosses names off when they leave. After a few years, the book is thousands of pages long, even though most of those visitors left ages ago. That's exactly what happens when code adds items to a `static` collection (a list/map that belongs to the whole class, not one instance) but never removes them — the JVM's garbage collector (the automatic memory cleaner) treats that "book" as permanently important (a *GC root* — something always considered "in use"), so anything written in it, and anything THOSE things point to, can never be thrown away. Over time this silently eats all available memory until the app crashes with an "Out of Memory" error.

## 📊 Visualize It
```
 [JVM GC Root]
       |
       v
 static Map<String, List<Listener>>   <-- never cleared
       |
       +--> "orderEvent" -> [L1, L2, L3, ... L50000]  (grows forever)
       |
       +--> "userEvent"  -> [L1, L2, ... ]

 Each Listener is "reachable" forever because the static
 map is a permanent root -> NEVER garbage collected.
```

## 🏭 The Real Production Answer (15-YOE Level)

Buggy code:
```java
// LEAK: static map, never cleared
public class EventBus {
    private static final Map<String, List<EventListener>> listeners =
        new HashMap<>();

    public static void register(String event, EventListener l) {
        listeners.computeIfAbsent(event, k -> new ArrayList<>()).add(l);
    }
    // No deregister method — listeners accumulate forever
}
```

Why it leaks: `listeners` is a GC root. Every registered listener object and all objects it transitively references are reachable forever. In a web app, if listeners are registered per-request and never removed, this grows unbounded.

Fix:
```java
public class EventBus {
    private static final Map<String, List<WeakReference<EventListener>>> listeners =
        new ConcurrentHashMap<>();

    public static void register(String event, EventListener l) {
        listeners.computeIfAbsent(event, k -> new CopyOnWriteArrayList<>())
                 .add(new WeakReference<>(l));
    }

    public static void deregister(String event, EventListener l) {
        List<WeakReference<EventListener>> list = listeners.get(event);
        if (list != null) list.removeIf(ref -> ref.get() == null || ref.get() == l);
    }
}
```

Better: use `WeakReference` for listeners AND provide an explicit `deregister`. The WeakReference lets the GC collect listeners whose owners are gone, but the deregister is the clean path.

## 🔑 Key Takeaway
A `static` collection is a permanent GC root — anything you add and never remove will live forever, so always pair "add" with an explicit "remove" path (or a `WeakReference`).
