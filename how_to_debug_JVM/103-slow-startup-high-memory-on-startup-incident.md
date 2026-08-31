# #103 — Slow Startup / High Memory on Startup

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Walk me through diagnosing: a Spring Boot app takes 45-60 seconds to start (should be 10-15s), memory jumps to 1.5GB immediately on startup, and the Kubernetes readiness probe keeps failing, causing a restart loop. How do you fix it?"

## 😊 Explain It Simply (for anyone)
Imagine opening a restaurant for the day by insisting every single ingredient, every appliance, and every staff member must be fully set up and tested *before* you unlock the front door — even the ones you might not need until dinner service. That's "eager initialization": Spring Boot, by default, tries to build every single component (a "bean" — a managed object the framework creates for you) the moment the app starts, whether or not it's needed right away. If you have hundreds of these components, or some of them need to talk to a slow database first, opening day takes forever, and Kubernetes — impatient customer that it is — keeps knocking, assuming you're never going to open, and restarts you before you're ready.

## 📊 Visualize It
```
Eager startup (slow):
[scan all classes]-->[create ALL beans]-->[connect DB]-->[ready] 45-60s
                                                            ^ readiness probe fails before this

Lazy startup (fast):
[scan all classes]-->[create only needed beans]-->[ready] 10-15s
                        (rest created on first use)
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- Spring Boot takes 45-60s to start (should be 10-15s)
- Memory jumps to 1.5GB immediately on startup
- Kubernetes readiness probe fails, pod restarts loop

**Diagnosis:**
```bash
# Enable startup timing
-Dspring.jmx.enabled=false  # disable unneeded JMX
--spring.main.lazy-initialization=true  # defer bean init

# Log class loading
-verbose:class 2>&1 | head -100   # show class loading storm

# Profile startup with JFR
-XX:StartFlightRecording=delay=5s,duration=60s,filename=/tmp/startup.jfr,settings=profile
```

**Common causes:**
1. Eager initialization of all beans (Spring loads everything at startup)
2. Slow database connectivity check (Flyway migration, HikariCP pool warmup)
3. Component scan of too many classes
4. JIT cold start (first requests slow before JIT kicks in)

**Fix:**
```java
// Lazy initialization — only create beans when first needed
@SpringBootApplication
public class App {
    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(App.class);
        app.setLazyInitialization(true);  // Java 2.2+
        app.run(args);
    }
}
```

```bash
# Class Data Sharing — reduces startup time 20-40%
java -Xshare:dump -XX:SharedArchiveFile=app-cds.jsa -cp app.jar
java -Xshare:on  -XX:SharedArchiveFile=app-cds.jsa -jar app.jar
```

## 🔑 Key Takeaway
Slow startup is usually eager bean creation or a slow DB warmup, not JVM overhead — profile with JFR or `-verbose:class` before assuming you need more resources.
