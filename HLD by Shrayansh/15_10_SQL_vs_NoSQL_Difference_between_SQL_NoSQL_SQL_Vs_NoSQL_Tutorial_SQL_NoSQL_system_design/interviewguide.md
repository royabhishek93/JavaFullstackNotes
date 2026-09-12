# Interview Guide: SQL vs NoSQL

## 🗣️ The Interview Scenario

> "We're building two things in this system: a wallet ledger that records money movement between users, and a real-time analytics feed ingesting millions of IoT sensor readings per minute. Which database would you pick for each, and — this is the part most candidates get wrong — justify it with more than 'it depends.' What specifically about each workload drives the choice?"

The interviewer is explicitly warning you here: saying "we could use either" or picking one without reasoning is treated as a **red flag answer**, not a neutral one.

## 🏗️ Architect's Explanation (For a New Developer)

Think of a **SQL database like a pre-printed ledger book** — before you write a single entry, you've already ruled the columns: "Name," "Roll Number," "Salary." Every row must conform to that structure, and every table can reference other tables through defined relationships (like a "Department" column pointing to a Departments table). This rigidity is a feature, not a bug: it's what lets the database *guarantee* your data stays internally consistent no matter how many people are writing to it at once.

A **NoSQL database is more like a filing cabinet where every folder can hold whatever shape of paper it wants** — one folder might have three fields, the next folder ten, and nobody had to agree on a shared template up front. This flexibility is exactly what lets you spread folders across many cabinets (servers) without needing them to coordinate tightly, which is why NoSQL systems scale horizontally so naturally.

The single most important mental model: **SQL trades flexibility for guaranteed correctness (ACID); NoSQL trades some correctness guarantees for flexibility, scale, and availability (BASE).** Almost every "which DB should I use" decision comes down to which side of that trade your specific workload cannot survive without.

## 📊 Visualize It

**The four-way comparison framework used to reason about both:**

```
              STRUCTURE          NATURE          SCALABILITY        PROPERTY
SQL       Tables/rows/cols   Concentrated on    Vertical (add    ACID (Atomicity,
          Predetermined      one server (data    RAM/CPU to one   Consistency,
          schema, relations  for one entity      big server)      Isolation,
          between tables     lives in one place)                  Durability)

NoSQL     4 types: Key-Value,  Distributed        Horizontal      BASE (Basically
          Document, Column-    (one entity's      (add more       Available, Soft
          wise, Graph          data can be split   commodity      state, Eventual
          No fixed schema      across nodes)       nodes)          consistency)
```

**A single logical record, SQL vs. NoSQL nature:**

```
SQL: one server holds ALL of Shreyansh's data              NoSQL: distributed across nodes
                                                            (no relational constraint)
   Server 1                                                  Node1: user record part A
   ┌─────────────┐                                           Node2: user record part B
   │ id | dept   │  <- Shreyansh's row lives                Node3: user record part C
   │ salary      │     entirely on ONE server
   │ address     │                                           Millions of records spread
   └─────────────┘                                           evenly for scale
```

## 🔧 Deep Dive: How It Actually Works

### The four-category comparison framework

**1. Structure**

- **SQL:** Structured Query Language, used to query/manage a **Relational Database Management System (RDBMS)**. Data lives in **tables** made of **rows and columns**, with **relations between tables** (parent/child, e.g., primary key / foreign key). Critically, SQL requires a **predetermined schema** — you must define column names, types, and lengths *before* you insert any data.
- **NoSQL:** No single table structure — instead, four distinct storage models:
  - **Key-Value DB** (e.g., DynamoDB): a key maps to an **opaque** value (string, integer, JSON — doesn't matter, the DB doesn't look inside it). You can only query by **key**, never by contents of the value. This restriction is exactly what makes it extremely fast.
  - **Document DB** (e.g., MongoDB): also key + value, but the value (JSON/XML) is **not opaque** — you *can* query on fields inside the document, not just the key. This is the key structural difference from Key-Value DBs.
  - **Column-wise DB** (e.g., Cassandra): each key maps to a **dynamic list of column-value pairs**. Different rows (keys) can have a completely different number/set of columns — one key might have 3 columns, another 2, with no shared schema requirement.
  - **Graph DB**: data modeled as **nodes and edges** representing relationships (e.g., "Shreyansh" —friend of→ "XYZ"). Used for social networks and recommendation engines. The key advantage over SQL's parent/child foreign-key relations: SQL has to do a **full table scan** to walk a relationship chain, while a graph DB follows the edge **directly** — much faster for relationship-heavy traversal.

**2. Nature**

- **SQL:** Data for a given entity is **concentrated**/less distributed — e.g., all of one employee's data (department, salary, address) typically lives together on **one server**. It's not standard practice to split a single row's columns across two different servers.
- **NoSQL:** **Distributed** by nature — e.g., out of 10 million user records, 2 million might live on one node and the rest spread across others, and this can be arranged easily. Explicitly called out as easier to distribute than SQL data.

**3. Scalability**

- **SQL:** Scales primarily **vertically** — bigger RAM, bigger storage, bigger single machine. Horizontal sharding (splitting rows or columns across servers) is technically possible but **not well supported** by SQL systems out of the box.
- **NoSQL:** Scales **horizontally** — as a table (e.g., a growing `users` table crossing a million rows) grows, new nodes are simply added and the data spreads across them.

**4. Property**

- **SQL → ACID:**
  - **A**tomicity, **C**onsistency, **I**solation, **D**urability.
  - The core purpose: guarantee **data integrity and full consistency** for every transaction — the rules a transaction must follow, and the guarantee that once it's done, the data is completely consistent.
- **NoSQL → BASE** (explicitly: "don't forget or don't use ACID, it follows BASE"):
  - **B**asically **A**vailable: because data is distributed and replicated, the system stays highly available — you rarely lose access to *some* copy of the data, even under failure.
  - **S**oft state: the data's state can change **even without direct user interaction** — because replicas continuously sync with each other (e.g., using vector clocks to figure out which copy is newest), a node can silently update its own copy just from syncing with peers.
  - **E**ventual consistency: a query might return **stale data**, but if you retry after some time, you'll eventually get the latest data once replicas finish syncing.

### When to use which — the decision checklist
1. **Flexible/complex query needs** (today it's a 3-table join, tomorrow the business needs a 5-table join) → **SQL**. NoSQL is explicitly called out as supporting only **basic, known-in-advance query patterns** — if you already know exactly which few columns you'll always search by, NoSQL is fine; if query needs will keep evolving, you need SQL's flexibility.
2. **Relational/hierarchical data** — heavy parent-child dependency chains → **SQL**. NoSQL data is generally not tightly interlinked in this way.
3. **Data integrity is non-negotiable** (you cannot lose or corrupt a single transaction — e.g., **financial institutions**) → **must use SQL**, because ACID is the only property set that guarantees this. NoSQL is explicitly framed as acceptable to lose/skew a transaction or two, because it's designed for **huge, constantly-changing** datasets where that's an acceptable trade-off.
4. **High availability + high performance, and the system can tolerate some inconsistency** → **NoSQL**. Its distributed nature means it's very hard to bring fully down, and its search/lookup performance is very high because data is spread across smaller, distributed nodes (directly tying back to the fast key-based lookups described under Key-Value stores).

## 🔥 Real Production Incident & Fix

**What broke:** A fast-growing fintech product initially built its **wallet balance ledger** on a NoSQL, multi-master, eventually-consistent database — chosen early on purely for its "high availability, easy horizontal scaling" reputation, without weighing the ACID requirement. During a brief network partition between two regions, two concurrent debit operations against the *same* wallet were each accepted locally by their own region (each region believed it had the authoritative, available copy), and the eventual-consistency sync later reconciled them in a way that silently **double-processed one withdrawal** — leaving a wallet with a negative balance that should have been rejected outright.

**How it was detected/diagnosed:** A nightly reconciliation batch job (comparing ledger totals against the sum of external payment gateway confirmations) flagged a mismatch. On-call pulled per-wallet transaction logs from both regions and found two writes to the same wallet balance field within the partition window, each locally "successful," with the eventual-consistency merge (last-write-wins by timestamp) simply overwriting rather than correctly summing/serializing the two debits.

**Root cause:** The team had implicitly relied on ACID-style guarantees (atomic, isolated transactions with immediate consistency) for a system that was, by design, only offering **BASE** guarantees — basically available and eventually consistent, with soft state. Money movement is exactly the kind of workload the framework calls out explicitly: *"if consistency is required... for example any kind of financial institution... you have to go with SQL."* NoSQL was the wrong property set for this specific table, even though it was the right fit for other parts of the same product (e.g., transaction history search, user activity feeds).

**The fix:** The wallet balance ledger itself was migrated to a **SQL database with proper ACID transactions** (single-writer-per-account semantics, serializable isolation for balance updates), while the NoSQL store was **kept** for read-heavy, denormalized views (transaction history search, spending analytics) where eventual consistency is perfectly acceptable. This is a deliberate polyglot-persistence split, not an "either/or" — using each database for the property it actually guarantees.

```
BEFORE: one NoSQL DB for everything          AFTER: split by required property

Wallet balance -> NoSQL (BASE)                Wallet balance -> SQL (ACID)
  -> partition -> double-debit -> negative      -> atomic, serialized writes
     balance bug                                -> no double-debit possible

Txn history/search -> NoSQL (BASE)  -- unchanged, this workload is fine on NoSQL
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Can you use SQL and NoSQL together in the same system?**
Yes — this is called polyglot persistence and is standard practice. You pick the database per workload based on which property (ACID vs BASE) that specific piece of data actually needs, rather than forcing one database to serve the whole system. A financial ledger might sit in SQL while a search/analytics feed built from the same product sits in NoSQL.

**Q2: What exactly is a "predetermined schema" and why does it matter operationally?**
It means you must define table structure — column names, types, lengths — before inserting any data, and any structural change later (adding/removing a column) is a migration that must be planned and executed carefully. NoSQL's lack of a fixed schema means different records can have different shapes with no migration step required, which is why NoSQL is more forgiving of evolving/unpredictable data shapes.

**Q3: What's the concrete difference between a Key-Value DB and a Document DB?**
Both map a key to a value, and both can technically store JSON. The difference is **queryability**: in a Key-Value store, the value is opaque — you can only look things up by key. In a Document DB, the database understands the structure of the value (JSON/XML) well enough to let you query and filter on fields *inside* that value, not just the key.

**Q4: Why is a Graph DB faster than SQL for relationship-heavy queries like "friends of friends"?**
SQL models relationships via primary/foreign keys, but traversing a relationship chain requires scanning rows to find matches — effectively a full scan pattern for each hop. A Graph DB stores the relationship itself as a direct edge between nodes, so following a connection is a direct pointer traversal rather than a search, making it dramatically faster for deep relationship queries like social graphs or recommendations.

**Q5: What does "eventual consistency" mean in practice, and how would you design a shopping cart around it?**
It means a read immediately after a write might return stale data, but repeated reads will converge to the latest value once replicas sync. For a shopping cart, this is usually acceptable — briefly seeing a slightly stale cart state is a minor UX issue — but checkout/payment steps should not rely on eventual consistency; they need the immediate-consistency guarantees of an ACID system instead.

**Q6: Give a concrete example of the vertical vs. horizontal scaling trade-off.**
Vertical scaling (SQL's default path) means upgrading to bigger RAM/CPU/storage on the same machine — simpler to reason about (no distributed coordination), but has a hard ceiling and the machine remains a single point of failure. Horizontal scaling (NoSQL's default path) means adding more commodity nodes as data grows — no practical ceiling and no single point of failure, but you take on distributed-systems complexity (partitioning, replication, eventual consistency) in exchange.

## 🔑 Key Takeaway

Say this out loud in the interview: **"I pick SQL when data integrity/consistency is non-negotiable and queries will keep evolving; I pick NoSQL when I need horizontal scale and high availability and can tolerate eventual consistency — and for a real system, I often use both, one per workload, rather than forcing a single database to do everything."**
