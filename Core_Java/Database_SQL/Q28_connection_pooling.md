# 🎯 Q28: Connection Pooling Tuning (HikariCP)

> **Interview Frequency:** 48% | **Difficulty:** ⭐⭐⭐ | **Study Time:** 3 minutes

---

## 🤔 Problem

Too many connections = memory waste. Too few = request queuing. What's optimal?

---

## 📌 HikariCP Configuration

```properties
spring.datasource.hikari.maximum-pool-size=20  # Max connections
spring.datasource.hikari.minimum-idle=5        # Min idle kept
spring.datasource.hikari.connection-timeout=30000  # 30 sec wait
spring.datasource.hikari.idle-timeout=600000   # Close after 10 min idle
spring.datasource.hikari.max-lifetime=1800000  # Recycle every 30 min
```

---

## 📌 Formula

**Max Pool Size** = (CPU_CORES × 2) + 5
- 4-core server: 13 connections
- 8-core server: 21 connections

---

## 💬 Interview Tip (Say This Exactly)

"Pool size = cores*2 + 5. Too many = memory + context switch. Too few = queuing. Adjust based on workload. Monitor: active connections, wait time, idle count."

---

**Last Updated:** February 22, 2026  
**Previous: [Q27_optimistic_locking.md](Q27_optimistic_locking.md) | Next: [../Design_Patterns/Q29_singleton_patterns.md](../Design_Patterns/Q29_singleton_patterns.md)**
