# Interview Guide: All Structural Design Patterns (Decorator, Proxy, Composite, Adapter, Bridge, Facade, Flyweight)

## 🗣️ The Interview Scenario

> "In one session, I want you to design: (1) a pizza-ordering system where toppings can be layered onto a base pizza without a combinatorial explosion of classes, (2) a way to restrict who can call `EmployeeDao.create()` based on role, (3) a file-system model where a directory can contain files or other directories, (4) an adapter so a weight machine that only returns pounds can serve a client that only understands kilograms, (5) a class hierarchy for living things and their breathing mechanisms that can grow independently on both axes, (6) a simplified interface that hides a complex air-conditioner subsystem from client code, and (7) a memory-efficient way to render a text/game object where thousands of instances share the same underlying data. For each, name the structural pattern you'd use and sketch the class relationships."

This is a rapid-fire "match the symptom to the structural pattern" question — the interviewer wants to see that you instantly recognize *class-explosion* → Decorator, *access-control* → Proxy, *tree-shaped containment* → Composite, *incompatible interfaces* → Adapter, *two independently-varying dimensions* → Bridge, *hide subsystem complexity* → Facade, and *shared-data memory savings* → Flyweight.

## 🏗️ Architect's Explanation (For a New Developer)

**Structural patterns** are all about one shared goal: taking existing classes and objects and **arranging** them — via composition or inheritance ("has-a" and "is-a" relationships) — into a bigger structure that solves a specific problem, *without* rewriting the pieces themselves. Here's the whole family in one breath, using everyday analogies:

- **Decorator** — "Pizza toppings." Add features to an object one layer at a time (extra cheese, then mushroom) without changing the base object or creating a new class for every combination.
- **Proxy** — "A security guard at a door." Something stands *in front of* the real object, controlling or logging access before the real object is ever reached.
- **Composite** — "Nested folders." A container can hold either a leaf (a file) or another container (a subfolder) — and you treat both uniformly through one shared interface, recursively.
- **Adapter** — "A power-plug adapter." Converts one interface's output (pounds) into what the client actually understands (kilograms), acting purely as a translator in the middle.
- **Bridge** — "A universal remote and interchangeable batteries." Splits an abstraction (living things) from its implementation detail (how they breathe) so *either side* can grow independently without touching the other.
- **Facade** — "A car's ignition button." Hides a complex multi-step subsystem (engine, fuel injection, starter motor) behind one simple method the client calls.
- **Flyweight** — "Photocopied name badges." Share identical, expensive-to-build data (e.g., a rendered glyph or graphic) across thousands of objects, storing only the small bit that's genuinely unique to each instance.

## 📊 Visualize It

**All seven, at a glance:**
```
DECORATOR                    PROXY                        COMPOSITE
BasePizza                    Client                       <<interface>> FileSystem
  ▲ is-a                        │                              ▲  ▲
ToppingDecorator "has-a" ─┐   ProxyDao ──controls──► RealDao   │  │
  ▲        ▲               │  (checks role first)     File ───┘  Directory ──has list of──┐
ExtraCheese Mushroom ◄──────┘                                              FileSystem ◄────┘
(wraps + adds cost)                                                        (leaf OR composite)

ADAPTER                      BRIDGE                        FACADE
Client → WeightMachine        LivingThing (abstraction)     Client → ACFacade → {ExternalUnit,
  Adapter (interface)            "has-a" ──► BreatheImpl      (one turnOn()      InternalUnit,
  → AdapterImpl                      ▲            (interface)  method)          many sub-steps}
     "has-a" WeightMachine    Dog/Fish/Tree       LandBreathe/
     (pounds) ──► converts     (each set their    WaterBreathe/
     to kg for client          own implementer)   LeafBreathe

FLYWEIGHT
LetterFactory (cache: Map<key, FlyweightObj>) ──► shared immutable intrinsic object
  client passes extrinsic data (row, col / x, y) as a PARAMETER at use-time, never stored
```

**Decorator layering detail (pizza cost accumulation):**
```
FarmhousePizza (cost=200)
   └─wrapped by─► ExtraCheeseDecorator (cost = base.cost() + 10 = 210)
                    └─wrapped by─► MushroomDecorator (cost = base.cost() + 15 = 225)
pizza.cost() → 225   // each decorator delegates to its wrapped object, then adds its own bit
```

## 🔧 Deep Dive: How It Actually Works

### 1. Decorator — add functionality without changing structure
**Problem avoided: class explosion.** Without Decorator, supporting N toppings on M base pizzas naively requires a class per *combination* (`MargaritaExtraCheese`, `MargaritaMushroom`, `MargaritaExtraCheeseMushroom`, ...).
```java
abstract class BasePizza { abstract double cost(); }
class Farmhouse extends BasePizza { double cost() { return 200; } }
class Margarita extends BasePizza { double cost() { return 100; } }

abstract class ToppingDecorator extends BasePizza {   // "is-a" BasePizza AND "has-a" BasePizza
    protected BasePizza pizza;
    ToppingDecorator(BasePizza pizza) { this.pizza = pizza; }
}
class ExtraCheese extends ToppingDecorator {
    ExtraCheese(BasePizza pizza) { super(pizza); }
    double cost() { return pizza.cost() + 10; }
}
class Mushroom extends ToppingDecorator {
    Mushroom(BasePizza pizza) { super(pizza); }
    double cost() { return pizza.cost() + 15; }
}
// pizza = new Mushroom(new ExtraCheese(new Farmhouse()));  → cost() = 200 + 10 + 15 = 225
```
Key structural detail: `ToppingDecorator` both **extends** `BasePizza` (so it *is* a pizza and can be layered further) and **holds a reference to** a `BasePizza` (so it can delegate and add its own increment).

### 2. Proxy — control access to the original object
```java
interface EmployeeDao { void create(); }
class EmployeeDaoImpl implements EmployeeDao { public void create() { /* real DB insert */ } }
class EmployeeDaoProxy implements EmployeeDao {
    private EmployeeDao real = new EmployeeDaoImpl();
    public void create() {
        if (!isAdminCall()) throw new SecurityException("not authorized");
        real.create();                          // only forwards if check passes
    }
}
```
The proxy implements the *same interface* as the real object, holds a reference to it, and interposes validation/logging/control before (or instead of) forwarding the call.

### 3. Composite — objects inside objects, tree-shaped
```java
interface FileSystem { void ls(); }
class File implements FileSystem {
    private String name;
    public void ls() { System.out.println(name); }
}
class Directory implements FileSystem {
    private List<FileSystem> children = new ArrayList<>();  // can hold File OR Directory
    void add(FileSystem fs) { children.add(fs); }
    public void ls() {
        for (FileSystem fs : children) fs.ls();               // RECURSION — leaf or composite, same call
    }
}
```
The defining trait: a composite node's operation (`ls()`) *recurses* into its children, and because both `File` (leaf) and `Directory` (composite) implement the same `FileSystem` interface, the caller never needs to check "is this a file or a directory?"

### 4. Adapter — bridge two incompatible interfaces
```java
interface WeightMachine { double getWeightInPounds(); }
class WeightMachineImpl implements WeightMachine { public double getWeightInPounds() { return 30; } }

interface WeightMachineAdapter { double getWeightInKg(); }
class WeightMachineAdapterImpl implements WeightMachineAdapter {
    private WeightMachine machine;
    WeightMachineAdapterImpl(WeightMachine machine) { this.machine = machine; }
    public double getWeightInKg() { return machine.getWeightInPounds() * 0.453592; }
}
// Client talks ONLY to the adapter, never directly to WeightMachine
```
The adapter sits in the middle, translating the adaptee's output format into what the client actually expects — the client is fully unaware the underlying machine even speaks in pounds.

### 5. Bridge — decouple abstraction from implementation so both vary independently
The transcript's motivating example: `LivingThing` (Dog, Fish, Tree) originally had `breatheProcess()` hardcoded *inside* each subclass — adding a new breathing mechanism (e.g., a bird breathing through nostrils) required modifying/adding a `LivingThing` subclass directly, tightly coupling "what kind of living thing" to "how it breathes."
```java
interface BreatheImplementer { void breatheProcess(); }
class LandBreathe implements BreatheImplementer {
    public void breatheProcess() { System.out.println("breathe through nose, inhale O2, exhale CO2"); }
}
class WaterBreathe implements BreatheImplementer {
    public void breatheProcess() { System.out.println("breathe through gills"); }
}

abstract class LivingThing {
    protected BreatheImplementer breatheImplementer;         // the "bridge" reference
    LivingThing(BreatheImplementer b) { this.breatheImplementer = b; }
    void breatheProcess() { breatheImplementer.breatheProcess(); }
}
class Fish extends LivingThing {
    Fish() { super(new WaterBreathe()); }
}
```
Now new breathing mechanisms (`NostrilBreathe` for birds) can be added **without touching `LivingThing` or its subclasses**, and new living-thing types can reuse existing breathing implementers — the two hierarchies (species vs. breathing mechanism) scale independently.

### 6. Facade — hide subsystem complexity
```java
class ACExternalUnit { void checkVoltage() {...} void consumeNitrogen() {...} void startCondenser() {...} }
class ACInternalUnit { void acceptUserTemperature() {...} void acceptUserOnCommand() {...} }

class ACFacade {
    private ACExternalUnit external = new ACExternalUnit();
    private ACInternalUnit internal = new ACInternalUnit();
    void turnOn() {                                    // ONE method hides the whole sequence
        external.checkVoltage();
        external.consumeNitrogen();
        external.startCondenser();
        internal.acceptUserOnCommand();
    }
}
// Client: acFacade.turnOn();   — never needs to know the internal step sequence
```
Two flavors highlighted in the transcript: (a) exposing only *necessary* methods (e.g., only `insert()` from a `Dao` with `insert/delete/updateById`), and (b) hiding an entire *multi-step orchestration* behind one method — both reduce client coupling to internal complexity, and future changes to the sequence only touch the facade.

### 7. Flyweight — reduce memory via shared intrinsic data
```java
interface Robot { void display(int x, int y); }        // extrinsic (x, y) passed as parameter
class HumanoidRobot implements Robot {
    private final String type; private final byte[] sprite;   // intrinsic — shared, immutable
    HumanoidRobot(String type, byte[] sprite) { this.type = type; this.sprite = sprite; }
    public void display(int x, int y) { /* render sprite at x,y */ }
}
class RobotFactory {
    static Map<String, Robot> cache = new HashMap<>();
    static Robot createRobot(String type) {
        if (cache.containsKey(type)) return cache.get(type);      // reuse
        Robot r = type.equals("humanoid") ? new HumanoidRobot(type, buildSprite()) : new RoboticDog(...);
        cache.put(type, r);
        return r;
    }
}
```
Same recipe as always: strip extrinsic fields out of the shared object, make it immutable, pass extrinsic data as a method parameter, and cache-and-reuse via a factory keyed by the intrinsic identity.

## 🔥 Real Production Incident & Fix

**What broke:** An e-commerce platform's checkout module used a `Facade` (`CheckoutFacade.completeOrder()`) that internally called seven subsystem steps: validate cart, reserve inventory, calculate tax, apply promo, charge payment, generate invoice, send confirmation email. A new engineer, under deadline pressure, **bypassed the facade** and called `PaymentGateway.charge()` directly from a new "quick reorder" feature — skipping the inventory-reservation and tax-recalculation steps that the facade normally guaranteed happened *before* payment.

**How the team noticed:** Finance flagged a spike in "paid orders with incorrect tax amount" and "orders charged for items that were actually out of stock" specifically from the quick-reorder flow — a metrics dashboard segmenting orders by entry-point showed the anomaly was isolated to that one bypassing code path.

**Root cause:** The Facade's entire value — guaranteeing a fixed, correct sequence of subsystem calls — was silently defeated because a new code path reached around it and called a lower-level subsystem method directly. This is a textbook Facade-misuse incident: the pattern only protects you if *all* callers are disciplined about going through it.

**The fix:** The team made `PaymentGateway.charge()` package-private (not public) so it could only be invoked from within the checkout module's package, forcing all external callers — including the new quick-reorder feature — to go through `CheckoutFacade`. They also added an architectural fitness test (a static-analysis rule via ArchUnit) that fails the build if any class outside the checkout package calls subsystem classes directly, preventing future accidental facade bypasses.

```
BEFORE (facade bypassed):                       AFTER (facade enforced + guarded):
QuickReorderFeature                             QuickReorderFeature
    │                                               │
    └──directly calls──► PaymentGateway.charge()    └──must call──► CheckoutFacade.completeOrder()
         (skips inventory + tax steps)                                  │
                                                                          ├─ validateCart()
                                                                          ├─ reserveInventory()
                                                                          ├─ calculateTax()
                                                                          └─ PaymentGateway.charge()
                                                     PaymentGateway.charge() now package-private
                                                        → compile error if called from outside
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: How do you tell Decorator and Proxy apart, since both "wrap" an object of the same interface?**
Decorator is about **adding new behavior/responsibility** to an object (and decorators can be stacked in any combination/order, each adding its own increment), while Proxy is about **controlling access** to an object (logging, authorization, lazy-loading) without changing or adding to its actual behavior — the proxy's `create()` either forwards unchanged or refuses, it doesn't enrich the result.

**Q2: How is Facade different from Adapter, since both sit "in front of" something?**
Adapter's job is to make one *existing, incompatible* interface usable by translating its calls/format (pounds → kg) — it doesn't simplify anything, just translates. Facade's job is to *simplify* a complex subsystem with many classes/steps into one easy entry point — it isn't solving an incompatibility problem, it's solving a complexity/coupling problem.

**Q3: When would you choose Bridge over simple subclassing?**
When you have **two independently varying dimensions** (e.g., "type of living thing" and "how it breathes," or "shape" and "rendering engine") — if you used plain subclassing for both dimensions, you'd get a combinatorial explosion of classes (`FlyingBirdNostrilBreathe`, `SwimmingFishGillBreathe`, ...). Bridge splits the two dimensions into separate hierarchies connected by a "has-a" reference, so either dimension can add new variants without touching the other.

**Q4: In Composite, how do you handle operations that only make sense for one type (leaf vs. composite), like "add a child," which a `File` can't support?**
Common approaches: (a) throw `UnsupportedOperationException` from the leaf's `add()` if the interface exposes it uniformly, or (b) keep `add()`/`remove()` only on the `Directory` (composite) type and have client code type-check or use `instanceof` when it specifically needs to build the tree — the transcript's example keeps `add()` only on `Directory`, not on the shared `FileSystem` interface, avoiding this exact problem.

**Q5: Isn't Flyweight incompatible with the other structural patterns — could you combine it with, say, Composite?**
Yes — a very natural combination: in a Composite file-system tree, if many `File` leaf nodes share identical metadata (e.g., default permission templates), those shared parts could be flyweighted, while the tree structure itself (parent-child containment) remains a Composite. Patterns aren't mutually exclusive; production systems frequently layer multiple structural patterns together.

**Q6: What's the single biggest risk of overusing Decorator?**
Debuggability — a deeply nested stack of decorators (`new C(new B(new A(base)))`) can make it hard to reason about the final object's behavior or trace which layer contributed which side effect, especially if decorators have subtle ordering dependencies (e.g., a logging decorator needs to wrap *outside* a caching decorator to log actual work, not cache hits) — always document expected wrapping order when decorators aren't fully order-independent.

## 🔑 Key Takeaway
Every structural pattern answers "how do I arrange existing classes/objects to solve a specific structural problem" — Decorator adds behavior without subclass explosion, Proxy controls access, Composite unifies tree-shaped containment, Adapter translates incompatible interfaces, Bridge decouples two independently-varying hierarchies, Facade hides subsystem complexity, and Flyweight shares data to save memory — in an interview, name the *symptom* first, then the pattern.
