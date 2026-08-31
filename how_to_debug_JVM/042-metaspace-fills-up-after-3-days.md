# #42 — After our microservice runs for 3 days, Metaspace fills up and causes Full GC

> **Category:** GC Tuning & Debugging | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"After our microservice runs for 3 days, Metaspace fills up and causes Full GC. What's happening and how do you diagnose a Metaspace leak?"

## 😊 Explain It Simply (for anyone)
Think of a library that stores not books, but the *blueprints* for how to build every kind of book — the templates, the printing instructions, the binding rules. This blueprint room is called "Metaspace" in Java-land, and it holds the definitions of every class (a "class" is like a cookie-cutter template your program uses to stamp out objects). Normally, when a whole "publishing house" (a component called a ClassLoader) shuts down, all its blueprints get thrown away too. But if something keeps creating brand-new publishing houses without ever retiring the old ones, the blueprint room keeps filling up — day after day — until there's no room left. A slow, multi-day buildup like this is a classic sign that some part of your app keeps generating new "publishing houses" (ClassLoaders) instead of reusing existing ones, often from things like dynamic code generation or repeatedly reloading web pages.

## 📊 Visualize It
```
Day 1:  Metaspace [███-------] 30%
Day 2:  Metaspace [██████----] 60%
Day 3:  Metaspace [██████████] 100% → Full GC triggered, still stuck

Cause: ClassLoader A ──creates──> new classes (never GC'd)
       ClassLoader B ──creates──> new classes (never GC'd)
       ClassLoader C ──creates──> new classes (never GC'd)  ← leak pattern
```

## 🏭 The Real Production Answer (15-YOE Level)
> Metaspace stores class metadata — the class definitions, method bytecode, constant pools. It grows when new classes are loaded and shrinks only when a ClassLoader is GC'd along with all its loaded classes.
>
> A 3-day growth pattern strongly suggests a ClassLoader leak: something is creating new ClassLoaders but never releasing them. Common culprits: dynamic code generation (Groovy, cglib, Javassist), OSGi bundles, JSP recompilation, or misbehaving reflection caches.

**Flags to configure:**

```bash
# Always cap Metaspace in production containers:
-XX:MetaspaceSize=256m       # Initial commit size (not a hard limit)
-XX:MaxMetaspaceSize=512m    # Hard cap — prevents unbounded native memory growth
# Without MaxMetaspaceSize, Metaspace can grow until native OOM kills the process

# Monitoring:
jstat -gcmetacapacity <pid> 5000
# Or from GC log: look for "Metaspace" lines in Full GC output
```

**Diagnosing the leak:**

```java
// Quick check: count ClassLoaders
import java.lang.management.*;
// In a VisualVM / Mission Control session, look at:
// Memory → MetaspaceUsage (should plateau, not grow linearly)

// From GC log — Metaspace in Full GC output:
// [gc,metaspace] GC(201) Metaspace: 480M(512M)->480M(512M) ← not freed = leak
```

**Fix:** Use a heap profiler (JFR, async-profiler) to find which ClassLoader is accumulating. Look for `sun.reflect.GeneratedMethodAccessor*` classes (reflection inflation), `$$EnhancerByCGLIB$$` (cglib proxies not getting released), or `groovy.lang.GroovyClassLoader` instances.

## 🔑 Key Takeaway
A multi-day Metaspace growth pattern points to a ClassLoader leak, not a Metaspace sizing problem — always cap it with `MaxMetaspaceSize` regardless.
