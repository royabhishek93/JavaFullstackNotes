# Thread Creation, Lifecycle States, and Inter-Thread Communication (wait/notify)

## What is this? (Plain English)

Think of a thread like a new employee at a company. Before you hire them, they're just a candidate on paper (**NEW**) — they exist but haven't started work. Once they join and are assigned to a desk, they're ready to work and waiting for their turn on a shared resource, like a meeting room (**RUNNABLE**) — sometimes actually working (running), sometimes just waiting for their turn, and the manager (the CPU scheduler) keeps switching who gets the room. If the employee needs to wait for a locked filing cabinet that a colleague is using, or is waiting on a slow response from another department (a DB call), they're stuck idle (**BLOCKED**). If they explicitly say "page me when the report is ready" and stop working until then (**WAITING**), or they say "wake me up in exactly 10 minutes" (**TIMED_WAITING**), they're paused in different ways. Eventually, the task is done and they clock out for good (**TERMINATED**) — once done, they can't un-retire and resume the same job.

This note also covers two different ways to hire this "worker" (create a thread) — either give them a task sheet (implement `Runnable`) or directly make them a full-time internal employee (extend `Thread`) — and how two workers coordinate safely when sharing the same resource (monitor locks, `wait()`/`notify()`/`notifyAll()`).

## The Problem It Solves

Two related problems come up once you start using multiple threads:

1. **How do you actually create and start a thread**, especially when the class that needs threading capability might already extend some other parent class? Java doesn't allow multiple inheritance of classes, so you need a way to add "thread capability" to a class without forcing it to give up its existing parent class.
2. **Once threads exist, how do you know what state a thread is in at any point** (created but not started, actively competing for CPU, stuck waiting for a lock/IO, deliberately paused), and **how do two threads safely coordinate work on a shared object** (e.g., one thread produces data, another consumes it) without corrupting shared state or busy-waiting and wasting CPU?

## Two Ways to Create a Thread

Java provides two ways to create a thread, and this exists specifically because of Java's single-inheritance rule:

- If class `A` already extends some parent class, it **cannot** also extend `Thread` (a class can only extend one parent). But it **can** implement the `Runnable` interface, since a class can implement multiple interfaces.
- `Runnable` is a **functional interface** with a single abstract method `run()`. It is *not* itself a thread.
- The `Thread` class **implements `Runnable`** and additionally provides all the machinery to actually create, start, interrupt, and manage a thread's lifecycle. Its own `run()` implementation does nothing by itself — internally it does: `if (target != null) target.run();` where `target` is whatever `Runnable` object was passed into the `Thread` constructor.

**Approach 1 — implement `Runnable`:**
1. Create a class that implements `Runnable` and overrides `run()`.
2. Create an instance of that class (the runnable object).
3. Pass the runnable object into the `Thread` constructor.
4. Call `start()` on the `Thread` object.

**Approach 2 — extend `Thread`:**
1. Create a class that extends `Thread` and overrides `run()`.
2. Create an instance of that class — this object *is itself* a thread, so there's no need to wrap it in a separate `Thread` object.
3. Call `start()` directly on it.
4. If `run()` is not overridden, the inherited `Thread.run()` does nothing (unless a `Runnable` was passed to its constructor).

**Which one is preferred in industry?** The `Runnable` interface approach is generally preferred in production code, because it keeps the class free to extend some other parent class and implement other interfaces — i.e., it doesn't burn the class's one shot at inheritance just to get threading capability. Directly extending `Thread` works but locks the class out of extending anything else.

## Java Thread Lifecycle (State Machine)

Based strictly on what the states and transitions mean here:

- **NEW**: the `Thread` object has been created (`new Thread(...)`) but `start()` has not been called yet — it's just an object in memory.
- **RUNNABLE**: after `start()` is called. This single state actually covers two informal sub-conditions that keep switching via context switching:
  - *runnable* — waiting for the CPU to give it time.
  - *running* — currently has the CPU and is executing.
- **BLOCKED**: the thread is waiting to acquire a lock held by another thread, or waiting on an I/O operation (e.g., reading from a file or a database). All monitor locks are released while blocked. Once the resource/lock becomes available, it goes back to RUNNABLE.
- **WAITING**: the thread explicitly called `wait()`. It stays here indefinitely, releasing all monitor locks, until another thread calls `notify()`/`notifyAll()` on the same object — then it goes back to RUNNABLE.
- **TIMED_WAITING**: the thread called `sleep(time)` (a time-bound wait). No monitor locks are released during this state. Once the given time elapses, it automatically goes back to RUNNABLE.
- **TERMINATED**: the thread's `run()` has completed (or it was otherwise stopped). This is final — a terminated thread cannot be restarted or go back to RUNNABLE. A thread can be stopped/terminated at any point in its life.

```
 Initial: [*] --> NEW  (new Thread(...))

 From            Trigger                                                    To
 ─────────────   ──────────────────────────────────────────────────────   ────────────────
 NEW             start()                                                     RUNNABLE
 RUNNABLE        scheduler context-switches (runnable <-> running)          RUNNABLE (self)
 RUNNABLE        waiting for I/O (file/DB read) or waiting to acquire a     BLOCKED
                 locked resource
 BLOCKED         I/O completes / lock acquired (locks released while         RUNNABLE
                 blocked)
 RUNNABLE        wait() called (releases all monitor locks)                 WAITING
 WAITING         notify() / notifyAll() called                              RUNNABLE
 RUNNABLE        sleep(time) called (monitor locks NOT released)            TIMED_WAITING
 TIMED_WAITING   sleep duration elapses                                     RUNNABLE
 RUNNABLE        run() completes                                            TERMINATED
 NEW             thread stopped before starting                            TERMINATED
 BLOCKED         thread stopped                                             TERMINATED
 WAITING         thread stopped                                             TERMINATED
 TIMED_WAITING   thread stopped                                             TERMINATED
 TERMINATED      (final state)                                              [*]
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Monitor Locks (Intrinsic Locks)

A **monitor lock** ensures only one thread can execute inside a `synchronized` method or block **on a given object** at a time:

- `synchronized` puts the lock **on the object being invoked on**, not on the method itself. So if `thread1` and `thread2` both call a synchronized method on the *same* object instance, only one of them proceeds at a time — the other waits until the first releases the lock (i.e., exits the synchronized method/block).
- If `thread1` and `thread2` instead call the same synchronized method on **two different object instances**, there is no contention at all — each object has its own independent monitor lock, so both threads can run concurrently.
- This matters specifically when multiple threads are working on a truly **shared resource** (the same object reference). If they're working on separate objects, synchronization on that object doesn't protect anything meaningful between them.

Monitor lock behavior across states:
- **BLOCKED**: all monitor locks are released.
- **WAITING** (via `wait()`): all monitor locks are released.
- **TIMED_WAITING** (via `sleep()`): monitor locks are **not** released.

## Key Code / Config

### 1. Creating a thread with `Runnable`

```java
class MultiThreadingLearning implements Runnable {
    @Override
    public void run() {
        System.out.println("Code executed by thread: " + Thread.currentThread().getName());
    }
}

public class RunnableDemo {
    public static void main(String[] args) {
        System.out.println("Main thread: " + Thread.currentThread().getName());

        Runnable runnableObject = new MultiThreadingLearning();
        Thread thread = new Thread(runnableObject); // thread is NEW here
        thread.start();                             // thread moves to RUNNABLE; internally calls run()
    }
}
```

### 2. Creating a thread by extending `Thread`

```java
class MultiThreadingLearning extends Thread {
    @Override
    public void run() {
        System.out.println("Code executed by thread: " + Thread.currentThread().getName());
    }
}

public class ThreadSubclassDemo {
    public static void main(String[] args) {
        System.out.println("Main thread: " + Thread.currentThread().getName());

        MultiThreadingLearning thread = new MultiThreadingLearning(); // already IS a Thread
        thread.start(); // no separate Thread object needed
    }
}
```

### 3. Monitor lock demonstration (synchronized method vs synchronized block vs no sync)

```java
class MonitorLockExample {
    public synchronized void task1() throws InterruptedException {
        Thread.sleep(10000); // holds the monitor lock for the full 10s (sleep does not release it)
        System.out.println("Task 1 completed");
    }

    public void task2() {
        System.out.println("Before synchronized"); // prints immediately, no lock needed yet
        synchronized (this) {
            System.out.println("Task 2 completed");
        }
    }

    public void task3() {
        System.out.println("Task 3 completed"); // no synchronization at all
    }
}

public class MonitorLockDemo {
    public static void main(String[] args) {
        MonitorLockExample obj = new MonitorLockExample(); // same object shared by all 3 threads

        Thread thread1 = new Thread(() -> {
            try { obj.task1(); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        });
        Thread thread2 = new Thread(obj::task2);
        Thread thread3 = new Thread(obj::task3);

        thread1.start(); // acquires monitor lock on obj, sleeps 10s while holding it
        thread2.start(); // prints "Before synchronized" immediately, then blocks waiting for obj's lock
        thread3.start(); // prints immediately, unaffected since it needs no lock

        // After 10s, thread1 releases the lock; only then does thread2 enter its synchronized block.
    }
}
```

### 4. Producer–consumer coordination with `wait()` / `notifyAll()`

```java
class SharedResource {
    private boolean itemAvailable = false;

    public synchronized void addItem() {
        itemAvailable = true;
        notifyAll(); // wake up any thread waiting on this object
    }

    public synchronized void consumeItem() throws InterruptedException {
        while (!itemAvailable) {   // "while", not "if" -- guards against spurious wakeup
            wait();                 // releases the monitor lock while waiting
        }
        itemAvailable = false;
    }
}

class ProduceTask implements Runnable {
    private final SharedResource sharedResource;
    ProduceTask(SharedResource sharedResource) { this.sharedResource = sharedResource; }

    @Override
    public void run() {
        try {
            System.out.println("Producer thread: " + Thread.currentThread().getName());
            Thread.sleep(2000); // simulate delay before producing
            sharedResource.addItem();
            System.out.println("Producer thread calling notify");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}

class ConsumeTask implements Runnable {
    private final SharedResource sharedResource;
    ConsumeTask(SharedResource sharedResource) { this.sharedResource = sharedResource; }

    @Override
    public void run() {
        try {
            System.out.println("Consumer thread: " + Thread.currentThread().getName());
            System.out.println("Consumer thread waiting");
            sharedResource.consumeItem();
            System.out.println("Consumer thread consumed the item");
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}

public class ProducerConsumerDemo {
    public static void main(String[] args) {
        SharedResource sharedResource = new SharedResource();

        Thread producerThread = new Thread(new ProduceTask(sharedResource));
        Thread consumerThread = new Thread(new ConsumeTask(sharedResource));

        consumerThread.start(); // runs first, finds itemAvailable=false, calls wait() (releases lock)
        producerThread.start(); // sleeps 2s, then addItem() acquires the lock and calls notifyAll()
        // Consumer wakes, re-checks the while condition, sees itemAvailable=true, and proceeds.
    }
}
```

**Why check the condition in a `while` loop instead of `if`?** Per the Oracle documentation, a waiting thread can occasionally wake up without `notify()`/`notifyAll()` ever being called (a **spurious wakeup**, sometimes caused by system-level noise). Using `while` re-checks the actual condition after waking up, so the thread only proceeds once the condition genuinely holds — `if` would proceed blindly after any wakeup, spurious or not.

## Deprecated Methods (noted, not covered in depth here)

`Thread.stop()`, `suspend()`, and `resume()` are deprecated methods on `Thread`. The transcript flags this as an important point to understand — since these are deprecated, thread termination has to be done differently — but the actual replacement mechanism is left as a topic for the next session and an assignment (implementing a bounded-buffer producer-consumer using a queue) was given for practice before that.

## Interview Q&A

**Q1: Why does Java provide two different ways to create a thread (implementing `Runnable` vs extending `Thread`)?**
Because Java only allows single inheritance of classes. If a class already extends some other parent, it cannot also extend `Thread`. But it can still implement `Runnable` (a functional interface), since interfaces support multiple implementation. Java gives both options so that any class — regardless of what it already extends — can still gain threading capability.

**Q2: Which approach is preferred in real projects, and why?**
Implementing `Runnable` is generally preferred. It keeps the class free to extend another parent class and implement other interfaces, i.e., it doesn't use up the class's single inheritance slot just for threading. Extending `Thread` directly works but permanently locks that class out of extending anything else.

**Q3: What actually happens internally when you call `thread.start()`?**
`start()` triggers the thread to move to the RUNNABLE state and internally invokes `run()`. If the thread was constructed by passing a `Runnable` into the `Thread` constructor, `Thread`'s own `run()` implementation checks `if (target != null) target.run();` and delegates to that runnable's `run()` method. If you extended `Thread` directly and overrode `run()`, your override runs instead.

**Q4: What's the difference between the BLOCKED and WAITING states?**
BLOCKED happens implicitly — the thread is waiting on an I/O operation (like a DB/file read) or waiting to acquire a lock that another thread currently holds; it returns to RUNNABLE automatically once the resource/lock is free. WAITING happens because the thread explicitly called `wait()`; it stays there indefinitely and only returns to RUNNABLE when another thread calls `notify()`/`notifyAll()` on the same object. Both release all monitor locks while in that state.

**Q5: Does `sleep()` release the monitor lock? Does `wait()`?**
No — `sleep()` puts the thread into TIMED_WAITING but it keeps holding any monitor lock it already has. `wait()`, on the other hand, releases all monitor locks held on that object while the thread waits, which is what allows another thread to acquire the lock and eventually call `notify()`/`notifyAll()`.

**Q6: What is a monitor lock, and why does it matter which object two threads are synchronizing on?**
A monitor lock is tied to a specific object instance. `synchronized` ensures only one thread can execute a synchronized method/block on that same object at a time — the second thread has to wait until the first releases the lock. If two threads instead operate on two different object instances, each object has its own independent monitor lock, so there's no contention between them at all — synchronization only protects a genuinely shared object.
