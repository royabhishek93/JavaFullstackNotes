# Interview Guide: Creational Design Patterns (Prototype, Singleton, Factory, Abstract Factory, Builder)

## 🗣️ The Interview Scenario

> "You're building a game engine that needs to spawn hundreds of pre-configured 'boss' enemies that are expensive to construct, guarantee exactly one shared `GameConfig` object across the whole engine, decide at runtime whether to render 'Circle', 'Square', or 'Rectangle' shapes without scattering `new Circle()` calls across 100 files, support both 'economy' and 'luxury' car catalogs that must never mix parts, and let a client build a `Home` object (wall → roof → door → window) where different home types (Flat, Duplex, Villa) implement some steps differently. Walk me through which creational pattern you'd reach for in each case, and design the class structure."

This is a classic "rapid-fire creational patterns" question — the interviewer is testing whether you can *recognize the right pattern from the symptom* (expensive cloning, single instance, spread-out `new` calls, families of related objects, multi-step construction) rather than just recite definitions.

## 🏗️ Architect's Explanation (For a New Developer)

Think of **creational patterns** as different answers to one question: *"Who is responsible for creating this object, and how?"* Every pattern in this family exists because letting client code call `new SomeClass()` directly, scattered everywhere, eventually causes pain. Here's the mental model for each, explained with everyday analogies:

- **Prototype** — "Photocopy machine." If building the original document (object) took hours, don't rebuild it from scratch for every small variation — photocopy it and tweak the copy.
- **Singleton** — "The one office key." Only one key should ever exist (e.g., one DB connection manager); everyone who asks for "the key" gets the *same* key, not a new one.
- **Factory** — "The restaurant kitchen." The customer (client) just orders "a burger"; they don't need to know the recipe. All the "how do I make X" logic lives in one kitchen (factory class), not repeated at every table.
- **Abstract Factory** — "A restaurant chain with themed kitchens." One kitchen only makes Italian dishes, another only Mexican — and you never accidentally get a taco with pasta. You first pick *which* kitchen (factory), then order from *within* that kitchen only, guaranteeing the family of products stays consistent.
- **Builder** — "Building a house floor by floor." Some products need many sequential steps (wall, roof, door, window) and different variants (Flat vs. Villa) might do a step differently. A director orchestrates the order of steps; the builder does the actual step-by-step assembly; only at the very end do you get the finished house.

## 📊 Visualize It

**Prototype pattern structure:**
```
        <<interface>>
          Prototype
         +clone(): Prototype
               ▲
               │ implements
          ┌────┴─────┐
          │  Student  │
          ├───────────┤
          │ -name     │
          │ -age      │
          │ -rollNo   │  (private fields — no external setter access)
          ├───────────┤
          │ +clone()  │──► creates `new Student(this.name, this.age, this.rollNo)`
          └───────────┘

Client:  original = new Student(...)
         clone     = original.clone()   // cloning logic lives INSIDE Student, not in client
```

**Factory vs. Abstract Factory (family safety):**
```
   Factory (one kitchen, many dishes)          Abstract Factory (factory of factories)
   ┌────────────────┐                          ┌──────────────────────┐
   │  ShapeFactory   │                         │ AbstractCarFactory   │◄── interface
   │ +getShape(type) │                         │ +getInstance(price)  │
   └───────┬─────────┘                         └───────────┬──────────┘
           │ if/else on type                                │ implemented by
   ┌───────┼────────┐                          ┌────────────┼─────────────┐
 Circle  Square  Rectangle               EconomyCarFactory        LuxuryCarFactory
                                          returns only               returns only
                                          Economy* cars               Luxury* cars

   CarProducer.getFactory("premium") ──► returns LuxuryCarFactory
   luxuryCarFactory.getInstance(price) ──► returns actual LuxuryCarX
```

**Builder pattern — step-by-step, mediator object:**
```
Director ──uses──► HomeBuilder (abstract)
                        ▲
             ┌──────────┴───────────┐
         FlatBuilder            VillaBuilder
         (overrides createWall)  (overrides createWall)

  director.construct(flatBuilder):
     builder.createWall()  ─┐
     builder.createRoof()   │  each step mutates the SAME
     builder.createDoor()   │  in-progress builder object
     builder.createWindow() ┘  (not the final product yet)
     home = builder.build()  ─► ONLY NOW is the final immutable Home created
```

## 🔧 Deep Dive: How It Actually Works

### 1. Prototype Pattern (the deep-dive topic of this lecture)

**The problem it solves:** Cloning an object naively from *outside* the class runs into two concrete issues:
1. **Private fields are inaccessible.** If `Student.rollNumber` is `private` with no getter, a client trying to build `clonedStudent.rollNumber = original.rollNumber` simply cannot compile.
2. **The client must know every field.** If `Student` has 100 fields and only 98 should be copied, the client (not the `Student` class) is forced to carry that copying logic — a clear violation of encapsulation.

**The fix — push the cloning responsibility into the class itself:**
```java
interface Prototype {
    Prototype clone();
}

class Student implements Prototype {
    private String name;
    private int age;
    private int rollNumber;

    Student(String name, int age, int rollNumber) { ... }

    @Override
    public Prototype clone() {
        // has full access to private fields — no getter/setter gymnastics needed
        return new Student(this.name, this.age, this.rollNumber);
    }
}
```
Client code becomes trivial: `Student clone = original.clone();` — no knowledge of internal fields required.

**Why the `Prototype` interface matters:** without it, one class might expose `getClone()`, another `duplicate()`, another `copy()` — no consistency. The interface forces every cloneable class to expose the *same* contract: `clone()`.

### 2. Singleton Pattern — four implementation strategies

| Strategy | How it works | Problem |
|---|---|---|
| **Eager initialization** | `private static final Connection instance = new Connection();` — created at class-load time | Wastes memory/resources if never actually used |
| **Lazy initialization** | `if (instance == null) instance = new Connection();` inside `getInstance()` | **Not thread-safe** — two threads can both pass the null-check simultaneously and create two instances |
| **Synchronized method** | `public static synchronized Connection getInstance()` | Thread-safe but **expensive** — every single call acquires a lock even after the instance already exists |
| **Double-checked locking** (industry standard) | Check null → lock → check null again → create | Avoids locking overhead once instance exists, while remaining thread-safe |

```java
class DBConnection {
    private static volatile DBConnection instance;
    private DBConnection() {}               // private constructor blocks external `new`

    public static DBConnection getInstance() {
        if (instance == null) {                        // 1st check — avoid locking when already built
            synchronized (DBConnection.class) {
                if (instance == null) {                 // 2nd check — avoid race between threads
                    instance = new DBConnection();
                }
            }
        }
        return instance;
    }
}
```
Key requirements to make Singleton work at all: **private constructor** (blocks external instantiation) + **static accessor method** (so callers use `ClassName.getInstance()`).

### 3. Factory Pattern
Centralizes object-creation logic that would otherwise be duplicated across hundreds of call sites:
```java
class ShapeFactory {
    Shape getShape(String type) {
        if (type.equals("circle"))    return new Circle();
        if (type.equals("square"))    return new Square();
        if (type.equals("rectangle")) return new Rectangle();
        throw new IllegalArgumentException("Unknown shape: " + type);
    }
}
```
If the creation logic ever needs to change (e.g., add a condition before creating a `Circle`), you change **one class**, not every file that used to call `new Circle()`.

### 4. Abstract Factory Pattern — "factory of factories"
Guarantees that a **family** of related objects is never mixed (e.g., you can never accidentally get a luxury-car object from the economy line):
```java
interface AbstractCarFactory {
    Car getInstance(double price);
}
class EconomyCarFactory implements AbstractCarFactory { ... }  // only returns Economy* cars
class LuxuryCarFactory  implements AbstractCarFactory { ... }  // only returns Luxury* cars

class CarProducer {
    AbstractCarFactory getFactory(String tier) {
        return tier.equals("premium") ? new LuxuryCarFactory() : new EconomyCarFactory();
    }
}
// Client: CarProducer producer = new CarProducer();
//         AbstractCarFactory factory = producer.getFactory("premium");  // step 1: pick the factory
//         Car car = factory.getInstance(price);                         // step 2: get the actual product
```

### 5. Builder Pattern — step-by-step construction
Used when object construction requires multiple ordered steps, and different variants implement steps differently:
```java
abstract class StudentBuilder {
    Student student = new Student();
    StudentBuilder setRollNumber(int r) { student.rollNumber = r; return this; }
    StudentBuilder setAge(int a)        { student.age = a; return this; }
    abstract StudentBuilder setSubjects();   // subclasses differ here (Engineering vs MBA)
    Student build() { return student; }      // only NOW is the final product returned
}
class EngineeringStudentBuilder extends StudentBuilder {
    StudentBuilder setSubjects() { student.subjects = List.of("DSA", "OS"); return this; }
}
// Director orchestrates the step order:
Student s = new EngineeringStudentBuilder()
                .setRollNumber(1).setAge(20).setSubjects().build();
```
Critical distinction covered in the transcript: **during construction, the builder holds a "mid-way" mutable object** (not the final product) — the final, presumably immutable `Student` is only materialized when `build()` is invoked.

## 🔥 Real Production Incident & Fix

**What broke:** A fintech team had a `ReportGenerator` object that was expensive to build — it opened a template file, parsed a schema, and pre-computed formatting rules (~200ms per instantiation). Under load, a batch job that generated 50,000 near-identical monthly statements (same template/schema, different customer data) was re-running this expensive constructor 50,000 times, causing the nightly batch to blow past its SLA window and page the on-call engineer at 2 AM.

**How the team noticed:** APM traces (via distributed tracing spans) showed `ReportGenerator.<init>()` consuming over 70% of total batch wall-clock time. A flame graph pinpointed the constructor, not the actual PDF-rendering logic, as the bottleneck.

**Root cause:** The team was calling `new ReportGenerator(templateId)` fresh for every customer instead of recognizing that the *template and schema* (intrinsic, shared data) were identical across all 50,000 reports — only the *customer data* (extrinsic, per-report data) differed. This is exactly the Prototype-pattern symptom: expensive-to-build object + repeated near-identical copies.

**The fix:** They built one `ReportGenerator` "master" per template, implemented `clone()` on it (deep-copying only the mutable per-customer buffer while reusing the parsed template/schema by reference), and had the batch loop clone the master instead of reconstructing it. Batch time dropped from ~2.7 hours to ~11 minutes.

```
BEFORE (no Prototype):                AFTER (Prototype):
for each of 50k customers:            master = new ReportGenerator(templateId)  // built ONCE
   new ReportGenerator(templateId)    for each of 50k customers:
   → reparse template + schema           clone = master.clone()   // cheap copy
   → 200ms × 50,000 = ~2.7 hrs           clone.setCustomerData(...)
                                          → ~13ms × 50,000 = ~11 min
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why not just use a copy constructor instead of the Prototype pattern?**
A copy constructor requires the client to know the concrete class at compile time (`new Student(original)`), which breaks down when you're cloning through an interface/abstract reference and don't know the exact runtime type. `clone()` on a common `Prototype` interface lets you copy any object polymorphically without knowing its concrete class — essential when a registry holds a mix of prototype objects.

**Q2: What's wrong with using `synchronized` on the entire `getInstance()` method for Singleton, and why does double-checked locking need the `volatile` keyword?**
Synchronizing the whole method forces every call — even the millionth call after the instance already exists — to acquire a lock, which is pure overhead. Double-checked locking avoids that by only locking during the brief creation window. `volatile` is required because, without it, JVM/CPU instruction reordering could let another thread see a non-null reference to an object whose constructor hasn't fully finished running (a partially-constructed object) — a genuine, subtle concurrency bug.

**Q3: How is Abstract Factory different from Factory, precisely?**
A Factory produces a *single kind* of object based on input (e.g., "give me a shape"). An Abstract Factory produces a *factory* which itself produces a *family* of related objects (e.g., "give me the luxury-car factory," and everything that factory ever returns is guaranteed to be a luxury car). Abstract Factory is Factory + a guarantee of consistency across a product family.

**Q4: In the Builder pattern, why have both a Builder and a Director — isn't that redundant?**
The Builder owns *how* to perform each individual step (e.g., how `createWall()` works for a `VillaBuilder` vs `FlatBuilder`); the Director owns *the order* in which steps are invoked, which can vary by use case (some products might need step 2 before step 1). Separating "how" from "in what order" lets you reuse the same builder with different directors, or vice versa.

**Q5: When would you avoid Singleton, even though "only one instance" sounds tempting?**
Singleton introduces global mutable state, which hurts testability (hard to mock/reset between unit tests) and can hide hidden dependencies. In modern codebases, dependency injection frameworks (Spring's default singleton-scoped beans) achieve the "one instance" guarantee without the anti-pattern baggage of a hardcoded `getInstance()` — prefer DI-managed singletons over hand-rolled ones when a framework is already present.

**Q6: In Prototype, what happens if `Student` contains a mutable nested object, like a `List<Subject>`? Does `clone()` handle that correctly?**
Not automatically — a naive field-by-field copy (shallow clone) would let the clone and original share the *same* underlying `List` reference, so mutating one's subjects would silently mutate the other's. The `clone()` implementation must explicitly perform a deep copy of any mutable nested fields (e.g., `new ArrayList<>(this.subjects)`) to guarantee true independence between original and clone.

## 🔑 Key Takeaway
Every creational pattern is a targeted answer to one recurring symptom — expensive-to-build objects (Prototype), the need for exactly one instance (Singleton), scattered `new` calls (Factory), families of objects that must stay consistent (Abstract Factory), or multi-step construction with variant steps (Builder) — so in an interview, name the *symptom* first, then map it to the pattern.
