# #104 — "StackOverflow Always Means Infinite Recursion"

> **Category:** Common Production Incidents | **Type:** Senior Trap Question | **Priority:** 👍 Good-to-Know

## 🗣️ The Interview Question
"StackOverflowError always means there's an infinite recursion bug in the code, right?"

## 😊 Explain It Simply (for anyone)
A `StackOverflowError` just means the tower of "who called whom" (the call stack) got too tall and toppled over — it doesn't automatically mean the tower was built by a broken, endlessly-repeating pattern. Sometimes the tower really is legitimately tall because of many different, unique layers stacked on top of each other (deep, but finite, chains through several frameworks, or genuinely deep nested data like XML/JSON). Other times, a single method is just holding a giant object (like a big local array) that eats up a lot of "tower height" per layer, so the tower runs out of room faster than expected even without deep recursion. You have to actually look at the tower's contents before deciding it's an infinite loop.

## 📊 Visualize It
```
Case A (infinite recursion):        Case B (legit deep, finite):
  isOdd()                             SpringAOP -> JPA -> Hibernate
  isEven()                            -> Interceptor1 -> Interceptor2
  isOdd()      <- same 2 methods      -> ... -> JDBC   <- 500+ DIFFERENT
  isEven()        repeating forever      methods, no repeats, just deep
  isOdd()
```

## 🏭 The Real Production Answer (15-YOE Level)
**WRONG.** StackOverflow can also happen with:
- Very deep (but finite) recursion through framework layers (Spring AOP wrapping → JPA → Hibernate → JDBC → multiple interceptors → deep enough)
- Local variables that are large arrays: `byte[] buf = new byte[512*1024]` inside a method consumes 512KB of stack frame immediately
- Deeply nested XML/JSON deserialization with legitimate depth

**Correct answer:** Check the stack trace. If the same method repeats → infinite recursion. If it's a unique chain of 500+ different methods → the call stack is legitimately deep. Fix: `-Xss2m` to increase stack size, or refactor deep call chains.

## 🔑 Key Takeaway
Look for repetition, not just depth — a repeating method name means a missing base case, a unique long chain means it's a legitimately deep call stack.
