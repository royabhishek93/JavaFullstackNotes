# #92 — "Closing in Finally Block Means No Leak"

> **Category:** Memory Leaks End-to-End | **Type:** Senior Trap Question | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"The team points to their `finally { conn.close(); }` pattern and says there can be no connection leak. Critique this."

## 😊 Explain It Simply (for anyone)
A `finally` block (code guaranteed to run no matter what happens in the "try" section) sounds bulletproof, but it has hidden holes: what if the thing you're trying to close was never successfully created in the first place (like trying to lock a door that was never actually installed)? Or what if the "closing" action ITSELF fails and throws its own error, which then completely erases the memory of the original problem that happened first? Or, with MULTIPLE things to close, what if closing the FIRST one fails — does that stop the SECOND one from ever being closed at all? These are all real traps that a naive `finally` doesn't handle, which is exactly why Java added "try-with-resources" as the safer, modern replacement.

## 📊 Visualize It
```
 Case 1: conn = null (creation threw) -> finally { conn.close() } -> NPE!
 Case 2: conn.close() itself throws -> original exception LOST
 Case 3: stmt.close() throws -> conn.close() on next line NEVER RUNS
                                 -> connection actually leaks!

 try-with-resources handles ALL three correctly:
   - closes in reverse order
   - suppresses (not discards) secondary exceptions
```

## 🏭 The Real Production Answer (15-YOE Level)

**Trap answer to reject:** "Yes, finally always runs, so the connection is always closed."

**Expert answer:**

The `finally` pattern has several ways to still leak:

Case 1 — object creation throws:
```java
Connection conn = null;
try {
    conn = dataSource.getConnection(); // throws SQLEx → conn is null
    // ...
} finally {
    conn.close(); // NullPointerException — exception suppressed, original exception lost
}
```

Case 2 — close() throws, masking original exception:
```java
} finally {
    conn.close(); // throws RuntimeException
    // Original exception from try block is LOST
}
```

Case 3 — multiple resources, first close throws:
```java
} finally {
    stmt.close(); // throws → next line never runs
    conn.close(); // NEVER CALLED — connection leaks
}
```

The only safe pattern is `try-with-resources`, which handles all of these correctly by calling close in reverse order and using exception suppression:
```java
try (Connection conn = dataSource.getConnection();
     PreparedStatement stmt = conn.prepareStatement(SQL)) {
    // ...
} // Both closed correctly, exceptions suppressed not lost
```

For Java <7 codebases, the correct pattern requires nested try/finally blocks, one per resource — which is exactly why try-with-resources was introduced.

## 🔑 Key Takeaway
A naive `finally { close(); }` can NPE, mask exceptions, or skip closing subsequent resources — try-with-resources is the only pattern that handles all these cases safely.
