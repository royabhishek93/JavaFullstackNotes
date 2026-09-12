# ForkJoinPool, Work-Stealing Pool & Executor Factory Methods

## What is this? (Plain English)

The `Executors` utility class gives you ready-made "recipes" for creating a thread pool instead of manually configuring `core size`, `max size`, `queue`, etc. every time. Three basic recipes: a **fixed** number of workers, a pool that **grows on demand and shrinks when idle**, and a **single** worker. Then there's a fourth, much more interesting recipe: the **work-stealing pool**, which exists to solve one specific problem — keeping ALL your CPU cores busy even when the work is unevenly distributed.

**Real-world analogy:** imagine a group of chefs (threads) in a kitchen. Normal thread pools work like a shared order queue — any free chef grabs the next order. Work-stealing is different: each chef keeps their *own* stack of sub-tasks on their personal counter. If a chef runs out of their own sub-tasks, instead of standing idle, they walk over to a busy chef's counter and steal a task *from the far end* of that chef's stack (not the one they're actively working on) — because stealing from the far end causes the least disruption.

## The Problem It Solves

### The three basic factory methods

| Factory method | Core / Max size | Queue | Idle threads | Best for |
|---|---|---|---|---|
| `Executors.newFixedThreadPool(n)` | Both = `n` | Unbounded | Stay alive forever | You know exactly how many concurrent tasks you need |
| `Executors.newCachedThreadPool()` | 0 / `Integer.MAX_VALUE` | Zero-capacity (direct handoff) | Die after 60s idle | Bursts of many **short-lived** tasks |
| `Executors.newSingleThreadExecutor()` | Both = 1 | Unbounded | Stays alive forever | Strictly sequential processing |

**Disadvantages:** fixed pools cap your concurrency even under heavy load; cached pools can spawn unbounded threads under sustained load and blow up memory; single-thread pools give you zero parallelism by design.

### The deeper problem: uneven work distribution

A normal thread pool has **one shared queue**. If one task is huge and gets picked up by Thread A while Thread B finishes its small task and goes idle, Thread B just sits there — it has no way to "help" Thread A, because the shared queue is empty and the big task is already in progress on a single thread.

**Fork/Join solves this by letting a task split itself into subtasks that other idle threads can pick up.**

## How Work-Stealing Actually Works

Each worker thread in a `ForkJoinPool` (or `WorkStealingPool`, which internally creates a `ForkJoinPool`) owns a **private work-stealing deque**, in addition to one shared **submission queue** for freshly-submitted top-level tasks.

```
                        ┌───────────────────────────────────────┐
                        │            Submission Queue            │
                        │   (shared, for new external tasks)     │
                        └───────────────────┬─────────────────────┘
                                            │
                                            │ free thread picks from here
                                            ▼
┌─────────────────────────────────┐               ┌─────────────────────────────────────┐
│        Worker Thread 1          │               │        Worker Thread 2 (busy)         │
│  ┌────────────────────────────┐ │               │  ┌────────────────────────────────┐  │
│  │  Own Work-Stealing Deque   │ │               │  │   Own Work-Stealing Deque       │  │
│  │            (D1)            │ │               │  │             (D2)                │  │
│  └────────────────────────────┘ │               │  └────────────────────────────────┘  │
└─────────────────────────────────┘               └─────────────────────────────────────┘

Additional cross-thread edges (not fitting cleanly in the boxes above):

  Worker Thread 2 ──"fork() splits big task, pushes 2nd half to FRONT of own deque"──► own Deque (D2)

  Worker Thread 1 ──"1. check own deque (empty)
                      2. check submission queue (empty)
                      3. STEAL from another thread's deque"──► Deque (D2)

  Deque (D2) ──"thief steals from the BACK (owner works from the front)"──► Worker Thread 1
```

*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

**Priority order for a thread that just went idle:**
1. Check its **own** work-stealing deque first (fastest, no contention).
2. Check the shared **submission queue** for new top-level work.
3. **Steal** from the *back* of another busy thread's deque (the owning thread always works from the *front* — stealing from the opposite end minimizes collision).

### Splitting a task: `RecursiveTask` / `RecursiveAction`

- Extend **`RecursiveTask<V>`** when your subtask needs to **return a value** (e.g. summing a range).
- Extend **`RecursiveAction`** when it does **not** return anything.
- Implement `compute()`: if the work is small enough (below a threshold), just compute it directly. Otherwise, split into two halves, call `fork()` on one half (pushes it into your own work-stealing deque for another thread to potentially steal), keep working on the other half yourself, then `join()` to wait for the forked half and combine results.

```java
class SumTask extends RecursiveTask<Long> {
    private final int start, end;
    SumTask(int start, int end) { this.start = start; this.end = end; }

    @Override
    protected Long compute() {
        if (end - start <= 4) {
            long sum = 0;
            for (int i = start; i <= end; i++) sum += i;
            return sum;
        }
        int mid = start + (end - start) / 2;
        SumTask left = new SumTask(start, mid);
        SumTask right = new SumTask(mid + 1, end);

        left.fork();                 // pushed to this thread's own deque; may get stolen
        long rightResult = right.compute(); // this thread keeps working on the right half
        long leftResult = left.join();      // wait for left half (steal victim or self) to finish

        return leftResult + rightResult;
    }
}

// Running it:
ForkJoinPool pool = ForkJoinPool.commonPool();
long total = pool.invoke(new SumTask(1, 100));

// Equivalent via the factory method (creates a ForkJoinPool internally):
ExecutorService workStealingPool = Executors.newWorkStealingPool(); // uses Runtime.availableProcessors() by default
```

## Interview Q&A

**Q: What's the practical difference between `newFixedThreadPool` and `newCachedThreadPool`?**
A: Fixed has a constant number of long-lived threads and an unbounded queue — good when concurrency needs are known and stable. Cached starts with zero threads, creates new ones on demand up to `Integer.MAX_VALUE`, and kills idle threads after 60 seconds — good for bursts of short tasks, risky for sustained heavy load (unbounded thread creation).

**Q: How does a work-stealing pool differ from a normal thread pool with a shared queue?**
A: A normal pool has one shared queue every idle thread pulls from. A work-stealing pool gives each thread its *own* deque; idle threads first check their own deque, then the submission queue, and only as a last resort steal work from another thread's deque — this keeps all cores busy even when work is split unevenly.

**Q: Why does the stealing thread take work from the *back* of the victim's deque instead of the front?**
A: The owning thread pushes and pops from the front (LIFO, cache-friendly, no contention). Stealing threads take from the back (FIFO from their perspective) specifically so the two ends rarely collide, minimizing synchronization overhead.

**Q: When do you use `RecursiveTask` vs `RecursiveAction`?**
A: `RecursiveTask<V>` when `compute()` needs to return a value (e.g., a sum). `RecursiveAction` when it doesn't return anything (e.g., an in-place transform).

**Q: What happens if you call `join()` without calling `fork()` first?**
A: You lose all parallelism — `join()` alone just runs the task's computation synchronously on the calling thread, defeating the purpose of Fork/Join.
