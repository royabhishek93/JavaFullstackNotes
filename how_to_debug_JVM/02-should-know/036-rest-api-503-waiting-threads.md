# #36 — REST API 503ing With WAITING Threads

> **Category:** Thread Dump Analysis | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"A REST API starts returning 503s. Thread dump shows all Tomcat threads in WAITING state with `java.lang.Object.wait()` in the stack. Is this a problem?"

## 😊 Explain It Simply (for anyone)
Picture a taxi rank with 50 taxis lined up, engines off, drivers relaxing, simply waiting for the dispatcher to radio them with a new job. That's completely normal — an idle, healthy taxi rank. Now imagine passengers standing on the street complaining they can't get a ride, even though there are 50 idle taxis right there. Something else must be broken — maybe the dispatch radio itself is down, or the street entrance to the taxi rank is blocked off, so passengers never even reach the taxis.

In server terms, threads sitting in `Object.wait()` (WAITING state) are like those idle, relaxed taxis — they're healthy workers with nothing to do right now, patiently waiting for the "dispatcher" (the network connector) to hand them a request. Seeing WAITING threads is *not* itself a red flag. If your users are getting errors anyway, the problem must be somewhere upstream — before requests even reach the worker threads.

## 📊 Visualize It
```
Client ──?──► [Load Balancer] ──?──► [Tomcat Connector Queue]
                                            │
                                   50 threads: WAITING (idle, healthy)
                                            │
                                   ...but 503s still happening!
                                   → check LB timeout, acceptCount,
                                     max-connections, crash loop
```

## 🏭 The Real Production Answer (15-YOE Level)
"No — and this is a trap. WAITING is the *expected* state for idle threads in a Tomcat thread pool. Tomcat's NIO connector threads sit in `java.lang.Object.wait()` waiting for the selector to signal incoming work. If all threads are in WAITING, that means the thread pool is *idle* — there are no incoming requests being processed.

So the 503 is coming from somewhere else. I'd look at:

1. Is Tomcat even receiving the requests? Check the connector acceptCount queue.
2. Is there a load balancer upstream that's timing out before Tomcat responds?
3. Is the application crash-looping and not actually serving?
4. Check `server.tomcat.max-connections` — if you've hit the max connections limit, new connections are rejected even if threads are available.

The distinguishing jstack pattern for a real Tomcat problem is threads in BLOCKED state on a shared resource, not WAITING state. WAITING Tomcat threads = healthy idle pool."

## 🔑 Key Takeaway
All threads in WAITING means the pool is idle and healthy — a 503 with WAITING threads means you must look upstream (load balancer, connector limits, crash loops), not at the thread pool itself.
