# Fork/Join Framework (Work Stealing)

**Interview Priority:** Senior: ✅ SHOULD KNOW | Mid: ✅ SHOULD KNOW

---

## Scenario

**Given this code, what is the performance issue?**

```java
public class SumSingleThread {
    public static void main(String[] args) {
        long sum = 0;
        for (int i = 0; i < 100_000_000; i++) {
            sum += i;
        }
        System.out.println(sum);
    }
}
```

**Problem:** One CPU core does all the work. On a 16-core machine, you waste 15 cores.

---

## Key Principle

**Fork/Join splits a big task into smaller tasks and runs them in parallel using work stealing.**

---

## Why It Happens (Simple English)

Some tasks are naturally divisible (sum, sort, search). Fork/Join breaks them into chunks and lets multiple worker threads execute them. Idle threads steal work from busy threads to keep all cores used.

---

## Core Classes

- `ForkJoinPool`
- `RecursiveTask<T>` (returns a result)
- `RecursiveAction` (no result)

---

## Real Example (Runnable)

```java
import java.util.concurrent.*;

public class ForkJoinSum extends RecursiveTask<Long> {
    private static final int THRESHOLD = 10_000;
    private final long start;
    private final long end;

    public ForkJoinSum(long start, long end) {
        this.start = start;
        this.end = end;
    }

    @Override
    protected Long compute() {
        long length = end - start;
        if (length <= THRESHOLD) {
            long sum = 0;
            for (long i = start; i < end; i++) {
                sum += i;
            }
            return sum;
        }

        long mid = start + length / 2;
        ForkJoinSum left = new ForkJoinSum(start, mid);
        ForkJoinSum right = new ForkJoinSum(mid, end);

        left.fork();
        long rightResult = right.compute();
        long leftResult = left.join();

        return leftResult + rightResult;
    }

    public static void main(String[] args) {
        ForkJoinPool pool = new ForkJoinPool();
        long result = pool.invoke(new ForkJoinSum(0, 100_000_000));
        System.out.println(result);
    }
}
```

**Expected output:**
```
4999999950000000
```

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| Single-thread loop for CPU-heavy divideable task | Fork/Join with parallel splitting |

**Wrong:**
```java
long sum = slowSingleThreadSum();
```

**Right:**
```java
ForkJoinPool pool = new ForkJoinPool();
long sum = pool.invoke(new ForkJoinSum(0, N));
```

---

## Work Stealing (Simple Explanation)

Each worker has its own deque of tasks. If one worker finishes early, it steals tasks from others. This keeps all CPU cores busy without heavy coordination.

---

## Interview Tip (Exact Answer)

"Fork/Join is for CPU-heavy, divisible tasks. It uses work stealing so idle threads grab tasks from busy ones. It is not for blocking I/O."

---

## Quick Checklist

- Use for CPU-bound tasks.
- Split tasks until they are small enough.
- Avoid blocking calls inside `compute()`.
- Use `ForkJoinPool.commonPool()` for small tasks.

---

## Critical Pitfalls

- Blocking I/O inside Fork/Join can starve worker threads.
- Too small threshold causes overhead; too large wastes parallelism.
- Recursive task creation can explode if you split too small.

---

## Follow-up Questions & Answers

**Q:** When should I avoid Fork/Join?

**A:** Avoid it for blocking I/O or tasks that cannot be split evenly.

**Q:** Is Fork/Join only for parallel streams?

**A:** Parallel streams use Fork/Join under the hood, but you can also use it directly for custom control.

---

## How to Use for Interviews

- Explain work stealing in 1 sentence.
- Give a simple divide-and-conquer example.
- Mention that it is CPU-bound, not I/O-bound.

---

**Last Updated:** March 5, 2026
