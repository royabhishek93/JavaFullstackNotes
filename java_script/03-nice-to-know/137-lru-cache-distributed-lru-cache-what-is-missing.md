# Distributed LRU Cache — What's Missing
> **Topic:** LRU Cache | **Level:** Senior Trap | **Frequency:** Medium

## The Setup

You have just walked the interviewer through a clean LRU cache implementation in JavaScript. It handles O(1) get and put, sentinel nodes, eviction, and TTL. The interviewer then says: "Great. Now deploy this as the caching layer for a service with 20 Node.js processes behind a load balancer. What's missing?"

## The Question

Can this single-process in-memory LRU cache be used as a distributed cache? What are the four fundamental gaps between this implementation and a production distributed cache?

## Diagram

```
SINGLE-PROCESS LRU (what we built)
=====================================
  Process A:  Map { "user:1" → node }  ←──── only lives here
              DLL: [user:1] ◄──► ...

  Process B:  Map { }                  ←──── completely independent
  Process C:  Map { }                  ←──── completely independent

  Load balancer sends request for "user:1" to Process B:
    → cache miss (even though Process A has it)
    → Postgres hit
    → inconsistent hit rates across processes

DISTRIBUTED CACHE (Redis Cluster)
=====================================
  Process A ──┐
  Process B ──┼──► Redis Cluster ──► shared eviction, shared state
  Process C ──┘      │
                   Replicas (Sentinel/Cluster)
                   AOF/RDB persistence
                   Mutex via SETNX / Redlock

CONCURRENCY PROBLEM (multi-threaded runtime)
=============================================
  Thread 1: insertAtHead(A) — executing line (3): head.next.prev = A
  Thread 2: insertAtHead(B) — executing line (4): head.next = B

  Interleaved execution corrupts the list silently.
  JavaScript's event loop hides this; Node.js worker threads expose it.
  Any Go, Java, or Python multi-threaded runtime exposes it immediately.
```

## Model Answer (15 YOE)

"This is a single-process, single-threaded, in-memory implementation. For distributed use you need four things that it entirely lacks:

**1. Concurrency safety.** Multiple goroutines or threads hitting the same structure corrupt the doubly linked list without a mutex or lock-free design. JavaScript's single-threaded event loop hides this, but Node.js worker threads or any multi-threaded runtime (Go, Java, Python with real threads) exposes it immediately. Fix: a read-write lock around all cache operations, or a lock-free design using atomic compare-and-swap.

**2. Persistence.** Process restart wipes the entire cache. If 20 processes all restart simultaneously (rolling deploy, crash), the origin (Postgres, third-party API) receives 100% of traffic with no cache protection. Redis solves this with AOF (append-only file) and RDB (point-in-time snapshots). Fix: use an external cache store with persistence configured.

**3. Replication and failover.** A single cache process is a single point of failure. If it dies, all traffic hits the origin. Redis Sentinel provides automatic failover with replica promotion. Redis Cluster provides horizontal sharding with per-shard replication. Fix: deploy with at least one replica and a failover mechanism.

**4. Capacity coordination.** In a multi-process setup, each process runs its own in-memory LRU. There is no global LRU across the fleet. A key evicted from Process A may still exist in Process B — inconsistent state. The total effective cache capacity is `process_count × per_process_capacity`, but the hit rate depends on whether the load balancer sends a given key to the same process consistently (sticky sessions) or randomly (round-robin). Fix: use a shared external cache (Redis) so all processes share one LRU policy and one eviction space."

## Why It's a Trap

Candidates who answer "just deploy it on multiple machines" reveal they have never operated a distributed system under load. The concurrency trap is especially subtle in JavaScript — the event loop gives a false sense of safety that disappears the moment worker threads or a different runtime is introduced. Strong candidates proactively list all four gaps and name Redis-specific features (AOF, Sentinel, Cluster) that address them.

## What NOT to Say

- "Yes, just deploy it — it will work fine" — ignores all four gaps
- "JavaScript is single-threaded so concurrency is not an issue" — worker threads and other runtimes make this wrong
- "Replication is optional for a cache" — a cache with no failover causes origin overload on any restart
- "Each process having its own LRU is fine" — it reduces effective hit rate and creates inconsistent state

## Follow-up

**Q:** For the concurrency problem specifically — if you had to make this implementation thread-safe in JavaScript using worker threads, what is the minimal change?

**A:** Wrap every `get` and `put` call in a mutex using a shared `SharedArrayBuffer` and `Atomics.wait` / `Atomics.notify`. In practice this is complex to implement correctly in JS. The idiomatic Node.js solution is to keep the LRU cache in a single dedicated worker thread (the "cache thread") and route all get/put requests to it via message passing — the event loop serializes all operations, restoring thread safety without explicit locks. For truly high-throughput multi-threaded scenarios, use a purpose-built concurrent hash map (e.g., Java's `ConcurrentHashMap` with a `ConcurrentLinkedDeque` for recency ordering) or simply offload to Redis.
