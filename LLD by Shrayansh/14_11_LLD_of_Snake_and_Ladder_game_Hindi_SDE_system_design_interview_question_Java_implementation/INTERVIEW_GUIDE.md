# 🐍 Snake and Ladder - Low Level Design Interview Guide
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

## **Design Pattern Used**: None required, but Strategy for dice + O(1) jump lookup

**Interviewer**: "Design Snake and Ladder game."

**You**: "Simple game, but let me show depth via efficient data structures. Key insight: **Snake and Ladder jumps should be O(1) lookup, not iterative searching.**"

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                SNAKE AND LADDER ARCHITECTURE                         │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────┐
                    │       GAME        │
                    │                  │
                    │  Board           │
                    │  Players[]       │
                    │  Dice            │
                    │  CurrentPlayer   │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │    BOARD     │ │    DICE      │ │   PLAYER     │
    │              │ │              │ │              │
    │ Size: 100    │ │ Sides: 6     │ │ CurrentPos   │
    │ jumps: Map   │ │ roll()       │ │ Name         │
    │ <Int,Int>    │ │              │ │              │
    └──────────────┘ └──────────────┘ └──────────────┘

    O(1) JUMP LOOKUP (Key Optimization):
    ┌────────────────────────────────────┐
    │  Map<Integer, Integer> jumps        │
    │                                      │
    │  Snakes: jumps.put(99, 12)  // Head→Tail
    │  Ladders: jumps.put(3, 90)  // Bottom→Top
    │                                      │
    │  int finalPosition(int pos) {       │
    │    return jumps.getOrDefault(pos, pos);
    │  }  // O(1) instead of iterating!    │
    └────────────────────────────────────┘
```

---

## 2. API Design

```http
POST /api/v1/games
Request: {"boardSize": 100, "players": ["player1", "player2"]}
Response: 201 CREATED
{"gameId": "game-1234", "currentTurn": "player1", "positions": {"player1": 0, "player2": 0}}

---

POST /api/v1/games/{gameId}/roll
Request: {"playerId": "player1"}
Response: 200 OK
{
  "diceValue": 5,
  "previousPosition": 0,
  "intermediatePosition": 5,
  "finalPosition": 90,  // Landed on ladder bottom!
  "event": "LADDER_CLIMB",
  "nextTurn": "player2"
}

// Winning move:
Response: 200 OK
{
  "diceValue": 6,
  "finalPosition": 100,
  "gameStatus": "COMPLETED",
  "winner": "player1"
}
```

---

## 3. ER Diagram & Database Design

```sql
CREATE TABLE games (
    game_id VARCHAR(50) PRIMARY KEY,
    board_size INT DEFAULT 100,
    status VARCHAR(20) DEFAULT 'IN_PROGRESS',
    winner_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE board_jumps (
    game_id VARCHAR(50) NOT NULL,
    start_position INT NOT NULL,
    end_position INT NOT NULL,
    jump_type VARCHAR(10) NOT NULL,  -- SNAKE or LADDER
    
    PRIMARY KEY (game_id, start_position),
    CHECK (jump_type = 'SNAKE' AND end_position < start_position 
           OR jump_type = 'LADDER' AND end_position > start_position)
);

CREATE TABLE player_moves (
    move_id VARCHAR(50) PRIMARY KEY,
    game_id VARCHAR(50) NOT NULL,
    player_id VARCHAR(50) NOT NULL,
    dice_value INT NOT NULL,
    position_before INT NOT NULL,
    position_after INT NOT NULL,
    move_number INT NOT NULL,
    
    FOREIGN KEY (game_id) REFERENCES games(game_id),
    INDEX idx_game_move (game_id, move_number)
);
```

---

## 4. Sequence Diagrams

```
Player   Game    Dice   Board   JumpMap
  │        │        │       │       │
  │─roll()▶│        │       │       │
  │        ├─roll()─▶│       │       │
  │        │◀value=5─│       │       │
  │        │        │       │       │
  │        │  newPos = currentPos + 5 = 5
  │        ├─getFinalPosition(5)──────────▶│
  │        │       │       │  jumps.get(5) = null (no jump)
  │        │◀──────────────────5────────│
  │        │  Position stays at 5
  │◀moved to 5────│       │       │       │

  // Next roll lands on ladder:
  │─roll()▶│        │       │       │
  │        ├─roll()─▶│       │       │
  │        │◀value=4─│       │       │
  │        │  newPos = 5 + 4 = 9
  │        ├─getFinalPosition(9)──────────▶│
  │        │       │       │  jumps.get(9) = 45 (ladder!)
  │        │◀──────────────────45───────│
  │◀CLIMBED ladder to 45!│       │       │
```

---

## 5. Scenario-First Explanations

### **5.1 Why HashMap for Jump Lookup (O(1)) Instead of List Iteration?**

**You**: "Naive approach - iterate through list of snakes/ladders every move:

```java
// ❌ NAIVE: O(N) lookup per move
class Board {
    List<Snake> snakes;
    List<Ladder> ladders;
    
    int getFinalPosition(int pos) {
        for (Snake s : snakes) {
            if (s.getHead() == pos) return s.getTail();
        }
        for (Ladder l : ladders) {
            if (l.getBottom() == pos) return l.getTop();
        }
        return pos;
    }
}
```

**Optimized: O(1) with unified HashMap**:
```java
// ✅ EFFICIENT: O(1) lookup
class Board {
    private Map<Integer, Integer> jumps = new HashMap<>();  // Both snakes AND ladders
    
    void addSnake(int head, int tail) {
        if (tail >= head) throw new IllegalArgumentException("Snake must go down!");
        jumps.put(head, tail);
    }
    
    void addLadder(int bottom, int top) {
        if (top <= bottom) throw new IllegalArgumentException("Ladder must go up!");
        jumps.put(bottom, top);
    }
    
    int getFinalPosition(int pos) {
        return jumps.getOrDefault(pos, pos);  // O(1)!
    }
}
```

**Key insight**: Treating snakes and ladders as the SAME abstraction (a 'jump' from position A to position B) simplifies the code AND improves performance. This is a great example of finding the right abstraction."

### **5.2 Why Validate No Overlapping Snake/Ladder Positions?**

**You**: "Critical edge case - what if a snake head is at the same position as a ladder bottom? Ambiguous! Must validate at setup:

```java
class Board {
    void addSnake(int head, int tail) {
        validateNoConflict(head);
        validateNoConflict(tail);
        if (tail >= head) throw new IllegalArgumentException();
        if (head == 100 || head == 1) throw new IllegalArgumentException("Can't start/end on boundary cells");
        jumps.put(head, tail);
    }
    
    void validateNoConflict(int position) {
        if (jumps.containsKey(position)) {
            throw new IllegalStateException("Position " + position + " already has a jump defined!");
        }
    }
}
```

This kind of validation-at-setup thinking shows attention to edge cases that interviewers love to probe."

---

## 6. Cross Questions

**Interviewer**: "What if dice roll takes player beyond position 100?"

**You**: "Standard rule: **must land EXACTLY on 100** to win. Overshoot = stay in place (or some variants: bounce back).

```java
class Game {
    void playTurn(Player player) {
        int diceValue = dice.roll();
        int newPosition = player.getPosition() + diceValue;
        
        if (newPosition > board.getSize()) {
            // Exceeds board - invalid move, stay in place
            System.out.println(player.getName() + " needs exact roll to win. Staying at " 
                              + player.getPosition());
            return;  // Turn wasted
        }
        
        int finalPosition = board.getFinalPosition(newPosition);
        player.setPosition(finalPosition);
        
        if (finalPosition == board.getSize()) {
            declareWinner(player);
        }
    }
}
```"

---

## 7. Trade-offs

### **Single HashMap vs Separate Snake/Ladder Lists**

| Aspect | Unified HashMap | Separate Lists |
|--------|-----------------|-----------------|
| **Lookup** | O(1) | O(N) |
| **Code Complexity** | Simple (one abstraction) | More classes, more code |
| **Extensibility** | Easy to add new jump types | Requires new list + logic |

**You**: "Unified HashMap wins on all fronts here - simpler AND faster."

---

## 8. Senior Trap Questions

### **Trap: "Just use nested if-else for each snake/ladder position!"**

**✅ Senior**: "That's O(N) per lookup AND doesn't scale - what if there are 20 snakes and 20 ladders? A HashMap-based unified 'jump' abstraction is both cleaner code and O(1) performance. This simple optimization often separates candidates in interviews - shows you think about scale even in 'toy' problems."

---

## 9. Technology Choices

**You**: "For multiplayer online version: **WebSocket** for real-time dice rolls and position updates, **Redis** for game state (fast, ephemeral - game state doesn't need to survive server restart long-term)."

---

## 🎓 **Final Tips**

1. **Unified Jump Abstraction**: Snakes and ladders are the same concept - just direction differs
2. **O(1) HashMap Lookup**: Key optimization over naive list iteration  
3. **Exact Landing Rule**: Common game rule edge case to handle
4. **Setup Validation**: No overlapping snake heads/ladder bottoms

Good luck! Simple game, but the O(1) optimization insight is exactly what separates senior engineers. 🚀
