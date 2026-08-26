# Chess Game - Complete LLD Interview Guide

**Interview Duration: 45 minutes | Difficulty: Hard | Must-Know: ⭐⭐ (Optional)**

**Note:** This is the most complex LLD problem. Only attempt if you have extra time!

---

## CONVERSATIONAL SCRIPT (How to approach in interview)

### Phase 1: Requirements Clarification (5 mins)

**You:** "Chess is complex - let me clarify the scope before jumping in."

**Functional Requirements:**
- "Standard 8x8 board with 6 piece types (King, Queen, Rook, Bishop, Knight, Pawn)"
- "Two players - White and Black, turn-based"
- "Valid move validation for each piece type"
- "Check, Checkmate, Stalemate detection"
- "Special moves - Castling, En Passant, Pawn Promotion"
- "Move history tracking"
- "Should we support AI player or just 2 humans?"

**Interviewer:** "Keep it to 2 human players. Focus on move validation and game state."

**You:** "For non-functional requirements:"
- "Fast move validation (< 100ms)"
- "Undo/Redo moves"
- "Save and load game state"
- "Extensible for future features (AI, timers, ratings)"

**Interviewer:** "Yes, and make sure the design is clean and testable."

**Key Design Challenge:** "The main complexity is **move validation** - each piece has different rules, and we need to check for check/checkmate after every move."

---

### Phase 2: Core Entities (3 mins)

**You:** "Let me identify the key entities:"

```
┌──────────────────────────────────────────────────────────────┐
│                    CORE ENTITIES                             │
└──────────────────────────────────────────────────────────────┘

1. Board - 8x8 grid of squares
   └─ Cell/Square - Contains piece or empty

2. Piece (Abstract)
   ├─ King
   ├─ Queen
   ├─ Rook
   ├─ Bishop
   ├─ Knight
   └─ Pawn

3. Player
   ├─ Color: White/Black
   └─ Pieces

4. Game
   ├─ Board
   ├─ Players
   ├─ Current Turn
   ├─ Game Status (Active, Check, Checkmate, Stalemate)
   └─ Move History

5. Move
   ├─ From Position
   ├─ To Position
   ├─ Piece moved
   └─ Captured piece (if any)
```

---

### Phase 3: Class Design (5 mins)

**You:** "Here's the UML structure:"

```
┌─────────────────────────────────────────────────────────────┐
│                    CLASS DIAGRAM                             │
└─────────────────────────────────────────────────────────────┘

┌────────────────────────┐
│        Game            │ (Facade)
│  ────────────────────  │
│  - board: Board        │
│  - players: Player[2]  │
│  - currentTurn: Color  │
│  - status: GameStatus  │
│  - moveHistory: List   │
│  ────────────────────  │
│  + makeMove()          │
│  + isValidMove()       │
│  + isCheck()           │
│  + isCheckmate()       │
│  + undo()              │
└────────┬───────────────┘
         │ 1
         │ 1
         ↓
┌────────────────────────┐
│        Board           │
│  ────────────────────  │
│  - cells: Cell[8][8]   │
│  ────────────────────  │
│  + getPiece(pos)       │
│  + setPiece(pos, piece)│
│  + movePiece(from, to) │
│  + getAllPieces(color) │
└────────┬───────────────┘
         │ 1
         │ 64
         ↓
┌────────────────────────┐
│        Cell            │
│  ────────────────────  │
│  - position: Position  │
│  - piece: Piece        │
│  ────────────────────  │
│  + isEmpty()           │
└────────────────────────┘


┌────────────────────────┐
│     Position           │ (Value Object)
│  ────────────────────  │
│  - row: int [0-7]      │
│  - col: int [0-7]      │
│  ────────────────────  │
│  + equals()            │
│  + toString() "e4"     │
└────────────────────────┘


┌────────────────────────┐
│    Piece (Abstract)    │ ← Strategy Pattern
│  ────────────────────  │
│  - color: Color        │
│  - position: Position  │
│  - hasMoved: boolean   │
│  ────────────────────  │
│  + canMove(board, to)  │ ← Abstract
│  + getPossibleMoves()  │ ← Abstract
└────────┬───────────────┘
         │
    ┌────┴────┬─────┬──────┬────────┬────────┐
    │         │     │      │        │        │
┌───▼───┐ ┌──▼──┐ ┌▼───┐ ┌▼─────┐ ┌▼──────┐ ┌▼────┐
│ King  │ │Queen│ │Rook│ │Bishop│ │Knight │ │Pawn │
└───────┘ └─────┘ └────┘ └──────┘ └───────┘ └─────┘
  1 sq     8 dirs  H/V    Diag    L-shape   Complex


┌────────────────────────┐
│        Player          │
│  ────────────────────  │
│  - name: String        │
│  - color: Color        │
│  ────────────────────  │
└────────────────────────┘


┌────────────────────────┐
│        Move            │
│  ────────────────────  │
│  - from: Position      │
│  - to: Position        │
│  - piece: Piece        │
│  - capturedPiece: Piece│
│  - isCastling: boolean │
│  - isEnPassant: boolean│
│  ────────────────────  │
└────────────────────────┘


┌────────────────────────┐
│      Color (Enum)      │
│  ────────────────────  │
│  - WHITE               │
│  - BLACK               │
└────────────────────────┘


┌────────────────────────┐
│   GameStatus (Enum)    │
│  ────────────────────  │
│  - ACTIVE              │
│  - CHECK               │
│  - CHECKMATE           │
│  - STALEMATE           │
│  - DRAW                │
└────────────────────────┘
```

**Key Design Pattern: STRATEGY**
- Each piece type has its own movement strategy
- `canMove()` method is polymorphic

---

### Phase 4: Core Implementation (25 mins)

**You:** "Let me implement the key classes step by step:"

#### 1. Basic Enums and Value Objects

```java
public enum Color {
    WHITE,
    BLACK;
    
    public Color opposite() {
        return this == WHITE ? BLACK : WHITE;
    }
}

public enum GameStatus {
    ACTIVE,
    CHECK,
    CHECKMATE,
    STALEMATE,
    DRAW
}

public class Position {
    private final int row;
    private final int col;
    
    public Position(int row, int col) {
        if (row < 0 || row > 7 || col < 0 || col > 7) {
            throw new IllegalArgumentException("Invalid position");
        }
        this.row = row;
        this.col = col;
    }
    
    // Chess notation: a1, e4, etc.
    public static Position fromChessNotation(String notation) {
        if (notation.length() != 2) {
            throw new IllegalArgumentException("Invalid notation");
        }
        char file = notation.charAt(0); // a-h
        char rank = notation.charAt(1); // 1-8
        
        int col = file - 'a'; // 0-7
        int row = 8 - (rank - '0'); // Convert to 0-7 (row 0 = rank 8)
        
        return new Position(row, col);
    }
    
    public String toChessNotation() {
        char file = (char)('a' + col);
        char rank = (char)('8' - row);
        return "" + file + rank;
    }
    
    public int getRow() { return row; }
    public int getCol() { return col; }
    
    @Override
    public boolean equals(Object obj) {
        if (!(obj instanceof Position)) return false;
        Position other = (Position) obj;
        return this.row == other.row && this.col == other.col;
    }
    
    @Override
    public int hashCode() {
        return row * 8 + col;
    }
    
    @Override
    public String toString() {
        return toChessNotation();
    }
}
```

---

#### 2. Abstract Piece Class (Strategy Pattern)

```java
import java.util.ArrayList;
import java.util.List;

public abstract class Piece {
    protected Color color;
    protected Position position;
    protected boolean hasMoved;
    
    public Piece(Color color, Position position) {
        this.color = color;
        this.position = position;
        this.hasMoved = false;
    }
    
    // Strategy pattern - each piece implements its own movement logic
    public abstract boolean canMove(Board board, Position to);
    
    public abstract List<Position> getPossibleMoves(Board board);
    
    public abstract String getSymbol(); // K, Q, R, B, N, P
    
    // Check if path is clear (for Rook, Bishop, Queen)
    protected boolean isPathClear(Board board, Position from, Position to) {
        int rowDir = Integer.compare(to.getRow() - from.getRow(), 0);
        int colDir = Integer.compare(to.getCol() - from.getCol(), 0);
        
        int currentRow = from.getRow() + rowDir;
        int currentCol = from.getCol() + colDir;
        
        while (currentRow != to.getRow() || currentCol != to.getCol()) {
            if (!board.isEmpty(new Position(currentRow, currentCol))) {
                return false;
            }
            currentRow += rowDir;
            currentCol += colDir;
        }
        
        return true;
    }
    
    // Getters and setters
    public Color getColor() { return color; }
    public Position getPosition() { return position; }
    public boolean hasMoved() { return hasMoved; }
    
    public void setPosition(Position position) {
        this.position = position;
        this.hasMoved = true;
    }
    
    @Override
    public String toString() {
        return color + " " + getSymbol() + " at " + position;
    }
}
```

---

#### 3. Concrete Piece Classes

```java
// KING - Moves 1 square in any direction
public class King extends Piece {
    public King(Color color, Position position) {
        super(color, position);
    }
    
    @Override
    public boolean canMove(Board board, Position to) {
        int rowDiff = Math.abs(to.getRow() - position.getRow());
        int colDiff = Math.abs(to.getCol() - position.getCol());
        
        // King moves 1 square in any direction
        return (rowDiff <= 1 && colDiff <= 1) && (rowDiff + colDiff > 0);
    }
    
    @Override
    public List<Position> getPossibleMoves(Board board) {
        List<Position> moves = new ArrayList<>();
        int[] dr = {-1, -1, -1, 0, 0, 1, 1, 1};
        int[] dc = {-1, 0, 1, -1, 1, -1, 0, 1};
        
        for (int i = 0; i < 8; i++) {
            int newRow = position.getRow() + dr[i];
            int newCol = position.getCol() + dc[i];
            
            if (newRow >= 0 && newRow < 8 && newCol >= 0 && newCol < 8) {
                Position newPos = new Position(newRow, newCol);
                if (board.isEmpty(newPos) || 
                    board.getPiece(newPos).getColor() != this.color) {
                    moves.add(newPos);
                }
            }
        }
        
        return moves;
    }
    
    @Override
    public String getSymbol() { return "K"; }
}


// QUEEN - Moves horizontally, vertically, or diagonally
public class Queen extends Piece {
    public Queen(Color color, Position position) {
        super(color, position);
    }
    
    @Override
    public boolean canMove(Board board, Position to) {
        int rowDiff = Math.abs(to.getRow() - position.getRow());
        int colDiff = Math.abs(to.getCol() - position.getCol());
        
        // Must move in straight line or diagonal
        boolean isStraight = (rowDiff == 0 || colDiff == 0);
        boolean isDiagonal = (rowDiff == colDiff);
        
        if (!isStraight && !isDiagonal) return false;
        
        return isPathClear(board, position, to);
    }
    
    @Override
    public List<Position> getPossibleMoves(Board board) {
        List<Position> moves = new ArrayList<>();
        
        // 8 directions: horizontal, vertical, diagonal
        int[] dr = {-1, -1, -1, 0, 0, 1, 1, 1};
        int[] dc = {-1, 0, 1, -1, 1, -1, 0, 1};
        
        for (int dir = 0; dir < 8; dir++) {
            for (int step = 1; step < 8; step++) {
                int newRow = position.getRow() + dr[dir] * step;
                int newCol = position.getCol() + dc[dir] * step;
                
                if (newRow < 0 || newRow >= 8 || newCol < 0 || newCol >= 8) break;
                
                Position newPos = new Position(newRow, newCol);
                
                if (board.isEmpty(newPos)) {
                    moves.add(newPos);
                } else {
                    if (board.getPiece(newPos).getColor() != this.color) {
                        moves.add(newPos);
                    }
                    break; // Can't jump over pieces
                }
            }
        }
        
        return moves;
    }
    
    @Override
    public String getSymbol() { return "Q"; }
}


// ROOK - Moves horizontally or vertically
public class Rook extends Piece {
    public Rook(Color color, Position position) {
        super(color, position);
    }
    
    @Override
    public boolean canMove(Board board, Position to) {
        // Must move in straight line (same row or same column)
        boolean sameRow = (to.getRow() == position.getRow());
        boolean sameCol = (to.getCol() == position.getCol());
        
        if (!sameRow && !sameCol) return false;
        
        return isPathClear(board, position, to);
    }
    
    @Override
    public List<Position> getPossibleMoves(Board board) {
        List<Position> moves = new ArrayList<>();
        
        // 4 directions: up, down, left, right
        int[] dr = {-1, 1, 0, 0};
        int[] dc = {0, 0, -1, 1};
        
        for (int dir = 0; dir < 4; dir++) {
            for (int step = 1; step < 8; step++) {
                int newRow = position.getRow() + dr[dir] * step;
                int newCol = position.getCol() + dc[dir] * step;
                
                if (newRow < 0 || newRow >= 8 || newCol < 0 || newCol >= 8) break;
                
                Position newPos = new Position(newRow, newCol);
                
                if (board.isEmpty(newPos)) {
                    moves.add(newPos);
                } else {
                    if (board.getPiece(newPos).getColor() != this.color) {
                        moves.add(newPos);
                    }
                    break;
                }
            }
        }
        
        return moves;
    }
    
    @Override
    public String getSymbol() { return "R"; }
}


// BISHOP - Moves diagonally
public class Bishop extends Piece {
    public Bishop(Color color, Position position) {
        super(color, position);
    }
    
    @Override
    public boolean canMove(Board board, Position to) {
        int rowDiff = Math.abs(to.getRow() - position.getRow());
        int colDiff = Math.abs(to.getCol() - position.getCol());
        
        // Must move diagonally
        if (rowDiff != colDiff) return false;
        
        return isPathClear(board, position, to);
    }
    
    @Override
    public List<Position> getPossibleMoves(Board board) {
        List<Position> moves = new ArrayList<>();
        
        // 4 diagonal directions
        int[] dr = {-1, -1, 1, 1};
        int[] dc = {-1, 1, -1, 1};
        
        for (int dir = 0; dir < 4; dir++) {
            for (int step = 1; step < 8; step++) {
                int newRow = position.getRow() + dr[dir] * step;
                int newCol = position.getCol() + dc[dir] * step;
                
                if (newRow < 0 || newRow >= 8 || newCol < 0 || newCol >= 8) break;
                
                Position newPos = new Position(newRow, newCol);
                
                if (board.isEmpty(newPos)) {
                    moves.add(newPos);
                } else {
                    if (board.getPiece(newPos).getColor() != this.color) {
                        moves.add(newPos);
                    }
                    break;
                }
            }
        }
        
        return moves;
    }
    
    @Override
    public String getSymbol() { return "B"; }
}


// KNIGHT - Moves in L-shape
public class Knight extends Piece {
    public Knight(Color color, Position position) {
        super(color, position);
    }
    
    @Override
    public boolean canMove(Board board, Position to) {
        int rowDiff = Math.abs(to.getRow() - position.getRow());
        int colDiff = Math.abs(to.getCol() - position.getCol());
        
        // L-shape: 2+1 or 1+2
        return (rowDiff == 2 && colDiff == 1) || (rowDiff == 1 && colDiff == 2);
    }
    
    @Override
    public List<Position> getPossibleMoves(Board board) {
        List<Position> moves = new ArrayList<>();
        
        // 8 possible L-shaped moves
        int[] dr = {-2, -2, -1, -1, 1, 1, 2, 2};
        int[] dc = {-1, 1, -2, 2, -2, 2, -1, 1};
        
        for (int i = 0; i < 8; i++) {
            int newRow = position.getRow() + dr[i];
            int newCol = position.getCol() + dc[i];
            
            if (newRow >= 0 && newRow < 8 && newCol >= 0 && newCol < 8) {
                Position newPos = new Position(newRow, newCol);
                if (board.isEmpty(newPos) || 
                    board.getPiece(newPos).getColor() != this.color) {
                    moves.add(newPos);
                }
            }
        }
        
        return moves;
    }
    
    @Override
    public String getSymbol() { return "N"; }
}


// PAWN - Most complex piece!
public class Pawn extends Piece {
    public Pawn(Color color, Position position) {
        super(color, position);
    }
    
    @Override
    public boolean canMove(Board board, Position to) {
        int direction = (color == Color.WHITE) ? -1 : 1; // White moves up, Black moves down
        int rowDiff = to.getRow() - position.getRow();
        int colDiff = Math.abs(to.getCol() - position.getCol());
        
        // Move forward 1 square
        if (colDiff == 0 && rowDiff == direction && board.isEmpty(to)) {
            return true;
        }
        
        // Move forward 2 squares (initial move)
        if (!hasMoved && colDiff == 0 && rowDiff == 2 * direction) {
            Position middle = new Position(position.getRow() + direction, position.getCol());
            return board.isEmpty(middle) && board.isEmpty(to);
        }
        
        // Capture diagonally
        if (colDiff == 1 && rowDiff == direction && !board.isEmpty(to)) {
            return board.getPiece(to).getColor() != this.color;
        }
        
        return false;
    }
    
    @Override
    public List<Position> getPossibleMoves(Board board) {
        List<Position> moves = new ArrayList<>();
        int direction = (color == Color.WHITE) ? -1 : 1;
        
        // Forward 1
        int newRow = position.getRow() + direction;
        if (newRow >= 0 && newRow < 8) {
            Position forward = new Position(newRow, position.getCol());
            if (board.isEmpty(forward)) {
                moves.add(forward);
                
                // Forward 2 (initial move)
                if (!hasMoved) {
                    Position forward2 = new Position(newRow + direction, position.getCol());
                    if (board.isEmpty(forward2)) {
                        moves.add(forward2);
                    }
                }
            }
        }
        
        // Diagonal captures
        for (int colOffset : new int[]{-1, 1}) {
            int newCol = position.getCol() + colOffset;
            if (newRow >= 0 && newRow < 8 && newCol >= 0 && newCol < 8) {
                Position diagonal = new Position(newRow, newCol);
                if (!board.isEmpty(diagonal) && 
                    board.getPiece(diagonal).getColor() != this.color) {
                    moves.add(diagonal);
                }
            }
        }
        
        return moves;
    }
    
    @Override
    public String getSymbol() { return "P"; }
}
```

---

#### 4. Board Class

```java
public class Board {
    private Piece[][] cells;
    
    public Board() {
        cells = new Piece[8][8];
    }
    
    public Piece getPiece(Position pos) {
        return cells[pos.getRow()][pos.getCol()];
    }
    
    public void setPiece(Position pos, Piece piece) {
        cells[pos.getRow()][pos.getCol()] = piece;
        if (piece != null) {
            piece.setPosition(pos);
        }
    }
    
    public boolean isEmpty(Position pos) {
        return getPiece(pos) == null;
    }
    
    public Piece removePiece(Position pos) {
        Piece piece = getPiece(pos);
        cells[pos.getRow()][pos.getCol()] = null;
        return piece;
    }
    
    public void movePiece(Position from, Position to) {
        Piece piece = removePiece(from);
        setPiece(to, piece);
    }
    
    // Get all pieces of a specific color
    public List<Piece> getAllPieces(Color color) {
        List<Piece> pieces = new ArrayList<>();
        for (int row = 0; row < 8; row++) {
            for (int col = 0; col < 8; col++) {
                Piece piece = cells[row][col];
                if (piece != null && piece.getColor() == color) {
                    pieces.add(piece);
                }
            }
        }
        return pieces;
    }
    
    // Find king position
    public Position findKing(Color color) {
        for (int row = 0; row < 8; row++) {
            for (int col = 0; col < 8; col++) {
                Piece piece = cells[row][col];
                if (piece instanceof King && piece.getColor() == color) {
                    return new Position(row, col);
                }
            }
        }
        return null;
    }
    
    // Initialize standard chess board
    public void initializeBoard() {
        // Place pawns
        for (int col = 0; col < 8; col++) {
            setPiece(new Position(1, col), new Pawn(Color.BLACK, new Position(1, col)));
            setPiece(new Position(6, col), new Pawn(Color.WHITE, new Position(6, col)));
        }
        
        // Place rooks
        setPiece(new Position(0, 0), new Rook(Color.BLACK, new Position(0, 0)));
        setPiece(new Position(0, 7), new Rook(Color.BLACK, new Position(0, 7)));
        setPiece(new Position(7, 0), new Rook(Color.WHITE, new Position(7, 0)));
        setPiece(new Position(7, 7), new Rook(Color.WHITE, new Position(7, 7)));
        
        // Place knights
        setPiece(new Position(0, 1), new Knight(Color.BLACK, new Position(0, 1)));
        setPiece(new Position(0, 6), new Knight(Color.BLACK, new Position(0, 6)));
        setPiece(new Position(7, 1), new Knight(Color.WHITE, new Position(7, 1)));
        setPiece(new Position(7, 6), new Knight(Color.WHITE, new Position(7, 6)));
        
        // Place bishops
        setPiece(new Position(0, 2), new Bishop(Color.BLACK, new Position(0, 2)));
        setPiece(new Position(0, 5), new Bishop(Color.BLACK, new Position(0, 5)));
        setPiece(new Position(7, 2), new Bishop(Color.WHITE, new Position(7, 2)));
        setPiece(new Position(7, 5), new Bishop(Color.WHITE, new Position(7, 5)));
        
        // Place queens
        setPiece(new Position(0, 3), new Queen(Color.BLACK, new Position(0, 3)));
        setPiece(new Position(7, 3), new Queen(Color.WHITE, new Position(7, 3)));
        
        // Place kings
        setPiece(new Position(0, 4), new King(Color.BLACK, new Position(0, 4)));
        setPiece(new Position(7, 4), new King(Color.WHITE, new Position(7, 4)));
    }
    
    public void display() {
        System.out.println("\n  a b c d e f g h");
        for (int row = 0; row < 8; row++) {
            System.out.print((8 - row) + " ");
            for (int col = 0; col < 8; col++) {
                Piece piece = cells[row][col];
                if (piece == null) {
                    System.out.print(". ");
                } else {
                    String symbol = piece.getSymbol();
                    if (piece.getColor() == Color.BLACK) {
                        symbol = symbol.toLowerCase();
                    }
                    System.out.print(symbol + " ");
                }
            }
            System.out.println((8 - row));
        }
        System.out.println("  a b c d e f g h\n");
    }
}
```

---

#### 5. Move Class

```java
public class Move {
    private Position from;
    private Position to;
    private Piece piece;
    private Piece capturedPiece;
    
    public Move(Position from, Position to, Piece piece, Piece capturedPiece) {
        this.from = from;
        this.to = to;
        this.piece = piece;
        this.capturedPiece = capturedPiece;
    }
    
    public Position getFrom() { return from; }
    public Position getTo() { return to; }
    public Piece getPiece() { return piece; }
    public Piece getCapturedPiece() { return capturedPiece; }
    
    @Override
    public String toString() {
        String notation = piece.getSymbol() + from.toChessNotation() + 
                         (capturedPiece != null ? "x" : "-") + 
                         to.toChessNotation();
        return notation;
    }
}
```

---

#### 6. Game Class (Main Controller)

```java
import java.util.ArrayList;
import java.util.List;

public class Game {
    private Board board;
    private Color currentTurn;
    private GameStatus status;
    private List<Move> moveHistory;
    
    public Game() {
        this.board = new Board();
        board.initializeBoard();
        this.currentTurn = Color.WHITE;
        this.status = GameStatus.ACTIVE;
        this.moveHistory = new ArrayList<>();
    }
    
    // Make a move
    public boolean makeMove(Position from, Position to) {
        Piece piece = board.getPiece(from);
        
        // Validation
        if (piece == null) {
            System.out.println("No piece at " + from);
            return false;
        }
        
        if (piece.getColor() != currentTurn) {
            System.out.println("Not your turn!");
            return false;
        }
        
        if (!piece.canMove(board, to)) {
            System.out.println("Invalid move for " + piece.getSymbol());
            return false;
        }
        
        Piece targetPiece = board.getPiece(to);
        if (targetPiece != null && targetPiece.getColor() == currentTurn) {
            System.out.println("Cannot capture own piece!");
            return false;
        }
        
        // Simulate move and check if king is in check
        Piece capturedPiece = simulateMove(from, to);
        if (isKingInCheck(currentTurn)) {
            undoSimulation(from, to, piece, capturedPiece);
            System.out.println("Move would put your king in check!");
            return false;
        }
        undoSimulation(from, to, piece, capturedPiece);
        
        // Execute move
        capturedPiece = board.getPiece(to);
        board.movePiece(from, to);
        
        // Record move
        moveHistory.add(new Move(from, to, piece, capturedPiece));
        
        // Check for check/checkmate
        currentTurn = currentTurn.opposite();
        updateGameStatus();
        
        System.out.println("Move: " + from + " → " + to);
        if (capturedPiece != null) {
            System.out.println("Captured: " + capturedPiece.getSymbol());
        }
        
        return true;
    }
    
    // Simulate move (for check validation)
    private Piece simulateMove(Position from, Position to) {
        Piece capturedPiece = board.getPiece(to);
        board.movePiece(from, to);
        return capturedPiece;
    }
    
    // Undo simulation
    private void undoSimulation(Position from, Position to, Piece piece, Piece captured) {
        board.setPiece(from, piece);
        board.setPiece(to, captured);
    }
    
    // Check if king is in check
    private boolean isKingInCheck(Color color) {
        Position kingPos = board.findKing(color);
        if (kingPos == null) return false;
        
        // Check if any opponent piece can attack the king
        Color opponentColor = color.opposite();
        List<Piece> opponentPieces = board.getAllPieces(opponentColor);
        
        for (Piece piece : opponentPieces) {
            if (piece.canMove(board, kingPos)) {
                return true;
            }
        }
        
        return false;
    }
    
    // Check if player has any valid moves
    private boolean hasValidMoves(Color color) {
        List<Piece> pieces = board.getAllPieces(color);
        
        for (Piece piece : pieces) {
            List<Position> possibleMoves = piece.getPossibleMoves(board);
            
            for (Position to : possibleMoves) {
                Position from = piece.getPosition();
                Piece captured = simulateMove(from, to);
                
                boolean inCheck = isKingInCheck(color);
                
                undoSimulation(from, to, piece, captured);
                
                if (!inCheck) {
                    return true; // Found a valid move
                }
            }
        }
        
        return false;
    }
    
    // Update game status after move
    private void updateGameStatus() {
        if (isKingInCheck(currentTurn)) {
            if (!hasValidMoves(currentTurn)) {
                status = GameStatus.CHECKMATE;
                System.out.println("\n*** CHECKMATE! " + currentTurn.opposite() + " wins! ***");
            } else {
                status = GameStatus.CHECK;
                System.out.println("\n*** CHECK! ***");
            }
        } else {
            if (!hasValidMoves(currentTurn)) {
                status = GameStatus.STALEMATE;
                System.out.println("\n*** STALEMATE! Draw! ***");
            } else {
                status = GameStatus.ACTIVE;
            }
        }
    }
    
    public void displayBoard() {
        board.display();
        System.out.println("Turn: " + currentTurn);
        System.out.println("Status: " + status);
    }
    
    public Color getCurrentTurn() { return currentTurn; }
    public GameStatus getStatus() { return status; }
    public List<Move> getMoveHistory() { return moveHistory; }
}
```

---

### Phase 5: Demo (3 mins)

**You:** "Here's a working game:"

```java
public class ChessDemo {
    public static void main(String[] args) {
        System.out.println("╔════════════════════════════════════╗");
        System.out.println("║         CHESS GAME DEMO            ║");
        System.out.println("╚════════════════════════════════════╝");
        
        Game game = new Game();
        game.displayBoard();
        
        // Scholar's Mate - fastest checkmate
        System.out.println("\n=== Scholar's Mate Demo ===\n");
        
        // 1. e4
        game.makeMove(Position.fromChessNotation("e2"), 
                     Position.fromChessNotation("e4"));
        game.displayBoard();
        
        // 1... e5
        game.makeMove(Position.fromChessNotation("e7"),
                     Position.fromChessNotation("e5"));
        game.displayBoard();
        
        // 2. Bc4
        game.makeMove(Position.fromChessNotation("f1"),
                     Position.fromChessNotation("c4"));
        game.displayBoard();
        
        // 2... Nc6
        game.makeMove(Position.fromChessNotation("b8"),
                     Position.fromChessNotation("c6"));
        game.displayBoard();
        
        // 3. Qh5
        game.makeMove(Position.fromChessNotation("d1"),
                     Position.fromChessNotation("h5"));
        game.displayBoard();
        
        // 3... Nf6??
        game.makeMove(Position.fromChessNotation("g8"),
                     Position.fromChessNotation("f6"));
        game.displayBoard();
        
        // 4. Qxf7# CHECKMATE!
        game.makeMove(Position.fromChessNotation("h5"),
                     Position.fromChessNotation("f7"));
        game.displayBoard();
        
        System.out.println("\n=== Move History ===");
        for (Move move : game.getMoveHistory()) {
            System.out.println(move);
        }
    }
}
```

---

### Phase 6: Design Patterns Used (2 mins)

**You:** "Here are the patterns I used:"

```
┌──────────────────────────────────────────────────────────────┐
│                  DESIGN PATTERNS                             │
└──────────────────────────────────────────────────────────────┘

1. STRATEGY PATTERN ⭐⭐⭐
   ═══════════════════════════════════════════════════════════
   - Each piece has its own movement strategy
   - canMove() and getPossibleMoves() are polymorphic
   - Easy to add new piece types
   
   abstract class Piece {
       abstract boolean canMove(Board, Position);
   }
   
   King, Queen, Rook, Bishop, Knight, Pawn extend Piece


2. TEMPLATE METHOD (in Piece class)
   ═══════════════════════════════════════════════════════════
   - isPathClear() is shared logic for sliding pieces
   - Rook, Bishop, Queen reuse this method


3. FACADE PATTERN
   ═══════════════════════════════════════════════════════════
   - Game class is the facade
   - Hides complexity of Board, Pieces, Move validation
   - Simple API: makeMove(), displayBoard()


4. COMMAND PATTERN (Move class)
   ═══════════════════════════════════════════════════════════
   - Move is a command object
   - Can be stored, undone, replayed
   - Enables move history, undo/redo


5. VALUE OBJECT (Position)
   ═══════════════════════════════════════════════════════════
   - Immutable
   - Equals/hashCode implemented
   - Can be used as map key
```

---

## KEY TAKEAWAYS

### Core Algorithms:
✅ **Move validation** - Each piece has unique rules
✅ **Check detection** - Simulate all opponent moves
✅ **Checkmate detection** - No valid moves + in check
✅ **Path validation** - For sliding pieces (Rook, Bishop, Queen)

### SOLID Principles:
✅ **Single Responsibility** - Each piece handles its own movement
✅ **Open/Closed** - Easy to add new pieces (Grasshopper, Nightrider)
✅ **Liskov Substitution** - All pieces can be treated as Piece
✅ **Interface Segregation** - Minimal interfaces
✅ **Dependency Inversion** - Game depends on abstract Piece

---

## FOLLOW-UP QUESTIONS

**Interviewer:** "How would you add castling?"

**You:**
```java
// In King class
public boolean canCastle(Board board, Position rookPos) {
    // Both king and rook must not have moved
    if (this.hasMoved) return false;
    
    Piece rook = board.getPiece(rookPos);
    if (!(rook instanceof Rook) || rook.hasMoved()) return false;
    
    // Path between king and rook must be empty
    // King must not be in check
    // King must not pass through check
    // King must not end in check
    
    return true;
}
```

**Interviewer:** "How would you add AI?"

**You:** "Use **Minimax algorithm** with alpha-beta pruning:"
```java
public interface Player {
    Move getNextMove(Board board);
}

public class HumanPlayer implements Player {
    // Read from input
}

public class AIPlayer implements Player {
    public Move getNextMove(Board board) {
        return minimax(board, depth, true).move;
    }
    
    private MoveScore minimax(Board board, int depth, boolean isMaximizing) {
        // Evaluate board position
        // Try all possible moves
        // Return best move
    }
}
```

---

## SOLID PRINCIPLES IN DEPTH

**You:** "Let me explain how SOLID principles make this chess game design elegant and extensible."

---

### 1. Single Responsibility Principle (SRP)

**Purpose:** Each class should have only ONE reason to change.

**Problem it solves:**
Without SRP, game logic becomes a tangled mess:
```java
// BAD: Game class doing everything
class Game {
    // Board management
    public void initializeBoard() { ... }
    
    // Move validation
    public boolean isValidMove(Piece piece, Position to) { ... }
    
    // Piece movement logic
    public boolean canKingMove(Position from, Position to) { ... }
    public boolean canQueenMove(Position from, Position to) { ... }
    
    // Check/checkmate detection
    public boolean isCheck() { ... }
    public boolean isCheckmate() { ... }
    
    // UI rendering
    public void displayBoard() { ... }
}
// Too many responsibilities! Changing king movement affects the Game class.
```

**Advantages:**
- ✅ **Clear ownership** - Each class has one clear job
- ✅ **Easy to test** - Test piece movement separately from check detection
- ✅ **Parallel development** - Different devs work on different pieces
- ✅ **Localized changes** - Fix knight movement without touching Game class

**In our design:**
```java
// GOOD: Separated responsibilities

// Piece: ONLY knows HOW to move (Strategy pattern)
abstract class Piece {
    public abstract boolean canMove(Board board, Position to);
    public abstract List<Position> getPossibleMoves(Board board);
}

class King extends Piece {
    @Override
    public boolean canMove(Board board, Position to) {
        // ONLY king movement rules
    }
}

// Board: ONLY manages the 8x8 grid and pieces
class Board {
    private Piece[][] cells;
    
    public Piece getPiece(Position pos) { ... }
    public void movePiece(Position from, Position to) { ... }
}

// Game: ONLY coordinates the game flow (Facade)
class Game {
    public boolean makeMove(Position from, Position to) { ... }
}

// Move: ONLY stores move data
class Move {
    private Position from, to;
    private Piece piece;
    private Piece capturedPiece;
}

// Position: ONLY represents coordinates (Value Object)
class Position {
    private final int row, col;
}
```

**Interview tip:** "If I need to change how a Knight moves, I only touch the `Knight` class. If I need to add castling, I add it to `King` class. Each class has one clear responsibility."

---

### 2. Open/Closed Principle (OCP)

**Purpose:** Classes should be OPEN for extension but CLOSED for modification.

**Problem it solves:**
Without OCP, adding pieces requires modifying existing code:
```java
// BAD: Hard-coded piece movement logic
class Game {
    public boolean isValidMove(Piece piece, Position from, Position to) {
        if (piece.getType() == PieceType.KING) {
            // King movement logic
        } else if (piece.getType() == PieceType.QUEEN) {
            // Queen movement logic
        } else if (piece.getType() == PieceType.KNIGHT) {
            // Knight movement logic
        }
        // To add Grasshopper piece, you must MODIFY this method - RISKY!
    }
}
```

**Advantages:**
- ✅ **Zero regression** - Existing pieces unaffected
- ✅ **Easy to add pieces** - Just create new piece class
- ✅ **Chess variants** - Add fairy chess pieces without changing core
- ✅ **Stable core** - Game logic never changes

**In our design:**
```java
// GOOD: Polymorphic piece design

abstract class Piece {
    public abstract boolean canMove(Board board, Position to);
    public abstract List<Position> getPossibleMoves(Board board);
    public abstract String getSymbol();
}

class King extends Piece {
    @Override
    public boolean canMove(Board board, Position to) {
        // King-specific logic
    }
}

class Queen extends Piece {
    @Override
    public boolean canMove(Board board, Position to) {
        // Queen-specific logic
    }
}

class Knight extends Piece {
    @Override
    public boolean canMove(Board board, Position to) {
        // Knight-specific logic
    }
}

// NEW: Add Grasshopper for fairy chess - zero changes to existing code!
class Grasshopper extends Piece {
    @Override
    public boolean canMove(Board board, Position to) {
        // Grasshopper jumps over pieces
    }
    
    @Override
    public String getSymbol() { return "G"; }
}

// Game class uses polymorphism:
class Game {
    public boolean makeMove(Position from, Position to) {
        Piece piece = board.getPiece(from);
        
        // Works for ANY piece - King, Queen, Knight, Grasshopper!
        if (!piece.canMove(board, to)) {
            return false;
        }
        
        board.movePiece(from, to);
        return true;
    }
}
```

**Interview tip:** "To add a new piece like Grasshopper, I create `Grasshopper extends Piece` with its movement rules. Zero changes to `Game` or `Board` classes. The system is closed for modification but open for extension."

---

### 3. Liskov Substitution Principle (LSP)

**Purpose:** Subclasses must be substitutable for their parent classes without breaking behavior.

**Problem it solves:**
Without LSP, some pieces violate contracts:
```java
// BAD: Violates LSP
abstract class Piece {
    public abstract boolean canMove(Board board, Position to);
    // Contract: Returns true if move is legal for this piece type
}

class King extends Piece {
    @Override
    public boolean canMove(Board board, Position to) {
        // Returns true/false based on king movement rules
    }
}

class BrokenPiece extends Piece {
    @Override
    public boolean canMove(Board board, Position to) {
        throw new UnsupportedOperationException("Not implemented!");  // BREAKS CONTRACT!
    }
}

// Code expecting boolean will crash:
Piece piece = new BrokenPiece();
if (piece.canMove(board, position)) {  // BOOM! Exception instead of boolean
    board.movePiece(from, position);
}
```

**Advantages:**
- ✅ **Predictable behavior** - All pieces work the same way
- ✅ **Polymorphism works** - Can treat all pieces uniformly
- ✅ **Testing is easy** - Mock pieces behave like real ones
- ✅ **No surprises** - Code doesn't break when switching implementations

**In our design:**
```java
// GOOD: All pieces honor the contract

abstract class Piece {
    public abstract boolean canMove(Board board, Position to);
    public abstract List<Position> getPossibleMoves(Board board);
    // Contract: Always returns boolean/list, never throws
}

class King extends Piece {
    @Override
    public boolean canMove(Board board, Position to) {
        int rowDiff = Math.abs(to.getRow() - position.getRow());
        int colDiff = Math.abs(to.getCol() - position.getCol());
        return (rowDiff <= 1 && colDiff <= 1);  // ✓ Returns boolean
    }
    
    @Override
    public List<Position> getPossibleMoves(Board board) {
        List<Position> moves = new ArrayList<>();
        // Add all valid king moves
        return moves;  // ✓ Returns list, never null
    }
}

class Queen extends Piece {
    @Override
    public boolean canMove(Board board, Position to) {
        // Queen movement logic
        return isValidQueenMove;  // ✓ Returns boolean
    }
    
    @Override
    public List<Position> getPossibleMoves(Board board) {
        List<Position> moves = new ArrayList<>();
        // Add all valid queen moves
        return moves;  // ✓ Returns list, never null
    }
}

// Polymorphism works perfectly:
Piece piece = board.getPiece(position);  // Could be King, Queen, Knight, etc.
if (piece.canMove(board, targetPosition)) {  // Works for ANY piece
    board.movePiece(position, targetPosition);
}
```

**Interview tip:** "Any code that works with `Piece` will work with `King`, `Queen`, `Knight`, or any future piece. They all honor the contract - `canMove()` always returns a boolean, `getPossibleMoves()` always returns a list."

---

### 4. Interface Segregation Principle (ISP)

**Purpose:** Clients should not be forced to depend on interfaces they don't use.

**Problem it solves:**
Without ISP, interfaces force unnecessary dependencies:
```java
// BAD: Fat interface forces implementations of unused methods
interface Piece {
    boolean canMove(Board board, Position to);
    List<Position> getPossibleMoves(Board board);
    boolean canCastle();              // Only King/Rook can castle
    boolean canEnPassant();           // Only Pawn can do en passant
    boolean canPromote();             // Only Pawn can promote
    int getMaterialValue();           // For AI evaluation
    boolean isSliding();              // For rendering
}

// Knight must implement ALL methods!
class Knight implements Piece {
    @Override
    public boolean canCastle() { 
        throw new UnsupportedOperationException();  // Forced!
    }
    
    @Override
    public boolean canEnPassant() {
        throw new UnsupportedOperationException();  // Forced!
    }
}
```

**Advantages:**
- ✅ **Lean interfaces** - Only necessary methods
- ✅ **Better cohesion** - Related methods together
- ✅ **No dummy code** - No forced implementations
- ✅ **Clear contracts** - Interface tells you what to expect

**In our design:**
```java
// GOOD: Segregated interfaces

// Core: Every piece must implement this
interface Piece {
    boolean canMove(Board board, Position to);
    List<Position> getPossibleMoves(Board board);
    Color getColor();
    Position getPosition();
}

// Optional: Only for pieces with special moves
interface CastlingCapable {
    boolean canCastle(Board board, Position kingTarget, Position rookPos);
}

interface PromotionCapable {
    Piece promoteTo(PieceType newType);
}

interface EnPassantCapable {
    boolean canEnPassant(Board board, Position targetPos);
}

// Optional: For AI evaluation
interface Valuable {
    int getMaterialValue();
}

// Implement only what you need:

// Knight: Just core interface
abstract class Knight implements Piece {
    // Only movement methods - nothing else!
}

// King: Core + Castling
class King implements Piece, CastlingCapable {
    @Override
    public boolean canCastle(Board board, Position kingTarget, Position rookPos) {
        // Castling logic for king
    }
}

// Pawn: Core + Promotion + EnPassant
class Pawn implements Piece, PromotionCapable, EnPassantCapable {
    @Override
    public Piece promoteTo(PieceType newType) {
        // Create Queen/Rook/Bishop/Knight
    }
    
    @Override
    public boolean canEnPassant(Board board, Position targetPos) {
        // En passant logic
    }
}

// AI-enhanced pieces: Core + Valuable
class AIQueen implements Piece, Valuable {
    @Override
    public int getMaterialValue() { return 9; }
}
```

**Interview tip:** "Core interface has only movement methods. If a piece can castle, it implements `CastlingCapable`. If it can promote, it implements `PromotionCapable`. Clients depend only on what they need."

---

### 5. Dependency Inversion Principle (DIP)

**Purpose:** High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Problem it solves:**
Without DIP, high-level code is tightly coupled:
```java
// BAD: Game tightly coupled to concrete pieces
class Game {
    private King whiteKing = new King(Color.WHITE, startPos);  // TIGHT COUPLING!
    private Queen whiteQueen = new Queen(Color.WHITE, startPos);  // TIGHT COUPLING!
    
    public boolean makeMove(Position from, Position to) {
        // Hard to test with mock pieces
        // Hard to add new piece types
    }
}
```

**Advantages:**
- ✅ **Loose coupling** - Easy to swap pieces
- ✅ **Testability** - Inject mock pieces for testing
- ✅ **Flexibility** - Add new pieces without changing Game
- ✅ **Maintainability** - Low-level changes don't affect high-level

**In our design:**
```java
// GOOD: Depend on abstraction (abstract class/interface)

abstract class Piece {
    public abstract boolean canMove(Board board, Position to);
    public abstract List<Position> getPossibleMoves(Board board);
}

class King extends Piece { ... }
class Queen extends Piece { ... }
class Knight extends Piece { ... }

class Board {
    private Piece[][] cells;  // Abstract type, not concrete!
    
    public Piece getPiece(Position pos) {
        return cells[pos.getRow()][pos.getCol()];  // Returns abstract Piece
    }
    
    public void setPiece(Position pos, Piece piece) {  // Accepts abstract Piece
        cells[pos.getRow()][pos.getCol()] = piece;
    }
}

class Game {
    private Board board;  // Depends on Board abstraction
    
    public boolean makeMove(Position from, Position to) {
        Piece piece = board.getPiece(from);  // Abstract type!
        
        if (!piece.canMove(board, to)) {  // Polymorphic call - don't care about concrete type!
            return false;
        }
        
        board.movePiece(from, to);
        return true;
    }
}

// Can initialize with any piece implementation:
board.setPiece(new Position(0, 4), new King(Color.BLACK, new Position(0, 4)));
board.setPiece(new Position(0, 3), new Queen(Color.BLACK, new Position(0, 3)));
board.setPiece(new Position(0, 2), new CustomPiece(Color.BLACK, new Position(0, 2)));  // NEW piece type!

// For testing - inject mock pieces:
class MockPiece extends Piece {
    private boolean shouldAllowMove = true;
    
    @Override
    public boolean canMove(Board board, Position to) {
        return shouldAllowMove;  // Controllable for testing
    }
    
    @Override
    public List<Position> getPossibleMoves(Board board) {
        return Arrays.asList(new Position(4, 4));  // Predictable for testing
    }
}

// Test game logic with mock pieces:
Board testBoard = new Board();
testBoard.setPiece(new Position(0, 0), new MockPiece());
Game testGame = new Game(testBoard);
```

**Interview tip:** "Game and Board don't know if they're working with King, Queen, or a custom piece - they just call methods on the abstract `Piece` type. I can add new pieces without modifying Game. For testing, I inject mock pieces that return predictable values."

---

## COMMON MISTAKES TO AVOID

❌ Not checking if move puts own king in check
❌ Forgetting path validation for sliding pieces
❌ Not handling turn-based logic correctly
❌ Inefficient check detection (O(n²))
❌ Mutable Position class (should be immutable)
❌ Not tracking hasMoved for pawns, king, rook (castling)

---

## COMPLEXITY ANALYSIS

**Move Validation:**
- Time: O(1) for most pieces, O(n) for sliding pieces
- Space: O(1)

**Check Detection:**
- Time: O(n) where n = number of opponent pieces
- Space: O(1)

**Checkmate Detection:**
- Time: O(n * m) where n = pieces, m = avg moves per piece
- Space: O(1) if simulating in-place

---

## KEY TAKEAWAYS

### SOLID Principles Applied:
✅ **Single Responsibility (SRP)** - Piece handles movement, Board manages grid, Game coordinates flow, Move stores data
✅ **Open/Closed (OCP)** - Add new pieces by creating new subclasses, zero changes to Game/Board
✅ **Liskov Substitution (LSP)** - All Piece subclasses are interchangeable in Game logic
✅ **Interface Segregation (ISP)** - Separate interfaces for core Piece, CastlingCapable, PromotionCapable, EnPassantCapable
✅ **Dependency Inversion (DIP)** - Game and Board depend on abstract Piece, not concrete King/Queen/Knight

---

## EXTENSIONS

✅ Undo/Redo - Store Move objects with captured pieces
✅ Save/Load - Serialize board state (FEN notation)
✅ Timer - Add time per player (blitz, rapid, classical)
✅ AI - Minimax with alpha-beta pruning
✅ Promotion - When pawn reaches end, promote to Queen/Rook/etc.
✅ En Passant - Special pawn capture
✅ Draw conditions - 50-move rule, threefold repetition

---

**END OF CHESS GAME GUIDE**

This is the most complex LLD - demonstrates Strategy Pattern beautifully!
