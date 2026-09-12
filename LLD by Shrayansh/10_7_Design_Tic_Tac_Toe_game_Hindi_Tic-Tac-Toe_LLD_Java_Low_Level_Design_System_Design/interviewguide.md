# Interview Guide: Tic-Tac-Toe (LLD)

## 🗣️ The Interview Scenario

> "Design a Tic-Tac-Toe game. It should support the classic 3x3 board initially, but I want your design to be extensible — tomorrow I might want a 5x5 board, 4 players instead of 2, and custom symbols instead of just X and O. Show me the classes, how they relate, and how a full game loop would run, including win detection."

The trap here is that most candidates hardcode `char board[3][3]` and `if (board[i][j] == 'X')` logic — which works for the demo but collapses the moment the interviewer asks "now make it NxN" or "now support 3 players." The real signal the interviewer wants is **extensibility discipline**: generic types instead of hardcoded literals, and composition instead of copy-pasted logic.

## 🏗️ Architect's Explanation (For a New Developer)

Strip away the "game" framing and think of Tic-Tac-Toe as three independent concerns that happen to interact:

1. **What gets placed on the board** — a piece/symbol (X, O, or anything else in the future). This should be modeled as its own type, not a raw `char`, so that "add a new symbol" is just "add a new subclass," not "rewrite comparison logic everywhere."
2. **Where things get placed** — a board, which is really just a generic NxN grid that stores piece references. The board shouldn't know anything about "winning" — it only tracks state.
3. **Who is placing things and what they're placing** — a player, who owns exactly one piece type for the whole game.

The architectural habit to build here (and one you'll reuse in *every* LLD interview): **identify the nouns first (objects), then figure out the relationships between them (has-a vs. is-a), and only then write the methods.** Rushing to code before nailing down "Piece is an abstract type, X and O are its children" is the single biggest reason candidates get stuck mid-interview restructuring their classes.

## 📊 Visualize It

Class structure:

```
                 +----------------+
                 |     Piece      |  (abstract class)
                 +----------------+
                 | # pieceType    |
                 +----------------+
                    ▲          ▲
          extends   |          |   extends
                     |          |
           +-----------+   +-----------+
           | PieceX    |   | PieceO    |   ... (extensible: PieceZ, PieceDollar, etc.)
           +-----------+   +-----------+

  +-----------------+        contains        +----------------------+
  |     Board       |----------------------->|  Piece[][] (N x N)   |
  +-----------------+                        +----------------------+
  | - size          |
  | - Piece[][] grid|
  +-----------------+

  +-----------------+        has-a          +----------------+
  |     Player      |----------------------->|     Piece      |
  +-----------------+                        +----------------+
  | - id / name      |
  | - Piece piece   |
  +-----------------+

  +-----------------+   has-a (Deque)       +----------------+
  |      Game        |----------------------->|  Player queue |
  +-----------------+                        +----------------+
  | - Board board    |     has-a
  +-----------------+ ------------------------> Board (1 board per game)
```

Runtime turn-flow (deque-based turn rotation):

```
   Deque<Player>: [P1, P2]

   turn 1: dequeue P1 --> P1 makes a move --> enqueue P1 at back --> [P2, P1]
   turn 2: dequeue P2 --> P2 makes a move --> enqueue P2 at back --> [P1, P2]
   ... repeat until winner found or board full ...

   invalid move (cell occupied)?  --> re-enqueue SAME player at FRONT, ask again
```

## 🔧 Deep Dive: How It Actually Works

### 1. `Piece` — the extensibility anchor

```java
abstract class Piece {
    PieceType pieceType;
    Piece(PieceType pieceType) { this.pieceType = pieceType; }
}

class PieceX extends Piece {
    PieceX() { super(PieceType.X); }
}

class PieceO extends Piece {
    PieceO() { super(PieceType.O); }
}
```

Notice the pattern: `PieceX`'s constructor calls `super(PieceType.X)` — it hardcodes its *own* type when talking to its parent, but the parent (`Piece`) stores the type generically. This is exactly what lets you add a `PieceZ` or `PieceDollar` later without touching `Board` or `Game` at all — they only ever deal with the abstract `Piece` reference.

### 2. `Board` — a generic N x N grid, not "3x3"

```java
class Board {
    int size;
    Piece[][] board;

    Board(int size) {
        this.size = size;
        this.board = new Piece[size][size];   // NxN, not hardcoded 3x3
    }
}
```

Keeping `size` as a constructor parameter (rather than a hardcoded `3`) is the single change that makes "5x5 board" a non-issue in this design — it's a configuration input, not a code change.

### 3. `Player` — owns exactly one piece for the whole game

```java
class Player {
    String id;      // or name
    Piece piece;    // which symbol this player plays with

    Player(String id, Piece piece) {
        this.id = id;
        this.piece = piece;
    }
}
```

### 4. `Game` — orchestrates board, players, and turn order

```java
class Game {
    Board board;
    Deque<Player> players;   // Deque chosen deliberately: cheap remove-from-front + add-to-back
    int winCount = 3;         // configurable: "how many in a row/col/diagonal wins?"

    void startGame() {
        while (true) {
            Player currentPlayer = players.pollFirst();     // take current player off the front
            printBoard();
            System.out.println("Enter row, col:");
            int row = readRow(), col = readCol();

            boolean success = board.addPiece(row, col, currentPlayer.piece);
            if (!success) {
                System.out.println("Incorrect position, try again");
                players.offerFirst(currentPlayer);           // same player retries — pushed back to FRONT
                continue;
            }

            players.offerLast(currentPlayer);                // valid move — goes to the BACK of the line

            if (checkWinner(row, col, currentPlayer.piece)) {
                System.out.println("Winner: " + currentPlayer.id);
                break;
            }
        }
    }
}
```

**Why a `Deque` instead of a plain list with an index counter?** Because "remove from the front, and if the move is valid push to the back, else push back to the front to retry" is *exactly* the deque contract (`pollFirst`/`offerFirst`/`offerLast`), and it reads cleanly without manual index arithmetic or modulo bookkeeping.

### 5. `Board.addPiece` — validation lives at the board level, not the game level

```java
boolean addPiece(int row, int col, Piece piece) {
    if (board[row][col] != null) {
        return false;   // cell occupied — caller (Game) decides what to do about it
    }
    board[row][col] = piece;
    return true;
}
```

The transcript explicitly calls out that this validation (cell already occupied) mirrors the same bounds-checking discipline you'd use in an **N-Queens** style board problem — always validate before mutating shared board state, and let the caller own the retry policy, not the board.

### 6. Win detection — the part most candidates hand-wave

The core idea: after every move, only check the row, column, and (if applicable) diagonal that the *just-played* cell belongs to — never rescan the whole board. That keeps each move's win-check proportional to `size`, not `size²`.

```java
boolean checkWinner(int row, int col, Piece piece) {
    boolean rowWin = true, colWin = true;
    for (int i = 0; i < board.size; i++) {
        if (board.board[row][i] != piece) rowWin = false;   // scan the row of the last move
        if (board.board[i][col] != piece) colWin = false;   // scan the column of the last move
    }
    // diagonal / anti-diagonal checks only apply when (row == col) or (row + col == size - 1)
    return rowWin || colWin /* || diagonalWin || antiDiagonalWin */;
}
```

### Extensibility summary (what this design buys you)

| Requirement change | What you touch |
|---|---|
| Board becomes 5x5 | Pass `size=5` to `Board` constructor — zero class changes |
| Add a 3rd player with a new symbol | Add `PieceZ extends Piece`, construct a 3rd `Player`, add to the `Deque` |
| Change win condition (e.g., 4-in-a-row on a big board) | Change the single `winCount` field / win-check loop bound |

## 🔥 Real Production Incident & Fix

**What broke**: A team building an internal "puzzle/mini-games" platform (used for user engagement rewards) shipped a Tic-Tac-Toe feature where the board size and win-length were hardcoded as `char[3][3]` with literal `board[i][0] == board[i][1] && board[i][1] == board[i][2]` win checks scattered across four separate `if` blocks (row, column, both diagonals). Three months later, product asked for a "Connect-4-style bonus round" — a bigger board with a different win-length — as a quick reuse of the existing Tic-Tac-Toe module.

**How the team noticed**: QA filed a bug report titled "5x5 bonus board never declares a winner" — the win-check code was still comparing exactly 3 hardcoded cells (`board[i][0]`, `board[i][1]`, `board[i][2]`), so on a 5x5 board a genuine 5-in-a-row never triggered any of the four hand-written conditions; the game would silently run until the board filled up and then report a draw, even when a player had clearly won on-screen.

**Root cause**: The original implementation had baked the literal board dimension (3) and win-length (3) directly into four independent conditional expressions instead of treating "size" and "win-length" as configuration and writing one general row/column/diagonal scan loop (as shown in the Deep Dive section above). There was no `Piece`/`Board` abstraction — just a raw `char[][]` — so there was no single place to fix the logic; it had to be found and patched in four different spots, and one diagonal case was missed entirely on the first fix attempt.

**The fix**: The team refactored to the exact structure shown above — a generic `size`-driven `Board`, a configurable `winCount`, and a single parameterized loop that checks the row/column/diagonal *of the last move only*, bounded by `size` and compared against `winCount` consecutive matches instead of three hardcoded indices. The bonus-round feature then required only a constructor argument change, and a regression test matrix (3x3/win3, 5x5/win4, 7x7/win5) was added to prevent the hardcoded-dimension mistake from recurring.

```
BEFORE: 4 hardcoded win-checks tied to literal "3":     AFTER: one generic scan bounded by `size` and `winCount`:

 if (b[i][0]==b[i][1] && b[i][1]==b[i][2]) win=true;     for (int i = 0; i < size; i++) {
 if (b[0][j]==b[1][j] && b[1][j]==b[2][j]) win=true;         rowMatch &= (board[row][i] == piece);
 ...(2 more hardcoded diagonal checks)...                     colMatch &= (board[i][col] == piece);
 // breaks silently on any board size != 3                }
                                                          // works for any size/winCount combination
```

## ❓ Likely Interview Follow-Up Questions & Answers

1. **"Why not just use `char` or `int` to represent X and O instead of a `Piece` class hierarchy?"**
   A primitive works for exactly two symbols, but the moment you need a third player or a custom symbol set, every place that does `if (cell == 'X')` needs to change. Modeling `Piece` as an abstract type means the board, game, and win-checker only ever compare `Piece` references (or an equality check on a `pieceType` field) — adding a new symbol is purely additive (a new subclass), consistent with the Open/Closed Principle.

2. **"Why did you choose a `Deque` for player turn order instead of a simple array with an index that you increment modulo the number of players?"**
   Both work, but the deque naturally expresses the actual business rule: "the current player either goes to the back of the line (valid move) or stays at the front to retry (invalid move)." Modulo-indexing works for the happy path but requires extra branching to handle "same player retries" without disturbing the rotation for everyone else.

3. **"Where would you put the logic that decides if the game is a draw?"**
   In the same loop as move-processing in `Game.startGame()`: if `board.addPiece()` never fails (all cells attempted) and `checkWinner()` has never returned true once every cell is filled, declare a draw. It's cleanest to track a simple move counter (`movesPlayed == size*size`) rather than re-scanning the board for emptiness each turn.

4. **"How would you support an NxN board but require only K-in-a-row to win (not the full N), like Gomoku?"**
   Keep the same row/col/diagonal scan structure but replace the "must match across the whole size" check with a sliding-window count of consecutive same-piece cells, and stop as soon as the count hits `K`. The `Board` and `Piece` classes need zero changes — only `checkWinner`'s internal loop changes.

5. **"What class is responsible for validating that a move is inside the board bounds — and why does that matter for a design interview?"**
   `Board.addPiece(row, col, piece)` should own bounds-checking (`row/col` within `[0, size)`) and occupancy-checking, not `Game`. This is a Single Responsibility Principle call: `Board` owns board-state invariants, `Game` owns turn orchestration and win-condition orchestration — mixing them makes both harder to unit test independently.

6. **"How would this design change for a multiplayer online version where moves come from different servers/requests instead of a single in-process loop?"**
   The `Game` object's state (whose turn it is, the board) would need to move into a persisted/shared store (DB or in-memory cache keyed by game ID) instead of local Java fields, and `startGame()`'s single `while(true)` loop would be replaced by a per-move API call that loads game state, applies exactly one move, checks the winner, and persists state back — the `Piece`/`Board`/`Player` class design itself stays identical; only the orchestration layer changes.

## 🔑 Key Takeaway

The interview signal isn't "can you build Tic-Tac-Toe" — it's whether you instinctively replace hardcoded literals (board size, win length, symbol set) with generic, configurable fields and an abstract `Piece` hierarchy, so that "make it NxN" or "add a player" is a data change, not a rewrite.
