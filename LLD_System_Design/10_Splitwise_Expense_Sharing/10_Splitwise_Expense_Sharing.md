# Splitwise / Expense Sharing — Complete LLD Interview Guide

**Interview Duration: 45 min | Difficulty: Hard | Must-Know: ⭐⭐⭐⭐ | 15-YOE Focus: Debt Simplification Algorithm + Split Types**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │               EXPENSE SHARING SYSTEM                            │
 │                                                                  │
 │  GROUPS               EXPENSES              BALANCES            │
 │  ┌──────────┐        ┌──────────────┐      ┌──────────────────┐ │
 │  │ Group    │        │ Expense      │      │ UserBalance      │ │
 │  │ members[]│◄──────►│ paidBy       │◄────►│ owes: +/-        │ │
 │  │ expenses │        │ amount       │      │ net per user     │ │
 │  │ balances │        │ splitType    │      │ simplified debts │ │
 │  └──────────┘        │ participants │      └──────────────────┘ │
 │                      └──────────────┘                           │
 │  SPLIT TYPES                        DEBT SIMPLIFICATION         │
 │  ┌────────────────────┐             ┌────────────────────────┐  │
 │  │ EQUAL    → ÷N      │             │ A owes B: ₹300         │  │
 │  │ EXACT    → custom  │             │ B owes C: ₹200         │  │
 │  │ PERCENT  → %       │             │ C owes A: ₹100         │  │
 │  │ SHARES   → ratio   │             │ After simplification:  │  │
 │  └────────────────────┘             │ A→C: ₹200, B→C: ₹100  │  │
 │                                     │ (3 txns → 2 txns)      │  │
 │                                     └────────────────────────┘  │
 └──────────────────────────────────────────────────────────────────┘

 DEBT SIMPLIFICATION — THE CORE ALGORITHM:
 ┌──────────────────────────────────────────────────────────────────┐
 │  STEP 1: Compute net balance per user                           │
 │  User A: paid ₹600, owes ₹400 → net = +₹200 (is owed)         │
 │  User B: paid ₹0,   owes ₹300 → net = -₹300 (owes)            │
 │  User C: paid ₹0,   owes ₹100 → net = -₹100 (owes)            │
 │  User D: paid ₹200, owes ₹0   → net = +₹200 (is owed)         │  
 │                                                                  │
 │  STEP 2: Separate into creditors (+) and debtors (-)           │
 │  Creditors: A(+200), D(+200)                                    │
 │  Debtors:   B(-300), C(-100)                                    │
 │                                                                  │
 │  STEP 3: Greedy matching (largest first)                        │
 │  B(-300) → A(+200): B pays A ₹200. B becomes -₹100. A settled.│
 │  B(-100) → D(+200): B pays D ₹100. B settled. D becomes +₹100.│
 │  C(-100) → D(+100): C pays D ₹100. Both settled.               │
 │                                                                  │
 │  Result: 3 transactions instead of N*(N-1)/2 raw transactions  │
 └──────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Let me gather requirements.

Functional:
- Create groups — e.g., 'Goa Trip', 'Flat 3B Roommates'
- Add expense: who paid, how much, split among whom, split type
- Split types: Equal (÷N), Exact (specify each), Percentage, Shares (ratio like 2:1:1)
- View balances: who owes whom how much
- Settle up: record a payment between two people
- Simplify debts: reduce N*(N-1) transactions to minimum number

Non-functional:
- Correctness: all expenses must balance to zero (sum of what everyone owes = sum of what was paid)
- Rounding: if ₹100 split 3 ways = ₹33.33... → assign ₹34 to one person, ₹33 to others
- Thread safety: concurrent expense additions in same group

The key insight is: the balances form a directed graph. Debt simplification is a graph problem — minimize the number of edges (transactions) while keeping the total amount owed by each person the same."

---

### Phase 2 — Core Entities

```
User     → userId, name, email
Group    → groupId, name, List<User> members, List<Expense> expenses
Expense  → expenseId, description, amount, paidBy(userId), SplitType,
           List<UserShare>, createdAt
UserShare→ userId, amountOwed  (computed from split strategy)
Balance  → Map<userId, Map<userId, Double>>  (A→B: ₹200 means A owes B ₹200)
SplitStrategy → interface: computeShares(amount, List<User>, params)
```

---

### Phase 3 — Implementation

```java
// ─── Split Types ────────────────────────────────────────────────
public enum SplitType { EQUAL, EXACT, PERCENTAGE, SHARES }

// ─── UserShare ──────────────────────────────────────────────────
public class UserShare {
    private final String userId;
    private final double amount;

    public UserShare(String userId, double amount) {
        this.userId = userId;
        this.amount = amount;
    }

    public String getUserId() { return userId; }
    public double getAmount() { return amount; }
}

// ─── Split Strategy ─────────────────────────────────────────────
public interface SplitStrategy {
    List<UserShare> split(double totalAmount, List<String> userIds, List<Double> params);
}

public class EqualSplit implements SplitStrategy {
    @Override
    public List<UserShare> split(double totalAmount, List<String> userIds, List<Double> params) {
        int n = userIds.size();
        double base   = Math.floor(totalAmount * 100 / n) / 100;  // floor to 2 decimal
        double extra  = totalAmount - base * n;                    // leftover from rounding
        int extraCents = (int) Math.round(extra * 100);

        List<UserShare> shares = new ArrayList<>();
        for (int i = 0; i < userIds.size(); i++) {
            double share = base + (i < extraCents ? 0.01 : 0.0); // distribute extra cents
            shares.add(new UserShare(userIds.get(i), share));
        }
        return shares;
    }
}

public class ExactSplit implements SplitStrategy {
    @Override
    public List<UserShare> split(double totalAmount, List<String> userIds, List<Double> params) {
        if (params == null || params.size() != userIds.size())
            throw new IllegalArgumentException("Exact amounts must match user count");
        double sum = params.stream().mapToDouble(Double::doubleValue).sum();
        if (Math.abs(sum - totalAmount) > 0.01)
            throw new IllegalArgumentException("Exact amounts must sum to total: " + sum + " ≠ " + totalAmount);

        List<UserShare> shares = new ArrayList<>();
        for (int i = 0; i < userIds.size(); i++)
            shares.add(new UserShare(userIds.get(i), params.get(i)));
        return shares;
    }
}

public class PercentageSplit implements SplitStrategy {
    @Override
    public List<UserShare> split(double totalAmount, List<String> userIds, List<Double> params) {
        double totalPercent = params.stream().mapToDouble(Double::doubleValue).sum();
        if (Math.abs(totalPercent - 100.0) > 0.001)
            throw new IllegalArgumentException("Percentages must sum to 100");

        List<UserShare> shares = new ArrayList<>();
        for (int i = 0; i < userIds.size(); i++) {
            double amount = Math.round(totalAmount * params.get(i) / 100.0 * 100) / 100.0;
            shares.add(new UserShare(userIds.get(i), amount));
        }
        return shares;
    }
}

// ─── Expense ─────────────────────────────────────────────────────
public class Expense {
    private final String       expenseId;
    private final String       description;
    private final double       totalAmount;
    private final String       paidByUserId;
    private final List<UserShare> shares;
    private final LocalDateTime   createdAt;

    public Expense(String expenseId, String description, double totalAmount,
                   String paidByUserId, List<UserShare> shares) {
        this.expenseId    = expenseId;
        this.description  = description;
        this.totalAmount  = totalAmount;
        this.paidByUserId = paidByUserId;
        this.shares       = Collections.unmodifiableList(shares);
        this.createdAt    = LocalDateTime.now();
    }

    public String getPaidByUserId() { return paidByUserId; }
    public List<UserShare> getShares() { return shares; }
    public double getTotalAmount() { return totalAmount; }
    public String getExpenseId()   { return expenseId; }
    public String getDescription() { return description; }
}

// ─── Group ───────────────────────────────────────────────────────
public class Group {
    private final String          groupId;
    private final String          name;
    private final List<String>    memberIds;
    private final List<Expense>   expenses = new ArrayList<>();
    private final ReadWriteLock   rwLock   = new ReentrantReadWriteLock();

    public Group(String groupId, String name, List<String> memberIds) {
        this.groupId   = groupId;
        this.name      = name;
        this.memberIds = new ArrayList<>(memberIds);
    }

    public void addExpense(Expense expense) {
        rwLock.writeLock().lock();
        try { expenses.add(expense); }
        finally { rwLock.writeLock().unlock(); }
    }

    public List<Expense> getExpenses() {
        rwLock.readLock().lock();
        try { return Collections.unmodifiableList(new ArrayList<>(expenses)); }
        finally { rwLock.readLock().unlock(); }
    }

    public String getGroupId() { return groupId; }
    public String getName()    { return name; }
    public List<String> getMemberIds() { return memberIds; }
}

// ─── Balance Calculator ──────────────────────────────────────────
public class BalanceCalculator {

    // Returns: Map<userId, netBalance>
    // Positive = this user is OWED money; Negative = this user OWES money
    public Map<String, Double> computeNetBalances(Group group) {
        Map<String, Double> netBalance = new HashMap<>();
        group.getMemberIds().forEach(id -> netBalance.put(id, 0.0));

        for (Expense expense : group.getExpenses()) {
            String payer = expense.getPaidByUserId();
            netBalance.merge(payer, expense.getTotalAmount(), Double::sum); // payer gets credit

            for (UserShare share : expense.getShares()) {
                netBalance.merge(share.getUserId(), -share.getAmount(), Double::sum); // debtor gets debit
            }
        }
        return netBalance;
    }

    // Debt simplification: minimize number of transactions
    public List<Transaction> simplifyDebts(Group group) {
        Map<String, Double> netBalance = computeNetBalances(group);

        // Separate into creditors (positive) and debtors (negative)
        // Use priority queues for greedy matching (largest first)
        PriorityQueue<double[]> creditors = new PriorityQueue<>((a, b) -> Double.compare(b[1], a[1]));
        PriorityQueue<double[]> debtors   = new PriorityQueue<>((a, b) -> Double.compare(a[1], b[1]));

        // We track userId as index into members array
        List<String> memberIds = group.getMemberIds();
        for (int i = 0; i < memberIds.size(); i++) {
            double bal = netBalance.getOrDefault(memberIds.get(i), 0.0);
            if (bal > 0.001)       creditors.offer(new double[]{i, bal});
            else if (bal < -0.001) debtors.offer(new double[]{i, bal});
        }

        List<Transaction> transactions = new ArrayList<>();

        while (!debtors.isEmpty() && !creditors.isEmpty()) {
            double[] debtor   = debtors.poll();
            double[] creditor = creditors.poll();

            double amount = Math.min(-debtor[1], creditor[1]);
            amount = Math.round(amount * 100.0) / 100.0; // round to ₹0.01

            transactions.add(new Transaction(
                memberIds.get((int) debtor[0]),    // from (debtor)
                memberIds.get((int) creditor[0]),  // to (creditor)
                amount
            ));

            debtor[1]   += amount;   // debtor owes less
            creditor[1] -= amount;   // creditor is owed less

            if (debtor[1] < -0.001)   debtors.offer(debtor);
            if (creditor[1] > 0.001)  creditors.offer(creditor);
        }

        return transactions;
    }
}

// ─── Transaction (simplified debt) ─────────────────────────────
public record Transaction(String fromUserId, String toUserId, double amount) {}

// ─── ExpenseService ──────────────────────────────────────────────
public class ExpenseService {
    private final Map<String, Group>        groups     = new ConcurrentHashMap<>();
    private final Map<SplitType, SplitStrategy> strategies = new HashMap<>();
    private final BalanceCalculator         calculator = new BalanceCalculator();

    public ExpenseService() {
        strategies.put(SplitType.EQUAL,      new EqualSplit());
        strategies.put(SplitType.EXACT,      new ExactSplit());
        strategies.put(SplitType.PERCENTAGE, new PercentageSplit());
    }

    public Expense addExpense(String groupId, String description, double amount,
                               String paidByUserId, SplitType splitType,
                               List<String> participantIds, List<Double> params) {
        Group group = getGroup(groupId);
        SplitStrategy strategy = strategies.get(splitType);
        List<UserShare> shares = strategy.split(amount, participantIds, params);

        // Validate: sum of shares ≈ total amount
        double sharesSum = shares.stream().mapToDouble(UserShare::getAmount).sum();
        if (Math.abs(sharesSum - amount) > 0.01)
            throw new IllegalStateException("Shares don't sum to total: " + sharesSum + " ≠ " + amount);

        Expense expense = new Expense(UUID.randomUUID().toString(),
            description, amount, paidByUserId, shares);
        group.addExpense(expense);
        return expense;
    }

    public Map<String, Double> getBalances(String groupId) {
        return calculator.computeNetBalances(getGroup(groupId));
    }

    public List<Transaction> getSimplifiedDebts(String groupId) {
        return calculator.simplifyDebts(getGroup(groupId));
    }

    private Group getGroup(String id) {
        Group g = groups.get(id);
        if (g == null) throw new IllegalArgumentException("Group not found: " + id);
        return g;
    }

    public void createGroup(Group group) { groups.put(group.getGroupId(), group); }
}
```

---

## Component Choices

```
COMPONENT             CHOICE                   WHY
──────────────────────────────────────────────────────────────────────
Split calculation     Strategy Pattern         Four split types behave
                                               differently. New split type
                                               (e.g., SHARES) = new class.
                                               No change to ExpenseService.

Debt simplification   Greedy + PriorityQueue  Always produces ≤ N-1
                                               transactions for N users.
                                               Optimal in most cases.
                                               PQ for O(N log N) vs O(N²).

Concurrency on Group  ReadWriteLock            Multiple readers: view balances.
                                               Single writer: add expense.
                                               RW lock allows concurrent reads
                                               = better throughput than mutex.

Rounding              Distribute extra cents   ₹100 ÷ 3 = ₹33.33...
                      to first N users         Solution: ₹34, ₹33, ₹33.
                                               Sum always = ₹100 exactly.
                                               Without: systematic rounding
                                               errors accumulate.

Net balance model     Single map per group     O(1) lookup per user.
                                               Recompute on demand from
                                               expenses (source of truth).
                                               Don't store derived balance —
                                               recompute to avoid staleness.
```

---

## Senior Trap Questions

**Q1: "Three people split ₹100 equally. How do you handle the ₹0.01 rounding difference?"**
```
₹100 ÷ 3 = ₹33.333...

Naive: round each to ₹33.33 → sum = ₹99.99 → missing ₹0.01

Correct approach:
  base = floor(10000/3) / 100 = ₹33.33
  extra = ₹100 - ₹33.33 × 3 = ₹0.01 → 1 extra cent
  Person 1: ₹33.34  (gets the extra cent)
  Person 2: ₹33.33
  Person 3: ₹33.33
  Sum: ₹100.00 ✅

EqualSplit.split() does this:
  extraCents = round((total - base*N) * 100)
  First extraCents people get base + ₹0.01, rest get base.
```

**Q2: "Prove that simplification produces at most N-1 transactions."**
```
The greedy algorithm on net balances produces at most N-1 transactions.

Proof sketch:
  N users → N net balances that sum to 0.
  In each iteration of the greedy loop:
    - At least one user becomes fully settled (balance hits 0)
    - One transaction is created
  After N-1 iterations: at most one user remains with a non-zero balance.
  But all balances sum to 0, so if N-1 are settled, the last must be too.
  → At most N-1 transactions total.

Naive (all direct debts): up to N*(N-1)/2 transactions.
For 10 users: naive=45, simplified=9. 80% reduction.
```

**Q3: "Multi-currency support — group in India, one member pays in USD, another in EUR."**
```
Add currency field to Expense.
Store all amounts in a single "base currency" (group's currency, e.g., INR).
At expense creation: convert foreign amounts using exchange rate at time of expense.
Store original amount AND converted amount + exchange rate used.

ExchangeRateService: fetches rate at expense creation time.
  expense: { amount: 50.00, currency: USD, convertedAmount: 4150.00, rateINR: 83.0 }

WHY snapshot the rate at creation time?
  Exchange rates change daily.
  If A paid $50 in January (rate 83) and you recompute in March (rate 86):
  A would be "owed" more money retroactively — unfair!
  Always lock the rate at the moment of the transaction.
```

**Q4: "Expense added then deleted. How does balance history work?"**
```
Option 1: Soft delete with reverse transaction
  expense.setDeleted(true)
  Calculate balances by ignoring deleted expenses.
  Simple but query iterates all expenses each time.

Option 2: Audit log + CQRS
  Never delete — instead mark deleted + record who deleted + when.
  Balance = sum of all non-deleted expense shares.
  Audit trail: user can see who deleted what.
  In production: this is what Splitwise actually does.

Option 3: Snapshot + delta
  Keep a periodic snapshot of balances.
  Balance = snapshot + sum of subsequent expenses.
  Efficient for groups with many historical expenses.
```

---

## Failure Modes

```
SCENARIO              WHAT HAPPENS             FIX
────────────────────────────────────────────────────────────────────
Two users add         Concurrent writes to     ReadWriteLock write lock
expense simultaneously group expenses list     serializes additions.
                                               Or: use CopyOnWriteArrayList.

User removes self     Balances become          Check: user has zero balance
from group            inconsistent             before removal.
                                               If owed: must settle first.

Circular debts        A→B→C→A each ₹100       Simplification handles this:
(all owe each other)  messy to display        net balances are all ₹0.
                                               Simplification: zero transactions
                                               (all cancel out). ✅

Group archived        Old expenses still       Keep expenses immutable.
                      needed for tax/audit     Archive flag on group.
                                               Expenses retained forever,
                                               just no new ones added.
```

---

## Interview Cheat Sheet

> "Splitwise has three layers of complexity: split strategy (equal, exact, percent, shares — use Strategy pattern), correct rounding (floor the base, distribute extra cents to the first N users so the sum is always exact), and debt simplification (the graph problem). For simplification: compute net balance per user, separate into creditors and debtors, greedily match the largest debtor with largest creditor until everyone is settled — this produces at most N-1 transactions versus the naive N*(N-1)/2. Thread safety on expense addition uses ReadWriteLock — multiple readers can view balances simultaneously, only writes need exclusive access. The rounding trap is the classic gotcha: ₹100 ÷ 3 = ₹33.33... naive rounding loses ₹0.01. Correct approach: compute the floor-rounded base, count the extra cents, assign them to the first K users."
