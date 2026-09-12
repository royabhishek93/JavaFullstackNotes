# ↩️ Undo/Redo Feature - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📘 Difficulty: Intermediate** — assumes you already know the core patterns; focuses on applying them to a real, moderately complex system.

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## **Design Pattern Used**: Command Pattern

**Interviewer**: "Design an Undo/Redo feature (like Ctrl+Z in a text editor)."

**You**: "Classic **Command Pattern** application! Core insight: **Every user action (type, delete, format) must be encapsulated as an object with both `execute()` AND `undo()` methods, stored in a history stack.**"

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                  UNDO/REDO ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │  COMMAND MANAGER  │
                    │   (Invoker)       │
                    │                  │
                    │  undoStack: Stack │
                    │  redoStack: Stack │
                    │                  │
                    │  executeCommand() │
                    │  undo()          │
                    │  redo()          │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │     Command        │  ◄── Interface
                    │   (interface)      │
                    │                    │
                    │  execute()          │
                    │  undo()            │
                    └─────────┬──────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │ InsertText   │  │ DeleteText   │  │ FormatText   │
    │  Command     │  │  Command     │  │  Command     │
    │              │  │              │  │              │
    │ execute():   │  │ execute():   │  │ execute():   │
    │  insert(pos, │  │  delete(pos, │  │  apply(style)│
    │   text)      │  │   text)      │  │              │
    │              │  │              │  │              │
    │ undo():      │  │ undo():      │  │ undo():      │
    │  delete(pos, │  │  insert(pos, │  │  apply(      │
    │   text)      │  │   text)      │  │   oldStyle)  │
    └──────────────┘  └──────────────┘  └──────────────┘

    STACK-BASED HISTORY:
    ┌─────────────────────────────────────────┐
    │ undoStack: [Cmd1, Cmd2, Cmd3] ← top      │
    │ redoStack: []                            │
    │                                           │
    │ User presses Ctrl+Z:                     │
    │  → Pop Cmd3, call cmd3.undo()            │
    │  → Push Cmd3 to redoStack                │
    │                                           │
    │ undoStack: [Cmd1, Cmd2]                  │
    │ redoStack: [Cmd3]                        │
    └─────────────────────────────────────────┘
```

---

## 2. API Design

```http
POST /api/v1/documents/{docId}/commands
Request: {"type": "INSERT_TEXT", "position": 10, "text": "Hello"}
Response: 200 OK
{"commandId": "cmd-1234", "canUndo": true, "canRedo": false}

---

POST /api/v1/documents/{docId}/undo
Response: 200 OK
{"undoneCommand": "INSERT_TEXT", "documentState": "<updated content>", "canUndo": true, "canRedo": true}

// Nothing to undo:
Response: 400 BAD_REQUEST
{"error": "NOTHING_TO_UNDO"}

---

POST /api/v1/documents/{docId}/redo
Response: 200 OK
{"redoneCommand": "INSERT_TEXT", "documentState": "<updated content>"}
```

---

## 3. ER Diagram & Database Design

```sql
-- For persistent undo history (e.g., across sessions)
CREATE TABLE command_history (
    command_id VARCHAR(50) PRIMARY KEY,
    document_id VARCHAR(50) NOT NULL,
    command_type VARCHAR(30) NOT NULL,
    command_data JSONB NOT NULL,  -- Serialized command state (position, text, etc.)
    sequence_number INT NOT NULL,  -- Order in history
    status VARCHAR(10) DEFAULT 'ACTIVE',  -- ACTIVE or UNDONE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (document_id) REFERENCES documents(document_id),
    INDEX idx_document_sequence (document_id, sequence_number)
);
```

**You**: "For most applications, undo/redo history is IN-MEMORY only (lost on app close - like most text editors). Persisting to DB (shown above) is only needed for collaborative/cloud editors where history must survive across sessions/devices."

---

## 4. Sequence Diagrams

```
User    CommandManager   InsertCommand   Document
  │            │                │             │
  │─type("Hello")▶│                │             │
  │            ├─new InsertCommand(pos=0,"Hello")│
  │            ├─execute()───────▶│             │
  │            │                ├─insert(0,"Hello")──▶│
  │            │                │             │  content = "Hello"
  │            ├─push(cmd) to undoStack        │
  │            ├─clear redoStack (new action invalidates redo!)
  │◀done───────│                │             │
  │            │                │             │
  │─Ctrl+Z─────▶│                │             │
  │            ├─pop() from undoStack──▶ cmd    │
  │            ├─cmd.undo()──────▶│             │
  │            │                ├─delete(0,5)─────▶│
  │            │                │             │  content = ""
  │            ├─push(cmd) to redoStack        │
  │◀undone─────│                │             │
```

**You**: "CRITICAL rule shown here: any NEW action after an undo **clears the redo stack**. You can't redo something if you've since done something new - that would create an inconsistent history branch."

---

## 5. Scenario-First Explanations

### **5.1 Why Command Pattern (Not Direct State Snapshots)?**

**You**: "Two approaches to undo/redo:

**Approach 1: Full State Snapshot (Memento Pattern)**:
```java
// Store ENTIRE document state before each change
class DocumentSnapshot {
    private String fullContent;  // Copy of ENTIRE document!
}

// For a 500-page document, EVERY keystroke snapshot = massive memory waste!
```

**Approach 2: Command Pattern (chosen)**:
```java
interface Command {
    void execute();
    void undo();
}

class InsertTextCommand implements Command {
    private Document document;
    private int position;
    private String text;
    
    InsertTextCommand(Document doc, int position, String text) {
        this.document = doc;
        this.position = position;
        this.text = text;
    }
    
    public void execute() {
        document.insertAt(position, text);
    }
    
    public void undo() {
        document.deleteAt(position, text.length());  // Inverse operation!
    }
}

class DeleteTextCommand implements Command {
    private Document document;
    private int position;
    private String deletedText;  // Store what was deleted, for undo
    
    public void execute() {
        this.deletedText = document.getTextAt(position, length);
        document.deleteAt(position, length);
    }
    
    public void undo() {
        document.insertAt(position, deletedText);  // Restore deleted text
    }
}

class CommandManager {
    private Deque<Command> undoStack = new ArrayDeque<>();
    private Deque<Command> redoStack = new ArrayDeque<>();
    
    void executeCommand(Command command) {
        command.execute();
        undoStack.push(command);
        redoStack.clear();  // Invalidate redo history on new action
    }
    
    void undo() {
        if (undoStack.isEmpty()) throw new IllegalStateException("Nothing to undo");
        Command command = undoStack.pop();
        command.undo();
        redoStack.push(command);
    }
    
    void redo() {
        if (redoStack.isEmpty()) throw new IllegalStateException("Nothing to redo");
        Command command = redoStack.pop();
        command.execute();
        undoStack.push(command);
    }
}
```

**Why Command Pattern wins**: Only stores the DELTA (what changed - position + text), not the entire document state. For a large document with thousands of edits, this is the difference between O(edits × document_size) memory (Memento) vs O(edits × avg_edit_size) memory (Command) - MASSIVE savings."

### **5.2 Why Composite Commands for Batch Operations?**

**You**: "What about 'Find & Replace All' - replacing 50 occurrences? Should be ONE undo, not 50!

```java
class MacroCommand implements Command {
    private List<Command> commands;
    
    MacroCommand(List<Command> commands) {
        this.commands = commands;
    }
    
    public void execute() {
        commands.forEach(Command::execute);
    }
    
    public void undo() {
        // CRITICAL: Undo in REVERSE order!
        for (int i = commands.size() - 1; i >= 0; i--) {
            commands.get(i).undo();
        }
    }
}

// Usage: Find & Replace All
List<Command> replaceCommands = new ArrayList<>();
for (Position pos : allOccurrences) {
    replaceCommands.add(new ReplaceTextCommand(document, pos, "old", "new"));
}
MacroCommand batchReplace = new MacroCommand(replaceCommands);
commandManager.executeCommand(batchReplace);  // ONE undo operation for all 50 replacements!
```

**Why reverse order for undo?** If Command A depends on state changed by Command B (e.g., inserting text shifts subsequent positions), undoing must happen in REVERSE order of execution to correctly restore original state - same principle as a stack (LIFO)."

---

## 6. Cross Questions

**Interviewer**: "How do you limit memory usage for very long edit histories?"

**You**: "Bounded stack with eviction:

```java
class CommandManager {
    private static final int MAX_HISTORY_SIZE = 100;
    private Deque<Command> undoStack = new ArrayDeque<>();
    
    void executeCommand(Command command) {
        command.execute();
        undoStack.push(command);
        
        if (undoStack.size() > MAX_HISTORY_SIZE) {
            undoStack.removeLast();  // Evict oldest command (bottom of stack)
        }
        redoStack.clear();
    }
}
```

Most editors (MS Word, VS Code) limit undo history to a fixed number of steps (e.g., last 100-1000 actions) rather than unlimited - trades off perfect history for bounded memory."

---

## 7. Trade-offs

### **Command Pattern vs Memento Pattern for Undo**

| Aspect | Command Pattern | Memento Pattern |
|--------|-------------------|--------------------|
| **Memory** | O(delta size) - efficient | O(full state) - expensive |
| **Complexity** | Requires inverse operation per command | Simple (just snapshot/restore) |
| **Best for** | Text editors, incremental changes | Small state objects, simple undo needs |

**You**: "Command Pattern requires more upfront design (each command needs a correct `undo()`), but pays off hugely for large mutable state like documents. Memento is simpler but only practical for small state objects (e.g., undo in a simple game with small state)."

---

## 8. Senior Trap Questions

### **Trap: "Just store previous document string before each edit!"**

**❌ Junior**: "Simple - keep array of document snapshots."

**✅ Senior**: "For a 10MB document with 1000 edits, that's potentially 10GB of memory (1000 × 10MB snapshots)! Command Pattern with delta-based undo/redo uses only the SIZE OF THE CHANGE, not the whole document - orders of magnitude more memory-efficient. This distinction is exactly what interviewers probe for - do you understand WHY Command Pattern is preferred over naive snapshotting for this specific use case?"

---

## 9. Technology Choices

**You**: "For collaborative undo/redo (Google Docs style) - this gets MUCH harder. Simple Command stack breaks down with concurrent multi-user edits. Production systems use **Operational Transformation (OT)** or **CRDTs (Conflict-free Replicated Data Types)** which handle undo in a distributed, conflict-tolerant way. Worth mentioning to show awareness of the added complexity in collaborative contexts."

---

## 🔥 Real-World Production Issue: The Undo Stack That Grew Without Bound and Crashed the App

*In plain English: an undo history with no size limit will eventually exhaust memory, even if each individual entry is small.*

**The war story:**

"A design tool's undo/redo used the Command Pattern's delta-based approach exactly as this guide recommends — memory-efficient per-command, in theory. But the `undoStack` itself (a `List<Command>`) had NO maximum size cap, on the assumption that 'deltas are small, users won't undo THAT many times in one session.'"

```
Power users doing iterative design work (hundreds of small tweaks
over a multi-hour session): 50,000+ commands pushed onto undoStack
over the course of a single long editing session

Each delta command: ~2KB (small individually, exactly as designed)
50,000 commands x 2KB = 100MB just for the undo history of ONE document

Browser tab (this was a web-based design tool) hit its memory limit,
tab crashed, ALL unsaved work lost -- including the very edits the
user was trying to protect by having undo/redo in the first place
```

**Root cause:** "delta storage is memory-efficient PER COMMAND" (true, and correctly implemented) doesn't mean the AGGREGATE undo history is bounded — an unbounded list of even small deltas grows linearly with session length, and a long enough session (or a scripted/automated series of many small edits) will eventually exhaust memory regardless of how small each individual delta is.

**The fix:** capped `undoStack` at a configurable maximum size (e.g., 500 commands), evicting the OLDEST commands first (FIFO) once the cap is reached — accepting that very old undo history becomes unavailable in exchange for a bounded, predictable memory footprint; also added periodic "checkpoint" full-snapshots every N commands so evicting old deltas doesn't leave the undo history in an inconsistent state if a very old snapshot is ever needed for recovery.

**Lesson for a new developer:** "Command Pattern's per-operation memory efficiency (deltas vs. full snapshots) solves ONE dimension of the memory problem, but doesn't automatically bound the OTHER dimension: how many commands can accumulate over an unbounded session length. Always cap unbounded collections (undo stacks, event logs, in-memory caches) with an explicit eviction policy, even when each individual entry is 'small'."

---

## 🎓 **Final Tips**

1. **Command Pattern**: Encapsulate execute() + undo() together
2. **Two stacks**: undoStack and redoStack, redo cleared on new action
3. **Delta storage, not full snapshots**: Memory efficiency is the KEY differentiator
4. **Composite/Macro commands**: Batch operations as single undo unit
5. **Reverse-order undo for composites**: LIFO semantics

Good luck! Undo/Redo tests your understanding of **Command Pattern** and memory-efficient state management. 🚀
