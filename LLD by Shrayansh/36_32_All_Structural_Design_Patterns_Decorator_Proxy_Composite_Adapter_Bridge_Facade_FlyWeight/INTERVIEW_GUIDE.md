# 🧱 All Structural Design Patterns - Interview Guide
## _Decorator · Proxy · Composite · Adapter · Bridge · Facade · Flyweight — 15 YOE Architect-Level Script_

**📘 Difficulty: Intermediate** — assumes you already know the core patterns; focuses on applying them to a real, moderately complex system.

> _(Companion to `transcript.md`, left untouched. Rapid-fire scenario revision guide for all 7 structural patterns.)_

---

**Interviewer**: "Give me all 7 structural patterns back-to-back with a one-line trigger for each."

**You**: "Structural patterns all answer: *how do I arrange/combine existing classes and objects into a bigger structure*, without the arrangement becoming fragile. Here's the map."

---

## 1. Decorator — "Wrap to add behavior, without touching the original"

```
new Mushroom(new ExtraCheese(new Farmhouse()))   -->  layered cost computation
```
**Trigger**: additive features on a base object, avoiding class-explosion from subclassing every combination. _(See dedicated Decorator guide for full detail.)_

---

## 2. Proxy — "A stand-in that controls access to the real object"

```
Client ──▶ EmployeeDaoProxy ──▶ EmployeeDaoImpl (the real object)
              │
              └─ checks: "is caller an ADMIN?" -> yes: forward call
                                                  -> no: throw exception
```
**Trigger**: need access-control / lazy-loading / logging in front of a real object, **without changing the real object's code or the client's expectations** (same interface on both sides).

```java
interface EmployeeDao { void create(); }
class EmployeeDaoImpl implements EmployeeDao { public void create() { /* real DB insert */ } }

class EmployeeDaoProxy implements EmployeeDao {
    private final EmployeeDaoImpl real = new EmployeeDaoImpl();
    public void create() {
        if (!currentUser().isAdmin()) throw new SecurityException("Forbidden");
        real.create();
    }
}
```

---

## 3. Composite — "Treat a tree of objects uniformly, whether leaf or branch"

```
                 FileSystemNode (interface): ls()
                       ▲              ▲
                       │              │
                     File (leaf)   Directory (composite)
                                       │ has-a List<FileSystemNode>
                                       │ (can hold Files AND more Directories)
Directory("root")
 ├── File("readme.md")            <- leaf
 └── Directory("src")             <- composite, recurses
       └── File("Main.java")      <- leaf
```
**Trigger**: "object contains objects of the same abstract type" — trees, nested folders, nested UI components, org charts.

```java
interface FileSystemNode { void ls(); }
class File implements FileSystemNode { public void ls() { System.out.println(name); } }
class Directory implements FileSystemNode {
    List<FileSystemNode> children = new ArrayList<>();
    public void ls() { for (FileSystemNode n : children) n.ls(); }   // recursion!
}
```

---

## 4. Adapter — "Bridge two incompatible interfaces"

```
Client (expects kg)  ──▶ WeightMachineAdapter ──▶ WeightMachine (returns pounds)
                              converts pounds -> kg
```
**Trigger**: integrating a legacy/3rd-party interface that doesn't match what your client code expects, without modifying either side.

---

## 5. Bridge — "Decouple abstraction from implementation so BOTH can vary independently"

```
BEFORE (tightly coupled):            AFTER (Bridge):
LivingThing                          LivingThing --has-a--> BreatheImplementer (I)
 ├── Dog (breathe: nose)                 ├── Dog                  ├── LandBreathe
 ├── Fish (breathe: gills)                ├── Fish                  ├── WaterBreathe
 └── Tree (breathe: leaves)               └── Tree                  └── TreeBreathe
 adding Bird needs a new subclass     adding a new breathing style = new
 AND new breathing logic mixed in     Implementer class; adding a new living
                                        thing = new abstraction class;
                                        neither touches the other hierarchy
```
**Trigger**: two hierarchies that would otherwise multiply combinatorially (like Shape×Color) if left as one inheritance tree.

---

## 6. Facade — "One simple interface hiding a complex subsystem"

```
Client ──▶ ACFacade.turnOn() ──▶ [ExternalUnit.checkVoltage(), startCondenser(),
                                    InternalUnit.acceptTemperature(), acceptCommand()...]
           (client only sees ONE method; 6 internal steps are hidden)
```
**Trigger**: a multi-step, multi-class subsystem where clients shouldn't need to know the internal orchestration, and you want future subsystem changes to NOT ripple out to every caller.

---

## 7. Flyweight — "Share common (intrinsic) data across many objects to save memory"

```
5,00,000 Humanoid Robots + 5,00,000 Robotic Dogs, each carrying a 31KB Sprite
        ⬇ naive: 10,00,000 × 31KB ≈ 31 GB  (OOM!)
        ⬇ Flyweight: extract "type" + "Sprite" (intrinsic, SHARED, identical for
          all robots of that type) out of each object; keep only x,y (extrinsic,
          unique per object) inside each instance.
        ⬇ result: only 2 shared Flyweight objects (one per type) + 10,00,000
          tiny (x,y) coordinate pairs ≈ a few MB total
```
**Trigger**: massive object counts where most of the per-object data is actually IDENTICAL across instances (intrinsic) and only a small part is unique (extrinsic, passed as a parameter instead of stored).

```java
class RobotFactory {
    static Map<String, Robot> cache = new HashMap<>();
    static Robot createRobot(String type) {
        return cache.computeIfAbsent(type, t ->
            t.equals("HUMANOID") ? new HumanoidRobot() : new RoboticDog());  // built ONCE, reused
    }
}
robot.display(x, y);  // x,y passed as parameter (extrinsic) — NOT stored in the shared object
```

---

## 8. The One-Page Decision Table

| Symptom | Pattern |
|---|---|
| "I need to add features without subclass explosion" | Decorator |
| "I need to control/gate access to an object" | Proxy |
| "I have a tree of same-type objects (files, org chart)" | Composite |
| "Two interfaces don't match, I can't change either" | Adapter |
| "Two hierarchies multiply combinatorially" | Bridge |
| "Complex subsystem, client should see ONE simple call" | Facade |
| "Millions of objects, most fields identical across them" | Flyweight |

---

## 9. Senior Trap Questions

**Trap: "Isn't Proxy the same as Decorator? Both wrap an object of the same interface."**
**✅ Senior answer:** "Structurally similar (both implement the same interface and hold a reference to the real object), but **intent** differs: Decorator's job is to **ADD new behavior/features**; Proxy's job is to **CONTROL access** (security, lazy loading, caching, rate-limiting) to the exact same behavior. If you're adding a feature, it's Decorator. If you're gatekeeping, it's Proxy."

**Trap: "Why use Bridge over just Strategy — they both use composition to vary behavior?"**
**✅ Senior answer:** "Strategy solves ONE varying dimension (e.g. just 'how to pay'). Bridge is specifically for when you have **TWO independent hierarchies** that would otherwise be combined via multiple inheritance or subclass explosion (e.g. Shape × Color, or LivingThing × BreathingMechanism) — Bridge lets each hierarchy grow without the other needing changes."

---

## 🔥 Real-World Production Issue: The Facade That Became a Hidden Bottleneck

*In plain English: a facade that quietly grows more steps over time can turn a fast endpoint into a slow one, unnoticed.*

**The war story:**

"Our checkout service had a beautiful `CheckoutFacade.completeOrder()` hiding 7 subsystem calls: inventory reservation, payment capture, tax calculation, shipping label generation, loyalty points, email, and analytics. It made the codebase wonderfully simple for 2 years — that was also the problem."

```
Client ──▶ CheckoutFacade.completeOrder()
              ├─ 1. InventoryService.reserve()      50ms
              ├─ 2. PaymentService.capture()        200ms
              ├─ 3. TaxService.calculate()          30ms
              ├─ 4. ShippingService.generateLabel() 800ms  ◄── new step added later!
              ├─ 5. LoyaltyService.addPoints()       40ms
              ├─ 6. EmailService.send()              20ms
              └─ 7. AnalyticsService.log()           10ms
                                     TOTAL: 1150ms, ALL SEQUENTIAL, ALL SYNCHRONOUS
```

**Root cause:** because the Facade hid the internal orchestration so well, nobody noticed that step 4 (`ShippingService.generateLabel()`, added 8 months after launch by a different team) was called **synchronously and sequentially** inside the facade, on the customer-facing checkout request path. Checkout latency crept from 300ms to 1150ms over many small "just add one more step to the facade" PRs, and nobody looked at the whole picture — that's exactly the risk of a facade: it's *too* easy to keep bolting more steps onto it.

```
   Latency creep (each dot = a PR adding "just one more facade step"):
   1200ms │                                                    ●
   1000ms │                                          ●
    800ms │                                ●
    600ms │                      ●
    400ms │            ●
    200ms │  ●
      0ms └──────────────────────────────────────────────────────▶ time (8 months)
```

**The fix:**
- Split the facade's steps into **critical path** (inventory, payment, tax — must complete before responding to the user) vs **non-critical/async path** (shipping label, loyalty points, email, analytics — dispatched to a message queue, processed asynchronously, with retries).
- Added a latency budget/SLO per facade method and a lightweight internal tracing span per subsystem call, so future "just add one step" PRs would immediately show up in latency dashboards and trigger review.

**Lesson for a new developer:** "Facade is fantastic for hiding complexity, but 'hidden' complexity can silently accumulate technical debt and latency if nobody keeps a latency/complexity budget on the facade itself. Treat the facade's internal orchestration as a first-class thing to monitor, not just an implementation detail to forget about."

---

## 🎓 Final Tips
1. Decorator adds features; Proxy controls access — same shape, different intent.
2. Composite lets you treat leaf and branch nodes uniformly via recursion.
3. Adapter bridges incompatible interfaces you can't modify.
4. Bridge decouples two independently-varying hierarchies.
5. Facade hides subsystem complexity — but must still be watched for latency creep in production.
6. Flyweight shares intrinsic (identical) data and passes extrinsic (per-instance) data as parameters to save massive memory.

Good luck! 🚀
