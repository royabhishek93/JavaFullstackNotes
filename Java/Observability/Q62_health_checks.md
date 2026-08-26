# 🎯 Q62: Health Checks and Readiness Probes?

> **Interview Frequency:** 40% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Kubernetes needs to know: Is app ready? Is app healthy? Restart if dead.

---

## 📌 Spring Boot Actuator

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health
  endpoint:
    health:
      show-details: always
```

---

## 📌 Endpoints

- **`/actuator/health`** → Overall health (UP/DOWN)
- **`/actuator/health/readiness`** → Ready to serve traffic?
- **`/actuator/health/liveness`** → Is app alive?

---

## ✅ Custom Health Check

```java
@Component
class DatabaseHealthCheck extends AbstractHealthIndicator {
    @Override
    protected void doHealthCheck(Health.Builder builder) {
        try {
            database.ping();
            builder.up();
        } catch (Exception e) {
            builder.down().withException(e);
        }
    }
}
```

---

## 📌 Kubernetes (K8s)

```yaml
livenessProbe:
  httpGet:
    path: /actuator/health/liveness
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /actuator/health/readiness
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

## 💬 Interview Tip (Say This Exactly)

"Liveness probe: is app alive (restart if down). Readiness probe: can app take traffic (remove from LB if not ready). Custom health checks for DB, cache, external APIs."

---

**Last Updated:** February 22, 2026  
**Next: [Q63_structured_logging.md](Q63_structured_logging.md)**
