# Stock Trading Platform — Zerodha / Groww / Upstox
> Online commission-free platform for trading and monitoring of stocks.

---

# PAGE 1 — Title & Rapid Answer Script

## What This Topic Is Really About

Two services live side-by-side with **opposite CAP requirements**:
- **Market data (price feed)** — 100M users reading prices → must be highly **Available** (AP)
- **Order placement / fund management** — wrong balance or duplicate trade = financial loss → must be highly **Consistent** (CP)

The design challenge: deliver stock prices to millions of users in <50ms **while** guaranteeing no two orders overdraft the same account, and no order is lost.

---

## Rapid Answer Script (speak this in 2-3 minutes)

```
"I'd split this into microservices with a strict CAP split.

 Consistency > Availability for trading (from the image):
 A wrong balance or duplicate trade causes huge financial loss.
 But viewing the stock price should be highly available — a user
 seeing a price 100ms stale is fine; a user being double-charged is not.

 PRICE PATH (AP):
 Price Ingester Svc subscribes to NSE/BSE data feed → writes to InfluxDB
 (time-series, historical charts) and publishes to Redis PubSub.
 WebSocket servers subscribe to Redis PubSub → push to client.
 Latency: Exchange → client in ~20ms, well under 50ms target.

 ORDER PATH (CP):
 User places order → Order Svc locks funds (SELECT FOR UPDATE, SERIALIZABLE)
 → publishes to Kafka 'new_orders' → Validator checks (KYC, funds, risk,
 duplicates via Redis SETNX) → Kafka 'verified_orders' → Exchange Gateway
 → NSE/BSE via FIX protocol → execution confirmation → Kafka 'order_status'
 → Order Tracker + Portfolio Svc + Notification Svc.

 Order state machine:
 PENDING → VERIFIED → PLACED → EXECUTED (or REJECTED)

 The key design insight is the fund-locking transaction:
 Lock funds when order is PENDING to prevent overdraft.
 Settle actual cost when EXECUTED (price may differ slightly from estimate).
 Auto-unlock if REJECTED or CANCELLED.

 For the exchange: we maintain 400-500 persistent FIX protocol connections
 to NSE/BSE grouped by symbol, not one connection per order."
```

---

# PAGE 2 — Glossary

| Term | Simple definition | Example |
|---|---|---|
| FIX Protocol | Financial Information eXchange — binary TCP protocol for order messages | Tag 35=D = NewOrderSingle (place order), Tag 35=8 = ExecutionReport |
| MARKET order | Execute immediately at best available price | BUY 10 RELIANCE at whatever price is available now |
| LIMIT order | Execute only at a specified price or better | SELL 5 TCS only if price reaches ₹3500 |
| STOP-LOSS | Trigger when price hits a threshold | If RELIANCE drops to ₹2400, sell automatically |
| Matched order | Buyer and seller agree on price → trade executed | BUY 10 @ 2459 matched with SELL 10 @ 2459 |
| Order book | NSE/BSE internal queue of all pending buy/sell orders | Sorted by price; best bid matches best ask |
| SELECT FOR UPDATE | SQL pessimistic lock — blocks concurrent transactions | Lock funds row before deducting (prevents overdraft) |
| SERIALIZABLE | Highest SQL isolation level — fully serial execution | Two simultaneous fund deductions → one waits, one fails |
| Fund locking | Split balance into available_balance + locked_balance | Place ₹25K BUY order → ₹25K moves to locked until executed |
| Redis PubSub | In-memory channel fan-out — no persistence | PUBLISH stock_price → 10 WebSocket servers receive instantly |
| InfluxDB | Time-series database — optimized for timestamped values | Stock price every second → downsampled to 1-min candles |
| WebSocket | Persistent bi-directional TCP connection | Server pushes price updates to browser without client polling |
| Sticky session | Load balancer always routes user to same server | WebSocket connection must stay on same server (state) |
| KYC | Know Your Customer — PAN + Aadhaar verification | User must be KYC verified before placing orders |
| Circuit breaker | Reject orders if price moves >10% in 5 min | Market protection during extreme volatility |
| locked_quantity | Shares locked in pending SELL orders | User can't sell same shares twice while SELL order is pending |
| Unrealized P&L | Profit/loss on holdings not yet sold | Current value − total investment (calculated on-the-fly from Redis price) |
| Exchange Gateway | Internal service bridging platform ↔ NSE/BSE | Formats FIX messages, maintains 400-500 persistent connections |

WHY ORDER BOOK EXISTS? (Beginner Explanation)
  Think of a fruit market where buyers write on one side of a chalkboard ("I'll buy
  10 kg mangoes for ₹50/kg") and sellers write on the other ("I'll sell 10 kg for ₹50/kg").
  The order book is that chalkboard — buyers sorted by highest bid price, sellers sorted
  by lowest ask price. When the best buyer price meets the best seller price, a trade fires.
  Problem it solves: without it, buyers and sellers have no central place to find each other.
  Every buyer would have to individually contact every seller — impossible at millions of
  orders per second across 8,000 stocks.
  Why the alternative is worse: direct matching without a central queue means the same shares
  could be "sold" to two buyers simultaneously, or buyer and seller never find each other at all.

WHY MARKET ORDER vs LIMIT ORDER DISTINCTION? (Beginner Explanation)
  Market order = "Buy me 10 RELIANCE RIGHT NOW at whatever price they're currently selling."
  You value speed over price — just get it done. The exchange fills it immediately at best price.
  Limit order = "Buy me 10 RELIANCE, but ONLY if the price drops to ₹2400."
  You value price over speed — the order waits in the order book until your condition is met.
  Problem it solves: traders have different goals — a fund rebalancing deadline needs execution
  NOW; a long-term investor wants a specific entry price and is happy to wait days.
  System design impact: market orders execute and vanish instantly; limit orders must be stored
  in the exchange's order book for hours or days and checked against every incoming price tick.
  Why both matter: an exchange with only market orders would have wildly unpredictable prices
  during panic events; limit orders provide liquidity and act as a natural price stabilizer.

---

# PAGE 3 — CAP Theorem Split (from image)

```
CAP: Consistency >> Availability (image explicitly states this)

"Correctness is more important than uptime.
 A wrong balance, duplicate trade, or stale price can lead to huge financial losses."

┌──────────────────────────────────────────────────────────────────────────────┐
│  Feature               │ CAP       │ Why                                    │
├──────────────────────────────────────────────────────────────────────────────┤
│ View stock price        │ AP        │ Stale by 100ms is fine. User reading   │
│ (market data)           │           │ price does not lose money.             │
│                         │           │ Must be "highly available" (image).    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Place order / lock funds│ CP        │ Two simultaneous orders cannot both    │
│                         │           │ pass if funds are insufficient.        │
│                         │           │ Overdraft = financial loss.            │
├──────────────────────────────────────────────────────────────────────────────┤
│ Order validation        │ CP        │ Duplicate order must be caught.        │
│                         │           │ Risk limits must be enforced.          │
├──────────────────────────────────────────────────────────────────────────────┤
│ Portfolio P&L           │ Eventual  │ Current value recalculated using Redis │
│                         │           │ price on every view. Never stored      │
│                         │           │ (stale data risk — price changes/sec). │
├──────────────────────────────────────────────────────────────────────────────┤
│ Trade execution         │ CP        │ At-most-once execution per order.      │
│                         │           │ Idempotency key = order_id.            │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# PAGE 4 — Requirements (from image)

```
FUNCTIONAL REQUIREMENTS:
  FR1: User registration, login, KYC verification (PAN + Aadhaar)
  FR2: View real-time stock prices, historical data, charts
  FR3: Watchlist — add stocks, see real-time updates
  FR4: Place / modify / cancel market and limit orders with status updates
  FR5: Dashboard — current holdings, trade history, PnL, performance insights
  FR6: Fund management — deposit, withdraw, view history

NON-FUNCTIONAL REQUIREMENTS (from image):
  Scale:    High-frequency trades, millions of users, 8-10k stocks (NSE+BSE)
  CAP:      Consistency >> Availability
            Wrong balance / duplicate trade / stale price = huge financial losses
            BUT: viewing stock price should be highly available
  Latency:  Order placement < 100ms
            Market data (updated stock value) < 50ms
  Uptime:   99.99% during market hours (9:15 AM – 3:30 PM IST)

WHY LOW LATENCY (MICROSECONDS) MATTERS IN TRADING? (Beginner Explanation)
  Stock prices change hundreds of times per second. If your app shows RELIANCE at
  ₹2458 but by the time your order reaches NSE the price is ₹2465, you overpaid ₹70
  on 100 shares. That is real money lost to "stale price" — traders call this slippage.
  Professional algorithmic traders fire thousands of orders per second. If your system
  is even 10ms slower than theirs, they buy all the cheap shares before your order arrives —
  retail users always end up with the worse price fill.
  Problem it solves: <50ms price feed ensures users trade on prices accurate enough to
  matter; <100ms order placement means the price you see is roughly the price you get.
  Why the alternative is worse: a 500ms price delay means you are trading on a price that
  is half a second old — during high volatility, that is dozens of price changes behind.

SCALE NUMBERS:
  8-10k     stock symbols (NSE+BSE combined)
  100K+     orders/minute at peak (market volatility)
  10K       orders/minute normal
  400-500   FIX protocol connections to exchange (per Exchange Gateway)
  ~20ms     end-to-end price update latency (Exchange → client)
```

---

# PAGE 5 — Core Entities (from image + blog)

```
ENTITY 1: User (UserDB — from image)
  user_id         UUID PRIMARY KEY
  email           VARCHAR UNIQUE
  mobile          VARCHAR UNIQUE
  name            VARCHAR
  password_hash   VARCHAR(255)          (bcrypt — from blog)
  pan_card        VARCHAR(10) UNIQUE    (required for KYC, encrypted)
  aadhaar_number  VARCHAR(12)           (optional, encrypted)
  kyc_status      ENUM(PENDING, VERIFIED, REJECTED)
  partner_detail  VARCHAR               (broker partner reference — from image)
  linked_bank_account VARCHAR(50)       (for fund transfers — from blog)
  balance          DECIMAL              (summary field)
  created_at      TIMESTAMPTZ

ENTITY 2: Stock
  stock_symbol  VARCHAR(20) PRIMARY KEY (RELIANCE, TCS, INFY)
  company_name  VARCHAR(255)
  exchange      ENUM(NSE, BSE)
  current_price DECIMAL(10,2)          (cached from Redis, not source of truth)
  prev_close    DECIMAL(10,2)
  day_high      DECIMAL(10,2)
  day_low       DECIMAL(10,2)
  volume        BIGINT
  market_cap    DECIMAL(15,2)
  sector        VARCHAR(100)
  last_updated_at TIMESTAMPTZ

ENTITY 3: Order (Order DB — from image)
  order_id      UUID PRIMARY KEY
  user_id       UUID FK → Users
  stock_id      UUID FK → Stocks
  order_type    ENUM(MARKET, LIMIT, STOP_LOSS)
  trade_type    ENUM(BUY, SELL)
  price         DECIMAL(10,2)          (limit price; NULL for MARKET orders)
  quantity      INT
  trade_id      UUID FK → Trades       (set on EXECUTED — shown in image LLD)
  status        ENUM(PENDING, VERIFIED, PLACED, EXECUTED, REJECTED, CANCELLED)
  placed_at     TIMESTAMPTZ
  executed_at   TIMESTAMPTZ
  exchange_order_id VARCHAR(50)        (assigned by NSE/BSE)

ENTITY 4: Trade (Trade DB — historical execution records)
  trade_id      UUID PRIMARY KEY
  order_id      UUID FK → Orders
  stock_symbol  VARCHAR(20)
  trade_type    ENUM(BUY, SELL)        (from blog.md)
  quantity      INT
  executed_price DECIMAL(10,2)         (actual exchange price — may differ from limit)
  executed_at   TIMESTAMPTZ
  exchange      ENUM(NSE, BSE)
  commission_fee DECIMAL(8,2)

ENTITY 5: Portfolio (Holdings)
  Composite PK: (user_id, stock_symbol)
  quantity      INT                    (available shares for selling)
  locked_quantity INT DEFAULT 0        (shares locked in pending SELL orders)
  avg_buy_price DECIMAL(10,2)          (weighted average)
  total_investment DECIMAL(15,2)       (quantity × avg_buy_price)
  ← current_value and profit_loss calculated ON THE FLY from Redis price

ENTITY 6: Watchlist (Watch DB — from image)
  userId        UUID
  watchlists    List<Watchlist>
  ─────────────────────────────
  Watchlist:
    id, userId, name, List<Symbol>
    stockSymbols (Set<String>)
  ─ Blog schema alternative: stock_symbols text[] with GIN index
    CREATE INDEX idx_watchlist_symbols ON watchlist USING GIN(stock_symbols)
    (enables fast array containment: WHERE 'RELIANCE' = ANY(stock_symbols))

ENTITY 7: Funds (Cash balance)
  user_id       UUID PRIMARY KEY
  available_balance DECIMAL            (cash free for trading)
  locked_balance    DECIMAL            (cash locked in pending BUY orders)
  total_balance     DECIMAL            (= available + locked)
  bank_account_id   VARCHAR
  last_deposit_at   TIMESTAMPTZ

ENTITY 8: Payment (Payment DB — image + blog combined)
  transaction_id   UUID PRIMARY KEY          (from blog)
  user_id          UUID FK → Users
  type             ENUM(DEPOSIT, WITHDRAWAL) (from blog)
  amount           DECIMAL
  status           ENUM(PENDING, COMPLETED, FAILED)
  payment_gateway  VARCHAR(50)               (Razorpay, Stripe, UPI)
  gateway_transaction_id VARCHAR(100)        (external transaction ID — from blog)
  currency         VARCHAR
  description      TEXT
  metadata         JSONB
  created_at       TIMESTAMPTZ
  completed_at     TIMESTAMPTZ               (from blog)
  ─ Image fields: PostPaym structure (user_id, amount, status, created_at,
    currency, gateway, description, metadata, timestamp) — all covered above
```

---

# PAGE 6 — API Design (from image)

```
USERS & AUTH:
  POST /auth/signup          Register with email, phone, password
  POST /auth/login           Login → returns JWT token
  POST /auth/verify-kyc      Submit PAN + Aadhaar → triggers KYC workflow

MARKET DATA:
  GET  /api/v1/stocks                    List all stocks (pagination)
  WS   /api/v1/stocks/{symbol}           Stock details (WebSocket — live price)
  GET  /api/v1/stocks/{symbol}/history   Historical data (OHLC candles for charts)

TRADING:
  POST   /api/v1/orders                  Place buy/sell order
  GET    /api/v1/orders                  List user orders (filters: date, status, stock)
  GET    /api/v1/orders/{order_id}       Order status
  DELETE /api/v1/orders/{order_id}       Cancel order (only PENDING or PLACED, not EXECUTED)

PORTFOLIO:
  GET  /api/v1/portfolio              Holdings summary + total P&L
  GET  /api/v1/portfolio/holdings     Detailed holdings per stock
  GET  /api/v1/portfolio/positions    Open positions
  GET  /api/v1/portfolio/performance  Daily/monthly returns, total P&L chart

WATCHLIST:
  GET    /api/v1/watchlists                           User's watchlists
  POST   /api/v1/watchlists                           Create new watchlist
  POST   /api/v1/watchlists/{watchlistId}/symbols     Add stock to watchlist
  DELETE /api/v1/watchlist/{stockSymbol}              Remove stock from watchlist

BATCH (bulk operations):
  POST /api/v1/batch/validate/{stockId}/symbols       Batch validate multiple stock symbols

FUNDS:
  POST /api/v1/funds/deposit     Initiate deposit from linked bank
  POST /api/v1/funds/withdraw    Withdraw to bank (only available_balance)
  GET  /api/v1/funds/history     Transaction history

EXAMPLE — Place Market Order:
  POST /api/v1/orders
  {
    "stockSymbol": "RELIANCE",
    "orderType": "MARKET",
    "tradeType": "BUY",
    "quantity": 10
  }
  Response 200:
  { "orderId": "ORD123", "status": "PENDING", "message": "Order placed successfully" }
```

```
MISSING REST ENDPOINTS (not in image — standard for interview completeness):

MARKET DATA (REST fallback):
  GET  /api/v1/stocks/{symbol}            Single stock details + current quote (REST fallback on WebSocket reconnect)

FUNDS:
  GET  /api/v1/funds/balance              Current balance: available_balance, locked_balance, total_balance

TRADING:
  PATCH /api/v1/orders/{order_id}         Modify a pending order (change quantity or limit price; only if status=PENDING)

REAL-TIME (WebSocket):
  WS   /ws/v1/orders/{user_id}           Real-time order status stream — server pushes PENDING → VERIFIED → EXECUTED to client
```

> **WHY GET /api/v1/stocks/{symbol}?**
> The existing WS endpoint delivers the live price, but WebSocket connections drop. PAGE 9 of this guide explicitly references `GET /api/v1/stocks/{symbol}` as the REST fallback on reconnect: "Fetch missed updates via REST: GET /api/v1/stocks/{symbol}". Without a REST version of the single-stock quote, the client has no way to recover stale state when it reconnects.

> **WHY GET /api/v1/funds/balance?**
> The FUNDS section has deposit, withdraw, and transaction history — but no way to read the current balance. A trading app must display `available_balance` vs `locked_balance` on the dashboard before a user places an order. Without this endpoint, the funds section is effectively write-only from the client's perspective.

> **WHY PATCH /api/v1/orders/{order_id}?**
> FR4 explicitly states "place / **modify** / cancel orders." Modify means changing quantity or limit price on a `PENDING` order before it is forwarded to the exchange. Once status reaches `PLACED` (sent via FIX to NSE/BSE), modification requires a cancel-and-replace flow — this PATCH handles only the `PENDING` window.

> **WHY WS /ws/v1/orders/{user_id}?**
> PAGE 12B describes pushing order status over WebSocket when the user is online: `{type: 'ORDER_STATUS', orderId: 'ORD123', status: 'EXECUTED'}`. The existing WS `/api/v1/stocks/{symbol}` handles only price feeds. A separate order-status channel is needed so the UI transitions PENDING → VERIFIED → EXECUTED in real time without the client having to poll `GET /api/v1/orders/{order_id}` repeatedly.

---

# PAGE 7 — High Level Architecture (from image)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   STOCK TRADING PLATFORM — HIGH LEVEL DESIGN                │
└─────────────────────────────────────────────────────────────────────────────┘

  users/client
       │
       ▼
  ┌────────────────────────────────────┐
  │        LB + API Gateway            │
  │  - Authentication & Authorization  │
  │  - Rate Limiting                   │
  │  - Routing                         │
  │  - Round-Robin                     │
  └───────────────────────────────────-┘
       │
  ┌────┼──────────────────────────────────────────────────────────┐
  │    │                                                          │
  ▼    ▼              ▼            ▼           ▼         ▼        ▼
┌──────────┐  ┌─────────────┐ ┌──────────┐ ┌───────┐ ┌──────┐ ┌────────┐
│ User Svc │  │ Price Track │ │Watchlist │ │ Order │ │Portf-│ │Payment │
│          │  │    Svc      │ │   Svc    │ │  Svc  │ │ olio │ │  Svc   │
└────┬─────┘  └─────────────┘ └────┬─────┘ └───┬───┘ │ Svc  │ └───┬────┘
     │                             │            │     └──────┘     │
     ▼                             ▼            ▼                  ▼
 UserDB    KYC             Watch DB       Validator           Payment DB
 Verif.                               → Order DB             Payment GW

  All services communicate with:  Exchange (NSE/BSE)
```

---

# PAGE 8 — Low Level Architecture (from image)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│                   STOCK TRADING PLATFORM — LOW LEVEL DESIGN                    │
└────────────────────────────────────────────────────────────────────────────────┘

  users/client
     │             │
     ▼             ▼
  LB + API         WebSocket Gateway
  Gateway          - Authentication & Authorization
  - Auth           - WebSocket stickiness (sticky sessions)
  - Auth
  - Rate Limit
  - Routing
     │
  ┌──┼─────────────────────────────────────────────────────────┐
  │  │                          │                              │
  ▼  ▼                          ▼                              ▼
┌──────────────────────┐  ┌───────────────────────┐  ┌────────────────────────┐
│      User Svc        │  │  Price Tracker Svc    │  │     Order Svc          │
│                      │  │  (WebSocket Svc, WS)  │  │                        │
│ ↓                    │  │                       │  │                        │
│ UserDB               │  │  user subscribe       │  │   kafka                │
│ user_id (PK)         │  │  to stocks            │  │  - raw orders          │
│ email                │  │          │            │  │  - verified orders     │
│ mobile               │  │          ▼            │  │  - rejected orders     │
│ name                 │  │   Redis PubSub        │  │          │             │
│ pan/verified (enc)   │  │  ← subscribe          │  │          ▼             │
│ aadhaarNumber (enc)  │  │    to symbols         │  │      Validator         │
│ partnerDetail        │  │          │            │  │  - KYC check           │
│ balance              │  │          ▼            │  │  - Funds check         │
└──────────────────────┘  │  WatchList Svc        │  │  - Margin check        │
       │                  │        │              │  │  - Risk & Regulatory   │
       ▼                  │        ▼              │  │  - Fail to reject dup  │
  KYC Verification        │    Watch DB           │  │          │             │
                          │    WatchList(userId,  │  │  ┌───────▼────────┐    │
                          │     List<Watchlist>)  │  │  │   Order DB     │    │
                          │    Watchlist(id,      │  │  │  order_id      │    │
                          │     userId, name,     │  │  │  user_id       │    │
                          │     List<Symbol>,     │  │  │  stock_id      │    │
                          │     stockSymbols(set))│  │  │  order_type    │    │
                          │                       │  │  │  price         │    │
                          ▼                       │  │  │  quantity      │    │
                     InfluxDB                     │  │  │  trade_id      │    │
                  (past price of stock)           │  │  │  status        │    │
                          │                       │  │  └────────────────┘    │
                          │ stock live updates     │  └────────────────────────┘
                          ▼                       │
                       kafka                      │
                  - stock_price                   │
                  - order_status                  │
                          │                       │
                          ▼                       │
               ┌─────────────────────┐            │
               │  Exchange Gateway   │◄───────────┘
               │  400-500 symbols/ws │
               └──────────┬──────────┘
                          │
                          ▼
                   Exchange (NSE/BSE)
                          │
                          └──────────────► Notification Svc

  PORTFOLIO + PAYMENT SIDE:
  Portfolio Svc ← -PnL Calculation ← -read ← Trade DB
  Payment Gateway ← Payment Svc → Payment DB
                                   (Payment: user_id, amount, status,
                                    created_at, currency, gateway,
                                    description, metadata, timestamp)

  Price Ingester Svc → update → InfluxDB (past price of stock)
                               → stock live updates via Kafka

  ORDER TRACKER SVC (from image):
  ─ Primary role: consume Kafka 'order_status' → UPDATE orders table
  ─ "If job needs to run immediately push directly in queue":
    Order Tracker can bypass Kafka and push directly to Exchange Gateway
    (used for time-sensitive order types like STOP_LOSS triggers, IOC orders)
  ─ Polls exchange every ~10s to detect stuck orders (placed but no execution
    confirmation) → triggers retry or manual review
```

---

# PAGE 9 — Real-Time Price Flow (Step 1 Deep Dive)

```
FLOW: Exchange → Price Ingester → InfluxDB + Redis PubSub → WebSocket → Client

┌─────────────────────────────────────────────────────────────────────────────┐
│  Exchange (NSE/BSE)                                                         │
│  Tick update: {symbol: 'RELIANCE', price: 2458.75, volume: 125K, ts: ...}  │
└──────────────────────┬──────────────────────────────────────────────────────┘
                       │ WebSocket/FIX data feed
                       ▼
          ┌────────────────────────┐
          │  Price Ingester Svc   │  Subscribes to all 8-10k stocks
          └────────────┬───────────┘
               ┌───────┴────────────┐
               ▼                    ▼
        ┌─────────────┐     ┌──────────────────┐
        │  InfluxDB   │     │  Redis PubSub    │
        │ (persist)   │     │  (fan-out)       │
        │             │     │                  │
        │ INSERT:     │     │ PUBLISH          │
        │ symbol=RELI │     │ stock_price      │
        │ price=2458.7│     │ '{symbol,price,  │
        │ volume=125K │     │  change}'        │
        │ timestamp   │     │                  │
        │             │     │ <10ms latency    │
        │ 100K writes/│     │ No persistence   │
        │ sec         │     └──────┬───────────┘
        │ 1-min candles│           │
        │ → 5m → 1h   │           │ all WebSocket servers subscribe
        │ → daily     │           ▼
        └─────────────┘   ┌─────────────────────────────┐
                          │ WebSocket Gateway (10+ svcs) │
                          │  SUBSCRIBE stock_price       │
                          │                              │
                          │  On message:                 │
                          │  symbol='RELIANCE' →         │
                          │  find users watching RELIANCE│
                          │  → push via WebSocket        │
                          └──────────────┬───────────────┘
                                         │ Sticky sessions (user_id hash)
                                         ▼
                                     clients
                               (only receive stocks
                                they subscribed to)

WHY WEBSOCKET (NOT HTTP POLLING) FOR LIVE PRICE FEED? (Beginner Explanation)
  HTTP polling = you knock on your neighbor's door every second asking "any new mail?"
  Most times they say no, but you still made the trip. With 10 million users asking
  every second, that is 10 million wasted round-trips per second hitting your servers.
  WebSocket = your neighbor calls YOU the moment mail arrives. One persistent phone line,
  zero wasted trips. Better still: the server pushes updates ONLY for stocks the user
  is watching — if nobody is watching BHEL right now, zero bytes are sent for it.
  Think of it as Netflix vs. constantly refreshing a web page: Netflix streams video
  directly to you; you do not reload the page 24 times a second to get the next frame.
  Problem it solves: persistent bidirectional connection eliminates polling overhead
  entirely; server pushes only changed data, only to interested subscribers.
  Why the alternative is worse: 10M users polling every 1s = 10M HTTP requests/sec
  just to read prices — you would need 100x the servers compared to WebSocket push.

LATENCY BREAKDOWN:
  Exchange → Price Ingester:        5ms  (network)
  Price Ingester → Redis PubSub:    2ms  (PUBLISH)
  Redis PubSub → WebSocket server:  3ms  (in-memory fan-out)
  WebSocket server → Client:       10ms  (internet)
  TOTAL:                          ~20ms  (well under 50ms target)

BANDWIDTH EFFICIENCY:
  Each client subscribes to ~10 stocks (watchlist)
  Server pushes ONLY those 10 stocks, not all 8-10k
  Bandwidth reduction: 1000× per client

WEBSOCKET FALLBACK (if connection drops):
  Client auto-reconnects with exponential backoff: 1s → 2s → 4s → max 30s
  On reconnect: re-send subscribe watchlist {action:'subscribe', symbols:[...]}
  Fetch missed updates via REST: GET /api/v1/stocks/{symbol} (single call per stock)
  Then resume WebSocket live feed as normal
```

---

# PAGE 10 — Order Placement Flow (Step 2-3 Deep Dive)

```
WHY ORDER STATE MACHINE EXISTS? (Beginner Explanation)
  Think of an order like a package being shipped: PENDING (we received your request),
  VERIFIED (we checked your funds and KYC), PLACED (handed to the exchange courier),
  EXECUTED (delivery confirmed). Each state tells every downstream service exactly what
  has happened and what it should do next — Portfolio Svc only updates holdings on
  EXECUTED; Notification Svc sends different messages for PENDING vs EXECUTED.
  Problem it solves: in a distributed system with Kafka and multiple async services,
  you need one source of truth for "where is this order right now?" Without states, two
  services might both attempt to process the same order, or a REJECTED order could still
  reach the exchange because nobody tracked that it failed validation.
  Why the alternative is worse: a simple boolean (placed/not placed) breaks the moment
  you need to distinguish "funds locked but not yet validated" from "sent to exchange
  but not confirmed" — both require completely different failure recovery logic.

STATE MACHINE:  PENDING → VERIFIED → PLACED → EXECUTED
                                    ↘ REJECTED (at any validation stage)

STEP 2: Order Svc — User Places MARKET BUY Order

  POST /api/v1/orders
  { stockSymbol: 'RELIANCE', orderType: 'MARKET', tradeType: 'BUY', quantity: 10 }

  Order Svc validates:
  1. JWT token valid (authentication)
  2. Stock symbol exists in stocks table
  3. Market hours: 9:15 AM – 3:30 PM IST
  4. Quantity: positive integer, valid lot size
  5. Get current price: Redis GET stock_price:RELIANCE → ₹2458.75
  6. Estimated cost: 10 × 2458.75 + ₹20 commission = ₹24,607.50

  FUND LOCKING TRANSACTION:
  BEGIN TRANSACTION
    SELECT available_balance FROM funds
    WHERE user_id={user_id} FOR UPDATE    ← PESSIMISTIC LOCK
    ↑ Blocks concurrent transactions on same row

    IF available_balance < 24607.50
      ROLLBACK → return 400 'Insufficient funds'

    UPDATE funds SET
      available_balance = available_balance - 24607.50,
      locked_balance    = locked_balance    + 24607.50
  COMMIT
  (Isolation: SERIALIZABLE — prevents dirty reads + phantom reads)

  INSERT INTO orders (order_id, user_id, stock_symbol, order_type: 'MARKET',
                      trade_type: 'BUY', quantity: 10, price: NULL,
                      status: 'PENDING', placed_at: now())

  Kafka.send('new_orders', { orderId, userId, stockSymbol, orderType,
                             tradeType, quantity })
  → Response to user: 200 OK { orderId: 'ORD123', status: 'PENDING' }

STEP 3: Validator — 4-Stage Pipeline

  Validator consumes Kafka 'new_orders' (5 instances, 50 partitions)

  CHECK 1: Duplicate order (Redis SETNX)
  ─ SETNX order_lock:{orderId} 1 EX 30
  ─ Returns 0 → duplicate, reject

  CHECK 2: Risk management (exposure limit)
  ─ SELECT SUM(quantity × price) FROM orders
    WHERE user_id={id} AND status IN ('PENDING','PLACED')
  ─ If total exposure > 10× available_balance → reject

  CHECK 3: Circuit breaker (price volatility)
  ─ If stock price moved >10% in last 5 min → reject
  ─ Prevents orders during extreme market events

WHY CIRCUIT BREAKER / HALT TRADING EXISTS? (Beginner Explanation)
  In the 2010 US "Flash Crash," the Dow Jones fell 1000 points in minutes because
  trading algorithms fed off each other's panic sell signals in a runaway spiral.
  A circuit breaker is the fuse in your home electrical panel: when current spikes
  dangerously, it cuts the power before the wires catch fire and burn the house down.
  In our system: if RELIANCE moves more than 10% in 5 minutes, all new orders for that
  stock are auto-rejected until the market stabilises and regulators can assess if the
  move is genuine, a system glitch, or attempted manipulation. SEBI (India's regulator)
  legally mandates these halts — they are not optional design choices.
  Problem it solves: breaks the algorithmic feedback loop that can crash a stock to near
  zero in seconds, wiping out millions of investor portfolios in one cascade.
  Why the alternative is worse: without a circuit breaker, one rogue algorithm could
  trigger a sell spiral that destroys market confidence and causes systemic financial damage.

  CHECK 4: Compliance
  ─ User not blocked/restricted for this stock
  ─ KYC status = VERIFIED (from image: KYC check in Validator)

  IF ALL PASS:
  ─ UPDATE orders SET status = 'VERIFIED'
  ─ Kafka.send('verified_orders', { orderId, ... })

  IF ANY FAIL:
  ─ UPDATE orders SET status = 'REJECTED', rejection_reason = '...'
  ─ Kafka.send('rejected_orders', { orderId, reason })
  ─ Unlock funds: UPDATE funds SET available_balance += locked, locked_balance -= locked

EXCHANGE GATEWAY: FIX Protocol

  Consumes Kafka 'verified_orders'
  Formats FIX message:
    Tag 35 = D          (NewOrderSingle)
    Tag 55 = RELIANCE   (Symbol)
    Tag 54 = 1          (Side: Buy)
    Tag 38 = 10         (Quantity)
    Tag 40 = 1          (OrdType: Market)
  Sends via TCP to NSE/BSE matching engine
  UPDATE orders SET status = 'PLACED', exchange_order_id = {assigned_id}

  Connection pool: 400-500 persistent FIX connections
  Grouped by symbol (RELIANCE, TCS, INFY on same connection)
  Reuse connections — avoid TCP handshake overhead per order
```

---

# PAGE 11 — Trade Execution & Settlement (Step 4 Deep Dive)

```
WHY MATCHING ENGINE EXISTS AND WHY IT MUST BE SEQUENTIAL? (Beginner Explanation)
  The matching engine is the auctioneer at NSE/BSE: it takes the highest buyer bid and
  the lowest seller ask — if they overlap in price, it declares "SOLD!" and the trade is
  done. It does this for hundreds of thousands of orders per second across 8,000+ stocks.
  Why sequential (not parallel) for a given stock symbol? Imagine two auctioneers running
  concurrently for RELIANCE — both could "sell" the same 10 shares to two different buyers
  at the same moment. Sequential processing guarantees each match is unique: one buyer,
  one seller, one trade. The speed comes from in-memory order book data structures, not
  from parallelising the match itself.
  Problem it solves: fair, deterministic, zero-duplicate matching of buy and sell orders
  at the correct market price — the bedrock that makes a stock exchange legally trustworthy.
  Why the alternative is worse: concurrent matching without serialisation causes duplicate
  trades, which is a regulatory violation that can result in the exchange being shut down.

STEP 4: NSE/BSE → Execution → Portfolio Update

  NSE matching engine:
  ─ Matches BUY 10 RELIANCE with best available SELL order
  ─ Execution at ₹2459.00 (may differ from cached ₹2458.75)
  ─ Sends FIX ExecutionReport:
      Tag 35 = 8    (ExecutionReport)
      Tag 150 = 2   (ExecType: Filled)
      executedPrice: 2459.00, executedQuantity: 10

  Exchange Gateway receives confirmation
  ─ Kafka.send('order_status', {
      orderId: 'ORD123',
      status: 'EXECUTED',
      executedPrice: 2459.00,
      executedQuantity: 10,
      executedAt: timestamp
    })

  Kafka 'order_status' consumed by THREE services in parallel:

  ┌─────────────────┐  ┌─────────────────────┐  ┌───────────────────┐
  │ Order Tracker   │  │   Portfolio Svc     │  │ Notification Svc  │
  │     Svc         │  │                     │  │                   │
  │                 │  │ Check existing      │  │ Push notification │
  │ UPDATE orders   │  │ holding:            │  │ via FCM/APNS:     │
  │ SET status=     │  │ SELECT quantity,    │  │ "RELIANCE BUY 10  │
  │ EXECUTED        │  │ avg_buy_price FROM  │  │  @ ₹2459.00"      │
  │                 │  │ portfolio WHERE     │  │                   │
  │ INSERT trades:  │  │ user_id + symbol    │  │ WebSocket push    │
  │ trade_id        │  │                     │  │ (if user online): │
  │ order_id        │  │ If new holding:     │  │ {type:ORDER_STATUS│
  │ executed_price  │  │ INSERT (qty=10,     │  │  status:EXECUTED} │
  │ commission: ₹20 │  │ avg=2459.00)        │  │                   │
  │                 │  │                     │  │ Email: optional   │
  │                 │  │ If existing:        │  │ (SendGrid/SES)    │
  │                 │  │ UPDATE avg_buy_price│  │                   │
  │                 │  │ = weighted avg      │  │                   │
  └─────────────────┘  └─────────────────────┘  └───────────────────┘

  FUND SETTLEMENT (actual vs estimated):
  Estimated cost:  10 × 2458.75 + 20 = ₹24,607.50  (locked at order time)
  Actual cost:     10 × 2459.00 + 20 = ₹24,610.00  (settled at execution)
  Difference:                          ₹2.50

  BEGIN TRANSACTION
    UPDATE funds SET
      locked_balance    -= 24607.50,  (unlock estimated amount)
      available_balance -= 2.50       (deduct the difference)
  COMMIT

WHY SETTLEMENT T+1/T+2 EXISTS? (Beginner Explanation)
  When you buy RELIANCE today, you do not instantly own the shares the moment the trade
  executes. The actual transfer of shares from the seller's demat account to yours takes
  1 business day (T+1, where T = trade day). Cash moves from your broker to the seller's
  broker overnight through a clearinghouse — NSCCL for NSE, ICCL for BSE.
  Think of it like a bank wire: the payment is "approved" in seconds, but the money
  physically moves overnight through interbank settlement systems.
  System design impact: "trade executed" and "settlement complete" are two separate events.
  Your portfolio shows the new shares immediately (for display purposes), but actual share
  ownership in CDSL/NSDL (India's depositories) is confirmed only the next business day.
  This is why fund locking on order placement matters — the broker must guarantee the cash
  will be there at T+1 even before settlement actually runs.
  Why the alternative (T+0 instant settlement) is worse: requires every broker, clearinghouse,
  and depository to be online and in perfect sync simultaneously — one failure blocks the
  entire market. T+1 gives the ecosystem overnight to reconcile and handle exceptions.

  P&L CALCULATION (on-the-fly from Redis):
  Current price: Redis GET stock_price:RELIANCE → ₹2460.00
  current_value:  10 × 2460.00 = ₹24,600
  profit_loss:    24,600 - 24,590 = +₹10 unrealized gain
  ← NEVER stored in DB (price changes every second → instant stale)
```

---

# PAGE 12B — Notification Service Deep Dive (Step 6)

```
STEP 6: Notification Svc — Order Status Push

  Notification Svc consumes Kafka 'order_status' (async, non-blocking)
  Receives: { orderId: 'ORD123', status: 'EXECUTED', stockSymbol: 'RELIANCE',
              executedPrice: 2459.00, executedQuantity: 10 }

  STEP 6a: Check user preferences
  ─ SELECT push_enabled, email_enabled, sms_enabled
    FROM user_preferences WHERE user_id={user_id}
  ─ Default: push=true, email=true, sms=false

  STEP 6b: Push notification (FCM / APNS)
  ─ POST https://fcm.googleapis.com/v1/projects/{project}/messages:send
    Body: {
      token: user_device_token,
      notification: {
        title: 'Order Executed',
        body:  'Your BUY order for 10 RELIANCE executed at ₹2459.00'
      },
      data: { orderId: 'ORD123', stockSymbol: 'RELIANCE' }
    }
  ─ User mobile app receives → tapping opens order details page

  STEP 6c: In-app WebSocket push (if user online)
  ─ Check if user has active WebSocket connection
  ─ If yes → send: { type: 'ORDER_STATUS', orderId: 'ORD123',
                     status: 'EXECUTED', executedPrice: 2459.00 }
  ─ Order status in UI updates: PENDING → EXECUTED in real-time

  STEP 6d: Email (optional, async)
  ─ Send via SendGrid/SES:
    Subject: 'Order Executed - RELIANCE'
    Body:    'Your BUY order for 10 shares of RELIANCE was executed at
              ₹2459.00. Total cost: ₹24,610 (including ₹20 commission).'

  STEP 6e: SMS (optional, if sms_enabled=true)
  ─ Send via Twilio/MSG91: 'RELIANCE BUY 10 @ ₹2459.00 executed'

  FAILURE HANDLING (retry + DLQ):
  ─ Failed notification → retry with exponential backoff
    Attempt 1: wait 1s, Attempt 2: wait 2s, Attempt 3: wait 4s
  ─ After 3 failed attempts → push to Dead Letter Queue (DLQ)
  ─ DLQ alert: ops team investigates (user's notification missed)
  ─ Kafka consumer offset NOT committed until notification delivered
    (guarantees at-least-once delivery)

  Notification Svc: image shows "update status of order every 10s"
  ─ If no EXECUTED confirmation after 10s, re-query order status
  ─ Polling fallback in case Kafka event is delayed
```

```
LIMIT SELL order:
  POST /api/v1/orders
  { stockSymbol: 'TCS', orderType: 'LIMIT', tradeType: 'SELL',
    quantity: 5, price: 3500.00 }

  Difference from MARKET order:
  ─ SELL check: does user own 5 TCS shares?
    SELECT quantity FROM portfolio WHERE user_id={id} AND stock_symbol='TCS'
    if quantity < 5 → 400 'Insufficient holdings'
  ─ Lock shares (prevent selling same shares twice):
    UPDATE portfolio SET quantity -= 5, locked_quantity += 5
  ─ Validate limit price: must be within ±10% of current market price
    (prevents erroneous orders like SELL at ₹1 or ₹100,000)
  ─ price = 3500.00 stored in orders table (not NULL)

  Exchange behavior:
  ─ LIMIT order sits in NSE/BSE order book until condition met
  ─ If TCS price reaches ₹3500 → matched with BUY order → EXECUTED
  ─ If price never reaches ₹3500 before 3:30 PM → day order cancelled
    OR remains open if GTC (Good Till Cancelled) specified

  On Execution (when TCS hits ₹3500):
  ─ Exchange sends 'EXECUTED' via FIX → Kafka 'order_status'
  ─ Portfolio Svc: UPDATE portfolio SET locked_quantity -= 5
    (shares already removed from available_quantity on order placement)
  ─ Funds Svc: UPDATE funds SET available_balance += (5 × 3500 - commission)
    = +₹17,480 credited to available_balance

  On Cancellation (user cancels or day-end):
  ─ DELETE /api/v1/orders/{orderId} (only if status = PENDING or PLACED)
  ─ UPDATE orders SET status = 'CANCELLED'
  ─ Restore shares: UPDATE portfolio SET locked_quantity -= 5, quantity += 5
```

---

# PAGE 12C — Portfolio P&L Calculation (Step 7)

```
STEP 7: GET /api/v1/portfolio — Real-Time P&L

  For each holding, fetch current price from Redis:
    GET stock_price:RELIANCE → 2460.00

  CALCULATION PER HOLDING:
  holding:        { stock_symbol: 'RELIANCE', quantity: 10,
                    avg_buy_price: 2459.00, total_investment: 24590 }
  current_value:  10 × 2460.00 = ₹24,600
  profit_loss:    24,600 − 24,590 = +₹10  (+0.04%)
  day_change:     (current_price − prev_close) / prev_close × 100
                = (2460 − 2455) / 2455 × 100 = +0.20%

  AGGREGATE PORTFOLIO:
  total_investment:  SUM(total_investment for all holdings) = ₹2,45,000
  current_value:     SUM(current_value for all holdings)    = ₹2,48,500
  total_profit_loss: 2,48,500 − 2,45,000 = +₹3,500 (+1.43%)
  today_change:      SUM(day_change weighted by current_value)

  RESPONSE JSON:
  {
    "holdings": [
      {
        "stockSymbol": "RELIANCE",
        "quantity": 10,
        "avgBuyPrice": 2459.00,
        "currentPrice": 2460.00,
        "currentValue": 24600,
        "profitLoss": +10,
        "profitLossPercent": "+0.04%",
        "dayChange": "+0.20%"
      }
    ],
    "totalInvestment": 245000,
    "currentValue": 248500,
    "totalProfitLoss": +3500,
    "totalProfitLossPercent": "+1.43%"
  }

  KEY POINT: current_value and profit_loss are NEVER stored in DB.
  Calculated fresh on every GET /api/v1/portfolio using Redis price.
  Only static fields stored: quantity, avg_buy_price, total_investment.
  prev_close stored in Stocks table (updated at end of each trading day).
```

## Sequence 1: Real-Time Price to Client

```
NSE/BSE    PriceIngester    InfluxDB    Redis PubSub    WS Gateway    Client
  │              │              │             │               │           │
  │ tick update  │              │             │               │           │
  │─────────────►│              │             │               │           │
  │              │ INSERT price │             │               │           │
  │              │─────────────►│             │               │           │
  │              │ PUBLISH      │             │               │           │
  │              │──────────────────────────► │               │           │
  │              │              │             │ fan-out <10ms │           │
  │              │              │             │───────────────►           │
  │              │              │             │               │ push WS   │
  │              │              │             │               │──────────►│
  │              │              │             │            ~20ms total    │
```

## Sequence 2: Market Order — Full Flow

```
User   OrderSvc  FundsDB   Kafka    Validator  ExchGW  NSE/BSE  OrderTracker  Portfolio
 │        │         │        │          │         │       │          │            │
 │ POST   │         │        │          │         │       │          │            │
 │ /order │         │        │          │         │       │          │            │
 │───────►│         │        │          │         │       │          │            │
 │        │ SELECT  │        │          │         │       │          │            │
 │        │ FOR UPD │        │          │         │       │          │            │
 │        │────────►│        │          │         │       │          │            │
 │        │ locked  │        │          │         │       │          │            │
 │        │◄────────│        │          │         │       │          │            │
 │        │ INSERT  │        │          │         │       │          │            │
 │        │ order   │        │          │         │       │          │            │
 │        │ PENDING │        │          │         │       │          │            │
 │ 200 OK │         │        │          │         │       │          │            │
 │◄───────│         │        │          │         │       │          │            │
 │        │ publish new_order│          │         │       │          │            │
 │        │────────────────► │          │         │       │          │            │
 │        │         │        │ consume  │         │       │          │            │
 │        │         │        │─────────►│         │       │          │            │
 │        │         │        │ validated│         │       │          │            │
 │        │         │        │ verified │         │       │          │            │
 │        │         │        │◄─────────│         │       │          │            │
 │        │         │        │ consume  │         │       │          │            │
 │        │         │        │──────────────────► │       │          │            │
 │        │         │        │          │ FIX msg │       │          │            │
 │        │         │        │          │         │──────►│          │            │
 │        │         │        │          │         │ match │          │            │
 │        │         │        │          │         │◄──────│          │            │
 │        │         │        │ EXECUTED status     │       │          │            │
 │        │         │        │◄──────────────────────────────────────┤            │
 │        │         │        │                     │       │          │ update     │
 │        │         │        │─────────────────────────────────────► │ trade/fund │
 │        │         │        │─────────────────────────────────────────────────►  │
```

## Sequence 3: Overdraft Prevention

```
User         OrderSvc(A)     FundsDB       OrderSvc(B)
  │               │              │               │
  │ Order A       │              │               │ Order B
  │──────────────►│              │               │◄──────────────
  │               │ SELECT FOR   │               │
  │               │ UPDATE ──────►│ ← ROW LOCKED  │
  │               │              │               │ SELECT FOR UPDATE
  │               │              │               │──────────────────►
  │               │              │               │ ← WAITS (row locked by A)
  │               │ balance=50K  │               │
  │               │◄─────────────│               │
  │               │ UPDATE -49K  │               │
  │               │─────────────►│               │
  │               │ COMMIT       │               │
  │               │─────────────►│ lock released  │
  │ 200 PENDING   │              │◄──────────────────────────────
  │◄──────────────│              │ balance=820   │
  │               │              │──────────────►│ reads 820
  │               │              │               │ 820 < 17500 → FAIL
  │               │              │               │ ROLLBACK
  │               │              │               │──►
  │               │              │               │ return 400
```

---

# PAGE 14 — Database Schema (Complete)

```sql
-- Orders table (Order DB)
CREATE TABLE orders (
    order_id         UUID PRIMARY KEY,
    user_id          UUID NOT NULL,
    stock_symbol     VARCHAR(20) NOT NULL,
    order_type       ENUM('MARKET','LIMIT','STOP_LOSS'),
    trade_type       ENUM('BUY','SELL'),
    quantity         INT NOT NULL,
    price            DECIMAL(10,2),           -- NULL for MARKET orders
    status           ENUM('PENDING','VERIFIED','PLACED','EXECUTED','REJECTED','CANCELLED'),
    placed_at        TIMESTAMPTZ DEFAULT NOW(),
    executed_at      TIMESTAMPTZ,
    exchange_order_id VARCHAR(50)
);
CREATE INDEX idx_orders_user ON orders(user_id, placed_at DESC);
CREATE INDEX idx_orders_status ON orders(status, placed_at);
CREATE INDEX idx_orders_stock ON orders(stock_symbol, status);

-- Funds table (critical — pessimistic locking)
CREATE TABLE funds (
    user_id           UUID PRIMARY KEY,
    available_balance DECIMAL(15,2) NOT NULL DEFAULT 0,
    locked_balance    DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_balance     DECIMAL(15,2) GENERATED ALWAYS AS (available_balance + locked_balance),
    bank_account_id   VARCHAR(50),
    last_deposit_at   TIMESTAMPTZ,
    last_withdrawal_at TIMESTAMPTZ
);
-- CRITICAL: Use SELECT ... FOR UPDATE with SERIALIZABLE isolation

-- Portfolio table
CREATE TABLE portfolio (
    user_id          UUID NOT NULL,
    stock_symbol     VARCHAR(20) NOT NULL,
    quantity         INT NOT NULL DEFAULT 0,
    locked_quantity  INT NOT NULL DEFAULT 0,      -- shares locked in pending SELL
    avg_buy_price    DECIMAL(10,2),
    total_investment DECIMAL(15,2),
    -- current_value and profit_loss: calculated ON-THE-FLY from Redis, not stored
    last_updated_at  TIMESTAMPTZ,
    PRIMARY KEY (user_id, stock_symbol)
);

-- Redis Key Space:
-- stock_price:{symbol}     STRING  current price  TTL 1s (refreshed constantly)
-- stock_price              PUBSUB  CHANNEL → fan-out to WebSocket servers
-- user_session:{token}     HASH    user session    TTL 24h
-- order_lock:{orderId}     STRING  dedup lock      TTL 30s  (SETNX)
```

---

# PAGE 15 — InfluxDB Time-Series Detail

```
MEASUREMENT: stock_prices
  TAGS (indexed):   symbol (RELIANCE, TCS ...), exchange (NSE, BSE)
  FIELDS:           price (float), volume (int), day_high (float), day_low (float)
  TIMESTAMP:        nanosecond precision

RETENTION + DOWNSAMPLING:
  1-min candles   →  stored forever    (all raw data)
  5-min candles   →  auto-aggregated   (continuous query)
  1-hour candles  →  auto-aggregated
  Daily candles   →  auto-aggregated

QUERY EXAMPLE (1D chart for RELIANCE):
  SELECT mean(price) FROM stock_prices
  WHERE symbol = 'RELIANCE'
    AND time > now() - 1d
  GROUP BY time(5m)
  → Returns ~288 data points, renders 5-minute candlestick chart in <100ms

WHY TIME-SERIES DB (InfluxDB) EXISTS? (Beginner Explanation)
  Stock prices are like a river — data only ever flows forward. You never go back and
  update yesterday's price tick (unlike a bank account balance that gets updated in-place).
  MySQL's B-tree index was designed for records you update at any time, in any order.
  InfluxDB's LSM tree was built specifically for append-only, time-stamped data streams.
  Scale reality: storing RELIANCE's price every second for 10 years = ~315 million rows
  for ONE stock. Across 10,000 stocks: 3 trillion rows. InfluxDB auto-compresses these
  into "candles" — instead of storing 3,600 individual 1-second prices, it stores one
  1-hour candle (open, high, low, close, volume). Data is time-partitioned, so "give me
  all RELIANCE prices for the last hour" skips directly to that time chunk in <100ms.
  Problem it solves: sustain 100K+ price writes/second across all stocks without index
  rebuild slowdowns, and serve historical chart queries in under 100ms.
  Why the alternative is worse: SQL B-tree rebuilds its index on every insert — at
  100K writes/sec the database thrashes and falls over within minutes.

WHY NOT SQL FOR TIME-SERIES:
  100K+ price writes/second × 10K stocks = 1B writes/day
  SQL: B-tree index rebuild on every insert → write bottleneck
  InfluxDB: LSM tree + time-based partitioning → optimized for append-only writes
```

---

# PAGE 15B — Scaling & Optimization (All 12 Techniques)

```
TECHNIQUE 1: Redis PubSub for real-time prices
  Price updates → stock_price channel (<10ms latency)
  WebSocket servers subscribe → push to clients
  No polling (avoids 100K+ concurrent poll requests)
  Scales horizontally: add more WebSocket servers

TECHNIQUE 2: InfluxDB time-series DB
  100K+ writes/sec for stock prices
  Auto-downsampling: 1-min candles → 5-min → hourly → daily
  Efficient range queries for charts (1Y data in <100ms)
  Retention policies: 1-min data forever; aggregates auto-calculated

TECHNIQUE 3: Kafka event-driven architecture
  Decouples: Order Svc → Validator → Exchange Gateway → Order Tracker
  Async processing: user gets 200 OK immediately (before exchange execution)
  Horizontal scaling: add more consumers per topic
  At-least-once delivery guarantees: no order lost

WHY KAFKA FOR ORDER EVENTS (NOT DIRECT SERVICE CALLS)? (Beginner Explanation)
  Kafka is the order ticket printer at a restaurant. When a waiter takes your order,
  they drop a ticket on the printer and immediately go serve the next table. The kitchen
  picks it up when it is ready. The waiter never stands there watching the chef cook.
  Without Kafka: Order Svc calls Validator directly (wait), then calls Exchange Gateway
  directly (wait), then calls Portfolio Svc (wait). If the exchange is slow (200ms) and
  the validator is busy (50ms), the user's browser spins for 250ms+ before seeing "Order
  placed." One slow step cascades into user-facing latency — and a crash in any step
  means the order is lost with no way to replay it.
  With Kafka: Order Svc drops the event and returns "200 PENDING" in under 10ms.
  Validator, Exchange Gateway, Portfolio Svc all process the same event asynchronously,
  at their own pace, independently scalable, with full replay on failure.
  Problem it solves: decoupling, async processing, independent scaling per service,
  and guaranteed at-least-once delivery even if a downstream service temporarily crashes.
  Why the alternative is worse: synchronous chained calls — if Exchange Gateway restarts
  for 30 seconds, every order placed during that window is silently lost forever.

TECHNIQUE 4: Fund locking with transactions (ACID)
  Lock funds on placement (available → locked) in single transaction
  Unlock on execution/rejection/cancellation
  SELECT FOR UPDATE + SERIALIZABLE: no race conditions

TECHNIQUE 5: Database sharding by user_id
  Orders table: sharded by user_id (all user's orders on same shard)
  Portfolio table: sharded by user_id (user's holdings together)
  10 shards: each handles ~100K users (1M total users)
  Cross-shard queries: only for admin/analytics (acceptable slow)

TECHNIQUE 6: Read replicas for portfolio & watchlist
  1 master (writes: order execution, fund updates, trade inserts)
  + 5 read replicas (reads: portfolio view, watchlist, order history)
  Read/write split: portfolio GET → replicas (95% of traffic)
  Trade execution writes → master only
  Replication lag: <1s (acceptable for portfolio view)

TECHNIQUE 7: Exchange Gateway connection pooling
  Maintain 400-500 persistent FIX connections to NSE/BSE
  Grouped by symbol (RELIANCE, TCS, INFY on same connection)
  Reuse connections: avoid TCP handshake overhead per order (~3-5ms each)
  Load balance: distribute orders across connections by symbol hash

TECHNIQUE 8: Order validation pipeline (<50ms)
  Multi-stage: (1) Duplicate SETNX, (2) Fund check, (3) Risk check, (4) Circuit breaker
  Parallel checks where possible
  Validator: 5 instances, 50 Kafka partitions = horizontal scale

TECHNIQUE 9: WebSocket Gateway auto-scaling
  Auto-scale: if connections > 10K per server → spin up new instance
  Sticky sessions (user_id hash): user always routes to same server
  Load balancer: consistent hash by user_id (preserves WebSocket state)
  Each server handles ~10K WebSocket connections

TECHNIQUE 10: Price caching strategy
  Redis: current price (TTL 1s, refreshed by Price Ingester continuously)
  Historical charts: cache popular queries (e.g. RELIANCE 1D chart → TTL 5min)
  Cache warming: pre-load top 100 most-watched stocks on server start
  Cache hit rate: 99%+ for current prices (all trades use cached price)

TECHNIQUE 11: Rate limiting
  Per user:    10 orders/sec        (prevents fat-finger / rapid-click errors)
  Per API:     100 req/sec per user (portfolio, watchlist, history endpoints)
  Global:      100K orders/min      (circuit breaker if exceeded — system protection)
  Enforced at: API Gateway (token bucket per user_id)

TECHNIQUE 12: Async notification with queues + DLQ
  Notification Svc consumes Kafka 'order_status' async (non-blocking)
  User gets trade confirmation within ~1s via push notification
  Email/SMS queued separately (non-blocking, lower priority)
  Failed notification → retry with exponential backoff (1s → 2s → 4s)
  After 3 failed attempts → Dead Letter Queue (DLQ) → ops alert
```

---

# PAGE 16 — Senior Trap Questions

## Q1: "How do you prevent overdraft with simultaneous orders?"

```
STRONG ANSWER:
  Fund locking with SELECT FOR UPDATE + SERIALIZABLE isolation.

  User has ₹50,000. Places two simultaneous BUY orders:
  Order A: 20 RELIANCE × ₹2459 = ₹49,180
  Order B: 5  TCS      × ₹3500 = ₹17,500
  Total required: ₹66,680 > ₹50,000 (would overdraft)

  WITHOUT LOCKING (wrong): Both check balance (₹50K ≥ both amounts),
  both pass, both execute → overdraft.

  WITH SELECT FOR UPDATE:
  Order A: SELECT available_balance FROM funds WHERE user_id=X FOR UPDATE
  → Row locked. Order B's SELECT FOR UPDATE waits.
  Order A: balance=₹50K ≥ ₹49,180 ✓, UPDATE available -= 49180, locked += 49180. COMMIT.
  Order B: Lock released. Reads balance = ₹820.
  ₹820 < ₹17,500 → ROLLBACK → 400 'Insufficient funds'.

  Isolation level: SERIALIZABLE. Prevents dirty reads + phantom reads.

  Alternative: Optimistic locking with version column.
  Use pessimistic for funds (high contention, correctness critical).
  Use optimistic for portfolio updates (lower contention, retries acceptable)."
```

---

## Q2: "Market order price is estimated at ₹2458.75 but executes at ₹2459.00. How do you handle the difference?"

```
STRONG ANSWER:
  Two-step fund settlement:

  STEP 1 (on order placement):
  Lock estimated cost: 10 × 2458.75 + ₹20 = ₹24,607.50
  UPDATE funds: available_balance -= 24607.50, locked_balance += 24607.50

  STEP 2 (on execution):
  Actual cost: 10 × 2459.00 + ₹20 = ₹24,610.00
  Difference: ₹2.50 more than estimated

  UPDATE funds:
    locked_balance    -= 24607.50  (unlock full estimated amount)
    available_balance -= 2.50      (deduct only the difference)

  If actual < estimated (execution better than expected):
    available_balance += (estimated - actual)  (refund the difference)

  This handles all cases: price improvement, price slippage, and exact match.
  The locked amount is always fully released; net debit is always the actual cost."
```

---

## Q3: "What is the FIX protocol? Why can't you just use REST to send orders to NSE?"

```
STRONG ANSWER:
  FIX (Financial Information eXchange) is a binary TCP protocol designed
  specifically for financial order routing. Used by every major exchange globally.

  Why not REST:
  ─ REST is HTTP (application layer). FIX is TCP (transport layer) → lower latency.
  ─ REST: new TCP connection per request (or HTTP keep-alive, still heavier).
    FIX: persistent TCP connection, binary messages, no HTTP overhead.
  ─ NSE/BSE simply don't accept REST. FIX is the industry standard.
  ─ FIX messages are tag-value pairs: Tag35=D means NewOrderSingle (place order).
    Tag35=8 means ExecutionReport (trade confirmation).

  Connection pooling:
  We maintain 400-500 persistent FIX connections to the exchange.
  Grouped by symbol (all RELIANCE, TCS, NIFTY orders on same connection).
  Reuse connections — TCP handshake takes 3-5ms, unacceptable per order."
```

---

## Q4: "Why don't you store P&L in the database? What if Redis goes down?"

```
STRONG ANSWER:
  P&L = current_value − total_investment
      = (quantity × current_price) − (quantity × avg_buy_price)

  current_price changes every second. If we store P&L in DB:
  ─ Must UPDATE portfolio rows 8-10K times/second (one per stock update)
  ─ With millions of users × 8-10K stocks → billions of DB writes/second
  ─ Not feasible. Also → stale data risk between updates.

  Instead: store only static fields (quantity, avg_buy_price, total_investment).
  Compute P&L on every portfolio GET request using Redis stock_price:{symbol}.

  If Redis goes down:
  ─ Fall back to InfluxDB (or PostgreSQL stocks table current_price)
  ─ P&L may be slightly stale (~1s) but correct
  ─ Redis is the fast cache; DB is the fallback source of truth
  ─ Portfolio GET is tolerated with 1-2s stale price — no financial risk
    (user is viewing, not trading, so slight staleness is acceptable)"
```

---

## Q5: "How do you handle a LIMIT order that never executes? What about end-of-day?"

```
STRONG ANSWER:
  Three outcomes for a LIMIT order:

  1. Executes (price condition met):
     Exchange sends EXECUTED → normal trade execution flow.

  2. Day order expires (price never reached, market closes):
     At 3:30 PM IST: NSE sends cancellation notification via FIX.
     Exchange Gateway publishes to Kafka 'order_status' with status='CANCELLED'.
     Order Tracker: UPDATE orders SET status='CANCELLED'.
     Portfolio Svc: locked_quantity -= 5, quantity += 5 (restore shares for SELL).
     Funds Svc: locked_balance -= estimated, available_balance += estimated (for BUY).

  3. GTC (Good Till Cancelled) order:
     Remains in exchange order book across multiple trading days.
     Status stays 'PLACED' in our system until executed or user cancels.

  Watcher job (cron at 3:31 PM):
  Query orders WHERE status IN ('PENDING','PLACED') AND placed_at < today_market_close
  → Verify with exchange if still open or cancelled → reconcile status."
```

---

# PAGE 17 — What NOT to Say

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  TRAP PHRASE                        │ WHY IT'S WRONG                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Availability > Consistency for     │ WRONG. Image explicitly states        ║
║  trading — uptime matters most"     │ Consistency >> Availability.          ║
║                                     │ Wrong balance = financial loss.       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Check balance, then update in      │ Race condition. Two concurrent        ║
║  two separate queries"              │ orders both read ₹50K, both pass,    ║
║                                     │ both execute → overdraft.             ║
║                                     │ Use SELECT FOR UPDATE in one txn.     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Store current P&L in portfolio DB" │ Price changes every second.           ║
║                                     │ Stored P&L is instantly stale.        ║
║                                     │ Calculate on-the-fly from Redis.      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Use REST API to send orders to     │ NSE/BSE only speak FIX protocol       ║
║  NSE/BSE"                           │ (binary TCP). Not REST/HTTP.          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Use SQL database for stock price   │ SQL B-tree can't handle 100K+         ║
║  history / charts"                  │ price writes/second. Use InfluxDB     ║
║                                     │ (time-series, LSM tree, downsampling).║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Poll REST endpoint every second    │ Polling: 10M users × 1/sec = 10M     ║
║  for price updates"                 │ req/sec on the server.                ║
║                                     │ WebSocket + Redis PubSub: server      ║
║                                     │ pushes only changed prices, only to   ║
║                                     │ users watching that stock.            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ "Market order executes at the       │ Market order executes at BEST         ║
║  price shown to the user"           │ AVAILABLE price at execution time.    ║
║                                     │ Price may differ (slippage).          ║
║                                     │ Estimated cost ≠ actual cost.        ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

# PAGE 18 — Key Numbers to Memorize

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Scale:                                                                      │
│  8-10K      stock symbols (NSE+BSE combined)                                 │
│  100K+      orders/minute at peak (market volatility)                        │
│  10K        orders/minute normal                                             │
│  400-500    FIX protocol connections per Exchange Gateway                    │
│                                                                              │
│  Latency:                                                                    │
│  < 100ms    order placement (user → 200 OK)                                  │
│  < 50ms     market data update (Exchange → client)                           │
│  ~20ms      actual price update latency (Exchange → WS client breakdown)    │
│  < 10ms     Redis PubSub fan-out latency                                     │
│                                                                              │
│  InfluxDB:                                                                   │
│  100K+      price writes/second                                              │
│  1-min      candle resolution stored forever                                 │
│  < 100ms    1-year historical data query for chart                           │
│                                                                              │
│  Order validation pipeline:                                                  │
│  < 50ms     total 4-stage validation (duplicate + fund + risk + circuit)    │
│  EX 30      Redis SETNX TTL for duplicate order prevention                  │
│  10×        max exposure multiplier (total pending ≤ 10× available balance) │
│  10%        circuit breaker threshold (price volatility in 5 min)           │
│  10 orders/sec  rate limit per user (fat-finger protection)                 │
│  100 req/sec    rate limit per user per API endpoint                        │
│  100K orders/min  global circuit breaker threshold                          │
│                                                                              │
│  Fund management:                                                            │
│  SERIALIZABLE  isolation level for fund updates                              │
│  SELECT FOR UPDATE  used for fund deduction (pessimistic lock)               │
│  10 min     TTL for order lock in Redis                                      │
│                                                                              │
│  Kafka topics:                                                               │
│  50         partitions on new_orders (by user_id hash)                      │
│  10         partitions on verified_orders                                    │
│  50         partitions on order_status (by order_id hash)                   │
│  100        partitions on stock_price (by symbol hash)                       │
│                                                                              │
│  Database choices:                                                           │
│  UserDB       → PostgreSQL (ACID, KYC data)                                 │
│  Order DB     → PostgreSQL (ACID, fund locking)                              │
│  Trade DB     → PostgreSQL (execution history)                               │
│  Watch DB     → PostgreSQL/MongoDB (array of symbols)                       │
│  Payment DB   → PostgreSQL (financial transactions)                          │
│  Price data   → InfluxDB (time-series, 100K+ writes/sec)                    │
│  Cache        → Redis (prices, sessions, locks, PubSub)                     │
│  Search       → Kafka event bus (order flow backbone)                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

# PAGE 19 — Whiteboard Draw Order

```
Step 1 — Write the CAP split (20 sec)
  "Consistency >> Availability for trading (from requirements)"
  "But: stock price VIEW = highly available"

Step 2 — Draw HLD (45 sec)
  clients → LB+API Gateway + WebSocket Gateway
  → User Svc / Price Tracker / WatchList / Order Svc / Portfolio / Payment
  → Exchange (NSE/BSE)

Step 3 — Draw the Price Path (45 sec)
  NSE/BSE → Price Ingester → InfluxDB (persist) + Redis PubSub (fan-out)
  → WebSocket servers → clients
  "~20ms end-to-end. Selective push — client only gets watched stocks."

Step 4 — Draw the Order Path (60 sec)
  Order Svc → lock funds (SELECT FOR UPDATE) → Kafka new_orders
  → Validator (duplicate SETNX, funds, risk, circuit breaker) → Kafka verified_orders
  → Exchange Gateway (FIX protocol, 400-500 connections) → NSE/BSE
  → Kafka order_status → Order Tracker + Portfolio + Notification

Step 5 — Draw the state machine (15 sec)
  PENDING → VERIFIED → PLACED → EXECUTED
                              ↘ REJECTED

Step 6 — Call out the hard problems (20 sec)
  "Overdraft: SELECT FOR UPDATE, SERIALIZABLE"
  "Duplicate: Redis SETNX EX 30"
  "P&L: calculated on-the-fly, never stored"
  "Price history: InfluxDB, not SQL"
```

---

# PAGE 20 — Final Quick-Revision Cheat Sheet

```
╔══════════════════════════════════════════════════════════════════════════════╗
║         STOCK TRADING PLATFORM — ONE-PAGE CHEAT SHEET                      ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  CAP SPLIT (state this explicitly):                                          ║
║  Price view = AP (Redis PubSub + WebSocket, ~20ms, eventual OK)             ║
║  Order/funds = CP (SELECT FOR UPDATE, SERIALIZABLE, ACID)                   ║
║                                                                              ║
║  PRICE PATH (AP):                                                            ║
║  NSE/BSE → Price Ingester → InfluxDB (charts) + Redis PubSub (live)         ║
║  → WebSocket Gateway → clients (selective push, only subscribed stocks)     ║
║  Latency: Exchange→client ~20ms. Bandwidth: 1000× reduction (selective)     ║
║                                                                              ║
║  ORDER PATH (CP) — State machine:                                            ║
║  PENDING → VERIFIED → PLACED → EXECUTED / REJECTED                          ║
║  Order Svc → lock funds (SELECT FOR UPDATE) → Kafka new_orders              ║
║  → Validator (duplicate SETNX + fund + risk + circuit breaker)              ║
║  → Kafka verified_orders → Exchange Gateway (FIX TCP)                       ║
║  → NSE/BSE → Kafka order_status → 3 parallel consumers                      ║
║                                                                              ║
║  FUND LOCKING (overdraft prevention):                                        ║
║  SELECT available_balance FROM funds WHERE user_id=X FOR UPDATE              ║
║  Check → UPDATE available→locked in ONE transaction (SERIALIZABLE)          ║
║  Settle actual cost on EXECUTED (unlock estimated, deduct difference)        ║
║                                                                              ║
║  ORDER VALIDATION PIPELINE (<50ms):                                          ║
║  1. Duplicate: Redis SETNX order_lock:{id} EX 30                            ║
║  2. Fund: SELECT FOR UPDATE funds                                            ║
║  3. Risk: total exposure ≤ 10× available_balance                            ║
║  4. Circuit breaker: price volatility ≤ 10% in 5 min                        ║
║                                                                              ║
║  P&L = NEVER STORED:                                                         ║
║  = quantity × current_price(Redis) - total_investment                       ║
║  Calculated on every portfolio GET. Stored: quantity, avg_buy_price only.   ║
║                                                                              ║
║  FIX PROTOCOL:                                                               ║
║  Binary TCP. Tag35=D (place order). Tag35=8 (execution report).             ║
║  400-500 persistent connections per Exchange Gateway instance.               ║
║                                                                              ║
║  INFLUXDB:                                                                   ║
║  100K+ price writes/sec. 1-min candles → 5m → 1h → daily (downsampling).  ║
║  1-year chart query <100ms. Never use SQL for time-series.                   ║
║                                                                              ║
║  WHAT NOT TO SAY:                                                            ║
║  ✗ Availability > Consistency for trading (image says opposite)              ║
║  ✗ Separate check-then-update for funds (race condition)                     ║
║  ✗ Store P&L in DB (stale after 1 second)                                   ║
║  ✗ REST API to NSE/BSE (use FIX protocol)                                   ║
║  ✗ SQL for stock price history (use InfluxDB)                                ║
║  ✗ Poll for prices (use WebSocket + Redis PubSub)                            ║
║                                                                              ║
║  INTERVIEW LINE:                                                             ║
║  "CAP split: price view = AP (WebSocket+PubSub, ~20ms), trading = CP        ║
║   (SELECT FOR UPDATE, SERIALIZABLE). Fund locking prevents overdraft.       ║
║   4-stage validation pipeline. FIX protocol to NSE/BSE.                     ║
║   InfluxDB for prices, PostgreSQL for orders + funds."                       ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

*Print: monospace font, 10pt, portrait, standard margins. All ASCII diagrams are print-ready.*

---

## KEY PATTERNS REFERENCED IN THIS DESIGN

> **For the 2-year developer:** These are the hidden concepts behind design decisions in this system. Each has a dedicated deep-dive file.

### WebSocket vs SSE vs Long Polling
**Why it matters here:** Stock trading requires bidirectional real-time communication — client places orders (client→server) AND receives market data stream — bid/ask updates every 100ms (server→client). WebSocket is mandatory. SSE is one-way. Long polling has 500ms+ latency — unacceptable for trading.
**Deep dive:** `../../WebSocket_vs_SSE_vs_Long_Polling.md`

### B-tree vs LSM Tree
**Why it matters here:** Trade history is append-only at high rates (10K–100K trades/second) → Cassandra LSM. Order book (bids/asks) requires fast range scans by price → PostgreSQL B-tree. The write pattern of each data type drives the storage engine choice.
**Deep dive:** `../../BTree_vs_LSM_Tree_MySQL_vs_Cassandra_RocksDB.md`

### UUID as Primary Key
**Why it matters here:** Trades are inserted at microsecond intervals — potentially millions per second. Random UUID PKs cause buffer pool cache thrashing (each insert fetches a different B-tree leaf page). Use ULID (time-ordered UUID) or sequential trade_id — keeps working set in buffer pool.
**Deep dive:** `../../UUID_as_Primary_Key_Why_Its_Bad.md`

### Optimistic vs Pessimistic Locking
**Why it matters here:** PESSIMISTIC for order matching — market order matches a limit order. Both sides must lock simultaneously to calculate fill price and update quantities atomically. Deadlock prevention: always lock lower order_id first (consistent ordering rule).
**Deep dive:** `../../Optimistic_vs_Pessimistic_Locking.md`

### CAP Theorem
**Why it matters here:** CP for order execution — during partition, reject new orders rather than risk executing at stale prices. A failed order is recoverable; an incorrect execution is a regulatory violation. Trading systems choose consistency over availability.
**Deep dive:** `../../CAP_Theorem_Applied_What_Actually_Breaks.md`

### [Database Sharding](../../Database_Sharding_Range_Hash_Consistent_Hashing.md)
**Why this system uses it:** Trade history table grows at 10M+ rows per day (millions of traders × multiple trades each). Shard by `trader_id` hash — all trades for one trader are on the same shard, making portfolio history queries fast. Order book is NOT sharded by trader — it's sharded by `instrument_id` (one shard per stock/instrument). The matching engine for RELIANCE.NS only needs to look at one shard's order book. Avoid sharding by `trade_date` — all today's trades would create an extreme hot shard.

### [CQRS / Event Sourcing](../../CQRS_Event_Sourcing.md)
**Why this system uses it:** Trade ledger uses event sourcing — every order placement, execution, cancellation, and modification is an immutable event. Current portfolio (positions, P&L) is derived by replaying events. Required by SEBI/SEC regulations: full, unalterable audit trail of every trade action. CQRS: write side = event store (Kafka + PostgreSQL), read side = pre-computed portfolio projections (Redis for real-time P&L, Elasticsearch for trade history search). Regulators can audit by replaying the event stream for any account from any point in time.

### [Kafka ISR & acks Replication](../../Kafka_ISR_acks_Replication_Guarantees.md)
**Why this system uses it:** Trade execution events: `acks=all + min.insync.replicas=2 + replication_factor=3` — mandatory. Losing a trade event after the matching engine records it as executed is a regulatory violation. If ISR shrinks to 1 broker (one replica falls behind), the producer receives `NotEnoughReplicasException` and retries rather than silently succeeding with single-replica durability. The matching engine's retry logic handles this: the order stays "pending" until the Kafka publish succeeds. Market data feed (price ticks): `acks=1` acceptable — stale by 1 tick is tolerable, throughput matters more.

### [Kafka Log Compaction & Outbox Pattern](../../Kafka_Log_Compaction_Outbox_Pattern.md)
**Why this system uses it:** Compacted topic for current positions: `positions` topic (key=`trader_id:instrument_id`, value=current_position). When a trader's portfolio view service restarts, it reads the compacted topic to initialize current positions without querying the trade history table (billions of rows). Compaction retains only the latest position per trader+instrument pair. Outbox pattern for trade events: matching engine writes executed trade to DB + outbox table in one transaction; Debezium publishes to Kafka. No race condition between DB write and Kafka publish for a trade that may be worth millions of dollars.

### [AWS API Gateway — REST vs HTTP vs WebSocket](../../../aws/22.api-gateway-rest-http-websocket-architect-interview.md)
**Why this system uses it:** Live stock price feed is the quintessential WebSocket API use case — persistent connection per trader, price updates pushed server-to-client at 1-second intervals. REST API for order placement with Usage Plans (retail vs institutional rate limits differ). The 29s timeout is a critical constraint: order execution can take >29s during market volatility — use SQS async pattern (POST /orders → orderId → poll status).

### [Kinesis vs MSK Kafka vs SQS — Streaming Decision](../../../aws/23.kinesis-vs-msk-kafka-vs-sqs-streaming-decision.md)
**Why this system uses it:** Trade execution uses SQS FIFO (`MessageGroupId=ticker`) — all BUY/SELL orders for AAPL process in order, preventing race conditions in the order book. Price feed uses Kinesis Data Streams (partitionKey=ticker) for ordered, replayable market data. Kinesis Enhanced Fan-Out: risk engine + audit service + price broadcast each get dedicated 2MB/s without sharing. MSK alternative if already using Kafka ecosystem for order matching engine.

### [Route53 Advanced Routing Policies](../../../aws/29.route53-routing-policies-dns-failover-architect-interview.md)
**Why this system uses it:** Latency-based routing for trading — 1ms latency difference matters for algorithmic traders. Failover routing: primary trading engine health check (fast, 10s interval) → if unhealthy, Route53 routes to DR region in < 90s. Multi-value answer routing for price feed WebSocket endpoints: 8 endpoints returned, client picks closest — simple load distribution without ALB for WebSocket connections.

### [Multi-Region Architecture](../../../aws/30.multi-region-aurora-global-dynamodb-global-tables.md)
**Why this system uses it:** Active-passive for trading (active-active too risky — conflicting orders in two regions). Aurora Global Database: trade history and portfolio data in primary region (us-east-1), Singapore secondary for AP traders' read queries. CRITICAL: DynamoDB Global Tables NOT suitable for order book or portfolio balance (LWW would create phantom trades). Global Accelerator for trading API — AWS backbone reduces jitter for algo traders + sub-30s failover during regional outage. India SEBI compliance: Indian customer trade data must remain in ap-south-1 (Mumbai).
