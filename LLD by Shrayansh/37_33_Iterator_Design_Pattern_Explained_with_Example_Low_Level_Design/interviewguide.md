# Interview Guide: Iterator Design Pattern

## 🗣️ The Interview Scenario

> "You've built a `Library` class that internally stores its `Book` objects in a `List`. A client needs to iterate over every book in the library, print its name, and total up the prices — but you want the client code to work identically even if you later swap the internal storage to a `LinkedList`, an array, or a tree. How would you design this so the client never needs to know how books are stored internally? And can you explain, concretely, how Java's own `Collections` framework (e.g., `ArrayList`, `LinkedList`) achieves exactly this with `Iterator`, `hasNext()`, and `next()`?"

The interviewer wants you to recognize that this is a request for the **Iterator pattern**, and — crucially — wants you to connect it to something they already trust you've used a hundred times: `java.util.Iterator`. Being able to explain *how* `ArrayList`'s internal `Itr` class implements `hasNext()`/`next()` is a strong signal of real understanding, not just pattern memorization.

## 🏗️ Architect's Explanation (For a New Developer)

Think about `java.util.Collections`: you can loop over an `ArrayList`, a `LinkedList`, a `PriorityQueue`, or a `HashSet` using the *exact same* two method calls — `hasNext()` and `next()` — even though internally an `ArrayList` uses a resizable array, a `LinkedList` uses linked nodes, and a `HashSet` uses a hash table. As a *client*, you never need to know or care which internal data structure a collection uses — you just ask it for an "iterator" and repeatedly call `hasNext()`/`next()` until you're done.

The **Iterator pattern** formalizes exactly this contract. It defines two roles:
- **Aggregate**: something that *holds* a collection of data internally (e.g., `Library` holding a `List<Book>`) and exposes one method — `createIterator()` — that hands back an object capable of walking that collection.
- **Iterator**: a small object with exactly two operations, `hasNext()` (is there more data?) and `next()` (give me the next item, and advance). Each concrete collection type writes its *own* iterator that knows how to traverse *its own* internal structure — but the client only ever talks to the common `Iterator` interface.

This is precisely why you can write one generic `for` loop pattern that works across every Java collection type: the pattern **decouples "how to access elements sequentially" from "how the collection actually stores its data.**"

## 📊 Visualize It

**Class structure:**
```
        <<interface>>                       <<interface>>
          Aggregate                            Iterator
      +createIterator(): Iterator          +hasNext(): boolean
             ▲                              +next(): Object
             │ implements                        ▲
        ┌────┴─────┐                              │ implements
        │ Library    │                    ┌────────┴─────────┐
        ├───────────┤                BookIterator      (other concrete iterators
        │ -books:    │                ├─────────────┤   for other aggregates)
        │  List<Book>│                │ -books: List  │
        ├───────────┤                │ -index: int    │
        │ +createIter│───creates────► │ +hasNext()     │
        │   ator()   │                │   index<size   │
        └───────────┘                │ +next()        │
                                      │   return books  │
                                      │   [index++]     │
                                      └─────────────────┘
```

**Mapping onto real Java Collections (from the transcript's own walkthrough):**
```
java.util.Collection (Aggregate interface)  ──exposes──►  iterator(): Iterator
        ▲ implemented by
   ArrayList, LinkedList, PriorityQueue, HashSet, ...  (concrete aggregates)
        │ each defines its OWN inner class
   ArrayList.Itr implements Iterator {
        cursor : int
        hasNext() { return cursor != size; }
        next()    { return elementData[cursor++]; }
   }
   // LinkedList's iterator walks node.next pointers instead — client never knows the difference
```

**Runtime interaction sequence:**
```
Client:  library.createIterator()
              │
              └─► returns new BookIterator(library.books)

Client loop:
   while (iterator.hasNext()) {
       Book b = iterator.next();
       print(b.getName());
   }
   // client has ZERO knowledge of List internals, array indices, or node pointers
```

## 🔧 Deep Dive: How It Actually Works

### The core contract — two interfaces, always
```java
interface Iterator {
    boolean hasNext();
    Object next();
}
interface Aggregate {
    Iterator createIterator();
}
```
Every "collection-like" class must implement `Aggregate` (expose `createIterator()`), and for each such collection there's a matching **concrete iterator** that knows how to walk *that specific* internal structure.

### Concrete example from the transcript — `Library` and `Book`
```java
class Book {
    private String name;
    private double price;
    Book(String name, double price) { this.name = name; this.price = price; }
    String getName() { return name; }
}

class Library implements Aggregate {
    private List<Book> books;
    Library(List<Book> books) { this.books = books; }
    public Iterator createIterator() {
        return new BookIterator(books);          // Library decides WHICH iterator to use
    }
}

class BookIterator implements Iterator {
    private List<Book> books;
    private int index = 0;
    BookIterator(List<Book> books) { this.books = books; }
    public boolean hasNext() { return index < books.size(); }
    public Object next() {
        Book b = books.get(index);
        index++;
        return b;
    }
}
```

### Client usage — completely decoupled from `Library`'s internal storage
```java
List<Book> bookList = List.of(new Book("Book1", 100), new Book("Book2", 200), ...);
Library library = new Library(bookList);

Iterator it = library.createIterator();
while (it.hasNext()) {
    Book b = (Book) it.next();
    System.out.println(b.getName());
}
```
The transcript is explicit about the payoff: the client "doesn't have to know what is the underlying data structure — array, linked list, tree, whatever it is." If `Library` were reimplemented tomorrow to store books in a tree instead of a `List`, only `BookIterator`'s internals (and `Library.createIterator()`, if it now returns a different concrete iterator) would need to change — **the client loop above wouldn't change at all**.

### The real-world proof: Java's own Collections framework
The transcript walks directly into the JDK source to show this isn't theoretical:
- `java.util.Iterator` — the actual JDK interface — has exactly `hasNext()` and `next()`.
- Inside `ArrayList`, there's an inner class (`ArrayList.Itr`) that implements `Iterator`:
  ```java
  // conceptually, inside ArrayList
  private class Itr implements Iterator<E> {
      int cursor = 0;
      public boolean hasNext() { return cursor != size; }
      public E next() { return elementData[cursor++]; }
  }
  ```
- Every concrete collection type (`ArrayList`, `LinkedList`, `PriorityQueue`, `HashSet`, ...) is a **concrete Aggregate**, and each provides its **own** concrete iterator implementation tailored to its internal storage — array indices for `ArrayList`, node traversal for `LinkedList`, etc.
- The generic `Collection` interface itself plays the role of `Aggregate`, exposing `iterator()` as the `createIterator()`-equivalent method.

This is exactly why `for (Book b : books)` (Java's enhanced for-loop, which desugars to calling `iterator()`, `hasNext()`, and `next()` under the hood) works identically across every collection type — it's the Iterator pattern, built directly into the language's for-each syntax.

### Why "aggregate" specifically, and not just "collection"
The transcript deliberately uses "aggregate" as the more general term: an aggregate is *anything that maintains a collection of data* — it could be backed by an array, a linked list, a hash table, or something entirely custom — and its only obligation to the pattern is exposing `createIterator()` that returns an object implementing `hasNext()`/`next()` tailored to its own internal structure.

## 🔥 Real Production Incident & Fix

**What broke:** A reporting service exposed a custom `TransactionLedger` class (backed internally by a memory-mapped file for very large ledgers) but did **not** implement a proper `Iterator` — instead, client code across a dozen different report generators directly called `ledger.getRawBuffer()` and manually parsed offsets to walk records. When the team later optimized `TransactionLedger` internally to switch from a flat memory-mapped file to a paginated, chunked storage format for better memory locality, every one of those dozen call sites broke simultaneously, because they all assumed the old flat-offset layout.

**How the team noticed:** A coordinated deploy of the new `TransactionLedger` storage format caused a wave of `ArrayIndexOutOfBoundsException` and silently-wrong totals across multiple downstream reporting jobs within minutes — an incident channel lit up with reports from three different teams who each owned one of the report generators, all pointing at the same underlying class change.

**Root cause:** There was no Iterator abstraction — client code had reached directly into the aggregate's internal representation instead of going through a stable, storage-agnostic traversal contract. Any internal storage change was guaranteed to break every direct consumer, because the "how to walk the data" logic was duplicated across a dozen call sites instead of centralized in one place.

**The fix:** The team introduced a proper `LedgerIterator` (`hasNext()`/`next()`) on `TransactionLedger`, migrated every report generator to use it instead of raw-buffer parsing, and made `getRawBuffer()` package-private so it could no longer be called externally. When the storage format changed again six months later (chunked → columnar), zero downstream report generators needed any changes — only `LedgerIterator`'s internals were touched.

```
BEFORE (no Iterator — direct internal access):        AFTER (Iterator pattern):
ReportGenerator1 ──reads raw offsets──► ledger.buffer  ReportGenerator1 ──┐
ReportGenerator2 ──reads raw offsets──► ledger.buffer  ReportGenerator2 ──┼──► ledger.createIterator()
ReportGenerator3 ──reads raw offsets──► ledger.buffer  ReportGenerator3 ──┘        (hasNext/next only)
   storage format change ──► ALL 3 break                storage format change ──► only LedgerIterator changes
```

## ❓ Likely Interview Follow-Up Questions & Answers

**Q1: What's the difference between "Aggregate" and "Iterator" — why can't one class do both jobs?**
The Aggregate owns and manages the actual data (the `List<Book>` inside `Library`); the Iterator owns only the *traversal state* (e.g., current index/cursor) for one specific walk over that data. Separating them means you can have **multiple independent iterators over the same aggregate simultaneously** (e.g., two different loops walking the same `Library` at different positions) without them interfering with each other — if `Library` itself tracked a single cursor, only one traversal could happen at a time.

**Q2: How does Java's enhanced for-loop (`for (Book b : books)`) relate to this pattern?**
It's syntactic sugar that the compiler desugars into exactly the Iterator pattern's method calls: it calls `books.iterator()` once, then repeatedly calls `hasNext()` and `next()` in a while-loop — meaning every for-each loop you've ever written in Java is already using this pattern under the hood, whether or not you realized it.

**Q3: What happens if the underlying collection is modified while an iterator is actively traversing it?**
In Java's built-in collections, this typically throws a `ConcurrentModificationException`, detected via a "modCount" field that the iterator checks on each `next()` call against the value it captured at creation time — this is a classic **fail-fast iterator** design, and a good follow-up answer shows you know iterators need an explicit strategy for concurrent mutation, not just naive traversal.

**Q4: Could you design an iterator that supports removing an element mid-traversal, and how would that change the interface?**
Yes — add a third method, `remove()`, to the `Iterator` interface (exactly as Java's real `Iterator<E>` does), which removes the *last element returned by `next()`* from the underlying collection, requiring the concrete iterator to track enough state (e.g., "last returned index") to perform that removal safely without breaking its own cursor.

**Q5: How would you design an iterator for a tree structure (e.g., in-order traversal of a binary tree) versus a simple list?**
The `hasNext()`/`next()` contract stays identical, but the concrete iterator internally needs its own traversal state machine — commonly an explicit stack that simulates the recursive in-order/pre-order/post-order walk — so that each `next()` call advances the stack-based traversal by exactly one node and returns it, while `hasNext()` simply checks whether the stack (or an internal "next node" pointer) is empty.

**Q6: Is Iterator considered a behavioral or structural pattern, and why does that classification matter?**
It's a **behavioral** pattern — it's about how objects *communicate and collaborate to accomplish a responsibility* (sequential access), not about how objects are *structurally composed* (structural patterns like Composite or Decorator). Recognizing the classification helps you reason about intent quickly in an interview: behavioral patterns solve "how should these objects interact," while structural patterns solve "how should these objects be assembled."

## 🔑 Key Takeaway
The Iterator pattern's entire value is decoupling "how to sequentially access elements" from "how the collection stores its data internally" — and Java's own `Collections` framework (`Iterator`, `hasNext()`, `next()`, plus the for-each loop) is a live, everyday proof that this pattern works at massive scale.
