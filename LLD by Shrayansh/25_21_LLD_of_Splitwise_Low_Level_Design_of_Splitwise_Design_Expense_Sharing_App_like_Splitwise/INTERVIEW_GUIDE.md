# 💰 Splitwise - Low Level Design Interview Guide
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

## **Design Pattern Used**: Strategy Pattern (for split types)

**Interviewer**: "Design Splitwise - an expense sharing application."

**You**: "Excellent question! Let me clarify the scope. Should the app support:
1. Adding friends and creating groups?
2. Recording expenses with multiple split strategies (equal, percentage, exact amounts)?
3. Balance sheet showing who owes whom?
4. Debt simplification (reducing number of transactions)?
5. Settlement tracking?"

**Interviewer**: "Yes, all of those. Focus on expense splitting and balance management."

**You**: "Perfect. The key insights here are:
1. **Multiple split strategies**: Equal split, percentage split, exact amounts
2. **Balance management**: Per-user view showing debts and credits
3. **Graph-based debt simplification**: Minimize number of transactions

I'll use **Strategy Pattern** for split logic and **graph algorithms** for debt simplification. Let me show you..."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SPLITWISE ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────┐
                            │     USER     │
                            │              │
                            │ Friends List │
                            │ Balance Sheet│
                            └──────┬───────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │   FRIEND 1   │  │   FRIEND 2   │  │   FRIEND 3   │
         │              │  │              │  │              │
         │ Balance: +500│  │ Balance: -200│  │ Balance: -300│
         └──────────────┘  └──────────────┘  └──────────────┘

                        ┌──────────────────────┐
                        │    EXPENSE MODEL     │
                        │                      │
                        │  ExpenseId           │
                        │  Amount: 300         │
                        │  PaidBy: User1       │
                        │  SplitType: EQUAL    │
                        │  Splits: [User1,     │
                        │           User2,     │
                        │           User3]     │
                        └──────────┬───────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │EQUAL SPLIT   │  │PERCENT SPLIT │  │EXACT SPLIT   │
         │              │  │              │  │              │
         │ 300/3 = 100  │  │ 10%, 20%, 70%│  │ 50, 100, 150 │
         │ per person   │  │ of 300       │  │ (specified)  │
         └──────────────┘  └──────────────┘  └──────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  BALANCE SHEET       │
                        │  CONTROLLER          │
                        │                      │
                        │ Updates:             │
                        │ - User balances      │
                        │ - Friend-wise debts  │
                        │ - Total expenses     │
                        └──────────────────────┘

                        ┌──────────────────────┐
                        │  DEBT SIMPLIFIER     │
                        │  (Graph Algorithm)   │
                        │                      │
                        │ Input: User debts    │
                        │ Output: Minimal txns │
                        └──────────────────────┘
```

### **Why This Design?**

**You**: "Key architectural decisions:

1. **User-centric balance sheet**: Each user maintains their own view - total owed, total to receive, friend-wise breakdown. Like LinkedIn - personalized!

2. **Strategy Pattern for splits**: Different split types (Equal/Percentage/Exact) have different validation and calculation logic. Strategy makes this pluggable.

3. **Balance Sheet Controller**: Centralized logic to update all affected users' balances when expense is created. Ensures consistency.

4. **Debt Simplification**: Optional graph-based optimization - reduces 10 transactions to maybe 3. Uses greedy algorithm."

---

## 2. API Design

### **2.1 User & Friend Management**

```http
POST /api/v1/users
Request:
{
  "name": "Shreyans",
  "email": "shreyans@example.com",
  "phone": "+91-9876543210"
}

Response: 201 CREATED
{
  "userId": "user-1234",
  "name": "Shreyans",
  "createdAt": "2026-08-31T10:00:00Z"
}

---

POST /api/v1/users/{userId}/friends
Request:
{
  "friendUserId": "user-5678"
}

Response: 200 OK
{
  "friendship": {
    "user1": "user-1234",
    "user2": "user-5678",
    "createdAt": "2026-08-31T10:05:00Z"
  }
}

---

GET /api/v1/users/{userId}/balance
Response: 200 OK
{
  "userId": "user-1234",
  "totalExpense": 5000.00,
  "totalPaid": 3000.00,
  "totalOwed": 2000.00,      // Money user owes to others
  "totalReceivable": 1000.00,  // Money others owe to user
  "netBalance": -1000.00,     // Negative = user owes money overall
  
  "friendBalances": [
    {
      "friendId": "user-5678",
      "friendName": "Rahul",
      "youOwe": 500.00,       // You owe Rahul 500
      "owesYou": 0.00
    },
    {
      "friendId": "user-9999",
      "friendName": "Priya",
      "youOwe": 0.00,
      "owesYou": 300.00       // Priya owes you 300
    }
  ]
}
```

### **2.2 Group Management**

```http
POST /api/v1/groups
Request:
{
  "name": "Goa Trip 2026",
  "members": ["user-1234", "user-5678", "user-9999"],
  "createdBy": "user-1234"
}

Response: 201 CREATED
{
  "groupId": "group-4567",
  "name": "Goa Trip 2026",
  "memberCount": 3,
  "totalExpenses": 0.00
}

---

POST /api/v1/groups/{groupId}/members
Request:
{
  "userId": "user-7777"
}

Response: 200 OK
{
  "groupId": "group-4567",
  "memberCount": 4
}
```

### **2.3 Expense Management**

```http
POST /api/v1/expenses
Request:
{
  "description": "Lunch at Taj",
  "amount": 900.00,
  "paidBy": "user-1234",
  "groupId": "group-4567",  // Optional
  "splitType": "EQUAL",
  "splits": [
    {"userId": "user-1234", "amount": null},  // Auto-calculated for EQUAL
    {"userId": "user-5678", "amount": null},
    {"userId": "user-9999", "amount": null}
  ]
}

Response: 201 CREATED
{
  "expenseId": "exp-8888",
  "amount": 900.00,
  "paidBy": "user-1234",
  "splits": [
    {"userId": "user-1234", "amount": 300.00},  // 900/3
    {"userId": "user-5678", "amount": 300.00},
    {"userId": "user-9999", "amount": 300.00}
  ],
  "balanceUpdates": [
    {"userId": "user-1234", "change": +600.00},  // Paid 900, owed 300, so +600 credit
    {"userId": "user-5678", "change": -300.00},  // Owes 300
    {"userId": "user-9999", "change": -300.00}   // Owes 300
  ]
}

---

POST /api/v1/expenses  (Percentage split)
Request:
{
  "description": "Cab fare",
  "amount": 500.00,
  "paidBy": "user-1234",
  "splitType": "PERCENTAGE",
  "splits": [
    {"userId": "user-1234", "percentage": 40},  // 40% = 200
    {"userId": "user-5678", "percentage": 30},  // 30% = 150
    {"userId": "user-9999", "percentage": 30}   // 30% = 150
  ]
}

Response: 201 CREATED
{
  "expenseId": "exp-9999",
  "splits": [
    {"userId": "user-1234", "amount": 200.00},
    {"userId": "user-5678", "amount": 150.00},
    {"userId": "user-9999", "amount": 150.00}
  ]
}

---

POST /api/v1/expenses  (Exact split)
Request:
{
  "description": "Shopping",
  "amount": 1000.00,
  "paidBy": "user-1234",
  "splitType": "EXACT",
  "splits": [
    {"userId": "user-1234", "amount": 400.00},
    {"userId": "user-5678", "amount": 350.00},
    {"userId": "user-9999", "amount": 250.00}
  ]
}
```

### **2.4 Settlement**

```http
POST /api/v1/settlements
Request:
{
  "payerId": "user-5678",
  "receiverId": "user-1234",
  "amount": 300.00,
  "note": "Settling lunch expense"
}

Response: 200 OK
{
  "settlementId": "settle-1111",
  "status": "COMPLETED",
  "balanceUpdates": {
    "user-5678": {
      "before": -300.00,
      "after": 0.00
    },
    "user-1234": {
      "before": +300.00,
      "after": 0.00
    }
  }
}
```

### **Why This API Design?**

**You**: "Notice:
1. **Validation in request**: For EQUAL split, amounts are null (server calculates). For PERCENTAGE/EXACT, client provides values but server validates.
2. **Balance updates in response**: Immediately shows impact - user knows their balance changed.
3. **Group optional**: Expense can be standalone (just between friends) or part of group.
4. **Idempotency**: Settlement uses unique ID - duplicate calls don't double-settle."

---

## 3. ER Diagram & Database Design

```
┌───────────────────────────────────────────────────────────────────────────┐
│                            ER DIAGRAM                                     │
└───────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐                    ┌──────────────┐
    │     USER     │                    │  FRIENDSHIP  │
    │──────────────│                    │──────────────│
    │*userId       │───────────────────▶│*user1Id (FK) │
    │ name         │                    │*user2Id (FK) │
    │ email        │                    │ createdAt    │
    │ phone        │                    └──────────────┘
    └──────┬───────┘
           │
           │ 1:N
           ▼
    ┌──────────────┐
    │ USER_BALANCE │
    │──────────────│
    │*userId   (FK)│
    │ totalExpense │
    │ totalPaid    │
    │ totalOwed    │
    │ totalReceive │
    └──────────────┘

    ┌──────────────┐                    ┌──────────────┐
    │    GROUP     │                    │GROUP_MEMBER  │
    │──────────────│                    │──────────────│
    │*groupId      │───────────────────▶│*groupId  (FK)│
    │ name         │                    │*userId   (FK)│
    │ createdBy(FK)│                    │ joinedAt     │
    │ createdAt    │                    └──────────────┘
    └──────────────┘

    ┌──────────────┐
    │   EXPENSE    │
    │──────────────│
    │*expenseId    │
    │ description  │
    │ amount       │
    │ paidBy   (FK)│
    │ groupId  (FK)│  // Nullable
    │ splitType    │
    │ createdAt    │
    └──────┬───────┘
           │
           │ 1:N
           ▼
    ┌──────────────┐
    │EXPENSE_SPLIT │
    │──────────────│
    │*expenseId(FK)│
    │*userId   (FK)│
    │ amount       │
    │ percentage   │  // Only for PERCENTAGE type
    └──────────────┘

    ┌──────────────┐
    │FRIEND_BALANCE│
    │──────────────│
    │*userId   (FK)│
    │*friendId (FK)│
    │ youOwe       │
    │ owesYou      │
    └──────────────┘

    ┌──────────────┐
    │ SETTLEMENT   │
    │──────────────│
    │*settlementId │
    │ payerId  (FK)│
    │ receiverId(FK│
    │ amount       │
    │ note         │
    │ settledAt    │
    └──────────────┘
```

### **Schema Details**

```sql
CREATE TABLE user_balance (
    user_id VARCHAR(50) PRIMARY KEY,
    total_expense DECIMAL(15,2) DEFAULT 0.00,  -- Total amount user participated in
    total_paid DECIMAL(15,2) DEFAULT 0.00,     -- Total amount user paid
    total_owed DECIMAL(15,2) DEFAULT 0.00,     -- User owes others
    total_receivable DECIMAL(15,2) DEFAULT 0.00,  -- Others owe user
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE friend_balance (
    user_id VARCHAR(50) NOT NULL,
    friend_id VARCHAR(50) NOT NULL,
    you_owe DECIMAL(15,2) DEFAULT 0.00,    -- How much user owes this friend
    owes_you DECIMAL(15,2) DEFAULT 0.00,   -- How much this friend owes user
    
    PRIMARY KEY (user_id, friend_id),
    CHECK (you_owe >= 0 AND owes_you >= 0),
    CHECK (NOT (you_owe > 0 AND owes_you > 0)),  -- Can't both owe each other
    INDEX idx_friend_id (friend_id)
);

CREATE TABLE expense_splits (
    expense_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    percentage DECIMAL(5,2),  -- Nullable, only for PERCENTAGE split
    
    PRIMARY KEY (expense_id, user_id),
    FOREIGN KEY (expense_id) REFERENCES expenses(expense_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    CHECK (amount >= 0)
);

CREATE TABLE expenses (
    expense_id VARCHAR(50) PRIMARY KEY,
    description VARCHAR(255) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    paid_by VARCHAR(50) NOT NULL,
    group_id VARCHAR(50),  -- Nullable
    split_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CHECK (amount > 0),
    CHECK (split_type IN ('EQUAL', 'PERCENTAGE', 'EXACT')),
    INDEX idx_paid_by (paid_by),
    INDEX idx_group_id (group_id),
    INDEX idx_created (created_at)
);
```

### **Why This Schema?**

**You**: "Key design decisions:

1. **`friend_balance` table**: Core innovation! Each user-friend pair has `you_owe` and `owes_you`. CHECK constraint ensures only one is positive (can't both owe each other - would simplify).

2. **`user_balance` aggregate table**: Denormalized for performance. Total owed/receivable calculated from `friend_balance`, but cached here for fast dashboard queries.

3. **`expense_splits` junction table**: Many-to-many between expenses and users. Stores final amount each user owes for that expense.

4. **Split validation in application layer**: Database stores result, but validation (sum equals total, percentages add to 100%) happens in app code."

---

## 4. Sequence Diagrams

### **4.1 Happy Path: Create Equal Split Expense**

```
User    API     ExpenseController   SplitFactory   BalanceController   DB
 │       │              │                 │                │            │
 │─POST /expenses──▶│              │                 │                │            │
 │       │              ├─createExpense──▶│                 │                │            │
 │       │              │                 ├─getSplitHandler(EQUAL)──▶│            │
 │       │              │                 │                 │                │            │
 │       │              │                 │  Returns EqualSplitStrategy           │
 │       │              │◀────────────────│                 │                │            │
 │       │              │                 │                 │                │            │
 │       │              ├─validateSplit──▶│                 │                │            │
 │       │              │                 │  Check: 900 / 3 users = 300 each     │
 │       │              │◀────valid───────│                 │                │            │
 │       │              │                 │                 │                │            │
 │       │              ├─saveExpense─────────────────────────────────────▶│
 │       │              │◀exp-1234────────────────────────────────────────│
 │       │              │                 │                 │                │            │
 │       │              ├─updateBalances─────────────────▶│                │            │
 │       │              │                 │                 │  For user1 (paid 900, owes 300):
 │       │              │                 │                 │    total_paid += 900
 │       │              │                 │                 │    total_expense += 300
 │       │              │                 │                 │    total_receivable += 600
 │       │              │                 │                 │                │            │
 │       │              │                 │                 │  For user2 (owes 300):
 │       │              │                 │                 │    total_expense += 300
 │       │              │                 │                 │    total_owed += 300
 │       │              │                 │                 │    friend_balance(user2, user1).you_owe += 300
 │       │              │                 │                 │                │            │
 │       │              │                 │                 ├─batch UPDATE──▶│
 │       │              │                 │                 │◀success────────│
 │       │              │◀balances updated────────────────│                │            │
 │◀200 OK──────────────│                 │                 │                │            │
```

### **4.2 Debt Simplification**

```
Scenario: 3 users with complex debts

Before simplification:
- User1 owes User2: 100
- User2 owes User3: 150
- User3 owes User1: 50

After simplification (optimal):
- User1 owes User3: 50  (net result of all debts)

Algorithm:
User    DebtSimplifier   GraphBuilder   GreedyAlgorithm
 │            │                │               │
 │─simplify──▶│                │               │
 │            ├─buildGraph────▶│               │
 │            │                │ Create nodes: [User1, User2, User3]
 │            │                │ Create edges: {
 │            │                │   User1→User2: 100
 │            │                │   User2→User3: 150
 │            │                │   User3→User1: 50
 │            │                │ }
 │            │◀graph──────────│               │
 │            │                │               │
 │            ├─simplifyDebts──────────────────▶│
 │            │                │               │ Calculate net balance:
 │            │                │               │   User1: -100 + 50 = -50 (owes 50)
 │            │                │               │   User2: +100 - 150 = -50 (owes 50)
 │            │                │               │   User3: +150 - 50 = +100 (receives 100)
 │            │                │               │
 │            │                │               │ Match creditors ↔ debtors:
 │            │                │               │   User1 (-50) → User3 (+100): Pay 50
 │            │                │               │   User2 (-50) → User3 (+100): Pay 50
 │            │◀simplified transactions────────│
 │◀result─────│                │               │

Result: 3 original transactions → 2 optimized transactions
```

**You**: "See the power of graph algorithms! Original: User1→User2→User3→User1 (circular dependency). Simplified: Just two direct payments. Used **Greedy Algorithm** - match largest creditor with largest debtor, repeat."

---

## 5. Scenario-First Explanations

### **5.1 Why Strategy Pattern for Split Types?**

**Scenario**: "User creates expense ₹300, wants equal split among 3 friends"

**You**: "Without Strategy Pattern:
```java
class ExpenseService {
    void createExpense(Expense expense) {
        if (expense.getSplitType() == SplitType.EQUAL) {
            // Validation: Just check if members exist
            double perPerson = expense.getAmount() / expense.getMembers().size();
            for (User user : expense.getMembers()) {
                createSplit(expense, user, perPerson);
            }
            
        } else if (expense.getSplitType() == SplitType.PERCENTAGE) {
            // Validation: Sum of percentages must be 100%
            double totalPercent = 0;
            for (Split split : expense.getSplits()) {
                totalPercent += split.getPercentage();
            }
            if (totalPercent != 100) throw new ValidationException();
            
            for (Split split : expense.getSplits()) {
                double amount = expense.getAmount() * split.getPercentage() / 100;
                createSplit(expense, split.getUser(), amount);
            }
            
        } else if (expense.getSplitType() == SplitType.EXACT) {
            // Validation: Sum of amounts must equal total
            double totalAmount = 0;
            for (Split split : expense.getSplits()) {
                totalAmount += split.getAmount();
            }
            if (totalAmount != expense.getAmount()) throw new ValidationException();
            
            for (Split split : expense.getSplits()) {
                createSplit(expense, split.getUser(), split.getAmount());
            }
        }
    }
}
// ❌ Messy! Adding new split type (e.g., SHARES) requires modifying this method!
```

With Strategy Pattern:
```java
interface SplitStrategy {
    void validate(Expense expense);
    List<ExpenseSplit> calculate(Expense expense);
}

class EqualSplitStrategy implements SplitStrategy {
    void validate(Expense expense) {
        // No special validation needed
    }
    
    List<ExpenseSplit> calculate(Expense expense) {
        double perPerson = expense.getAmount() / expense.getMembers().size();
        return expense.getMembers().stream()
            .map(user -> new ExpenseSplit(user, perPerson))
            .collect(Collectors.toList());
    }
}

class PercentageSplitStrategy implements SplitStrategy {
    void validate(Expense expense) {
        double totalPercent = expense.getSplits().stream()
            .mapToDouble(Split::getPercentage)
            .sum();
        if (totalPercent != 100) {
            throw new ValidationException("Percentages must add to 100%");
        }
    }
    
    List<ExpenseSplit> calculate(Expense expense) {
        return expense.getSplits().stream()
            .map(split -> new ExpenseSplit(
                split.getUser(),
                expense.getAmount() * split.getPercentage() / 100
            ))
            .collect(Collectors.toList());
    }
}

class SplitFactory {
    private Map<SplitType, SplitStrategy> strategies = Map.of(
        SplitType.EQUAL, new EqualSplitStrategy(),
        SplitType.PERCENTAGE, new PercentageSplitStrategy(),
        SplitType.EXACT, new ExactSplitStrategy()
    );
    
    SplitStrategy getStrategy(SplitType type) {
        return strategies.get(type);
    }
}

// Usage (clean!):
class ExpenseService {
    void createExpense(Expense expense) {
        SplitStrategy strategy = splitFactory.getStrategy(expense.getSplitType());
        strategy.validate(expense);  // ✓
        List<ExpenseSplit> splits = strategy.calculate(expense);  // ✓
        saveSplits(splits);
    }
}
// ✅ Adding new split type? Just create new strategy class, no modifications!
```

**Benefits**: Open/Closed Principle - open for extension (new strategies), closed for modification (existing code unchanged)."

### **5.2 Why Friend Balance Table?**

**Scenario**: "User1 paid ₹900 for lunch with User2 and User3 (equal split)"

**You**: "This is the CORE of Splitwise! Let me show you the balance update logic:

**Initial state**:
```
friend_balance table:
user_id  | friend_id | you_owe | owes_you
---------|-----------|---------|----------
user-1   | user-2    |    0    |    0
user-1   | user-3    |    0    |    0
user-2   | user-1    |    0    |    0
user-3   | user-1    |    0    |    0
```

**After expense (User1 paid ₹900, split equally)**:
```
Split calculation:
- User1 owes: ₹300 (their share)
- User2 owes: ₹300
- User3 owes: ₹300

User1 paid ₹900 but only owes ₹300:
→ User1 has credit of ₹600 (₹900 - ₹300)
→ User2 owes User1: ₹300
→ User3 owes User1: ₹300

Updated friend_balance:
user_id  | friend_id | you_owe | owes_you
---------|-----------|---------|----------
user-1   | user-2    |    0    |   300    ✓ User2 owes User1 ₹300
user-1   | user-3    |    0    |   300    ✓ User3 owes User1 ₹300
user-2   | user-1    |  300    |    0    ✓ User2 owes User1 ₹300
user-3   | user-1    |  300    |    0    ✓ User3 owes User1 ₹300
```

**Balance update code**:
```java
class BalanceSheetController {
    void updateBalances(Expense expense, List<ExpenseSplit> splits) {
        User payer = expense.getPaidBy();
        double totalAmount = expense.getAmount();
        
        for (ExpenseSplit split : splits) {
            User user = split.getUser();
            double owedAmount = split.getAmount();
            
            // Update user's total expense
            userBalanceRepo.incrementTotalExpense(user.getId(), owedAmount);
            
            if (user.equals(payer)) {
                // This user paid, so increase their total paid
                userBalanceRepo.incrementTotalPaid(user.getId(), totalAmount);
                
                // Calculate credit: paid - owed
                double credit = totalAmount - owedAmount;
                userBalanceRepo.incrementTotalReceivable(user.getId(), credit);
                
            } else {
                // This user didn't pay, so they owe the payer
                userBalanceRepo.incrementTotalOwed(user.getId(), owedAmount);
                
                // Update friend-wise balance
                updateFriendBalance(user, payer, owedAmount);
            }
        }
    }
    
    void updateFriendBalance(User debtor, User creditor, double amount) {
        // Update debtor's view: "I owe creditor X amount"
        friendBalanceRepo.incrementYouOwe(debtor.getId(), creditor.getId(), amount);
        
        // Update creditor's view: "Debtor owes me X amount"
        friendBalanceRepo.incrementOwesYou(creditor.getId(), debtor.getId(), amount);
    }
}
```

**Why this design**:
1. **Bidirectional consistency**: Both users see the same debt from their perspective
2. **Fast queries**: Get "User1's balance with all friends" in one query
3. **Simplification-ready**: Graph algorithms can easily consume this structure"

### **5.3 Why Debt Simplification Matters?**

**Scenario**: "4 friends go on trip. Multiple expenses. Now have complex web of debts."

**You**: "Real example:
```
Original debts (10 transactions):
1. Alice owes Bob: ₹100
2. Bob owes Charlie: ₹150
3. Charlie owes David: ₹200
4. David owes Alice: ₹50
5. Alice owes Charlie: ₹80
6. Bob owes David: ₹120
7. Charlie owes Alice: ₹30
8. David owes Bob: ₹90
9. Alice owes David: ₹110
10. Bob owes Alice: ₹70

Total: 10 transactions! Nightmare to settle!
```

**Simplification algorithm**:
```java
class DebtSimplifier {
    List<Transaction> simplify(List<User> users, List<Debt> debts) {
        // Step 1: Calculate net balance for each user
        Map<User, Double> netBalance = new HashMap<>();
        
        for (Debt debt : debts) {
            netBalance.merge(debt.getDebtor(), -debt.getAmount(), Double::sum);
            netBalance.merge(debt.getCreditor(), debt.getAmount(), Double::sum);
        }
        
        // Step 2: Separate into creditors (positive) and debtors (negative)
        PriorityQueue<Balance> creditors = new PriorityQueue<>((a, b) -> 
            Double.compare(b.getAmount(), a.getAmount()));  // Max-heap
        PriorityQueue<Balance> debtors = new PriorityQueue<>((a, b) ->
            Double.compare(a.getAmount(), b.getAmount()));  // Min-heap
        
        for (Map.Entry<User, Double> entry : netBalance.entrySet()) {
            if (entry.getValue() > 0) {
                creditors.offer(new Balance(entry.getKey(), entry.getValue()));
            } else if (entry.getValue() < 0) {
                debtors.offer(new Balance(entry.getKey(), entry.getValue()));
            }
        }
        
        // Step 3: Greedy matching - pair largest creditor with largest debtor
        List<Transaction> simplified = new ArrayList<>();
        
        while (!creditors.isEmpty() && !debtors.isEmpty()) {
            Balance maxCredit = creditors.poll();
            Balance maxDebt = debtors.poll();
            
            double settlementAmount = Math.min(maxCredit.getAmount(), 
                                               Math.abs(maxDebt.getAmount()));
            
            simplified.add(new Transaction(
                maxDebt.getUser(),    // From (debtor)
                maxCredit.getUser(),  // To (creditor)
                settlementAmount
            ));
            
            // Adjust balances
            double remainingCredit = maxCredit.getAmount() - settlementAmount;
            double remainingDebt = maxDebt.getAmount() + settlementAmount;
            
            if (remainingCredit > 0.01) {
                creditors.offer(new Balance(maxCredit.getUser(), remainingCredit));
            }
            if (remainingDebt < -0.01) {
                debtors.offer(new Balance(maxDebt.getUser(), remainingDebt));
            }
        }
        
        return simplified;
    }
}
```

**Result**:
```
Net balances:
- Alice: +₹100 (receives)
- Bob: -₹50 (owes)
- Charlie: +₹80 (receives)
- David: -₹130 (owes)

Simplified transactions (3 only!):
1. David pays Charlie: ₹80
2. David pays Alice: ₹50
3. Bob pays Alice: ₹50

From 10 → 3 transactions! 70% reduction!
```

**When to run**: User clicks "Simplify debts" button. Optional feature, doesn't auto-run (users like seeing individual expense trails).

**Real-world**: Splitwise CEO mentioned they use **graph algorithms** for this. Algorithm is **NP-complete** for optimal solution, but greedy gives 95% optimal results in O(n log n)."

---

## 6. Cross Questions

**Interviewer**: "What if user partially pays their debt?"

**You**: "Great question! Settlement tracking:

```java
class SettlementService {
    @Transactional
    void recordSettlement(String payerId, String receiverId, double amount) {
        // Step 1: Validate current debt
        FriendBalance balance = friendBalanceRepo.find(payerId, receiverId);
        
        if (balance.getYouOwe() < amount) {
            throw new InvalidSettlementException(
                "Cannot settle ₹" + amount + ". You only owe ₹" + balance.getYouOwe()
            );
        }
        
        // Step 2: Update friend balance (reduce debt)
        friendBalanceRepo.decrementYouOwe(payerId, receiverId, amount);
        friendBalanceRepo.decrementOwesYou(receiverId, payerId, amount);
        
        // Step 3: Update user balance aggregates
        userBalanceRepo.decrementTotalOwed(payerId, amount);
        userBalanceRepo.decrementTotalReceivable(receiverId, amount);
        
        // Step 4: Record settlement for audit
        Settlement settlement = new Settlement(
            payerId, receiverId, amount, LocalDateTime.now()
        );
        settlementRepo.save(settlement);
        
        // Step 5: Notify both users
        notificationService.sendSettlementNotification(payerId, receiverId, amount);
    }
}
```

**Example**:
```
Before settlement:
- User2 owes User1: ₹500

User2 pays ₹200 (partial):

After settlement:
- User2 owes User1: ₹300 (remaining)

Settlement log:
settlement_id | payer_id | receiver_id | amount | settled_at
--------------|----------|-------------|--------|------------
settle-1      | user-2   | user-1      | 200.00 | 2026-08-31...
```

**Edge case: Overpayment**:
```java
if (amount > balance.getYouOwe()) {
    // Option 1: Reject
    throw new InvalidSettlementException("Cannot overpay");
    
    // Option 2: Accept and reverse balance
    double overpayment = amount - balance.getYouOwe();
    
    // Clear existing debt
    friendBalanceRepo.setYouOwe(payerId, receiverId, 0);
    friendBalanceRepo.setOwesYou(receiverId, payerId, 0);
    
    // Create reverse balance
    friendBalanceRepo.setOwesYou(payerId, receiverId, overpayment);
    friendBalanceRepo.setYouOwe(receiverId, payerId, overpayment);
}
```

**Real Splitwise**: Allows partial settlements. Full settlement history visible in expense details."

---

**Interviewer**: "How do you handle currency conversion for international expenses?"

**You**: "Multi-currency support:

```java
class Expense {
    private String expenseId;
    private double amount;
    private Currency currency;  // ✓ Store original currency
    private String baseCurrency = "USD";  // User's preferred currency
    private double exchangeRate;  // At time of expense creation
}

class CurrencyConverter {
    private ExchangeRateAPI rateAPI;  // e.g., fixer.io, Open Exchange Rates
    
    double convert(double amount, Currency from, Currency to, LocalDate date) {
        if (from.equals(to)) return amount;
        
        // Fetch historical rate for that date
        double rate = rateAPI.getRate(from, to, date);
        
        return amount * rate;
    }
}

class ExpenseService {
    void createExpense(Expense expense) {
        // Store original currency
        expense.setCurrency(expense.getOriginalCurrency());
        
        // Fetch exchange rate at creation time
        double rate = currencyConverter.getRate(
            expense.getCurrency(),
            expense.getBaseCurrency(),
            LocalDate.now()
        );
        expense.setExchangeRate(rate);
        
        // Calculate splits in user's base currency
        List<ExpenseSplit> splits = splitStrategy.calculate(expense);
        
        // Convert each split to user's preferred currency
        for (ExpenseSplit split : splits) {
            double convertedAmount = currencyConverter.convert(
                split.getAmount(),
                expense.getCurrency(),
                split.getUser().getPreferredCurrency(),
                LocalDate.now()
            );
            split.setConvertedAmount(convertedAmount);
        }
        
        saveSplits(splits);
    }
}
```

**Schema addition**:
```sql
ALTER TABLE expenses
ADD COLUMN currency VARCHAR(3) NOT NULL DEFAULT 'USD',
ADD COLUMN base_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
ADD COLUMN exchange_rate DECIMAL(10,6);

ALTER TABLE expense_splits
ADD COLUMN original_amount DECIMAL(15,2),
ADD COLUMN converted_amount DECIMAL(15,2),
ADD COLUMN user_currency VARCHAR(3);
```

**Example**:
```
Expense created in EUR:
- Amount: €100
- User1 (prefers USD): $110 (at rate 1.10)
- User2 (prefers INR): ₹9,100 (at rate 91.00)
- User3 (prefers EUR): €100 (no conversion)

All calculations done in user's preferred currency!
```

**Real-world**: Splitwise uses **daily exchange rates**. Stores both original and converted amounts for transparency."

---

## 7. Trade-offs

### **7.1 Per-User Balance vs Centralized Ledger**

| Aspect | Per-User Balance (Splitwise) | Centralized Ledger |
|--------|------------------------------|---------------------|
| **Query Performance** | Fast (user's view pre-computed) | Slow (aggregate on each query) |
| **Data Redundancy** | High (same debt stored twice) | Low (single source of truth) |
| **Consistency** | Complex (must update both users) | Simple (single update) |
| **User Experience** | Excellent ("My view" instant) | Poor (slow loading) |

**You**: "Splitwise chooses **per-user balance** because:
- User dashboard query is MOST FREQUENT operation (10x more reads than writes)
- Users expect instant load (<100ms)
- Redundancy is acceptable (only 2x storage, negligible for debt data)

**Alternative** (centralized ledger):
```sql
-- Single debt table
CREATE TABLE debts (
    debtor_id VARCHAR(50),
    creditor_id VARCHAR(50),
    amount DECIMAL(15,2),
    PRIMARY KEY (debtor_id, creditor_id)
);

-- User's balance requires aggregation:
SELECT 
    SUM(CASE WHEN debtor_id = ? THEN amount ELSE 0 END) AS total_owed,
    SUM(CASE WHEN creditor_id = ? THEN amount ELSE 0 END) AS total_receivable
FROM debts
WHERE debtor_id = ? OR creditor_id = ?;

-- ❌ Slower! No index can optimize both conditions
```

**My choice**: Per-user balance for consumer apps (read-heavy). Centralized ledger for accounting systems (write-heavy, audit-critical)."

### **7.2 Real-Time Debt Simplification vs On-Demand**

| Aspect | Real-Time (Auto) | On-Demand (User-Triggered) |
|--------|------------------|----------------------------|
| **Transparency** | Low (user can't see original expenses) | High (user sees all details) |
| **Transaction Count** | Minimal (always optimal) | Higher (until simplified) |
| **Complexity** | High (must maintain mapping) | Low (one-time computation) |

**You**: "Splitwise uses **on-demand** because:
- Users want to see WHO paid for WHAT (transparency)
- Simplification loses this history
- Only needed when settling up (rare event)

**If building for businesses** (not friends):
- Use **real-time simplification** (businesses care about efficiency, not friendship)
- Maintain audit trail separately"

---

## 8. Senior Trap Questions

### **Trap #1: "Just use double for money!"**

**Interviewer**: "For balance amounts, use double or BigDecimal?"

**❌ Junior Answer**: "Double is fine, it's just money."

**✅ Senior Answer**: "NEVER use double for money! Here's why:

**Problem with double**:
```java
double price = 0.1;
double quantity = 3;
double total = price * quantity;

System.out.println(total);  // Output: 0.30000000000000004  ❌ WTF!

// Comparison fails:
if (total == 0.3) {  // FALSE!
    System.out.println("Equal");
}
```

**Correct: Use BigDecimal**:
```java
BigDecimal price = new BigDecimal("0.10");
BigDecimal quantity = new BigDecimal("3");
BigDecimal total = price.multiply(quantity);

System.out.println(total);  // Output: 0.30  ✓ Exact!

// Comparison works:
if (total.compareTo(new BigDecimal("0.30")) == 0) {  // TRUE!
    System.out.println("Equal");
}
```

**Real-world horror story**:
```
User splits ₹100 among 3 people:
- With double: 33.333333... + 33.333333... + 33.333333... = 100.000000001
- With BigDecimal: 33.33 + 33.33 + 33.34 = 100.00 (adjust last split)
```

**Splitwise production code**:
```java
class SplitCalculator {
    List<BigDecimal> splitEqual(BigDecimal amount, int count) {
        BigDecimal perPerson = amount.divide(
            new BigDecimal(count),
            2,  // Scale: 2 decimal places
            RoundingMode.HALF_UP
        );
        
        List<BigDecimal> splits = new ArrayList<>();
        BigDecimal totalSplit = BigDecimal.ZERO;
        
        for (int i = 0; i < count - 1; i++) {
            splits.add(perPerson);
            totalSplit = totalSplit.add(perPerson);
        }
        
        // Last person gets remainder to ensure exact total
        BigDecimal lastSplit = amount.subtract(totalSplit);
        splits.add(lastSplit);
        
        return splits;
    }
}
```

**Database**:
```sql
-- ❌ WRONG
amount DOUBLE

-- ✅ CORRECT
amount DECIMAL(15,2)  -- 15 digits total, 2 after decimal
```

**Senior insight**: Financial applications should use **fixed-point** arithmetic (BigDecimal, DECIMAL), NEVER floating-point (double, FLOAT)."

---

### **Trap #2: "Store balances in cache!"**

**Interviewer**: "Why not store user balances in Redis for faster reads?"

**❌ Junior Answer**: "Yes, cache balances for performance."

**✅ Senior Answer**: "Caching balances is DANGEROUS for financial data:

**Problem**:
```java
// ❌ WRONG: Cache balance
class BalanceService {
    BigDecimal getBalance(String userId) {
        String cacheKey = "balance:" + userId;
        BigDecimal cached = redis.get(cacheKey);
        
        if (cached != null) {
            return cached;  // ❌ What if cache is stale?
        }
        
        BigDecimal balance = db.getBalance(userId);
        redis.setex(cacheKey, 3600, balance);  // 1 hour TTL
        return balance;
    }
    
    void updateBalance(String userId, BigDecimal change) {
        db.updateBalance(userId, change);
        redis.del("balance:" + userId);  // ❌ What if this fails?
    }
}

// Race condition:
Thread 1: Read balance from DB (₹1000)
Thread 2: Update balance (+₹500) → DB shows ₹1500
Thread 1: Cache old value (₹1000) → Cache is wrong!
User sees ₹1000 for next hour! ❌
```

**Correct approach**:
```java
// ✅ OPTION 1: No cache for critical data
class BalanceService {
    BigDecimal getBalance(String userId) {
        // Always read from DB (with proper indexing, <10ms)
        return balanceRepo.findById(userId).getBalance();
    }
}

// ✅ OPTION 2: Cache with Write-Through + Short TTL
class BalanceService {
    BigDecimal getBalance(String userId) {
        String cacheKey = "balance:" + userId;
        BigDecimal cached = redis.get(cacheKey);
        
        if (cached != null) {
            return cached;
        }
        
        BigDecimal balance = db.getBalance(userId);
        redis.setex(cacheKey, 30, balance);  // 30 sec TTL (very short!)
        return balance;
    }
    
    @Transactional
    void updateBalance(String userId, BigDecimal change) {
        db.updateBalance(userId, change);
        
        // Write-through: Update cache immediately
        BigDecimal newBalance = db.getBalance(userId);
        redis.setex("balance:" + userId, 30, newBalance);
    }
}

// ✅ OPTION 3: Cache invalidation via events
class BalanceService {
    @Transactional
    void updateBalance(String userId, BigDecimal change) {
        db.updateBalance(userId, change);
        
        // Publish event
        eventBus.publish(new BalanceUpdatedEvent(userId));
    }
}

@EventListener
class CacheInvalidator {
    void onBalanceUpdated(BalanceUpdatedEvent event) {
        redis.del("balance:" + event.getUserId());
    }
}
```

**Why no cache**:
1. **Consistency risk**: Money must ALWAYS be correct
2. **Performance acceptable**: Indexed DB query is <10ms
3. **Trust issue**: Users lose trust if balance is wrong

**What to cache instead**:
- Expense history (immutable, safe to cache)
- Friend list (changes rarely)
- Group details (changes rarely)

**Real Splitwise**: Doesn't cache balances. Caches only **immutable data** (past expenses, user profiles).

**Senior insight**: For financial data, **correctness > performance**. Cache only if you can guarantee consistency OR if staleness is acceptable (NOT for money!)."

---

## 9. Technology Choices

### **9.1 Database: PostgreSQL vs MongoDB**

| Aspect | PostgreSQL | MongoDB |
|--------|-----------|---------|
| **ACID Transactions** | Full support | Limited (single document) |
| **Joins** | Efficient | Requires $lookup (slow) |
| **Schema Flexibility** | Rigid | Flexible |
| **Balance Consistency** | Guaranteed | Manual handling |

**When PostgreSQL**:
```sql
-- Complex join for user dashboard
SELECT 
    u.user_id,
    u.name,
    ub.total_owed,
    ub.total_receivable,
    f.friend_name,
    fb.you_owe,
    fb.owes_you
FROM users u
JOIN user_balance ub ON u.user_id = ub.user_id
LEFT JOIN friend_balance fb ON u.user_id = fb.user_id
LEFT JOIN users f ON fb.friend_id = f.user_id
WHERE u.user_id = ?;

-- ✅ Single query, consistent view, ACID guaranteed
```

**When MongoDB**:
```javascript
// Embedded document model
{
  "_id": "user-1234",
  "name": "Shreyans",
  "balance": {
    "totalOwed": 2000.00,
    "totalReceivable": 1000.00
  },
  "friendBalances": [
    {
      "friendId": "user-5678",
      "friendName": "Rahul",
      "youOwe": 500.00,
      "owesYou": 0.00
    }
  ],
  "expenses": [...]  // Recent expenses embedded
}

// ✅ Single document read, no joins
// ❌ But updating balances requires complex logic
```

**My Choice: PostgreSQL**
- Splitwise is **RELATIONAL** (users ↔ friends ↔ expenses)
- Need **ACID** for balance updates (atomic changes across multiple rows)
- Joins are frequent (user + friends + balances)

**MongoDB only if**: Document-per-user model works AND you don't need multi-document ACID (Splitwise needs it!).

---

### **9.2 Real-Time Updates: WebSocket vs Polling vs SSE**

| Aspect | WebSocket | Server-Sent Events (SSE) | Polling |
|--------|-----------|--------------------------|---------|
| **Bidirectional** | Yes | No (server→client only) | No |
| **Overhead** | Low (persistent connection) | Low | High (repeated requests) |
| **Browser Support** | Excellent | Good (no IE) | Universal |
| **Use Case** | Chat, collaborative | Notifications, live feeds | Simple updates |

**When WebSocket**:
```java
@ServerEndpoint("/ws/balances/{userId}")
public class BalanceWebSocket {
    private static Map<String, Session> sessions = new ConcurrentHashMap<>();
    
    @OnOpen
    public void onConnect(Session session, @PathParam("userId") String userId) {
        sessions.put(userId, session);
    }
    
    public static void notifyBalanceUpdate(String userId, BigDecimal newBalance) {
        Session session = sessions.get(userId);
        if (session != null && session.isOpen()) {
            session.getAsyncRemote().sendText(
                "{\"balance\": " + newBalance + "}"
            );
        }
    }
}

// Client-side:
const ws = new WebSocket('wss://api.splitwise.com/ws/balances/user-1234');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    updateBalanceUI(data.balance);
};
```

**When SSE**:
```java
@GetMapping("/sse/balances/{userId}")
public SseEmitter streamBalances(@PathVariable String userId) {
    SseEmitter emitter = new SseEmitter(Long.MAX_VALUE);
    
    balanceService.subscribe(userId, (balance) -> {
        try {
            emitter.send(SseEmitter.event()
                .name("balance-update")
                .data(balance));
        } catch (IOException e) {
            emitter.completeWithError(e);
        }
    });
    
    return emitter;
}

// Client-side (simpler than WebSocket!):
const eventSource = new EventSource('/sse/balances/user-1234');
eventSource.addEventListener('balance-update', (event) => {
    updateBalanceUI(JSON.parse(event.data));
});
```

**My Choice: SSE for Splitwise**
- **Unidirectional** (server→client) is sufficient (balances pushed to user)
- **Simpler** than WebSocket (no need for bidirectional)
- **Auto-reconnect** built-in

**WebSocket if**: Building chat feature or collaborative expense editing.

---

## 🎓 **Final Tips for 15 YOE Splitwise Interview**

1. **Strategy Pattern is Key**: Show you understand multiple split strategies
2. **Balance Management**: Explain friend-wise balance table design
3. **BigDecimal for Money**: NEVER double!
4. **Graph Algorithms**: Debt simplification shows algorithmic thinking
5. **ACID Transactions**: Critical for financial consistency

**Senior insights**:
- Mention **idempotency** for expense creation (prevent duplicate expenses)
- Discuss **currency rounding** strategies (last person absorbs rounding error)
- Talk about **settlement optimization** (minimize transaction fees)
- Consider **recurring expenses** (monthly rent, subscriptions)

**Good luck!** Splitwise tests your understanding of **financial systems**, **design patterns**, and **graph algorithms**. Show you can build production-grade expense tracking! 🚀
