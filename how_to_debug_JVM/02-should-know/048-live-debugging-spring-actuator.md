# #48 — Live Debugging with Spring Boot Actuator

> **Category:** Production Debugging Tools | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"How do you use Spring Boot Actuator for production debugging?"

## 😊 Explain It Simply (for anyone)
Think of your car's dashboard again: there's a set of gauges you're meant to check while driving (speed, fuel, engine temperature) and there's a locked panel under the hood that only a mechanic should open, and never while the car is moving on the highway.

Spring Boot Actuator is that dashboard for a running web application. It exposes a set of web addresses (endpoints) you can visit to check health, live metrics, and even see what all the threads are doing right now — all safe to check while the app keeps serving real users. It even has a "gauge" you can adjust live: you can turn up the detail level of logging for just one troublesome part of the code, watch the extra detail stream in, and then turn it back down — all without restarting the car (application). But one panel — the full memory dump — is like popping the hood and doing major surgery while still driving on the highway: it can stall the "car" for many seconds, so you only do it after pulling over (removing that instance from the load balancer) first.

## 📊 Visualize It
```
 Actuator Dashboard (safe while driving)
 ┌───────────────────────────────┐
 │ /health         ✅            │
 │ /metrics        ✅            │
 │ /threaddump     ✅            │
 │ /loggers (POST) ✅ live tweak │
 ├───────────────────────────────┤
 │ /heapdump       🔴 pull over  │
 │                    first!     │
 └───────────────────────────────┘
```

## 🏭 The Real Production Answer (15-YOE Level)
```yaml
# application.yml — expose carefully
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,threaddump,loggers
        # DO NOT expose heapdump in load-balanced prod
  endpoint:
    health:
      show-details: when_authorized
```

```bash
# Thread dump (safe)
curl -s http://localhost:8080/actuator/threaddump | jq '.threads[] | select(.threadState == "BLOCKED")'

# Live metrics — JVM memory
curl -s http://localhost:8080/actuator/metrics/jvm.memory.used | jq '.measurements[0].value'

# Change log level at runtime (no restart!)
curl -X POST http://localhost:8080/actuator/loggers/com.myapp.OrderService \
  -H 'Content-Type: application/json' \
  -d '{"configuredLevel": "DEBUG"}'
# After debugging, set back to INFO

# Heap dump (HIGH RISK — full GC + write pause)
# curl http://localhost:8080/actuator/heapdump > /tmp/heap.hprof
# Only use on instance already taken out of load balancer
```

## 🔑 Key Takeaway
Actuator's health/metrics/threaddump/loggers endpoints are safe to use live; `/heapdump` is high-risk and should only run after draining traffic from that instance.
