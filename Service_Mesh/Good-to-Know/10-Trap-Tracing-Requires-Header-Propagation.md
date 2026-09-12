# Trap 7: "The Mesh Gives Me Full Distributed Tracing Automatically, No App Code Changes Needed, Right?"

**Interviewer:** "Since Consul/Istio does distributed tracing for me automatically, I don't need to change any application code for tracing, right?"

**Correct Answer: No — nuanced.**

```
  What the mesh gives you FOR FREE (zero app changes):
  ------------------------------------------------------
  Envoy(hop 1) generates a SPAN  --\
  Envoy(hop 2) generates a SPAN  ---> all sent to Jaeger/Zipkin
  Envoy(hop 3) generates a SPAN  --/     but DISCONNECTED,
                                          not yet one coherent trace

  What REQUIRES an app code change:
  ------------------------------------------------------
  App must forward trace headers (x-request-id, x-b3-traceid,
  traceparent, etc.) from the INCOMING request onto any
  OUTGOING call it makes as a result of it.

  Only then do the spans get STITCHED into ONE end-to-end trace.
```

The mesh auto-generates spans for each hop and can gather timing/error data with zero app changes. But **end-to-end trace correlation** (stitching hop 1 → hop 2 → hop 3 into ONE trace) requires the application to propagate a small set of tracing headers on any outbound call it makes as a result of an inbound request. If the app doesn't propagate those headers, you get disconnected, orphaned spans instead of one coherent trace.

## Why This Trap Exists

"The mesh handles observability for me" is a half-truth that sounds complete. This trap tests whether you know the **precise boundary** of what's automatic (per-hop metrics/spans) versus what still requires minimal, deliberate app cooperation (header propagation for trace correlation).

---
See also: [01-Concepts-Reference.md — Part 5: Observability](../Must-Know/01-Concepts-Reference.md#5-observability-metrics-tracing-kialigrafana)
