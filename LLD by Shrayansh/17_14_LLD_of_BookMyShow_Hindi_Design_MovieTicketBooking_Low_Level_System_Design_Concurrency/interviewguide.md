# Interview Guide: BookMyShow (Movie Ticket Booking) LLD

## 🗣️ The Interview Scenario

> "Design a movie ticket booking system like BookMyShow. A user should be able to pick their city, browse movies playing in that city, choose a theatre and show, select seats, and complete a booking with payment. Give me the class design first, then tell me: **two different users click the same seat for the same show at almost the same time — how does your system guarantee only one of them gets it?** Also, what happens if someone selects a seat, walks away, and never pays?"

This is a deliberately two-part question. Most candidates can sketch the entities. The interview is actually won or lost on the concurrency answer — that's where a Principal Engineer is really testing you.

## 🏗️ Architect's Explanation (For a New Developer)

Think of this system as a **funnel that narrows as the user commits more**:

`City → Movies in that city → Theatres showing the selected movie → Shows (time slots) at a theatre → Seats in that show → Booking → Payment`

The key insight the transcript hammers on: **this is a top-down design, not bottom-up.** In problems like "design a parking lot" or "design an elevator," you usually start from the smallest physical unit (a parking spot, a lift car) and build up. Here, the *product* is the Movie — a movie doesn't belong to one theatre, it's the top-level searchable entity that "flows down" into theatres and shows. So we start modeling from `Movie` and work down to `Seat`.

The second core idea is a **controller/registry pattern**: because everything is scoped by city (you can't show a user movies playing in Mumbai when they're in Bangalore), we need lookup objects — a `MovieController` and a `TheatreController` — that act as in-memory indexes (`Map<City, List<Movie>>` and `Map<City, List<Theatre>>`) so we can answer "what's playing near me?" in O(1) instead of scanning everything.

The third and most important idea: **concurrency control on seat booking**. Multiple people can look at the same seat map at the same time, but only one booking may succeed per seat. This is solved with **optimistic locking using a version number**, not a heavyweight lock.

## 📊 Visualize It

### Class / entity structure

```
Movie
 ├─ movieId, name, duration

MovieController
 ├─ Map<City, List<Movie>>      // city-wise movie listing
 └─ List<Movie> allMovies       // full catalog

Theatre
 ├─ theatreId, address (has city)
 └─ List<Screen>

Screen
 ├─ screenId
 └─ List<Seat>                  // seat layout for this screen

Seat
 ├─ seatId
 └─ SeatCategory (SILVER | GOLD | PLATINUM) → price

Show
 ├─ showId
 ├─ Movie movieDetail
 ├─ Screen screenInfo
 ├─ time
 └─ List<SeatId> bookedSeatIds  // which seats are already taken

TheatreController
 ├─ Map<City, List<Theatre>>
 └─ List<Theatre> allTheatres

Booking
 ├─ Show
 ├─ List<Seat> bookedSeats
 └─ Payment

Payment
 ├─ paymentId
 └─ paymentStatus

BookMyShow (driver / facade)
 ├─ MovieController
 └─ TheatreController
```

### Concurrent seat-booking flow (optimistic locking)

```
              Seat #30 (version = 1)
                     │
       ┌─────────────┴─────────────┐
       │                           │
   User A reads                User B reads
   seat, version=1              seat, version=1
       │                           │
   User A commits first        User B tries to commit
   check: local v(1) == db v(1)?  check: local v(1) == db v(1)?
   YES → book seat, v becomes 2   NO! db is now v(2) → REJECTED
       │                           │
   Booking SUCCESS              "Seat unavailable, retry"
```

## 🔧 Deep Dive: How It Actually Works

### 1. Object identification (top-down)

The transcript explicitly calls out that most LLD problems (parking lot, elevator) are built **bottom-up**, but this one is **top-down** because the *product being sold* (the Movie) sits at the top of the hierarchy:

- `Movie` — `movieId`, `name`, `duration` (you can extend with language/genre).
- `MovieController` — holds `Map<City, List<Movie>>` **plus** a flat `List<Movie> allMovies`, because sometimes you need to look up a movie by ID regardless of city.
- `Theatre` — `theatreId`, `address` (city can live inside `Address` or be a separate field — the instructor notes it's not mandatory to make `Address` a separate class), `List<Screen>`.
- `Screen` — `screenId`, `List<Seat>` (seat layout differs per screen, so seats belong to the screen, not the theatre).
- `Show` — `showId`, `movieDetail` (which movie), `screenInfo` (which screen), `time`, and critically `List<Seat Id> bookedSeatIds` — **the Show is the entity that owns "which seats are taken," not the Screen**, because the same screen can run multiple shows (8am, 12pm, 4pm) with independent booking state.
- `Seat` — `seatId`, `SeatCategory` (Silver / Gold / Platinum), each category carrying its own price for fare computation.
- `TheatreController` — mirrors `MovieController`: `Map<City, List<Theatre>>` plus `List<Theatre> allTheatres`, needed because the app is "tied up with the city" from the very first screen.
- `Booking` — references the `Show`, the list of booked `Seat`s, and a `Payment`.
- `Payment` — `paymentId`, `paymentStatus`.
- `BookMyShow` — the driver/facade class holding `MovieController` and `TheatreController`, exposing the operations users actually call.

### 2. The booking walkthrough (traced end-to-end in the transcript)

```java
// 1. Find movies available in the user's city
List<Movie> movies = movieController.getMoviesByCity("Bangalore");

// 2. Filter to the movie the user is interested in (e.g. "Baahubali")
Movie interested = filter(movies, "Baahubali");

// 3. Find all theatres in the city, then all shows of that movie
List<Theatre> theatres = theatreController.getTheatresByCity("Bangalore");
List<Show> shows = getShowsForMovie(theatres, interested);

// 4. User picks one particular show (e.g. the 4pm show)
Show selectedShow = shows.get(0);

// 5. User selects seat #30 within that show's screen
Seat seat = selectedShow.getScreenInfo().getSeat(30);
if (!selectedShow.getBookedSeatIds().contains(seat.getSeatId())) {
    selectedShow.getBookedSeatIds().add(seat.getSeatId());
    Booking booking = new Booking(selectedShow, List.of(seat), payment);
    // booking successful
} else {
    // "seat already booked" — reject and ask user to retry
}
```

The instructor explicitly demonstrates the **failure path**: a second user tries to book the exact same seat #30 for the same show → since it's already in `bookedSeatIds`, the booking is rejected with "seat not available, try again."

### 3. Concurrency control — the follow-up question that matters most

Two locking philosophies are contrasted directly:

| | **Pessimistic Locking** | **Optimistic Locking** |
|---|---|---|
| When you lock | At **read** time — lock immediately, before anyone else can even view the record | Only at **commit/write** time |
| Mechanism | Acquire a lock → read → update → release lock | Read + remember a `version` number → on update, check if version is unchanged → if yes, update and increment version; if no, **fail and force a re-read** |
| Cost under high concurrency | Poor — with millions of users trying to book seats for a popular show, locking every seat a user merely *looks at* would strangle throughput | Good — no lock is held while the user is just browsing/deciding |

The instructor's explicit recommendation: **"In my opinion, optimistic locking is the best way to handle concurrency for this app."** Reasoning given: if a user is selecting multiple seats one at a time (select, deselect, select another), a pessimistic lock held from the moment of *selection* would prevent efficient utilization of the system under heavy traffic ("millions of users").

**How optimistic locking is applied per seat:**
- Every `Seat` carries a hidden `version` counter (this is literally how DB-level optimistic locking, e.g. JPA `@Version`, works — the video ties this to standard practice).
- User reads the seat → gets `version = 1`.
- On booking commit: check `WHERE seatId = X AND version = 1` → if the row still matches, book it and bump `version` to `2`.
- If another transaction already booked it and moved `version` to `2` first, your commit's `WHERE version = 1` matches zero rows → **your transaction fails**, and the caller must re-fetch and retry (or simply be told the seat is gone).

### 4. Seat-hold timeout (the second concurrency requirement)

Two explicit requirements were called out:
1. The same seat number must never be sold to two people.
2. If a user selects a seat but does **not complete payment within a time window (the video uses a 10-minute example)**, the seat lock must auto-release.

**Solution given:** store the seat-hold in a caching layer such as **Redis**, which natively supports **TTL / expiry on keys**. Set the lock's expiry to N minutes (10 in the example); if the user hasn't confirmed payment by then, the key expires automatically and the seat becomes bookable again — no manual cleanup job required.

## 🔥 Real Production Incident & Fix

**What broke:** A mid-sized ticketing startup (a BookMyShow-style clone) launched a flash sale for a blockbuster's opening-day show. Within the first two minutes of tickets going live, the on-call engineer started getting PagerDuty alerts: **"payment_failed_after_seat_confirmed"** spiking, and customer support tickets saying *"I paid for seat H12 but the confirmation shows someone else's booking ID for the same seat."*

**How the team noticed:** A Grafana dashboard tracking `bookings_created` vs `payments_succeeded` showed a sudden divergence — booking rows were being created faster than they should have been possible for a single-seat inventory, and a database uniqueness constraint on `(show_id, seat_id, status='CONFIRMED')` started throwing constraint-violation exceptions in the logs at a rate of ~40/minute.

**Root cause:** The original implementation used a **naive read-then-write** pattern with no version check at all:
```java
Seat seat = repository.findSeat(seatId);
if (!seat.isBooked()) {
    seat.setBooked(true);          // race condition here
    repository.save(seat);
}
```
Under low traffic this "worked" because requests were naturally spaced out. Under flash-sale load, dozens of threads across multiple app server instances read `isBooked() == false` for the *same seat* in the same few milliseconds, all passed the check, and all proceeded to "book" it — the database's own unique constraint was the only thing that caught some of them (after money had already been captured on the payment gateway side for more than one user).

**The fix:** Exactly the pattern from this transcript — add a `version` column to the `seat_show` row, and change the update to a **conditional, optimistic-locking write**:
```sql
UPDATE seat_show
SET booked = true, version = version + 1
WHERE seat_id = :seatId AND show_id = :showId AND version = :expectedVersion;
-- if affected rows == 0 → booking fails, caller must retry with fresh read
```
Combined with a Redis-backed seat hold with a **TTL of 10 minutes** for the payment window, this eliminated double-bookings entirely and gave clear, cheap "seat taken, please pick another" feedback instead of confusing double-charge refunds.

```
BEFORE:                              AFTER:
read → check flag → write            read (get version) → write WITH version check
(race window between                 (DB atomically rejects stale writes;
 check and write)                     losing thread retries or informs user)
   ❌ two threads both "win"            ✅ only one thread's write matches
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: Why not just use a database row-level lock (`SELECT ... FOR UPDATE`) instead of optimistic locking?**
A: `SELECT FOR UPDATE` is a pessimistic lock — it works, but it holds a lock on the row for the entire transaction duration, which includes network round-trips to the payment gateway if you're not careful. At high concurrency (a flash sale with thousands of concurrent seat views per second), this serializes access and creates lock contention/timeouts. Optimistic locking only pays a cost at the actual write, so read-heavy, low-conflict-rate workloads (most users looking at a seat map are *not* going to collide) perform far better.

**Q2: What happens if the optimistic-lock update fails — do you retry automatically or fail the request?**
A: For a user-facing seat booking, you should **not** silently auto-retry picking a *different* seat — that would violate user consent. Instead, fail fast, tell the user "this seat was just taken," refresh the seat map, and let them pick again. Auto-retry is more appropriate for backend-internal counters (e.g., decrementing available inventory count) where any valid unit is interchangeable.

**Q3: Why does the `Show` object hold `bookedSeatIds` instead of the `Screen`?**
A: A `Screen` is a physical/reusable resource — the same screen hosts multiple shows a day (8am, 12pm, 4pm), each with independent seating state. If booking state lived on `Screen`, an 8am booking would incorrectly block the same seat for the 4pm show. `Show` is the unique combination of (movie, screen, time), so booked-seat tracking must be scoped there.

**Q4: How would you avoid holding a Redis lock indefinitely if a user closes the browser tab mid-payment?**
A: That's exactly why the hold is stored with a TTL (e.g., 10 minutes) rather than as a permanent flag. Redis's native expiry mechanism removes the key automatically — no cron job or manual cleanup process is needed, and the seat becomes available to other users the moment the TTL lapses, regardless of what the abandoning user's client does.

**Q5: How do you scale the "find movies playing in my city" query as the catalog grows to millions of shows?**
A: The `MovieController`'s `Map<City, List<Movie>>` is the in-memory analogy of what, in production, becomes a properly indexed database query or a cache (Redis/Elasticsearch) keyed by city — you never want to scan the entire movie catalog per user request. The same principle applies to `TheatreController`'s city-indexed map. In an interview, explicitly naming this as "an index by city, backed by a cache in production" shows you understand the transition from LLD toy model to real system.

**Q6: Why keep both a `Map<City, List<Movie>>` and a flat `List<Movie> allMovies` in `MovieController`?**
A: Because not every lookup is city-scoped — e.g., an admin operation, a search-by-movie-ID, or a recommendation engine may need the full catalog regardless of geography. Maintaining both avoids forcing every future feature to reverse-engineer the full list by iterating over all cities.

## 🔑 Key Takeaway

When an interviewer asks you to design a booking system, the class diagram is table stakes — the differentiator is showing you understand **why optimistic locking (version-checked writes) beats naive read-then-write or heavy pessimistic locks** for high-contention, high-read/low-conflict resources like seats, and that you pair it with a **TTL-based hold** to release abandoned selections automatically.
