# Interview Guide: Command Design Pattern (Undo/Redo Feature)

## 🗣️ The Interview Scenario

> "Design the remote-control software for a smart home system that controls an air conditioner and other devices. The client should be able to press a button to turn the AC on/off and set its temperature — but here's the twist: the system must also support **undo** for the last N operations, and it must be easy to add new devices (like a smart bulb) later without bloating the client code or coupling it to every device's internal API. How would you design this so undo/redo just works, and the client never needs to know *how* a device performs its operations?"

This question is a favorite for testing whether a candidate reaches for the **Command pattern** specifically because of the **undo/redo requirement** — a very common, very telling interview signal — and whether they understand *where* the undo history should live (hint: not on the device itself).

## 🏗️ Architect's Explanation (For a New Developer)

Think about a **TV remote control**. You (the client) never need to know the internal circuitry of the TV — you just press "Volume Up." The remote is what translates your button press into a specific instruction the TV understands. Now imagine you also want an "undo" button — pressing it should reverse whatever the *last* button did, without you having to remember what you pressed.

The **Command pattern** formalizes this real-world remote-control mental model into four roles:
- **Receiver**: the actual device that does real work (e.g., `AirConditioner` — knows how to turn itself on/off).
- **Command**: a small object that wraps *one specific instruction* to a receiver (e.g., "TurnACOnCommand") and exposes `execute()` (and, for undo support, `undo()`).
- **Invoker**: the thing that *triggers* commands (e.g., the `RemoteControl`) — it holds a reference to whichever command is currently "loaded" and calls `execute()` when a button is pressed, without knowing what that command actually does internally.
- **Client**: sets up which command is assigned to which button, then simply "presses buttons" — completely decoupled from the receiver's internal API.

Undo becomes almost free once you have this structure: the invoker just keeps a **stack of executed commands**, and "undo" pops the last command off the stack and calls *its* `undo()` method. The receiver (AC) never has to know anything about undo — it's a "dumb object" that just responds to whatever method is called on it.

## 📊 Visualize It

**Class structure:**
```
   Client
     │ configures
     ▼
┌─────────────────┐        holds        ┌────────────────────┐
│  RemoteControl   │────────────────────►│   <<interface>>      │
│  (Invoker)       │                     │      ICommand         │
├─────────────────┤                     │  +execute()           │
│ -command         │                     │  +undo()              │
│ -commandHistory  │                     └──────────┬────────────┘
│    : Stack<ICmd> │                                │ implements
│ +setCommand(cmd) │                    ┌────────────┴─────────────┐
│ +pressButton()   │              TurnACOnCommand           TurnACOffCommand
│ +undo()          │              -receiver: AirConditioner  -receiver: AirConditioner
└─────────────────┘              +execute()→ac.turnOn()      +execute()→ac.turnOff()
                                  +undo()   → ac.turnOff()    +undo()   → ac.turnOn()
                                             │                            │
                                             └──────────┬─────────────────┘
                                                         ▼
                                              ┌────────────────────┐
                                              │  AirConditioner      │  (Receiver)
                                              ├────────────────────┤
                                              │ -isOn: boolean       │
                                              │ -temperature: int    │
                                              │ +turnOn()/turnOff()  │
                                              │ +setTemperature(t)   │
                                              └────────────────────┘
```

**Runtime sequence — execute then undo:**
```
Client:  remote.setCommand(new TurnACOnCommand(ac))
Client:  remote.pressButton()
              │
              ├─► command.execute()        → ac.turnOn()   [AC is now ON]
              └─► commandHistory.push(command)

Client:  remote.undo()
              │
              ├─► cmd = commandHistory.pop()   → gets TurnACOnCommand
              └─► cmd.undo()                   → ac.turnOff()   [AC reverted to OFF]
```

## 🔧 Deep Dive: How It Actually Works

### The problem with the "naive" design (no Command pattern)
The transcript starts with a simple `AirConditioner` class with `turnOnAC()`, `turnOffAC()`, and `setTemperature()`, called *directly* by client code:
```java
AirConditioner ac = new AirConditioner();
ac.turnOnAC();
ac.setTemperature(22);
ac.turnOffAC();
```
Three concrete problems are called out:
1. **Lack of abstraction** — if turning on the AC someday requires a *sequence* of internal steps (not just one method call), the client would need to know and call all those steps directly, and any change to that sequence breaks every call site.
2. **No way to implement undo/redo** — there's no natural place to record "what was done" so it can be reversed; forcing the *client* to track command history and manually call the opposite operation is fragile and puts business logic in the wrong layer.
3. **Difficulty in code maintenance** — adding a new device (e.g., `Bulb` with `turnOnBulb()`/`turnOffBulb()`) means the client must directly learn and call that device's new API too, making the client increasingly bulky and tightly coupled to every device it controls.

### The Command pattern's four-part decomposition
```java
// 1. Receiver — the real device, knows nothing about commands or undo
class AirConditioner {
    private boolean isOn;
    private int temperature;
    void turnOnAC()  { isOn = true; }
    void turnOffAC() { isOn = false; }
    void setTemperature(int t) { temperature = t; }
}

// 2. Command — one command object per distinct operation
interface ICommand {
    void execute();
    void undo();
}
class TurnACOnCommand implements ICommand {
    private final AirConditioner ac;
    TurnACOnCommand(AirConditioner ac) { this.ac = ac; }
    public void execute() { ac.turnOnAC(); }
    public void undo()    { ac.turnOffAC(); }     // the OPPOSITE operation
}
class TurnACOffCommand implements ICommand {
    private final AirConditioner ac;
    TurnACOffCommand(AirConditioner ac) { this.ac = ac; }
    public void execute() { ac.turnOffAC(); }
    public void undo()    { ac.turnOnAC(); }
}

// 3. Invoker — the remote control, holds current command + a history stack
class RemoteControl {
    private ICommand command;
    private Stack<ICommand> commandHistory = new Stack<>();

    void setCommand(ICommand command) { this.command = command; }
    void pressButton() {
        command.execute();
        commandHistory.push(command);           // record for undo
    }
    void undo() {
        if (!commandHistory.isEmpty()) {
            ICommand last = commandHistory.pop();
            last.undo();
        }
    }
}

// 4. Client — knows nothing about AirConditioner's internal API
AirConditioner ac = new AirConditioner();
RemoteControl remote = new RemoteControl();
remote.setCommand(new TurnACOnCommand(ac));
remote.pressButton();       // AC turns on, command pushed to history
remote.undo();              // pops TurnACOnCommand, calls its undo() → AC turns off
```

### Why each of the three original problems is solved
- **Abstraction restored**: the client only ever calls `pressButton()` — it has zero knowledge of how many internal steps `turnOnAC()` actually requires. If that logic changes, only the `AirConditioner` (receiver) or the specific `Command` class changes.
- **Undo/redo becomes structural, not ad hoc**: the transcript's key insight is that the invoker maintains a **stack of executed commands**, and each concrete command class implements its own `undo()` as the semantic opposite of `execute()` — the receiver (`AirConditioner`) is described explicitly as a "dumb object" that has no idea undo even exists.
- **Maintainability for new devices**: adding a `Bulb` receiver with `TurnBulbOnCommand`/`TurnBulbOffCommand` requires *zero* changes to `RemoteControl` or the client's `pressButton()` logic — you only add new Command classes.

### The TV channel analogy for redo/back
The transcript draws a parallel to TV remote "back" behavior (switch to channel 54, press "back," return to channel 43) as an intuitive way to describe what popping the command stack and calling `undo()` accomplishes — a good analogy to reuse verbally in an interview.

## 🔥 Real Production Incident & Fix

**What broke:** A collaborative diagramming tool (think a simplified Figma-style canvas editor) implemented undo by having the *client-side editor component* directly track "what changed" (e.g., diffing shape positions before/after each drag) and manually reversing that diff on undo, instead of using discrete Command objects with their own `undo()` logic. When the team added a new "batch resize" feature (resizing 20 selected shapes at once), the ad hoc diff-based undo only correctly reverted *some* shapes, because the diffing logic had been written and tested only against single-shape moves.

**How the team noticed:** A user bug report said "I resized 20 shapes and hit undo, and only 3 of them went back to their original size" — QA reproduced it consistently, and a targeted unit test on the undo stack showed the recorded "diff" for a batch operation was silently truncated to the last shape processed in the loop, because the ad hoc diff-tracking code overwrote a single shared "last change" variable instead of recording one command per shape.

**Root cause:** There was no proper Command abstraction — undo logic was reverse-engineered from observed state diffs rather than being explicitly encoded per-operation, so any new multi-object operation exposed gaps the original diffing code never anticipated. This is precisely the "who owns undo logic" problem the transcript warns about: the client (or a generic diff engine) should never own undo — the operation itself should.

**The fix:** The team refactored to a proper Command-pattern implementation: every user action (move, resize, batch-resize, delete) became its own Command object implementing `execute()`/`undo()`, and a `BatchCommand` (composite of multiple commands) was introduced specifically for multi-shape operations, pushing *one* `BatchCommand` onto the history stack that internally calls `undo()` on each of its N child commands in reverse order. Undo correctness for batch operations went from "broken for >1 shape" to 100% reliable, verified by property-based tests that execute random operation sequences and assert full state restoration after full undo.

```
BEFORE (ad hoc diff tracking):                AFTER (Command pattern + Composite):
resize 20 shapes in a loop                    resize 20 shapes in a loop
  → overwrites one shared "lastDiff" var        → creates 20 ResizeCommand objects
  → undo only reverts the last shape              → wraps them in ONE BatchCommand
                                                    → push BatchCommand to history
                                                 undo() → BatchCommand.undo()
                                                          → calls undo() on all 20,
                                                            in reverse order
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Where exactly does the undo history live, and why does it matter that it's there and not on the receiver?**
The undo history (a stack of executed commands) lives on the **Invoker** (`RemoteControl`), not the **Receiver** (`AirConditioner`). This matters because the receiver should remain a simple, reusable, single-responsibility object that just performs operations when told — it shouldn't need to know about command sequencing, undo semantics, or which "button" triggered it. Keeping history on the invoker also means multiple invokers could share one receiver with independent undo histories if needed.

**Q2: How would you implement "redo" in addition to "undo"?**
Maintain a second stack (a "redo stack"). When `undo()` pops a command from the history stack and calls its `undo()`, push that same command onto the redo stack. When `redo()` is called, pop from the redo stack and call `execute()` again, then push it back onto the history stack. Any *new* command executed after an undo should clear the redo stack (standard editor behavior — you can't redo into a "future" that's been overwritten).

**Q3: What if a command's `undo()` isn't a perfect inverse — e.g., "delete a row" where the row's exact original data must be restored?**
The command object itself must capture enough state at execution time to reverse itself precisely — e.g., a `DeleteRowCommand` should store a copy of the deleted row's data *before* deleting it, so `undo()` can re-insert that exact data rather than trying to reconstruct it from nothing. This is a very common follow-up: undo commands often need to carry a memento (snapshot) of prior state, not just "the opposite method name."

**Q4: How does the Command pattern relate to the Memento pattern, and would you ever combine them?**
Command encapsulates *an operation* (what to do / how to undo it); Memento encapsulates *a snapshot of state* (what things looked like at some point). They're frequently combined: a Command's `undo()` implementation can internally use a Memento object to restore prior state precisely, especially when the "inverse operation" isn't a simple opposite method call (e.g., undoing a bulk edit).

**Q5: Why is this pattern specifically well-suited to "undo/redo" interview questions, versus, say, using a simple stack of state snapshots?**
Snapshotting entire state before every operation is memory-heavy and doesn't scale for large documents/objects. The Command pattern instead stores just the *intent* of each operation (small, cheap objects) and relies on each command knowing how to reverse only its own specific effect — far more memory-efficient and the natural OOP way to express "reversible actions" as first-class objects.

**Q6: How would you make this thread-safe if multiple threads could press buttons or trigger undo concurrently?**
The shared mutable state — the command stack (and the receiver's own state) — needs synchronization or a concurrent data structure (e.g., wrapping stack operations in synchronized blocks, or using a `ConcurrentLinkedDeque` with careful ordering guarantees), since interleaved `pressButton()`/`undo()` calls from different threads could otherwise corrupt history ordering or cause lost updates on the receiver's state.

## 🔑 Key Takeaway
The Command pattern turns "an operation" into a first-class object with `execute()`/`undo()`, decoupling the invoker (who triggers it) from the receiver (who performs it) — and undo/redo becomes almost trivial once you realize the invoker just needs a stack of these command objects, not any undo logic of its own.
