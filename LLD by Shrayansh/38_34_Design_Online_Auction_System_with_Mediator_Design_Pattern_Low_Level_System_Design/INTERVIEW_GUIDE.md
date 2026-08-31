# 🔨 Online Auction System - Low Level Design Interview Guide
## _15 YOE Architect-Level Conversational Script_

---

## 📋 **Table of Contents**
1. [Architecture Diagram](#1-architecture-diagram)
2. [API Design](#2-api-design)
3. [ER Diagram & Database Design](#3-er-diagram--database-design)
4. [Sequence Diagrams](#4-sequence-diagrams)
5. [Scenario-First Explanations](#5-scenario-first-explanations)
6. [Cross Questions](#6-cross-questions)
7. [Trade-offs](#7-trade-offs)
8. [Senior Trap Questions](#8-senior-trap-questions)
9. [Technology Choices](#9-technology-choices)

---

## **Design Pattern Used**: Mediator Pattern

**Interviewer**: "Design an Online Auction System like eBay."

**You**: "The core challenge: **Bidders shouldn't directly communicate with each other, but all need to be notified when a new highest bid is placed, and the auction itself needs to coordinate bid validation, timing, and notifications.** This is a perfect **Mediator Pattern** use case - the Auction acts as mediator between Bidders."

---

## 1. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                ONLINE AUCTION ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────┐
                    │   AUCTION (Mediator)  │
                    │                      │
                    │  currentHighestBid    │
                    │  bidders: List<Bidder>│
                    │  endTime              │
                    │                      │
                    │  placeBid(bidder,amt) │◄─── Central coordination point
                    │  notifyAllBidders()   │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌────────────┐   ┌────────────┐   ┌────────────┐
       │  Bidder A   │   │  Bidder B   │   │  Bidder C   │
       │            │   │            │   │            │
       │ placeBid() │   │ placeBid() │   │ placeBid() │
       │ onOutbid() │   │ onOutbid() │   │ onOutbid() │
       └────────────┘   └────────────┘   └────────────┘
       
       Bidders NEVER talk to each other directly!
       All communication flows through Auction (Mediator)

    WHY MEDIATOR (Not Direct Bidder-to-Bidder Observer)?
    ┌────────────────────────────────────────────┐
    │  Auction ALSO enforces business rules:       │
    │  - Bid must exceed current + minIncrement    │
    │  - Auction must not have ended                │
    │  - Seller cannot bid on own auction           │
    │                                              │
    │  Centralizing these rules in Mediator avoids  │
    │  duplicating validation logic in every Bidder │
    └────────────────────────────────────────────┘
```

---

## 2. API Design

```http
POST /api/v1/auctions
Request:
{
  "itemId": "item-1234",
  "startingPrice": 1000,
  "minIncrement": 50,
  "endTime": "2026-09-05T18:00:00Z",
  "sellerId": "seller-5678"
}
Response: 201 CREATED
{"auctionId": "auction-9999", "status": "ACTIVE"}

---

POST /api/v1/auctions/{auctionId}/bids
Request: {"bidderId": "bidder-1111", "amount": 1100}
Response: 200 OK
{
  "bidId": "bid-2222",
  "status": "ACCEPTED",
  "currentHighestBid": 1100,
  "outbidNotificationsSent": 3
}

// Bid too low:
Response: 400 BAD_REQUEST
{"error": "BID_TOO_LOW", "currentHighest": 1100, "minimumNextBid": 1150}

// Auction ended:
Response: 410 GONE
{"error": "AUCTION_ENDED", "winningBid": 1500, "winner": "bidder-3333"}

---

GET /ws/auctions/{auctionId}  (WebSocket)
Server pushes:
{"type": "NEW_HIGHEST_BID", "amount": 1150, "bidderId": "bidder-1111"}
{"type": "AUCTION_ENDING_SOON", "secondsRemaining": 30}
{"type": "AUCTION_ENDED", "winner": "bidder-1111", "finalPrice": 1150}
```

---

## 3. ER Diagram & Database Design

```sql
CREATE TABLE auctions (
    auction_id VARCHAR(50) PRIMARY KEY,
    item_id VARCHAR(50) NOT NULL,
    seller_id VARCHAR(50) NOT NULL,
    starting_price DECIMAL(10,2) NOT NULL,
    current_highest_bid DECIMAL(10,2),
    min_increment DECIMAL(10,2) DEFAULT 10,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    end_time TIMESTAMP NOT NULL,
    
    CHECK (status IN ('ACTIVE', 'ENDED', 'CANCELLED'))
);

CREATE TABLE bids (
    bid_id VARCHAR(50) PRIMARY KEY,
    auction_id VARCHAR(50) NOT NULL,
    bidder_id VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (auction_id) REFERENCES auctions(auction_id),
    INDEX idx_auction_amount (auction_id, amount DESC)  -- Fast "get highest bid" query
);
```

---

## 4. Sequence Diagrams

```
BidderA   Auction(Mediator)   BidderB   BidderC   DB
   │             │                │         │       │
   │─bid(1100)──▶│                │         │       │
   │             ├─validate(1100 > current+increment)│
   │             ├─INSERT bid─────────────────────────▶│
   │             ├─updateHighest(1100)                 │
   │             ├─notify(BidderB)─────────▶│         │
   │             ├─notify(BidderC)────────────────────▶│
   │◀ACCEPTED────│                │         │       │
   │             │                │  "Outbid! New highest: 1100"
   │             │                │◀────────│         │
```

**You**: "BidderA never directly tells BidderB 'I outbid you' - the Auction (Mediator) handles ALL cross-bidder notification. This decoupling is the essence of Mediator Pattern - N bidders would need N² communication paths without a mediator, but only N paths (bidder↔mediator) with one."

---

## 5. Scenario-First Explanations

### **5.1 Why Mediator Pattern (Not Direct Observer Between Bidders)?**

**You**: "Without Mediator (chaos!):
```java
// ❌ Every bidder must know about every other bidder
class Bidder {
    List<Bidder> otherBidders;  // Tight coupling!
    
    void placeBid(double amount) {
        // Validate against ALL other bidders' bids? Where's the source of truth?
        for (Bidder other : otherBidders) {
            other.notifyOutbid(amount);  // N² communication complexity!
        }
    }
}
```

With Mediator:
```java
interface AuctionMediator {
    void placeBid(Bidder bidder, double amount);
    void registerBidder(Bidder bidder);
}

class Auction implements AuctionMediator {
    private double currentHighestBid;
    private Bidder currentHighestBidder;
    private List<Bidder> registeredBidders = new ArrayList<>();
    private double minIncrement;
    private LocalDateTime endTime;
    
    public void placeBid(Bidder bidder, double amount) {
        // Centralized validation
        if (LocalDateTime.now().isAfter(endTime)) {
            throw new AuctionEndedException();
        }
        if (amount < currentHighestBid + minIncrement) {
            throw new BidTooLowException(currentHighestBid + minIncrement);
        }
        if (bidder.equals(seller)) {
            throw new IllegalArgumentException("Seller cannot bid on own auction");
        }
        
        Bidder previousHighestBidder = currentHighestBidder;
        currentHighestBid = amount;
        currentHighestBidder = bidder;
        
        bidRepo.save(new Bid(this, bidder, amount));
        
        // Mediator handles ALL notification - bidders don't know about each other!
        if (previousHighestBidder != null) {
            previousHighestBidder.onOutbid(amount);
        }
        notifyAllExcept(bidder, new BidUpdateEvent(amount));
    }
    
    private void notifyAllExcept(Bidder excluded, BidUpdateEvent event) {
        registeredBidders.stream()
            .filter(b -> !b.equals(excluded))
            .forEach(b -> b.onBidUpdate(event));
    }
    
    public void registerBidder(Bidder bidder) {
        registeredBidders.add(bidder);
    }
}

class Bidder {
    private AuctionMediator auction;  // Only knows about the MEDIATOR
    
    void placeBid(double amount) {
        auction.placeBid(this, amount);  // Delegate ALL logic to mediator
    }
    
    void onOutbid(double newAmount) {
        notificationService.send(this, "You've been outbid! New highest: " + newAmount);
    }
}
```

**Key benefit**: Adding new business rules (e.g., 'auto-extend auction if bid placed in last 30 seconds' - anti-sniping) requires changing ONLY the Auction (Mediator) class, not every Bidder."

### **5.2 Why Anti-Sniping Auto-Extension is a Common Follow-up**

**You**: "Real auction platforms (eBay) extend the auction if a bid comes in the final moments, preventing 'sniping':

```java
class Auction implements AuctionMediator {
    private static final Duration EXTENSION_WINDOW = Duration.ofSeconds(30);
    private static final Duration EXTENSION_AMOUNT = Duration.ofMinutes(2);
    
    public void placeBid(Bidder bidder, double amount) {
        // ... validation and bid processing ...
        
        Duration timeRemaining = Duration.between(LocalDateTime.now(), endTime);
        if (timeRemaining.compareTo(EXTENSION_WINDOW) < 0) {
            endTime = endTime.plus(EXTENSION_AMOUNT);  // Extend!
            notifyAllExcept(null, new AuctionExtendedEvent(endTime));
        }
    }
}
```

This prevents bidders from waiting until the last second to snipe a bid with no time for others to respond - a real-world business rule that's a natural extension of the Mediator's centralized control."

---

## 6. Cross Questions

**Interviewer**: "How do you handle two bids arriving at the EXACT same millisecond?"

**You**: "Database-level atomicity via optimistic locking or SERIALIZABLE isolation:

```java
@Transactional(isolation = Isolation.SERIALIZABLE)
public void placeBid(Bidder bidder, double amount) {
    Auction auction = auctionRepo.findByIdWithLock(auctionId);  // Row lock
    
    if (amount <= auction.getCurrentHighestBid()) {
        throw new BidTooLowException();
    }
    
    auction.setCurrentHighestBid(amount);
    auctionRepo.save(auction);  // Whichever transaction commits FIRST wins
}
```

With `SERIALIZABLE` isolation or `SELECT FOR UPDATE`, concurrent bid attempts are naturally serialized by the database - the second transaction sees the updated highest bid and correctly rejects if it's now too low."

---

## 7. Trade-offs

### **Mediator Pattern vs Observer Pattern for This Use Case**

| Aspect | Mediator | Pure Observer |
|--------|----------|-----------------|
| **Business Logic Location** | Centralized in Mediator | Spread across Subject + Observers |
| **Coupling** | Bidders only know Mediator | Bidders might need to know Subject's rules |
| **Best for** | Complex coordination rules (bid validation, anti-sniping) | Simple notify-only scenarios |

**You**: "Observer Pattern would work for the NOTIFICATION aspect (Auction as Subject, Bidders as Observers), but Mediator is more appropriate here because there's substantial CENTRALIZED BUSINESS LOGIC (bid validation, minimum increment, anti-sniping) that doesn't fit cleanly into pure Observer's 'just notify' model."

---

## 8. Senior Trap Questions

### **Trap: "Just use a simple database UPDATE, race conditions aren't a big deal for auctions!"**

**✅ Senior**: "Actually, auctions are a CLASSIC place where race conditions cause real financial disputes. Two bidders submitting simultaneously with client-side 'I saw current bid was $1000, so I bid $1050' can both pass client validation but only ONE should win at the database level. Must use pessimistic locking (`SELECT FOR UPDATE`) or `SERIALIZABLE` transaction isolation to guarantee only one bid succeeds atomically - and the LOSING bidder must get clear feedback ('someone else just bid higher, please bid again') rather than silent failure."

---

## 9. Technology Choices

**You**: "**WebSocket** for real-time bid updates to all watching bidders (crucial for the 'exciting last-minute bidding war' UX). **PostgreSQL** with `SERIALIZABLE` isolation for bid consistency - correctness over raw throughput since financial disputes are costly. **Redis** for caching current highest bid for fast read-only display (non-authoritative, just for UI performance)."

---

## 🎓 **Final Tips**

1. **Mediator Pattern**: Auction centralizes ALL bidder coordination + business rules
2. **Anti-sniping extension**: Common real-world follow-up question
3. **Concurrent bid handling**: SERIALIZABLE isolation or SELECT FOR UPDATE
4. **N² → N communication**: Key benefit of Mediator over direct peer communication

Good luck! Online Auction tests **Mediator Pattern** and concurrent bid consistency. 🚀
