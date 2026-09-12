# #138 — How does ZGC achieve sub-millisecond pauses on a 100GB heap?

> **Category:** GC Tuning & Debugging | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"How does ZGC achieve sub-millisecond pauses on a 100GB heap?"

## 😊 Explain It Simply (for anyone)
Imagine a massive library that needs to reorganize its entire collection while staying open to visitors, and it manages this with two clever tricks. First, every bookshelf label (a "pointer" pointing to where a book lives) has a tiny hidden sticker on it that says whether that book has already been moved or not — like a coded tag, invisible to visitors but readable by staff. Second, whenever a visitor tries to pick up a book using an old label, a librarian standing right there quietly checks the sticker, realizes the book moved, and hands them the current location instead — the visitor never even notices a delay. Because of these two tricks, books (objects) can be physically relocated to new shelves *while people are still browsing*, without ever needing to close the library. The only times the doors do briefly lock are for a few seconds of setup and final bookkeeping — each lasting under a millisecond.

## 📊 Visualize It
```
64-bit pointer (colored):
[unused bits][marked][remapped][finalizable][      address bits      ]
                 ↑ metadata embedded directly in the pointer

Access an object reference:
  Thread reads pointer → Load Barrier checks color bits
    → stale? fix pointer on the fly (self-heal)
    → not stale? proceed normally
  (all concurrent, no STW needed for relocation itself)
```

## 🏭 The Real Production Answer (15-YOE Level)
> ZGC uses three techniques that fundamentally differ from G1GC:
>
> 1. **Colored pointers**: ZGC embeds GC metadata (marked, remapped, finalized flags) directly in the 64-bit pointer using spare bits. This allows the GC to know an object's GC state without a separate table.
>
> 2. **Load barriers**: Every object reference load executes a tiny code snippet (the load barrier) that checks and corrects stale pointers. This is how ZGC can move objects concurrently without stopping threads — threads update their own stale pointers when they next access them.
>
> 3. **Concurrent relocation**: Objects are moved while application threads run. The old location is kept valid via forwarding pointers until all stale references are healed.
>
> The STW phases in ZGC are only: Initial Mark (< 1ms), Remark (< 1ms), and Relocate Start (< 1ms). Everything else is concurrent.

```bash
# ZGC tuning is minimal — it's mostly self-tuning:
-XX:+UseZGC
-Xmx<size>                              # Give it plenty of heap headroom
-XX:ZCollectionInterval=0               # Default: GC-triggered, not interval-based
-XX:ZFragmentationLimit=25              # Trigger GC when 25% fragmentation

# ZGC heap headroom — ZGC needs extra heap to relocate objects concurrently:
# Rule of thumb: ZGC needs 20-30% more heap than G1GC for same workload
# If G1GC needs 8GB, ZGC might need 10-12GB

# Monitor ZGC:
-Xlog:gc*:file=/var/log/app/gc.log:time,uptime:filecount=10,filesize=10m
# Look for: "Garbage Collection" lines showing pause and concurrent times
```

## 🔑 Key Takeaway
Colored pointers plus load barriers let ZGC relocate objects concurrently and self-heal stale references, keeping every STW phase under a millisecond regardless of heap size.
