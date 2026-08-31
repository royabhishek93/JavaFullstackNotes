# #99 — "Default JVM flags are good enough for production"

> **Category:** JVM Tuning Production Playbook | **Type:** Senior Trap Question | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Default JVM flags are good enough for production."

## 😊 Explain It Simply (for anyone)
A brand-new car straight from the factory (JVM default settings) is tuned for the "average driver in average conditions" — it's not built with your company's specific highway (production workload) in mind. Out of the box, the car doesn't even have a dashcam recording what happened before a crash (GC logging is disabled by default), doesn't save the black box data after an accident (heap dumps disabled by default), and might just idle by the roadside confused instead of pulling over safely after a serious engine failure (the JVM tries to "continue" after an OOM instead of exiting cleanly). Before you drive this car on your production highway, you install a dashcam, a black box, and a few other safety upgrades — that's exactly what a minimum production flag set does for the JVM.

## 📊 Visualize It
```
 Default JVM                    Production-ready JVM
 ┌───────────────┐               ┌───────────────────────────┐
 │ GC logging: OFF│    ──────►   │ GC logging: ON (rotating)  │
 │ Heap dump: OFF │    ──────►   │ Heap dump on OOM: ON       │
 │ OOM: keep going│    ──────►   │ Exit on OOM: ON            │
 │ Code cache 240m│    ──────►   │ Code cache 512m            │
 └───────────────┘               └───────────────────────────┘
```

## 🏭 The Real Production Answer (15-YOE Level)
> "JVM ergonomic defaults are designed for development workloads and desktop applications.
> They're conservative and will fail you in production in several predictable ways.
>
> What the defaults get wrong:
>
> 1. Heap sizing: default max heap = 25% of physical RAM on host.
>    In a K8s container with 4GB limit, JVM sees HOST memory (say 64GB) and sets -Xmx=16GB.
>    Without UseContainerSupport or explicit Xmx, you immediately OOMKill.
>    (Thankfully UseContainerSupport is default from Java 8u191+, but explicit is better.)
>
> 2. GC logging: disabled by default.
>    When you have a production incident, you have no GC evidence.
>    Always add: -Xlog:gc*:file=/logs/gc.log:time,uptime:filecount=5,filesize=20m
>
> 3. Heap dump: disabled by default.
>    When OOM happens, you get a stack trace but no heap dump.
>    Always add: -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps/
>
> 4. OOM behavior: by default JVM logs the error and tries to continue.
>    A JVM in OOM state is thrashing, not serving requests.
>    Add: -XX:+ExitOnOutOfMemoryError
>
> 5. Code cache: default 240MB, often not enough for Spring Boot + libraries.
>    Code cache full = JIT disabled = severe performance degradation.
>    Add: -XX:ReservedCodeCacheSize=512m
>
> Minimum production flag set is 8-12 flags beyond defaults."

## 🔑 Key Takeaway
JVM defaults are tuned for development, not production incidents — always add explicit heap sizing, GC logging, heap-dump-on-OOM, exit-on-OOM, and a larger code cache before going live.
