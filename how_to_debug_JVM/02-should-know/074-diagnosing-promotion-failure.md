# #74 — Walk through diagnosing a promotion failure

> **Category:** GC Tuning & Debugging | **Type:** Advanced Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Walk through diagnosing a promotion failure."

## 😊 Explain It Simply (for anyone)
Think of a small apartment (young generation) where new tenants (objects) stay temporarily before "graduating" to a permanent house (the old generation) once they've proven they'll stick around a while. Now imagine moving day arrives and the permanent houses are already full — there's nowhere for the graduating tenants to go. So they're forced to stay crammed in the temporary apartment, which then gets awkwardly re-labeled as "permanent" on the spot, even though it wasn't built for that. This creates a messy, mismatched neighborhood (memory fragmentation), and pretty soon the whole town needs an emergency, all-hands reorganization (a Full GC) to sort everything out properly. That's a "promotion failure" — objects that were supposed to graduate into long-term memory find there's no room, and the system has to improvise in a way that causes bigger problems shortly after.

## 📊 Visualize It
```
Young GC tries to promote objects → Old Gen
Old Gen: [████████████████░░] 88.7% full ← barely any room

Promotion attempt FAILS
  → objects stay in Eden/Survivor, regions relabeled as Old (evacuation failure)
  → fragmentation ↑
  → Full GC likely soon after
```

## 🏭 The Real Production Answer (15-YOE Level)
> Promotion failure occurs when the Old generation cannot accommodate all the objects that need to be promoted from the Young generation during a Young GC. G1GC handles this with "evacuation failure" — some objects stay in their original Eden/Survivor regions, which are then treated as Old regions. This causes region fragmentation and usually leads to a Full GC shortly after.

**Diagnostic flow:**

```bash
# Step 1: Confirm promotion failure in GC log
grep "evacuation failure\|promotion failed\|To-space exhausted" /var/log/app/gc.log

# Step 2: Check Old gen occupancy trend before the failure
# Look for: steady climb in O% in jstat output
jstat -gcutil <pid> 2000 120
# S0    S1    E       O      M     CCS   YGC   YGCT  FGC  FGCT   GCT
# 0.00  89.4  72.3    88.7   97.2  91.0  423   8.234   2  12.445  20.679
#                     ^^^^  ← Old at 88.7% = recipe for promotion failure

# Step 3: Root cause options:
# A) Allocation spike: burst of long-lived objects
# B) Tenuring threshold too low: objects being promoted too early
# C) Survivor space too small: overflow promotion

# Tuning levers:
-XX:MaxTenuringThreshold=15       # Default 15; increase to keep objects in young longer
-XX:SurvivorRatio=8               # Eden:Survivor ratio (default 8 → 8:1:1)
# Larger survivors = fewer overflow promotions

# For G1GC specifically — increase young gen ceiling:
-XX:G1MaxNewSizePercent=40        # Allow G1 to grow young gen more
```

## 🔑 Key Takeaway
A climbing Old-gen occupancy in `jstat` before an evacuation failure is the tell-tale sign of an impending promotion failure — fix survivor sizing and tenuring before it forces a Full GC.
