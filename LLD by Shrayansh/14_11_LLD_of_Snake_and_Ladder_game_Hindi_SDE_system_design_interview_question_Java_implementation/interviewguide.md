# Interview Guide: Snake and Ladder Game (LLD)

## 🗣️ The Interview Scenario

> "This one's a real Amazon LLD interview question: design the classic Snake and Ladder game. Support a configurable board size, a configurable number of dice, and a configurable/dynamic set of snakes and ladders — all of these should be settable at game setup time, not hardcoded. Then show me the actual turn-by-turn game loop, including how a player's position updates when they land on a snake or a ladder."

The subtlety interviewers probe for here is whether you model **snakes and ladders as the same underlying concept** (a "jump" from one cell to another) or whether you accidentally build two parallel, duplicated systems — one for snakes, one for ladders — that double your code and double your bug surface. The transcript's presenter explicitly unifies them, and that unification is the single most important design decision in this problem.

## 🏗️ Architect's Explanation (For a New Developer)

Here's the insight that unlocks this whole design: **a snake and a ladder are structurally identical.** Both are "if you land on cell A, you actually end up on cell B instead." The *only* difference between them is the direction: a ladder's destination cell number is *higher* than its start (you go up), and a snake's destination cell number is *lower* than its start (you go down). Nothing about the *mechanism* differs — so instead of writing separate `Snake` and `Ladder` classes with duplicated "teleport the player" logic, you model **one** class — call it `Jump` — that just holds a `start` cell and an `end` cell. Whether it "feels like" a snake or a ladder is simply a side effect of whether `end > start` or `end < start`; you never need to branch on "is this a snake or ladder" anywhere in your movement logic.

The second key idea is where that jump information lives: not as a separate global list you have to search through every turn, but stored **directly inside each board cell**. Every `Cell` on the board either has no jump (plain cell) or holds a reference to a `Jump` object. This means "does landing here trigger anything?" is an O(1) lookup at the cell the player just landed on — no scanning through a list of all snakes/ladders on every move.

## 📊 Visualize It

Class structure:

```
                    +----------------+
                    |     Game        |
                    +----------------+
                    | - Board board    |  (composition: Game HAS-A Board)
                    | - Dice dice       |  (composition: Game HAS-A Dice)
                    | - Deque<Player>   |  (composition: Game HAS-A players)
                    | - Player winner   |
                    +----------------+
                          |
              has-a       v
                    +----------------+
                    |     Board       |
                    +----------------+
                    | - Cell[] cells   |   (1D array, size = boardSize)
                    +----------------+
                          |
              has-a many  v
                    +----------------+
                    |      Cell       |
                    +----------------+
                    | - Jump jump      |   (nullable — null if plain cell)
                    +----------------+
                          |
              has-a (0..1) v
                    +----------------+
                    |      Jump       |   <-- SAME class represents BOTH snakes and ladders
                    +----------------+
                    | - start          |
                    | - end            |
                    +----------------+
                    (end < start  => behaves like a SNAKE)
                    (end > start  => behaves like a LADDER)

                    +----------------+
                    |     Player      |
                    +----------------+
                    | - id             |
                    | - currentPosition|
                    +----------------+

                    +----------------+
                    |      Dice       |
                    +----------------+
                    | - diceCount      |
                    | +rollDice(): int |  (sums `diceCount` random rolls)
                    +----------------+
```

Runtime turn flow:

```
 Deque<Player>: [P1, P2]

 pollFirst() -> P1                    P1.currentPosition = 4
        |                                       |
        v                                       v
 roll = dice.rollDice()   (e.g. sum of 2 dice = 3)
        |
        v
 newPosition = currentPosition + roll = 7
        |
        v
 cell = board.cells[newPosition]
        |
        v
 if (cell.jump != null)  newPosition = cell.jump.end     <-- unified snake/ladder handling
        |
        v
 P1.currentPosition = newPosition
        |
        v
 if (newPosition == board.size - 1) --> P1 is WINNER, game ends
 else --> offerLast(P1)  (P1 goes to back of the queue for next turn)
```

## 🔧 Deep Dive: How It Actually Works

### Requirement clarification (stated up front, exactly as in the transcript)

- **How many dice?** Configurable — could be 1, could be 2 (matching real board-game variants where using two dice is common).
- **How many snakes/ladders, and board size?** Fully dynamic — set at game-setup time, not hardcoded, so the same classes support a "quick 4x4-ish mini board with 2 snakes" or a "full 100-cell board with 8 snakes and 6 ladders" without any code change.
- **Winning condition?** Reaching the final cell first ends the game (the transcript notes this specific rule — some variants require *other* players to keep playing until second/third place is also decided — is a business-rule decision you should explicitly confirm with the interviewer, since it changes the loop's termination condition).

### `Player` — minimal state

```java
class Player {
    String id;
    int currentPosition;
}
```

### `Dice` — configurable count, not hardcoded to one die

```java
class Dice {
    int diceCount;   // e.g., 2 for a two-dice game

    int rollDice() {
        int total = 0;
        for (int i = 0; i < diceCount; i++) {
            total += new Random().nextInt(6) + 1;   // roll each die, sum the results
        }
        return total;
    }
}
```

The transcript is explicit that this loop-based summation is *why* `diceCount` is a first-class field rather than a hardcoded constant: "if it's two dice, I roll twice and add both random numbers to my total; if it were three, I'd roll three times."

### `Jump` — the unifying abstraction for snakes AND ladders

```java
class Jump {
    int start;
    int end;
    // No "type" field needed — a Snake is just a Jump where end < start,
    // a Ladder is just a Jump where end > start.
}
```

### `Cell` — holds a jump reference, not the other way around

```java
class Cell {
    Jump jump;   // null if this is a plain cell with no snake/ladder
}
```

The transcript explains the reasoning for *why cells hold jumps* rather than the board holding a separate `List<Jump>`: since the board is already represented as an indexable array of cells, and you always need to check "the cell I just landed on" during a move, embedding the jump reference directly in the cell makes that check a single array-index dereference instead of a linear search through a separate snakes/ladders collection.

### `Board` — a 1D array, not a 2D grid, and why

```java
class Board {
    Cell[] cells;
    int boardSize;

    Board(int boardSize, int numSnakes, int numLadders) {
        this.boardSize = boardSize;
        this.cells = new Cell[boardSize];
        for (int i = 0; i < boardSize; i++) cells[i] = new Cell();
        addJumps(numSnakes, numLadders);
    }

    void addJumps(int numSnakes, int numLadders) {
        // Random placement respecting the invariant:
        //   snake  -> start > end   (moves you DOWN)
        //   ladder -> start < end   (moves you UP)
        for (int i = 0; i < numSnakes; i++) {
            int start = randomCellExcludingHeadAndTail();
            int end = randomCellLessThan(start);
            cells[start].jump = new Jump(start, end);
        }
        for (int i = 0; i < numLadders; i++) {
            int start = randomCellExcludingHeadAndTail();
            int end = randomCellGreaterThan(start);
            cells[start].jump = new Jump(start, end);
        }
    }
}
```

Notice the loop shape for both snakes and ladders is *identical* — the only difference is whether the randomly-chosen `end` must be less-than or greater-than `start`. This is the direct payoff of unifying them into one `Jump` type: the board-population code has one pattern reused twice, not two separately-written and separately-maintained algorithms.

The transcript explicitly notes an alternative modeling approach some candidates use: keeping `Cell` itself lightweight (just a plain marker) and instead having `Board` hold two separate lists — `List<Jump> snakes` and `List<Jump> ladders` — and checking membership by scanning those lists per move. This works too, but the cell-embedded-jump approach is preferred specifically because it avoids a linear scan on every single move.

### `Game` — orchestration, using the same Deque turn-rotation idea as Tic-Tac-Toe

```java
class Game {
    Board board;
    Dice dice;
    Deque<Player> players;
    Player winner;

    void initGame(int boardSize, int numDice, int numSnakes, int numLadders, List<Player> playerList) {
        this.board = new Board(boardSize, numSnakes, numLadders);
        this.dice = new Dice(numDice);
        this.players = new ArrayDeque<>(playerList);
    }

    void startGame() {
        while (winner == null) {
            Player currentPlayer = players.pollFirst();
            int diceValue = dice.rollDice();
            int newPosition = currentPlayer.currentPosition + diceValue;

            if (newPosition >= board.boardSize) {
                // overshoot: invalid move in some rule variants — player stays put, forfeits this turn
                players.offerLast(currentPlayer);
                continue;
            }

            Cell landedCell = board.cells[newPosition];
            if (landedCell.jump != null) {
                newPosition = landedCell.jump.end;   // ONE unified check handles both snake and ladder
            }

            currentPlayer.currentPosition = newPosition;
            System.out.println(currentPlayer.id + " new position: " + newPosition);

            if (newPosition == board.boardSize - 1) {
                winner = currentPlayer;
                System.out.println("Winner: " + currentPlayer.id);
            } else {
                players.offerLast(currentPlayer);
            }
        }
    }
}
```

Walking through the transcript's worked example: Player 1 starts at position 0, rolls, moves to some new position; if that new position happens to be the *start* of a `Jump` whose `end` is lower (a snake), the player's `currentPosition` is set to that lower `end` value instead — the print statements in the demo explicitly show "player's computed new position" immediately followed by "player's actual new position after applying any jump," so you can visually confirm when a snake/ladder fired.

### Why `Deque` again (same reasoning as Tic-Tac-Toe)

Exactly as in the Tic-Tac-Toe design: turn order is naturally expressed as "take the current player off the front, and once their turn resolves, put them at the back" — `pollFirst()` + `offerLast()`. This is a reusable idiom worth carrying into any turn-based game LLD question.

### Overshoot rule — a deliberately-called-out edge case

The transcript draws a direct comparison to the N-Queens-style bounds checking: if a player's computed new position would exceed the last cell of the board (e.g., needing exactly a 3 to finish but rolling a 5), the move is invalid for that turn under the classic rule ("must land exactly on the final cell") — the player's position doesn't change, and the game continues without applying the roll. This bounds-check is explicitly flagged as a "You can improve this logic further" spot — a good signal to interviewers that you know this is a real edge case even if your first pass keeps it simple.

## 🔥 Real Production Incident & Fix

**What broke**: A mobile gaming studio built a "Snake and Ladder" mini-game inside a larger rewards app. The first implementation modeled snakes and ladders as two *separate* classes (`Snake { int head, tail; }` and `Ladder { int bottom, top; }`) stored in two separate `List`s on the `Board`, with two nearly-identical (but independently written) pieces of movement logic: `checkSnakeBite(position)` and `checkLadderClimb(position)`, each doing its own linear scan over its own list.

**How the team noticed**: A live-ops event added a "double ladders" promotional board variant with twice the normal number of ladders. QA found that on this specific board, a small percentage of games would let a player's token visually render at the *wrong* cell after climbing a ladder — investigation traced it to `checkLadderClimb()`, which had been copy-pasted from `checkSnakeBite()` months earlier and modified, but a boundary condition (`>=` vs `>` when comparing the player's landed cell against a ladder's bottom) had been copied incorrectly during the port, causing an off-by-one only on ladders whose bottom cell coincided with certain dice-roll sums. Because the two checks were maintained as separate code paths, a bug fix applied to `checkSnakeBite()` a month earlier (fixing the exact same class of off-by-one) was never propagated to `checkLadderClimb()`, since nothing structurally linked them.

**Root cause**: Modeling snakes and ladders as two independent classes with two independently-maintained pieces of "does this position trigger a jump" logic meant bug fixes didn't automatically apply to both, and the two scanning loops drifted out of sync over time — a direct violation of the DRY principle stemming from a missed abstraction (the fact that a snake and a ladder are the exact same concept, differing only in direction).

**The fix**: The team collapsed `Snake` and `Ladder` into a single `Jump(start, end)` class (as shown in the Deep Dive above), embedded directly into each `Cell`, and deleted both `checkSnakeBite()` and `checkLadderClimb()` in favor of one `applyJumpIfPresent(cell)` method used uniformly regardless of direction. The promotional "double ladders" board variant then required zero special-case code — it was just a board-generation parameter (`numLadders`) — and the class of off-by-one bugs became structurally impossible to have "fixed in one place but not the other," since there was only one place.

```
BEFORE: two parallel classes, two parallel (and drifting) checks   AFTER: one Jump concept, one check

 Snake { head, tail }         checkSnakeBite(pos)  -- has old off-by-one fix     Cell { Jump jump }
 Ladder { bottom, top }       checkLadderClimb(pos) -- missing the same fix     if (cell.jump != null)
   (bug fixed in one,           (bug NOT fixed in the other — drift)               newPos = cell.jump.end;
    not the other)                                                              (single code path, no drift possible)
```

## ❓ Likely Interview Follow-Up Questions & Answers

1. **"Why model snakes and ladders as a single `Jump` class instead of two distinct classes with clearer, more self-documenting names?"**
   Because the *mechanism* (land on `start`, get teleported to `end`) is byte-for-byte identical for both — the only difference is the relative ordering of the two numbers, which is a *data* fact (`end < start` vs `end > start`), not a *behavioral* fact requiring different code paths. Modeling them separately duplicates the movement-check logic and creates exactly the kind of maintenance drift shown in the incident above.

2. **"Why did you choose to store the `Jump` reference on the `Cell` rather than keeping a separate list of all jumps on the `Board`?"**
   Because every move requires answering "does the cell I just landed on trigger anything?" — with the jump stored on the cell, that's a direct array index lookup (`O(1)`), whereas a separate list requires scanning (`O(number of jumps)`) on every single turn. For small boards the performance difference is negligible, but the design is also simply cleaner: the fact "this cell has a jump" is a property of that cell, not a fact you should have to cross-reference elsewhere.

3. **"How do you guarantee, at board-generation time, that you never place a snake and a ladder starting on the same cell, or a jump that points to another jump's start cell (chaining)?"**
   Track which cell indices already have a `Jump` assigned (e.g., a `Set<Integer>` of used start cells) and exclude both used starts *and* used ends from candidate positions when placing the next jump — this is a generation-time invariant to enforce explicitly, and calling it out shows you're thinking about correctness beyond the happy path.

4. **"What would you change if the win condition were 'last player remaining loses' instead of 'first player to reach the end wins'?"**
   The loop's termination condition changes from `while (winner == null)` to something like `while (activePlayers.size() > 1)`, and instead of breaking on the first player reaching the final cell, you'd remove that player from the active rotation (mark them "finished," record their finishing rank) and continue the loop with the remaining players until only one is left. The `Board`, `Cell`, `Jump`, and `Dice` classes need no changes at all — only `Game`'s loop-termination and player-removal logic changes.

5. **"Your dice roll uses `new Random()` created fresh — what's a subtle issue with that in high-frequency code, and how would you fix it?"**
   Creating a new `Random` instance on every call is wasteful and, if multiple `Random` objects are created in rapid succession (same system-time-based seed), can produce correlated/less-random sequences; the fix is to hold a single `Random` instance as a field on `Dice` (constructed once) and reuse it across all rolls.

6. **"How would you unit-test the `Jump` application logic without relying on actual dice randomness?"**
   Inject a fake/mock `Dice` (or make `rollDice()` overridable/pluggable) that returns a fixed, predetermined sequence of values, then assert that `Player.currentPosition` ends up exactly where a known `Jump` on the board should send it — this isolates the "does landing on a jump cell correctly teleport the player" logic from the non-deterministic dice-rolling logic entirely.

## 🔑 Key Takeaway

Recognize that a snake and a ladder are the same abstraction (`start` cell, `end` cell) differing only by direction, unify them into one `Jump` type stored directly on each `Cell`, and reuse the `Deque`-based "poll from front, offer to back" idiom for turn rotation — this single unification decision is what separates a clean design from a duplicated, drift-prone one.
