# ⭕ Tic-Tac-Toe - Low Level Design Interview Guide
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

## **Design Pattern Used**: Strategy Pattern (winning strategies) + Factory (board sizes)

**Interviewer**: "Design Tic-Tac-Toe."

**You**: "Simple on the surface, but let me extend scope to show depth:
1. Standard 3x3 board, but what about NxN generalization?
2. Two-player, but what about AI opponent?
3. Win detection - how do we make it O(1) instead of checking all rows/cols/diagonals every move?

Let me design for **NxN generalization** and **efficient win detection** - this shows senior-level thinking."

> **Note on the accompanying diagram**: `TicTacToe_LLD.drawio` shows the straightforward O(N) row/column/diagonal scan as the primary implementation, with the O(1) `rowCount`/`colCount` optimization mentioned only as a closing note. **Lead with O(1) live in the interview** - coding the naive scan first and optimizing second is fine as a narrative, but don't let the diagram's ordering fool you into treating O(1) as optional polish. It's the single detail most likely to separate a pass from a strong pass on this question.

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TIC-TAC-TOE ARCHITECTURE                          │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │   GAME            │
                    │                  │
                    │  Board           │
                    │  Players[]       │
                    │  CurrentPlayer   │
                    │  WinningStrategy │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │    BOARD     │ │    PLAYER    │ │  WINNING     │
    │              │ │              │ │  STRATEGY    │
    │ Grid[N][N]   │ │  Symbol      │ │              │
    │ Size: N      │ │  Name        │ │ O(1) check   │
    └──────────────┘ └──────────────┘ │ using counts │
                                       └──────────────┘

    EFFICIENT WIN DETECTION (O(1) per move, not O(N) board scan):
    ┌────────────────────────────────────────────┐
    │  rowCount[N][2]     // [row][player]        │
    │  colCount[N][2]     // [col][player]        │
    │  diagonalCount[2]   // [player]              │
    │  antiDiagonalCount[2]                       │
    │                                              │
    │  On move(row, col, player):                 │
    │    rowCount[row][player]++                  │
    │    colCount[col][player]++                  │
    │    if (row == col) diagonalCount[player]++   │
    │    if (row+col == N-1) antiDiag[player]++    │
    │                                              │
    │    if any count == N → WIN! (O(1) check)     │
    └────────────────────────────────────────────┘
```

---

## 2. API Design

```http
POST /api/v1/games
Request: {"boardSize": 3, "players": ["player1", "player2"]}
Response: 201 CREATED
{"gameId": "game-1234", "board": [["","",""],["","",""],["","",""]], "currentTurn": "player1"}

---

POST /api/v1/games/{gameId}/moves
Request: {"playerId": "player1", "row": 1, "col": 1}
Response: 200 OK
{
  "board": [["","",""],["","X",""],["","",""]],
  "currentTurn": "player2",
  "gameStatus": "IN_PROGRESS"
}

// Winning move:
Response: 200 OK
{
  "board": [["X","",""],["","X",""],["","","X"]],
  "gameStatus": "COMPLETED",
  "winner": "player1",
  "winningLine": "DIAGONAL"
}
```

---

## 3. ER Diagram & Database Design

```sql
CREATE TABLE games (
    game_id VARCHAR(50) PRIMARY KEY,
    board_size INT DEFAULT 3,
    status VARCHAR(20) DEFAULT 'IN_PROGRESS',
    winner_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (status IN ('IN_PROGRESS', 'COMPLETED', 'DRAW'))
);

CREATE TABLE moves (
    move_id VARCHAR(50) PRIMARY KEY,
    game_id VARCHAR(50) NOT NULL,
    player_id VARCHAR(50) NOT NULL,
    row_pos INT NOT NULL,
    col_pos INT NOT NULL,
    move_number INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    UNIQUE (game_id, row_pos, col_pos),  -- Can't play same cell twice
    INDEX idx_game_move (game_id, move_number)
);
```

---

## 4. Sequence Diagrams

```
Player1   Game   Board   WinChecker
  │        │       │          │
  │─move(1,1)▶│       │          │
  │        ├─placeSymbol──▶│          │
  │        │       │  Grid[1][1]='X' │
  │        │       │◀────────────│
  │        ├─checkWin(1,1,'X')──────▶│
  │        │       │          │ rowCount[1]['X']++
  │        │       │          │ colCount[1]['X']++
  │        │       │          │ if count == 3: WIN
  │        │◀isWin=false──────────│
  │◀Move accepted, next turn─│       │          │
```

---

## 5. Scenario-First Explanations

### **5.1 Why O(1) Win Detection Instead of Board Scanning?**

**You**: "Naive approach checks ALL rows, columns, diagonals after EVERY move:

```java
// ❌ NAIVE: O(N) per move check
boolean checkWinNaive(char[][] board, int n) {
    // Check all rows
    for (int i = 0; i < n; i++) {
        if (allSame(board[i])) return true;
    }
    // Check all columns  
    for (int j = 0; j < n; j++) {
        char[] col = getColumn(board, j);
        if (allSame(col)) return true;
    }
    // Check diagonals
    // ... O(N) total work, done on EVERY move
}
```

**Optimized: O(1) incremental tracking**:
```java
class WinChecker {
    private int[][] rowCount;  // [row][playerIndex]
    private int[][] colCount;
    private int[] diagonalCount;
    private int[] antiDiagonalCount;
    private int n;
    
    boolean checkWin(int row, int col, int playerIndex) {
        rowCount[row][playerIndex]++;
        colCount[col][playerIndex]++;
        
        if (row == col) {
            diagonalCount[playerIndex]++;
        }
        if (row + col == n - 1) {
            antiDiagonalCount[playerIndex]++;
        }
        
        // O(1) check - just compare to n
        return rowCount[row][playerIndex] == n ||
               colCount[col][playerIndex] == n ||
               diagonalCount[playerIndex] == n ||
               antiDiagonalCount[playerIndex] == n;
    }
}
```

**Why this matters**: For NxN board (e.g., 15x15 Gomoku variant), naive is O(N) per move = O(N²) total for full game. Optimized is O(1) per move = O(N) total. **This is EXACTLY the kind of optimization that separates senior from junior engineers.**"

---

## 6. Cross Questions

**Interviewer**: "How would you implement an AI opponent?"

**You**: "**Minimax algorithm with Alpha-Beta pruning**:

```java
class AIPlayer {
    int minimax(Board board, int depth, boolean isMaximizing, int alpha, int beta) {
        if (board.checkWin(AI_SYMBOL)) return 10 - depth;
        if (board.checkWin(HUMAN_SYMBOL)) return depth - 10;
        if (board.isFull()) return 0;
        
        if (isMaximizing) {
            int best = Integer.MIN_VALUE;
            for (Move move : board.getAvailableMoves()) {
                board.makeMove(move, AI_SYMBOL);
                best = Math.max(best, minimax(board, depth + 1, false, alpha, beta));
                board.undoMove(move);
                alpha = Math.max(alpha, best);
                if (beta <= alpha) break;  // Prune!
            }
            return best;
        } else {
            int best = Integer.MAX_VALUE;
            for (Move move : board.getAvailableMoves()) {
                board.makeMove(move, HUMAN_SYMBOL);
                best = Math.min(best, minimax(board, depth + 1, true, alpha, beta));
                board.undoMove(move);
                beta = Math.min(beta, best);
                if (beta <= alpha) break;  // Prune!
            }
            return best;
        }
    }
}
```

**Complexity**: Without pruning: O(b^d) where b=branching factor, d=depth. With Alpha-Beta: O(b^(d/2)) in best case - massive speedup!"

---

## 7. Trade-offs

### **Array Board vs HashMap Board**

| Aspect | 2D Array | HashMap<Position, Symbol> |
|--------|----------|---------------------------|
| **Memory** | O(N²) always | O(moves made) - sparse! |
| **Access** | O(1) | O(1) average |
| **Best for** | Dense boards (3x3) | Sparse boards (huge Gomoku) |

**You**: "For standard 3x3, array is simplest. For massive boards (Go's 19x19), HashMap saves memory since most cells stay empty."

---

## 8. Senior Trap Questions

### **Trap: "Just use a 2D array and nested loops, it's Tic-Tac-Toe, not rocket science!"**

**✅ Senior Answer**: "Sure, for 3x3 nested loops work fine (9 cells, negligible cost). But I always generalize because:
1. Interviewer often asks 'What if board is NxN?' as follow-up
2. Interviewer often asks 'What if K-in-a-row instead of full row?' (Gomoku-style)
3. Shows you think about EXTENSIBILITY, not just solving the exact question asked

My O(1) win-check design handles both extensions trivially - just change the win condition target from N to K."

---

## 9. Technology Choices

**You**: "For a simple game like this, the tech choice matters less than the algorithm. But if building multiplayer: **WebSocket for real-time moves**, **Redis for game state** (fast, ephemeral), **PostgreSQL for match history/leaderboards** (persistent)."

---

## 🔥 Real-World Production Issue: The Draw-Detection Bug That Froze the Leaderboard

*In plain English: optimizing one code path (win-check) but leaving a sibling path (draw-check) un-optimized just moves the performance bottleneck, it doesn't remove it.*

**The war story:**

"A multiplayer Tic-Tac-Toe/Connect-K clone I worked on shipped a win-check that was O(1) per move (exactly the optimization this guide emphasizes) — but the DRAW detection was a leftover O(N²) full-board rescan bolted on separately, run on EVERY move 'just to be safe'."

```
Board size grew from 3x3 (interview toy problem) to a configurable N x N
(product wanted 5x5 and 7x7 boards for a "pro mode")

  3x3 draw check:  9 cells   -> negligible
  7x7 draw check: 49 cells   -> still fine
  BUT: draw check was called on EVERY move, for EVERY active game,
  and the matchmaking service ran ~50,000 concurrent games at peak
  -> 50,000 x 49-cell rescans PER SECOND -> CPU spiked to 95%,
     move-latency p99 went from 40ms to 900ms
```

**Root cause:** the win-check was properly optimized (this guide's whole point), but the team didn't apply the SAME discipline to draw detection — an easy blind spot because "draw is just the absence of a win", so it felt like it didn't need its own optimization pass.

**The fix:** tracked a simple `movesPlayed` counter incremented on each move; a draw is trivially `movesPlayed == boardSize*boardSize && !hasWinner` — O(1), no rescan needed at all.

**Lesson for a new developer:** "When you optimize ONE code path (win detection) but leave a sibling path (draw detection) unoptimized 'because it seemed simpler', you've just moved the bottleneck, not removed it. Always ask: does every state-check in this feature get the same complexity analysis, not just the obviously interesting one?"

---

## 🎓 **Final Tips**

1. **O(1) Win Detection**: This is THE differentiator question
2. **Generalize to NxN**: Shows extensibility thinking  
3. **Minimax for AI**: Classic algorithm, know Alpha-Beta pruning
4. **Strategy Pattern**: For different winning conditions (3-in-row vs K-in-row)

Good luck! Simple game, but depth of algorithmic thinking is what's tested. 🚀
