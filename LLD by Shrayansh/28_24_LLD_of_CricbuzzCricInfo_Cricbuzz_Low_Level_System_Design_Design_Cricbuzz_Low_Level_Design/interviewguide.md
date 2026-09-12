# Interview Guide: LLD of Cricbuzz / CricInfo (Live Cricket Scorecard System)

## 🗣️ The Interview Scenario

> "Design the low-level system behind a live cricket score app like Cricbuzz. A match is ongoing between two teams; the app shows a live scorecard that updates ball-by-ball — current batsmen, current bowler, runs, wickets, overs completed, strike rate, economy rate, and so on. Model the classes involved, and specifically explain how you'd keep the scorecard updated in real time as each ball is bowled, and how you'd track which batsman is on strike and which bowler is up next."

This question tests whether you can model a real, stateful, event-driven domain (a live match) with proper entity relationships, and whether you know to reach for the **Observer pattern** for the "update multiple scorecards whenever a ball event happens" requirement — a very natural, non-contrived use case for it.

## 🏗️ Architect's Explanation (For a New Developer)

Think about how a physical cricket scoreboard at a stadium works. There's one live "match" happening. It's divided into "innings" (first one team bats, then the other). Within an innings, the game proceeds "over by over," and within each over, "ball by ball." After every single ball, several things need to be updated simultaneously: the batsman's personal stats (runs faced, balls faced, strike rate), the bowler's personal stats (overs bowled, runs conceded, economy rate), and the team's total score.

The natural design insight here is: **a single event (one ball being bowled) needs to notify multiple different "listeners" that all need to react to it** — the batsman's scorecard needs updating, the bowler's scorecard needs updating, and potentially other things (a live win-probability widget, a commentary feed, etc.) in a real system. This "one event, many independent things that react to it" shape is *exactly* what the **Observer design pattern** is built for — instead of the code that constructs a `Ball` object manually calling five different update methods in five different places, the `Ball` simply maintains a list of "observers" (score updaters) and calls `notify()` once; each observer independently does its own job.

The rest of the design is really about correctly modeling the **nested containment hierarchy** of a cricket match: a `Match` has `Team`s and `Innings`; an `Innings` has `Over`s; an `Over` has `Ball`s; and separately, a `Player` (who is a `Person`) can have both a `BattingScoreCard` and a `BowlingScoreCard`, since the same person bats in one innings and may bowl in the other.

## 📊 Visualize It

**Class structure / containment hierarchy:**
```
Match
 ├─ TeamA, TeamB
 ├─ venue, matchTime, tossWinner
 ├─ MatchType (interface) ──► T20Match / TestMatch (getNumberOfOvers(), getMaxOverPerBowler())
 └─ List<Innings>
        Innings
         ├─ battingTeam, bowlingTeam
         └─ List<Over>
                Over
                 └─ List<Ball>
                        Ball
                         ├─ BallType (enum: NORMAL, WIDE, NO_BALL, ...)
                         ├─ RunType (enum: ONE, TWO, FOUR, SIX, WIDE_RUN, ...)
                         ├─ batsmanOnStrike, bowler
                         └─ List<ScoreUpdateObserver>   ◄── Observer pattern

Team
 ├─ teamName
 └─ List<Player> (playing XI)
        + PlayerBattingController   (tracks striker / non-striker / "yet to play" queue)
        + PlayerBowlingController   (tracks current bowler, overs bowled per bowler)

Player extends Person
 ├─ name, address (inherited from Person)
 ├─ PlayerType (BATSMAN, WICKET_KEEPER, ALL_ROUNDER, CAPTAIN, ...)
 ├─ BattingScoreCard  (totalRuns, ballsPlayed, fours, sixes, strikeRate)
 └─ BowlingScoreCard  (oversDelivered, runsGiven, wicketsTaken, noBallCount, wideBallCount, economyRate)
```

**Observer pattern in action — one ball notifies multiple scorecards:**
```
        Ball is bowled (constructed with all its details)
                    │
                    │  notifyObservers(ballInfo)
                    ▼
        ┌───────────────────────────┐
        │   List<ScoreUpdateObserver>│
        └───────────────────────────┘
             │                    │
             ▼                    ▼
  BattingScoreCardUpdater   BowlingScoreCardUpdater
   (update() called)         (update() called)
     - totalBallsPlayed++      - ballsBowled++
     - if RunType==FOUR:       - if RunType==FOUR: totalRunsGiven+=4
         fours++, runs+=4      - recompute economyRate
     - recompute strikeRate
```

**Batting/Bowling controller queues:**
```
PlayerBattingController
  "yetToPlay" queue: [P4, P5, P6, ... P11]   (dequeue front when a wicket falls)
  strikerPlayer:      P1
  nonStrikerPlayer:   P2

PlayerBowlingController
  bowlerDeque: [B1, B2, B3, ...]  (rotate: front bowls, moves to back after over,
                                    skip if maxOversPerBowler already reached)
  currentBowler: B1
  Map<Player, oversBowledCount>   (enforce max-overs-per-bowler rule)
```

## 🔧 Deep Dive: How It Actually Works

### Step 1 — Requirement gathering from the product's own UI

Start from what the actual Cricbuzz app shows: a list of ongoing matches; clicking a match shows its live **scorecard**, which updates ball-by-ball. A scorecard shows, per team/innings: total runs, wickets, overs bowled; and per **batting player**: runs scored, balls faced, fours, sixes, strike rate; and per **bowling player**: overs bowled, runs given, wickets taken, no-balls, wides, economy rate. This becomes your functional requirement list before any class is drawn.

### Step 2 — Top-down object identification

Going top-down: `Match` → has `Team`s → each `Team` has `Player`s → the match proceeds through `Innings` → each `Innings` is made of `Over`s → each `Over` is made of `Ball`s. This containment chain is the backbone of the entire class diagram.

### Step 3 — `Match`

`Match` has: two `Team` references, `venue`, `matchTime`, `tossWinner`, and a list of `Innings`. Importantly, `Match` also holds a `MatchType` — an **interface** implemented by concrete classes like `T20Match` and `TestMatch`/`ODIMatch`, each returning match-format-specific constants: `getNumberOfOvers()` (e.g., 50 for ODI, 20 for T20) and `getMaxOverPerBowler()` (e.g., 10 for ODI, 5 for T20). This is explicitly called out as a way to control match-format-specific rules through polymorphism rather than scattering `if (matchType == "T20")` conditionals throughout the codebase.

### Step 4 — `Team`, `Player`, and the two "per-player" controllers

`Team` has a `teamName` and a `List<Player>` representing the **playing XI** (ordering matters, since batting order is derived from this list). Each `Player` extends `Person` (which holds `name`, `address`, and other generic personal fields) and adds a `PlayerType` (batsman, wicket-keeper, all-rounder, captain, etc.) plus **two scorecards**: `BattingScoreCard` and `BowlingScoreCard` — because the same player can both bat and bowl across the two innings of a match.

- **`BattingScoreCard`**: total runs, total balls played, total fours, total sixes, strike rate.
- **`BowlingScoreCard`**: total overs delivered, runs given, wickets taken, no-ball count, wide-ball count, economy rate.

Two controllers live at the `Team` level to manage in-match state that a plain data object can't hold on its own:
- **`PlayerBattingController`**: maintains a **queue of players yet to bat** ("yet to play"). Every time a batsman gets out, the controller dequeues the next player from the front of this queue and assigns them as the new striker (or non-striker, depending on context). It also explicitly tracks which player is currently **on strike** and which is the **non-striker**, since — as the transcript notes — the UI needs to visually distinguish the striker with a marker (e.g., a star `*`), and this state must live somewhere queryable.
- **`PlayerBowlingController`**: maintains a **deque of bowlers**. The bowler at the front bowls the current over; once done, if they still have overs remaining (haven't hit the format's max-overs-per-bowler limit), they go to the **back** of the deque; otherwise they're excluded going forward. A `Map<Player, oversBowledCount>` tracks how many overs each bowler has delivered, so the controller can enforce the format's `getMaxOverPerBowler()` rule (e.g., a bowler can never exceed 10 overs in an ODI) and also enforce that the **same bowler cannot bowl two consecutive overs**.

### Step 5 — `Innings`, `Over`, `Ball`

- `Innings` has a `battingTeam`, `bowlingTeam` (these flip between the two innings of a match), and a `List<Over>`. The number of overs an innings must run is passed down from `Match`'s `MatchType` (`getNumberOfOvers()`).
- `Over` has a `List<Ball>` — note explicitly that an over can contain **more than the "legal" ball count** because no-balls and wides don't count toward the six legal deliveries, so the list length can exceed 6.
- `Ball` carries: a `BallType` enum (normal, no-ball, wide, etc.), a `RunType` enum (one, two, four, six, wide-run, etc.), and references to **which batsman faced it** and **which bowler bowled it**.

### Step 6 — Kicking off a match (the orchestration walkthrough)

`Match.start()` initializes both teams' players and, for the given `MatchType` (say `T20Match`), determines who bats first based on the toss result (an explicit simplifying assumption used in the transcript: whoever wins the toss chooses to bat). Setting up the very first over requires establishing **who the striker and non-striker are** — this is exactly where `PlayerBattingController.chooseNextBatsman()` is invoked: it pulls the next player from the front of the "yet to play" queue and fills in the striker/non-striker slots. Similarly, for the bowling side, `PlayerBowlingController.chooseNextBowler()` is invoked: it takes the bowler from the front of the deque, checks whether their `oversBowledCount` has already hit the format's max, and if not, assigns them as the current bowler for the new over and increments their overs-bowled count; otherwise it's returned to the deque (not put back at the front) and the next candidate is tried.

### Step 7 — The Observer pattern for ball-by-ball scorecard updates

This is the design's centerpiece. Every `Ball` needs to update **both** the batting scorecard (of the batsman who faced it) and the bowling scorecard (of the bowler who bowled it) the moment it's constructed. Rather than hardcoding these two updates inline, `Ball` maintains a `List<ScoreUpdateObserver>` and, upon construction/delivery, calls a `notify()` method that iterates the list and invokes each observer's `update()`:

```java
interface ScoreUpdateObserver {
    void update(Ball ball);
}

class BattingScoreCardUpdater implements ScoreUpdateObserver {
    public void update(Ball ball) {
        Player striker = ball.getBatsman();
        striker.getBattingScoreCard().incrementBallsPlayed();
        if (ball.getRunType() == RunType.FOUR) striker.getBattingScoreCard().addFour();
        if (ball.getRunType() == RunType.SIX)  striker.getBattingScoreCard().addSix();
        striker.getBattingScoreCard().recomputeStrikeRate();
    }
}

class BowlingScoreCardUpdater implements ScoreUpdateObserver {
    public void update(Ball ball) {
        Player bowler = ball.getBowler();
        bowler.getBowlingScoreCard().incrementBallsBowled();
        bowler.getBowlingScoreCard().addRunsConceded(ball.getRunsScored());
        bowler.getBowlingScoreCard().recomputeEconomyRate();
    }
}
```

Each ball's constructor essentially says: "here's who batted, who bowled, what type of ball and run it was — now notify every registered scorecard updater," and each updater independently increments the fields relevant to it. This decouples "a ball happened" from "everything that must react to it," matching the classic Observer pattern definition (a subject notifies a list of interested observers without knowing their concrete implementation details).

### Step 8 — Simulating a delivery

The demo walkthrough uses a simplified random-number generator to decide the outcome of each ball (assuming, as a stated simplification, that every ball is a "normal" ball type, and randomly picks whether it's a wicket via one random draw, then randomly picks the run value — 0/1/2/4/6 — via another random draw), purely to demonstrate the flow end-to-end; in a real system, this data would come from an external live-feed input rather than random generation.

## 🔥 Real Production Incident & Fix

**What broke:** A live-scores startup building a Cricbuzz-style app had their `BowlingScoreCardUpdater` compute `economyRate` using `totalRunsGiven / totalOversBowled`, where `totalOversBowled` was stored as a whole number (rounding 4.3 overs — i.e., 4 overs and 3 balls — down to `4`). During a high-profile T20 match, commentators and fans on social media started flagging that the app's displayed economy rates were visibly wrong compared to the official broadcast feed and competitor apps, especially in the death overs when partial-over bowling figures matter most for live analysis.

**How the team noticed:** A spike in negative app-store reviews mentioning "wrong economy rate" during the match, plus an internal analytics dashboard showed the discrepancy metric (app's computed stat vs. the official data feed's stat) crossing an alert threshold for the `economyRate` field specifically — while `totalRuns` and `wickets` remained accurate, isolating the bug to that one derived metric.

**Root cause:** Overs in cricket are not a decimal quantity in the traditional sense — "4.3 overs" means 4 completed overs plus 3 balls of a 5th, i.e., 27 legal deliveries, **not** `4.3` as a float. The team's code stored `oversBowled` as `ballsBowled / 6` truncated to an integer, discarding the partial-over remainder entirely before computing economy rate, so a bowler with figures "4.3-0-30" was scored as if they'd bowled a clean 4 overs, understating their economy rate.

**The fix:** The team refactored `BowlingScoreCard` to track `totalLegalBallsBowled` as the single source of truth (an integer count, immune to the overs-notation ambiguity), and computed economy rate as `(totalRunsGiven * 6.0) / totalLegalBallsBowled` — mathematically equivalent to "runs per over" but computed from whole legal balls, entirely sidestepping the overs-as-decimal trap. They also added a unit test asserting that a bowler with figures "4.3-0-30" (27 legal balls, 30 runs) produces an economy rate of `30 * 6 / 27 = 6.67`, not the previously-buggy `30 / 4 = 7.5`.

```
BEFORE (bug): overs stored as truncated int, partial over silently dropped
  oversBowled = ballsBowled / 6            // 27 balls → 4 (loses the .3)
  economyRate = runsGiven / oversBowled    // 30 / 4 = 7.5 (WRONG)

AFTER (fixed): legal balls as source of truth, no truncation
  totalLegalBallsBowled = 27
  economyRate = (runsGiven * 6.0) / totalLegalBallsBowled   // 30*6/27 = 6.67 (correct)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why use the Observer pattern for scorecard updates instead of just calling both update methods directly inside `Ball`'s constructor?**
Direct calls tightly couple `Ball` to every specific scorecard type, so adding a new reactive feature (say, a live win-probability recalculation, or a commentary auto-generator) would require modifying `Ball`'s constructor every time; with Observer, `Ball` only needs to know about the generic `ScoreUpdateObserver` interface and calls `notify()` once, so new observers can be registered without changing `Ball` at all — this is the Open/Closed Principle in action.

**Q2: How do you model that a `MaxOversPerBowler` rule differs between T20 and ODI without littering the code with `if` statements?**
Model `MatchType` as an interface with concrete implementations `T20Match` and `ODIMatch`/`TestMatch`, each returning its own constant from `getMaxOverPerBowler()` (5 for T20, 10 for ODI); `PlayerBowlingController` then just calls `match.getMatchType().getMaxOverPerBowler()` polymorphically, so adding a new format later (e.g., a 100-ball format) means adding one new class, not touching existing conditional logic.

**Q3: Why does `Player` hold both a `BattingScoreCard` and a `BowlingScoreCard` instead of splitting into separate `Batsman` and `Bowler` classes?**
Because a single real player can bat in one innings and bowl in the other (an all-rounder is the most obvious case, but even specialist batsmen occasionally bowl), so modeling both scorecards on `Player` avoids awkward casting or a parallel-class-per-role explosion, at the cost of a bowler having an (unused/zeroed) `BattingScoreCard` — an acceptable trade-off given how naturally cricket blurs the batsman/bowler boundary.

**Q4: How would you track that the same bowler cannot bowl two consecutive overs?**
`PlayerBowlingController` uses a deque: the current over's bowler is always taken from the front, and once their over is complete, they are placed at the **back** of the deque (never re-inserted at the front), which structurally guarantees at least one other bowler must bowl before they can be selected again — a nice example of choosing the right data structure to enforce a business rule for free.

**Q5: An over can technically contain more than 6 `Ball` objects — why, and how does your model account for it?**
Because no-balls and wides don't count as one of the six "legal" deliveries in an over (the bowler must re-bowl them), so `Over.balls` is modeled as an open-ended `List<Ball>` rather than a fixed-size array of 6, and completion of an over is determined by counting only balls whose `BallType` is a *legal* delivery type, not by list length.

**Q6: How would you extend this design to support DRS (Decision Review System) or live win-probability without breaking existing code?**
Add a new class implementing `ScoreUpdateObserver` (e.g., `WinProbabilityUpdater`) and register it in `Ball`'s observer list alongside the existing batting/bowling updaters — since `Ball` only depends on the `ScoreUpdateObserver` interface, this is a pure addition with zero modification to `Ball`, `BattingScoreCardUpdater`, or `BowlingScoreCardUpdater`.

## 🔑 Key Takeaway

Model the containment hierarchy top-down (Match → Innings → Over → Ball, Team → Player), but the interview-winning insight is recognizing that "one ball event must update multiple independent scorecards" is a textbook Observer pattern use case — say that explicitly and show the `notify()`/`update()` flow.
