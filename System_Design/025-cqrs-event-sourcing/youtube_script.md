# CQRS and Event Sourcing — YouTube Script
Duration: ~10 min | Target: Engineers 3–10 YOE | Episode: 25 of 29

## HOOK (0:00–0:30)

Here's a number that should terrify you: in 2019, a major payment processor lost **forty-three million dollars** worth of audit trail because someone ran an UPDATE statement on their transaction ledger. The regulator asked, "show me every change to account X in January," and they couldn't. The database only stored current balances — history was gone.

[Screen cue: Breaking news headline "Payment Processor Fined $43M for Audit Trail Failure" with database icon showing UPDATE statement crossing out historical records]

Now imagine you're building a payment system. Would you UPDATE rows? Or would you do what every serious financial system does — never UPDATE anything, ever? That's what we're covering today: CQRS and Event Sourcing, the patterns that power the world's most reliable systems.

## THE PROBLEM (0:30–2:00)

Let me paint you a picture. You're building an e-commerce platform. Black Friday hits. You've got a hundred thousand users placing orders, and another million users checking their order status. Both hitting the same PostgreSQL database. The write queries — inserting orders with inventory checks and payment validation — they need ACID guarantees, they need normalized tables, they need JOINs across orders, order items, and products.

But the read queries? They're just simple lookups: "show me my order history." They don't need JOINs. They don't need transactions. They just need to be FAST.

[Screen cue: Diagram showing PostgreSQL server being hammered from both sides — left side showing "INSERT orders + validate stock + charge payment" and right side showing "SELECT my order history" — both competing for the same database resources]

Here's the problem: your write operations and read operations have completely different requirements, but they're fighting for the same database resources. Writes slow down because readers are holding locks. Reads slow down because writers are holding locks. And when you try to scale, you can't — because they're coupled together.

Second problem: someone asks you, "what was the price of product X when I ordered it three months ago?" You look at your database. The product table shows current price: ninety-nine dollars. But was that the price in January? You have no idea. You UPDATE the price every time it changes. History is gone.

That's the problem CQRS and Event Sourcing solve. Think about it this way: what if write operations and read operations lived in completely separate worlds, optimized for their own jobs? And what if instead of storing "what things are now," you stored "what happened" — a complete, immutable history?

## THE SOLUTION (2:00–5:00)

Let's start with CQRS — Command Query Responsibility Segregation. Picture a bank with two counters. Counter A is the teller window: you walk up, hand over cash, a transaction happens. That's the write side. Counter B is the customer service desk: you ask "what's my balance?" They look it up from a pre-calculated summary. That's the read side.

These counters don't share the same queue. The customer service desk has its own snapshot of every account balance — a denormalized summary optimized purely for answering questions fast. The teller counter handles the actual work — validates transactions, applies business rules, updates authoritative records.

[Screen cue: Draw split architecture diagram — left side "WRITE SIDE" with PostgreSQL showing normalized tables (orders, order_items, products), right side "READ SIDE" with Elasticsearch showing single denormalized document (order_view with all fields pre-joined). Arrow in the middle labeled "Kafka: order-events" flowing from write to read]

Now watch what happens when a user places an order. The request hits your write side. It validates stock, charges payment, applies business rules, stores the order in PostgreSQL with full ACID guarantees. Then it publishes an event to Kafka: "OrderPlaced." That takes five milliseconds.

The user gets an HTTP 200 response: "Order placed successfully."

Meanwhile, asynchronously, a Kafka consumer picks up that OrderPlaced event, processes it — takes about a hundred milliseconds — and updates your read model in Elasticsearch at T plus one-ten milliseconds. That read model is a single denormalized document: order ID, product name, price, status, user name, delivery address — everything pre-joined. No JOINs needed at query time.

Now when another user queries their order history, it's a single document lookup in Elasticsearch. Five milliseconds. No locks. No JOINs. Write side and read side scale independently.

[Screen cue: Timeline showing T+0ms: user clicks button, T+5ms: write complete + event published, T+105ms: Kafka consumer processes event, T+110ms: read model updated]

That's CQRS. Now let's add Event Sourcing — a different concept, often used together but independent.

Instead of storing "order forty-two status equals SHIPPED," imagine storing every event that happened to order forty-two:
- Event one: OrderPlaced, user forty-two ordered two blue shoes at ninety-nine dollars each, total one ninety-eight, January fifteenth.
- Event two: PaymentCharged, amount one ninety-eight, transaction ID TXN underscore XYZ.
- Event three: OrderShipped, carrier UPS, tracking number one-Z-nine-nine-nine.
- Event four: OrderDelivered, delivered at January eighteenth.

[Screen cue: Show event_store table with seq column (1, 2, 3, 4), event_type column (OrderPlaced, PaymentCharged, OrderShipped, OrderDelivered), and payload column showing JSON for each event]

Current state is DERIVED by replaying those events. Want to know "what was the price when I ordered it?" Event one, priceAtTime: ninety-nine. "When was it shipped?" Event three, timestamp. Every question is answered by the immutable log.

Here's the power move: one event stream, multiple projections. That same Kafka topic "order-events" feeds:
- Consumer A: updates the orders database for ops dashboard.
- Consumer B: updates the user profile database for order history.
- Consumer C: pushes to the analytics warehouse for revenue metrics.
- Consumer D: feeds fraud detection for pattern analysis.

[Screen cue: Show Kafka topic "order-events" at center with four arrows pointing to four different databases — each labeled with its purpose]

One source of truth, four different read models, each optimized for different queries.

Now here's the optimization you need to know. Order forty-two has been active since 2019. It has two thousand events. Replaying two thousand events on every read would be insane. Solution: snapshots. After every hundred events, you save a snapshot of the current state. When you need to rebuild state, you load the latest snapshot — that's seq one thousand one hundred — then replay only events one thousand one-oh-one to current. At most a hundred events, not two thousand.

[Screen cue: Show snapshot_store table with orderId=42, seq_number=1100, state_snapshot showing status DELIVERED, total 198, then arrow showing "replay only 0-100 events from here"]

## DEEP DIVE — WHERE ENGINEERS GET IT WRONG (5:00–8:00)

Trap number one: eventual consistency lag. Remember that timeline? Write completes at T plus five milliseconds. Read model updates at T plus one-ten milliseconds. The user submits an order, you return HTTP 200 "Order placed!" They immediately refresh the page to see their orders. At T plus ten milliseconds, they query the read model. The order isn't there yet. The read model hasn't been updated. They think it failed. They place the order again. Now you have a duplicate order problem.

[Screen cue: Show state machine diagram — user at T+5ms sees "success", at T+10ms queries orders and sees empty list, thinks it failed, clicks "Place Order" again]

Four solutions. Solution one: optimistic UI. When the user clicks "Place Order," show it in the UI immediately from the command response. Don't wait for the read model. Browser-side state management handles it. Solution two: read-your-writes consistency. After a write, route that specific user's next read to the WRITE side PostgreSQL for the next five hundred milliseconds. By then, the read model has caught up. Solution three: event-driven UI. Use Server-Sent Events or WebSocket to push an "OrderConfirmed" event to the browser when the read model updates. The browser updates the UI then, not before. Solution four: accept it. For most operations, a hundred milliseconds of eventual consistency is fine. Show a "Your order is being confirmed..." spinner for one to two seconds. Acceptable UX.

Trap number two: complexity cost. CQRS plus Event Sourcing is not free. You need a framework — Axon in Java, Eventide in Ruby, EventFlow in .NET. Your team needs expertise in event-driven architecture. You're maintaining two data models, not one. Schema evolution gets harder: you can't just ALTER TABLE. You need to handle event versioning — what happens when you add a new field to OrderPlaced version two, but old events are version one?

[Screen cue: Comparison table — left column "Traditional CRUD", right column "CQRS+ES". Rows showing: Code complexity (1x vs 3x), Team expertise needed (junior-friendly vs senior-level), Schema changes (ALTER TABLE vs event upcasting), Infrastructure (1 DB vs 2 DBs + message broker)]

Trap number three: when NOT to use it. If you're building a simple CRUD app with less than a hundred thousand records, total, CQRS is overkill. The overhead of managing eventual consistency, two data stores, Kafka infrastructure — it's not justified. Use plain MVC with an ORM. CQRS shines when your read-to-write ratio is greater than ten-to-one AND you have different scaling needs. Event Sourcing shines when audit trail or time-travel queries are actual requirements, not nice-to-haves.

Trap number four: event store choice matters. Most engineers reach for Kafka because it's familiar. Kafka is great for event streaming, but it's not designed for per-aggregate event lookup. You can't efficiently query "get all events for orderId equals forty-two" in Kafka. You have to consume the entire partition. Better pattern: use Kafka for event streaming between services, AND use PostgreSQL as the event store for per-aggregate queries. Create an events table with aggregate_id, event_type, payload JSONB, version, created_at. Index on aggregate_id and version. The UNIQUE constraint on aggregate_id plus version gives you optimistic concurrency control for free. If two processes try to append version four simultaneously, one fails with a unique violation.

[Screen cue: Show two architectures side-by-side — "Kafka alone" showing full partition scan, vs "Kafka + Postgres events table" showing direct aggregate query with index seek]

Axon Framework, in Java, gives you the annotations to build this cleanly: `@Aggregate` marks the write-side domain object, `@CommandHandler` handles incoming commands and validates business rules before applying an event, `@EventSourcingHandler` gets called during state replay to rebuild the aggregate from its events, and `@EventHandler` on the read side updates the query projections. That separation — command validation on the write side, projection updates on the read side — is the whole pattern in code form.

## REAL WORLD (8:00–9:30)

Let's talk real numbers from Indian tech companies.

PhonePe processes fifteen crore UPI transactions per day. Their payment ledger is pure Event Sourcing. Every debit, every credit, stored as an immutable event. Current balance is derived. Why? RBI regulatory compliance. The regulator can audit complete history going back years. They can't delete records — it's illegal. Their read model for balance inquiries is Redis, updated within fifty milliseconds of each event. Writes go to PostgreSQL event store, five milliseconds per transaction. Reads hit Redis, sub-millisecond latency. They scale independently: Black Friday payment writes don't compete with balance inquiry reads.

[Screen cue: PhonePe logo. Numbers: "15 crore txns/day, 5ms write (Postgres events), 50ms read model sync, <1ms balance query (Redis)"]

Swiggy's order system is CQRS without full Event Sourcing. Write side: PostgreSQL with inventory validation, restaurant confirmation, delivery assignment. Normalized tables, ACID guarantees. Read side: Elasticsearch for order history search, Redis for "current active orders" real-time updates. Each order write publishes an event. Kafka consumers update both Elasticsearch and Redis. During lunch hour peak — one lakh orders per minute — the write database and read database scale separately. Read queries don't lock the write path.

[Screen cue: Swiggy logo. Numbers: "1 lakh orders/min peak, Write: PostgreSQL (normalized), Read: ES (search) + Redis (active orders), 100ms sync lag"]

Zerodha, India's largest stock broker, uses Event Sourcing for regulatory compliance. Every order placed, executed, canceled — immutable events stored for seven years minimum. SEBI regulations mandate complete audit trails. Their trade book, P&L dashboard, tax lot accounting — each is a different projection of the same event stream. When a user disputes a trade, they replay events from the event store filtered by timestamp and account ID. Complete audit trail, legally defensible.

[Screen cue: Zerodha logo. Numbers: "7-year event retention, SEBI-compliant audit trail, Event store: Postgres (partitioned by year), Read models: Redis (live positions) + Druid (analytics)"]

## OUTRO + NEXT EPISODE (9:30–10:00)

So here's the decision framework. If you hear "audit trail," "regulatory compliance," "transaction history" in an interview — Event Sourcing. If you hear "read at scale," "complex queries," "dashboard performance" — CQRS. They're independent patterns. Use one, use both, or use neither based on actual requirements.

Remember the architect's one-liner: "Event Sourcing treats the database as an append-only ledger of what happened — never what 'currently is' — which gives you a complete audit trail, time-travel queries, and the ability to rebuild any read model from scratch; CQRS then separates who writes to that ledger from who reads from its projections, letting each side scale and evolve independently."

If this pattern clicked for you, hit subscribe. Next episode — Episode twenty-six — we're diving into Authentication and Authorization Security: how Swiggy prevents account takeovers, how OAuth two really works under the hood, and the zero-trust architecture pattern you'll be asked about in senior-level interviews. See you there.

[Screen cue: Subscribe button animation. Text: "Next → Ep 26: AuthN/AuthZ Security"]
