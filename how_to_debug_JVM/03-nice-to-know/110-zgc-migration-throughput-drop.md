# #110 — We migrated to ZGC and our throughput dropped 25%

> **Category:** GC Tuning & Debugging | **Type:** Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"We migrated to ZGC and our throughput dropped 25%. Is this expected and what do you do?"

## 😊 Explain It Simply (for anyone)
Imagine hiring a cleaning crew that works *while* your restaurant is open, quietly tidying tables around customers instead of closing the doors for a few minutes each night. Customers never notice a "closed" sign — but that cleaning crew still needs staff, and those staff members are now taking up kitchen space and resources that could've gone toward cooking more food. That's the tradeoff with ZGC (a modern garbage collector designed for near-zero pause times): it does almost all its cleanup work *while your program keeps running*, so users never feel a freeze — but that constant background cleaning eats real CPU power that your application could otherwise use to do actual work, which is why raw throughput (how much work gets done overall) can drop. It's a deliberate trade: smoother, more consistent response times in exchange for using more resources overall.

## 📊 Visualize It
```
G1GC:  [busy][busy][FREEZE 200ms][busy][busy]   ← throughput-friendly, visible pause
ZGC:   [busy+cleanup][busy+cleanup][busy+cleanup] ← no freeze, but CPU tax every moment
                 ↑
        15-30% CPU always spent concurrently on GC
```

## 🏭 The Real Production Answer (15-YOE Level)
> Completely expected. ZGC achieves sub-millisecond pauses by doing almost all GC work concurrently — while your application threads are running. That concurrent work consumes real CPU. Typically 15–30% of CPU is consumed by GC threads running concurrently. For a throughput-sensitive workload, that CPU is no longer available to application threads.
>
> The tradeoff is explicit: ZGC trades throughput for latency. For a latency-sensitive API, losing 25% throughput but getting 10ms p99.9 vs 200ms p99.9 is worth it. For a batch job that needs to process 1M records/hour, it is not worth it.

**Decision matrix:**

```
WORKLOAD TYPE          RECOMMENDED GC    REASONING
─────────────────────────────────────────────────────────────────
REST API < 50ms p99    G1GC or ZGC       G1GC: balanced; ZGC: sub-ms
Real-time trading       ZGC / Shenandoah  Cannot afford STW pauses
Batch processing        ParallelGC        Maximize throughput, no pause SLA
Stream processing       G1GC              Balanced throughput+latency
Large heap (>32GB)      ZGC               G1GC struggles with large heaps
```

## 🔑 Key Takeaway
ZGC deliberately trades throughput for latency — a 25% throughput drop is the expected cost of near-zero pauses, not a misconfiguration.
