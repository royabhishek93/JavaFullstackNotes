# How to Debug JVM — 151 Ranked Interview Q&As (15 YOE Prep)

**2026 Edition | Every question split into its own file, globally ranked #1 (most important) to #151 (niche) for a 15-years-experience Java/Spring Boot architect interview.**

Each file (`NNN-slug.md`) contains the same 5-part structure:
1. 🗣️ **The Interview Question** — verbatim
2. 😊 **Explain It Simply** — a plain-English, non-technical analogy anyone can follow
3. 📊 **Visualize It** — a small ASCII diagram of the problem/fix
4. 🏭 **The Real Production Answer (15-YOE Level)** — full original technical answer, code/commands preserved
5. 🔑 **Key Takeaway** — one sentence to say out loud in the interview

---

## Priority Tiers

| Tier | Rank Range | Count | Meaning |
|------|-----------|-------|---------|
| 🔥 Must-Know | #1–#31 | 31 | Absolute foundation — asked in nearly every senior/staff Java interview |
| ⭐ Should-Know | #32–#62 | 31 | Very commonly asked — strong signal of real production experience |
| 👍 Good-to-Know | #63–#104 | 42 | Good depth — differentiates senior from staff-level candidates |
| 📘 Advanced | #105–#130 | 26 | Deeper internals — virtual threads, ZGC, native image, JIT |
| ⚙️ Expert/Niche | #131–#144, #150–#151 | 16 | Specialist knowledge — less frequently asked but shows true depth |
| 🌐 Modern Observability | #145–#149 | 5 | 2026 additions — continuous eBPF profiling, APM-first triage, AI-assisted RCA |

---

## Folder Layout

Files are physically grouped into 3 folders by study priority:

| Folder | Contains | Count |
|--------|----------|-------|
| [01-must-know/](01-must-know/) | 🔥 Must-Know tier — #1–#31 | 31 |
| [02-should-know/](02-should-know/) | ⭐ Should-Know + 👍 Good-to-Know tiers — #32–#104 | 73 |
| [03-nice-to-know/](03-nice-to-know/) | 📘 Advanced + ⚙️ Expert/Niche + 🌐 Modern Observability tiers — #105–#151 | 47 |

The ranked index below still reflects the original 6-tier priority classification; use the tier labels to judge importance, and the folder column above to find the file on disk.

---

## Full Ranked Index (#1 → #151)

### 🔥 Must-Know (#1–#31)

| # | File | Question | Category | Type |
|---|------|----------|----------|------|
| 1 | [001-heap-space-oom-spring-boot-rest-api.md](01-must-know/001-heap-space-oom-spring-boot-rest-api.md) | Heap Space OOM in a Spring Boot REST API | Heap Dump Analysis | Scenario Q&A |
| 2 | [002-metaspace-oom-classloader-leak.md](01-must-know/002-metaspace-oom-classloader-leak.md) | Metaspace OOM from a Classloader Leak | Heap Dump Analysis | Scenario Q&A |
| 3 | [003-just-increase-heap-size-trap.md](01-must-know/003-just-increase-heap-size-trap.md) | "Just Increase Heap Size" — The Trap | Heap Dump Analysis | Senior Trap Question |
| 4 | [004-jmap-dump-safe-in-production-trap.md](01-must-know/004-jmap-dump-safe-in-production-trap.md) | "jmap -dump Is Safe in Production" — The Trap | Heap Dump Analysis | Senior Trap Question |
| 5 | [005-shallow-heap-vs-retained-heap-trap.md](01-must-know/005-shallow-heap-vs-retained-heap-trap.md) | Shallow Heap vs Retained Heap — The Trap | Heap Dump Analysis | Senior Trap Question |
| 6 | [006-ecommerce-checkout-dead-stop.md](01-must-know/006-ecommerce-checkout-dead-stop.md) | E-Commerce Checkout Dead Stop | Thread Dump Analysis | Scenario Q&A |
| 7 | [007-database-connection-pool-starvation.md](01-must-know/007-database-connection-pool-starvation.md) | Database Connection Pool Starvation | Thread Dump Analysis | Scenario Q&A |
| 8 | [008-deadlock-means-cpu-spikes-trap.md](01-must-know/008-deadlock-means-cpu-spikes-trap.md) | "A Deadlock Means the CPU Spikes to 100%" (Trap) | Thread Dump Analysis | Senior Trap Question |
| 9 | [009-k8s-pod-oomkilled-jvm-never-threw-oom-gc.md](01-must-know/009-k8s-pod-oomkilled-jvm-never-threw-oom-gc.md) | Our Kubernetes pod keeps getting OOMKilled but the JVM never throws OOM | GC Tuning & Debugging | Scenario Q&A |
| 10 | [010-more-heap-reduces-gc-frequency-trap.md](01-must-know/010-more-heap-reduces-gc-frequency-trap.md) | We should give the JVM as much heap as possible to reduce GC frequency | GC Tuning & Debugging | Senior Trap Question |
| 11 | [011-high-cpu-always-infinite-loop-trap.md](01-must-know/011-high-cpu-always-infinite-loop-trap.md) | "High CPU Always Means Infinite Loop" | CPU Profiling & Flame Graphs | Senior Trap Question |
| 12 | [012-jcmd-commands-first-when-ssh-prod-box.md](01-must-know/012-jcmd-commands-first-when-ssh-prod-box.md) | jcmd Commands to Run First When You SSH Into a Production Box | Production Debugging Tools | Scenario Q&A |
| 13 | [013-jstat-output-interpretation.md](01-must-know/013-jstat-output-interpretation.md) | Interpreting jstat Output in Production | Production Debugging Tools | Scenario Q&A |
| 14 | [014-jmap-vs-jcmd-for-heap-dump.md](01-must-know/014-jmap-vs-jcmd-for-heap-dump.md) | jmap vs jcmd for Heap Dumps — Which Do You Use? | Production Debugging Tools | Scenario Q&A |
| 15 | [015-reading-jstat-columns-interview-quiz.md](01-must-know/015-reading-jstat-columns-interview-quiz.md) | Reading jstat Columns — Interview Quiz | Production Debugging Tools | Scenario Q&A |
| 16 | [016-jcmd-native-memory-vs-xmx-hidden-gap.md](01-must-know/016-jcmd-native-memory-vs-xmx-hidden-gap.md) | jcmd VM.native_memory vs -Xmx — The Hidden Memory Gap | Production Debugging Tools | Advanced Scenario Q&A |
| 17 | [017-jmap-dump-is-standard-way-trap.md](01-must-know/017-jmap-dump-is-standard-way-trap.md) | "jmap -dump Is the Standard Way to Get a Heap Dump" — Trap | Production Debugging Tools | Senior Trap Question |
| 18 | [018-threadlocal-leak-in-thread-pool-leaks-file.md](01-must-know/018-threadlocal-leak-in-thread-pool-leaks-file.md) | ThreadLocal Leak in Thread Pool | Memory Leaks End-to-End | Scenario Q&A |
| 19 | [019-microservice-oomkilled-k8s-despite-low-heap.md](01-must-know/019-microservice-oomkilled-k8s-despite-low-heap.md) | Microservice Getting OOMKilled in K8s Despite Low Heap Usage | JVM Tuning Production Playbook | Scenario Q&A |
| 20 | [020-set-xmx-as-large-as-possible-trap.md](01-must-know/020-set-xmx-as-large-as-possible-trap.md) | "We should set -Xmx as large as possible to avoid OOM" | JVM Tuning Production Playbook | Senior Trap Question |
| 21 | [021-jvm-uses-exactly-xmx-memory-trap.md](01-must-know/021-jvm-uses-exactly-xmx-memory-trap.md) | "The JVM uses exactly -Xmx memory, so if -Xmx is 4GB, the process uses 4GB" | JVM Tuning Production Playbook | Senior Trap Question |
| 22 | [022-restarting-fixed-memory-issue-trap.md](01-must-know/022-restarting-fixed-memory-issue-trap.md) | "Restarting the service fixed our memory issue, so we're good" | JVM Tuning Production Playbook | Senior Trap Question |
| 23 | [023-outofmemoryerror-java-heap-space-incident.md](01-must-know/023-outofmemoryerror-java-heap-space-incident.md) | OutOfMemoryError: Java Heap Space | Common Production Incidents | Scenario Q&A |
| 24 | [024-high-cpu-100-not-a-code-loop-incident.md](01-must-know/024-high-cpu-100-not-a-code-loop-incident.md) | High CPU (100%) — Not a Code Loop | Common Production Incidents | Scenario Q&A |
| 25 | [025-application-completely-frozen-deadlock-incident.md](01-must-know/025-application-completely-frozen-deadlock-incident.md) | Application Completely Frozen — Deadlock | Common Production Incidents | Scenario Q&A |
| 26 | [026-slow-responses-connection-pool-exhaustion-incident.md](01-must-know/026-slow-responses-connection-pool-exhaustion-incident.md) | Slow Responses Under Load — Connection Pool Exhaustion | Common Production Incidents | Scenario Q&A |
| 27 | [027-oom-killed-by-kubernetes-jvm-never-threw-oom-incident.md](01-must-know/027-oom-killed-by-kubernetes-jvm-never-threw-oom-incident.md) | OOM-Killed by Kubernetes — JVM Never Threw OOM | Common Production Incidents | Scenario Q&A |
| 28 | [028-high-cpu-always-app-in-loop-trap.md](01-must-know/028-high-cpu-always-app-in-loop-trap.md) | "High CPU Always Means My Application Code Is in a Loop" | Common Production Incidents | Senior Trap Question |
| 29 | [029-restart-fixes-the-production-incident-trap.md](01-must-know/029-restart-fixes-the-production-incident-trap.md) | "A Restart Fixes the Production Incident" | Common Production Incidents | Senior Trap Question |
| 30 | [030-k8s-oomkill-means-heap-too-large-trap.md](01-must-know/030-k8s-oomkill-means-heap-too-large-trap.md) | "Kubernetes OOMKill Means the JVM's Heap Is Too Large" | Common Production Incidents | Senior Trap Question |
| 31 | [031-just-increase-heap-to-fix-oom-incidents-trap.md](01-must-know/031-just-increase-heap-to-fix-oom-incidents-trap.md) | "Just Increase the Heap to Fix OOM Incidents" | Common Production Incidents | Senior Trap Question |

### ⭐ Should-Know (#32–#62)

| # | File | Question | Category | Type |
|---|------|----------|----------|------|
| 32 | [032-gc-overhead-limit-exceeded.md](02-should-know/032-gc-overhead-limit-exceeded.md) | GC Overhead Limit Exceeded vs Heap Space OOM | Heap Dump Analysis | Scenario Q&A |
| 33 | [033-static-collection-grows-without-bound.md](02-should-know/033-static-collection-grows-without-bound.md) | Diagnosing an Unbounded Static Collection Leak | Heap Dump Analysis | Scenario Q&A |
| 34 | [034-threadlocal-leak-in-thread-pool-heap.md](02-should-know/034-threadlocal-leak-in-thread-pool-heap.md) | ThreadLocal Leak in a Thread Pool | Heap Dump Analysis | Advanced Scenario Q&A |
| 35 | [035-metaspace-oom-add-more-memory-trap.md](02-should-know/035-metaspace-oom-add-more-memory-trap.md) | "Metaspace OOM = Not Enough Memory, Add More" — The Trap | Heap Dump Analysis | Senior Trap Question |
| 36 | [036-rest-api-503-waiting-threads.md](02-should-know/036-rest-api-503-waiting-threads.md) | REST API 503ing With WAITING Threads | Thread Dump Analysis | Scenario Q&A |
| 37 | [037-add-more-threads-to-handle-load-trap.md](02-should-know/037-add-more-threads-to-handle-load-trap.md) | "Add More Threads to Handle the Load" (Trap) | Thread Dump Analysis | Senior Trap Question |
| 38 | [038-thread-pool-size-equals-cpu-cores-trap.md](02-should-know/038-thread-pool-size-equals-cpu-cores-trap.md) | "Thread Pool Size Should Equal CPU Core Count" (Trap) | Thread Dump Analysis | Senior Trap Question |
| 39 | [039-waiting-threads-are-a-bug-trap.md](02-should-know/039-waiting-threads-are-a-bug-trap.md) | "All Those WAITING Threads Are a Bug" (Trap) | Thread Dump Analysis | Senior Trap Question |
| 40 | [040-p99-latency-spike-correlate-gc.md](02-should-know/040-p99-latency-spike-correlate-gc.md) | Our API p99 latency spiked from 80ms to 2 seconds intermittently | GC Tuning & Debugging | Scenario Q&A |
| 41 | [041-gc-overhead-limit-exceeded-gc-file.md](02-should-know/041-gc-overhead-limit-exceeded-gc-file.md) | We're getting java.lang.OutOfMemoryError: GC overhead limit exceeded | GC Tuning & Debugging | Scenario Q&A |
| 42 | [042-metaspace-fills-up-after-3-days.md](02-should-know/042-metaspace-fills-up-after-3-days.md) | After our microservice runs for 3 days, Metaspace fills up and causes Full GC | GC Tuning & Debugging | Scenario Q&A |
| 43 | [043-g1gc-full-gc-despite-free-heap-humongous.md](02-should-know/043-g1gc-full-gc-despite-free-heap-humongous.md) | G1GC keeps triggering Full GC even though heap has plenty of free space | GC Tuning & Debugging | Scenario Q&A |
| 44 | [044-maxgcpausemillis-guarantee-trap.md](02-should-know/044-maxgcpausemillis-guarantee-trap.md) | MaxGCPauseMillis=50 guarantees my GC pauses are under 50ms, right? | GC Tuning & Debugging | Senior Trap Question |
| 45 | [045-cpu-spike-after-traffic-increase-regex.md](02-should-know/045-cpu-spike-after-traffic-increase-regex.md) | Service CPU Spike After Traffic Increase | CPU Profiling & Flame Graphs | Scenario Q&A |
| 46 | [046-string-operations-in-hot-path.md](02-should-know/046-string-operations-in-hot-path.md) | String Operations in the Hot Path | CPU Profiling & Flame Graphs | Scenario Q&A |
| 47 | [047-jvisualvm-fine-for-prod-profiling-trap.md](02-should-know/047-jvisualvm-fine-for-prod-profiling-trap.md) | "JVisualVM Is Fine for Production Profiling" | CPU Profiling & Flame Graphs | Senior Trap Question |
| 48 | [048-live-debugging-spring-actuator.md](02-should-know/048-live-debugging-spring-actuator.md) | Live Debugging with Spring Boot Actuator | Production Debugging Tools | Scenario Q&A |
| 49 | [049-nmt-finding-native-memory-growth.md](02-should-know/049-nmt-finding-native-memory-growth.md) | NMT — Finding Native Memory Growth Beyond -Xmx | Production Debugging Tools | Advanced Scenario Q&A |
| 50 | [050-jstack-f-safe-for-stuck-jvm-trap.md](02-should-know/050-jstack-f-safe-for-stuck-jvm-trap.md) | "jstack -F Is Safe for a Stuck JVM" — Trap | Production Debugging Tools | Senior Trap Question |
| 51 | [051-jstat-shows-real-time-gc-pauses-trap.md](02-should-know/051-jstat-shows-real-time-gc-pauses-trap.md) | "jstat Shows Real-Time GC Pauses" — Trap | Production Debugging Tools | Senior Trap Question |
| 52 | [052-actuator-heapdump-is-production-safe-trap.md](02-should-know/052-actuator-heapdump-is-production-safe-trap.md) | "Spring Actuator /heapdump Is Production-Safe" — Trap | Production Debugging Tools | Senior Trap Question |
| 53 | [053-static-collections-leak.md](02-should-know/053-static-collections-leak.md) | Static Collections Leak | Memory Leaks End-to-End | Scenario Q&A |
| 54 | [054-classloader-leak-on-redeployment.md](02-should-know/054-classloader-leak-on-redeployment.md) | Classloader Leak on Redeployment | Memory Leaks End-to-End | Scenario Q&A |
| 55 | [055-cache-without-eviction.md](02-should-know/055-cache-without-eviction.md) | Cache Without Eviction | Memory Leaks End-to-End | Scenario Q&A |
| 56 | [056-metaspace-vs-heap-oom-triage-difference.md](02-should-know/056-metaspace-vs-heap-oom-triage-difference.md) | Metaspace OOM vs. Heap OOM — Triage Difference | Memory Leaks End-to-End | Advanced Scenario Q&A |
| 57 | [057-weakreference-prevents-memory-leaks-trap.md](02-should-know/057-weakreference-prevents-memory-leaks-trap.md) | "WeakReference Prevents Memory Leaks" | Memory Leaks End-to-End | Senior Trap Question |
| 58 | [058-garbage-collector-will-clean-up-trap.md](02-should-know/058-garbage-collector-will-clean-up-trap.md) | "The Garbage Collector Will Clean Up" | Memory Leaks End-to-End | Senior Trap Question |
| 59 | [059-memory-usage-growing-means-leak-trap.md](02-should-know/059-memory-usage-growing-means-leak-trap.md) | "Memory Usage Growing Means There's a Memory Leak" | Memory Leaks End-to-End | Senior Trap Question |
| 60 | [060-more-jvm-threads-means-more-concurrency-trap.md](02-should-know/060-more-jvm-threads-means-more-concurrency-trap.md) | "More JVM threads means more concurrency and better throughput" | JVM Tuning Production Playbook | Senior Trap Question |
| 61 | [061-memory-leak-gradual-oom-over-days-incident.md](02-should-know/061-memory-leak-gradual-oom-over-days-incident.md) | Memory Leak — Gradual OOM Over Days | Common Production Incidents | Scenario Q&A |
| 62 | [062-hikaricp-timeout-means-db-slow-trap.md](02-should-know/062-hikaricp-timeout-means-db-slow-trap.md) | "HikariCP Connection Timeout Means the Database Is Slow" | Common Production Incidents | Senior Trap Question |

### 👍 Good-to-Know (#63–#104)

| # | File | Question | Category | Type |
|---|------|----------|----------|------|
| 63 | [063-direct-buffer-memory-oom-netty-leak.md](02-should-know/063-direct-buffer-memory-oom-netty-leak.md) | Direct Buffer Memory OOM in a Netty Service | Heap Dump Analysis | Scenario Q&A |
| 64 | [064-unable-to-create-native-thread.md](02-should-know/064-unable-to-create-native-thread.md) | "Unable to Create Native Thread" Is Not a Heap Problem | Heap Dump Analysis | Scenario Q&A |
| 65 | [065-hibernate-osiv-memory-accumulation.md](02-should-know/065-hibernate-osiv-memory-accumulation.md) | Hibernate OSIV Causing Slow Memory Accumulation | Heap Dump Analysis | Scenario Q&A |
| 66 | [066-http-client-connection-pool-response-body-leak.md](02-should-know/066-http-client-connection-pool-response-body-leak.md) | HTTP Client Connection Pool + Unconsumed Response Body Leak | Heap Dump Analysis | Scenario Q&A |
| 67 | [067-heap-dump-anytime-trap.md](02-should-know/067-heap-dump-anytime-trap.md) | "Heap Dump Captures Current State — Take It Anytime" — The Trap | Heap Dump Analysis | Senior Trap Question |
| 68 | [068-payment-service-random-freezes.md](02-should-know/068-payment-service-random-freezes.md) | Payment Service Random Freezes | Thread Dump Analysis | Scenario Q&A |
| 69 | [069-batch-job-hanging-synchronized-bottleneck.md](02-should-know/069-batch-job-hanging-synchronized-bottleneck.md) | Batch Job Hanging on a Synchronized Bottleneck | Thread Dump Analysis | Scenario Q&A |
| 70 | [070-microservice-memory-leak-plus-thread-leak.md](02-should-know/070-microservice-memory-leak-plus-thread-leak.md) | Microservice Memory Leak Plus Thread Leak | Thread Dump Analysis | Scenario Q&A |
| 71 | [071-producer-consumer-deadlock.md](02-should-know/071-producer-consumer-deadlock.md) | Producer-Consumer Deadlock | Thread Dump Analysis | Scenario Q&A |
| 72 | [072-kill-deadlocked-thread-to-resolve-trap.md](02-should-know/072-kill-deadlocked-thread-to-resolve-trap.md) | "Just Kill the Deadlocked Thread to Resolve It" (Trap) | Thread Dump Analysis | Senior Trap Question |
| 73 | [073-young-gc-pauses-exceed-target.md](02-should-know/073-young-gc-pauses-exceed-target.md) | Young GC pauses are 300ms but we set MaxGCPauseMillis=100 | GC Tuning & Debugging | Scenario Q&A |
| 74 | [074-diagnosing-promotion-failure.md](02-should-know/074-diagnosing-promotion-failure.md) | Walk through diagnosing a promotion failure | GC Tuning & Debugging | Advanced Scenario Q&A |
| 75 | [075-full-gc-always-production-incident-trap.md](02-should-know/075-full-gc-always-production-incident-trap.md) | Full GC is always a production incident | GC Tuning & Debugging | Senior Trap Question |
| 76 | [076-tune-gc-flags-to-fix-memory-problem-trap.md](02-should-know/076-tune-gc-flags-to-fix-memory-problem-trap.md) | Let's tune GC flags to fix our memory problem | GC Tuning & Debugging | Senior Trap Question |
| 77 | [077-cpu-spike-no-traffic-increase-2am.md](02-should-know/077-cpu-spike-no-traffic-increase-2am.md) | CPU Spike With No Traffic Increase | CPU Profiling & Flame Graphs | Scenario Q&A |
| 78 | [078-specific-endpoint-slow-others-fine.md](02-should-know/078-specific-endpoint-slow-others-fine.md) | Specific Endpoint Slow, Others Fine | CPU Profiling & Flame Graphs | Scenario Q&A |
| 79 | [079-thread-contention-cpu-spin-busy-loop.md](02-should-know/079-thread-contention-cpu-spin-busy-loop.md) | Thread Contention Causing CPU Spin | CPU Profiling & Flame Graphs | Scenario Q&A |
| 80 | [080-memory-allocation-storm-driving-gc-cpu.md](02-should-know/080-memory-allocation-storm-driving-gc-cpu.md) | Memory Allocation Storm Driving GC CPU | CPU Profiling & Flame Graphs | Scenario Q&A |
| 81 | [081-hashmap-with-bad-hashcode.md](02-should-know/081-hashmap-with-bad-hashcode.md) | HashMap With a Bad hashCode() | CPU Profiling & Flame Graphs | Scenario Q&A |
| 82 | [082-flame-graph-x-axis-is-time-order-trap.md](02-should-know/082-flame-graph-x-axis-is-time-order-trap.md) | "Flame Graph X-Axis Is Time Order" | CPU Profiling & Flame Graphs | Senior Trap Question |
| 83 | [083-fix-the-hottest-method-first-trap.md](02-should-know/083-fix-the-hottest-method-first-trap.md) | "Fix the Hottest Method First" | CPU Profiling & Flame Graphs | Senior Trap Question |
| 84 | [084-find-slow-method-live-arthas-trace.md](02-should-know/084-find-slow-method-live-arthas-trace.md) | Find the Slow Method in a Live Spring Boot Service — No Restart Allowed | Production Debugging Tools | Scenario Q&A |
| 85 | [085-arthas-in-production-safe-vs-risky.md](02-should-know/085-arthas-in-production-safe-vs-risky.md) | Arthas in Production — What's Safe vs Risky | Production Debugging Tools | Scenario Q&A |
| 86 | [086-jfr-always-on-profiling-setup.md](02-should-know/086-jfr-always-on-profiling-setup.md) | Setting Up JFR for Always-On Production Profiling | Production Debugging Tools | Scenario Q&A |
| 87 | [087-arthas-changes-code-permanently-trap.md](02-should-know/087-arthas-changes-code-permanently-trap.md) | "Arthas Changes Production Code Permanently" — Trap | Production Debugging Tools | Senior Trap Question |
| 88 | [088-more-jstat-columns-means-more-gc-trap.md](02-should-know/088-more-jstat-columns-means-more-gc-trap.md) | "More jstat GC Columns Means More GC Happening" — Trap | Production Debugging Tools | Senior Trap Question |
| 89 | [089-unclosed-resources-try-with-resources.md](02-should-know/089-unclosed-resources-try-with-resources.md) | Unclosed Resources (try-with-resources) | Memory Leaks End-to-End | Scenario Q&A |
| 90 | [090-hibernate-jpa-entitymanager-leak.md](02-should-know/090-hibernate-jpa-entitymanager-leak.md) | Hibernate/JPA EntityManager Leak | Memory Leaks End-to-End | Scenario Q&A |
| 91 | [091-jvm-flags-proactive-memory-leak-detection.md](02-should-know/091-jvm-flags-proactive-memory-leak-detection.md) | JVM Flags for Proactive Memory Leak Detection | Memory Leaks End-to-End | Advanced Scenario Q&A |
| 92 | [092-closing-in-finally-block-means-no-leak-trap.md](02-should-know/092-closing-in-finally-block-means-no-leak-trap.md) | "Closing in Finally Block Means No Leak" | Memory Leaks End-to-End | Senior Trap Question |
| 93 | [093-fixed-the-leak-heap-is-stable-trap.md](02-should-know/093-fixed-the-leak-heap-is-stable-trap.md) | "We Fixed the Leak — Heap Is Stable" | Memory Leaks End-to-End | Senior Trap Question |
| 94 | [094-p99-latency-spikes-every-2-hours.md](02-should-know/094-p99-latency-spikes-every-2-hours.md) | P99 Latency Spikes Every 2 Hours | JVM Tuning Production Playbook | Scenario Q&A |
| 95 | [095-new-deployment-slow-first-5-minutes.md](02-should-know/095-new-deployment-slow-first-5-minutes.md) | New Deployment is Slow for First 5 Minutes | JVM Tuning Production Playbook | Scenario Q&A |
| 96 | [096-high-cpu-after-deployment-low-traffic.md](02-should-know/096-high-cpu-after-deployment-low-traffic.md) | High CPU Usage After Deployment Despite Low Traffic | JVM Tuning Production Playbook | Scenario Q&A |
| 97 | [097-metaspace-oom-in-production-groovy.md](02-should-know/097-metaspace-oom-in-production-groovy.md) | Metaspace OutOfMemoryError in Production | JVM Tuning Production Playbook | Scenario Q&A |
| 98 | [098-thread-count-growing-unboundedly.md](02-should-know/098-thread-count-growing-unboundedly.md) | Spring Boot Service Thread Count Growing Unboundedly | JVM Tuning Production Playbook | Scenario Q&A |
| 99 | [099-default-jvm-flags-good-enough-trap.md](02-should-know/099-default-jvm-flags-good-enough-trap.md) | "Default JVM flags are good enough for production" | JVM Tuning Production Playbook | Senior Trap Question |
| 100 | [100-g1gc-always-better-than-parallel-trap.md](02-should-know/100-g1gc-always-better-than-parallel-trap.md) | "G1GC always performs better than Parallel GC because it's newer" | JVM Tuning Production Playbook | Senior Trap Question |
| 101 | [101-stackoverflowerror-incident.md](02-should-know/101-stackoverflowerror-incident.md) | StackOverflowError | Common Production Incidents | Scenario Q&A |
| 102 | [102-thread-pool-rejection-incident.md](02-should-know/102-thread-pool-rejection-incident.md) | Thread Pool Rejection — RejectedExecutionException | Common Production Incidents | Scenario Q&A |
| 103 | [103-slow-startup-high-memory-on-startup-incident.md](02-should-know/103-slow-startup-high-memory-on-startup-incident.md) | Slow Startup / High Memory on Startup | Common Production Incidents | Scenario Q&A |
| 104 | [104-stackoverflow-always-infinite-recursion-trap.md](02-should-know/104-stackoverflow-always-infinite-recursion-trap.md) | "StackOverflow Always Means Infinite Recursion" | Common Production Incidents | Senior Trap Question |

### 📘 Advanced (#105–#130)

| # | File | Question | Category | Type |
|---|------|----------|----------|------|
| 105 | [105-oom-in-thread-x-means-thread-x-has-leak-trap.md](03-nice-to-know/105-oom-in-thread-x-means-thread-x-has-leak-trap.md) | "OOM in Thread X" Doesn't Mean Thread X Has the Leak | Heap Dump Analysis | Senior Trap Question |
| 106 | [106-completablefuture-blocking-main-pool.md](03-nice-to-know/106-completablefuture-blocking-main-pool.md) | CompletableFuture Blocking the Main Pool | Thread Dump Analysis | Scenario Q&A |
| 107 | [107-virtual-threads-carrier-thread-pinning.md](03-nice-to-know/107-virtual-threads-carrier-thread-pinning.md) | Virtual Threads and Carrier Thread Pinning | Thread Dump Analysis | Advanced Scenario Q&A |
| 108 | [108-lock-free-alternative-analysis.md](03-nice-to-know/108-lock-free-alternative-analysis.md) | Lock-Free Alternative Analysis | Thread Dump Analysis | Advanced Scenario Q&A |
| 109 | [109-async-code-is-non-blocking-trap.md](03-nice-to-know/109-async-code-is-non-blocking-trap.md) | "Thread Dump Shows My Async Code Is Non-Blocking" (Trap) | Thread Dump Analysis | Senior Trap Question |
| 110 | [110-zgc-migration-throughput-drop.md](03-nice-to-know/110-zgc-migration-throughput-drop.md) | We migrated to ZGC and our throughput dropped 25% | GC Tuning & Debugging | Scenario Q&A |
| 111 | [111-zgc-best-gc-use-everywhere-trap.md](03-nice-to-know/111-zgc-best-gc-use-everywhere-trap.md) | ZGC is the best GC — we should use it everywhere in production | GC Tuning & Debugging | Senior Trap Question |
| 112 | [112-xms-equals-xmx-always-good-practice-trap.md](03-nice-to-know/112-xms-equals-xmx-always-good-practice-trap.md) | Setting -Xms equal to -Xmx prevents heap resizing overhead and is always good practice | GC Tuning & Debugging | Senior Trap Question |
| 113 | [113-reflection-heavy-code-after-library-upgrade.md](03-nice-to-know/113-reflection-heavy-code-after-library-upgrade.md) | Reflection-Heavy Code Path After Library Upgrade | CPU Profiling & Flame Graphs | Scenario Q&A |
| 114 | [114-profiling-async-reactive-code-webflux.md](03-nice-to-know/114-profiling-async-reactive-code-webflux.md) | Profiling Async/Reactive Code (WebFlux) | CPU Profiling & Flame Graphs | Advanced Scenario Q&A |
| 115 | [115-container-cpu-throttling-vs-jvm-cpu.md](03-nice-to-know/115-container-cpu-throttling-vs-jvm-cpu.md) | Container CPU Throttling vs JVM CPU | CPU Profiling & Flame Graphs | Advanced Scenario Q&A |
| 116 | [116-profile-in-dev-same-as-prod-trap.md](03-nice-to-know/116-profile-in-dev-same-as-prod-trap.md) | "Profile in Dev, Get the Same Results as Prod" | CPU Profiling & Flame Graphs | Senior Trap Question |
| 117 | [117-async-profiler-always-safe-max-out-trap.md](03-nice-to-know/117-async-profiler-always-safe-max-out-trap.md) | "async-profiler Is Always Safe — Max It Out" | CPU Profiling & Flame Graphs | Senior Trap Question |
| 118 | [118-programmatic-jmx-monitoring.md](03-nice-to-know/118-programmatic-jmx-monitoring.md) | Programmatic JMX Monitoring in Java | Production Debugging Tools | Advanced Scenario Q&A |
| 119 | [119-inner-anonymous-class-holding-outer-ref.md](03-nice-to-know/119-inner-anonymous-class-holding-outer-ref.md) | Inner/Anonymous Class Holding Outer Reference | Memory Leaks End-to-End | Scenario Q&A |
| 120 | [120-string-intern-abuse.md](03-nice-to-know/120-string-intern-abuse.md) | String.intern() Abuse | Memory Leaks End-to-End | Scenario Q&A |
| 121 | [121-dom-parsing-large-xml-oom.md](03-nice-to-know/121-dom-parsing-large-xml-oom.md) | DOM Parsing Large XML → OOM | Memory Leaks End-to-End | Scenario Q&A |
| 122 | [122-completablefuture-chain-leak.md](03-nice-to-know/122-completablefuture-chain-leak.md) | CompletableFuture Chain Leak | Memory Leaks End-to-End | Scenario Q&A |
| 123 | [123-heap-dump-no-single-large-object-distributed-leak.md](03-nice-to-know/123-heap-dump-no-single-large-object-distributed-leak.md) | Heap Dump Shows No Single Large Object — Distributed Leak | Memory Leaks End-to-End | Advanced Scenario Q&A |
| 124 | [124-memory-leak-in-reactive-webflux-application.md](03-nice-to-know/124-memory-leak-in-reactive-webflux-application.md) | Memory Leak in Reactive/WebFlux Application | Memory Leaks End-to-End | Advanced Scenario Q&A |
| 125 | [125-leak-is-in-library-not-my-code-trap.md](03-nice-to-know/125-leak-is-in-library-not-my-code-trap.md) | "The Leak Is in the Library, Not My Code" | Memory Leaks End-to-End | Senior Trap Question |
| 126 | [126-oomkills-after-leak-fix-before-restart.md](03-nice-to-know/126-oomkills-after-leak-fix-before-restart.md) | Service OOMKills After Memory Leak Fix But Before Restart | JVM Tuning Production Playbook | Scenario Q&A |
| 127 | [127-kafka-consumer-10-second-gc-pauses.md](03-nice-to-know/127-kafka-consumer-10-second-gc-pauses.md) | Kafka Consumer Service with 10-Second GC Pauses | JVM Tuning Production Playbook | Scenario Q&A |
| 128 | [128-zgc-vs-shenandoah-when-to-choose.md](03-nice-to-know/128-zgc-vs-shenandoah-when-to-choose.md) | ZGC vs Shenandoah — When to Choose Which | JVM Tuning Production Playbook | Advanced Scenario Q&A |
| 129 | [129-virtual-threads-deep-dive-pinning-monitoring.md](03-nice-to-know/129-virtual-threads-deep-dive-pinning-monitoring.md) | Virtual Threads Deep Dive — Pinning and Monitoring | JVM Tuning Production Playbook | Advanced Scenario Q&A |
| 130 | [130-jvm-native-crash-hs-err-pid-incident.md](03-nice-to-know/130-jvm-native-crash-hs-err-pid-incident.md) | JVM Native Crash (hs_err_pid file) | Common Production Incidents | Scenario Q&A |

### ⚙️ Expert/Niche (#131–#144)

| # | File | Question | Category | Type |
|---|------|----------|----------|------|
| 131 | [131-multiple-pods-oom-killing-simultaneously-k8s.md](03-nice-to-know/131-multiple-pods-oom-killing-simultaneously-k8s.md) | Multiple Kubernetes Pods OOM-Killing Simultaneously | Heap Dump Analysis | Advanced Scenario Q&A |
| 132 | [132-memory-leak-only-in-production-not-staging.md](03-nice-to-know/132-memory-leak-only-in-production-not-staging.md) | Memory Leak That Only Reproduces in Production | Heap Dump Analysis | Advanced Scenario Q&A |
| 133 | [133-metaspace-growing-dynamic-proxy-explosion.md](03-nice-to-know/133-metaspace-growing-dynamic-proxy-explosion.md) | Metaspace Growing From Dynamic Proxy / Reflection Explosion | Heap Dump Analysis | Advanced Scenario Q&A |
| 134 | [134-programmatic-deadlock-detection-threadmxbean.md](03-nice-to-know/134-programmatic-deadlock-detection-threadmxbean.md) | Programmatic Deadlock Detection with ThreadMXBean | Thread Dump Analysis | Advanced Scenario Q&A |
| 135 | [135-thread-dump-comparison-across-time.md](03-nice-to-know/135-thread-dump-comparison-across-time.md) | Thread Dump Comparison Across Time | Thread Dump Analysis | Advanced Scenario Q&A |
| 136 | [136-nightly-batch-3x-slower-prod-k8s-throttled.md](03-nice-to-know/136-nightly-batch-3x-slower-prod-k8s-throttled.md) | Nightly batch job runs fine on dev but runs 3x slower in prod Kubernetes | GC Tuning & Debugging | Scenario Q&A |
| 137 | [137-g1gc-concurrent-mark-cycle-fails.md](03-nice-to-know/137-g1gc-concurrent-mark-cycle-fails.md) | Explain G1GC concurrent mark cycle and when it fails | GC Tuning & Debugging | Advanced Scenario Q&A |
| 138 | [138-zgc-sub-ms-pauses-100gb-heap.md](03-nice-to-know/138-zgc-sub-ms-pauses-100gb-heap.md) | How does ZGC achieve sub-millisecond pauses on a 100GB heap? | GC Tuning & Debugging | Advanced Scenario Q&A |
| 139 | [139-jit-deoptimization-intermittent-cpu-spikes.md](03-nice-to-know/139-jit-deoptimization-intermittent-cpu-spikes.md) | JIT Deoptimization Causing Intermittent CPU Spikes | CPU Profiling & Flame Graphs | Advanced Scenario Q&A |
| 140 | [140-comparing-flame-graphs-before-after.md](03-nice-to-know/140-comparing-flame-graphs-before-after.md) | Comparing Two Flame Graphs (Before/After) | CPU Profiling & Flame Graphs | Advanced Scenario Q&A |
| 141 | [141-arthas-ognl-expressions-advanced-usage.md](03-nice-to-know/141-arthas-ognl-expressions-advanced-usage.md) | Arthas OGNL Expressions — Advanced Live State Inspection | Production Debugging Tools | Advanced Scenario Q&A |
| 142 | [142-graalvm-native-image-tradeoffs.md](03-nice-to-know/142-graalvm-native-image-tradeoffs.md) | GraalVM Native Image — Real Production Trade-offs | JVM Tuning Production Playbook | Advanced Scenario Q&A |
| 143 | [143-jit-compilation-slower-after-warmup.md](03-nice-to-know/143-jit-compilation-slower-after-warmup.md) | JIT Compilation — When Code Gets SLOWER After Warmup | JVM Tuning Production Playbook | Advanced Scenario Q&A |
| 144 | [144-satb-write-barrier-g1gc-correctness.md](03-nice-to-know/144-satb-write-barrier-g1gc-correctness.md) | Explain the SATB write barrier and why it matters for G1GC correctness | GC Tuning & Debugging | Advanced Scenario Q&A |

### 🌐 Modern Observability (#145–#149) — 2026 additions

| # | File | Question | Category | Type |
|---|------|----------|----------|------|
| 145 | [145-continuous-ebpf-profiling-pyroscope-parca.md](03-nice-to-know/145-continuous-ebpf-profiling-pyroscope-parca.md) | Fleet-Wide Continuous Profiling with eBPF (Grafana Pyroscope / Parca) | Modern Observability (2026) | Scenario Q&A |
| 146 | [146-apm-first-triage-datadog-newrelic-dynatrace.md](03-nice-to-know/146-apm-first-triage-datadog-newrelic-dynatrace.md) | APM-First Triage (Datadog / New Relic / Dynatrace) Before Touching CLI Tools | Modern Observability (2026) | Scenario Q&A |
| 147 | [147-apm-dashboard-green-trap.md](03-nice-to-know/147-apm-dashboard-green-trap.md) | "The APM Dashboard Is All Green, So Nothing Is Wrong" | Modern Observability (2026) | Senior Trap Question |
| 148 | [148-ai-assisted-heap-thread-dump-analysis.md](03-nice-to-know/148-ai-assisted-heap-thread-dump-analysis.md) | Using AI/LLMs to Accelerate Heap & Thread Dump Root Cause Analysis | Modern Observability (2026) | Advanced Scenario Q&A |
| 149 | [149-ebpf-profiling-zero-overhead-trap.md](03-nice-to-know/149-ebpf-profiling-zero-overhead-trap.md) | "eBPF Profiling Has Zero Overhead, So Just Leave It Always On Everywhere" | Modern Observability (2026) | Senior Trap Question |

### ⚙️ Expert/Niche (#150–#151) — additional deep-dive tooling

| # | File | Question | Category | Type |
|---|------|----------|----------|------|
| 150 | [150-remote-debugging-jdwp-production-risks.md](03-nice-to-know/150-remote-debugging-jdwp-production-risks.md) | Remote Debugging a Live JVM (JDWP/jdb) — What's Actually Safe in Production | Production Debugging Tools | Advanced Scenario Q&A |
| 151 | [151-safepoint-pause-diagnosis-printsafepointstatistics.md](03-nice-to-know/151-safepoint-pause-diagnosis-printsafepointstatistics.md) | Diagnosing "Stop-the-World" Pauses That Aren't GC (Safepoint Diagnosis) | GC Tuning & Debugging | Advanced Scenario Q&A |

---

## How To Use This

- **1 week before interview:** read tiers 🔥 and ⭐ (files #1–#62) — covers ~95% of what gets asked
- **Day before interview:** skim 👍 Good-to-Know (#63–#104) for depth questions
- **If applying for Staff/Principal:** also read 📘 Advanced and ⚙️ Expert/Niche (#105–#144)
- **If the role touches production observability/on-call:** read 🌐 Modern Observability (#145–#149) — continuous profiling, APM-first triage, and AI-assisted RCA are now routinely asked alongside classic CLI tooling
- Each file is self-contained — read in any order, or follow the rank sequence top to bottom

## Source Topics (for reference)

| Topic | Original Focus |
|-------|----------------|
| Heap Dump Analysis | OOM debugging, MAT, dominator tree, retained vs shallow heap |
| Thread Dump Analysis | Deadlocks, jstack, thread states, virtual threads |
| GC Tuning & Debugging | G1GC, ZGC, GC logs, humongous objects, SATB |
| CPU Profiling & Flame Graphs | async-profiler, JFR, JIT, flame graph reading |
| Production Debugging Tools | jcmd, Arthas, jstat, NMT, Spring Actuator |
| Memory Leaks End-to-End | ThreadLocal, static collections, classloaders, caches |
| JVM Tuning Production Playbook | K8s memory, GraalVM, virtual threads, JIT warmup |
| Common Production Incidents | 10 real incident runbooks + trap questions |
| Modern Observability (2026) | Continuous eBPF profiling (Pyroscope/Parca), APM-first triage (Datadog/New Relic/Dynatrace), AI-assisted heap/thread dump RCA |
