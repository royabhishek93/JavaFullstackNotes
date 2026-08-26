# Phaser (Flexible Multi-Phase Synchronizer)

**Interview Priority:** Senior: 👍 GOOD TO KNOW | Mid: 📚 AWARENESS

---

## Scenario

**Given this code using CyclicBarrier, what problem do you hit when phases have different participant counts?**

```java
// Adding/removing threads mid-run is impossible with CyclicBarrier
CyclicBarrier barrier = new CyclicBarrier(5); // fixed count forever
```

**Problem:** `CyclicBarrier` and `CountDownLatch` have fixed participant counts. You can't add or remove threads between phases.

---

## Key Principle

**`Phaser` is a reusable, flexible synchronizer where parties can register and deregister dynamically across multiple phases.**

---

## Why It Happens (Simple English)

`CountDownLatch` is one-shot. `CyclicBarrier` resets but with a fixed count. `Phaser` solves both: it resets after each phase, allows dynamic registration, and supports hierarchical phasers for fork/join-style work.

---

## Basic Phaser Example

```java
import java.util.concurrent.Phaser;

public class PhaserExample {
    public static void main(String[] args) {
        Phaser phaser = new Phaser(1); // register main thread

        for (int i = 0; i < 3; i++) {
            int id = i;
            phaser.register(); // register each worker
            new Thread(() -> {
                System.out.println("Thread " + id + " Phase 1");
                phaser.arriveAndAwaitAdvance(); // wait for all at phase 1

                System.out.println("Thread " + id + " Phase 2");
                phaser.arriveAndDeregister(); // done — leave phaser
            }).start();
        }

        phaser.arriveAndAwaitAdvance(); // main arrives at phase 1
        System.out.println("All done with phase 1");
        phaser.arriveAndDeregister();   // main leaves
    }
}
```

---

## Key Phaser Methods

| Method | What It Does |
|---|---|
| `register()` | Add one more party |
| `arriveAndAwaitAdvance()` | Arrive + block until all arrive |
| `arriveAndDeregister()` | Arrive + permanently remove this party |
| `arrive()` | Arrive without waiting (non-blocking) |
| `getPhase()` | Current phase number |
| `getRegisteredParties()` | Current registered count |

---

## Phaser vs CountDownLatch vs CyclicBarrier

| Feature | CountDownLatch | CyclicBarrier | Phaser |
|---|---|---|---|
| Reusable | No | Yes (fixed) | Yes (dynamic) |
| Dynamic parties | No | No | Yes |
| Multi-phase | No | No | Yes |
| Party count | Fixed | Fixed | Changes at runtime |

---

## Tiered (Hierarchical) Phaser

```java
// Parent phaser aggregates child phasers — useful for tree-structured work
Phaser parent = new Phaser();
Phaser child1 = new Phaser(parent, 3);
Phaser child2 = new Phaser(parent, 3);
// child phasers advance independently; parent advances when all children advance
```

---

## Wrong vs Right

| ❌ Wrong | ✅ Right |
|---|---|
| `CyclicBarrier` when worker count changes | `Phaser` with `register()`/`arriveAndDeregister()` |
| Re-creating barriers each phase | Single `Phaser` across all phases |

---

## Interview Tip (Exact Answer)

"`Phaser` is the most flexible synchronizer in Java. Unlike `CyclicBarrier`, it lets parties join and leave between phases, supports multiple named phases, and can be arranged in a tree for fork/join-style coordination."

---

## Quick Checklist

- Use `Phaser` when participant count changes across phases.
- `arriveAndAwaitAdvance()` is the most common call (arrive + wait).
- `arriveAndDeregister()` for threads that finish early.
- Phase number increments after all parties arrive.

---

## Critical Pitfalls

- Forgetting to register the main thread causes it to not control phase advancement.
- `arrive()` without waiting can let a thread race ahead to the next phase.
- Hierarchical phasers can deadlock if child/parent registration is inconsistent.

---

## Follow-up Questions & Answers

**Q:** When would you choose `Phaser` over `CyclicBarrier`?

**A:** When threads dynamically join or leave the computation, or when you need more than one synchronization phase with changing participants.

**Q:** Can `Phaser` terminate?

**A:** Yes — override `onAdvance()` to return `true` when the phaser should terminate (e.g., after N phases).

```java
Phaser phaser = new Phaser(3) {
    @Override
    protected boolean onAdvance(int phase, int registeredParties) {
        return phase >= 2 || registeredParties == 0; // terminate after phase 2
    }
};
```

---

## How to Use for Interviews

- Lead with "dynamic participant count is the key differentiator from CyclicBarrier."
- Show the `register()` + `arriveAndDeregister()` pair.
- Mention `onAdvance()` for controlled termination.

---

**Last Updated:** August 18, 2026
