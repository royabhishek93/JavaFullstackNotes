# 🎯 Q61: Distributed Tracing (Jaeger, Zipkin, Spring Cloud Sleuth)?

> **Interview Frequency:** 38% | **Difficulty:** ⭐⭐⭐⭐ | **Study Time:** 4 minutes

---

## 🤔 Problem

User request goes: API → Service A → Service B → Database. Where does it slow down?

---

## 📌 Spring Cloud Sleuth

Automatically adds trace ID and span ID to logs:

```
2026-02-22 10:30:00 [api,a1b2c3d4,e5f6g7h8] INFO  Request started
2026-02-22 10:30:01 [api,a1b2c3d4,f9i0j1k2] INFO  Service A called
2026-02-22 10:30:02 [api,a1b2c3d4,l3m4n5o6] INFO  Service B called
2026-02-22 10:30:05 [api,a1b2c3d4,p7q8r9s0] INFO  Response sent (5 seconds total)
```

---

## 📌 Zipkin/Jaeger

Visualize traces:
- Each service segment shows duration
- Identify bottleneck (Service B took 3s)
- See parallel vs sequential calls

---

## ✅ Setup

```yaml
spring:
  sleuth:
    sampler:
      probability: 0.1  # Sample 10% of requests
  zipkin:
    baseUrl: http://zipkin:9411
```

---

## 💬 Interview Tip (Say This Exactly)

"Spring Cloud Sleuth adds trace IDs automatically. View traces in Zipkin/Jaeger to find bottlenecks across microservices. Essential for debugging distributed systems."

---

**Last Updated:** February 22, 2026  
**Next: [Q62_health_checks.md](Q62_health_checks.md)**
