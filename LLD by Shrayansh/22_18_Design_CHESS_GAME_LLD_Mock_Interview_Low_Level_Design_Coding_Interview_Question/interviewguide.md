# Interview Guide: Chess Game LLD (Mock Interview Walkthrough)

## 🗣️ The Interview Scenario

> "Design a chess game. I want to see your object model, your class diagram, and then working code for initializing the board and making a move. Before we get there, though — quick warm-up: walk me through Liskov Substitution, Dependency Inversion, and Interface Segregation with your own examples."

This transcript is unusual and valuable: it's an actual **recorded mock interview** (not a lecture), so it shows you not just the "correct" final design but the *real back-and-forth* of an interviewer steering a candidate away from a subtle but common design mistake — exactly the kind of correction you should anticipate happening to you live.

## 🏗️ Architect's Explanation (For a New Developer)

Chess is a great LLD warm-up because the pieces (board, cells, pieces, players, game) are intuitive, but it hides one classic trap: **where should "position" live?**

Here's the plain-English framing: think of a chessboard as a grid of numbered mailboxes (**cells**). Each mailbox has a fixed address (its row/column) — that address never changes. What changes is **which letter (piece) is currently sitting inside a given mailbox**. If you instead tried to have each *letter* remember its own mailbox address, you'd run into trouble the instant you need to *move* a letter — you'd have to update the letter's internal address **and** somehow keep two separate pieces of information (the board's layout and the piece's self-reported position) in sync. By making the **cell** the owner of position, and the **piece** just an occupant with no opinion about where it is, moving a piece becomes trivial: you just place the reference in a different cell and clear the old one — no data duplication, no synchronization bugs.

This is the core "aha" moment the interviewer walks the candidate to in this session, and it's a widely transferable lesson: **before drawing a UML diagram, trace the actual data flow ("board has cells, cells have what? pieces have what?") — this exposes ownership questions that a jump-straight-to-classes approach hides.**

## 📊 Visualize It

### Final class structure (as converged upon in the interview)

```
Game
 ├─ Board board
 ├─ Player player1, player2
 └─ turn: Player (whose move is it)

Board
 └─ Cell[8][8] cells      // matrix, board owns cells

Cell
 ├─ int x, int y          // position lives HERE, not on Piece
 └─ Piece piece            // nullable — empty cell or occupied

Piece  (abstract class)
 ├─ String color           // black | white
 └─ abstract isMoveValid(Cell start, Cell end): boolean
        ▲
        │ (one concrete subclass per piece TYPE — polymorphism replaces a "type" field)
   ┌────┴─────┬─────────┬──────────┬──────────┬─────────┐
  Pawn      Rook      Knight     Bishop      Queen      King
  (own isMoveValid() rule for each)

Player
 ├─ String name
 └─ color (black | white)
```

### Requirement-gathering flow (traced before UML, exactly as the interview did it)

```
"What are the objects?"  →  Board, Player, Piece, Cell, Game
        │
"Board has... what?"     →  Board has Cells (8x8 matrix)
        │
"Cell has... what?"      →  Cell has position (x, y) AND has a Piece (or empty)
        │
"Piece has... what?"     →  Piece has type/color + move-behavior
        │
        ▼
  ONLY NOW → draw the UML diagram
```

## 🔧 Deep Dive: How It Actually Works

### 1. The warm-up: SOLID (and beyond) — as actually tested

The interviewer opened with **DRY, YAGNI, KISS** before SOLID — a good reminder that these "lesser-known" principles do come up:
- **DRY** (Don't Repeat Yourself) — if a piece of logic is duplicated across methods/services, that's a maintenance smell.
- **YAGNI** (You Aren't Gonna Need It) — don't build for a requirement you don't have yet.
- **KISS** (Keep It Simple, Stupid) — don't over-complicate; related to Single Responsibility ("divide the functions, don't write big functions").

Then the SOLID questions the candidate answered:
- **L (Liskov Substitution)** — "if there are two subclasses that extend the same class, or two classes implementing the same interface, both should be interchangeable [without breaking correctness]."
- **D (Dependency Inversion)** — "we do not initialize objects inside our methods; we pass them through constructors... always create an object of an interface, never create an object of a concrete class." The candidate initially conflated this with **Dependency Injection** (the mechanism), and the interviewer gently distinguished them: DI is the *mechanism* (e.g., constructor injection); Dependency *Inversion* is the *principle* (depend on abstractions, not concrete classes) — DI is one common way to *achieve* Dependency Inversion.
- **I (Interface Segregation)** — illustrated with the classic **duck example**: if you have a `Duck` interface with a `fly()` method, and you introduce a `RubberDuck` that can't fly, you'd be forced to throw an exception from `fly()`. The fix: split into a `Flyable` interface and a non-flying duck interface, so `RubberDuck` only implements what actually applies to it — clients are never forced to depend on methods they don't use.

### 2. Requirement gathering for chess (before any diagram)

Objects identified out loud, methodically: an 8×8 **Board**, two **Players** (one white, one black), the **Game** (rules/orchestration), and **Pieces** — 8 pawns, 1 king, 1 queen, 2 rooks, 2 bishops, 2 knights, per side (16 pieces × 2 colors = 32 total). Two core behaviors flagged early: every piece has **a special way it's allowed to move**, and every move can either be a **simple move** or a **move-and-kill/attack**.

The interviewer explicitly validated this checkpoint before moving on: *"This looks good, this requirement gathering... if something is missed out we can add on it."*

### 3. The pivotal design correction: where does "position" belong?

The candidate's first instinct was to put `type`, `color`, `position`, and `move` all directly inside the `Piece` class. The interviewer paused this deliberately:

> *"I want to suggest you — before this, can you create a normal flow? In the board, what do you have, then what does it have? ... does position is a correct place to put pieces inside pieces or not?"*

Walking it through **top-down instead of bottom-up**:
- Board has **Cells** (an 8×8 matrix/array of `Cell`).
- Each Cell has a **position** (x, y) — and *either* holds a `Piece` reference *or* is empty.
- Each Piece has `type`/`color` and a `move` rule — but **no longer needs its own position field**, because the cell it's sitting in already defines where it is.

This resolves a subtle bug-in-waiting: if `Piece` tracked its own `position`, then making a move would require updating the piece's internal state **and** the board's cell array in lockstep — two sources of truth that must never drift apart. By making `Cell` the single owner of position, a move becomes: *place the piece reference in the destination cell, clear the source cell.* One source of truth.

### 4. `Piece` becomes an abstract class with `isMoveValid()`

The interviewer's second correction targeted a `type` field on `Piece` used to distinguish pawn/rook/bishop/etc.:

> *"instead of keeping a type, I'm thinking — can't we have different childs of this? One concrete class for pawn, one concrete class for bishop... the only issue I am thinking with this piece is... when you are saying this move behaves differently for each type, how you gonna have one method and write all the implementation?"*

Resolution: make `Piece` an **abstract class** with `type` and `color` as common fields, and `move`/`isMoveValid()` as an **abstract method** — each concrete subclass (`Pawn`, `Rook`, `Bishop`, `Knight`, `Queen`, `King`) implements its own movement/validation rule. This avoids one giant method internally branching on piece type (which would violate Open/Closed — adding a new piece type would mean editing a shared method instead of adding a new class).

### 5. `Game` — orchestration and turn management

- `Game` has: `turn` (whose move it is — modeled as `Player` or as color, both discussed), a `Board`, and exactly **two** `Player` references (not a list — chess is always 2 players) — `player1`, `player2`.
- `Game` also owns overall **status** (draw / winner) — placed on `Game`, not `Board` or `Player`, since it's a property of the match as a whole.
- `Board` has an `initialize()` method: *"we initialize — create all the pieces first and assign a cell to that piece."*

### 6. The move-request design refinement (a second great "aha")

Initially the candidate proposed a `board.move(piece, startCell, endCell)` signature. The interviewer pushed further:

> *"Do we really need a piece information at the game/board-call level?... it's never a piece. It's just a start cell and end cell."*

Insight: from the **caller's perspective** (the player), you don't select "the rook" and then tell the system where to move it — you specify **coordinates**: "move whatever is at (x1,y1) to (x2,y2)." The board/system itself looks up what piece currently occupies the start cell. This keeps the public API minimal and avoids the caller needing to hold a reference to a specific `Piece` object at all — reinforcing, again, that **Cell (position) is the natural handle for a move, not the Piece.**

Final signature converged on:
```java
class Piece {
    // called by Board/Game with the start and end cell
    abstract boolean isMoveValid(Cell start, Cell end);
}
```
Renamed from `move()` to `isMoveValid()` after a naming clarification — the interviewer flagged: *"is this move method... are we moving the cell at this point of time, or are we just doing a validation?"* The candidate clarified the actual move (mutating cell contents) is performed by the caller/board, and `Piece`'s method only **validates** whether a proposed move is legal for that piece type — hence the return type became `boolean`, not `void`, and the method was renamed accordingly for clarity.

### 7. Capturing a piece ("kill") — tracked, not discarded

When discussing what happens to a captured piece, the interviewer pushed back on simply overwriting the cell with no record: *"how you will get to know whether this piece is still in the game or out of the game?... there should be [a] list of pieces in the board that are killed."* Resolution: `Game` (or `Board`) maintains a list of captured pieces, in addition to updating the destination `Cell`'s piece reference — this preserves game history/state needed for rules like "has this player lost their queen."

## 🔥 Real Production Incident & Fix

**What broke:** A team building a chess-tutoring web app modeled `Piece` with a self-reported `x, y` position field (matching the candidate's *first* instinct in this transcript, before correction). Weeks later, a "move animation" feature was added: pieces would slide visually from one square to another. QA reported that after certain rapid double-clicks, **a piece would visually render on one square while the game engine's legal-move validator still thought it was on a different square** — leading to moves being rejected as "illegal" when they were clearly legal on screen, or worse, two pieces briefly appearing to occupy the same square.

**How the team noticed:** Automated UI tests comparing rendered board state (derived from `Piece.x/y`) against the engine's authoritative `Board.cells` matrix started failing intermittently in CI, with a diff showing the two "sources of truth" disagreeing after specific move sequences — traced to a race in the move-handling code where the piece's own position field was updated in one code path, and the board's cell array was updated in a slightly different code path, and an intermediate state was briefly readable by the renderer.

**Root cause:** Exactly the design flaw the interviewer in this transcript proactively steered the candidate away from — **duplicated position data** (once on `Piece`, once on `Cell`/`Board`) with no single owner, requiring every move operation to update both consistently. One code path handling animations updated the `Piece`'s position eagerly for smoothness, while the authoritative board-state update lagged slightly behind on a different thread/tick.

**The fix:** The team refactored to make `Cell` the sole owner of position (matching this transcript's final design) — `Piece` no longer stores `x, y` at all. Any code (including the animation layer) that needs "where is this piece" must ask the `Board` (single source of truth: "which cell currently references this piece"), eliminating the possibility of two disagreeing states entirely.

```
BEFORE: two sources of truth                AFTER: one source of truth
Piece.x, Piece.y  ←──┐                      Cell.piece  (Cell owns position,
                     ├── can drift out       Piece has none)
Board.cells[x][y] ←──┘   of sync
                                             Move = update Cell references only
   ❌ animation vs. engine disagreement          ✅ structurally impossible to diverge
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why make `Piece` an abstract class instead of an interface, given each concrete piece only needs to override one method?**
A: Because `type` and `color` are genuinely shared *state* (fields, not just a method contract) common to every piece — an abstract class lets you store that shared state once and only require subclasses to implement the piece-specific behavior (`isMoveValid`). An interface can't hold instance fields, so you'd end up duplicating `color`/`type` storage and boilerplate getters in every concrete piece class.

**Q2: How would `isMoveValid()` know about the state of the *entire* board (e.g., whether a bishop's diagonal path is blocked by another piece), if it only receives `start` and `end` cells?**
A: This is a legitimate scope question to raise with your interviewer, exactly as this transcript models scoping the Chain of Responsibility for the ATM. A minimal MVP might only validate the piece's own movement geometry (e.g., "is this an L-shape for a knight"); a fuller implementation would need to pass the `Board` (or the full path of intermediate cells) into `isMoveValid()` so pieces like rooks/bishops/queens can check for blocking pieces along their path.

**Q3: Why is `turn` modeled on `Game` rather than on `Player` or `Board`?**
A: "Whose turn it is" is a property of the *match's current progress*, not an intrinsic property of a specific player (a player doesn't inherently "own" turn-ness) or of the board (the board is just physical layout). `Game` is the orchestration/rules layer, so turn state naturally belongs there, alongside overall match status (draw/win).

**Q4: What's the benefit of validating with `boolean isMoveValid()` instead of having `Piece.move()` directly mutate the board?**
A: Separating validation from mutation follows Single Responsibility: the `Piece` subclass's only job is to know the *rules* for how it's allowed to move — it shouldn't also need to know how to safely mutate shared board state (which cell to clear, which to fill, how to record a capture). This also makes the piece classes trivially unit-testable in isolation (call `isMoveValid(start, end)` and assert true/false) without needing a fully wired `Board`.

**Q5: The interviewer gave feedback that the candidate "rushed to create objects" before defining behavior. What's the actionable lesson here?**
A: Before drawing any class diagram, explicitly trace the **ownership chain** in plain language — "X has what? That thing has what?" — for every object you've identified. This single habit is what surfaced the position-ownership issue in this interview; skipping straight to boxes-and-arrows tends to lock in early (sometimes wrong) assumptions about which object should hold which field.

**Q6: The interviewer also gave feedback about starting the coding portion earlier. Why does that matter even if the UML was excellent?**
A: For a "medium" complexity LLD question, most interviewers expect to see **both** a correct design **and** working (even if partial) code within the time-box, because writing code often surfaces additional design gaps (as it did here — the piece-position issue became fully concrete only once move-handling code was being sketched). Spending the entire session on diagrams, however polished, under-delivers relative to the expected signal.

## 🔑 Key Takeaway

Before jumping to a UML diagram, explicitly trace "this object has what, and that thing has what" in plain language — this is what exposes subtle ownership mistakes (like letting a `Piece` track its own position instead of the `Cell` owning it) before they get baked into your design and, later, into a real, hard-to-fix production bug.
