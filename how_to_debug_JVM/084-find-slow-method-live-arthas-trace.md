# #84 — Find the Slow Method in a Live Spring Boot Service — No Restart Allowed

> **Category:** Production Debugging Tools | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Your order processing service response time jumped from 50ms to 800ms. How do you find the slow method in production without restarting?"

## 😊 Explain It Simply (for anyone)
Imagine a hospital patient suddenly feels much weaker, but doctors can't put them under anesthesia to "restart" and re-examine from scratch — the patient has to keep living and working while being diagnosed. A skilled doctor instead attaches a live monitor (like an ECG) that watches the heart, lungs, and blood vessels one by one, in real time, to find exactly which organ is struggling.

That's what happens here. The "patient" is a running Java application that suddenly got 16x slower (50ms → 800ms). We can't restart it (that would be like sending the patient home, which doesn't fix or diagnose anything). Instead, we attach a special live-monitoring tool called Arthas directly to the running process. It lets us "trace" a method call the same way a doctor traces blood flow — watching each step (each sub-call) and timing exactly how long each one takes, until we find the one slow link in the chain.

In this case, it turns out the slowness isn't in our own code logic — it's in getting a database connection from a pool (like waiting in a long line at a bank teller because there aren't enough tellers open). The fix isn't to rewrite code; it's to open more "teller windows" (increase the connection pool size).

## 📊 Visualize It
```
 Request (800ms) ─▶ OrderService.processOrder()
                        │
                        ▼
                 InventoryService.checkStock()  [780ms]
                        │
                        ▼
             InventoryRepository.findByProductId() [775ms]
                        │
                        ▼
                 HikariCP.getConnection()  ◀── BOTTLENECK (770ms)
                        │
                 (pool exhausted, waiting)
```

## 🏭 The Real Production Answer (15-YOE Level)
Three tools in order:

**Step 1 — Arthas trace (fastest diagnosis):**
```bash
# Start Arthas
java -jar arthas-boot.jar <pid>

# Trace processOrder and all its sub-calls, show top 20 slowest
trace com.myapp.OrderService processOrder '#cost > 100'

# Output shows call tree with timing:
# ---[800ms]--- OrderService.processOrder()
#     ---[780ms]--- InventoryService.checkStock()
#         ---[775ms]--- InventoryRepository.findByProductId()
#             ---[770ms]--- HikariCP.getConnection()  <-- HERE
```

**Step 2 — Watch the slow method's args:**
```bash
# See what product ID causes the slowdown
watch com.myapp.InventoryRepository findByProductId '{params, returnObj}' '#cost > 500'
```

**Step 3 — Root cause:** HikariCP connection wait = pool too small for current load. Fix: increase `maximumPoolSize` or investigate why connections aren't being returned.

## 🔑 Key Takeaway
Use `trace` with a cost filter (`#cost > N`) to zero in on the exact slow hop in a live call chain without ever restarting the JVM.
