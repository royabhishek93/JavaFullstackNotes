# Java Full-Stack Interview — Visual Notes

---

## 1. JVM Memory Model

```
┌─────────────────────────────────────────────────────────────────┐
│                          JVM MEMORY                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   HEAP MEMORY                             │   │
│  │                                                           │   │
│  │  ┌─────────────────────┐   ┌───────────────────────────┐ │   │
│  │  │    YOUNG GENERATION  │   │      OLD GENERATION        │ │   │
│  │  │                      │   │  (long-lived objects)      │ │   │
│  │  │  Eden  S0   S1        │   │                           │ │   │
│  │  │  [new] [  ] [  ]      │   │  Major GC (rare, slow)    │ │   │
│  │  │  Minor GC (frequent)  │   │                           │ │   │
│  │  └─────────────────────┘   └───────────────────────────┘ │   │
│  │                                                           │   │
│  │  String Pool lives inside Heap (since Java 7+)           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   METHOD AREA (Metaspace)                 │   │
│  │                                                           │   │
│  │  Class metadata  │  Static variables  │  Constant pool   │   │
│  │  Static methods  │  Method definitions                   │   │
│  │                                                           │   │
│  │  Before Java 8: PermGen (inside heap, fixed size)        │   │
│  │  Java 8+:       Metaspace (native memory, dynamic)       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────┐   ┌───────────────────────────┐     │
│  │   STACK (per thread)    │   │      PC REGISTER           │     │
│  │                         │   │  (current instruction)     │     │
│  │  Method frames          │   └───────────────────────────┘     │
│  │  Local variables        │                                      │
│  │  StackOverflowError     │   ┌───────────────────────────┐     │
│  │  when recursion too deep│   │   NATIVE METHOD STACK      │     │
│  └────────────────────────┘   └───────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘

StackOverflowError  → stack full (deep recursion)
OutOfMemoryError    → heap full (too many objects)
```

---

## 2. Garbage Collector

```
OBJECT LIFECYCLE:

  new Employee()   →  Eden  →  Minor GC  →  Survivor  →  Old Gen  →  GC
                                             (if alive)   (if old)   (eventually)

HOW GC WORKS:

  Step 1: Mark (find all reachable objects from GC Roots)
  Step 2: Sweep (remove unreachable objects)
  Step 3: Compact (optional — reorganize memory)

GC ROOTS:
  ┌────────────────────────────────┐
  │  Static variables              │
  │  Local variables in stack      │
  │  Active thread references      │
  └────────────┬───────────────────┘
               │ reachable from these → NOT collected
               ▼
  Everything else → COLLECTED

MINOR GC vs MAJOR GC:
  Minor → Young generation only, fast (milliseconds)
  Major → Old generation, slow (can pause app)
  Full  → Entire heap, slowest
```

---

## 3. String Pool & Object Count

```
String a = "hii";          → "hii" in String Constant Pool (SCP)
String b = "Ashmita";      → "Ashmita" in SCP
String c = "hii"+"Ashmita";→ compile-time constant → "hiiAshmita" in SCP
String d = a + b;          → runtime → new StringBuilder + new String in HEAP

                    STRING CONSTANT POOL (inside Heap, Java 7+)
                    ┌──────────────────────────────────────┐
                    │  "hii"         ←── a points here     │
                    │  "Ashmita"     ←── b points here     │
                    │  "hiiAshmita"  ←── c points here     │
                    └──────────────────────────────────────┘

                    HEAP
                    ┌──────────────────────────────────────┐
                    │  StringBuilder obj  ←── (temporary)  │
                    │  "hiiAshmita" String obj ←── d       │
                    └──────────────────────────────────────┘

Total objects = 5

RULES:
  literal + literal  → compile time → 1 SCP object
  variable + variable → runtime     → 2 heap objects (SB + String)

== vs equals():
  String a = "abc";
  String b = "ab" + "c";   ← compile-time constant → same SCP object
  a == b      → true  (same reference)
  a.equals(b) → true  (same content)

  String x = new String("abc");
  x == a      → false (different object, heap vs SCP)
  x.equals(a) → true
```

---

## 4. String, StringBuilder, StringBuffer

```
┌──────────────────┬───────────────────┬───────────────────┐
│  Feature         │  StringBuilder    │  StringBuffer     │
├──────────────────┼───────────────────┼───────────────────┤
│  Mutable         │  YES              │  YES              │
│  Thread-safe     │  NO               │  YES              │
│  Synchronized    │  NO               │  YES              │
│  Performance     │  FASTER           │  SLOWER           │
│  Use case        │  Single thread    │  Multi-thread     │
└──────────────────┴───────────────────┴───────────────────┘

String is IMMUTABLE:
  String s = "Hello";
  s.concat(" World");   ← creates NEW object, s unchanged
  System.out.println(s); → "Hello"

final + StringBuilder:
  final StringBuilder sb = new StringBuilder("Hello");
  sb.append(" World");  ✅ content can change
  sb = new StringBuilder(); ❌ reference cannot change
```

---

## 5. Collections Hierarchy

```
                         Iterable
                             │
                         Collection
                    ┌────────┴────────┐
                   List              Set               Map (separate)
              ┌─────┴─────┐     ┌────┴────┐      ┌─────────┴─────────┐
         ArrayList  LinkedList  HashSet  TreeSet  HashMap  LinkedHashMap
          Vector                LinkedHashSet       Hashtable  TreeMap
          Stack                                    ConcurrentHashMap

PICK THE RIGHT ONE:
  Need fast random access?        → ArrayList   O(1) get
  Need fast insert/delete middle? → LinkedList  O(1) add/remove at node
  No duplicates, no order?        → HashSet
  No duplicates, insertion order? → LinkedHashSet  ⭐ most asked
  No duplicates, sorted?          → TreeSet
  Key-value, no order?            → HashMap
  Key-value, insertion order?     → LinkedHashMap
  Key-value, sorted keys?         → TreeMap
  Thread-safe key-value?          → ConcurrentHashMap

Arrays.asList() vs List.of():
  Arrays.asList() → fixed size, allows set(), throws on add/remove
  List.of()       → fully immutable, throws on set/add/remove
```

---

## 6. HashMap — Internal Working

```
HashMap<String, Integer> map = new HashMap<>();
map.put("name", 1);

STEP 1: hashCode("name") → int hash value
STEP 2: hash % capacity  → bucket index (e.g. index 3)
STEP 3: store in bucket as LinkedList node

BUCKET ARRAY:
index:  0    1    2    3        4    5    ...  15
       null null null [name=1] null null ...  null
                        │
                    (LinkedList node)
                    { key="name", value=1, next=null }

COLLISION (same bucket):
index 3: [name=1] → [game=2] → [fame=3]
           equals("name")? Yes → found
           equals("name")? No  → next
           equals("name")? No  → next

JAVA 8 UPGRADE (bucket size > 8):
  LinkedList → Red-Black Tree  (O(n) → O(log n))

KEY RULES:
  Override equals() AND hashCode() together
  hashCode() → find bucket
  equals()   → confirm match within bucket

Integer cache (-128 to 127):
  Integer a = 100; Integer b = 100; → a == b → true  (same cached object)
  Integer a = 128; Integer b = 128; → a == b → false (new objects)
```

---

## 7. HashSet — Why No Duplicates

```
HashSet internally = HashMap where:
  element  → KEY
  dummy Object → VALUE  (always same PRESENT object)

add("Apple"):
  1. hash("Apple") → bucket 5
  2. bucket 5 empty → insert

add("Apple") again:
  1. hash("Apple") → bucket 5
  2. bucket 5 has node → equals("Apple") → TRUE → DUPLICATE
  3. Do NOT insert

No duplicate = HashMap key uniqueness guarantee
```

---

## 8. Fail-Fast vs Fail-Safe

```
FAIL-FAST (ArrayList, HashMap):
  Iterator created → reads modCount
  If collection modified → modCount changes
  Iterator detects mismatch → throws ConcurrentModificationException

  List<String> list = new ArrayList<>();
  for (String s : list) {
      list.remove(s);  // ← ConcurrentModificationException ❌
  }
  FIX: use Iterator.remove() or CopyOnWriteArrayList

FAIL-SAFE (CopyOnWriteArrayList, ConcurrentHashMap):
  Iterator works on COPY of data
  Modification on original → iterator not affected
  No exception → may see stale data
```

---

## 9. Java Streams — Lazy Evaluation

```
STREAM PIPELINE:

  Source           Intermediate ops (LAZY)      Terminal op (triggers all)
  ─────────        ────────────────────────     ─────────────────────────
  list.stream() → .filter(x > 10)           → .collect()
                → .map(x * 2)               → .forEach()
                → .sorted()                 → .count()
                                            → .findFirst()

NOTHING runs until terminal op fires!

  stream.filter(x -> x > 10)  ← builds instruction only
  stream.map(x -> x * 2)      ← builds instruction only
  stream.collect(...)          ← FIRES the entire pipeline

WHY LAZY?
  Process only what's needed:
  .filter().findFirst() → stops at FIRST match, doesn't process whole list

COMMON OPERATIONS:
  map()     → transform each element (1 → 1)
  flatMap() → transform each element to stream, then FLATTEN (1 → many)
  filter()  → keep matching elements
  sorted()  → sort
  distinct()→ remove duplicates
  skip(n)   → skip first n
  limit(n)  → take first n
  reduce()  → aggregate to single value
  collect() → gather into List/Map/Set

map() vs flatMap():
  map("abc") → "ABC"        (one string in, one string out)
  flatMap("abc") → 'a','b','c' (one string in, stream of chars out, flattened)
```

---

## 10. Thread Lifecycle

```
                   ┌──────────────────────────────────────────────────┐
                   │              THREAD LIFECYCLE                     │
                   │                                                   │
  Thread t = new Thread()
                   │
                   ▼
              ┌─────────┐
              │   NEW   │  ← created, start() not called yet
              └────┬────┘
                   │  t.start()
                   ▼
           ┌────────────────┐
           │   RUNNABLE     │  ← ready, waiting for CPU
           └───────┬────────┘
                   │  CPU assigned
                   ▼
           ┌────────────────┐
           │    RUNNING     │  ← actively executing run()
           └───────┬────────┘
          ┌────────┴─────────────┐
          │                      │
          ▼                      ▼
   ┌─────────────┐       ┌──────────────┐
   │   WAITING   │       │   BLOCKED    │
   │  wait()     │       │  waiting for │
   │  join()     │       │  a lock      │
   └──────┬──────┘       └──────┬───────┘
          │                     │
          └──────────┬──────────┘
                     │  notified / lock available
                     ▼
                RUNNABLE again
                     │
                     ▼
              ┌─────────────┐
              │  TERMINATED │  ← run() finished, cannot restart
              └─────────────┘
```

---

## 11. Deadlock

```
DEADLOCK — two threads waiting for each other forever:

  Thread 1:  holds Lock A  →  waiting for Lock B
  Thread 2:  holds Lock B  →  waiting for Lock A
                ↑_________________________↑
                   neither can proceed!

  Resource A ←──── Thread 1 ────► Resource B
       │                               │
       └──────── Thread 2 ────────────┘

PREVENT DEADLOCK:
  1. Consistent lock ordering (always acquire A before B)
  2. tryLock() with timeout (give up if can't get lock in time)
  3. Avoid nested locks

RACE CONDITION:
  Two threads read same value → both update → one overwrite lost
  Fix: synchronized or AtomicInteger
```

---

## 12. synchronized vs AtomicInteger

```
SYNCHRONIZED (pessimistic locking):
  Thread 1 → acquires lock → runs → releases lock
  Thread 2 → WAITS          ─────────────────────► runs

  synchronized void increment() { count++; }

ATOMIC INTEGER (optimistic — CAS: Compare And Swap):
  Thread 1: read=5, expected=5, actual=5 → swap to 6 ✅
  Thread 2: read=5, expected=5, actual=6 → MISMATCH → retry
            read=6, expected=6, actual=6 → swap to 7 ✅

  No lock. No waiting. Just retry on conflict.
  AtomicInteger count = new AtomicInteger(0);
  count.incrementAndGet();

COMPARE:
  synchronized  → lock-based,   thread waits,  always correct
  AtomicInteger → lock-free,    thread retries, better throughput
  Use AtomicInteger for simple counters in high-concurrency code.
```

---

## 13. Runnable vs Callable vs Thread

```
EXTENDING Thread:
  class MyTask extends Thread { void run() {...} }
  PROBLEM: Java = single inheritance → can't extend anything else

IMPLEMENTING Runnable:
  class MyTask implements Runnable { void run() {...} }
  BENEFIT: can still extend another class
  LIMITATION: cannot return result, cannot throw checked exceptions

IMPLEMENTING Callable:
  class MyTask implements Callable<String> { String call() throws Exception {...} }
  BENEFIT: returns result, can throw checked exceptions
  Used with: ExecutorService.submit() → returns Future<T>

execute() vs submit():
  executor.execute(runnable)   → fire & forget, no result tracking
  executor.submit(callable)    → returns Future, can get result, track status
```

---

## 14. Abstract Class vs Interface

```
┌──────────────────────────┬───────────────────────────────────────┐
│  Abstract Class           │  Interface                            │
├──────────────────────────┼───────────────────────────────────────┤
│  Can have state (fields)  │  No instance variables (constants ok) │
│  Has constructor          │  No constructor                       │
│  extends (single)         │  implements (multiple allowed)        │
│  Abstract + concrete      │  Abstract by default (Java 7-)        │
│  methods                  │  + default/static methods (Java 8+)   │
│  Any access modifier      │  public methods                       │
└──────────────────────────┴───────────────────────────────────────┘

WHY interface has no constructor?
  Constructor initializes object state.
  Interface has NO state → nothing to initialize → no constructor needed.
  Each implementing class has its own state + constructor.

DIAMOND PROBLEM with default methods:
  Interface1.show() + Interface2.show() → same name
  ┌──────────────────────────────────────────────────────┐
  │  class Test implements Interface1, Interface2 {      │
  │    @Override public void show() {                    │
  │       Interface1.super.show();  ← pick one           │
  │    }                                                 │
  │  }                                                   │
  └──────────────────────────────────────────────────────┘
  Rule: subclass MUST override to resolve ambiguity.
```

---

## 15. Immutable Class

```
How to make a class immutable:
  1. Declare class as final         (cannot be subclassed)
  2. All fields private + final     (cannot be reassigned)
  3. Initialize in constructor only (no setters)
  4. Defensive copy for mutable fields (List, Map, arrays)

  final class Employee {
      private final int id;
      private final List<String> skills;
      Employee(int id, List<String> skills) {
          this.id = id;
          this.skills = new ArrayList<>(skills); // defensive copy
      }
      List<String> getSkills() {
          return Collections.unmodifiableList(skills); // defensive copy on return
      }
  }

WHY? Thread-safe by default, no synchronization needed.
String is immutable → safe to share across threads.

Java 16+ Record:
  record Employee(int id, String name) {}  ← auto: constructor, getters, equals, hashCode, toString
  Fields are final → immutable by design.
```

---

## 16. Spring Boot Bean Scopes

```
┌────────────────┬──────────────────────────────────────────────────┐
│  Scope         │  Behaviour                                        │
├────────────────┼──────────────────────────────────────────────────┤
│  singleton ★   │  ONE object for entire app lifetime (default)    │
│  prototype     │  NEW object every time it is requested           │
│  request       │  ONE object per HTTP request (web only)          │
│  session       │  ONE object per user session (web only)          │
│  application   │  ONE object per web app context (web only)       │
└────────────────┴──────────────────────────────────────────────────┘

SCENARIO: prototype + request, 2 HTTP requests, method order: proto → req → proto

  One request:
    Step 1 → prototype requested → new object (count=1)
    Step 2 → request scope requested → new object (count=1)
    Step 3 → prototype requested → new object (count=2)
    Total: 2 prototype, 1 request

  Two requests → 4 prototype, 2 request beans
```

---

## 17. @Transactional — How It Works

```
  Client → Proxy wrapper → Your Service method → Database

Spring creates a PROXY around your @Service bean.
The proxy intercepts calls and:
  1. Opens a database transaction (BEGIN)
  2. Calls your actual method
  3. If success    → COMMIT
  4. If RuntimeException → ROLLBACK

IMPORTANT:
  ✅ Works for PUBLIC methods called from OUTSIDE the class
  ❌ Does NOT work for private methods (proxy can't intercept)
  ❌ Does NOT work for internal calls (this.method() bypasses proxy)
  ❌ Put @Transactional on the method called from outside, not inner method

USE WHEN:
  Multiple DB ops that must succeed or fail together:
  debitAccount() + creditAccount() = @Transactional
```

---

## 18. ACID Properties

```
ACID = Atomicity + Consistency + Isolation + Durability

┌──────────────┬───────────────────────────────────────────────────┐
│  Property    │  Meaning                                          │
├──────────────┼───────────────────────────────────────────────────┤
│  Atomicity   │  All or nothing. No partial execution.            │
│              │  Debit fails → Credit cancelled (rollback)        │
├──────────────┼───────────────────────────────────────────────────┤
│  Consistency │  Rules never break. Balance can't go negative.    │
│              │  Transaction rejected if it violates constraint.  │
├──────────────┼───────────────────────────────────────────────────┤
│  Isolation   │  Concurrent transactions don't see each other's   │
│              │  intermediate state. Last seat booked once only.  │
├──────────────┼───────────────────────────────────────────────────┤
│  Durability  │  Committed data survives crash. Saved to disk.    │
└──────────────┴───────────────────────────────────────────────────┘

COMMIT vs ROLLBACK:
  Commit   → persist all changes permanently
  Rollback → undo all changes back to previous state
```

---

## 19. Normalization

```
1NF → Each cell has ONE value (no repeating columns, no arrays in cell)
2NF → No partial dependency (non-key column depends on FULL primary key)
3NF → No transitive dependency (non-key column depends only on primary key)

EXAMPLE:

Before 1NF:
  student_id │ name  │ subjects
  1          │ Alice │ Math, Science  ← multiple values in one cell ❌

After 1NF:
  student_id │ name  │ subject
  1          │ Alice │ Math
  1          │ Alice │ Science

After 2NF (remove partial dependency):
  Students: student_id, name
  Enrollment: student_id, subject

After 3NF (remove transitive dependency):
  If: dept_id → dept_name (dept_name depends on dept_id, not student_id)
  → move dept_name to Departments table
```

---

## 20. Monolithic vs Microservices

```
MONOLITHIC:
  ┌──────────────────────────────────┐
  │           ONE APPLICATION         │
  │  UI + Business Logic + DB Access  │
  │  All modules in one codebase      │
  │  Single deployment unit           │
  └──────────────────────────────────┘
  Pros: Simple, easy to develop at start
  Cons: Tight coupling, redeploy all for small change, one failure = all down

MICROSERVICES:
  Client
    │
    ▼
  API Gateway
    ├──► User Service     → DB_Users
    ├──► Order Service    → DB_Orders
    ├──► Payment Service  → DB_Payments
    └──► Notification Service

  Each service:
    ✅ Independent deployment
    ✅ Own database
    ✅ Own tech stack possible
    ✅ Isolated failure
  Cons: Network overhead, distributed transactions complex, ops overhead

COMMUNICATION:
  Synchronous:  FeignClient / RestTemplate (caller waits)
  Asynchronous: Kafka (caller doesn't wait, event-driven)
```

---

## 21. Circuit Breaker (Resilience4j)

```
PROBLEM: Service A → Service B (down) → A keeps retrying → cascades failure

CIRCUIT BREAKER STATES:

           10 failures             30 sec timeout
  CLOSED ──────────────► OPEN ──────────────────► HALF-OPEN
    │                     │                            │
    │ (normal, calling B) │ (skip B, use fallback)     │ test 1 call
    │                     │                            │
    └─────────────────────────────────────────────────►┘ (if success → CLOSED)
                                                        (if fail    → OPEN again)

  @CircuitBreaker(name = "userService", fallbackMethod = "fallbackResponse")

Properties:
  failure-rate-threshold=50      ← open if 50% calls fail
  sliding-window-size=10         ← check last 10 calls
  wait-duration-in-open-state=10s← stay open 10s, then half-open
```

---

## 22. React — Virtual DOM & Reconciliation

```
REACT RENDERING FLOW:

  1. Developer writes JSX
     ↓
  2. Babel converts JSX → React.createElement() calls
     ↓
  3. React builds Virtual DOM (plain JS object tree)
     ↓
  4. React renders to Real DOM (first time)
     ↓
  State/Props change
     ↓
  5. React creates NEW Virtual DOM
     ↓
  6. DIFFING (compare old vs new Virtual DOM)
     Only find what changed
     ↓
  7. RECONCILIATION — update ONLY changed nodes in Real DOM

WHY Virtual DOM?
  Real DOM manipulation is expensive.
  Virtual DOM is a JS object — cheap to create and compare.
  Batch multiple changes → ONE real DOM update.
```

---

## 23. React Hooks — Quick Reference

```
useState        → store data that causes re-render when changed
useEffect       → run side effects (API call, timer, subscription)
useCallback     → memoize a function (prevent re-creation every render)
useMemo         → memoize a computed value (expensive calculation)
useRef          → store value WITHOUT causing re-render (DOM refs, timers)
useContext      → read from Context without prop drilling

useEffect dependency array:
  []              → runs ONCE after first render
  [dep1, dep2]    → runs when dep1 or dep2 changes
  (no array)      → runs on EVERY render

WHY can't hooks be inside conditions?
  React tracks hooks by ORDER of calls.
  If a hook is skipped (condition false) → order breaks → state gets mixed up.
  Rule: always call hooks at TOP LEVEL.

useMemo vs useCallback:
  useMemo(()    => expensiveCalc, [deps]) → caches the RESULT
  useCallback(() => someFunction, [deps]) → caches the FUNCTION

React.memo():
  Wraps component → skips re-render if props didn't change
  Only effective when combined with useCallback for function props
```

---

## 24. Redux Flow

```
  User Action (click button)
        │
        ▼
  Component dispatches Action
  { type: "ADD_TO_CART", payload: "Laptop" }
        │
        ▼
  Reducer receives action
  function cartReducer(state=[], action) {
    switch(action.type) {
      case "ADD_TO_CART": return [...state, action.payload]
      default: return state
    }
  }
        │
        ▼
  Store updates (single source of truth)
  { user: {...}, cart: ["Laptop"], isLoggedIn: true }
        │
        ▼
  React re-renders subscribed components

ONE-WAY DATA FLOW:
  Action → Reducer → Store → View → Action (cycle)

vs Context API:
  Context = built-in, simple sharing, no actions/reducers
  Redux   = structured, DevTools, time-travel debugging, complex state
```

---

## 25. HashMap vs ConcurrentHashMap vs Hashtable

```
┌──────────────────────┬─────────────────────┬──────────────────────┐
│  HashMap              │  ConcurrentHashMap  │  Hashtable           │
├──────────────────────┼─────────────────────┼──────────────────────┤
│  Not thread-safe      │  Thread-safe        │  Thread-safe         │
│  No locking           │  Bucket-level lock  │  Full map lock       │
│  null key ✅          │  null key ❌        │  null key ❌         │
│  null value ✅        │  null value ❌      │  null value ❌       │
│  Fail-fast iterator   │  Fail-safe iterator │  Fail-fast iterator  │
│  Fastest single thread│  Best multi-thread  │  Slowest             │
└──────────────────────┴─────────────────────┴──────────────────────┘

ConcurrentHashMap Java 8+:
  Removed 16 segments → now bucket-level CAS locking
  Multiple threads can write to DIFFERENT buckets simultaneously
  If bucket > 8 entries → LinkedList → Red-Black Tree

WHY null not allowed in ConcurrentHashMap?
  map.get(key) returns null → can't tell: key missing OR value is null
  In concurrent use, this ambiguity causes bugs → null banned.
```

---

## 26. Spring Boot Interceptor vs Filter vs AOP

```
  HTTP Request
      │
      ▼
  Filter (javax.servlet)          ← very first, before Spring even sees it
      │   Log, CORS, encoding
      ▼
  DispatcherServlet
      │
      ▼
  Interceptor (HandlerInterceptor) ← Spring-managed, has access to HandlerMethod
      │   preHandle()  ← before controller
      ▼
  Controller
      │
  Interceptor postHandle()         ← after controller, before response
      │
  Interceptor afterCompletion()    ← after full request+response cycle

AOP (@Aspect):
  Works at METHOD LEVEL on Spring beans
  Does not intercept HTTP — intercepts Java method calls
  Used for: logging, transactions, security at service layer

Interceptor lifecycle:
  preHandle()      → return true=continue, false=stop
  postHandle()     → add to response, logging
  afterCompletion()→ cleanup, final timing log
```

---

## 27. Key Output Questions

```
Q: char addition
   System.out.println('j' + 'a' + 'v' + 'a');
   'j'=106, 'a'=97, 'v'=118 → 106+97+118+97 = 418  ← NOT "java"

Q: i = i++ + ++i  (i=5)
   i++ → uses 5, then i becomes 6
   ++i → i becomes 7, uses 7
   i = 5 + 7 = 12

Q: String in for-each remove
   for (String s : list) { list.remove(s); }
   → ConcurrentModificationException (fail-fast)

Q: Arrays.asList set vs add
   list.set(1, "X") → ✅ allowed (modify)
   list.add("Y")    → ❌ UnsupportedOperationException (fixed size)

Q: Abstract chain (A→B→C, c.secondMethod())
   C c = new C();
   c.firstMethod();  → FIRST, THIRD
   c.secondMethod(); → SECOND, FIRST, THIRD
   c.thirdMethod();  → THIRD

Q: mutable key in HashMap
   Cat cat1 = new Cat("Jack");
   map.put(cat1, 50);
   cat1.setName("Jill");       ← hashCode changes!
   map.get(cat1) → null        ← wrong bucket now

Q: Compile error — unreachable catch
   try { int a = 2/0; }
   catch (ArrayIndexOutOfBoundsException e) {...}
   catch (Exception e) {...}
   catch (ArithmeticException e) {...}  ← COMPILE ERROR: already caught by Exception
```

---

## 28. SQL — Common Queries

```sql
-- Second highest salary (handles duplicates)
SELECT DISTINCT salary
FROM Employee
ORDER BY salary DESC
LIMIT 1 OFFSET 1;

-- Second highest in each department
SELECT department, salary FROM (
  SELECT department, salary,
    DENSE_RANK() OVER (PARTITION BY department ORDER BY salary DESC) as rnk
  FROM Employee
) t WHERE rnk = 2;

-- Top 3 customers by purchase in last 6 months
SELECT c.id, c.name, SUM(o.amount) AS total
FROM Customer c
JOIN Orders o ON c.id = o.customer_id
WHERE o.order_date >= NOW() - INTERVAL '6 months'
GROUP BY c.id, c.name
ORDER BY total DESC
LIMIT 3;

-- Top 3 selling categories
SELECT p.category, SUM(od.quantity) AS total_sold
FROM OrderDetails od
JOIN Products p ON od.product_id = p.product_id
GROUP BY p.category
ORDER BY total_sold DESC
LIMIT 3;

WHERE vs HAVING:
  WHERE  → filters ROWS before grouping (no aggregate functions)
  HAVING → filters GROUPS after grouping (can use SUM, COUNT, etc.)
```

---

## 29. Java 8 Stream — Employee Queries

```java
// All IT employees sorted by salary desc
employees.stream()
    .filter(e -> e.getDepartment().equals("IT"))
    .sorted(Comparator.comparingDouble(Employee::getSalary).reversed())
    .collect(Collectors.toList());

// Highest paid employee
employees.stream()
    .max(Comparator.comparingDouble(Employee::getSalary));

// Group by department
employees.stream()
    .collect(Collectors.groupingBy(Employee::getDepartment));

// Average salary per department
employees.stream()
    .collect(Collectors.groupingBy(
        Employee::getDepartment,
        Collectors.averagingDouble(Employee::getSalary)));

// Second highest salary
employees.stream()
    .map(Employee::getSalary)
    .distinct()
    .sorted(Comparator.reverseOrder())
    .skip(1)
    .findFirst();

// 3rd highest salary
employees.stream()
    .map(Employee::getSalary)
    .distinct()
    .sorted(Comparator.reverseOrder())
    .skip(2)
    .findFirst();

// First non-repeating char in "Character"
str.chars()
    .mapToObj(c -> (char) c)
    .collect(Collectors.groupingBy(c -> c, LinkedHashMap::new, Collectors.counting()))
    .entrySet().stream()
    .filter(e -> e.getValue() == 1)
    .map(Map.Entry::getKey)
    .findFirst();  // → 'h'
```

---

## 30. Multi-Tenant Database — Three Patterns

```
PATTERN 1: Shared DB, Shared Schema
  One table, tenant_id column:
  users: [ tenant_id | user_id | name ]
  Query: SELECT * FROM users WHERE tenant_id = 'TCS'
  Pro: cheapest, simplest
  Con: weakest isolation, risk of data leak if WHERE forgotten

PATTERN 2: Shared DB, Separate Schema
  CompanyDB
    ├── tcs_schema.users
    ├── wipro_schema.users
    └── accenture_schema.users
  Pro: better isolation, same DB server
  Con: schema management complexity

PATTERN 3: Separate DB per Tenant
  App → TCS → Database_TCS
      → Wipro → Database_Wipro
  Pro: strongest isolation, separate backup/scaling
  Con: most expensive, complex routing

Spring Implementation:
  Header: X-Tenant-ID: TCS → ThreadLocal → AbstractRoutingDataSource → routes to correct DB
```

---

## 31. Production Debugging Flow

```
INCIDENT: "Payment failed for order 789"

STEP 1 → Grafana (metrics dashboard)
  Check: error rate ↑, latency ↑, which service unhealthy
  Result: Payment Service showing high latency

STEP 2 → Elasticsearch (centralised logs)
  Search: orderId=789 AND @timestamp:[now-1h TO now]
  Find: traceId = "abc-123-xyz"

STEP 3 → Follow traceId across all services
  API Gateway → Order Service → Payment Service → ❌ timeout on bank API

STEP 4 → Grafana metrics for Payment Service
  Bank API external latency: HIGH

ROOT CAUSE: Bank API is slow → Payment Service timeout

FIX: increase timeout / add retry / add circuit breaker

kubectl commands:
  kubectl get pods -n <namespace>
  kubectl logs <pod-name> -n <namespace>
  kubectl logs -f <pod-name>       ← live stream
```

---

## 32. JWT + AWS Cognito Project Architecture

```
  Browser / Mobile App
          │
          │  1. Login → redirect to Cognito
          ▼
  AWS Cognito (User Pool)
          │  returns JWT token (with roles inside)
          ▼
  API Request + Authorization: Bearer <jwt>
          │
          ▼
  CloudFront + WAF (security, DDoS)
          │
          ▼
  API Gateway / Load Balancer
          │  JWT Authorizer validates:
          │  ✔ signature valid?  ✔ expired?  ✔ issued by Cognito?
          │  Invalid → 401
          ▼
  Spring Boot Microservices (in EKS)
          │  @PreAuthorize("hasRole('ADMIN')")
          │  Spring Security extracts roles from JWT claims
          │  Role mismatch → 403
          ▼
  Database / Other services

401 = token invalid / missing (authentication failed)
403 = token valid but role not allowed (authorization failed)
```

---

## 33. Kafka — Safe Message Delivery

```
PRODUCER ──► Kafka Topic ──► CONSUMER

acks=all (safe delivery):
  Producer sends message
  Leader replica writes it
  ALL in-sync replicas acknowledge
  Only then: producer gets success confirmation

CONSUMER OFFSET:
  Kafka tracks: "Consumer read up to message #50"
  auto.commit.offset=true → offset committed automatically after poll()
  RISK: consumer crashes after commit but before processing → message LOST

IDEMPOTENT consumer (solve duplicate processing):
  Before processing: check if tradeId already in settlement table
  If YES → skip (already processed)
  If NO  → process + save
  Even if Kafka re-delivers → processed only ONCE
```

---

## 34. React Performance Optimization

```
PROBLEM: unnecessary re-renders slow down the app

┌───────────────────────────────────────────────────────────────┐
│  Tool             │  What it solves                           │
├───────────────────┼───────────────────────────────────────────┤
│  React.memo()     │  Skip re-render if props unchanged        │
│  useCallback()    │  Stable function reference across renders │
│  useMemo()        │  Cache expensive calculation result       │
│  Code splitting   │  import() + React.lazy() + Suspense       │
│  Virtualization   │  react-window: render only visible items  │
└───────────────────┴───────────────────────────────────────────┘

useCallback example:
  const handleClick = useCallback(() => {
    doSomething(id);
  }, [id]);   ← only recreate if id changes
  → Child with React.memo() won't re-render unnecessarily

Context re-render fix:
  Split into multiple contexts (CountContext, ThemeContext)
  Memoize provider value: const val = useMemo(() => ({count}), [count])
  Consumer components wrapped in React.memo

Debouncing:
  Delay function execution until user STOPS typing
  setTimeout — reset timer on each keystroke
  Only fires after N ms of silence
  Use case: search-as-you-type API calls
```

---

## 35. N+1 Problem (JPA/Hibernate)

```
PROBLEM:
  departments = SELECT * FROM department  ← 1 query
  for each dept:
    SELECT * FROM employee WHERE dept_id = ?  ← N queries
  = N+1 total queries — terrible at scale

FIX 1: JPQL JOIN FETCH
  @Query("SELECT d FROM Department d JOIN FETCH d.employees")
  → 1 query with JOIN, loads everything at once

FIX 2: Change fetch type
  @OneToMany(fetch = FetchType.EAGER)
  → loads related data automatically in same query
  CAUTION: always loads even when not needed

FIX 3: EntityGraph (per-query control)
  @EntityGraph(attributePaths = {"employees"})

RULE: LAZY loading is default and usually right.
      Use JOIN FETCH when you know you need related data.
```

---

## Summary: The 10 Must-Know Diagrams

```
1. JVM Memory   → Heap (Young/Old) + Metaspace + Stack
2. String Pool  → SCP vs Heap, literal vs new String()
3. HashMap      → hash → bucket → LinkedList/Tree
4. Thread       → NEW → RUNNABLE → RUNNING → WAITING/BLOCKED → TERMINATED
5. Streams      → lazy pipeline, intermediate vs terminal
6. ACID         → Atomicity/Consistency/Isolation/Durability
7. Microservices→ API Gateway → services → own DBs
8. React        → JSX → VirtualDOM → Diffing → Real DOM
9. @Transactional → proxy wraps method → commit/rollback
10. Circuit Breaker → CLOSED → OPEN → HALF-OPEN
```
