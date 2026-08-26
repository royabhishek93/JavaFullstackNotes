# Online Stock Broker / Trading System — Complete LLD Interview Guide

**Interview Duration: 50 min | Difficulty: Very Hard | Must-Know: ⭐⭐⭐⭐⭐ | 15-YOE Focus: Order Book + Matching Engine + Thread Safety**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                 STOCK TRADING SYSTEM                            │
 │                                                                  │
 │  TRADER                ORDER BOOK               MARKET          │
 │  ┌──────────┐         ┌────────────────────┐   ┌────────────┐  │
 │  │ BUY 100  │         │  BIDS (BUY orders) │   │ Last Price │  │
 │  │ SELL 50  │────────►│  ₹200 × 200 shares │   │ ₹199.50    │  │
 │  │ CANCEL   │         │  ₹199 × 150 shares │   │ Volume     │  │
 │  │ MARKET   │         │  ₹198 × 300 shares │   │ 52-week hi │  │
 │  └──────────┘         ├────────────────────┤   └────────────┘  │
 │                       │  ASKS (SELL orders)│                    │
 │                       │  ₹201 × 100 shares │   MATCHING ENGINE │
 │                       │  ₹202 × 250 shares │   ┌────────────┐  │
 │                       │  ₹203 × 400 shares │   │ Price-time │  │
 │                       └────────────────────┘   │ priority   │  │
 │                                                 └────────────┘  │
 │                                                                  │
 │  MATCHING RULE: Buy ₹201 meets Sell ₹201 → TRADE EXECUTES      │
 │  ┌──────────────────────────────────────────────────────────┐  │
 │  │  Best Bid: highest buy price (₹200)                      │  │
 │  │  Best Ask: lowest sell price (₹201)                      │  │
 │  │  SPREAD:   ₹201 - ₹200 = ₹1 (bid-ask spread)           │  │
 │  │  When bid >= ask: MATCH → TRADE                          │  │
 │  └──────────────────────────────────────────────────────────┘  │
 │                                                                  │
 │  ORDER TYPES:                                                   │
 │  ┌──────────────────────────────────────────────────────────┐  │
 │  │  MARKET: execute now at best available price             │  │
 │  │  LIMIT:  execute only at specified price or better       │  │
 │  │  STOP:   trigger a market order when price hits trigger  │  │
 │  └──────────────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────────────┘

 ORDER BOOK STRUCTURE (per stock symbol):
 ┌──────────────────────────────────────────────────────────────────┐
 │  BIDS (BUY) — sorted DESCENDING by price                       │
 │  Price  │ Queue<Order>  (FIFO for same price = time priority)  │
 │  ₹200   │ [Trader A × 100, Trader B × 200]                    │
 │  ₹199   │ [Trader C × 150]                                     │
 │  ₹198   │ [Trader D × 300]                                     │
 │                                                                  │
 │  ASKS (SELL) — sorted ASCENDING by price                       │
 │  Price  │ Queue<Order>                                          │
 │  ₹201   │ [Trader E × 100]                                     │
 │  ₹202   │ [Trader F × 250]                                     │
 └──────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Let me clarify scope.

Functional:
- Place orders: Market, Limit, Stop-Loss orders
- Order Book: maintain bid/ask queues per stock
- Matching Engine: match buy and sell orders, execute trades
- Cancel order: remove from order book if unexecuted
- Order status: PENDING, PARTIALLY_FILLED, FILLED, CANCELLED
- Portfolio: track holdings and cash balance per trader

Non-functional:
- Latency: matching engine must be sub-millisecond — this is the hardest constraint
- Correctness: no order can be overfilled, no negative cash/shares
- Thread safety: multiple traders submitting orders simultaneously
- Fairness: same price → first come first served (time priority)

The core data structure is the Order Book. Getting the Order Book right — price-time priority, atomic matching, correct fills — is 80% of this interview."

---

### Phase 3 — Implementation

```java
// ─── Order Types ─────────────────────────────────────────────────
public enum OrderType   { MARKET, LIMIT, STOP }
public enum OrderSide   { BUY, SELL }
public enum OrderStatus { PENDING, PARTIALLY_FILLED, FILLED, CANCELLED }

// ─── Order ───────────────────────────────────────────────────────
public class Order {
    private final String  orderId;
    private final String  traderId;
    private final String  symbol;
    private final OrderType type;
    private final OrderSide side;
    private final double  limitPrice;   // 0 for MARKET orders
    private final int     quantity;
    private volatile int  filledQuantity;
    private volatile OrderStatus status;
    private final Instant submittedAt;

    public Order(String traderId, String symbol, OrderType type, OrderSide side,
                 double limitPrice, int quantity) {
        this.orderId        = UUID.randomUUID().toString();
        this.traderId       = traderId;
        this.symbol         = symbol;
        this.type           = type;
        this.side           = side;
        this.limitPrice     = limitPrice;
        this.quantity       = quantity;
        this.filledQuantity = 0;
        this.status         = OrderStatus.PENDING;
        this.submittedAt    = Instant.now();
    }

    public synchronized void fill(int fillQty) {
        if (fillQty <= 0 || fillQty > getRemainingQuantity())
            throw new IllegalArgumentException("Invalid fill quantity: " + fillQty);
        filledQuantity += fillQty;
        status = filledQuantity >= quantity ? OrderStatus.FILLED : OrderStatus.PARTIALLY_FILLED;
    }

    public synchronized void cancel() {
        if (status == OrderStatus.FILLED) throw new IllegalStateException("Cannot cancel filled order");
        status = OrderStatus.CANCELLED;
    }

    public int getRemainingQuantity() { return quantity - filledQuantity; }
    public boolean isFilled()         { return status == OrderStatus.FILLED; }
    public boolean isCancelled()      { return status == OrderStatus.CANCELLED; }
    public boolean isActive()         { return status == OrderStatus.PENDING
                                            || status == OrderStatus.PARTIALLY_FILLED; }

    public String getOrderId()       { return orderId; }
    public String getTraderId()      { return traderId; }
    public String getSymbol()        { return symbol; }
    public OrderType getType()       { return type; }
    public OrderSide getSide()       { return side; }
    public double getLimitPrice()    { return limitPrice; }
    public int getQuantity()         { return quantity; }
    public Instant getSubmittedAt()  { return submittedAt; }
}

// ─── Trade ───────────────────────────────────────────────────────
public record Trade(String tradeId, String symbol, String buyOrderId,
                    String sellOrderId, double price, int quantity,
                    Instant executedAt) {
    public Trade(String symbol, String buyId, String sellId, double price, int qty) {
        this(UUID.randomUUID().toString(), symbol, buyId, sellId,
             price, qty, Instant.now());
    }
}

// ─── Order Book (per symbol) ─────────────────────────────────────
public class OrderBook {
    private final String symbol;

    // BUY orders: higher price = higher priority → DESCENDING by price
    // Same price → FIFO by time → use TreeMap<price, Queue<Order>> (desc)
    private final TreeMap<Double, Queue<Order>> bids =
        new TreeMap<>(Collections.reverseOrder());

    // SELL orders: lower price = higher priority → ASCENDING by price
    private final TreeMap<Double, Queue<Order>> asks = new TreeMap<>();

    // Order index for fast cancel/lookup
    private final Map<String, Order> orderIndex = new ConcurrentHashMap<>();

    // The matching engine lock — all operations on this book are serialized
    private final ReentrantLock bookLock = new ReentrantLock();

    private final List<Trade> tradeHistory = new ArrayList<>();

    public OrderBook(String symbol) { this.symbol = symbol; }

    // ─── Add order + trigger matching ────────────────────────────
    public List<Trade> addOrder(Order order) {
        bookLock.lock();
        try {
            orderIndex.put(order.getOrderId(), order);
            List<Trade> trades = match(order);
            if (order.isActive()) {
                // Unmatched remainder → add to book
                addToBook(order);
            }
            return trades;
        } finally {
            bookLock.unlock();
        }
    }

    // ─── Core Matching Engine ────────────────────────────────────
    private List<Trade> match(Order incoming) {
        List<Trade> trades = new ArrayList<>();

        if (incoming.getSide() == OrderSide.BUY) {
            // Incoming BUY: look at ASKS (sells), match lowest ask first
            while (incoming.isActive() && !asks.isEmpty()) {
                Map.Entry<Double, Queue<Order>> bestAsk = asks.firstEntry();
                double askPrice = bestAsk.getKey();

                // BUY LIMIT: only match if ask price ≤ limit price
                if (incoming.getType() == OrderType.LIMIT
                        && askPrice > incoming.getLimitPrice()) break;

                // MARKET order: match at ask price (no price condition)
                Queue<Order> askQueue = bestAsk.getValue();
                Trade trade = executeTrade(incoming, askQueue.peek(), askPrice);
                trades.add(trade);
                tradeHistory.add(trade);

                if (askQueue.peek() != null && askQueue.peek().isFilled()) {
                    askQueue.poll(); // remove fully filled order from front
                }
                if (askQueue.isEmpty()) asks.remove(askPrice);
            }
        } else {
            // Incoming SELL: look at BIDS (buys), match highest bid first
            while (incoming.isActive() && !bids.isEmpty()) {
                Map.Entry<Double, Queue<Order>> bestBid = bids.firstEntry();
                double bidPrice = bestBid.getKey();

                // SELL LIMIT: only match if bid price ≥ limit price
                if (incoming.getType() == OrderType.LIMIT
                        && bidPrice < incoming.getLimitPrice()) break;

                Queue<Order> bidQueue = bestBid.getValue();
                Trade trade = executeTrade(bidQueue.peek(), incoming, bidPrice);
                trades.add(trade);
                tradeHistory.add(trade);

                if (bidQueue.peek() != null && bidQueue.peek().isFilled()) {
                    bidQueue.poll();
                }
                if (bidQueue.isEmpty()) bids.remove(bidPrice);
            }
        }
        return trades;
    }

    private Trade executeTrade(Order buyOrder, Order sellOrder, double tradePrice) {
        int fillQty = Math.min(buyOrder.getRemainingQuantity(),
                               sellOrder.getRemainingQuantity());
        buyOrder.fill(fillQty);
        sellOrder.fill(fillQty);
        return new Trade(symbol, buyOrder.getOrderId(),
                         sellOrder.getOrderId(), tradePrice, fillQty);
    }

    private void addToBook(Order order) {
        TreeMap<Double, Queue<Order>> book =
            order.getSide() == OrderSide.BUY ? bids : asks;
        double price = order.getType() == OrderType.MARKET
            ? (order.getSide() == OrderSide.BUY ? Double.MAX_VALUE : 0.0)
            : order.getLimitPrice();
        book.computeIfAbsent(price, k -> new LinkedList<>()).offer(order);
    }

    // ─── Cancel order ────────────────────────────────────────────
    public boolean cancelOrder(String orderId) {
        bookLock.lock();
        try {
            Order order = orderIndex.get(orderId);
            if (order == null || !order.isActive()) return false;
            order.cancel();
            removeFromBook(order);
            return true;
        } finally {
            bookLock.unlock();
        }
    }

    private void removeFromBook(Order order) {
        TreeMap<Double, Queue<Order>> book =
            order.getSide() == OrderSide.BUY ? bids : asks;
        Queue<Order> queue = book.get(order.getLimitPrice());
        if (queue != null) {
            queue.remove(order);
            if (queue.isEmpty()) book.remove(order.getLimitPrice());
        }
    }

    public double getBestBid() { return bids.isEmpty() ? 0.0 : bids.firstKey(); }
    public double getBestAsk() { return asks.isEmpty() ? 0.0 : asks.firstKey(); }
    public String getSymbol()  { return symbol; }
    public List<Trade> getRecentTrades(int n) {
        return tradeHistory.subList(Math.max(0, tradeHistory.size() - n),
                                    tradeHistory.size());
    }
}

// ─── Trading Engine ──────────────────────────────────────────────
public class TradingEngine {
    private final Map<String, OrderBook>   orderBooks = new ConcurrentHashMap<>();
    private final Map<String, Portfolio>   portfolios = new ConcurrentHashMap<>();
    private final Map<String, Order>       allOrders  = new ConcurrentHashMap<>();

    public List<Trade> submitOrder(Order order) {
        // Pre-check: trader has sufficient funds/shares
        Portfolio portfolio = portfolios.get(order.getTraderId());
        if (portfolio == null) throw new IllegalArgumentException("Unknown trader");

        if (order.getSide() == OrderSide.BUY) {
            double required = order.getType() == OrderType.MARKET
                ? Double.MAX_VALUE  // need to check after execution for market
                : order.getLimitPrice() * order.getQuantity();
            if (order.getType() == OrderType.LIMIT && portfolio.getCash() < required)
                throw new InsufficientFundsException("Insufficient cash");
        } else {
            if (portfolio.getShares(order.getSymbol()) < order.getQuantity())
                throw new InsufficientSharesException("Insufficient shares");
        }

        allOrders.put(order.getOrderId(), order);
        OrderBook book = orderBooks.computeIfAbsent(order.getSymbol(),
            k -> new OrderBook(k));

        List<Trade> trades = book.addOrder(order);
        // Update portfolios for each trade
        trades.forEach(t -> updatePortfolios(t, order.getSymbol()));
        return trades;
    }

    private void updatePortfolios(Trade trade, String symbol) {
        Order buyOrder  = allOrders.get(trade.buyOrderId());
        Order sellOrder = allOrders.get(trade.sellOrderId());
        double cost = trade.price() * trade.quantity();

        Portfolio buyer  = portfolios.get(buyOrder.getTraderId());
        Portfolio seller = portfolios.get(sellOrder.getTraderId());

        buyer.deductCash(cost);
        buyer.addShares(symbol, trade.quantity());
        seller.addCash(cost);
        seller.deductShares(symbol, trade.quantity());
    }

    public boolean cancelOrder(String symbol, String orderId) {
        OrderBook book = orderBooks.get(symbol);
        return book != null && book.cancelOrder(orderId);
    }
}
```

---

## Component Choices

```
COMPONENT              CHOICE                   WHY
──────────────────────────────────────────────────────────────────────
Order book structure   TreeMap<price, Queue>    TreeMap gives O(log N) for
                                               best bid/ask lookup.
                                               Queue (LinkedList): FIFO for
                                               time priority at same price.
                                               BIDS: reverse order (high→low).
                                               ASKS: natural order (low→high).

Matching lock          Per-symbol ReentrantLock Serialize all operations on
                                               one symbol's book.
                                               RELX and INFY books are
                                               independent → no shared lock.
                                               vs global lock: bottleneck.

Order fills            synchronized method     fill() validates and updates
                                               atomically. Prevents overfill.

Order cancel           Remove from Queue       O(N) scan in queue — acceptable
                                               for LLD. Production: doubly-
                                               linked list with O(1) node removal
                                               via order ID → node map.

Portfolio updates       After each trade        Update buyer and seller
                                               portfolios as trades execute.
                                               Keep portfolio state consistent
                                               with executed trades.

Price-time priority    TreeMap + Queue         Price is the first dimension.
                                               Time (FIFO in Queue) is the
                                               tiebreaker. Standard exchange
                                               matching rule.
```

---

## Senior Trap Questions

**Q1: "Two threads submit orders at the same time. Can they deadlock?"**
```
Deadlock requires: Thread 1 holds Lock A, wants Lock B.
                   Thread 2 holds Lock B, wants Lock A.

With per-symbol locks:
  Thread 1: Lock("RELX")
  Thread 2: Lock("INFY")
  → Different symbols → different locks → NO deadlock. ✅

But: what if a single order spans two symbols? (Spread orders: buy RELX, sell INFY)
  Thread 1: Lock("INFY") first, then Lock("RELX")
  Thread 2: Lock("RELX") first, then Lock("INFY")
  → DEADLOCK!

FIX: Always acquire symbol locks in alphabetical order.
  sort([symbolA, symbolB]) → lock in sorted order.
  Thread 1: lock("INFY") then lock("RELX")
  Thread 2: lock("INFY") then lock("RELX")
  → Both try to acquire INFY first → one waits → no circular dependency ✅
```

**Q2: "MARKET order comes in. No sellers exist. What happens?"**
```
Matching loop: incoming BUY MARKET, iterate asks → asks is EMPTY.
Loop doesn't execute. Zero trades.

For MARKET orders: they remain active but can't be added to the book
at Double.MAX_VALUE (implementation hack) for long — it's dangerous.

Better approach: MARKET orders get IOC (Immediate Or Cancel) semantics:
  - Try to fill immediately
  - Whatever can't be filled immediately → CANCEL the remainder
  - User never has a MARKET order sitting in the book waiting

Implementation:
  if (order.getType() == OrderType.MARKET && order.isActive()) {
      order.cancel(); // IOC: cancel unfilled remainder immediately
  }

This prevents MARKET orders from sitting in the book at extreme prices.
```

**Q3: "How does your matching engine handle 10,000 orders per second?"**
```
Current implementation: single ReentrantLock per symbol.
For 10,000 orders/sec for one symbol: all orders serialize.
If matching takes 1ms: max throughput = 1000 orders/sec per symbol. Too slow.

Production optimizations:

1. Lock-free data structures:
   Use java.util.concurrent.atomic classes.
   ConcurrentSkipListMap replaces TreeMap (thread-safe, no lock needed).
   LMAX Disruptor ring buffer: ultra-high-throughput between producer threads
   and matching engine thread. Zero garbage, no contention.

2. Single-threaded matching (per symbol):
   Instead of locking, use a DEDICATED THREAD per symbol.
   All orders for "RELX" go to a queue, consumed by one thread.
   No synchronization needed → maximum throughput.
   This is how real exchanges (NSE, BSE) work:
   each symbol has its own "gateway" thread.

3. Batch processing:
   Collect 100 orders in 1ms → process as a batch → less overhead.

For this LLD interview: explain the single-threaded per-symbol model
as the production approach, current implementation as a starting point.
```

**Q4: "STOP order: how do you implement it?"**
```
STOP order: "If RELX drops below ₹180, sell my 100 shares."
Becomes a MARKET order when trigger price is hit.

Implementation:
  StopOrder: stopPrice, underlying MARKET order
  StopOrderManager: Map<symbol, TreeMap<price, List<StopOrder>>>
  
  On every trade executed at price P:
    stopOrderManager.checkTriggers(symbol, P)
    → finds all STOP orders where stopPrice >= P (for SELL STOP)
    → converts each to MARKET order → submits to order book

  This is done INSIDE the matching loop, after each trade.
  Triggered stop orders may cascade into more trades.
  
  Risk: cascading stops can cause flash crashes.
  Mitigation: circuit breaker (halt trading if price moves >10% in 1 minute).
```

---

## Failure Modes

```
SCENARIO              WHAT HAPPENS             FIX
────────────────────────────────────────────────────────────────────
App crash mid-match   In-flight order          Persistent order log (WAL).
                      lost                     On restart: replay WAL.
                                               Recover order book state.

Oversell (bug)        Shares sold that         Pre-check in submitOrder:
                      trader doesn't own       portfolio.getShares() check.
                                               Validate before adding to book.

Negative cash         Buyer pays for trade     Pre-check cash for LIMIT orders.
                      they can't afford        For MARKET: reserve cash equal
                                               to worst-case price before submit.

Price manipulation    Single trader posts and  Circuit breaker: detect spoofing
(spoofing)            cancels large orders    (order:cancel ratio >5 in 30s)
                      to move price            → flag trader for review.
                                               Rate limit cancel operations.
```

---

## Interview Cheat Sheet

> "A trading system is fundamentally an Order Book problem. The Order Book for each symbol has two sides: bids (buy orders) sorted high-to-low by price, asks (sell orders) sorted low-to-high by price. Each price level has a queue for time priority (first-in = first matched at same price). The matching engine is simple: when a new order arrives, check if the opposite side's best price crosses it — BUY limit ≥ best ask → match. Execute the trade, reduce quantities. A per-symbol ReentrantLock serializes all operations on one book — no two threads can match against the same symbol simultaneously. The deadlock trap for multi-symbol orders: always acquire symbol locks in alphabetical order. MARKET orders are IOC — cancel unfilled remainder immediately after matching, never park them in the book at an extreme price. For production throughput: single-threaded per symbol (dedicated thread per symbol, no locking needed) or LMAX Disruptor for millions of operations per second."
