# #136 — Nightly batch job runs fine on dev but runs 3x slower in prod Kubernetes

> **Category:** GC Tuning & Debugging | **Type:** Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"Nightly batch job runs fine on dev but runs 3x slower in prod Kubernetes. GC-related? What do you investigate?"

## 😊 Explain It Simply (for anyone)
Imagine a construction crew that's told "you have 2 workers available" but they show up with 64 people ready to dig, because nobody told them the site actually only has room for 2 shovels. All 64 people constantly bump into each other, wait in line for a shovel, and get in each other's way — the job takes far longer than if only 2 people showed up in the first place. That's what happens when a Java program run inside a container doesn't realize it only has a couple of CPUs available: it might spin up dozens of "cleanup crew" threads (garbage collection threads) based on the *host machine's* total power, not the small slice it's actually been given. On top of that, Kubernetes can also literally put the brakes on a container that tries to use more CPU than it's allowed (called "throttling"), like a governor limiting a car's engine — and garbage collection, being CPU-hungry work, suffers badly when throttled.

## 📊 Visualize It
```
Dev machine:      64 CPUs available → GC threads sized correctly
Prod K8s pod:      2 CPU limit, but JVM (misconfigured) thinks 64 CPUs exist
                   → spins 64 GC threads competing for 2 CPUs
                   → CPU throttled (CFS) → GC crawls → batch job 3x slower
```

## 🏭 The Real Production Answer (15-YOE Level)
> First check: is the pod CPU throttled? In K8s, CPU limits cause CFS throttling which directly hurts GC thread performance. GC is CPU-intensive and throttled pods can see 5–10x GC overhead.
>
> Second check: is the JVM using ParallelGC and appropriately sizing GC threads? By default, ParallelGC uses `Runtime.getRuntime().availableProcessors()` GC threads. In a container with 2 CPU, that might be 2 GC threads — reasonable. But if UseContainerSupport was off on Java 8, the JVM sees 64 cores and spins 64 GC threads competing for 2 CPUs.

**Investigation:**

```bash
# Check GC thread count:
java -XX:+PrintFlagsFinal -version 2>&1 | grep -E "ParallelGCThreads|ConcGCThreads"

# Explicitly set for containers:
-XX:ParallelGCThreads=4       # STW parallel GC workers
-XX:ConcGCThreads=2           # Concurrent GC threads (G1 background)
# Rule: ConcGCThreads ≈ ParallelGCThreads / 4, min 1

# Check if CPU throttled in K8s:
kubectl exec -it <pod> -- cat /sys/fs/cgroup/cpu/cpu.stat
# throttled_time > 0 means the JVM is being starved
```

## 🔑 Key Takeaway
A 3x slowdown in prod K8s is usually GC thread misalignment with actual CPU limits, compounded by CFS throttling — always explicitly set GC thread counts in containers.
