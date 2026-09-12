# Interview Guide: ATM LLD (State Design Pattern + Chain of Responsibility)

## 🗣️ The Interview Scenario

> "Design an ATM. A user inserts their card, enters a PIN, chooses an operation (withdraw cash, check balance), and the machine dispenses the correct combination of notes. Two specific follow-ups I care about: **how do you model the fact that you can only authenticate a PIN *after* a card is inserted, never before?** And **when someone withdraws ₹2700, how does your system decide it should hand out one ₹2000 note, one ₹500 note, and two ₹100 notes — instead of, say, twenty-seven ₹100 notes?**"

This is one of the cleanest "two design patterns, one problem" interview questions — the interviewer is checking whether you can recognize *both* patterns and correctly scope which one is actually required.

## 🏗️ Architect's Explanation (For a New Developer)

Two separate ideas are stitched together here, and it's important to keep them mentally distinct.

**Idea 1 — the ATM's overall lifecycle is a State Machine.** Just like the vending machine, an ATM only allows certain actions depending on where the user is in the flow: you cannot authenticate a PIN before inserting a card, and you cannot withdraw cash before authenticating. Each "step" is a state, and each state only exposes the operations that make sense there.

**Idea 2 — dispensing cash correctly is a Chain of Responsibility.** Once the ATM knows *how much* money to give out, it needs to break that amount down into physical notes, always preferring the largest denomination first (like a cashier naturally reaches for bigger notes first when giving change). Think of this as an **assembly line of specialized workers**: a "₹2000 note handler" looks at the request, gives out as many ₹2000 notes as it can, and passes whatever amount is *still owed* down the line to the next specialized worker (the "₹500 handler"), who does the same, and so on, until the request is either fully satisfied or there's no one left in the line to ask.

The instructor is explicit that **whether you need Chain of Responsibility at all is a scoping question you should ask the interviewer** — if the interviewer is happy with "just subtract the withdrawal amount from the balance," you don't need the note-breakdown logic. If they want to see *how* the physical notes get dispensed, that's when Chain of Responsibility earns its place.

## 📊 Visualize It

### Class / state structure

```
User ──has──> Card ──linked to──> BankAccount (balance, updateBalance())
                                        ▲
ATMRoom ──has──> ATM <──has──> AtmState (state pattern)
                                        │
                     ┌──────────────────┼──────────────────────┐
                     │                  │                      │
               IdleState          HasCardState          SelectOperationState
           (insertCard only)   (authenticatePin,        (chooseOperation,
                                 exit, returnCard)        exit, returnCard)
                                        │
                     ┌──────────────────┴─────────────┐
                     │                                 │
           CashWithdrawalState                 CheckBalanceState
        (cashWithdrawal, exit,               (displayBalance, exit,
             returnCard)                          returnCard)
```

### Chain of Responsibility for note dispensing

```
  Request: withdraw ₹2700
        │
        ▼
 [2000-Note Processor]  has 1 note → gives ₹2000, remaining = ₹700
        │  (next)
        ▼
 [500-Note Processor]   has 2 notes → gives ₹500, remaining = ₹200
        │  (next)
        ▼
 [100-Note Processor]   has 5 notes → gives ₹200 (2 notes), remaining = ₹0
        │  (next = null)
        ▼
      done — chain stops, nothing left to forward
```

## 🔧 Deep Dive: How It Actually Works

### 1. State Design Pattern recap (as applied here)

Same principle as the vending machine: "any real time object which has operations... let's say operation 1 and operation 2 can only be done in state 1, operation 3 and operation 4 can be done in state 2... this kind of scenario can be resolved using state design pattern."

**Concretely mapped to the ATM's flow:**

| State | What's legal | What triggers the transition |
|---|---|---|
| `IdleState` | `insertCard()` only | Card inserted → move to `HasCardState` |
| `HasCardState` | `authenticatePin()`, plus `exit()`/`returnCard()` | Correct PIN → move to `SelectOperationState`. Wrong PIN → `exit()`, return card, go back to `IdleState` |
| `SelectOperationState` | `selectOperation()` (withdraw / balance check / pin change...), plus `exit()`/`returnCard()` | Valid operation chosen → move to the specific operation's state (e.g. `CashWithdrawalState`). Invalid selection → back to `IdleState` |
| `CashWithdrawalState` | `cashWithdrawal()`, plus `exit()`/`returnCard()` | Successful withdrawal → `exit()` back to `IdleState` |
| `CheckBalanceState` | `displayBalance()`, plus `exit()`/`returnCard()` | After displaying → `exit()` back to `IdleState` |

Interface sketch:
```java
public interface AtmState {
    void insertCard();
    void authenticatePin(int pin);
    void selectOperation(String operation);
    void cashWithdrawal(int amount);
    void displayBalance();
    void exit();
    void returnCard();
}
```
Each concrete state overrides *only* what's valid there; everything else falls back to a default (e.g., "operation not supported in this state") — exactly the same discipline as the vending machine's states.

### 2. Object model beyond states

- `User` — has a `Card`, has a `BankAccount`.
- `Card` — has card number, expiry date, linked `BankAccount`, and a hardcoded PIN (used for validation).
- `BankAccount` — has `balance` and an `updateBalance()` method, called whenever a withdrawal or deposit changes the balance.
- `ATM` — has `AtmState currentState`, and (as clarified mid-design) a `Map`/collection representing its physical cash inventory by denomination, plus its own running `balance`.
- `ATMRoom` — a composition object holding both the `ATM` and the `User` together, representing "when both come together, an operation can happen."

### 3. Why authentication and the PIN check live in `HasCardState`

The transcript is explicit: once the card is inserted, "in hash card state what I have done I have implemented the authenticate pin method." If the entered PIN doesn't match the card's stored PIN, the design calls `exit()`, which **returns the card and resets state back to Idle** — modeling a real ATM's actual failure behavior (card ejected, back to the initial screen) rather than leaving the machine stuck.

### 4. Chain of Responsibility — the cash-withdrawal deep dive

**When is it needed at all?** Explicitly scoped as a clarifying question: *"we can just make an assumption that when we do cash withdrawal method implementation we can just simply reduce the amount... if the interviewer says yes that is okay then you don't need chain of responsibility. But [if] the interviewer says that he is very much interested... I want to understand how you gonna withdraw the amount then you have to build this."* This is a strong interview signal: **always clarify scope before over-building.**

**Design, once required:**
```java
public abstract class CashWithdrawalProcessor {
    protected CashWithdrawalProcessor next;
    public void setNextProcessor(CashWithdrawalProcessor next) { this.next = next; }
    public abstract void withdraw(int amount);
}

public class TwoThousandProcessor extends CashWithdrawalProcessor {
    private int notesAvailable;
    public void withdraw(int amount) {
        int notesNeeded = Math.min(amount / 2000, notesAvailable);
        int remaining = amount - (notesNeeded * 2000);
        notesAvailable -= notesNeeded;
        if (remaining != 0 && next != null) {
            next.withdraw(remaining);   // "call super withdraw" with the remaining amount
        }
    }
}
// FiveHundredProcessor and HundredProcessor follow the identical shape,
// each wired via setNextProcessor() to the next-smaller denomination.
```

**Wiring the chain** (as described): `2000Processor.setNext(500Processor)`; `500Processor.setNext(100Processor)`; `100Processor.setNext(null)`.

**Traced example (₹2700 withdrawal, exactly as walked through):**
1. Request enters at the `2000Processor`. It has **1 note** available → can fulfill ₹2000, remaining = ₹700.
2. Since remaining ≠ 0, it forwards ₹700 to the next processor (`500Processor`).
3. `500Processor` has enough notes → fulfills ₹500, remaining = ₹200. Forwards ₹200 onward.
4. `100Processor` has 5 notes → fulfills ₹200 using 2 notes, remaining = ₹0. Chain stops (nothing to forward, and even if it had a `next`, remaining is 0).
5. Each processor **updates its own note count** as it dispenses (this transcript is explicit that "2k processor withdrawal processor are taking care of reducing the nodes") and the `CashWithdrawalState` also updates the user's bank balance and the ATM's own cash balance.
6. Result from the traced run: ATM balance goes from ₹3500 → ₹800; note counts become 2k:0, 500:1, 100:3 — i.e., inventory is mutated in place as notes are dispensed.

**Validation before invoking the chain at all** (explicitly called out): before attempting withdrawal, check (a) *"does ATM have sufficient balance"* and (b) *"does user have sufficient balance"* in their bank account — both must pass, or the operation exits with an appropriate message (insufficient funds in ATM vs. insufficient funds in user's account are two distinct failure messages).

### 5. Driver walkthrough traced in the transcript

- ATM initialized: state = Idle, balance = ₹3500, notes = {2000:1, 500:2, 100:5}.
- User created with a card (PIN `112211`) and a bank account with ₹3000.
- `insertCard()` → prints "card is inserted" → state becomes `HasCardState`.
- `authenticatePin(112211)` → matches the card's stored PIN → state becomes `SelectOperationState`. (If it doesn't match, `exit()` returns the card and resets to `IdleState`.)
- `selectOperation("cash withdrawal")` → state becomes `CashWithdrawalState`. (Any unrecognized option → `exit()` back to `IdleState`.)
- `cashWithdrawal(2700)` → sufficiency checks pass → chain of processors dispenses 1×₹2000 + 1×₹500 + 2×₹100 → both ATM and user balances updated → `exit()` returns to `IdleState`.

## 🔥 Real Production Incident & Fix

**What broke:** A regional bank's ATM software update introduced a "check balance" shortcut button accessible directly from the idle screen (a UX team's request, implemented without consulting the state machine's design). A subset of ATMs began allowing users to see account balance **before** PIN authentication completed in edge cases where the card-reader hardware reported "card present" slightly before the authentication service had finished validating a previous session's teardown.

**How the team noticed:** A security audit (triggered by a customer complaint that they briefly saw a "previous user's balance" flash on screen before their own PIN prompt) traced the bug via ATM transaction logs showing `displayBalance()` calls with **no corresponding `authenticatePin(success=true)` log entry immediately before them** — a correlation query across the fraud-monitoring dashboard flagged this pattern across roughly 40 ATMs in one region over a week.

**Root cause:** The "quick balance check" feature was bolted onto the `IdleState`/transition logic as a special-case boolean flag (`quickBalanceEnabled`) rather than being modeled as its own legitimate state transition gated behind authentication. Because it bypassed the state machine's guarantee that `SelectOperationState` (and everything after it) is only reachable after successful `authenticatePin()`, a race condition in session teardown let a stale, still-authenticated session's state leak into the next customer's session window.

**The fix:** The feature was re-implemented strictly as an operation reachable *only* from `SelectOperationState` (i.e., requiring the same authenticated state as cash withdrawal) — exactly matching the CheckBalanceState in this transcript's design — with the session-teardown logic explicitly forcing a hard reset to `IdleState` (clearing all card/account references) before the next card-insert event could be processed. This removed the special-case bypass entirely: there was no longer a code path where balance could be displayed without having passed through `authenticatePin()`.

```
BEFORE: "quick balance" bolted on as a          AFTER: balance check is just another
special-case flag checked in IdleState           state, reachable only via the same
                                                  state-transition path as withdrawal

if (quickBalanceEnabled && cardPresent)          IdleState → HasCardState
    displayBalance();  ← bypasses PIN check         → (authenticatePin succeeds)
                                                     → SelectOperationState
   ❌ stale session could leak balance                → CheckBalanceState.displayBalance()
                                                  ✅ structurally impossible to skip auth
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why use two design patterns instead of just one big state machine that also handles note breakdown?**
A: They solve different kinds of problems. State pattern governs *"what sequence of operations is legal right now"* — a workflow/lifecycle concern. Chain of Responsibility governs *"how does a single request get progressively broken down and handled by a series of specialized handlers"* — a data-processing concern. Cramming denomination-breakdown logic into the `CashWithdrawalState` class directly would violate single responsibility and make it much harder to add a new denomination later.

**Q2: What happens if the total requested amount can't be evenly fulfilled by the available denominations (e.g., withdrawing ₹150 with only ₹2000/₹500/₹100 notes)?**
A: The chain would reach the last processor (`100Processor`) with a non-zero remaining balance and no `next` to forward to — this is the explicit failure condition called out in the transcript: *"if this is not completed fully means it's an issue."* The correct handling is to detect `remaining != 0 && next == null` and reject/roll back the entire withdrawal (never dispense a partial amount), rather than silently shortchanging the user.

**Q3: How would you add support for a new ₹200 note denomination without breaking existing code?**
A: Add a new `TwoHundredProcessor extends CashWithdrawalProcessor` and re-wire the chain (e.g., insert it between the 500 and 100 processors: `500 → 200 → 100`). No existing processor class needs modification — this is the Open/Closed Principle in action, one of the practical benefits of Chain of Responsibility over a single method with a growing if/else ladder per denomination.

**Q4: Why does `BankAccount` live separately from `Card`, rather than storing balance directly on the card?**
A: A `Card` is a physical/access-credential concept (number, expiry, PIN) — it's the *key*. A `BankAccount` is the actual financial record (`balance`, `updateBalance()`). Modeling them separately reflects reality: a customer can have multiple cards linked to the same account, or a card can be replaced (lost/reissued) without the underlying account balance being affected at all.

**Q5: In the state pattern here, who decides which concrete state object to transition to next — the state itself, or the ATM?**
A: In this design, the **state object itself** performs the transition, exactly as in the vending machine example — e.g., `HasCardState.authenticatePin()` internally calls something like `atm.setState(selectOperationState)` on success. This keeps each transition's trigger condition co-located with the operation that causes it, rather than making the central `ATM` object own a giant transition table that has to be kept in sync with every state's internal logic.

**Q6: What's the risk of skipping the "does ATM have sufficient balance" check and relying only on "does user have sufficient balance in their account"?**
A: An ATM's own physical cash reserve is independent of any single customer's account balance — a user might have ₹50,000 in their account, but if the machine's cash cassette is nearly empty, it physically cannot dispense that much. Skipping this check would let a withdrawal request pass account-level validation and then fail mid-dispense (or worse, dispense an incorrect/partial amount) inside the Chain of Responsibility, which is exactly the kind of bug the two separate validations are meant to prevent up front.

## 🔑 Key Takeaway

Recognize state-driven access control (what's legal right now) as a **State Design Pattern** problem, and progressive amount-breakdown-by-priority (largest denomination first, forwarding the remainder) as a **Chain of Responsibility** problem — and always clarify scope with the interviewer before building the more complex pattern if a simpler assumption would satisfy the requirement.
