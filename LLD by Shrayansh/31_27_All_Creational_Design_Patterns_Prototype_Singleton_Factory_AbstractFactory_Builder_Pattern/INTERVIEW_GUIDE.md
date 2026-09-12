# 🏗️ All Creational Design Patterns - Interview Guide
## _Prototype · Singleton · Factory · Abstract Factory · Builder — 15 YOE Architect-Level Script_

**📘 Difficulty: Intermediate** — assumes you already know the core patterns; focuses on applying them to a real, moderately complex system.

> _(Companion to `transcript.md`, left untouched. This is the rapid-fire, scenario-based revision guide I'd use the night before an interview.)_

---

**Interviewer**: "Give me a lightning round on all 5 creational patterns — when do I reach for each one?"

**You**: "All 5 solve **one** meta-problem: controlling *how* and *when* objects get created, so that creation logic doesn't leak everywhere. Let me go pattern by pattern with the one-line trigger for each."

---

## 1. Prototype Pattern — "Cloning is cheaper than building"

```
┌───────────────┐   clone()   ┌───────────────┐
│  Original Robot   │ ───────────▶ │   Cloned Robot #1  │
│  (expensive to      │             └───────────────┘
│   construct from      │   clone()   ┌───────────────┐
│   scratch)             │ ───────────▶ │   Cloned Robot #2  │
└───────────────┘             └───────────────┘
```

**Trigger**: "I need many near-identical copies of an expensive-to-build object, with minor per-copy tweaks."

```java
interface Prototype { Prototype clone(); }

class Student implements Prototype {
    private int age; private String name;      // even PRIVATE fields
    Student(int age, String name) { this.age = age; this.name = name; }

    public Student clone() {
        return new Student(this.age, this.name);   // the class clones ITSELF
    }
}
```

**Key insight**: cloning logic must live **inside** the class being cloned (not the client), because only the class itself can access its own private fields, and only it truly knows which fields need copying vs. recomputing.

---

## 2. Singleton Pattern — "Exactly one instance, always"

```
        ┌─────────────────────────────┐
        │      DBConnectionManager           │
        │  - private static instance          │◄── only ONE ever exists
        │  - private constructor                │    (constructor is private!)
        │  + static getInstance()                │
        └─────────────────────────────┘
             ▲            ▲            ▲
        caller A     caller B     caller C   -- all get the SAME object
```

**4 implementations, ranked by production-readiness:**

| Style | Thread-safe? | Eager/Lazy? | Verdict |
|---|---|---|---|
| Eager init (`static final instance = new X()`) | Yes (class loading is thread-safe) | Eager | Simple, but wastes memory if never used |
| Lazy (`if (obj==null) obj = new X()`) | **No** — race condition creates 2 objects | Lazy | Broken under concurrency |
| Synchronized method | Yes | Lazy | Correct but slow — locks on EVERY call forever |
| **Double-checked locking** | **Yes** | Lazy | ✅ Industry standard — locks only during the rare creation window |

```java
class DBConnectionManager {
    private static volatile DBConnectionManager instance;   // volatile is mandatory!
    private DBConnectionManager() {}

    static DBConnectionManager getInstance() {
        if (instance == null) {                          // check 1 (no lock, fast path)
            synchronized (DBConnectionManager.class) {
                if (instance == null) {                   // check 2 (inside lock)
                    instance = new DBConnectionManager();
                }
            }
        }
        return instance;
    }
}
```

---

## 3. Factory Pattern — "Centralize the `if/else` of object creation"

```
100 call-sites doing `new Circle()` / `new Square()`
        ⬇  refactor
100 call-sites doing `ShapeFactory.getShape("CIRCLE")`
        ⬇
   ShapeFactory is the ONLY place with creation logic
```

**Trigger**: "Object creation depends on a condition, and that condition-check is duplicated across many call-sites."

---

## 4. Abstract Factory Pattern — "A factory that returns the right factory"

```
CarFactoryProducer.getFactory("LUXURY")  ──▶ LuxuryCarFactory
                                                     └─▶ .getInstance(price) ──▶ actual Car
```

**Trigger**: "I have multiple related *families* of products (Economic cars, Luxury cars), each needing its own creation rule, and I want one consistent entry point."

---

## 5. Builder Pattern — "Assemble a complex, immutable object step by step"

```
new HomeBuilder()
     .createFoundation()
     .createWalls()
     .createRoof()
     .createDoors()
     .build()  ──▶  immutable Home object
```

**Trigger**: "An object has many optional fields / a multi-step construction sequence, and I want it immutable once built. A `Director` can orchestrate the *order* of steps if it varies by use-case; the `Builder` implements each step."

---

## 6. The One-Page Decision Table

| If your problem is... | Use... |
|---|---|
| "I need many similar copies of an expensive object" | **Prototype** |
| "I need exactly one shared instance" | **Singleton** |
| "Which class to instantiate depends on a condition" | **Factory** |
| "Multiple related families of objects, needing consistency" | **Abstract Factory** |
| "An object needs many optional params / staged construction" | **Builder** |

---

## 7. Senior Trap Questions

**Trap: "Can't Prototype and Builder both be used to 'construct' objects — aren't they redundant?"**
**✅ Senior answer:** "No — Prototype creates a **copy of an existing instance** (fast, avoids re-running expensive initialization); Builder creates a **brand-new instance from scratch**, step by step, often when many fields are optional. They solve opposite problems: 'copy what exists' vs 'construct what doesn't exist yet'."

**Trap: "Why does Singleton need `volatile` on the double-checked-locking field?"**
**✅ Senior answer:** "Without `volatile`, the JVM/CPU can reorder instructions during object construction — another thread could see a non-null reference to a **partially constructed** object (due to instruction reordering in the constructor vs the reference assignment), causing subtle bugs that only appear under high concurrency. `volatile` establishes a happens-before relationship that prevents this reordering."

---

## 🔥 Real-World Production Issue: The Non-Thread-Safe "Singleton" Config Loader

*In plain English: a lazily-initialized Singleton without proper locking can create multiple instances under real traffic, not just in theory.*

**The war story:**

"A junior engineer wrote a `ConfigLoader` singleton using the naive lazy-init pattern (no synchronization) because 'Singleton just means one instance, right?' It worked fine in local testing (single-threaded) and passed code review because nobody ran a concurrency test."

```java
class ConfigLoader {                              // ❌ BROKEN under load
    private static ConfigLoader instance;
    static ConfigLoader getInstance() {
        if (instance == null) {
            instance = new ConfigLoader();   // <- reads config file from disk, SLOW (50ms)
        }
        return instance;
    }
}
```

```
Production traffic spike (Black Friday): 40 concurrent request-handler threads
all call getInstance() within the same 50ms window:

Thread-1  ─┐
Thread-2  ─┤ ALL see instance == null simultaneously
Thread-3  ─┤ ALL proceed to `new ConfigLoader()`
   ...     │ → 40 separate ConfigLoader objects created
Thread-40 ─┘ → 40 separate file reads hit disk simultaneously
                → disk I/O queue saturated
                → API latency p99 spiked from 20ms to 4000ms
                → auto-scaler misread this as a "load" issue and
                  added MORE pods, worsening the disk contention
```

**Root cause:** classic lazy-singleton race condition — exactly the bug the transcript's "4 ways to implement Singleton" section warns about, except this time it wasn't a students' whiteboard example, it took down a Black Friday traffic spike.

**The fix:** migrated to double-checked locking with `volatile`, AND (more importantly) added a **concurrency unit test** using `ExecutorService` + `CountDownLatch` to assert only one instance is ever created under 100 concurrent threads — now a mandatory test template for every Singleton in the codebase.

**Lesson for a new developer:** "Singleton looks trivial on a whiteboard but is one of the easiest patterns to get subtly wrong under real concurrency. Never merge a Singleton implementation without a concurrency test that actually spins up multiple threads and asserts `getInstance()` returns the *same* object reference every time."

---

## 🎓 Final Tips
1. Prototype: clone expensive objects; cloning logic lives inside the class itself.
2. Singleton: double-checked locking + `volatile` is the production-grade approach.
3. Factory: centralizes conditional creation logic in one place.
4. Abstract Factory: a factory of factories, for consistent related families.
5. Builder: staged, immutable construction for objects with many optional fields.
6. Always write a concurrency test for any Singleton before it reaches production.

Good luck! 🚀
