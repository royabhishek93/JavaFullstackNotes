# #97 — Metaspace OutOfMemoryError in Production

> **Category:** JVM Tuning Production Playbook | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"We're seeing java.lang.OutOfMemoryError: Metaspace in production on a service that dynamically processes Groovy scripts. How do you approach this?"

## 😊 Explain It Simply (for anyone)
Imagine a library (Metaspace) that stores the "blueprint" for every type of form you might ever need to fill out (class metadata). Normally you print a blueprint once and reuse it forever. But if every single customer request causes the printer to generate a brand-new blueprint from scratch — even if it's an identical form to one printed five minutes ago — the library shelves fill up infinitely because old blueprints are never thrown away as long as *anyone* might still reference them. This is exactly what happens when code is compiled dynamically (like Groovy scripts) without caching: every evaluation creates new classes, and the library (Metaspace) has no ceiling by default, so it eventually overflows the building.

## 📊 Visualize It
```
Metaspace (grows unbounded by default)
┌─────────────────────────────────────┐
│ Class A (script v1) ████            │
│ Class A (script v1, RE-loaded) ████ │ ← should've reused!
│ Class A (script v1, RE-loaded) ████ │ ← should've reused!
│ Class A (script v1, RE-loaded) ████ │ ← never freed (ClassLoader alive)
│ ...forever growing...                │
└─────────────────────────────────────┘
        → OutOfMemoryError: Metaspace
```

## 🏭 The Real Production Answer (15-YOE Level)
> "Metaspace OOM from dynamic class loading is a classic problem. Unlike heap, Metaspace stores class
> metadata, and crucially, classes are not GCed unless their ClassLoader is GCed.
>
> The pattern: each Groovy script compilation creates new classes. If you're creating a new
> GroovyShell or GroovyClassLoader per request without caching, each script evaluation loads new
> classes that are never unloaded.
>
> Diagnosis:
>   jcmd <pid> VM.native_memory summary
>   # Look at: Class space and Metaspace lines
>   # Growing Metaspace with growing class count = ClassLoader leak
>
>   jcmd <pid> VM.classloaders
>   # Shows ClassLoader hierarchy and class counts
>
> Fix path:
>
> 1. Cache compiled scripts — use a WeakHashMap<String, Script> or Caffeine cache
>    keyed by script content hash. Same script = same compiled class = no new ClassLoader.
>
> 2. One shared GroovyShell with script caching
>    GroovyShell is thread-safe for eval if scripts are compiled once
>
> 3. Set a Metaspace limit so OOM happens with a heap dump instead of JVM crash:
>    -XX:MaxMetaspaceSize=512m
>    -XX:+HeapDumpOnOutOfMemoryError
>
> 4. For severe leak, periodic reload of the entire application (circuit breaker for bad scripts)
>
> At 15 years experience: I've seen this exact pattern with Drools rule engines, Velocity templates
> with dynamic compilation, and JOOQ code gen running in-process. The fix is always the same:
> cache the compiled artifact, not just the source."

## 🔑 Key Takeaway
Metaspace OOM from dynamic scripting is almost always a missing cache — cache the compiled class, not just the source text, and every scripting-engine leak disappears.
