# #19 — Microservice Getting OOMKilled in K8s Despite Low Heap Usage

> **Category:** JVM Tuning Production Playbook | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"We have a Spring Boot service running in a pod with 2GB limit. Java heap peaks at 800MB (monitored via Prometheus JVM metrics). But K8s OOMKills the pod every few hours. What's happening?"

## 😊 Explain It Simply (for anyone)
Think of your apartment (the container memory limit) as 2GB, and the furniture you can see in the living room (heap, which Prometheus shows you) only takes up 800MB. But there's a garage, an attic, and a basement (native memory: thread stacks, class metadata, JIT compiled code, off-heap buffers) that nobody is tracking. If those hidden storage areas keep filling up with boxes nobody throws away, eventually the whole apartment (the process) gets evicted by the landlord (Kubernetes' OOMKiller) — even though the living room looked totally fine. The lesson: heap metrics are just one room in a much bigger house, and a "low heap" reading can hide a raging leak somewhere else in that house.

## 📊 Visualize It
```
 Pod Memory Limit: 2GB
 ┌─────────────────────────────┐
 │ Heap (Prometheus sees this) │ 800MB  ✅ looks fine
 ├─────────────────────────────┤
 │ Metaspace                   │ ?? MB  ⚠️ hidden
 │ Code Cache                  │ ?? MB  ⚠️ hidden
 │ Thread Stacks               │ ?? MB  ⚠️ hidden
 │ Direct ByteBuffers (Netty)  │ ?? MB  ⚠️ growing!
 │ GC internal structures      │ ?? MB  ⚠️ hidden
 └─────────────────────────────┘
        Total RSS > 2GB → OOMKilled
```

## 🏭 The Real Production Answer (15-YOE Level)
> "Classic native memory leak masquerading as a heap problem. The 800MB you're seeing in Prometheus is heap
> only. The JVM process RSS includes several other regions that micrometer and standard JVM metrics don't
> expose by default.
>
> My diagnostic path:
>
> Step 1: Enable native memory tracking:
>   -XX:NativeMemoryTracking=summary
>
> Step 2: After reproducing, run:
>   jcmd <pid> VM.native_memory summary
>
> This gives you a breakdown: Heap, Metaspace, Code Cache, Thread stacks, Direct buffers, GC internal.
>
> Common culprits at 15 years of production experience:
>
> 1. Direct ByteBuffer leak (Netty, Kafka, NIO): appears in 'Other' or 'Internal' in native memory.
>    Symptom: off-heap memory grows without bound.
>    Fix: ensure ByteBuffers are released, tune -XX:MaxDirectMemorySize
>
> 2. Metaspace leak: usually from dynamic class generation (CGLIB, Groovy scripts, JOOQ codegen at runtime,
>    Spring proxies in a loop). Metaspace is unbounded by default.
>    Fix: -XX:MaxMetaspaceSize=512m so you get an OOM with a heap dump instead of a silent RSS creep
>
> 3. Thread stack explosion: each platform thread = 512KB-1MB stack.
>    256 threads = 128-256MB just in stacks.
>    Fix: -Xss256k for services that don't use deep recursion, or migrate to virtual threads
>
> 4. Code cache full: long-running services can fill code cache, causing JIT deoptimization.
>    Fix: -XX:ReservedCodeCacheSize=512m
>
> Given the 2GB limit and 800MB heap peak, my first guess is direct buffer leak from a Netty-based client
> (common in WebFlux or gRPC services). The heap looks fine because the allocations are off-heap."

## 🔑 Key Takeaway
When heap looks healthy but the pod still OOMKills, stop staring at heap metrics and go straight to Native Memory Tracking — the leak is almost always off-heap.
