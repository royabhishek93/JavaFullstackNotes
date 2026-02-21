# 📂 Individual Question Files - How to Use

> Each question is now in its own file for maximum focus during interview prep

---

## 🚀 Quick Navigation by Topic

### 🔥 CORE JAVA (String Memory, Immutability, Concurrency)

#### String Memory (4 Questions)
- [Q1: Where does `"hello"` go in memory?](Core_Java/Q1_string_pool_memory.md)
- [Q2: Why does `c == d` return false when both are `"hi"`?](Core_Java/Q2_string_concatenation.md)
- [Q3: What does `.intern()` do?](Core_Java/Q3_string_intern_method.md)
- [Q4: How does GC work with String Pool?](Core_Java/Q4_string_garbage_collection.md)

**Study This If:** Your interview involves Java fundamentals, backend development, or memory optimization

**Time Needed:** ~10 minutes total

**Key Concepts:**
- String Pool vs Heap allocation
- Reference equality vs content equality (`==` vs `.equals()`)
- Memory optimization through string pooling

---

#### Immutable Classes (3+ Questions)
- [Q5: What makes a class immutable?](Core_Java/Q5_immutable_class_requirements.md)
- [Q6: Deep copy vs shallow copy?](Core_Java/Q6_defensive_copying_vs_clone.md)
- [Q7: Returning mutable collections safely](Core_Java/Q7_return_mutable_collections.md) [Coming soon]

**Study This If:** You're designing DTOs, value objects, or working on thread-safe code

**Time Needed:** ~12 minutes total

**Key Concepts:**
- Four requirements for immutability
- Defensive copying patterns
- Safe collection returns

---

#### Multithreading & Concurrency (6+ Questions)
- [Q8: Race conditions - what are they?](Core_Java/Q8_race_conditions.md) [Coming soon]
- [Q9: Synchronized methods vs blocks](Core_Java/Q9_synchronized_methods_vs_blocks.md) [Coming soon]
- [Q10: How to prevent deadlocks?](Core_Java/Q10_deadlock_prevention.md) [Coming soon]
- [Q11: What is volatile?](Core_Java/Q11_volatile_visibility.md) [Coming soon]
- [Q12: Volatile vs Synchronized](Core_Java/Q12_volatile_vs_synchronized.md) [Coming soon]
- [Q13: When to use AtomicInteger?](Core_Java/Q13_atomicinteger_usage.md) [Coming soon]

**Study This If:** Interview involves backend services, concurrent systems, or microservices

**Time Needed:** ~20 minutes total

---

#### Asynchronous Programming (2 Questions)
- [Q14: Blocking vs Non-Blocking?](Core_Java/Q14_blocking_vs_nonblocking.md) [Coming soon]
- [Q15: Async vs Non-Blocking - What's the difference?](Core_Java/Q15_async_vs_nonblocking.md) [Coming soon]

**Study This If:** Interview is for reactive systems, APIs, or high-throughput services

**Time Needed:** ~8 minutes total

---

### ✨ MODERN JAVA 8-21

#### Interface Evolution (5 Questions)
- [Q1: Main problem before Java 8?](Java8to21/Q1_interface_problem_before_java8.md) [Coming soon]
- [Q2: What is a default method?](Java8to21/Q2_default_methods.md) [Coming soon]
- [Q3: Static methods in interfaces?](Java8to21/Q3_static_methods_interfaces.md) [Coming soon]
- [Q4: Private methods (Java 9+)?](Java8to21/Q4_private_methods_interfaces.md) [Coming soon]
- [Q5: Conflicting default methods?](Java8to21/Q5_conflicting_default_methods.md) [Coming soon]

**Study This If:** Interview asks about modern Java APIs, framework design, or backward compatibility

---

#### Records & Sealed Classes (2 Questions)
- [Q6: What are Records?](Java8to21/Q6_records_introduced.md) [Coming soon]
- [Q7: What are Sealed Classes?](Java8to21/Q7_sealed_classes.md) [Coming soon]

**Study This If:** Interview involves data modeling, DTOs, or Java 15+

---

#### Pattern Matching & Text Blocks (2 Questions)
- [Q8: What is Pattern Matching?](Java8to21/Q8_pattern_matching.md) [Coming soon]
- [Q9: What are Text Blocks?](Java8to21/Q9_text_blocks.md) [Coming soon]

**Study This If:** Interview mentions code cleanliness, Java 16+, or modern syntax

---

#### CompletableFuture (3 Questions)
- [Q10: What is CompletableFuture?](Java8to21/Q10_completablefuture_basics.md) [Coming soon]
- [Q11: Chaining async operations?](Java8to21/Q11_chaining_async_operations.md) [Coming soon]
- [Q12: Exception handling in async?](Java8to21/Q12_exception_handling_async.md) [Coming soon]

**Study This If:** Interview involves reactive programming or async APIs

---

### 🌟 SPRING BOOT

#### Bean Scopes & Configuration (5 Questions)
- [Q1: What are bean scopes?](SpringBoot/Q1_bean_scopes.md) [Coming soon]
- [Q2: Prototype in Singleton?](SpringBoot/Q2_prototype_in_singleton.md) [Coming soon]
- [Q3: Is Singleton thread-safe?](SpringBoot/Q3_singleton_thread_safety.md) [Coming soon]
- [Q4: Singleton vs ThreadLocal?](SpringBoot/Q4_singleton_vs_threadlocal.md) [Coming soon]
- [Q5: Circular dependencies?](SpringBoot/Q5_circular_dependencies.md) [Coming soon]

**Study This If:** You're working with Spring Boot or backend frameworks

---

## 📱 How to Use These Files

### Before Interview (1-2 hours prep)

**Step 1: Pick your topic** (~5 mins)
```
Interview is for: Payment Gateway Backend
Relevant topics: String Memory, Immutability, Concurrency, Bean Scopes
```

**Step 2: Study 3-4 individual questions** (~30 mins)
```
Pick Q1, Q2, Q5, Q11
Read each file carefully
```

**Step 3: Read the Interview Tip** (~5 mins)
```
Memorize the exact answer you should give
```

**Step 4: Practice out loud** (~10 mins)
```
"The main problem before Java 8 was..."
```

---

### During Interview

When interviewer asks: "Explain string memory allocation"

**Your approach:**
1. Open your mental file: [Q1_string_pool_memory.md](Core_Java/Q1_string_pool_memory.md)
2. Lead with the Interview Tip
3. Use the "Why It Happens" section for explanation
4. Reference the code example if they ask for details
5. Use Quick Checklist to ensure you didn't miss anything

---

## 🎯 Study Paths by Role

### Path A: Backend API Server (3 hours)
- String Memory: Q1, Q2, Q3
- Bean Scopes: Q1, Q2, Q3
- CompletableFuture: Q10, Q11
- Concurrency: Q11, Q12, Q13

### Path B: Data-Heavy Systems (3 hours)
- Immutability: Q5, Q6, Q7
- Concurrency: Q8, Q9, Q10, Q13
- Volatile/Atomic: Q11, Q12, Q13
- Records: Java8to21 Q6

### Path C: High-Throughput Reactive (2.5 hours)
- Async vs Blocking: Q14, Q15
- CompletableFuture: Q10, Q11, Q12
- Default Methods: Java8to21 Q1, Q2
- Pattern Matching: Java8to21 Q8

### Path D: Spring Framework Deep Dive (2 hours)
- Bean Scopes: Q1, Q2, Q3, Q4, Q5
- Concurrency: Q3 (thread-safety)
- Immutability: Q5, Q6

---

## 💡 Pro Tips

**Tip 1:** Read before bed the night before
- Brain consolidates memory during sleep
- 15 minutes of reading = day-of retention boost

**Tip 2:** Say it out loud
- Interviews are verbal
- Reading is passive
- Practice speaking the answers

**Tip 3:** Link concepts
- String memory connects to Immutability (Q1 → Q5)
- Concurrency connects to Spring Scopes (Q3, Q12 → SpringBoot Q3, Q4)
- Create mental connections

**Tip 4:** Do the code examples
- Copy them to your editor
- Change values and see what happens
- Build muscle memory

---

## 📊 File Organization

```
Core_Java/
├── Q1_string_pool_memory.md           # Study time: 2 mins
├── Q2_string_concatenation.md         # Study time: 2 mins
├── Q3_string_intern_method.md         # Study time: 2 mins
├── Q4_string_garbage_collection.md    # Study time: 2 mins
├── Q5_immutable_class_requirements.md # Study time: 2 mins
├── Q6_defensive_copying_vs_clone.md   # Study time: 3 mins
├── Q7_return_mutable_collections.md   # Study time: 3 mins
├── Q8_race_conditions.md              # Study time: 3 mins
├── Q9_synchronized_methods_vs_blocks.md
├── Q10_deadlock_prevention.md
├── Q11_volatile_visibility.md
├── Q12_volatile_vs_synchronized.md
├── Q13_atomicinteger_usage.md
├── Q14_blocking_vs_nonblocking.md
├── Q15_async_vs_nonblocking.md
└── CORE_JAVA_QA_REFERENCE.md          # Full reference (all 15 Q&As)

Java8to21/
├── Q1_interface_problem_before_java8.md
├── Q2_default_methods.md
├── ... (10 more files)
└── JAVA8TO21_QA_REFERENCE.md          # Full reference (all 12 Q&As)

SpringBoot/
├── Q1_bean_scopes.md
├── Q2_prototype_in_singleton.md
├── Q3_singleton_thread_safety.md
├── Q4_singleton_vs_threadlocal.md
├── Q5_circular_dependencies.md
└── SPRINGBOOT_QA_REFERENCE.md         # Full reference (all 5 Q&As)
```

---

**Last Updated:** February 21, 2026
