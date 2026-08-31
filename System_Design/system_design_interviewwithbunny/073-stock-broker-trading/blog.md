Stock Trading Platform (Zerodha / Groww / Upstox)

"User places order → Order Svc validates → Kafka queue → Validator checks (funds/risk/balance) → Exchange Gateway → NSE/BSE matching engine → Trade executed → Kafka order_status → Portfolio Svc updates holdings → Notification sent → Real-time price via WebSocket (InfluxDB + Redis PubSub)"

1. Functional Requirements

Feature 1: Enable user registration, login, and KYC verification (Aadhaar, PAN card)
Feature 2: Support to view real-time stock prices, historical data, charts (candlestick, line graphs)
Feature 3: Allow users to verify/link their bank account for fund transfers and withdrawals
Feature 4: Provide user with a watchlist with real-time price updates for tracked stocks (WebSocket push)
Feature 5: Provide a dashboard to track current portfolio holdings, P&L (Profit & Loss), and performance metrics
Feature 6: Users can place orders: Market orders (immediate execution at current price), Limit orders (execute only at specified price or better), Stop-loss orders (trigger when price reaches threshold)
Feature 7: Order placement flow: Place buy/sell order → Limit user orders based on available funds → Order status updates (PENDING → VERIFIED → PLACED → EXECUTED/REJECTED)
Feature 8: Support batch list processing for multiple stocks (bulk operations, portfolio rebalancing)
2. Non-Functional Requirements

Scale & Performance
Scale — Handle high-frequency trades with millions of users, 8-10k stocks (NSE/BSE combined)
Trade Volume — Peak hours: 100K+ orders/minute during market volatility, normal: 10K orders/min
Latency — Order placement < 100ms, market data (updated stock value) < 50ms real-time push
Reliability & Consistency
Uptime — 99.99% availability during market hours (9:15 AM - 3:30 PM IST), system downtime more important than uptime
Wrong balance — Duplicate trade or stale price can lead to huge financial losses - consistency critical
Buy-Sell balance — Buy or sell orders should be highly available, no order should be lost
3. Core Entity

Entity 1: User - user_id, email, name, phone, kyc_status (PENDING/VERIFIED/REJECTED), pan_card, aadhaar_number, linked_bank_account, created_at
Entity 2: Stock - stock_symbol (RELIANCE, TCS, INFY), company_name, exchange (NSE/BSE), current_price, day_high, day_low, volume, market_cap, last_updated_at
Entity 3: Order - order_id, user_id, stock_symbol, order_type (MARKET/LIMIT/STOP_LOSS), trade_type (BUY/SELL), quantity, price (limit price for LIMIT orders, null for MARKET), status (PENDING/VERIFIED/PLACED/EXECUTED/REJECTED/CANCELLED), placed_at, executed_at, exchange_order_id
Entity 4: Trade - trade_id, order_id, stock_symbol, quantity, executed_price, executed_at, exchange (NSE/BSE), commission_fee
Entity 5: Portfolio - user_id, stock_symbol, quantity (shares owned), avg_buy_price, current_value, total_investment, profit_loss (calculated), last_updated_at
Entity 6: Watchlist - user_id, stock_symbols[] (array of tracked stocks like ['RELIANCE', 'TCS', 'INFY']), created_at, updated_at
Entity 7: Funds - user_id, available_balance (cash available for trading), locked_balance (funds locked in pending orders), total_balance, bank_account_id, last_deposit_at
4. API Designing

Users & Authentication
POST /auth/signup — User registration with email, phone, password
POST /auth/login — Login with credentials, returns JWT token
POST /auth/verify-kyc — Submit KYC documents (PAN, Aadhaar), triggers verification workflow
Market Data
GET /api/v1/stocks — List all stocks (paginated) with current prices, volume, change%
GET /api/v1/stocks/{symbol} — Get detailed stock info (OHLC, volume, market cap, historical data)
GET /api/v1/stocks/{symbol}/history — Historical price data (daily/weekly/monthly candles) for charts
Trading
POST /api/v1/orders — Place buy/sell order {stockSymbol, orderType, tradeType, quantity, price (for LIMIT)}
GET /api/v1/orders — List user orders with status, filters by date/status/stock
DELETE /api/v1/orders/{orderId} — Cancel pending order (only if status=PENDING or PLACED, not EXECUTED)
Portfolio & Funds
GET /api/v1/portfolio — Get user's holdings with current value, P&L, performance
GET /api/v1/portfolio/performance — Portfolio performance metrics (daily/monthly returns, total P&L)
POST /api/v1/funds/deposit — Initiate fund deposit from linked bank account
POST /api/v1/funds/withdraw — Withdraw funds to bank account (only available_balance, not locked)
GET /api/v1/funds/history — Fund transaction history (deposits, withdrawals, order locks)
Watchlist & Batch
GET /api/v1/watchlist — Get user's watchlist with real-time prices for tracked stocks
POST /api/v1/watchlist — Add stock to watchlist {stockSymbol: 'RELIANCE'}
DELETE /api/v1/watchlist/{stockSymbol} — Remove stock from watchlist
POST /api/v1/batch/validate/{stockId}/symbols — Batch validate multiple stock symbols (bulk operations)
5. High Level Design

Architecture: users/client → LB/API Gateway (Authentication, Authorization, Routing, Rate limiting, Round-robin) → Services → Databases
User Svc → UserDB: Registration, login, KYC verification (Aadhaar/PAN validation), session management
Price Tracker Svc → InfluxDB (time-series DB): Stores real-time stock prices, historical OHLC data, subscribes to Exchange data feed
WatchList Svc → Watch DB: User's tracked stocks, triggers WebSocket updates when price changes
Order Svc → Order DB + Kafka: Places orders, publishes to Kafka 'new_orders' topic, validates user input, tracks order status
Portfolio Svc → Trade DB: Calculates holdings, P&L, average buy price, updates on trade execution, PnL calculation logic
Payment Svc → Payment DB: Fund deposits/withdrawals via Payment Gateway (Razorpay, Stripe), bank account linking
Validator: Validates orders (sufficient funds, risk checks, duplicate order prevention) before sending to Exchange
Exchange Gateway: Communicates with NSE/BSE via FIX protocol, sends orders, receives execution confirmations, handles 400-500 symbols/legs per connection
Exchange (NSE/BSE): External matching engine, executes trades, sends order_status updates back via Kafka
Kafka: Event backbone - topics: new_orders (order placement), verified_orders (post-validation), order_status (execution updates), stock_price (real-time price feed)
WebSocket Gateway: Pushes real-time price updates to clients (watchlist, portfolio), subscribes to Redis PubSub (stock_price channel)
InfluxDB: Time-series DB for stock prices (high write throughput, efficient range queries for charts)
Redis PubSub: Real-time price updates (publish: stock_price updates, subscribe: WebSocket servers, low latency <10ms)
6. Deep Dive Design (Low Level)

Step 1: Real-Time Price Updates (WebSocket + Redis PubSub + InfluxDB)
Price Tracker Svc subscribes to Exchange data feed: NSE/BSE provides real-time price stream via WebSocket/FIX protocol, receives tick-by-tick updates for 8-10k stocks, Example update: {symbol: 'RELIANCE', price: 2458.75, volume: 125000, timestamp: '2026-01-26T10:30:45.123Z'}
Write to InfluxDB (time-series DB): INSERT into stock_prices measurement: {symbol: 'RELIANCE', price: 2458.75, volume: 125000, day_high: 2465.00, day_low: 2450.00, timestamp}, InfluxDB optimized for time-series: High write throughput (100K+ writes/sec), Efficient range queries for charts (1D, 1W, 1M, 1Y historical data), Automatic downsampling (store 1-min candles forever, aggregate to 5-min/1-hour/daily)
Publish to Redis PubSub: PUBLISH stock_price '{"symbol": "RELIANCE", "price": 2458.75, "change": +0.45%}', Channel: stock_price (global channel for all stock updates), Low latency: <10ms from Exchange → Redis PubSub → WebSocket clients
WebSocket Gateway subscribes: WebSocket servers (10+ instances) subscribe to Redis PubSub: SUBSCRIBE stock_price, On message received: Parse update, broadcast to connected clients watching that stock, Clients watching RELIANCE receive: {symbol: 'RELIANCE', price: 2458.75, change: +0.45%} instantly
Client connection: User opens app → WebSocket connection established: ws://api.trading.com/prices, Client sends watchlist: {action: 'subscribe', symbols: ['RELIANCE', 'TCS', 'INFY']}, Server filters updates: Only sends RELIANCE/TCS/INFY price changes to this client (not all 8-10k stocks), Efficient: Each client receives only watched stocks, reduces bandwidth 1000×
Step 2: Order Placement Flow (Market Order)
User places MARKET BUY order: POST /api/v1/orders with {stockSymbol: 'RELIANCE', orderType: 'MARKET', tradeType: 'BUY', quantity: 10}, MARKET order: Execute immediately at current market price (best available price)
Order Svc validation: (1) Check user authentication (JWT token valid), (2) Validate stock symbol: Query stock_symbols table, if not exists → return 400 'Invalid stock symbol', (3) Check market hours: if (currentTime < 9:15 AM OR currentTime > 3:30 PM IST) → return 400 'Market closed', (4) Check quantity: Must be positive integer, (5) Generate order_id (UUID)
Check available funds: Query Funds table: SELECT available_balance FROM funds WHERE user_id={user_id}, Current price: Query Redis cache: GET stock_price:RELIANCE → 2458.75, Estimated cost: quantity × price = 10 × 2458.75 = ₹24,587.50, Commission: ₹20 (flat fee), Total required: ₹24,607.50, If available_balance < ₹24,607.50 → return 400 'Insufficient funds'
Lock funds: BEGIN TRANSACTION, UPDATE funds SET available_balance = available_balance - 24607.50, locked_balance = locked_balance + 24607.50 WHERE user_id={user_id}, COMMIT, Ensures funds can't be used for other orders (prevents overdraft)
Insert order: INSERT INTO orders (order_id, user_id, stock_symbol: 'RELIANCE', order_type: 'MARKET', trade_type: 'BUY', quantity: 10, price: null, status: 'PENDING', placed_at: now())
Publish to Kafka: Kafka.send('new_orders', {orderId, userId, stockSymbol: 'RELIANCE', orderType: 'MARKET', tradeType: 'BUY', quantity: 10}), Response to user: 200 OK {orderId: 'ORD123', status: 'PENDING', message: 'Order placed successfully'}
Step 3: Order Validation & Exchange Submission
Validator consumes Kafka 'new_orders': Validator service (5 instances, consume from 50 partitions), Receives order: {orderId: 'ORD123', ...}
Validation checks: (1) Duplicate check: SELECT COUNT(*) FROM orders WHERE user_id={user_id} AND stock_symbol='RELIANCE' AND status IN ('PENDING', 'PLACED') AND placed_at > NOW() - INTERVAL '5 seconds', if count > 1 → reject as duplicate (user double-clicked submit), (2) Risk management: Check user's total exposure: SELECT SUM(quantity × price) FROM orders WHERE user_id={user_id} AND status IN ('PENDING', 'PLACED'), if exposure > 10× available_balance → reject (prevent excessive risk), (3) Circuit breaker: if stock price moved >10% in last 5 min → reject (market volatility protection), (4) Compliance: Check if user is blocked/restricted for trading this stock
If validation passes: UPDATE orders SET status='VERIFIED' WHERE order_id='ORD123', Publish to Kafka 'verified_orders': {orderId: 'ORD123', ...}
Exchange Gateway consumes 'verified_orders': Exchange Gateway subscribes to Kafka, receives verified order, Formats order in FIX protocol (Financial Information eXchange): FIX message: 35=D (NewOrderSingle), 55=RELIANCE (Symbol), 54=1 (Buy), 38=10 (Quantity), 40=1 (Market order), Sends via TCP to NSE/BSE matching engine
UPDATE orders SET status='PLACED', exchange_order_id={exchange_assigned_id} WHERE order_id='ORD123'
NSE/BSE matching engine: Matches BUY order with available SELL orders, Execution at best available price (e.g., ₹2459.00, slightly higher than cached price ₹2458.75), Sends execution confirmation back to Exchange Gateway
Step 4: Trade Execution & Order Status Updates
Exchange sends execution confirmation: FIX message: 35=8 (ExecutionReport), 150=2 (Filled), Execution details: {orderId: exchange_order_id, executedPrice: 2459.00, executedQuantity: 10, executedAt: timestamp}
Exchange Gateway publishes to Kafka: Kafka.send('order_status', {orderId: 'ORD123', status: 'EXECUTED', executedPrice: 2459.00, executedQuantity: 10, executedAt: timestamp}), Topic: order_status (consumed by Order Tracker Svc, Notification Svc, Portfolio Svc)
Order Tracker Svc updates order: UPDATE orders SET status='EXECUTED', executed_at=now() WHERE order_id='ORD123', INSERT INTO trades (trade_id, order_id, stock_symbol: 'RELIANCE', quantity: 10, executed_price: 2459.00, executed_at: now(), exchange: 'NSE', commission_fee: 20)
Update funds (unlock and deduct actual cost): Actual cost: 10 × 2459.00 = ₹24,590 (vs estimated ₹24,587.50, difference due to price movement), Total debit: ₹24,590 + ₹20 commission = ₹24,610, BEGIN TRANSACTION, UPDATE funds SET locked_balance = locked_balance - 24607.50 (unlock estimated), available_balance = available_balance - (24610 - 24607.50) = -2.50 (deduct difference), COMMIT, Final: User's cash balance reduced by ₹24,610
Portfolio Svc updates holdings: Consumes Kafka 'order_status', Check if user owns stock: SELECT quantity, avg_buy_price FROM portfolio WHERE user_id={user_id} AND stock_symbol='RELIANCE', If exists: UPDATE portfolio SET quantity = quantity + 10, avg_buy_price = ((prev_quantity × prev_avg_price) + (10 × 2459.00)) / (prev_quantity + 10) WHERE ..., Else (first purchase): INSERT INTO portfolio (user_id, stock_symbol: 'RELIANCE', quantity: 10, avg_buy_price: 2459.00, total_investment: 24590, last_updated_at: now())
Calculate P&L: Current price: GET stock_price:RELIANCE → 2460.00 (from Redis), current_value: 10 × 2460.00 = ₹24,600, profit_loss: 24600 - 24590 = +₹10 (unrealized gain), UPDATE portfolio SET current_value=24600, profit_loss=10
Step 5: Limit Order Flow
User places LIMIT SELL order: POST /api/v1/orders with {stockSymbol: 'TCS', orderType: 'LIMIT', tradeType: 'SELL', quantity: 5, price: 3500.00}, LIMIT order: Execute only when market price reaches ₹3500 (or higher for SELL, lower for BUY)
Order Svc validation: (1) Check user owns stock: SELECT quantity FROM portfolio WHERE user_id={user_id} AND stock_symbol='TCS', if quantity < 5 → return 400 'Insufficient holdings', (2) Validate limit price: Must be within ±10% of current market price (prevent erroneous orders like SELL at ₹1 or ₹100,000), (3) Lock shares: UPDATE portfolio SET quantity = quantity - 5, locked_quantity = locked_quantity + 5 (prevent selling same shares twice)
Insert LIMIT order: INSERT INTO orders (order_id, user_id, stock_symbol: 'TCS', order_type: 'LIMIT', trade_type: 'SELL', quantity: 5, price: 3500.00, status: 'PENDING', placed_at: now())
Publish to Kafka 'new_orders', Validator validates and publishes to 'verified_orders', Exchange Gateway sends to NSE/BSE
Exchange behavior: LIMIT order sits in order book until price condition met, If TCS price reaches ₹3500.00 → order matched with BUY order at that price, If price never reaches ₹3500 → order remains open (until cancelled or market closes), End of day: If not executed → order cancelled (day order) OR remains open (GTC - Good Till Cancelled, if specified)
Execution (when price hits ₹3500): Exchange sends 'EXECUTED' status → Kafka 'order_status', Order Tracker Svc updates order status='EXECUTED', Portfolio Svc: UPDATE portfolio SET locked_quantity = locked_quantity - 5 (unlock shares, already removed from available quantity), Funds Svc: UPDATE funds SET available_balance = available_balance + (5 × 3500 - commission) = +₹17,480 (credit proceeds)
Step 6: Notification Service (Order Status Updates)
Notification Svc consumes Kafka 'order_status': Receives: {orderId: 'ORD123', status: 'EXECUTED', stockSymbol: 'RELIANCE', ...}
Determine notification channels: Check user preferences: SELECT push_enabled, email_enabled, sms_enabled FROM user_preferences WHERE user_id={user_id}, If push_enabled: Send push notification via FCM/APNS
Push notification: FCM (Firebase): POST https://fcm.googleapis.com/v1/projects/.../messages:send with {token: user_device_token, notification: {title: 'Order Executed', body: 'Your BUY order for 10 shares of RELIANCE executed at ₹2459.00'}, data: {orderId: 'ORD123', stockSymbol: 'RELIANCE'}}, User's mobile app receives notification, tapping opens order details
In-app notification: WebSocket push: If user is online (active WebSocket connection), send: {type: 'ORDER_STATUS', orderId: 'ORD123', status: 'EXECUTED', stockSymbol: 'RELIANCE', executedPrice: 2459.00}, Real-time update in app (order status changes from 'PENDING' → 'EXECUTED')
Email notification (optional): Send email: Subject: 'Order Executed - RELIANCE', Body: 'Your BUY order for 10 shares of RELIANCE was executed at ₹2459.00. Total cost: ₹24,610 (including ₹20 commission).', SMTP via SendGrid/SES
Step 7: Portfolio Performance Calculation (PnL)
User views portfolio: GET /api/v1/portfolio
Portfolio Svc calculates real-time P&L: For each holding, fetch current price from Redis: GET stock_price:RELIANCE → 2460.00, Holding: {stock_symbol: 'RELIANCE', quantity: 10, avg_buy_price: 2459.00, total_investment: 24590}, Current value: 10 × 2460.00 = ₹24,600, Unrealized P&L: 24600 - 24590 = +₹10 (+0.04%), Day change: (current_price - prev_close) / prev_close × 100 = (2460 - 2455) / 2455 × 100 = +0.20%
Aggregate portfolio: Total investment: SUM(total_investment for all holdings) = ₹2,45,000, Current value: SUM(current_value for all holdings) = ₹2,48,500, Total P&L: 2,48,500 - 2,45,000 = +₹3,500 (+1.43%), Today's change: SUM(day change for all holdings weighted by current value)
Response: {holdings: [{stockSymbol: 'RELIANCE', quantity: 10, avgBuyPrice: 2459.00, currentPrice: 2460.00, currentValue: 24600, profitLoss: +10, profitLossPercent: +0.04%, dayChange: +0.20%}, ...], totalInvestment: 245000, currentValue: 248500, totalProfitLoss: +3500, totalProfitLossPercent: +1.43%}
7. Database Schema Details

Users (UserDB)
user_id — uuid PRIMARY KEY
email — varchar(255) UNIQUE
phone — varchar(15) UNIQUE
name — varchar(255)
password_hash — varchar(255) (bcrypt)
kyc_status — enum (PENDING, VERIFIED, REJECTED)
pan_card — varchar(10) UNIQUE (required for KYC)
aadhaar_number — varchar(12) (encrypted, required for KYC)
linked_bank_account — varchar(50) (account number for fund transfers)
created_at — timestamptz
Stocks (Stock master data)
stock_symbol — varchar(20) PRIMARY KEY (e.g., 'RELIANCE', 'TCS', 'INFY')
company_name — varchar(255) (Reliance Industries Limited)
exchange — enum (NSE, BSE)
current_price — decimal(10,2) (cached from Redis, updated every second)
prev_close — decimal(10,2) (previous day closing price)
day_high — decimal(10,2)
day_low — decimal(10,2)
volume — bigint (shares traded today)
market_cap — decimal(15,2) (in crores)
sector — varchar(100) (Technology, Finance, Energy, etc.)
last_updated_at — timestamptz
Orders (Order DB)
order_id — uuid PRIMARY KEY
user_id — uuid FK → Users
stock_symbol — varchar(20) FK → Stocks
order_type — enum (MARKET, LIMIT, STOP_LOSS)
trade_type — enum (BUY, SELL)
quantity — int (number of shares)
price — decimal(10,2) (limit price for LIMIT orders, null for MARKET)
status — enum (PENDING, VERIFIED, PLACED, EXECUTED, REJECTED, CANCELLED)
placed_at — timestamptz
executed_at — timestamptz (nullable, when trade executed)
exchange_order_id — varchar(50) (order ID from NSE/BSE)
Indexes — INDEX on (user_id, placed_at DESC), INDEX on (status, placed_at), INDEX on (stock_symbol, status)
Trades (Trade history)
trade_id — uuid PRIMARY KEY
order_id — uuid FK → Orders
stock_symbol — varchar(20)
quantity — int
executed_price — decimal(10,2) (actual execution price from exchange)
executed_at — timestamptz
exchange — enum (NSE, BSE)
commission_fee — decimal(8,2) (brokerage commission)
trade_type — enum (BUY, SELL)
Indexes — INDEX on (order_id), INDEX on (executed_at DESC) for recent trades
Portfolio (Holdings)
Composite PK — (user_id, stock_symbol)
user_id — uuid FK → Users
stock_symbol — varchar(20) FK → Stocks
quantity — int (shares owned, available for selling)
locked_quantity — int DEFAULT 0 (shares locked in pending SELL orders)
avg_buy_price — decimal(10,2) (weighted average purchase price)
total_investment — decimal(15,2) (quantity × avg_buy_price)
current_value — decimal(15,2) (quantity × current_price, calculated)
profit_loss — decimal(15,2) (current_value - total_investment, calculated)
last_updated_at — timestamptz
Calculation — P&L calculated on-the-fly using current price from Redis, not stored (stale data risk)
Funds (Cash balance)
user_id — uuid PRIMARY KEY FK → Users
available_balance — decimal(15,2) (cash available for trading)
locked_balance — decimal(15,2) (cash locked in pending BUY orders)
total_balance — decimal(15,2) (available_balance + locked_balance)
bank_account_id — varchar(50) (linked bank account for deposits/withdrawals)
last_deposit_at — timestamptz
last_withdrawal_at — timestamptz
Watchlist
user_id — uuid FK → Users
stock_symbols — text[] (array of stock symbols: ['RELIANCE', 'TCS', 'INFY'])
created_at — timestamptz
updated_at — timestamptz
Indexes — GIN index on stock_symbols for array containment queries
Payment Transactions (Payment DB)
transaction_id — uuid PRIMARY KEY
user_id — uuid FK → Users
type — enum (DEPOSIT, WITHDRAWAL)
amount — decimal(15,2)
status — enum (PENDING, COMPLETED, FAILED)
payment_gateway — varchar(50) (Razorpay, Stripe, UPI)
gateway_transaction_id — varchar(100) (external transaction ID)
created_at — timestamptz
completed_at — timestamptz (nullable)
InfluxDB (Time-series stock prices)
Measurement — stock_prices
Tags — symbol (indexed), exchange
Fields — price (float), volume (int), day_high (float), day_low (float)
Timestamp — nanosecond precision
Retention — 1-min candles forever, 5-min/1-hour/daily aggregated via continuous queries
Query example — SELECT mean(price) FROM stock_prices WHERE symbol='RELIANCE' AND time > now() - 1d GROUP BY time(5m)
Redis Cache
stock_price:{symbol} — STRING (current price) - stock_price:RELIANCE → '2458.75' (TTL 1 sec, refreshed constantly)
stock_price PubSub — CHANNEL - PUBLISH stock_price '{symbol, price, change}', WebSocket servers SUBSCRIBE
user_session:{token} — HASH (user session data) - TTL 24 hours
order_lock:{orderId} — STRING (distributed lock for order processing) - TTL 30 sec
Kafka Topics
new_orders — New order placements (50 partitions by user_id hash), consumed by Validator
verified_orders — Validated orders ready for exchange (10 partitions), consumed by Exchange Gateway
order_status — Order execution updates from exchange (50 partitions by order_id hash), consumed by Order Tracker, Portfolio Svc, Notification Svc
stock_price — Real-time price feed from exchanges (100 partitions by stock_symbol hash), consumed by Price Tracker Svc
8. Scaling & Optimization

Technique 1: Redis PubSub for real-time prices - Price updates published to stock_price channel (<10ms latency), WebSocket servers subscribe and push to clients, avoids polling (100K+ concurrent connections), scales horizontally (add more WebSocket servers)
Technique 2: InfluxDB time-series DB - Optimized for stock prices (100K+ writes/sec), automatic downsampling (1-min candles → 5-min → hourly → daily), efficient range queries for charts (1Y data in <100ms), retention policies (1-min data forever, aggregates auto-calculated)
Technique 3: Kafka event-driven architecture - Decouples order flow (Order Svc → Validator → Exchange Gateway → Order Tracker), async processing (user gets 200 OK immediately), enables horizontal scaling (add more consumers), guarantees order processing (at-least-once delivery)
Technique 4: Fund locking with transactions - Prevents overdraft: Lock funds on order placement (UPDATE available → locked in single transaction), Unlock on execution/cancellation, ACID guarantees (no race conditions), Isolation level: SERIALIZABLE for fund updates
Technique 5: Database sharding - Orders table sharded by user_id (user's orders on same shard, fast queries), Portfolio sharded by user_id (user's holdings together), 10 shards: each handles 100K users (total 1M users), Cross-shard: Only for admin queries (acceptable slow)
Technique 6: Read replicas for portfolio/watchlist - 1 master (writes: order execution, fund updates) + 5 read replicas (reads: portfolio view, watchlist, order history), Read/write split: Portfolio GET → replicas (95% traffic), Trade execution → master, Lag <1 sec (acceptable for portfolio view)
Technique 7: Exchange Gateway connection pooling - Maintain 400-500 persistent FIX connections to NSE/BSE, Connection per symbol group (RELIANCE, TCS, INFY on same connection), Reuse connections (avoid handshake overhead), Load balancing: Distribute orders across connections
Technique 8: Order validation pipeline - Multi-stage: (1) Duplicate check (Redis SET orderId EX 5, SETNX returns false if exists), (2) Fund check (query Funds table), (3) Risk check (total exposure limit), (4) Circuit breaker (price volatility), Parallel checks where possible (<50ms total validation)
Technique 9: WebSocket gateway auto-scaling - Auto-scale based on connections: if connections > 10K per server → add instance, Sticky sessions: User always connects to same server (maintains WebSocket state), Load balancer: Route by user_id hash (consistent routing)
Technique 10: Price caching strategy - Redis cache: Current price (TTL 1 sec, refreshed from InfluxDB/PubSub), Historical data: Cache popular queries (RELIANCE 1D chart → 5 min TTL), Cache warming: Pre-load top 100 stocks on server start, Hit rate: 99% for current prices (all trades use cached price)
Technique 11: Rate limiting - Per user: 10 orders/sec (prevent fat-finger errors, accidental rapid clicks), Per API endpoint: 100 req/sec per user (portfolio, watchlist), Global: 100K orders/min (circuit breaker if exceeded, system protection)
Technique 12: Async notification with queues - Notification Svc consumes Kafka 'order_status' async, User gets trade confirmation within 1 sec (push notification), Email/SMS queued for later (non-blocking), Failed notifications → retry with exponential backoff (DLQ after 3 attempts)
9. Common Interview Questions

Q
How do you ensure real-time price updates reach millions of users with <50ms latency?
A
Real-time price distribution with WebSocket + Redis PubSub:

(1) Price ingestion: Price Tracker Svc subscribes to NSE/BSE data feed (WebSocket/FIX protocol), receives tick-by-tick updates for 8-10k stocks, Example: {symbol: 'RELIANCE', price: 2458.75, volume: 125000, timestamp}.

(2) Dual write: Write to InfluxDB (time-series persistence): INSERT stock_prices (symbol='RELIANCE', price=2458.75, volume=125000, timestamp), Async write, high throughput (100K+ writes/sec), Used for historical charts, not real-time push. Publish to Redis PubSub: PUBLISH stock_price '{"symbol": "RELIANCE", "price": 2458.75, "change": +0.45%}', Fan-out to all subscribers instantly (<10ms), No persistence (in-memory pub/sub).

(3) WebSocket servers subscribe: 10 WebSocket gateway servers (horizontally scaled), Each server: SUBSCRIBE stock_price (Redis PubSub channel), Receives all price updates in real-time, Filters and pushes to connected clients.

(4) Client connections: User opens app → WebSocket connection: ws://api.trading.com/prices, Handshake: Client sends watchlist: {action: 'subscribe', symbols: ['RELIANCE', 'TCS', 'INFY']}, Server stores subscription: userConnections[userId] = {socket, symbols: ['RELIANCE', 'TCS', 'INFY']}.

(5) Selective push: Redis PubSub message received: {symbol: 'RELIANCE', price: 2458.75}, Server iterates connected users: for each user watching 'RELIANCE', send via WebSocket: socket.send({symbol: 'RELIANCE', price: 2458.75}), Only users watching RELIANCE receive update (not all 8-10k stock updates), Reduces bandwidth 1000× (each user watches ~10 stocks, not all 8-10k).

(6) Latency breakdown: Exchange → Price Tracker: 5ms (network), Price Tracker → Redis PubSub: 2ms (PUBLISH command), Redis PubSub → WebSocket server: 3ms (in-memory fan-out), WebSocket server → Client: 10ms (internet latency), Total: ~20ms (well under 50ms target).

(7) Scaling: Horizontal: Add more WebSocket servers (each handles 10K connections), Load balancer: Sticky sessions (user_id hash → same server), maintains WebSocket state, Redis PubSub: Single channel, all servers subscribe (fan-out), no coordination needed.

(8) Fallback: If WebSocket disconnects: Client auto-reconnects with exponential backoff (1s, 2s, 4s, max 30s), On reconnect: Re-subscribe to watchlist, fetch missed updates from REST API (GET /api/v1/stocks/{symbol}). Result: Sub-50ms real-time updates, scales to millions of concurrent users, efficient bandwidth usage (selective push), resilient (auto-reconnect on failure).

Q
How do you prevent overdraft when multiple orders are placed simultaneously?
A
Fund locking with database transactions and pessimistic locking:

(1) Problem: User has ₹50,000 available balance, Places 2 simultaneous MARKET BUY orders: Order A: Buy 20 RELIANCE @ ₹2459 = ₹49,180, Order B: Buy 5 TCS @ ₹3500 = ₹17,500, Total required: ₹49,180 + ₹17,500 = ₹66,680 > ₹50,000 (overdraft!), Without locking: Both orders check balance (₹50,000 > ₹49,180 ✓, ₹50,000 > ₹17,500 ✓), Both pass validation, both execute → overdraft by ₹16,680.

(2) Solution: Pessimistic locking with SELECT FOR UPDATE: Order A processing: BEGIN TRANSACTION, SELECT available_balance FROM funds WHERE user_id={user_id} FOR UPDATE (locks row, other transactions wait), available_balance = ₹50,000, Check: ₹50,000 >= ₹49,180 ✓ (pass), UPDATE funds SET available_balance = 50000 - 49180 = ₹820, locked_balance = 0 + 49180 = ₹49,180, COMMIT (releases lock).

(3) Order B processing (simultaneously): BEGIN TRANSACTION, SELECT available_balance FROM funds WHERE user_id={user_id} FOR UPDATE, Waits for Order A transaction to commit (row locked), Once Order A commits: reads available_balance = ₹820 (updated value), Check: ₹820 >= ₹17,500 ✗ (fail), ROLLBACK, Return error: 400 'Insufficient funds'.

(4) Transaction isolation: Isolation level: SERIALIZABLE (highest level), Prevents: Dirty reads (read uncommitted data), Non-repeatable reads (data changes mid-transaction), Phantom reads (new rows appear), Guarantees: Each transaction sees consistent snapshot.

(5) Alternative: Optimistic locking with version: funds table has version column (starts at 1), Order A: SELECT available_balance, version FROM funds WHERE user_id={user_id}, Read: balance=₹50,000, version=1, UPDATE funds SET available_balance=820, locked_balance=49180, version=2 WHERE user_id={user_id} AND version=1, If version still 1: update succeeds (1 row affected), If version changed (Order B updated first): update fails (0 rows affected), Retry with new version.

(6) Optimistic vs Pessimistic: Pessimistic (SELECT FOR UPDATE): Use when contention is high (many users trading simultaneously), Blocks concurrent updates (serializes), Guarantees correctness at cost of throughput. Optimistic (version check): Use when contention is low (rare simultaneous orders from same user), Allows concurrent reads, retry on conflict, Higher throughput, but retries add latency.

(7) Production choice: Use pessimistic locking for fund updates (correctness critical, can't overdraft), Use optimistic locking for portfolio updates (can tolerate retries, less critical). Result: No overdraft possible, ACID guarantees maintained, concurrent orders handled correctly, trade-off: slight latency increase for correctness (acceptable for financial transactions).

Q
Walk through complete order flow from placement to execution with all validations and state transitions.
A
Complete order flow (MARKET BUY order):

(1) User places order: POST /api/v1/orders {stockSymbol: 'RELIANCE', orderType: 'MARKET', tradeType: 'BUY', quantity: 10}.

(2) Order Svc validation: Check JWT token valid (user authenticated), Validate stock_symbol: SELECT EXISTS FROM stocks WHERE stock_symbol='RELIANCE', if not exists → 400 'Invalid stock', Check market hours: if currentTime NOT BETWEEN 9:15 AM AND 3:30 PM IST → 400 'Market closed', Check quantity: must be positive int, multiple of lot size (1 for equity), Generate order_id: UUID.

(3) Fund check: Query current price: Redis GET stock_price:RELIANCE → ₹2458.75, Estimated cost: 10 × 2458.75 + ₹20 commission = ₹24,607.50, Fund locking: BEGIN TRANSACTION, SELECT available_balance FROM funds WHERE user_id={user_id} FOR UPDATE, if available_balance < 24607.50 → ROLLBACK, return 400 'Insufficient funds', UPDATE funds SET available_balance -= 24607.50, locked_balance += 24607.50, COMMIT.

(4) Insert order: INSERT INTO orders (order_id, user_id, stock_symbol, order_type: 'MARKET', trade_type: 'BUY', quantity: 10, price: null, status: 'PENDING', placed_at: now()), Status: PENDING (initial state).

(5) Kafka publish: Kafka.send('new_orders', {orderId, userId, stockSymbol, orderType, tradeType, quantity}), Response to user: 200 OK {orderId: 'ORD123', status: 'PENDING'}.

(6) Validator consumes 'new_orders': Duplicate check: Redis SETNX order_lock:{orderId} 1 EX 30, if already exists (SETNX returns 0) → duplicate, reject, Risk check: Total exposure: SELECT SUM(quantity × price) FROM orders WHERE user_id={user_id} AND status IN ('PENDING','PLACED'), if exposure > 10× available_balance → reject (excessive risk), Circuit breaker: SELECT price FROM stock_prices WHERE symbol='RELIANCE' AND timestamp > NOW() - 5 MIN, if price volatility > 10% in 5 min → reject (market volatility), If all pass: UPDATE orders SET status='VERIFIED', Publish Kafka 'verified_orders': {orderId}.

(7) Exchange Gateway consumes 'verified_orders': Format FIX message (Financial Information eXchange): Tag 35=D (NewOrderSingle), Tag 55='RELIANCE' (Symbol), Tag 54=1 (Side: Buy), Tag 38=10 (Quantity), Tag 40=1 (OrdType: Market), Send via TCP to NSE matching engine, UPDATE orders SET status='PLACED', exchange_order_id={assigned_by_exchange}.

(8) NSE matching engine: Matches BUY order with best available SELL order

(s), Execution price: ₹2459.00 (market price at execution time, may differ from cached ₹2458.75), Sends FIX ExecutionReport: Tag 35=8, Tag 150=2 (ExecType: Filled), Details: {executedPrice: 2459.00, executedQuantity: 10}.

(9) Exchange Gateway receives execution: Publish Kafka 'order_status': {orderId, status: 'EXECUTED', executedPrice: 2459.00, executedQuantity: 10, executedAt: timestamp}.

(10) Order Tracker Svc consumes 'order_status': UPDATE orders SET status='EXECUTED', executed_at=now(), INSERT INTO trades (trade_id, order_id, stock_symbol, quantity: 10, executed_price: 2459.00, executed_at: now(), exchange: 'NSE', commission_fee: 20).

(11) Fund update: Actual cost: 10 × 2459 + 20 = ₹24,610 (vs estimated ₹24,607.50), BEGIN TRANSACTION, UPDATE funds SET locked_balance -= 24607.50 (unlock estimated), available_balance -= (24610 - 24607.50) = -2.50 (deduct difference), COMMIT.

(12) Portfolio Svc consumes 'order_status': Check existing holding: SELECT quantity, avg_buy_price FROM portfolio WHERE user_id={user_id} AND stock_symbol='RELIANCE', If new holding: INSERT INTO portfolio (user_id, stock_symbol, quantity: 10, avg_buy_price: 2459.00, total_investment: 24590), If existing: UPDATE portfolio SET quantity += 10, avg_buy_price = (prev_qty × prev_avg + 10 × 2459) / (prev_qty + 10), total_investment = quantity × avg_buy_price.

(13) Notification Svc consumes 'order_status': Push notification via FCM: {title: 'Order Executed', body: 'RELIANCE BUY 10 @ ₹2459.00'}, WebSocket push (if user online): {type: 'ORDER_STATUS', orderId, status: 'EXECUTED'}. State transitions: PENDING (order created, funds locked) → VERIFIED (validations passed) → PLACED (sent to exchange) → EXECUTED (trade confirmed) OR REJECTED (validation failed, funds unlocked). Result: End-to-end order flow with validations, fund locking prevents overdraft, state tracking enables user visibility, Kafka decouples stages for scalability.

Key Interview Tips

⚠️
CRITICAL: Fund locking with SELECT FOR UPDATE mandatory to prevent overdraft. NEVER check balance and update in separate queries (race condition). Use single transaction with pessimistic lock. Isolation level SERIALIZABLE for fund updates. Duplicate trade or stale price = huge financial losses.

⭐
Real-time prices: Exchange → Price Tracker → InfluxDB (persist) + Redis PubSub (fan-out) → WebSocket servers (subscribe) → Clients (selective push). Sub-50ms latency. WebSocket scales horizontally (sticky sessions), Redis PubSub handles fan-out to 10+ servers instantly.

💡
State transitions: PENDING (created, funds locked) → VERIFIED (validation passed) → PLACED (sent to exchange) → EXECUTED (trade confirmed). Track status in orders table + Kafka 'order_status' topic. Enables user visibility, retry logic, audit trail.

⭐
Order validation pipeline: (1) Duplicate check (Redis SETNX), (2) Fund check (SELECT FOR UPDATE), (3) Risk check (total exposure limit), (4) Circuit breaker (price volatility >10% in 5min). Multi-stage prevents invalid orders reaching exchange. <50ms total validation.

⚠️
NEVER calculate P&L and store in DB. Current value = quantity × current_price (from Redis). Calculate on-the-fly when user views portfolio. Storing creates stale data risk (price changes every second). Only store: quantity, avg_buy_price, total_investment (static until trade).

💡
InfluxDB time-series: Optimized for stock prices (100K+ writes/sec). Automatic downsampling: 1-min candles → 5-min → hourly → daily (continuous queries). Retention forever for 1-min data. Efficient range queries for charts (1Y data <100ms). Don't use SQL DB for time-series.

⭐
Exchange communication: FIX protocol (Financial Information eXchange) via TCP. Maintain 400-500 persistent connections (connection pool per symbol group). Format order: Tag 35=D (NewOrderSingle), Tag 55=symbol, Tag 54=side (1=Buy,2=Sell), Tag 38=quantity, Tag 40=type (1=Market,2=Limit). Receive ExecutionReport: Tag 35=8.

system-design
stock-trading
zerodha
