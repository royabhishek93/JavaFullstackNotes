# #6 — E-Commerce Checkout Dead Stop

> **Category:** Thread Dump Analysis | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"Your e-commerce platform completely stops accepting orders for 8 minutes during Black Friday peak traffic. CPU is near zero. No errors in application logs. On-call engineer pages you. What do you do?"

## 😊 Explain It Simply (for anyone)
Imagine two chefs in a kitchen. Chef A is holding the only knife and waiting for the only cutting board, which Chef B is holding. Chef B is holding the cutting board and waiting for the knife, which Chef A has. Neither chef will ever give up what they're holding, so neither can move forward — and no food gets made. That's a **deadlock**: two workers (threads, the little workers inside a program that do tasks) each holding something the other needs, forever stuck.

The weird giveaway is that the kitchen goes *silent* — no clattering pans, no noise — because nobody is actually working, they're just standing there waiting. In computer terms, that means the CPU (the "brain" doing the work) usage drops to nearly zero, because blocked threads use zero processing power while they wait.

A **thread dump** (`jstack`) is like walking into the kitchen and asking every chef "what are you doing right now?" — it's a snapshot listing every thread and exactly what it's holding or waiting for. Reading the dump lets you spot the exact circular wait and prove it's a deadlock, not something else.

## 📊 Visualize It
```
 checkout-thread-5              payment-thread-3
 ┌──────────────┐               ┌──────────────┐
 │ holds:        │               │ holds:        │
 │ InventoryLock │◄──wants──────►│ CartLock      │
 └──────────────┘               └──────────────┘
        ▲                              ▲
        └──────wants───────────────────┘
       (circular wait = DEADLOCK, CPU ≈ 0%)
```

## 🏭 The Real Production Answer (15-YOE Level)
"CPU near zero with no throughput — classic deadlock or thread pool exhaustion signature. Here's my exact sequence:

First, get a PID: `ps aux | grep java` or check the service wrapper.

Take three thread dumps immediately, 10 seconds apart:
```bash
jstack -l 12345 > /tmp/dump1.txt
sleep 10
jstack -l 12345 > /tmp/dump2.txt
sleep 10
jstack -l 12345 > /tmp/dump3.txt
```

Open dump1.txt and search for 'deadlock' first. If found, I see something like:
```
Found 1 deadlock.
=============================
"checkout-thread-5":
  waiting to lock monitor 0x00000006c2800f60 (object 0x000000076ab3d0c0, a com.shop.CartService),
  which is held by "payment-thread-3"
"payment-thread-3":
  waiting to lock monitor 0x00000006c2800f20 (object 0x000000076ab3d050, a com.shop.InventoryService),
  which is held by "checkout-thread-5"
```

If no deadlock, I count BLOCKED threads. If all Tomcat threads are BLOCKED with a HikariCP stack frame, it's pool exhaustion — likely a slow DB query holding connections.

For the immediate fix: if it's deadlock, restart the service (painful but necessary for Black Friday). File the incident. Fix the code post-peak.

For pool exhaustion: check if DB is alive, check slow query log, potentially kill long-running DB queries to unblock the connection pool.

Root cause always gets a post-mortem."

## 🔑 Key Takeaway
CPU near zero plus total throughput stall is the deadlock signature — take multiple `jstack` dumps immediately and search for "Found 1 deadlock" before doing anything else.
