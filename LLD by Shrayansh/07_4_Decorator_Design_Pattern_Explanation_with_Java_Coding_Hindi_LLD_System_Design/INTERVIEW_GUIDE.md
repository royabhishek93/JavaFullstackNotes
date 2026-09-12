# 🍕 Decorator Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

> _(Companion to `transcript.md`, left untouched. Whiteboard-style scenario discussion for a new developer.)_

---

**Interviewer**: "Design a Pizza Billing System / Coffee Machine where a base item can have any combination of add-ons (extra cheese, mushroom, extra shot, whipped cream…), and the price/behavior must reflect all the combinations without class explosion."

**You**: "This is textbook **Decorator Pattern** — 'add more functionality to an existing object, without changing its structure', by wrapping it in layers."

---

## 1. Architecture Diagram

```
                     ┌───────────────────┐
                     │   BasePizza (abstract) │
                     │   + cost()               │
                     └─────────┬──────────────┘
                ┌────────────────┼───────────────┐
                ▼                                 ▼
        ┌───────────────┐               ┌────────────────────┐
        │  Farmhouse (₹200)│               │  ToppingDecorator   │  ◄─ IS-A BasePizza
        │  Margherita (₹100)│               │  (abstract)           │     AND
        └───────────────┘               │  - basePizza reference │  HAS-A BasePizza
                                          └─────────┬──────────────┘
                                    ┌─────────────────┼───────────────┐
                                    ▼                 ▼                ▼
                            ExtraCheese(+10)   Mushroom(+15)      Veggie(+8)
```

```java
abstract class BasePizza {
    abstract double cost();
}
class Farmhouse extends BasePizza { double cost() { return 200; } }
class Margherita extends BasePizza { double cost() { return 100; } }

abstract class ToppingDecorator extends BasePizza {     // IS-A pizza...
    protected BasePizza basePizza;                        // ...and HAS-A pizza (wraps it)
}

class ExtraCheese extends ToppingDecorator {
    ExtraCheese(BasePizza basePizza) { this.basePizza = basePizza; }
    double cost() { return basePizza.cost() + 10; }        // delegate + add
}
class Mushroom extends ToppingDecorator {
    Mushroom(BasePizza basePizza) { this.basePizza = basePizza; }
    double cost() { return basePizza.cost() + 15; }
}

// Usage: layers wrap layers, like an onion
BasePizza pizza = new Mushroom(new ExtraCheese(new Farmhouse()));
pizza.cost();  // -> 200 (Farmhouse) + 10 (ExtraCheese) + 15 (Mushroom) = 225
```

```
Call stack visualization for pizza.cost():

  Mushroom.cost()
     └─▶ ExtraCheese.cost()
            └─▶ Farmhouse.cost() = 200
         returns 200 + 10 = 210
  returns 210 + 15 = 225
```

---

## 2. Scenario-First Explanation: Why Not Just Subclass Every Combination?

**You**: "Without Decorator, to support Margherita+ExtraCheese, Margherita+Mushroom, Margherita+ExtraCheese+Mushroom, Farmhouse+ExtraCheese... you'd need a subclass for **every permutation of base × toppings**. With just 2 bases and 5 toppings, that's already 2 × 2⁵ = 64 potential classes. This is called **class explosion**, and Decorator solves it by separating 'base' from 'toppings' and letting toppings be stacked dynamically at runtime instead of at compile time."

---

## 3. Cross Questions

**Q: "How is this different from the Builder pattern? Both seem to 'construct' something."**
**A:** "Builder assembles a single object step-by-step and then calls `build()` once to get an **immutable final product** — construction ends there. Decorator wraps an *already complete, usable* object in layers, where **each layer itself is fully functional and can be used independently at any point** — `new Farmhouse()` is a valid pizza, `new ExtraCheese(new Farmhouse())` is also a valid, complete pizza. You're not 'finishing' anything — you're composing behavior recursively."

**Q: "Can I add toppings in any order, and does order matter?"**
**A:** "Order can matter for cost accumulation logic but typically not for the total value (addition is commutative). But it CAN matter for behavior, e.g. if a `DiscountDecorator` computes percentage-off — applying it before vs after `ExtraCheese` gives different totals. Always clarify this with the interviewer for behavior-changing decorators, not just additive ones."

---

## 4. Trade-offs

| Aspect | Decorator Pattern | Subclass-per-combination |
|---|---|---|
| Number of classes | O(features) | O(2^features) — explodes |
| Runtime flexibility | Add/remove layers dynamically | Fixed at compile time |
| Readability of construction | `new Mushroom(new ExtraCheese(new Base()))` (nested) | Simple `new SpecificComboClass()` but only for pre-defined combos |

---

## 5. Senior Trap Questions

**Trap: "Why not just add a `List<String> toppings` field to `Pizza` and loop over it to add costs?"**
**✅ Senior answer:** "That works for simple additive cost, but breaks down the moment toppings have their *own behavior* beyond a number — e.g. a topping that changes `describe()` text, or triggers different `cook()` steps, or needs to be a composable/stackable object elsewhere in the code (like `StringBuilder`-style wrapping in `OkHttp`'s interceptors or Java I/O streams: `new BufferedInputStream(new GZIPInputStream(new FileInputStream(...)))`). Decorator generalizes to ANY behavior, not just additive numeric fields — that's why it's a design pattern and not just a data structure choice."

---

## 🔥 Real-World Production Issue: The Java I/O Stream Decorator Memory Leak

*In plain English: closing only the innermost layer of a wrapped object skips the outer layers' cleanup logic, silently corrupting your output.*

**The war story:**

"This isn't hypothetical — Java's own `InputStream`/`OutputStream` hierarchy IS the Decorator Pattern in production, and it's a classic source of **resource leak bugs** that I've personally debugged."

```
new BufferedOutputStream(
   new GZIPOutputStream(
      new FileOutputStream("report.gz")))
```

```
┌───────────────────────────┐
│ BufferedOutputStream (decorator)│
│  wraps ↓                            │
│ ┌───────────────────────┐        │
│ │ GZIPOutputStream (decorator)│      │
│ │  wraps ↓                        │      │
│ │ ┌─────────────────┐        │      │
│ │ │ FileOutputStream   │        │      │   <- holds the actual OS file handle
│ │ │ (the REAL resource) │        │      │
│ │ └─────────────────┘        │      │
│ └───────────────────────┘        │
└───────────────────────────┘
```

**Incident:** a batch export job called `outer.write(data)` then only called `fileOutputStream.close()` directly (closing the *innermost* wrapped object) instead of `outer.close()` (the outermost decorator). Result: the `BufferedOutputStream`'s internal buffer was never flushed, and files were silently truncated in production for 6 hours before a downstream data pipeline flagged corrupted `.gz` files.

```
  ❌ WRONG: fileOutputStream.close();     -- closes only the innermost layer
             GZIPOutputStream's trailer never written, buffer never flushed
             → truncated / corrupt file

  ✅ RIGHT: bufferedOutputStream.close(); -- closes the OUTERMOST decorator
             which internally flushes + closes each wrapped layer in order:
             Buffered.close() -> flush buffer -> Gzip.close() -> write trailer
                                -> File.close() -> release OS handle
```

**Root cause:** whoever wrote the closing code didn't understand that in a Decorator chain, **you must always operate on the OUTERMOST wrapper**, because each layer's `close()`/`flush()` is responsible for finishing its own work AND delegating to the wrapped inner object. Skipping layers breaks that contract.

**Fix applied:** enforced use of `try-with-resources` on the outermost decorator only, added a static analysis rule (SpotBugs/Error Prone) to flag direct access to inner stream references after wrapping, and added integration tests that verify `.gz` files are valid (not just "file exists").

**Lesson for a new developer:** "When you build your own Decorator chains — pizza toppings, HTTP client interceptors, whatever — always expose ONLY the outermost wrapped reference to callers. Never let calling code reach 'through' the decorator to the wrapped object directly; that breaks the whole pattern's guarantees, exactly like this incident."

---

## 🎓 Final Tips
1. Decorator = wrap an object in layers, each layer both IS-A the same type and HAS-A reference to the wrapped object.
2. Solves **class explosion** from combinatorial subclassing.
3. Each layer must be fully usable standalone — that's what differentiates it from Builder.
4. In production (I/O streams, HTTP interceptors), always operate on the **outermost** decorator only — never reach into inner layers directly.

Good luck! 🚀
