# LongAdder & LongAccumulator (High-Contention Counters)

**Interview Priority:** Senior: 👍 GOOD TO KNOW | Mid: 📚 AWARENESS

---

## Scenario

**Given this code under 100 concurrent threads, what is the performance problem?**

```java
AtomicLong counter = new AtomicLong(0);

// 100 threads doing this simultaneously
counter.incrementAndGet();
```

**Problem:** Under high contention, all threads fight over the same `AtomicLong` memory location. CAS retries cause a spin-wait storm.

---

## Key Principle

**`LongAdder` reduces contention by striping updates across multiple internal cells; threads update different cells and the sum is computed only when `sum()` is called.**

---

## Why It Happens (Simple English)

`AtomicLong` uses a single memory location. When 100 threads all try to CAS it simultaneously, most fail and retry (spin). `LongAdder` avoids this by giving each thread its own "cell" to write to. The final value is the sum of all cells — fast writes, slightly more expensive reads.

---

## LongAdder

```java
import java.util.concurrent.atomic.LongAdder;

public class LongAdderExample {
    private final LongAdder counter = new LongAdder();

    public void increment() {
        counter.increment();         // add 1
    }

    public void add(long value) {
        counter.add(value);          // add arbitrary value
    }

    public long getCount() {
        return counter.sum();        // read total (may see stale under concurrent writes)
    }

    public long getAndReset() {
        return counter.sumThenReset(); // read + reset to 0 atomically
    }
}
```

---

## LongAdder vs AtomicLong

| Feature | `AtomicLong` | `LongAdder` |
|---|---|---|
| Write performance (low contention) | Fast | Slightly slower (cell overhead) |
| Write performance (high contention) | Degrades (CAS spins) | Stays fast (no contention) |
| Read (`get`/`sum`) | Exact, instant | Sum of cells (not atomic snapshot) |
| Compare-and-set | Yes (`compareAndSet`) | No |
| Use case | Shared state with reads+writes | Pure counters / stats |

---

## LongAccumulator (Generalized)

`LongAccumulator` generalizes `LongAdder` to any associative, commutative operation (not just addition).

```java
import java.util.concurrent.atomic.LongAccumulator;

// Track the running maximum across threads
LongAccumulator maxValue = new LongAccumulator(Long::max, Long.MIN_VALUE);

// Many threads calling:
maxValue.accumulate(someValue);  // internally: cell = max(cell, someValue)

long result = maxValue.get();    // overall max
```

```java
// Track running sum (same as LongAdder but explicit)
LongAccumulator sum = new LongAccumulator((a, b) -> a + b, 0L);
sum.accumulate(10);
sum.accumulate(20);
System.out.println(sum.get()); // 30
```

**Constraint:** The accumulator function must be commutative and associative (order of application doesn't matter).

---

## DoubleAdder & DoubleAccumulator

Same concepts for `double` values:

```java
DoubleAdder total = new DoubleAdder();
total.add(1.5);
total.add(2.3);
System.out.println(total.sum()); // 3.8

DoubleAccumulator max = new DoubleAccumulator(Double::max, Double.MIN_VALUE);
max.accumulate(3.14);
```

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| `AtomicLong` counter under 50+ threads | `LongAdder` — no contention |
| Read `LongAdder.sum()` expecting atomic snapshot | Use `AtomicLong` when exact read is required |
| `LongAdder` for compare-and-swap logic | `AtomicLong.compareAndSet()` |

---

## Interview Tip (Exact Answer)

"`LongAdder` is a striped counter designed for high write contention. Each thread updates its own cell; `sum()` aggregates them. It's significantly faster than `AtomicLong` when many threads increment simultaneously, but it doesn't support atomic compare-and-set so it can't replace `AtomicLong` everywhere."

---

## Quick Checklist

- `LongAdder` for metrics, event counts, rate counters under high concurrency.
- `LongAccumulator` for custom associative ops (max, min, bitwise AND/OR).
- `sumThenReset()` is useful for periodic metric flushing.
- The `sum()` read is NOT a point-in-time snapshot — it may see partial updates.

---

## Critical Pitfalls

- Do NOT use `LongAdder` when you need an exact atomic snapshot (use `AtomicLong`).
- `LongAccumulator` function must be commutative and associative — subtraction is NOT valid.
- `sumThenReset()` is only best-effort atomic; avoid relying on it for exact accounting.

---

## Follow-up Questions & Answers

**Q:** Why is `LongAdder` faster under high contention?

**A:** It avoids CAS retry loops by striping state across cells. Threads that would otherwise spin on a single address each write to their own cell, so there's no contention.

**Q:** Can I use `LongAdder` to implement a rate limiter?

**A:** Not reliably — the sum is not an atomic snapshot. For rate limiting, use a `Semaphore` or `AtomicLong` with CAS.

---

## How to Use for Interviews

- Lead with "striped cells to avoid CAS contention."
- Contrast with `AtomicLong`: faster writes, weaker read guarantees.
- Mention `LongAccumulator` as the generalization (max/min are classic examples).

---

**Last Updated:** August 18, 2026
