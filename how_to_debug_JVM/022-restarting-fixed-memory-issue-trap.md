# #22 — "Restarting the service fixed our memory issue, so we're good"

> **Category:** JVM Tuning Production Playbook | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Restarting the service fixed our memory issue, so we're good."

## 😊 Explain It Simply (for anyone)
Imagine your car's "check engine" light comes on, so you disconnect the battery and reconnect it — the light goes off, and you tell yourself "great, it's fixed!" But the actual mechanical problem that triggered the light (a leaking gasket, a memory leak) is still sitting there under the hood, quietly getting worse each time you drive. Eventually you'll need to disconnect the battery more and more often just to keep driving, until one day disconnecting it isn't enough and the car breaks down on the highway. A restart is disconnecting the battery — it clears the symptom instantly, but it is never the repair, and treating it as "good enough" just delays and often worsens the real failure.

## 📊 Visualize It
```
Memory usage over restarts:
 100% |        ▄▄        ▄▄▄        ▄▄▄▄▄▄
      |     ▄▄▄  \    ▄▄▄   \    ▄▄▄      \
   0% |_▄▄▄▄______\__▄▄________\_▄▄________\__ (restarts get more frequent)
      restart1   restart2      restart3
      Leak keeps getting worse — restart never removes the root cause
```

## 🏭 The Real Production Answer (15-YOE Level)
> "Restart hides the problem, it doesn't fix it. In 15 years I've seen this 'fix' come back to bite
> teams repeatedly.
>
> A service that needs periodic restarts for memory reasons has one of:
> 1. A memory leak (heap: object lifecycle bug; native: resource not freed)
> 2. Unbounded caches or state accumulation
> 3. Connection pool or thread pool leak
>
> The restart cadence will accelerate over time as the leak gets worse with load.
>
> Worse: restart-as-mitigation encourages teams to not fix the root cause. I've seen services
> with scheduled cron restarts running for years in production, accumulating technical debt.
>
> The engineering response to a memory issue:
> 1. Capture a heap dump before restart (jcmd GC.heap_dump, -XX:+HeapDumpOnOutOfMemoryError)
> 2. Analyze with Eclipse MAT or JProfiler
> 3. Find the leak, fix it, add a regression test
> 4. Add memory usage alerts so you catch it early next time
>
> A scheduled restart is acceptable only as a temporary measure with a ticket tracking the root
> cause fix and a deadline."

## 🔑 Key Takeaway
A restart that "fixes" a memory issue is only hiding a leak that gets worse over time — treat it as a temporary bandage with a tracked ticket, never as the actual fix.
