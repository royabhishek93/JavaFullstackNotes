## [notes.md] The Naive (Non-Optimized) Flow

```mermaid
sequenceDiagram
    participant Q as DelayedWorkQueue (min-heap)
    participant T1 as Worker Thread 1
    participant T2 as Worker Thread 2
    participant T3 as Worker Thread 3

    Note over Q,T3: Queue empty -> all 3 threads in indefinite WAIT
    Note over Q: task1, task2, task3 all offered, all due at t=2s
    Q->>T1: signal() wakes exactly ONE waiting thread
    T1->>Q: check head -> time elapsed -> poll() task1 -> RUNNING
    T1->>T2: finally block: queue non-empty -> signal() one more thread
    T2->>Q: check head -> time elapsed -> poll() task2 -> RUNNING
    T2->>T3: finally block: queue non-empty -> signal() one more thread
    T3->>Q: check head -> time elapsed -> poll() task3 -> RUNNING
    Note over T1,T3: all 3 threads finish around t=3s, become RUNNABLE again
    Note over Q: only task4 left, due at t=4s
    T1->>Q: acquire lock, delay = 4-3 = 1s -> TIMED_WAIT, release lock
    T2->>Q: acquire lock, delay = 4-3 = 1s -> TIMED_WAIT, release lock
    T3->>Q: acquire lock, delay = 4-3 = 1s -> TIMED_WAIT, release lock
    Note over T1,T3: WASTE: OS now maintains 3 separate timers for 1 task
```

## [notes.md] The Optimized Flow — Leader-Follower Pattern

```mermaid
stateDiagram-v2
    [*] --> Waiting: pool created, leader = null

    Waiting --> Runnable: signaled (task became/is head of queue)
    Runnable --> CheckHead: acquire lock, peek queue head

    CheckHead --> Running: delay <= 0 (time elapsed) -> poll() task
    CheckHead --> BecomeLeader: delay > 0 AND leader == null
    CheckHead --> Waiting: delay > 0 AND leader != null (indefinite wait, NO OS timer)

    BecomeLeader --> TimedWait: leader = currentThread; awaitNanos(delay)
    TimedWait --> CheckHead: OS timer expires -> leader = null -> re-check head

    Running --> Waiting: task finished; if queue non-empty, signal one follower
    Running --> [*]: pool shutdown
```
