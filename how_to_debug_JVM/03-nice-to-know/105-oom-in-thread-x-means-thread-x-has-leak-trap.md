# #105 — "OOM in Thread X" Doesn't Mean Thread X Has the Leak

> **Category:** Heap Dump Analysis | **Type:** Senior Trap Question | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"The OOM stack trace shows it happened in the HTTP request handler thread pool. So the leak is in the request handler code."

## 😊 Explain It Simply (for anyone)
Think of a shared parking garage that slowly fills up over the whole day because one specific delivery truck (a background job) keeps parking cars in a corner every morning and never moves them. The garage doesn't actually become "full" (no free spots) until late afternoon, at which moment it just so happens that an ordinary employee car (an unrelated HTTP request thread) is the one that drives up looking for a spot and gets turned away at the gate.

If you only look at WHO got turned away at the gate (the OOM stack trace), you'd wrongly blame that ordinary employee's car — but they did nothing wrong, they simply had the bad luck of arriving right when the garage finally ran out of room. The real culprit is the delivery truck that quietly filled the corner hours earlier.

## 📊 Visualize It
```
02:00 AM  Background thread:  fills 2GB of retained cache objects
   ...      (heap slowly fills all day, nobody notices)
03:00 PM  HTTP-thread-42 tries to allocate a 1KB String
                → heap has zero room left
                → OutOfMemoryError thrown HERE (in HTTP-thread-42's stack)

  Stack trace says: "HTTP-thread-42, controller.handleRequest()"
  ❌ WRONG conclusion: "leak is in the request handler"
  ✅ RIGHT approach: heap dump → Dominator Tree → GC Root path
       → points back to the 2 AM background cache refresh task
```

## 🏭 The Real Production Answer (15-YOE Level)

This is a critical misunderstanding of where OOM is thrown. `OutOfMemoryError` is thrown at the point where the allocation *fails* — i.e., where the JVM tried to allocate memory and found none available.

The thread that failed to allocate is almost never the thread responsible for the leak. The leaking thread already put the objects on the heap hours or days ago — those objects simply never got collected.

Example: A background thread running a scheduled cache refresh created 2 GB of retained objects at 2 AM. At 3 PM, a routine HTTP request thread tries to allocate a 1 KB `String` and gets OOM. The stack trace points to the HTTP thread's request handling code. But the leak is in the cache refresh scheduled task.

Correct approach: Look at heap dump dominator tree and GC root paths — not the OOM stack trace — to find the responsible code.

## 🔑 Key Takeaway
The thread that throws OOM is just the unlucky one that asked for memory last — use the heap dump's GC-root path, not the stack trace, to find who actually retained the memory.
