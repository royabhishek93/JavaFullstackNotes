# #54 — Classloader Leak on Redeployment

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** ⭐ Should-Know

## 🗣️ The Interview Question
"A Tomcat app leaks Metaspace on every hot redeploy. Why? How do you diagnose and fix?"

## 😊 Explain It Simply (for anyone)
Picture a school that gets a brand new set of textbooks (a "classloader" — the mechanism that loads your app's code into memory) every semester, and the old textbooks are supposed to be thrown out. But if even ONE teacher (some shared, long-lived system component) keeps an old textbook on their desk "just in case," the school can't fully discard that whole old set — the printer, publisher, and binding are all still considered "in use." Metaspace (the memory area where class definitions live) fills up bit by bit with every "hot redeploy" (replacing the running app with a new version without restarting the whole server), because the old version's classes never fully go away.

## 📊 Visualize It
```
 Redeploy #1: WebAppClassLoader_v1 (10 MB of class metadata)
 Redeploy #2: WebAppClassLoader_v2 (10 MB)  <- v1 should be freed, isn't!
 Redeploy #3: WebAppClassLoader_v3 (10 MB)  <- v1, v2 still held

              DriverManager (bootstrap classloader, lives forever)
                     |
                     +--> holds reference to JDBC Driver
                                 (loaded by WebAppClassLoader_v1)
                                 => v1 can NEVER be GC'd
```

## 🏭 The Real Production Answer (15-YOE Level)

The root cause is a classloader leak. When you redeploy a web app, Tomcat creates a new `WebAppClassLoader` for the new version and discards the old one. For the old classloader to be GC'd, nothing in the JVM's parent classloaders or static state can hold a reference to it or any class loaded by it.

Common culprits:

1. JDBC driver registration: `DriverManager` is in the bootstrap classloader. When your app loads a JDBC driver (e.g., MySQL's `com.mysql.jdbc.Driver`), `DriverManager` holds a reference to that driver instance, which is loaded by the app classloader. The app classloader can never be GC'd.

Fix:
```java
// In ServletContextListener.contextDestroyed:
@Override
public void contextDestroyed(ServletContextEvent sce) {
    Enumeration<Driver> drivers = DriverManager.getDrivers();
    while (drivers.hasMoreElements()) {
        Driver driver = drivers.nextElement();
        if (driver.getClass().getClassLoader() == getClass().getClassLoader()) {
            try { DriverManager.deregisterDriver(driver); }
            catch (SQLException e) { log.warn("Driver deregister failed", e); }
        }
    }
    // Also stop any background threads started by your app
}
```

2. Static references in library singletons (e.g., log4j MDC, EhCache) that hold references to web-app classes.

Diagnosis: take two heap dumps — one before redeploy, one after. In MAT, compare. If `WebAppClassLoader` instances keep accumulating, you have a classloader leak.

## 🔑 Key Takeaway
A classloader can only be garbage collected when NOTHING outside it — including bootstrap-level singletons like `DriverManager` — still points to any class it loaded.
