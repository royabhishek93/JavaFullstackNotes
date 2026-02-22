# 🎯 Q60: Metrics Collection (Micrometer, Prometheus)?

> **Interview Frequency:** 40% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

Need to monitor: request latency, error rate, cache hits. How?

---

## 📌 Micrometer (Spring Standard)

```java
MeterRegistry meterRegistry;

// Counter: increment on events
meterRegistry.counter("orders.placed", "status", "success").increment();

// Timer: measure duration
Timer.Sample sample = Timer.start(meterRegistry);
// ... do work ...
sample.stop(Timer.builder("api.response.time").register(meterRegistry));

// Gauge: current value
meterRegistry.gauge("cache.size", () -> cache.size());

// Distribution: histogram
meterRegistry.timer("database.query").record(() -> query());
```

---

## 📌 Export to Prometheus

```yaml
management:
  endpoints:
    web:
      exposure:
        include: prometheus
  metrics:
    export:
      prometheus:
        enabled: true
```

Then: `GET http://localhost:8080/actuator/prometheus`

---

## ✅ Key Metrics

- **Latency:** p50, p95, p99 response times
- **Throughput:** Requests per second
- **Error rate:** % failed requests
- **Resource:** CPU, memory, connections
- **Business:** Orders placed, revenue, users

---

## 💬 Interview Tip (Say This Exactly)

"Micrometer provides metrics API. Prometheus scrapes /actuator/prometheus endpoint. Alert on key metrics: latency p95, error rate >1%, CPU >80%. Dashboard in Grafana for visualization."

---

**Last Updated:** February 22, 2026  
**Next: [Q61_distributed_tracing.md](Q61_distributed_tracing.md)**
