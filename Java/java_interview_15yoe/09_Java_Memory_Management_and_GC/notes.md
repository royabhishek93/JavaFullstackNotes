# Java Memory Management: Stack, Heap, Generations, and Garbage Collection

## What is this? (Plain English)

Think of your Java application as a busy restaurant kitchen. The **stack** is like each chef's personal countertop — small, temporary, and private to that chef (thread). Whatever a chef is working on right now (a chopped onion, a mixing bowl reference) sits there, and the moment that dish is done, everything on that countertop is cleared away immediately, in reverse order of how it was placed there.

The **heap** is the shared walk-in fridge/pantry — much bigger, and every chef (thread) can reach into it to store or fetch ingredients (objects). But nobody manually throws away leftovers from the fridge; instead, a cleanup crew (the **garbage collector**) periodically walks through the fridge, and if an ingredient has no label pointing to any chef who still needs it, the crew throws it out. The JVM decides when the cleanup crew comes in — you can *ask* them to come now (`System.gc()`), but they're not obligated to show up right away.

## The Problem It Solves

Java doesn't make you manually allocate and free memory like C/C++ (`malloc`/`free`). The JVM has to answer two questions automatically:

1. **Where should different kinds of data live** (temporary local variables vs. long-lived objects vs. class-level metadata), so that access is fast and cleanup is efficient?
2. **How do we reclaim memory for objects nobody references anymore**, without the programmer having to track every reference by hand, while keeping the "cleanup" work itself as fast and non-disruptive to the running application as possible?

This is exactly why the JVM splits memory into **Stack** (per-thread, temporary) and **Heap** (shared, object storage), and further splits the Heap into generations, so that garbage collection can be optimized differently for short-lived objects versus long-lived ones.

## Heap Generations and GC Flow

Objects are created in Eden; each Minor GC cycle marks dead (unreferenced) objects, sweeps them away, and copies survivors into the *other* survivor space with their age incremented by 1. Once an object's age crosses the configured threshold (e.g. age = 3), it is **promoted** to the Old Generation. A Major GC then runs (less frequently) within the Old Generation itself. Class metadata, static/class variables, and constants live separately in **Metaspace** (non-heap memory).

```
Flow: new Object() -> Eden
  Eden  --[Minor GC #1: Mark & Sweep, dead objects removed, survivors copied, age=1]--> S0
  S0    --[Minor GC #2: survivors copied to other survivor space, age+1]--> S1
  S1    --[Minor GC #3: survivors copied back, age+1]--> S0
  S0    --[age reaches promotion threshold (e.g. age=3)]--> Old Generation
  S1    --[age reaches promotion threshold (e.g. age=3)]--> Old Generation
  Old   --[Major GC: Mark & Sweep (slower, less frequent)]--> Old

(Non-heap: Metaspace holds class metadata, static/class variables, constants)
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

- **Heap** is always larger than the stack and is divided into **Young Generation** and **Old Generation**.
- **Young Generation** = `Eden` + two `Survivor` spaces (`S0`, `S1`). Every new object is created in `Eden` first.
- **Old / Tenured Generation** holds objects that have survived enough garbage-collection cycles to be "promoted."
- **Metaspace** is *outside* the heap (non-heap memory). It stores class metadata, class-level (static) variables, and constants (`static final`). Classes are loaded into it when the JVM needs them and removed when no longer needed. Before Java 7/8, this was called **PermGen (Permanent Generation)** and was a fixed-size part of the Heap itself — if it filled up you got an `OutOfMemoryError` with no way to expand it. Metaspace is separate from the Heap and can expand as needed.

### Stack vs. Heap — what's stored where

| Stored in **Stack** | Stored in **Heap** |
|---|---|
| Temporary/local variables (scoped to a block) | Actual objects (created via `new`) |
| One memory frame per method call | String pool (string literals live here) |
| Primitive data types (value stored directly) | Shared across all threads |
| References that point to Heap objects | Divided into Young Gen + Old Gen |
| Each thread has its **own** stack | Larger than the stack |

Variables are only visible within their own scope; when a scope (block/method) ends, its variables/references are removed in **LIFO** order (last in, first out). If the stack fills up, you get a `StackOverflowError`.

### ASCII: Object lifecycle across Eden → Survivors → Old Generation

This mirrors the worked example: objects are created in Eden, and each Minor GC cycle marks dead (unreferenced) objects, sweeps them away, and copies survivors into the *other* survivor space with their age incremented by 1. Once an object's age crosses the configured threshold (e.g. age = 3), it is **promoted** to the Old Generation.

```
YOUNG GENERATION                                             OLD GENERATION
+-----------------------------------------------------+      +------------------+
|  Eden          Survivor S0        Survivor S1        |      |  (tenured objs)  |
+-----------------------------------------------------+      +------------------+

Step 1 - Objects created (all new objects go to Eden):
  Eden: [O1][O2][O3][O4][O5]        S0: (empty)         S1: (empty)

Step 2 - Minor GC #1 (Mark & Sweep):
  Mark: O2, O5 have no reference -> eligible for deletion
  Sweep: O2, O5 removed; survivors O1,O3,O4 copied into S0, age = 1
  Eden: (empty)                     S0: [O1a1][O3a1][O4a1]   S1: (empty)

Step 3 - New objects created before next GC:
  Eden: [O6][O7]                    S0: [O1a1][O3a1][O4a1]   S1: (empty)

Step 4 - Minor GC #2:
  Mark: O7 (Eden) and O4 (S0) have no reference -> eligible for deletion
  Sweep: O7, O4 removed; survivors copied to the OTHER survivor space, age+1
  Eden: (empty)   S0: (empty)       S1: [O6a1][O1a2][O3a2]

Step 5 - More objects created; Minor GC #3 (promotion threshold set to age 3):
  Mark & Sweep runs again on Eden + S1; survivors copied back to S0, age+1
  O1 has now reached age = 3 (the promotion threshold)
  -> O1 is PROMOTED out of Young Generation into the Old Generation

  Eden: (empty)   S0: [new survivors...]   S1: (empty)   Old Gen: [O1]
```

**Minor GC** = garbage collection within the Young Generation — runs frequently and fast, since Eden/Survivor objects are typically short-lived and few in number.

**Major GC** = garbage collection within the Old Generation — runs far less frequently, and takes longer, because objects there are long-lived, tend to be larger, and tend to have many more references pointing to (and from) them.

## Key Code / Config

### 1. Stack vs. Heap walkthrough (the exact example from the video)

```java
public class MemoryManagement {

    public static void main(String[] args) {
        int t = 10;                                  // primitive -> stored directly in main's stack frame
        Person personObj = new Person();             // Person object -> Heap; personObj (ref) -> stack
        String stringLiteral = "24";                  // literal -> stored/looked-up in the String Pool (inside Heap)
        MemoryManagement memObj = new MemoryManagement(); // another Heap object; memObj (ref) -> stack

        memObj.memoryManagementTest(personObj);       // new stack frame created for this method call
    }

    void memoryManagementTest(Person personObj) {
        Person personObj2 = personObj;                 // alias: same Heap object, new reference
        String stringLiteral2 = "24";                  // "24" already in String Pool -> reused, no new object
        String stringLiteral3 = new String("24");      // `new` forces a NEW String object (bypasses pool)
    }                                                   // <- scope ends here: personObj, personObj2,
                                                          //    stringLiteral2, stringLiteral3 all removed (LIFO)
}                                                         // <- main's scope ends: t, personObj, stringLiteral,
                                                          //    memObj all removed (LIFO)
// After both stack frames unwind, the Person/MemoryManagement objects in the Heap have
// NO remaining references -> they become eligible for the Garbage Collector to reclaim.

class Person { }
```

### 2. Making objects eligible for garbage collection

```java
Person personObj = new Person();
personObj = null;              // removes the reference -> the old Person object is now unreferenced

Person personObj1 = new Person();
Person personObj2 = new Person();
personObj1 = personObj2;       // personObj1 now points to personObj2's object;
                                // the object personObj1 USED to point to has no more references
```

### 3. Requesting (not forcing) garbage collection

```java
System.gc();
// Tells the JVM "please scan the heap and delete unreferenced objects."
// The JVM gives NO GUARANTEE it will actually run GC when you call this.
// The JVM alone decides when/how often to run GC (e.g. more often if heap is filling up fast).
// This is why Java's memory management is called "automatic."
```

### 4. Reference types

```java
// Strong reference (the default / what you use 99% of the time):
Person personObj = new Person();
// As long as this strong reference exists, the GC will NEVER delete the object.

// Weak reference:
import java.lang.ref.WeakReference;

WeakReference<Person> weakPersonObj = new WeakReference<>(new Person());
// As soon as the GC runs, this object WILL be freed, regardless of the weak reference.
// Accessing weakPersonObj.get() after that point returns null.

// Soft reference (a variant of weak reference):
import java.lang.ref.SoftReference;

SoftReference<Person> softPersonObj = new SoftReference<>(new Person());
// The GC is ALLOWED to free this object, but typically only does so when memory is
// genuinely running low / urgently needed. If there's sufficient heap space, the GC
// may choose to keep it alive longer.
```

### 5. Garbage collector algorithms and implementations discussed

| GC type | Threads doing GC work | Stop-the-world pauses? | Compaction? | Notes |
|---|---|---|---|---|
| **Serial GC** | 1 single thread | Yes — all app threads pause | No | Simplest, slowest; only one thread frees Young + Old gen |
| **Parallel GC** | Multiple threads (based on CPU core count) | Yes, but shorter pauses | No | Faster cleanup due to parallel threads; less pause time than Serial; Java 8's default |
| **CMS (Concurrent Mark and Sweep)** | GC threads run concurrently *alongside* app threads | JVM tries to avoid pausing app threads, but does **not** guarantee zero pauses | No | Application keeps running while GC works in parallel, best-effort only |
| **G1 (Garbage First)** | Concurrent, improved further | Aims for close to zero application pause | Yes | Also performs memory compaction; latest JVMs push pause times even lower |

- **Mark and Sweep**: Phase 1 (*Mark*) walks the heap and flags objects with no remaining references as eligible for deletion. Phase 2 (*Sweep*) removes those flagged objects from memory.
- **Mark and Sweep with Compaction**: after sweeping, the remaining live objects are compacted together sequentially, leaving one contiguous free block at the end (instead of scattered/fragmented free gaps), making it easier to place new objects later.
- **"Stop-the-world"**: while GC is running (in Serial/Parallel GC), all application threads pause completely, then resume once GC finishes. This is why GC is considered an expensive operation — the slower/more frequent the GC, the more your application pauses.
- Reducing pause time increases **throughput** (more requests processed per unit time) and decreases **latency** (faster response per request), since application threads spend less time paused.

## Interview Q&A

**Q1: What's the fundamental difference between what gets stored in the Stack vs. the Heap?**
A: The Stack stores temporary/local variables, primitive values, and references — one private memory frame per method call, and a separate stack per thread. The Heap stores the actual objects (created via `new`), including the String pool, and is shared across all threads. When a method's scope ends, its stack frame (and everything in it) is destroyed immediately in LIFO order; heap objects are only removed later, by the garbage collector, once nothing references them anymore.

**Q2: If you call `System.gc()`, is garbage collection guaranteed to run immediately?**
A: No. `System.gc()` is only a request/hint to the JVM to scan the heap for unreferenced objects. The JVM has full control over if and when GC actually runs — it may run it, delay it, or skip it. This is exactly why Java's memory management is called "automatic": the JVM decides GC frequency based on how quickly the heap is filling up.

**Q3: What's the difference between Minor GC and Major GC?**
A: Minor GC cleans the Young Generation (Eden + Survivor spaces) — it runs frequently and is fast because Young Gen objects are typically short-lived and few. Major GC cleans the Old Generation — it runs much less frequently and takes longer, because Old Gen objects are long-lived, tend to be larger, and have accumulated many more references over time.

**Q4: Explain the difference between Strong, Weak, and Soft references.**
A: A Strong reference (the default, e.g. `Person p = new Person()`) prevents the GC from ever deleting the object as long as that reference exists. A Weak reference (`WeakReference<Person>`) will have its referent freed the moment GC runs, regardless of whether the weak reference still exists — accessing it afterward returns `null`. A Soft reference is a variant of weak reference where the GC is *allowed* to free the object, but typically only does so when memory is genuinely low/urgently needed; if there's enough heap space, the GC may choose to keep it alive.

**Q5: What's the difference between PermGen and Metaspace?**
A: PermGen (used before roughly Java 7/8) was part of the Heap itself and had a fixed size — once it filled up, you'd get an `OutOfMemoryError` with no way to grow it. Metaspace replaced PermGen and lives outside the Heap (non-heap memory); it can expand as needed. Both store the same kind of data: class metadata, class-level (static) variables, and constants.

**Q6: Why is garbage collection considered an "expensive" operation, and how do different GC implementations try to reduce that cost?**
A: When GC runs (especially Serial GC, which uses a single thread), all application threads are paused ("stop-the-world") until GC finishes — the more often or the longer this happens, the slower your application feels. Parallel GC reduces pause time by using multiple threads (based on CPU core count) to do the cleanup work faster. CMS goes further by running GC concurrently alongside application threads so they don't have to fully stop, though the JVM doesn't guarantee zero pausing. G1 improves on this even more and also adds memory compaction. Lower pause times translate directly into higher throughput and lower latency for the application.
