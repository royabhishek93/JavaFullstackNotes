# #56 — Metaspace OOM vs. Heap OOM — Triage Difference

> **Category:** Memory Leaks End-to-End | **Type:** Advanced Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"You see `OutOfMemoryError: Metaspace` in production. Walk through your triage."

## 😊 Explain It Simply (for anyone)
The JVM has two different "storage rooms" that can each run out of space: the Heap (where your actual DATA/objects live — like customer records) and Metaspace (where the BLUEPRINTS of your classes live — like architectural drawings describing how to build each type of object). A "Heap OOM" means you have too much data. A "Metaspace OOM" means you have too many BLUEPRINTS — usually because the app keeps generating brand new blueprint copies (redeploying, or auto-generating proxy classes) faster than old ones get thrown away. Diagnosing one is very different from diagnosing the other — you don't look at your data, you look at how many "versions of the blueprints" are piling up.

## 📊 Visualize It
```
 Heap OOM                    Metaspace OOM
 --------                    -------------
 Too much DATA                Too many CLASS BLUEPRINTS
 (objects, arrays)            (class metadata, per redeploy)

 [Object] [Object] [Object]   [WebAppClassLoader_v1: 500 classes]
 [Object] [Object] ...        [WebAppClassLoader_v2: 500 classes]  <- v1 not freed!
                               [WebAppClassLoader_v3: 500 classes]
```

## 🏭 The Real Production Answer (15-YOE Level)

Metaspace stores class metadata. The two main causes:

1. **Classloader leak** (most common in web apps): old classloaders not GC'd on redeploy (described in Q3). Symptom: Metaspace grows by ~X MB on each redeploy, never released.

Diagnosis:
```bash
jcmd <pid> VM.classloaders      # lists classloaders and class counts
jcmd <pid> GC.heap_info         # check Metaspace committed vs. reserved
```

In MAT: search for `ClassLoader` instances. If you see 15 `WebAppClassLoader` instances after 15 redeploys, that's the leak.

2. **Dynamic class generation**: frameworks that generate proxy classes (CGLIB, Javassist, Byte-Buddy) can generate new classes on every request if misconfigured — e.g., creating a new `ProxyFactory` per request instead of reusing cached proxies.

Fix for dynamic generation: ensure proxy/enhancer caches are per-class not per-request:
```java
// WRONG: new ProxyFactory every call generates new class in Metaspace
ProxyFactory factory = new ProxyFactory();
factory.setSuperclass(MyService.class);

// RIGHT: cache the generated class or use Spring's singleton proxy
```

Sizing: as a stopgap, `-XX:MaxMetaspaceSize=512m` prevents JVM from consuming all native memory, but it just shifts the OOM earlier. The root cause must be fixed.

## 🔑 Key Takeaway
Metaspace OOM is almost always about too many class LOADERS or dynamically generated classes, not too much data — check `jcmd VM.classloaders` first.
