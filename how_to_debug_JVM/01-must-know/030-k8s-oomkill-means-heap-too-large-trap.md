# #30 — "Kubernetes OOMKill Means the JVM's Heap Is Too Large"

> **Category:** Common Production Incidents | **Type:** Senior Trap Question | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"If Kubernetes OOM-kills the pod, that means we set the JVM heap too large, right?"

## 😊 Explain It Simply (for anyone)
The building manager (Kubernetes/the Linux kernel) doesn't care how tidy your personal closet (the JVM heap, controlled by `-Xmx`) is — it only cares about the *total weight* of everything in your entire apartment, including furniture in the hallway you don't normally think about (metaspace, thread stacks, native memory, and general JVM overhead). You could set your closet limit conservatively low and still get evicted, because all that "extra furniture" outside the closet pushed the total over the building's weight limit. So blaming the closet size alone is only looking at part of the picture.

## 📊 Visualize It
```
Container limit: 4GB
Heap (-Xmx2g): fits fine, looks "small enough"
  + Metaspace + Code cache + Thread stacks + Direct buffers + ~300MB overhead
  = total RSS can still exceed 4GB --> OOMKilled anyway
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG.** K8s OOMKill measures total container RSS, not JVM heap. A JVM with `-Xmx2g` can easily consume 3.5GB RSS because of metaspace, code cache, thread stacks, direct buffers, and JVM overhead.

**Correct answer:** RSS = heap + metaspace + code cache + (threads × stack size) + direct buffers + ~300MB JVM overhead. Set container memory limit = `-Xmx` + 1.0-1.5GB headroom. Use `-XX:MaxRAMPercentage=70` to let JVM self-size within container limits.

## 🔑 Key Takeaway
OOMKill is about total container RSS, not just heap size — always budget 1-1.5GB of headroom above `-Xmx` for everything else the JVM needs.
