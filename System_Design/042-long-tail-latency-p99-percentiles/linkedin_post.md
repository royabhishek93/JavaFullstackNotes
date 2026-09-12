# Long-Tail Latency & P99 Percentiles — LinkedIn Post

## Post Text (copy-paste ready)

Your average latency is 20ms. Your P99 is 2 seconds. That 100x gap is why users say "slow" while your dashboard says "green."

- 1% slow requests + 100 API calls per user session = 63% of sessions hit a slow request (1 - 0.99^100)
- Chain 5 microservices, each at P99=99% fast → composed P99 = 95.1%. End-to-end is worse than any single hop
- JVM full GC pauses (500ms-2s) show up ONLY in P99, never in P50 — that's your first diagnostic clue
- Hedged requests (Google's trick): duplicate the request at the P95 threshold, take whichever responds first — cuts P99 from 800ms to ~110ms for ~1% extra traffic
- Undersized connection pool (10 vs needed 60) turns a 50ms P99 into 250ms — just from queueing

Swipe → to see the 5 root causes of long-tail latency, the fan-out math, and the exact fix for each.

Save this. You'll need it in your next system design interview.

#SystemDesign #SoftwareArchitecture #InterviewPrep #Backend

---

## Caption Variants

### Variant A — Short (150 chars max)
P50=20ms, P99=2s — a 100x gap. Here's why averages lie and how Google's "hedged requests" fix it. 🎥👇

### Variant B — Long (400–600 chars)
"Average response time: 20ms" looks great on a dashboard — until you learn that 1% slow requests, multiplied across a 100-call user session, means 63% of your users hit a slow request (1 - 0.99^100). Payment systems at PhonePe/Paytm scale live and die by this: P50=20ms vs P99=2s is a real interview scenario. The fixes are concrete: hedged requests (Google/BigTable/Cassandra), Little's Law for connection pool sizing, ZGC for sub-10ms GC pauses, and Prometheus histograms instead of storing raw data points. Full breakdown in the carousel and video.

---

## Best Time to Post
Tuesday or Wednesday, 8:00–9:30 AM IST (commute/pre-work scroll for Indian tech audience)

## Engagement Hook
What's the worst "green dashboard, angry users" gap you've debugged — and what was actually hiding in your P99?
