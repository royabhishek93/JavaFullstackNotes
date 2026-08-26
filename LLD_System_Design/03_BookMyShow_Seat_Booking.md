# BookMyShow / Concurrent Seat Booking — Complete LLD Interview Guide

**Interview Duration: 50 min | Difficulty: Hard | Must-Know: ⭐⭐⭐⭐⭐ | 15-YOE Focus: Concurrent Booking + Distributed Lock + Payment Integration**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │               BOOKMYSHOW SEAT BOOKING SYSTEM                    │
 │                                                                  │
 │  BROWSING              BOOKING FLOW             PAYMENT          │
 │  ┌──────────┐         ┌───────────────┐        ┌─────────────┐ │
 │  │ Movie    │         │ 1. Browse     │        │ Razorpay    │ │
 │  │ Theatre  │         │ 2. SelectSeats│        │ PaymentGW   │ │
 │  │ Show     │◄───────►│ 3. HOLD(10min)│◄──────►│ Txn Status  │ │
 │  │ Seats    │         │ 4. Pay        │        └─────────────┘ │
 │  └──────────┘         │ 5. CONFIRM    │                         │
 │                       └───────────────┘        NOTIFICATIONS    │
 │                                                ┌─────────────┐  │
 │  SEAT STATUS MAP (per Show)                    │ Email/SMS   │  │
 │  ┌─────────────────────────────┐               │ Ticket PDF  │  │
 │  │ A1:AVAILABLE A2:HELD  A3:✓ │               └─────────────┘  │
 │  │ B1:AVAILABLE B2:AVAILABLE   │                                 │
 │  │ C1:HELD(exp) C2:AVAILABLE   │                                 │
 │  └─────────────────────────────┘                                 │
 └──────────────────────────────────────────────────────────────────┘

 SEAT STATE MACHINE:
 ┌──────────────────────────────────────────────────────────────────┐
 │  [AVAILABLE] ──holdSeats()──► [HELD] ── 10min TTL ──► [AVAILABLE]│
 │                                  │                               │
 │                             confirmPayment()                     │
 │                                  │                               │
 │                            [CONFIRMED/BOOKED]                   │
 │                             (permanent)                         │
 │                                                                  │
 │  [HELD] ──cancelHold()──► [AVAILABLE]                           │
 └──────────────────────────────────────────────────────────────────┘

 CONCURRENT BOOKING — THE CORE PROBLEM:
 ┌──────────────────────────────────────────────────────────────────┐
 │  User A selects seats A1, A2                                     │
 │  User B selects seats A2, A3   ← SAME SEAT A2!                  │
 │                                                                  │
 │  Without locking:                                                │
 │    Both read A2: AVAILABLE                                       │
 │    Both hold A2                                                  │
 │    Both pay successfully                                         │
 │    A2 is double-booked 💥                                        │
 │                                                                  │
 │  With atomic hold:                                               │
 │    User A: atomically mark A1,A2 HELD → success ✅               │
 │    User B: try to mark A2 HELD → conflict! → try next available  │
 └──────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Let me clarify requirements.

Functional:
- Browse movies → select city → select theatre → select show → see seat map
- Select seats, put on temporary HOLD (10 min) while user pays
- If payment succeeds: confirm seats (permanent booking)
- If payment fails or times out: release held seats back to available
- Booking confirmation: email + PDF ticket
- Cancellation: full refund if >48h before show, 50% otherwise

Non-functional — this is where it gets interesting:
- A new Shah Rukh Khan movie releases at 12:00am. 100,000 users try to book simultaneously. The seat map for each show has maybe 300 seats. Without distributed locking: double bookings. With locking: deadlocks if we lock multiple seats.
- The system must handle ~1000 concurrent seat operations per show per second.
- Hold TTL: 10 minutes. If user doesn't pay, seats must auto-release.

The hardest problem here is: how do you atomically hold multiple seats without double-booking or deadlock?"

---

### Phase 2 — Core Entities

```
Movie          → movieId, title, genre, duration, language
Theatre        → theatreId, name, city, List<Screen>
Screen         → screenId, List<SeatRow>
Show           → showId, movieId, screenId, startTime, Map<SeatId,SeatStatus>
Seat           → seatId, row, number, SeatType (PREMIUM/REGULAR/RECLINER), price
SeatStatus     → AVAILABLE / HELD / CONFIRMED
SeatHold       → holdId, showId, List<Seat>, userId, expiresAt
Booking        → bookingId, showId, userId, List<Seat>, totalAmount, status
Payment        → paymentId, bookingId, amount, gatewayRef, status
```

---

### Phase 3 — Implementation

```java
// ─── SeatStatus ─────────────────────────────────────────────────
public enum SeatStatus { AVAILABLE, HELD, CONFIRMED }
public enum SeatType   { REGULAR, PREMIUM, RECLINER }

// ─── Seat ────────────────────────────────────────────────────────
public class Seat {
    private final String seatId;   // "A1", "B12"
    private final String row;
    private final int    number;
    private final SeatType type;
    private final double   price;

    public Seat(String seatId, String row, int number, SeatType type, double price) {
        this.seatId = seatId; this.row = row; this.number = number;
        this.type = type; this.price = price;
    }

    public String getSeatId() { return seatId; }
    public double getPrice()  { return price; }
    public SeatType getType() { return type; }
}

// ─── Show (the core concurrency battleground) ────────────────────
public class Show {
    private final String showId;
    private final String movieId;
    private final String screenId;
    private final LocalDateTime startTime;

    // Seat status map — concurrent access
    private final ConcurrentHashMap<String, SeatStatus> seatStatusMap;
    // Hold → userId mapping (for timeout + conflict detection)
    private final ConcurrentHashMap<String, String>     seatHoldMap;
    // Per-show lock for atomic multi-seat operations
    private final ReentrantLock showLock = new ReentrantLock();

    public Show(String showId, String movieId, String screenId,
                LocalDateTime startTime, List<Seat> seats) {
        this.showId    = showId;
        this.movieId   = movieId;
        this.screenId  = screenId;
        this.startTime = startTime;
        this.seatStatusMap = new ConcurrentHashMap<>();
        this.seatHoldMap   = new ConcurrentHashMap<>();
        seats.forEach(s -> seatStatusMap.put(s.getSeatId(), SeatStatus.AVAILABLE));
    }

    // ─── Atomic multi-seat hold ──────────────────────────────────
    // ALL seats must be AVAILABLE, or we hold NONE (all-or-nothing)
    public SeatHold holdSeats(String userId, List<String> seatIds, int holdMinutes) {
        showLock.lock();
        try {
            // Validate all are available
            for (String seatId : seatIds) {
                SeatStatus status = seatStatusMap.get(seatId);
                if (status == null) throw new IllegalArgumentException("Seat not found: " + seatId);
                if (status != SeatStatus.AVAILABLE)
                    throw new SeatNotAvailableException("Seat " + seatId + " is " + status);
            }
            // All available — hold atomically
            String holdId = UUID.randomUUID().toString();
            seatIds.forEach(seatId -> {
                seatStatusMap.put(seatId, SeatStatus.HELD);
                seatHoldMap.put(seatId, holdId);
            });

            LocalDateTime expiresAt = LocalDateTime.now().plusMinutes(holdMinutes);
            SeatHold hold = new SeatHold(holdId, showId, seatIds, userId, expiresAt);
            scheduleHoldExpiry(hold);
            return hold;
        } finally {
            showLock.unlock();
        }
    }

    // ─── Confirm hold after payment ─────────────────────────────
    public boolean confirmSeats(String holdId, List<String> seatIds) {
        showLock.lock();
        try {
            for (String seatId : seatIds) {
                if (!holdId.equals(seatHoldMap.get(seatId)))
                    return false; // hold expired or mismatch
                if (seatStatusMap.get(seatId) != SeatStatus.HELD)
                    return false;
            }
            seatIds.forEach(seatId -> {
                seatStatusMap.put(seatId, SeatStatus.CONFIRMED);
                seatHoldMap.remove(seatId);
            });
            return true;
        } finally {
            showLock.unlock();
        }
    }

    // ─── Release hold (timeout or cancel) ───────────────────────
    public void releaseHold(String holdId, List<String> seatIds) {
        showLock.lock();
        try {
            seatIds.forEach(seatId -> {
                if (holdId.equals(seatHoldMap.get(seatId))) {
                    seatStatusMap.put(seatId, SeatStatus.AVAILABLE);
                    seatHoldMap.remove(seatId);
                }
            });
        } finally {
            showLock.unlock();
        }
    }

    private void scheduleHoldExpiry(SeatHold hold) {
        long delayMs = Duration.between(LocalDateTime.now(), hold.getExpiresAt()).toMillis();
        Executors.newSingleThreadScheduledExecutor().schedule(() ->
            releaseHold(hold.getHoldId(), hold.getSeatIds()),
            delayMs, TimeUnit.MILLISECONDS
        );
    }

    public Map<String, SeatStatus> getSeatStatusSnapshot() {
        return Collections.unmodifiableMap(seatStatusMap);
    }

    public String getShowId() { return showId; }
}

// ─── BookingService ─────────────────────────────────────────────
public class BookingService {
    private final Map<String, Show>    shows   = new ConcurrentHashMap<>();
    private final Map<String, Booking> bookings = new ConcurrentHashMap<>();
    private final PaymentGateway       paymentGateway;
    private final NotificationService  notifier;

    public BookingService(PaymentGateway paymentGateway, NotificationService notifier) {
        this.paymentGateway = paymentGateway;
        this.notifier       = notifier;
    }

    public SeatHold holdSeats(String userId, String showId, List<String> seatIds) {
        Show show = getShow(showId);
        SeatHold hold = show.holdSeats(userId, seatIds, 10);
        System.out.printf("Hold created: %s for seats %s. Expires: %s%n",
            hold.getHoldId(), seatIds, hold.getExpiresAt());
        return hold;
    }

    public Booking confirmBooking(String holdId, String showId,
                                   List<String> seatIds, String userId,
                                   double amount, String paymentToken) {
        // 1. Charge payment
        PaymentResult payment = paymentGateway.charge(paymentToken, amount);
        if (!payment.isSuccess()) {
            // Payment failed — hold still valid for retry
            throw new PaymentFailedException("Payment failed: " + payment.getError());
        }

        // 2. Confirm seats
        Show show = getShow(showId);
        boolean confirmed = show.confirmSeats(holdId, seatIds);
        if (!confirmed) {
            // Hold expired between payment and confirmation — refund
            paymentGateway.refund(payment.getTransactionId(), amount);
            throw new HoldExpiredException("Seat hold expired. Payment refunded.");
        }

        // 3. Create booking record
        Booking booking = new Booking(UUID.randomUUID().toString(),
            showId, userId, seatIds, amount, BookingStatus.CONFIRMED);
        bookings.put(booking.getBookingId(), booking);

        // 4. Send confirmation
        notifier.sendBookingConfirmation(userId, booking);
        return booking;
    }

    public void cancelBooking(String bookingId) {
        Booking booking = bookings.get(bookingId);
        if (booking == null) throw new IllegalArgumentException("Booking not found");

        Show show = getShow(booking.getShowId());
        // Mark seats available again
        show.releaseHold("CANCEL-" + bookingId, booking.getSeatIds());
        // Actually release confirmed seats:
        booking.getSeatIds().forEach(seatId ->
            show.forceReleaseSeat(seatId));

        double refund = calculateRefund(booking);
        // Process refund...
        booking.setStatus(BookingStatus.CANCELLED);
        notifier.sendCancellationConfirmation(booking.getUserId(), refund);
    }

    private double calculateRefund(Booking booking) {
        Show show = shows.get(booking.getShowId());
        long hoursToShow = Duration.between(LocalDateTime.now(), show.getStartTime()).toHours();
        if (hoursToShow > 48) return booking.getTotalAmount();           // full refund
        if (hoursToShow > 0)  return booking.getTotalAmount() * 0.5;    // 50% refund
        return 0.0;                                                       // no refund
    }

    private Show getShow(String showId) {
        Show show = shows.get(showId);
        if (show == null) throw new IllegalArgumentException("Show not found: " + showId);
        return show;
    }

    public void addShow(Show show) { shows.put(show.getShowId(), show); }
}
```

---

## Component Choices

```
COMPONENT             CHOICE                   WHY
─────────────────────────────────────────────────────────────────────
Seat hold atomicity   Per-show ReentrantLock   All-or-nothing hold for
                      wrapping all seatIds     multiple seats. If A2 is
                                               unavailable: hold NOTHING
                                               (don't partially hold A1).
                                               Global lock: too coarse.
                                               Per-seat lock: deadlock risk
                                               (Thread1 holds A1, wants A2;
                                               Thread2 holds A2, wants A1).

Hold TTL              ScheduledExecutor        10-min auto-release.
                                               Production: Redis TTL key
                                               (survives app restart).
                                               Key: "hold:{holdId}" TTL=600s

Seat status storage   ConcurrentHashMap        Fast O(1) lookup by seatId.
                                               Within showLock: updates safe.

Payment-then-confirm  Two-phase                Pay first, then confirm hold.
ordering                                       If confirm fails: refund.
                                               Never confirm before pay
                                               (seats booked without payment).

Booking confirmation  Async notification       Don't make user wait for email.
                                               Fire-and-forget after booking
                                               confirmed in DB.
```

---

## ASCII — Concurrent Booking Race

```
  Time    User A (wants A1,A2)        User B (wants A2,A3)
  ────────────────────────────────────────────────────────
  T=0     acquires showLock ─────────────── WAITING ──────
  T=1     check A1: AVAILABLE                │
  T=2     check A2: AVAILABLE                │
  T=3     mark A1: HELD                      │
  T=4     mark A2: HELD                      │
  T=5     release showLock ──────────── acquires showLock
  T=6                                    check A2: HELD ❌
  T=7                                    throw SeatNotAvailableException
  T=8                                    → UI: "A2 no longer available"
  T=9                                    → suggest A3, A4 instead
  ────────────────────────────────────────────────────────
  RESULT: A is booked A1+A2. B gets to try different seats.
          Zero double-booking. ✅
```

---

## Senior Trap Questions

**Q1: "What about distributed deployment — 5 app servers, same show, different users?"**
```
In-process ReentrantLock only works on ONE JVM.
With 5 app servers: User A on Server1, User B on Server2.
Both servers have separate lock instances → both think they own the lock!
Double booking is back!

FIX: Distributed lock via Redis (Redlock algorithm):
  String lockKey = "show:lock:" + showId;
  Boolean acquired = redis.set(lockKey, serverId, "NX", "EX", 5); // 5s lock
  if (acquired) {
      try {
          // hold seats atomically in DB
          seatRepository.holdSeatsAtomically(showId, seatIds, holdId);
      } finally {
          redis.del(lockKey); // release
      }
  }

Better approach: Optimistic locking in DB
  seats table: seatId, showId, status, version (optimistic lock column)
  UPDATE seats SET status='HELD', version=version+1, holdId=?
  WHERE seatId=? AND status='AVAILABLE' AND version=?
  If rows_updated = 0 → someone else got it → retry or fail
  No distributed lock needed → higher throughput
```

**Q2: "Payment succeeded but hold confirmation failed (hold expired in 10ms gap). How do you handle the refund automatically?"**
```
This is the payment-confirmation race condition.

Timeline:
  T=0:00: Hold created, expires T=10:00
  T=9:59: User clicks "Pay"
  T=9:59.5: Payment gateway charges card ✅
  T=10:00: Hold expires (ScheduledExecutor fires) ← race!
  T=10:00.5: confirmSeats() → hold not found → returns false
  T=10:00.6: We catch "false" → initiate refund via gateway

Implementation:
  boolean confirmed = show.confirmSeats(holdId, seatIds);
  if (!confirmed) {
      paymentGateway.refund(payment.getTransactionId(), amount);
      throw new HoldExpiredException("Hold expired. Payment refunded. Ref: " + txnId);
  }

The refund must happen in the SAME request so the user immediately knows.
Store payment txnId → in case refund also fails → background job retries refund.
User sees: "Sorry, your hold expired. Your ₹350 will be refunded in 5-7 days."
```

**Q3: "How do you show real-time seat availability without querying DB on every request?"**
```
Push approach using WebSocket / SSE:
  1. Seat map page: client subscribes to SSE stream for showId
  2. When any seat status changes (HOLD/CONFIRM/RELEASE):
     → Publish event: { showId, seatId, newStatus } to Redis Pub/Sub
  3. All connected clients receive update → update seat color in UI

Scale:
  100,000 users watching the same show's seat map simultaneously
  One Redis pub/sub channel per showId
  Each seat change: one publish → 100,000 clients updated in <100ms

Without this: 100,000 clients polling every 2s = 50,000 GET requests/sec
With SSE: 100,000 persistent connections, push updates → much less DB load
```

---

## Failure Modes

```
SCENARIO              WHAT HAPPENS            FIX
────────────────────────────────────────────────────────────────────
App restart during    Held seats never        Redis TTL for holds (not
hold period           released                in-memory). Survives restart.

Payment gateway       User charges retried,   Idempotency key per holdId.
timeout — retry       double charge           Gateway: "already charged for
                                              this holdId" → return same txn.

Show cancelled        Confirmed bookings      CancelShow event:
after booking                                 → auto-refund all bookings
                                              → batch job per show

Seat layout           Admin changes screen    Versioned seat config.
changed after         mid-sale               New version applies to
bookings                                     future shows, not booked ones.
```

---

## Interview Cheat Sheet

> "BookMyShow's core problem is concurrent seat booking under massive load — think SRK movie releasing at midnight with 100,000 simultaneous users. The solution is all-or-nothing atomic holds: use a per-show lock (or Redis distributed lock in production), verify ALL selected seats are AVAILABLE, then HOLD all of them in one atomic operation. If any seat is taken: hold nothing, return error to user. A 10-minute TTL on the hold (Redis TTL in production) auto-releases if payment doesn't complete. The payment flow is: charge card → then confirm hold → if hold confirmation fails, automatically refund. The sneaky trap is between payment success and hold confirmation: the hold can expire in that millisecond gap — detect this with the `confirmSeats()` return value and trigger immediate refund. For real-time seat map updates: SSE/WebSocket + Redis pub/sub so 100k users watching the seat map don't hammer the DB with polling."
