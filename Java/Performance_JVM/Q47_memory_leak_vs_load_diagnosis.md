# Q47: Quick Diagnosis - How Do You Tell If It's a Memory Leak or Just Too Much Load?

**Study Time:** 5-7 minutes | **Frequency:** 58% follow-up in senior interviews 🔥 | **Difficulty:** ⭐⭐⭐⭐

---

## The Scenario

Your production app reports high heap usage. But is it a **memory leak** or just **legitimate memory consumption under load**?

```
Heap Usage: 6GB out of 8GB
GC Logs show frequent Full GC
Response times: 500ms (normal is 50ms)
```

Is the app sick or is it just under heavy load? You have 2 minutes to decide whether to:
- **Option A:** Restart the service (temporary fix for legitimate load)
- **Option B:** Hunt for a memory leak (root cause analysis)

---

## 🔥 The Right Diagnostic Approach (Differentiating)

### Test 1: Check GC Behavior (Most Revealing)

#### Memory Leak Pattern (Unhealthy):
```bash
jstat -gc -h5 <PID> 1000 100

S0C    S1C    S0U    S1U      EC       EU        OC         OU       MC     MU    CCSC   CCSU
...
17920  17920  0      8960  143360  110592  1118720   1118720   220032  211123 ...
                     ↑                     ↑ INCREASING
# Old Gen growing with each Full GC = MEMORY LEAK
```

**What it means:**
- **S0 (Survivor Space 0):** Almost empty (0%)
- **OU (Old Gen Usage):** Growing (95%+)
- After each Full GC, OU stays high → Objects not being collected → **LEAK**

#### Load Pattern (Healthy):
```bash
S0C    S1C    S0U    S1U      EC       EU        OC         OU       MC     MU    CCSC   CCSU
...
17920  17920  8960   0      143360  65536     1118720   400000     220032  211123 ...
                                            ↑ VARIES
# Old Gen drops after Full GC = Objects being collected = NOT A LEAK
```

**What it means:**
- **OU (Old Gen Usage):** Goes up during load, **drops after Full GC**
- Repeat: Up on load → Down after GC → Pattern cycles → **Healthy app**

#### Quick Command:
```bash
# Watch GC for 30 seconds
jstat -gcutil -h2 <PID> 1000 30

# Look at "OU" (Old Gen Usage %)
# Pattern 1 (Leak):    78 → 85 → 90 → 95 → OOM
# Pattern 2 (Load):    75 → 88 → 92 → GC → 45 → (repeats)
```

---

### Test 2: Monitor Memory After GC Stabilization

#### Method: Force a Full GC and observe

```bash
# Step 1: Trigger Full GC
jcmd <PID> GC.run

# Step 2: Wait 2 seconds
sleep 2

# Step 3: Check heap immediately after
jmap -heap <PID> | grep -A 5 "Heap Configuration"

# Example Output:
# Heap Configuration:
#    MaxHeapSize              = 8589934592 (bytes)
#    OldSize                  = 4294967296 (bytes)
#    NewSize                  = 279904256 (bytes)
# Heap Usage:
#    PS Scavenge GC (Allocation Failure):
#    Old Generation currently used = 5500000000 bytes  ← HIGH after GC

# Interpretation:
# If "Old Gen used" stays high after GC → LEAK
# If "Old Gen used" drops significantly → Just load
```

---

### Test 3: Check Memory Growth Over Time

#### Method: Collect heap usage at different time points

```bash
#!/bin/bash
# Script to track memory leak vs load pattern

for i in {1..10}; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    HEAP_USED=$(jmap -heap <PID> 2>/dev/null | grep "used =" | awk '{print $NF}' | tr -d 'bytes()')
    echo "$TIMESTAMP: Heap Used = $HEAP_USED bytes"
    sleep 60
done

# Output Analysis:
# Leak Pattern (continuously growing):
# 2025-01-01 14:00:00: Heap Used = 2000000000 bytes
# 2025-01-01 14:01:00: Heap Used = 2500000000 bytes
# 2025-01-01 14:02:00: Heap Used = 3000000000 bytes
# 2025-01-01 14:03:00: Heap Used = 3500000000 bytes
# → STRAIGHT LINE UP = LEAK

# Load Pattern (may spike but stabilizes):
# 2025-01-01 14:00:00: Heap Used = 1000000000 bytes
# 2025-01-01 14:01:00: Heap Used = 3000000000 bytes (spike from request batch)
# 2025-01-01 14:02:00: Heap Used = 2000000000 bytes (GC ran)
# 2025-01-01 14:03:00: Heap Used = 2200000000 bytes (plateau)
# → SAWTOOTH PATTERN = NOT A LEAK
```

---

## Decision Tree (Quick Diagnosis)

```
Start: "High heap usage reported"
    ↓
Test 1: Run "jstat -gc" - Check Old Gen after Full GC
    ├─→ OU stays high/increases → Likely LEAK
    └─→ OU drops after Full GC → Likely LOAD
    
If indicates LEAK:
    ├─→ Test 2: jcmd GC.run + check heap immediately
    │   ├─→ Doesn't drop much → CONFIRMED LEAK
    │   └─→ Drops significantly → False positive
    └─→ Test 3: Memory growth over 5 minutes
        ├─→ Continuous growth → CONFIRMED LEAK
        └─→ Stable/fluctuating → LOAD pattern
        
Decision:
LEAK Confirmed? → Take heap dump, analyze in MAT
LOAD Pattern?  → Scale up resources, reduce request rate
```

---

## Real Examples: How to Interpret GC Logs

### Example 1: Clear Memory Leak

**GC Log Snippet:**
```
[2025-01-01T14:00:00] Full GC (G1 Evacuation Pause) ... Old Gen: 4000M → 3800M
[2025-01-01T14:05:00] Full GC (G1 Evacuation Pause) ... Old Gen: 5200M → 5100M
[2025-01-01T14:10:00] Full GC (G1 Evacuation Pause) ... Old Gen: 6500M → 6400M
[2025-01-01T14:15:00] Full GC (G1 Evacuation Pause) ... Old Gen: 7800M → 7700M
[2025-01-01T14:20:00] OutOfMemoryError: Java heap space
```

**Analysis:**
- After each Full GC, Old Gen barely decreases (only 100-200MB)
- Old Gen usage increases: 3800M → 5100M → 6400M → 7700M
- Reaches OOM in exactly 20 minutes
- **Verdict: DEFINITE MEMORY LEAK**
- **Action: Don't restart, analyze heap dump for root cause**

---

### Example 2: High Load, Not a Leak

**GC Log Snippet:**
```
[2025-01-01T14:00:00] Young GC ... Old Gen: 800M → 600M
[2025-01-01T14:02:00] Young GC ... Old Gen: 1200M → 900M
[2025-01-01T14:04:00] Young GC ... Old Gen: 2100M → 1500M  (spike from batch load)
[2025-01-01T14:06:00] Full GC  ... Old Gen: 3800M → 600M  ← BIG DROP!
[2025-01-01T14:08:00] Young GC ... Old Gen: 1100M → 800M
[2025-01-01T14:10:00] Young GC ... Old Gen: 1300M → 900M
[2025-01-01T14:12:00] Full GC  ... Old Gen: 2900M → 700M  ← BIG DROP!
```

**Analysis:**
- After Full GC, Old Gen drops **significantly** (3800M → 600M)
- Pattern repeats every few minutes
- Usage rises during load, drops after GC
- **Verdict: NOT A LEAK, just under load**
- **Action: Scale resources, reduce load, or increase heap if needed**

---

## Interview Tricky Follow-Ups

### Q: "What if the memory never drops after GC?"

**Wrong Answer:** "Then we need to increase heap size"

**Right Answer:**
```
If memory doesn't drop after Full GC, it means:
    1. Those objects ARE needed by the application
    2. They're legitimately in use
    
Possible causes:
    A) Very high load (millions of concurrent requests)
    B) Legitimate large data structures (caches, indices)
    C) Memory leak (objects that SHOULD be GC'd aren't)

To distinguish:
    → Traffic reduce test
        * Reduce incoming requests by 50%
        * If memory drops → It's load-related
        * If memory stays → It's a leak
    
    → Heap dump analysis
        * Check what objects are retained
        * Are they supposed to be there?
        * Why are there 10M instances of UserCache?
```

---

### Q: "Old Gen usage is 95% but app is responding fine. True leak?"

**Wrong Answer:** "Yes, we have a memory leak, restart immediately"

**Right Answer:**
```
High Old Gen usage ≠ automatic leak

Check response times and GC frequency:

Scenario A: response_time = 1000ms, Full GC every 5 seconds
    → Severe leak, GC struggling, app is hanging

Scenario B: response_time = 50ms, Full GC every 30 minutes
    → Just using available heap, no problem
    → Don't restart for no reason

Real metric: Full GC frequency and duration
    • < 2s Full GC pause, < 1x per minute → Healthy
    • > 2s Full GC pause, > 5x per minute → Sick app
```

---

### Q: "Our app uses 7GB of 8GB but never crashes. Is there a leak?"

**Wrong Answer:** "If it's working, why fix it?"

**Right Answer:**
```
Not crashing yet ≠ No leak

Check these signs:

1. Trending analysis:
   • Heap usage was 500MB 1 month ago, now 7GB? → LEAK
   • Heap usage stayed at 7GB for 1 month? → Legitimate (load-based)

2. What triggers restart cycles?
   • Deployed Tuesday, OOM Thursday? → Leak introduced
   • OOM happens every 2 weeks at same time? → Batch job trigger

3. GC behavior:
   • Full GC once/day, heap drops after → Fine
   • Full GC 10 times/day, heap stagnates → Leak warning

Prevention steps:
   • Cap heap at 75% of available server memory
   • Set alert at 80% usage
   • Implement graceful shutdown at 90%
   • Auto-restart before hitting wall
```

---

## 🔥 Senior-Level Diagnosis Checklist

### Should Take Less Than 3 Minutes:

```
☐ Run: jstat -gcutil <PID> 1000 5
   Ask: Does Old Gen drop after each GC?
   
☐ Pattern Recognition:
   ☐ Sawtooth (up/down) = Load issue
   ☐ Linear increase = Leak
   
☐ Quick verification:
   jcmd <PID> GC.run
   jmap -heap <PID> | grep "used ="
   
☐ Decision:
   ☐ Memory dropped significantly → Healthy under load
   ☐ Memory stayed same → LEAK, take dump
```

### If It's a Leak:
```
☐ Don't panic restart (wastes time)
☐ Take heap dump immediately
☐ Check for: static caches, ThreadLocal, listeners
☐ Implement bounds while investigating
☐ Deploy fix, monitor recovery
```

### If It's Load:
```
☐ Reduce traffic (circuit breaker, rate limit)
☐ Scale horizontally (add more instances)
☐ Increase heap if trend goes up (with limits)
☐ Monitor GC pause times (if > 2s, still a problem)
```

---

## Wrong vs Right Diagnosis

| Situation | ❌ Wrong Diagnosis | ✅ Right Diagnosis | Action |
|-----------|-------------------|-------------------|--------|
| **Old Gen 90%, drops to 20% after GC** | "We have a leak" | "Just high load" | Scale resources |
| **Old Gen 90%, stays at 88% after GC** | "Who cares, still runs" | "Definite leak" | Take dump, fix |
| **Memory 500MB→7GB over 2 weeks** | "Scaling issue, buy more hardware" | "Leak introduced recently" | Find what changed, fix code |
| **Full GC every 10 seconds, 1s pauses** | "App is fine" | "App is struggling badly" | Fix leak immediately |
| **Memory constant at 6GB for 3 months** | "This is a leak waiting to happen" | "Legitimate working set size" | Monitor, don't fix |

---

## Real Interview Answer (2-3 minutes)

**Interviewer:** "Memory is at 95% heap. How do you determine if it's a leak or load?"

**Your Answer:**

> "I'd use three quick tests:
> 
> **First:** Run `jstat -gcutil` and observe the Old Gen usage column over 30 seconds. If it drops significantly after a Full GC, it's load-related. If it stays high or increases, it suggests a leak.
> 
> **Second:** Force a Full GC with `jcmd GC.run` and check the heap immediately. If memory drops by more than 50%, it's load. If it drops by less than 20%, it's a leak.
> 
> **Third:** Look at GC frequency. If Full GC happens multiple times per minute with increasing pauses, that's a sick app with a leak. If it happens once per 30 minutes with normal pauses, that's healthy.
> 
> Based on findings:
> - **If it's load:** Reduce traffic, add capacity, increase heap limit
> - **If it's a leak:** Don't restart yet — take a heap dump and analyze in MAT to find the culprit
> 
> This takes about 2-3 minutes to diagnose and gives me actionable data instead of guessing."

---

## ⚠️ Common Pitfalls

**Pitfall 1: Using heap percentage as the sole signal**

❌ **Wrong approach:**
```bash
# Monitoring script that triggers alert at 90% heap
HEAP_PERCENT=$(jmap -heap <PID> | grep "used =" | awk '{print ($1/$2)*100}')
if [ $HEAP_PERCENT -gt 90 ]; then
    alert "MEMORY LEAK DETECTED - RESTART NOW!"
fi
```
**Why it fails:** 90% heap usage is normal under load. A healthy app can run at 95% heap and still GC successfully. This creates false positives that lead to unnecessary restarts.

✅ **Right approach:**
```bash
# Monitor Old Gen usage AFTER Full GC
# If drops significantly: healthy
# If stays high: leak

jstat -gcutil <PID> 1000 30 | tail -5
# Watch the OU column (Old Gen Usage %)
# Pattern: 45 → 80 → 42 → 75 → 40 = HEALTHY (sawtooth = load)
# Pattern: 45 → 80 → 79 → 95 → OOM = LEAK (monotonic rise)
```

---

**Pitfall 2: Forcing Full GC repeatedly during diagnosis**

❌ **Wrong approach:**
```bash
#!/bin/bash
# Check for leak by forcing GC every 5 seconds
for i in {1..20}; do
    jcmd <PID> GC.run  # Forces Full GC
    sleep 5
done
# Then check if memory stabilized
```
**Why it fails:** You're creating artificial Full GCs that don't reflect production. Load takes time to manifest leaks. Forcing GC every 5 seconds masks the real pattern and adds GC overhead during diagnosis.

✅ **Right approach:**
```bash
# Let app run naturally, observe GC logs passively
# Only force ONE Full GC to establish baseline
jcmd <PID> GC.run
sleep 2
jmap -heap <PID> > heap_snapshot_1.txt

# Wait 5-10 minutes with normal load, then check again
sleep 600
jmap -heap <PID> > heap_snapshot_2.txt

# Compare snapshots
diff heap_snapshot_1.txt heap_snapshot_2.txt
# Memory grew 100MB in 10 minutes under normal load? That's a ~500MB/hour leak
```

---

**Pitfall 3: Assuming sustained high memory = leak**

❌ **Wrong approach:**
```
Memory Usage Today:
14:00 → 2GB
14:05 → 5GB (alert!)
14:10 → 5GB (still alert!)
14:15 → 5GB (MUST BE LEAK!)

→ Restart app immediately
```
**Why it fails:** Memory spiked to serve a batch job, stayed at 5GB because all that data is still needed. After batch completes (2 hours later), it drops to 500MB. You restarted for nothing.

✅ **Right approach:**
```
Diagnosis sequence:
1. Check GC logs: Is Old Gen dropping after Full GC?
   - YES → It's load-related, memory will drop when load drops
   - NO → Likely leak

2. Check for batch jobs/scheduled tasks
   - 14:00: Batch job starts (loads 5GB of data)
   - 15:30: Batch ends, data GC'd
   - Monitor longer window: at least 1 hour of production pattern

3. Check response time
   - Memory at 5GB, response time = 50ms → Healthy
   - Memory at 5GB, response time = 500ms → App struggling, likely leak

Decision:
If memory drops after load ends: NOT a leak
If memory stays high while app idle: LEAK
```

---

## 🛑 When NOT to Use This Diagnosis Approach

1. **When Old Gen usage is already at 99%** → Don't test further, take heap dump immediately, you're seconds from OOM
2. **When GC pause times are already > 5 seconds** → Don't diagnose, restart and analyze later, users are suffering now
3. **When you haven't captured GC logs from startup** → Don't try to diagnose from 1-hour snapshot, you need trend data
4. **When load pattern is unknown** → Don't assume anything; get traffic metrics first (requests/sec, user count changes)
5. **For critical production services** → Don't do extensive testing, restart to safe state, diagnose offline on staging

---

## Key Insights for Production

| Tool | What It Shows | Leak Signal |
|------|---------------|------------|
| **jstat -gc** | Young/Old/Perm Gen usage | OU doesn't drop after GC |
| **jmap -heap** | Current memory snapshot | Used > 85% after Full GC |
| **GC logs** | Full trend over time | Continuous sawtooth up |
| **Thread count (jps)** | Active threads | Growing thread pool = leak |
| **Native memory (jcmd)** | Off-heap memory | Growing = buffer leak |

