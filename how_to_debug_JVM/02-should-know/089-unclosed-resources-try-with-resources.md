# #89 — Unclosed Resources (try-with-resources)

> **Category:** Memory Leaks End-to-End | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Show a subtle resource leak that `finally` does not fully prevent."

## 😊 Explain It Simply (for anyone)
Imagine you tell yourself "no matter what happens, I will turn off the stove before leaving the kitchen" (a `finally` block — code that's supposed to always run, even if something goes wrong). But what if you never actually turned the stove ON because you tripped and fell before reaching it? Now your "always turn it off" instruction tries to touch a stove that was never lit, and you might slip again trying to reach for something that doesn't exist. This is what happens when a resource (a file, a network connection) fails to open — the "clean up" code assumes it exists and crashes trying to close something that was never created. Java's modern "try-with-resources" (a special syntax that automatically and safely closes things for you, in the right order, even during errors) exists specifically to avoid this trap.

## 📊 Visualize It
```
 try {
    fis = new FileInputStream(path);  <-- throws before assignment
 } finally {
    fis.close();  <-- fis is still null -> NullPointerException!
                      original exception is now HIDDEN
 }

 try-with-resources instead:
 try (FileInputStream fis = new FileInputStream(path)) {
    ...
 }  // close() guaranteed, exceptions properly suppressed, not lost
```

## 🏭 The Real Production Answer (15-YOE Level)

Buggy code (pre try-with-resources):
```java
// LEAK: if new FileInputStream throws, fis is null and finally NPEs
public void process(String path) throws IOException {
    FileInputStream fis = null;
    try {
        fis = new FileInputStream(path); // might throw
        // ... process ...
    } finally {
        fis.close(); // NullPointerException if constructor threw!
    }
}
```

Slightly better but still subtle:
```java
finally {
    if (fis != null) fis.close(); // NPE avoided, but close() can throw
    // If close() throws, that exception masks the original exception
}
```

Fix — Java 7+ try-with-resources:
```java
public void process(String path) throws IOException {
    try (FileInputStream fis = new FileInputStream(path)) {
        // ... process — fis.close() always called, exception properly suppressed
    }
}
```

For JDBC specifically:
```java
// LEAK: statement and connection not closed on exception paths
try (Connection conn = dataSource.getConnection();
     PreparedStatement ps = conn.prepareStatement(SQL);
     ResultSet rs = ps.executeQuery()) {
    while (rs.next()) { /* ... */ }
} // ALL three closed in reverse order automatically
```

## 🔑 Key Takeaway
A naive `finally { resource.close(); }` can NPE or swallow exceptions — always prefer try-with-resources, which closes safely and preserves the original exception via suppression.
