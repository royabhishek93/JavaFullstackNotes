# 📑 Complete Index & Interview Questions Map

> Navigate all topics, questions, and answers by category. **Perfect for last-minute interview prep!**

---

## ⚡ QUICK REFERENCE GUIDES (Interview Prep Format)

**Study these first! Each Q&A takes 2-3 minutes. Full code examples included.**

| Topic | File | Questions | Est. Time | Best For |
|-------|------|-----------|-----------|----------|
| **Core Java Essentials** | [CORE_JAVA_QA_REFERENCE.md](Core_Java/CORE_JAVA_QA_REFERENCE.md) | 15 Q&As | 45 mins | String memory, immutability, multithreading, volatile/atomic, async |
| **Modern Java (8-21)** | [JAVA8TO21_QA_REFERENCE.md](Java8to21/JAVA8TO21_QA_REFERENCE.md) | 12 Q&As | 36 mins | Interface defaults, records, sealed classes, pattern matching, CompletableFuture |
| **Spring Boot** | [SPRINGBOOT_QA_REFERENCE.md](SpringBoot/SPRINGBOOT_QA_REFERENCE.md) | 5 Q&As | 15 mins | Bean scopes, thread-safety, circular dependencies |

**Total Quick Study Time:** ~1.5 hours for all three guides

**How to Use:**
1. Pick guides relevant to your interview (Senior? Do all 3)
2. Read the "Problem" to understand context
3. Check "Why It Happens" explanation
4. Study "❌ Wrong Code" to know what not to do
5. Study "✅ Right Code" to know the solution
6. Memorize the "Interview Tip"
7. Use "Quick Checklist" for last-minute review

---

## 🔍 Quick Topic Finder

### By Frequency (Most Asked First)
1. [Bean Scopes](#-spring-bean-scopes) ⭐⭐⭐ (90%+ interviews)
2. [String Memory](#-java-string-memory) ⭐⭐⭐ (85%+ interviews)
3. [Modern Java Features](#-java-9-to-21-features) ⭐⭐⭐ (70%+ interviews)
4. [Immutability](#-immutable-classes--defensive-copying) ⭐⭐⭐ (75%+ interviews)
5. [Multithreading & Concurrency](#-multithreading--concurrency) ⭐⭐ (65%+ interviews)
6. [Interface Default/Static Methods](#-interface-default--static-methods) ⭐⭐ (60%+ interviews)
7. [Circular Dependencies](#-spring-circular-dependencies) ⭐⭐ (40%+ interviews)

---

## 📂 By File & Topic

### 🔥 SPRING FRAMEWORK

---

#### 🌟 Spring: Bean Scopes
**Files:** [spring-bean-scopes.md](SpringBoot/spring-bean-scopes.md) | [spring-bean-scopes-interview.md](SpringBoot/spring-bean-scopes-interview.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What are the main bean scopes in Spring? | Singleton, Prototype, Request, Session, Application | [Interview Q&A](SpringBoot/spring-bean-scopes-interview.md) |
| What happens when you inject a Prototype bean into a Singleton? | Singleton gets one instance, never uses new ones | [Bean Scopes](SpringBoot/spring-bean-scopes.md) |
| Is a Singleton bean thread-safe? | Not automatically - depends on implementation | [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md) |
| How does Spring handle Request scope in non-web contexts? | Throws `ScopeNotActive` exception | [Interview Q&A](SpringBoot/spring-bean-scopes-interview.md) |
| What's the difference between Singleton and Prototype? | Singleton = one per container, Prototype = new each time | [Bean Scopes](SpringBoot/spring-bean-scopes.md) |

**Related Topics:**
- [Singleton Concurrency](#-spring-singleton-concurrency) - Thread safety issues
- [Circular Dependencies](#-spring-circular-dependencies) - Scope-related problems

**Key Concepts:**
- 🔥 Singleton scope basics and when to use
- ✅ Prototype scope memory implications
- ✅ Request/Session lifecycle in web apps
- 👍 Custom scope implementation patterns
- ⚙️ Bean scope conflicts and resolution

---

#### 🌟 Spring: Singleton Concurrency
**File:** [spring-singleton-concurrency.md](SpringBoot/spring-singleton-concurrency.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| Are Spring Singletons thread-safe? | By default NO - shared mutable state is unsafe | [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md) |
| How do you make a Singleton bean thread-safe? | Use immutability, synchronized blocks, or atomic variables | [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md) |
| What's the issue with instance fields in Singleton? | Multiple threads = race conditions and data corruption | [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md) |
| Can you use volatile in Singleton beans? | Yes, but only for specific patterns (lazy init, flags) | [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md) |
| What's the difference between Singleton scope and Thread-local? | Singleton = one per Spring container, ThreadLocal = one per thread | [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md) |

**Related Topics:**
- [Volatile vs Atomic](#-java-volatileatomic-interview) - Thread safety mechanisms
- [Multithreading Guide](#-multithreading--concurrency) - Concurrency fundamentals

**Key Concepts:**
- 🔥 Singleton beans are NOT thread-safe by default
- ✅ How to identify and fix race conditions
- ✅ Synchronized patterns vs atomic variables
- 👍 Double-checked locking pattern
- ⚙️ Performance implications of synchronization

---

#### 🌟 Spring: Circular Dependencies
**File:** [spring-circular-dependency.md](SpringBoot/spring-circular-dependency.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What is a circular dependency? | A → B → A (direct or indirect) | [Circular Dependency](SpringBoot/spring-circular-dependency.md) |
| Does Spring detect circular dependencies? | Yes, throws `BeanCurrentlyInCreationException` | [Circular Dependency](SpringBoot/spring-circular-dependency.md) |
| How do you resolve circular dependencies? | Setter injection, Lazy init, or refactor | [Circular Dependency](SpringBoot/spring-circular-dependency.md) |
| Why does constructor injection fail with circular deps? | Constructor must run before object exists | [Circular Dependency](SpringBoot/spring-circular-dependency.md) |
| When would you use `@Lazy` annotation? | To delay bean creation until first use | [Circular Dependency](SpringBoot/spring-circular-dependency.md) |

**Related Topics:**
- [Bean Scopes](#-spring-bean-scopes) - Factory pattern solutions
- [Singleton Concurrency](#-spring-singleton-concurrency) - Initialization concerns

**Key Concepts:**
- 🔥 Detection at startup (compile-time guarantee)
- ✅ Constructor vs setter injection trade-offs
- ✅ Lazy initialization pattern
- 👍 ObjectProvider pattern for dynamic resolution
- ⚙️ Refactoring to break cycles

---

### ☕ CORE JAVA

---

#### 🌟 Java: String Memory Allocation
**File:** [java-string-memory-allocation.md](Core_Java/java-string-memory-allocation.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What is the String Pool? | Special memory region for string literals | [String Memory](Core_Java/java-string-memory-allocation.md) |
| Why does `a == b` return true but `c == d` returns false? | Pool vs heap: literals in pool, concatenation in heap | [String Memory](Core_Java/java-string-memory-allocation.md) |
| Where does `"hello"` go? | String Pool | [String Memory](Core_Java/java-string-memory-allocation.md) |
| Where does `"hel" + "lo"` go? | Heap (runtime concatenation) | [String Memory](Core_Java/java-string-memory-allocation.md) |
| What does `intern()` do? | Moves string to pool or returns existing pool reference | [String Memory](Core_Java/java-string-memory-allocation.md) |
| Is the String Pool GC'd? | Yes, if no references exist | [String Memory](Core_Java/java-string-memory-allocation.md) |

**Related Topics:**
- [Immutable Classes](#-immutable-classes--defensive-copying) - String immutability design
- [Modern Java Features](#-java-9-to-21-features) - Records and Text Blocks

**Key Concepts:**
- 🔥 String Pool behavior with literals
- 🔥 Memory location differences (Stack vs Heap)
- ✅ Early vs late binding and performance
- ✅ `intern()` method and use cases
- 👍 String Pool implications for large datasets
- ⚙️ GC and String Pool interaction

---

#### 🌟 Java: Immutable Classes & Defensive Copying
**File:** [java-immutable-complete-guide.md](Core_Java/java-immutable-complete-guide.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What makes a class immutable? | Final class, final fields, no setters, defensive copies | [Immutable Guide](Core_Java/java-immutable-complete-guide.md) |
| What is defensive copying? | Creating copies to prevent external modification | [Immutable Guide](Core_Java/java-immutable-complete-guide.md) |
| Why is immutability important? | Thread-safety, caching, security | [Immutable Guide](Core_Java/java-immutable-complete-guide.md) |
| How do you return mutable collections safely? | Return new ArrayList(list), not the original | [Immutable Guide](Core_Java/java-immutable-complete-guide.md) |
| Is String immutable? | Yes - final fields, no setters, defensive copying | [Immutable Guide](Core_Java/java-immutable-complete-guide.md) |
| What's the performance impact of defensive copying? | Small overhead for thread-safety and correctness | [Immutable Guide](Core_Java/java-immutable-complete-guide.md) |

**Related Topics:**
- [String Memory](#-java-string-memory) - How String immutability works
- [Java Records](#-java-9-to-21-features) - Modern immutability pattern
- [Singleton Concurrency](#-spring-singleton-concurrency) - Thread-safe patterns

**Key Concepts:**
- 🔥 Immutability as primary concurrency pattern
- ✅ Defensive copying techniques
- ✅ Collections.unmodifiableList() vs new ArrayList()
- 👍 Performance vs correctness trade-offs
- ⚙️ Deep copy vs shallow copy scenarios

---

#### 🌟 Java: Java 9-21 Features
**File:** [java-9-to-21-features.md](Java8to21/java-9-to-21-features.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What are Records? | Immutable DTOs with generated equals/hashCode/toString | [Java 9-21](Java8to21/java-9-to-21-features.md) |
| What are Sealed Classes? | Control inheritance - only specific classes can extend | [Java 9-21](Java8to21/java-9-to-21-features.md) |
| How does Pattern Matching simplify code? | Combine type check and cast: `if (obj instanceof String s)` | [Java 9-21](Java8to21/java-9-to-21-features.md) |
| What's the difference between Records and Data Classes? | Records are final and fully immutable | [Java 9-21](Java8to21/java-9-to-21-features.md) |
| When should you use Text Blocks? | Multi-line strings for JSON, SQL, HTML | [Java 9-21](Java8to21/java-9-to-21-features.md) |
| What's the advantage of var keyword? | Reduce boilerplate, improve readability | [Java 9-21](Java8to21/java-9-to-21-features.md) |

**Related Topics:**
- [Immutable Classes](#-immutable-classes--defensive-copying) - Records as immutable pattern
- [String Memory](#-java-string-memory) - Text Blocks efficiency
- [Interface Methods](#-interface-default--static-methods) - Records with interface contracts

**Key Concepts:**
- 🔥 Records eliminate boilerplate (100+ lines → 10)
- ✅ Sealed Classes for domain modeling
- ✅ Pattern Matching for type safety
- 👍 Text Blocks for readability (SQL, JSON, HTML)
- 👍 Local variable type inference (var)
- ⚙️ Switch expressions (Java 14+)

---

#### 🌟 Java: Volatile & AtomicInteger
**File:** [java-volatile-atomic-interview.md](Core_Java/java-volatile-atomic-interview.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What does volatile do? | Forces read/write from main memory, prevents caching | [Volatile & Atomic](Core_Java/java-volatile-atomic-interview.md) |
| What's the difference between volatile and synchronized? | Volatile = visibility only, synchronized = visibility + atomicity | [Volatile & Atomic](Core_Java/java-volatile-atomic-interview.md) |
| When should you use AtomicInteger? | For atomic compound operations (read-modify-write) | [Volatile & Atomic](Core_Java/java-volatile-atomic-interview.md) |
| Is volatile a replacement for locks? | No - doesn't guarantee atomicity | [Volatile & Atomic](Core_Java/java-volatile-atomic-interview.md) |
| What's the performance advantage of volatile? | Faster than synchronized (no lock overhead) | [Volatile & Atomic](Core_Java/java-volatile-atomic-interview.md) |

**Related Topics:**
- [Multithreading & Concurrency](#-multithreading--concurrency) - Deep concurrency patterns
- [Singleton Concurrency](#-spring-singleton-concurrency) - Thread-safe beans
- [Immutability](#-immutable-classes--defensive-copying) - Immutability vs synchronization

**Key Concepts:**
- 🔥 Volatile visibility guarantees
- ✅ Atomic operations and CAS (Compare-And-Swap)
- ✅ Performance: volatile > synchronized > locks
- 👍 Double-checked locking pattern
- ⚙️ Memory barriers and happens-before relationships

---

#### 🌟 Java: Multithreading & Concurrency
**File:** [java-multithreading-concurrency-guide.md](Core_Java/java-multithreading-concurrency-guide.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What's the difference between Thread and Runnable? | Thread is a class, Runnable is an interface | [Multithreading](Core_Java/java-multithreading-concurrency-guide.md) |
| What is a race condition? | Multiple threads access shared mutable state → unpredictable behavior | [Multithreading](Core_Java/java-multithreading-concurrency-guide.md) |
| How do you prevent race conditions? | Synchronization, immutability, atomic variables, or locks | [Multithreading](Core_Java/java-multithreading-concurrency-guide.md) |
| What's the difference between synchronized method and block? | Method = entire method locked, block = only critical section | [Multithreading](Core_Java/java-multithreading-concurrency-guide.md) |
| What are ExecutorService and Thread Pools? | Manage threads efficiently without creating new ones each time | [Multithreading](Core_Java/java-multithreading-concurrency-guide.md) |
| What's a deadlock and how do you prevent it? | Circular wait → lock order, timeout, or tryLock() | [Multithreading](Core_Java/java-multithreading-concurrency-guide.md) |

**Related Topics:**
- [Volatile & Atomic](#-java-volatileatomic-interview) - Low-level synchronization
- [Singleton Concurrency](#-spring-singleton-concurrency) - Spring bean thread-safety
- [Immutability](#-immutable-classes--defensive-copying) - Concurrency without locks

**Key Concepts:**
- 🔥 Race conditions and synchronization
- 🔥 Thread pools and ExecutorService
- ✅ Locks and ReentrantLock
- ✅ Volatile and Atomic classes
- 👍 Deadlock detection and prevention
- 👍 Thread safety design patterns
- ⚙️ ConcurrentHashMap and concurrent collections

---

#### 🌟 Java: CompletableFuture Interview
**File:** [java-completablefuture-interview.md](Java8to21/java-completablefuture-interview.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What is CompletableFuture? | Promise of a value that will be available in the future | [CompletableFuture](Java8to21/java-completablefuture-interview.md) |
| What's the difference between Future and CompletableFuture? | CF is composable, cancelable, and has callbacks | [CompletableFuture](Java8to21/java-completablefuture-interview.md) |
| How do you chain async operations? | thenApply(), thenAccept(), thenCombine() | [CompletableFuture](Java8to21/java-completablefuture-interview.md) |
| What happens if you don't complete a CompletableFuture? | Thread hangs forever on .get() | [CompletableFuture](Java8to21/java-completablefuture-interview.md) |
| How do you handle exceptions in CF? | exceptionally(), handle(), or whenComplete() | [CompletableFuture](Java8to21/java-completablefuture-interview.md) |

**Related Topics:**
- [Multithreading & Concurrency](#-multithreading--concurrency) - Thread pool management
- [Non-Blocking vs Async](#-java-non-blocking-vs-async) - Related concepts
- [Java 9-21 Features](#-java-9-to-21-features) - Modern async patterns

**Key Concepts:**
- 🔥 CompletableFuture vs callbacks
- ✅ Chaining async operations
- ✅ Exception handling patterns
- 👍 Parallel task execution
- ⚙️ Custom executor configuration

---

#### 🌟 Java: Non-Blocking vs Async
**File:** [java-non-blocking-vs-async-interview.md](Core_Java/java-non-blocking-vs-async-interview.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What's the difference between Blocking and Non-Blocking? | Blocking = wait for result, Non-Blocking = return immediately | [Non-Blocking vs Async](Core_Java/java-non-blocking-vs-async-interview.md) |
| Is async the same as non-blocking? | Not exactly - async uses callbacks, NB returns immediately | [Non-Blocking vs Async](Core_Java/java-non-blocking-vs-async-interview.md) |
| Give a real example of blocking code | Socket.read() - thread sleeps until data available | [Non-Blocking vs Async](Core_Java/java-non-blocking-vs-async-interview.md) |
| Give a real example of non-blocking code | NIO channels or event-driven systems | [Non-Blocking vs Async](Core_Java/java-non-blocking-vs-async-interview.md) |
| When should you use non-blocking? | High-traffic services with many concurrent requests | [Non-Blocking vs Async](Core_Java/java-non-blocking-vs-async-interview.md) |

**Related Topics:**
- [CompletableFuture](#-java-completablefuture-interview) - Async mechanisms
- [Multithreading](#-multithreading--concurrency) - Thread management
- [Spring Singleton](#-spring-singleton-concurrency) - Shared resource handling

**Key Concepts:**
- 🔥 Blocking vs Non-Blocking distinctions
- ✅ Callback patterns
- ✅ Event-driven architecture
- 👍 Reactor and Project Reactor concepts
- ⚙️ NIO channels and selectors

---

#### 🌟 Java: Interface Default & Static Methods
**File:** [Java8to21/java-interface-default-static-methods.md](Java8to21/java-interface-default-static-methods.md)

**Core Questions:**

| Question | Answer Preview | File |
|----------|---|------|
| What was the main problem before Java 8 interfaces? | Adding method = breaking all 500+ implementations | [Interface Methods](Java8to21/java-interface-default-static-methods.md) |
| What is a default method? | Method with implementation in interface (optional override) | [Interface Methods](Java8to21/java-interface-default-static-methods.md) |
| What are static methods in interfaces for? | Utility/factory functions (no polymorphism) | [Interface Methods](Java8to21/java-interface-default-static-methods.md) |
| What happens with conflicting default methods? | Compiler error - must override to resolve | [Interface Methods](Java8to21/java-interface-default-static-methods.md) |
| Can you override a static method in interface? | No - static methods don't override (shadowing only) | [Interface Methods](Java8to21/java-interface-default-static-methods.md) |
| What are Java 9+ private methods in interfaces? | Hide internal logic from implementations | [Interface Methods](Java8to21/java-interface-default-static-methods.md) |
| What's the version compatibility trap? | Default methods are binary-compatible but can break contracts | [Interface Methods](Java8to21/java-interface-default-static-methods.md) |

**Related Topics:**
- [Java 9-21 Features](#-java-9-to-21-features) - Modern Java patterns
- [String Memory](#-java-string-memory) - Collections API evolution example
- [Immutable Classes](#-immutable-classes--defensive-copying) - Interface design patterns

**Key Concepts:**
- 🔥 Interface evolution without breaking changes (MOST IMPORTANT)
- 🔥 Java 9+ private methods for code reuse
- ✅ Multiple inheritance conflict resolution
- ✅ Version compatibility and semantic contracts
- ✅ Static methods for utilities only
- 👍 Functional interface constraints
- ⚙️ Debugging challenges with defaults

---

---

## 🎯 By Interview Level

### Junior Developer (Focus on basics)
1. [String Memory Allocation](Core_Java/java-string-memory-allocation.md) - 30 min
2. [Bean Scopes Basics](SpringBoot/spring-bean-scopes.md) - 30 min
3. [Java 9-21 Features](Java8to21/java-9-to-21-features.md) - 45 min

**Total:** 1h 45m

---

### Mid-Level Developer (Cover common patterns)
1. All above +
2. [Immutable Classes](Core_Java/java-immutable-complete-guide.md) - 45 min
3. [Volatile & Atomic](Core_Java/java-volatile-atomic-interview.md) - 30 min
4. [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md) - 30 min
5. [Circular Dependencies](SpringBoot/spring-circular-dependency.md) - 20 min
6. [Interface Methods](Java8to21/java-interface-default-static-methods.md) - 30 min

**Total:** 3h 15m

---

### Senior Developer (Master everything)
1. All above +
2. [Multithreading & Concurrency](Core_Java/java-multithreading-concurrency-guide.md) - 2 hours
3. [CompletableFuture](Java8to21/java-completablefuture-interview.md) - 1 hour
4. [Non-Blocking vs Async](Core_Java/java-non-blocking-vs-async-interview.md) - 45 min
5. Focus on pitfalls and trade-offs sections

**Total:** 6-7 hours

---

## 🔥 Most Frequently Asked

### Top 10 Interview Questions

1. **"What's the difference between `==` and `equals()` for strings?"**
   - Answer: See [String Memory](Core_Java/java-string-memory-allocation.md)
   - Related: Pool vs Heap allocation

2. **"What bean scopes does Spring have?"**
   - Answer: See [Bean Scopes](SpringBoot/spring-bean-scopes.md)
   - Related: Singleton vs Prototype implications

3. **"What happens if you inject a Prototype bean into a Singleton?"**
   - Answer: See [Bean Scopes Interview Q&A](SpringBoot/spring-bean-scopes-interview.md)
   - Related: Scope lifecycle and memory

4. **"Are Singleton beans thread-safe?"**
   - Answer: See [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md)
   - Related: Synchronization patterns, volatile, atomic

5. **"What's a circular dependency and how do you resolve it?"**
   - Answer: See [Circular Dependencies](SpringBoot/spring-circular-dependency.md)
   - Related: Constructor vs setter injection

6. **"What makes a class immutable?"**
   - Answer: See [Immutable Classes](Core_Java/java-immutable-complete-guide.md)
   - Related: String immutability, Records

7. **"What are Records and when should you use them?"**
   - Answer: See [Java 9-21 Features](Java8to21/java-9-to-21-features.md)
   - Related: Sealed classes, pattern matching

8. **"What's the difference between volatile and synchronized?"**
   - Answer: See [Volatile & Atomic](Core_Java/java-volatile-atomic-interview.md)
   - Related: Memory barriers, lock-free patterns

9. **"How do default methods help with interface evolution?"**
   - Answer: See [Interface Methods](Java8to21/java-interface-default-static-methods.md)
   - Related: Java 8 changes, Collections API

10. **"What's the difference between blocking and non-blocking I/O?"**
    - Answer: See [Non-Blocking vs Async](Core_Java/java-non-blocking-vs-async-interview.md)
    - Related: CompletableFuture, reactive programming

---

## 📊 Coverage Matrix

| Topic | Junior | Mid | Senior | Frequency | Time |
|-------|--------|-----|--------|-----------|------|
| String Memory | ✅ | ✅ | ✅ | 85% | 30m |
| Bean Scopes | ✅ | ✅ | ✅ | 90% | 30m |
| Java 9-21 | ✅ | ✅ | ✅ | 70% | 45m |
| Immutability | ❌ | ✅ | ✅ | 75% | 45m |
| Volatile/Atomic | ❌ | ✅ | ✅ | 60% | 30m |
| Singleton Thread-Safety | ❌ | ✅ | ✅ | 55% | 30m |
| Circular Deps | ❌ | ✅ | ✅ | 40% | 20m |
| Interface Methods | ❌ | ✅ | ✅ | 60% | 30m |
| Multithreading | ❌ | ❌ | ✅ | 70% | 2h |
| CompletableFuture | ❌ | ❌ | ✅ | 50% | 1h |
| Non-Blocking/Async | ❌ | ❌ | ✅ | 45% | 45m |

---

## 🎓 Study Strategies

### For Job Interview in 1 Week
**Priority:** Focus on frequency
1. [String Memory](Core_Java/java-string-memory-allocation.md)
2. [Bean Scopes](SpringBoot/spring-bean-scopes.md)
3. [Java 9-21](Java8to21/java-9-to-21-features.md)
4. [Immutable Classes](Core_Java/java-immutable-complete-guide.md)

### For Senior Role in 2 Weeks
**Add:** Trade-offs and pitfalls
1. All above
2. [Volatile & Atomic](Core_Java/java-volatile-atomic-interview.md)
3. [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md)
4. [Interface Methods](Java8to21/java-interface-default-static-methods.md) (Java 9+ private methods!)
5. [Circular Dependencies](SpringBoot/spring-circular-dependency.md)

### For Deep Mastery (1 Month)
**Add:** Architecture and design patterns
1. All above
2. [Multithreading](Core_Java/java-multithreading-concurrency-guide.md)
3. [CompletableFuture](Java8to21/java-completablefuture-interview.md)
4. [Non-Blocking/Async](Core_Java/java-non-blocking-vs-async-interview.md)

---

## 🔗 Topic Cross-References

### If you got a question about...

**String behavior?**
→ [String Memory](Core_Java/java-string-memory-allocation.md)
→ [Immutable Classes](Core_Java/java-immutable-complete-guide.md)
→ [Java 9-21 Features](Java8to21/java-9-to-21-features.md) (Text Blocks)

**Thread safety?**
→ [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md)
→ [Volatile & Atomic](Core_Java/java-volatile-atomic-interview.md)
→ [Multithreading](Core_Java/java-multithreading-concurrency-guide.md)
→ [Immutable Classes](Core_Java/java-immutable-complete-guide.md) (as solution)

**Spring Beans?**
→ [Bean Scopes](SpringBoot/spring-bean-scopes.md)
→ [Singleton Concurrency](SpringBoot/spring-singleton-concurrency.md)
→ [Circular Dependencies](SpringBoot/spring-circular-dependency.md)

**Java Fundamentals?**
→ [String Memory](Core_Java/java-string-memory-allocation.md)
→ [Immutable Classes](Core_Java/java-immutable-complete-guide.md)
→ [Java 9-21 Features](Java8to21/java-9-to-21-features.md)

**Modern Java?**
→ [Java 9-21 Features](Java8to21/java-9-to-21-features.md)
→ [Interface Methods](Java8to21/java-interface-default-static-methods.md)
→ [CompletableFuture](Java8to21/java-completablefuture-interview.md)

**Async/Reactive?**
→ [Non-Blocking vs Async](Core_Java/java-non-blocking-vs-async-interview.md)
→ [CompletableFuture](Java8to21/java-completablefuture-interview.md)
→ [Multithreading](Core_Java/java-multithreading-concurrency-guide.md)

---

## 💾 Downloadable Cheat Sheets

### One-Page Cheat: Common Interview Questions
- [Saved as part of each file's Interview Tips section]

### Memory Diagrams
- String Pool vs Heap: [String Memory](Core_Java/java-string-memory-allocation.md)
- Bean Lifecycle: [Bean Scopes](SpringBoot/spring-bean-scopes.md)
- Thread synchronization: [Multithreading](Core_Java/java-multithreading-concurrency-guide.md)

---

## 🚀 How to Use This Index

1. **Find your target role:** Junior / Mid / Senior
2. **Pick the most frequent topics** from coverage matrix
3. **Read the file** for that topic
4. **Follow related topics** using cross-references
5. **Practice the interview questions** (20+ per file)
6. **Explain concepts out loud** (best learning method)

---

## 📌 Quick Navigation

**Back to main:** [README.md](README.md)  
**Leftover topics:** [LEFTOVER_TOPICS.md](LEFTOVER_TOPICS.md)

---

**Last Updated:** February 21, 2026  
**Total Topics:** 11  
**Total Questions:** 200+  
**Total Study Time:** 5-7 hours for mastery

**Happy studying! 🎓**
