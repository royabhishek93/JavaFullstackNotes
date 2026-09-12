# Multithreading Part 4 — ReentrantLock, ReadWriteLock, StampedLock, and Semaphore

## What is this? (Plain English)

`synchronized` puts a **monitor lock on an object**. That's fine as long as every thread that needs to be mutually exclusive is locking on the *same* object. But real applications don't always work that way — different threads can be holding references to different objects entirely, yet you still need only one of them at a time to run a piece of code.

Think of it like a single toilet key at a gas station versus a general "one person at a time" rule enforced by a bouncer who doesn't care which car you drove in. `synchronized` is the toilet key tied to a specific car (object) — if two people arrive in different cars, both can use the toilet at once, defeating the purpose. A `Lock` object (`ReentrantLock`, `ReadWriteLock`, etc.) is the bouncer: he doesn't care what object/car you came with, he only cares about the single `Lock` instance you were told to check in with.

Java gives four kinds of these explicit locks: **Reentrant, ReadWrite, Semaphore, and StampedLock**. None of them depend on the object calling them — they depend only on the lock instance you pass around.

## The Problem It Solves

**Limitation of `synchronized`:** the monitor lock is tied to an object. If `Thread 1` calls a synchronized method on `object1` and `Thread 2` calls the same synchronized method on `object2`, both threads get their *own* monitor lock and both run concurrently — even though the requirement was "only one thread should ever be inside this critical section, no matter which object it came through."

`ReentrantLock` solves this: it is a standalone lock object you create once and pass to every thread. Locking/unlocking happens on that lock object, not on whatever object happens to be calling the method — so mutual exclusion holds even across different object instances.

Beyond plain mutual exclusion, three more specialized needs come up:
- **Read-heavy workloads** — if a resource is read far more often than it's written, forcing every reader to fully exclude every other reader (as a plain lock would) wastes concurrency. `ReadWriteLock` allows many concurrent readers, but a writer still needs exclusive access.
- **Avoiding the cost of locking entirely when contention is rare** — `StampedLock` adds an *optimistic read* mode: no lock is actually taken; you just remember a "version stamp" and validate afterward that nobody wrote in the meantime.
- **Allowing more than one thread into a section, up to a fixed capacity** — e.g., a pool of 2 printers or 5 DB connections. `Semaphore` lets you configure exactly how many threads (permits) can be inside a critical section simultaneously.

## Shared Lock vs Exclusive Lock

Before `ReadWriteLock` makes sense, two underlying concepts:

- **Shared lock (a.k.a. read lock):** Any number of threads can hold a shared lock on the same resource at the same time. It only permits *reading*, not writing.
- **Exclusive lock (a.k.a. write lock):** Only one thread can hold it, and only when **no other lock — shared or exclusive — is currently held** on that resource. It permits both reading and writing.

Rules:
- If a shared lock is already held by any thread, no other thread can acquire an exclusive lock until all shared locks are released.
- If an exclusive lock is held by a thread, no other thread — not even for a shared/read lock — can acquire anything until it is released.
- Multiple threads can simultaneously hold shared locks on the same resource.

## Lock Acquisition / Release Flow (ReentrantLock)

```
            ┌─────────────────────┐
     ┌──>│ Thread calls lock.lock()│
     │  └────────────┬───────────┘
     │              v
     │  ┌─────────────────────┐
     │  │   Is lock free?   │
     │  └───┬────────────┬────┘
     │     No │           │ Yes
     │        v           v
     │  ┌────────────────┐  ┌───────────────────────────┐
     └───┤ Thread blocks/waits │  │ Lock acquired - enter    │
        └───────────────┘  │ critical section (try)  │
                                     └──────────┬─────────┘
                                                v
                                     ┌──────────────────┐
                                     │ finally: lock.unlock() │
                                     └─────────────┬─────────┘
                                                v
                          ┌─────────────────────────────────┐
                          │ Lock released - next waiting     │
                          │ thread may acquire (back to      │
                          │ "Is lock free?")                 │
                          └─────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## ReadWriteLock Concurrency: Multiple Readers vs Exclusive Writer

```
Shared state: no lock held
  [Resource free] (S0)

  S0 --[Thread A: readLock().lock()]--> [Read lock held by A] (RA)
  RA --[Thread B: readLock().lock() -> allowed]--> [Read lock held by A and B, concurrent reads OK] (RAB)
  RAB --[Thread C: writeLock().lock() -> BLOCKED, stays at RAB]
  RAB --[A and B: readLock().unlock()]--> S0
  S0  --[Thread C: writeLock().lock()]--> [Write lock held by C, exclusive] (WC)
  WC  --[Any other thread: readLock or writeLock -> BLOCKED, stays at WC]
  WC  --[C: writeLock().unlock()]--> S0
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

**When to use `ReadWriteLock`:** when reads vastly outnumber writes (e.g., thousands of reads vs. tens of writes). Letting all readers proceed concurrently, and only serializing the rare writes, gives much better throughput than a single exclusive lock for everything.

## Key Code / Config

### 1. Why `synchronized` fails across different objects

```java
class SharedResource {
    public synchronized void producer(int threadId) throws InterruptedException {
        System.out.println("Lock acquired by thread " + threadId);
        Thread.sleep(4000);
        System.out.println("Lock released by thread " + threadId);
    }
}

public class SynchronizedProblemDemo {
    public static void main(String[] args) {
        SharedResource resource1 = new SharedResource();
        SharedResource resource2 = new SharedResource();

        // Different objects -> different monitor locks -> BOTH run concurrently.
        new Thread(() -> {
            try { resource1.producer(0); } catch (InterruptedException e) { }
        }).start();

        new Thread(() -> {
            try { resource2.producer(1); } catch (InterruptedException e) { }
        }).start();
    }
}
```

### 2. `ReentrantLock` — mutual exclusion independent of the calling object

```java
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

class SharedResource {
    public void producer(Lock lock, int threadId) throws InterruptedException {
        lock.lock();
        try {
            System.out.println("Lock acquired by thread " + threadId);
            Thread.sleep(4000);
        } finally {
            lock.unlock();
            System.out.println("Lock released by thread " + threadId);
        }
    }
}

public class ReentrantLockDemo {
    public static void main(String[] args) {
        Lock lock = new ReentrantLock();

        SharedResource resource1 = new SharedResource(); // different objects...
        SharedResource resource2 = new SharedResource(); // ...same lock

        new Thread(() -> {
            try { resource1.producer(lock, 0); } catch (InterruptedException e) { }
        }).start();

        new Thread(() -> {
            try { resource2.producer(lock, 1); } catch (InterruptedException e) { }
        }).start();
        // Even with different objects, only one thread is inside the critical
        // section at a time, because both are locking on the same Lock instance.
    }
}
```

### 3. `ReadWriteLock` — concurrent readers, exclusive writer

```java
import java.util.concurrent.locks.ReadWriteLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;

class SharedResource {
    public void producer(ReadWriteLock lock, int threadId) throws InterruptedException {
        lock.readLock().lock(); // shared lock - only reads
        try {
            System.out.println("Read lock acquired by thread " + threadId);
            Thread.sleep(8000);
        } finally {
            lock.readLock().unlock();
            System.out.println("Read lock released by thread " + threadId);
        }
    }

    public void consumer(ReadWriteLock lock, int threadId) throws InterruptedException {
        lock.writeLock().lock(); // exclusive lock - reads + writes
        try {
            System.out.println("Write lock acquired by thread " + threadId);
        } finally {
            lock.writeLock().unlock();
            System.out.println("Write lock released by thread " + threadId);
        }
    }
}

public class ReadWriteLockDemo {
    public static void main(String[] args) {
        ReadWriteLock lock = new ReentrantReadWriteLock();
        SharedResource resource = new SharedResource();

        // Thread 1 and Thread 2 both take the READ lock -> both proceed concurrently.
        new Thread(() -> {
            try { resource.producer(lock, 0); } catch (InterruptedException e) { }
        }).start();

        new Thread(() -> {
            try { resource.producer(lock, 1); } catch (InterruptedException e) { }
        }).start();

        // Thread 3 wants the WRITE lock -> must wait until BOTH read locks are released.
        new Thread(() -> {
            try { resource.consumer(lock, 2); } catch (InterruptedException e) { }
        }).start();
    }
}
```

### 4. `StampedLock` — read/write locking plus optimistic reads

Pessimistic locks (`synchronized`, `ReentrantLock`, `ReadWriteLock`) always take an actual lock before proceeding. Optimistic locking takes **no lock at all**; it works the way DB optimistic concurrency control does — using a **row version number**:

- Every row starts at `version = 1`.
- On read, a thread remembers the version it saw.
- On update, the thread issues `UPDATE ... WHERE id = ? AND version = <version it saw>` and simultaneously increments the version.
- If another thread updated the row in between, the version no longer matches, the update fails/rolls back, and the thread must re-read and retry.

`StampedLock` provides this exact idea via a "stamp" (an internal version-like token):

```java
import java.util.concurrent.locks.StampedLock;

class SharedResource {
    private final StampedLock lock = new StampedLock();
    private int value = 10;

    // Read/write lock style usage - same shape as ReadWriteLock, but every
    // lock/unlock call passes a "stamp" that represents the lock's state.
    public void readWithLock() throws InterruptedException {
        long stamp = lock.readLock();
        try {
            System.out.println("Read lock acquired, value = " + value);
        } finally {
            lock.unlockRead(stamp);
        }
    }

    public void writeWithLock() {
        long stamp = lock.writeLock();
        try {
            value = 11;
            System.out.println("Write lock acquired, updated value");
        } finally {
            lock.unlockWrite(stamp); // internally advances the stamp/version
        }
    }

    // Optimistic read: no lock taken at all, only the current stamp is captured.
    public void optimisticUpdate() throws InterruptedException {
        long stamp = lock.tryOptimisticRead(); // no lock acquired
        int localValue = value;
        localValue = localValue + 1; // pretend work: 10 -> 11

        Thread.sleep(6000); // simulate time doing work

        if (!lock.validate(stamp)) {
            // Some other thread took a WRITE lock in the meantime -> stamp is stale.
            System.out.println("Validation failed - rolling back, re-read and retry");
        } else {
            value = localValue;
            System.out.println("Validation succeeded - update applied: " + value);
        }
    }
}
```

`lock.validate(stamp)` returns `false` if any write lock was acquired (and released) since the stamp was taken — that's how the optimistic read detects a concurrent modification without ever blocking.

### 5. `Semaphore` — allow N threads into a critical section

```java
import java.util.concurrent.Semaphore;

class SharedResource {
    public void producer(Semaphore semaphore, int threadId) throws InterruptedException {
        semaphore.acquire();
        try {
            System.out.println("Lock acquired by thread " + threadId);
            Thread.sleep(4000);
        } finally {
            semaphore.release();
            System.out.println("Lock released by thread " + threadId);
        }
    }
}

public class SemaphoreDemo {
    public static void main(String[] args) {
        Semaphore semaphore = new Semaphore(2); // only 2 permits -> 2 threads at a time
        SharedResource resource = new SharedResource();

        for (int i = 0; i < 4; i++) {
            int threadId = i;
            new Thread(() -> {
                try { resource.producer(semaphore, threadId); } catch (InterruptedException e) { }
            }).start();
        }
        // Threads 0 and 1 acquire immediately; threads 2 and 3 wait until a
        // permit is released. Typical use cases: a pool of printers, or a
        // fixed-size DB connection pool.
    }
}
```

### 6. `Condition` — inter-thread communication without a monitor lock

`wait()`/`notify()`/`notifyAll()` only work with `synchronized`'s monitor lock. Once you switch to `ReentrantLock`/`ReadWriteLock`/`StampedLock`, there is no monitor lock to wait/notify on — so each `Lock` exposes a `Condition` object instead, with equivalent methods: `await()` (= `wait()`), `signal()` (= `notify()`), `signalAll()` (= `notifyAll()`).

```java
import java.util.concurrent.locks.Condition;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;

class SharedResource {
    private final Lock lock = new ReentrantLock();
    private final Condition condition = lock.newCondition();
    private boolean available = false;

    public void produce() throws InterruptedException {
        lock.lock();
        try {
            while (available) {
                condition.await(); // equivalent to wait()
            }
            available = true;
            System.out.println("Produced");
            condition.signal(); // equivalent to notify() - wake the consumer
        } finally {
            lock.unlock();
        }
    }

    public void consume() throws InterruptedException {
        lock.lock();
        try {
            while (!available) {
                condition.await();
            }
            available = false;
            System.out.println("Consumed");
            condition.signal(); // wake the producer
        } finally {
            lock.unlock();
        }
    }
}
```

## Interview Q&A

**Q1: Why doesn't `synchronized` work if two threads call the same synchronized method but through two different object instances?**
A: `synchronized` acquires a monitor lock tied to the specific object instance. Two different instances have two different monitor locks, so both threads acquire their own lock and run concurrently — there's no cross-object mutual exclusion. `ReentrantLock` fixes this because the lock is a standalone object you explicitly pass around, independent of whichever object is calling the method.

**Q2: What's the difference between a shared lock and an exclusive lock?**
A: A shared (read) lock can be held by multiple threads at once, but only permits reading. An exclusive (write) lock can be held by only one thread, requires that no other lock (shared or exclusive) is currently held, and permits both reading and writing.

**Q3: When would you choose `ReadWriteLock` over a plain `ReentrantLock`?**
A: When reads vastly outnumber writes. A plain lock forces every access — even simple reads — to be fully serialized. `ReadWriteLock` lets any number of readers proceed concurrently and only forces writers to wait for exclusive access, which gives much better throughput in read-heavy workloads.

**Q4: How does `StampedLock`'s optimistic read differ from its read lock, and how does `validate()` work?**
A: The read lock (`readLock()`) is a real shared lock — it still blocks writers and returns a stamp, but the stamp isn't very useful there. The optimistic read (`tryOptimisticRead()`) takes **no lock at all** — it just captures the current stamp (an internal version marker). After doing work, you call `lock.validate(stamp)`; if any thread took a write lock in between, the stamp is now stale and `validate()` returns `false`, meaning you must roll back and retry. This mirrors DB optimistic locking, which checks a row-version column before committing an update.

**Q5: What problem does `Semaphore` solve that `ReentrantLock` cannot?**
A: `ReentrantLock` only ever allows one thread into a critical section. `Semaphore` is constructed with a number of permits, allowing exactly that many threads to be inside the critical section concurrently. Typical uses are capping concurrent access to a limited pool of resources — e.g., 2 printers, or a fixed-size database connection pool — where more than the pool size simply cannot be served at once.

**Q6: If you're using `ReentrantLock` instead of `synchronized`, how do you replicate `wait()`/`notify()` behavior for inter-thread communication?**
A: You create a `Condition` from the lock via `lock.newCondition()`, and use `condition.await()` in place of `wait()`, `condition.signal()` in place of `notify()`, and `condition.signalAll()` in place of `notifyAll()`. The semantics are identical — the only difference is that they operate on the explicit `Lock`/`Condition` pair rather than an object's intrinsic monitor lock.
