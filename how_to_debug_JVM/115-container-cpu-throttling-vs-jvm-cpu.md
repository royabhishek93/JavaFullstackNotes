# #115 — Container CPU Throttling vs JVM CPU

> **Category:** CPU Profiling & Flame Graphs | **Type:** Advanced Scenario Q&A | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"In Kubernetes, your pod shows low CPU usage (30% of limit) but is experiencing high latency. JVM profiling shows nothing hot. What's the issue?"

## 😊 Explain It Simply (for anyone)
Imagine you're allowed to use a shared photocopier for exactly 30 seconds out of every 100-second window, on average — even if you only actually need it in short, intense bursts. If your usage pattern is "sprint for 40 seconds, then rest for 60," the person managing the copier will forcibly stop you partway through your sprint once you've used your allotted 30 seconds in that window, then make you wait, even though your *average* usage over a whole hour looks perfectly reasonable. That forced pause is called throttling, and it's exactly what happens to containers in Kubernetes: the system enforces a CPU budget over short, repeating time windows (typically 100 milliseconds), so even a JVM whose average CPU usage looks modest can burst hard for a brief moment, get paused mid-burst, and cause requests to stall — even though nothing inside the JVM was actually "hot" or slow. Since the JVM itself isn't doing anything wrong, its own profiler sees nothing unusual; you have to look at the container's own throttling statistics, kept outside the JVM, to see that the operating system itself paused your process.

## 📊 Visualize It
```
100ms scheduling window (CFS):
 [=====JVM burst=====][THROTTLED, paused][=====JVM burst=====]
        30ms used            70ms of nothing            ...
Average CPU: 30% of limit    <- looks "fine" on a dashboard!
But: real latency includes forced pauses mid-burst.

Check: /sys/fs/cgroup/cpu/cpu.stat -> throttled_time, nr_throttled
```

## 🏭 The Real Production Answer (15-YOE Level)
CPU throttling. Kubernetes CFS (Completely Fair Scheduler) enforces CPU limits in 100ms periods. Even if average usage is 30%, a JVM can burst above the CPU limit in a short window, triggering throttling. The container is throttled — not using more CPU — but threads are paused.

Check:
```bash
# From inside the container
cat /sys/fs/cgroup/cpu/cpu.stat
# Look for: throttled_time (nanoseconds throttled)
# nr_throttled (number of periods throttled)
```

Or via metrics: `container_cpu_cfs_throttled_seconds_total` in Prometheus.

If throttling is significant, options:
1. Increase CPU limit (not request) to allow bursting
2. Set `--cpu-period` and `--cpu-quota` to give longer windows (reduces burst but also reduces average responsiveness)
3. JVM flag: `-XX:ActiveProcessorCount=N` to tell the JVM how many CPUs are available — affects ForkJoinPool size, GC thread count

Also: G1GC uses parallel GC threads that burst CPU. If GC is throttled, GC pause times explode. JFR GC event data will show long pauses not caused by GC work but by scheduler throttling.

## 🔑 Key Takeaway
Low average CPU with high latency in Kubernetes points to CFS throttling, not JVM hotspots — check `cpu.stat`'s `throttled_time` before profiling the JVM itself.
