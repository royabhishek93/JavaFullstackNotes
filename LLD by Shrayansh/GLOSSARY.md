# 📖 Jargon Buster — Plain-English Glossary

A quick lookup for the shorthand terms used across the `INTERVIEW_GUIDE.md` files in this repo. If you hit an unfamiliar acronym while reading a guide, check here first.

---

### Concurrency & Correctness

- **Race condition** — a bug that only happens when two things run "at the same time" in an unlucky order. Like two people grabbing the last seat at once because nobody checked first.
- **TOCTOU (Time-Of-Check to Time-Of-Use)** — a race condition where you *check* something ("is this seat free?") and *use* it ("book the seat") as two separate steps, and someone else sneaks in between the two steps.
- **Atomic operation** — an operation that either fully happens or doesn't happen at all — nobody can see it "half-done". Databases give you atomic `UPDATE ... WHERE` statements specifically to avoid TOCTOU bugs.
- **Idempotency / Idempotency key** — making a repeated request behave exactly like doing it once. If your app crashes right after charging a card and the client retries, an idempotency key lets the server recognize "I already did this" and avoid charging twice.
- **Thread pool** — a fixed set of reusable worker threads that handle incoming requests. If every worker gets stuck waiting on something slow, new requests have nobody to serve them ("thread pool exhaustion").
- **Circuit breaker** — a safety switch that stops calling a failing/slow external service for a while, instead of letting every request hang waiting on it. Same idea as a home electrical circuit breaker.
- **Double-checked locking / `volatile`** — a specific safe way to create a Singleton object under concurrent access; `volatile` stops the CPU from reordering instructions in a way that could expose a half-built object to another thread.
- **ACID** — the 4 guarantees a database transaction gives you: Atomicity (all-or-nothing), Consistency (never leaves data in a broken state), Isolation (transactions don't see each other's half-done work), Durability (once saved, it survives a crash). This is why financial systems (ATM, payments) insist on it.

### Security

- **OWASP** — Open Web Application Security Project; publishes the well-known "Top 10" list of common web security vulnerabilities. When a guide says "OWASP-relevant", it means the bug is a well-known, common class of security mistake.
- **Broken access control / trust boundary violation** — trusting data or a decision from somewhere you shouldn't (e.g., trusting a discount amount sent by the client instead of recalculating it on the server).
- **RCE (Remote Code Execution)** — the worst-case security bug: an attacker manages to run their own arbitrary code on your server.
- **PCI-DSS** — the security standard payment companies must follow (e.g., never store raw card numbers).

### Reliability & Scale

- **p99 latency** — "99% of requests are faster than this number." A more honest way to talk about speed than the average, because it captures the slow outliers that make users complain.
- **SLA (Service Level Agreement)** — a promise about how reliable/fast a service will be (e.g., "99.99% uptime"), often with a contractual/business consequence if broken.
- **SLO (Service Level Objective)** — the internal target a team aims for (e.g., "p99 < 200ms") that usually backs up an SLA.
- **Blast radius** — how much of the system breaks when one thing goes wrong. Good design keeps blast radius small (one bug shouldn't take down unrelated features).
- **God object / God class** — a single class that has grown to do far too much (validation + pricing + notifications + logging...), making every change risky because so many unrelated things live in one place.
- **Contract testing** — automated tests that check "does this dependency (or my code wrapping it) still behave the way I assumed?" — catches silent breaking changes from third parties before they reach production.
- **Feature flag** — a config switch that turns a feature on/off (or for specific users) without a code deployment.

### Infrastructure Building Blocks (mentioned in "Technology Choices" sections)

- **Kafka / message queue** — a durable, ordered log of events that multiple consumers can read independently, used to decouple "something happened" from "who needs to react to it".
- **WebSocket** — a persistent, two-way connection between client and server, used for real-time updates (chat, live scores, live bidding) instead of the client repeatedly asking "anything new?".
- **Redis** — a very fast in-memory data store, commonly used as a cache (not the permanent source of truth) or for ephemeral state like current game state or a rate-limiter counter.
- **Consistent hashing** — a way to distribute data/requests across many servers so that when you add/remove one server, only a small fraction of data needs to move (instead of nearly all of it).
- **Sharding / partitioning** — splitting one big dataset across multiple databases/servers so no single machine has to hold or serve all of it.
- **CAP theorem** — a rule of thumb saying a distributed system can't simultaneously guarantee perfect Consistency, Availability, and Partition-tolerance — you must choose trade-offs.
- **Back-of-envelope estimation** — quick, rough math (e.g., "2M users × 50 requests/day ≈ 100M requests/day") used early in a design to decide if you need a single server or a heavily distributed system.

### Design Pattern Shorthand

- **SOLID (SRP, OCP, LSP, ISP, DIP)** — the 5 foundational object-oriented design principles; see [03_SOLID's guide](03_1_SOLID_Principles_with_Easy_Examples_Hindi_OOPs_SOLID_Principles_-_Low_Level_Design/INTERVIEW_GUIDE.md) for the full plain-English breakdown of each letter.
- **Has-a vs Is-a** — "Is-a" means inheritance (a `Car` IS-A `Vehicle`). "Has-a" means one object holds a reference to another (a `Library` HAS-A list of `Book`s).
- **Intrinsic vs Extrinsic state** (Flyweight Pattern) — intrinsic = data that's identical and shareable across many objects (a robot's 2D sprite image); extrinsic = data unique to one specific object (that robot's x,y position on screen), passed in as a parameter instead of stored.
- **CGLIB proxy** — a technique frameworks like Hibernate/Spring use to generate a "stand-in" object at runtime that defers real work (like a DB query) until you actually touch it — a real-world example of the Proxy Pattern.

---

*If a term you encountered isn't listed here, it's likely explained inline the first time it's used in that specific guide — look for the sentence right after it in parentheses or the following sentence.*
