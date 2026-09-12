# 🧭 LLD & HLD Interview Roadmap - Interview Guide
## _15 YOE Architect-Level Conversational Script_

**📗 Difficulty: Beginner** — ideal starting point for a new developer; read this before tackling applied system-design questions.

> _(Companion to `transcript.md`, left untouched. This is how I'd frame the "how do I even prepare for LLD/HLD interviews" conversation with a new developer joining my team.)_

---

**New Developer**: "I have interviews coming up in a few months. Where do I even start with LLD and HLD prep — it feels like an infinite list of topics?"

**You**: "Let me draw you the exact roadmap I'd follow, in order — this isn't a random topic dump, each layer is a prerequisite for the next."

---

## 1. The LLD Prerequisite Ladder

```
┌───────────────────────────┐
│  4. Solve LLD Questions            │  Parking Lot, Elevator, Splitwise,
│     (apply patterns to problems)     │  BookMyShow, Snake&Ladder, ATM,
│                                       │  Vending Machine, Chess, File System...
└───────────┬───────────────────┘
              ▲
┌───────────┴───────────────────┐
│  3. Learn Design Patterns (23 total) │  Strategy, Observer, Decorator, Factory,
│     (creational/structural/behavioral)│  Singleton, Builder, Adapter, Bridge...
└───────────┬───────────────────┘
              ▲
┌───────────┴───────────────────┐
│  2. SOLID Principles                    │  SRP, OCP, LSP, ISP, DIP
└───────────┬───────────────────┘
              ▲
┌───────────┴───────────────────┐
│  1. OOP Fundamentals                    │  Inheritance, Polymorphism,
│     (any OOP language works)              │  Abstraction, Encapsulation
└───────────────────────────────┘
```

**You**: "Notice the teaching philosophy here (and I use this with every mentee): **don't try to memorize all 23 patterns before solving any real question.** Instead, learn a handful of high-leverage patterns, then IMMEDIATELY apply them to a real interview question (like Vending Machine → State Pattern, Parking Lot → Strategy/Factory). Patterns learned in isolation without application fade fast; patterns learned via a concrete problem stick."

---

## 2. The HLD Path Is Different — and That's Important to Know

```
LLD: "no fixed syllabus, no single correct answer"     HLD: "concepts must come FIRST, questions come after"

┌──────────────┐                                   ┌──────────────┐
│  Question-first    │                                   │  Concept-first     │
│  (apply patterns as  │                                   │  (you literally CANNOT│
│   you learn them)      │                                   │   design a system without│
└──────────────┘                                   │   knowing consistent      │
                                                        │   hashing, CAP theorem,    │
                                                        │   sharding, etc. FIRST)      │
                                                        └──────────────┘
```

```
HLD Roadmap layers (bottom = foundational concepts, learned before big questions):

┌─────────────────────────────────────────────┐
│  Big System Questions: WhatsApp, DynamoDB, Rate Limiter,│
│  Autocomplete, URL Shortener...                              │
├─────────────────────────────────────────────┤
│  Scaling: horizontal/vertical partitioning, replication,       │
│  leader election, indexing, caching                             │
├─────────────────────────────────────────────┤
│  Infra building blocks: Kafka/queues, proxies, CDN, storage      │
│  (block/file/object), Bloom filters, Merkle trees, gossip           │
├─────────────────────────────────────────────┤
│  Core concepts: TCP/WebSocket/HTTP/WebRTC, client-server &          │
│  peer-to-peer, CAP theorem, microservices patterns (Saga,             │
│  Strangler Fig), back-of-envelope estimation, SQL vs NoSQL,             │
│  consistent hashing                                                        │
└─────────────────────────────────────────────┘
```

---

## 3. Cross Questions

**Q: "Should I learn all 23 design patterns before attempting any LLD question?"**
**A:** "No — that's the single biggest time-waster in LLD prep. Learn 4-5 foundational patterns (Strategy, Observer, Factory, Singleton, State), then start solving real questions immediately, picking up new patterns AS a question demands them. This mirrors how patterns actually get used on the job — you reach for a pattern when a real problem calls for it, not because you're working through a checklist."

**Q: "Which topics are 'must-know' if I only have 2 weeks before an interview?"**
**A:** "Priority order for LLD: SOLID Principles (non-negotiable, gets asked directly AND implicitly graded in every design) → Strategy, Observer, Factory, Singleton, State (cover ~70% of common questions) → 3-4 solved questions using ONLY those patterns (Parking Lot, Vending Machine, Splitwise, BookMyShow). For HLD: back-of-envelope estimation, CAP theorem, consistent hashing, SQL vs NoSQL — these four alone unlock understanding most 'design X at scale' questions."

---

## 4. Senior Trap Questions

**Trap: "Isn't memorizing more patterns always better preparation?"**
**✅ Senior answer:** "Breadth without application is fragile under interview pressure — you'll freeze translating a memorized pattern definition into a live problem. Depth on fewer, well-practiced patterns, each tied to at least one fully-solved question you can explain end-to-end (including trade-offs and 'why not X instead'), is a far stronger interview signal than shallow familiarity with all 23."

---

## 🔥 Real-World Production Issue: The "We'll Figure Out Scale Later" Roadmap Mistake

*In plain English: skipping the fundamentals to jump straight into "big" system design leads to expensive, risky retrofits later — build the foundation first.*

**The war story:**

"This roadmap discipline isn't just for interviews — I've seen the EXACT same 'skip the fundamentals, jump straight to big questions' mistake made in real system design at a company, with real production consequences."

```
What the team did:                          What should have happened
(jumped straight to building                (roadmap discipline: understand
 a 'WhatsApp-scale' chat feature              foundational concepts FIRST):
 without foundational concepts):
┌───────────────────────────┐            ┌───────────────────────────┐
│ Built chat feature on a single   │            │ 1. Estimate scale (back-of-  │
│ Postgres instance, no sharding,     │            │    envelope: 2M DAU, 50 msgs/ │
│ no partitioning strategy, no          │            │    user/day = 100M msgs/day)   │
│ consistent hashing for routing         │            │ 2. Pick sharding strategy UP    │
│  "we'll figure out scale later"        │            │    FRONT (consistent hashing    │
└───────────────────────────┘            │    by conversation_id)             │
         ⬇ 8 months later, user growth        │ 3. Design for horizontal scale   │
         hit 2M DAU                              │    from day 1                       │
         ⬇                                        └───────────────────────────┘
   Single Postgres instance hit CPU/IO
   ceiling — no sharding strategy existed,
   and RETROFITTING consistent hashing
   onto a live system with existing data
   required a multi-week, high-risk
   migration with a 6-hour planned outage
```

**Root cause:** the team skipped the "foundational concepts before big questions" discipline this very roadmap teaches — they attempted to design a large-scale system without first understanding consistent hashing, sharding strategy, and back-of-envelope capacity estimation, exactly the prerequisite layers at the bottom of the HLD roadmap diagram above. The result was a costly, risky retrofit instead of a clean upfront design.

**The fix:** the team paused feature work for two weeks to formally learn/apply consistent hashing and sharding, then executed a carefully planned, low-risk migration with dual-writes and gradual traffic cutover — the exact kind of foundational-concept-first thinking this roadmap is designed to instill before you're ever in a live incident.

**Lesson for a new developer:** "The roadmap's ordering (fundamentals → patterns → applied questions, and for HLD: core concepts → infra building blocks → big questions) isn't just a study plan — it mirrors how you should approach REAL system design work. Skipping straight to 'build the big feature' without the foundational layer is how teams end up doing expensive, risky retrofits instead of cheap, safe upfront design decisions."

---

## 🎓 Final Tips
1. LLD prep: OOP fundamentals → SOLID → a handful of patterns → apply immediately to real questions (don't memorize all 23 upfront).
2. HLD prep: concepts (CAP, consistent hashing, estimation) MUST come before attempting big system questions — you literally cannot design without them.
3. Depth on fewer well-practiced, fully-explainable patterns/questions beats shallow breadth.
4. This same "fundamentals-first" discipline applies to real production system design, not just interviews — skipping it leads to expensive retrofits later.

Good luck! 🚀
