# Library Management System — Complete LLD Interview Guide

**Interview Duration: 40 min | Difficulty: Medium | Must-Know: ⭐⭐⭐⭐ | 15-YOE Focus: Reservation Queue + Fine Calculation**

---

## BIG PICTURE — Architecture

```
 ┌──────────────────────────────────────────────────────────────────┐
 │                LIBRARY MANAGEMENT SYSTEM                        │
 │                                                                  │
 │  MEMBERS              CATALOG               BORROWING            │
 │  ┌──────────┐        ┌──────────────┐      ┌──────────────────┐ │
 │  │ Member   │        │ Book         │      │ BookLending      │ │
 │  │ memberId │        │ ISBN         │      │ lendBook()       │ │
 │  │ name     │◄──────►│ title/author │◄────►│ returnBook()     │ │
 │  │ email    │        │ copies[ ]    │      │ reserveBook()    │ │
 │  │ fines    │        │ available    │      │ calculateFine()  │ │
 │  └──────────┘        └──────────────┘      └──────────────────┘ │
 │                                                                  │
 │  RESERVATION QUEUE          NOTIFICATION               FINE     │
 │  ┌────────────────┐        ┌────────────┐      ┌─────────────┐ │
 │  │ ISBN → Queue   │        │ Email/SMS  │      │ ₹2/day      │ │
 │  │ [M1, M2, M3]   │        │ on avail.  │      │ after 14d   │ │
 │  │ FIFO order     │        └────────────┘      │ grace period│ │
 │  └────────────────┘                            └─────────────┘ │
 └──────────────────────────────────────────────────────────────────┘

 BOOK COPY STATE MACHINE:
 ┌──────────────────────────────────────────────────────────────────┐
 │  [AVAILABLE] ──lend()──► [BORROWED]                             │
 │       ▲                       │                                  │
 │       │                   return()                               │
 │       │                       │                                  │
 │       └── noReservation ──────┘                                 │
 │                                                                  │
 │  [BORROWED] ──reserveRequested──► queue member                  │
 │  on return: notify first in queue ──► [RESERVED for 48h]        │
 │  if not claimed in 48h ──► notify next in queue                 │
 │                                                                  │
 │  [AVAILABLE/BORROWED] ──lostOrDamaged──► [LOST]                │
 └──────────────────────────────────────────────────────────────────┘
```

---

## CONVERSATIONAL SCRIPT

### Phase 1 — Requirements (5 min)

**You:** "Let me gather requirements.

Functional:
- Members can search books by title, author, ISBN
- Borrow a book for 14 days — must have available copy
- Return book — system calculates fine if overdue
- Reserve book if all copies borrowed — FIFO queue
- When copy returned: notify first in reservation queue
- Reserved copy held for 48 hours — if not picked up, offer to next

Non-functional:
- Thread safe — concurrent borrows for same last copy
- Fine calculation must be accurate even for multi-year overdue
- Reservation queue per ISBN (not per copy — any returned copy satisfies next in queue)

Key question: Is a Book an ISBN (a title) or a physical copy? They're different entities. One ISBN can have 3 physical copies. I'll model them separately."

---

### Phase 2 — Core Entities

```
Book (ISBN-level)    → ISBN, title, author, genre, List<BookCopy>
BookCopy             → copyId, ISBN, status (AVAILABLE/BORROWED/RESERVED/LOST)
Member               → memberId, name, email, List<Lending> activeLoans, double fineOwed
Lending              → lendingId, copyId, memberId, borrowDate, dueDate, returnDate
Reservation          → reservationId, ISBN, memberId, reservedAt, expiresAt
LibrarySystem        → manages all operations
FineCalculator       → strategy interface: calculate(Lending lending)
NotificationService  → notify(Member, message)
```

---

### Phase 3 — Implementation

```java
// ─── Enums ─────────────────────────────────────────────────────
public enum CopyStatus { AVAILABLE, BORROWED, RESERVED, LOST }

// ─── BookCopy ───────────────────────────────────────────────────
public class BookCopy {
    private final String copyId;
    private final String isbn;
    private volatile CopyStatus status;

    public BookCopy(String copyId, String isbn) {
        this.copyId = copyId;
        this.isbn   = isbn;
        this.status = CopyStatus.AVAILABLE;
    }

    public synchronized boolean tryBorrow() {
        if (status == CopyStatus.AVAILABLE) {
            status = CopyStatus.BORROWED;
            return true;
        }
        return false;
    }

    public synchronized void returnCopy()    { status = CopyStatus.AVAILABLE; }
    public synchronized void reserveCopy()   { status = CopyStatus.RESERVED; }

    public CopyStatus getStatus() { return status; }
    public String getCopyId()     { return copyId; }
    public String getIsbn()       { return isbn; }
}

// ─── Book (ISBN level) ──────────────────────────────────────────
public class Book {
    private final String isbn;
    private final String title;
    private final String author;
    private final List<BookCopy> copies = new ArrayList<>();

    public Book(String isbn, String title, String author) {
        this.isbn   = isbn;
        this.title  = title;
        this.author = author;
    }

    public void addCopy(BookCopy copy)  { copies.add(copy); }

    public Optional<BookCopy> getAvailableCopy() {
        return copies.stream()
            .filter(c -> c.getStatus() == CopyStatus.AVAILABLE)
            .findFirst();
    }

    public long availableCount() {
        return copies.stream().filter(c -> c.getStatus() == CopyStatus.AVAILABLE).count();
    }

    public String getIsbn()   { return isbn; }
    public String getTitle()  { return title; }
    public String getAuthor() { return author; }
}

// ─── Lending ───────────────────────────────────────────────────
public class Lending {
    private final String lendingId;
    private final String copyId;
    private final String memberId;
    private final LocalDate borrowDate;
    private final LocalDate dueDate;
    private LocalDate returnDate;

    public Lending(String copyId, String memberId) {
        this.lendingId  = UUID.randomUUID().toString();
        this.copyId     = copyId;
        this.memberId   = memberId;
        this.borrowDate = LocalDate.now();
        this.dueDate    = borrowDate.plusDays(14);
    }

    public void markReturned() { this.returnDate = LocalDate.now(); }

    public boolean isOverdue() {
        LocalDate effectiveReturn = returnDate != null ? returnDate : LocalDate.now();
        return effectiveReturn.isAfter(dueDate);
    }

    public long overdueDays() {
        if (!isOverdue()) return 0;
        LocalDate effectiveReturn = returnDate != null ? returnDate : LocalDate.now();
        return ChronoUnit.DAYS.between(dueDate, effectiveReturn);
    }

    public String getLendingId() { return lendingId; }
    public String getCopyId()    { return copyId; }
    public String getMemberId()  { return memberId; }
    public LocalDate getDueDate() { return dueDate; }
}

// ─── Fine Calculator (Strategy) ────────────────────────────────
public interface FineCalculator {
    double calculate(Lending lending);
}

public class StandardFineCalculator implements FineCalculator {
    private static final double FINE_PER_DAY = 2.0;   // ₹2/day
    private static final double MAX_FINE     = 500.0;  // cap at ₹500

    @Override
    public double calculate(Lending lending) {
        long overdueDays = lending.overdueDays();
        if (overdueDays <= 0) return 0.0;
        return Math.min(overdueDays * FINE_PER_DAY, MAX_FINE);
    }
}

// ─── Library System ─────────────────────────────────────────────
public class LibrarySystem {
    private final Map<String, Book>       catalog        = new ConcurrentHashMap<>();
    private final Map<String, Member>     members        = new ConcurrentHashMap<>();
    private final Map<String, Lending>    activeLoans    = new ConcurrentHashMap<>();
    // ISBN → ordered queue of reservations
    private final Map<String, Queue<Reservation>> reservationQueues = new ConcurrentHashMap<>();
    private final FineCalculator          fineCalculator = new StandardFineCalculator();
    private final NotificationService     notifier;
    private final Map<String, ReentrantLock> bookLocks  = new ConcurrentHashMap<>();

    public LibrarySystem(NotificationService notifier) {
        this.notifier = notifier;
    }

    // ─── Borrow ──────────────────────────────────────────────────
    public Lending borrowBook(String memberId, String isbn) {
        Member member = members.get(memberId);
        if (member == null) throw new IllegalArgumentException("Unknown member");
        if (member.hasPendingFines()) throw new IllegalStateException("Clear fines before borrowing");
        if (member.getActiveLoans() >= 3)
            throw new IllegalStateException("Max 3 books at a time");

        Book book = catalog.get(isbn);
        if (book == null) throw new IllegalArgumentException("Book not found: " + isbn);

        // Per-ISBN lock prevents concurrent last-copy race
        ReentrantLock bookLock = bookLocks.computeIfAbsent(isbn, k -> new ReentrantLock());
        bookLock.lock();
        try {
            Optional<BookCopy> copy = book.getAvailableCopy();
            if (copy.isEmpty()) {
                throw new IllegalStateException("No copies available. Reserve instead.");
            }
            copy.get().tryBorrow();
            Lending lending = new Lending(copy.get().getCopyId(), memberId);
            activeLoans.put(lending.getLendingId(), lending);
            member.addActiveLoan();
            System.out.printf("Borrowed: %s (copy %s). Due: %s%n",
                book.getTitle(), copy.get().getCopyId(), lending.getDueDate());
            return lending;
        } finally {
            bookLock.unlock();
        }
    }

    // ─── Return ──────────────────────────────────────────────────
    public double returnBook(String lendingId) {
        Lending lending = activeLoans.remove(lendingId);
        if (lending == null) throw new IllegalArgumentException("Unknown lending");

        lending.markReturned();
        double fine = fineCalculator.calculate(lending);

        BookCopy copy = findCopy(lending.getCopyId());
        copy.returnCopy();

        Member member = members.get(lending.getMemberId());
        member.decrementActiveLoan();
        if (fine > 0) {
            member.addFine(fine);
            System.out.printf("Fine owed: ₹%.2f for %d overdue days%n",
                fine, lending.overdueDays());
        }

        // Notify reservation queue
        processReservationQueue(copy.getIsbn(), copy);
        return fine;
    }

    // ─── Reserve ─────────────────────────────────────────────────
    public Reservation reserveBook(String memberId, String isbn) {
        Book book = catalog.get(isbn);
        if (book == null) throw new IllegalArgumentException("Book not found");
        if (book.availableCount() > 0)
            throw new IllegalStateException("Copies available — borrow directly");

        Queue<Reservation> queue = reservationQueues
            .computeIfAbsent(isbn, k -> new LinkedList<>());

        boolean alreadyReserved = queue.stream()
            .anyMatch(r -> r.getMemberId().equals(memberId));
        if (alreadyReserved) throw new IllegalStateException("Already in queue");

        Reservation reservation = new Reservation(isbn, memberId);
        queue.offer(reservation);
        System.out.printf("Reserved. Position in queue: %d%n", queue.size());
        return reservation;
    }

    // ─── Process Queue on Return ─────────────────────────────────
    private void processReservationQueue(String isbn, BookCopy returnedCopy) {
        Queue<Reservation> queue = reservationQueues.get(isbn);
        if (queue == null || queue.isEmpty()) return;

        Reservation next = queue.poll();
        returnedCopy.reserveCopy(); // hold for 48h
        next.setExpiresAt(LocalDateTime.now().plusHours(48));

        Member member = members.get(next.getMemberId());
        notifier.notify(member,
            "Your reserved book '" + catalog.get(isbn).getTitle()
            + "' is available. Pick up within 48 hours.");

        // Schedule expiry — if not picked up, offer to next in queue
        scheduleReservationExpiry(isbn, returnedCopy, next);
    }

    private void scheduleReservationExpiry(String isbn, BookCopy copy, Reservation reservation) {
        Executors.newSingleThreadScheduledExecutor().schedule(() -> {
            if (copy.getStatus() == CopyStatus.RESERVED) {
                // Not claimed — free it and notify next
                copy.returnCopy();
                processReservationQueue(isbn, copy);
            }
        }, 48, TimeUnit.HOURS);
    }

    private BookCopy findCopy(String copyId) {
        return catalog.values().stream()
            .flatMap(b -> b.getCopies().stream())
            .filter(c -> c.getCopyId().equals(copyId))
            .findFirst()
            .orElseThrow();
    }

    public void addBook(Book book) { catalog.put(book.getIsbn(), book); }
    public void addMember(Member member) { members.put(member.getMemberId(), member); }
}

// ─── Reservation ───────────────────────────────────────────────
public class Reservation {
    private final String reservationId;
    private final String isbn;
    private final String memberId;
    private final LocalDateTime reservedAt;
    private LocalDateTime expiresAt;

    public Reservation(String isbn, String memberId) {
        this.reservationId = UUID.randomUUID().toString();
        this.isbn          = isbn;
        this.memberId      = memberId;
        this.reservedAt    = LocalDateTime.now();
    }

    public void setExpiresAt(LocalDateTime time) { this.expiresAt = time; }
    public String getMemberId() { return memberId; }
    public String getIsbn()     { return isbn; }
}
```

---

## Component Choices

```
COMPONENT            CHOICE                  WHY
─────────────────────────────────────────────────────────────────────
Concurrency          Per-ISBN ReentrantLock  Don't lock ALL books.
                                             Lock only the ISBN being
                                             borrowed. Other ISBNs
                                             proceed concurrently.
                                             vs synchronized: can't do
                                             per-key granularity.

Reservation          LinkedList Queue        FIFO is the fairness rule.
                                             Offer/poll O(1).

Fine calculation     Strategy Pattern        Different libraries may
                                             have different fine rules.
                                             StandardFine, GracePeriodFine,
                                             etc. — swap without changing
                                             LibrarySystem.

Reservation expiry   ScheduledExecutor       48-hour auto-expiry per
                                             reservation. Non-blocking.
                                             Production: Redis TTL key
                                             or scheduled job in DB.

Copy-level locking   synchronized on copy    tryBorrow() is atomic.
                                             Multiple threads checking
                                             same copy — only one wins.
                                             Per-ISBN lock covers queue.
```

---

## Senior Trap Questions

**Q1: "Two members try to borrow the last copy simultaneously. Who wins?"**
```
The per-ISBN ReentrantLock ensures only one thread enters the
critical section at a time.

Thread 1: acquires bookLock → getAvailableCopy() → copy found → borrowed ✅
Thread 2: waits for bookLock → getAvailableCopy() → copy.status=BORROWED → throws
          "No copies available. Reserve instead."

The key: lock wraps BOTH the availability check AND the status update.
If they were separate (check outside lock, update inside lock) → race condition.
```

**Q2: "Member returns book. Queue is processed. Member picks up reserved copy. What if the original borrower tries to borrow again before expiry?"**
```
The copy is in RESERVED status for 48h for the queue member.
If another member tries to borrow the same ISBN:
  - If other copies exist and are AVAILABLE → they get those
  - If only the RESERVED copy remains → "No copies available. Reserve instead."

The RESERVED copy is exclusively held for the queue member.
After 48h without pickup: copy status → AVAILABLE, next in queue notified.
The 48h window is generous but prevents indefinite holding.
```

**Q3: "How do you handle the same member appearing in two reservation queues simultaneously and then returning a book in one queue?"**
```
A member can reserve multiple books (different ISBNs).
Reservation queue is per-ISBN — completely independent.
Member has maxActiveLoans check (3 books) at borrow time.

Scenario: Member has 3 books, queued for Book X.
Book X becomes available, member is notified.
Member must return one book to borrow Book X (activeLoans=3 cap).
The reserved hold timer (48h) starts ticking.
If they don't return+borrow within 48h → reservation expires.
```

**Q4: "ISBN vs Copy — why model them separately? What's the impact on search?"**
```
Book (ISBN level): metadata — title, author, subject, description.
BookCopy: physical instance — condition (GOOD/DAMAGED), location (shelf B3), barcode.

Search is always at ISBN level:
  "Find Harry Potter" → returns the Book entity (ISBN)
  Then: "How many copies available?" → count BookCopy where status=AVAILABLE

If you model them as one class:
  - Duplicate metadata for every physical copy
  - "Is any copy available?" requires joining/iterating copies
  - Updates to metadata (fix author name) → update N rows instead of 1

The separation = Book is the logical entity, BookCopy is the physical artifact.
```

---

## Failure Modes

```
SCENARIO               WHAT HAPPENS              FIX
────────────────────────────────────────────────────────────────────
Notification service   Member doesn't know       Retry with backoff.
down when copy returned reservation is ready     Fallback: SMS if email fails.
                                                 Reservation holds for 48h.
                                                 Member can also poll status.

48h timer fires but    ScheduledExecutor task    Use persistent scheduler
app restarts           lost on restart           (Quartz/DB-based job) in prod.
                                                 Or: check reservation expiry
                                                 on every borrow request.

Fine unpaid,           Member tries to borrow    Check hasPendingFines()
member tries borrow    → should be blocked       before borrowing. Block
                                                 until fine cleared.

Book marked returned   Data inconsistency        Barcode scan at return.
but actually lost                                Copy status → LOST manually.
                                                 Charge replacement cost.
                                                 Fine still applies.
```

---

## Interview Cheat Sheet

> "Library management is about two key relationships: Book (ISBN metadata) vs BookCopy (physical instance), and Members vs Lendings. The core complexity is the reservation queue — when all copies of an ISBN are borrowed, members join a FIFO queue. When any copy is returned, the first person in queue is notified and the copy is held for 48 hours. If they don't collect, the next person is notified. Thread safety uses per-ISBN locks — not a global lock — so concurrent borrows of different books don't block each other. The concurrent last-copy race is the classic trap: the availability check and the status update must be inside the same lock, not separate. Fine calculation uses Strategy pattern so different libraries can have different rules. In production, the 48-hour reservation expiry would be a Quartz job or Redis TTL, not an in-memory ScheduledExecutor that would lose state on restart."
