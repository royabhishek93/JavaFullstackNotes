# Thread Control in Java: Deprecated stop()/suspend()/resume(), Thread Joining, Priority, and Daemon Threads

## What is this? (Plain English)

Think of a restaurant kitchen. The head chef (main thread) sends a junior cook (worker thread) off to prepare a dish. If the head chef just walks away without checking back, the junior cook keeps cooking on their own timeline — that's a normal ("user") thread, independent once started.

- **`join()`** is the head chef saying "I'm not plating anything else until you tell me this dish is done" — the head chef (calling thread) stops and waits until the junior cook (target thread) finishes.
- **Thread priority** is like telling the kitchen "serve this order first" — it's just a request to whoever is scheduling the work (the JVM's thread scheduler); the scheduler is free to ignore it.
- **Daemon threads** are like the cleaning staff that only work while the restaurant is open — the moment the last customer-facing cook (user thread) leaves, the cleaning staff (daemon threads) are also sent home immediately, mid-task, without waiting for them to finish.
- **`stop()`/`suspend()`/`resume()`** are like forcibly dragging a cook away from the stove mid-task without letting them turn off the burner or put down what they're holding — dangerous, because whatever they were "holding" (a lock) never gets released.

## The Problem It Solves

Three separate problems come up once you have multiple threads working together:

1. **Forcing a thread to stop or pause from the outside is dangerous.** `Thread.stop()` kills a thread abruptly — no lock release, no resource cleanup happens. If a thread holds a lock on a shared resource and gets stopped, that lock is never released, and any other thread waiting for that lock waits forever (deadlock). `Thread.suspend()` has the same core problem: unlike `wait()` (which releases the monitor lock it's holding), `suspend()` freezes the thread while it still holds its locks. Since `resume()` exists only to wake up a `suspend()`-ed thread, it's deprecated for the same reason. This is why all three methods are deprecated — the safe alternative is the `wait()`/`notify()` coordination shown for the producer-consumer problem.

2. **Sometimes you genuinely need to wait for another thread to finish before continuing.** If a main thread starts a worker thread and then finishes its own work immediately, the worker keeps running independently in the background. If you need the main thread to pause and resume only after the worker is done — to coordinate a dependency, or to make sure a task completes before moving ahead — you need `join()`.

3. **Not every background thread should keep the program alive.** Some threads exist only to support other, more important threads (logging, autosave, garbage collection). These "daemon" threads should not prevent the JVM from shutting down once the real work is done.

## Thread Joining and Daemon Shutdown Behavior

**Diagram 1 — Thread Joining**
```
Lanes: Main = Main Thread | T1 = Thread-1 (worker)

1)  Main ──────────> T1 : new Thread(...)
2)  Main ──────────> T1 : start()
3)  Main ──(self-call)─>    : thread1.join()
    note: Main is blocked here, waiting for Thread-1 to finish
4)  T1   ──(self-call)─>    : produce() acquires lock
5)  T1   ──(self-call)─>    : Thread.sleep(8s) (holds lock)
6)  T1   ──(self-call)─>    : releases lock, method returns
7)  Main <────────── T1 : Thread-1 finishes (terminated)
    note: join() returns, Main resumes execution
8)  Main ──(self-call)─>    : continue / finish
```

**Diagram 2 — Daemon Shutdown**
```
Lanes: Main = Main Thread (user thread) | D = Daemon Thread

1)  Main ──────────> D : new Thread(...); setDaemon(true)
2)  Main ──────────> D : start()
    ┌─ par: Daemon runs in background        /  Main finishes its own work ───────────────┐
3)  │  D    ──(self-call)─>  : produce() acquires lock                                  │
4)  │  D    ──(self-call)─>  : Thread.sleep(8s) (in progress...)                        │
5)  │  Main ──(self-call)─>  : finishes remaining statements                            │
    └─────────────────────────────────────────────────────────────────────────────────────────┘
    note: Last user thread (Main) has completed execution
6)  D <───────────────────────── Main : JVM exits immediately
    note: Daemon thread is killed mid-task — sleep never completes, lock never released, no cleanup happens
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

## Key Code / Config

### Shared resource used across the examples below

```java
public class SharedResource {
    // Simulates a resource that a thread locks and holds for a while.
    public synchronized void produce() {
        System.out.println(Thread.currentThread().getName() + ": lock acquired");
        try {
            Thread.sleep(8000); // holds the lock for 8 seconds while "working"
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
        System.out.println(Thread.currentThread().getName() + ": lock released");
    }
}
```

### Why `stop()` / `suspend()` / `resume()` are dangerous (deprecated APIs)

```java
public class SuspendResumeDemo {
    public static void main(String[] args) throws InterruptedException {
        SharedResource resource = new SharedResource();
        System.out.println("Main thread is started");

        Thread thread1 = new Thread(resource::produce, "Thread-1");
        Thread thread2 = new Thread(() -> {
            try {
                Thread.sleep(1000); // let Thread-1 acquire the lock first
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            resource.produce(); // will block waiting for the monitor lock
        }, "Thread-2");

        thread1.start();
        thread2.start();

        Thread.sleep(3000); // give Thread-1 time to acquire the lock and start sleeping

        // Deprecated: suspend() freezes Thread-1 WITHOUT releasing the lock it holds.
        // Thread-2 will now wait forever for that lock -> deadlock.
        thread1.suspend();
        System.out.println("Thread-1 is suspended");

        System.out.println("Main thread is finishing its work");

        // Only calling resume() releases Thread-1 to finish and eventually release the lock.
        // If resume() is never called, Thread-2 waits indefinitely and the program never ends.
        Thread.sleep(3000);
        thread1.resume();
    }
}
```

### `join()` — making the main thread wait for a worker thread to finish

```java
public class JoinDemo {
    public static void main(String[] args) throws InterruptedException {
        SharedResource resource = new SharedResource();
        System.out.println("Main thread is started");

        Thread thread1 = new Thread(resource::produce, "Thread-1");
        thread1.start();

        // Without join(), main could finish before Thread-1 even starts its work.
        System.out.println("Main thread is waiting for Thread-1 to finish");
        thread1.join(); // blocks main here until thread1 terminates

        System.out.println("Main thread has finished its work");
    }
}
```

Use case: coordinating dependent tasks — e.g. if a later step depends on the results of two earlier threads, call `thread1.join()` and `thread2.join()` before proceeding, so you don't need to manually track completion with `wait()`/`notify()`.

### Thread priority — a hint, not a guarantee

```java
public class PriorityDemo {
    public static void main(String[] args) {
        Thread thread1 = new Thread(() -> System.out.println("Thread-1 running"));
        Thread thread2 = new Thread(() -> System.out.println("Thread-2 running"));
        Thread thread3 = new Thread(() -> System.out.println("Thread-3 running"));

        thread1.setPriority(Thread.MIN_PRIORITY);   // 1  (lowest)
        thread2.setPriority(Thread.NORM_PRIORITY);  // 5  (default)
        thread3.setPriority(Thread.MAX_PRIORITY);   // 10 (highest)

        // A newly created thread inherits the priority of its parent thread
        // unless setPriority() is called explicitly, as done above.

        thread1.start();
        thread2.start();
        thread3.start();

        // NOTE: even though thread3 has the highest priority, the JVM does NOT
        // guarantee it runs first. Priority is only a hint to the thread scheduler.
        // In practice, run this several times and the execution order will vary.
    }
}
```

### Daemon thread — dies immediately when all user threads finish

```java
public class DaemonDemo {
    public static void main(String[] args) {
        SharedResource resource = new SharedResource();
        System.out.println("Main thread is started");

        Thread daemonThread = new Thread(resource::produce, "Daemon-Thread");
        daemonThread.setDaemon(true); // must be set BEFORE start()
        daemonThread.start();

        System.out.println("Main thread has finished its work");
        // Once main (the only user thread) finishes, the JVM exits immediately.
        // Daemon-Thread is killed mid-sleep — "lock released" is never printed,
        // and no cleanup happens for it.
    }
}
```

## Important Concepts

- **`Thread.stop()`**: Terminates a thread abruptly with no lock release and no resource cleanup — can leave locks held forever, causing deadlocks in other threads waiting on that lock. Deprecated.
- **`Thread.suspend()`**: Freezes a thread's execution without releasing any monitor locks it holds (unlike `wait()`, which does release locks). Deprecated for the same deadlock risk as `stop()`.
- **`Thread.resume()`**: Reactivates a thread frozen by `suspend()`. Deprecated because it only exists to pair with the deprecated `suspend()`.
- **`thread.join()`**: Makes the calling thread block and wait until the target thread completes execution (reaches the terminated state), regardless of how long that takes. Used to coordinate between threads or to guarantee a task finishes before the program moves on.
- **Thread priority (`setPriority()`, 1–10)**: `Thread.MIN_PRIORITY` = 1, `Thread.NORM_PRIORITY` = 5 (default), `Thread.MAX_PRIORITY` = 10. A newly created thread inherits its parent thread's priority by default. Priority is only a hint to the thread scheduler about which thread to prefer next — the JVM does not guarantee any specific execution order based on it, so it should not be relied on in production code.
- **User thread**: A normal thread; the JVM stays alive as long as at least one user thread is still running.
- **Daemon thread**: A background/support thread (set via `setDaemon(true)` before `start()`). It only stays alive as long as at least one user thread is alive — the instant all user threads finish, all daemon threads are terminated immediately, mid-task, with no cleanup. Real examples: the JVM's garbage collector thread, an editor's autosave feature, and background logging.

## Interview Q&A

**Q1: Why are `Thread.stop()`, `suspend()`, and `resume()` deprecated?**
A: `stop()` terminates a thread abruptly without releasing any locks it holds or cleaning up resources, which can leave other threads waiting on those locks forever (deadlock). `suspend()` has the same core flaw — it freezes a thread while it still holds its monitor locks, unlike `wait()`, which properly releases locks before blocking. Since `resume()` only exists to wake threads frozen by `suspend()`, it's deprecated as a consequence.

**Q2: What's the practical difference between `wait()` and `suspend()`?**
A: Both pause a thread, but `wait()` releases the monitor lock the thread holds before pausing (allowing other threads to acquire that lock), while `suspend()` freezes the thread without releasing any locks — which is exactly what makes `suspend()` dangerous and deprecated.

**Q3: What does `thread.join()` do, and when would you use it?**
A: `join()` makes the calling thread block and wait until the target thread finishes execution, no matter how long it takes. It's used when you need a guarantee that a task is complete before moving on — for example, waiting for one or more worker threads to finish before using their results, instead of manually coordinating with `wait()`/`notify()`.

**Q4: Does setting a high thread priority guarantee that thread runs first?**
A: No. Thread priority (1–10, with `Thread.MAX_PRIORITY` = 10 as the highest) is only a hint to the JVM's thread scheduler about which thread to prefer. It does not guarantee any specific execution order — running the same program multiple times can produce different orderings regardless of priority. In practice, thread priority should not be relied on in production code.

**Q5: What is a daemon thread, and how is it different from a normal (user) thread?**
A: A daemon thread is a background thread marked with `setDaemon(true)` before it's started. The JVM keeps running as long as at least one user thread is alive; the moment all user threads finish, every daemon thread is terminated immediately — even mid-task — with no cleanup. A normal user thread, by contrast, keeps running independently even after the main thread finishes.

**Q6: Can you give real examples of daemon threads and explain why they're implemented that way?**
A: Yes — the JVM's own garbage collector thread, an editor's autosave feature, and background logging are typical daemon threads. They're meant to support the main program only while it's running; once the program (its user threads) is done, there's no reason for these support tasks to keep the JVM alive, so they're killed automatically along with program shutdown.
