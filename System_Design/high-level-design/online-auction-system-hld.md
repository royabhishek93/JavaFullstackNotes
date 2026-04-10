# High-Level Design: Online Auction System (eBay-style)

## System Overview
Design a real-time online auction platform like eBay where users can list items for auction, place bids, and complete purchases. The system handles millions of concurrent auctions with real-time bid updates, automatic auction closing, and payment processing.

---

## Requirements

### Functional Requirements
1. **User Management**: Registration, authentication, profile management, seller ratings
2. **Auction Creation**: Sellers list items with starting price, reserve price, duration, images
3. **Bidding**: Place bids, automatic bid increment, proxy bidding (auto-bid up to max)
4. **Real-time Updates**: Live bid updates to all watchers
5. **Search & Discovery**: Search by category, price, location, ending soon
6. **Auction Closing**: Automatic closure at end time, winner notification
7. **Payment**: Integrated payment processing, escrow service
8. **Notifications**: Bid alerts, outbid alerts, auction ending, won/lost notifications
9. **Watch List**: Users can watch/favorite auctions
10. **Fraud Detection**: Shill bidding detection, suspicious activity monitoring

### Non-Functional Requirements
1. **Consistency**: Strong consistency for bid placement (no duplicate winners)
2. **Low Latency**: < 100ms for bid placement, < 1s for real-time updates
3. **Availability**: 99.95% uptime (4.38 hours downtime/year)
4. **Scalability**: Support 100M users, 50M concurrent auctions
5. **Real-time**: Bid updates pushed within 1 second
6. **Fairness**: Timestamp-based bid ordering, no race conditions
7. **Security**: Secure payments, user data protection

---

## Capacity Estimation

### Traffic
- **Total Users**: 100M users, 10M DAU
- **Active Auctions**: 50M concurrent auctions
- **New Auctions/day**: 5M listings
- **Bids/day**: 500M bids (avg 10 bids per auction)
- **Bids/second**: 500M / 86400 ≈ 5800 bids/sec (peak: 20K bids/sec)
- **Search queries**: 100M/day ≈ 1200 QPS
- **WebSocket connections**: 1M concurrent users watching auctions

### Storage
- **User profiles**: 100M × 2KB = 200GB
- **Auction data**: 50M × 5KB = 250GB (active), 10TB (historical)
- **Bid history**: 500M bids/day × 200 bytes × 365 days = 36TB/year
- **Images**: 50M auctions × 5 images × 500KB = 125TB
- **Total storage**: ~150TB (with replicas: 450TB)

### Bandwidth
- **Writes**: 5800 bids/sec × 500 bytes = 2.9MB/s
- **Reads**: 1M watchers × 1KB update/sec = 1GB/s
- **Images**: 1200 QPS × 5 images × 500KB = 3GB/s (use CDN)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Users (Web/Mobile)                          │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                CDN (CloudFront/Cloudflare)                       │
│                   (Static content, images)                       │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Load Balancer (Application Gateway)                 │
│                    (SSL termination)                             │
└────────┬──────────────────────┬─────────────────────────────────┘
         │                      │
         ▼                      ▼
┌──────────────────┐   ┌──────────────────────────────────────────┐
│  API Gateway     │   │     WebSocket Gateway                    │
│  (REST/GraphQL)  │   │  (Real-time bid updates)                 │
└────────┬─────────┘   └────────┬─────────────────────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Microservices Layer                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  User    │ │ Auction  │ │ Bidding  │ │ Payment  │           │
│  │ Service  │ │ Service  │ │ Service  │ │ Service  │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │ Search   │ │Notification│ │ Image   │ │  Fraud   │           │
│  │ Service  │ │  Service  │ │ Service  │ │Detection │           │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
└────────┬──────────────────────┬──────────────────────┬──────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌──────────────────┐   ┌──────────────────┐  ┌──────────────────┐
│   PostgreSQL     │   │   Redis Cache    │  │   Kafka          │
│   (Primary DB)   │   │  (Hot auctions)  │  │  (Event Stream)  │
│   (Master-Slave) │   │                  │  │                  │
└──────────────────┘   └──────────────────┘  └──────────────────┘
         │                      
         ▼                      
┌──────────────────┐   ┌──────────────────┐  ┌──────────────────┐
│  Elasticsearch   │   │      S3          │  │   Scheduler      │
│  (Search Index)  │   │  (Images/Logs)   │  │ (Auction Closer) │
└──────────────────┘   └──────────────────┘  └──────────────────┘
```

---

## Core Components

### 1. Auction Service

**Responsibilities**:
- Create, update, delete auctions
- Manage auction lifecycle (scheduled, active, closing, closed)
- Set reserve prices, buy-now prices
- Handle auction extensions (anti-snipe: extend if bid in last 5 mins)

**Database Schema**:
```sql
CREATE TABLE auctions (
    auction_id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category_id INT,
    starting_price DECIMAL(10,2),
    reserve_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    buy_now_price DECIMAL(10,2),
    bid_increment DECIMAL(10,2) DEFAULT 1.00,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20), -- SCHEDULED, ACTIVE, CLOSING, SOLD, UNSOLD
    winner_id BIGINT,
    total_bids INT DEFAULT 0,
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    INDEX idx_status_end_time (status, end_time),
    INDEX idx_category_status (category_id, status)
);

CREATE TABLE auction_images (
    image_id BIGSERIAL PRIMARY KEY,
    auction_id BIGINT REFERENCES auctions(auction_id),
    image_url VARCHAR(500),
    display_order INT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**API Endpoints**:
```
POST   /api/v1/auctions              # Create auction
GET    /api/v1/auctions/{id}         # Get auction details
PUT    /api/v1/auctions/{id}         # Update auction (before bids)
DELETE /api/v1/auctions/{id}         # Cancel auction
GET    /api/v1/auctions/search       # Search auctions
GET    /api/v1/users/{id}/auctions   # User's auctions (selling)
```

---

### 2. Bidding Service (Core Component)

**Critical Requirements**:
- **Atomicity**: No duplicate winning bids
- **Ordering**: Process bids in timestamp order
- **Low latency**: < 100ms response time
- **Fairness**: Handle race conditions correctly

**Bid Placement Flow**:
```
1. User places bid
2. Validate bid (amount > current_price + increment)
3. Acquire distributed lock on auction_id
4. Re-check current price (optimistic locking)
5. Insert bid record
6. Update auction current_price
7. Release lock
8. Publish bid event to Kafka
9. Send real-time update via WebSocket
10. Trigger notifications (outbid users)
```

**Database Schema**:
```sql
CREATE TABLE bids (
    bid_id BIGSERIAL PRIMARY KEY,
    auction_id BIGINT NOT NULL,
    bidder_id BIGINT NOT NULL,
    bid_amount DECIMAL(10,2) NOT NULL,
    bid_time TIMESTAMP DEFAULT NOW(),
    is_auto_bid BOOLEAN DEFAULT FALSE,
    max_auto_bid DECIMAL(10,2), -- For proxy bidding
    status VARCHAR(20), -- ACTIVE, OUTBID, WINNING, WON, RETRACTED
    ip_address INET,
    user_agent TEXT,
    INDEX idx_auction_time (auction_id, bid_time DESC),
    INDEX idx_bidder_time (bidder_id, bid_time DESC),
    UNIQUE (auction_id, bid_time, bidder_id) -- Prevent duplicates
);
```

**Bid Placement Logic** (Pessimistic Locking):
```java
@Transactional
public BidResponse placeBid(Long auctionId, Long userId, BigDecimal amount) {
    // 1. Acquire distributed lock (Redis/Zookeeper)
    Lock lock = redisLock.acquire("auction:" + auctionId, 5000);
    
    try {
        // 2. Get auction with row-level lock
        Auction auction = auctionRepo.findByIdForUpdate(auctionId);
        
        // 3. Validate
        if (auction.getEndTime().isBefore(Instant.now())) {
            throw new AuctionClosedException();
        }
        if (amount.compareTo(auction.getCurrentPrice().add(auction.getBidIncrement())) < 0) {
            throw new InvalidBidAmountException();
        }
        if (userId.equals(auction.getSellerId())) {
            throw new SelfBiddingNotAllowedException();
        }
        
        // 4. Place bid
        Bid bid = new Bid(auctionId, userId, amount, Instant.now());
        bidRepo.save(bid);
        
        // 5. Update auction
        auction.setCurrentPrice(amount);
        auction.setTotalBids(auction.getTotalBids() + 1);
        auctionRepo.save(auction);
        
        // 6. Publish event
        kafkaProducer.send("bid-events", new BidEvent(auctionId, userId, amount));
        
        // 7. Check for auto-extension (anti-snipe)
        if (ChronoUnit.MINUTES.between(Instant.now(), auction.getEndTime()) < 5) {
            auction.setEndTime(auction.getEndTime().plus(5, ChronoUnit.MINUTES));
        }
        
        return new BidResponse(bid.getBidId(), "SUCCESS", auction.getCurrentPrice());
        
    } finally {
        lock.release();
    }
}
```

**Proxy Bidding (Automatic Bidding)**:
```java
// User sets max bid: $100
// Current price: $50
// System automatically bids up to $100 as others bid

public void handleAutoBidding(Long auctionId, BigDecimal newBid) {
    List<Bid> autoBids = bidRepo.findActiveAutoBids(auctionId);
    
    for (Bid autoBid : autoBids) {
        if (autoBid.getMaxAutoBid().compareTo(newBid) > 0) {
            BigDecimal nextBid = newBid.add(auction.getBidIncrement());
            if (nextBid.compareTo(autoBid.getMaxAutoBid()) <= 0) {
                placeBid(auctionId, autoBid.getBidderId(), nextBid);
            }
        }
    }
}
```

---

### 3. Real-time Update System (WebSocket)

**Architecture**:
```
┌──────────┐         ┌──────────────────┐         ┌──────────────┐
│  User    │◀──WS───▶│  WebSocket       │◀───────▶│   Redis      │
│ Browser  │         │  Server (Node.js)│  PubSub │   (PubSub)   │
└──────────┘         └──────────────────┘         └──────┬───────┘
                              ▲                           │
                              │                           │
                     Subscribe to auction:{id}            ▼
                                                  ┌──────────────┐
                                                  │  Kafka       │
                                                  │ (Bid Events) │
                                                  └──────────────┘
```

**Implementation** (Node.js + Socket.io):
```javascript
// WebSocket Server
io.on('connection', (socket) => {
    socket.on('watch-auction', (auctionId) => {
        // Subscribe to Redis pub/sub
        redis.subscribe(`auction:${auctionId}`);
        socket.join(`auction:${auctionId}`);
    });
    
    socket.on('unwatch-auction', (auctionId) => {
        socket.leave(`auction:${auctionId}`);
    });
});

// Bid Event Consumer (Kafka)
kafka.consume('bid-events', (bidEvent) => {
    const update = {
        auctionId: bidEvent.auctionId,
        currentPrice: bidEvent.amount,
        bidderName: bidEvent.bidderName,
        timestamp: bidEvent.timestamp,
        totalBids: bidEvent.totalBids
    };
    
    // Publish to Redis
    redis.publish(`auction:${bidEvent.auctionId}`, JSON.stringify(update));
    
    // Redis pub/sub triggers WebSocket broadcast
});

// Redis subscriber
redis.on('message', (channel, message) => {
    const auctionId = channel.split(':')[1];
    io.to(`auction:${auctionId}`).emit('bid-update', JSON.parse(message));
});
```

---

### 4. Auction Scheduler & Auto-Close Service

**Responsibilities**:
- Automatically close auctions at end_time
- Determine winners
- Trigger payment processing
- Send notifications

**Implementation Strategy**:

**Option 1: Polling (Simple but inefficient)**
```sql
-- Run every 10 seconds
SELECT auction_id FROM auctions 
WHERE status = 'ACTIVE' 
  AND end_time <= NOW()
  AND end_time > NOW() - INTERVAL '10 seconds';
```

**Option 2: Scheduled Tasks (Better)**
```java
@Scheduled(fixedRate = 5000) // Run every 5 seconds
public void closeAuctions() {
    List<Auction> closingAuctions = auctionRepo.findByStatusAndEndTimeBefore(
        "ACTIVE", Instant.now()
    );
    
    for (Auction auction : closingAuctions) {
        closeAuction(auction.getAuctionId());
    }
}

@Transactional
public void closeAuction(Long auctionId) {
    Auction auction = auctionRepo.findById(auctionId);
    
    // Get highest bid
    Bid winningBid = bidRepo.findTopByAuctionIdOrderByBidAmountDesc(auctionId);
    
    if (winningBid != null && winningBid.getBidAmount().compareTo(auction.getReservePrice()) >= 0) {
        auction.setStatus("SOLD");
        auction.setWinnerId(winningBid.getBidderId());
        
        // Trigger payment
        paymentService.createPaymentIntent(auction, winningBid);
        
        // Notify winner
        notificationService.sendAuctionWonNotification(winningBid.getBidderId(), auction);
        
        // Notify losers
        List<Bid> losingBids = bidRepo.findByAuctionIdAndBidderIdNot(auctionId, winningBid.getBidderId());
        for (Bid losingBid : losingBids) {
            notificationService.sendAuctionLostNotification(losingBid.getBidderId(), auction);
        }
    } else {
        auction.setStatus("UNSOLD");
    }
    
    auctionRepo.save(auction);
}
```

**Option 3: Delay Queue (Most Efficient)**
```java
// At auction creation
delayQueue.schedule(
    new CloseAuctionTask(auctionId),
    auction.getEndTime().toEpochMilli() - System.currentTimeMillis(),
    TimeUnit.MILLISECONDS
);

// Or use Redis Sorted Set
redis.zadd("closing-auctions", auction.getEndTime().toEpochMilli(), auctionId);

// Worker polls sorted set
while (true) {
    Set<String> auctions = redis.zrangeByScore(
        "closing-auctions", 0, System.currentTimeMillis(), 0, 100
    );
    for (String auctionId : auctions) {
        closeAuction(Long.parseLong(auctionId));
        redis.zrem("closing-auctions", auctionId);
    }
    Thread.sleep(1000);
}
```

---

### 5. Search Service

**Requirements**:
- Full-text search (title, description)
- Filter by category, price range, location, ending soon
- Sort by relevance, price, ending time, popularity
- Auto-complete suggestions
- Faceted search (category counts)

**Technology**: Elasticsearch

**Index Schema**:
```json
{
  "mappings": {
    "properties": {
      "auction_id": {"type": "long"},
      "title": {"type": "text", "analyzer": "standard"},
      "description": {"type": "text"},
      "category": {"type": "keyword"},
      "current_price": {"type": "double"},
      "end_time": {"type": "date"},
      "status": {"type": "keyword"},
      "location": {"type": "geo_point"},
      "seller_rating": {"type": "float"},
      "image_url": {"type": "keyword"},
      "total_bids": {"type": "integer"}
    }
  }
}
```

**Search Query Example**:
```json
POST /auctions/_search
{
  "query": {
    "bool": {
      "must": [
        {"match": {"title": "vintage camera"}},
        {"term": {"status": "ACTIVE"}}
      ],
      "filter": [
        {"range": {"current_price": {"gte": 100, "lte": 500}}},
        {"range": {"end_time": {"gte": "now"}}}
      ]
    }
  },
  "sort": [
    {"end_time": {"order": "asc"}}
  ],
  "aggs": {
    "categories": {
      "terms": {"field": "category"}
    }
  }
}
```

**Sync Strategy** (CDC - Change Data Capture):
```
PostgreSQL → Debezium → Kafka → Elasticsearch Connector
```

---

### 6. Fraud Detection Service

**Fraud Patterns**:
1. **Shill Bidding**: Seller or accomplice bids to inflate price
2. **Bid Shielding**: Accomplice places high bid, then retracts
3. **Bid Sniping**: Automated last-second bidding (mitigated by auto-extend)
4. **Account Farming**: Creating multiple fake accounts

**Detection Algorithms**:

**Shill Bidding Detection**:
```java
public boolean detectShillBidding(Long auctionId) {
    Auction auction = auctionRepo.findById(auctionId);
    List<Bid> bids = bidRepo.findByAuctionId(auctionId);
    
    // Check for suspicious patterns
    for (Bid bid : bids) {
        // 1. Same IP as seller
        if (bid.getIpAddress().equals(auction.getSellerIpAddress())) {
            return true;
        }
        
        // 2. Bidder only bids on this seller's auctions
        long totalBids = bidRepo.countByBidderId(bid.getBidderId());
        long sellerBids = bidRepo.countByBidderIdAndSellerId(
            bid.getBidderId(), auction.getSellerId()
        );
        if (totalBids == sellerBids && totalBids > 5) {
            return true;
        }
        
        // 3. New account with high-value bids
        User bidder = userRepo.findById(bid.getBidderId());
        if (ChronoUnit.DAYS.between(bidder.getCreatedAt(), Instant.now()) < 7 
            && bid.getBidAmount().compareTo(new BigDecimal(1000)) > 0) {
            flagForReview(bid);
        }
    }
    return false;
}
```

**Machine Learning Model**:
```python
# Features for fraud detection
features = [
    'bid_frequency',           # Bids per hour
    'account_age_days',        # Days since registration
    'seller_bidder_affinity',  # % of bids on same seller
    'ip_match_seller',         # Binary flag
    'bid_time_pattern',        # Last-minute vs spread out
    'average_bid_amount',
    'retraction_rate'          # % of bids retracted
]

# Train RandomForest or XGBoost
model = XGBClassifier()
model.fit(X_train, y_train)

# Real-time scoring
fraud_score = model.predict_proba(bid_features)[0][1]
if fraud_score > 0.8:
    block_bid()
elif fraud_score > 0.5:
    flag_for_manual_review()
```

---

### 7. Payment Service

**Flow**:
```
1. Auction closes with winner
2. Create payment intent (Stripe/PayPal)
3. Notify winner to pay within 48 hours
4. On payment success:
   - Hold funds in escrow
   - Notify seller to ship item
5. On delivery confirmation:
   - Release funds to seller
   - Allow buyer to leave feedback
6. On timeout/failure:
   - Offer to second-highest bidder
   - Penalize non-paying winner
```

**Integration** (Stripe):
```java
public PaymentIntent createPayment(Auction auction, Bid winningBid) {
    PaymentIntentCreateParams params = PaymentIntentCreateParams.builder()
        .setAmount((long) (winningBid.getBidAmount().doubleValue() * 100)) // cents
        .setCurrency("usd")
        .setCustomer(getStripeCustomerId(winningBid.getBidderId()))
        .putMetadata("auction_id", auction.getAuctionId().toString())
        .setTransferData(
            PaymentIntentCreateParams.TransferData.builder()
                .setDestination(getSellerAccountId(auction.getSellerId()))
                .build()
        )
        .setOnBehalfOf(getSellerAccountId(auction.getSellerId()))
        .setApplicationFeeAmount(calculateFee(winningBid.getBidAmount())) // Platform fee
        .build();
    
    return PaymentIntent.create(params);
}
```

---

### 8. Notification Service

**Notification Types**:
- Outbid alert (push/email/SMS)
- Auction ending soon (5 mins, 1 hour, 24 hours)
- Auction won/lost
- Payment reminder
- Shipping updates

**Implementation**:
```java
@KafkaListener(topics = "bid-events")
public void handleBidEvent(BidEvent event) {
    // Notify outbid users
    List<Bid> previousBids = bidRepo.findByAuctionIdAndStatus(
        event.getAuctionId(), "WINNING"
    );
    
    for (Bid outbidBid : previousBids) {
        // Update status
        outbidBid.setStatus("OUTBID");
        bidRepo.save(outbidBid);
        
        // Send notification
        User user = userRepo.findById(outbidBid.getBidderId());
        if (user.isNotificationsEnabled()) {
            // Push notification (Firebase Cloud Messaging)
            fcmService.send(user.getFcmToken(), 
                "You've been outbid!", 
                "Current price: " + event.getAmount()
            );
            
            // Email (SendGrid)
            emailService.sendTemplate(user.getEmail(), 
                "outbid_notification",
                Map.of("auctionTitle", event.getAuctionTitle(), 
                       "currentPrice", event.getAmount())
            );
        }
    }
}
```

---

## Scalability & Optimization

### 1. Caching Strategy

**Redis Layers**:
```
Layer 1: Hot auctions (ending in < 1 hour)
  - Full auction data
  - Current bid info
  - TTL: 1 hour

Layer 2: Active auctions (ending in < 24 hours)
  - Basic auction info
  - TTL: 6 hours

Layer 3: User watchlists
  - List of watched auction IDs
  - TTL: 1 hour
```

**Cache Aside Pattern**:
```java
public Auction getAuction(Long auctionId) {
    // Try cache first
    Auction cached = redis.get("auction:" + auctionId, Auction.class);
    if (cached != null) {
        return cached;
    }
    
    // Cache miss - fetch from DB
    Auction auction = auctionRepo.findById(auctionId);
    
    // Warm cache with TTL based on end time
    long ttl = calculateTTL(auction.getEndTime());
    redis.setex("auction:" + auctionId, ttl, auction);
    
    return auction;
}
```

### 2. Database Optimization

**Partitioning**:
```sql
-- Partition auctions by status and time
CREATE TABLE auctions_active PARTITION OF auctions
    FOR VALUES IN ('ACTIVE')
    PARTITION BY RANGE (end_time);

CREATE TABLE auctions_closed PARTITION OF auctions
    FOR VALUES IN ('SOLD', 'UNSOLD');

-- Partition bids by auction_id (hash partitioning)
CREATE TABLE bids PARTITION BY HASH (auction_id);
CREATE TABLE bids_0 PARTITION OF bids FOR VALUES WITH (MODULUS 10, REMAINDER 0);
CREATE TABLE bids_1 PARTITION OF bids FOR VALUES WITH (MODULUS 10, REMAINDER 1);
-- ... up to bids_9
```

**Indexing**:
```sql
-- Compound indexes for common queries
CREATE INDEX idx_auction_status_end ON auctions(status, end_time);
CREATE INDEX idx_bid_auction_time ON bids(auction_id, bid_time DESC);
CREATE INDEX idx_bid_user_time ON bids(bidder_id, bid_time DESC);
CREATE INDEX idx_auction_category_status ON auctions(category_id, status, end_time);
```

**Read Replicas**:
```
Master (Write): Bid placement, auction creation
Replica 1 (Read): Search queries, auction details
Replica 2 (Read): User dashboard, watchlists
Replica 3 (Read): Analytics, reporting
```

### 3. WebSocket Scaling

**Challenge**: 1M concurrent WebSocket connections

**Solution**: Horizontal scaling with Redis Pub/Sub
```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  WS      │     │  WS      │     │  WS      │
│ Server 1 │     │ Server 2 │     │ Server 3 │
│ (300K)   │     │ (300K)   │     │ (400K)   │
└────┬─────┘     └────┬─────┘     └────┬─────┘
     │                │                │
     └────────────────┼────────────────┘
                      ▼
              ┌──────────────┐
              │ Redis PubSub │
              │ (Broadcast)  │
              └──────────────┘
```

**Load Balancing**: Sticky sessions based on auction_id
```nginx
upstream websocket_backend {
    ip_hash; # Sticky sessions
    server ws1.example.com:8080;
    server ws2.example.com:8080;
    server ws3.example.com:8080;
}
```

### 4. Image Storage & CDN

**Storage**:
- Original images: AWS S3
- Optimized thumbnails: CloudFront CDN
- On-demand resizing: Lambda@Edge

**Upload Flow**:
```
1. User uploads image
2. API generates pre-signed S3 URL
3. Client uploads directly to S3
4. S3 trigger → Lambda → Image processing
   - Generate thumbnails (100x100, 300x300, 800x800)
   - Compress (WebP format)
   - Store in S3
5. Invalidate CDN cache
```

---

## API Design

### REST APIs

```
# Authentication
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout

# Auctions
POST   /api/v1/auctions                    # Create auction
GET    /api/v1/auctions/{id}               # Get auction details
PUT    /api/v1/auctions/{id}               # Update auction
DELETE /api/v1/auctions/{id}               # Cancel auction
GET    /api/v1/auctions/search             # Search auctions
  ?q=vintage camera
  &category=electronics
  &minPrice=100
  &maxPrice=500
  &sortBy=ending_soon
  &page=1
  &limit=20

# Bidding
POST   /api/v1/auctions/{id}/bids          # Place bid
GET    /api/v1/auctions/{id}/bids          # Get bid history
POST   /api/v1/auctions/{id}/auto-bid      # Enable proxy bidding
GET    /api/v1/users/me/bids               # My bids

# Watchlist
POST   /api/v1/users/me/watchlist          # Add to watchlist
DELETE /api/v1/users/me/watchlist/{id}     # Remove from watchlist
GET    /api/v1/users/me/watchlist          # Get watchlist

# Payment
POST   /api/v1/payments/intent             # Create payment
POST   /api/v1/payments/{id}/confirm       # Confirm payment
GET    /api/v1/payments/{id}               # Payment status
```

### WebSocket API

```javascript
// Client connection
const socket = io('wss://api.auction.com', {
    auth: { token: userToken }
});

// Watch auction (subscribe to updates)
socket.emit('watch-auction', { auctionId: 12345 });

// Receive real-time bid updates
socket.on('bid-update', (data) => {
    console.log('New bid:', data);
    // { auctionId, currentPrice, bidderName, timestamp, totalBids }
});

// Auction ending soon alert
socket.on('auction-ending', (data) => {
    // { auctionId, timeRemaining: "5 minutes" }
});

// Outbid notification
socket.on('outbid', (data) => {
    // { auctionId, yourBid, currentBid }
});

// Unwatch auction
socket.emit('unwatch-auction', { auctionId: 12345 });
```

---

## Database Schema (Complete)

```sql
-- Users
CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    profile_image_url VARCHAR(500),
    stripe_customer_id VARCHAR(100),
    stripe_account_id VARCHAR(100), -- For sellers
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    seller_rating DECIMAL(3,2) DEFAULT 5.0,
    buyer_rating DECIMAL(3,2) DEFAULT 5.0,
    total_auctions_sold INT DEFAULT 0,
    total_auctions_won INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

-- Categories
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_category_id INT REFERENCES categories(category_id),
    slug VARCHAR(100) UNIQUE,
    icon_url VARCHAR(500)
);

-- Auctions (already defined above, repeated for completeness)
CREATE TABLE auctions (
    auction_id BIGSERIAL PRIMARY KEY,
    seller_id BIGINT REFERENCES users(user_id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    category_id INT REFERENCES categories(category_id),
    condition VARCHAR(20), -- NEW, LIKE_NEW, GOOD, FAIR, POOR
    starting_price DECIMAL(10,2) NOT NULL,
    reserve_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    buy_now_price DECIMAL(10,2),
    bid_increment DECIMAL(10,2) DEFAULT 1.00,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'SCHEDULED',
    winner_id BIGINT REFERENCES users(user_id),
    total_bids INT DEFAULT 0,
    view_count INT DEFAULT 0,
    watch_count INT DEFAULT 0,
    shipping_cost DECIMAL(10,2),
    location VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- Bids (already defined above)
CREATE TABLE bids (
    bid_id BIGSERIAL PRIMARY KEY,
    auction_id BIGINT REFERENCES auctions(auction_id),
    bidder_id BIGINT REFERENCES users(user_id),
    bid_amount DECIMAL(10,2) NOT NULL,
    bid_time TIMESTAMP DEFAULT NOW(),
    is_auto_bid BOOLEAN DEFAULT FALSE,
    max_auto_bid DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'ACTIVE',
    ip_address INET,
    user_agent TEXT
);

-- Watchlist
CREATE TABLE watchlist (
    watch_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    auction_id BIGINT REFERENCES auctions(auction_id),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, auction_id)
);

-- Payments
CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    auction_id BIGINT REFERENCES auctions(auction_id),
    buyer_id BIGINT REFERENCES users(user_id),
    seller_id BIGINT REFERENCES users(user_id),
    amount DECIMAL(10,2) NOT NULL,
    platform_fee DECIMAL(10,2),
    stripe_payment_intent_id VARCHAR(100),
    status VARCHAR(20), -- PENDING, COMPLETED, FAILED, REFUNDED
    paid_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Feedback/Ratings
CREATE TABLE feedback (
    feedback_id BIGSERIAL PRIMARY KEY,
    auction_id BIGINT REFERENCES auctions(auction_id),
    from_user_id BIGINT REFERENCES users(user_id),
    to_user_id BIGINT REFERENCES users(user_id),
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    feedback_type VARCHAR(10), -- BUYER, SELLER
    created_at TIMESTAMP DEFAULT NOW()
);

-- Notifications
CREATE TABLE notifications (
    notification_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    type VARCHAR(50), -- OUTBID, AUCTION_WON, AUCTION_LOST, PAYMENT_REMINDER
    title VARCHAR(200),
    message TEXT,
    auction_id BIGINT REFERENCES auctions(auction_id),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Backend** | Java/Spring Boot | Enterprise-grade, strong transactional support |
| **API Gateway** | Kong / AWS API Gateway | Rate limiting, auth, routing |
| **WebSocket** | Node.js + Socket.io | Excellent for real-time connections |
| **Database** | PostgreSQL | ACID compliance, robust for financial data |
| **Cache** | Redis | In-memory speed, pub/sub for real-time |
| **Message Queue** | Apache Kafka | Event streaming, scalable, durable |
| **Search** | Elasticsearch | Full-text search, faceted search |
| **Object Storage** | AWS S3 | Scalable image storage |
| **CDN** | CloudFront | Low-latency image delivery |
| **Payments** | Stripe / PayPal | Industry standard, PCI compliant |
| **Auth** | JWT + OAuth 2.0 | Stateless, scalable authentication |
| **Monitoring** | Prometheus + Grafana | Metrics and visualization |
| **Logging** | ELK Stack | Centralized logging |
| **Container** | Docker + Kubernetes | Orchestration, auto-scaling |

---

## Security

### 1. Authentication & Authorization
- JWT tokens with 15-min expiry + refresh tokens
- OAuth 2.0 for social login
- MFA for high-value transactions
- Role-based access control (RBAC)

### 2. Payment Security
- PCI DSS compliance (use Stripe - they handle card data)
- Two-factor authentication for payments > $1000
- Fraud detection before payment processing
- Escrow service (hold funds until delivery)

### 3. Data Protection
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Personal data hashing (PII)
- GDPR compliance (data deletion, export)

### 4. Rate Limiting
```java
@RateLimit(requests = 10, per = "1m") // 10 bids per minute per user
public BidResponse placeBid(BidRequest request) {
    // ...
}
```

### 5. Input Validation
- Sanitize all user inputs (prevent SQL injection, XSS)
- Image upload validation (file type, size, content)
- Bid amount validation (prevent negative bids)

---

## Monitoring & Observability

### Key Metrics

**Business Metrics**:
- Active auctions count
- Bids per second
- Conversion rate (auctions with bids / total auctions)
- Average selling price
- Payment success rate

**Technical Metrics**:
- API latency (p50, p95, p99)
- Database query time
- Cache hit ratio
- WebSocket connection count
- Error rate

**Alerts**:
```yaml
alerts:
  - name: HighBidLatency
    condition: p99_bid_latency > 200ms
    action: page_oncall
  
  - name: LowCacheHitRatio
    condition: cache_hit_ratio < 70%
    action: slack_alert
  
  - name: DatabaseReplicationLag
    condition: replication_lag > 5s
    action: page_oncall
  
  - name: HighErrorRate
    condition: error_rate > 1%
    action: page_oncall
```

---

## Interview Q&A

### Q1: How do you prevent duplicate bids in a distributed system?
**Answer**:
1. **Distributed Lock** (Redis): Acquire lock on `auction:{id}` before bid placement
2. **Database Constraints**: UNIQUE constraint on `(auction_id, bid_time, bidder_id)`
3. **Optimistic Locking**: Use version field in auction table
4. **Idempotency Key**: Client sends unique key, server deduplicates

### Q2: How do you handle auction closing at exact time with millions of auctions?
**Answer**:
**Option 1**: Scheduled polling (simple but inefficient)
**Option 2**: Delay queue (Redis sorted set by end_time)
```java
// Add auction to sorted set
redis.zadd("closing-auctions", auction.getEndTime().toEpochMilli(), auctionId);

// Worker polls for auctions ready to close
Set<String> ready = redis.zrangeByScore("closing-auctions", 0, now());
```
**Option 3**: Distributed scheduler (Quartz Scheduler cluster)

### Q3: How do you handle WebSocket scalability (1M+ concurrent connections)?
**Answer**:
1. **Horizontal Scaling**: Multiple WebSocket servers
2. **Redis Pub/Sub**: Broadcast messages across servers
3. **Sticky Sessions**: Route same user to same server (IP hash)
4. **Message Batching**: Batch updates every 500ms instead of instant
5. **Selective Updates**: Only send to users watching specific auction

### Q4: How do you detect and prevent shill bidding?
**Answer**:
1. **IP Matching**: Check if bidder IP == seller IP
2. **Account Analysis**: Flag if bidder only bids on one seller's items
3. **Behavioral Patterns**: New accounts with high bids
4. **Machine Learning**: Train model on historical fraud data
5. **Manual Review**: Flag suspicious auctions for review

### Q5: CAP Theorem - Which do you choose?
**Answer**:
- **Bid Placement**: CP (Consistency + Partition Tolerance)
  - Use strong consistency (ACID) to prevent duplicate winners
  - Brief unavailability acceptable during partition
- **Auction Search**: AP (Availability + Partition Tolerance)
  - Slightly stale search results acceptable
  - Always available for browsing

### Q6: How do you handle time synchronization across distributed servers?
**Answer**:
1. **NTP** (Network Time Protocol): Sync all servers
2. **Database Timestamp**: Use DB server time as source of truth
   ```sql
   INSERT INTO bids (bid_time) VALUES (NOW());
   ```
3. **Logical Clocks**: Use Lamport timestamps for ordering
4. **Lease-based Locking**: Lock expires after fixed duration

### Q7: How would you implement "Buy Now" feature?
**Answer**:
```java
@Transactional
public PurchaseResponse buyNow(Long auctionId, Long buyerId) {
    Lock lock = redisLock.acquire("auction:" + auctionId);
    try {
        Auction auction = auctionRepo.findById(auctionId);
        
        if (auction.getBuyNowPrice() == null) {
            throw new BuyNowNotAvailableException();
        }
        if (!auction.getStatus().equals("ACTIVE")) {
            throw new AuctionNotActiveException();
        }
        
        // Immediately close auction
        auction.setStatus("SOLD");
        auction.setWinnerId(buyerId);
        auction.setEndTime(Instant.now());
        auctionRepo.save(auction);
        
        // Cancel all existing bids
        bidRepo.updateStatusByAuctionId(auctionId, "CANCELLED");
        
        // Create payment
        Payment payment = paymentService.createPayment(auction, buyerId);
        
        return new PurchaseResponse("SUCCESS", payment.getPaymentId());
    } finally {
        lock.release();
    }
}
```

### Q8: How do you handle cross-border auctions (multi-currency)?
**Answer**:
1. **Currency Conversion**: Use real-time exchange rates API (e.g., Fixer.io)
2. **Display**: Show prices in user's preferred currency
3. **Storage**: Store all prices in base currency (USD)
4. **Bidding**: Convert bid amount to base currency before comparison
```java
BigDecimal bidInUSD = currencyConverter.convert(
    bidAmount, userCurrency, "USD"
);
```

### Q9: How would you implement auction recommendations?
**Answer**:
1. **Collaborative Filtering**: Users who bid on X also bid on Y
2. **Content-Based**: Recommend similar categories/price ranges
3. **Personalization**: Based on watch history, past bids
4. **Real-time**: Use Kafka Streams for online learning
```python
# Feature engineering
user_features = [
    'avg_bid_amount',
    'favorite_categories',
    'bid_frequency',
    'won_auctions_ratio'
]

# Train model
from sklearn.neighbors import NearestNeighbors
model = NearestNeighbors(n_neighbors=10)
model.fit(user_item_matrix)

# Recommend
recommendations = model.kneighbors(user_vector)
```

### Q10: How do you ensure high availability during peak times (e.g., Black Friday)?
**Answer**:
1. **Auto-scaling**: Kubernetes HPA (Horizontal Pod Autoscaler)
   ```yaml
   autoscaling:
     minReplicas: 10
     maxReplicas: 100
     targetCPUUtilization: 70%
   ```
2. **Pre-warming**: Scale up before expected traffic
3. **Load Testing**: Simulate peak load (Gatling, JMeter)
4. **Circuit Breakers**: Fail fast on downstream service failures
5. **Graceful Degradation**: Disable non-critical features (recommendations, analytics)
6. **CDN**: Offload static content
7. **Database**: Read replicas, connection pooling

---

## Cost Estimation (AWS)

### Infrastructure (Monthly)

| Service | Specification | Cost |
|---------|--------------|------|
| **EC2** (App Servers) | 50 × m5.2xlarge (8 vCPU, 32GB) | $12,000 |
| **RDS PostgreSQL** | db.r5.4xlarge (16 vCPU, 128GB) + 3 replicas | $15,000 |
| **ElastiCache Redis** | 10 × cache.r5.xlarge (26GB) | $3,000 |
| **Elasticsearch** | 5 × r5.xlarge.elasticsearch | $2,500 |
| **MSK (Kafka)** | 6 × kafka.m5.large | $1,500 |
| **S3** | 200TB storage + requests | $4,600 |
| **CloudFront** | 100TB transfer | $8,500 |
| **API Gateway** | 1B requests/month | $3,500 |
| **Lambda** | 10M invocations (image processing) | $200 |
| **EKS** | Kubernetes cluster | $150 |
| **Data Transfer** | Inter-AZ & outbound | $2,000 |
| **Monitoring** | CloudWatch, X-Ray | $500 |
| **Total** | | **~$53,000/month** |

**Revenue Model**:
- Seller fee: 10% of final price
- Listing fee: $0.35 per auction
- Featured listing: $5-20 per auction
- If 5M auctions/month at avg $50, revenue = $25M/month
- Infrastructure = 0.2% of revenue

---

## Deployment Architecture

```yaml
# Kubernetes deployment example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bidding-service
spec:
  replicas: 10
  selector:
    matchLabels:
      app: bidding-service
  template:
    metadata:
      labels:
        app: bidding-service
    spec:
      containers:
      - name: bidding-service
        image: auction-platform/bidding-service:v1.0
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: REDIS_URL
          value: "redis://redis-cluster:6379"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 5
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - bidding-service
            topologyKey: "kubernetes.io/hostname"
```

---

**This comprehensive HLD covers a production-ready online auction system at eBay scale!**
