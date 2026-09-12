# Interview Guide: Memento Design Pattern (Snapshot / Undo)

## 🗣️ The Interview Scenario

> "We want to build an 'undo' feature for a configuration management system — whenever a configuration changes, we should be able to take a snapshot of its state and roll back to any previous snapshot later, without exposing the internal implementation details of the configuration object to the rest of the system. How would you design this?"

This question tests whether you can recognize **"I need history/undo of an object's state"** as the signature of the **Memento pattern**, and whether you understand its three-part structure and *why* it protects encapsulation.

## 🏗️ Architect's Explanation (For a New Developer)

Think of a video game's "save point" system. When you save your game, you don't hand the game engine's entire internal memory dump to some external save-file manager and let it poke around — the **game itself** decides exactly what needs to be written into the save file (your position, inventory, health) and packages it into an opaque save file. The **save-file manager** (like a folder of save slots) just stores a stack of these opaque save files; it doesn't know or care what's inside them. When you hit "load," you hand a save file back to the game, and only the game knows how to unpack it and restore itself.

That's the **Memento pattern**, a *behavioral* pattern used specifically for **storing an object's history** — whenever you need undo/rollback/snapshot functionality, this pattern should be your first thought (it's also known as the **Snapshot pattern** for exactly this reason). Its second big benefit: **it does not expose the object's internal implementation** to whoever is managing the history.

Three roles:
- **Originator** — the actual object whose state needs to be saved/restored (e.g., a `Configuration`).
- **Memento** — an object that holds a *snapshot* of the Originator's state (possibly a subset of fields, not all of them).
- **Caretaker** — manages the **list/history** of Mementos; it stores them and can hand the latest one back for an undo, but never looks inside them.

## 📊 Visualize It

**Class structure:**

```
      Originator                    Memento                      Caretaker
   ------------------          --------------------          -------------------
   - state (e.g. height,       - height                      - List<Memento> history
     width)                    - width
   + createMemento():          + getters                      + addMemento(Memento m)
       Memento                                                 + undo(): Memento
   + restoreMemento(Memento)

   Originator ──creates & reads──▶ Memento ◀──stores, without reading inside──── Caretaker
```

**Runtime undo sequence (from the transcript's configuration example):**

```
originator.state = (5, 10)
    │
    ▼ createMemento() ──► Memento{5,10} ──► caretaker.add(Memento{5,10})   [History: [ (5,10) ]]

originator.state = (7, 12)
    │
    ▼ createMemento() ──► Memento{7,12} ──► caretaker.add(Memento{7,12})   [History: [ (5,10), (7,12) ]]

originator.state = (9, 14)     <-- no snapshot taken for this change

caretaker.undo()  ──► pops last Memento{7,12} from history, returns it
    │
    ▼
originator.restoreMemento(Memento{7,12})
    │
    ▼
originator.state = (7, 12)     <-- restored, NOT back to (9,14) or (5,10)
```

## 🔧 Deep Dive: How It Actually Works

### 1. Originator — owns both the state and the save/restore logic
```java
class Configuration {   // the Originator
    private int height;
    private int width;

    void setHeight(int h) { height = h; }
    void setWidth(int w)  { width = w; }

    ConfigurationMemento createMemento() {
        return new ConfigurationMemento(height, width);   // Originator decides what to save
    }

    void restoreMemento(ConfigurationMemento m) {
        this.height = m.getHeight();
        this.width = m.getWidth();
    }
}
```
Key design point emphasized in the source: **the Originator alone decides what goes into the Memento.** Even if `Configuration` had 100 fields, `createMemento()` might choose to save only the fields it actually cares about restoring — the outside world only ever calls `createMemento()`/`restoreMemento()` and never needs to understand the object's internals. This is exactly what "does not expose the object's internal implementation" means in practice.

### 2. Memento — a plain data holder
```java
class ConfigurationMemento {
    private final int height;
    private final int width;

    ConfigurationMemento(int height, int width) {
        this.height = height;
        this.width = width;
    }
    int getHeight() { return height; }
    int getWidth()  { return width; }
}
```
The Memento can mirror the Originator's fields one-to-one (as in this simplified example) or, in a real system, hold only a **subset** of fields — whatever the Originator decides is necessary to reconstruct a prior state.

### 3. Caretaker — manages history, but never inspects the Memento's contents
```java
class Caretaker {
    private List<ConfigurationMemento> history = new ArrayList<>();

    void addMemento(ConfigurationMemento m) {
        history.add(m);
    }

    ConfigurationMemento undo() {
        ConfigurationMemento last = history.get(history.size() - 1);
        history.remove(history.size() - 1);   // pop the last snapshot
        return last;
    }
}
```

### 4. Client / driver code — wiring it together
```java
Configuration config = new Configuration();
Caretaker caretaker = new Caretaker();

config.setHeight(5); config.setWidth(10);
caretaker.addMemento(config.createMemento());      // snapshot #1: (5, 10)

config.setHeight(7); config.setWidth(12);
caretaker.addMemento(config.createMemento());      // snapshot #2: (7, 12)

config.setHeight(9); config.setWidth(14);          // state changes again, no snapshot taken

ConfigurationMemento last = caretaker.undo();       // pops snapshot #2: (7, 12)
config.restoreMemento(last);
// config now prints height=7, width=12 — NOT 9,14
```
This exact worked example — including the final printed values — is the trace given in the transcript and is a good one to reproduce verbatim if asked to whiteboard it.

## 🔥 Real Production Incident & Fix

**What broke:** A feature-flag/configuration service allowed engineers to tweak live rollout percentages and other config values through an admin panel. There was no undo mechanism — the "history" was just an append-only audit log table (config value + timestamp), and reverting meant an engineer manually re-typing old values from log entries.

**How the team noticed:** During an incident, an on-call engineer needed to instantly revert a bad config change (a rollout percentage set to 100% instead of 1%, causing a broken feature to hit all users). Reading the audit log and manually re-entering the previous JSON blob took over six minutes under pressure — directly extending the incident's user-facing impact window. Post-incident review flagged "mean time to rollback" as unacceptably high, specifically because there was no structured "restore to last snapshot" capability, just a human reading logs.

**Root cause:** The system conflated **audit logging** (a flat, append-only record for compliance/debugging) with **restorable state** (something a system can programmatically reconstruct from). There was no `Memento`-shaped object capturing "everything needed to fully restore state," and no `Caretaker`-shaped API to pop the last valid state and hand it back — engineers were manually doing the Originator's restore logic in their heads under time pressure.

**The fix:** The team introduced an explicit `ConfigSnapshot` (Memento) created automatically on every config change and stored in a `ConfigHistory` (Caretaker) service; the admin panel got a one-click "revert to previous" button that called `configService.restore(history.popLast())`. Mean time to rollback dropped from minutes to seconds because the restore logic (owned entirely by the Originator/config service) was now invoked programmatically instead of manually reconstructed from an audit log by a human.

```
BEFORE: flat audit log, human must manually             AFTER: Memento snapshot + Caretaker history,
reconstruct and re-type old config under pressure         one-click programmatic restore

  AuditLog: [ {t1, configJSON}, {t2, configJSON}, ... ]    ConfigHistory (Caretaker)
  Engineer reads log → manually retypes old values          .addSnapshot(configService.createMemento())
  into admin panel during a live incident (slow, error-     .undo() → returns last ConfigSnapshot
  prone)                                                    configService.restore(snapshot)  <- instant
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why does the Memento pattern preserve encapsulation better than just exposing the Originator's fields via public getters/setters?**
A: If the Caretaker (or any external code) had to read the Originator's fields directly to build a snapshot, it would need intimate knowledge of the Originator's internal structure, and any internal refactor of the Originator would break external snapshot-building code. Instead, `createMemento()`/`restoreMemento()` live **inside** the Originator, so only the Originator ever needs to know its own internal layout — the Caretaker just stores an opaque object.

**Q2: Does the Memento need to store every single field of the Originator?**
A: No — the Memento only needs to hold **whatever subset of state is required to reconstruct a valid prior state**. The Originator decides this when implementing `createMemento()`; it's common for large objects to snapshot only the fields relevant to undo, not their entire internal state (e.g., not caches or derived/computed fields).

**Q3: How would you support multiple levels of undo (not just one step back)?**
A: The Caretaker maintains a **list** of Mementos rather than a single reference; `undo()` pops the most recent entry off that list (as shown in the worked example, which supports undoing back through snapshot #2, then snapshot #1, and so on). For "redo" support, you'd additionally push undone Mementos onto a separate redo stack.

**Q4: What's the memory cost concern with Memento, and how would you mitigate it?**
A: Since every `createMemento()` call stores a full (or partial) copy of state, an unbounded history list can grow indefinitely and consume significant memory for large or frequently-changing objects. Mitigations include capping history size (e.g., keep only the last N snapshots), storing diffs/deltas instead of full copies, or evicting old snapshots on a TTL.

**Q5: How is Memento different from just serializing the object to JSON and storing that?**
A: Superficially similar (both capture state externally), but Memento is a *structured OOP pattern* with a clear separation of responsibility: the Originator alone controls what's captured and how it's restored, and the Caretaker is deliberately kept ignorant of the Memento's internal shape. A raw JSON blob stored by an external service doesn't enforce this separation — anything with access to the JSON can inspect and depend on its internal shape, defeating the encapsulation goal.

**Q6: Could Memento be combined with Command pattern for a full undo/redo system?**
A: Yes, and this is a common real-world pairing: Command encapsulates *the action that was performed* (useful for redo and for logging what happened), while Memento encapsulates *the state before/after* the action (useful for restoring exact prior values). Together they give you both "what happened" and "what to revert to."

## 🔑 Key Takeaway

Whenever an interview question mentions **undo, rollback, snapshot, or history of an object's state**, think Memento immediately: let the Originator alone decide what state to save and restore (protecting its encapsulation), and let a separate Caretaker manage the list of opaque snapshots without ever looking inside them.
