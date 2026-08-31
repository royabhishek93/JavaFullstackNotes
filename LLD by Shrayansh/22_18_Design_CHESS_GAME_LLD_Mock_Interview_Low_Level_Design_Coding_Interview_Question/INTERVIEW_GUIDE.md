# ♟️ Chess Game - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

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

## **Design Patterns Used**: Strategy (piece movement) + Template Method (turn processing)

**Interviewer**: "Design a Chess game."

**You**: "Chess is a fantastic OOP design question because of **polymorphic piece behavior**. Let me clarify scope:
1. Full rule validation (check, checkmate, castling, en passant, pawn promotion)?
2. Two-player only, or also support AI/online multiplayer?
3. Move history/undo?

I'll design with **Strategy Pattern for piece movement** - each piece type has different movement rules, but they all implement a common interface."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CHESS ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │       GAME        │
                    │                  │
                    │  Board           │
                    │  Players[2]      │
                    │  CurrentTurn     │
                    │  MoveHistory     │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │    BOARD     │ │    PIECE     │ │ MOVE         │
    │              │ │  (abstract)  │ │ VALIDATOR    │
    │ Cell[8][8]   │ │              │ │              │
    │              │ │ canMove()    │ │ isCheck()    │
    └──────────────┘ │ (Strategy)   │ │ isCheckmate()│
                      └──────┬───────┘ └──────────────┘
                             │
          ┌──────┬──────┬────┼────┬──────┬──────┐
          ▼      ▼      ▼    ▼    ▼      ▼      ▼
        King  Queen  Rook Bishop Knight Pawn
        
    EACH PIECE IMPLEMENTS canMove() DIFFERENTLY:
    ┌────────────────────────────────────────────┐
    │  Bishop: diagonal only                       │
    │  Rook: horizontal/vertical only              │
    │  Knight: L-shaped (2+1)                      │
    │  Pawn: forward only, diagonal for capture    │
    │  King: 1 step any direction                  │
    │  Queen: combines Rook + Bishop                │
    └────────────────────────────────────────────┘
```

---

## 2. API Design

```http
POST /api/v1/games
Request: {"whitePlayer": "user1", "blackPlayer": "user2"}
Response: 201 CREATED
{"gameId": "game-1234", "board": "<FEN notation>", "currentTurn": "WHITE"}

---

POST /api/v1/games/{gameId}/moves
Request: {"from": "e2", "to": "e4", "playerId": "user1"}
Response: 200 OK
{
  "valid": true,
  "board": "<updated FEN>",
  "check": false,
  "capturedPiece": null,
  "nextTurn": "BLACK"
}

// Invalid move:
Response: 400 BAD_REQUEST
{
  "error": "INVALID_MOVE",
  "message": "Pawn cannot move 3 squares"
}

// Checkmate:
Response: 200 OK
{
  "valid": true,
  "gameStatus": "CHECKMATE",
  "winner": "WHITE"
}
```

---

## 3. ER Diagram & Database Design

```sql
CREATE TABLE games (
    game_id VARCHAR(50) PRIMARY KEY,
    white_player_id VARCHAR(50) NOT NULL,
    black_player_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'IN_PROGRESS',
    winner_id VARCHAR(50),
    current_fen TEXT,  -- Board state in FEN notation
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE moves (
    move_id VARCHAR(50) PRIMARY KEY,
    game_id VARCHAR(50) NOT NULL,
    move_number INT NOT NULL,
    player_id VARCHAR(50) NOT NULL,
    from_square VARCHAR(2) NOT NULL,  -- e.g., 'e2'
    to_square VARCHAR(2) NOT NULL,
    piece_type VARCHAR(10) NOT NULL,
    captured_piece VARCHAR(10),
    is_check BOOLEAN DEFAULT FALSE,
    is_castle BOOLEAN DEFAULT FALSE,
    is_en_passant BOOLEAN DEFAULT FALSE,
    promoted_to VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    INDEX idx_game_move (game_id, move_number)
);
```

**You**: "Storing board state as **FEN notation** (Forsyth-Edwards Notation) is industry-standard - compact string representation, easily transmitted over network, human-readable for debugging."

---

## 4. Sequence Diagrams

```
Player   Game    Board   Piece(Bishop)   MoveValidator
  │        │        │           │              │
  │─move(c1,f4)▶│        │           │              │
  │        ├─getPiece(c1)──▶│           │              │
  │        │◀Bishop─────────│           │              │
  │        ├─canMove(c1,f4)──────────────▶│              │
  │        │        │  Check: diagonal path? YES         │
  │        │        │  Check: path clear? YES             │
  │        │◀true───────────────────────│              │
  │        ├─isKingInCheck(afterMove)────────────────────▶│
  │        │        │           │              │  Simulate move, check if own king exposed
  │        │◀false──────────────────────────────────────│
  │        ├─executeMove()──▶│           │              │
  │◀Move valid, board updated│           │              │
```

---

## 5. Scenario-First Explanations

### **5.1 Why Strategy Pattern for Piece Movement?**

**You**: "Without Strategy Pattern (Bad Design):
```java
// ❌ God method with switch statement
boolean canMove(Piece piece, Position from, Position to) {
    switch (piece.getType()) {
        case BISHOP:
            return isValidDiagonal(from, to) && isPathClear(from, to);
        case ROOK:
            return isValidStraight(from, to) && isPathClear(from, to);
        case KNIGHT:
            return isValidLShape(from, to);  // No path check needed - jumps!
        case KING:
            return isOneStep(from, to) && !isPositionAttacked(to);
        // ... 6 cases total, all logic centralized
    }
}
// Adding new piece type or variant (e.g., Chess960) = modify this method
```

With Strategy Pattern:
```java
abstract class Piece {
    protected Color color;
    protected Position position;
    
    abstract boolean canMove(Board board, Position to);
    abstract List<Position> getPossibleMoves(Board board);
}

class Bishop extends Piece {
    boolean canMove(Board board, Position to) {
        if (!isValidDiagonal(position, to)) return false;
        return board.isPathClear(position, to);
    }
}

class Knight extends Piece {
    boolean canMove(Board board, Position to) {
        int rowDiff = Math.abs(to.getRow() - position.getRow());
        int colDiff = Math.abs(to.getCol() - position.getCol());
        return (rowDiff == 2 && colDiff == 1) || (rowDiff == 1 && colDiff == 2);
        // No path check - knight jumps over pieces!
    }
}

class Pawn extends Piece {
    boolean canMove(Board board, Position to) {
        int direction = (color == Color.WHITE) ? 1 : -1;
        int rowDiff = to.getRow() - position.getRow();
        
        // Forward move
        if (to.getCol() == position.getCol()) {
            if (rowDiff == direction && board.isEmpty(to)) return true;
            if (isFirstMove() && rowDiff == 2 * direction && board.isEmpty(to)) return true;
        }
        // Diagonal capture
        if (Math.abs(to.getCol() - position.getCol()) == 1 && rowDiff == direction) {
            return board.hasOpponentPiece(to, color) || isEnPassantValid(board, to);
        }
        return false;
    }
}

class King extends Piece {
    boolean canMove(Board board, Position to) {
        int rowDiff = Math.abs(to.getRow() - position.getRow());
        int colDiff = Math.abs(to.getCol() - position.getCol());
        
        if (rowDiff <= 1 && colDiff <= 1) {
            return !board.isPositionAttacked(to, color.opposite());  // Can't move into check!
        }
        // Castling special case
        return isCastlingValid(board, to);
    }
}
```

**Benefits**: Each piece encapsulates its own movement logic. Adding a new chess variant (e.g., Fairy chess pieces) = new Piece subclass, zero changes to existing pieces!"

### **5.2 Why 'Simulate Move' for Check Detection?**

**You**: "Critical rule: **A move is illegal if it leaves your OWN king in check**. This requires simulation:

```java
class MoveValidator {
    boolean isMoveLegal(Board board, Move move) {
        // Step 1: Basic piece movement rule
        if (!move.getPiece().canMove(board, move.getTo())) {
            return false;
        }
        
        // Step 2: Simulate the move
        Board simulatedBoard = board.copy();
        simulatedBoard.executeMove(move);
        
        // Step 3: Check if OWN king is in check after this hypothetical move
        Position kingPosition = simulatedBoard.findKing(move.getPiece().getColor());
        if (simulatedBoard.isPositionAttacked(kingPosition, move.getPiece().getColor().opposite())) {
            return false;  // Illegal! Own king would be in check
        }
        
        return true;
    }
}
```

**Why this matters**: This is why chess engines need efficient board copying/undo mechanisms - EVERY candidate move must be simulated to check legality. This drives the choice of board representation (bitboards in production engines for O(1) copy vs O(64) for array-based)."

---

## 6. Cross Questions

**Interviewer**: "How do you detect checkmate vs stalemate?"

**You**: "Both require checking ALL possible moves for the player in check/not in check:

```java
class GameStateEvaluator {
    GameStatus evaluateState(Board board, Color playerColor) {
        boolean inCheck = board.isKingInCheck(playerColor);
        boolean hasLegalMoves = hasAnyLegalMove(board, playerColor);
        
        if (inCheck && !hasLegalMoves) {
            return GameStatus.CHECKMATE;  // King attacked, no escape
        }
        if (!inCheck && !hasLegalMoves) {
            return GameStatus.STALEMATE;  // Not attacked, but no legal moves (draw!)
        }
        if (inCheck) {
            return GameStatus.CHECK;
        }
        return GameStatus.IN_PROGRESS;
    }
    
    boolean hasAnyLegalMove(Board board, Color color) {
        for (Piece piece : board.getPieces(color)) {
            for (Position candidateMove : piece.getPossibleMoves(board)) {
                if (moveValidator.isMoveLegal(board, new Move(piece, candidateMove))) {
                    return true;  // Found at least one legal move
                }
            }
        }
        return false;  // No legal moves exist
    }
}
```

**Complexity concern**: Checking every piece × every possible destination × simulating each = expensive! Production chess engines use **bitboards** and incremental attack-map updates for O(1) amortized checks instead of O(n²) brute force."

---

## 7. Trade-offs

### **Board Representation: 2D Array vs Bitboard**

| Aspect | 2D Array (char[8][8]) | Bitboard (64-bit long) |
|--------|------------------------|--------------------------|
| **Memory** | 64 bytes | 8 bytes per piece type (12 longs = 96 bytes total, but bit ops are fast) |
| **Move Generation Speed** | Slower (loop-based) | Extremely fast (bitwise ops) |
| **Complexity** | Simple, readable | Complex, hard to debug |
| **Use Case** | Interviews, learning | Production chess engines (Stockfish) |

**You**: "For an INTERVIEW, 2D array with Piece objects is the right level of abstraction - readable OOP design. For a PRODUCTION chess engine competing at high ELO, bitboards are essential for performance (searching millions of positions per second)."

---

## 8. Senior Trap Questions

### **Trap: "Just check if move matches piece pattern, that's enough!"**

**❌ Junior**: "If Bishop moves diagonally, it's valid."

**✅ Senior**: "Three additional checks needed beyond basic pattern:
1. **Path clearance**: Can't jump over pieces (except Knight)
2. **Destination occupancy**: Can't capture own piece
3. **King safety**: Move can't leave own king in check (pinned piece scenario!)

```java
// Classic 'pinned piece' bug if you skip check #3:
// White Bishop is between White King and Black Rook (pinned)
// Bishop 'moves diagonally' validly, but exposes King to Rook's attack
// MUST be rejected!
```

This 'pinned piece' scenario is a favorite interview gotcha - shows if you truly understand chess rules or just pattern-matched the obvious cases."

---

## 9. Technology Choices

**You**: "For online multiplayer chess: **WebSocket** for real-time move sync, **Redis** for active game state (fast reads/writes during gameplay), **PostgreSQL** for completed game history/replay (analytics, puzzle generation from famous games)."

---

## 🎓 **Final Tips**

1. **Strategy Pattern**: Each piece type = independent movement logic
2. **Move Simulation**: Critical for check/checkmate/pin detection
3. **FEN Notation**: Industry-standard board serialization
4. **Bitboards**: Mention for production-scale performance discussion

Good luck! Chess tests **polymorphism mastery** and **algorithmic edge-case thinking** (pins, en passant, castling). 🚀
