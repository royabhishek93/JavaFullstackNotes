# Q4: GC Sweeping Phase - Reclaiming Memory

**Study Time:** 10-12 minutes | **Interview Frequency:** 75% | **Difficulty:** ⭐⭐⭐⭐

---

## 🤔 The Core Question

**"After marking live objects, how does the JVM actually reclaim memory from dead objects?"**

This is where candidates separate themselves - understanding sweeping, compaction, and fragmentation is critical for production performance tuning.

---

## 🧠 Simple Explanation

### The Three Strategies

After marking phase identifies garbage, the JVM has three ways to reclaim memory:

> **1. Sweep** - Delete garbage, leave gaps (fast but fragments memory)  
> **2. Compact** - Move live objects together, eliminate gaps (slow but clean)  
> **3. Copy** - Copy live objects to new space, abandon old space (fastest, needs extra space)

Different GC algorithms use different strategies!

---

## 📊 Visual Understanding

### Strategy 1: Mark-Sweep (CMS, Serial Old)

**After Marking:**
```
Memory:
[A ✅][B ❌][C ✅][D ❌][E ❌][F ✅][G ❌]
 Live  Dead  Live  Dead  Dead  Live  Dead
```

**After Sweeping:**
```
Memory:
[A ✅][Free][C ✅][Free    ][F ✅][Free]
```

**Characteristics:**
- ✅ Fast: Just mark regions as free
- ❌ Fragmented: Gaps between live objects
- ❌ Problem: Can't allocate large objects even with enough total free space

---

### Strategy 2: Mark-Sweep-Compact (Parallel Old, G1)

**After Marking:**
```
Memory:
[A ✅][B ❌][C ✅][D ❌][E ❌][F ✅][G ❌]
```

**After Sweeping:**
```
Memory:
[A ✅][C ✅][F ✅][       Free Space       ]
 ↑ Moved ↑ Moved ↑ Moved
```

**Characteristics:**
- ✅ No fragmentation: All live objects together
- ✅ Simple allocation: Just bump pointer
- ❌ Slower: Must move objects and update all references
- ❌ Longer STW pause

---

### Strategy 3: Copy (Young Gen, G1)

**Before:**
```
From Space:
[A ✅][B ❌][C ✅][D ❌][E ❌][F ✅][G ❌]

To Space:
[                Empty                  ]
```

**After:**
```
From Space:
[           Abandoned (All Free)        ]

To Space:
[A ✅][C ✅][F ✅][      Free Space      ]
```

**Characteristics:**
- ✅ Fastest: No explicit sweep, just copy live objects
- ✅ No fragmentation: Live objects copied contiguously
- ✅ Simple: Abandon entire old space at once
- ❌ Requires extra space: Need 2x memory (From + To)
- ✅ Perfect for Young Gen: Most objects die young, few copies needed

---

## 🎯 Why Fragmentation Matters

### The Problem

```
Memory after multiple GC cycles:
[Obj][Free][Obj][Free][Obj][Free][Obj]
Total free: 300KB (3 × 100KB gaps)
```

**Try to allocate 200KB object:**
```
❌ Allocation fails!
Even though 300KB total free, no single gap is 200KB
```

**Result:** `OutOfMemoryError` with plenty of free memory! 😱

---

### Real Production Example

**Symptom:**
```
Application logs:
java.lang.OutOfMemoryError: Java heap space

JVM metrics:
Heap used: 12GB / 16GB (75% used)
Why OOM with 25% free? → Fragmentation!
```

**GC Log:**
```
[CMS: 12000K->12000K(16000K), 0.5 seconds]
                          ↑
                    Heap didn't shrink! (fragmentation)
```

**Analysis:**
```
Heap visualization:
████▓▓██████▓▓▓███▓▓████
█ = Live object (1MB each)
▓ = Free space (512KB each)

Total free: 4GB
Largest continuous free: 512KB
Large object allocation (2MB): ❌ FAIL!
```

**Solution:** Full compaction triggered:
```
[Full GC (Allocation Failure): 12000K->8000K(16000K), 2.5 seconds]
                                                      ↑
                                                Long pause! (compaction)
```

---

## ❌ Wrong Code vs ✅ Right Code

### Mistake 1: Creating Many Large Objects

**❌ WRONG (Causes fragmentation):**
```java
@Service
public class ReportService {
    public byte[] generateReport(List<Order> orders) {
        // Creates many large temporary arrays
        byte[] temp1 = new byte[10_000_000];  // 10MB
        byte[] temp2 = new byte[10_000_000];  // 10MB
        byte[] result = new byte[10_000_000]; // 10MB
        
        // Process...
        
        return result;  // temp1, temp2 become garbage
    }
}
```

**What happens:**
```
Heap before:
[        Free Space        ]

After 1st call:
[temp1 10MB][temp2 10MB][result 10MB][Free]

After 2nd call (temp1, temp2 from 1st call now garbage):
[Free  10MB][Free  10MB][result1 10MB][temp1 10MB][temp2 10MB][result2 10MB]
 ↑ Gap       ↑ Gap
 
After 100 calls:
[Gap][Obj][Gap][Obj][Gap][Obj]... (Fragmented!)
```

**✅ RIGHT (Reuse buffers):**
```java
@Service
public class ReportService {
    // Reuse buffers to avoid allocation churn
    private static final ThreadLocal<ByteBuffer> BUFFER_POOL = 
        ThreadLocal.withInitial(() -> ByteBuffer.allocate(10_000_000));
    
    public byte[] generateReport(List<Order> orders) {
        ByteBuffer buffer = BUFFER_POOL.get();
        buffer.clear();  // Reuse existing buffer
        
        // Process directly into buffer...
        
        return Arrays.copyOf(buffer.array(), buffer.position());
    }
}
```

**Why better:**
- Allocates once per thread
- No temporary large objects
- No fragmentation
- Much faster (no GC pressure)

---

### Mistake 2: Not Understanding Young Gen vs Old Gen Collection

**❌ WRONG Understanding:**
```java
@Service
public class CacheService {
    // Developer thinks: "Small objects, no GC problem"
    private Map<String, byte[]> cache = new HashMap<>();
    
    public void cacheData(String key, byte[] data) {
        cache.put(key, data);  // ❌ Eventually promotes to Old Gen
    }
}
```

**What actually happens:**
```
Time 0: Object created in Young Gen (Eden)
  [Eden: cache entry]
  
Time 1: Young GC
  → Object survives → Survivor space
  
Time 2: Young GC  
  → Object survives → Survivor space (age 2)
  
Time 15: Young GC (after ~15 survivals)
  → Object promoted to Old Gen
  
Old Gen:
  [cache entry] (stays here forever!)
  
Problem: Old Gen uses Mark-Sweep-Compact
  - Slower GC
  - Longer pauses
  - Fragmentation risk
```

**✅ RIGHT Approach:**
```java
@Service
public class CacheService {
    // Option 1: Use Guava Cache with expiration
    private LoadingCache<String, byte[]> cache = CacheBuilder.newBuilder()
        .maximumSize(10000)
        .expireAfterWrite(10, TimeUnit.MINUTES)  // ✅ Auto-evict
        .build(CacheLoader.from(() -> null));
    
    // Option 2: Use Caffeine (better performance)
    private Cache<String, byte[]> cache = Caffeine.newBuilder()
        .maximumSize(10000)
        .expireAfterWrite(10, TimeUnit.MINUTES)
        .build();
    
    // Option 3: Use WeakHashMap for soft references
    private Map<String, WeakReference<byte[]>> cache = new WeakHashMap<>();
}
```

---

### Mistake 3: Forcing Full GC

**❌ WRONG:**
```java
@RestController
public class MaintenanceController {
    @PostMapping("/cleanup")
    public ResponseEntity<?> cleanup() {
        // Clear some caches
        cacheService.clearAll();
        
        System.gc();  // ❌ BAD! Forces expensive Full GC
        
        return ResponseEntity.ok("Cleaned");
    }
}
```

**What happens:**
```
System.gc() typically triggers:
1. Young GC (fast, 10-50ms)
2. Old Gen compaction (slow, 1-5 seconds)
   - All application threads paused
   - ALL requests blocked
   
Production impact:
- All API requests timeout
- Cascading failures
- Customer complaints
```

**✅ RIGHT:**
```java
@RestController
public class MaintenanceController {
    @PostMapping("/cleanup")
    public ResponseEntity<?> cleanup() {
        // Clear caches
        cacheService.clearAll();
        
        // Let JVM decide when to GC ✅
        // Or use explicit memory management:
        cacheService.evictOldEntries();
        
        return ResponseEntity.ok("Cleaned");
    }
}

// If you REALLY need to trigger GC (rare):
@RestController
public class AdminController {
    @PostMapping("/admin/force-gc")
    public ResponseEntity<?> forceGC() {
        // Log warning
        logger.warn("Manual GC requested by admin");
        
        // Check if safe
        if (activeRequestCount.get() > 0) {
            return ResponseEntity.status(503).body("Busy, try later");
        }
        
        // Trigger during maintenance window only
        System.gc();
        
        return ResponseEntity.ok("GC triggered");
    }
}
```

---

## 🧪 Complete Working Example: Demonstrating Fragmentation

```java
public class FragmentationDemo {
    
    static class LargeObject {
        private byte[] data;
        
        LargeObject(int sizeMB) {
            this.data = new byte[sizeMB * 1024 * 1024];
        }
        
        @Override
        protected void finalize() throws Throwable {
            System.out.println("GC'd: " + (data.length / 1024 / 1024) + "MB object");
        }
    }
    
    public static void main(String[] args) {
        System.out.println("=== Demonstrating Fragmentation ===\n");
        
        // Start with clean heap
        Runtime runtime = Runtime.getRuntime();
        System.gc();
        sleep(100);
        
        printMemory("Initial");
        
        // Create alternating pattern: keep some, discard some
        List<LargeObject> kept = new ArrayList<>();
        
        for (int i = 0; i < 10; i++) {
            LargeObject obj = new LargeObject(10);  // 10MB
            
            if (i % 2 == 0) {
                kept.add(obj);  // Keep even indices
                System.out.println("Kept object " + i);
            } else {
                System.out.println("Created + discarded object " + i);
                // obj becomes garbage immediately
            }
        }
        
        printMemory("After creating objects");
        
        // Trigger GC
        System.out.println("\n--- Triggering GC ---");
        System.gc();
        sleep(100);
        
        printMemory("After first GC");
        
        // Now try to allocate large object
        System.out.println("\n--- Attempting to allocate 25MB object ---");
        try {
            LargeObject large = new LargeObject(25);
            System.out.println("✅ Allocation succeeded");
            printMemory("After large allocation");
        } catch (OutOfMemoryError e) {
            System.out.println("❌ Allocation failed due to fragmentation!");
            System.out.println("   (Even though total free space exists)");
        }
        
        // Clear everything
        System.out.println("\n--- Clearing all references ---");
        kept.clear();
        System.gc();
        sleep(100);
        
        printMemory("After clearing all");
    }
    
    static void printMemory(String label) {
        Runtime runtime = Runtime.getRuntime();
        long total = runtime.totalMemory();
        long free = runtime.freeMemory();
        long used = total - free;
        long max = runtime.maxMemory();
        
        System.out.printf("%s:\n", label);
        System.out.printf("  Used:  %dMB / %dMB\n", used / 1024 / 1024, total / 1024 / 1024);
        System.out.printf("  Free:  %dMB\n", free / 1024 / 1024);
        System.out.printf("  Max:   %dMB\n\n", max / 1024 / 1024);
    }
    
    static void sleep(int ms) {
        try { Thread.sleep(ms); } catch (Exception e) {}
    }
}
```

**Run with:**
```bash
java -Xms256m -Xmx256m -XX:+UseSerialGC -verbose:gc FragmentationDemo
```

**Expected Output:**
```
=== Demonstrating Fragmentation ===

Initial:
  Used:  2MB / 245MB
  Free:  243MB
  Max:   256MB

Kept object 0
Created + discarded object 1
Kept object 2
Created + discarded object 3
Kept object 4
Created + discarded object 5
Kept object 6
Created + discarded object 7
Kept object 8
Created + discarded object 9

After creating objects:
  Used:  102MB / 245MB
  Free:  143MB
  Max:   256MB

--- Triggering GC ---
[GC (System.gc())  102MB->52MB(245MB), 0.0123 secs]
GC'd: 10MB object
GC'd: 10MB object
GC'd: 10MB object
GC'd: 10MB object
GC'd: 10MB object

After first GC:
  Used:  52MB / 245MB
  Free:  193MB
  Max:   256MB

--- Attempting to allocate 25MB object ---
✅ Allocation succeeded
(Note: Modern JVMs compact automatically when needed)

After large allocation:
  Used:  77MB / 245MB
  Free:  168MB
  Max:   256MB

--- Clearing all references ---
[GC (System.gc())  77MB->2MB(245MB), 0.0089 secs]

After clearing all:
  Used:  2MB / 245MB
  Free:  243MB
  Max:   256MB
```

**Note:** Modern JVMs (especially with compacting collectors like G1) often compact automatically when fragmentation is detected, so you may not see OOM in this demo. The principle still applies to production systems at scale.

---

## 🎯 Interview-Ready Answer

**Question:** "Explain the difference between mark-sweep and mark-compact GC algorithms."

**Your Answer:**
```
After the marking phase identifies live objects, the JVM has multiple 
strategies for reclaiming memory from dead objects:

**Mark-Sweep (Used by: CMS):**
- Simply marks freed memory regions as available
- Fast: O(n) where n = number of dead objects
- Problem: Causes fragmentation - gaps between live objects
- Risk: Can lead to OutOfMemoryError even with sufficient total free 
  space, because no single contiguous block is large enough
- Best for: Low-latency requirements where pause time matters more than 
  fragmentation

**Mark-Sweep-Compact (Used by: Parallel Old, Serial Old):**
- After marking and sweeping, moves all live objects together
- Eliminates fragmentation completely
- Slower: Must move objects AND update all references pointing to them
- Longer STW pause: Typically 2-5x longer than mark-sweep
- Best for: Throughput-oriented applications, batch processing

**Copy Collection (Used by: Young Gen in all collectors):**
- Divides space into "From" and "To" regions
- Copies only live objects from From → To
- Abandons entire From space
- Fastest: No explicit sweep, just copy survivors
- Requires: 2x memory overhead
- Perfect for: Young Gen where 90%+ objects die young, so copying is 
  minimal

In production, most modern collectors use a hybrid approach:
- Young Gen: Always copying (fast, objects die quickly)
- Old Gen: Mark-sweep-compact or incremental compaction (G1)
- Goal: Balance throughput, latency, and memory efficiency

The choice affects:
- GC pause times: Copy < Mark-Sweep < Mark-Compact
- Memory efficiency: Mark-Compact > Mark-Sweep > Copy
- Fragmentation risk: Mark-Sweep (high), others (none)
```

---

## 📋 Quick Checklist

- [ ] Understand three sweeping strategies (Sweep, Compact, Copy)
- [ ] Can explain fragmentation and its impact
- [ ] Know which collectors use which strategy
- [ ] Understand Young Gen always uses copying
- [ ] Can explain compaction penalty (longer pause)
- [ ] Know when fragmentation causes OOM despite free memory

---

## 🚨 Critical Pitfalls in Production

### Pitfall 1: CMS Collector Fragmentation Failure

**❌ Problem Scenario:**

```java
@Service
public class BatchProcessor {
    public void processBatch() {
        // Processes 10K orders, each allocates temporary objects
        for (Order order : loadOrders()) {
            byte[] report = generateReport(order);  // 5MB each
            sendEmail(report);
            // report becomes garbage
        }
    }
}
```

**What happens with CMS (Mark-Sweep only):**
```
Cycle 1: [Obj1][Free][Obj2][Free][Obj3]
Cycle 2: [Obj1][Free][Obj4][Free][Obj3]
Cycle 3: [Obj1][Free][Obj4][Free][Obj5]
...
After 1000 cycles: [Obj][F][Obj][F][Obj][F]... (Heavily fragmented)

Allocation of large object (10MB):
  ❌ No contiguous 10MB block available
  → Triggers "Concurrent Mode Failure"
  → Falls back to Serial Old GC
  → Full STW compaction (5-10 seconds!)
```

**Real Impact:** Payment processing service:
- Running CMS for low-latency
- After 48 hours: concurrent mode failure
- Full GC pause: **8.2 seconds**
- 1000+ payment requests timed out
- $50K in failed transactions

**GC Logs:**
```
[CMS-concurrent-mark: 0.123s]
[CMS-concurrent-preclean: 0.045s]
[CMS: 18000K->18000K(20000K), 0.5s]  ← Heap didn't shrink!
[Full GC (Allocation Failure): 18000K->12000K(20000K), 8.2s]
                               ↑ Concurrent Mode Failure!
```

**✅ Solution 1: Switch to G1 GC**
```bash
# G1 does incremental compaction
java-XX:+UseG1GC \
     -XX:MaxGCPauseMillis=200 \
     -XX:G1HeapRegionSize=16M \
     -jar app.jar
```

**✅ Solution 2: Tune CMS (if must use CMS)**
```bash
# Start concurrent cycle earlier
java -XX:+UseConcMarkSweepGC \
     -XX:CMSInitiatingOccupancyFraction=70 \  # Start at 70% (default 92%)
     -XX:+UseCMSInitiatingOccupancyOnly \
     -XX:+CMSScavengeBeforeRemark \
     -jar app.jar
```

**✅ Solution 3: Reduce Object Allocation**
```java
@Service
public class BatchProcessor {
    // Reuse buffer pool
    private static final GenericObjectPool<ByteBuffer> BUFFER_POOL = 
        new GenericObjectPool<>(new ByteBufferFactory(5_000_000));
    
    public void processBatch() {
        for (Order order : loadOrders()) {
            ByteBuffer buffer = BUFFER_POOL.borrowObject();
            try {
                generateReport(order, buffer);  // ✅ Reuse buffer
                sendEmail(buffer);
            } finally {
                buffer.clear();
                BUFFER_POOL.returnObject(buffer);  // ✅ Return to pool
            }
        }
    }
}
```

---

### Pitfall 2: Premature Promotion to Old Gen

**❌ Problem Code:**
```java
@RestController
public class DataController {
    @GetMapping("/data")
    public ResponseEntity<byte[]> getData() {
        // Large temporary object
        byte[] data = loadLargeData();  // 5MB
        byte[] processed = processData(data);  // Another 5MB
        return ResponseEntity.ok(processed);
        // 'data' and 'processed' should die young
    }
}
```

**What happens under load:**
```
Request rate: 100 req/s
Each request: 10MB temporary objects
Total allocation: 1GB/s

Young Gen: 512MB
Young GC frequency: Every 512ms

Problem:
- Some objects survive Young GC (unlucky timing)
- After 15 survivals → Promoted to Old Gen
- Old Gen fills with temporary objects!
- Triggers expensive Old Gen GC
```

**Real Impact:** API service:
- p99 latency: 50ms (target)
- After premature promotion: p99 = 2.5 seconds
- Cause: Old Gen GC pauses every 10 minutes
- SLA violated

**GC Logs:**
```
[GC (Allocation Failure) [PSYoungGen: 512M->64M(512M)] 0.050s]  ← Young GC (good)
[GC (Allocation Failure) [PSYoungGen: 512M->128M(512M)] 0.055s]
[GC (Allocation Failure) [PSYoungGen: 512M->256M(512M)] 0.080s]
                                              ↑ Survivors growing!
[Full GC (Ergonomics) [PSYoungGen: 512M->0K][ParOldGen: 4096M->2048M(8192M)] 2.5s]
                                             ↑ Old Gen GC!
```

**✅ Solution 1: Increase Young Gen Size**
```bash
# Give temporary objects more time to die
java -Xmx16g \
     -XX:NewRatio=1 \          # Young = 50% of heap (default: 33%)
     -XX:MaxTenuringThreshold=15 \
     -jar app.jar
```

**✅ Solution 2: Reduce Per-Request Allocation**
```java
@RestController
public class DataController {
    @Autowired
    private DataStreamService streamService;
    
    @GetMapping("/data")
    public void getData(HttpServletResponse response) {
        // Stream directly to response, avoid large allocations
        streamService.streamData(response.getOutputStream());
        // ✅ No large temporary objects!
    }
}
```

**✅ Solution 3: Use Object Pooling**
```java
@Configuration
public class BufferPoolConfig {
    @Bean
    public GenericObjectPool<ByteBuffer> bufferPool() {
        return new GenericObjectPool<>(
            new BasePooledObjectFactory<ByteBuffer>() {
                @Override
                public ByteBuffer create() {
                    return ByteBuffer.allocateDirect(5_000_000);
                }
                @Override
                public PooledObject<ByteBuffer> wrap(ByteBuffer obj) {
                    return new DefaultPooledObject<>(obj);
                }
            }
        );
    }
}
```

---

### Pitfall 3: Ignoring Humongous Objects (G1 GC)

**❌ Problem Code:**
```java
@Service
public class ImageProcessor {
    public byte[] processImage(MultipartFile file) {
        byte[] image = file.getBytes();  // Could be 10MB+
        byte[] processed = applyFilters(image);
        return processed;
    }
}
```

**What happens with G1 GC:**
```
G1 Region Size: 2MB (default for 8GB heap)

Object > 1MB = "Humongous" object
- Allocated directly in Old Gen!
- Takes multiple contiguous regions
- Not collected during Young GC
- Only collected during mixed/full GC
```

**Real Impact:** Image processing service:
- 1000 images/min uploaded
- Each 5MB (Humongous)
- All go to Old Gen immediately
- Old Gen fills quickly
- Frequent Old Gen GCs

**GC Logs:**
```
[GC pause (G1 Humongous Allocation) 1024M->1024M(2048M), 0.010s]
              ↑ Humongous object allocated
[GC pause (G1 Evacuation Pause) (mixed) 1536M->1024M(2048M), 0.250s]
              ↑ Must collect Old Gen
```

**✅ Solution 1: Increase G1 Region Size**
```bash
# Make regions larger so objects aren't "humongous"
java -XX:+UseG1GC \
     -XX:G1HeapRegionSize=8M \  # 8MB regions, so <4MB not humongous
     -Xmx16g \
     -jar app.jar
```

**✅ Solution 2: Stream Large Objects**
```java
@Service
public class ImageProcessor {
    public void processImage(MultipartFile file, OutputStream out) {
        // Process in chunks, don't load entire image
        try (InputStream in = file.getInputStream()) {
            byte[] buffer = new byte[8192];  // ✅ Small buffer
            int read;
            while ((read = in.read(buffer)) != -1) {
                processChunk(buffer, 0, read);
                out.write(buffer, 0, read);
            }
        }
    }
}
```

**✅ Solution 3: Direct ByteBuffers (Off-Heap)**
```java
@Service
public class ImageProcessor {
    public ByteBuffer processImage(MultipartFile file) {
        // Use off-heap memory (not subject to GC)
        int size = (int) file.getSize();
        ByteBuffer buffer = ByteBuffer.allocateDirect(size);
        
        // Process...
        
        return buffer;  // ✅ Not on GC heap
    }
    
    // Must manually free:
    public void cleanup(ByteBuffer buffer) {
        if (buffer.isDirect()) {
            ((DirectBuffer) buffer).cleaner().clean();
        }
    }
}
```

---

## 🔄 Follow-Up Questions & Answers

### Q1: "how does compaction update all references to moved objects?"

**Answer:**
```
When objects are moved during compaction, the JVM must update all 
references pointing to them. This happens in multiple phases:

**Phase 1: Mark Phase**
- Identify all live objects
- Calculate new addresses (compacted layout)
- Record forwarding pointers: Old Address → New Address

**Phase 2: Update References**
- Scan all GC Roots (Stack, Static)
- For each reference:
  - Check forwarding table
  - Update to new address
- Scan all objects:
  - Update their internal references

**Phase 3: Move Objects**
- Copy object data to new locations
- Update object headers

Example:
Before compaction:
Stack: p → Object A at 0x1000
       q → Object B at 0x2000
A.child → Object B at 0x2000

Forwarding table after marking:
0x1000 → 0x500  (A)
0x2000 → 0x550  (B)

After updating references:
Stack: p → Object A at 0x500 ✅
       q → Object B at 0x550 ✅
A.child → Object B at 0x550 ✅

This is why compaction is slow - must scan ALL references in:
- Stack frames
- Static variables
- All live objects
- Remember sets
- Code cache

Modern collectors optimize by:
1. Parallel updating (multiple threads)
2. Regional compaction (G1)
3. Concurrent compaction (Shenandoah, ZGC)
```

---

### Q2: "Why use copying instead of compacting in Young Gen?"

**Answer:**
```
Copying is faster than mark-sweep-compact in Young Gen because of the 
"weak generational hypothesis": Most objects die young (90-98%).

**Copying Collection (Young Gen):**
- Only copy LIVE objects (2-10% of objects)
- Example: 512MB heap, 20MB survives
- Work: Copy 20MB → 0.02 seconds
- Complexity: O(live objects)

**Mark-Sweep-Compact (if used in Young Gen):**
- Must sweep entire heap
- Example: 512MB heap, 492MB garbage
- Work: Mark all + Sweep 492MB + Compact 20MB → 0.15 seconds
- Complexity: O(heap size)

**Math:**
Young Gen: 512MB
Survival rate: 5%

Copying: Copy 25MB = 25ms
Compacting: Sweep 512MB + Compact 25MB = 120ms

Copying is 4-5x faster in Young Gen!

In Old Gen, the opposite is true:
- Most objects are long-lived (70-90% survive)
- Copying 70% of objects is expensive
- Mark-sweep better (or incremental compaction like G1)

This is why all modern collectors use:
- Young Gen: Copy (Eden → Survivor → Survivor)
- Old Gen: Mark-Sweep-Compact or incremental
```

---

### Q3: "What are write barriers and why needed?"

**Answer:**
```
Write barriers are code inserted by the JVM whenever an application 
thread modifies an object reference. They're critical for:

1. Concurrent GC (tracking changes during GC)
2. Generational GC (tracking old → young references)
3. Regional GC like G1 (tracking inter-region references)

**Example: Generational Write Barrier**

Without barrier:
Old Gen Object A
  ↓
Young Gen Object B

Young GC:
- Scans only Young Gen
- Doesn't see A → B reference
- B incorrectly collected!

With write barrier:
// Application code:
oldObject.field = youngObject;

// JVM inserts:
if (oldObject in Old Gen && youngObject in Young Gen) {
    markCardTable(oldObject);  // Mark card as "dirty"
}

// During Young GC:
- Scan GC Roots
- Scan dirty cards in Old Gen ✅
- Find A → B reference ✅
- B correctly survives ✅

**Example: Concurrent GC Barrier (G1, ZGC)**

Problem:
Thread 1 (GC): Marks A as black (done processing)
Thread 2 (App): A.child = C (adds new reference)
Thread 3 (GC): Finishes marking
Result: C not marked → incorrectly collected!

Solution - Write Barrier:
// Application code:
A.child = C;

// JVM inserts:
if (A is BLACK && C is WHITE) {
    markAsGray(A);  // Re-scan A
    // OR
    markAsGray(C);  // Mark C immediately
}

**Performance Cost:**
- Every reference write has small overhead (10-20 cycles)
- But enables concurrent GC
- Worth it for reduced pause times

In production:
- Write barriers auto-inserted by JIT compiler
- Negligible performance impact (<1% throughput)
- Critical for low-latency collectors (G1, ZGC, Shenandoah)
```

---

### Q4: "Can objects be moved while application is running?"

**Answer:**
```
Depends on the GC algorithm:

**Traditional GCs (Serial, Parallel, CMS): NO**
- Objects moved only during STW pauses
- Safe: No application threads accessing objects

**Modern Low-Latency GCs (ZGC, Shenandoah): YES**
- Objects can be moved while application runs
- Called "concurrent compaction" or "concurrent evacuation"

**How is this safe?**

**ZGC Approach - Load Barriers:**
Every object access:
Object obj = someRef;

Is compiled to:
Object obj = loadBarrier(someRef);

// loadBarrier checks:
if (obj has been moved) {
    // Self-heal: update reference to new location
    someRef = obj.newAddress;
    return obj.newAddress;
} else {
    return obj;
}

**Example:**
Thread 1 (GC): Moves Object A from 0x1000 → 0x2000
Thread 2 (App): Accesses A via field.ref (still points to 0x1000)
Load barrier:
  - Detects forwarding pointer at 0x1000
  - Updates field.ref to 0x2000
  - Returns 0x2000

**Shenandoah Approach - Brooks Pointers:**
Every object has hidden forwarding pointer:
[Forwarding Ptr][Object Data]

Initially: Points to itself
After move: Points to new location

**Performance Cost:**
- Load barriers on every reference read
- 5-10% throughput impact
- But: GC pauses <10ms (vs 100-1000ms for traditional)

**Production Decision:**
- Need <10ms pauses? → Use ZGC/Shenandoah
- Prefer throughput? → Use G1/Parallel

Most apps: G1 is best balance
Ultra-low latency: ZGC
```

---

### Q5: "How do you detect fragmentation in production?"

**Answer:**
```
**Method 1: GC Logs**

Symptom: Old Gen size doesn't decrease after GC
[Full GC: 7000K->7000K(10000K), 1.5s]
                      ↑ No reduction = fragmentation or leak

Healthy:
[Full GC: 7000K->2000K(10000K), 0.8s]
                      ↑ Good reduction

**Method 2: Heap Dump Analysis**

VisualVM or Eclipse MAT:
- Look for many small free blocks
- Check largest contiguous free block
- If "Largest Free" << "Total Free" → Fragmentation

Example:
Total Heap: 8GB
Used: 6GB
Free: 2GB
Largest Free Block: 50MB ← Problem!

**Method 3: GC Metrics**

Prometheus/Grafana:
jvm_memory_pool_bytes{pool="PS Old Gen"}
jvm_gc_pause_seconds{action="end of major GC"}

Alert if:
- Old Gen usage >85% for >10 minutes
- Major GC frequency increasing
- Major GC time increasing

**Method 4: -XX:+PrintFLSStatistics (CMS)**

Shows free list fragmentation:
Total Free Space: 2048K
Number of Free Blocks: 1024 ← Many small blocks = fragmented
Average Block Size: 2K

**Method 5: Application Symptoms**

- OutOfMemoryError with plenty of free memory
- GC logs showing "concurrent mode failure"
- Increasing Full GC frequency
- Erratic allocation failures

**Production Monitoring Setup:**

# GC logging
java -Xlog:gc*:file=gc.log \
     -XX:+PrintGCDetails \
     -XX:+PrintGCDateStamps \
     -jar app.jar

# Monitor:
1. Old Gen usage trend (should be sawtooth)
2. GC pause time trend (should be stable)
3. GC frequency (should be predictable)
4. Heap usage after Full GC (should drop significantly)

Alert if:
- Old Gen >90% for >5 min
- Full GC pause >2s
- Full GC frequency >1 per hour
- Concurrent mode failure
```

---

## 🎓 Key Takeaways

| Concept | Why Important | Interview Score |
|---------|---------------|-----------------|
| Mark-Sweep vs Compact | Algorithm trade-offs | ⭐⭐⭐⭐⭐ |
| Fragmentation causes OOM | Production debugging | ⭐⭐⭐⭐⭐ |
| Copying for Young Gen | Why it's fast | ⭐⭐⭐⭐ |
| Compaction penalty | Longer STW pauses | ⭐⭐⭐⭐ |
| Write barriers | Concurrent GC enabler | ⭐⭐⭐ |

---

## 🔗 What's Next?

Now that you understand sweeping and compaction, learn **how the heap is structured**:
- [Q5: Heap Generations](Q5_heap_generations.md) - Young Gen, Old Gen, Metaspace

---

**Last Updated:** March 1, 2026
