# #95 — New Deployment is Slow for First 5 Minutes

> **Category:** JVM Tuning Production Playbook | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"After each deployment, users complain about slow responses for the first 3-5 minutes. After that the service is fast. How do you fix this?"

## 😊 Explain It Simply (for anyone)
Think of a car engine on a cold winter morning (a freshly started JVM) — it runs, but sluggishly, until it warms up, at which point it hits peak performance. The JVM does the same thing: at first it runs your code the "slow but simple" way (interpreting instructions one at a time), and only after watching a method run many times does it invest in building a highly optimized version of that code (like a mechanic tuning the engine once they know exactly how you drive). The fix options are basically: warm the car up in the garage before driving it (traffic warming), pre-build parts of the "engine" ahead of time (Class Data Sharing), or buy a car that's fast from the very first second by design (native compilation), each with its own cost trade-off.

## 📊 Visualize It
```
Compilation Tiers over time:
 Level 0 Interpreted  ──► instant start, slow execution
 Level 1-3 C1 compiled ──► seconds in, moderate speed
 Level 4 C2 compiled   ──► minutes in, PEAK speed
                              ▲
                   users hit slowness HERE (first 3-5 min)
```

## 🏭 The Real Production Answer (15-YOE Level)
> "JVM warm-up. This is tiered compilation doing its job but doing it too slowly for your SLO.
>
> What's happening:
>   Level 0: Interpreted (slow, instant start)
>   Level 1-3: C1 compiled (fast compilation, moderate performance, kicks in seconds)
>   Level 4: C2 compiled (slow compilation, peak performance, minutes)
>
> The first N invocations of each method are interpreted. Hot methods get profiled, then C1-compiled,
> then if hot enough C2-compiled. During that ramp, you're running interpreted or lightly optimized code.
>
> Solutions in order of complexity:
>
> Option 1: Traffic warming in the load balancer
>   Use a readiness probe that does internal warm-up calls before the pod enters rotation.
>   Spring Boot Actuator /actuator/health for basic readiness.
>   Better: a custom /actuator/warmup endpoint that exercises hot code paths.
>
> Option 2: Class Data Sharing (CDS) — reduces startup time
>   Step 1: Generate archive on build:
>     java -Xshare:dump -XX:SharedArchiveFile=app.jsa -cp app.jar
>   Step 2: Run with archive:
>     java -Xshare:on -XX:SharedArchiveFile=app.jsa -jar app.jar
>   Savings: 20-40% startup time, lower memory when multiple JVMs share the archive
>
> Option 3: Spring AOT + GraalVM Native
>   If startup < 100ms is required, compile to native image.
>   Trade-off: no JIT means peak throughput is 20-40% lower than JVM.
>   Reflection, dynamic proxies, CGLIB need explicit registration.
>   Not suitable for all Spring applications without significant configuration.
>
> Option 4: AppCDS with dynamic archive (Java 13+)
>   java -XX:ArchiveClassesAtExit=app-dynamic.jsa -jar app.jar
>   Captures classes loaded during an actual run, better than static dump."

## 🔑 Key Takeaway
Slow first minutes after deploy is JIT warm-up, not a bug — fix it with traffic warming and CDS before reaching for the nuclear option of native image.
