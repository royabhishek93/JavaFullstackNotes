# Q6: Generational GC in Action - Minor, Major, and Full GC

**Study Time:** 12-15 minutes | **Interview Frequency:** 90% | **Difficulty:** ⭐⭐⭐⭐⭐

---

## 🤔 The Core Question

**"What's the difference between Minor GC, Major GC, and Full GC, and when does each happen?"**

This is a **critical senior interview question**. Understanding GC types and Stop-The-World pauses is essential for production troubleshooting.

---

## 🧠 Simple Explanation

### The Three Types of GC

> **Minor GC** - Cleans Young Gen (fast, frequent)  
> **Major GC** - Cleans Old Gen (slow, rare)  
> **Full GC** - Cleans entire heap (slowest, rarest)

**Key Difference:** Where they collect and how long they take.

---

## 📊 Visual Understanding

### Minor GC (Young Generation Collection)

**Before:**
```
Young Gen:
[Eden: 500MB used] [S0: 50MB] [S1: empty]

Old Gen:
[2GB used]
```

**Minor GC happens:**
```
Young Gen:
[Eden: empty ✅] [S0: empty] [S1: 60MB ✅]
                                  ↑ Survivors moved here

Old Gen:
[2.1GB used]
      ↑ 100MB promoted (aged objects)
```

**Time:** 10-50ms  
**Frequency:** Every few seconds  
**Impact:** Brief pause, usually not noticeable

---

### Major GC (Old Generation Collection)

**Before:**
```
Young Gen:
[Eden: 200MB] [S0: 20MB] [S1: empty]

Old Gen:
[7.5GB used] ← Nearly full! (8GB capacity)
```

**Major GC happens:**
```
Young Gen:
[Eden: empty] [S0: empty] [S1: 25MB]

Old Gen:
[5GB used] ← Cleaned (mark-sweep-compact)
     ↑ 2.5GB freed
```

**Time:** 100ms - 5s  
**Frequency:** Minutes to hours  
**Impact:** Noticeable pause

---

### Full GC (Entire Heap Collection)

**Before:**
```
Young Gen: [80% full]
Old Gen: [90% full]
Metaspace: [Classes loaded]
```

**Full GC happens:**
```
Young Gen: [empty]
Old Gen: [compacted]
Metaspace: [dead classes unloaded]
```

**Time:** 1-10s (or more!)  
**Frequency:** Rarely (emergency)  
**Impact:** Severe pause, **all app threads frozen**

---

## 🔄 Minor GC: Step-by-Step

### The Copy Collection Process

**Scenario:**
```java
// Creating objects
for (int i = 0; i < 1000; i++) {
    Person p = new Person();  // Allocated in Eden
}
// Most objects become garbage immediately
```

**Step 1: Eden fills up**
```
[Eden: 512MB / 512MB] ← Full!
Minor GC triggered
```

**Step 2: Stop-The-World pause**
```
All application threads paused
GC threads start
```

**Step 3: Mark live objects in Young Gen**
```
Scan GC Roots (Stack + Static)
Find references to Young Gen objects
Mark them: ✅ Live
```

**Step 4: Copy survivors**
```
From: Eden + Survivor0
To: Survivor1

Live objects copied → Survivor1
Age incremented (age++)
```

**Step 5: Promote old objects**
```
Objects with age ≥ 15 → Old Gen
```

**Step 6: Clear Eden and Survivor0**
```
Eden: Mark as free
Survivor0: Mark as free
(No actual deletion, just mark as available)
```

**Step 7: Resume application**
```
All application threads resumed
```

**Time:** Typically 10-50ms for well-tuned apps

---

## 🚨 Stop-The-World (STW): The Hidden Tax

### What is STW?

> **All application threads must pause during GC**

**Why?**
- GC needs consistent snapshot of memory
- Can't have app threads modifying objects while GC scans them
- Otherwise: Incorrect marking, crashes

**The Safepoint Problem:**

When GC starts, threads must reach a "safepoint" before pausing.

**Example:**
```java
// Thread 1: Running tight loop
for (long i = 0; i < 10_000_000_000L; i++) {
    sum += i;  // No safepoint! (optimized loop)
}

// Problem: GC wants to start
// - All other threads paused
// - Thread 1 can't pause (no safepoint)
// - All threads wait for Thread 1!
```

**Real Impact:** Payment API:
- GC triggered
- One thread in tight loop (CSV parsing)
- Time to safepoint: **18 seconds** 😱
- All requests blocked for 18 seconds
- Thousands of timeouts

**Solution:** Enable counted loop safepoints (Java 10+):
```bash
-XX:+UseCountedLoopSafepoints
```

---

## ❌ Wrong Code vs ✅ Right Code

### Mistake 1: Triggering Unnecessary Full GCs

**❌ WRONG:**
```java
@Service
public class CacheService {
    private Map<String, Data> cache = new HashMap<>();
    
    @Scheduled(fixedRate = 60000)  // Every minute
    public void cleanupCache() {
        cache.clear();
        System.gc();  // ❌ BAD! Forces expensive Full GC
    }
}
```

**What happens:**
```
Time 0s: System.gc() called
  → Full GC triggered (STW)
  → All threads paused: 2-5 seconds
  → All in-flight requests timeout

Production impact:
- 60 Full GCs per hour
- Each pause: 3 seconds
- Total downtime: 180 seconds/hour = 5% downtime!
- SLA violated
```

**✅ RIGHT:**
```java
@Service
public class CacheService {
    // Option 1: Use expiring cache (no manual cleanup)
    private LoadingCache<String, Data> cache = CacheBuilder.newBuilder()
        .expireAfterWrite(10, TimeUnit.MINUTES)
        .maximumSize(10000)
        .build(...);
    
    // Option 2: If manual cleanup needed, just clear
    @Scheduled(fixedRate = 60000)
    public void cleanupCache() {
        cache.clear();  // ✅ Just clear, let JVM decide when to GC
    }
}
```

---

### Mistake 2: Not Understanding Allocation Rate Impact

**❌ WRONG Understanding:**
```java
@RestController
public class ImageController {
    @PostMapping("/process")
    public ResponseEntity<byte[]> processImage(@RequestBody byte[] image) {
        // Developer thinks: "Only 10MB, no problem"
        byte[] temp1 = applyFilter1(image);  // 10MB
        byte[] temp2 = applyFilter2(temp1);  // 10MB
        byte[] result = applyFilter3(temp2); // 10MB
        return ResponseEntity.ok(result);
        // Total allocated: 40MB per request
    }
}
```

**What happens at scale:**
```
Traffic: 100 req/s
Allocation per request: 40MB
Allocation rate: 4GB/s

Young Gen: 4GB
Minor GC frequency: Every 1 second!

Result:
- GC overhead: 1 Minor GC/s × 50ms = 5% overhead
- Some objects still processing during GC → Premature promotion
- Old Gen fills quickly
- Major GC every 10 minutes
- P99 latency spikes
```

**✅ RIGHT (Reuse Buffers):**
```java
@RestController
public class ImageController {
    @Autowired
    private ByteBufferPool bufferPool;
    
    @PostMapping("/process")
    public ResponseEntity<byte[]> processImage(@RequestBody byte[] image) {
        ByteBuffer buffer = bufferPool.acquire();
        try {
            // Reuse same buffer for all operations ✅
            applyFilter1(image, buffer);
            applyFilter2(buffer);
            applyFilter3(buffer);
            return ResponseEntity.ok(buffer.array());
        } finally {
            bufferPool.release(buffer);
        }
        // Allocation per request: Almost none! ✅
    }
}
```

---

### Mistake 3: Ignoring Remembered Sets (Card Table)

**❌ WRONG Understanding:**
```java
// Developer thinks: "Young GC only scans Young Gen"

@Service
public class OrderService {
    // Old Gen object
    private List<Order> recentOrders = new ArrayList<>();
    
    public void addOrder(Order order) {
        recentOrders.add(order);  // Old → Young reference
    }
}
```

**Problem:**
```
Old Gen Object: recentOrders (List)
  ↓ Reference
Young Gen Object: Order

During Minor GC:
- Must scan Young Gen for live objects
- But what if Old Gen references Young Gen?
- Can't just scan Young Gen!
```

**Solution: Card Table (Remembered Set)**
```
Every write that creates Old → Young reference:
  → Marks 512-byte "card" as dirty

During Minor GC:
  → Scan GC Roots
  → Scan dirty cards in Old Gen ✅
  → Find all Old → Young references
```

**Write Barrier (automatic):**
```java
// Your code:
oldObject.field = youngObject;

// JVM inserts:
if (oldObject in Old Gen && youngObject in Young Gen) {
    markCardDirty(oldObject);
}
```

**Why you care:**
- Write barriers have small overhead (1-2%)
- But enable fast Minor GCs
- Without them, would need to scan entire Old Gen!

**✅ RIGHT: Just be aware, JVM handles it**
```java
@Service
public class OrderService {
    private List<Order> recentOrders = new ArrayList<>();
    
    public void addOrder(Order order) {
        recentOrders.add(order);
        // JVM automatically handles card marking ✅
    }
}
```

---

## 🧪 Complete Working Example: Observing GC Types

```java
import java.util.*;

public class GCTypesDemo {
    
    // Old Gen object (survives)
    private static List<byte[]> longLived = new ArrayList<>();
    
    public static void main(String[] args) throws InterruptedException {
        System.out.println("=== Demonstrating Minor, Major, and Full GC ===\n");
        
        // 1. Cause Minor GC
        System.out.println("1. Triggering Minor GC (Young Gen only)...");
        causeMinorGC();
        System.out.println("   → Minor GC collected short-lived objects\n");
        
        // 2. Cause promotion to Old Gen
        System.out.println("2. Promoting objects to Old Gen...");
        promoteToOldGen();
        System.out.println("   → Objects promoted after aging\n");
        
        // 3. Fill Old Gen to cause Major GC
        System.out.println("3. Filling Old Gen to trigger Major GC...");
        fillOldGen();
        System.out.println("   → Major GC cleaned Old Gen\n");
        
        // 4. Trigger Full GC
        System.out.println("4. Triggering Full GC (entire heap)...");
        longLived.clear();  // Release Old Gen objects
        System.gc();
        Thread.sleep(100);
        System.out.println("   → Full GC reclaimed all memory\n");
        
        printMemoryInfo();
    }
    
    static void causeMinorGC() throws InterruptedException {
        // Create tons of short-lived objects
        for (int i = 0; i < 1000; i++) {
            byte[] temp = new byte[100_000];  // 100KB
            // temp immediately becomes garbage
        }
        
        // Suggest GC (usually triggers Minor GC)
        System.gc();
        Thread.sleep(100);
    }
    
    static void promoteToOldGen() throws InterruptedException {
        List<byte[]> survivors = new ArrayList<>();
        
        // Create objects that survive multiple GCs
        for (int gc = 0; gc < 20; gc++) {
            // Keep these alive
            survivors.add(new byte[1_000_000]);  // 1MB
            
            // Create garbage to trigger GC
            for (int i = 0; i < 100; i++) {
                new byte[100_000];
            }
            
            System.gc();
            Thread.sleep(50);
            System.out.println("   GC cycle " + (gc + 1) + " - objects aging...");
        }
        
        // These objects now in Old Gen
        longLived.addAll(survivors);
    }
    
    static void fillOldGen() throws InterruptedException {
        System.out.println("   Allocating large objects (go to Old Gen)...");
        
        // Allocate large objects (go directly to Old Gen)
        for (int i = 0; i < 50; i++) {
            longLived.add(new byte[10_000_000]);  // 10MB each
            System.out.println("   Allocated " + (i + 1) * 10 + "MB");
            
            if (i % 10 == 0) {
                Thread.sleep(100);
            }
        }
        
        // Old Gen full → Major GC
        System.out.println("   Old Gen full, Major GC will occur...");
        Thread.sleep(500);
    }
    
    static void printMemoryInfo() {
        Runtime runtime = Runtime.getRuntime();
        long total = runtime.totalMemory();
        long free = runtime.freeMemory();
        long used = total - free;
        long max = runtime.maxMemory();
        
        System.out.println("=== Final Memory State ===");
        System.out.printf("Used:  %.2f MB / %.2f MB\n", used / 1024.0 / 1024.0, total / 1024.0 / 1024.0);
        System.out.printf("Free:  %.2f MB\n", free / 1024.0 / 1024.0);
        System.out.printf("Max:   %.2f MB\n", max / 1024.0 / 1024.0);
    }
}
```

**Run with GC logging:**
```bash
java -Xms512m -Xmx512m \
     -Xlog:gc*:file=gc.log \
     -XX:+PrintGCDetails \
     GCTypesDemo
```

**Expected Output:**
```
=== Demonstrating Minor, Major, and Full GC ===

1. Triggering Minor GC (Young Gen only)...
[GC (System.gc()) [PSYoungGen: 102400K->1024K(153600K)] 102400K->1032K(512000K), 0.0123 secs]
                    ↑ Young Gen cleaned
   → Minor GC collected short-lived objects

2. Promoting objects to Old Gen...
   GC cycle 1 - objects aging...
   GC cycle 2 - objects aging...
   ...
   GC cycle 15 - objects aging...
[GC (System.gc()) [PSYoungGen: 20480K->0K][ParOldGen: 0K->15360K] 0.0234 secs]
                                          ↑ Promoted to Old Gen!
   → Objects promoted after aging

3. Filling Old Gen to trigger Major GC...
   Allocating large objects (go to Old Gen)...
   Allocated 10MB
   Allocated 20MB
   ...
   Allocated 500MB
   Old Gen full, Major GC will occur...
[Full GC (Allocation Failure) [PSYoungGen: 0K->0K][ParOldGen: 358400K->256000K(358400K)] 1.234s]
                                                                 ↑ Old Gen compacted
   → Major GC cleaned Old Gen

4. Triggering Full GC (entire heap)...
[Full GC (System.gc()) [PSYoungGen: 0K->0K][ParOldGen: 256000K->1024K(358400K)] 0.8765s]
                                                               ↑ Everything cleaned
   → Full GC reclaimed all memory

=== Final Memory State ===
Used:  2.50 MB / 496.00 MB
Free:  493.50 MB
Max:   512.00 MB
```

---

## 🎯 Interview-Ready Answer

**Question:** "Explain the difference between Minor GC, Major GC, and Full GC."

**Your Answer:**
```
Java has three types of garbage collection, each targeting different 
parts of the heap:

**Minor GC (Young Generation Collection):**
- Collects only Young Gen (Eden + Survivors)
- Triggered when Eden fills up
- Frequency: Every few seconds (high allocation rate apps)
- Duration: Typically 10-50ms
- Algorithm: Copy collection (fast)
- Process: Copy live objects to Survivor space, promote aged objects
- All application threads paused (Stop-The-World)

**Major GC (Old Generation Collection):**
- Collects only Old Gen (tenured space)
- Triggered when Old Gen fills up
- Frequency: Minutes to hours
- Duration: 100ms to several seconds
- Algorithm: Mark-sweep-compact (slower)
- Process: Mark live objects, sweep dead, compact to eliminate fragmentation
- May or may not pause application (depends on collector)
- Note: With CMS/G1, can be mostly concurrent

**Full GC (Entire Heap Collection):**
- Collects both Young Gen AND Old Gen
- Also collects Metaspace (unloads unused classes)
- Triggered when:
  * Old Gen critically full
  * Explicit System.gc() call
  * Metaspace full
  * Heap fragmentation severe
- Frequency: Rarely (emergency situation)
- Duration: Seconds to minutes (worst case)
- All application threads paused (Stop-The-World)
- Should be rare in well-tuned production apps

**Key Differences:**
1. Scope: Minor (Young) vs Major (Old) vs Full (Everything)
2. Performance: Minor (fast) vs Major (slow) vs Full (slowest)
3. Impact: Minor (acceptable) vs Full (severe)

**Production Monitoring:**
- Minor GCs: Normal, should be frequent and fast
- Major/Old GCs: Acceptable if infrequent (<1/hour)
- Full GCs: Investigate if frequent (>1/day)

**Optimization Goals:**
- 99% of GCs should be Minor GCs
- Minor GC: <50ms pause
- Full GC: <1/day frequency

In modern collectors like G1, the distinction blurs - G1 does 
"mixed collections" that collect both young and parts of old gen 
incrementally, avoiding traditional Full GCs.
```

---

## 📋 Quick Checklist

- [ ] Understand Minor GC (Young Gen, fast)
- [ ] Understand Major GC (Old Gen, slower)
- [ ] Understand Full GC (entire heap, slowest)
- [ ] Know Stop-The-World pauses affect all GC types
- [ ] Understand write barriers and card tables
- [ ] Can explain when each GC type is triggered

---

## 🚨 Critical Pitfalls in Production

### Pitfall 1: Continuous Full GCs (GC Thrashing)

**❌ Problem Scenario:**
```java
@Service
public class ReportService {
    public byte[] generateReport() {
        // Allocates 500MB
        List<ReportRow> rows = fetchAllData();  // 500MB
        byte[] pdf = convertToPDF(rows);  // Another 500MB
        return pdf;
    }
}
```

**What happens:**
```
Heap: 1GB
Young Gen: 300MB
Old Gen: 700MB

Request comes in:
  → Allocate 500MB (goes to Old Gen, too large for Young)
  → Old Gen: 700MB → 1200MB ❌ FULL!
  → Full GC triggered (reclaim space)
  → Process request
  → Return PDF
  → 500MB garbage in Old Gen

Next request:
  → Same cycle
  → Another Full GC!

Result: Full GC on EVERY request!
```

**Real Impact:** Report generation API:
- Every request: Full GC (2 seconds)
- Throughput: 1 request / 2 seconds = 0.5 req/s
- Should be: 100 req/s
- **200x slowdown!**

**GC Logs:**
```
[Full GC (Allocation Failure) 1024M->524M(1024M) 2.1s]
[Full GC (Allocation Failure) 1024M->524M(1024M) 2.2s]
[Full GC (Allocation Failure) 1024M->524M(1024M) 2.0s]
  ↑ Continuous Full GCs = GC Thrashing
```

**✅ Solution 1: Increase Heap**
```bash
# Give more room
-Xmx4g
```

**✅ Solution 2: Stream Instead of Loading**
```java
@Service
public class ReportService {
    public void generateReport(OutputStream out) {
        // Stream data, never load all at once ✅
        try (Stream<ReportRow> rows = fetchDataStream()) {
            convertToPDF(rows, out);  // Process incrementally
        }
        // Peak memory: 10MB instead of 500MB!
    }
}
```

**✅ Solution 3: Use Off-Heap Memory**
```java
@Service
public class ReportService {
    public ByteBuffer generateReport() {
        // Use direct buffer (off-heap)
        ByteBuffer buffer = ByteBuffer.allocateDirect(500_000_000);
        // Not subject to GC ✅
        return buffer;
    }
}
```

---

### Pitfall 2: Long Time-To-Safepoint

**❌ Problem Code:**
```java
@Service
public class DataProcessor {
    public void processFile(String filename) {
        String content = readFile(filename);
        
        // Tight loop, no safepoints!
        for (int i = 0; i < content.length(); i++) {
            if (content.charAt(i) == ',') {
                count++;  // Simple operation, no safepoint
            }
        }
        // Loop could run for seconds without safepoint
    }
}
```

**What happens:**
```
Thread 1: Normal request processing (reaches safepoint instantly)
Thread 2: Normal request processing (reaches safepoint instantly)
Thread 3: Running tight loop (no safepoint for 10 seconds!)

GC wants to start:
  1. Signals all threads to pause
  2. Thread 1 pauses ✅ (at safepoint)
  3. Thread 2 pauses ✅ (at safepoint)
  4. Thread 3... still running ❌
  5. ALL threads wait for Thread 3
  6. After 10 seconds, Thread 3 finally reaches safepoint
  7. GC can start

Result: 10 second pause for 50ms GC!
```

**Real Impact:** CSV import service:
- Time to safepoint: **12.5 seconds**
- Actual GC time: 45ms
- Total pause: 12.5 seconds
- All requests timed out

**GC Logs:**
```
[Times: user=0.04s sys=0.00s real=12.54s]
        ↑ GC work ↑         ↑ Total including time-to-safepoint
12.5s to reach safepoint!
```

**✅ Solution 1: Enable Safepoints in Counted Loops (Java 10+)**
```bash
-XX:+UseCountedLoopSafepoints  # ✅ Inserts safepoints in tight loops
```

**✅ Solution 2: Rewrite Loop**
```java
@Service
public class DataProcessor {
    public void processFile(String filename) {
        String content = readFile(filename);
        
        // Use library method (has safepoints)
        count = content.split(",").length;  // ✅ Has safepoints
        
        // Or break loop into chunks:
        for (int i = 0; i < content.length(); i++) {
            if (content.charAt(i) == ',') {
                count++;
            }
            
            // Periodic check (creates safepoint opportunity)
            if (i % 10000 == 0) {
                Thread.yield();  // ✅ Safepoint opportunity
            }
        }
    }
}
```

---

### Pitfall 3: Allocation Failure Triggering Unexpected Full GC

**❌ Problem Scenario:**
```java
@RestController
public class UploadController {
    @PostMapping("/upload")
    public ResponseEntity<?> handleUpload(@RequestParam("file") MultipartFile file) {
        // File can be huge
        byte[] content = file.getBytes();  // ❌ Could be 100MB!
        processData(content);
        return ResponseEntity.ok("Success");
    }
}
```

**What happens:**
```
Heap: 4GB
Young Gen: 1.3GB
Old Gen: 2.7GB (2GB used, 700MB free)

Large file uploaded: 1GB
Cannot fit in Young Gen (1.3GB capacity, but partially full)
Cannot fit in Old Gen (700MB free < 1GB needed)

Result:
  1. Try allocate in Young Gen ❌ (too large)
  2. Try allocate in Old Gen ❌ (not enough space)
  3. Trigger Full GC (try to free space)
  4. If still not enough → OutOfMemoryError
```

**Real Impact:** File upload service:
- Some users upload 500MB files
- Triggers Full GC: 5 seconds
- Everyone else's uploads fail (timeout)
- 1 large file kills entire service

**GC Logs:**
```
[GC (Allocation Failure) [PSYoungGen: 1024M->1024M(1024M)] 3072M->3072M(4096M), 0.010s]
  ↑ Young GC failed (couldn't free enough)
[Full GC (Allocation Failure) [PSYoungGen: 1024M->0M][ParOldGen: 2048M->512M(3072M)] 5.234s]
  ↑ Forced Full GC
```

**✅ Solution 1: Limit Upload Size**
```properties
# application.properties
spring.servlet.multipart.max-file-size=10MB
spring.servlet.multipart.max-request-size=10MB
```

**✅ Solution 2: Stream Large Files**
```java
@RestController
public class UploadController {
    @PostMapping("/upload")
    public ResponseEntity<?> handleUpload(@RequestParam("file") MultipartFile file) {
        // Stream instead of loading to memory ✅
        try (InputStream in = file.getInputStream()) {
            processStream(in);  // Process chunks
        }
        return ResponseEntity.ok("Success");
    }
    
    void processStream(InputStream in) throws IOException {
        byte[] buffer = new byte[8192];  // Small buffer in Young Gen ✅
        int read;
        while ((read = in.read(buffer)) != -1) {
            processChunk(buffer, read);
        }
    }
}
```

**✅ Solution 3: Use Direct Buffers (Off-Heap)**
```java
@RestController
public class UploadController {
    @PostMapping("/upload")
    public ResponseEntity<?> handleUpload(@RequestParam("file") MultipartFile file) {
        // Allocate off-heap (not subject to GC) ✅
        ByteBuffer buffer = ByteBuffer.allocateDirect((int) file.getSize());
        
        try (InputStream in = file.getInputStream();
             ReadableByteChannel channel = Channels.newChannel(in)) {
            channel.read(buffer);
            processBuffer(buffer);
        }
        
        return ResponseEntity.ok("Success");
    }
}
```

---

## 🔄 Follow-Up Questions & Answers

### Q1: "Can Young GC and Old GC run simultaneously?"

**Answer:**
```
Depends on the garbage collector:

**Serial GC: NO**
- Single-threaded
- Young GC → pauses everything
- Old GC → pauses everything
- Never concurrent

**Parallel GC: NO**
- Multi-threaded, but not concurrent
- Young GC → pauses everything (multiple GC threads)
- Old GC → pauses everything (multiple GC threads)
- Cannot run both simultaneously

**CMS (Concurrent Mark Sweep): PARTIALLY**
- Young GC: Still Stop-The-World
- Old GC: Mostly concurrent
- Young GC can interrupt concurrent Old GC phase
- But not truly simultaneous

**G1 GC: YES (sort of)**
- Young GC: Stop-The-World
- But G1 does "mixed collections" (Young + some Old regions)
- Concurrent marking happens while app runs
- Young GC can happen during concurrent phase

**ZGC/Shenandoah: YES**
- Concurrent compaction
- Young and Old collected concurrently
- Minimal STW pauses (<10ms)

**Production implication:**
If you see overlapping GC pauses in logs, check collector:
- Parallel/Serial: Should not overlap (indicates problem)
- CMS/G1/ZGC: Can overlap (normal)

**Example (G1):**
[GC pause (G1 Evacuation Pause) (young) 512M->128M, 0.025s]
[GC concurrent-mark-start]  ← Old Gen marking starts
[GC pause (G1 Evacuation Pause) (young) 512M->128M, 0.030s]
                             ↑ Young GCwhile Old Gen marking!
[GC concurrent-mark-end]
```

---

### Q2: "What's the difference between Full GC and Major GC?"

**Answer:**
```
This is confusing because terminology varies by collector:

**Classic Definition:**
- Minor GC: Young Gen only
- Major GC: Old Gen only
- Full GC: Young + Old + Metaspace

**Reality (depends on collector):**

**Parallel GC:**
- "Minor GC" = Young Gen
- "Full GC" = Young + Old + Metaspace (no separate "Major")
- No "Major GC" in logs

**CMS:**
- "Minor GC" =Young Gen (also called "ParNew")
- "CMS" = Old Gen concurrent collection
- "Full GC" = Concurrent Mode Failure (emergency, everything)

**G1:**
- "Minor GC" = Young Gen evacuation
- "Mixed GC" = Young + some Old regions
- "Full GC" = Emergency compaction (should be rare)
- No "Major GC" terminology

**Production usage:**
Most people use "Major GC" and "Full GC" interchangeably to mean 
"expensive Old Gen collection".

**What matters:**
- Young GC: < 50ms (acceptable)
- Old/Major/Full GC: >100ms (investigate if frequent)

**In interviews, clarify:**
"By Full GC, do you mean a collection of the entire heap including 
Metaspace, or just an Old Gen collection? The terminology varies by 
collector."
```

---

### Q3: "Why does Minor GC pause time increase over time?"

**Answer:**
```
Several reasons:

**1. Young Gen Size Increased (Auto-tuning):**
JVM might increase Young Gen if it sees benefits:
- More objects means more to scan → longer GC

**2. Old Gen Filling Up:**
Young GC must scan Old→Young references:
- More objects in Old Gen → more cards to scan
- Can increase Young GC time by 2-3x

**3. Many Old→Young References:**
Write barriers mark cards dirty:
- If many Old Gen objects reference Young Gen
- More cards to scan during Young GC
- Example: Large cache holding recent objects

**4. Survivor Space Issues:**
If survivors don't fit:
- More time spent promoting to Old Gen
- Promotion slower than copying

**5. CPU Throttling:**
If pod/container CPU throttled:
- GC threads run slower
- Same work takes longer

**Real Example:**

App startup:
[GC (Allocation Failure) [PSYoungGen: 512M->64M] 0.015s]  ← 15ms

After 12 hours:
[GC (Allocation Failure) [PSYoungGen: 512M->64M] 0.055s]  ← 55ms!

Analysis:
- Old Gen grew from 100MB → 2GB
- More Old→Young references
- More cards to scan
- 3-4x slower Young GC

**Solutions:**

**Solution 1: Reduce Old→Young References**
// Before:
static List<RecentOrder> cache = new ArrayList<>();
public void addOrder(Order order) {
    cache.add(order);  // Old→Young reference
}

// After:
LoadingCache<String, Order> cache = CacheBuilder.newBuilder()
    .expireAfterWrite(10, TimeUnit.MINUTES)  // Auto-evict
    .build(...);

**Solution 2: Limit Old Gen Growth**
- Investigate what's filling Old Gen
- Add cache size limits
- Fix memory leaks

**Solution 3: Tune GC Threads**
-XX:ParallelGCThreads=8  // More threads = faster GC

**Solution 4: Switch to G1**
G1 handles large heaps better:
-XX:+UseG1GC
-XX:MaxGCPauseMillis=50
```

---

### Q4: "Should I call System.gc() in production?"

**Answer:**
```
**Short answer: NEVER in production APIs**

**Why it's tempting:**
// After big operation
bigCache.clear();
System.gc();  // "Help" the GC

**Why it's dangerous:**

**1. Forces Stop-The-World Full GC:**
System.gc() typically triggers Full GC:
- All application threads pause
- Can take seconds
- All in-flight requests timeout

**2. JVM Knows Better:**
- JVM has sophisticated heuristics
- Knows optimal GC timing
- Your manual GC likely suboptimal

**3. May Be Ignored:**
-XX:+DisableExplicitGC  // Ignores System.gc()
- Many production systems set this
- Your call does nothing

**Real horror story:**
Developer added System.gc() to batch job cleanup:

@Scheduled(fixedRate = 60000)  // Every minute
public void cleanup() {
    cache.clear();
    System.gc();  // 😱
}

Result:
- Full GC every minute
- 3 second pause each time
- 5% downtime
- SLA violations
- $50K in SLA penalties

**Acceptable use cases (RARE):**

**1. Test/Development:**
// OK in tests to verify GC behavior
@Test
public void testMemoryLeak() {
    createObjects();
    System.gc();
    assertMemoryFreed();
}

**2. Admin Endpoint (with protection):**
@PostMapping("/admin/gc")
public ResponseEntity<?> forceGC() {
    if (!maintenanceMode) {
        return ResponseEntity.status(403).body("Not in maintenance");
    }
    
    if (activeRequests > 0) {
        return ResponseEntity.status(503).body("System busy");
    }
    
    logger.warn("Manual GC requested");
    System.gc();
    return ResponseEntity.ok("GC triggered");
}

**3. After Large Cleanup (Maybe):**
@PreDestroy
public void cleanup() {
    // Shutting down anyway
    cache.clear();
    connectionPool.close();
    System.gc();  // OK, app shutting down
}

**Better alternatives:**

**Instead of:**
bigOperation();
System.gc();  // Force GC

**Do:**
bigOperation();
// Let JVM decide when to GC ✅

**Or use weak references:**
private Map<String, WeakReference<Data>> cache = new WeakHashMap<>();
// GC automatically clears when memory needed ✅

**Interview answer:**
"System.gc() should never be called in production request paths. It 
forces an expensive Full GC that pauses all threads. The JVM's 
automatic GC timing is almost always superior. The only acceptable 
uses are in tests, admin endpoints during maintenance windows, or 
during graceful shutdown."
```

---

### Q5: "What's a 'promotion failure' and how to fix it?"

**Answer:**
```
**Promotion Failure** = Young GC tries to promote objects to Old Gen, 
but Old Gen is full or fragmented.

**Scenario:**
Minor GC happens:
1. Survivors need to be promoted (age ≥ 15)
2. Old Gen full or too fragmented
3. Cannot complete promotion
4. Triggers emergency Full GC

**GC Log:**
[GC (Allocation Failure) [PSYoungGen: 512M->512M(512M)] 3072M->3072M(4096M) 0.010s]
  ↑ Young GC failed (couldn't promote)
[Full GC (Ergonomics) [PSYoungGen: 512M->0M][ParOldGen: 3072M->2048M(3584M)] 5.234s]
  ↑ Forced Full GC to make room

**Causes:**

**1. Old Gen Full:**
- Too much long-lived data
- Memory leak
- Cache without limits

**2. Old Gen Fragmented:**
- Mark-sweep without compaction (CMS)
- Many different object sizes
- Free blocks too small for promotion

**3. Promotion Rate Too High:**
- Objects promoted too quickly
- Young Gen too small
- Objects don't die before promotion

**Real Example:**

E-commerce site:
- Session data in Old Gen (memory leak)
- Old Gen: 3.5GB / 4GB (90% full)
- Every Minor GC: tries to promote 100MB
- Old Gen can't fit → Promotion failure
- Full GC every 30 seconds
- P99 latency: 6 seconds

**Solutions:**

**Solution 1: Increase Old Gen Size**
-Xmx16g
-XX:NewRatio=2  # Old Gen = 10.6GB (was 4GB)

**Solution 2: Fix Memory Leaks**
// Before:
static Map<String, Session> sessions = new HashMap<>();  // Never cleared!

// After:
@Bean
public ConcurrentMapCacheManager cacheManager() {
    return new ConcurrentMapCacheManager("sessions");
}
// Or use Redis for distributed sessions ✅

**Solution 3: Increase Young Gen (Reduce Promotion)**
-Xmx16g
-XX:NewRatio=1  # Young Gen = 50% (was 33%)
// Objects have more time to die before promotion

**Solution 4: Increase Tenuring Threshold **
-XX:MaxTenuringThreshold=15  # Default
-XX:TargetSurvivorRatio=90   # Keep objects in Young Gen longer

**Solution 5: Switch to G1 (Handles Fragmentation Better)**
-XX:+UseG1GC
-XX:MaxGCPauseMillis=200
// G1 does incremental compaction, handles fragmentation better

**Monitoring:**
jstat -gccause <pid> 1000
Look for:
- High "Promoted" column (promotion rate)
- Frequent Full GCs
- Old Gen consistently >85%

Prevention:
- Monitor promotion rate (<10MB/s ideal)
- Limit cache sizes
- Fix memory leaks early
- Use appropriate GC (G1 for large heaps)
```

---

## 🎓 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Minor vs Major vs Full GC | GC fundamentals | ⭐⭐⭐⭐⭐ |
| Stop-The-World pauses | Performance impact | ⭐⭐⭐⭐⭐ |
| Promotion failure | Common production issue | ⭐⭐⭐⭐ |
| System.gc() dangers | Production anti-pattern | ⭐⭐⭐⭐ |
| Card table/write barriers | Old→Young references | ⭐⭐⭐ |

---

## 🔗 What's Next?

Now that you understand how generational GC works, learn **which GC implementation to choose**:
- [Q7: GC Implementations](Q7_gc_implementations.md) - Serial, Parallel, CMS, G1, ZGC

---

**Last Updated:** March 1, 2026
