# Interview Guide: Logging System (Chain of Responsibility Design Pattern)

## 🗣️ The Interview Scenario

> "Design a logging framework that supports multiple log levels — INFO, DEBUG, ERROR — where a log call written at any level should be correctly routed to the handler responsible for that level, without the calling code needing to know which specific handler will process it. Also, tell me what design pattern this maps to, and give me one more real-world example of where you'd reach for that same pattern."

Interviewers use "design a logger" and "design an ATM cash dispenser" almost interchangeably as a *proxy* question for "do you know the Chain of Responsibility pattern and can you recognize when it applies?" The tell-tale signal in the phrasing is always some version of: *"the sender doesn't need to know who exactly will handle the request."* Recognizing that phrase — and immediately naming Chain of Responsibility — is exactly the shortcut this transcript teaches.

## 🏗️ Architect's Explanation (For a New Developer)

Imagine you're at a company help desk with a request, but you don't know which department handles it. So you hand your request to the first person you see. If they can't help, instead of you having to figure out who to ask next, *they* pass your request along to the next person in line, who checks if *they* can help, and so on — until someone in the chain handles it (or nobody can, and it falls off the end).

That's the **Chain of Responsibility** pattern in one sentence: **a sender hands off a request, and a linked chain of receiver objects each get a chance to handle it — whoever can handle it does, and the sender never needs to know in advance who that will be.**

The concrete mechanical trick that makes this work in code: every handler in the chain holds a reference to "the next handler" (`nextProcessor`/`nextLogProcessor`). When a handler receives a request it *cannot* satisfy, it doesn't throw an error or return "not handled" to the caller — it silently forwards the request to its own `next` reference. The caller only ever talks to the *first* handler in the chain and is completely unaware of how many handlers exist or which one eventually processes the request.

## 📊 Visualize It

Generic Chain of Responsibility structure:

```
  Client -----> Receiver1 --(can't handle? forward)--> Receiver2 --(can't handle? forward)--> Receiver3 --> ... --> ReceiverN
                   |                                       |                                       |
                   v (if handled)                          v (if handled)                          v (if handled)
              [ Response ]                             [ Response ]                             [ Response ]
```

ATM cash-dispenser walkthrough (the transcript's motivating example before logging):

```
  Client requests: withdraw ₹2020
        |
        v
  ₹2000-note Handler:  can I dispense using only ₹2000 notes? -- No (2020 isn't a clean multiple)
        |  forward remaining amount
        v
  ₹500-note Handler:   can I dispense ₹500 notes for what's left? -- dispenses what it can, forwards remainder
        |  forward remaining amount
        v
  ₹100-note Handler:   can I dispense ₹100 notes for what's left? -- dispenses, forwards remainder
        |
        v
  (no more handlers) --> if remainder != 0: "Insufficient amount / cannot dispense exact change"
```

Log-level chain (the concrete implementation from the transcript):

```
  client.log(Level.ERROR, "message")
        |
        v
  InfoLogProcessor (level=INFO)
        |   log.level != INFO --> forward to next
        v
  DebugLogProcessor (level=DEBUG)
        |   log.level != DEBUG --> forward to next
        v
  ErrorLogProcessor (level=ERROR)
        |   log.level == ERROR --> HANDLE IT (print/write the message), do NOT forward further
        v
      (end of chain, next = null)
```

## 🔧 Deep Dive: How It Actually Works

### The abstract handler — holding the "next" link

```java
abstract class LogProcessor {
    LogProcessor nextLogProcessor;

    LogProcessor(LogProcessor nextLogProcessor) {
        this.nextLogProcessor = nextLogProcessor;
    }

    void log(int level, String message) {
        if (nextLogProcessor != null) {
            nextLogProcessor.log(level, message);   // pass-through when this node can't handle it
        }
    }
}
```

Every concrete processor **extends** `LogProcessor` and, when its own constructor runs, is handed a reference to the *next* processor in the chain — that reference gets assigned to the parent's `nextLogProcessor` field via `super(next)`.

### The three concrete levels

```java
class InfoLogProcessor extends LogProcessor {
    InfoLogProcessor(LogProcessor nextLogProcessor) { super(nextLogProcessor); }

    @Override
    void log(int level, String message) {
        if (level == LogLevel.INFO) {
            System.out.println("INFO: " + message);
        } else {
            super.log(level, message);   // can't handle it — delegate to whatever comes next
        }
    }
}

class DebugLogProcessor extends LogProcessor {
    DebugLogProcessor(LogProcessor nextLogProcessor) { super(nextLogProcessor); }

    @Override
    void log(int level, String message) {
        if (level == LogLevel.DEBUG) {
            System.out.println("DEBUG: " + message);
        } else {
            super.log(level, message);
        }
    }
}

class ErrorLogProcessor extends LogProcessor {
    ErrorLogProcessor(LogProcessor nextLogProcessor) { super(nextLogProcessor); }

    @Override
    void log(int level, String message) {
        if (level == LogLevel.ERROR) {
            System.out.println("ERROR: " + message);
        } else {
            super.log(level, message);
        }
    }
}
```

Notice the pattern precisely: each concrete class checks **only** whether it personally can handle the level. If yes, it processes and stops (it never calls `super.log()` in that branch — the chain terminates there). If no, it calls `super.log(level, message)`, which is the *parent's* generic forwarding logic — and the parent forwards to whatever `nextLogProcessor` was wired in at construction time.

### Building the chain (this is the part most candidates fumble)

```java
public static void main(String[] args) {
    LogProcessor errorLogger = new ErrorLogProcessor(null);              // last in chain — next = null
    LogProcessor debugLogger = new DebugLogProcessor(errorLogger);       // debug's next = error
    LogProcessor logChain    = new InfoLogProcessor(debugLogger);        // info's next = debug

    logChain.log(LogLevel.ERROR, "Something went wrong!");
    // walks: Info (not INFO, forward) -> Debug (not DEBUG, forward) -> Error (matches, handled, printed)
}
```

The construction order is built **backwards** — you build the *last* handler first (with `null` as its next), then wrap each preceding handler around it, and finally hold onto only the *first* handler (`logChain`) as your public entry point. The client only ever calls `.log()` on that first reference and has zero knowledge of `DebugLogProcessor` or `ErrorLogProcessor` existing.

### Why this is exactly "Chain of Responsibility" and not just polymorphism

The distinguishing feature isn't "one method has different behavior in each subclass" (that alone is just standard OOP polymorphism) — it's that **each object explicitly forwards the request to another object of the same abstract type when it opts out of handling it**, forming a literal linked-list-like chain of *decision points*, not just a type hierarchy of *behaviors*. The sender is decoupled from ever needing to enumerate "who might handle this."

### Recognizing it in interview questions — the trigger phrases

The transcript explicitly lists the phrases that should make Chain of Responsibility "light up" in your head:
- **"Design an ATM"** (or any cash/currency dispenser) — denomination handlers (₹2000 → ₹500 → ₹100 → ...) each try to fulfill part of the withdrawal amount and forward the remainder.
- **"Design a vending machine"** — could similarly chain handlers for different coin/note denominations or product dispensing steps.
- **"Design a logging system"** — exactly the example built above; log level is the routing key.
- More broadly: **any time a request needs to be handled by "whoever is capable," and the sender shouldn't need to know who that is in advance.**

## 🔥 Real Production Incident & Fix

**What broke**: A backend team implemented request-validation for an internal API gateway as one giant `validateRequest()` method containing a long sequence of `if/else` checks — auth-token validation, rate-limit validation, payload-schema validation, business-rule validation — all inlined in a single function, executed top to bottom regardless of which check actually applied to a given endpoint. As more endpoints were added, engineers kept adding new `else if` branches for endpoint-specific validation rules directly into this one function, because there was no structural mechanism for "only some checks apply to some requests, and the set of applicable checks needs to be composable per endpoint."

**How the team noticed**: A production incident occurred when a new "bulk export" endpoint was added — it needed a special payload-size validation step that had to run *before* schema validation (large exports were legitimately schema-valid but needed a separate quota check first). A developer inserted the new check in the wrong position within the giant `if/else` chain, causing the size-limit check to run *after* an expensive schema deserialization step instead of before it. The bug wasn't caught by tests (the giant function had poor test isolation — you couldn't test one validation step without setting up conditions for every check before it), and it surfaced in production only when a malicious client sent oversized payloads that passed the (correctly-ordered-for-normal-endpoints but wrongly-ordered-for-this-one) chain, causing repeated OOM-driven pod restarts — caught via a spike in Kubernetes `OOMKilled` events in the cluster's metrics dashboard.

**Root cause**: Validation logic was structured as one monolithic conditional block instead of independent, composable handler units. There was no way to express "for this specific endpoint, the ordering of checks should be different" without editing shared code that every other endpoint also depended on — a direct violation of the Open/Closed Principle, and exactly the kind of problem Chain of Responsibility exists to solve.

**The fix**: The team refactored validation into a `Validator` abstract class mirroring `LogProcessor` exactly — `AuthValidator`, `RateLimitValidator`, `PayloadSizeValidator`, `SchemaValidator`, each with a `next` reference, each deciding independently whether it applies and either short-circuiting (reject the request) or forwarding to the next validator. Each endpoint could now assemble its *own* chain in whatever order it needed (the bulk-export endpoint simply constructed its chain with `PayloadSizeValidator` wired before `SchemaValidator`), and each validator became independently unit-testable in isolation, the same way `InfoLogProcessor`/`DebugLogProcessor`/`ErrorLogProcessor` can be tested one at a time.

```
BEFORE: one giant if/else, shared, hard to reorder per-endpoint    AFTER: composable chain per endpoint

 validateRequest(req) {                                             AuthValidator -> RateLimitValidator ->
   if (!authOk) reject;                                             PayloadSizeValidator -> SchemaValidator
   if (!rateLimitOk) reject;                                             (bulk-export endpoint's chain,
   if (!schemaOk) reject;       <-- wrong order for one endpoint           size-check placed BEFORE schema)
   if (endpoint == "bulkExport" && payloadTooBig) reject; // bolted on
 }
```

## ❓ Likely Interview Follow-Up Questions & Answers

1. **"How is Chain of Responsibility different from just using a `switch` statement or a simple Factory to route the request to the right handler?"**
   A `switch`/Factory requires the *dispatcher* to know, upfront, the full set of possible handlers and the exact condition that selects each one — it's a single decision point. Chain of Responsibility instead distributes the decision across a *sequence* of independent objects, each of which only needs to know "can I handle this?" and "who's next?" — no single object needs global knowledge of the whole routing table, which matters when the set of handlers or their order needs to vary per call site (as in the incident above).

2. **"What happens if no handler in the chain can process the request? How do you avoid silent failures?"**
   The chain must terminate at some point (the last handler's `next` is `null`), and that terminal point should explicitly signal "unhandled" — either by throwing an exception, returning a sentinel/failure value, or logging a warning — rather than silently doing nothing. In the ATM example, if the full amount can't be exactly dispensed by any denomination combination, the last handler (or a dedicated fallback) must return "insufficient/invalid amount" rather than quietly returning less cash than requested.

3. **"In the logging example, why does each `log()` override call `super.log(...)` in the fallback branch, instead of calling `this.nextLogProcessor.log(...)` directly?"**
   Because the base class `LogProcessor` already implements the generic "forward to next" logic once — calling `super.log()` reuses that single implementation instead of duplicating `if (nextLogProcessor != null) nextLogProcessor.log(...)` inside every concrete subclass. It's a small but deliberate DRY choice: the "how do I forward" logic lives in exactly one place.

4. **"How would you change this design if a single log message needed to be handled by *multiple* processors instead of stopping at the first match (e.g., every ERROR log should also be captured by an audit processor)?"**
   You'd change the semantics from "stop at first match" to "let matching handlers process AND still forward" — i.e., remove the implicit early-return behavior and instead have every handler both act (if applicable) and unconditionally call `next` regardless of whether it handled the message. This is a legitimate variant of the pattern sometimes called a "pipeline" rather than strict Chain of Responsibility, and it's worth explicitly naming the distinction to show you understand the pattern's flexibility.

5. **"Is Chain of Responsibility related to the Decorator pattern? They both seem to involve wrapping objects."**
   They share the mechanical shape (each object holds a reference to another object of the same type and delegates), but the *intent* differs: Decorator's goal is to **add behavior/responsibility** to every object in the chain (all of them execute, each adding something), while Chain of Responsibility's goal is **routing** — only the handler that can process the request actually acts, and it's about *finding the right owner*, not stacking behavior.

6. **"How would you make the chain configurable at runtime (e.g., read handler order from config) instead of hardcoding it in `main`?"**
   Build the chain by iterating over a list of handler factories/classes read from configuration, constructing them in reverse order (last configured handler gets `next = null`, then wrap backwards) exactly as done manually in the transcript's `main` method — the wiring logic itself doesn't change, only *where the list of handlers comes from* (config file/DB vs. hardcoded).

## 🔑 Key Takeaway

Chain of Responsibility decouples "who sends a request" from "who handles it" by giving each handler a reference to the next handler and letting each one decide independently whether to act or forward — recognize it instantly whenever a question implies "the sender shouldn't need to know who will end up handling this."
