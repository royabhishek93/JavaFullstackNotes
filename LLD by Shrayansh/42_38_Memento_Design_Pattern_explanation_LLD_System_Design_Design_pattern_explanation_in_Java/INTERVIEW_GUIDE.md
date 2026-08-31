# 📸 Memento Design Pattern - Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

**Interviewer**: "Explain the Memento Design Pattern."

**You**: "Memento captures and externalizes an object's **internal state so it can be restored later, WITHOUT violating encapsulation** (i.e., without exposing the object's private fields directly to whoever needs to save/restore that state)."

---

## 1. Architecture Diagram

```
┌──────────────┐         creates          ┌──────────────┐
│  Originator    │─────────────────────────▶│   Memento      │
│                │                          │  (immutable    │
│  state         │                          │   snapshot)    │
│  createMemento()│                         │                │
│  restore(memento)│◄─────restores from────│  getState()    │
└──────────────┘                          │  (package-private│
                                            │   or private!)   │
                                            └───────┬──────┘
                                                    │ stored by
                                                    ▼
                                            ┌──────────────┐
                                            │  Caretaker     │
                                            │                │
                                            │ history: Stack │  ◄── Does NOT peek inside Memento!
                                            │  <Memento>     │      Just stores/retrieves opaquely
                                            └──────────────┘
```

## 2. Code Example - Text Editor Undo

```java
// Memento - encapsulates snapshot, exposes state ONLY to Originator
class TextMemento {
    private final String content;  // package-private access, or use nested class trick
    
    TextMemento(String content) {
        this.content = content;
    }
    
    private String getContent() {  // PRIVATE - only Originator (same file/nested class) can access!
        return content;
    }
}

// Originator - the object whose state we're snapshotting
class TextEditor {
    private String content = "";
    
    void type(String text) {
        content += text;
    }
    
    TextMemento save() {
        return new TextMemento(content);  // Create snapshot
    }
    
    void restore(TextMemento memento) {
        this.content = memento.getContent();  // Only TextEditor can call this private method
                                               // (if TextMemento is a nested class of TextEditor)
    }
    
    String getContent() { return content; }
}

// Caretaker - manages history, but NEVER looks inside Memento (opaque to it!)
class History {
    private Deque<TextMemento> mementos = new ArrayDeque<>();
    
    void push(TextMemento memento) {
        mementos.push(memento);
    }
    
    TextMemento pop() {
        return mementos.pop();
    }
}

// Usage
TextEditor editor = new TextEditor();
History history = new History();

editor.type("Hello");
history.push(editor.save());  // Snapshot 1: "Hello"

editor.type(" World");
history.push(editor.save());  // Snapshot 2: "Hello World"

editor.restore(history.pop());  // Back to "Hello World" (well, pops most recent)
// To actually undo, need to pop the PREVIOUS snapshot's before-state - typical stack-based undo logic
```

---

## 3. Scenario-First Explanations

### **Why Memento Instead of Just Exposing Getters/Setters for All Fields?**

**You**: "Without Memento, to implement undo you might expose `getContent()`/`setContent()` publicly, and have the `History` class directly store raw `String` snapshots:

```java
// ❌ Works, but couples History to TextEditor's internal representation
class History {
    Stack<String> snapshots;  // Directly stores TextEditor's internal state type!
}
```

This seems fine for a SIMPLE `String` state, but for COMPLEX objects with many fields, you'd need to expose EVERY field via public getters/setters, breaking encapsulation. Worse, if `TextEditor`'s internal representation later changes (e.g., switches from `String` to a `Rope` data structure for better performance with huge documents), the `History`/`Caretaker` code breaks too since it directly stored the OLD representation type.

Memento Pattern keeps the STATE STRUCTURE ENCAPSULATED - the `Caretaker` (History) just holds an OPAQUE `Memento` object it can't peek inside. Only the `Originator` (TextEditor) knows how to extract/restore from its own Mementos, often via `private` access on a NESTED class (a common Java idiom for enforcing this)."

---

## 4. Cross Questions

**Interviewer**: "How is Memento different from just serializing the object (e.g., to JSON) for snapshots?"

**You**: "Serialization (JSON/binary) is a VALID and common IMPLEMENTATION technique for Memento in practice, but the PATTERN itself is about the STRUCTURAL RELATIONSHIP: Originator creates opaque snapshots, Caretaker stores them without understanding their contents, and ONLY the Originator can meaningfully restore from them. Whether the actual snapshot mechanism uses a private inner class, JSON serialization, or a binary blob is an IMPLEMENTATION DETAIL. The key architectural principle Memento captures is: **'state capture/restore without violating encapsulation and without coupling the history-management code to the internal representation.'**"

---

## 5. Trade-offs

| Aspect | Memento Pattern | Direct Field Exposure |
|--------|-------------------|------------------------------|
| **Encapsulation** | Preserved (opaque snapshots) | Broken (all fields public) |
| **Memory** | Can be expensive for large state (full snapshots) | Same concern applies |
| **Coupling** | Caretaker decoupled from Originator internals | Tightly coupled |

**You**: "Memory is a REAL concern - if `TextEditor`'s content is 500MB, storing FULL snapshots for every keystroke is wasteful (this is why, in practice for text editors, COMMAND PATTERN with delta-based undo is often preferred over full-state Memento for large mutable documents - see the Undo/Redo guide for that comparison)."

---

## 6. Senior Trap Questions

### **Trap: "Memento and Command Pattern seem to solve the same undo problem - aren't they redundant?"**

**✅ Senior**: "They solve undo via DIFFERENT MECHANISMS with different trade-offs:
- **Memento**: Stores FULL STATE SNAPSHOTS before/after changes. Simple conceptually, but memory-expensive for large state.
- **Command**: Stores the OPERATION (delta) plus enough info to REVERSE it (e.g., 'inserted text X at position Y' → undo is 'delete text at position Y, length=X.length()'). Memory-efficient for large mutable state, but requires implementing a correct inverse operation for EVERY command type.

**When to use which**: Memento for SMALL, simple state objects where full snapshots are cheap (e.g., a small game's state, a form's field values). Command for LARGE, complex mutable objects (text editors, graphics editors) where storing full snapshots at every step would be memory-prohibitive.

They're COMPLEMENTARY patterns for the same PROBLEM DOMAIN (undo/history), chosen based on the SIZE and MUTATION PATTERN of the state being tracked."

---

## 7. Technology Choices

**You**: "**Java Serialization** (`Serializable` interface) combined with a version history table is often used to implement Memento for PERSISTENT undo across sessions. **Redux (JavaScript)** state management, despite not being OOP, uses a similar 'time-travel debugging' concept based on storing STATE SNAPSHOTS - conceptually related to Memento's ideas applied at an application-architecture level."

---

## 🎓 Final Tips
1. **Memento preserves encapsulation** while enabling state snapshot/restore
2. **Three roles**: Originator (creates/restores), Memento (opaque snapshot), Caretaker (stores history, doesn't peek inside)
3. **Complementary to Command Pattern**: Memento = full snapshots (simple, memory-heavy), Command = deltas (efficient, more design work)
4. **Real-world**: Game save states, form draft auto-save, simple undo systems

Good luck! 🚀
