# Comprehensive LLD Extraction from Video Transcripts

## Table of Contents
1. [System Designs Overview](#system-designs-overview)
2. [Components & Objects by System](#components--objects-by-system)
3. [Technology Choices & Patterns](#technology-choices--patterns)
4. [Database Schemas & Data Structures](#database-schemas--data-structures)
5. [Interview Tips & Trap Questions](#interview-tips--trap-questions)
6. [Scenario Questions & Answers](#scenario-questions--answers)

---

## System Designs Overview

### Major Systems Covered:
1. **BookMyShow** - Movie Ticket Booking System
2. **Cricbuzz** - Cricket Scoring System
3. **Splitwise** - Expense Sharing Application
4. **Payment Gateway** - Payment Processing System
5. **ATM System** - Automated Teller Machine
6. **Vending Machine** - Product Dispensing System
7. **Elevator System** - Multi-floor Elevator Control
8. **Car Rental System (ZoomCar)** - Vehicle Rental Platform
9. **Tic-Tac-Toe** - Game Design
10. **Snake & Ladder** - Board Game
11. **Chess Game** - Chess System Design
12. **Logging System** - Chain of Responsibility Pattern
13. **File System** - Composite Pattern Implementation
14. **Inventory Management System**

---

## Components & Objects by System

### 1. BOOKMYSHOW - Movie Ticket Booking

#### Core Objects:
- **Movie**: movieId, movieName, movieDuration
- **MovieController**: Map<City, List<Movie>>, allMovies
- **Theater**: theaterId, address, city, List<Screen>, List<Show>
- **Screen**: screenId, List<Seat>
- **Seat**: seatId, seatCategory (SILVER/GOLD/PLATINUM), row, price
- **Show**: showId, Movie, Screen, startTime, List<Integer> bookedSeatIds
- **TheaterController**: Map<City, List<Theater>>, allTheaters
- **Booking**: Show, List<Seat>, Payment
- **Payment**: paymentId, paymentStatus
- **User**: (implicit user interaction)

#### Key Relationships:
- MovieController manages City → Movies mapping
- TheaterController manages City → Theaters mapping
- Theater has multiple Screens
- Screen has multiple Seats
- Show belongs to Theater and displays a Movie on a Screen
- Booking references Show and Seats
- Payment is linked to Booking

#### Design Patterns Used:
- **MVC Pattern**: Separation of Movie/Theater Controllers
- **Optimistic Locking**: For concurrency control on seat booking
  - Each seat maintains a version number
  - Before booking, check if version matches
  - If version changed, another user booked it
  - Update version on successful booking

#### Concurrency Strategy:
**Problem**: Multiple users booking same seat simultaneously

**Solution**: Optimistic Locking
```
User1 reads Seat (version = 1)
User2 reads Seat (version = 1)
User1 updates → check version == 1 → SUCCESS → version = 2
User2 updates → check version == 1 → FAIL (version is now 2)
User2 must retry with latest data
```

**Alternative**: Pessimistic Locking (lock on read, not preferred for ticket booking)

**Additional Feature**: Redis Lock with Expiry
- When seat selected, lock for 10-15 minutes
- Auto-release if payment not completed
- Prevents indefinite reservation

---

### 2. CRICBUZZ - Cricket Scoring System

#### Core Objects:
- **Match**: teamA, teamB, venue, matchDate, List<Innings>, matchType, tossWinner
- **Team**: teamName, List<Player>, PlayerBattingController, PlayerBowlingController
- **Player**: Person (name, address), playerType, BattingScoreCard, BowlingScoreCard
- **PlayerType**: BATSMAN, BOWLER, WICKET_KEEPER, ALL_ROUNDER, CAPTAIN
- **BattingScoreCard**: totalRuns, totalBallsPlayed, totalFours, totalSixes, strikeRate
- **BowlingScoreCard**: totalOversDelivered, totalRunsGiven, totalWicketsTaken, noBallCount, wideBallCount, economyRate
- **PlayerBattingController**: Queue<Player> yetToPlay, Player striker, Player nonStriker
- **PlayerBowlingController**: Deque<Player>, Map<Player, Integer> overCount, Player currentBowler
- **Innings**: Team battingTeam, Team bowlingTeam, List<Over>
- **Over**: List<Ball>, overNumber
- **Ball**: ballNumber, BallType, runType, Player playedBy, Player bowledBy
- **BallType**: NORMAL, NO_BALL, WIDE_BALL
- **RunType**: ONE, TWO, THREE, FOUR, SIX, WICKET
- **ScoreUpdater**: Observer pattern for updating scores

#### Key Relationships:
- Match has two Teams and manages Innings
- Team has Players and Controllers for batting/bowling order
- Innings has multiple Overs
- Over has multiple Balls
- Ball tracks which Player played and which Player bowled
- ScoreUpdater observes Ball events and updates ScoreCards

#### Design Patterns Used:
- **Observer Pattern**: Ball events trigger score updates
  - Ball maintains List<ScoreUpdater>
  - After each ball, notifies all observers
  - BattingScoreCardUpdater updates batsman stats
  - BowlingScoreCardUpdater updates bowler stats
- **Strategy Pattern**: Different MatchTypes (T20, ODI, Test) define different rules
- **State Pattern**: Could be used for match states (not explicitly mentioned)

#### Data Structures:
- **Queue**: For batting order (yetToPlay)
- **Deque**: For bowling rotation (allows adding bowler to back after over)
- **Map**: Track over count per bowler

---

### 3. SPLITWISE - Expense Sharing App

#### Core Objects:
- **User**: userId, userName, BankAccount, Card
- **Group**: groupId, groupName, List<User>, List<Expense>
- **Expense**: expenseId, description, amount, paidBy (User), List<Split>, ExpenseType (EQUAL/PERCENTAGE)
- **Split**: User, amount (computed from percentage if needed)
- **UserExpenseBalanceSheet**: Map<User, Balance> (friend-wise balances)
- **Balance**: amountGetBack, amountOwe
- **BankAccount**: accountNumber, balance, updateBalance()
- **Card**: cardNumber, cvv, expiryDate
- **ExpenseController**: Creates and validates expenses
- **SplitFactory**: Creates EQUAL or PERCENTAGE split validators

#### Key Relationships:
- User belongs to multiple Groups
- Group contains multiple Expenses
- Expense has one payer and multiple Splits
- Each User maintains BalanceSheet tracking all friend balances
- Split links User to their share of Expense

#### Design Patterns Used:
- **Factory Pattern**: SplitFactory creates appropriate split validator (EQUAL/PERCENTAGE)
- **Strategy Pattern**: Different split strategies (equal, percentage, exact amounts)
- **Graph Algorithms**: Can use graphs to simplify debts (mentioned by Splitwise CEO on Quora)

#### Validation Logic:
```
For EQUAL split:
- Sum of all splits == total expense amount
- Each split amount = total / number of people

For PERCENTAGE split:
- Sum of all percentages == 100%
- OR sum of computed amounts == total expense
```

#### Balance Sheet Structure:
```
User1:
  - Friend1: {getBack: 500, owe: 0}
  - Friend2: {getBack: 0, owe: 300}
  - Friend3: {getBack: 200, owe: 0}
  Total: {getBack: 700, owe: 300}
```

---

### 4. PAYMENT GATEWAY - Payment Processing System

#### Core Objects:
- **User**: userId, userName, drivingLicense (document verification)
- **Instrument**: instrumentId, userId, instrumentType
- **InstrumentType**: BANK, CARD, BALANCE (enum)
- **BankInstrument**: extends Instrument, bankAccountNumber, ifscCode
- **CardInstrument**: extends Instrument, cardNumber, cvvNumber
- **InstrumentController**: Uses InstrumentServiceFactory
- **InstrumentServiceFactory**: Returns BankService or CardService based on type
- **InstrumentService**: Abstract class with addInstrument(), getInstrument()
- **BankService**: Specific logic for bank operations
- **CardService**: Specific logic for card operations
- **TransactionController**: makePayment(), getTransactionHistory()
- **TransactionService**: Creates transactions, fetches instrument details, calls processor
- **Transaction**: transactionId, amount, senderUserId, receiverUserId, debitInstrumentId, creditInstrumentId, status
- **TransactionStatus**: SUCCESS, PENDING, DENIED (enum)
- **Processor**: External service to process payments
- **UserController**: Exposes user APIs

#### Key Relationships:
- User has multiple Instruments
- Instrument is abstract, specialized by BankInstrument and CardInstrument
- TransactionController uses TransactionService
- TransactionService uses InstrumentController to fetch instrument details
- TransactionService calls Processor for actual payment processing
- Each Transaction links sender, receiver, and their instruments

#### Design Patterns Used:
- **Factory Pattern**: InstrumentServiceFactory creates appropriate service (Bank/Card)
  - Allows adding new instrument types (UPI, Wallet) easily
- **DTO Pattern**: InstrumentDo separates client representation from DB entity
  - Client never sees internal DB schema
  - Easy to change DB without affecting clients
- **Single Responsibility**: Separate services for each instrument type
- **Strategy Pattern**: Could be extended for different payment processors

#### Architecture Highlights:
```
Client → Controller → Service → Factory → Specific Service → Processor
```

#### Async Payment Flow (Advanced):
1. **Synchronous Validation**:
   - Check sender has sufficient balance
   - Check receiver account is valid
   - Reserve funds if valid
   - Create transaction in PENDING state
   
2. **Asynchronous Processing**:
   - Call Processor asynchronously (may take 3-5 days)
   - Processor eventually returns success/failure
   - Update transaction status accordingly

---

### 5. ATM SYSTEM

#### Core Objects:
- **ATMState**: Interface with operations (insertCard, authenticatePin, selectOperation, etc.)
- **IdleState**: Only allows card insertion
- **HasCardState**: Allows PIN authentication
- **SelectOperationState**: User selects cash withdrawal, balance check, pin change
- **CashWithdrawalState**: Processes withdrawal, updates balance
- **CheckBalanceState**: Displays balance
- **ATM**: currentState, atmBalance, noOfTwoThousandNotes, noOfFiveHundredNotes, noOfHundredNotes
- **User**: card, bankAccount
- **Card**: cardNumber, cvv, pin, bankAccount
- **BankAccount**: balance, updateBalance()
- **CashWithdrawalProcessor**: Interface for different withdrawal algorithms
- **TwoThousandWithdrawalProcessor**: Processes 2000 notes
- **FiveHundredWithdrawalProcessor**: Processes 500 notes
- **HundredWithdrawalProcessor**: Processes 100 notes

#### State Transitions:
```
IDLE → (insert card) → HAS_CARD 
HAS_CARD → (authenticate pin) → SELECT_OPERATION
SELECT_OPERATION → (select cash withdrawal) → CASH_WITHDRAWAL
CASH_WITHDRAWAL → (dispense cash) → IDLE
SELECT_OPERATION → (cancel) → IDLE (refund money)
```

#### Design Patterns Used:
- **State Design Pattern**: Different states with state-specific operations
  - IdleState: Only insertCard() implemented
  - HasCardState: Only authenticatePin() implemented
  - Each state throws exception for unsupported operations
  - State changes managed by ATM object
  
- **Chain of Responsibility**: Cash withdrawal processing
  - 2000 processor → 500 processor → 100 processor
  - Each processor handles what it can, forwards remainder
  - Example: 2700 = 1×2000 + 1×500 + 2×100

#### Cash Withdrawal Chain Logic:
```
Withdraw 2700:
1. TwoThousandProcessor: 
   - Has 1 note
   - Dispenses 2000
   - Remaining = 700
   - Calls super.withdraw(700)

2. FiveHundredProcessor:
   - Has 2 notes
   - Dispenses 500
   - Remaining = 200
   - Calls super.withdraw(200)

3. HundredProcessor:
   - Has 5 notes
   - Dispenses 200 (2 notes)
   - Remaining = 0
   - Complete

Result: 0×2000 + 1×500 + 3×100 remaining
```

---

### 6. VENDING MACHINE

#### Core Objects:
- **VendingMachine**: currentState, inventory
- **State**: Interface with operations (pressInsertCashButton, insertCoin, selectProductButton, etc.)
- **IdleState**: Only pressInsertCashButton() allowed
- **HasMoneyState**: insertCoin(), selectProductButton(), refund() allowed
- **SelectionState**: chooseProduct(), getChange(), refund() allowed
- **DispensingState**: Only dispenseProduct() allowed
- **Inventory**: List<ItemShelf>
- **ItemShelf**: code, Item, isSold
- **Item**: ItemType, price
- **ItemType**: COKE, PEPSI, JUICE, SODA (enum)
- **Coin**: NICKEL(5), QUARTER(25) (enum with value)

#### State Transitions:
```
IDLE → (pressInsertCashButton) → HAS_MONEY
HAS_MONEY → (insertCoins) → HAS_MONEY
HAS_MONEY → (selectProductButton) → SELECTION
SELECTION → (chooseProduct) → DISPENSING
DISPENSING → (dispenseProduct) → IDLE
HAS_MONEY/SELECTION → (refund) → IDLE
```

#### Design Patterns Used:
- **State Design Pattern**: Similar to ATM
  - Each state implements only relevant operations
  - Other operations throw exceptions or use default
  - VendingMachine holds currentState
  - States change the machine's state

#### Key Features:
- Inventory management per shelf
- Coin collection and change return
- Refund capability at multiple states
- Product availability tracking

---

### 7. ELEVATOR SYSTEM

#### Core Objects:
- **Building**: List<Floor>
- **Floor**: floorId, ExternalButton
- **ExternalButton**: buttonDispatcher (ExternalButtonDispatcher)
- **ExternalButtonDispatcher**: List<ElevatorController>, algorithm to select elevator
- **InternalButton**: buttonDispatcher (InternalButtonDispatcher)
- **InternalButtonDispatcher**: List<ElevatorController>
- **ElevatorController**: elevator (ElevatorCar), pendingJobs (Queue), accepts/submits requests
- **ElevatorCar**: elevatorId, Display, currentFloor, Direction, Status, InternalButton, Door
- **Display**: floor, direction
- **Direction**: UP, DOWN (enum)
- **Status**: MOVING, IDLE (enum)
- **ElevatorAlgorithm**: LOOK/SCAN algorithm implementation

#### Key Components:
1. **External Dispatcher**: Decides which elevator serves external requests
   - ODD-EVEN: Elevator 1 serves odd floors, Elevator 2 serves even
   - NEAREST: Pick elevator closest to request
   - SHORTEST_TIME: Pick elevator with min wait time

2. **Elevator Controller**: Manages one elevator
   - Maintains request queue (PriorityQueue)
   - Controls elevator movement
   - Accepts new requests and updates queue

3. **Elevator Car**: Physical elevator unit
   - Just moves as instructed
   - No logic, just destination floor and direction

#### LOOK/SCAN Elevator Algorithm:
**Data Structures Used**:
- **MinHeap**: For UP direction requests (ascending order)
- **MaxHeap**: For DOWN direction requests (descending order)  
- **PendingJobs Queue**: For opposite direction requests

**Algorithm Flow**:
```
Current Floor: 3, Direction: UP
New Requests: 6 (UP), 4 (UP), 2 (DOWN), 7 (DOWN)

1. MinHeap (UP): [4, 6] (current direction)
2. MaxHeap (DOWN): [] (empty)
3. PendingJobs: [2, 7] (opposite direction)

Execution:
- Serve 4 (from MinHeap)
- Serve 6 (from MinHeap)
- MinHeap empty → Change direction to DOWN
- Move PendingJobs to MaxHeap: [7, 2]
- Serve 7
- Serve 2
- Done
```

**Look-Ahead Optimization**:
- Before continuing in direction, check if more requests ahead
- If no requests ahead, change direction early
- Prevents unnecessary travel to end

**Example**:
```
Floor 3, going UP, request at floor 6
No more requests after 6
After serving floor 6, immediately change to DOWN
Don't continue to floor 10 unnecessarily
```

---

### 8. CAR RENTAL SYSTEM (ZoomCar)

#### Core Objects:
- **User**: userId, userName, drivingLicense
- **Vehicle**: vehicleId, vehicleNumber, vehicleType, companyName, modelName, kmDriven, manufacturingDate, status
- **VehicleType**: CAR, BIKE (enum - extensible)
- **VehicleStatus**: ACTIVE, INACTIVE (enum)
- **Car**: extends Vehicle (specific car properties)
- **Bike**: extends Vehicle (specific bike properties)
- **Store**: storeId, VehicleInventoryManagement, location, List<Reservation>
- **VehicleInventoryManagement**: List<Vehicle>, add/remove/update operations
- **Location**: address, city, state, pinCode
- **Reservation**: reservationId, user, vehicle, bookingDate, dateBookedFrom, dateBookedTo, reservationStatus
- **ReservationStatus**: SCHEDULED, IN_PROGRESS, COMPLETED, CANCELLED (enum)
- **Bill**: reservation, isPaid (boolean), amount
- **Payment**: bill, amount
- **VehicleRentalSystem**: List<User>, List<Store>

#### Key Relationships:
- Store has VehicleInventoryManagement
- VehicleInventoryManagement manages List<Vehicle>
- Store maintains List<Reservation>
- Reservation links User and Vehicle
- Bill is generated against Reservation
- Payment is made against Bill

#### Design Patterns Used:
- **Factory Pattern**: Can extend for different vehicle types
- **Template Pattern**: Vehicle is abstract, Car/Bike are concrete
- **Single Responsibility**: 
  - Store handles location-specific operations
  - VehicleInventoryManagement handles vehicle CRUD
  - Separates concerns, easy to modify

#### Workflow:
```
1. User searches by Location
2. System returns List<Store> in that location
3. User selects Store
4. Store returns List<Vehicle> (via InventoryManagement)
5. User selects Vehicle
6. User creates Reservation (Store.createReservation())
7. System generates Bill (against Reservation)
8. User makes Payment (against Bill)
9. User picks up vehicle → Update Reservation status to IN_PROGRESS
10. User returns vehicle → Store.completeReservation() → Status = COMPLETED
```

#### Interview Tips (from transcript):
**CRITICAL**: "Design as simple as possible"
- Don't add features unless interviewer asks
- Let interviewer suggest additions
- Adding too many features can backfire if you can't implement them

---

### 9. TIC-TAC-TOE GAME

#### Core Objects:
- **PlayingPiece**: Abstract class with pieceType
- **PieceType**: X, O (enum - extensible)
- **PlayingPieceX**: extends PlayingPiece
- **PlayingPieceO**: extends PlayingPiece
- **Board**: size, PlayingPiece[][]
- **Player**: name, playingPiece
- **Game**: Queue<Player>, board

#### Game Flow:
1. Initialize board (size × size)
2. Create players with pieces (X and O)
3. Add players to queue
4. Loop until winner or tie:
   - Remove player from front of queue
   - Display board
   - Get free cells
   - If no free cells → TIE
   - Player selects cell (row, col)
   - If cell occupied → invalid, try again
   - Place piece on board
   - Add player to back of queue
   - Check winner (row/column/diagonal)
   - If winner found → return winner

#### Winner Check Logic:
- Check all rows
- Check all columns
- Check both diagonals
- If any line has all same pieces → Winner

---

### 10. SNAKE AND LADDER GAME

(Would extract from transcript if needed - follow similar structure)

---

## Technology Choices & Patterns

### Design Patterns Used Across Systems:

#### 1. State Design Pattern
**Used In**: ATM, Vending Machine
**Purpose**: Object behavior changes based on internal state
**When to Use**: Operations depend on current state
**Implementation**:
- State interface with all operations
- Concrete states implement only relevant operations
- Context object holds current state
- States can change context's state

**Example Pattern**:
```java
interface State {
    void operation1();
    void operation2();
}

class State1 implements State {
    public void operation1() { /* implementation */ }
    public void operation2() { throw new Exception(); }
}

class Context {
    private State currentState;
    void setState(State s) { this.currentState = s; }
}
```

#### 2. Observer Design Pattern  
**Used In**: Cricbuzz (Score updates)
**Purpose**: Notify multiple observers when subject changes
**Implementation**:
- Subject maintains List<Observer>
- Observer interface with update() method
- Subject.notifyObservers() calls update() on all observers
- Observers update themselves based on event

**Example**: Ball event triggers batting and bowling score updates

#### 3. Chain of Responsibility
**Used In**: ATM (Cash withdrawal), Logging System
**Purpose**: Pass request through chain of handlers
**Implementation**:
- Handler interface with process() method
- Each handler has reference to next handler
- Handler processes what it can, forwards remainder
- Last handler in chain returns or throws exception

**Example**: 2000→500→100 note dispensing

#### 4. Factory Design Pattern
**Used In**: Payment Gateway (Instrument types), Splitwise (Split types)
**Purpose**: Create objects without specifying exact class
**Implementation**:
- Factory method returns interface/abstract class
- Based on input parameter, creates appropriate concrete class
- Allows adding new types without changing client code

#### 5. Strategy Design Pattern
**Used In**: Splitwise (Split strategies), Cricbuzz (Match types)
**Purpose**: Define family of algorithms, make them interchangeable
**Implementation**:
- Strategy interface with algorithm() method
- Concrete strategies implement different algorithms
- Context uses strategy interface

#### 6. MVC Pattern
**Used In**: BookMyShow (Movie/Theater Controllers)
**Purpose**: Separate data, logic, and presentation
**Implementation**:
- Model: Data objects (Movie, Theater, etc.)
- Controller: Business logic (MovieController, TheaterController)
- View: UI (not implemented in LLD, but architecture supports it)

#### 7. Template Method Pattern
**Used In**: Vehicle hierarchy (Car Rental)
**Purpose**: Define skeleton in parent, let children override steps
**Implementation**:
- Abstract parent with template method
- Children override specific steps
- Common logic stays in parent

#### 8. Composite Design Pattern
**Used In**: File System design
**Purpose**: Treat individual objects and compositions uniformly
**Implementation**:
- Component interface
- Leaf: individual object
- Composite: contains children (can be leaf or composite)

---

## Database Schemas & Data Structures

### Data Structures Used:

#### 1. BookMyShow
- **HashMap**: City → Movies, City → Theaters
- **List**: Seats in Screen, Shows in Theater
- **Optimistic Lock**: Version field on each Seat

#### 2. Cricbuzz
- **Queue**: Batting order (yet to play)
- **Deque**: Bowling rotation
- **Map**: Bowler → Over count
- **List**: Players, Overs, Balls

#### 3. Splitwise
- **Map**: User → Balance (balance sheet)
- **Map**: Friend → Balance (per-user friend balances)
- **List**: Users, Expenses, Splits

#### 4. Elevator System
- **PriorityQueue (MinHeap)**: UP direction requests
- **PriorityQueue (MaxHeap)**: DOWN direction requests  
- **Queue**: Pending jobs (opposite direction)
- **List**: Elevators, Floors

#### 5. Car Rental
- **List**: Users, Stores, Vehicles, Reservations
- **Map**: Could be used for quick lookups (not explicitly mentioned)

### Pseudo-Schema Representations:

#### BOOKMYSHOW Tables:

**Movie**
- movieId (PK)
- movieName
- movieDuration

**Theater**
- theaterId (PK)
- address
- city
- List<screenId> (FK)
- List<showId> (FK)

**Screen**
- screenId (PK)
- theaterId (FK)
- List<seatId> (FK)

**Seat**
- seatId (PK)
- screenId (FK)
- seatCategory
- row
- price

**Show**
- showId (PK)
- movieId (FK)
- screenId (FK)
- theaterId (FK)
- startTime
- bookedSeatIds (List<Integer>)

**Booking**
- bookingId (PK)
- showId (FK)
- userId (FK)
- List<seatId> (FK)
- paymentId (FK)

**Payment**
- paymentId (PK)
- bookingId (FK)
- amount
- status

---

#### CRICBUZZ Tables:

**Match**
- matchId (PK)
- teamAId (FK)
- teamBId (FK)
- venue
- matchDate
- matchType
- tossWinner

**Team**
- teamId (PK)
- teamName
- List<playerId> (FK)

**Player**
- playerId (PK)
- name
- address
- playerType

**BattingScoreCard**
- scoreCardId (PK)
- playerId (FK)
- matchId (FK)
- totalRuns
- totalBalls
- fours
- sixes
- strikeRate

**BowlingScoreCard**
- scoreCardId (PK)
- playerId (FK)
- matchId (FK)
- oversDelivered
- runsGiven
- wicketsTaken
- noBalls
- wideBalls
- economyRate

**Innings**
- inningsId (PK)
- matchId (FK)
- battingTeamId (FK)
- bowlingTeamId (FK)
- List<overId> (FK)

**Over**
- overId (PK)
- inningsId (FK)
- overNumber
- List<ballId> (FK)

**Ball**
- ballId (PK)
- overId (FK)
- ballNumber
- ballType
- runType
- playedBy (playerId FK)
- bowledBy (playerId FK)

---

#### SPLITWISE Tables:

**User**
- userId (PK)
- userName
- bankAccountId (FK)
- cardId (FK)

**Group**
- groupId (PK)
- groupName
- List<userId> (FK)

**Expense**
- expenseId (PK)
- groupId (FK)
- description
- amount
- paidBy (userId FK)
- expenseType
- createdDate

**Split**
- splitId (PK)
- expenseId (FK)
- userId (FK)
- amount
- percentage

**UserExpenseBalanceSheet**
- balanceSheetId (PK)
- userId (FK)
- friendId (userId FK)
- amountGetBack
- amountOwe

---

#### PAYMENT GATEWAY Tables:

**User**
- userId (PK)
- userName
- email
- drivingLicense

**Instrument**
- instrumentId (PK)
- userId (FK)
- instrumentType

**BankInstrument**
- instrumentId (PK, FK)
- bankAccountNumber
- ifscCode

**CardInstrument**
- instrumentId (PK, FK)
- cardNumber
- cvvNumber
- expiryDate

**Transaction**
- transactionId (PK)
- amount
- senderUserId (FK)
- receiverUserId (FK)
- debitInstrumentId (FK)
- creditInstrumentId (FK)
- status
- timestamp

---

## Interview Tips & Trap Questions

### General Interview Guidelines:

#### 1. **Design as Simple as Possible** (Critical - from Car Rental transcript)
- Don't add features unless interviewer asks
- When unsure, ask: "Do you want me to include X?"
- Most likely interviewer will say NO
- Adding too many features can backfire if you can't implement them

#### 2. **Start with Flow, Then Objects**
- First create requirement flow diagram
- Identify objects from the flow
- Then create relationships
- Finally create UML/class diagrams

#### 3. **Use Top-Down or Bottom-Up Appropriately**
- **Top-Down**: When product/service is central (Movie → Theater → Screen)
- **Bottom-Up**: When smaller components build up (Parking spot → Floor → Building)

#### 4. **State Pattern Identification**
- Question: "Different operations allowed in different states?"
- If YES → State Design Pattern
- Examples: ATM, Vending Machine, TV (On/Off states)

#### 5. **Concurrency Management**
- **Optimistic Locking**: Preferred for high-traffic scenarios (BookMyShow)
  - No lock on read
  - Version check on update
  - Best for: Movie tickets, product purchases
  
- **Pessimistic Locking**: Lock on read
  - Not recommended for high-traffic
  - Use only when conflicts are frequent

#### 6. **Separate Concerns**
- Don't put all logic in one class
- Use Controller classes for business logic
- Use Manager/Service classes for operations
- Example: VehicleInventoryManagement separate from Store

---

### Specific System Trap Questions:

#### BookMyShow Traps:

**Q1**: How do you handle concurrent seat booking?
**WRONG**: "Use database transactions"
**RIGHT**: "Use optimistic locking with version field. Check version before update, fail if changed."

**Q2**: What if payment fails after seat is booked?
**WRONG**: Ignore the scenario
**RIGHT**: "Use Redis lock with TTL (10-15 min). Auto-release if payment not completed. Or keep seat in PENDING status with timeout."

**Q3**: How do you ensure one seat isn't booked by two users?
**WRONG**: "Just check if seat is available"
**RIGHT**: "Optimistic locking. Each seat has version. User1 books with version check. User2's version check fails if User1 succeeded."

#### Elevator System Traps:

**Q4**: How do you decide which elevator to send?
**WRONG**: "Just use round-robin"
**RIGHT**: "Multiple strategies: ODD-EVEN, NEAREST, SHORTEST_WAIT. Let interviewer decide. For SHORTEST_WAIT, use LOOK algorithm with priority queues."

**Q5**: What if elevator is going UP and request comes from below current floor?
**WRONG**: "Change direction immediately"
**RIGHT**: "Add to pending queue. Complete all UP requests first, then process pending DOWN requests. This is LOOK algorithm."

**Q6**: How do you handle empty elevator going to top floor unnecessarily?
**WRONG**: Accept inefficiency
**RIGHT**: "Look-ahead optimization. Before continuing, check if requests exist ahead. If not, change direction."

#### Splitwise Traps:

**Q7**: How do you validate split amounts?
**WRONG**: Just divide equally
**RIGHT**: "Factory pattern for EQUAL vs PERCENTAGE. EQUAL: sum == total. PERCENTAGE: sum of percentages == 100%, compute amounts. Client can send amounts or percentages."

**Q8**: How do you track who owes whom?
**WRONG**: Single global balance
**RIGHT**: "Each user maintains BalanceSheet. Map<Friend, Balance>. Balance has amountOwe and amountGetBack. Per-friend granularity."

#### Payment Gateway Traps:

**Q9**: How do you handle different payment instruments?
**WRONG**: If-else for Bank vs Card
**RIGHT**: "Factory pattern. InstrumentServiceFactory returns BankService or CardService. Each has specific validation/processing logic. Easy to add UPI, Wallet, etc."

**Q10**: What if payment processing takes 3-5 days?
**WRONG**: Make client wait
**RIGHT**: "Async processing. Validate synchronously (balance check), create transaction in PENDING. Process asynchronously. Update status when processor responds."

#### ATM Traps:

**Q11**: How do you dispense cash in notes?
**WRONG**: Give all in smallest notes
**RIGHT**: "Chain of Responsibility. 2000 processor → 500 processor → 100 processor. Each dispenses maximum possible, forwards remainder."

**Q12**: How do you manage states?
**WRONG**: Multiple if-else blocks
**RIGHT**: "State Design Pattern. Each state implements only allowed operations. Unsupported operations throw exception. ATM holds currentState."

---

### What NOT to Say:

#### General DON'Ts:
- ❌ "I'll use microservices" (unless asked about scalability)
- ❌ "I'll add Kafka for messaging" (overkill for LLD)
- ❌ "Database will handle it" (you must design the logic)
- ❌ "We'll use cloud services" (focus on design, not infrastructure)

#### Concurrency DON'Ts:
- ❌ "Just use synchronized keyword" (too generic)
- ❌ "Database locking will handle it" (you need application-level strategy)
- ❌ "It won't happen" (conflicts are real in production)

#### Design Pattern DON'Ts:
- ❌ Overuse patterns (don't force-fit)
- ❌ Mix multiple patterns without clarity
- ❌ Use pattern names without understanding

---

## Scenario Questions & Answers

### BookMyShow Scenarios:

**Q1**: User selects seat, another user books it before payment completes. What happens?
**A**: Optimistic locking fails for second user. Version mismatch. Second user gets "seat already booked" message and must retry.

**Q2**: User books seat but doesn't complete payment in 15 minutes. What happens?
**A**: Redis lock expires. Seat becomes available again. First user's booking is cancelled if they return to pay later.

**Q3**: 100 users trying to book last seat. How do you handle?
**A**: All 100 read seat (version=1). First to update wins (version=2). Other 99 fail version check, must retry (but seat unavailable, booking fails).

**Q4**: Show started but some seats still showing as booked (payment pending). What to do?
**A**: Background job to cancel expired bookings. Release seats with payment pending > timeout. Update seat status to available.

**Q5**: How do you handle show cancellation?
**A**: Update Show status. Trigger refund for all bookings. Send notifications to users. Update Theater's show list.

---

### Cricbuzz Scenarios:

**Q6**: Ball is bowled, runs scored. How do you update scorecard?
**A**: Ball object notifies observers (BattingScoreCardUpdater, BowlingScoreCardUpdater). They update respective scorecards based on runType.

**Q7**: Batsman gets out. Who bats next?
**A**: PlayerBattingController.chooseNextBatsman() removes player from yetToPlay queue, assigns to striker/non-striker position.

**Q8**: Same bowler can't bowl consecutive overs. How to ensure?
**A**: PlayerBowlingController uses Deque. After over complete, remove from front, add to back (if overs remaining). Next bowler comes from front.

**Q9**: ODI becomes T20. How do you handle different rules?
**A**: MatchType strategy. ODI returns 50 overs, max 10 overs per bowler. T20 returns 20 overs, max 4 overs per bowler. Strategy pattern allows switching.

**Q10**: Mid-match, need to know current run rate, required run rate. How?
**A**: Compute from ScoreCards. Total runs from BattingScoreCard, total overs from Innings. Current RR = runs/overs. Required RR = (target - runs)/(overs remaining).

---

### Splitwise Scenarios:

**Q11**: Equal split of 100 among 3 people. How much does each pay?
**A**: SplitFactory creates EqualSplitValidator. 100/3 = 33.33 each. Validation: 33.33 + 33.33 + 33.34 = 100 ✓

**Q12**: Percentage split: Friend1 = 50%, Friend2 = 30%, Friend3 = 20%. Amount = 1000. Calculate.
**A**: Friend1 = 500, Friend2 = 300, Friend3 = 200. Validation: 50+30+20 = 100% ✓. Amounts: 500+300+200 = 1000 ✓

**Q13**: User1 paid 1000, split equally among User1, User2, User3. How to update balances?
**A**: 
- User1: Paid 1000, owes 333.33. Net: +666.67 (get back from others)
- User2: Paid 0, owes 333.33. Net: -333.33 (owe to User1)
- User3: Paid 0, owes 333.33. Net: -333.33 (owe to User1)

**Q14**: Multiple expenses in group. How to simplify?
**A**: Graph algorithm (mentioned by Splitwise CEO). Create debt graph. Find cycles and eliminate. Find minimum edges to settle all debts.

**Q15**: User leaves group. How to settle balances?
**A**: Calculate net balance for leaving user. If positive, collect from group. If negative, pay to group. Update remaining members' balances accordingly. Remove user from group.

---

### Payment Gateway Scenarios:

**Q16**: User has 3 bank accounts, 2 cards. Which instrument for transaction?
**A**: User selects debit instrument. For credit (receiving money), use user's default/preferred instrument. If not set, use latest added or random.

**Q17**: Transaction fails after debit but before credit. What happens?
**A**: Transaction remains in PENDING. Retry mechanism or manual intervention. Ideally, use distributed transaction or saga pattern (advanced). For LLD, mark as FAILED with rollback flag.

**Q18**: Add new instrument type (UPI). How does design handle it?
**A**: Create UPIInstrument extends Instrument. Create UPIService extends InstrumentService. Update InstrumentServiceFactory to return UPIService for UPI type. No changes to existing code.

**Q19**: Processor takes 5 days to respond. How do you handle?
**A**: Async processing. Transaction status = PENDING. Show user "Processing" message. Processor calls webhook when done. Update transaction status. Send notification to user.

**Q20**: User transaction fails due to insufficient balance. What to show user?
**A**: TransactionService validates balance before calling Processor. If insufficient, return error immediately with reason: "Insufficient balance. Available: X, Required: Y."

---

### Elevator Scenarios:

**Q21**: Elevator at floor 5, going UP. Request from floor 3 going DOWN. When does it serve?
**A**: Elevator continues UP, serves all UP requests. When MinHeap empty, change direction to DOWN. Move pending requests to MaxHeap. Then serve floor 3.

**Q22**: Elevator going UP to floor 10. Last request was floor 7. Should it go to 10?
**A**: No. Look-ahead optimization. After serving floor 7, check if more UP requests. If none, immediately change to DOWN. Don't waste time going to floor 10.

**Q23**: 3 elevators. User at floor 5 presses UP. Which elevator comes?
**A**: Depends on strategy. NEAREST: Calculate distance for each elevator, pick closest. ODD-EVEN: Floor 5 is odd, send odd elevator. SHORTEST_WAIT: Calculate ETA for each, send fastest.

**Q24**: Elevator at floor 3 going UP. Requests: floor 6 (UP), floor 4 (UP), floor 2 (DOWN). What order?
**A**: MinHeap (UP) = [4, 6]. MaxHeap (DOWN) = []. PendingJobs = [2]. Serve: 4 → 6 → change direction → 2.

**Q25**: Elevator full at floor 5, request from floor 6. What happens?
**A**: Advanced feature (not in basic LLD). Could add capacity check. If full, skip request, dispatch another elevator.

---

### ATM Scenarios:

**Q26**: User inserts card with wrong PIN 3 times. What happens?
**A**: ATM tracks failed attempts. After 3 failures, block card, change state to IDLE, return card. Notify user and bank.

**Q27**: ATM has 1×2000, 2×500, 5×100 notes. User requests 2700. Can it dispense?
**A**: Chain: 2000 dispenses 2000 (remaining 700) → 500 dispenses 500 (remaining 200) → 100 dispenses 200 (2 notes). Success! Remaining: 0×2000, 1×500, 3×100.

**Q28**: ATM has only 100 rupee notes. User requests 2500. What happens?
**A**: 100 processor dispenses 2500 (25 notes) if sufficient. If only 20 notes available, dispense 2000, mark as insufficient funds, return remaining balance to user account.

**Q29**: User cancels transaction after inserting card but before entering PIN. What state?
**A**: From HasCardState, call exitTransaction(). Change state to IDLE, return card, no charges.

**Q30**: ATM is in Idle state. User presses check balance button. What happens?
**A**: IdleState doesn't support checkBalance(). Throws exception or shows error. User must first insert card (go to HasCardState), then authenticate (go to SelectOperationState).

---

### Car Rental Scenarios:

**Q31**: User books car for tomorrow. Another user tries to book same car same time. What happens?
**A**: First booking creates Reservation (status=SCHEDULED). When second user searches, VehicleInventoryManagement checks reservations. Car shows as unavailable for that time slot.

**Q32**: User picks up car but doesn't return. How to handle?
**A**: Reservation status = IN_PROGRESS. Set expected return date. Background job checks overdue reservations. Send notifications. After grace period, charge penalty, mark as LATE.

**Q33**: User cancels reservation before pickup. Refund?
**A**: Update Reservation status = CANCELLED. Bill.isPaid = false or create refund record. Payment refund initiated. Vehicle becomes available again.

**Q34**: Store runs out of cars. User already has reservation. What to do?
**A**: Guaranteed reservation (already created). Store must honor it. Transfer car from another nearby store, or upgrade user to better vehicle at same price.

**Q35**: User returns car at different store than pickup. How to handle?
**A**: Reservation has pickupLocation and dropLocation. If different stores, update store inventories. Remove vehicle from pickup store, add to drop store inventory.

---

### General Cross-Cutting Scenarios:

**Q36**: How do you handle notifications across all systems?
**A**: Observer pattern or Message Queue. Event triggers notification. Different channels: Email, SMS, Push. Template-based messages.

**Q37**: How do you handle audit logs for all transactions?
**A**: Add AuditLog table/object. Record: userId, action, timestamp, entityType, entityId, before/after state. Triggered after every create/update/delete.

**Q38**: How to handle system downtime/maintenance?
**A**: Graceful shutdown. Stop accepting new requests. Complete in-flight requests. Return "Service Unavailable" for new requests. Maintenance window notification in advance.

**Q39**: How to handle data backup and recovery?
**A**: Regular snapshots. Transaction logs. Point-in-time recovery. For LLD, mention DB backup strategy (daily snapshots, binlog backups).

**Q40**: How do you scale horizontally?
**A**: Stateless services. Load balancer distributes requests. Shared database or database sharding. Cache layer (Redis). Message queue for async processing.

---

## Summary

This extraction covers:
- ✅ All major components from HLD/LLD diagrams
- ✅ Technology choices and design patterns with rationale
- ✅ Database schemas and data structures
- ✅ Interview tips and trap questions
- ✅ 40+ scenario questions with answers

**Note**: These transcripts are video lectures in Hindi/English. Exact latency numbers and capacity estimates are not provided in the transcripts as they focus on object-oriented design and design patterns rather than high-level system design metrics.

For detailed Draw.io diagrams, see the separate diagram files generated for each system.

---

## Files to Create:
1. ✅ This extraction document
2. 🔄 BookMyShow.drawio - Complete LLD diagram
3. 🔄 Cricbuzz.drawio - Complete LLD diagram
4. 🔄 Splitwise.drawio - Complete LLD diagram
5. 🔄 PaymentGateway.drawio - Complete LLD diagram
6. 🔄 ATM.drawio - Complete LLD diagram
7. 🔄 VendingMachine.drawio - Complete LLD diagram
8. 🔄 ElevatorSystem.drawio - Complete LLD diagram
9. 🔄 CarRental.drawio - Complete LLD diagram

