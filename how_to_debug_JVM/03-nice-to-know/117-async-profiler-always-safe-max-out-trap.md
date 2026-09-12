# #117 — "async-profiler Is Always Safe — Max It Out"

> **Category:** CPU Profiling & Flame Graphs | **Type:** Senior Trap Question | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"Since async-profiler has low overhead, I'll profile at 10000 samples/sec for 10 minutes in prod."

## 😊 Explain It Simply (for anyone)
Imagine a security camera system that's normally set to take one snapshot every ten seconds, which is unobtrusive and barely uses any storage or power. If you crank that same camera up to take a hundred snapshots every single second and let it run for ten straight minutes, you'll generate an overwhelming pile of footage that's slow and painful to review, and the camera itself will start drawing enough extra power and disk activity that it can actually interfere with whatever it's supposed to be quietly observing. Profiling tools work the same way: a low, sensible sampling rate over a short window is nearly invisible to the running application, but cranking the sampling frequency way up (and running it far longer than needed) increases overhead, can flood the operating system with interrupt signals that disrupt precise timing, and produces a data file so large it becomes difficult to actually open and analyze. "Low overhead" describes the tool's *sensible defaults*, not a blank check to push every dial to maximum in a live, revenue-generating system.

## 📊 Visualize It
```
Default: 10ms interval (100 samples/sec)  -> <1-3% overhead   SAFE for prod

Pushed:  1ms interval (1000 samples/sec)  -> higher overhead
                                              + more OS signal interrupts
                                              + can disturb latency-sensitive code

10 minutes of wall-clock mode -> 50-100MB SVG, painful to open/analyze

Safe defaults: cpu 30-60s | alloc 30s | wall 15s (shorter, due to data volume)
```

## 🏭 The Real Production Answer (15-YOE Level)
async-profiler overhead scales with sampling frequency and duration. Defaults are usually fine; pushing limits isn't.

The default sampling interval for async-profiler is **10ms** (100 samples/sec). At this rate, overhead is <1-3%. But:

- Increasing to 1000 samples/sec (1ms interval) increases overhead and OS signal delivery frequency — can interfere with application timing, especially for latency-sensitive services.
- 10 minutes of profiling generates a large SVG (potentially 50-100MB) that can be slow to analyze and takes memory to hold in the JVM.
- Wall-clock mode (`-e wall`) profiles ALL threads including I/O-blocked ones — generates far more data than CPU mode and should be time-limited.

Safe production defaults:
```bash
# CPU profiling: 30-60 seconds, default interval, HTML output
./profiler.sh -e cpu -d 60 -f /tmp/cpu.html <pid>

# Allocation profiling: 30 seconds, reduced detail
./profiler.sh -e alloc -d 30 -f /tmp/alloc.html <pid>

# Wall-clock: shorter duration due to data volume
./profiler.sh -e wall -d 15 -f /tmp/wall.html <pid>
```

Always test the profiling command in staging first. Be aware that `perf_events` require kernel capabilities — in containers you may need `--privileged` or the `SYS_ADMIN` capability, which has security implications.

## 🔑 Key Takeaway
"Low overhead" describes async-profiler's sensible defaults, not a license to max out sampling rate and duration in production — stick to short, default-rate sessions and test in staging first.
