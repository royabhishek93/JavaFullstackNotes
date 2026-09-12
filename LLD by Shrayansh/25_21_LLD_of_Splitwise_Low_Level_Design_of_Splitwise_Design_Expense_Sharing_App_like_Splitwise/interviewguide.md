# Interview Guide: Splitwise (Expense Sharing App) LLD

## 🗣️ The Interview Scenario

> "Design a low-level system for an expense-sharing application like Splitwise. Users should be able to add friends, create groups, add expenses inside a group (or directly one-on-one), split those expenses equally or by percentage, and always be able to view a running balance sheet — who owes them money, and who they owe. Walk me through your class design, and specifically explain how you'd keep every user's balance sheet accurate as new expenses get added."

This question is asked at nearly every product-based company's LLD round because it tests requirement-gathering discipline, object modeling for a real transactional domain, and — most importantly — whether you can correctly reason about **how state (the balance sheet) gets updated as a side effect of a business action (creating an expense)**.

## 🏗️ Architect's Explanation (For a New Developer)

Imagine you go on a trip with three friends. You paid for the hotel (₹400 total, split equally 4 ways). Mentally, everyone now "owes" you ₹100... except you, since you already paid your own share. Two things need to happen for that mental math to become software:

1. **Someone needs to compute the split** — the ₹400 needs to be broken into per-person amounts (₹100 each) or percentages, depending on how the expense was created.
2. **Everyone's personal ledger needs to be updated** — you need +₹300 credited to your "money owed to me" bucket (the three friends' shares), and each friend needs -₹100 recorded as "money I owe this person."

Splitwise's LLD is really the story of designing clean objects for exactly these two responsibilities, and — critically — **keeping the object that just holds data (`Expense`) separate from the object that has the responsibility of orchestrating what happens when an expense is created (`ExpenseController`)**. This separation is the single most important design decision in this problem: it's the classic "dumb data objects + smart controllers" style, which keeps your domain model easy to test and easy to extend (e.g., adding a new split type later doesn't touch your `Expense` class at all).

## 📊 Visualize It

**Class structure:**
```
UserController ──has──► List<User>
GroupController ──has──► List<Group>

Group
 ├─ groupId, groupName
 ├─ List<User> members
 ├─ List<Expense> expenseList
 └─ has ExpenseController  (creates expenses inside the group)

User
 ├─ userId, userName
 └─ UserExpenseBalanceSheet
        └─ Map<User, Balance>       // per-friend ledger
                Balance { amountGetBack, amountOwe }
        └─ totalYourExpense, totalPayment, totalGetBack, totalYouOwe (rollups)

Expense (plain data object)
 ├─ expenseId, description, amount
 ├─ paidByUser
 ├─ splitType (EQUAL | PERCENTAGE)
 └─ List<Split>                    // Split { user, amount/percentage }

ExpenseController
 ├─ has SplitFactory (validates + builds Split objects per splitType)
 ├─ creates the Expense
 └─ calls ► BalanceSheetController.updateBalanceSheet(expense)

BalanceSheetController
 └─ updates User.balanceSheet for every user involved in the expense
```

**Runtime flow when an expense is created:**
```
Client / UI
   │  createExpense(desc, amount, paidBy, splitType, splits[])
   ▼
ExpenseController
   │  1. SplitFactory.validate(splits, totalAmount)  ── e.g. sum(splits) == amount?
   │  2. new Expense(...)
   ▼
BalanceSheetController.updateBalanceSheet(expense)
   │  for each split in expense.splits:
   │     - increase paidByUser's totalPayment & totalGetBack
   │     - increase splitUser's totalYouOwe / totalExpense
   │     - update the per-friend Balance map on BOTH users
   ▼
Updated User.balanceSheet (queryable any time by the UI)
```

## 🔧 Deep Dive: How It Actually Works

### Step 1 — Requirement gathering (define the "happy path" first)

The transcript is explicit that you should never jump straight to a UML diagram. First narrate the app's happy path like a product walkthrough:
- Add friends (Friend1, Friend2, Friend3...).
- Create a Group (e.g., "College Group", "Outing Group") and add specific friends to that group only.
- Create an Expense either **inside a group** (shared among that group's members) or **directly from the app** (not attached to any group — a plain one-on-one or ad-hoc split).
- Every expense must support a **split** between friends.
- The app must always show a **balance sheet** — how much a user has to give back, and how much they'll get back, from/to each friend.

From this, extract concrete functional requirements:
- Ability to add Friends.
- Ability to add/manage a Group.
- Inside a Group, ability to create Expenses with a chosen split capability: **Equal** split (e.g., ₹200 total → ₹50 each for 4 friends) or **Percentage** split (e.g., 10%, 20%, 5%, 5%...).
- Maintain a **Balance Sheet** per user.

### Step 2 — Object identification

From the flow, the high-level objects fall out naturally: `User` (a.k.a. Friend/Member), `Group`, `Expense`, `Split`, and `BalanceSheet`.

### Step 3 — Understand exactly what data an Expense carries, before designing classes

Walking through a concrete example (Lunch, ₹400, split equally among 3 friends) reveals that for **each split type**, the client sends different shapes of data:
- **Equal split**: for each user, an `amount` is computed and sent (e.g., User owes ₹133.33).
- **Percentage split**: for each user, a `percentage` is assigned (e.g., 5%, 5%...) — and either the **client computes the equivalent amount before sending it to the server**, or the **server computes the amount from the percentage**. The transcript explicitly calls out that you should discuss *both* approaches with your interviewer and pick one deliberately (the reference implementation chooses "client always sends amount after converting from percentage," but explains how to extend it to let the server compute from percentage instead).

### Step 4 — Design `Expense` as a pure data holder

```java
class Expense {
    String expenseId;
    String description;
    double amount;
    User paidBy;
    SplitType splitType;      // EQUAL, PERCENTAGE
    List<Split> splits;       // who owes how much
}

class Split {
    User user;
    double amount;            // (or percentage, depending on your chosen design)
}
```
Deliberately keep `Expense` "dumb" — it just stores data. All creation/update/validation responsibility is delegated to a controller, following the principle: *treat domain entities as data holders and route all control flow through controllers* (this mirrors how `ExpenseController`, `UserController`, `GroupController`, and `BalanceSheetController` are all separate from their respective entities).

### Step 5 — `ExpenseController` + `SplitFactory` (creation & validation)

- `ExpenseController.createExpense(...)` is the single entry point — an expense can be created from **two places**: from inside a `Group`, or directly from the app (unattached to a group). Both paths funnel through the same controller method, which receives split details (which friend owes what), the total expense amount, and description.
- A `SplitFactory` is used to obtain and **validate** split objects before the expense is finalized:
  - For **Equal** splits: validate that the sum of all individual amounts equals the total expense amount (transcript's own example: 300 + 200 + 200 = 600, but if the declared total is different, this is an invalid request and should be rejected).
  - For **Percentage** splits: validate that all percentages sum to exactly 100%.
  - This validation logic is naturally extensible — the transcript notes you can add a "compute amount from percentage" step here later without touching any other class, since it's isolated behind the factory.

### Step 6 — `User`, `UserController`, `Group`, `GroupController`

- `User { userId, userName, UserExpenseBalanceSheet }` — plus a `UserController` holding `List<User>` and performing CRUD (add/remove/update user) operations. The key design point: the Splitwise app never mutates a `User` directly — all such operations flow through `UserController`.
- `Group { groupId, groupName, List<User> members, List<Expense> expenseList, ExpenseController }` — a group has its own list of members (who can be added/removed **from that group only**, not from the entire app) and its own list of expenses. A `GroupController` wraps group-level operations (create/manage group, add/remove members) the same way `UserController` wraps user-level operations.

### Step 7 — The Balance Sheet (the most important part)

Every `User` maintains its **own** balance sheet describing, per friend, how much is owed and how much is owed back — a `Map<User, Balance>` where `Balance` has two fields conceptually: **amount to get back** and **amount to give**. On top of the per-friend map, the balance sheet also keeps rollups: `totalGetBack`, `totalYouOwe` (or `totalPayment`), and `totalExpense` — so the UI can show both a summary view (top-level totals) and a drill-down view (per-friend breakdown) without recomputing anything on read.

```java
class UserExpenseBalanceSheet {
    Map<User, Balance> friendBalances; // per-friend ledger
    double totalYourExpense;
    double totalGetBack;
    double totalYouOwe;
    double totalPaymentMade;
}

class Balance {
    double amountGetBack; // this friend owes you
    double amountOwe;     // you owe this friend
}
```

### Step 8 — `BalanceSheetController` — updating balances when an expense is created

This is where the transactional correctness of the whole design lives. When `ExpenseController` finishes creating an `Expense`, it delegates to `BalanceSheetController.updateBalanceSheet(expense)`, which walks the list of splits and, for the specific worked example in the transcript (Lunch ₹500, User1 paid, splits: User1 owes ₹250, User2 owes ₹250):
1. For the user **who paid** (User1): increase `totalPayment` by the full amount (₹500), and increase `totalExpense` by their own share (₹250, since they still "consumed" part of the expense even though they fronted the money).
2. For every **other user in the split** (User2): increase their `totalExpense` by their share (₹250), and update the **per-friend Balance map** on both sides — User1's map entry for User2 gets `amountGetBack += 250`, and User2's map entry for User1 gets `amountOwe += 250`.
3. This "iterate over friends and increase/decrease the appropriate ledger entry" logic is exactly the kind of thing you should be ready to trace step-by-step on a whiteboard — the interviewer is testing whether you can reason about *both sides* of a ledger update staying in sync.

### Bonus mentioned in the transcript: debt simplification

The transcript notes that Splitwise's actual CEO has publicly mentioned (on Quora) that they use a **graph-based algorithm** to simplify group debts — collapsing chains of debt (A owes B, B owes C) into fewer, larger direct transactions (A owes C directly) so people don't have to make as many payments to settle up. This is a strong bonus point to mention if the interviewer probes deeper on "how would you minimize the number of transactions needed to settle a group."

## 🔥 Real Production Incident & Fix

**What broke:** An engineering team building a Splitwise-style expense app shipped a new "percentage split" feature. Their `BalanceSheetController.updateBalanceSheet()` method updated the **payer's** ledger entries correctly but had an off-by-reference bug: when iterating over the list of splits to update each friend's `Balance`, they mutated the payer's own `Balance` object *inside the same loop iteration* meant for friends, because the payer was accidentally included in their own splits list (a leftover from an equal-split code path that hadn't been adjusted for percentage splits).

**How the team noticed:** Customer support started getting tickets like "I paid ₹1000 for dinner and the app says I owe myself ₹150." The QA team's regression test suite didn't catch it because it only tested equal splits, not percentage splits with the payer explicitly included in the splits list. A support engineer noticed a spike in "balance sheet doesn't add up" tickets specifically correlated with the percentage-split feature's rollout, and pulled the change log to correlate the release date.

**Root cause:** The `Expense`'s split list included the payer as one of the "owing" users for percentage splits (since the UI let the payer optionally include themselves in the percentage distribution), but `BalanceSheetController` blindly treated every entry in the splits list as "a friend who owes the payer," including the payer's own entry — corrupting their self-referential balance.

**The fix:** The team added an explicit guard in `BalanceSheetController.updateBalanceSheet()`: `if (split.getUser().equals(expense.getPaidBy())) { updatePayerExpenseOnly(); continue; }` before updating the per-friend `Balance` map, ensuring the payer's own share only affects their `totalExpense` rollup, never their `friendBalances` map (a user should never have a `Balance` entry pointing at themselves).

```
BEFORE (bug): payer accidentally treated as their own "friend" in the splits loop
   for split in expense.splits:
       updateBalance(split.user, split.amount)   // ← runs even when split.user == payer

AFTER (fixed): payer's own share is short-circuited before touching the friend-balance map
   for split in expense.splits:
       if split.user == payer: updatePayerTotalsOnly(split.amount); continue
       updateBalance(split.user, split.amount)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why is `Expense` kept as a plain data object instead of putting the balance-update logic inside it?**
Because entities that hold both data and complex cross-object orchestration logic become hard to test and hard to extend — by routing all "what happens when an expense is created" logic through `ExpenseController` and `BalanceSheetController`, the `Expense` class stays a simple, stable data container, and you can change business rules (e.g., add a new split type, change how balances are computed) without touching the entity class at all.

**Q2: How would you extend this design to support a "settle up" / payment action between two friends?**
Add a lightweight `Payment` (or reuse `Expense` with a dedicated `SplitType.SETTLEMENT`) representing a direct transfer, then run it through the same `BalanceSheetController.updateBalanceSheet()` pipeline but with the update direction reversed (decrease the payer's `amountOwe` to the recipient, and decrease the recipient's `amountGetBack` from the payer) — reusing the existing controller keeps the ledger-update logic in exactly one place.

**Q3: How do you validate a percentage split adds up correctly, and what about floating-point rounding errors?**
`SplitFactory` validates that all percentages sum to 100% (or all split amounts sum to the total expense amount for equal splits); for floating-point amounts, use a small epsilon tolerance (e.g., `Math.abs(sum - total) < 0.01`) or work in integer paise/cents internally to avoid floating-point drift entirely — a detail worth calling out proactively to show production awareness.

**Q4: What happens when a user is removed from a group but still has an outstanding balance?**
The design should block removal (or force a "settle up first" flow) if `Balance.amountOwe` or `amountGetBack` is non-zero for that user within the group's scope — this is a good place to mention you'd add a `canRemoveMember()` check in `GroupController` before allowing removal, protecting data integrity.

**Q5: How would debt simplification (the graph algorithm) actually work at a high level?**
Model each user as a node and each net balance as a weighted directed edge (who owes whom, net of all expenses); then repeatedly find the maximum creditor and maximum debtor across the whole graph and settle between them directly, which provably minimizes the total number of transactions needed to zero out the graph — this is the technique Splitwise's CEO referenced regarding simplifying group debts.

**Q6: Why have both a `UserController`/`GroupController` and a `BalanceSheetController` instead of one big "AppController"?**
Splitting controllers by responsibility (user CRUD vs. group CRUD vs. balance-sheet mutation vs. expense creation) follows the single-responsibility principle, keeps each controller's method list small and testable in isolation, and matches how the transcript deliberately separates "who manages users" from "who manages the ledger side effects of an expense."

## 🔑 Key Takeaway

The whole design hinges on separating "an Expense is just data" from "creating an Expense has side effects on multiple users' balance sheets" — get that controller-driven ledger-update flow right (and prove you can trace it for both the payer and the friend), and you've nailed the interview.
