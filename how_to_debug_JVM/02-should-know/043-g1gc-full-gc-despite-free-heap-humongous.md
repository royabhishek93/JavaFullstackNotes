# #43 — G1GC keeps triggering Full GC even though heap has plenty of free space

> **Category:** GC Tuning & Debugging | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"G1GC keeps triggering Full GC even though heap has plenty of free space. How can Full GC happen when heap is not full?"

## 😊 Explain It Simply (for anyone)
Imagine a parking garage divided into small, identical parking spots. Now imagine a moving truck arrives that's too big for one spot — it needs several spots side-by-side, all empty and connected, to park. Even if the garage is mostly empty overall, if the empty spots are scattered randomly across different floors instead of next to each other, the truck can't park. That's exactly the problem with "humongous objects" in G1GC: it divides the heap (memory) into equal-sized regions (like parking spots), and any object bigger than half a region size needs multiple *contiguous* (side-by-side) regions. If your program creates lots of large objects, they can leave the heap looking like a checkerboard of used and empty spots — plenty of total empty space, but no single big empty block. When that happens, G1GC has to do a full, expensive cleanup (a "Full GC") just to rearrange everything into one clean, usable block.

## 📊 Visualize It
```
Heap Regions (each box = 1 region):
[used][FREE][used][FREE][used][FREE]  ← fragmented, no contiguous block
                                          
Need: 3 contiguous FREE regions for a humongous object
Result: none available → triggers Full GC to compact
```

## 🏭 The Real Production Answer (15-YOE Level)
> This is the humongous object problem. In G1GC, any object larger than half the region size is treated as a Humongous object. Humongous objects are allocated directly in Old-generation regions and are never moved. They can only be freed during a concurrent cycle or a Full GC.
>
> If you have many humongous objects fragmenting the old gen, G1GC may not be able to find a contiguous set of regions for a new humongous allocation, triggering a Full GC even though total free space exists.

**Diagnosis:**

```bash
# Find your current region size:
java -XX:+PrintFlagsFinal -version 2>&1 | grep G1HeapRegionSize
# Default is auto-calculated as heap/2048

# From GC log:
grep -i "humongous" /var/log/app/gc.log | wc -l  # How frequent?

# Enable humongous detail:
-Xlog:gc+humongous=debug:file=/var/log/app/gc.log:time,uptime
```

**Fix:**

```bash
# If your heap is 4GB and you have 4MB objects:
# Default region size = 4096MB / 2048 = 2MB
# 4MB object > 1MB (half of 2MB) → humongous

# Fix: increase region size so 4MB < half of region size:
-XX:G1HeapRegionSize=16m   # Now threshold = 8MB, 4MB object is NOT humongous

# Valid values: 1, 2, 4, 8, 16, 32 MB (must be power of 2)
# Rule of thumb: set so your largest common object < half of region size
```

## 🔑 Key Takeaway
Free heap ≠ usable heap — humongous object fragmentation can force Full GC even when total free space looks healthy.
