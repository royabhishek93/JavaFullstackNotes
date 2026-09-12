# #133 — Metaspace Growing From Dynamic Proxy / Reflection Explosion

> **Category:** Heap Dump Analysis | **Type:** Advanced Scenario Q&A | **Priority:** ⚙️ Expert/Niche

## 🗣️ The Interview Question
"Metaspace steadily grows over weeks in a production Spring Boot app. No hot deploys. No OSGi. Why?"

## 😊 Explain It Simply (for anyone)
Even if nobody is manually swapping out the blueprint books (no hot redeploys), your program can still secretly print BRAND NEW custom blueprint books on its own at runtime — for example, some frameworks (like Spring's CGLIB, JSON libraries, or scripting engines) automatically generate a fresh, one-off blueprint every single time they do a certain operation, instead of reusing the same blueprint.

If that "print a new one every time" behavior happens inside a loop that runs constantly (evaluating a business rule, serializing objects, creating beans), you slowly accumulate thousands of subtly different blueprint books that pile up on the shelf (Metaspace) week after week, even though no one intentionally reloaded anything.

## 📊 Visualize It
```
Week 1:  Metaspace [■□□□□□□□]  20%
Week 2:  Metaspace [■■■□□□□□]  35%
Week 3:  Metaspace [■■■■■□□□]  55%
Week 4:  Metaspace [■■■■■■■□]  80%  → OOM: Metaspace

Root cause loop:
  evaluateRule(script) {
    new GroovyClassLoader()      ← new "librarian" every call!
      .parseClass(script)        ← new class every call!
  }                               // never cached, never unloaded

Fix:
  ruleCache.computeIfAbsent(hash(script), sharedLoader::parseClass)
  → one classloader, one class per unique script → Metaspace flat
```

## 🏭 The Real Production Answer (15-YOE Level)

Even without hot deploys, Metaspace can leak via:

1. **CGLIB proxy per-invocation**: If Spring beans are being created (not reusing singletons) and each creation generates a CGLIB subclass
2. **Groovy DSL evaluation**: Scripts compiled at runtime without caching
3. **Reflection-based serialization frameworks**: Jackson or Kryo generating accessor classes per type
4. **Programmatic `ClassLoader` usage**: Library code that creates a new classloader per operation

Diagnosis:
```bash
# Track class count over time
jcmd <pid> VM.classloaders
# Shows classloader hierarchy and class counts per loader

# Monitor via JMX
# java.lang:type=ClassLoading → LoadedClassCount (should be stable)
# java.lang:type=ClassLoading → TotalLoadedClassCount (ever-increasing is expected, but slope matters)

# Heap dump → MAT → Window → Heap Dump Details → Class Loaders tab
# Look for many instances of the same classloader type

# Find retained heap per classloader
# MAT OQL: SELECT * FROM java.lang.ClassLoader WHERE this.@retainedHeapSize > 1000000
```

Pattern catch:
```java
// Bug: new GroovyClassLoader per rule evaluation
public Object evaluateRule(String ruleScript, Map<String, Object> context) {
    GroovyClassLoader loader = new GroovyClassLoader(); // New classloader each time!
    Class<?> ruleClass = loader.parseClass(ruleScript); // New class in Metaspace!
    // loader never closed, class never unloaded
    return ruleClass.newInstance();
}

// Fix: cache compiled classes
private final Map<String, Class<?>> ruleCache = new ConcurrentHashMap<>();
private final GroovyClassLoader sharedLoader = new GroovyClassLoader();

public Object evaluateRule(String ruleScript, Map<String, Object> context) {
    Class<?> ruleClass = ruleCache.computeIfAbsent(
        DigestUtils.sha256Hex(ruleScript),
        key -> sharedLoader.parseClass(ruleScript)
    );
    return ruleClass.newInstance();
}
```

## 🔑 Key Takeaway
No hot-deploys doesn't mean no classloader leak — check for per-call dynamic proxy/script/reflection class generation that never gets cached.
