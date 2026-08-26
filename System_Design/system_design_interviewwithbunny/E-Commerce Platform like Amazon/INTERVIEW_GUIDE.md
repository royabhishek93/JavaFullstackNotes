# E-Commerce Platform (Amazon / Flipkart) — Interview Script
## Design Real Examples: Amazon, Flipkart, Myntra, Meesho
### Speak This Word-for-Word to Your Interviewer

> How to use this: Read PAGE 1 and PAGE 2 tonight — understand the inventory consistency model cold.
> This system is unique: the interview is 40% design, 60% proving you understand the checkout flow.
> Every follow-up question will be about overselling, race conditions, and payment failure handling.

---

# ═══════════════ PAGE 1 — START HERE ═══════════════

## BIG PICTURE (Understand This Before Anything Else)

> **► STUDY this diagram, don't draw it ◄**
> An e-commerce platform is not a simple CRUD app. The hardest problem is inventory consistency:
> preventing overselling when 10,000 users simultaneously try to buy the last item.
> The checkout flow is a distributed state machine — any failure between inventory reservation
> and payment confirmation must not leave inventory permanently locked.

```
  CLIENT LAYER                          SERVICE LAYER                        DATA LAYER
  ────────────                          ─────────────                        ──────────

  Mobile / Web
    │
    │ HTTPS requests
    ▼
  ┌────────────────────────────────┐
  │          API Gateway           │
  │  Authentication, Rate Limiting │
  │  Routing to microservices      │
  └───────┬────────────────────────┘
          │
    ┌─────┴──────────────────────────────────────────────┐
    │                                                    │
    ▼                                                    ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
  │  User Svc    │  │  Search Svc  │  │  Product Svc │  │  Cart Svc        │
  │              │  │              │  │              │  │                  │
  │ User DB      │  │ Elasticsearch│  │ MongoDB      │  │ Cart DB          │
  │ (MySQL)      │  │ + Redis cache│  │ (DocumentDB) │  │ (PostgreSQL)     │
  └──────────────┘  └──────┬───────┘  └──────┬───────┘  └──────────────────┘
                           │    CDC           │ CDC
                           │◄─────────────────┘
                           │   (MongoDB oplog → Kafka → ES indexer)
                           │
    ┌──────────────────────┴──────────────────────────────────────────┐
    │                           Kafka                                 │
    │  Topics: product.updated | order.created | payment.success      │
    │          inventory.updated | order.shipped                      │
    └──────┬───────────────┬──────────────────┬────────────────┬──────┘
           │               │                  │                │
           ▼               ▼                  ▼                ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │ Inventory    │  │ Order Status │  │  Payment Svc │  │ Notification │
  │ Svc          │  │ Svc          │  │              │  │ System       │
  │              │  │              │  │ Payment GW   │  │              │
  │ Inventory DB │  │ Order DB     │  │ (Stripe)     │  │ Email/SMS    │
  │ (PostgreSQL) │  │ (MySQL)      │  │ Payment DB   │  │ /Push        │
  │ Qty-source   │  │              │  │              │  │              │
  │ of truth     │  │              │  │              │  │              │
  └──────┬───────┘  └──────────────┘  └──────────────┘  └──────────────┘
         │
         │ CDC → Redis cache invalidation
         ▼
  ┌───────────────────────────────────────────────────────┐
  │  Redis                                                │
  │  cart:{userId}           TTL 7d                       │
  │  product:{productId}     TTL 30min                    │
  │  search:{hash(query)}    TTL 10min                    │
  │  inventory:{productId}   TTL 5min                     │
  │  lock:inventory:{pid}    TTL 30sec (distributed lock) │
  └───────────────────────────────────────────────────────┘
```

```
  CHECKOUT FLOW (THE CRITICAL PATH — memorise this)
  ──────────────────────────────────────────────────

  POST /v1/checkout
       │
       ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Checkout Service (orchestrator)                                    │
  │                                                                     │
  │  1. Fetch cart items from Cart DB                                   │
  │                                                                     │
  │  2. FOR EACH product in cart:                                       │
  │     SETNX lock:inventory:{product_id} {session_id} EX 30           │
  │     If 0 → another checkout in progress → abort, return 409        │
  │                                                                     │
  │  3. FOR EACH product (with DB lock):                                │
  │     SELECT qty, reserved_qty FROM inventory                         │
  │     WHERE product_id=? FOR UPDATE                                   │
  │     If qty < cart_qty → release all locks → return 'Out of stock'   │
  │                                                                     │
  │  4. Reserve: UPDATE inventory                                       │
  │     SET reserved_qty = reserved_qty + cart_qty                      │
  │     (stock removed from pool but NOT deducted yet)                  │
  │                                                                     │
  │  5. BEGIN TRANSACTION:                                              │
  │     INSERT orders (status='PENDING_PAYMENT')                        │
  │     COMMIT                                                          │
  │                                                                     │
  │  6. Release Redis locks: DEL lock:inventory:{product_id} (each)     │
  │                                                                     │
  │  7. Create payment intent → return {order_id, payment_url}          │
  └─────────────────────────────────────────────────────────────────────┘
       │
       │ User completes payment at Payment Gateway
       ▼
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Payment Webhook: POST /webhooks/payment                            │
  │                                                                     │
  │  1. Validate signature (HMAC)                                       │
  │  2. Idempotency: SELECT * FROM payments WHERE order_id=?            │
  │     If exists → return 200 (already processed)                      │
  │  3. BEGIN TRANSACTION SERIALIZABLE:                                 │
  │     INSERT payments (status='SUCCESS')                              │
  │     UPDATE orders SET status='PAYMENT_CONFIRMED'                    │
  │     UPDATE inventory SET qty = qty - cart_qty,                      │
  │                          reserved_qty = reserved_qty - cart_qty     │
  │     DELETE FROM cart_items WHERE cart_id=?                          │
  │     COMMIT                                                          │
  │  4. Publish Kafka: payment.success, order.confirmed                 │
  └─────────────────────────────────────────────────────────────────────┘
```

---

## RAPID ANSWER — If You Only Have 5 Minutes

*Read this first. Understand the whole answer before going deep.*

```
"I'd design this e-commerce platform around five core problems:

1. Product Search (Elasticsearch + CDC):
   Products live in MongoDB for flexible schema (mobiles have different attributes
   than books). A CDC pipeline — MongoDB oplog → Kafka → ES indexer — keeps search
   fresh within 1-2 seconds. Redis caches top 10K queries with 10-min TTL.
   Result: 100K searches/sec during peak sales events.

2. Cart Management (PostgreSQL + Redis):
   Cart tied to user_id (not session) for cross-device sync. PostgreSQL is source
   of truth (ACID, survives cache eviction). Redis caches HSET cart:{userId} with
   7-day TTL for <1ms reads. ON CONFLICT upsert handles concurrent add-to-cart.

3. Inventory Consistency (THE hard problem):
   Two-layer lock to prevent overselling:
   Layer 1: Redis SETNX lock:inventory:{product_id} — fast rejection of concurrent
   checkouts (1-2ms, prevents thundering herd).
   Layer 2: PostgreSQL SELECT FOR UPDATE — ACID row lock while reading/reserving.
   reserved_qty column holds stock during the checkout→payment window.
   Actual qty deduction happens ONLY after payment.success webhook.
   Redis lock auto-expires in 30s — prevents deadlock if service crashes.

4. Payment (Idempotency + Webhooks):
   order_id as idempotency_key to Stripe. UNIQUE constraint on payments(order_id)
   prevents double-charge. Webhook signature validation prevents forgery.
   Idempotency check (SELECT before INSERT) prevents duplicate processing on replay.

5. Event-Driven Architecture (Kafka):
   Decouples all post-payment work. order.confirmed → Warehouse picks items.
   payment.success → Inventory deducted, cache invalidated, email sent.
   Kafka retention 7 days enables replay. Dead-letter queue for failed consumers."
```

---

# ═══════════════ PAGE 2 — GLOSSARY ═══════════════

## Terminology — Know These Before Reading Further

```
┌───────────────────────────────┬──────────────────────────────────────────────────────────────┐
│ Term                          │ What It Means (Simply)                                       │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ CDC (Change Data Capture)     │ Listening to a DB's write-ahead log (oplog/WAL) to stream    │
│                               │ every insert/update/delete to downstream consumers           │
│                               │ (Elasticsearch, Redis) without the app knowing about them.  │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ SETNX                         │ Redis "SET if Not eXists" — atomic check+set. Returns 1 if   │
│                               │ key was set (you got the lock), 0 if key existed (locked).   │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Distributed Lock              │ A Redis SETNX key with expiry. Ensures only one process      │
│                               │ executes a critical section at a time across multiple        │
│                               │ service instances. Auto-expiry prevents deadlocks.           │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ reserved_qty                  │ A column in inventory that marks stock as "in checkout" but  │
│                               │ not yet paid for. Prevents showing items as available when   │
│                               │ they're locked in active checkout sessions.                  │
│                               │ available = qty - reserved_qty                               │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ SELECT FOR UPDATE             │ PostgreSQL pessimistic row lock. Blocks other transactions   │
│                               │ from modifying this row until current transaction commits.   │
│                               │ Used inside checkout to prevent two users reserving same     │
│                               │ inventory simultaneously.                                   │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Idempotency Key               │ A unique identifier (order_id) sent to Payment Gateway.      │
│                               │ If the same key is sent twice, gateway returns the original  │
│                               │ result without charging again. Critical for safe retries.    │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Payment Webhook               │ HTTP callback that Payment Gateway sends to your backend     │
│                               │ when payment status changes. Must be idempotent — gateway   │
│                               │ retries webhooks on timeout. Your handler must deduplicate.  │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Elasticsearch (ES)            │ Distributed search engine built on Lucene. Supports full-    │
│                               │ text search, filters, aggregations, fuzzy matching,          │
│                               │ autocomplete. Far more capable than PostgreSQL tsvector.     │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Faceted Search                │ Search with filter counts: "Electronics (5000), Books (3000)"│
│                               │ Powered by ES aggregations. Allows users to narrow results   │
│                               │ by category, price range, brand, rating simultaneously.      │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Eventual Consistency          │ Data will be consistent across replicas/caches eventually    │
│                               │ (1-5 seconds), not immediately. Acceptable for search        │
│                               │ and caching. NEVER acceptable for inventory or payments.     │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ SKIP LOCKED                   │ PostgreSQL feature: if row is locked by another transaction, │
│                               │ skip it and try next available row. Eliminates contention    │
│                               │ in queue-based processing (flash sales checkout queue).      │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Consumer Group (Kafka)        │ Multiple instances of one service sharing a Kafka topic.     │
│                               │ Each partition is consumed by exactly one member of group.   │
│                               │ Enables horizontal scaling and at-least-once delivery.       │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Dead Letter Queue (DLQ)       │ Kafka topic where failed events land after N retries.        │
│                               │ Prevents one bad event from blocking entire consumer.        │
│                               │ Ops team investigates and replays manually.                  │
├───────────────────────────────┼──────────────────────────────────────────────────────────────┤
│ Thundering Herd               │ 100K users all hit checkout at flash sale start simultaneously│
│                               │ overwhelming DB with lock contention. Solved by Redis lock   │
│                               │ as fast early rejection before DB is involved.               │
└───────────────────────────────┴──────────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 3 — WHY EACH COMPONENT ═══════════════

## Component Choices — Why We Picked Each One

```
┌──────────────────────────┬───────────────────────────────────────────────────────────────────┐
│ COMPONENT                │ WHY THIS? NOT SOMETHING ELSE?                                     │
├──────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ MongoDB for              │ WHY: Different product categories have completely different        │
│ Product catalog          │ attributes. Mobile phones have {RAM, storage, processor}.         │
│                          │ Books have {author, ISBN, publisher}. Clothing has {size, color,  │
│                          │ material}. MongoDB's flexible schema handles all these without     │
│                          │ sparse NULL columns or EAV anti-pattern.                          │
│                          │ WHY NOT PostgreSQL: Would require either 1 massive table with     │
│                          │ 200+ nullable columns (sparse, wasteful), or EAV pattern          │
│                          │ (product_attributes table) requiring joins for every query.       │
│                          │ Adding new product category requires ALTER TABLE. MongoDB:        │
│                          │ just insert a document with new fields.                           │
├──────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ Elasticsearch for        │ WHY: Full-text search with relevance scoring (title^3 boosts),    │
│ Product Search           │ fuzzy matching, synonyms (laptop=notebook), faceted aggregations  │
│                          │ (filter counts per brand/category/price-range), autocomplete via  │
│                          │ edge n-gram tokenizer. Handles 100K queries/sec on 100M products. │
│                          │ WHY NOT PostgreSQL full-text: tsvector lacks relevance scoring,   │
│                          │ no synonyms, no faceted aggregations, can't handle 100K QPS        │
│                          │ without massive vertical scaling. ES cluster scales horizontally. │
│                          │ WHY NOT MongoDB search: Mongo Atlas Search is good but ES has     │
│                          │ richer query DSL and better performance at this scale.            │
├──────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ PostgreSQL for           │ WHY: Inventory requires ACID transactions with row-level          │
│ Inventory DB             │ locking (SELECT FOR UPDATE). reserved_qty pattern needs atomic    │
│                          │ read-modify-write. Strong consistency is mandatory — overselling  │
│                          │ items is a business disaster. PostgreSQL MVCC handles concurrent  │
│                          │ checkout sessions without full table locks.                       │
│                          │ WHY NOT Redis for inventory: Redis is fast but not durable enough │
│                          │ as source of truth. A Redis crash loses all reservation state.   │
│                          │ Redis is used ONLY as a cache layer, not source of truth.        │
├──────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ Redis Distributed        │ WHY: SETNX is O(1), executes in <1ms. During checkout, before    │
│ Lock (SETNX)             │ hitting the DB, we try to acquire this lock. If 10K users hit    │
│                          │ checkout simultaneously, only 1 succeeds per product — the other  │
│                          │ 9999 get rejected immediately by Redis without ever touching the  │
│                          │ DB. This prevents thundering herd on PostgreSQL.                 │
│                          │ EX 30 (30s expiry): If service crashes mid-checkout, lock auto-  │
│                          │ releases after 30s. Prevents permanent inventory lock.           │
│                          │ WHY NOT only PostgreSQL lock: SELECT FOR UPDATE holds row lock   │
│                          │ for entire checkout duration (~500ms). At 10K concurrent users,  │
│                          │ this causes massive lock contention and DB connection exhaustion. │
├──────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ PostgreSQL for           │ WHY: Cart requires ACID guarantees. ON CONFLICT upsert handles   │
│ Cart DB                  │ concurrent add-to-cart (same user, multiple devices). Relational  │
│                          │ FK constraint (cart → items) ensures data integrity. Cross-device │
│                          │ sync works because cart is tied to user_id, not session.         │
│                          │ WHY NOT Redis only: Redis evicts under memory pressure. User      │
│                          │ loses their cart silently. PostgreSQL is the durable source of   │
│                          │ truth. Redis is the fast read cache on top.                      │
├──────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ MySQL for                │ WHY: ACID transactions for order lifecycle. Order status must      │
│ Order DB                 │ never be partially written. Relational integrity (order → items  │
│                          │ → payment) enables complex reporting queries. Schema is fixed     │
│                          │ (orders always have the same structure — unlike products).        │
│                          │ Partitioned by month for query performance on historical orders.  │
├──────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ Kafka for                │ WHY: Decouples services. Payment Service doesn't need to know     │
│ Event Streaming          │ about Notification, Warehouse, or Analytics. Each service         │
│                          │ consumes independently, scales independently, fails independently.│
│                          │ Event replay: Can rebuild Elasticsearch index from product.updated│
│                          │ topic if ES cluster corrupts. 7-day retention = audit trail.     │
│                          │ WHY NOT direct service calls: Synchronous call chain means        │
│                          │ Checkout waits for Notification to send email before returning.  │
│                          │ One slow downstream service blocks the entire checkout flow.     │
├──────────────────────────┼───────────────────────────────────────────────────────────────────┤
│ CDC for                  │ WHY: Product Service doesn't need to know about Elasticsearch.   │
│ Search Sync              │ MongoDB oplog captures every change automatically. ES indexer    │
│                          │ consumes from Kafka, can fall behind and catch up without         │
│                          │ affecting Product writes. Supports multiple consumers (ES,        │
│                          │ Redis cache, analytics) from one CDC event stream.               │
│                          │ WHY NOT dual-writes: Product Service would need to write to both │
│                          │ MongoDB AND ES in the same request. If ES write fails, data is   │
│                          │ inconsistent with no recovery path. Tight coupling.              │
└──────────────────────────┴───────────────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 4 — FULL INTERVIEW SCRIPT ═══════════════

---

## OPENING — When Interviewer Says "Design an E-Commerce Platform like Amazon"

"The core challenge here is inventory consistency — preventing overselling when thousands of users
simultaneously attempt to buy the last item in stock. Unlike most systems where eventual consistency
is fine, the checkout flow requires strong consistency: we cannot let two users both successfully
purchase the same last unit. Every design decision I make in the checkout path will be driven by
'what happens if this step fails — does inventory stay permanently locked?'

Let me clarify requirements first."

---

## STEP 1 — Requirements Gathering

```
┌────────────────────────────────────────────┬──────────────────────────────────────────────┐
│ YOU ASK                                    │ INTERVIEWER SAYS (typical)                   │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Is this the full Amazon platform or a      │ Core flow: search, add to cart, checkout,    │
│ specific subsystem?                        │ payment, order tracking.                     │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ What's the scale?                          │ 10M MAU, 10 orders/sec, 100K product         │
│                                            │ searches/sec during peak (sales events).     │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Do we need to handle flash sales with      │ Yes — limited stock items, concurrent users. │
│ very limited inventory?                    │ Overselling is unacceptable.                 │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Multi-seller or single seller?             │ Multiple sellers, but we own inventory       │
│                                            │ management (like Amazon Fulfilled by Amazon). │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ What consistency trade-offs are okay?      │ Search and product views: eventual okay.     │
│                                            │ Checkout, inventory, payments: strong.       │
├────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ Do we need real-time order tracking?       │ Yes — user should see status updates within  │
│                                            │ seconds of state change.                     │
└────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

```
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ REQUIREMENTS SUMMARY                                                                      │
├──────────────────────────────────────────┬────────────────────────────────────────────────┤
│ FUNCTIONAL                               │ NON-FUNCTIONAL                                 │
├──────────────────────────────────────────┼────────────────────────────────────────────────┤
│ 1. Search products by name, category,    │ Scale: 10M MAU, 10 orders/sec normal           │
│    price filters, ratings                │   100 orders/sec peak (flash sales)            │
│ 2. View product details + images         │ 100K search queries/sec during sales events    │
│ 3. Add items to cart                     │ Products: 100M+ in catalog                    │
│ 4. Checkout + payment                    │ Latency: Search <500ms, product page <200ms   │
│ 5. Order status tracking                 │ Checkout <3s end-to-end                       │
│ 6. Manage limited-stock inventory        │ Consistency: STRONG for checkout/payment       │
│                                          │ EVENTUAL for search/cache (1-2s lag ok)       │
│                                          │ Availability: 99.99% for checkout              │
└──────────────────────────────────────────┴────────────────────────────────────────────────┘
```

Key insight: Volume at 10 orders/sec is NOT the challenge. The challenge is correctness under
concurrent access to the same limited-stock item.

---

## STEP 2 — Capacity Estimation

```
TRAFFIC:
  10M MAU → ~3.3M DAU (30% daily return rate)
  3.3M users × 5 searches/day = 16.5M searches/day = ~190 searches/sec avg
  Peak (10x avg during sales event) = ~1900 searches/sec → ES cluster handles this
  Search cache (Redis) handles 60-70% → actual ES queries ~600/sec normally

ORDER VOLUME:
  10 orders/sec = 864,000 orders/day ≈ 1M orders/day
  With 2% conversion: 50M product views/day → ~580 views/sec

STORAGE:
  Products: 100M × 5 KB = 500 GB (MongoDB)
  Product images: 100M × 5 images × 1 MB = 500 TB (S3 + CloudFront CDN)
  Orders: 1M/day × 2 KB × 365 days = 730 GB/year (partitioned monthly)
  Elasticsearch index: 100M products × 3 KB indexed fields = 300 GB, 10-node cluster
  Redis: Cart (10M users × 2KB = 20 GB) + Product cache + Search cache ≈ 50 GB total

INVENTORY LOCKS:
  10 orders/sec × avg 3 items/order = 30 lock acquisitions/sec
  Peak: 100 orders/sec × 3 = 300 lock acquisitions/sec
  → Redis SETNX handles 100K operations/sec. Trivial.

DB CONNECTIONS:
  200 connections per API server × 10 Checkout Service instances = 2000 connections
  PostgreSQL max_connections = 5000 → connection pooling (PgBouncer) essential
```

---

## STEP 3 — Core Entities

```
┌──────────────────────┬──────────────────────────────────────────────────────────────────────┐
│ Entity               │ Key Fields                                                           │
├──────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ User                 │ user_id (uuid PK), name, email, password (bcrypt),                  │
│ (MySQL)              │ address[] JSON [{street, city, state, zip, country, is_default}]     │
├──────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Product              │ product_id (string PK), title, category, price (float), qty (int),  │
│ (MongoDB)            │ currency, description, images[] (S3 URLs),                           │
│                      │ specifications: {} — FLEXIBLE (RAM/storage for phones,               │
│                      │ author/ISBN for books, size/color for clothing)                      │
├──────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Cart                 │ cart_id (uuid PK), user_id (FK)                                     │
│ (PostgreSQL)         │ cart_items: (cart_id, product_id) composite PK,                     │
│                      │ qty (int), price (decimal 10,2), currency                           │
├──────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Inventory            │ product_id (uuid PK, INDEXED), qty (int) — total warehouse stock,   │
│ (PostgreSQL)         │ reserved_qty (int) — in active checkouts, not yet paid,             │
│ — SOURCE OF TRUTH    │ warehouse_id (uuid), last_updated (timestamp)                       │
│                      │ available = qty - reserved_qty                                      │
├──────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Order                │ order_id (uuid PK), user_id (FK), items JSON [{product_id, qty,     │
│ (MySQL)              │ price, currency}], total (decimal 10,2), status ENUM                │
│                      │ (PENDING_PAYMENT|PAYMENT_CONFIRMED|PROCESSING|SHIPPED|DELIVERED     │
│                      │ |CANCELLED), payment_id, shipping_address JSON, created_at          │
├──────────────────────┼──────────────────────────────────────────────────────────────────────┤
│ Payment              │ payment_id (varchar PK — from gateway), order_id (uuid UNIQUE FK),  │
│ (MySQL)              │ amount (decimal 10,2), status ENUM (PENDING|SUCCESS|FAILED|REFUNDED)│
│                      │ timestamp. UNIQUE on order_id = idempotency guarantee               │
└──────────────────────┴──────────────────────────────────────────────────────────────────────┘
```

---

## STEP 4 — API Design

```
┌─────────────────────────────────────────┬───────────────────────────────────────────────────┐
│ ENDPOINT                                │ NOTES                                             │
├─────────────────────────────────────────┼───────────────────────────────────────────────────┤
│ GET /v1/product/search                  │ Query params: q={term}, category, priceMin,       │
│   ?q=laptop&category=electronics        │ priceMax, rating, sortBy, page, size              │
│   &priceMax=1000&sortBy=rating          │ Returns List<{product_id, title, price, qty,      │
│                                         │ image_url, rating}> with pagination               │
├─────────────────────────────────────────┼───────────────────────────────────────────────────┤
│ GET /v1/product/{productId}             │ Full product details from MongoDB + Redis cache   │
│                                         │ Returns product with specifications, all images   │
├─────────────────────────────────────────┼───────────────────────────────────────────────────┤
│ POST /v1/cart/add                       │ Body: {product_id, qty}                          │
│                                         │ Validates stock, upserts cart_items              │
│                                         │ Returns: {cart_id}                               │
├─────────────────────────────────────────┼───────────────────────────────────────────────────┤
│ GET /v1/cart/{userId}                   │ Redis first (HGETALL cart:{userId}), else DB      │
│                                         │ Returns enriched cart with current prices         │
├─────────────────────────────────────────┼───────────────────────────────────────────────────┤
│ POST /v1/checkout                       │ Body: {cart_id, shipping_address_id,             │
│                                         │   payment_method_id}                             │
│                                         │ Orchestrates: lock → validate → reserve →        │
│                                         │ create order → payment intent                    │
│                                         │ Returns: {order_id, payment_url, expires_at}     │
├─────────────────────────────────────────┼───────────────────────────────────────────────────┤
│ POST /v1/payment (webhook)              │ Internal — called by Payment Gateway              │
│                                         │ Validates signature, deduplicates, processes      │
├─────────────────────────────────────────┼───────────────────────────────────────────────────┤
│ GET /v1/status/{orderId}                │ Returns full order status with history            │
│                                         │ {status, tracking_id, estimated_delivery,        │
│                                         │  history: [{status, timestamp}]}                  │
└─────────────────────────────────────────┴───────────────────────────────────────────────────┘
```

---

## STEP 5 — High Level Design

"Let me draw the services and walk through the main flows."

*Describe the architecture diagram from Page 1.*

"Three zones of consistency:

Zone 1 — Strong consistency required (Checkout, Inventory, Payments):
  PostgreSQL with ACID transactions, Redis distributed locks, idempotent webhooks.

Zone 2 — Eventual consistency acceptable (Search, Product cache):
  Elasticsearch synced from MongoDB via CDC pipeline within 1-2 seconds.
  Redis caches search results, product details, inventory counts.

Zone 3 — Async / decoupled (Notifications, Analytics, Warehouse):
  All driven by Kafka events published after payment success.
  These services can be slow, fail, and retry — they don't block checkout."

---

## STEP 6 — Deep Dives

---

### DEEP DIVE 1: Product Search (Elasticsearch + CDC)

```
User: GET /v1/product/search?q=laptop&category=electronics&priceMax=1000&sortBy=rating
         │
         ▼
  Search Service
    1. key = hash(query + filters + sort)
    2. GET search:{key} from Redis → if HIT: return cached (10min TTL)
    3. IF MISS: query Elasticsearch:
         POST /products/_search
         {
           "query": {
             "bool": {
               "must": [
                 { "multi_match": {
                     "query": "laptop",
                     "fields": ["title^3", "description", "brand"]
                 }}
               ],
               "filter": [
                 { "term":  { "category": "electronics" }},
                 { "range": { "price":  { "lte": 1000 }}},
                 { "range": { "qty":    { "gt":  0    }}}
               ]
             }
           },
           "sort": [{ "rating": "desc" }],
           "aggs": {
             "brands":       { "terms": { "field": "brand" }},
             "price_ranges": { "range": { "field": "price",
               "ranges": [{"to":500},{"from":500,"to":1000},{"from":1000}]}}
           },
           "from": 0, "size": 20
         }
    4. Cache result in Redis: SET search:{key} {result} EX 600
    5. Return [{product_id, title, price, qty, image_url, rating}] + filter counts

  CDC SYNC PIPELINE (keeps ES fresh):
    MongoDB product update
      → oplog change stream (Kafka Connect MongoDB Source)
      → Kafka topic 'product.changes'
      → ES indexer consumer: es.index(id=product_id, body=fullDocument)
      → Lag: 1-2 seconds
      → If ES down: indexer catches up from Kafka offset on restart

  WHY title^3?
    Boosts title match 3x over description. "laptop" in title → higher score than
    "laptop" mentioned only in description.
```

**Say to interviewer:** *"I use CDC instead of dual-writes because Product Service should not know
about Elasticsearch. If ES is down, MongoDB still accepts writes. The indexer catches up when ES
comes back using Kafka offset replay."*

---

### DEEP DIVE 2: Cart Management (PostgreSQL + Redis)

```
ADD TO CART: POST /v1/cart/add { product_id: 'ABC', qty: 2 }
  1. Validate product exists (Product Service) and has qty > 0 (Inventory Service)
  2. PostgreSQL upsert:
       INSERT INTO cart_items (cart_id, product_id, qty, price, currency)
       VALUES (?, 'ABC', 2, 899.00, 'USD')
       ON CONFLICT (cart_id, product_id)
       DO UPDATE SET qty = cart_items.qty + 2, updated_at = now()
  3. Redis update:
       HSET cart:{userId} product:ABC '{"qty":2,"price":899,"currency":"USD"}'
       EXPIRE cart:{userId} 604800  (7 days)

GET CART: GET /v1/cart/{userId}
  1. HGETALL cart:{userId} → if HIT: return (< 1ms)
  2. If MISS: SELECT ci.*, p.title, p.image_url FROM cart_items ci
              JOIN products p USING(product_id)
              WHERE ci.cart_id = ?
     Then cache in Redis

CROSS-DEVICE SYNC:
  Cart keyed by user_id, not session_id.
  Login on mobile → same cart as desktop (loaded from PostgreSQL).

GUEST → LOGIN MIGRATION:
  Guest cart: Redis only, key = session_id, TTL = 24h
  On login: UPDATE cart_items SET cart_id={user_cart_id} WHERE cart_id={guest_cart_id}

PRICE CHANGE HANDLING:
  Cart stores price AT TIME OF ADDING. At checkout, re-validate vs current price.
  Show user: "Price changed from $899 to $799 — continue?" before confirming.

STOCK VALIDATION AT CHECKOUT:
  cart_items stores qty and price, NOT a guarantee of availability.
  Actual stock validation happens during checkout (SELECT qty FROM inventory FOR UPDATE).
```

---

### DEEP DIVE 3: Checkout — Inventory Lock (THE Critical Path)

```
This is the most important deep dive. Interviewers will probe every step.

PROBLEM: Product has qty=1. User A and User B click "Checkout" simultaneously.
Without protection: both read qty=1, both reserve, both pay → overselling.

SOLUTION: Two-layer locking.

  Layer 1: Redis SETNX (fast pre-filter, 1-2ms)
  ─────────────────────────────────────────────
  SETNX lock:inventory:{product_id} {checkout_session_id} EX 30

  Returns 1 → you acquired lock, proceed
  Returns 0 → another checkout in progress for this product
            → Option A: Return HTTP 409 "Product being reserved, try again"
            → Option B: Poll/retry with exponential backoff (up to 5s)

  WHY Redis before DB?: Rejects 9,999 of 10,000 concurrent checkouts in 1ms
  without touching PostgreSQL. DB sees only 1 request per product at a time.

  Layer 2: PostgreSQL SELECT FOR UPDATE (ACID guarantee)
  ───────────────────────────────────────────────────────
  After Redis lock acquired:
    SELECT qty, reserved_qty
    FROM inventory
    WHERE product_id = ?
    FOR UPDATE;  -- Row-level exclusive lock

    available = qty - reserved_qty
    IF available < cart_qty:
      ROLLBACK
      DEL lock:inventory:{product_id}  -- release Redis lock
      RETURN 400 "Product X has insufficient stock"

    UPDATE inventory
    SET reserved_qty = reserved_qty + cart_qty
    WHERE product_id = ?;
    COMMIT;

  WHY SELECT FOR UPDATE here?: Even if Redis lock was released by expiry and
  two sessions reach DB simultaneously, PostgreSQL row lock ensures only one
  can modify reserved_qty at a time. Belt AND suspenders.

FULL CHECKOUT FLOW PSEUDOCODE:
  def checkout(cart_id, user_id, payment_method):
    items = fetch_cart_items(cart_id)
    locks_acquired = []

    try:
      for item in items:
        result = redis.set(f"lock:inventory:{item.product_id}",
                           session_id, nx=True, ex=30)
        if not result:
          raise LockConflictError(item.product_id)
        locks_acquired.append(item.product_id)

      with db.transaction():
        for item in items:
          inventory = db.query(
            "SELECT qty, reserved_qty FROM inventory "
            "WHERE product_id=? FOR UPDATE", item.product_id)
          if inventory.qty - inventory.reserved_qty < item.qty:
            raise OutOfStockError(item.product_id)
          db.execute("UPDATE inventory SET reserved_qty=reserved_qty+? "
                     "WHERE product_id=?", item.qty, item.product_id)

        order_id = db.execute("INSERT INTO orders (..., status='PENDING_PAYMENT')")

    finally:
      for pid in locks_acquired:
        redis.delete(f"lock:inventory:{pid}")  # always release

    payment_url = create_payment_intent(order_id, total)
    return order_id, payment_url

PAYMENT TIMEOUT HANDLING:
  Background job runs every 60 seconds:
    SELECT order_id FROM orders
    WHERE status='PENDING_PAYMENT'
    AND created_at < NOW() - INTERVAL '15 minutes'

  For each expired order:
    UPDATE inventory SET reserved_qty = reserved_qty - cart_qty
    UPDATE orders SET status = 'PAYMENT_TIMEOUT'
    Notify user: "Your checkout session expired, items returned to stock"
```

**Say to interviewer:** *"The key insight is reserved_qty. We never actually deduct qty during
checkout. We only increment reserved_qty, removing items from the available pool. Actual qty
deduction happens ONLY after payment.success webhook. If payment fails or times out, we just
decrement reserved_qty — no money moved, inventory restored."*

---

### DEEP DIVE 4: Payment — Idempotency & Webhook Handling

```
PAYMENT INITIATION:
  1. Checkout Service calls Payment Service with {order_id, amount, currency}
  2. Payment Service calls Stripe:
       stripe.paymentIntents.create({
         amount: 149999,  // cents
         currency: 'usd',
         metadata: { order_id: 'ORD_123', user_id: 'USR_456' },
         idempotency_key: 'ORD_123'  // order_id = idempotency key
       })
  3. Store in Payment DB: INSERT (payment_id, order_id, amount, status='PENDING')
  4. Return payment_url to client

WEBHOOK HANDLER (POST /webhooks/payment):
  1. Signature validation:
       stripe.webhooks.constructEvent(payload, stripe_signature, webhook_secret)
       REJECT if invalid → prevents forged webhooks

  2. Idempotency check:
       SELECT * FROM payments WHERE payment_id = {event.payment_intent_id}
       IF status = 'SUCCESS' → RETURN 200 OK (already processed, duplicate webhook)

  3. Process (SERIALIZABLE transaction):
       BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

       UPDATE payments
       SET status = 'SUCCESS', gateway_response = {webhook_payload}
       WHERE payment_id = ? AND status = 'PENDING';

       IF affected_rows = 0:
         ROLLBACK;
         RETURN 200;  -- concurrent webhook already processed it

       UPDATE orders SET status = 'PAYMENT_CONFIRMED', payment_id = ?
       WHERE order_id = ?;

       UPDATE inventory
       SET qty = qty - order_qty,
           reserved_qty = reserved_qty - order_qty
       WHERE product_id IN (SELECT product_id FROM order_items WHERE order_id=?);

       DELETE FROM cart_items WHERE cart_id = ?;

       COMMIT;

  4. Publish Kafka:
       producer.send('payment.success', { order_id, payment_id, amount, timestamp })
       producer.send('order.confirmed', { order_id, user_id, items, shipping_address })

  5. RETURN 200 OK to Stripe (Stripe stops retrying)

FAILURE SCENARIOS:
  Payment declined:  webhook payment_intent.payment_failed
                     → UPDATE orders SET status='PAYMENT_FAILED'
                     → UPDATE inventory SET reserved_qty = reserved_qty - order_qty
                     → Notify user "Payment failed, please try another method"

  Webhook timeout:   Stripe retries with exponential backoff (up to 3 days)
                     → Idempotency check on every retry → safe to replay any time

  DB crash during:   ROLLBACK → Stripe retries → idempotency check handles it
  webhook processing
```

---

### DEEP DIVE 5: Order Tracking (Kafka Event-Driven)

```
ORDER LIFECYCLE:
  PENDING_PAYMENT → PAYMENT_CONFIRMED → PROCESSING → SHIPPED → DELIVERED
                                                              → CANCELLED (if pre-ship)

KAFKA EVENT FLOW:
  payment.success     → Order Status Svc: UPDATE orders SET status='PAYMENT_CONFIRMED'
                     → Notification Svc: Email "Order confirmed! #ORD_123"
                     → Warehouse Svc: Create pick list

  order.shipped       → Order Status Svc: UPDATE status='SHIPPED', tracking_id=?, carrier=?
                     → Notification Svc: SMS "Order shipped, track: FedEx TRK456"

  order.delivered     → Order Status Svc: UPDATE status='DELIVERED', delivered_at=NOW()
                     → Notification Svc: Push "Package delivered!"

GET /v1/status/{orderId}:
  SELECT status, tracking_id, carrier, estimated_delivery FROM orders WHERE order_id=?
  SELECT status, timestamp FROM order_status_history WHERE order_id=? ORDER BY timestamp

REAL-TIME UPDATES:
  Option A — WebSocket (preferred):
    Client: WS connect to /v1/orders/{order_id}/track
    Backend: WebSocket Manager subscribes to Redis Pub/Sub: SUBSCRIBE order:{order_id}:updates
    Order Status Svc: PUBLISH order:{order_id}:updates {status, timestamp}
    WebSocket Manager: forwards message to client connection
    Latency: <500ms from Kafka event to user's screen

  Option B — Polling (fallback):
    Client: GET /v1/status/{order_id} every 30 seconds
    Less efficient but works when WebSocket unavailable

CANCELLATION:
  Allowed only if status in [PENDING_PAYMENT, PAYMENT_CONFIRMED, PROCESSING]
  SHIPPED and beyond → cannot cancel

  On cancel:
    UPDATE orders SET status='CANCELLED', reason=?
    UPDATE inventory SET qty = qty + order_qty WHERE product_id IN (order items)
    Initiate refund: stripe.refunds.create({payment_intent: payment_id})
    Publish 'order.cancelled' → Notification: "Refund in 5-7 business days"
```

---

### DEEP DIVE 6: Flash Sales (High-Volume Concurrent Checkout)

```
PROBLEM: Amazon Prime Day — 1M users try to buy 1000 units of a product at exact sale start.
Normal checkout design collapses: DB deadlocks, Payment GW rate-limited, overselling.

PRE-SALE PREPARATION (1 hour before):
  1. Flag product: flash_sale=true, sale_start_time, sale_quantity=1000
  2. Cache warm-up: Pre-load product details to Redis + CDN 1hr before sale
  3. Auto-scale: Checkout Service 5x normal capacity (50 → 250 instances)
  4. Dedicated read replicas for flash sale product queries
  5. Pre-allocate inventory table:
       CREATE TABLE flash_sale_inventory (
         product_id UUID,
         queue_position INT,    -- 1 to sale_quantity
         user_id UUID NULL,
         status ENUM('available', 'reserved', 'sold'),
         reserved_at TIMESTAMP
       );
       INSERT 1000 rows with status='available', queue_position=1..1000

VIRTUAL WAITING ROOM (prevents thundering herd):
  Before sale_start_time:
    All users directed to waiting room (Cloudflare Waiting Room or custom)
    Shows countdown timer. ~1M users queued.

  At sale_start_time:
    Waiting room releases users in controlled batches: 1000 users/sec
    Each user gets a short-lived token (JWT, 5-min TTL)
    Backend REJECTS requests without valid token → bots and early-birds blocked

CHECKOUT WITH SKIP LOCKED (no contention):
  User clicks 'Buy Now' → checkout request arrives

  BEGIN TRANSACTION;
    SELECT queue_position, status
    FROM flash_sale_inventory
    WHERE product_id = ?
      AND status = 'available'
    ORDER BY queue_position
    LIMIT 1
    FOR UPDATE SKIP LOCKED;   -- if row locked by another txn, SKIP it, try next

    IF found:
      UPDATE flash_sale_inventory
      SET status = 'reserved', user_id = ?, reserved_at = NOW()
      WHERE queue_position = ?;
      COMMIT;
      → proceed to payment
    ELSE:
      ROLLBACK;
      RETURN 'Sold out';       -- no contention, immediate response

  WHY SKIP LOCKED over normal SELECT FOR UPDATE?
    Normal FOR UPDATE: 1000 concurrent users queue behind 1 lock → serialized, slow
    SKIP LOCKED: each user grabs next UNLOCKED row → parallel, no blocking

QUEUE-BASED CHECKOUT (rate control):
  Instead of synchronous checkout for all 1000 users simultaneously:
    Publish to Kafka 'checkout.requests': {user_id, queue_position, timestamp}
    50 worker consumers process at steady 100 checkouts/sec
    User sees: "You're in line, position #523. Estimated wait: 5 min"
    WebSocket updates queue position in real-time

INVENTORY RESERVATION TIMEOUT:
  Background job every 10 seconds:
    UPDATE flash_sale_inventory
    SET status = 'available', user_id = NULL
    WHERE status = 'reserved'
      AND reserved_at < NOW() - INTERVAL '5 minutes'
  → User didn't pay in 5 min → inventory released to next user in queue

REDIS COUNTER FOR INSTANT SOLD-OUT CHECK:
  Before ANY DB work: DECR flash_sale:{product_id}:remaining
  If result >= 0 → proceed to checkout
  If result < 0  → RETURN 'Sold out' immediately (no DB hit)
  Sync with DB every 5s to correct counter drift

RATE LIMITING:
  Per-user: 1 checkout attempt per 10s (Redis: SETEX ratelimit:user:{id} 10 '1')
  Per-IP: 10 requests/sec (API Gateway)
  CAPTCHA before checkout to filter bots

REAL-WORLD NUMBERS (Amazon Prime Day):
  10M products on sale simultaneously
  100K orders/minute at peak
  Waiting room gates 5M concurrent users
  Queue-based checkout: 50K checkouts/min sustainable
  99.9% uptime during sale
  WITHOUT optimizations: DB deadlocks at 10K concurrent checkout writes/sec
  WITH optimizations: Waiting room + SKIP LOCKED + Redis counter → no overselling
```

---

### DEEP DIVE 7: Product Recommendations & Personalization

```
WHY IT MATTERS: Recommendations drive 30-40% of Amazon's revenue.
"Users who bought X also bought Y" — that single widget is worth billions.

DATA COLLECTION (event pipeline):
  Kafka captures user events:
    'product.viewed':      { user_id, product_id, timestamp, session_id }
    'product.added_to_cart': { user_id, product_id, qty }
    'product.purchased':   { user_id, product_id, order_id }
    'product.searched':    { user_id, query, filters }

  Flink/Spark Streaming consumes events → aggregates per user profile:
    User profile (Cassandra, partitioned by user_id):
      { recent_views: [last 20 product_ids],
        recent_searches: [last 10 queries],
        purchase_history: [all product_ids],
        preferred_categories: [],
        avg_price_range: {min, max} }

STRATEGY 1 — Collaborative Filtering:
  User-based:
    Find users with >50% overlap in purchase_history (Jaccard similarity)
    Recommend: products those users bought that current user has NOT bought

  Item-based ("Users who bought X also bought Y"):
    Co-purchase matrix: if A and B purchased together 1000 times:
    similarity(A,B) = 1000 / sqrt(total_purchases(A) × total_purchases(B))
    High similarity → show as related products

  Matrix Factorization (ALS — Alternating Least Squares):
    Offline training on sparse 100M users × 10M products interaction matrix
    Produces: user_factors (100M × 50 dims), product_factors (10M × 50 dims)
    Score(user, product) = dot_product(user_factors[user], product_factors[product])
    Top 100 products per user stored in Redis: SET recs:{user_id} [...] EX 86400
    Batch job refreshed daily (Spark job on S3 data lake, ~4 hours)

STRATEGY 2 — Content-Based:
  Product embeddings: BERT/Sentence Transformers on (title + description + category)
  → 768-dimensional vector per product

  User profile vector: average of embeddings of recently viewed/purchased products
  Recommendation: ES kNN search with vector field → products closest to user's profile

STRATEGY 3 — Trending:
  Global trending: products with highest view_count in last 24h
    → Used for cold-start users (no history)
  Category trending: top products per category, updated hourly
  Personalized: trending within user's preferred_categories[]

STRATEGY 4 — Business Rules:
  Margin-aware: boost high-margin products
  Inventory-aware: boost overstocked items (qty > 1000)
  Promotional: priority to sale items, new arrivals

HYBRID RANKING (combine all strategies):
  final_score = 0.4 × collaborative
              + 0.3 × content_based
              + 0.2 × trending
              + 0.1 × business_rules
  Return top 20 by final_score

SERVING ARCHITECTURE:
  Pre-compute: Nightly Spark batch generates top 100 recs per user
               Stored: SET recs:{user_id} [{product_id, score}, ...] EX 86400
  Real-time:  On API call: fetch from Redis (pre-computed),
               blend with trending + business rules,
               apply diversity (don't return 10 similar products, mix categories)
  Cold-start: No history → global trending + editorial curated picks

ENDPOINTS:
  GET /v1/recommendations/home
    → { trending_products, recommended_for_you, recently_viewed, based_on_cart }
  GET /v1/recommendations/product/{product_id}
    → { similar_products, frequently_bought_together }

A/B TESTING:
  50% users get old algorithm, 50% get new
  Track: CTR, add-to-cart rate, purchase conversion, revenue per user
  If new algo has +5% conversion with p-value < 0.05 → roll out to 100%

PERFORMANCE:
  Recommendation API: <100ms p95 (Redis lookup + blending)
  Pre-computation: 100M users × 100 recs = 10B recs/day, Spark 4 hours
  Storage: Redis 100GB for all pre-computed recs + user profiles

PRIVACY:
  Hash user_id before analytics storage (no PII in logs)
  20% recommendations from new categories (prevent filter bubbles)
  Show reason: "Based on your purchase of X" or "Trending in Electronics"
```

---

### DEEP DIVE 8: Disaster Recovery & Data Consistency Strategy

```
THREE REGIONS:
  Primary:   us-east-1 (writes, all services active)
  Secondary: us-west-2 (hot standby, <1s lag from primary)
  Tertiary:  eu-west-1 (warm standby, <10s lag, tiebreaker)

DATABASE REPLICATION:
  MySQL (User DB, Order DB):
    Primary → synchronous replication → us-west-2 (hot standby, <1s lag)
    Primary → async replication → eu-west-1 (warm standby, <10s lag)
    Tool: MySQL Group Replication or AWS Aurora Global Database

  PostgreSQL (Cart DB, Inventory DB):
    Streaming replication with replication slots
    Same topology: sync to us-west-2, async to eu-west-1

  MongoDB (Product DB):
    Multi-region replica set
    Write concern: majority (written to >=2 nodes before commit)
    Read preference: nearest (low latency reads from closest replica)

  Elasticsearch:
    Can be rebuilt from Kafka 'product.changes' topic (7-day retention)
    Cross-cluster replication for hot failover

  Kafka:
    MirrorMaker 2 replicates topics from primary to secondary cluster
    Consumers switch to secondary cluster on primary failure

CONSISTENCY TIERS:

  Tier 1 — Strong Consistency (inventory, orders, payments):
    Synchronous replication to secondary before commit (50-100ms extra latency)
    No overselling even during failover
    Trade-off: slower writes, worth it for correctness

  Tier 2 — Eventual Consistency (products, search, cache):
    Async replication (1-5s lag acceptable)
    Showing a product at old price for 5 seconds: acceptable
    Redis stale cache <10s: acceptable
    ES search showing old stock: acceptable (real check at checkout anyway)

FAILOVER PROCEDURE:
  1. Route53 health checks every 30s (TCP, HTTP, DB connectivity)
  2. 3 consecutive failures (90s) → trigger failover
  3. Database promotion:
       pg_ctl promote (PostgreSQL)
       aurora.promoteReadReplicaDBCluster (Aurora MySQL)
       Takes 2-5 minutes
  4. Route53 DNS update → points to us-west-2 load balancer
  5. App servers in us-west-2 become active, us-east-1 goes read-only
  6. Kafka consumers switch to secondary Kafka cluster
  Total downtime: ~8 minutes. Data loss: <1s (Tier 1), <10s (Tier 2)

SPLIT-BRAIN PREVENTION:
  Fencing: primary region stops accepting writes when network partition detected
  Witness node: eu-west-1 is tiebreaker for quorum voting
  Distributed lock: Consul/etcd ensures only ONE region is primary at a time

RTO / RPO TARGETS:
  Tier 1 (orders, inventory, payments):
    RPO: <1 second  (synchronous replication)
    RTO: <5 minutes (automated failover)
  Tier 2 (products, search):
    RPO: <10 seconds (async replication)
    RTO: <5 minutes
  Backups (last resort):
    RPO: <1 hour (hourly S3 Glacier backups)
    RTO: <4 hours (manual restore)

DATA CORRUPTION RECOVERY:
  Point-in-time recovery: restore DB to any second in last 7 days
  Logical backups: daily mysqldump/pg_dump to S3, 30-day retention
  Binary log replay: MySQL binlogs, PostgreSQL WAL archives for fine-grained replay

KAFKA DURABILITY:
  Replication factor 3 (events written to 3 brokers before acknowledged)
  min.insync.replicas=2 (producer fails if <2 replicas available)
  Retention 7 days → can replay events to rebuild Elasticsearch or Redis

MONITORING & RECONCILIATION:
  Replication lag alerts: >5s (Tier 1), >30s (Tier 2)
  Nightly reconciliation: compare Order DB vs Payment DB for discrepancies
  Inventory audit: compare Inventory.qty vs sum(order_items.qty) for sold products
  Financial: match Order DB revenue vs bank settlement CSV

COST vs BENEFIT:
  Multi-region adds 60-80% infrastructure cost
  $1M/month extra vs $10M revenue loss for 1-hour outage
  → Business continuity insurance, not optional for e-commerce at scale
```

---

# ═══════════════ PAGE 5 — FOLLOW-UP QUESTIONS ═══════════════

```
┌─────────────────────────────────────────────┬─────────────────────────────────────────────┐
│ FOLLOW-UP QUESTION                          │ ANSWER (Key Points)                         │
├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ "How do you handle flash sales where        │ Virtual waiting room (Cloudflare Waiting     │
│  100K users hit checkout simultaneously?"   │ Room) gates users at 1K/sec. Redis counter  │
│                                             │ DECR flash_sale:{pid}:remaining for instant │
│                                             │ sold-out check. PostgreSQL SKIP LOCKED for  │
│                                             │ flash_sale_inventory table (pre-allocated   │
│                                             │ rows, no contention). Queue-based checkout  │
│                                             │ via Kafka (100 checkouts/sec steady rate).  │
├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ "What if the Redis lock expires (30s)       │ Two safety nets: (1) Background job releases│
│  while user is still in checkout?"          │ PENDING_PAYMENT orders older than 15 min → │
│                                             │ reserved_qty released. (2) PostgreSQL       │
│                                             │ FOR UPDATE is the real ACID guarantee —     │
│                                             │ Redis lock is just the fast pre-filter.     │
│                                             │ A new checkout attempt after lock expiry    │
│                                             │ will hit DB and see reserved_qty is full.   │
├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ "What if Kafka consumer for Notification    │ Consumer groups with DLQ after 3 retries.   │
│  Service is down?"                          │ Kafka retains events 7 days. When consumer  │
│                                             │ comes back up, it replays from last commit  │
│                                             │ offset. User gets email late, not never.    │
│                                             │ Notification failure doesn't affect order.  │
├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ "How do you keep Elasticsearch in sync      │ CDC pipeline: MongoDB oplog → Kafka Connect │
│  with 100M products being updated?"         │ → ES indexer. Lag 1-2s. Batch indexing:    │
│                                             │ buffer 100 events, bulk API every 2s.       │
│                                             │ If ES down: indexer pauses at Kafka offset, │
│                                             │ replays on recovery. Rebuild from scratch:  │
│                                             │ replay entire 'product.changes' topic.      │
├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ "How do you prevent double-charging         │ order_id as idempotency_key to Stripe.      │
│  a user?"                                   │ Stripe deduplicates on their end.           │
│                                             │ Our end: UNIQUE constraint on              │
│                                             │ payments(order_id). Webhook handler checks  │
│                                             │ payment status before processing. SERIALIZ- │
│                                             │ ABLE transaction prevents concurrent        │
│                                             │ webhooks both inserting payment records.    │
├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ "How do you scale the checkout service?"    │ Checkout is stateless — horizontal scaling. │
│                                             │ Redis locks are distributed across all      │
│                                             │ instances. PgBouncer for DB connection       │
│                                             │ pooling (10 instances × 200 connections =   │
│                                             │ 2K logical, 200 actual to PostgreSQL).      │
│                                             │ Scale to 100 instances for flash sales.     │
├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ "What's your DR (Disaster Recovery)         │ Tier 1 (inventory, orders, payments):       │
│  strategy?"                                 │ Synchronous replication, RPO <1s, RTO <5m. │
│                                             │ Tier 2 (search, cache): Async replication,  │
│                                             │ RPO <10s. Can rebuild ES from Kafka replay. │
│                                             │ Multi-region active-passive with Route53    │
│                                             │ health checks. Auto-failover in <5 minutes. │
├─────────────────────────────────────────────┼─────────────────────────────────────────────┤
│ "How do you handle the case where cart      │ At checkout, re-validate all cart items     │
│  item goes out of stock after adding?"      │ against current inventory. If any item has  │
│                                             │ insufficient stock: return error listing    │
│                                             │ which items are unavailable, remove them    │
│                                             │ from cart, let user decide to proceed with  │
│                                             │ remaining items or abort.                   │
└─────────────────────────────────────────────┴─────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 6 — SCALING & OPTIMIZATION TECHNIQUES ═══════════════

```
┌─────┬──────────────────────────────────┬──────────────────────────────────────────────────┐
│  #  │ TECHNIQUE                        │ DETAILS                                          │
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│  1  │ Elasticsearch Sharding           │ Product index sharded by hash(product_id) or     │
│     │                                  │ category. 5 primary shards, 1 replica each.      │
│     │                                  │ Parallel queries across shards → 100K QPS.       │
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│  2  │ Redis Multi-Layer Caching        │ Cart (7d TTL), Product details (30min),          │
│     │                                  │ Search results (10min), Inventory (5min).        │
│     │                                  │ 60-70% cache hit rate on search, 70% product.    │
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│  3  │ CDN for Product Images           │ S3 → CloudFront (CDN). 95% cache hit rate.      │
│     │                                  │ <50ms image load latency globally.               │
│     │                                  │ Product image URLs stored in MongoDB, served CDN.│
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│  4  │ Database Read Replicas           │ MySQL/PostgreSQL replicas for read-heavy queries  │
│     │                                  │ (product views, order history). Writes to primary.│
│     │                                  │ Inventory: all reads from replica except checkout.│
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│  5  │ CDC Pipeline                     │ MongoDB/PostgreSQL → Debezium → Kafka →          │
│     │                                  │ Elasticsearch / Redis. Decouples data sync.       │
│     │                                  │ Eventual consistency (1-2s lag) for search/cache. │
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│  6  │ Redis Distributed Locks          │ SETNX lock:inventory:{pid} EX 30.                │
│     │                                  │ Prevents overselling during concurrent checkouts.│
│     │                                  │ Auto-expiry prevents deadlock on service crash.  │
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│  7  │ Kafka Event Streaming            │ Decouples all post-payment work. Async notif,    │
│     │                                  │ warehouse fulfillment, analytics. Services scale │
│     │                                  │ independently. Event replay for debugging.        │
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│  8  │ Connection Pooling               │ PgBouncer in front of PostgreSQL.                │
│     │                                  │ 10 Checkout instances × 200 logical connections  │
│     │                                  │ → 200 actual DB connections. Prevents exhaustion.│
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│  9  │ API Rate Limiting                │ 1000 req/min per user (API Gateway).             │
│     │                                  │ 10 req/sec per IP (flash sale bot protection).   │
│     │                                  │ Checkout: 1 attempt/10s per user (Redis SETEX).  │
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│ 10  │ Database Partitioning            │ Orders table partitioned by month (order date).  │
│     │                                  │ Query "orders in Jan 2025" hits 1 partition.     │
│     │                                  │ Improves performance + simplifies archival.       │
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│ 11  │ Lazy Loading / Pagination        │ Search returns 20 items/page (infinite scroll).  │
│     │                                  │ Product images lazy-loaded. Reviews fetched       │
│     │                                  │ on-demand. Reduces initial payload 10x.          │
├─────┼──────────────────────────────────┼──────────────────────────────────────────────────┤
│ 12  │ Inventory Reservation            │ reserved_qty column holds stock during 15-min    │
│     │                                  │ checkout→payment window. Prevents overselling     │
│     │                                  │ AND prevents false "out of stock" display.        │
│     │                                  │ available = qty - reserved_qty                   │
└─────┴──────────────────────────────────┴──────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 7 — KEY NUMBERS ═══════════════

```
┌────────────────────────────────────┬────────────────────────────────────────────────────────┐
│ METRIC                             │ VALUE                                                  │
├────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Monthly Active Users               │ 10M MAU                                                │
│ Orders per second (normal)         │ 10 orders/sec                                          │
│ Orders per second (flash sale)     │ 100 orders/sec                                         │
│ Product catalog size               │ 100M+ products                                         │
│ Peak search queries                │ 100K queries/sec (sales events)                        │
├────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Search latency (p95)               │ <500ms (Elasticsearch)                                 │
│ Product page load                  │ <200ms (Redis cache hit < 50ms)                        │
│ Checkout end-to-end                │ <3 seconds (lock 10ms + DB 50ms + payment intent 200ms)│
│ Redis lock acquisition             │ <10ms (SETNX)                                          │
│ CDC lag (MongoDB → ES)             │ 1-2 seconds                                            │
├────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Redis TTL — Cart                   │ 7 days                                                 │
│ Redis TTL — Product details        │ 30 minutes (invalidated by Kafka on update)            │
│ Redis TTL — Search results         │ 10 minutes, 60-70% cache hit rate                     │
│ Redis TTL — Inventory cache        │ 5 minutes (synced via CDC)                             │
│ Redis TTL — Distributed lock       │ 30 seconds (deadlock prevention)                      │
├────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Inventory reservation timeout      │ 5 minutes (flash sales) / 15 minutes (regular)        │
│ Payment timeout                    │ 15 minutes from order creation                        │
│ Kafka event retention              │ 7 days (replay + audit trail)                         │
├────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Storage — Products (MongoDB)       │ 100M × 5 KB = 500 GB                                  │
│ Storage — Product images (S3)      │ 100M × 5 images × 1 MB = 500 TB (CDN-served)         │
│ Storage — Orders/year              │ 1M/day × 2 KB × 365 = 730 GB/year                    │
│ Storage — User data                │ 10M users × 2 KB = 20 GB (MySQL)                     │
│ Storage — Elasticsearch index      │ 300 GB, 10-node cluster, 5 primary shards             │
│ Storage — Redis (all caches)       │ ~50 GB + 100 GB recs = 150 GB total with recommendations│
├────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ CDN cache hit rate (images)        │ 95%, <50ms latency globally, CDN TTL 24 hours         │
│ ES search cache hit rate           │ 60-70% (top 10K queries cached in Redis)              │
│ Concurrent users (normal)          │ 50K-100K concurrent                                   │
│ Concurrent users (flash sale)      │ 1M concurrent (waiting room gates to 1K/sec)          │
├────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Conversion rate                    │ 2-5% (searches → orders)                              │
│ Cart abandonment rate              │ 60-70%                                                 │
│ Average Order Value                │ $50-150 depending on category                         │
│ Repeat Purchase Rate               │ 30-40% of users order again within 90 days            │
│ Recommendations revenue share      │ 30-40% of total e-commerce revenue                    │
│ Recommendation avg cart uplift     │ +25% cart size when users add recommended products    │
└────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

# ═══════════════ PAGE 8 — INTERVIEW TIPS ═══════════════

```
⚠️  CRITICAL — Say This About Inventory:
    "We use reserved_qty column as a two-phase commit. During checkout: increment reserved_qty
    (removes from available pool). After payment success: decrement both qty AND reserved_qty.
    Payment failure/timeout: only decrement reserved_qty. This ensures inventory is always
    consistent regardless of payment outcome."

⚠️  CRITICAL — Say This About Locks:
    "Two-layer locking: Redis SETNX as fast early rejection (1ms, prevents thundering herd on DB),
    PostgreSQL SELECT FOR UPDATE as ACID guarantee. EX 30 on Redis lock prevents permanent
    deadlock if service crashes mid-checkout."

⭐  INTERVIEWERS ALWAYS ASK: "How do you prevent overselling?"
    Answer order:
    1. Redis SETNX lock — fast rejection of concurrent checkouts for same product
    2. PostgreSQL SELECT FOR UPDATE — ACID row lock for atomic read+reserve
    3. reserved_qty column — inventory held without deducting (payment may fail)
    4. Actual deduction ONLY after payment.success webhook
    5. Lock auto-expires 30s + background job releases stale reservations after 15min

⭐  INTERVIEWERS ALWAYS ASK: "Why MongoDB for products?"
    Answer: "Different product types have completely different attributes. MongoDB's flexible
    schema avoids either 200-column sparse tables or the EAV anti-pattern. Adding a new product
    category (VR headsets, drones) requires no schema migration — just insert documents."

⭐  INTERVIEWERS ALWAYS ASK: "How do you keep Elasticsearch consistent with MongoDB?"
    Answer: "CDC pipeline — MongoDB oplog → Kafka Connect → ES indexer consumer.
    1-2 second eventual consistency is acceptable for search. CDC decouples Product Service
    from search implementation. ES can be rebuilt from Kafka topic replay if corrupted."

💡  DATABASE SELECTION CHEAT SHEET:
    User DB → MySQL:         Fixed schema, ACID for auth, relational (user→orders)
    Product DB → MongoDB:    Flexible schema, diverse product types, no ALTER TABLE
    Cart DB → PostgreSQL:    ACID upserts (ON CONFLICT), relational, JSONB support
    Inventory DB → PostgreSQL: ACID + SELECT FOR UPDATE, source of truth for stock
    Order DB → MySQL:        ACID transactions, relational, complex reporting queries
    Cache → Redis:           HASH for cart, STRING for products/search, distributed locks
    Search → Elasticsearch:  Full-text, filters, facets, autocomplete, 100K QPS

💡  KAFKA TOPICS TO MENTION:
    product.updated → ES indexer, Redis cache invalidator
    order.created   → Inventory Svc (reserve), Notification Svc
    payment.success → Order Svc (confirm), Inventory Svc (deduct), Notification, Warehouse
    order.shipped   → Order Status Svc, Notification, Tracking
    inventory.updated → Product Svc (sync qty), ES indexer, Redis cache

⚠️  NEVER SAY:
    - "I'll use eventual consistency for inventory" (overselling disaster)
    - "I'll use MongoDB for orders" (strong ACID required)
    - "I'll update inventory synchronously in checkout" (what if payment fails?)
    - "I'll use Redis as source of truth for stock" (Redis can lose data)

⭐  BONUS POINT — Say This About CDC:
    "CDC decouples the source database from derived data stores. If Elasticsearch goes down,
    MongoDB keeps accepting writes. The indexer consumer catches up from its last committed
    Kafka offset when ES recovers. No data lost. No code change in Product Service."
```

---

*Part of the "System Design Complete Course" — Interview With Bunny*
