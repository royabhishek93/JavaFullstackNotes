# #125 — "The Leak Is in the Library, Not My Code"

> **Category:** Memory Leaks End-to-End | **Type:** Senior Trap Question | **Priority:** 📘 Advanced

## 🗣️ The Interview Question
"MAT shows a Hibernate internal map consuming 600MB. The team says 'it's a Hibernate bug.' How do you respond?"

## 😊 Explain It Simply (for anyone)
Blaming the library is like blaming your kitchen pantry for being over-stuffed with groceries — the pantry didn't buy the groceries, YOU did, one shopping trip at a time. A library (someone else's pre-built code, like Hibernate) is just a container that holds whatever YOUR code tells it to hold. If a Hibernate internal structure is huge, it's almost always because your code configured it with no limits, or forgot to "check out" (close) sessions properly. Upgrading the library version without fixing your usage is like buying a bigger pantry — you'll fill that one up too.

## 📊 Visualize It
```
 "Blame the library" (WRONG):
   Hibernate SessionFactory -> "must be a Hibernate bug" -> upgrade version -> still leaks

 "Investigate usage" (RIGHT):
   Hibernate SessionFactory
       |
       +-- L2 cache: no TTL/max-size configured?  <- YOUR config
       +-- Open EntityManagers never closed?        <- YOUR code
       +-- session.load() in a loop, never cleared? <- YOUR code
```

## 🏭 The Real Production Answer (15-YOE Level)

**Trap answer to reject:** "That's a known Hibernate issue, we should upgrade the version."

**Expert answer:**

This is almost always a misdiagnosis. Hibernate's internal collections grow because your code instructed them to. Libraries retain state on your behalf — they don't acquire resources independently.

In this case: Hibernate's `SessionFactory` has a second-level cache. It grows because:
- Your code configured it without TTL or max size
- Your code is loading and caching thousands of entities
- Your code is not closing `EntityManager` instances, keeping first-level caches alive

What to investigate:
1. How many open EntityManagers are in the dump? (`SELECT em FROM org.hibernate.internal.SessionImpl em`)
2. Is the L2 cache configured with bounds? Check `hibernate.cache.region.*` settings.
3. Are you calling `session.load()` in a loop without clearing the session?

The library is a mirror of your usage patterns. When a library's internal structure is the dominator, ask "what did my code tell it to hold?"

Architect principle: assume your code owns the problem until proven otherwise. Blaming the library is a dead end — you'll find the same issue after the upgrade.

## 🔑 Key Takeaway
A library's internal structures only grow because your code configured or fed them that way — always investigate your own usage before blaming the library.
