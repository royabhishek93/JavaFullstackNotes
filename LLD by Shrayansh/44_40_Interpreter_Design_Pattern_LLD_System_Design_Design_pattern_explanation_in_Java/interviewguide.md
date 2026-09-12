# Interview Guide: Interpreter Design Pattern

## 🗣️ The Interview Scenario

> "Design a small system that can evaluate mathematical expressions like `a * b` or `a * b + c * d`, where the actual values of `a`, `b`, `c`, `d` are supplied at runtime via some kind of context/variable map. How would you structure this so that arbitrarily complex expressions can be built up and evaluated, and new operators could be added later?"

This tests whether you can recognize an **"evaluate an expression against a context"** problem and map it to the **Interpreter pattern**, including correctly identifying terminal vs. non-terminal expressions and using recursion to resolve nested sub-expressions.

## 🏗️ Architect's Explanation (For a New Developer)

Picture a hand raised in the air. On its own, that gesture is ambiguous — it could mean "stop," "hello," "the number five," or "I have a question." What it actually *means* depends entirely on the **context** you interpret it in: at a traffic intersection, it means stop; among friends, it's a greeting; in a math class, it might represent the digit five. The gesture is the same; the *interpretation* changes based on context.

The **Interpreter pattern** is exactly this idea formalized for evaluating expressions: it defines a way to **understand/evaluate an expression using a supplied context**. In programming terms, an expression like `a * b` breaks down into pieces:
- **Terminal expressions** — things that cannot be broken down further (e.g., the variable `a`, or the variable `b`, standing alone).
- **Non-terminal expressions** — things built up from other expressions (e.g., `a * b` is non-terminal because it's composed of `a`, `b`, and the `*` operation; it can be split further).

Every expression, no matter how complex, is a tree of terminal and non-terminal pieces, and you evaluate it by recursively asking each piece "what's your value, given this context?" — terminal pieces answer directly by looking themselves up in the context; non-terminal pieces recursively ask their children, then combine the results.

## 📊 Visualize It

**Class structure:**

```
              <<interface>>
           AbstractExpression
         -----------------------
         + interpret(Context ctx) : int
                    ▲
       ┌────────────┴─────────────────┐
NumberTerminalExpression       MultiplyNonTerminalExpression
------------------------      -------------------------------
- value : String (var name)   - left : AbstractExpression
+ interpret(ctx):              - right : AbstractExpression
    return ctx.get(value)     + interpret(ctx):
                                  return left.interpret(ctx)
                                       * right.interpret(ctx)

              Context
       -------------------------
       - variables : Map<String,Integer>   e.g., {"a":2, "b":4}
       + get(String name) : int
```

**Evaluating `a * b + c * d` (a tree of terminals and non-terminals):**

```
                     SumNonTerminalExpression
                      (left, right, op = "+")
                   /                          \
     MultiplyNonTerminalExpr              MultiplyNonTerminalExpr
      (left=a, right=b)                     (left=c, right=d)
        /          \                          /          \
   NumberTerm(a) NumberTerm(b)          NumberTerm(c) NumberTerm(d)

Context = { a:2, b:4, c:8, d:16 }

interpret() resolution (bottom-up):
  NumberTerm(a).interpret(ctx) = 2         NumberTerm(b).interpret(ctx) = 4
  Multiply(a,b).interpret(ctx) = 2*4 = 8
  NumberTerm(c).interpret(ctx) = 8         NumberTerm(d).interpret(ctx) = 16
  Multiply(c,d).interpret(ctx) = 8*16 = 128
  Sum(...).interpret(ctx) = 8 + 128 = 136
```

## 🔧 Deep Dive: How It Actually Works

### 1. `AbstractExpression` — the interface every piece implements
```java
interface AbstractExpression {
    int interpret(Context context);
}
```

### 2. `Context` — the runtime variable bindings
```java
class Context {
    private Map<String, Integer> variables = new HashMap<>();
    void set(String name, int value) { variables.put(name, value); }
    int get(String name) { return variables.get(name); }
}
```

### 3. Terminal expression — cannot be broken down further, resolves directly from context
```java
class NumberTerminalExpression implements AbstractExpression {
    private String variableName;   // e.g., "a"
    NumberTerminalExpression(String variableName) { this.variableName = variableName; }

    public int interpret(Context context) {
        return context.get(variableName);   // asks the context directly
    }
}
```

### 4. Non-terminal expression — composed of two (or more) sub-expressions, resolved recursively
```java
class MultiplyNonTerminalExpression implements AbstractExpression {
    private AbstractExpression left;
    private AbstractExpression right;

    MultiplyNonTerminalExpression(AbstractExpression left, AbstractExpression right) {
        this.left = left;
        this.right = right;
    }

    public int interpret(Context context) {
        return left.interpret(context) * right.interpret(context);
        // left/right could themselves be terminal OR non-terminal — this recurses naturally
    }
}
```
The key structural insight: `left` and `right` are typed as `AbstractExpression`, so a `MultiplyNonTerminalExpression` can hold either a `NumberTerminalExpression` **or another `MultiplyNonTerminalExpression`** as a child — this is what lets the tree grow arbitrarily deep for complex expressions.

### 5. Client — building and evaluating `a * b`
```java
Context context = new Context();
context.set("a", 2);
context.set("b", 4);

AbstractExpression expr = new MultiplyNonTerminalExpression(
    new NumberTerminalExpression("a"),
    new NumberTerminalExpression("b")
);

int result = expr.interpret(context);   // 2 * 4 = 8
```

### 6. Scaling up to `a * b + c * d`
```java
context.set("a", 2); context.set("b", 4); context.set("c", 8); context.set("d", 16);

AbstractExpression expr = new SumNonTerminalExpression(
    new MultiplyNonTerminalExpression(
        new NumberTerminalExpression("a"), new NumberTerminalExpression("b")),
    new MultiplyNonTerminalExpression(
        new NumberTerminalExpression("c"), new NumberTerminalExpression("d"))
);

int result = expr.interpret(context);   // (2*4) + (8*16) = 8 + 128 = 136
```
Note this composes recursively: the `SumNonTerminalExpression`'s `left` and `right` are themselves `MultiplyNonTerminalExpression`s, each of which in turn holds two `NumberTerminalExpression`s.

### 7. Generalizing further: one `BinaryExpression` class instead of one class per operator
Instead of creating a separate class for every operator (`MultiplyNonTerminalExpression`, `SumNonTerminalExpression`, a subtract one, etc.), you can generalize to a single class that also takes the operator itself as a parameter:
```java
class BinaryExpression implements AbstractExpression {
    private AbstractExpression left, right;
    private String operator;   // "+", "*", etc.

    public int interpret(Context context) {
        int l = left.interpret(context);
        int r = right.interpret(context);
        switch (operator) {
            case "+": return l + r;
            case "*": return l * r;
            default: return 0;
        }
    }
}
```
This reduces class explosion when there are many operators, at the cost of moving operator logic into a `switch` inside one class rather than one class per operator (a trade-off worth mentioning if asked).

## 🔥 Real Production Incident & Fix

**What broke:** A rules engine for calculating dynamic pricing (e.g., `basePrice * demandMultiplier + surgeFee`) originally hardcoded each pricing formula as a Java method with inline arithmetic, string-parsed from a config value using ad-hoc string splitting (`split("\\*")`, `split("\\+")`) rather than a real expression tree.

**How the team noticed:** A product manager added a slightly more complex formula, `basePrice * (demandMultiplier + loyaltyDiscount)`, which introduced parentheses for the first time. The naive string-splitting logic didn't understand operator precedence or grouping and silently computed `basePrice * demandMultiplier + loyaltyDiscount` instead (multiplying only the first term) — a completely different, and higher, price. This wasn't caught until a customer support escalation reported an incorrect charge, and root-cause investigation traced it to the mis-evaluated formula.

**Root cause:** The system was treating "expression evaluation" as ad-hoc string manipulation instead of modeling it properly as a tree of terminal and non-terminal expressions with a defined `interpret(context)` contract. There was no structural way to represent grouping/precedence, so more complex formulas silently produced wrong results rather than failing loudly.

**The fix:** The team introduced a proper Interpreter-based expression tree: terminal expressions for variables/literals, non-terminal expressions for each operator (with `left`/`right` sub-expressions), and a `Context` holding the runtime variable bindings — exactly as in this transcript. Parentheses/grouping were now handled naturally by the tree structure itself (a sub-expression *is* the "parenthesized group"), and each new formula was validated by unit-testing its expression tree's `interpret()` output against known values before deployment.

```
BEFORE: pricing formulas evaluated via fragile string        AFTER: formulas modeled as a real expression
splitting, no real precedence/grouping handling                tree; each node's interpret() is unit-testable

  "basePrice * (demand + loyalty)"                              Multiply(
     .split("*") -> naive, ignores parentheses                     Terminal("basePrice"),
     -> WRONG result silently computed                              Sum(Terminal("demand"), Terminal("loyalty"))
                                                                  ).interpret(context)  <- correct, testable
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: What's the precise difference between a terminal and a non-terminal expression?**
A: A **terminal expression** cannot be decomposed any further — it's a leaf node that resolves its value directly (typically by looking itself up in the context), like a single variable `a`. A **non-terminal expression** is composed of one or more sub-expressions (which may themselves be terminal or non-terminal) and resolves its value by recursively interpreting those children and combining the results, like `a * b`.

**Q2: How does the `Context` object fit into this pattern, and why is it passed on every `interpret()` call rather than stored once?**
A: The `Context` holds the runtime variable bindings (e.g., `a=2, b=4`) that give meaning to terminal expressions — the same expression tree (`a * b`) can be evaluated against completely different contexts to get different results. Passing it as a parameter to every `interpret()` call (rather than storing it inside the expression tree) keeps the expression tree itself reusable and stateless with respect to any one specific set of variable values.

**Q3: How would you extend this to support subtraction and a more complex expression like `a * b + c * d`?**
A: Add a new non-terminal expression class (e.g., `SumNonTerminalExpression`) implementing the same `AbstractExpression` interface, with its own `left`/`right` children and `interpret()` performing `left.interpret(ctx) + right.interpret(ctx)`. Because every node — terminal or non-terminal — implements the same interface, you can nest a `SumNonTerminalExpression` whose children are themselves `MultiplyNonTerminalExpression` instances, letting you build arbitrarily complex expression trees like `a*b + c*d`.

**Q4: What's the downside of creating a dedicated class per operator (Multiply, Sum, Subtract, ...) versus one generalized `BinaryExpression` class with a `switch` on operator type?**
A: One class per operator is more aligned with Open/Closed Principle (adding an operator means adding a class, not modifying existing code) but leads to class proliferation as operators grow. A single generalized class with an operator field and internal `switch` reduces class count but means adding a new operator requires modifying that shared class's `switch` statement — a direct trade-off between extensibility and simplicity, both explicitly shown as valid approaches in the transcript.

**Q5: When would you NOT want to use the Interpreter pattern for expression evaluation?**
A: For very complex grammars (full programming languages, complex query languages), hand-rolling an Interpreter-pattern class hierarchy becomes unwieldy — you'd typically reach for a proper parser generator/lexer-parser toolchain (e.g., ANTLR) instead. Interpreter is best suited to **small, well-bounded expression languages** (simple arithmetic, simple rule conditions) where the grammar is limited and stable.

**Q6: How does recursion naturally fall out of this design, and where exactly does it happen?**
A: Recursion happens inside a non-terminal expression's `interpret()` method: when it calls `left.interpret(context)`, `left` might itself be another non-terminal expression, whose `interpret()` will again call `interpret()` on *its* children, and so on until terminal expressions (the base case) are reached and return a direct value from the context. This mirrors classic tree-recursion, with terminal expressions acting as the recursion's base case.

## 🔑 Key Takeaway

When you need to evaluate expressions built from smaller sub-expressions against a runtime context, model each piece — terminal (a leaf value looked up from context) and non-terminal (a composition of sub-expressions) — as classes implementing a shared `interpret(context)` method, and let recursion through that shared interface do the evaluation naturally, however deep the expression tree grows.
