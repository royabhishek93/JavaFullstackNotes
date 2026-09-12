# Interview Guide: The LLD & HLD Interview Preparation Roadmap

## 🗣️ The Interview Scenario

> "We have about twelve weeks before your system design interview loop starts. Walk me through exactly how you'd structure your preparation for Low-Level Design and High-Level Design — what do you learn first, in what order, and why? Also, how would you know when you're actually 'ready' versus just 'have watched a lot of videos'?"

This is a meta-question, not a coding question — but senior interviewers and mentors ask it constantly, because *how* a candidate organizes their learning tells you a lot about whether they understand system design as a discipline with dependencies, or as a random grab-bag of trivia ("what is Singleton", "what is CAP theorem") memorized without structure.

## 🏗️ Architect's Explanation (For a New Developer)

Think of LLD and HLD as two separate skill trees, each with prerequisites — like a video game where you can't equip the level-20 armor until you've farmed the level-10 dungeon.

**LLD (Low-Level Design)** is about *classes and objects* — how you structure code inside one component. It has a very clean dependency chain:

1. **OOP fundamentals** (inheritance, polymorphism, abstraction, encapsulation) — the alphabet. Without this, nothing else makes sense, in any language (Java, C++, Python — doesn't matter).
2. **SOLID principles** — the grammar. These are *not* design patterns; they are the underlying rules that make a design "good" in the first place. That's why they always come first.
3. **Design patterns** (23 classic GoF patterns, split into creational / structural / behavioral) — the vocabulary. Reusable solutions to problems that keep repeating (e.g., "I need only one instance of this object" → Singleton).
4. **LLD interview questions** (Parking Lot, Vending Machine, ATM, Notify-Me/Amazon-style stock alerts, Pizza Billing, Splitwise, BookMyShow, Tic-Tac-Toe, Elevator, Snake & Ladder, Chess, File System...) — the sentences you actually write in the interview, built by combining patterns.

The key teaching philosophy here — and a genuinely useful interview-prep insight — is: **you do not need to learn all 23 patterns before you can solve any question.** Some questions map almost 1:1 onto a single pattern (Vending Machine → State pattern, Notify-Me → Observer pattern, Pizza toppings → Decorator pattern). Others are "composite" questions that stitch together multiple patterns you've already learned. So the efficient strategy is: learn a handful of high-leverage patterns, immediately apply them to real interview questions, then keep expanding the pattern vocabulary and revisiting harder questions.

**HLD (High-Level Design)** is different in one important way: you often *cannot* attempt the big questions until you've learned the underlying technology, because the vocabulary itself is technical infrastructure, not just object modeling. You can't design something using consistent hashing if you don't know what consistent hashing *is* — there's no "common sense" fallback the way there sometimes is in LLD.

So HLD has two tiers:
- **Foundational building blocks**: TCP vs WebSocket vs HTTP vs WebRTC, client-server vs peer-to-peer architecture, CAP theorem, microservice patterns (Saga is called out as unmissable, Strangler Fig sometimes), scaling from zero to a million users, consistent hashing, back-of-the-envelope estimation, SQL vs NoSQL decision-making.
- **Applied big questions**: Design a key-value store (DynamoDB-style), Design WhatsApp, Design a Rate Limiter, Design an autocomplete/typeahead system.
- **Deeper infrastructure tier** (comes after the above): message queues (Kafka), proxies, CDNs, storage types (block storage, file storage, object storage like S3), RAID, filesystem internals, Bloom filters, Merkle trees, gossip protocols, caching strategies, and database scaling techniques (horizontal/vertical partitioning, replication, leader election, indexing).

## 📊 Visualize It

```
LLD SKILL TREE                          HLD SKILL TREE
───────────────                         ───────────────
OOP Fundamentals                        Networking Basics
(inheritance, polymorphism)             (TCP, HTTP, WebSocket, WebRTC)
      │                                        │
      ▼                                        ▼
SOLID Principles                        Client-Server vs P2P
(SRP, OCP, LSP, ISP, DIP)               CAP Theorem
      │                                        │
      ▼                                        ▼
Design Patterns (23, GoF)               Core Building Blocks
┌─────────────┬─────────────┬─────────┐  (Consistent Hashing,
│ Creational  │ Structural  │Behavioral│  Back-of-Envelope Est.,
│ Singleton   │ Decorator   │Strategy │  SQL vs NoSQL,
│ Factory     │ Proxy       │Observer │  Saga / Strangler,
│ Builder     │ Adapter     │State    │  Scale 0→1M users)
└─────────────┴─────────────┴─────────┘        │
      │                                        ▼
      ▼                                 Applied Big Questions
LLD Interview Questions                 (Design WhatsApp,
(Parking Lot, Vending Machine,          Rate Limiter, Key-Value
ATM, Notify-Me, BookMyShow,             Store, Typeahead/Autocomplete)
Elevator, Splitwise, Chess...)                 │
                                                ▼
                                         Infra Deep-Dive
                                         (Kafka, CDN, Proxies,
                                         Bloom Filters, Merkle Trees,
                                         Gossip Protocol, DB Sharding)
```

```
WRONG ORDER (common junior mistake)      RIGHT ORDER (roadmap-driven)
────────────────────────────────         ────────────────────────────
"Design Parking Lot" (cold)              OOP → SOLID → 2-3 patterns
      │                                          │
      ▼                                          ▼
Ad-hoc classes, no consistent             Recognize Parking Lot needs
principle behind decisions                Strategy (pricing) + Factory
      │                                   (spot allocation)
      ▼                                          │
Interviewer asks "why this                       ▼
design?" → no principled answer           Confident, principle-backed
                                           answer: "I used Strategy here
                                           because pricing rules vary
                                           independently of vehicle type"
```

## 🔧 Deep Dive: How It Actually Works

### The LLD sequencing logic
- **Step 0 — Prerequisite check:** if you understand inheritance, polymorphism, and abstraction in *any* OOP language, you're eligible to start LLD. Language doesn't matter (Java, C++, Python are all fine).
- **Step 1 — SOLID first, always.** SOLID is explicitly called the "number one" prerequisite before patterns, because it's the criteria you use to *judge* whether a pattern-based design is actually good.
- **Step 2 — Learn patterns in small batches, not all-at-once.** The stated teaching method is deliberately *not* "cover all 23 patterns, then start solving questions." Instead: cover a few important patterns → solve real questions that use exactly those patterns → repeat. This avoids the common failure mode of memorizing pattern definitions with no idea when to reach for them.
- **Step 3 — Map patterns to canonical questions.** Some LLD questions are almost direct applications of one pattern:
  - Vending Machine → State pattern
  - Notify-Me / stock alert system → Observer pattern
  - Pizza/Coffee billing with toppings → Decorator pattern
  - Parking Lot → Strategy (pricing) + Factory (spot/vehicle creation)
  - ATM → State pattern
  Other questions (Splitwise, BookMyShow, Cricbuzz) are larger and combine multiple patterns plus plain OOP modeling — these come later once the pattern vocabulary is bigger.
- **Important mindset point:** knowing the pattern name is *not* mandatory to solve a question. Sometimes you naturally arrive at a Strategy-like or Observer-like structure just by solving the problem, and only afterward you'd recognize "oh, that's the Observer pattern." Patterns exist so you don't have to reinvent an already-known-good solution — they're a shared vocabulary between you and your interviewer, not a checklist to force-fit.

### Why LLD has "no fixed curriculum"
Unlike HLD, there's no "Chapter 1, Chapter 2, Chapter 3" and no single correct answer for a given LLD question — two engineers can design a valid Parking Lot completely differently. That's precisely why a *structured learning sequence* (OOP → SOLID → patterns → questions) matters: it gives you a repeatable decision-making framework even though the destination (the "correct" class diagram) isn't unique.

### Why HLD sequencing is different
For HLD, a meaningful chunk of the big questions genuinely can't be attempted without first knowing the underlying technology — e.g., you cannot propose "use consistent hashing to distribute keys across shards" if you've never learned what consistent hashing is. So the roadmap explicitly puts more foundational technology topics *before* the flagship questions:
- Networking layer: TCP, HTTP, WebSocket, WebRTC, client-server vs peer-to-peer.
- Distributed systems theory: CAP theorem.
- Patterns at the service level: microservices patterns, with the Saga pattern explicitly flagged as something you must not skip (for distributed transactions), and the Strangler Fig pattern for incremental migrations.
- Estimation skills: scaling from 0 to a million users, back-of-the-envelope capacity estimation (a very common interview ask: "how many servers/how much memory would you need?").
- Data layer decisions: SQL vs NoSQL, when to use a key-value store like DynamoDB (which itself depends on understanding consistent hashing).
- Then the flagship "big" questions: Design WhatsApp, Design a Rate Limiter, Design an Autocomplete/Typeahead system.
- Then the deep infrastructure tier that supports scaling those systems further: Kafka/queues, proxies, CDNs, block/file/object storage (S3), RAID, filesystem design, Bloom filters, Merkle trees, gossip protocols, caching layers, and database scaling techniques (horizontal/vertical partitioning, mirroring/replication, leader election, indexing).

### Where the actual interview questions come from
A practical, often-overlooked point: the questions used for practice aren't invented in a vacuum — they are pulled from real interviews conducted at product-based companies, supplemented by candidate submissions and pattern-of-frequency analysis (i.e., "which question keeps getting asked across many companies"). This matters for interview prep strategy: prioritize the questions that show up repeatedly across companies over rare/niche ones.

## 🔥 Real Production Incident & Fix

**The incident:** A newly-formed team at a mid-size e-commerce company was under a two-week deadline to add "notify me when back in stock" to their product page — almost exactly the Observer-pattern use case. Two junior engineers, who understood inheritance and polymorphism but had skipped SOLID and pattern study entirely (they went straight from "I know OOP" to "let's just write the feature"), implemented it as a single `StockService` class with a hard-coded list of `if (channel.equals("email")) {...} else if (channel.equals("sms")) {...}` blocks directly inside the stock-update method, and a tightly-coupled `List<String> subscriberEmails` field.

**How the team noticed:** Three weeks after launch, product asked for a third notification channel (push notification), and QA flagged that adding it required touching the *same* method that also handled email and SMS — and a regression slipped through where updating the SMS logic accidentally broke the email path because both were interleaved in one giant conditional block. Code review on the fix PR flagged "this class has too many reasons to change" — a textbook Single Responsibility Principle violation, and the reviewer noted the shape of the problem was a textbook Observer pattern that nobody had recognized.

**Root cause:** The team had jumped straight to "the big LLD interview questions" mentality (write code that works for the feature request) without the SOLID → pattern-recognition step that the roadmap emphasizes. There was no reusable "subscribe/notify" abstraction, so every new channel meant editing shared, already-tested, already-live code — directly violating the Open/Closed Principle too (modifying instead of extending).

**The fix:** They refactored using the Observer pattern: an `Observable` (the product/stock entity) maintaining a list of `Observer` implementations (`EmailAlertObserver`, `SmsAlertObserver`, later `PushAlertObserver`), with `notifyAll()` iterating the list and calling `update()` on each — so adding push notifications became "write one new class implementing `Observer`, register it," with zero changes to already-tested code.

```
BEFORE (all channels tangled in one class)     AFTER (Observer pattern applied)
──────────────────────────────────────────     ────────────────────────────────
StockService {                                  Observable (Stock)
  onStockUpdate() {                                 │  notifies
    if (email) sendEmail()                          ▼
    if (sms)   sendSms()          ───►       Observer interface
    // adding "push" means editing                  ▲
    // this same tested method                      │ implements
  }                                        EmailObserver  SmsObserver  PushObserver
}                                          (new channel = new class, zero edits above)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why does SOLID come before design patterns in a learning roadmap, and not the other way around?**
A: SOLID gives you the *evaluation criteria* for a good design — for example, "does this class have only one reason to change?" (SRP). Design patterns are concrete recipes that *happen to satisfy* those criteria in common scenarios. If you learn patterns first without SOLID, you tend to memorize pattern shapes without understanding *why* they're structured that way, and you can't recognize when a pattern is being misapplied.

**Q2: If there's no single "correct" LLD answer, how do you evaluate a candidate's design in an interview?**
A: You're not grading against one canonical UML diagram; you're grading against principles — is the design open for extension without modifying tested code (OCP)? Does each class have a single responsibility? Can child classes substitute parents without breaking behavior (LSP)? A structured but non-unique answer that satisfies these is considered strong, even if it differs from another valid design.

**Q3: Why can't you always jump straight into HLD's "big" questions (like Design WhatsApp) the way you sometimes can with LLD?**
A: Many HLD questions assume familiarity with specific distributed-systems technology (consistent hashing, CAP theorem trade-offs, replication strategies) that isn't derivable from first principles the way OOP-based class design often is. Without that vocabulary, you literally can't propose or discuss the standard solutions, so foundational topics are a hard prerequisite rather than a nice-to-have.

**Q4: Give an example of an LLD question that maps almost directly to one design pattern, and explain the mapping.**
A: A Vending Machine maps closely to the State pattern — the machine's behavior (accept coins, dispense item, return change) genuinely changes based on its current state (`Idle`, `HasMoney`, `Dispensing`, `SoldOut`), and each state encapsulates only the transitions valid from it, avoiding a giant switch statement scattered with state-checking conditionals.

**Q5: What's the practical risk of memorizing all 23 GoF patterns before ever applying one to a real question?**
A: You end up with definitional knowledge ("Singleton ensures one instance") but no pattern-recognition instinct — the actual interview skill is spotting *which* pattern fits a *novel* problem statement under time pressure. That instinct only comes from repeatedly seeing pattern → applied-question pairs, which is why the roadmap deliberately interleaves a few patterns with immediate question practice instead of front-loading all pattern theory.

**Q6: Why is the Saga pattern specifically flagged as "unmissable" in the HLD microservices section?**
A: Because distributed transactions across microservices can't use a single ACID database transaction — Saga (via choreography or orchestration, with compensating actions) is the standard way to maintain data consistency across services, and it comes up constantly in real interviews whenever a design spans more than one service with its own database.

## 🔑 Key Takeaway

Both LLD and HLD are skill trees with real dependencies, not flashcard decks — LLD needs OOP → SOLID → a *few* patterns before you attempt questions, and HLD needs core distributed-systems building blocks (CAP theorem, consistent hashing, estimation) before the flagship questions; skipping the foundation to rush toward "the big questions" is the single most common and costly interview-prep mistake.
