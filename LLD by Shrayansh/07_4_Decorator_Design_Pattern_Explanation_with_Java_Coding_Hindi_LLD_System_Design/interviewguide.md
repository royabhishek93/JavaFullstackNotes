# Interview Guide: Decorator Design Pattern

## 🗣️ The Interview Scenario

> "Design a pizza ordering system: there's a base pizza (Margherita, Farmhouse, Veg Delight — each with its own base cost), and a customer can add any combination of toppings — extra cheese, mushroom — and even the *same* topping multiple times (double extra cheese). If you modeled this with one subclass per possible combination, how many classes would you need? Now redesign it so adding a new topping never requires creating new classes for every existing base-pizza-and-topping combination."

This is one of the most commonly asked LLD questions specifically because it exposes "class explosion" — the exact problem the Decorator pattern exists to solve — and pizza/coffee/car customization are the standard framing used across real interviews (including being explicitly called out as a frequent coffee-machine design question).

## 🏗️ Architect's Explanation (For a New Developer)

Imagine a base object — a plain pizza, a plain cup of coffee, a base car — that has some starting features and a starting cost. Now imagine you want to layer *optional, stackable* extras on top of it: extra cheese, mushrooms, AC, power steering. The Decorator pattern's core idea: **wrap the base object in a "decorator" object that has the exact same type/interface as the thing it's wrapping, adds one extra feature, and internally holds a reference to the object it's wrapping** so it can delegate to it and add its own bit on top. Because the decorator is itself the same type as what it wraps, you can wrap a decorator in *another* decorator, and another, and another — like Russian nesting dolls, each layer adding one more feature/cost on top of everything already wrapped inside it. This is exactly how you get "base pizza + extra cheese + mushroom + extra cheese again" without ever writing a single new class for that specific combination.

## 📊 Visualize It

```
CONCEPTUAL SHAPE OF DECORATION (nesting dolls)
────────────────────────────────────────────────
BaseObject (F1)
   └─ Decorator adds F2 → wraps BaseObject         [F1 + F2]
        └─ Decorator adds F3 → wraps previous       [F1 + F2 + F3]
             └─ ...you can keep wrapping forever, each layer
                is itself the same type as what's inside it
```

```
CLASS STRUCTURE (Pizza example)
──────────────────────────────────
        <<abstract>>
        BasePizza
        + getCost() : double
       ▲     ▲      ▲
       │     │      │ extends (IS-A)
  FarmHouse BreadPizza  VegDelight
  (cost=200) (cost=120)  (cost=180)

        <<abstract>>
        ToppingDecorator  extends BasePizza     ← same type it wraps!
        ▲          ▲
        │          │ extends
   ExtraCheese   Mushroom
   - BasePizza pizza     ← HAS-A (composition, constructor-injected)
   + getCost() {
       return pizza.getCost() + 10;   // delegates + adds its own cost
     }
```

```
BEFORE (class explosion)                 AFTER (decorator composition)
──────────────────────────                ─────────────────────────────
FarmHouse                                 new Mushroom(
FarmHousePlusCheese                          new ExtraCheese(
FarmHousePlusCheesePlusMushroom                 new FarmHouse()))
FarmHousePlusMushroomPlusCheese                  ▲
BreadPizzaPlusCheese                             one line, any combination,
BreadPizzaPlusCheesePlusMushroom                 any order, any repeat count —
...(combinatorial explosion,                     ZERO new classes needed
   one class per COMBINATION)
```

## 🔧 Deep Dive: How It Actually Works

### Three real-world motivating examples (all the same shape)
1. **Pizza shop:** base pizza + toppings (extra cheese, mushrooms) — you can combine "base + extra cheese," "base + extra cheese + mushroom," or even "base + extra cheese + mushroom + extra cheese again" (adding the same topping twice).
2. **Coffee shop:** base coffee (with milk/sugar) + add-ons (extra cream, double cream, extra milk in specific quantities like 200ml).
3. **Car customization:** base car (body + basic drivability) + optional add-ons (AC, power steering) in any combination.

### Why a plain inheritance approach fails: class explosion
If you tried to model this with one subclass per exact feature combination — `BaseCar`, `BaseCarPlusAC`, `BaseCarPlusACPlusPowerSteering`, `BaseCarPlusPowerSteering`, and so on — the number of classes grows combinatorially with the number of optional add-ons (and it gets even worse once you allow repeating the same add-on multiple times, or multiple different base products). This is explicitly named as **"class explosion"** — the specific problem that makes the Decorator pattern necessary. The trigger condition for reaching for Decorator: your "base" stays fixed once created, and what varies afterward is purely optional **toppings/combinations layered on top of it**.

### The structural solution
- **`BasePizza`** — an **abstract class** declaring `getCost()` (abstract/to-be-implemented). Concrete pizza types (`FarmHouse`, `BreadPizza`/Margherita, `VegDelight`) directly extend `BasePizza` (a plain IS-A/inheritance relationship) and each implements `getCost()` to return its own fixed price — e.g., Margherita → ₹100, Farmhouse → ₹200, Veg Delight → ₹120 (illustrative figures from the example).
- **`ToppingDecorator`** — also an **abstract class**, and critically, it **extends `BasePizza`** too. This is the key structural trick: the decorator is declared to be the *same type* as the thing it decorates, which is exactly what allows decorators to be stacked on top of each other (a decorator wrapping another decorator is still valid, because both are `BasePizza`s).
- **Concrete toppings** — `ExtraCheese extends ToppingDecorator` and `Mushroom extends ToppingDecorator`. Each holds a `private BasePizza pizza` field — a **HAS-A relationship**, set via **constructor injection**: e.g., `ExtraCheese(BasePizza pizza) { this.pizza = pizza; }`.
- **Cost delegation is the heart of the pattern.** `ExtraCheese.getCost()` returns `pizza.getCost() + 10` (its own fixed topping surcharge added to whatever the wrapped pizza's cost turns out to be) — and, importantly, `pizza.getCost()` might itself be another decorator's `getCost()`, which itself delegates further down, all the way to the innermost concrete base pizza. Similarly, `Mushroom.getCost()` returns `pizza.getCost() + 5`.

### Walking through a concrete combination: Margherita + Extra Cheese + Mushroom
Construction (innermost-first): `BasePizza pizza = new Mushroom(new ExtraCheese(new Margherita()));`

1. `new Margherita()` — a `BasePizza` object whose `getCost()` returns `100`.
2. `new ExtraCheese(margheritaObj)` — wraps the Margherita object; `getCost()` will later compute `margherita.getCost() + 10`.
3. `new Mushroom(extraCheeseObj)` — wraps the `ExtraCheese` decorator (not the base pizza directly!); `getCost()` will compute `extraCheeseObj.getCost() + 5`.

Calling `pizza.getCost()` on the outermost `Mushroom` object triggers a chain of delegated calls: `Mushroom.getCost()` calls `ExtraCheese.getCost()`, which calls `Margherita.getCost()` (returns `100`), then `ExtraCheese` adds its own `+10` (→ `110`), then control returns to `Mushroom`, which adds its own `+5` (→ `115`). The final returned total is `115` — computed entirely via recursive delegation through the wrapping chain, with **no single class anywhere containing "Margherita plus cheese plus mushroom" logic explicitly** — that specific combination exists only as a runtime object graph, not as a class.

### Why order and repetition are both trivially supported
Because every decorator is itself a `BasePizza`, you can wrap decorators in any order and repeat the same topping as many times as needed — e.g., wanting "double extra cheese" is just wrapping an `ExtraCheese` decorator around an object that's already wrapped in another `ExtraCheese` decorator. No new class is ever required for a new combination or repetition count — this is precisely what eliminates the class-explosion problem.

## 🔥 Real Production Incident & Fix

**The incident:** A food-delivery platform's menu-pricing module for a coffee-brand partner initially modeled "coffee with add-ons" using concrete subclasses per exact combination, because the original menu only had three fixed combos ("Latte," "Latte + Extra Shot," "Latte + Extra Shot + Vanilla Syrup"). When the partner rolled out a fully customizable menu (any base drink × any combination of extra shot, syrup, whipped cream, oat milk upgrade, with repeatable extra shots), the engineering team's initial instinct was to keep extending the same pattern — creating a new subclass per newly-requested combination as support tickets came in from the partner's ops team.

**How the team noticed:** Within a month, the pricing module had over 40 near-duplicate subclasses, and a pricing bug (a syrup surcharge silently applied twice) was traced to two classes — `LatteExtraShotVanilla` and `LatteVanillaExtraShot` — that had been created independently by two different engineers for what was meant to be the same combination but had drifted slightly out of sync in their surcharge logic. Code review on the bugfix flagged that the module had, in effect, silently hit the class-explosion problem the team had been warned about in design review months earlier but had deferred addressing.

**Root cause:** Modeling "a fixed base plus an open-ended, combinable, repeatable set of optional add-ons" using one subclass per exact combination is combinatorially unbounded — any new add-on or new base drink multiplies the number of required classes, and near-duplicate classes (like the two differently-ordered Latte variants) inevitably drift apart because there's no single shared source of truth for how a given add-on affects cost.

**The fix:** The team refactored to the Decorator pattern: an abstract `BaseDrink` (with concrete `Latte`, `Cappuccino`, `Americano` subclasses each returning a fixed base cost), an abstract `AddOnDecorator extends BaseDrink` holding a wrapped `BaseDrink` reference, and concrete `ExtraShotAddOn`, `VanillaSyrupAddOn`, `WhippedCreamAddOn`, `OatMilkAddOn` decorators, each adding its own fixed surcharge via delegation. The 40+ subclasses were deleted; every existing and future combination — including repeated extra shots — is now expressed purely as a runtime chain of decorator objects, with each add-on's surcharge logic defined exactly once.

```
BEFORE: one subclass per exact combination      AFTER: Decorator pattern, one class per add-on
(40+ classes, some duplicated/drifted)          ────────────────────────────────────────────────
Latte                                           BaseDrink (Latte, Cappuccino, Americano)
LatteExtraShot                                       ▲
LatteExtraShotVanilla     ← drifted logic       AddOnDecorator extends BaseDrink
LatteVanillaExtraShot     ← drifted logic            ├─ ExtraShotAddOn  (+cost, delegates)
LatteVanillaShot...                                   ├─ VanillaSyrupAddOn (+cost, delegates)
(combinatorial explosion continues)                   ├─ WhippedCreamAddOn (+cost, delegates)
                                                       └─ OatMilkAddOn (+cost, delegates)
                                                 Any combination = nested constructor calls,
                                                 zero new classes, one surcharge source of truth
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why must `ToppingDecorator` extend `BasePizza` rather than just holding a `BasePizza` reference without extending it?**
A: The whole point of the pattern is that a decorated object must be usable *anywhere* a plain base object could be used — including being wrapped by yet another decorator. If `ToppingDecorator` didn't extend `BasePizza`, you couldn't pass a decorated pizza into another decorator's constructor (which expects a `BasePizza`), and you couldn't stack multiple toppings at all.

**Q2: How does the Decorator pattern differ from simply adding optional boolean fields (like `hasExtraCheese`, `hasMushroom`) directly onto a single `Pizza` class?**
A: The flag-based approach doesn't scale to *repeated* add-ons (e.g., double extra cheese needs a quantity, not a boolean) and forces every new topping to modify the shared `Pizza` class and its cost-calculation method — violating the Open/Closed Principle. Decorator instead adds each new topping as an entirely new, independent class, and repetition is handled naturally by just wrapping the same decorator multiple times.

**Q3: What's the exact mechanism by which the final cost gets computed, and why is it recursive?**
A: Each decorator's `getCost()` calls `wrappedObject.getCost()` and adds its own fixed surcharge to the result. Since the wrapped object might itself be another decorator (whose `getCost()` does the same thing one level deeper), the calls chain recursively inward until they reach the innermost concrete base pizza, which returns a plain fixed value with no further delegation — then the results bubble back outward, each layer adding its own cost on the way back.

**Q4: Where else, outside of food/drink examples, is the Decorator pattern commonly used in real systems?**
A: Java's I/O stream classes are a classic real example — wrapping a `FileInputStream` in a `BufferedInputStream`, then in a `GZIPInputStream`, each layer adding behavior (buffering, decompression) while preserving the same `InputStream`-compatible interface, exactly mirroring the pizza/topping wrapping structure.

**Q5: How would you extend this design to support removing a specific add-on after the object has already been constructed (e.g., "remove one extra cheese")?**
A: The pattern as described is naturally suited to *adding* wrapped layers, not surgically removing an inner one after construction, since each layer only knows about the thing it directly wraps, not the reverse. In practice, you'd typically reconstruct the desired chain from scratch (e.g., recompute the order from the customer's current topping list) rather than trying to "unwrap" a specific layer out of an existing object graph.

**Q6: What's the risk of over-using Decorator, and when would a simpler approach (like a list of add-on IDs with a lookup table for costs) be preferable?**
A: If add-ons are purely additive numeric costs with no behavioral differences (no differing logic per add-on, just "add X to the price"), a simple list of add-on identifiers plus a cost lookup table is simpler and avoids the object-wrapping ceremony entirely. Decorator earns its complexity specifically when each add-on can carry genuinely different *behavior* (not just a number) that needs to compose cleanly with other add-ons' behavior.

## 🔑 Key Takeaway

Reach for the Decorator pattern specifically when you have a fixed base object plus an open-ended, combinable, and possibly repeatable set of optional add-ons — model the add-on as an abstract decorator that extends the same base type it wraps, delegates to the wrapped object, and adds its own contribution, so new combinations and new add-ons never require new classes.
