E-Commerce Platform (Amazon/Flipkart)

"Product search (Elasticsearch) → Cart management (Redis) → Inventory check (Redis lock) → Order placement → Payment (idempotency) → Order fulfillment (Kafka events)"

1. Functional Requirements

Feature 1: User should be able to search and finds products based on product title or names
Feature 2: User should be able to view the details of the product (description, image, available quantity, review)
Feature 3: User should place the select the quantity and move the item to cart
Feature 4: User should should be able to make the payment and do the checkout
Feature 5: User should be able to check the status of the order
Feature 6: Manage purchase of items having limited stock
2. Non-Functional Requirements

Scale
Orders per Second — 10 orders/second, 10M MAU (Monthly Active Users)
Products — 100M+ products across multiple categories
Search Queries — 100K+ searches per second during peak (sales events)
Performance & Availability
Low Latency — Searching - fast product search <500ms with filters
CAP Theorem — Highly available with respect to searching and viewing the items, and highly consistent with respect to placing the order
Inventory Consistency — Strong consistency for inventory updates - no overselling of limited stock items
Payment Reliability — Exactly-once payment processing with idempotency
3. Core Entities (Identify Core Entity)

Entity 1: User - Customer with user_id, name, email, password, address[], payment_methods[]
Entity 2: Product - Item with product_id, title, category, price, qty (quantity), currency, description, images[]
Entity 3: Cart - Shopping cart with cart_id, user_id, items (product_id, qty, price, currency)
Entity 4: Order - Purchase order with order_id, user_id, items (product_id, qty, price, currency), total, status
Entity 5: Checkout - Payment flow tracking
4. API Designing

Product Search & Details
GET /v1/product/search?q={searchTerm} — Search products → List<ProductId (Partial Info)> with pagination
GET /v1/product/{productId} — Get product details → all product ids with extra CRUD operations and return Details
Cart Management
POST /v1/cart/add — Add to cart {post body: all product ids + all other CRUD} → return cartId
GET /v1/cart/{userId} — Get cart items for user
Checkout & Payment
POST /v1/checkout — Initiate checkout {post body: all product ids with qty and price} → return orderId
POST /v1/payment — Process payment {post body: orderId}
GET /v1/status/{orderId} — Get order status
5. High Level Design (from Image)

Clients → API Gateway: Authentication, authorization, routing
User Service → User DB (MySQL): User profiles, authentication
Search Service → Elasticsearch: Product search with full-text and filters, Redis cache for hot queries
Product Service → Product DB (MongoDB - DocumentDB): Product catalog with flexible schema, CDC to Elasticsearch via Kafka
Cart Service → Cart DB (PostgreSQL): Cart state with items (product_id, qty, price, currency)
Inventory Service → Inventory DB (PostgreSQL): Stock tracking, source of truth for quantity, indexed on product_id
Order Status Service → Order DB (MySQL): Order lifecycle tracking
Checkout Service: Orchestrates inventory check (Redis lock) → payment → order creation
Payment Service → Payment DB: Payment transactions, Payment Gateway integration
Kafka: Event streaming (order.created, payment.success, inventory.updated, order.shipped)
Notification System: Consumes Kafka events, sends email/SMS/push notifications
Redis: Cart caching, inventory locking, search result caching
6. Deep Dive Design (Low Level - from Image)

Step 1: Product Search (Elasticsearch + CDC)
User searches: GET /v1/product/search?q=laptop&category=electronics&priceMax=1000&sortBy=rating
Search Service queries: Elasticsearch with full-text + filters
ES query: { 'query': { 'bool': { 'must': [ { 'multi_match': { 'query': 'laptop', 'fields': ['title^3', 'description', 'category'] } } ], 'filter': [ { 'term': { 'category': 'electronics' } }, { 'range': { 'price': { 'lte': 1000 } } } ] } }, 'sort': [ { 'rating': 'desc' } ], 'size': 20 }
CDC Pipeline (from image): Product DB (MongoDB) → Sync Kafka → CDC Consumer → Elasticsearch indexing
Why CDC?: Product updates (price, title, qty) automatically sync to ES within 1-2 seconds, maintains search index fresh
Caching: Popular searches cached in Redis with TTL=10 min, key: hash(query + filters + sort)
Response: [{ product_id, title, category, price, qty, currency, image_url, rating }]
Note from image: Product stored in MongoDB (flexible schema for different product types - mobiles have specs, books have authors, etc.)
Step 2: Product Details & Images
User views product: GET /v1/product/{product_id}
Product Service queries: MongoDB db.products.findOne({product_id: {product_id}})
Document structure: { product_id, title, category, price, qty, currency, description, images[], specifications: {...}, reviews_summary: {avg_rating, total_reviews} }
Images: Stored in S3, URLs in MongoDB, served via CDN (CloudFront) for fast global access
Reviews: Separate Reviews DB, aggregated ratings cached in Redis, detailed reviews fetched on-demand
Caching: Product details cached in Redis with TTL=30 min, invalidated on product updates via Kafka event
Step 3: Add to Cart (Redis + PostgreSQL)
User adds item: POST /v1/cart/add with {user_id, product_id, qty: 2}
Cart Service flow: (1) Validates product exists and qty available (query Inventory Service), (2) Updates cart in PostgreSQL: INSERT INTO cart_items (cart_id, user_id, product_id, qty, price, currency) ON CONFLICT (cart_id, product_id) DO UPDATE SET qty=qty+2, (3) Caches cart in Redis: HSET cart:{user_id} product:{product_id} '{qty: 2, price: 899, currency: USD}' with TTL=7 days
Cart DB schema (PostgreSQL - from image): cart_id, user_id, items (product_id, qty, price, currency)
Why PostgreSQL for cart?: ACID guarantees, relational structure (user → cart → items), supports complex queries
Get cart: GET /v1/cart/{user_id} → Check Redis first (HGETALL cart:{user_id}), if miss fetch from PostgreSQL and cache
Update quantity: PATCH /v1/cart/{cart_id}/items/{product_id} with {qty: 5} → updates both PostgreSQL and Redis
Remove item: DELETE /v1/cart/{cart_id}/items/{product_id} → removes from PostgreSQL and Redis HDEL
Step 4: Checkout - Inventory Check with Redis Lock (CRITICAL)
User initiates checkout: POST /v1/checkout with {cart_id, shipping_address_id, payment_method_id}
Checkout Service orchestration (from image shows 'check the stock availability before checkout'):
Step 1: Fetch cart items from Cart DB
Step 2: FOR EACH product in cart: Acquire Redis distributed lock: SETNX lock:inventory:{product_id} {checkout_session_id} EX 30 (30 second expiry)
Step 3: If lock acquired (SETNX returns 1): Query Inventory Service: SELECT qty FROM inventory WHERE product_id={product_id} FOR UPDATE (pessimistic lock)
Step 4: Validate qty >= cart_qty, if insufficient: Release lock (DEL lock:inventory:{product_id}), return error 'Product X has insufficient stock'
Step 5: If all products have sufficient stock: Reserve inventory (don't deduct yet): UPDATE inventory SET reserved_qty = reserved_qty + {cart_qty} WHERE product_id={product_id}
Step 6: Create order in PENDING_PAYMENT status: INSERT INTO orders (order_id, user_id, items, total, status='PENDING_PAYMENT', created_at)
Step 7: Release Redis locks: FOR EACH product DEL lock:inventory:{product_id}
Step 8: Return {order_id, payment_url} to client
Note: Redis lock prevents race condition where multiple users checkout last item simultaneously, Inventory DB has 'reserved_qty' column to hold stock during payment
Step 5: Payment Processing with Idempotency
User redirected to payment: Payment Gateway (Stripe/Razorpay) with payment_url
Payment Service (from image): Creates payment intent with idempotency_key=order_id
Payment Gateway processes: User enters card details, gateway charges card
Webhook: POST /webhooks/payment with {order_id, payment_id, status: 'success', amount}
Payment Service webhook handler: (1) Validates signature, (2) Idempotency check: SELECT * FROM payments WHERE order_id={order_id}, if exists return 200 (already processed), (3) BEGIN TRANSACTION; INSERT INTO payments (payment_id, order_id, amount, status='SUCCESS', timestamp); UPDATE orders SET status='PAYMENT_CONFIRMED', payment_id={payment_id}; COMMIT;
Deduct inventory (from image shows 'CDC to invalidate and update qty change'): UPDATE inventory SET qty = qty - {reserved_qty}, reserved_qty = reserved_qty - {reserved_qty} WHERE product_id IN ({order_product_ids})
Publish Kafka events: 'payment.success' and 'order.confirmed' topics with {order_id, user_id, items, total}
Image shows: Kafka → Consumer updates Payment info, triggers Notification System
Clear cart: DELETE FROM cart_items WHERE cart_id={cart_id} (order placed, cart no longer needed)
If payment fails: Webhook 'payment.failed' → Release reserved inventory: UPDATE inventory SET reserved_qty = reserved_qty - {cart_qty}, order status='PAYMENT_FAILED'
Step 6: Order Status Tracking (Kafka Event-Driven)
Order lifecycle: PENDING_PAYMENT → PAYMENT_CONFIRMED → PROCESSING → SHIPPED → OUT_FOR_DELIVERY → DELIVERED
Status updates via Kafka (from image): Order Status Service consumes 'order.confirmed', 'order.shipped', 'order.delivered' events
Warehouse system: Picks items, updates via POST /v1/orders/{order_id}/ship → Publishes 'order.shipped' to Kafka
Delivery partner: Updates location and status via API → Publishes 'order.out_for_delivery' to Kafka
User checks status: GET /v1/status/{order_id} → Order Status Service queries Order DB: SELECT status, tracking_id, estimated_delivery FROM orders WHERE order_id={order_id}
Real-time updates: WebSocket connection or polling (every 30s) for tracking updates
Notification flow (from image): Kafka events → Notification System → Email/SMS/Push: 'Order confirmed', 'Order shipped', 'Out for delivery', 'Delivered'
Step 7: Inventory Management & CDC (Source of Truth)
Inventory DB (PostgreSQL - from image): Indexed on product_id, columns: {product_id, qty, reserved_qty, warehouse_id, last_updated}
Inventory is 'Qty-source of truth' as noted in image - authoritative for stock levels
Stock updates: (1) New stock arrival: UPDATE inventory SET qty = qty + {new_stock} WHERE product_id={product_id}, (2) Publish Kafka 'inventory.updated' event
CDC pipeline (from image): Inventory DB → CDC (Change Data Capture) → Kafka → Updates Redis cache, Elasticsearch product qty
Redis caching: HSET inventory:{product_id} 'qty' {qty} 'reserved_qty' {reserved_qty} with TTL=5 min, used for quick availability checks
Low stock alerts: Background job monitors inventory.qty < threshold (e.g., 10 units) → notifies warehouse to restock
Overselling prevention: reserved_qty column ensures items in checkout but not yet paid don't show as available, actual deduction only after payment success
Step 8: Product Catalog Management (MongoDB - Flexible Schema)
Why MongoDB for products (from image shows 'MongoDB (DocumentDB)'): Different product categories have different attributes - Mobile (specs: RAM, storage, camera), Book (author, ISBN, publisher), Clothing (size, color, material)
Schema-less advantage: No need to define all possible attributes upfront, easy to add new product types
Example document: { product_id: 'LAPTOP_123', title: 'MacBook Pro', category: 'electronics', price: 1999, qty: 50, currency: 'USD', specs: { ram: '16GB', storage: '512GB SSD', processor: 'M3' }, images: ['s3://...'], brand: 'Apple', warranty: '1 year' }
Indexing: db.products.createIndex({product_id: 1}), db.products.createIndex({category: 1, price: 1}), db.products.createIndex({title: 'text', description: 'text'}) for basic search
CDC to Elasticsearch (from image): MongoDB oplog → Kafka → ES indexer, ensures search index always in sync with product catalog
Product updates: Seller updates price/qty via admin API → MongoDB updated → CDC pipeline syncs to ES and Redis within 1-2 seconds
Step 9: Search Optimization (Elasticsearch Architecture)
ES Index mapping: PUT /products { 'mappings': { 'properties': { 'product_id': {'type': 'keyword'}, 'title': {'type': 'text', 'analyzer': 'standard'}, 'description': {'type': 'text'}, 'category': {'type': 'keyword'}, 'price': {'type': 'float'}, 'qty': {'type': 'integer'}, 'rating': {'type': 'float'}, 'brand': {'type': 'keyword'}, 'images': {'type': 'keyword'} } } }
Synonyms: Configure analyzer with synonyms (laptop = notebook, mobile = phone) for better search relevance
Faceted search: Aggregations for filters: 'aggs': { 'brands': { 'terms': { 'field': 'brand' } }, 'price_ranges': { 'range': { 'field': 'price', 'ranges': [{'to': 500}, {'from': 500, 'to': 1000}, {'from': 1000}] } } } → Returns counts for UI filters
Autocomplete: Edge n-gram tokenizer for type-ahead suggestions, updates as user types (debounced 300ms)
Performance: ES cluster with 10 nodes, 5 primary shards, 1 replica per shard, handles 100K queries/sec during sales events
Caching: Redis caches top 10K search queries with results, TTL=10 min, serves 60-70% from cache
Step 10: System Integration via Kafka (Event-Driven Architecture)
Kafka topics (from image shows Sync Kafka connecting components):
Topic 1: 'product.updated' - Product catalog changes → consumed by ES indexer, cache invalidator
Topic 2: 'order.created' - New order placed → consumed by Inventory Service (reserve stock), Notification Service
Topic 3: 'payment.success' - Payment confirmed → consumed by Order Service (update status), Inventory Service (deduct stock), Notification Service
Topic 4: 'order.shipped' - Warehouse ships order → consumed by Order Status Service, Notification Service, Tracking Service
Topic 5: 'inventory.updated' - Stock levels changed → consumed by Product Service (update qty), ES indexer, Redis cache updater
Consumer groups: Each service has dedicated consumer group, enables horizontal scaling and fault tolerance
Event schema: {event_id, event_type, timestamp, payload: {...}, metadata: {source_service, correlation_id}}
Idempotent consumers: Use event_id to deduplicate, prevents duplicate processing if event replayed
Dead letter queue: Failed events moved to DLQ after 3 retries, manual investigation and replay
7. Database Schema Details (from Image)

User DB (MySQL - from image)
user_id — uuid PRIMARY KEY
name — varchar(255)
email — varchar(255) UNIQUE
password — varchar(255) (bcrypt hash)
address[] — JSON [{street, city, state, zip, country, is_default}]
Product DB (MongoDB/DocumentDB - from image)
product_id — string (unique identifier)
title — string (product name)
category — string (electronics, books, clothing)
price — float
qty — integer (available quantity)
currency — string (USD, EUR, INR)
description — string (long text)
images — array of strings (S3 URLs)
specifications — object (flexible schema - RAM, storage, author, ISBN, size, color, etc.)
Cart DB (PostgreSQL - from image)
cart_id — uuid PRIMARY KEY
user_id — uuid FK → Users
items — JSONB [{product_id, qty, price, currency}] or separate cart_items table
Cart_Items (PostgreSQL - normalized approach)
cart_id — uuid
product_id — uuid
qty — integer
price — decimal(10,2)
currency — varchar(3)
Composite PK — (cart_id, product_id)
Inventory DB (PostgreSQL - from image, 'Qty-source of truth')
product_id — uuid PRIMARY KEY, INDEXED
qty — integer (available stock)
reserved_qty — integer (reserved during checkout, not yet paid)
warehouse_id — uuid (location)
last_updated — timestamp
Index — INDEX on product_id for fast lookups during checkout
Order DB (MySQL - from image)
order_id — uuid PRIMARY KEY
user_id — uuid FK → Users
items — JSON [{product_id, qty, price, currency}]
total — decimal(10,2)
status — enum (PENDING_PAYMENT, PAYMENT_CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED)
payment_id — varchar(255)
shipping_address — JSON {street, city, state, zip}
created_at — timestamp INDEXED
Payment DB (from image)
payment_id — varchar(255) PRIMARY KEY (from gateway)
order_id — uuid FK → Orders, UNIQUE (idempotency)
timestamp — timestamp
status — enum (PENDING, SUCCESS, FAILED, REFUNDED)
amount — decimal(10,2)
Redis - Caching & Locks
cart:{userId} — HASH {product_id: {qty, price, currency}} TTL 7 days
product:{productId} — STRING (JSON product details) TTL 30 min
search:{hash(query)} — STRING (JSON search results) TTL 10 min
inventory:{productId} — HASH {qty, reserved_qty} TTL 5 min
lock:inventory:{productId} — STRING {checkout_session_id} EX 30 (distributed lock)
Elasticsearch - Product Index
product_id — keyword
title — text (analyzed for full-text search)
description — text
category — keyword (exact match for filters)
price — float
qty — integer (synced from Inventory via CDC)
rating — float
brand — keyword
8. Key Architectural Decisions from Image

Database Choices
User DB - MySQL — Why: ACID transactions for user accounts, relational integrity (user → addresses → orders)
Product DB - MongoDB — Why: Flexible schema for diverse product types (electronics, books, clothing have different attributes), easy to add new categories
Cart DB - PostgreSQL — Why: ACID guarantees for cart operations, relational structure (cart → items), supports complex queries
Inventory - PostgreSQL — Why: Source of truth for stock, requires ACID (strong consistency), supports SELECT FOR UPDATE (pessimistic locking)
Order DB - MySQL — Why: ACID transactions critical for orders, relational (order → items → payment), complex queries for reporting
CDC (Change Data Capture) from Image
Product → ES — MongoDB → Kafka → Elasticsearch indexer, keeps search up-to-date within 1-2s
Inventory → Redis — PostgreSQL → CDC → Kafka → Redis cache updater, invalidates and updates qty changes
Why CDC? — Decouples source DB from derived data stores (ES, Redis), eventual consistency acceptable for search/cache, enables independent scaling
Redis Lock Pattern (Critical for Inventory)
Lock Acquisition — SETNX lock:inventory:{product_id} {session_id} EX 30
Purpose — Prevents race condition where multiple users checkout last item simultaneously
Timeout — 30 seconds auto-expiry prevents deadlock if service crashes
Pattern — Acquire lock → Check DB stock → Reserve → Release lock (even on failure)
Kafka Event-Driven Architecture
Image shows — 'Sync Kafka' connecting Product, Inventory, Payment, Order, Notification services
Benefits — (1) Decouples services, (2) Async processing, (3) Event replay for debugging, (4) Scales independently per consumer
Topics — product.updated, order.created, payment.success, inventory.updated, order.shipped
9. Scaling & Optimization Techniques

Technique 1: Elasticsearch Sharding - Product index sharded by category or hash(product_id), enables parallel queries
Technique 2: Redis Caching - Cart (7d TTL), Product details (30min), Search results (10min), Inventory (5min), 70% cache hit rate
Technique 3: CDN for Images - Product images served via CloudFront, 95% cache hit, <50ms latency globally
Technique 4: Database Read Replicas - MySQL/PostgreSQL replicas for read queries (product views, order history), writes to primary
Technique 5: CDC Pipeline - MongoDB/PostgreSQL → Kafka → Elasticsearch/Redis, decouples data sync, eventual consistency
Technique 6: Redis Distributed Locks - Prevents inventory overselling during concurrent checkouts, SETNX with expiry
Technique 7: Kafka Event Streaming - Decouples order flow, async notifications, enables event replay and audit
Technique 8: Connection Pooling - API servers maintain 200 DB connections per pool, prevents exhaustion
Technique 9: API Rate Limiting - 1000 req/min per user, protects against abuse and DDoS
Technique 10: Database Partitioning - Partition orders table by month (order_date), improves query performance
Technique 11: Lazy Loading - Paginate search results (20 per page), infinite scroll, reduces initial payload
Technique 12: Inventory Reservation - reserved_qty column holds stock during checkout→payment flow, prevents overselling
10. Common Interview Questions

Q
How do you prevent overselling when multiple users try to buy the last item?
A
Multi-layer approach with distributed locks + database pessimistic locking (from image's 'check the stock availability before checkout' with Redis Lock):

(1) Redis distributed lock BEFORE inventory check: During checkout, FOR EACH product in cart: SETNX lock:inventory:{product_id} {checkout_session_id} EX 30, if SETNX returns 0 (lock exists) → wait and retry or return 'Another user is checking out this item, please wait', if returns 1 (acquired) → proceed to step 2,

(2) Database pessimistic lock: SELECT qty, reserved_qty FROM inventory WHERE product_id={product_id} FOR UPDATE (row-level exclusive lock),

(3) Validate: if qty < cart_qty → Release Redis lock, return 'Insufficient stock',

(4) Reserve inventory: UPDATE inventory SET reserved_qty = reserved_qty + {cart_qty} WHERE product_id={product_id}, this removes items from available pool but doesn't deduct yet (payment might fail),

(5) Release Redis lock: DEL lock:inventory:{product_id},

(6) Create order with status='PENDING_PAYMENT',

(7) Payment webhook success: UPDATE inventory SET qty = qty - {cart_qty}, reserved_qty = reserved_qty - {cart_qty}, now actually deduct from stock,

(8) Payment failure: UPDATE inventory SET reserved_qty = reserved_qty - {cart_qty}, release reservation. Why both locks?: Redis lock is fast (1-2ms) early rejection for concurrent requests (100 users trying to checkout simultaneously), PostgreSQL FOR UPDATE ensures ACID guarantees within transaction, prevents phantom reads. Lock expiry: Redis lock auto-expires in 30s if service crashes, prevents deadlock. Example: Product has qty=1, User A and User B both click checkout → User A's SETNX succeeds → User B's SETNX fails (waits) → User A reserves qty → User B's SETNX succeeds after A releases → User B checks qty=0 (reserved=1) → Returns 'Out of stock' → No overselling. Reserved_qty column explained: qty=10, reserved_qty=3 means 10 total in warehouse, 3 in active checkouts, 7 available for new purchases, prevents showing items as available when they're locked in checkout flow.

Q
How do you implement product search with filters (category, price, rating)?
A
Elasticsearch-based search with CDC sync (from image shows Product → Sync Kafka → Elasticsearch):

(1) Index mapping: PUT /products { 'mappings': { 'properties': { 'product_id': {'type': 'keyword'}, 'title': {'type': 'text', 'analyzer': 'standard', 'fields': {'keyword': {'type': 'keyword'}}}, 'description': {'type': 'text'}, 'category': {'type': 'keyword'}, 'price': {'type': 'float'}, 'rating': {'type': 'float'}, 'brand': {'type': 'keyword'}, 'qty': {'type': 'integer'} } } },

(2) CDC pipeline (from image): MongoDB product updates → Kafka 'product.updated' topic → ES indexer consumer → index.update(product_id, updated_fields), keeps ES in sync within 1-2 seconds,

(3) Search query: GET /v1/product/search?q=laptop&category=electronics&priceMin=500&priceMax=1500&rating>=4 → Backend builds: POST /products/_search { 'query': { 'bool': { 'must': [ { 'multi_match': { 'query': 'laptop', 'fields': ['title^3', 'description', 'brand'], 'type': 'best_fields' } } ], 'filter': [ { 'term': { 'category': 'electronics' } }, { 'range': { 'price': { 'gte': 500, 'lte': 1500 } } }, { 'range': { 'rating': { 'gte': 4 } } }, { 'range': { 'qty': { 'gt': 0 } } } ] } }, 'sort': [ { 'rating': 'desc' } ], 'from': 0, 'size': 20 },

(4) Scoring: 'title^3' boosts title matches 3x over description, relevance score combines text match + filters,

(5) Faceted search: Add aggregations: 'aggs': { 'categories': { 'terms': { 'field': 'category' } }, 'price_ranges': { 'range': { 'field': 'price', 'ranges': [{'to': 500}, {'from': 500, 'to': 1000}, {'from': 1000}] } }, 'brands': { 'terms': { 'field': 'brand', 'size': 20 } } } → Returns counts: {Electronics: 5000, Books: 3000, ...} for UI filter checkboxes,

(6) Autocomplete: Separate index with edge_ngram tokenizer, queries on every keystroke (debounced 300ms), suggests 'laptop', 'laptop bag', 'laptop stand',

(7) Synonyms: Configure analyzer: 'laptop' → ['laptop', 'notebook', 'portable computer'], improves recall,

(8) Caching: Redis caches popular queries (key: hash(query + filters + sort)) with TTL=10 min, serves 60-70% from cache,

(9) Performance: ES cluster 10 nodes, 5 primary shards (100M products / 5 = 20M per shard), query p95 <100ms. Why Elasticsearch over PostgreSQL full-text?: ES designed for full-text search with relevance scoring, fuzzy matching, synonyms, faceted search - PostgreSQL's tsvector can't match this. MongoDB vs PostgreSQL for products?: Image shows MongoDB (DocumentDB) because different product types have vastly different schemas (electronics: specs={RAM, processor}, books: {author, ISBN}, clothing: {size, color}) - flexible schema avoids sparse columns and NULL hell in relational DB.

Q
How do you manage shopping cart state across sessions and devices?
A
Hybrid Redis + PostgreSQL cart management (from image shows Cart DB PostgreSQL + Redis caching):

(1) Cart creation: User logs in → Check if cart exists: SELECT cart_id FROM carts WHERE user_id={user_id}, if not: INSERT INTO carts (cart_id, user_id, created_at) VALUES ({uuid}, {user_id}, now()),

(2) Add to cart: POST /v1/cart/add with {product_id, qty: 2},

(a) Validate product exists and has stock (query Product Service),

(b) PostgreSQL update: INSERT INTO cart_items (cart_id, product_id, qty, price, currency) VALUES ({cart_id}, {product_id}, 2, 899, 'USD') ON CONFLICT (cart_id, product_id) DO UPDATE SET qty = cart_items.qty + 2, updated_at = now(),

(c) Redis cache: HSET cart:{user_id} product:{product_id} '{qty: 2, price: 899, currency: USD, added_at: timestamp}' with TTL=7 days,

(3) Get cart:

(a) Check Redis: HGETALL cart:{user_id}, if hit: return cached data (1ms latency),

(b) If miss: Query PostgreSQL: SELECT ci.product_id, ci.qty, ci.price, ci.currency, p.title, p.image_url FROM cart_items ci JOIN products p ON ci.product_id = p.product_id WHERE ci.cart_id={cart_id}, then cache in Redis,

(4) Update quantity: PATCH /v1/cart/items/{product_id} with {qty: 5} → Update PostgreSQL and Redis atomically,

(5) Remove item: DELETE /v1/cart/items WHERE cart_id={cart_id} AND product_id={product_id} → Also Redis HDEL cart:{user_id} product:{product_id},

(6) Cross-device sync: Cart tied to user_id (not session_id), user logs in on mobile → same cart appears (fetched from PostgreSQL), Redis cache per user ensures fast access,

(7) Guest cart: For non-logged-in users, use session_id instead of user_id, store in Redis only with TTL=24h, on login: migrate guest cart to user cart: UPDATE cart_items SET cart_id={user_cart_id} WHERE cart_id={guest_cart_id},

(8) Cart expiry: Background job deletes carts inactive >30 days: DELETE FROM carts WHERE updated_at < now() - INTERVAL 30 DAY,

(9) Price updates: If product price changes after adding to cart, show both: 'Added at $899, now $799', let user decide to keep or remove,

(10) Stock validation at checkout: Before payment, re-validate all items still in stock, if any out of stock → remove from cart, notify user. Why PostgreSQL for cart?: ACID guarantees (cart updates must be reliable), survives Redis cache evictions (source of truth), supports complex queries (JOIN with products for enriched data), relational integrity (cart → items FK). Redis for performance: Cart reads are 10x more frequent than writes (user browses, views cart multiple times before checkout), Redis serves reads in <1ms, PostgreSQL ~50ms, at scale 10K concurrent users × 100 cart reads/min = 1M reads/min → Redis essential. TTL strategy: 7 days for active carts (user likely to return), auto-cleanup prevents memory bloat, PostgreSQL keeps cart forever (until user deletes account) for business analytics.

Q
How do you handle the checkout flow from cart to order confirmation?
A
Multi-step checkout orchestration (from image shows Checkout → Redis Lock → Kafka flow):

(1) Initiate checkout: POST /v1/checkout with {cart_id, shipping_address_id, payment_method_id},

(2) Checkout Service orchestration: Step 1: Fetch cart items: SELECT product_id, qty, price FROM cart_items WHERE cart_id={cart_id}, Step 2: Acquire distributed locks: FOR EACH product in cart: SETNX lock:inventory:{product_id} {checkout_session_id} EX 30, if any lock fails → abort, release acquired locks, return 'Product being checked out by another user', Step 3: Validate inventory (with DB lock): FOR EACH product: SELECT qty, reserved_qty FROM inventory WHERE product_id={product_id} FOR UPDATE, if qty < cart_qty → abort, release locks, return 'Product X out of stock', Step 4: Reserve inventory: UPDATE inventory SET reserved_qty = reserved_qty + {cart_qty} WHERE product_id={product_id}, Step 5: Calculate total: total = SUM(price × qty) + shipping_fee + tax, Step 6: Create order: BEGIN TRANSACTION; INSERT INTO orders (order_id, user_id, items, total, status='PENDING_PAYMENT', shipping_address, created_at); COMMIT;, Step 7: Release Redis locks: FOR EACH product: DEL lock:inventory:{product_id}, Step 8: Create payment intent: Call Payment Service → payment_gateway.createPaymentIntent({amount: total, currency, idempotency_key: order_id}), Step 9: Return to client: {order_id, payment_url, expires_at: now() + 15min},

(3) User completes payment: Redirected to Payment Gateway, enters card details, confirms payment,

(4) Payment webhook: POST /webhooks/payment with {order_id, payment_id, status: 'success'},

(a) Idempotency check: SELECT * FROM payments WHERE order_id={order_id}, if exists return 200 (already processed),

(b) BEGIN TRANSACTION; INSERT INTO payments (payment_id, order_id, amount, status='SUCCESS', timestamp); UPDATE orders SET status='PAYMENT_CONFIRMED', payment_id={payment_id} WHERE order_id={order_id}; UPDATE inventory SET qty = qty - {cart_qty}, reserved_qty = reserved_qty - {cart_qty} WHERE product_id IN ({order_product_ids}); DELETE FROM cart_items WHERE cart_id={cart_id}; COMMIT;,

(c) Publish Kafka events: 'payment.success' topic: {order_id, user_id, items, total, timestamp}, 'order.confirmed' topic: {order_id, items, shipping_address, warehouse_id},

(5) Kafka consumers:

(a) Notification Service → sends email/SMS 'Order confirmed',

(b) Inventory Service → updates Redis cache (invalidate product:{product_id} cache, update inventory:{product_id} qty),

(c) Warehouse Service → creates pick list for order fulfillment,

(6) Payment timeout: Background job checks orders with status='PENDING_PAYMENT' created >15 min ago → Release reserved inventory: UPDATE inventory SET reserved_qty = reserved_qty - {cart_qty}, order status → 'PAYMENT_TIMEOUT', send notification 'Checkout expired, items returned to stock',

(7) Failure scenarios:

(a) Inventory insufficient during reserve → abort checkout, don't create order, release locks,

(b) Payment fails (card declined) → webhook 'payment.failed' → release reserved_qty, order status='PAYMENT_FAILED',

(c) Service crash during checkout → Redis locks auto-expire after 30s, reserved_qty released by timeout job. Why this flow?:

(1) Locks prevent race conditions on limited stock,

(2) Reserved_qty column ensures stock not shown as available during 15min payment window,

(3) Idempotency prevents double charging on webhook replay,

(4) Kafka decouples payment from fulfillment (warehouse can be slow, doesn't block checkout),

(5) Transaction ensures atomicity (payment recorded + inventory deducted + cart cleared all-or-nothing). Performance: Average checkout time 2-3 seconds (lock acquisition ~10ms, DB queries ~50ms, payment intent creation ~200ms), can handle 10K checkouts/min with horizontal scaling of Checkout Service.

Q
How do you implement CDC (Change Data Capture) for syncing Product DB to Elasticsearch?
A
CDC pipeline for near real-time search index updates (from image shows Product → Sync Kafka → Elasticsearch):

(1) CDC source setup:

(a) MongoDB: Enable oplog (operations log) which records all write operations, use MongoDB Change Streams to listen: db.products.watch([{$match: {operationType: {$in: ['insert', 'update', 'replace', 'delete']}}}]),

(b) PostgreSQL (for other tables): Enable logical replication, use Debezium connector to capture WAL (Write-Ahead Log) changes,

(2) Kafka connector:

(a) MongoDB Change Stream → Kafka Connect MongoDB Source Connector → publishes to Kafka topic 'product.changes',

(b) Event schema: {operation: 'update', product_id: 'LAPTOP_123', fullDocument: {product_id, title, price, qty, ...}, timestamp},

(3) Elasticsearch indexer consumer:

(a) Kafka Consumer Group 'es-product-indexer' subscribes to 'product.changes',

(b) Consumer code: for event in kafka.consume(): if event.operation == 'insert' or 'update': es.index(index='products', id=event.product_id, body=event.fullDocument), elif event.operation == 'delete': es.delete(index='products', id=event.product_id),

(c) Batch indexing: Buffer 100 events, bulk index to ES every 2 seconds for efficiency: es.bulk(operations=[...]),

(4) Error handling:

(a) ES indexing fails → Log error, push event to DLQ (Dead Letter Queue), retry with exponential backoff,

(b) Kafka consumer lag monitoring: Alert if lag >1000 events (indexer falling behind), auto-scale consumer instances,

(5) Initial load: On first setup, bulk export all products from MongoDB → Elasticsearch: db.products.find().forEach(doc => es.index({...})), then start CDC to keep in sync,

(6) Consistency:

(a) Eventual consistency: Product updated in MongoDB → 1-2 seconds later appears in ES search, acceptable for e-commerce search,

(b) Ordering guarantee: Kafka partition by product_id ensures updates for same product processed in order,

(7) Performance:

(a) MongoDB oplog tail: <10ms latency to capture change,

(b) Kafka latency: ~50ms end-to-end,

(c) ES indexing: Bulk API can index 10K docs/sec,

(d) Total lag: Product update → searchable in 1-2 seconds,

(8) Why CDC over direct writes?:

(a) Separation of concerns: Product Service doesn't need to know about ES,

(b) Fault tolerance: If ES down, MongoDB still accepts writes, indexer catches up later,

(c) Replay: Can rebuild entire ES index from Kafka topic (retention 7 days),

(d) Multiple consumers: Same events used for Redis cache invalidation, analytics, audit logs. Alternative: Dual writes (Product Service writes to both MongoDB and ES) - bad because:

(1) Tight coupling,

(2) Transaction complexity (what if ES write fails?),

(3) Product Service needs to know search implementation. Real-world: Amazon uses similar CDC pipeline with Kinesis Streams, millions of product updates/hour, ES cluster 100+ nodes, <5 second lag p99.

Q
How do you design the payment integration with idempotency and webhook handling?
A
Payment flow with strong consistency guarantees (from image shows Payment Svc → Payment Gateway, Kafka → Consumer updates payment info):

(1) Payment initiation: Checkout Service calls Payment Service: POST /v1/payments with {order_id, amount: 1499.99, currency: 'USD', user_id, return_url},

(2) Payment Service creates intent:

(a) Generate idempotency_key = order_id (ensures same order can't be charged twice),

(b) Call Stripe/Razorpay API: stripe.paymentIntents.create({ amount: 149999, currency: 'usd', customer: stripe_customer_id, metadata: {order_id, user_id}, idempotency_key: order_id }),

(c) Stripe returns: {payment_intent_id, client_secret, status: 'requires_payment_method'},

(d) Store in Payment DB: INSERT INTO payments (payment_id, order_id, amount, currency, status='PENDING', created_at) VALUES ({payment_intent_id}, {order_id}, 1499.99, 'USD', now()),

(e) Return to client: {payment_url: 'https://checkout.stripe.com/...'},

(3) User payment flow: User redirected to Stripe checkout page, enters card details, Stripe processes (3D Secure if needed), on success: Stripe redirects back to return_url with payment_intent_id,

(4) Webhook handling (CRITICAL): Stripe sends POST /webhooks/payment with {type: 'payment_intent.succeeded', data: {object: {id: payment_intent_id, amount, status: 'succeeded', metadata: {order_id}}}},

(a) Signature validation: Extract stripe_signature header, verify HMAC: stripe.webhooks.constructEvent(payload, signature, webhook_secret), prevents replay attacks and unauthorized requests,

(b) Idempotency check: SELECT * FROM payments WHERE payment_id={payment_intent_id}, if status='SUCCESS' → return 200 OK (webhook already processed, duplicate event),

(c) Process payment: BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE; UPDATE payments SET status='SUCCESS', gateway_response=jsonb({webhook_payload}), updated_at=now() WHERE payment_id={payment_intent_id} AND status='PENDING'; if affected_rows == 0: ROLLBACK; return 200 (concurrent webhook, lost race); UPDATE orders SET status='PAYMENT_CONFIRMED', payment_id={payment_intent_id}, paid_at=now() WHERE order_id={order_id}; UPDATE inventory SET qty = qty - {cart_qty}, reserved_qty = reserved_qty - {cart_qty} WHERE product_id IN (SELECT product_id FROM order_items WHERE order_id={order_id}); COMMIT;,

(d) Publish Kafka events: 'payment.success': {order_id, payment_id, amount, timestamp}, 'order.confirmed': {order_id, user_id, items, total},

(e) Return 200 OK to Stripe (acknowledges receipt, Stripe won't retry),

(5) Kafka consumers (from image shows Kafka → Consumer):

(a) Notification Service: Sends email 'Payment successful, order #{order_id} confirmed',

(b) Inventory Service: Invalidates Redis cache for affected products,

(c) Order Fulfillment: Creates warehouse pick list,

(6) Failure scenarios:

(a) Payment declined: Webhook 'payment_intent.payment_failed' → UPDATE orders SET status='PAYMENT_FAILED', release reserved inventory, notify user,

(b) Webhook timeout: Stripe retries webhook 3 times (exponential backoff), if still fails → manual reconciliation via admin dashboard or polling Stripe API,

(c) Database transaction fails: ROLLBACK, return 500 to Stripe → Stripe retries webhook → eventual consistency,

(7) Idempotency guarantees:

(a) order_id as idempotency_key: User clicks 'Pay' multiple times → Stripe creates single payment_intent, subsequent calls return existing intent,

(b) Database UNIQUE constraint: UNIQUE INDEX on payments(order_id) ensures one payment per order, prevents double charge on race condition,

(c) Webhook deduplication: Check payment.status before processing, prevents double inventory deduction on webhook replay,

(8) Reconciliation: Nightly job compares Payment DB with Stripe API: stripe.paymentIntents.list({created: {gte: yesterday}}), flags discrepancies (payment succeeded in Stripe but order still PENDING_PAYMENT in DB) → admin investigation,

(9) Testing: Use Stripe test webhooks: stripe trigger payment_intent.succeeded, verify idempotency: send same webhook twice, assert order processed once. Security:

(1) Webhook signature verification prevents forged webhooks,

(2) HTTPS enforced for webhook endpoint,

(3) Rate limiting 100 webhooks/min per IP,

(4) Payment DB has separate credentials from other services (least privilege). Performance: Payment webhook processing <200ms (transaction + Kafka publish), can handle 1000 payments/sec with horizontal scaling, Kafka decouples from slow consumers (email sending).

Q
How do you track order status and implement real-time updates for users?
A
Event-driven order tracking with Kafka (from image shows Order DB → Kafka → Consumer → Notification System):

(1) Order lifecycle states: PENDING_PAYMENT → PAYMENT_CONFIRMED → PROCESSING (warehouse) → SHIPPED → OUT_FOR_DELIVERY → DELIVERED → (optional) RETURNED/CANCELLED,

(2) State transitions via Kafka events:

(a) Order creation: Checkout Service publishes 'order.created' to Kafka: {order_id, user_id, items, total, status: 'PENDING_PAYMENT', timestamp},

(b) Payment success: Payment webhook publishes 'payment.success' → Order Status Service consumes → UPDATE orders SET status='PAYMENT_CONFIRMED',

(c) Warehouse picks items: Warehouse system POST /v1/orders/{order_id}/process → publishes 'order.processing' → Order Status Service updates → status='PROCESSING',

(d) Shipment: Warehouse POST /v1/orders/{order_id}/ship with {tracking_id, carrier, estimated_delivery} → publishes 'order.shipped' → status='SHIPPED',

(e) Delivery partner updates: External API calls POST /v1/orders/{order_id}/tracking with {location, status} → publishes 'order.out_for_delivery' or 'order.delivered',

(3) Kafka topic structure: Topics: 'order.lifecycle' (all state changes), 'order.tracking' (location updates), Event schema: {event_id, event_type: 'order.shipped', order_id, timestamp, payload: {tracking_id, carrier, estimated_delivery, warehouse_location}},

(4) Consumer groups:

(a) Order Status Service: Updates Order DB with new status, stores history: INSERT INTO order_status_history (order_id, status, timestamp, metadata),

(b) Notification Service: Sends email/SMS/push for each status change: 'Order confirmed', 'Order shipped - Track here', 'Out for delivery - ETA 2 PM', 'Delivered',

(c) Analytics Service: Tracks metrics (avg delivery time, on-time rate),

(5) Real-time updates to user: Approach 1 - WebSocket: User opens order tracking page → Client establishes WebSocket: WS /v1/orders/{order_id}/track, Backend WebSocket Manager subscribes to Redis Pub/Sub channel: order:{order_id}:updates, Order Status Service publishes status changes to Redis channel, WebSocket Manager forwards to client's connection, Client displays real-time status and map (if location tracking), Approach 2 - Polling (fallback): Client polls GET /v1/status/{order_id} every 30 seconds, Less efficient but works if WebSocket unavailable,

(6) Order status API: GET /v1/status/{order_id} → Query Order DB: SELECT status, tracking_id, estimated_delivery, carrier FROM orders WHERE order_id={order_id}, Query status history: SELECT status, timestamp FROM order_status_history WHERE order_id={order_id} ORDER BY timestamp ASC, Response: {order_id, current_status: 'SHIPPED', tracking_id: 'TRK123', carrier: 'FedEx', estimated_delivery: '2025-01-25', history: [{status: 'PAYMENT_CONFIRMED', timestamp: '...'}, {status: 'PROCESSING', timestamp: '...'}, {status: 'SHIPPED', timestamp: '...'}]},

(7) Location tracking integration: Delivery partner API pushes updates: POST /v1/orders/{order_id}/location with {lat, lng, timestamp}, Order Tracking Service: Stores in time-series DB (InfluxDB): INSERT INTO delivery_locations (order_id, lat, lng, timestamp), Publishes to Redis Pub/Sub for real-time map updates, Client shows driver location on map, recalculates ETA using Google Maps Distance Matrix API,

(8) Notification customization: User preferences: Allow users to opt-in/out per notification type (email, SMS, push), send only opted-in channels, Template: Email template: 'Hi {user_name}, your order #{order_id} has been shipped! Track it here: {tracking_url}',

(9) Cancellation flow: User cancels: POST /v1/orders/{order_id}/cancel with {reason: 'changed_mind'}, Validation: if status in ['SHIPPED', 'OUT_FOR_DELIVERY', 'DELIVERED'] → return 400 'Cannot cancel, order already shipped', if status in ['PENDING_PAYMENT', 'PAYMENT_CONFIRMED', 'PROCESSING'] → allow cancellation, Update: UPDATE orders SET status='CANCELLED', cancelled_at=now(), cancellation_reason={reason}, Refund: If payment captured, initiate refund via Payment Gateway, Inventory: Release stock: UPDATE inventory SET qty = qty + {order_qty} WHERE product_id IN (order items), Kafka: Publish 'order.cancelled' → Notification Service sends 'Order cancelled, refund in 5-7 days',

(10) SLA monitoring: Track metrics: % orders delivered on time (status='DELIVERED' AND delivered_at <= estimated_delivery), avg time from PAYMENT_CONFIRMED to DELIVERED, % orders stuck in PROCESSING >24h (alert warehouse), Dashboard: Grafana shows real-time order funnel: PENDING

(100) → CONFIRMED

(80) → PROCESSING

(60) → SHIPPED

(40) → DELIVERED

(20). Performance: Kafka handles 100K order events/sec, Order Status Service processes events in <100ms, WebSocket can support 1M concurrent connections (scaled horizontally), Real-time updates delivered <500ms from event publish to user's screen.

Q
How do you handle high-volume flash sales (100K orders in 1 minute)?
A
Flash sale architecture with queuing and rate limiting:

(1) Pre-sale preparation:

(a) Product flagged as flash_sale=true with sale_start_time, sale_end_time, sale_quantity=1000,

(b) Cache warm-up: Pre-load product details, images to CDN and Redis 1 hour before sale,

(c) Database optimization: Dedicated read replicas for flash sale product queries, index on (product_id, sale_start_time),

(d) Auto-scaling: Scale Checkout Service 5x normal capacity (50 → 250 instances) 10 min before sale,

(2) Virtual waiting room:

(a) Before sale_start_time: Users directed to waiting room page (Cloudflare Waiting Room or custom), shows countdown timer, ~1M users in queue,

(b) At sale_start_time: Waiting room releases users in batches (1000 users/sec) with random token, prevents thundering herd on backend,

(c) Token validation: Backend accepts requests only with valid token from waiting room,

(3) Inventory handling:

(a) Pre-allocate inventory: CREATE TABLE flash_sale_inventory (product_id, queue_position INT, user_id NULL, status ENUM('available', 'reserved', 'sold'), reserved_at TIMESTAMP), INSERT 1000 rows with status='available', queue_position=1 to 1000,

(b) Checkout flow: User clicks 'Buy Now' → Backend: BEGIN TRANSACTION; SELECT queue_position, status FROM flash_sale_inventory WHERE product_id={product_id} AND status='available' ORDER BY queue_position LIMIT 1 FOR UPDATE SKIP LOCKED; if found: UPDATE SET status='reserved', user_id={user_id}, reserved_at=now(); COMMIT; else: ROLLBACK; return 'Sold out';

(c) SKIP LOCKED: PostgreSQL feature, if row locked by concurrent transaction, skip it and try next → prevents contention,

(4) Queue-based checkout:

(a) Add to Kafka queue: Instead of synchronous checkout, publish to Kafka 'checkout.requests' topic: {user_id, product_id, timestamp}, FIFO guarantee within partition (partition by product_id),

(b) Checkout workers: Consumer group of 50 workers processes queue at steady rate (100 checkouts/sec), prevents overwhelming Payment Gateway and Inventory DB,

(c) User sees: 'You're in line, position #523. Estimated wait: 5 min', WebSocket updates queue position in real-time,

(5) Timeout & release: Reserved inventory timeout: Background job every 10 sec: UPDATE flash_sale_inventory SET status='available', user_id=NULL WHERE status='reserved' AND reserved_at < now() - INTERVAL 5 MINUTE, if user doesn't complete payment in 5 min, inventory released for next user,

(6) Rate limiting:

(a) Per-user: 1 checkout attempt per 10 seconds (Redis: SETEX ratelimit:user:{user_id} 10 '1'), prevents bots spamming checkout,

(b) Per-IP: 10 requests/sec (API Gateway rate limit),

(c) CAPTCHA: Require CAPTCHA before checkout to filter bots,

(7) Caching strategy:

(a) Product details: Cached in Redis + CDN, 99% hit rate, only 1% hits DB (1M users × 0.01 = 10K DB queries vs 1M without cache),

(b) Inventory check: Redis counter for quick check: DECR flash_sale:{product_id}:remaining, if result >= 0: proceed to checkout (queue-based), if <0: return 'Sold out' immediately,

(c) Sync Redis with DB: Periodically (every 5 sec) update Redis counter from DB to correct drift,

(8) Payment optimization:

(a) Batch payment processing: Instead of 1 payment intent per order, batch 100 orders → 100 payment intents in parallel via Payment Gateway,

(b) Async confirmation: User sees 'Order placed, confirming payment...' immediately, payment processes in background,

(c) Webhook handling: Scale webhook consumer 10x to handle 1000 payment webhooks/sec,

(9) Database write optimization:

(a) Batch inserts: Buffer 100 order records, INSERT in single transaction every 2 seconds, reduces DB load 100x,

(b) Write to primary: All order writes to primary DB,

(c) Read from replicas: User order status queries hit replicas (eventual consistency acceptable, 1-2 sec lag),

(10) Post-sale cleanup:

(a) Disable rate limiting, scale down instances to normal capacity,

(b) Analyze metrics: % users got product, avg checkout time, peak load handled,

(c) Notify users on waitlist: 'Sold out in 3 minutes, sign up for restock alert'. Real-world example: Amazon Prime Day: 10M products on sale, 100K orders/minute peak, waiting room gates 5M concurrent users, queue-based checkout processes 50K checkouts/min, 99.9% uptime during sale, inventory sold out products in <10 min. Performance numbers: Without optimizations: 100K concurrent checkout requests → DB meltdown (10K writes/sec = deadlocks), Payment Gateway rate limit exceeded (max 1K/sec), overselling due to race conditions, With optimizations: Waiting room → 1K users/sec enter (controlled), Queue-based checkout → 100 checkouts/sec (sustainable), Redis SKIP LOCKED → no deadlocks, Batch DB writes → 500 writes/sec (comfortable), no overselling (flash_sale_inventory table serializes access).

Q
How do you implement product recommendations and personalization?
A
Multi-strategy recommendation engine:

(1) Data collection:

(a) User events: Kafka topics capture: 'product.viewed': {user_id, product_id, timestamp, session_id}, 'product.added_to_cart': {user_id, product_id, qty}, 'product.purchased': {user_id, product_id, order_id}, 'product.searched': {user_id, query, filters},

(b) Event processing: Apache Flink/Spark Streaming consumes events, aggregates per user: recent_views (last 20 products), recent_searches (last 10 queries), purchase_history (all purchases),

(c) Storage: User profile in Cassandra partitioned by user_id: {user_id, recent_views[], recent_searches[], purchase_history[], preferred_categories[], avg_price_range},

(2) Recommendation strategies: Strategy 1 - Collaborative filtering:

(a) User-based: Find similar users (Jaccard similarity on purchase history), recommend products those users bought: similar_users = users with >50% overlap in purchase_history, recommendations = products purchased by similar_users NOT purchased by current user,

(b) Item-based: Find similar products (cosine similarity on co-purchase matrix), recommend: 'Users who bought X also bought Y', co-purchase matrix: If product A and B purchased together 1000 times, similarity(A,B) = 1000 / sqrt(purchases(A) × purchases(B)),

(c) Matrix factorization: Offline training (ALS algorithm) on user-product interaction matrix (100M users × 10M products = sparse), factorizes into user_factors (100M × 50) and product_factors (10M × 50), recommendation_score(user, product) = dot(user_factors[user], product_factors[product]), top 100 products per user stored in Redis, refreshed daily, Strategy 2 - Content-based:

(a) Product embeddings: Use product metadata (title, description, category, brand) to generate embeddings (BERT/Sentence Transformers), 768-dimensional vector per product,

(b) User profile vector: Average of embeddings of products user viewed/purchased,

(c) Recommendation: Find products with highest cosine similarity to user profile vector, Elasticsearch kNN search with vector field for fast retrieval, Strategy 3 - Trending & popular:

(a) Global trending: Products with highest view_count in last 24h, shown to cold-start users (no history),

(b) Category trending: Top products per category, updated hourly,

(c) Personalized trending: Trending in user's preferred_categories[], Strategy 4 - Business rules:

(a) Margin-aware: Boost products with higher profit margin,

(b) Inventory-aware: Boost overstocked products (qty >1000),

(c) Promotional: Priority to products on sale or new arrivals,

(3) Hybrid ranking: Combine all strategies with weighted scoring: final_score = 0.4 × collaborative_score + 0.3 × content_score + 0.2 × trending_score + 0.1 × business_score, Sort products by final_score, return top 20,

(4) Real-time personalization:

(a) Home page: GET /v1/recommendations/home → returns: {trending_products: [...], recommended_for_you: [...], recently_viewed: [...], based_on_cart: [...]},

(b) Product detail page: GET /v1/recommendations/product/{product_id} → returns 'Similar products' and 'Frequently bought together',

(c) Search results: Personalize ranking based on user history (boost products in preferred_categories),

(5) Serving architecture:

(a) Pre-compute: Nightly batch job generates top 100 recommendations per user (collaborative filtering + content-based), stores in Redis: SET recs:{user_id} '[{product_id, score}, ...]' EX 86400,

(b) Real-time blending: On API call, fetch from Redis (pre-computed), blend with trending and business rules, apply diversity (don't show 10 similar products, mix categories),

(c) Fallback: If user has no history (cold start), show global trending + editorial curated,

(6) A/B testing:

(a) Experiment framework: Randomly assign users to variant A (old algo) or B (new algo), track metrics: click-through rate (CTR), add-to-cart rate, purchase conversion, revenue per user,

(b) Winner: If variant B has +5% conversion with p-value <0.05, roll out to 100%,

(7) Model training:

(a) Offline: Apache Spark job on S3 data lake (1 year of events, 10 TB), trains ALS model (collaborative filtering) weekly, trains BERT embeddings monthly,

(b) Feature store: Tecton/Feast stores features (user_avg_cart_value, product_category_popularity), used by ML models,

(c) Online: Low-latency feature serving from Redis (user recent_views) or PostgreSQL (user purchase_history),

(8) Privacy & ethics:

(a) No PII in logs: Hash user_id before storing in analytics DB,

(b) Diversity: Don't create filter bubbles, 20% recommendations should be from new categories (exploration vs exploitation),

(c) Explainability: Show reason: 'Based on your purchase of Product X' or 'Trending in Electronics',

(9) Performance:

(a) Recommendation API latency: <100ms p95 (Redis lookup + blending),

(b) Pre-computation: 100M users × 100 recs each = 10B recs/day, Spark job takes 4 hours,

(c) Storage: Redis 100GB for pre-computed recs + user profiles. Business impact: Recommendations drive 30-40% of e-commerce revenue, avg +25% cart size when users add recommended products, reduces bounce rate (users discover more relevant products).

Q
What's your disaster recovery and data consistency strategy for the e-commerce platform?
A
Multi-region DR with tiered consistency (from image shows strong consistency for orders, eventual for search):

(1) Architecture: Primary region us-east-1, Secondary us-west-2, Tertiary eu-west-1,

(2) Database replication:

(a) MySQL (User, Order DB): Primary in us-east-1, synchronous replication to us-west-2 (hot standby, <1s lag), asynchronous to eu-west-1 (warm standby, <10s lag), uses MySQL Group Replication or AWS Aurora Global Database,

(b) PostgreSQL (Cart, Inventory): Similar setup, streaming replication with replication slots,

(c) MongoDB (Product): Multi-region cluster with replica sets per region, write concern majority ensures data written to >=2 nodes, read preference nearest for low latency,

(3) Consistency tiers: Tier 1 - Strong consistency (inventory, orders, payments):

(a) Inventory updates: Synchronous replication to secondary before commit, ensures no overselling even during failover,

(b) Orders: ACID transactions with 2PC (two-phase commit) if spanning services,

(c) Payments: Idempotency + unique constraints prevent double charge,

(d) Trade-off: Slower writes (50-100ms extra for replication), acceptable for low-frequency operations, Tier 2 - Eventual consistency (product catalog, search, cache):

(a) Product updates: Written to primary MongoDB, replicated asynchronously (1-5s lag),

(b) Elasticsearch: CDC pipeline syncs within 1-2 seconds,

(c) Redis cache: Invalidated via Kafka events, stale cache for <10s acceptable,

(d) Benefit: Fast writes, high availability, user impact minimal (showing product at old price for 5s is fine),

(4) Failover procedure:

(a) Health checks: Route53 checks primary region every 30s (TCP, HTTP, database connectivity),

(b) Trigger: If 3 consecutive failures (90s) → initiate failover,

(c) Database promotion: us-west-2 promoted to primary (pg_ctl promote for PostgreSQL, aurora.promoteReadReplicaDBCluster for Aurora), takes 2-5 min,

(d) Application routing: Route53 updates DNS to point to us-west-2 load balancer,

(e) Kafka: MirrorMaker replicates events to secondary Kafka cluster, consumers switch to secondary,

(f) Data loss: <1s for synchronous replicas (Tier 1), <10s for async (Tier 2),

(5) Split-brain prevention:

(a) Fencing: Primary region fences itself (stops accepting writes) when it detects partition,

(b) Witness node: Third region (eu-west-1) acts as tiebreaker for quorum,

(c) Distributed lock: Consul/etcd ensures only one region is primary at a time,

(6) RTO/RPO targets:

(a) Tier 1 (orders, inventory): RPO <1 second (sync replication), RTO <5 minutes (automated failover),

(b) Tier 2 (products, search): RPO <10 seconds (async replication), RTO <5 minutes,

(c) Backups: RPO <1 hour (hourly backups to S3 Glacier), RTO <4 hours (manual restore from backup),

(7) Testing:

(a) Monthly DR drills: Simulate primary region failure, execute failover, verify RTO met, test backup restore,

(b) Chaos engineering: Randomly terminate instances (during low traffic 2-4 AM), verify auto-recovery,

(c) Tabletop exercises: Team walks through disaster scenarios (DDoS, data corruption, AWS outage),

(8) Data corruption recovery:

(a) Point-in-time recovery: Restore database to timestamp before corruption, supported for last 7 days,

(b) Logical backups: Daily mysqldump/pg_dump to S3, retention 30 days,

(c) Binary logs: MySQL binlogs for replay, PostgreSQL WAL archives,

(9) Kafka durability:

(a) Replication factor 3: Events written to >=3 brokers before acknowledged,

(b) min.insync.replicas=2: Producer write fails if <2 replicas available,

(c) Event retention 7 days: Can replay events to rebuild state,

(10) Monitoring & alerts:

(a) Replication lag: Alert if lag >5 seconds (Tier 1) or >30 seconds (Tier 2),

(b) Database metrics: Connections, query latency, deadlocks, slow queries,

(c) Application metrics: Order placement errors, payment failures, checkout abandonment rate,

(d) Business metrics: Revenue/hour, conversion rate, average order value (anomaly detection),

(11) Consistency validation:

(a) Reconciliation job: Nightly job compares Order DB with Payment DB, flags discrepancies (order PAYMENT_CONFIRMED but no payment record),

(b) Inventory audit: Compare Inventory DB qty with sum(order_items.qty) for sold products, detect leaks,

(c) Financial reconciliation: Match revenue in Order DB with bank settlements,

(12) Cost: Multi-region adds 60-80% infrastructure cost vs single region, Trade-off: $1M/month extra cost vs $10M revenue loss for 1-hour outage, insurance for business continuity. Example: Primary region outage at 2:00 PM → Health checks fail at 2:01:30 → Failover initiated at 2:02 → Database promoted at 2:05 → DNS updated at 2:06 → Users routed to secondary at 2:08 → Service fully restored, data loss <1s (in-flight orders may need retry), total downtime <8 minutes, business impact <$50K revenue loss vs $1M for 1-hour outage without DR.

11. Key Numbers to Remember

Scale & Volume (from image)
Orders per Second — 10 orders/second normal, 100 orders/sec peak (flash sales)
Monthly Active Users — 10M MAU
Products — 100M+ products in catalog
Search Queries — 100K queries/sec during peak events
Concurrent Users — 50K-100K concurrent users during normal hours, 1M during sales
Performance Requirements
Search Latency — <500ms for product search with filters (Elasticsearch p95)
Product Details — <200ms to load product page (Redis cache hit <50ms, DB miss <200ms)
Checkout Flow — <3 seconds from cart to payment URL (includes inventory lock + reservation)
Payment Processing — <5 seconds for payment gateway response
Redis Lock — <10ms to acquire distributed lock for inventory
Caching & TTL
Cart Cache — Redis TTL 7 days for active carts
Product Cache — Redis TTL 30 min (invalidated on product update via Kafka)
Search Cache — Redis TTL 10 min for popular queries, 60-70% hit rate
Inventory Cache — Redis TTL 5 min (synced from DB via CDC)
CDN Cache — Product images cached 24 hours at edge, 95% hit rate
Consistency & Locking
Redis Lock TTL — 30 seconds (prevents deadlock if service crashes)
Inventory Reservation — 5 minutes timeout (released if payment not completed)
Payment Timeout — 15 minutes from order creation to payment completion
CDC Lag — 1-2 seconds (Product DB → Kafka → Elasticsearch sync)
Database & Storage
Product Catalog — 100M products × 5 KB avg = 500 GB (MongoDB)
User Data — 10M users × 2 KB = 20 GB (MySQL)
Orders — 100M orders/year × 2 KB = 200 GB/year (partitioned monthly)
Elasticsearch — 100M products × 3 KB (indexed fields) = 300 GB, 10 nodes cluster
Business Metrics
Conversion Rate — 2-5% (searches → orders)
Cart Abandonment — 60-70% (items added but not purchased)
Average Order Value — $50-150 depending on category
Repeat Purchase Rate — 30-40% of users order again within 90 days
Key Interview Tips

⚠️
CRITICAL: Prevent inventory overselling with Redis distributed lock BEFORE database check. SETNX lock:inventory:{product_id} {session_id} EX 30. Follow with SELECT FOR UPDATE on inventory table. Use reserved_qty column to hold stock during checkout→payment flow.

⭐
Interviewers ALWAYS ask: 'How to prevent overselling?'. Answer: (1) Redis SETNX lock before inventory check, (2) PostgreSQL SELECT FOR UPDATE pessimistic lock, (3) reserved_qty column for checkout→payment window, (4) Deduct qty only after payment success webhook, (5) Lock auto-expires 30s to prevent deadlock.

💡
CDC pipeline (from image): Product DB (MongoDB) → Kafka → Elasticsearch indexer. Enables eventual consistency (1-2s lag) for search, decouples Product Service from search implementation, supports multiple consumers (ES, Redis cache, analytics).

⭐
Must mention: Image shows different DBs for different purposes - User (MySQL - ACID), Product (MongoDB - flexible schema), Cart (PostgreSQL - relational), Inventory (PostgreSQL - source of truth). Each chosen for specific characteristics.

⚠️
NEVER update inventory synchronously in checkout. Use reserved_qty during checkout, actual qty deduction only after payment.success webhook. Prevents stock lock if user abandons payment. Background job releases reserved_qty after 5-15 min timeout.

💡
Image shows Kafka event-driven: order.created, payment.success, inventory.updated, order.shipped. Decouples services (Notification, Analytics, Fulfillment consume independently), enables async processing, supports event replay for debugging.

⭐
Interviewers love: 'Checkout flow orchestration'. Walk through: Fetch cart → Acquire Redis locks → Validate inventory (SELECT FOR UPDATE) → Reserve stock (reserved_qty) → Create order PENDING_PAYMENT → Release locks → Payment webhook → Deduct qty → Publish Kafka events → Clear cart.

⚠️
NEVER use eventual consistency for payments and inventory. Strong consistency (ACID transactions) required. Image emphasizes: 'highly consistent with respect to placing the order'. Search can be eventual (1-2s lag acceptable).

💡
Flash sales optimization: Virtual waiting room gates users (1K/sec), queue-based checkout (Kafka), PostgreSQL SKIP LOCKED prevents contention, Redis counter for quick stock check, reserved_qty with 5-min timeout, batch DB writes (100 orders/txn).

⭐
Must explain: Payment idempotency. order_id as idempotency_key to Stripe, UNIQUE constraint on payments(order_id), webhook signature validation, status check before processing. Prevents double charge on retry, handles webhook replay gracefully.

system-design
e-commerce
Amazon
Flipkart
Elasticsearch
product-search
inventory-management
distributed-locks
Redis-SETNX
cart-management
CDC-pipeline
Kafka-events
payment-idempotency
MongoDB-flexible-schema
PostgreSQL-ACID
flash-sales
order-tracking
webhook-handling
overselling-prevention
Part of the "System Design Complete Course" course · Interview With Bunny

Stay Updated
Subscribe to my Channel
Connect
"Let's have a coffee together..."
FIND ME EVERYWHERE

Philosophy
How to become successful.!!
Dream life() {
while(!succeed) {
try();
}
return dreamFulfilled();
}
@Copyright?? Really?  ·  If you want, I'll clone this website too... and give you the source code