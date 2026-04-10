# High-Level Design: Online Stock Brokerage System

## System Overview
Design a real-time stock trading platform like Robinhood, TD Ameritrade, or E*TRADE that allows users to buy/sell stocks, track portfolios, view real-time market data, and execute trades with ultra-low latency. System must handle millions of concurrent users and process thousands of trades per second during market hours.

---

## Requirements

### Functional Requirements
1. **User Management**: Registration, KYC verification, account management
2. **Market Data**: Real-time stock prices, charts, historical data, watchlists
3. **Order Placement**: Market orders, limit orders, stop-loss, trailing stops
4. **Order Matching**: Match buy/sell orders (simplified matching engine)
5. **Portfolio Management**: Holdings, profit/loss, performance tracking
6. **Transactions**: Deposits, withdrawals, dividend payments
7. **Research**: Stock analysis, news, analyst ratings, earnings
8. **Notifications**: Price alerts, order execution, margin calls
9. **Compliance**: Regulatory reporting, audit trails, tax documents
10. **Risk Management**: Margin trading, position limits, circuit breakers

### Non-Functional Requirements
1. **Ultra-low Latency**: < 10ms for order placement, < 100ms for execution
2. **High Throughput**: 100K orders/sec during peak trading hours
3. **Consistency**: Strong consistency for orders, accounts, transactions
4. **Availability**: 99.99% during market hours (9:30 AM - 4:00 PM ET)
5. **Real-time Data**: Market data updates < 100ms latency
6. **Security**: SOC 2, financial data encryption, fraud detection
7. **Reliability**: Zero data loss for orders and transactions
8. **Fairness**: FIFO order execution, no front-running
9. **Auditability**: Complete audit trail for compliance

---

## Capacity Estimation

### Traffic
- **Total Users**: 50M users
- **Active Traders (DAU)**: 5M (10% of total)
- **Concurrent Users**: 500K during market open
- **Orders/day**: 20M orders (market hours: 6.5 hours)
- **Orders/second**: 20M / 23400 ≈ 850 orders/sec (peak: 10K orders/sec)
- **Market Data Updates**: 1M symbols × 10 updates/sec = 10M updates/sec
- **Portfolio Views**: 100M/day ≈ 1150 req/sec

### Storage
- **User Accounts**: 50M × 5KB = 250GB
- **Orders** (historical): 20M orders/day × 500 bytes × 252 days/year = 2.5TB/year
- **Transactions**: 50M transactions/day × 1KB × 252 days = 12.6TB/year
- **Market Data** (tick data): 1M symbols × 1KB × 10 updates/sec × 23400 sec/day = 234TB/day
  - Keep 1 year: 58PB (impractical, use time-series compression)
  - With compression (100:1): 580TB/year
- **Total**: ~600TB with replicas (3x) = 1.8PB

### Bandwidth
- **Market Data Streaming**: 10M updates/sec × 100 bytes = 1GB/s = 8 Gbps
- **Order Writes**: 10K orders/sec × 500 bytes = 5MB/s
- **Portfolio Reads**: 1150 req/sec × 50KB = 57MB/s

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                   Users (Web/Mobile/Desktop)                     │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                     CDN (Static Content)                          │
└────────────────────┬─────────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                Load Balancer (Ultra-low latency)                  │
│                    (Anycast routing)                              │
└──────┬────────────────────────┬──────────────────────────────────┘
       │                        │
       ▼                        ▼
┌──────────────────┐    ┌──────────────────────────────────────────┐
│   WebSocket      │    │       API Gateway                        │
│   Gateway        │    │       (REST APIs)                        │
│ (Market Data)    │    └────────┬─────────────────────────────────┘
└──────────────────┘             │
                                 │
      ┌──────────────────────────┼──────────────────────────────────┐
      │                          │                                  │
      ▼                          ▼                                  ▼
┌──────────────┐      ┌──────────────────┐           ┌──────────────┐
│   Order      │      │   Account        │           │   Market     │
│  Service     │      │   Service        │           │   Data       │
│  (Critical)  │      │                  │           │   Service    │
└──────┬───────┘      └──────────────────┘           └──────────────┘
       │                       │                              │
       ▼                       ▼                              ▼
┌──────────────┐      ┌──────────────────┐           ┌──────────────┐
│  Matching    │      │  Portfolio       │           │  Analytics   │
│  Engine      │      │  Service         │           │  Service     │
└──────┬───────┘      └──────────────────┘           └──────────────┘
       │                       │
       ▼                       ▼
┌──────────────┐      ┌──────────────────┐           ┌──────────────┐
│ Settlement   │      │  Transaction     │           │ Notification │
│  Service     │      │  Service         │           │  Service     │
└──────────────┘      └──────────────────┘           └──────────────┘

──────────────────────── Data Layer ─────────────────────────────────

┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │   InfluxDB   │  │    Redis     │  │    Kafka     │
│ (Orders/Acct)│  │(Market Data) │  │ (Cache/RT)   │  │  (Events)    │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘

┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  ScyllaDB    │  │      S3      │  │ Elasticsearch│  │  QuickSight  │
│(Time-series) │  │(Docs/Reports)│  │  (Audit Log) │  │ (Analytics)  │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Core Components

### 1. Account Service

**Responsibilities**:
- User registration and KYC
- Account management (individual, joint, IRA, margin)
- Buying power calculation
- Cash balance management

**Database Schema** (PostgreSQL):
```sql
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255),
    full_name VARCHAR(200),
    ssn_hash VARCHAR(255), -- PII encrypted
    date_of_birth DATE,
    kyc_status VARCHAR(20), -- PENDING, VERIFIED, REJECTED
    kyc_verified_at TIMESTAMP,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE accounts (
    account_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    account_number VARCHAR(20) UNIQUE NOT NULL,
    account_type VARCHAR(20), -- CASH, MARGIN, IRA, ROTH_IRA
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, SUSPENDED, CLOSED
    cash_balance DECIMAL(15, 2) DEFAULT 0.00 CHECK (cash_balance >= 0),
    margin_balance DECIMAL(15, 2) DEFAULT 0.00,
    buying_power DECIMAL(15, 2) GENERATED ALWAYS AS (
        CASE 
            WHEN account_type = 'CASH' THEN cash_balance
            WHEN account_type = 'MARGIN' THEN cash_balance * 2 -- 2x leverage
            ELSE cash_balance
        END
    ) STORED,
    margin_requirement DECIMAL(15, 2) DEFAULT 0.00,
    maintenance_margin DECIMAL(15, 2) DEFAULT 0.00,
    pattern_day_trader BOOLEAN DEFAULT FALSE,
    day_trades_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (user_id, account_type)
);

CREATE TABLE transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(account_id),
    type VARCHAR(20), -- DEPOSIT, WITHDRAWAL, DIVIDEND, INTEREST, FEE
    amount DECIMAL(15, 2) NOT NULL,
    balance_after DECIMAL(15, 2),
    description TEXT,
    reference_id VARCHAR(100), -- External bank transfer ID
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, COMPLETED, FAILED
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    INDEX idx_account_created (account_id, created_at DESC)
);
```

**Buying Power Calculation**:
```java
@Service
public class AccountService {
    
    public BigDecimal calculateBuyingPower(Long accountId) {
        Account account = accountRepo.findById(accountId);
        
        if (account.getAccountType().equals("CASH")) {
            // Cash account: can only use settled cash
            return account.getCashBalance();
        } 
        else if (account.getAccountType().equals("MARGIN")) {
            // Margin account: 2x leverage
            BigDecimal portfolioValue = portfolioService.getPortfolioValue(accountId);
            BigDecimal totalEquity = account.getCashBalance().add(portfolioValue);
            BigDecimal marginUsed = account.getMarginBalance();
            
            // Buying power = (Total Equity × 2) - Margin Used
            return totalEquity.multiply(new BigDecimal(2)).subtract(marginUsed);
        }
        
        return BigDecimal.ZERO;
    }
    
    // Margin call check
    @Scheduled(cron = "0 */15 * * * *") // Every 15 minutes during market hours
    public void checkMarginCalls() {
        List<Account> marginAccounts = accountRepo.findByAccountType("MARGIN");
        
        for (Account account : marginAccounts) {
            BigDecimal portfolioValue = portfolioService.getPortfolioValue(account.getAccountId());
            BigDecimal totalEquity = account.getCashBalance().add(portfolioValue);
            BigDecimal marginUsed = account.getMarginBalance();
            
            // Maintenance margin: 25% of total value
            BigDecimal maintenanceRequirement = portfolioValue.multiply(new BigDecimal(0.25));
            
            if (totalEquity.subtract(marginUsed).compareTo(maintenanceRequirement) < 0) {
                // Issue margin call
                notificationService.sendMarginCall(account);
                
                // If still below after 2 hours, force liquidation
                if (isMarginCallExpired(account)) {
                    liquidatePositions(account);
                }
            }
        }
    }
}
```

**APIs**:
```
POST   /api/v1/accounts                  # Create account
GET    /api/v1/accounts/{id}             # Get account details
GET    /api/v1/accounts/{id}/balance     # Get buying power
POST   /api/v1/accounts/{id}/deposit     # Deposit funds
POST   /api/v1/accounts/{id}/withdraw    # Withdraw funds
GET    /api/v1/accounts/{id}/transactions # Transaction history
```

---

### 2. Market Data Service

**Data Sources**:
- **Stock Exchanges**: NYSE, NASDAQ (via FIX protocol)
- **Data Vendors**: Bloomberg, Reuters, Polygon.io, IEX Cloud
- **Websocket Feeds**: Real-time tick data

**Technology**: InfluxDB (time-series database) + Redis (real-time cache)

**Data Model** (InfluxDB):
```
Measurement: stock_quotes
Tags: symbol, exchange
Fields: price, bid, ask, volume, timestamp
```

**Schema**:
```sql
-- InfluxDB schema
CREATE RETENTION POLICY tick_data ON trading_db DURATION 30d REPLICATION 1;
CREATE RETENTION POLICY daily_data ON trading_db DURATION INF REPLICATION 1;

-- Tick data (high-frequency, short retention)
stock_quotes,symbol=AAPL,exchange=NASDAQ price=175.50,bid=175.48,ask=175.52,volume=1000 1680000000000000000

-- Aggregated data (daily candles, long retention)
stock_candles,symbol=AAPL,interval=1d open=175.00,high=176.50,low=174.00,close=175.50,volume=50000000 1680000000000000000
```

**Real-time Market Data Pipeline**:
```
Exchange (FIX/WebSocket) → Market Data Gateway → Kafka → Stream Processor → InfluxDB + Redis
                                                                    ↓
                                                            WebSocket Server → Clients
```

**Implementation**:
```java
@Service
public class MarketDataService {
    
    @Autowired
    private InfluxDBClient influxDB;
    
    @Autowired
    private RedisTemplate<String, Quote> redis;
    
    @Autowired
    private SimpMessagingTemplate websocket;
    
    // Ingest market data from Kafka
    @KafkaListener(topics = "market-data-raw")
    public void ingestMarketData(Quote quote) {
        // 1. Store in InfluxDB (for historical analysis)
        Point point = Point.measurement("stock_quotes")
            .addTag("symbol", quote.getSymbol())
            .addTag("exchange", quote.getExchange())
            .addField("price", quote.getPrice())
            .addField("bid", quote.getBid())
            .addField("ask", quote.getAsk())
            .addField("volume", quote.getVolume())
            .time(quote.getTimestamp(), WritePrecision.NS);
        
        influxDB.writeApi().writePoint("trading_db", "autogen", point);
        
        // 2. Cache in Redis (for fast lookup)
        redis.opsForValue().set(
            "quote:" + quote.getSymbol(),
            quote,
            Duration.ofSeconds(60)
        );
        
        // 3. Broadcast to subscribed clients via WebSocket
        websocket.convertAndSend("/topic/quotes/" + quote.getSymbol(), quote);
        
        // 4. Check price alerts
        checkPriceAlerts(quote);
    }
    
    // Get latest quote
    public Quote getLatestQuote(String symbol) {
        // Try cache first
        Quote quote = redis.opsForValue().get("quote:" + symbol);
        if (quote != null) {
            return quote;
        }
        
        // Cache miss - query InfluxDB
        String flux = String.format("""
            from(bucket: "trading_db")
              |> range(start: -1m)
              |> filter(fn: (r) => r["_measurement"] == "stock_quotes")
              |> filter(fn: (r) => r["symbol"] == "%s")
              |> last()
            """, symbol);
        
        List<FluxTable> tables = influxDB.getQueryApi().query(flux, "trading_db");
        
        // Parse and return
        if (!tables.isEmpty()) {
            FluxRecord record = tables.get(0).getRecords().get(0);
            quote = parseQuote(record);
            
            // Warm cache
            redis.opsForValue().set("quote:" + symbol, quote, Duration.ofSeconds(60));
            
            return quote;
        }
        
        throw new SymbolNotFoundException(symbol);
    }
    
    // Get historical data (OHLCV)
    public List<Candle> getHistoricalData(String symbol, String interval, Instant start, Instant end) {
        String flux = String.format("""
            from(bucket: "trading_db")
              |> range(start: %s, stop: %s)
              |> filter(fn: (r) => r["_measurement"] == "stock_quotes")
              |> filter(fn: (r) => r["symbol"] == "%s")
              |> window(every: %s)
              |> reduce(fn: (r, accumulator) => ({
                  open: if exists accumulator.open then accumulator.open else r.price,
                  high: if r.price > accumulator.high then r.price else accumulator.high,
                  low: if r.price < accumulator.low then r.price else accumulator.low,
                  close: r.price,
                  volume: accumulator.volume + r.volume
                }),
                identity: {open: 0.0, high: 0.0, low: 999999.0, close: 0.0, volume: 0})
            """, start, end, symbol, interval);
        
        List<FluxTable> tables = influxDB.getQueryApi().query(flux, "trading_db");
        return parseCandles(tables);
    }
}
```

**WebSocket Streaming** (Client-side):
```javascript
// Connect to WebSocket
const socket = new WebSocket('wss://api.trading.com/stream');

// Subscribe to symbols
socket.send(JSON.stringify({
    action: 'subscribe',
    symbols: ['AAPL', 'GOOGL', 'MSFT']
}));

// Receive real-time quotes
socket.onmessage = (event) => {
    const quote = JSON.parse(event.data);
    updateUI(quote);
    // { symbol: 'AAPL', price: 175.50, change: +2.30, changePercent: +1.33, timestamp: 1680000000 }
};
```

---

### 3. Order Service (Critical Component)

**Order Types**:
1. **Market Order**: Execute immediately at current market price
2. **Limit Order**: Execute only at specified price or better
3. **Stop-Loss**: Trigger market order when price drops to stop price
4. **Stop-Limit**: Trigger limit order when price reaches stop price
5. **Trailing Stop**: Dynamic stop that follows price movements

**Database Schema**:
```sql
CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(account_id),
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(4) NOT NULL, -- BUY, SELL
    type VARCHAR(20) NOT NULL, -- MARKET, LIMIT, STOP, STOP_LIMIT, TRAILING_STOP
    quantity INT NOT NULL CHECK (quantity > 0),
    price DECIMAL(10, 4), -- For limit orders
    stop_price DECIMAL(10, 4), -- For stop orders
    trailing_percent DECIMAL(5, 2), -- For trailing stop
    time_in_force VARCHAR(10) DEFAULT 'DAY', -- DAY, GTC, IOC, FOK
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, OPEN, PARTIALLY_FILLED, FILLED, CANCELLED, REJECTED
    filled_quantity INT DEFAULT 0,
    average_fill_price DECIMAL(10, 4),
    commission DECIMAL(10, 2) DEFAULT 0.00,
    rejected_reason TEXT,
    placed_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    filled_at TIMESTAMP,
    INDEX idx_account_placed (account_id, placed_at DESC),
    INDEX idx_symbol_status (symbol, status),
    INDEX idx_status_updated (status, updated_at)
);

CREATE TABLE executions (
    execution_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT REFERENCES orders(order_id),
    symbol VARCHAR(10) NOT NULL,
    side VARCHAR(4) NOT NULL,
    quantity INT NOT NULL,
    price DECIMAL(10, 4) NOT NULL,
    commission DECIMAL(10, 2) DEFAULT 0.00,
    executed_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_order (order_id)
);
```

**Order Placement Flow**:
```
1. Validate order (sufficient funds, valid symbol, market hours)
2. Check buying power / shares available
3. Reserve funds / shares
4. Insert order into database
5. Send to matching engine
6. Matching engine executes order
7. Update order status
8. Update portfolio
9. Publish order event
10. Send notification
```

**Implementation**:
```java
@Service
public class OrderService {
    
    @Transactional(isolation = Isolation.SERIALIZABLE)
    public OrderResponse placeOrder(OrderRequest request) {
        Long accountId = request.getAccountId();
        String symbol = request.getSymbol();
        String side = request.getSide(); // BUY or SELL
        int quantity = request.getQuantity();
        String type = request.getType();
        
        // 1. Validate market hours (9:30 AM - 4:00 PM ET)
        if (!isMarketOpen() && !request.isExtendedHours()) {
            throw new MarketClosedException();
        }
        
        // 2. Validate symbol
        if (!marketDataService.isValidSymbol(symbol)) {
            throw new InvalidSymbolException(symbol);
        }
        
        // 3. Get account
        Account account = accountService.getAccount(accountId);
        if (!account.getStatus().equals("ACTIVE")) {
            throw new AccountNotActiveException();
        }
        
        // 4. Check pattern day trader rule (max 3 day trades in 5 days)
        if (account.getDayTradesCount() >= 3 && !account.isPatternDayTrader()) {
            throw new PatternDayTraderException();
        }
        
        // 5. Check buying power (for BUY) or shares (for SELL)
        if (side.equals("BUY")) {
            BigDecimal estimatedCost = estimateOrderCost(symbol, quantity, type, request.getPrice());
            BigDecimal buyingPower = accountService.calculateBuyingPower(accountId);
            
            if (estimatedCost.compareTo(buyingPower) > 0) {
                throw new InsufficientBuyingPowerException(
                    String.format("Need $%.2f, have $%.2f", estimatedCost, buyingPower)
                );
            }
            
            // Reserve funds
            accountService.reserveFunds(accountId, estimatedCost);
            
        } else { // SELL
            int availableShares = portfolioService.getAvailableShares(accountId, symbol);
            
            if (quantity > availableShares) {
                throw new InsufficientSharesException(
                    String.format("Need %d shares, have %d", quantity, availableShares)
                );
            }
            
            // Reserve shares
            portfolioService.reserveShares(accountId, symbol, quantity);
        }
        
        // 6. Create order
        Order order = new Order();
        order.setAccountId(accountId);
        order.setSymbol(symbol);
        order.setSide(side);
        order.setType(type);
        order.setQuantity(quantity);
        order.setPrice(request.getPrice());
        order.setStopPrice(request.getStopPrice());
        order.setTimeInForce(request.getTimeInForce());
        order.setStatus("PENDING");
        order.setPlacedAt(Instant.now());
        
        orderRepo.save(order);
        
        // 7. Log audit trail
        auditService.logOrder(order, "ORDER_PLACED");
        
        // 8. Send to matching engine
        kafkaProducer.send("order-queue", new OrderEvent(order));
        
        return new OrderResponse(order.getOrderId(), "PENDING", "Order placed successfully");
    }
    
    private BigDecimal estimateOrderCost(String symbol, int quantity, String type, BigDecimal limitPrice) {
        BigDecimal price;
        
        if (type.equals("MARKET")) {
            // Use current ask price (worst case)
            Quote quote = marketDataService.getLatestQuote(symbol);
            price = quote.getAsk();
        } else {
            // Use limit price
            price = limitPrice;
        }
        
        BigDecimal cost = price.multiply(new BigDecimal(quantity));
        BigDecimal commission = calculateCommission(cost); // $0 for most brokers now
        
        return cost.add(commission);
    }
}
```

**Order Cancellation**:
```java
@Transactional
public void cancelOrder(Long orderId, Long accountId) {
    Order order = orderRepo.findById(orderId);
    
    // Verify ownership
    if (!order.getAccountId().equals(accountId)) {
        throw new UnauthorizedException();
    }
    
    // Can only cancel PENDING or OPEN orders
    if (!order.getStatus().equals("PENDING") && !order.getStatus().equals("OPEN")) {
        throw new OrderNotCancellableException();
    }
    
    // Update status
    order.setStatus("CANCELLED");
    order.setUpdatedAt(Instant.now());
    orderRepo.save(order);
    
    // Release reserved funds/shares
    if (order.getSide().equals("BUY")) {
        BigDecimal reservedAmount = estimateOrderCost(
            order.getSymbol(), order.getQuantity(), order.getType(), order.getPrice()
        );
        accountService.releaseFunds(order.getAccountId(), reservedAmount);
    } else {
        portfolioService.releaseShares(order.getAccountId(), order.getSymbol(), order.getQuantity());
    }
    
    // Notify matching engine
    kafkaProducer.send("order-queue", new OrderCancelledEvent(orderId));
    
    // Send notification
    notificationService.sendOrderCancelled(order);
}
```

---

### 4. Matching Engine (Simplified)

**Note**: In reality, exchanges run sophisticated matching engines. This is a simplified version for educational purposes.

**Order Book Structure**:
```
Symbol: AAPL

BUY Orders (Bids) - sorted by price DESC, time ASC
Price    Quantity   Time        Order ID
175.50   100        10:00:00    ORD123
175.48   200        10:00:05    ORD124
175.45   150        10:00:10    ORD125

SELL Orders (Asks) - sorted by price ASC, time ASC
Price    Quantity   Time        Order ID
175.55   100        10:00:02    ORD126
175.58   150        10:00:07    ORD127
175.60   200        10:00:12    ORD128
```

**Matching Algorithm** (Price-Time Priority):
```java
@Service
public class MatchingEngine {
    
    // In-memory order book (per symbol)
    private Map<String, OrderBook> orderBooks = new ConcurrentHashMap<>();
    
    @KafkaListener(topics = "order-queue")
    public void processOrder(OrderEvent event) {
        Order order = event.getOrder();
        
        if (order.getStatus().equals("CANCELLED")) {
            removeOrder(order);
            return;
        }
        
        // Get order book for symbol
        OrderBook book = orderBooks.computeIfAbsent(
            order.getSymbol(),
            k -> new OrderBook(order.getSymbol())
        );
        
        if (order.getType().equals("MARKET")) {
            executeMarketOrder(book, order);
        } else if (order.getType().equals("LIMIT")) {
            executeLimitOrder(book, order);
        }
        
        // Update order status
        orderService.updateOrderStatus(order);
    }
    
    private void executeMarketOrder(OrderBook book, Order order) {
        int remainingQty = order.getQuantity();
        
        // Get opposite side
        PriorityQueue<Order> oppositeOrders = order.getSide().equals("BUY") 
            ? book.getAsks() 
            : book.getBids();
        
        while (remainingQty > 0 && !oppositeOrders.isEmpty()) {
            Order matchingOrder = oppositeOrders.peek();
            
            int matchQty = Math.min(remainingQty, matchingOrder.getQuantity());
            BigDecimal matchPrice = matchingOrder.getPrice();
            
            // Execute trade
            executeTrade(order, matchingOrder, matchQty, matchPrice);
            
            remainingQty -= matchQty;
            matchingOrder.setQuantity(matchingOrder.getQuantity() - matchQty);
            
            if (matchingOrder.getQuantity() == 0) {
                oppositeOrders.poll(); // Remove fully filled order
            }
        }
        
        if (remainingQty == 0) {
            order.setStatus("FILLED");
        } else if (remainingQty < order.getQuantity()) {
            order.setStatus("PARTIALLY_FILLED");
        } else {
            order.setStatus("REJECTED");
            order.setRejectedReason("No matching orders available");
        }
    }
    
    private void executeLimitOrder(OrderBook book, Order order) {
        // Check if limit order can be immediately matched
        PriorityQueue<Order> oppositeOrders = order.getSide().equals("BUY") 
            ? book.getAsks() 
            : book.getBids();
        
        int remainingQty = order.getQuantity();
        
        while (remainingQty > 0 && !oppositeOrders.isEmpty()) {
            Order matchingOrder = oppositeOrders.peek();
            
            // Check if price matches
            boolean priceMatches = order.getSide().equals("BUY")
                ? order.getPrice().compareTo(matchingOrder.getPrice()) >= 0
                : order.getPrice().compareTo(matchingOrder.getPrice()) <= 0;
            
            if (!priceMatches) {
                break; // No more matches possible
            }
            
            int matchQty = Math.min(remainingQty, matchingOrder.getQuantity());
            BigDecimal matchPrice = matchingOrder.getPrice(); // Taker gets maker's price
            
            executeTrade(order, matchingOrder, matchQty, matchPrice);
            
            remainingQty -= matchQty;
            matchingOrder.setQuantity(matchingOrder.getQuantity() - matchQty);
            
            if (matchingOrder.getQuantity() == 0) {
                oppositeOrders.poll();
            }
        }
        
        // Add remaining order to book
        if (remainingQty > 0) {
            order.setQuantity(remainingQty);
            order.setStatus("OPEN");
            
            if (order.getSide().equals("BUY")) {
                book.addBid(order);
            } else {
                book.addAsk(order);
            }
        } else {
            order.setStatus("FILLED");
        }
    }
    
    private void executeTrade(Order buyOrder, Order sellOrder, int quantity, BigDecimal price) {
        // Create execution records
        Execution buyExecution = new Execution(
            buyOrder.getOrderId(),
            buyOrder.getSymbol(),
            "BUY",
            quantity,
            price,
            Instant.now()
        );
        
        Execution sellExecution = new Execution(
            sellOrder.getOrderId(),
            sellOrder.getSymbol(),
            "SELL",
            quantity,
            price,
            Instant.now()
        );
        
        executionRepo.saveAll(List.of(buyExecution, sellExecution));
        
        // Update portfolios
        portfolioService.addShares(buyOrder.getAccountId(), buyOrder.getSymbol(), quantity, price);
        portfolioService.removeShares(sellOrder.getAccountId(), sellOrder.getSymbol(), quantity, price);
        
        // Update accounts
        BigDecimal cost = price.multiply(new BigDecimal(quantity));
        accountService.debitCash(buyOrder.getAccountId(), cost);
        accountService.creditCash(sellOrder.getAccountId(), cost);
        
        // Publish trade event
        kafkaProducer.send("trade-events", new TradeEvent(buyExecution, sellExecution));
        
        // Send notifications
        notificationService.sendOrderFilled(buyOrder, quantity, price);
        notificationService.sendOrderFilled(sellOrder, quantity, price);
    }
}

// Order Book data structure
class OrderBook {
    private String symbol;
    private PriorityQueue<Order> bids; // Max heap (highest price first)
    private PriorityQueue<Order> asks; // Min heap (lowest price first)
    
    public OrderBook(String symbol) {
        this.symbol = symbol;
        this.bids = new PriorityQueue<>(
            Comparator.comparing(Order::getPrice).reversed()
                .thenComparing(Order::getPlacedAt)
        );
        this.asks = new PriorityQueue<>(
            Comparator.comparing(Order::getPrice)
                .thenComparing(Order::getPlacedAt)
        );
    }
}
```

---

### 5. Portfolio Service

**Responsibilities**:
- Track holdings (positions)
- Calculate profit/loss
- Track cost basis
- Generate performance reports

**Database Schema**:
```sql
CREATE TABLE positions (
    position_id BIGSERIAL PRIMARY KEY,
    account_id BIGINT REFERENCES accounts(account_id),
    symbol VARCHAR(10) NOT NULL,
    quantity INT NOT NULL,
    available_quantity INT NOT NULL, -- Not reserved in pending orders
    average_cost DECIMAL(10, 4) NOT NULL,
    total_cost DECIMAL(15, 2) NOT NULL,
    market_value DECIMAL(15, 2),
    unrealized_pnl DECIMAL(15, 2),
    realized_pnl DECIMAL(15, 2) DEFAULT 0.00,
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (account_id, symbol)
);

CREATE TABLE position_history (
    history_id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    action VARCHAR(10), -- BUY, SELL
    quantity INT NOT NULL,
    price DECIMAL(10, 4) NOT NULL,
    commission DECIMAL(10, 2),
    execution_id BIGINT REFERENCES executions(execution_id),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_account_symbol (account_id, symbol, created_at DESC)
);
```

**Position Update** (on trade execution):
```java
@Service
public class PortfolioService {
    
    @Transactional
    public void addShares(Long accountId, String symbol, int quantity, BigDecimal price) {
        Position position = positionRepo.findByAccountIdAndSymbol(accountId, symbol);
        
        if (position == null) {
            // Create new position
            position = new Position();
            position.setAccountId(accountId);
            position.setSymbol(symbol);
            position.setQuantity(quantity);
            position.setAvailableQuantity(quantity);
            position.setAverageCost(price);
            position.setTotalCost(price.multiply(new BigDecimal(quantity)));
        } else {
            // Update existing position (weighted average cost)
            BigDecimal totalCost = position.getTotalCost()
                .add(price.multiply(new BigDecimal(quantity)));
            int totalQuantity = position.getQuantity() + quantity;
            
            position.setQuantity(totalQuantity);
            position.setAvailableQuantity(position.getAvailableQuantity() + quantity);
            position.setTotalCost(totalCost);
            position.setAverageCost(totalCost.divide(new BigDecimal(totalQuantity), 4, RoundingMode.HALF_UP));
        }
        
        position.setUpdatedAt(Instant.now());
        positionRepo.save(position);
        
        // Log history
        PositionHistory history = new PositionHistory(accountId, symbol, "BUY", quantity, price);
        positionHistoryRepo.save(history);
    }
    
    @Transactional
    public void removeShares(Long accountId, String symbol, int quantity, BigDecimal price) {
        Position position = positionRepo.findByAccountIdAndSymbol(accountId, symbol);
        
        if (position == null || position.getQuantity() < quantity) {
            throw new InsufficientSharesException();
        }
        
        // Calculate realized P&L
        BigDecimal costBasis = position.getAverageCost().multiply(new BigDecimal(quantity));
        BigDecimal proceeds = price.multiply(new BigDecimal(quantity));
        BigDecimal realizedPnL = proceeds.subtract(costBasis);
        
        // Update position
        position.setQuantity(position.getQuantity() - quantity);
        position.setAvailableQuantity(position.getAvailableQuantity() - quantity);
        position.setTotalCost(position.getTotalCost().subtract(costBasis));
        position.setRealizedPnl(position.getRealizedPnl().add(realizedPnL));
        position.setUpdatedAt(Instant.now());
        
        if (position.getQuantity() == 0) {
            positionRepo.delete(position); // Close position
        } else {
            positionRepo.save(position);
        }
        
        // Log history
        PositionHistory history = new PositionHistory(accountId, symbol, "SELL", quantity, price);
        positionHistoryRepo.save(history);
    }
    
    // Calculate unrealized P&L for all positions
    @Scheduled(fixedRate = 60000) // Every minute during market hours
    public void updatePortfolioValues() {
        List<Position> positions = positionRepo.findAll();
        
        for (Position position : positions) {
            try {
                Quote quote = marketDataService.getLatestQuote(position.getSymbol());
                
                BigDecimal marketValue = quote.getPrice().multiply(new BigDecimal(position.getQuantity()));
                BigDecimal unrealizedPnL = marketValue.subtract(position.getTotalCost());
                
                position.setMarketValue(marketValue);
                position.setUnrealizedPnl(unrealizedPnL);
                position.setUpdatedAt(Instant.now());
                
                positionRepo.save(position);
            } catch (Exception e) {
                log.error("Failed to update position for {}: {}", position.getSymbol(), e.getMessage());
            }
        }
    }
    
    // Get portfolio value
    public BigDecimal getPortfolioValue(Long accountId) {
        List<Position> positions = positionRepo.findByAccountId(accountId);
        
        return positions.stream()
            .map(Position::getMarketValue)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
    }
}
```

**APIs**:
```
GET    /api/v1/portfolios/{accountId}           # Get portfolio summary
GET    /api/v1/portfolios/{accountId}/positions # Get all positions
GET    /api/v1/portfolios/{accountId}/performance # Performance metrics
GET    /api/v1/portfolios/{accountId}/history   # Position history
```

---

## Scalability & Performance Optimization

### 1. Ultra-low Latency Architecture

**Colocation**: Host matching engine close to exchange (reduces network latency from 100ms to < 1ms)

**In-Memory Processing**:
```java
// Keep order book entirely in memory
private Map<String, OrderBook> orderBooks = new ConcurrentHashMap<>();

// Use lock-free data structures
private LongAdder orderCount = new LongAdder();
private AtomicLong lastTradePrice = new AtomicLong();
```

**LMAX Disruptor** (high-performance queue):
```java
// Replace Kafka with Disruptor for critical path
Disruptor<OrderEvent> disruptor = new Disruptor<>(
    OrderEvent::new,
    1024 * 1024, // Ring buffer size
    Executors.defaultThreadFactory(),
    ProducerType.MULTI,
    new YieldingWaitStrategy() // Lowest latency wait strategy
);

disruptor.handleEventsWith(matchingEngineHandler);
disruptor.start();
```

**Zero-Copy Networking**:
```java
// Use Aeron for ultra-low latency messaging
Aeron aeron = Aeron.connect();
Publication publication = aeron.addPublication("aeron:ipc", 1001);
Subscription subscription = aeron.addSubscription("aeron:ipc", 1001);
```

### 2. Database Optimization

**Hot-Cold Data Separation**:
```sql
-- Hot data (today's orders): In-memory PostgreSQL table
CREATE UNLOGGED TABLE orders_today AS SELECT * FROM orders WHERE placed_at >= CURRENT_DATE;

-- Cold data (historical orders): Partitioned by date
CREATE TABLE orders PARTITION BY RANGE (placed_at);
CREATE TABLE orders_2024_04 PARTITION OF orders FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
```

**Read Replicas**:
```
Master: Order writes, account updates
Replica 1: Market data queries
Replica 2: Portfolio reads, transaction history
Replica 3: Analytics, reports
```

### 3. Caching Strategy

```java
// Level 1: Application cache (Caffeine)
Cache<String, Quote> l1Cache = Caffeine.newBuilder()
    .maximumSize(100000)
    .expireAfterWrite(1, TimeUnit.SECONDS)
    .build();

// Level 2: Redis (distributed)
@Cacheable(value = "quotes", key = "#symbol", ttl = 60)
public Quote getQuote(String symbol) { ... }

// Level 3: Database
```

### 4. Horizontal Scaling

**Shard by Symbol**:
```
Matching Engine 1: Symbols A-H
Matching Engine 2: Symbols I-P
Matching Engine 3: Symbols Q-Z
```

**Shard by Account**:
```
Account Service 1: Accounts 0-999999
Account Service 2: Accounts 1000000-1999999
...
```

---

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend** | Java 17 + Spring Boot | Low latency, mature ecosystem |
| **Matching Engine** | C++ / Rust | Ultra-low latency, memory control |
| **Database (OLTP)** | PostgreSQL / CockroachDB | ACID, distributed |
| **Time-Series DB** | InfluxDB / TimescaleDB | Optimized for market data |
| **Cache** | Redis / Hazelcast | In-memory speed |
| **Message Queue** | Kafka / LMAX Disruptor | High throughput, low latency |
| **Real-time Stream** | WebSocket (Socket.io) | Bidirectional, low overhead |
| **Search** | Elasticsearch | Symbol search, audit logs |
| **Object Storage** | S3 | Documents, reports |
| **Monitoring** | Prometheus + Grafana | Real-time metrics |
| **Tracing** | Jaeger | Distributed tracing |

---

## Interview Q&A

### Q1: How do you ensure exactly-once execution of orders?
**Answer**:
1. **Idempotent Order IDs**: Client generates unique order ID
2. **Database Constraints**: UNIQUE constraint on order_id
3. **Distributed Transactions**: Saga pattern with compensating transactions
4. **At-least-once delivery**: Kafka with consumer offset management
5. **Deduplication**: Check order_id before processing

### Q2: How do you handle market data at 10M updates/sec?
**Answer**:
1. **Sampling**: Only store 1 update per second for most symbols
2. **Compression**: Time-series compression (100:1 ratio)
3. **Aggregation**: Pre-aggregate to 1min/5min/1hour candles
4. **Partitioning**: Separate hot (realtime) and cold (historical) data
5. **Caching**: Cache latest quote in Redis

### Q3: How do you prevent race conditions in order matching?
**Answer**:
1. **Single-threaded per symbol**: Each symbol has dedicated thread
2. **Lock-free data structures**: ConcurrentHashMap, AtomicLong
3. **LMAX Disruptor**: Ring buffer for sequential processing
4. **Database locks**: SELECT FOR UPDATE for critical sections
5. **Optimistic locking**: Version field for conflict detection

### Q4: How do you calculate buying power with margin?
**Answer**:
```
For Cash Account:
  Buying Power = Cash Balance

For Margin Account (2x leverage):
  Total Equity = Cash + Market Value of Holdings
  Margin Used = Amount borrowed
  Buying Power = (Total Equity × 2) - Margin Used
  
Maintenance Margin: Must maintain 25% equity
  If (Total Equity - Margin Used) < 25% of Market Value:
    Issue Margin Call
```

### Q5: How do you handle stop-loss orders during market crash?
**Answer**:
1. **Circuit Breakers**: Halt trading if price moves > 10% in 5 mins
2. **Order Queue**: Queue stop-losses triggered, execute gradually
3. **Price Limits**: Limit orders instead of market orders
4. **Gap Protection**: Don't execute if price gaps too far
5. **Priority**: Time priority (FIFO) for fairness

### Q6: How do you ensure regulatory compliance?
**Answer**:
1. **Audit Trail**: Log every order, execution, account change
2. **Immutable Logs**: Write-once storage (S3 Glacier)
3. **Real-time Monitoring**: Detect wash trading, spoofing
4. **Pattern Day Trader**: Track day trades, enforce limits
5. **Tax Reporting**: Generate 1099 forms, cost basis reports
6. **Data Retention**: 7 years for SEC compliance

### Q7: How do you test the system?
**Answer**:
1. **Unit Tests**: Test individual components
2. **Load Testing**: Simulate 100K orders/sec (Gatling)
3. **Chaos Engineering**: Randomly kill services
4. **Market Replay**: Replay historical market data
5. **Canary Deployment**: Test on 1% of traffic first
6. **Shadow Mode**: Run new matching engine in parallel

### Q8: How do you handle database failover?
**Answer**:
1. **Synchronous Replication**: Master-slave with immediate replication
2. **Automatic Failover**: Promote slave within 10 seconds
3. **Connection Pooling**: Retry logic, circuit breaker
4. **Read Replicas**: Continue serving reads during failover
5. **Data Validation**: Compare master and replica checksums

### Q9: How would you implement fractional shares?
**Answer**:
1. **Store as Decimal**: `quantity DECIMAL(10, 6)` instead of INT
2. **Order Aggregation**: Batch fractional orders, execute as whole
3. **Omnibus Account**: Broker holds whole shares, allocates fractions to users
4. **Rounding**: Handle rounding errors fairly (round-robin)

### Q10: How do you optimize for mobile apps?
**Answer**:
1. **GraphQL**: Clients request only needed fields
2. **Data Pagination**: Infinite scroll for order history
3. **Push Notifications**: FCM for price alerts
4. **Offline Mode**: Cache last known data
5. **Compression**: Gzip responses
6. **CDN**: Serve static assets from edge

---

## Cost Estimation (AWS - Monthly)

| Service | Specification | Cost |
|---------|--------------|------|
| **EC2** (App Servers) | 50 × c5n.4xlarge (16 vCPU, 42GB) | $18,000 |
| **RDS PostgreSQL** | db.r5.4xlarge Multi-AZ + replicas | $12,000 |
| **InfluxDB Cloud** | 10TB/month ingestion + storage | $15,000 |
| **ElastiCache Redis** | 20 × cache.r5.xlarge | $6,000 |
| **MSK** (Kafka) | 9 brokers × kafka.m5.2xlarge | $4,500 |
| **S3** | 100TB storage | $2,300 |
| **CloudFront** | 10TB transfer | $850 |
| **API Gateway** | 1B requests | $3,500 |
| **Market Data** | Bloomberg Terminal (500 users) | $250,000 |
| **Monitoring** | Datadog | $5,000 |
| **Total** | | **~$317,000/month** |

**Revenue Model**:
- Commission: $0 (most brokers now)
- Payment for Order Flow (PFOF): $0.002 per share
- Margin Interest: 8% APR on borrowed funds
- Premium Subscriptions: $5/month × 1M users = $5M/month

---

**This comprehensive HLD covers a production-grade stock brokerage system!**
