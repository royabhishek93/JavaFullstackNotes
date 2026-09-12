# #44 — MaxGCPauseMillis=50 guarantees my GC pauses are under 50ms, right?

> **Category:** GC Tuning & Debugging | **Type:** Senior Trap Question | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"MaxGCPauseMillis=50 guarantees my GC pauses are under 50ms, right?"

## 😊 Explain It Simply (for anyone)
Think of setting a "please arrive within 30 minutes" goal for a food delivery app. The app will *try* its best — routing the driver smartly, picking the closest restaurant — but if there's a sudden traffic jam or the restaurant is slammed with orders, the delivery might still take 45 minutes. The 30-minute number was never a magic force field, just a target the system optimizes toward. `MaxGCPauseMillis` works the same way for Java's G1 garbage collector: it's a goal the collector uses to decide how much cleanup work to bite off each time, not an ironclad promise. If unavoidable work (like clearing out a jam-packed waiting room of new objects) is bigger than that goal, the pause will run long — there's no way to refuse doing necessary work, just like a delivery driver can't teleport through traffic.

## 📊 Visualize It
```
Setting:  -XX:MaxGCPauseMillis=50   ← a HINT, not a contract

Reality:
  ┌─────────────────────────────┐
  │ Mandatory Eden evacuation    │  ← MUST happen every Young GC
  │ Root scanning (many threads) │  ← can't be skipped
  │ Full GC (ignores this flag)  │  ← completely bypasses target
  └─────────────────────────────┘
       Actual pause can exceed 50ms regardless
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG. The experienced answer:**

> No. `MaxGCPauseMillis` is a target and a hint to G1GC's region selection algorithm. G1GC uses it to decide how many Old generation regions to include in a mixed collection — fewer regions means shorter pause, lower throughput. But it absolutely cannot guarantee the pause will stay under 50ms.
>
> G1GC will exceed the target when: Eden has grown too large (the minimum young collection already exceeds budget), root scanning takes longer than expected (high thread count, JNI), or a Full GC is triggered (Full GC ignores this parameter entirely).
>
> The guarantee-like pause SLA algorithms are ZGC and Shenandoah, and even they don't provide hard guarantees — they just routinely achieve sub-millisecond pauses by design, not by the JVM trying to hit a target.

## 🔑 Key Takeaway
`MaxGCPauseMillis` is a tuning hint for G1's region selection, never a hard SLA guarantee — Full GC ignores it entirely.
