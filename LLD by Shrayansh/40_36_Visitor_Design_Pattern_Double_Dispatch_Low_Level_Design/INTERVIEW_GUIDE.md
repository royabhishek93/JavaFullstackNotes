# 👁️ Visitor Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

---

**Interviewer**: "Explain the Visitor Design Pattern and Double Dispatch."

**You**: "Visitor Pattern lets you **add new OPERATIONS to a group of related classes WITHOUT modifying those classes**. It uses a technique called **Double Dispatch** to correctly route to the right operation based on BOTH the visited element's type AND the visitor's type."

---

## 1. Architecture Diagram

```
┌──────────────┐                    ┌──────────────┐
│   Shape        │  ◄── Interface     │   Visitor      │  ◄── Interface
│  (interface)   │                    │  (interface)   │
│                │                    │                │
│ accept(Visitor)│                    │ visit(Circle)  │
└───────┬──────┘                    │ visit(Square)  │
        │                            │ visit(Triangle)│
   ┌────┼────┬────────┐             └───────┬──────┘
   ▼    ▼    ▼        │                     │
┌────┐┌────┐┌────────┐│           ┌─────────┼─────────┐
│Circle││Square││Triangle││          ▼                   ▼
└────┘└────┘└────────┘          ┌──────────────┐  ┌──────────────┐
                                 │AreaVisitor    │  │PerimeterVisitor│
                                 └──────────────┘  └──────────────┘
```

## 2. Code Example - Double Dispatch Explained

```java
interface Shape {
    void accept(ShapeVisitor visitor);  // First dispatch: which Shape?
}

interface ShapeVisitor {
    void visit(Circle circle);
    void visit(Square square);
}

class Circle implements Shape {
    double radius;
    public void accept(ShapeVisitor visitor) {
        visitor.visit(this);  // Second dispatch: which visit() overload?
    }
}

class Square implements Shape {
    double side;
    public void accept(ShapeVisitor visitor) {
        visitor.visit(this);
    }
}

// Adding a NEW OPERATION (calculate area) WITHOUT modifying Circle/Square!
class AreaCalculatorVisitor implements ShapeVisitor {
    private double totalArea = 0;
    
    public void visit(Circle circle) {
        totalArea += Math.PI * circle.radius * circle.radius;
    }
    
    public void visit(Square square) {
        totalArea += square.side * square.side;
    }
    
    double getTotalArea() { return totalArea; }
}

// Usage
List<Shape> shapes = List.of(new Circle(5), new Square(4));
AreaCalculatorVisitor areaVisitor = new AreaCalculatorVisitor();
for (Shape shape : shapes) {
    shape.accept(areaVisitor);  // Double dispatch resolves to correct visit() method!
}
System.out.println("Total area: " + areaVisitor.getTotalArea());
```

---

## 3. Scenario-First Explanations

### **Why "Double Dispatch" - What's the Problem with Single Dispatch (Regular Polymorphism)?**

**You**: "Java (like most OOP languages) supports SINGLE dispatch - method resolution depends on ONLY the RUNTIME type of the object the method is called ON, not on argument types:

```java
// ❌ This does NOT work as expected with normal method overloading (single dispatch):
void calculateArea(Shape shape) {
    if (shape instanceof Circle) {
        // handle circle
    } else if (shape instanceof Square) {
        // handle square
    }
    // Every NEW operation requires modifying THIS method + adding instanceof checks!
    // Violates Open/Closed Principle
}
```

**Double Dispatch trick**: 
1. FIRST dispatch: `shape.accept(visitor)` - resolves polymorphically to `Circle.accept()` or `Square.accept()` based on shape's RUNTIME type
2. SECOND dispatch: Inside `accept()`, calling `visitor.visit(this)` - since `this` has COMPILE-TIME type `Circle` (inside `Circle.accept()`), Java resolves to the `visit(Circle)` overload specifically, NOT `visit(Square)`

This TWO-STEP dance is why it's called 'double dispatch' - the correct method is resolved based on BOTH the Shape's type (via the first virtual call) AND implicitly the Visitor's type (via the second call), all without a SINGLE `instanceof` check anywhere!"

### **Why Visitor Enables Adding Operations Without Modifying Existing Classes**

**You**: "Want to add a NEW operation like `PerimeterCalculatorVisitor` or `RenderVisitor` (for drawing)? Just create a NEW class implementing `ShapeVisitor` - ZERO changes to `Circle`, `Square`, or any existing code! This is the Open/Closed Principle taken to its logical extreme - the shape hierarchy is 'closed' for modification but 'open' for new OPERATIONS via new Visitors."

---

## 4. Cross Questions

**Interviewer**: "What's the downside of Visitor Pattern? When would you NOT use it?"

**You**: "The trade-off is INVERTED from Strategy/normal OOP: Visitor makes it EASY to add new OPERATIONS but HARD to add new ELEMENT TYPES (new Shape subclasses). Adding a new `Triangle` class means updating EVERY existing Visitor implementation to add a `visit(Triangle)` method - if you have 10 different visitors, that's 10 places to update!

**Rule of thumb**: Use Visitor when your ELEMENT HIERARCHY is STABLE (rarely add new shapes) but you frequently need NEW OPERATIONS (area, perimeter, rendering, serialization, etc.). If your element hierarchy changes frequently but operations are stable, prefer regular polymorphism (virtual methods on the elements themselves)."

---

## 5. Trade-offs

| Aspect | Visitor Pattern | Regular Polymorphism (methods on Shape) |
|--------|-------------------|------------------------------------------------|
| **Adding new operations** | Easy (new Visitor class) | Hard (modify every Shape subclass) |
| **Adding new element types** | Hard (update every Visitor) | Easy (implement interface methods once) |
| **Best for** | Stable hierarchy, frequent new operations | Frequent new types, stable operations |

---

## 6. Senior Trap Questions

### **Trap: "Just use instanceof checks, simpler than this double-dispatch complexity!"**

**✅ Senior**: "instanceof-based dispatch VIOLATES Open/Closed Principle - EVERY new operation requires modifying a central method with growing if-else/switch chains, AND you lose compile-time safety (forgetting to handle a new Shape subtype only fails at RUNTIME, not compile-time). With Visitor Pattern, if you add a new Shape and forget to update a Visitor interface, the COMPILER forces you to implement the missing `visit()` method - catching the gap at COMPILE TIME instead of a production bug. This compile-time safety is the real senior-level justification for the added complexity."

---

## 7. Technology Choices

**You**: "**AST (Abstract Syntax Tree) traversal in compilers** is THE classic real-world Visitor Pattern use case - a stable set of node types (BinaryExpr, Literal, FunctionCall) with MANY different operations needed (type-checking, code generation, optimization passes, pretty-printing) - each implemented as a separate Visitor without touching the AST node classes."

---

## 🔥 Real-World Production Issue: The Visitor That Forgot to Handle a New Element Type

*In plain English: across independently-deployed services, adding a new type doesn't guarantee every service was updated to handle it.*

**The war story:**

"A hotel-booking platform used Visitor Pattern for room operations (`RoomPricingVisitor`, `RoomMaintenanceVisitor`, `RoomCleaningVisitor` — exactly this guide's example). This guide even calls out the Visitor Pattern's own trade-off: 'easy to add operations, hard to add new element types.' The team learned this the hard way when Product added a new room type."

```
Existing element types: SingleRoom, DoubleRoom, DeluxeRoom
Existing visitors: RoomPricingVisitor, RoomMaintenanceVisitor, RoomCleaningVisitor
(each visitor has a visit() overload for EACH of the 3 room types)

Product added a new room type: SuiteRoom (extends Room, new element type)

BUG: the RoomVisitor INTERFACE was updated to add "visit(SuiteRoom)",
which the compiler correctly forced RoomPricingVisitor and
RoomCleaningVisitor to implement -- BUT RoomMaintenanceVisitor lived
in a SEPARATE microservice/repo (maintained by a different team) that
wasn't redeployed at the same time, and its OLD version of the
RoomVisitor interface (without visit(SuiteRoom)) was still in production

Result: SuiteRoom bookings silently skipped maintenance scheduling
entirely for 3 weeks, because the OLD maintenance service's visitor
implementation had no code path for the new room type at all --
discovered when a guest complained about an uncleaned suite
```

**Root cause:** this is the EXACT trade-off the guide warns about ("hard to add new element types") manifesting across a distributed system — within a single deployable, the compiler guarantees every Visitor implements every element type; but across independently-deployed SERVICES sharing a versioned interface contract, that compile-time guarantee doesn't span deployment boundaries, so a new element type can silently go unhandled by a service that hasn't been updated yet.

**The fix:** for distributed/microservice contexts, added a runtime-level contract test (consumer-driven contract testing) verifying every service implementing `RoomVisitor` handles ALL currently-known room types, run in CI for every service, catching missed implementations BEFORE deployment rather than relying purely on same-process compiler guarantees; also established a rollout convention: new element types require ALL consuming services to deploy their updated visitor implementations before the new element type can be created in production.

**Lesson for a new developer:** "Visitor Pattern's 'add a new element type = compiler forces every visitor to handle it' safety guarantee is a SINGLE-DEPLOYABLE guarantee — it evaporates the moment different Visitor implementations live in independently-deployed services. In a microservices context, pair Visitor Pattern with contract tests and coordinated rollout practices to preserve the safety it promises on paper."

---

## 🎓 Final Tips
1. **Double Dispatch**: Two-step polymorphic resolution avoids instanceof checks
2. **Adds operations without modifying elements** - Open/Closed Principle
3. **Trade-off inverted**: Easy to add operations, hard to add new element types
4. **Real-world**: Compiler AST traversal, code analysis tools

Good luck! 🚀
