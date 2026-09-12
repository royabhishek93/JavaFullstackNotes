# #101 — StackOverflowError

> **Category:** Common Production Incidents | **Type:** Scenario Q&A | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"Walk me through diagnosing: `java.lang.StackOverflowError` shows up in logs, often somewhere in recursive code paths (XML parsing, tree traversal, JSON deserialization), and the stack trace looks truncated. How do you find the root cause?"

## 😊 Explain It Simply (for anyone)
Think of a stack of trays in a cafeteria (the "call stack" — where the program keeps track of which function called which). Every time a method calls another method, a new tray goes on top. If a method keeps calling itself (or calls another method that calls it back) without ever stopping, trays keep piling up until the stack literally can't hold any more and topples over — that's a `StackOverflowError`. The stack trace looks "truncated" because there are thousands of nearly-identical trays, and the log only shows you the top and bottom of that towering pile.

## 📊 Visualize It
```
Call stack (grows upward, limited height):
  [isOdd(1)]
  [isEven(2)]
  [isOdd(3)]
  [isEven(4)]
    ...
  [isOdd(99999)]   <- stack limit hit here
  [main]
       ^-- same method repeating = infinite recursion, no base case
```

## 🏭 The Real Production Answer (15-YOE Level)

**Symptoms:**
- `java.lang.StackOverflowError` in logs
- Often in recursive code paths (XML parsing, tree traversal, JSON deserialization)
- Stack trace is truncated (only shows top/bottom of deep recursion)

**Diagnosis:**
```bash
# Look at the stack trace — is the same method repeating?
grep "at com.myapp" logs/app.log | uniq -c | sort -rn | head -10
# If one method appears 1000+ times → infinite recursion
```

**Root causes:**
1. Recursive method missing base case
2. Mutual recursion: A calls B calls A
3. Deserialization of circular object graph (Jackson/Gson)
4. Very deep call stack with large local arrays (deep framework wrapping)

**Fix for recursion:**
```java
// Broken: infinite mutual recursion
boolean isEven(int n) { return n == 0 ? true : isOdd(n - 1); }
boolean isOdd(int n)  { return n == 0 ? false : isEven(n - 1); }
// For n=100000 → StackOverflow

// Fixed: convert to iteration or use tail recursion manually
boolean isEven(int n) {
    while (n > 0) n -= 2;
    return n == 0;
}
```

**Stack size tuning (rarely the right fix):**
```bash
-Xss1m   # default 512k-1m; increase only if deep legitimate recursion
# Better fix: convert recursion to iteration with explicit stack
```

## 🔑 Key Takeaway
Count how many times the same method repeats in the stack trace — if it's in the thousands, fix the missing base case, don't just bump `-Xss`.
