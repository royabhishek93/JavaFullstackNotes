# E-Commerce Platform (Amazon/Flipkart) — Beginner's Study Guide

**Created**: 2025  
**Purpose**: Interview preparation for E-Commerce system design (Amazon, Flipkart, Myntra scale)  
**Difficulty**: ⭐⭐⭐⭐ (Advanced — Inventory Consistency + Distributed Locking + CDC + Event-Driven)  
**Time to Master**: 7 days (40 hours)

---

## 🎯 **What Makes This System Unique**

E-Commerce platform design is **NOT** about CRUD operations. 60% of the interview will focus on **proving you understand inventory consistency** — specifically:

1. **The overselling problem**: How do you prevent 10,000 concurrent users from all buying the last unit in stock?
2. **The stuck inventory problem**: How do you ensure inventory doesn't stay locked forever if checkout fails?
3. **The payment failure problem**: If payment succeeds at the gateway but webhook delivery fails, how do you recover?

Every answer you give must reference one of three patterns:
- **Two-layer locking** (Redis SETNX + PostgreSQL FOR UPDATE)
- **reserved_qty column** (soft hold during checkout→payment window)
- **Idempotent webhooks** (UNIQUE constraint + SELECT before INSERT)

---

## 📚 **7-DAY STUDY PLAN**

### **Day 1-2: Understand the Checkout Critical Path** (10 hours)
- [ ] Study [03-checkout-flow-sequence-BEGINNER.drawio](./03-checkout-flow-sequence-BEGINNER.drawio) in Draw.io
- [ ] Memorize the 34-step checkout sequence from "Browse" to "Kafka event published"
- [ ] Understand **why** Redis SETNX happens before PostgreSQL FOR UPDATE (thundering herd prevention)
- [ ] Practice explaining: "What happens if the service crashes at step 23 (after reservation, before payment intent)?"
- [ ] **Checkpoint**: Can you draw the two-layer locking flow on a whiteboard without notes?

**Key Question to Answer**: *Why can't we just use PostgreSQL SELECT FOR UPDATE alone? Why do we need Redis?*

**Answer**: 10K concurrent users hitting PostgreSQL SELECT FOR UPDATE simultaneously causes lock contention and connection pool exhaustion. Redis SETNX rejects 9,999 users in <1ms before they touch the database. The 1 winner then proceeds to PostgreSQL with no contention.

---

### **Day 3: Inventory Consistency Deep Dive** (6 hours)
- [ ] Study the `inventory` table schema in [04-data-model-BEGINNER.drawio](./04-data-model-BEGINNER.drawio)
- [ ] Understand the formula: `available = qty - reserved_qty`
- [ ] Walk through 3 scenarios:
  1. **Happy path**: Checkout succeeds, payment succeeds → qty and reserved_qty both decrement
  2. **Payment fails**: reserved_qty decrements, qty unchanged → inventory restored
  3. **Timeout (15 min)**: Cron job finds `PENDING_PAYMENT` orders, decrements reserved_qty
- [ ] Practice explaining: "Why does reserved_qty exist? Why not just decrement qty during checkout?"
- [ ] **Checkpoint**: Draw the inventory state transitions through checkout→payment→completion

**Real-World Analogy**: A hotel holds your room while you enter your credit card (reserved_qty). Only after payment succeeds does the room become unavailable to others (qty decrement). Card declines? The hold is released, next guest can book.

---

### **Day 4: Data Model & Technology Choices** (8 hours)
- [ ] Study all 6 data stores in [04-data-model-BEGINNER.drawio](./04-data-model-BEGINNER.drawio):
  - MongoDB (products — flexible schema)
  - PostgreSQL (inventory, cart — ACID)
  - MySQL (orders, payments — partitioned)
  - Elasticsearch (search — full-text)
  - Redis (cache + locks — TTL)
  - Kafka (events — decoupling)
- [ ] For each WHY box in [02-architecture-components-BEGINNER.drawio](./02-architecture-components-BEGINNER.drawio), memorize:
  - What problem does this technology solve?
  - What happens if we use something else instead?
- [ ] Practice explaining: "Why MongoDB for products but PostgreSQL for inventory?"
- [ ] **Checkpoint**: Can you explain 3 data stores and their trade-offs in 2 minutes?

**Interview Trap**: "Why not use Redis as the source of truth for inventory?" → Answer: Redis evicts under memory pressure. A crash loses all reservation state. PostgreSQL MVCC with row-level locks provides ACID guarantees required for financial transactions (inventory = money).

---

### **Day 5: Event-Driven Architecture** (6 hours)
- [ ] Study Kafka topics in [04-data-model-BEGINNER.drawio](./04-data-model-BEGINNER.drawio):
  - `product.changes` (CDC from MongoDB)
  - `order.created` (checkout complete, payment pending)
  - `payment.success` (trigger warehouse + email)
  - `order.shipped` (tracking update)
  - `inventory.updated` (stock replenishment)
- [ ] Understand consumer groups, at-least-once delivery, dead-letter queues
- [ ] Practice explaining: "Why Kafka instead of direct REST calls from Payment Service to Notification Service?"
- [ ] **Checkpoint**: Draw the event flow after `payment.success` is published (5 consumers, 5 actions)

**Answer**: Direct calls mean Checkout Service waits for Notification to send email, Warehouse to generate label, Analytics to log event. One slow/failed downstream service blocks the entire checkout. Kafka decouples: publish event, return 201 immediately. Each consumer retries independently.

---

### **Day 6: Search & CDC Sync** (4 hours)
- [ ] Study Elasticsearch mapping in [04-data-model-BEGINNER.drawio](./04-data-model-BEGINNER.drawio)
- [ ] Understand CDC pipeline: MongoDB oplog → Kafka → ES Indexer → Elasticsearch
- [ ] Practice explaining: "Why not write to both MongoDB AND Elasticsearch in the same request?"
- [ ] Understand fuzzy matching (`labtop` → `laptop`), faceted aggregations (brand counts), autocomplete (edge n-gram)
- [ ] **Checkpoint**: Explain the search flow from user typing "lap" to autocomplete suggestions appearing

**Interview Trap**: "What if Elasticsearch is 2 seconds behind MongoDB?" → Answer: Eventual consistency is acceptable for search. Checkout validates inventory from PostgreSQL (source of truth) anyway. User might see a sold-out product in search briefly, but checkout will reject it.

---

### **Day 7: Mock Interviews & Edge Cases** (6 hours)
- [ ] Practice 3 mock interviews using the [20-Minute Whiteboard Template](#20-minute-whiteboard-template)
- [ ] Answer all 10 Interview Q&A questions without looking at answers
- [ ] Complete the [Self-Check Questions](#self-check-questions) (all 4 categories)
- [ ] Study [Common Mistakes to Avoid](#common-mistakes-to-avoid)
- [ ] **Final Checkpoint**: Can you design the system end-to-end in 20 minutes on a whiteboard?

---

## 🔥 **7 KEY CONCEPTS (Memorize These)**

### **1. Inventory Consistency via reserved_qty Pattern**

**Problem**: Flash sale, 1 unit left, 10K concurrent checkouts. How to prevent overselling?

**Solution**: The `inventory` table has 3 columns:
- `qty` (total warehouse stock) — source of truth
- `reserved_qty` (in active checkouts, not yet paid) — soft hold
- `available` (virtual: `qty - reserved_qty`) — what users see

**Flow**:
1. **During checkout**: `UPDATE inventory SET reserved_qty = reserved_qty + 1` (stock removed from pool, but NOT deducted)
2. **After payment.success webhook**: `UPDATE inventory SET qty = qty - 1, reserved_qty = reserved_qty - 1` (actual deduction)
3. **On payment failure/timeout**: `UPDATE inventory SET reserved_qty = reserved_qty - 1` (stock restored, qty unchanged)

**Why this works**: Prevents overselling (lock at reservation) + prevents stock leakage (only deduct after money received).

**Real-World Analogy**: Concert with 1 ticket. You click "Buy" → ticket reserved (removed from available pool). Card declines → ticket released back. Card succeeds → ticket sold (removed from warehouse).

---

### **2. Two-Layer Distributed Locking**

**Problem**: 10K users hit checkout simultaneously for the same product. PostgreSQL connection pool (200 conns) exhausted in 50ms.

**Solution**: Lock in 2 layers (belt AND suspenders):

**Layer 1 — Redis SETNX (Fast Rejection)**:
```bash
SETNX lock:inventory:{product_id} {session_id} EX 30
→ Returns 1 if acquired (you proceed)
→ Returns 0 if already locked (another checkout in progress → reject with 409)
```
- Executes in <1ms
- 9,999 users rejected immediately without touching database
- Auto-expires in 30 sec (service crash → lock released, no deadlock)

**Layer 2 — PostgreSQL SELECT FOR UPDATE (ACID Guarantee)**:
```sql
SELECT qty, reserved_qty FROM inventory WHERE product_id = ? FOR UPDATE;
-- Row-level pessimistic lock until COMMIT
```
- Only 1 user (the Redis lock winner) reaches here
- Blocks other transactions from modifying this row until current transaction commits
- ACID guarantee: reservation and order creation are atomic

**Why both?**: Redis prevents thundering herd on DB. PostgreSQL ensures ACID even if Redis lock expires during processing.

**Interview Trap**: "What if Redis lock expires (30 sec) but PostgreSQL transaction is still running?" → Answer: PostgreSQL row lock still holds. Even if another user gets Redis lock, they'll block on `SELECT FOR UPDATE` until first transaction commits. Two layers = defense in depth.

---

### **3. Idempotent Payment Webhooks**

**Problem**: Payment gateway retries webhooks on timeout. If we deduct inventory twice for the same payment, we have a bug.

**Solution**: Idempotency via UNIQUE constraint + SELECT before INSERT.

**Database Schema**:
```sql
CREATE TABLE payments (
  payment_id VARCHAR(100) PRIMARY KEY,  -- Stripe payment intent ID
  order_id VARCHAR(36) UNIQUE NOT NULL, -- UNIQUE prevents double-charge
  amount DECIMAL(10,2) NOT NULL,
  status ENUM('PENDING', 'SUCCESS', 'FAILED'),
  created_at TIMESTAMP DEFAULT NOW()
);
```

**Webhook Handler Pseudocode**:
```python
def handle_payment_webhook(payment_intent_id, order_id):
    # 1. Idempotency check
    existing = db.query("SELECT * FROM payments WHERE order_id = ?", order_id)
    if existing and existing.status == 'SUCCESS':
        return 200  # Already processed, safe replay

    # 2. Process (SERIALIZABLE transaction)
    with db.transaction(isolation='SERIALIZABLE'):
        db.execute("INSERT INTO payments (payment_id, order_id, amount, status) "
                   "VALUES (?, ?, ?, 'SUCCESS')", payment_intent_id, order_id, amount)
        db.execute("UPDATE orders SET status = 'PAYMENT_CONFIRMED' WHERE order_id = ?", order_id)
        db.execute("UPDATE inventory SET qty = qty - ?, reserved_qty = reserved_qty - ? "
                   "WHERE product_id IN (SELECT product_id FROM order_items WHERE order_id = ?)",
                   order_qty, order_qty, order_id)
        db.execute("DELETE FROM cart_items WHERE cart_id = ?", cart_id)
    
    # 3. Publish events
    kafka.send('payment.success', {'order_id': order_id, ...})
    return 200
```

**Why UNIQUE constraint?**: If webhook is replayed, the `INSERT` fails with duplicate key error → transaction rolls back → no double-deduction. Graceful failure.

**Real-World Analogy**: Stamping "PAID" on an invoice. If you try to stamp it twice, the second stamp doesn't fit (UNIQUE constraint). You know it's already paid → no double-charge.

---

### **4. CDC for Search Sync (Eventual Consistency)**

**Problem**: Product catalog has 100M products. How do we keep Elasticsearch fresh without slowing down Product Service writes?

**Solution**: Change Data Capture (CDC) pipeline.

**Flow**:
1. **Product Service** writes to MongoDB only (no knowledge of Elasticsearch)
2. **MongoDB oplog** (write-ahead log) captures every insert/update/delete
3. **Kafka Connect** (MongoDB Source Connector) streams oplog to Kafka topic `product.changes`
4. **ES Indexer** (Kafka consumer) reads from Kafka, bulk-indexes to Elasticsearch
5. **Lag**: 1-2 seconds (eventual consistency)

**Why CDC instead of dual-writes?**:
- Product Service doesn't need to know about Elasticsearch (loose coupling)
- If Elasticsearch is down, MongoDB writes continue → no impact on sellers uploading products
- ES Indexer catches up from Kafka offset when ES comes back online
- Supports multiple consumers from one CDC stream (ES, Redis cache invalidator, analytics)

**Real-World Analogy**: Library catalog updates. When you return a book (MongoDB write), the head librarian writes it in the master ledger (oplog). Every hour, a clerk copies new entries to the public search catalog (ES indexer → Elasticsearch). Patrons might not see your returned book for 1-2 minutes, but that's acceptable — they're not checking out that exact book immediately anyway.

---

### **5. Flexible Product Schema (MongoDB)**

**Problem**: E-commerce has 1000+ product categories. Mobiles have `{RAM, storage, processor}`. Books have `{author, ISBN, publisher}`. Clothing has `{size, color, material}`. How to store without sparse tables?

**Solution**: MongoDB document-based flexible schema.

**Example Documents**:
```javascript
// Mobile Phone
{
  "_id": ObjectId("..."),
  "product_id": "PROD-123",
  "title": "iPhone 15 Pro Max",
  "category": "electronics",
  "price": 1299.99,
  "specifications": {
    "RAM": "8GB",
    "storage": "256GB",
    "processor": "A17 Pro",
    "screen_size": "6.7 inch",
    "battery": "4422mAh"
  }
}

// Book
{
  "_id": ObjectId("..."),
  "product_id": "PROD-456",
  "title": "Clean Code",
  "category": "books",
  "price": 39.99,
  "specifications": {
    "author": "Robert C. Martin",
    "ISBN": "978-0-13-235088-4",
    "publisher": "Prentice Hall",
    "page_count": 464,
    "language": "English"
  }
}
```

**Why MongoDB over PostgreSQL?**:
- **PostgreSQL**: Would require either (1) one massive table with 200+ nullable columns (sparse, wasteful), or (2) EAV pattern (`product_attributes` table) requiring joins for every query, or (3) ALTER TABLE for every new category.
- **MongoDB**: Just insert a document with new fields. No schema migration. Elasticsearch extracts common fields (brand, color) for faceted search via CDC pipeline.

**Interview Trap**: "How do you query products by RAM size if it's inside a nested object?" → Answer: Elasticsearch indexes `specifications.RAM` as a separate field during CDC sync. Queries like "RAM >= 8GB" run against ES, not MongoDB.

---

### **6. ON CONFLICT for Cart Race Conditions**

**Problem**: User opens mobile app and web simultaneously. Adds same product from both. How to prevent duplicate rows?

**Solution**: Composite UNIQUE constraint + ON CONFLICT upsert.

**Schema**:
```sql
CREATE TABLE cart_items (
  cart_id UUID NOT NULL,
  product_id VARCHAR(50) NOT NULL,
  qty INTEGER NOT NULL CHECK (qty > 0),
  price NUMERIC(10,2) NOT NULL,
  PRIMARY KEY (cart_id, product_id),  -- Composite key
  UNIQUE (cart_id, product_id)        -- Enforces one row per product
);
```

**Upsert Query**:
```sql
INSERT INTO cart_items (cart_id, product_id, qty, price, currency)
VALUES (?, ?, 2, 899.00, 'USD')
ON CONFLICT (cart_id, product_id)
DO UPDATE SET qty = cart_items.qty + EXCLUDED.qty,
              added_at = NOW();
```

**Flow**:
1. Mobile: `INSERT qty=2` → succeeds (first insert)
2. Web (simultaneous): `INSERT qty=1` → finds conflict (same `cart_id, product_id`) → executes `UPDATE qty = 2 + 1 = 3`
3. Result: 1 row with `qty=3` (correct behavior)

**Why this works**: Database atomically checks for conflict and executes UPDATE in a single operation. No race window.

**Cross-Device Sync**: Cart tied to `user_id` (not session). User logs in on any device → sees same cart (loaded from PostgreSQL). Redis caches `HSET cart:{user_id}` for fast reads.

---

### **7. Event-Driven Decoupling (Kafka)**

**Problem**: After payment succeeds, we need to (1) send email, (2) notify warehouse, (3) log analytics, (4) invalidate cache. If we do all this synchronously, checkout takes 5 seconds.

**Solution**: Kafka event-driven architecture.

**Flow**:
1. **Payment Service** processes webhook, publishes `payment.success` event to Kafka, returns 200 OK to gateway
2. **5 independent consumers** process the event:
   - **Notification Service** → sends email/SMS (slow, 2 sec)
   - **Warehouse Service** → creates pick list (offline, can retry)
   - **Analytics Service** → ETL to data warehouse (batch, non-blocking)
   - **Inventory Service** → invalidates Redis cache `DEL inventory:{product_id}` (fast, <10ms)
   - **Order Service** → updates order status history (audit trail)

**Why Kafka?**:
- Each consumer scales independently (Notification slow? Add more Notification instances)
- Each consumer fails independently (Warehouse down? Retries from Kafka offset, doesn't block email)
- 7-day retention = audit trail (can replay events to rebuild Elasticsearch index)
- Dead-letter queue (DLQ) = one bad event doesn't block entire consumer

**Interview Comparison**: "Why not REST calls?" → Answer: Synchronous call chain means Checkout waits for Notification to send email before returning. If Notification is slow (SMTP timeout), checkout is slow. If Warehouse is down, checkout fails. Kafka: publish event, return immediately. Each consumer at its own pace.

**Real-World Analogy**: Restaurant order. You pay at the counter (payment webhook). Cashier hands you a receipt (202 Accepted) and rings a bell (Kafka publish). Kitchen hears bell, starts cooking (Warehouse consumer). Waiter hears bell, brings water (Notification consumer). You don't wait for food to be cooked before leaving the counter.

---

## 💬 **INTERVIEW Q&A (Memorize Strong Answers)**

### **Q1: How do you prevent overselling when 10,000 users try to buy the last unit in stock?**

❌ **Weak Answer**: "We use database transactions to ensure only one user can checkout at a time."

✅ **Strong Answer**: 
> "We use **two-layer distributed locking** combined with the **reserved_qty pattern**:
> 
> **Layer 1 (Redis SETNX)**: Fast pre-filter that rejects 9,999/10,000 concurrent users in <1ms before they touch the database. `SETNX lock:inventory:{product_id} {session_id} EX 30` returns 1 if acquired, 0 if locked. Auto-expires in 30 sec to prevent deadlock on crash.
> 
> **Layer 2 (PostgreSQL FOR UPDATE)**: The 1 Redis lock winner proceeds to `SELECT qty, reserved_qty FROM inventory WHERE product_id=? FOR UPDATE` — a row-level pessimistic lock that blocks other transactions until COMMIT.
> 
> **Reservation**: We don't deduct `qty` during checkout. We increment `reserved_qty` (soft hold). `available = qty - reserved_qty` shows users what they can buy. Only after `payment.success` webhook do we execute `UPDATE inventory SET qty=qty-1, reserved_qty=reserved_qty-1` atomically. If payment fails, `UPDATE reserved_qty=reserved_qty-1` only — stock restored, no money moved.
> 
> This prevents overselling (lock at reservation) and prevents stock leakage (only deduct after payment confirmed)."

**Follow-Up**: "What if the service crashes between reservation and payment?"
> "The Redis lock auto-expires in 30 sec. The PostgreSQL row lock is released on transaction ROLLBACK. A background cron job runs every 60 sec, finds orders in `PENDING_PAYMENT` status for >15 min, and executes `UPDATE inventory SET reserved_qty=reserved_qty-{order_qty}` to release the hold. We also poll the payment gateway API to check if payment actually succeeded (webhook delivery failed) and reconcile."

---

### **Q2: Why use Elasticsearch for search instead of PostgreSQL full-text search?**

❌ **Weak Answer**: "Elasticsearch is faster than PostgreSQL for search."

✅ **Strong Answer**:
> "PostgreSQL's `tsvector` full-text search has 4 critical limitations at scale:
> 
> 1. **No fuzzy matching**: `LIKE '%laptop%'` won't find 'labtop' (user typo). Elasticsearch's fuzzy query (`fuzziness: AUTO`) fixes typos automatically using Levenshtein distance.
> 
> 2. **No relevance scoring**: PostgreSQL can't boost title matches over description mentions. Elasticsearch `multi_match` with `title^3` boosts title 3x, ranking results by relevance.
> 

> 3. **No faceted aggregations**: "Show me how many results per brand, per price range" requires expensive GROUP BY in PostgreSQL. Elasticsearch `aggs` returns facet counts in the same query with no additional DB hit.
> 
> 4. **Scale**: PostgreSQL `LIKE '%search%'` scans every row in a 100M product table (30-60 sec). Elasticsearch pre-builds an inverted index (word → document IDs) before any query arrives, returning results in <100ms. We handle 100K searches/sec during sales events — PostgreSQL would fall over.
> 
> We sync via CDC: MongoDB oplog → Kafka → ES Indexer. Product Service writes only to MongoDB. Lag is 1-2 sec (eventual consistency acceptable for search). If Elasticsearch is down, MongoDB writes continue — no impact on sellers."

**Follow-Up**: "What if Elasticsearch is 5 seconds behind MongoDB after a bulk product upload?"
> "Eventual consistency is acceptable for search. Users might see a sold-out product briefly in search results, but checkout validates inventory from PostgreSQL (source of truth) anyway. The checkout will reject with 'Out of stock' if `available = qty - reserved_qty < cart_qty`. Inventory is strongly consistent, search is eventually consistent."

---

### **Q3: How do you handle payment webhook retries without double-charging the user?**

❌ **Weak Answer**: "We check if the payment ID already exists before processing."

✅ **Strong Answer**:
> "We use **idempotency via UNIQUE constraint** on the `payments` table:
> 
> **Schema**: 
> ```sql
> CREATE TABLE payments (
>   payment_id VARCHAR(100) PRIMARY KEY,  -- Stripe payment intent ID
>   order_id VARCHAR(36) UNIQUE NOT NULL, -- UNIQUE prevents double-charge
>   amount DECIMAL(10,2) NOT NULL,
>   status ENUM('PENDING', 'SUCCESS', 'FAILED')
> );
> ```
> 
> **Webhook Handler**:
> 1. **Signature validation**: `stripe.webhooks.constructEvent(payload, signature, secret)` — rejects forged webhooks
> 2. **Idempotency check**: `SELECT * FROM payments WHERE order_id=?`. If `status='SUCCESS'` → return 200 OK (already processed, safe replay).
> 3. **Process in SERIALIZABLE transaction**:
>    - `INSERT INTO payments (payment_id, order_id, amount, status) VALUES (..., 'SUCCESS')`
>    - `UPDATE orders SET status='PAYMENT_CONFIRMED'`
>    - `UPDATE inventory SET qty=qty-1, reserved_qty=reserved_qty-1`
>    - `DELETE FROM cart_items`
> 4. **Publish Kafka**: `payment.success`, `order.confirmed`
> 5. **Return 200 OK** → Stripe stops retrying
> 
> If the webhook is replayed, the `INSERT` will fail with duplicate key error on `order_id` (UNIQUE constraint) → transaction rolls back → no double-deduction. The UNIQUE constraint acts as our idempotency guarantee.
> 
> We also send `order_id` as `idempotency_key` to Stripe when creating the payment intent. If we retry creating the intent (network timeout), Stripe returns the same `payment_id` instead of charging twice."

**Follow-Up**: "What if the webhook delivery fails completely (never arrives)?"
> "We have a background reconciliation job that runs every 60 seconds:
> 1. Find orders in `PENDING_PAYMENT` status for >15 minutes
> 2. Poll Stripe API: `stripe.paymentIntents.retrieve(payment_id)`
> 3. If status is `succeeded` → manually trigger webhook handler logic
> 4. If status is `failed` → release inventory reservation
> This ensures we don't miss payments even if webhooks are lost."

---

### **Q4: Why store the cart in both PostgreSQL and Redis?**

❌ **Weak Answer**: "Redis is faster, so we use it for reads."

✅ **Strong Answer**:
> "We use a **cache-aside pattern** with PostgreSQL as source of truth and Redis as the fast read layer:
> 
> **Why PostgreSQL?**:
> - **Durability**: Redis evicts keys under memory pressure (LRU policy). If a cart is evicted, user's items silently disappear. PostgreSQL persists carts to disk — survives crashes and restarts.
> - **ACID guarantees**: `ON CONFLICT (cart_id, product_id) DO UPDATE SET qty = qty + EXCLUDED.qty` handles race conditions when user adds same item from mobile + web simultaneously.
> - **Cross-device sync**: Cart is tied to `user_id` (not session). User logs in on mobile → sees same cart as desktop (loaded from PostgreSQL).
> 
> **Why Redis on top?**:
> - **Speed**: `HGETALL cart:{user_id}` returns cart in <1ms. PostgreSQL query takes 10-50ms. With 10M concurrent users all refreshing their cart, that 10ms difference is the gap between a fast site and a slow site.
> - **Reduces DB load**: 60-70% cache hit rate means 6-7M reads/sec handled by Redis, only 3-4M hit PostgreSQL.
> 
> **Write flow**:
> 1. `INSERT INTO cart_items ... ON CONFLICT ...` (PostgreSQL)
> 2. `DEL cart:{user_id}` (Redis) — invalidate cache
> 3. Next read misses cache → rebuilds from PostgreSQL → `HSET cart:{user_id}` (cache populated)
> 
> **Read flow**:
> 1. `HGETALL cart:{user_id}` (Redis) — if hit, return
> 2. If miss → `SELECT * FROM cart_items WHERE cart_id=?` (PostgreSQL) → cache result
> 
> Redis is a sticky note on the fridge (fast, but can fall off). PostgreSQL is the notebook where you write the list (permanent, but takes longer to flip pages)."

**Follow-Up**: "What TTL do you use for cart cache?"
> "7 days (`EXPIRE cart:{user_id} 604800`). Long enough that users who browse over multiple days see their cart persist. After 7 days, we assume the user abandoned it and let Redis evict. PostgreSQL still has it if they come back."

---

### **Q5: How do you handle flash sales where 100K users try to buy 100 units simultaneously?**

❌ **Weak Answer**: "We add more servers to handle the load."

✅ **Strong Answer**:
> "Flash sales are the worst-case stress test for inventory consistency. Here's our multi-layer defense:
> 
> **1. Redis Distributed Lock (First Line of Defense)**:
> - `SETNX lock:inventory:{product_id} {session_id} EX 30`
> - 100K users hit checkout → only 1 gets Redis lock per product
> - The other 99,999 are rejected in <1ms with `409 Conflict: Item being reserved by another user`
> - No database is touched for rejected users → prevents thundering herd
> 
> **2. Queue-Based Processing (Optional Enhancement)**:
> - For extremely limited stock (<100 units), we can front the checkout with a Redis queue:
>   - `RPUSH checkout:queue:{product_id} {user_session}`
>   - Worker pops from queue (`BLPOP`) and processes serially
>   - Users see position in queue: "You are #543 in line"
> - This prevents all 100K users from simultaneously hitting the checkout endpoint
> 
> **3. PostgreSQL SKIP LOCKED (Queue Processing)**:
> - If using DB-backed queue:
>   ```sql
>   SELECT * FROM checkout_requests
>   WHERE product_id=? AND status='PENDING'
>   ORDER BY created_at
>   LIMIT 1
>   FOR UPDATE SKIP LOCKED;
>   ```
> - Multiple workers can process queue in parallel without lock contention (skip rows locked by other workers)
> 
> **4. reserved_qty Pattern**:
> - `available = qty - reserved_qty` shows users real-time availability
> - If 100 units, 100 users can simultaneously reserve (distributed lock ensures serially)
> - The 101st user sees `available=0` → "Out of stock"
> 
> **5. Rate Limiting (API Gateway)**:
> - 100 requests/sec per user (prevents bot spam)
> - 10K requests/sec per product (prevents single product from killing entire system)
> 
> **6. Pre-Warming**:
> - 30 minutes before flash sale, cache inventory in Redis: `SET inventory:{product_id} {qty} EX 3600`
> - Checkout reads from cache first (no DB hit for availability check)
> - Actual reservation still uses PostgreSQL FOR UPDATE (ACID guarantee)
> 
> **Result**: 99,900/100K users rejected in <1ms (Redis), 100 users proceed to checkout (distributed lock + reserved_qty), 0 overselling."

**Follow-Up**: "What about bot traffic artificially inflating the queue?"
> "We implement CAPTCHA challenges for flash sales (invisible reCAPTCHA on checkout button). We also use device fingerprinting (FingerprintJS) to detect multiple checkout attempts from the same device/IP → rate limit to 1 checkout per product per device."

---

### **Q6: How do you scale the Elasticsearch cluster to handle 100K searches/sec?**

❌ **Weak Answer**: "We add more Elasticsearch nodes."

✅ **Strong Answer**:
> "Scaling Elasticsearch involves 4 layers:
> 
> **1. Redis Cache Layer (First Line of Defense)**:
> - `GET search:{hash(query+filters+sort)}` — cache key is hash of entire query
> - TTL: 10 minutes (balance freshness vs hit rate)
> - 60-70% cache hit rate → actual ES queries drop from 100K/sec to 30-40K/sec
> 
> **2. Horizontal Scaling (ES Cluster)**:
> - 10-node cluster (3 master-eligible, 7 data nodes)
> - 100M products, 10 shards → 10M products per shard → 1 shard per data node
> - Each shard is a Lucene index, independently queryable
> - Load balancer round-robins search requests across data nodes
> 
> **3. Replica Shards (Read Scaling)**:
> - 1 primary shard + 2 replica shards = 3 copies of each shard
> - Reads can hit any replica → 3x read throughput
> - Writes go to primary, async-replicated to replicas (<100ms lag)
> 
> **4. Index Optimization**:
> - **Disable `_source` for heavy fields**: Store only indexed fields (title, description), fetch full product from MongoDB if needed
> - **Use doc_values for sorting/aggregations**: Column-oriented storage for faceted filters (brand, price range)
> - **Refresh interval: 1s** (near real-time, acceptable 1-sec lag)
> - **Force merge daily**: Consolidate index segments (10 segments → 1) → faster queries
> 
> **5. Query Optimization**:
> - **Use `bool` queries with filters**: `must` clause does scoring, `filter` clause does exact match (cached)
>   ```json
>   {
>     \"query\": {
>       \"bool\": {
>         \"must\": [{\"multi_match\": {\"query\": \"laptop\", \"fields\": [\"title^3\", \"description\"]}}],
>         \"filter\": [
>           {\"term\": {\"category\": \"electronics\"}},
>           {\"range\": {\"price\": {\"lte\": 1000}}}
>         ]
>       }
>     }
>   }
>   ```
> - **Filters are cached**: Elasticsearch caches filter results (bit sets) → subsequent queries with same filter are instant
> 
> **Result**: 100K searches/sec → 30K actual ES queries/sec (Redis cache) → distributed across 7 data nodes × 3 replicas = 21 query-capable shards → ~1500 queries/sec per shard (well within Elasticsearch capacity)."

**Follow-Up**: "How do you handle search traffic spikes during sales events (10x normal)?"
> "We have auto-scaling policies:
> 1. **CloudWatch alarm**: If average query latency >200ms for 2 minutes → trigger scale-up
> 2. **Add 3 data nodes** (pre-configured AMIs with Elasticsearch installed)
> 3. **Elasticsearch auto-rebalances shards** across new nodes (~5 minutes)
> 4. **Scale down after event**: If query latency <50ms for 30 minutes → terminate extra nodes
> 
> We also pre-warm the Redis cache before sales events (run popular queries, cache results)."

---

### **Q7: How does CDC (Change Data Capture) work for syncing MongoDB to Elasticsearch?**

❌ **Weak Answer**: "We have a background job that polls MongoDB every minute and updates Elasticsearch."

✅ **Strong Answer**:
> "We use a **CDC pipeline** that streams MongoDB changes to Elasticsearch in real-time (1-2 sec lag):
> 
> **Architecture**:
> ```
> MongoDB (oplog) → Kafka Connect (MongoDB Source) → Kafka topic 'product.changes'
>   → ES Indexer (Kafka consumer) → Elasticsearch (bulk index)
> ```
> 
> **Step-by-Step Flow**:
> 
> **1. MongoDB Oplog (Write-Ahead Log)**:
> - Every insert/update/delete in MongoDB is appended to the oplog (replication log)
> - Oplog is a capped collection (`local.oplog.rs`) with format:
>   ```json
>   {
>     \"ts\": Timestamp(1234567890, 1),
>     \"op\": \"i\",  // i=insert, u=update, d=delete
>     \"ns\": \"ecommerce.products\",
>     \"o\": {\"_id\": ObjectId(\"...\"), \"product_id\": \"PROD-123\", \"title\": \"...\" ...}
>   }
>   ```
> 
> **2. Kafka Connect MongoDB Source Connector**:
> - Connects to MongoDB replica set
> - Tails the oplog (similar to MySQL binlog replication)
> - Publishes each oplog entry as a Kafka event to topic `product.changes`
> - Preserves ordering (partition key = `product_id` → same product always goes to same partition)
> 
> **3. Kafka Topic `product.changes`**:
> - 12 partitions (parallel processing by ES Indexer)
> - Retention: 7 days (enables replay if ES cluster crashes)
> - Schema: `{event_type: 'INSERT'|'UPDATE'|'DELETE', product_id, fullDocument: {...}, timestamp}`
> 
> **4. ES Indexer (Kafka Consumer)**:
> - Consumer group: `es-indexer-group` (multiple instances for parallel processing)
> - Batches events (up to 500 events or 5 sec, whichever first)
> - Bulk indexes to Elasticsearch:
>   ```python
>   for event in batch:
>       if event['event_type'] == 'INSERT' or event['event_type'] == 'UPDATE':
>           es.index(index='products', id=event['product_id'], body=event['fullDocument'])
>       elif event['event_type'] == 'DELETE':
>           es.delete(index='products', id=event['product_id'])
>   ```
> - Commits Kafka offset after successful bulk index (at-least-once delivery)
> 
> **Why CDC instead of dual-writes?**:
> - **Loose coupling**: Product Service doesn't know about Elasticsearch (no ES client in Product Service code)
> - **Resilience**: If ES is down, MongoDB writes continue → no impact on sellers uploading products
> - **Replay**: If ES index corrupts, replay from Kafka offset 0 (7 days history) → rebuild entire index
> - **Multiple consumers**: Same CDC stream feeds Redis cache invalidator, analytics ETL, recommendation model
> 
> **Lag**: 1-2 seconds average, 10 seconds p99 (bulk import spikes). Eventual consistency acceptable for search."

**Follow-Up**: "What if the ES Indexer crashes mid-batch?"
> "Kafka consumer commits offset AFTER successful bulk index. If indexer crashes before commit, on restart it re-processes from last committed offset. This means at-least-once delivery → ES Indexer must be idempotent. Elasticsearch `_id = product_id` ensures re-indexing the same document is a no-op (upsert, not duplicate)."

---

### **Q8: How do you ensure cart state is consistent when a user adds items from mobile and web simultaneously?**

❌ **Weak Answer**: "We lock the cart row before updating."

✅ **Strong Answer**:
> "We use **ON CONFLICT upsert** with a composite UNIQUE constraint to handle race conditions:
> 
> **Schema**:
> ```sql
> CREATE TABLE cart_items (
>   cart_id UUID NOT NULL,
>   product_id VARCHAR(50) NOT NULL,
>   qty INTEGER NOT NULL CHECK (qty > 0),
>   price NUMERIC(10,2) NOT NULL,
>   currency VARCHAR(3) NOT NULL,
>   added_at TIMESTAMP DEFAULT NOW(),
>   PRIMARY KEY (cart_id, product_id),  -- Composite key
>   UNIQUE (cart_id, product_id)        -- Enforces one row per product
> );
> ```
> 
> **Race Scenario**:
> - User opens mobile app, adds "iPhone" (qty=1)
> - Simultaneously opens web, adds "iPhone" (qty=2)
> - Both requests hit the backend at the same time
> 
> **Without ON CONFLICT**:
> - Two `INSERT` statements execute concurrently
> - Result: 2 rows with same `cart_id, product_id` → broken cart (duplicate items in UI)
> 
> **With ON CONFLICT**:
> ```sql
> INSERT INTO cart_items (cart_id, product_id, qty, price, currency)
> VALUES (?, 'iPhone', 1, 999.00, 'USD')
> ON CONFLICT (cart_id, product_id)
> DO UPDATE SET qty = cart_items.qty + EXCLUDED.qty,
>               added_at = NOW();
> ```
> 
> **Flow**:
> 1. **Mobile request** (arrives first): `INSERT qty=1` → succeeds (no conflict)
> 2. **Web request** (arrives 10ms later): `INSERT qty=2` → finds conflict (same `cart_id, product_id`) → executes `UPDATE qty = 1 + 2 = 3`
> 3. **Result**: 1 row with `qty=3` (correct aggregation)
> 
> **Why this works**:
> - Database atomically checks UNIQUE constraint and executes UPDATE in a single operation (no race window between SELECT and UPDATE)
> - `EXCLUDED.qty` refers to the value from the `INSERT` statement that conflicted (in this case, 2)
> - Even if 10 concurrent requests arrive, they're serialized by the UNIQUE constraint → final qty = sum of all requests
> 
> **Redis Cache Invalidation**:
> - After PostgreSQL write: `DEL cart:{user_id}` (invalidate cache)
> - Next read misses cache → rebuilds from PostgreSQL → `HSET cart:{user_id} product:iPhone '{"qty":3,...}'`
> - This ensures cross-device sync: mobile sees qty=3, web sees qty=3 (both read from same PostgreSQL row)"

**Follow-Up**: "What if the user changes the quantity on mobile while web is adding more?"
> "Same ON CONFLICT logic applies. The UNIQUE constraint ensures all updates are serialized and aggregated. The final qty is the sum of all operations. However, for a better UX, we could use optimistic locking:
> 
> Add a `version` column:
> ```sql
> UPDATE cart_items SET qty=?, version=version+1 WHERE cart_id=? AND product_id=? AND version=?
> ```
> If `affected_rows=0` → version conflict → return `409 Conflict` to client → client re-fetches cart and retries.
> 
> This prevents the last-write-wins problem where one user's change silently overwrites another's."

---

### **Q9: How do you handle database failures during the checkout process?**

❌ **Weak Answer**: "We retry the checkout request."

✅ **Strong Answer**:
> "Database failures during checkout fall into 3 categories, each handled differently:
> 
> **1. Failure BEFORE Inventory Reservation (Connection Error)**:
> - **Scenario**: User clicks "Checkout" → network timeout before `SELECT FOR UPDATE`
> - **Handling**:
>   - Checkout Service returns `503 Service Unavailable` to client
>   - Client retries with exponential backoff (100ms, 200ms, 400ms, up to 3 retries)
>   - Redis lock was never acquired → no cleanup needed
>   - Safe to retry (idempotent)
> 
> **2. Failure DURING Transaction (DB Crash Mid-Transaction)**:
> - **Scenario**: `SELECT FOR UPDATE` succeeds, `UPDATE reserved_qty` executes, then DB crashes before `COMMIT`
> - **Handling**:
>   - PostgreSQL transaction auto-rolls back on crash (MVCC guarantees)
>   - `reserved_qty` is NOT incremented (transaction never committed)
>   - Redis lock auto-expires in 30 sec (`EX 30`)
>   - Next user can acquire lock and proceed
>   - No stuck inventory
> 
> **3. Failure AFTER Reservation (Order Creation Fails)**:
> - **Scenario**: `reserved_qty` incremented successfully, but `INSERT INTO orders` fails (DB connection lost)
> - **Handling**:
>   - Checkout Service catches exception, executes cleanup:
>     ```python
>     try:
>         reserve_inventory(product_id, qty)
>         order_id = create_order(cart_id, user_id)
>     except DatabaseError:
>         rollback_reservation(product_id, qty)  # UPDATE reserved_qty = reserved_qty - qty
>         raise CheckoutError(\"Checkout failed, please retry\")
>     finally:
>         redis.delete(f\"lock:inventory:{product_id}\")  # Always release lock
>     ```
>   - Redis lock released in `finally` block (guaranteed execution)
>   - Inventory reservation rolled back manually
> 
> **4. Failure AFTER Order Creation (Payment Intent Fails)**:
> - **Scenario**: Order created (`status='PENDING_PAYMENT'`), but Stripe API call fails (network error)
> - **Handling**:
>   - Order exists in DB with `status='PENDING_PAYMENT'`
>   - Inventory is reserved (`reserved_qty` incremented)
>   - Background job (cron every 60 sec) finds orders `PENDING_PAYMENT` >15 min:
>     ```sql
>     SELECT order_id FROM orders
>     WHERE status='PENDING_PAYMENT' AND created_at < NOW() - INTERVAL '15 minutes'
>     ```
>   - For each order:
>     - Poll Stripe API: `stripe.paymentIntents.retrieve(payment_id)`
>     - If not found → payment intent was never created → release reservation:
>       ```sql
>       UPDATE inventory SET reserved_qty = reserved_qty - order_qty;
>       UPDATE orders SET status = 'PAYMENT_TIMEOUT';
>       ```
>     - If found with status `succeeded` → webhook was lost → manually trigger webhook handler
>     - If found with status `failed` → release reservation
> 
> **5. Database Failover (Primary Fails, Replica Promoted)**:
> - **PostgreSQL Multi-AZ Setup**: 1 primary + 2 replicas (streaming replication)
> - If primary fails, AWS RDS auto-promotes replica to primary (~30 sec failover)
> - During failover:
>   - In-flight transactions are lost (rollback)
>   - Redis locks expire after 30 sec
>   - Clients retry checkout (idempotent)
>   - reserved_qty discrepancies are reconciled by background job
> 
> **Result**: Every failure mode has a cleanup path. Inventory never stays stuck. Users can always retry."

**Follow-Up**: "What if the Redis lock expires (30 sec) but the transaction is still running?"
> "PostgreSQL row lock (FOR UPDATE) still holds. Even if another user acquires the Redis lock, they'll block on `SELECT ... FOR UPDATE` until the first transaction commits. The Redis lock is a fast pre-filter to prevent thundering herd. The PostgreSQL lock is the ACID guarantee. Two layers = belt AND suspenders."

---

### **Q10: How do you scale this system to support 10x more users (100M MAU)?**

❌ **Weak Answer**: "We add more servers and use a load balancer."

✅ **Strong Answer**:
> "Scaling from 10M to 100M MAU (10x) requires scaling every layer:
> 
> **1. Compute Layer (Stateless Services)**:
> - **Horizontal scaling**: Add more instances of each microservice (User, Product, Cart, Checkout, Order, Payment)
> - **Load balancer**: ALB (Application Load Balancer) distributes traffic across instances
> - **Auto-scaling**: Scale out when CPU >70%, scale in when CPU <30%
> - **Result**: 10x users → 10x service instances (100 → 1000 instances total)
> 
> **2. Database Layer (Stateful)**:
> 
> **MongoDB (Products)**:
> - **Shard by category**: 10 shards → 100 shards (10M products per shard → 1M products per shard)
> - **Vertical scaling per shard**: r6g.2xlarge → r6g.4xlarge (more RAM for working set)
> - **Read replicas**: 3 replicas per shard (1 primary + 2 secondaries) → reads distributed
> - **Result**: 10K writes/sec (product uploads) + 100K reads/sec (product pages) supported
> 
> **PostgreSQL (Inventory, Cart)**:
> - **Connection pooling**: PgBouncer with 5000 max connections (was 500)
> - **Read replicas**: 5 read replicas (was 2) → read traffic (inventory checks) distributed
> - **Partitioning**: Partition `cart_items` by user_id (hash partition, 100 partitions)
> - **Write scaling**: For inventory writes, consider Citus (distributed PostgreSQL) with sharding
> - **Result**: 1K checkouts/sec peak (10x from 100/sec) supported
> 
> **MySQL (Orders)**:
> - **Partitioning**: Already partitioned by month → no change needed (scales linearly with time)
> - **Read replicas**: 10 read replicas (was 5) → order status queries distributed
> - **Archive old partitions**: Move orders >1 year to S3 (Glacier) → keeps active dataset small
> 
> **3. Cache Layer (Redis)**:
> - **Redis Cluster**: 1 single-node instance → 10-node cluster (sharded by key)
> - **Memory**: 50GB → 500GB (10x cart data + product cache + search cache)
> - **Eviction policy**: allkeys-lru (evict least recently used keys when memory full)
> - **Result**: 500K cache ops/sec (cart reads, search cache hits) supported
> 
> **4. Elasticsearch**:
> - **Cluster size**: 10 data nodes → 100 data nodes
> - **Shards**: 10 shards → 100 shards (1M products per shard)
> - **Replicas**: 2 replicas per shard → 3 replicas (higher read throughput)
> - **Result**: 1M searches/sec peak supported
> 
> **5. Kafka**:
> - **Partitions**: 12 partitions per topic → 120 partitions (10x parallelism for consumers)
> - **Brokers**: 3 brokers → 10 brokers (distribute partition leadership)
> - **Consumer instances**: 12 instances (1 per partition) → 120 instances (1 per partition)
> - **Result**: 100K events/sec (10x from 10K/sec) supported
> 
> **6. CDN (CloudFront)**:
> - **Edge locations**: 200+ global edge locations (no change, already scales)
> - **S3 origin**: Auto-scales (no limit on objects or bandwidth)
> - **Cost optimization**: Compress images (WebP format, 50% smaller than JPEG)
> - **Result**: 10M image requests/sec supported (served from edge, <10ms latency)
> 
> **7. API Gateway Rate Limiting**:
> - **Per-user**: 100 req/sec → 1000 req/sec (allow power users)
> - **Per-product**: 10K req/sec → 100K req/sec (flash sales)
> - **Global**: 1M req/sec total → 10M req/sec total
> 
> **8. Monitoring & Observability**:
> - **Metrics**: Prometheus + Grafana (track p50, p99 latencies per service)
> - **Alerting**: PagerDuty alerts when error rate >1% or latency p99 >500ms
> - **Distributed tracing**: Jaeger (trace checkout flow across 7 services)
> 
> **Cost Estimate (AWS)**:
> - Compute: 1000 EC2 instances (c6g.2xlarge @ $0.272/hr) → $200K/month
> - MongoDB Atlas: 100 shards (M40 tier) → $150K/month
> - PostgreSQL RDS: r6g.4xlarge Multi-AZ + 5 replicas → $50K/month
> - Elasticsearch: 100 r6g.xlarge.search instances → $100K/month
> - Redis: 10-node cluster (cache.r6g.2xlarge) → $20K/month
> - S3 + CloudFront: 500TB storage + 10M requests/sec → $30K/month
> - **Total**: ~$550K/month for 100M MAU
> 
> **Result**: System supports 10M orders/day (was 1M/day), 1M searches/sec (was 100K/sec), 1K checkouts/sec (was 100/sec)."

**Follow-Up**: "Which component becomes the bottleneck first?"
> "**Inventory Service** (PostgreSQL writes during checkout). Even with Redis distributed lock reducing DB load, at 1K checkouts/sec we're executing 1K `UPDATE reserved_qty` writes/sec on PostgreSQL. Solution: Shard inventory DB by `product_id` (hash-based sharding) or use Citus (distributed PostgreSQL). This distributes writes across 10 shards → 100 writes/sec per shard (well within capacity)."

---

## 📋 **SELF-CHECK QUESTIONS**

### **Category A: Core Concepts**

1. **What is the formula for available inventory?**  
   <details><summary>Answer</summary>
   
   `available = qty - reserved_qty`
   
   - `qty` = total warehouse stock (source of truth)
   - `reserved_qty` = in active checkouts (soft hold, not yet paid)
   - `available` = what users can buy (shown in UI)
   </details>

2. **What are the 3 steps of the two-layer locking pattern?**  
   <details><summary>Answer</summary>
   
   1. **Layer 1 (Redis SETNX)**: `SETNX lock:inventory:{product_id} {session_id} EX 30` → returns 1 if acquired, 0 if locked → fast rejection in <1ms
   2. **Layer 2 (PostgreSQL FOR UPDATE)**: `SELECT qty, reserved_qty FROM inventory WHERE product_id=? FOR UPDATE` → row-level pessimistic lock → ACID guarantee
   3. **Always release in finally block**: `DEL lock:inventory:{product_id}` → prevents stuck locks even on exception
   </details>

3. **Why does the payment webhook handler need to check if the payment already exists before processing?**  
   <details><summary>Answer</summary>
   
   Payment gateways retry webhooks on timeout (exponential backoff, up to 3 days). Without idempotency check:
   - First webhook: Deducts inventory, updates order status
   - Retry webhook: Deducts inventory AGAIN → overselling, double-deduction
   
   Solution: `SELECT * FROM payments WHERE order_id=?`. If `status='SUCCESS'` → return 200 OK (already processed). UNIQUE constraint on `order_id` ensures database-level enforcement.
   </details>

4. **What is the difference between CDC (Change Data Capture) and dual-writes?**  
   <details><summary>Answer</summary>
   
   **Dual-writes**: Product Service writes to both MongoDB AND Elasticsearch in the same request.
   - Problem: If ES write fails, data is inconsistent. Tight coupling (Product Service must know about ES).
   
   **CDC**: Product Service writes only to MongoDB. Oplog → Kafka → ES Indexer → Elasticsearch.
   - Benefit: Loose coupling (Product Service doesn't know about ES). If ES down, MongoDB writes continue. Replay from Kafka offset if ES corrupts.
   </details>

5. **Why use MongoDB for products but PostgreSQL for inventory?**  
   <details><summary>Answer</summary>
   
   **MongoDB (Products)**:
   - Flexible schema needed: Mobiles have `{RAM, storage}`, books have `{author, ISBN}`, clothing has `{size, color}`
   - No ALTER TABLE for new categories
   - Document model fits product catalog perfectly
   
   **PostgreSQL (Inventory)**:
   - ACID transactions required: `reserved_qty` pattern needs atomic read-modify-write
   - Row-level locking (SELECT FOR UPDATE) prevents overselling
   - Strong consistency mandatory (inventory = money)
   - Fixed schema (qty, reserved_qty, warehouse_id — doesn't change)
   </details>

---

### **Category B: Failure Scenarios**

6. **What happens if the Redis lock expires (30 sec) but the PostgreSQL transaction is still running?**  
   <details><summary>Answer</summary>
   
   PostgreSQL row lock (FOR UPDATE) still holds. Even if another user acquires the Redis lock (after 30 sec expiry), they'll block on `SELECT ... FOR UPDATE` until the first transaction commits or rolls back.
   
   **Result**: Two-layer locking provides belt AND suspenders. Redis prevents thundering herd. PostgreSQL guarantees ACID.
   </details>

7. **What happens if payment succeeds at Stripe but the webhook delivery fails (network error)?**  
   <details><summary>Answer</summary>
   
   Order stays in `PENDING_PAYMENT` status. Inventory stays reserved (`reserved_qty` incremented).
   
   **Recovery**:
   1. Background cron job runs every 60 sec
   2. Finds orders `PENDING_PAYMENT` >15 min
   3. Polls Stripe API: `stripe.paymentIntents.retrieve(payment_id)`
   4. If status `succeeded` → webhook was lost → manually trigger webhook handler logic
   5. If status `failed` → release inventory reservation
   
   **Reconciliation**: Ensures no stuck inventory. No manual ops intervention needed.
   </details>

8. **What happens if Elasticsearch is 10 seconds behind MongoDB after a bulk product upload?**  
   <details><summary>Answer</summary>
   
   Users might see stale search results (newly uploaded products don't appear for 10 sec).
   
   **Why acceptable**: Eventual consistency is fine for search. Checkout validates inventory from PostgreSQL (source of truth) anyway. If user finds a sold-out product in search, checkout will reject with "Out of stock".
   
   **Not acceptable for**: Inventory (must be strongly consistent). Payments (must be strongly consistent).
   </details>

9. **What happens if the service crashes between incrementing reserved_qty and creating the order?**  
   <details><summary>Answer</summary>
   
   - **reserved_qty** is incremented (committed transaction)
   - **Order** was never created (transaction not started or rolled back)
   - **Redis lock** expires after 30 sec
   - **Stuck inventory**: reserved_qty incremented but no order exists
   
   **Recovery**:
   1. Background job runs every 60 sec
   2. Finds discrepancies: `SELECT product_id, reserved_qty FROM inventory WHERE reserved_qty > 0`
   3. Cross-references with orders: `SELECT SUM(qty) FROM order_items WHERE order_id IN (SELECT order_id FROM orders WHERE status='PENDING_PAYMENT') GROUP BY product_id`
   4. If `reserved_qty > SUM(pending orders)` → decrement difference (orphaned reservations)
   
   Alternatively, simpler approach: Find orders `PENDING_PAYMENT` >15 min → release those reservations.
   </details>

10. **What happens if a user adds the same product from mobile and web at exactly the same millisecond?**  
    <details><summary>Answer</summary>
    
    **Without ON CONFLICT**: Two `INSERT` statements → 2 rows with same `cart_id, product_id` → duplicate items in cart.
    
    **With ON CONFLICT**:
    ```sql
    INSERT INTO cart_items (cart_id, product_id, qty, ...)
    VALUES (?, 'iPhone', 1, ...)
    ON CONFLICT (cart_id, product_id)
    DO UPDATE SET qty = cart_items.qty + EXCLUDED.qty;
    ```
    - First INSERT (mobile) → succeeds
    - Second INSERT (web) → finds UNIQUE constraint conflict → executes UPDATE instead
    - Result: 1 row with `qty = 1 + 1 = 2` (correct aggregation)
    
    **Why this works**: UNIQUE constraint ensures database atomically serializes conflicting inserts. No race window.
    </details>

---

### **Category C: Scaling**

11. **How would you handle 10x more search traffic (1M searches/sec)?**  
    <details><summary>Answer</summary>
    
    1. **Increase Redis cache hit rate**: Pre-warm cache with popular queries before sales events
    2. **Scale Elasticsearch cluster**: 10 nodes → 100 nodes, 10 shards → 100 shards
    3. **Add replica shards**: 2 replicas → 3 replicas (3x read throughput)
    4. **CDN layer**: Cache popular search results in CloudFront (edge caching, <10ms latency)
    5. **Rate limiting**: 100 searches/sec per user → prevents abuse
    
    **Result**: 60-70% Redis cache hit → 300K ES queries/sec → distributed across 100 nodes × 3 replicas = 300 query-capable shards → ~1K queries/sec per shard (well within capacity).
    </details>

12. **How would you handle a flash sale where 100K users try to buy 10 units simultaneously?**  
    <details><summary>Answer</summary>
    
    1. **Redis Queue**: `RPUSH checkout:queue:{product_id} {user_session}` → users see queue position
    2. **Worker processes queue serially**: `BLPOP checkout:queue:{product_id}` → only 1 checkout at a time per product
    3. **Distributed lock**: `SETNX lock:inventory:{product_id}` before checkout → fast rejection for 99,990/100K users
    4. **reserved_qty pattern**: `available = qty - reserved_qty` → shows real-time availability (10 → 9 → 8 → ...)
    5. **Rate limiting**: 1 checkout per product per user (prevent bot spam)
    6. **CAPTCHA**: Invisible reCAPTCHA on checkout button (prevent bots)
    
    **Result**: 10 users successfully checkout, 99,990 users see "Out of stock" or queue timeout.
    </details>

13. **How would you shard the inventory database to handle 10x more checkouts?**  
    <details><summary>Answer</summary>
    
    **Sharding strategy**: Hash-based sharding by `product_id`
    
    1. **10 shards**: `shard_id = hash(product_id) % 10`
    2. **Each shard**: PostgreSQL instance with 10M products
    3. **Checkout routing**: Checkout Service computes shard_id, routes to correct shard
    4. **Multi-product cart**: For cart with products from multiple shards, use 2PC (two-phase commit) or compensating transactions
    
    **Result**: 1K checkouts/sec → distributed across 10 shards → 100 checkouts/sec per shard (well within PostgreSQL capacity).
    
    **Alternative**: Use Citus (distributed PostgreSQL) — auto-shards by distribution column (`product_id`), handles distributed transactions transparently.
    </details>

---

### **Category D: Design Tradeoffs**

14. **Why use eventual consistency for search but strong consistency for inventory?**  
    <details><summary>Answer</summary>
    
    **Search (Eventual Consistency OK)**:
    - User impact: Sees newly uploaded product 1-2 sec late → minor UX issue
    - Recovery: Checkout validates inventory anyway → no money lost
    - Benefit: Decoupling (Product Service doesn't wait for ES), faster writes
    
    **Inventory (Strong Consistency Required)**:
    - User impact: Overselling = selling 2 units when only 1 exists → customer complaint, refund, reputation damage
    - Recovery: No recovery — money already moved
    - Requirement: ACID transactions (SELECT FOR UPDATE), distributed locks
    
    **Rule**: Strong consistency for financial transactions (inventory, payments). Eventual consistency for non-critical reads (search, cache).
    </details>

15. **Why use Kafka instead of direct REST calls from Payment Service to Notification Service?**  
    <details><summary>Answer</summary>
    
    **Direct REST calls**:
    - Payment webhook calls Notification Service synchronously → waits for email to send (2 sec)
    - If Notification is slow/down → payment webhook times out → Stripe retries → webhook handler runs twice
    - Tight coupling: Payment Service must know Notification Service URL
    
    **Kafka**:
    - Payment webhook publishes `payment.success` event to Kafka → returns 200 OK immediately
    - Notification Service consumes event independently → sends email at its own pace
    - If Notification is down → Kafka retains event → Notification catches up when it restarts
    - Loose coupling: Payment Service doesn't know who consumes the event (could be 10 services)
    - At-least-once delivery: Notification retries from Kafka offset on crash
    
    **Result**: Webhook handler returns in <100ms (fast). Notification sends email in 2 sec (slow but non-blocking).
    </details>

---

## 🔢 **KEY NUMBERS TO MEMORIZE**

| **Metric** | **Value** | **Why This Number?** |
|------------|-----------|----------------------|
| **Scale** | 10M MAU, 1M orders/day, 100K searches/sec | Interview baseline — shows you understand Amazon/Flipkart scale |
| **Inventory Lock TTL** | 30 seconds (Redis SETNX) | Auto-expires if service crashes → prevents deadlock. Long enough for checkout flow (<5 sec), short enough to recover quickly |
| **Payment Timeout** | 15 minutes (PENDING_PAYMENT cron job) | Stripe payment page expires in 15 min → safe to release reservation after this |
| **Cart Cache TTL** | 7 days (Redis EXPIRE) | Long enough for users who browse over multiple days, short enough to evict abandoned carts |
| **Search Cache TTL** | 10 minutes (Redis) | Balance freshness (new products appear within 10 min) vs hit rate |
| **Product Cache TTL** | 30 minutes (Redis) | Product details change infrequently (price updates, stock updates faster via inventory cache) |
| **Inventory Cache TTL** | 5 minutes (Redis) | Inventory changes frequently (every order) → short TTL prevents stale data |
| **CDC Lag** | 1-2 sec avg, 10 sec p99 | MongoDB oplog → Kafka → ES Indexer → Elasticsearch. Eventual consistency acceptable for search |
| **Kafka Retention** | 7 days (product.changes), 30 days (payment events) | Enables replay for audit trail. Financial events (payments) kept longer for compliance |
| **Database Connections** | 200 per service instance, pooled via PgBouncer | PostgreSQL max_connections = 5000 → supports 25 service instances per DB |
| **Elasticsearch Cluster** | 10 nodes, 10 shards, 2 replicas per shard | 100M products → 10M per shard. 2 replicas → 3x read throughput |
| **Redis Memory** | 50GB (cart 20GB + product 15GB + search 10GB + misc 5GB) | 10M users × 2KB cart = 20GB. Eviction: allkeys-lru |
| **Checkout Success Rate** | >95% (below this, investigate lock timeouts, DB contention) | Key SLA metric — <95% means inventory locking or payment gateway issues |
| **Payment Webhook Retries** | Up to 3 days (Stripe exponential backoff) | Idempotency critical — webhook handler must handle 100+ retries for same event |
| **Flash Sale Queue Length** | <500 users (above this, show "Out of stock" immediately) | Prevents 100K users waiting in queue for 10 units → UX disaster |
| **Image CDN Hit Rate** | >90% (CloudFront edge caching) | Product images rarely change → cache at edge for <10ms latency |
| **Cart Abandonment Rate** | 60-70% (industry average) | If >80% → UX issue (complex checkout) or pricing problem |

---

## 📝 **20-MINUTE WHITEBOARD TEMPLATE**

Use this structure when an interviewer says: *"Design an e-commerce platform like Amazon"*

### **Minutes 0-2: Requirements Gathering**

**Say to interviewer**:
> "The core challenge is inventory consistency — preventing overselling when thousands of users simultaneously try to buy limited-stock items. Let me clarify the scope."

**Ask**:
1. "Is this the full Amazon platform or specific subsystems?" → *Focus on core flow: search → cart → checkout → payment → order tracking*
2. "What scale?" → *10M MAU, 1M orders/day, 100K searches/sec peak*
3. "Flash sales with limited stock?" → *Yes, <100 units, 10K concurrent users*
4. "Consistency requirements?" → *Search: eventual OK. Checkout/inventory/payments: strong consistency required*

### **Minutes 2-4: Capacity Estimation**

**Say**:
> "Let me estimate storage and throughput."

**Write on board**:
```
Products: 100M × 5KB = 500GB (MongoDB)
Orders: 1M/day × 2KB = 2GB/day = 730GB/year (MySQL partitioned monthly)
Elasticsearch: 100M × 3KB indexed = 300GB, 10-node cluster
Redis: Cart (10M users × 2KB = 20GB) + cache ≈ 50GB total
Throughput: 100K searches/sec, 1K checkouts/sec peak, 10 orders/sec avg
```

### **Minutes 4-8: High-Level Architecture**

**Draw 4 layers** (top to bottom):

```
┌─────────────────────────────────────────────────────────┐
│ CLIENT: Mobile App / Web / Seller Portal                │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ API GATEWAY: Auth (JWT), Rate Limiting, Routing         │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ MICROSERVICES:                                          │
│ User | Product | Search | Cart | Checkout | Inventory  │
│ Order | Payment | Notification | Warehouse              │
└─────────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│ DATA STORES:                                            │
│ MongoDB (products) | PostgreSQL (inventory, cart)       │
│ MySQL (orders, payments) | Elasticsearch (search)       │
│ Redis (cache + locks) | Kafka (events) | S3 (images)    │
└─────────────────────────────────────────────────────────┘
```

**Say**:
> "Three zones of consistency: (1) Strong for checkout/inventory/payments (PostgreSQL ACID + Redis locks), (2) Eventual for search (CDC pipeline), (3) Async for post-checkout (Kafka events)."

### **Minutes 8-14: Deep Dive — Checkout Critical Path**

**Draw sequence diagram** showing:

1. **User**: Clicks "Checkout"
2. **Checkout Service**: Fetches cart → begins two-layer locking
3. **Redis**: `SETNX lock:inventory:{product_id} {session_id} EX 30` → returns 1 (acquired)
4. **PostgreSQL**: `SELECT qty, reserved_qty FROM inventory WHERE product_id=? FOR UPDATE` → row lock
5. **Check**: `available = qty - reserved_qty < cart_qty?` → If yes: ROLLBACK, release lock, return "Out of stock"
6. **Reserve**: `UPDATE inventory SET reserved_qty = reserved_qty + cart_qty`
7. **Create Order**: `INSERT INTO orders (..., status='PENDING_PAYMENT')`
8. **Release Redis Lock**: `DEL lock:inventory:{product_id}`
9. **Payment Intent**: Call Stripe, return `payment_url` to client
10. **User**: Completes payment at Stripe
11. **Stripe**: POST `/webhooks/payment` (HMAC signature)
12. **Payment Service**: Idempotency check (`SELECT * FROM payments WHERE order_id=?`) → if exists, return 200
13. **Transaction**: `INSERT payments; UPDATE orders SET status='PAYMENT_CONFIRMED'; UPDATE inventory SET qty=qty-1, reserved_qty=reserved_qty-1; DELETE cart_items; COMMIT;`
14. **Kafka**: Publish `payment.success`, `order.confirmed`

**Say**:
> "The key insight: reserved_qty is a soft hold. We don't deduct qty until payment succeeds. This prevents overselling (lock at reservation) and prevents stock leakage (only deduct after money received)."

### **Minutes 14-17: Data Model**

**Draw 3 tables**:

**inventory**:
```
product_id | qty | reserved_qty | available (virtual: qty - reserved_qty)
-----------|-----|--------------|---------------------------------------
PROD-123   | 10  | 3            | 7
```

**orders**:
```
order_id | user_id | status            | items (JSON) | payment_id
---------|---------|-------------------|--------------|------------
ORD-456  | USR-789 | PENDING_PAYMENT   | [{...}]      | NULL
ORD-456  | USR-789 | PAYMENT_CONFIRMED | [{...}]      | PAY-999
```

**payments** (UNIQUE order_id for idempotency):
```
payment_id | order_id | amount | status
-----------|----------|--------|--------
PAY-999    | ORD-456  | 149.99 | SUCCESS
```

**Say**:
> "UNIQUE constraint on payments(order_id) ensures idempotency. Webhook can be replayed 100 times — INSERT fails on duplicate, transaction rolls back, no double-charge."

### **Minutes 17-19: Event-Driven Architecture**

**Draw Kafka topics**:

```
product.changes  → [ES Indexer, Redis Cache Invalidator, Analytics]
order.created    → [Notification, Analytics]
payment.success  → [Notification, Warehouse, Inventory, Analytics]
order.shipped    → [Notification, Order Status]
```

**Say**:
> "Kafka decouples post-checkout workflow. Payment Service publishes payment.success, returns 200 immediately. Each consumer scales, fails, and retries independently. 7-day retention = audit trail."

### **Minutes 19-20: Failure Handling**

**Say**:
> "Three failure recovery mechanisms:
> 
> 1. **Redis lock auto-expires (30 sec)**: Service crash → lock released → next user can checkout
> 2. **Idempotent webhook** (UNIQUE order_id): Stripe retries → SELECT before INSERT → safe replay
> 3. **Background reconciliation cron**: Finds orders PENDING_PAYMENT >15 min → polls Stripe API → releases stuck inventory or confirms payment"

**Ask interviewer**:
> "Should I deep-dive into search (Elasticsearch + CDC), cart (cross-device sync), or scaling (10x users)?"

---

## ⚠️ **COMMON MISTAKES TO AVOID**

### **1. Saying "We use database transactions" without explaining the two-layer locking**

❌ **Why wrong**: Interviewer will ask: *"What happens when 10K users hit the database simultaneously?"* Your answer (transactions) doesn't address thundering herd.

✅ **Correct**: "We use Redis SETNX as a pre-filter to reject 9,999/10K users before they touch the database. The 1 winner proceeds to PostgreSQL FOR UPDATE for ACID guarantee."

---

### **2. Deducting inventory qty during checkout (before payment)**

❌ **Why wrong**: If payment fails, you've permanently deducted inventory. Next customer sees "Out of stock" for an item that's physically sitting in the warehouse.

✅ **Correct**: "We use reserved_qty pattern. During checkout, increment reserved_qty (soft hold). After payment.success webhook, decrement both qty and reserved_qty (actual deduction). Payment fails? Decrement reserved_qty only (stock restored)."

---

### **3. Writing to both MongoDB and Elasticsearch in the same request**

❌ **Why wrong**: Tight coupling. If Elasticsearch is down, MongoDB writes fail → sellers can't upload products.

✅ **Correct**: "CDC pipeline. Product Service writes only to MongoDB. Oplog → Kafka → ES Indexer → Elasticsearch. Loose coupling. If ES down, MongoDB writes continue. Indexer catches up from Kafka offset."

---

### **4. Not explaining idempotency for payment webhooks**

❌ **Why wrong**: Interviewer will ask: *"Stripe retries webhooks. How do you prevent double-charge?"* If you don't mention UNIQUE constraint, you fail the interview.

✅ **Correct**: "UNIQUE constraint on payments(order_id). Webhook handler: SELECT before INSERT. If row exists with status='SUCCESS', return 200 OK (already processed, safe replay)."

---

### **5. Using session_id as the cart key instead of user_id**

❌ **Why wrong**: User logs in on mobile → different session → sees empty cart (even though they added items on desktop).

✅ **Correct**: "Cart is tied to user_id (not session). Cross-device sync: user logs in on any device, sees same cart (loaded from PostgreSQL). Redis caches HSET cart:{user_id}."

---

### **6. Forgetting to release the Redis lock in a finally block**

❌ **Why wrong**: If an exception is thrown after acquiring the lock but before releasing it, the lock stays held until expiry (30 sec) → inventory stuck.

✅ **Correct**: 
```python
try:
    redis.setnx(f"lock:inventory:{pid}", session_id, ex=30)
    # ... checkout logic ...
finally:
    redis.delete(f"lock:inventory:{pid}")  # Always release
```

---

### **7. Not handling the case where payment succeeds but webhook delivery fails**

❌ **Why wrong**: Inventory stays reserved forever. Stock leakage.

✅ **Correct**: "Background cron job runs every 60 sec. Finds orders PENDING_PAYMENT >15 min. Polls Stripe API to check payment status. If succeeded → manually trigger webhook handler. If failed → release reservation."

---

### **8. Using PostgreSQL full-text search instead of Elasticsearch**

❌ **Why wrong**: Interviewer will ask: *"Can PostgreSQL handle 100K searches/sec?"* (No.) *"Does it support fuzzy matching?"* (No.) *"Faceted aggregations?"* (Expensive GROUP BY.)

✅ **Correct**: "Elasticsearch pre-builds an inverted index. Supports fuzzy matching (labtop → laptop), relevance scoring (title^3), faceted aggregations (brand counts). 10-node cluster handles 100K QPS. PostgreSQL would fall over."

---

### **9. Claiming "eventual consistency is fine" for inventory**

❌ **Why wrong**: Inventory inconsistency = overselling = customer complaints, refunds, reputation damage.

✅ **Correct**: "Inventory requires strong consistency (ACID). Search and cache can be eventually consistent (1-2 sec lag acceptable). Rule: strong consistency for financial transactions, eventual for non-critical reads."

---

### **10. Not explaining what happens if the Redis lock expires while the transaction is still running**

❌ **Why wrong**: Interviewer will ask: *"Lock expires at 30 sec. Transaction takes 35 sec. What happens?"*

✅ **Correct**: "PostgreSQL row lock (FOR UPDATE) still holds. Even if another user acquires the Redis lock after 30 sec expiry, they'll block on SELECT FOR UPDATE until the first transaction commits. Two-layer locking provides belt AND suspenders."

---

## ✅ **FINAL SIGN-OFF CHECKLIST**

Before the interview, verify you can:

- [ ] **Draw the checkout sequence** (34 steps) on a whiteboard in 10 minutes
- [ ] **Explain two-layer locking** without notes (why Redis SETNX before PostgreSQL FOR UPDATE)
- [ ] **Derive available inventory**: `available = qty - reserved_qty` and walk through 3 states (checkout, payment success, payment fail)
- [ ] **Explain idempotent webhooks** (UNIQUE constraint + SELECT before INSERT)
- [ ] **Describe CDC pipeline**: MongoDB oplog → Kafka → ES Indexer → Elasticsearch (5 components, 1-2 sec lag)
- [ ] **Answer "Why MongoDB for products?"** (flexible schema, no ALTER TABLE for new categories)
- [ ] **Answer "Why PostgreSQL for inventory?"** (ACID, SELECT FOR UPDATE, row-level locks)
- [ ] **Answer "Why Kafka instead of REST calls?"** (loose coupling, async, independent failure/retry)
- [ ] **Handle 3 failure scenarios**: (1) Redis lock expires mid-transaction, (2) Payment succeeds but webhook lost, (3) Service crashes after reservation
- [ ] **Explain ON CONFLICT upsert** for cart race conditions (mobile + web simultaneous add)
- [ ] **Scale to 10x users** (horizontal scaling for services, sharding for databases, Redis cluster, ES cluster)
- [ ] **Recall 10 key numbers**: Lock TTL (30s), Payment timeout (15min), Cart cache TTL (7d), CDC lag (1-2s), Kafka retention (7d)

---

## 🎓 **CONGRATULATIONS!**

You've completed the E-Commerce Platform study guide. You now understand:

1. **Inventory consistency** (two-layer locking + reserved_qty pattern)
2. **Idempotent webhooks** (UNIQUE constraint prevents double-charge)
3. **CDC for search sync** (MongoDB oplog → Kafka → Elasticsearch)
4. **Event-driven decoupling** (Kafka publishes, consumers process independently)
5. **Flexible product schema** (MongoDB documents handle multi-category catalog)
6. **Cart race condition handling** (ON CONFLICT upsert for concurrent adds)
7. **Failure recovery** (auto-expiring locks, background reconciliation, webhook retries)

**Next Steps**:
1. Practice 3 mock interviews using the [20-Minute Whiteboard Template](#20-minute-whiteboard-template)
2. Review the 4 Draw.io diagrams in sequence (context → architecture → checkout flow → data model)
3. Answer the [10 Interview Q&A questions](#interview-qa-memorize-strong-answers) out loud (record yourself, watch for filler words)
4. Time yourself: Can you explain the checkout critical path in 6 minutes? (That's the real interview pressure test.)

**You're ready when**: You can design the system end-to-end on a whiteboard in 20 minutes, answer 3 follow-up questions, and never say "I don't know" for core concepts (inventory locking, webhooks, CDC).

---

**Good luck with your interview! 🚀**
