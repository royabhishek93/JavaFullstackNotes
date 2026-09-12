# #2 — Metaspace OOM from a Classloader Leak

> **Category:** Heap Dump Analysis | **Type:** Scenario Q&A | **Priority:** 🔥 Must-Know

## 🗣️ The Interview Question
"'java.lang.OutOfMemoryError: Metaspace' in a long-running Spring Boot app after multiple hot reloads (dev environment) and also happening in production after several days. What's happening?"

## 😊 Explain It Simply (for anyone)
Every class (the "blueprint" for creating objects) your program uses gets loaded into a special storage area called "Metaspace" by something called a "classloader" — think of the classloader as a librarian who brings in new blueprint books. Normally, when nobody needs a set of blueprints anymore, the whole librarian (and every book they brought in) can be thrown out together and the shelf space is reclaimed.

But if someone keeps a single sticky note referencing one of those books (a "strong reference"), the librarian can NEVER be thrown out — meaning ALL the books they ever brought in stay on the shelf forever. If your code keeps creating brand new librarians for the same job (e.g., every time you run a small on-the-fly script) instead of reusing one, you get more and more librarians who can never leave, and the blueprint shelf (Metaspace) eventually overflows.

## 📊 Visualize It
```
 Request 1 → new ClassLoader#1 → loads Class A
 Request 2 → new ClassLoader#2 → loads Class A (again!)
 Request 3 → new ClassLoader#3 → loads Class A (again!)
       ...
 Request N → new ClassLoader#N → loads Class A (again!)

  Metaspace: [CL#1][CL#2][CL#3]...[CL#N]  ← never unloaded
             (something still references CL#1..N, so GC can't collect them)

  Fix: reuse ONE classloader / cache compiled classes
  Metaspace: [CL#shared: Class A]   ← stable, no growth
```

## 🏭 The Real Production Answer (15-YOE Level)

This is a classloader leak. Every time a new classloader loads classes into Metaspace, the metadata is retained until that classloader itself becomes unreachable and gets GC'd. If something strong-references the classloader (or any class it loaded), Metaspace grows forever.

Production patterns:
- **Dynamic class generation**: CGLIB proxies, Spring AOP, Hibernate bytecode enhancement. Each redeploy in an OSGi container or app server creates new classloaders.
- **JDBC driver registration**: `DriverManager` holds static references to `Driver` objects loaded by webapp classloaders — classic Tomcat leak.
- **Groovy/Script engines**: Each `GroovyClassLoader.parseClass()` in a loop generates a new class.
- **Reflections library**: Scanning classpath at runtime can generate and retain synthetic classes.

Diagnosis:
```bash
# Watch Metaspace live
jstat -gcmetacapacity <pid> 2000 30
# MCMN(min) MCMX(max) MC(current committed) CCSMN CCSMX CCSC — watch MC climbing

# Count class count
jcmd <pid> VM.class_histogram | head -50

# Enable classloader leak diagnostic
# JVM flag: -XX:+TraceClassLoading -XX:+TraceClassUnloading (verbose, dev only)
```

MAT analysis for Metaspace leak:
- Open dump → Window → Heap Dump Details → Class Loaders
- Look for hundreds/thousands of classloader instances of the same type

Fix:
```java
// Wrong — leaks Groovy classes in Metaspace
GroovyShell shell = new GroovyShell();
Script script = shell.parse(scriptSource); // New class per parse call in loop

// Correct — cache compiled scripts, reuse classloader
// Use GroovyScriptEngine or cache Script objects keyed by hash of source
```

## 🔑 Key Takeaway
Metaspace OOM is almost always a classloader that can't be unloaded — find who holds a strong reference to it, don't just raise the size limit.
