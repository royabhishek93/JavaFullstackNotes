## [notes.md] Thread Joining and Daemon Shutdown Behavior — Diagram 1 (Thread Joining)

```mermaid
sequenceDiagram
    participant Main as Main Thread
    participant T1 as Thread-1 (worker)

    Main->>T1: new Thread(...) 
    Main->>T1: start()
    Main->>Main: thread1.join()
    Note over Main: Main is blocked here,<br/>waiting for Thread-1 to finish
    T1->>T1: produce() acquires lock
    T1->>T1: Thread.sleep(8s) (holds lock)
    T1->>T1: releases lock, method returns
    T1-->>Main: Thread-1 finishes (terminated)
    Note over Main: join() returns,<br/>Main resumes execution
    Main->>Main: continue / finish
```

## [notes.md] Thread Joining and Daemon Shutdown Behavior — Diagram 2 (Daemon Shutdown)

```mermaid
sequenceDiagram
    participant Main as Main Thread (user thread)
    participant D as Daemon Thread

    Main->>D: new Thread(...); setDaemon(true)
    Main->>D: start()
    par Daemon runs in background
        D->>D: produce() acquires lock
        D->>D: Thread.sleep(8s) (in progress...)
    and Main finishes its own work
        Main->>Main: finishes remaining statements
    end
    Note over Main: Last user thread (Main) has<br/>completed execution
    Main-->>D: JVM exits immediately
    Note over D: Daemon thread is killed mid-task —<br/>sleep never completes, lock never released,<br/>no cleanup happens
```
