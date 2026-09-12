# Lock-Free Concurrency in Java — Compare-And-Swap, Atomic Classes, and volatile

## What is this? (Plain English)

Imagine a whiteboard with a single number written on it, and two people want to update it — but there's no locked room, no queue, no "wait your turn." Instead, each person works like this:

1. Peek at the number currently on the board.
2. Work out, in their head, what the new number should be.
3. Walk up to the board and check: *"Is the number still what I peeked at a moment ago?"*
4. If yes — erase it and write the new number. Done.
5. If no (someone else changed it in between) — don't argue, don't wait. Just peek again, recompute, and retry.

Nobody ever blocks anybody else out of the room. There's no lock at all — just a very fast "check-and-update" step that either succeeds immediately or gets retried. That's exactly what **Compare-And-Swap (CAS)** is: a CPU-level operation that lets a thread update a shared value only if nobody else has changed it since the thread last looked — and if someone did, the thread just loops and tries again. Java's `Atomic*` classes (`AtomicInteger`, `AtomicBoolean`, `AtomicLong`, `AtomicReference`) are built directly on top of this CPU operation, giving you thread-safe updates **without ever using a lock**.

## The Problem It Solves

There are two ways to achieve concurrency in Java:

1. **Lock-based mechanism** — `synchronized`, `ReentrantLock`, `ReadWriteLock`, `Semaphore`, etc. Only one thread is allowed inside the critical section at a time; every other thread has to wait (block) until the lock is released.
2. **Lock-free mechanism** — no locks at all. Threads coordinate using an atomic, CPU-supported retry loop instead of blocking each other.

Lock-based mechanisms are necessary and correct for complex business logic with multiple steps, but they come with **contention overhead** — threads get blocked, parked, and later woken up by the OS/JVM, which costs time whenever many threads compete for the same lock.

Lock-free mechanisms remove that blocking overhead entirely, but only work for a **narrow, specific use case**: simple **"read → modify → update"** operations on a single shared variable (like incrementing a counter). It is *not* a general replacement for lock-based concurrency — for anything more complex than a simple read-modify-write, you still need locks. Where it does apply, it is faster than lock-based approaches because no thread ever waits idle for another to finish; it just recomputes and retries.

This lock-free approach is powered by **Compare-And-Swap (CAS)**, an atomic operation implemented directly in modern CPUs. "Atomic" here means the operation executes as a single, indivisible unit — no matter how many CPU cores exist and no matter how many threads run in parallel, the CPU guarantees that only one thread's CAS attempt can succeed at any given instant.

CAS takes three inputs:
- **Memory location** — where the shared variable lives.
- **Expected value** — what the thread believes the current value is (read moments earlier).
- **New value** — what the thread wants to write.

CAS then does, as one indivisible step:
1. **Load** the current value from memory.
2. **Compare** it against the expected value.
3. If they match → **update** memory with the new value (success). If they don't match → do nothing (fail), because someone else already changed it.

This is conceptually identical to **optimistic concurrency control** used with databases: a row has a `row_version` column; a thread reads the row along with its version, computes its change, then runs an `UPDATE ... WHERE row_version = <version it read>`. If another thread already updated the row (and bumped its version) in the meantime, the `WHERE` clause matches zero rows, the update fails, and the thread must re-read the (now newer) version and retry. CAS is the same idea, just implemented as a raw CPU instruction operating on memory instead of a SQL `UPDATE` operating on a database row.

## How Compare-And-Swap (CAS) Works — The Retry Loop

```
 ┌──────────────────────────────┐
 │ Read current value from memory  │<────────────────────────────────┐
 └──────────────────────────────┘                                    │
              v                                                     │
 ┌─────────────────────────────────┐                                    │
 │ Compute new value (e.g. current + 1)  │                            │
 └────────────────────────┬───────────────┘                                    │
              v                                                     │
 ┌──────────────────────────────────────────────┐                          │
 │ CAS(memory, expected, new)             │                          │
 │ compare memory value == expected?      │                          │
 └────────────────────────────────────┬───────────────────────────┘
   Match: update succeeds │                          No match: someone else
                          v                          already changed it
           ┌─────────────────────────┐      ┌───────────────────────────────┐
           │ Memory updated to new value │      │ CAS fails, no update happens │
           └─────────────┬─────────────┘      └───────────────────────────────┘
                       v                                                (loops back to "Read current value")
           ┌────────────────────┐
           │   Return success       │
           └────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

Worked example from the video: two threads both read `counter = 0` from memory (both have `expected = 0`). CAS is itself atomic, so only one thread can actually execute the compare-and-update step at a time:
- **Thread 1** goes first: compares its expected `0` against memory `0` → matches → memory updated to `1`. Success.
- **Thread 2** goes next: compares its expected `0` against memory (now `1`) → **no match** → CAS fails, returns `false`.
- Thread 2 does **not** give up — it loops: re-reads memory (`1`), sets `expected = 1`, computes new value `2`, retries CAS → now `1 == 1` → matches → memory updated to `2`. Success.

### The ABA Problem (and how it's fixed)

A subtle issue with CAS: suppose memory holds `10`. A thread reads it, planning to CAS it from `10` → `13`. But in between the thread's read and its CAS attempt, some other thread(s) change the value from `10` → `12` → back to `10`. When the first thread finally runs its CAS, it checks "is memory still `10`?" — yes, it is — so the CAS **succeeds**, even though the value was actually modified twice in between. The thread has no way of knowing the value moved away and came back — this is the **ABA problem**.

The fix is to attach a **version number (or timestamp)** alongside the value. Each change increments the version, so:
- `10` written with version `1`
- `12` written with version `2`
- `10` written again, but now with version `3`

A thread expecting `(value=10, version=1)` will **not** match `(value=10, version=3)`, even though the raw value looks the same — so the CAS correctly fails and the thread re-reads and retries.

## Key Code / Config

### 1. Why a simple counter increment is NOT atomic

```java
public class SharedResource {
    private int counter;

    public void increment() {
        counter++; // looks like one operation, but it isn't
    }

    public int get() {
        return counter;
    }
}
```

`counter++` is actually three separate steps under the hood:

```java
// counter++ is equivalent to:
int temp = counter;   // 1. load current value
temp = temp + 1;      // 2. increment it
counter = temp;       // 3. assign it back
```

These three steps are **not atomic**. With a single thread calling `increment()` 400 times, the result is correctly `400`. But split the same 400 calls across **two threads** (200 calls each, running in parallel):

```java
SharedResource resource = new SharedResource();

Runnable task = () -> {
    for (int i = 0; i < 200; i++) {
        resource.increment();
    }
};

Thread t1 = new Thread(task);
Thread t2 = new Thread(task);
t1.start();
t2.start();
t1.join();
t2.join();

System.out.println(resource.get()); // expected 400, but actual run printed 371
```

Because both threads can load the *same* current value before either one writes back its incremented result, updates get silently lost — this is a classic race condition, and it happened here because `counter++` is not a single atomic unit.

### 2. Fix option 1 — lock-based (`synchronized`)

```java
public class SharedResource {
    private int counter;

    public synchronized void increment() {
        counter++;
    }

    public int get() {
        return counter;
    }
}
```

Only one thread can be inside `increment()` at a time; every other thread blocks until it finishes. This is correct but pays the cost of thread blocking/contention.

### 3. Fix option 2 — lock-free (`AtomicInteger`, internally uses CAS)

```java
import java.util.concurrent.atomic.AtomicInteger;

public class SharedResource {
    private final AtomicInteger counter = new AtomicInteger(0);

    public void increment() {
        counter.incrementAndGet(); // increments by 1, using CAS internally
    }

    // to increment/decrement by an arbitrary amount:
    public void incrementBy(int delta) {
        counter.addAndGet(delta);
    }

    public int get() {
        return counter.get();
    }
}
```

`AtomicInteger` (and `AtomicBoolean`, `AtomicLong`, `AtomicReference` for arbitrary objects) fit the **"read → modify → update"** use case exactly — the one narrow scenario where lock-free CAS applies. Internally, `incrementAndGet()` runs a loop conceptually equivalent to:

```java
// Conceptual reconstruction of what incrementAndGet() does internally,
// using the public compareAndSet(expected, new) API directly:
public int incrementAndGetManually(AtomicInteger counter) {
    while (true) {
        int current = counter.get();       // 1. read current value from memory
        int updated = current + 1;         // 2. compute new value
        if (counter.compareAndSet(current, updated)) { // 3. CAS attempt
            return updated;                // success — new value applied
        }
        // failure: someone else changed it first — loop and retry
    }
}
```

Since this is lock-free, no thread ever blocks waiting for another — a thread whose CAS fails simply re-reads and retries immediately.

### 4. `volatile` — visibility, not atomicity

Each CPU core has its own local caches (L1, L2) sitting in front of main memory. Normally, a write by one thread on one core may only land in that core's local cache and take time to propagate to main memory / other cores' caches — so another thread reading the same variable on a different core could see a **stale** value.

```java
public class VolatileExample {
    private volatile boolean running = true; // marked volatile

    public void stop() {
        running = false; // write goes straight to main memory, not just a local cache
    }

    public void run() {
        while (running) { // read goes straight to main memory, not a stale cached copy
            // do work
        }
    }
}
```

Declaring a variable `volatile` forces **every read and every write to go directly to main memory**, bypassing the CPU-local caches. This guarantees that a change made by one thread becomes immediately visible to every other thread.

Important distinction the video specifically calls out: **`volatile` has no relation to thread safety or atomicity.** It only guarantees *visibility* of the latest value across threads — it does nothing to make a multi-step operation like `counter++` atomic. Atomicity/thread-safety for a compound operation still requires either a lock (`synchronized`) or a CAS-based `Atomic*` class. (Internally, the `value` field inside `AtomicInteger` is itself declared `volatile`, so reads always see the latest memory value — but it's the CAS operation, not the `volatile` modifier, that provides atomicity.)

### 5. Concurrent collections — quick recap

Java's concurrent collections use either lock-based or lock-free (CAS) internals depending on the data structure:

| Collection | Concurrency mechanism |
|---|---|
| `PriorityBlockingQueue` | Lock-based — uses `ReentrantLock` internally |
| `ConcurrentLinkedDeque` / `ConcurrentLinkedQueue` | Lock-free — uses CAS internally (e.g. `casNext`) to link nodes |

Same pattern as everything above: some concurrent collections pick locks, others pick CAS, depending on which fits their access pattern.

## Interview Q&A

**Q1: Why isn't `counter++` atomic, even though it's a single line of code?**
A: It compiles down to three separate steps — load the current value, increment it, and write it back. Two threads can both load the same value before either writes back, so an update from one thread can be silently lost. A single line of source code is not the same thing as a single atomic CPU operation.

**Q2: How does `AtomicInteger` achieve thread safety without using a lock?**
A: It uses the CPU's Compare-And-Swap (CAS) instruction, which is atomic in hardware — no matter how many cores are running threads in parallel, only one thread's compare-and-update can succeed at a time. A thread whose CAS attempt fails (because the value changed since it last read it) simply re-reads the current value and retries, instead of blocking.

**Q3: When should you use `Atomic*` classes instead of `synchronized`, and when should you not?**
A: Use `Atomic*` classes only for the narrow "read → modify → update" case on a single variable, like a counter — it's faster because no thread ever blocks. For anything with more complex, multi-step business logic touching multiple variables/objects, lock-free CAS doesn't fit; you need `synchronized`/`ReentrantLock` instead. Lock-free is not a general replacement for locks, just an alternative for this specific use case.

**Q4: What is the ABA problem in CAS, and how is it fixed?**
A: A thread reads a value (say `10`), intending to CAS it to a new value later. In between, other threads change it `10 → 12 → 10`. When the first thread finally runs its CAS, the value looks unchanged (`10`), so the CAS succeeds — even though it actually changed twice in between, which can hide bugs. It's fixed by attaching a version number/timestamp to the value, so `(10, version 1)` and `(10, version 3)` are treated as different states even though the raw value matches.

**Q5: Does marking a variable `volatile` make compound operations like `counter++` thread-safe?**
A: No. `volatile` only guarantees that reads and writes go directly to main memory (visibility across threads) — it has no relation to atomicity or thread safety. `counter++` is still three separate steps and can still race even if `counter` is `volatile`. For atomic increments you need `AtomicInteger` (CAS) or a lock.

**Q6: How is CAS related to optimistic locking used with databases?**
A: They're the same idea at different layers. In DB optimistic concurrency control, a thread reads a row along with its `row_version`, computes a change, then runs `UPDATE ... WHERE row_version = <version read>`; if another transaction already changed the row (bumping the version), the update matches zero rows and the thread must re-read and retry. CAS does the identical "read → compare expected vs. current → update if matched" dance, except it operates on a CPU-level memory location instead of a database row.
