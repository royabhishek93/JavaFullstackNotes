# #61 — Memory Leak — Gradual OOM Over Days

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"Walk me through diagnosing: memory grows 50-100MB/day, the team has a 'weekly restart' schedule that masks the problem, and the pod eventually OOM-kills after about 7 days. How do you find the leak?"

## 😊 Explain It Simply (for anyone)
This is like a junk drawer that gets 1% fuller every single day — nobody notices day to day, but after a week it won't close anymore. A "weekly restart" is like emptying the drawer every Sunday: it hides the problem instead of solving it. To actually find the leak, you take two snapshots of what's in the drawer (a class histogram) some time apart, then compare them — whatever category of item keeps showing up in bigger and bigger piles between the two snapshots is your leak. A very common specific culprit is a "sticky note" (ThreadLocal — data attached to a specific worker thread) that a request writes down but never peels off, so when the same worker picks up the next customer, the old sticky note is still there taking up space.

## 📊 Visualize It
```
Day 1   Day 2   Day 3  ... Day 7 (OOM)
[■□□□]  [■■□□]  [■■■□]     [■■■■] restart masks it weekly

diff hist1 hist2 --> which class count/bytes is only ever GROWING?
  char[] / String  -> string accumulation
  HashMap$Entry    -> map growing
  ThreadLocal val  -> not removed after request
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- Memory grows 50-100MB/day
- Weekly restart schedule (masking the leak)
- Eventually OOM-kills pod after ~7 days

**Diagnosis — compare heap over time:**
```bash
# Capture histogram baseline
jcmd <pid> GC.class_histogram > /tmp/hist1.txt

# Wait 30 minutes
jcmd <pid> GC.class_histogram > /tmp/hist2.txt

# Find growing classes
diff <(sort /tmp/hist1.txt) <(sort /tmp/hist2.txt) | grep "^>" | sort -k3 -rn | head -20
```

**Look for:**
- `char[]` / `byte[]` / `String` growing → string accumulation
- `HashMap$Entry` or `LinkedHashMap$Entry` → map growing
- Event listener objects → listener not unregistered
- CGLIB proxies → classloader leak in dynamic proxy

**Common pattern — ThreadLocal not cleaned:**
```java
// Broken: ThreadLocal in thread pool = memory accumulates
private static final ThreadLocal<UserContext> CTX = new ThreadLocal<>();

// In request handler:
CTX.set(new UserContext(userId));  // set on thread
// ... process request ...
// FORGOT: CTX.remove() — next request reuses thread, old context remains

// Fixed: always clean up
try {
    CTX.set(context);
    processRequest();
} finally {
    CTX.remove();  // CRITICAL for thread pool threads
}
```

## 🔑 Key Takeaway
A weekly restart schedule is a red flag, not a fix — take two histograms 30 minutes apart and diff them to find whatever class only ever grows.
