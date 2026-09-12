# #35 — "Metaspace OOM = Not Enough Memory, Add More" — The Trap

> **Category:** Heap Dump Analysis | **Type:** Senior Trap Question | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"We're getting Metaspace OOM. Let's add `-XX:MaxMetaspaceSize=512m` — currently it's 256m."

## 😊 Explain It Simply (for anyone)
If your bookshelf (Metaspace) keeps overflowing, the tempting fix is "buy a bigger bookshelf." That works ONLY if the number of unique books you genuinely need has simply outgrown a shelf that was sized too small from the start.

But if the REAL problem is that someone keeps printing brand new near-duplicate copies of the same book over and over and NEVER throwing any away (a classloader leak), then a bigger shelf just means it takes a bit longer to fill up completely — the overflow is guaranteed to happen again, just later, and now you'll have an even bigger mess to sort through when it finally does.

## 📊 Visualize It
```
jstat -gcmetacapacity <pid> 5000 100
  Sample 1:  MC = 200m
  Sample 2:  MC = 230m
  Sample 3:  MC = 255m   ← hits MaxMetaspaceSize=256m → OOM
                          (MC only ever climbs, NEVER drops = leak, not sizing)

"Fix" by raising to 512m:
  Sample 1:  MC = 200m
  Sample 2:  MC = 350m
  Sample 3:  MC = 510m   ← hits new limit → OOM again, just later

Real fix: jcmd <pid> VM.class_histogram | head -30
  look for $$EnhancerByCGLIB$$ / script-generated class name explosions
```

## 🏭 The Real Production Answer (15-YOE Level)

By default, Metaspace has no maximum and grows until the OS runs out of virtual address space. If you're hitting a `MaxMetaspaceSize` limit, either:

1. You explicitly set it too low (possible — but check if the app *ever* stabilized below that limit)
2. **More likely: there is a classloader leak** and no amount of Metaspace will ever be enough — it'll just OOM later

The tell: run `jstat -gcmetacapacity <pid> 5000 100` and watch whether `MC` (Metaspace Committed) is growing monotonically without any decreases. If it never drops, class unloading is not happening, which means classloaders are being retained.

Increasing `MaxMetaspaceSize` without finding the leak buys time but guarantees the OOM recurs — just later, and potentially with worse impact (larger Metaspace means more time before detection).

Diagnostic first step:
```bash
jcmd <pid> VM.class_histogram | head -30
# Watch for high counts of `$$EnhancerByCGLIB$$` or script class names
```

## 🔑 Key Takeaway
If Metaspace usage only ever climbs and never drops between GCs, that's a classloader leak — raising `MaxMetaspaceSize` just delays the identical crash.
