# Threads, Processes, and the JVM Memory Model (Multithreading Part 1)

## What is this? (Plain English)

Think of a **process** as an entire restaurant, and a **thread** as one chef working in that restaurant's kitchen. The restaurant (process) has its own building, its own ingredients storage, its own equipment — resources that belong only to that restaurant and are never shared with the restaurant across the street (another process). Inside the restaurant, you can have multiple chefs (threads) working at the same time. All the chefs share the same kitchen, the same ingredient storage, and the same recipe book (shared resources), but each chef has their own personal notepad for jotting down what step of the recipe they're currently on (private, per-thread memory). One chef always starts working first the moment the restaurant opens (the **main thread**), and that chef can hire more chefs (create more threads) to help out.

**The core rule:** a *process* is an independent, isolated instance of a running program with its own memory; a *thread* is the smallest unit of execution inside a process, and multiple threads inside the same process share that process's memory but also keep some memory private to themselves.

## The Problem It Solves

Before you can reason about concurrency, deadlocks, race conditions, or thread safety, you need a precise answer to two very commonly asked interview questions that trip up experienced engineers:

1. **What exactly is a process, and what is a thread — and how are they related?**
2. **When multiple threads run inside the same process, which memory do they share, and which memory does each thread keep to itself?**

Getting this wrong leads to confusion later about *why* synchronization is needed for some data (heap objects, static/global variables) but not for others (local variables on a thread's own stack), and *why* two threads can "run in parallel" on one CPU core even though there's only one core available (context switching).

## The Process → JVM Instance → Threads Relationship (and Memory Model)

```
┌──────────────────────── Operating System ────────────────────────────────┐
│                                                                                                        │
│  ┌────────────── Process 1 (started by: java MultithreadingLearning) ───────────────────────┐   │
│  │                                                                                                  │   │
│  │   JVM Instance 1 (-Xms256m -Xmx2g)                                                              │   │
│  │        │                                                                                        │   │
│  │        ├──> Shared by ALL threads inside Process 1:                                             │   │
│  │        │      • Heap (objects created with 'new')                                               │   │
│  │        │      • Code Segment (compiled machine code, read-only)                                 │   │
│  │        │      • Data Segment (global / static variables)                                        │   │
│  │        │                                                                                        │   │
│  │        ├──> Main Thread (auto-created): Stack | Register | Program Counter                      │   │
│  │        ├──> Thread 1 (created from main): Stack | Register | Program Counter                    │   │
│  │        └──> Thread 2 (created from main): Stack | Register | Program Counter                    │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                        │
│  ┌────────────── Process 2 (a separate 'java' execution) ───────────────────────────────┐   │
│  │   JVM Instance 2 — own Heap / Code Segment / Data Segment, never shared with Process 1          │   │
│  └──────────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```
*(Full Mermaid source: see [mermaid-diagrams.md](mermaid-diagrams.md))*

**How execution actually gets here (compile → run → process → threads):**
1. `javac Main.java` compiles the source into **bytecode**.
2. `java Main` executes it. At this point the JVM starts a **new process**.
3. A **new JVM instance** is allocated to that process, and this JVM instance owns all of that process's memory areas (Heap, Code Segment, Data Segment) plus per-thread areas (Stack, Register, Program Counter) for every thread it creates.
4. The JVM interprets or JIT-compiles the bytecode into native **machine code**, which is stored in the **Code Segment**.
5. Every process starts with exactly one thread, called the **main thread**. From the main thread, more threads can be created to run tasks concurrently.
6. Each thread gets its own Stack, Register, and Program Counter, but all threads in that process point at and share the same Code Segment, Data Segment, and Heap.

**What each memory area is for:**
- **Code Segment** (shared) — holds the compiled machine code that the CPU executes. It is **read-only**; no thread can modify it.
- **Data Segment** (shared) — holds global and static variables. Threads can both read and modify this data, so proper synchronization is required to avoid data inconsistency.
- **Heap** (shared within a process, never shared across processes) — every object created with `new` is allocated here. Threads of the same process share this heap and can read/modify it, so synchronization is required. Two different processes never share heap memory — each gets its own, isolated from the other.
- **Stack** (per-thread) — each thread has its own stack, used to manage method calls and local variables.
- **Register** (per-thread) — used to store intermediate values while the CPU/JIT is executing or reshuffling instructions. It is also the mechanism used during **context switching**: when a thread's CPU time slice ends, whatever the CPU had computed so far is saved into that thread's register, and reloaded from there when the thread's turn comes around again.
- **Program Counter / PC** (per-thread) — points to the address of the next instruction (in the Code Segment) that the thread needs to execute, and increments after each instruction completes successfully.

**Heap sizing per process:** a process's JVM instance is given a heap sized between an initial value and a maximum value, configured with `-Xms` (initial heap size) and `-Xmx` (maximum heap size) flags. If a process tries to allocate more heap than its configured `-Xmx`, it throws an `OutOfMemoryError`, even if other processes on the machine still have plenty of memory available — because each process's heap allocation is bounded by its own JVM instance's configured limits.

**Context switching (single CPU core vs. multiple cores):**
- With **one CPU core**, only one thread can actually run at any instant. The OS/JVM scheduler gives each thread a time slice; when the slice ends, the CPU's intermediate results are saved into that thread's register, and the OS switches to run another thread. This is **context switching** — it *looks like* threads run simultaneously, but they are actually taking turns.
- With **multiple CPU cores**, if the number of threads is less than or equal to the number of cores, threads can run truly in **parallel** with no context switching needed. If there are more threads than cores, context switching still happens for the excess threads.

## Key Code / Config

```java
// MultithreadingLearning.java
public class MultithreadingLearning {
    public static void main(String[] args) {
        // Every process starts with exactly one thread: the main thread.
        System.out.println(Thread.currentThread().getName());
        // Output: main
    }
}
```

```bash
# Step 1: compile the source into bytecode
javac MultithreadingLearning.java

# Step 2: run it — this is the point where the JVM starts a NEW PROCESS
java MultithreadingLearning

# Configure this process's own JVM instance heap size:
#   -Xms  -> initial heap size
#   -Xmx  -> maximum heap size (exceeding this throws OutOfMemoryError)
java -Xms256m -Xmx2g MultithreadingLearning
```

> Note: this part of the transcript only covers how the **main thread** is automatically created when a process starts. The explicit APIs for creating additional threads yourself (e.g. extending `Thread`, implementing `Runnable`) are introduced in the next part of the series.

## Interview Q&A

**Q1: What is the difference between a process and a thread?**
A: A process is an instance of a program that is currently being executed; the OS allocates it its own resources (like heap memory), and processes never share resources with each other — they run completely independently. A thread is often called a "lightweight process" — it's the smallest sequence of instructions that the CPU executes independently. A process always starts with one thread (the main thread), and from it more threads can be created to perform tasks concurrently. Threads within the same process do share resources.

**Q2: Which memory areas are shared between threads of the same process, and which are private to each thread? Why the split?**
A: Shared: the **Code Segment** (compiled machine code, read-only), the **Data Segment** (global/static variables), and the **Heap** (objects created with `new`) — all threads in a process work against the same copy of these because they belong to the process as a whole. Private per thread: the **Stack** (each thread manages its own method calls and local variables), the **Register** (stores each thread's intermediate computation state), and the **Program Counter** (tracks which instruction address that specific thread is currently executing). The shared areas need synchronization because multiple threads can read and modify them concurrently; the private areas don't, because only one thread ever touches its own stack/register/PC.

**Q3: If two threads share the same heap, why don't two separate processes share heap memory too?**
A: Because a new JVM instance is allocated per process, and each JVM instance owns its own Heap, Code Segment, and Data Segment. Threads created within that one process's JVM instance share that instance's memory. A different process gets an entirely separate JVM instance with its own memory areas, so there is no sharing across process boundaries — the two heaps live at different memory locations and are fully isolated.

**Q4: How does context switching actually work at the register/program-counter level?**
A: Each thread's Program Counter points to the address of the next instruction (inside the Code Segment) that thread needs to run. The OS/JVM scheduler assigns a CPU time slice to a thread; the CPU loads the instruction from that address and starts executing, using its register to hold intermediate results. When the time slice ends, whatever the CPU has computed so far is saved into that thread's own register storage, and the OS switches the CPU to run a different thread. When the original thread's turn comes back around, its saved register state is reloaded into the CPU, and execution resumes exactly where it left off, using the Program Counter to know which instruction is next.

**Q5: Does context switching mean threads never truly run in parallel?**
A: It depends on the number of CPU cores versus the number of threads. With a single CPU core, only one thread executes at any given instant — multiple threads only *appear* to run simultaneously because the OS rapidly context-switches between them. With multiple CPU cores, if the number of threads is less than or equal to the number of cores, threads can execute truly in parallel with no context switching required at all.

**Q6: What is the difference between multitasking and multithreading?**
A: Multitasking is running multiple separate **processes** at the same time (e.g. Process 1 and Process 2) — these processes are independent tasks and never share any resources; the OS context-switches between them. Multithreading is running multiple **threads inside a single process** — these threads do share resources like the Heap, Code Segment, and Data Segment, but can still execute tasks independently and concurrently.

**Q7: What are the benefits and challenges of multithreading?**
A: Benefits: improved performance through task parallelism (splitting work across threads instead of running everything sequentially on one thread), better application responsiveness, and efficient resource sharing (threads reuse the same process resources rather than duplicating them). Challenges: concurrency issues such as deadlocks and data inconsistency, since threads can read and modify shared data like the heap and static/global variables — this requires synchronization (locks, `synchronized` blocks), which adds overhead; and multithreaded code is generally harder to test and debug than single-threaded code.
