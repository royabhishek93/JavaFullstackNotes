# Interview Guide: Mediator Design Pattern — Online Auction System LLD

## 🗣️ The Interview Scenario

> "Design an online auction system. Multiple bidders can place bids on an item. When a bidder places a bid, every other bidder must be notified of the new bid amount so they can decide whether to raise it. Design the classes involved, keeping in mind that bidders should not need to know about each other directly. How would you extend this design to also model an airline system where multiple flights request permission to land from a control tower?"

This is a classic "loose coupling between many peer objects" question. The interviewer is really testing whether you reach for **Mediator** instead of wiring every bidder to every other bidder (an $O(n^2)$ mess).

## 🏗️ Architect's Explanation (For a New Developer)

Imagine an actual auction house. Bidders don't lean over and shout numbers directly into each other's ears — that would be chaotic, and every bidder would need to know the identity and location of every other bidder in the room. Instead, everyone raises a paddle and speaks *to the auctioneer*. The auctioneer (the **mediator**) announces the new bid to the room. Bidders never talk to each other directly — they only know the auctioneer.

That's the entire idea behind the **Mediator pattern**: it's a *behavioral* design pattern that **encourages loose coupling by preventing objects from referring to each other explicitly**, and instead makes them **communicate through a mediator object**.

Two objects that would otherwise need direct references to each other (and to every other object in the group) instead only need a reference to *one* thing: the mediator. The mediator is the only object that knows about everybody.

Same idea applies to an **airline control tower**: planes don't negotiate landing slots with each other — each plane radios the tower, the tower checks against other traffic, and only the tower talks back to each plane.

## 📊 Visualize It

**Class structure (colleague ↔ mediator):**

```
        <<interface>>                      <<interface>>
          Colleague                        AuctionMediator
        --------------                    -------------------
        + placeBid()                      + addBidder(Colleague)
        + receiveBidNotification()        + placeBid(Colleague, amount)
        + getName()
              ▲                                    ▲
              | implements                         | implements
              |                                     |
         ---------                              ---------
         | Bidder |----- has-a ---------------->| Auction |
         ---------      (auctionMediator)        ---------
         - name                                  - List<Colleague> colleagues
         - auctionMediator
```

**Runtime interaction (nobody talks to a peer directly):**

```
BidderA.placeBid(1000)
        │
        ▼
Auction.placeBid(BidderA, 1000)     <-- mediator receives the request
        │
        ├──► loop over colleagues list
        │        │
        │        ├──► skip BidderA (the sender)
        │        ├──► BidderB.receiveBidNotification("A bid 1000")
        │        └──► BidderC.receiveBidNotification("A bid 1000")
        ▼
BidderA never called BidderB or BidderC directly.
```

## 🔧 Deep Dive: How It Actually Works

### 1. The `Colleague` interface
Represents any participant object — in this domain, a `Bidder`.
```java
interface Colleague {
    void placeBid(double amount);
    void receiveBidNotification(String bidderName, double amount);
    String getName();
}
```

### 2. The concrete `Bidder`
```java
class Bidder implements Colleague {
    private String name;
    private AuctionMediator auctionMediator;

    Bidder(String name, AuctionMediator auctionMediator) {
        this.name = name;
        this.auctionMediator = auctionMediator;
        auctionMediator.addBidder(this);   // self-register on construction
    }

    public void placeBid(double amount) {
        auctionMediator.placeBid(this, amount);   // never calls another Bidder directly
    }

    public void receiveBidNotification(String bidderName, double amount) {
        System.out.println(name + " notified: " + bidderName + " bid " + amount);
    }
}
```
Note the transcript's key design decision: **the `Bidder`'s constructor takes the `AuctionMediator` as a dependency**, because in a real system there could be many concurrent auctions running, and a bidder needs to know *which* auction it belongs to.

### 3. The `AuctionMediator` interface and `Auction` implementation
```java
interface AuctionMediator {
    void addBidder(Colleague bidder);
    void placeBid(Colleague bidder, double amount);
}

class Auction implements AuctionMediator {
    private List<Colleague> colleagues = new ArrayList<>();

    public void addBidder(Colleague bidder) {
        colleagues.add(bidder);
    }

    public void placeBid(Colleague bidder, double amount) {
        for (Colleague c : colleagues) {
            if (!c.getName().equals(bidder.getName())) {   // don't echo back to the sender
                c.receiveBidNotification(bidder.getName(), amount);
            }
        }
    }
}
```

### 4. Wiring it together
```java
Auction auction = new Auction();
Bidder bidderA = new Bidder("A", auction);   // registers itself with `auction`
Bidder bidderB = new Bidder("B", auction);

bidderA.placeBid(2000);   // auction notifies bidderB only
bidderB.placeBid(2500);   // auction notifies bidderA only
```

### Key design decisions worth saying out loud in the interview
- The mediator maintains the **list of colleagues** — colleagues never hold references to each other.
- `placeBid` **filters out the sender** so a bidder doesn't get notified about its own bid.
- This same structure models an **Airline Management System**: `Colleague` → `Flight`, `AuctionMediator` → `ControlTower`, and `placeBid` → `requestLanding`.
- The pattern is intentionally "base-level" — in a real interview you'd extend it: highest-bid tracking, bid validation (must exceed current highest), auction close time, concurrency control on simultaneous bids, etc.

### Mediator vs. Observer vs. Proxy (a common interview trap)
| Pattern | Intent |
|---|---|
| **Mediator** | Two objects should **not** talk to each other directly at all — route everything through a middleman. |
| **Observer** | One subject's **state change** should notify *all* interested parties — it's about propagating a state change, not about avoiding direct object coupling. |
| **Proxy** | Controls **access** to a single real object — used for lazy loading, authorization checks, logging before delegating to the real object. |

They can *look* structurally similar (something sits "in the middle"), but the **problem being solved** is different in each case — this is exactly the kind of distinction an interviewer probes for.

## 🔥 Real Production Incident & Fix

**What broke:** An early version of a live-bidding feature for a flash-sale platform had each `Bidder`-equivalent service instance hold direct WebSocket references to every other connected client in the same auction room, so it could push "someone outbid you" events directly. It worked fine in testing with 5 concurrent bidders.

**How the team noticed:** During a flash-sale event with ~4,000 concurrent bidders on a single hot item, the on-call engineer got paged for CPU saturation and a spike in p99 latency on bid submission. APM traces showed a single `placeBid` call fanning out into thousands of direct network calls, and worse, several bidder connections were **stale/closed but still referenced**, causing exceptions that silently swallowed notifications for a chunk of users — support tickets came in saying "I bid but never saw it register."

**Root cause:** Every bidder object held a **direct reference** to every other bidder's connection (no mediator). Adding/removing a bidder mid-auction required updating everyone's reference list, which was error-prone and never fully consistent — some bidders had stale connection handles. There was no single source of truth for "who is currently in this auction."

**The fix:** They introduced a central `AuctionMediator` (exactly this pattern) per auction room. Bidders registered/deregistered with the mediator only; the mediator held the single authoritative list of active connections and handled fan-out, retries, and pruning of dead connections in one place. Bid-submission latency dropped because the fan-out logic could be optimized/batched centrally instead of duplicated per-bidder.

```
BEFORE (each bidder → every other bidder,          AFTER (single mediator owns
stale references cause silent notification loss)   the authoritative list)

  B1 ⇄ B2 ⇄ B3 ⇄ B4                                   B1   B2   B3   B4
  ⇅  ⇅  ⇅  ⇅   (tangled, N² links)                     \    |    |   /
  B5 ⇄ ... ⇄ Bn                                          \   |   |  /
                                                            AuctionMediator
                                                       (owns list, prunes dead
                                                        connections, fans out)
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why not just use Observer here — isn't a bidder "observing" the auction state?**
A: Intent differs. Observer is about *one subject's state changing and notifying all interested parties* (e.g., stock price changes). Mediator is specifically about preventing **peer-to-peer coupling** between objects that need to interact bidirectionally (place bid *and* receive notifications). In this problem, every bidder is both a sender and a receiver, and none should know about the others — that bidirectional "nobody talks directly" constraint is the Mediator signature.

**Q2: How would you prevent the sender from getting its own bid notification echoed back?**
A: In `placeBid`, when iterating the colleague list, compare the sender's identity (e.g., by name/ID) and skip notifying itself — as done in the transcript's `Auction.placeBid` implementation. In production you'd compare object identity or a stable bidder ID rather than a mutable name field.

**Q3: How does this design scale to multiple simultaneous auctions?**
A: Each `Bidder` is constructed with a specific `AuctionMediator` (i.e., a specific `Auction` instance) it belongs to, rather than a single global mediator. Multiple `Auction` objects can exist concurrently, each maintaining its own independent colleague list — this is exactly why the mediator reference is passed through the `Bidder` constructor rather than hardcoded.

**Q4: What are the downsides of the Mediator pattern?**
A: The mediator itself can become a **god object** — as more interaction logic is added (validation, ordering, business rules), the mediator class can grow large and become a single point of complexity/failure, which somewhat reintroduces the "one big class does everything" problem the pattern was meant to avoid elsewhere. It also becomes a single bottleneck under high concurrency unless designed carefully.

**Q5: How would you extend this design to track the current highest bid and reject lower bids?**
A: Add state to `Auction` (e.g., `currentHighestBid`, `currentHighestBidder`). In `placeBid`, validate `amount > currentHighestBid` before accepting; if the bid is lower, notify only the bidder who attempted it (a rejection), rather than broadcasting to everyone. This shows the interviewer you can extend the base UML rather than just reciting it.

**Q6: Is Mediator the same as a message broker / pub-sub system architecturally?**
A: Conceptually related — both decouple senders from receivers — but Mediator is a synchronous, in-process OOP pattern where the mediator directly calls methods on colleagues. A message broker (Kafka, RabbitMQ) is a distributed, typically asynchronous infrastructure component. In an LLD interview, Mediator is the object-oriented micro-pattern; a message broker would come up in a broader system-design/HLD discussion.

## 🔑 Key Takeaway

Whenever two (or more) objects need to interact but **should not hold direct references to each other**, introduce a mediator that owns the list of participants and routes all communication — this turns an N² web of dependencies into a clean hub-and-spoke design, and it's the textbook fit for auction systems, air-traffic control, and chat rooms.
