# LLD System Design Diagrams - Shrayansh's Series

This README documents comprehensive Low Level Design (LLD) diagrams extracted from Shrayansh's LLD video tutorial series.

**📍 Location**: Each diagram is now located in its respective video transcript folder alongside `transcript.md` and `video.html`

## 📂 File Organization

Each video folder now contains:
- `transcript.md` - Full transcript of the video
- `video.html` - Video embed/link
- `[Topic]_LLD.drawio` or `[Pattern]_Pattern.drawio` - Interactive diagram

**Example structure:**
```
17_14_LLD_of_BookMyShow_Hindi_Design_MovieTicketBooking.../
├── transcript.md
├── video.html
└── BookMyShow_LLD.drawio  ← Diagram here!
```

## 🗂️ Quick Reference - Diagram Locations

| Diagram File | Folder Location |
|--------------|-----------------|
| TicTacToe_LLD.drawio | `10_7_Design_Tic_Tac_Toe_game...` |
| Elevator_LLD.drawio | `11_8_Elevator_System_Low_Level_Design...` |
| CarRental_LLD.drawio | `12_9_LLD_of_Car_Rental_System...` |
| LoggingSystem_LLD.drawio | `13_10_Design_Logging_System...` |
| SnakeLadder_LLD.drawio | `14_11_LLD_of_Snake_and_Ladder_game...` |
| Proxy_Pattern.drawio | `16_13_Proxy_Design_Pattern...` |
| BookMyShow_LLD.drawio | `17_14_LLD_of_BookMyShow...` |
| NullObject_Pattern.drawio | `19_15_LLD_of_NULL_Object_Pattern...` |
| VendingMachine_LLD.drawio | `20_16_Design_Vending_Machine...` |
| ATM_LLD.drawio | `21_17_LLD_of_ATM...` |
| Chess_LLD.drawio | `22_18_Design_CHESS_GAME...` |
| FileSystem_LLD.drawio | `23_19_Design_File_System...` |
| Adapter_Pattern.drawio | `24_20_Adapter_Design_Pattern...` |
| Splitwise_LLD.drawio | `25_21_LLD_of_Splitwise...` |
| Builder_Pattern.drawio | `27_23_Builder_Design_Pattern...` |
| Cricbuzz_LLD.drawio | `28_24_LLD_of_CricbuzzCricInfo...` |
| Facade_Pattern.drawio | `29_25_Facade_Design_Pattern...` |
| Bridge_Pattern.drawio | `30_26_Bridge_Design_Pattern...` |
| InventoryManagement_LLD.drawio | `33_29_LLD_of_Inventory_Management_System...` |
| WordProcessor_LLD.drawio | `34_30_Design_Word_Processor...` |
| UndoRedo_LLD.drawio | `35_31_Design_Undo_Redo_feature...` |
| Iterator_Pattern.drawio | `37_33_Iterator_Design_Pattern...` |
| OnlineAuction_LLD.drawio | `38_34_Design_Online_Auction_System...` |
| ShoppingCartCoupons_LLD.drawio | `39_35_LLD_Apply_Coupons_on_Shopping_Cart...` |
| Visitor_Pattern.drawio | `40_36_Visitor_Design_Pattern...` |
| Memento_Pattern.drawio | `42_38_Memento_Design_Pattern...` |
| PaymentGateway_LLD.drawio | `46_42_LLD_of_Payment_Gateway...` |

## 📁 Available Diagrams

### ✅ Complete Diagrams (27 Systems & Design Patterns)

#### **Payment & Booking Systems**

1. **BookMyShow_LLD.drawio** - Movie Ticket Booking System
   - Design Patterns: MVC, Optimistic Locking
   - Key Feature: Concurrency control for seat booking
   - Sections: Class Diagram, ER Diagram, Scenario Questions

2. **PaymentGateway_LLD.drawio** - Payment Processing System
   - Design Patterns: Factory Pattern, DTO Pattern, Async Processing
   - Key Feature: Instrument management (Bank/Card), async payment processing
   - Scope: Peer-to-peer payments (NOT peer-to-merchant)

3. **Splitwise_LLD.drawio** - Expense Sharing App
   - Design Pattern: Factory Pattern (EQUAL/PERCENTAGE splits)
   - Key Feature: Balance sheet management, debt simplification
   - Validation: Split amounts, percentage calculations

4. **CarRental_LLD.drawio** - Car Rental System (ZoomCar)
   - Design Pattern: Template Method Pattern
   - Key Feature: Separation of concerns (Store vs InventoryManagement)
   - Interview Tip: "Design as SIMPLE as possible"

#### **Real-time & Scoring Systems**

5. **[Cricbuzz_LLD.drawio](Cricbuzz_LLD.drawio)** - Cricket Scoring System
   - Design Pattern: Observer Pattern
   - Key Feature: Real-time score updates (ball-by-ball)
   - Data Structures: Queue (batting), Deque (bowling), Map (over tracking)

#### **State Machine Systems**

6. **[ATM_LLD.drawio](ATM_LLD.drawio)** - ATM System
   - Design Patterns: State Pattern + Chain of Responsibility
   - Key Feature: State transitions + Cash dispensing (2000→500→100)
   - States: Idle → HasCard → SelectOperation → CashWithdrawal

7. **[VendingMachine_LLD.drawio](VendingMachine_LLD.drawio)** - Vending Machine
   - Design Pattern: State Pattern
   - Key Feature: State-based operation control
   - States: Idle → HasMoney → Selection → Dispensing

#### **Optimization Algorithms**

8. **[Elevator_LLD.drawio](Elevator_LLD.drawio)** - Elevator System
   - Algorithm: LOOK/SCAN with Look-ahead optimization
   - Data Structures: MinHeap (UP requests), MaxHeap (DOWN requests), Queue (pending)
   - Key Feature: Efficient elevator dispatching (ODD-EVEN, NEAREST, SHORTEST_WAIT)

#### **Game Designs**

9. **[TicTacToe_LLD.drawio](TicTacToe_LLD.drawio)** - Tic-Tac-Toe Game
   - Design Pattern: Template Method (PlayingPiece hierarchy)
   - Key Feature: N×N extensible board, Queue-based turn management
   - Approach: Top-down design

10. **[SnakeLadder_LLD.drawio](SnakeLadder_LLD.drawio)** - Snake and Ladder Game
    - Design Pattern: Template Method (Jump hierarchy)
    - Key Feature: Queue-based turn rotation, chain jumps
    - Algorithm: Position validation, overshoot handling

11. **[Chess_LLD.drawio](Chess_LLD.drawio)** - Chess Game
    - Design Pattern: Strategy Pattern (piece movement strategies)
    - Key Feature: Complex movement validation, special moves (castling, en passant, promotion)
    - Complexity: Check, Checkmate, Stalemate detection

#### **Infrastructure & Logging**

12. **[LoggingSystem_LLD.drawio](LoggingSystem_LLD.drawio)** - Logging System
    - Design Pattern: Chain of Responsibility
    - Key Feature: Log level filtering, multiple outputs
    - Chain: ERROR → DEBUG → INFO → null

13. **[FileSystem_LLD.drawio](FileSystem_LLD.drawio)** - File System Design
    - Design Pattern: Composite Pattern
    - Key Feature: Tree structure (directory inside directory)

14. **[InventoryManagement_LLD.drawio](InventoryManagement_LLD.drawio)** - Inventory Management System
    - Design Pattern: Factory + DAO Pattern
    - Key Feature: Stock management, warehouse organization

15. **[OnlineAuction_LLD.drawio](OnlineAuction_LLD.drawio)** - Online Auction System
    - Design Pattern: Mediator Pattern
    - Key Feature: Bid management, auction lifecycle

16. **[ShoppingCartCoupons_LLD.drawio](ShoppingCartCoupons_LLD.drawio)** - Shopping Cart with Coupons
    - Design Pattern: Chain of Responsibility (coupon validation)
    - Key Feature: Discount calculation chain

17. **[WordProcessor_LLD.drawio](WordProcessor_LLD.drawio)** - Word Processor
    - Design Pattern: Command Pattern
    - Key Feature: Document operations with undo support

18. **[UndoRedo_LLD.drawio](UndoRedo_LLD.drawio)** - Undo-Redo System
    - Design Pattern: Command Pattern + Stack
    - Key Feature: Action history management

#### **Standalone Design Patterns**

19. **[Null_Object_Pattern.drawio](Null_Object_Pattern.drawio)** - Null Object Pattern
    - Purpose: Avoid null checks by providing default behavior
    - Example: Vehicle (Car, Bike, NullVehicle)

20. **[Proxy_Pattern.drawio](Proxy_Pattern.drawio)** - Proxy Pattern
    - Purpose: Control access to real object (lazy load, cache, security)
    - Example: EmployeeDao + EmployeeDaoProxy

21. **[Adapter_Pattern.drawio](Adapter_Pattern.drawio)** - Adapter Pattern
    - Purpose: Make incompatible interfaces work together
    - Example: Power socket adapter (round plug → square socket)

22. **[Builder_Pattern.drawio](Builder_Pattern.drawio)** - Builder Pattern
    - Purpose: Construct complex objects step-by-step
    - Example: Student object with many optional fields

23. **[Bridge_Pattern.drawio](Bridge_Pattern.drawio)** - Bridge Pattern
    - Purpose: Decouple abstraction from implementation
    - Example: LivingThing + BreatheImplementer (fish/tree/dog breathe differently)

24. **[Facade_Pattern.drawio](Facade_Pattern.drawio)** - Facade Pattern
    - Purpose: Simplify complex subsystem with unified interface
    - Example: OrderFacade hiding ProductDao/Payment/Invoice/Notification

25. **[Iterator_Pattern.drawio](Iterator_Pattern.drawio)** - Iterator Pattern
    - Purpose: Sequential access without exposing data structure
    - Example: Java Collections (ArrayList, LinkedList, HashSet all use same iterator interface)

26. **[Visitor_Pattern.drawio](Visitor_Pattern.drawio)** - Visitor Pattern
    - Purpose: Add operations to existing class hierarchy without modification (double dispatch)
    - Example: Hotel room operations (pricing, maintenance, reservation)

27. **[Memento_Pattern.drawio](Memento_Pattern.drawio)** - Memento Pattern
    - Purpose: Save & restore object state (undo functionality)
    - Example: Configuration snapshots with undo/redo support

---

## 📋 Diagram Structure

Each diagram contains **3 main sections**:

### SECTION 1-3: CLASS DIAGRAM & RELATIONSHIPS
- All classes/objects with attributes and methods
- Relationships (associations, aggregations, inheritances)
- Design patterns implementation
- Color coding:
  - 🔵 Blue: Core entities
  - 🟡 Yellow: Controllers/Services
  - 🔴 Red: Important business logic classes
  - 🟣 Purple: Interfaces/Abstract classes
  - 🟢 Green: Concrete implementations
  - 🟠 Orange: Enums

### SECTION 4: ER DIAGRAM (Database Schema)
- All database tables with columns
- Primary Keys (PK) and Foreign Keys (FK)
- Data types
- Relationships between tables
- Constraints

### SECTION 7: SCENARIO QUESTIONS (Interview Focus)
- 5 Q&A per system focusing on:
  - **Failure cases**: What happens when things go wrong?
  - **Scale**: How to handle millions of users?
  - **Trade-offs**: Why this approach over alternatives?
  - **Senior trap questions**: Common mistakes to avoid

---

## 🎨 How to Use These Diagrams

### Opening in Draw.io
1. Go to [app.diagrams.net](https://app.diagrams.net)
2. File → Open → Navigate to the specific video folder
3. Select the `.drawio` file
4. Edit, zoom, export as needed

### Finding a Diagram
- **Quick Reference**: See the "Quick Reference - Diagram Locations" table above
- **By Topic**: Each diagram is in the folder matching its topic (e.g., BookMyShow diagram is in the BookMyShow folder)
- **All at Once**: Use the file search in your code editor to find `*.drawio` files

### For Interview Preparation
1. **Study the class diagrams** to understand object relationships
2. **Review ER diagrams** to learn database design
3. **Practice scenario questions** - these are common in LLD interviews
4. **Understand design patterns** - highlighted in each diagram

### For Implementation
- Use diagrams as blueprints for coding
- Follow the exact class structures shown
- Implement design patterns as demonstrated
- Refer to ER diagrams for database schema creation

---

## 🔑 Key Design Patterns Covered

| Pattern | Systems Using It | Purpose |
|---------|------------------|---------|
| **State Pattern** | ATM, Vending Machine | Different operations in different states |
| **Observer Pattern** | Cricbuzz | Real-time score updates |
| **Chain of Responsibility** | ATM (cash), Logging System, Shopping Cart | Pass request through chain |
| **Factory Pattern** | Payment Gateway, Splitwise | Create objects without specifying class |
| **Strategy Pattern** | Cricbuzz, Elevator, Chess | Interchangeable algorithms |
| **MVC Pattern** | BookMyShow | Separate data, logic, presentation |
| **Template Method** | Car Rental, TicTacToe, SnakeLadder | Abstract parent, concrete children |
| **Optimistic Locking** | BookMyShow | Concurrency control |
| **DTO Pattern** | Payment Gateway | Separate client view from DB |
| **Composite Pattern** | File System | Tree structure, object inside object |
| **Mediator Pattern** | Online Auction | Centralized communication |
| **Command Pattern** | Word Processor, Undo-Redo | Encapsulate commands, support undo |
| **Null Object Pattern** | Standalone | Avoid null checks with default behavior |
| **Proxy Pattern** | Standalone | Control access (security, lazy load, cache) |
| **Adapter Pattern** | Standalone | Make incompatible interfaces compatible |
| **Builder Pattern** | Standalone | Construct complex objects step-by-step |
| **Bridge Pattern** | Standalone | Decouple abstraction from implementation |
| **Facade Pattern** | Standalone | Simplify complex subsystem |
| **Iterator Pattern** | Standalone | Sequential access without exposing structure |
| **Visitor Pattern** | Standalone | Add operations without modifying classes (double dispatch) |
| **Memento Pattern** | Standalone | Save & restore object state (undo) |

---

## 📚 Complete System List from Transcripts

### ✅ Diagrams Created (27 systems + design patterns)
1. BookMyShow - Movie Ticket Booking
2. Cricbuzz - Cricket Scoring
3. ATM System - Cash Withdrawal
4. Elevator System - Multi-floor Control
5. Splitwise - Expense Sharing
6. Payment Gateway - Payment Processing
7. Car Rental (ZoomCar) - Vehicle Rental
8. Vending Machine - Product Dispensing
9. Tic-Tac-Toe - Game Design
10. Snake & Ladder - Board Game
11. Chess Game - Complex Game Rules
12. Logging System - Chain of Responsibility
13. File System - Composite Pattern
14. Inventory Management - Order Management
15. Online Auction - Mediator Pattern
16. Shopping Cart Coupons - Decorator Pattern
17. Word Processor - Flyweight Pattern
18. Undo/Redo Feature - Command Pattern
19. **Null Object Pattern** - Eliminate null checks
20. **Proxy Pattern** - Access control, caching, preprocessing
21. **Adapter Pattern** - Bridge incompatible interfaces
22. **Builder Pattern** - Step-by-step object construction
23. **Bridge Pattern** - Decouple abstraction from implementation
24. **Facade Pattern** - Simplify complex subsystem interface
25. **Iterator Pattern** - Sequential access without exposing structure
26. **Visitor Pattern** - Add operations without modifying classes
27. **Memento Pattern** - Save & restore object state

---

## 💡 Interview Tips from the Series

### General Guidelines:
1. **Design as SIMPLE as possible** - Don't add features unless interviewer asks
2. **Start with flow, then objects** - Flow diagram → Objects → Relationships → UML
3. **Ask before adding features** - "Do you want me to include X?"
4. **Separate concerns** - Don't put all logic in one class
5. **State pattern identification** - "Different operations in different states?" → State Pattern

### Concurrency:
- **Optimistic Locking**: Preferred for high-traffic (BookMyShow tickets)
- **Pessimistic Locking**: Only when conflicts frequent (not recommended for high-traffic)

### What NOT to Say:
- ❌ "I'll use microservices" (unless asked about scalability)
- ❌ "Database will handle it" (you must design the logic)
- ❌ "Just use synchronized" (too generic)

---

## 🔗 Related Files

- **[COMPREHENSIVE_LLD_EXTRACTION.md](../COMPREHENSIVE_LLD_EXTRACTION.md)** - Complete text extraction of all systems
  - All components and objects
  - Technology choices with rationale
  - Database schemas
  - Interview tips and trap questions
  - 40+ scenario questions with answers

---

## 📖 Source

All diagrams are based on **Shrayansh's LLD Tutorial Series** (Hindi/English mixed language).  
The series covers 27 complete systems and design patterns (ALL from Shrayansh's LLD series!)  
**Format**: Draw.io XML (.drawio)  
**Coverage**: 100% of major systems and design patterns from the tutorial series
---

## 🤝 Contributing

These diagrams are extracted from video transcripts. If you find any discrepancies or want to add more systems:
1. Refer to the original video transcripts
2. Follow the same structure (3 sections)
3. Maintain color coding consistency
4. Include scenario questions with answers

---

## 📝 Notes

- All diagrams are in draw.io XML format
- ER diagrams show logical schema (may need normalization for production)
- Scenario questions are typical interview questions from the tutorials
- Design patterns are explicitly highlighted in each diagram
- Some systems may have variations - diagrams show core concepts

---

**Last Updated**: 2026-08-31  
**Total Diagrams**: 27 complete systems + design patterns  
**Format**: Draw.io XML (.drawio)  
**Coverage**: 18 system designs + 9 standalone design patterns
